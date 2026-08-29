"""
Post-install report generator.

Writes a structured summary to ~/.corvus/last_report.txt and prints
a formatted version to the terminal via rich.
"""

from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich import box

from .detect import SystemInfo
from .installer import InstallResult, InstallStatus

console = Console()

REPORT_DIR = Path.home() / ".corvus"
REPORT_PATH = REPORT_DIR / "last_report.txt"


def generate(results: list[InstallResult], info: SystemInfo) -> None:
    """Print a rich summary table and write the plain-text report file."""
    _print_terminal_report(results, info)
    _write_file_report(results, info)
    console.print(f"\n[dim]Report saved to {REPORT_PATH}[/dim]")


def _print_terminal_report(results: list[InstallResult], info: SystemInfo) -> None:
    console.print()
    console.rule("[bold]Corvus Install Report[/bold]")
    console.print(
        f"  Host: [cyan]{info.distro}[/cyan] {info.distro_version}  |  "
        f"PM: [cyan]{info.package_manager}[/cyan]  |  "
        f"Time: [cyan]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/cyan]"
    )
    console.print()

    table = Table(box=box.SIMPLE_HEAD, show_lines=False)
    table.add_column("Tool", style="bold", no_wrap=True)
    table.add_column("Package", style="dim")
    table.add_column("Status", no_wrap=True)
    table.add_column("Notes", overflow="fold")

    status_styles = {
        InstallStatus.SUCCESS: "[green]✓ success[/green]",
        InstallStatus.FAILED: "[red]✗ failed[/red]",
        InstallStatus.SKIPPED: "[yellow]⚡ skipped[/yellow]",
        InstallStatus.UNAVAILABLE: "[dim]– n/a[/dim]",
    }

    for r in results:
        table.add_row(
            r.tool,
            r.package or "—",
            status_styles[r.status],
            r.reason[:80] if r.reason else "",
        )

    console.print(table)

    # Summary counters
    counts = {s: 0 for s in InstallStatus}
    for r in results:
        counts[r.status] += 1

    console.print(
        f"  [green]{counts[InstallStatus.SUCCESS]} succeeded[/green]  "
        f"[red]{counts[InstallStatus.FAILED]} failed[/red]  "
        f"[yellow]{counts[InstallStatus.SKIPPED]} skipped[/yellow]  "
        f"[dim]{counts[InstallStatus.UNAVAILABLE]} unavailable[/dim]"
    )


def _write_file_report(results: list[InstallResult], info: SystemInfo) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "Corvus Install Report",
        "=" * 60,
        f"Date:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Distro:  {info.distro} {info.distro_version}",
        f"PM:      {info.package_manager}",
        f"Root:    {'yes' if info.is_root else 'no'}",
        "",
        f"{'Tool':<25} {'Package':<30} {'Status':<12} Notes",
        "-" * 100,
    ]

    for r in results:
        status_str = r.status.name.lower()
        note = r.reason[:50] if r.reason else ""
        lines.append(f"{r.tool:<25} {(r.package or '—'):<30} {status_str:<12} {note}")

    lines.append("")
    lines.append("Summary")
    lines.append("-" * 40)

    counts = {s: 0 for s in InstallStatus}
    for r in results:
        counts[r.status] += 1

    for status, count in counts.items():
        lines.append(f"  {status.name.lower():<12}: {count}")

    REPORT_PATH.write_text("\n".join(lines) + "\n")
