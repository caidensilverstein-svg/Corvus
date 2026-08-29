"""
Install loop with interactive conflict resolution.

Flow per tool:
  1. Check already installed → skip.
  2. Attempt install via package manager.
  3. On success → mark done, append to rollback log.
  4. On dependency conflict → present prompt: (K)eep / (R)eplace / (S)kip.
  5. On other failure → mark failed with captured stderr.
"""

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Optional

_SUDO = [] if os.getuid() == 0 else ["sudo"]

from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TaskProgressColumn, TimeElapsedColumn, SpinnerColumn
from rich.prompt import Prompt

from .detect import SystemInfo
from .matrix import ToolEntry

console = Console()

_ROLLBACK_LOG = Path.home() / ".corvus" / "install_log.txt"


class InstallStatus(Enum):
    SUCCESS = auto()
    SKIPPED = auto()
    ALREADY_INSTALLED = auto()
    FAILED = auto()
    UNAVAILABLE = auto()


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


# ── Package index sync ───────────────────────────────────────────────────────

def pm_sync(pm: str, verbose: bool = False) -> None:
    cmds = {
        "apt":    _SUDO + ["apt-get", "update", "-qq"],
        "pacman": _SUDO + ["pacman", "-Sy", "--noconfirm"],
        "dnf":    _SUDO + ["dnf", "check-update"],
        "zypper": _SUDO + ["zypper", "refresh"],
        "brew":   ["brew", "update"],
    }
    cmd = cmds.get(pm)
    if not cmd:
        return
    label = " ".join(cmd)
    console.print(f"[dim]$ {label}[/dim]")
    kwargs = {"timeout": 180, "env": {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}}
    if verbose:
        subprocess.run(cmd, **kwargs)
    else:
        subprocess.run(cmd, capture_output=True, **kwargs)


# ── Already-installed check ──────────────────────────────────────────────────

def _is_installed(pm: str, package: str) -> bool:
    try:
        if pm == "apt":
            r = subprocess.run(["dpkg", "-l", package], capture_output=True, timeout=10)
            return r.returncode == 0 and b"ii" in r.stdout
        if pm == "pacman":
            r = subprocess.run(["pacman", "-Q", package], capture_output=True, timeout=10)
            return r.returncode == 0
        if pm in ("dnf", "zypper"):
            r = subprocess.run(["rpm", "-q", package], capture_output=True, timeout=10)
            return r.returncode == 0
        if pm == "brew":
            r = subprocess.run(["brew", "list", "--formula", package], capture_output=True, timeout=10)
            return r.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return False


# ── Package manager command builders ────────────────────────────────────────

def _build_install_cmd(pm: str, package: str, replace: bool = False) -> list[str]:
    if pm == "apt":
        if replace:
            return _SUDO + ["apt-get", "install", "-y", "--reinstall", package]
        return _SUDO + ["apt-get", "install", "-y", package]
    if pm == "pacman":
        if replace:
            return _SUDO + ["pacman", "-S", "--noconfirm", "--overwrite", "*", package]
        return _SUDO + ["pacman", "-S", "--noconfirm", package]
    if pm == "dnf":
        return _SUDO + ["dnf", "install", "-y", package]
    if pm == "zypper":
        if replace:
            return _SUDO + ["zypper", "install", "-y", "--force", package]
        return _SUDO + ["zypper", "install", "-y", package]
    if pm == "brew":
        return ["brew", "install", package]
    raise ValueError(f"Unknown package manager: {pm}")


def _is_conflict_error(stderr: str, pm: str) -> bool:
    conflict_signals = {
        "apt":    ["held broken packages", "unmet dependencies", "conflicts with", "dependency problems"],
        "pacman": ["conflicting packages", "conflict"],
        "dnf":    ["conflicts", "protected multilib versions"],
        "zypper": ["conflicts with", "conflict"],
        "brew":   ["conflicts with"],
    }
    signals = conflict_signals.get(pm, [])
    lower = stderr.lower()
    return any(s in lower for s in signals)


# ── Rollback log ─────────────────────────────────────────────────────────────

def _append_rollback_log(pm: str, package: str, tool: str) -> None:
    remove_cmds = {
        "apt":    f"sudo apt-get remove -y {package}",
        "pacman": f"sudo pacman -R --noconfirm {package}",
        "dnf":    f"sudo dnf remove -y {package}",
        "zypper": f"sudo zypper remove -y {package}",
        "brew":   f"brew uninstall {package}",
    }
    cmd = remove_cmds.get(pm, f"# unknown pm — package: {package}")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"{ts}  {tool:<25}  {cmd}\n"
    try:
        _ROLLBACK_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(_ROLLBACK_LOG, "a") as f:
            f.write(entry)
    except OSError:
        pass


# ── Conflict resolution prompt ───────────────────────────────────────────────

def _prompt_conflict(tool: str, package: str, stderr: str) -> ConflictChoice:
    console.print()
    console.print(f"[bold yellow]Conflict detected while installing [cyan]{tool}[/cyan][/bold yellow]")
    console.print(f"[dim]{stderr.strip()[-600:]}[/dim]")
    console.print()
    console.print("How would you like to resolve this?")
    console.print("  [bold](K)[/bold]eep existing packages, skip this tool")
    console.print("  [bold](R)[/bold]eplace / reinstall (may overwrite existing files)")
    console.print("  [bold](S)[/bold]kip this tool entirely")
    console.print()

    while True:
        raw = Prompt.ask("Choice", choices=["k","r","s","K","R","S"], default="s", show_choices=False).lower()
        if raw == "k": return ConflictChoice.KEEP
        if raw == "r": return ConflictChoice.REPLACE
        if raw == "s": return ConflictChoice.SKIP


# ── Core install routine ─────────────────────────────────────────────────────

def install_tool(tool: ToolEntry, info: SystemInfo, dry_run: bool = False, verbose: bool = False) -> InstallResult:
    pm = info.package_manager
    package = tool.packages.get(pm)

    if package is None:
        return InstallResult(tool=tool.name, package="", status=InstallStatus.UNAVAILABLE,
                             reason=f"No package defined for {pm}")

    if not dry_run and _is_installed(pm, package):
        return InstallResult(tool=tool.name, package=package, status=InstallStatus.ALREADY_INSTALLED,
                             reason="already installed")

    if dry_run:
        cmd = _build_install_cmd(pm, package)
        console.print(f"  [dim]dry-run:[/dim] {' '.join(cmd)}")
        return InstallResult(tool=tool.name, package=package, status=InstallStatus.SUCCESS, reason="dry-run")

    result = _run_install(tool.name, pm, package, replace=False, verbose=verbose)
    if result.status == InstallStatus.SUCCESS:
        _append_rollback_log(pm, package, tool.name)
        return result

    if result.status == InstallStatus.FAILED and _is_conflict_error(result.reason, pm):
        choice = _prompt_conflict(tool.name, package, result.reason)
        if choice in (ConflictChoice.SKIP, ConflictChoice.KEEP):
            return InstallResult(tool=tool.name, package=package, status=InstallStatus.SKIPPED,
                                 reason=f"User chose {choice.value} during conflict")
        if choice == ConflictChoice.REPLACE:
            result = _run_install(tool.name, pm, package, replace=True, verbose=verbose)
            if result.status == InstallStatus.SUCCESS:
                _append_rollback_log(pm, package, tool.name)
            return result

    return result


def _run_install(tool_name: str, pm: str, package: str, replace: bool, verbose: bool = False) -> InstallResult:
    try:
        cmd = _build_install_cmd(pm, package, replace=replace)
    except ValueError as e:
        return InstallResult(tool=tool_name, package=package, status=InstallStatus.FAILED, reason=str(e))

    env = {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}

    try:
        if verbose:
            proc = subprocess.run(cmd, timeout=300, env=env, text=True)
            stdout, stderr = "", ""
        else:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
            stdout, stderr = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return InstallResult(tool=tool_name, package=package, status=InstallStatus.FAILED,
                             reason="Install timed out after 5 minutes")
    except FileNotFoundError:
        return InstallResult(tool=tool_name, package=package, status=InstallStatus.FAILED,
                             reason=f"Package manager '{pm}' not found on PATH")

    if proc.returncode == 0:
        return InstallResult(tool=tool_name, package=package, status=InstallStatus.SUCCESS)

    return InstallResult(tool=tool_name, package=package, status=InstallStatus.FAILED,
                         reason=(stderr or stdout).strip())


# ── Batch install loop ───────────────────────────────────────────────────────

def run_install_loop(
    tools: list[ToolEntry],
    info: SystemInfo,
    dry_run: bool = False,
    verbose: bool = False,
) -> list[InstallResult]:
    results: list[InstallResult] = []
    total = len(tools)

    status_icons = {
        InstallStatus.SUCCESS:          "[green]✓ installed[/green]",
        InstallStatus.ALREADY_INSTALLED:"[dim]↩ already installed[/dim]",
        InstallStatus.SKIPPED:          "[yellow]⚡ skipped[/yellow]",
        InstallStatus.UNAVAILABLE:      "[dim]– not available[/dim]",
        InstallStatus.FAILED:           "[red]✗ failed[/red]",
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("[cyan]Starting...", total=total)

        for idx, tool in enumerate(tools, 1):
            progress.update(task, description=f"[cyan][{idx}/{total}] {tool.name}")
            console.print(f"\n[bold][{idx}/{total}][/bold] [cyan]{tool.name}[/cyan] — {tool.description}")

            result = install_tool(tool, info, dry_run=dry_run, verbose=verbose)
            results.append(result)

            icon = status_icons[result.status]
            if result.status == InstallStatus.SUCCESS:
                console.print(f"  {icon} ({result.package})")
            elif result.status == InstallStatus.FAILED:
                short = result.reason[:120] + "..." if len(result.reason) > 120 else result.reason
                console.print(f"  {icon} — {short}")
            else:
                console.print(f"  {icon}" + (f" — {result.reason}" if result.status == InstallStatus.SKIPPED else ""))

            progress.advance(task)

    installed = sum(1 for r in results if r.status == InstallStatus.SUCCESS)
    if installed > 0:
        console.print(f"[dim]Rollback log: {_ROLLBACK_LOG}[/dim]")

    return results
