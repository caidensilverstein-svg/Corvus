"""
Tool compatibility matrix.

Each entry maps a canonical tool name to:
  - description: short human-readable purpose
  - packages: per-package-manager install targets (None = not available)
  - category: grouping for the report
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ToolEntry:
    name: str
    description: str
    category: str
    packages: dict[str, Optional[str]]  # pm -> package name (None = unavailable)


# fmt: off
TOOLS: list[ToolEntry] = [
    # ── Reconnaissance ──────────────────────────────────────────────────────
    ToolEntry(
        name="nmap",
        description="Network exploration and security auditing",
        category="Reconnaissance",
        packages={"apt": "nmap", "pacman": "nmap", "dnf": "nmap", "brew": "nmap"},
    ),
    ToolEntry(
        name="masscan",
        description="Fast TCP port scanner",
        category="Reconnaissance",
        packages={"apt": "masscan", "pacman": "masscan", "dnf": "masscan", "brew": "masscan"},
    ),
    ToolEntry(
        name="netdiscover",
        description="ARP reconnaissance tool",
        category="Reconnaissance",
        packages={"apt": "netdiscover", "pacman": "netdiscover", "dnf": None, "brew": None},
    ),
    ToolEntry(
        name="whois",
        description="WHOIS domain lookup",
        category="Reconnaissance",
        packages={"apt": "whois", "pacman": "whois", "dnf": "whois", "brew": "whois"},
    ),
    ToolEntry(
        name="dnsrecon",
        description="DNS enumeration tool",
        category="Reconnaissance",
        packages={"apt": "dnsrecon", "pacman": "dnsrecon", "dnf": None, "brew": None},
    ),
    ToolEntry(
        name="theHarvester",
        description="Email, domain, and host enumeration",
        category="Reconnaissance",
        packages={"apt": "theharvester", "pacman": "theharvester", "dnf": None, "brew": None},
    ),

    # ── Web Application ──────────────────────────────────────────────────────
    ToolEntry(
        name="nikto",
        description="Web server vulnerability scanner",
        category="Web Application",
        packages={"apt": "nikto", "pacman": "nikto", "dnf": None, "brew": "nikto"},
    ),
    ToolEntry(
        name="gobuster",
        description="Directory/file/DNS brute-forcer",
        category="Web Application",
        packages={"apt": "gobuster", "pacman": "gobuster", "dnf": None, "brew": "gobuster"},
    ),
    ToolEntry(
        name="sqlmap",
        description="Automatic SQL injection detection and exploitation",
        category="Web Application",
        packages={"apt": "sqlmap", "pacman": "sqlmap", "dnf": None, "brew": "sqlmap"},
    ),
    ToolEntry(
        name="wfuzz",
        description="Web fuzzer",
        category="Web Application",
        packages={"apt": "wfuzz", "pacman": "wfuzz", "dnf": None, "brew": None},
    ),
    ToolEntry(
        name="burpsuite",
        description="Web application security testing platform",
        category="Web Application",
        packages={"apt": "burpsuite", "pacman": None, "dnf": None, "brew": None},
    ),

    # ── Password Attacks ─────────────────────────────────────────────────────
    ToolEntry(
        name="john",
        description="John the Ripper password cracker",
        category="Password Attacks",
        packages={"apt": "john", "pacman": "john", "dnf": "john", "brew": "john"},
    ),
    ToolEntry(
        name="hashcat",
        description="Advanced GPU-based password cracker",
        category="Password Attacks",
        packages={"apt": "hashcat", "pacman": "hashcat", "dnf": "hashcat", "brew": "hashcat"},
    ),
    ToolEntry(
        name="hydra",
        description="Network login brute-forcer",
        category="Password Attacks",
        packages={"apt": "hydra", "pacman": "hydra", "dnf": None, "brew": "hydra"},
    ),
    ToolEntry(
        name="medusa",
        description="Parallel network login auditor",
        category="Password Attacks",
        packages={"apt": "medusa", "pacman": "medusa", "dnf": None, "brew": None},
    ),

    # ── Exploitation ─────────────────────────────────────────────────────────
    ToolEntry(
        name="metasploit-framework",
        description="Penetration testing framework",
        category="Exploitation",
        packages={"apt": "metasploit-framework", "pacman": "metasploit", "dnf": None, "brew": None},
    ),
    ToolEntry(
        name="exploitdb",
        description="Exploit Database (searchsploit)",
        category="Exploitation",
        packages={"apt": "exploitdb", "pacman": "exploitdb", "dnf": None, "brew": None},
    ),
    ToolEntry(
        name="beef-xss",
        description="Browser exploitation framework",
        category="Exploitation",
        packages={"apt": "beef-xss", "pacman": None, "dnf": None, "brew": None},
    ),

    # ── Wireless ─────────────────────────────────────────────────────────────
    ToolEntry(
        name="aircrack-ng",
        description="WiFi security auditing suite",
        category="Wireless",
        packages={"apt": "aircrack-ng", "pacman": "aircrack-ng", "dnf": "aircrack-ng", "brew": "aircrack-ng"},
    ),
    ToolEntry(
        name="kismet",
        description="Wireless network detector and sniffer",
        category="Wireless",
        packages={"apt": "kismet", "pacman": "kismet", "dnf": None, "brew": None},
    ),
    ToolEntry(
        name="reaver",
        description="WPS PIN brute-forcer",
        category="Wireless",
        packages={"apt": "reaver", "pacman": "reaver", "dnf": None, "brew": None},
    ),

    # ── Sniffing & Spoofing ──────────────────────────────────────────────────
    ToolEntry(
        name="wireshark",
        description="Network protocol analyzer",
        category="Sniffing & Spoofing",
        packages={"apt": "wireshark", "pacman": "wireshark-qt", "dnf": "wireshark", "brew": "wireshark"},
    ),
    ToolEntry(
        name="tcpdump",
        description="Command-line packet capture",
        category="Sniffing & Spoofing",
        packages={"apt": "tcpdump", "pacman": "tcpdump", "dnf": "tcpdump", "brew": "tcpdump"},
    ),
    ToolEntry(
        name="ettercap",
        description="ARP poisoning and MITM attacks",
        category="Sniffing & Spoofing",
        packages={"apt": "ettercap-graphical", "pacman": "ettercap", "dnf": "ettercap", "brew": None},
    ),

    # ── Forensics ────────────────────────────────────────────────────────────
    ToolEntry(
        name="volatility",
        description="Memory forensics framework",
        category="Forensics",
        packages={"apt": "volatility", "pacman": "volatility3", "dnf": None, "brew": None},
    ),
    ToolEntry(
        name="autopsy",
        description="Digital forensics platform",
        category="Forensics",
        packages={"apt": "autopsy", "pacman": None, "dnf": None, "brew": None},
    ),
    ToolEntry(
        name="binwalk",
        description="Firmware analysis and extraction",
        category="Forensics",
        packages={"apt": "binwalk", "pacman": "binwalk", "dnf": None, "brew": "binwalk"},
    ),

    # ── Reverse Engineering ──────────────────────────────────────────────────
    ToolEntry(
        name="gdb",
        description="GNU debugger",
        category="Reverse Engineering",
        packages={"apt": "gdb", "pacman": "gdb", "dnf": "gdb", "brew": "gdb"},
    ),
    ToolEntry(
        name="radare2",
        description="Reverse engineering framework",
        category="Reverse Engineering",
        packages={"apt": "radare2", "pacman": "radare2", "dnf": "radare2", "brew": "radare2"},
    ),
    ToolEntry(
        name="ghidra",
        description="NSA reverse engineering suite",
        category="Reverse Engineering",
        packages={"apt": "ghidra", "pacman": "ghidra", "dnf": None, "brew": "ghidra"},
    ),
]
# fmt: on


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
