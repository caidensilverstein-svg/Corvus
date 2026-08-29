"""
CLI entry point — argument parsing and top-level orchestration.
"""

import sys
import argparse
from typing import Optional

from rich.console import Console
from rich.panel import Panel

from . import __version__
from .detect import detect, elevate_hint
from .matrix import get_all_tools, get_tools_for_pm, get_by_category, get_tool
from .installer import run_install_loop
from .report import generate

console = Console()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="corvus",
        description="Cross-distro Kali Linux tool installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  corvus                        # interactive: install all tools
  corvus --tools nmap,sqlmap    # install specific tools only
  corvus --list                 # list all tools in the matrix
  corvus --dry-run              # show what would be installed
  corvus --category "Web Application"
        """,
    )
    parser.add_argument(
        "--version", action="version", version=f"Corvus {__version__}"
    )
    parser.add_argument(
        "--tools",
        metavar="TOOL[,TOOL...]",
        help="Comma-separated list of specific tools to install",
    )
    parser.add_argument(
        "--category",
        metavar="CATEGORY",
        help="Install only tools in a specific category",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available tools and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print install commands without executing them",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip writing the report file",
    )
    return parser


def cmd_list(pm: str) -> None:
    """Print all tools grouped by category, flagging availability for current PM."""
    by_cat = get_by_category()
    for category, tools in by_cat.items():
        console.print(f"\n[bold underline]{category}[/bold underline]")
        for t in tools:
            pkg = t.packages.get(pm)
            if pkg:
                availability = f"[green]{pkg}[/green]"
            else:
                availability = "[dim]not available[/dim]"
            console.print(f"  {t.name:<25} {t.description:<55} {availability}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Detect system
    info = detect()

    console.print(
        Panel(
            f"[bold cyan]Corvus[/bold cyan] v{__version__}  —  "
            f"[dim]{info.distro} {info.distro_version} / {info.package_manager}[/dim]",
            expand=False,
        )
    )

    if info.package_manager == "unknown":
        console.print(
            "[bold red]Error:[/bold red] Could not detect a supported package manager "
            "(apt, pacman, dnf, brew). Aborting."
        )
        return 1

    hint = elevate_hint(info)
    if hint:
        console.print(f"[dim]Note: {hint}[/dim]")

    if args.list:
        cmd_list(info.package_manager)
        return 0

    # Resolve which tools to install
    if args.tools:
        names = [n.strip() for n in args.tools.split(",")]
        tools = []
        for name in names:
            t = get_tool(name)
            if t is None:
                console.print(f"[yellow]Warning:[/yellow] '{name}' not found in matrix, skipping")
            else:
                tools.append(t)
        if not tools:
            console.print("[red]No valid tools specified.[/red]")
            return 1
    elif args.category:
        by_cat = get_by_category()
        tools = by_cat.get(args.category)
        if not tools:
            available = ", ".join(sorted(by_cat.keys()))
            console.print(
                f"[red]Category '{args.category}' not found.[/red]\n"
                f"Available: {available}"
            )
            return 1
    else:
        tools = get_tools_for_pm(info.package_manager)

    if args.dry_run:
        console.print("[bold yellow]Dry run — no packages will be installed.[/bold yellow]")

    console.print(f"\n[bold]{len(tools)} tool(s) selected.[/bold]")

    results = run_install_loop(tools, info, dry_run=args.dry_run)

    if not args.no_report:
        generate(results, info)

    failed = sum(1 for r in results if r.status.name == "FAILED")
    return 1 if failed > 0 else 0
