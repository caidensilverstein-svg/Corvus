"""
Install loop with interactive conflict resolution.

Flow per tool:
  1. Attempt install via package manager.
  2. On success → mark done.
  3. On dependency conflict → present Ubuntu-style prompt:
       (K)eep existing  /  (R)eplace  /  (S)kip
  4. On other failure → mark failed with captured stderr.
"""

import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from rich.console import Console
from rich.prompt import Prompt

from .detect import SystemInfo
from .matrix import ToolEntry

console = Console()


class InstallStatus(Enum):
    SUCCESS = auto()
    SKIPPED = auto()
    FAILED = auto()
    UNAVAILABLE = auto()  # not in matrix for this PM


class ConflictChoice(Enum):
    KEEP = "keep"
    REPLACE = "replace"
    SKIP = "skip"


@dataclass
class InstallResult:
    tool: str
    package: str
    status: InstallStatus
    reason: str = ""


# ── Package manager command builders ────────────────────────────────────────

def _build_install_cmd(pm: str, package: str, replace: bool = False) -> list[str]:
    """Return the shell command list to install a package."""
    base = {
        "apt": ["sudo", "apt-get", "install", "-y"],
        "pacman": ["sudo", "pacman", "-S", "--noconfirm"],
        "dnf": ["sudo", "dnf", "install", "-y"],
        "brew": ["brew", "install"],
    }
    cmd = base.get(pm, [])
    if not cmd:
        raise ValueError(f"Unknown package manager: {pm}")

    if replace:
        if pm == "apt":
            cmd = ["sudo", "apt-get", "install", "-y", "--reinstall"]
        elif pm == "pacman":
            cmd = ["sudo", "pacman", "-S", "--noconfirm"]

    return cmd + [package]


def _is_conflict_error(stderr: str, pm: str) -> bool:
    """Heuristically detect dependency conflict output."""
    conflict_signals = {
        "apt": [
            "held broken packages",
            "unmet dependencies",
            "conflicts with",
            "dependency problems",
        ],
        "pacman": [
            "conflicting packages",
            "conflict",
        ],
        "dnf": [
            "conflicts",
            "conflict",
            "protected multilib versions",
        ],
        "brew": [
            "already installed",
            "conflicts with",
        ],
    }
    signals = conflict_signals.get(pm, [])
    lower = stderr.lower()
    return any(s in lower for s in signals)


# ── Conflict resolution prompt ───────────────────────────────────────────────

def _prompt_conflict(tool: str, package: str, stderr: str) -> ConflictChoice:
    """
    Display an Ubuntu-style conflict prompt and return the user's choice.
    Never auto-resolves — always waits for explicit input.
    """
    console.print()
    console.print(f"[bold yellow]Conflict detected while installing [cyan]{tool}[/cyan][/bold yellow]")
    console.print(f"[dim]{stderr.strip()[-600:]}[/dim]")  # last 600 chars of error
    console.print()
    console.print("How would you like to resolve this?")
    console.print("  [bold](K)[/bold]eep existing packages, skip this tool")
    console.print("  [bold](R)[/bold]eplace / reinstall (may overwrite existing files)")
    console.print("  [bold](S)[/bold]kip this tool entirely")
    console.print()

    while True:
        raw = Prompt.ask(
            "Choice",
            choices=["k", "r", "s", "K", "R", "S"],
            default="s",
            show_choices=False,
        ).lower()
        if raw == "k":
            return ConflictChoice.KEEP
        if raw == "r":
            return ConflictChoice.REPLACE
        if raw == "s":
            return ConflictChoice.SKIP


# ── Core install routine ─────────────────────────────────────────────────────

def install_tool(tool: ToolEntry, info: SystemInfo, dry_run: bool = False) -> InstallResult:
    """
    Attempt to install a single tool.  Returns an InstallResult.
    If dry_run=True, prints what would run but does not execute.
    """
    pm = info.package_manager
    package = tool.packages.get(pm)

    if package is None:
        return InstallResult(
            tool=tool.name,
            package="",
            status=InstallStatus.UNAVAILABLE,
            reason=f"No package defined for {pm}",
        )

    if dry_run:
        cmd = _build_install_cmd(pm, package)
        console.print(f"  [dim]dry-run:[/dim] {' '.join(cmd)}")
        return InstallResult(tool=tool.name, package=package, status=InstallStatus.SUCCESS, reason="dry-run")

    # First attempt
    result = _run_install(pm, package, replace=False)
    if result.status == InstallStatus.SUCCESS:
        return result

    # If it's a conflict, ask the user
    if result.status == InstallStatus.FAILED and _is_conflict_error(result.reason, pm):
        choice = _prompt_conflict(tool.name, package, result.reason)

        if choice == ConflictChoice.SKIP or choice == ConflictChoice.KEEP:
            return InstallResult(
                tool=tool.name,
                package=package,
                status=InstallStatus.SKIPPED,
                reason=f"User chose {choice.value} during conflict",
            )

        if choice == ConflictChoice.REPLACE:
            result = _run_install(pm, package, replace=True)
            return result

    return result


def _run_install(pm: str, package: str, replace: bool) -> InstallResult:
    """Execute the install command and capture output."""
    try:
        cmd = _build_install_cmd(pm, package, replace=replace)
    except ValueError as e:
        return InstallResult(
            tool=package,
            package=package,
            status=InstallStatus.FAILED,
            reason=str(e),
        )

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5-minute cap per tool
        )
    except subprocess.TimeoutExpired:
        return InstallResult(
            tool=package,
            package=package,
            status=InstallStatus.FAILED,
            reason="Install timed out after 5 minutes",
        )
    except FileNotFoundError:
        return InstallResult(
            tool=package,
            package=package,
            status=InstallStatus.FAILED,
            reason=f"Package manager '{pm}' not found on PATH",
        )

    if proc.returncode == 0:
        return InstallResult(tool=package, package=package, status=InstallStatus.SUCCESS)

    return InstallResult(
        tool=package,
        package=package,
        status=InstallStatus.FAILED,
        reason=(proc.stderr or proc.stdout).strip(),
    )


# ── Batch install loop ───────────────────────────────────────────────────────

def run_install_loop(
    tools: list[ToolEntry],
    info: SystemInfo,
    dry_run: bool = False,
) -> list[InstallResult]:
    """
    Iterate over tools, print live status, and return all results.
    """
    results: list[InstallResult] = []
    total = len(tools)

    for idx, tool in enumerate(tools, 1):
        console.print(f"\n[bold][[{idx}/{total}]][/bold] Installing [cyan]{tool.name}[/cyan] — {tool.description}")

        result = install_tool(tool, info, dry_run=dry_run)
        results.append(result)

        if result.status == InstallStatus.SUCCESS:
            console.print(f"  [green]✓ installed[/green] ({result.package})")
        elif result.status == InstallStatus.SKIPPED:
            console.print(f"  [yellow]⚡ skipped[/yellow] — {result.reason}")
        elif result.status == InstallStatus.UNAVAILABLE:
            console.print(f"  [dim]– not available for {info.package_manager}[/dim]")
        else:
            short = result.reason[:120] + "..." if len(result.reason) > 120 else result.reason
            console.print(f"  [red]✗ failed[/red] — {short}")

    return results
