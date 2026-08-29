"""
Tool compatibility matrix — loaded from data/tools.json.

To regenerate tools.json from kali.org:
    python3 scripts/gen_matrix.py
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ToolEntry:
    name: str
    description: str
    category: str
    packages: dict[str, Optional[str]]  # pm -> package name (None = unavailable)


# Resolve data/tools.json relative to this file's package root
_DATA_FILE = Path(__file__).parent.parent / "data" / "tools.json"


def _load() -> list[ToolEntry]:
    if not _DATA_FILE.exists():
        raise FileNotFoundError(
            f"Tool data not found at {_DATA_FILE}. "
            "Run: python3 scripts/gen_matrix.py"
        )
    raw = json.loads(_DATA_FILE.read_text())
    return [
        ToolEntry(
            name=t["name"],
            description=t.get("description", ""),
            category=t.get("category", "Uncategorized"),
            packages=t.get("packages", {}),
        )
        for t in raw
    ]


# Loaded once at import time
TOOLS: list[ToolEntry] = _load()


def get_all_tools() -> list[ToolEntry]:
    return TOOLS


def get_tool(name: str) -> Optional[ToolEntry]:
    for t in TOOLS:
        if t.name.lower() == name.lower():
            return t
    return None


def get_tools_for_pm(pm: str) -> list[ToolEntry]:
    """Return tools available for a given package manager."""
    return [t for t in TOOLS if t.packages.get(pm) is not None]


def get_by_category() -> dict[str, list[ToolEntry]]:
    result: dict[str, list[ToolEntry]] = {}
    for tool in TOOLS:
        result.setdefault(tool.category, []).append(tool)
    return result
