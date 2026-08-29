#!/usr/bin/env python3
"""
Generate data/tools.json from kali.org/tools/ + Kali apt Packages index.

Usage:
    python3 scripts/gen_matrix.py [--out data/tools.json]

Requires: requests, beautifulsoup4
    pip install requests beautifulsoup4
"""

import argparse
import gzip
import io
import json
import re
import sys
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Install deps: pip install requests beautifulsoup4", file=sys.stderr)
    sys.exit(1)

BASE = "https://www.kali.org"
TOOLS_URL = f"{BASE}/tools/"
# Kali apt Packages index — plain text with Name/Description for every package
KALI_PACKAGES_URL = "https://http.kali.org/kali/dists/kali-rolling/main/binary-amd64/Packages.gz"

# Tools available under different names on non-apt package managers.
PM_OVERRIDES: dict[str, dict] = {
    "nmap":                {"pacman": "nmap",          "dnf": "nmap",          "brew": "nmap"},
    "masscan":             {"pacman": "masscan",        "dnf": "masscan",       "brew": "masscan"},
    "wireshark":           {"pacman": "wireshark-qt",   "dnf": "wireshark",     "brew": "wireshark"},
    "tcpdump":             {"pacman": "tcpdump",        "dnf": "tcpdump",       "brew": "tcpdump"},
    "john":                {"pacman": "john",           "dnf": "john",          "brew": "john"},
    "hashcat":             {"pacman": "hashcat",        "dnf": "hashcat",       "brew": "hashcat"},
    "hydra":               {"pacman": "hydra",          "dnf": None,            "brew": "hydra"},
    "medusa":              {"pacman": "medusa",         "dnf": None,            "brew": None},
    "aircrack-ng":         {"pacman": "aircrack-ng",    "dnf": "aircrack-ng",   "brew": "aircrack-ng"},
    "nikto":               {"pacman": "nikto",          "dnf": None,            "brew": "nikto"},
    "sqlmap":              {"pacman": "sqlmap",         "dnf": None,            "brew": "sqlmap"},
    "gobuster":            {"pacman": "gobuster",       "dnf": None,            "brew": "gobuster"},
    "wfuzz":               {"pacman": "wfuzz",          "dnf": None,            "brew": None},
    "radare2":             {"pacman": "radare2",        "dnf": "radare2",       "brew": "radare2"},
    "ghidra":              {"pacman": "ghidra",         "dnf": None,            "brew": "ghidra"},
    "gdb":                 {"pacman": "gdb",            "dnf": "gdb",           "brew": "gdb"},
    "binwalk":             {"pacman": "binwalk",        "dnf": None,            "brew": "binwalk"},
    "autopsy":             {"pacman": None,             "dnf": None,            "brew": None},
    "volatility3":         {"pacman": "volatility3",    "dnf": None,            "brew": None},
    "scapy":               {"pacman": "python-scapy",   "dnf": "python3-scapy", "brew": "scapy"},
    "macchanger":          {"pacman": "macchanger",     "dnf": None,            "brew": None},
    "netdiscover":         {"pacman": "netdiscover",    "dnf": None,            "brew": None},
    "ettercap":            {"pacman": "ettercap",       "dnf": "ettercap",      "brew": None},
    "ettercap-graphical":  {"pacman": "ettercap",       "dnf": "ettercap",      "brew": None},
    "responder":           {"pacman": "responder",      "dnf": None,            "brew": None},
    "impacket-scripts":    {"pacman": "impacket",       "dnf": None,            "brew": None},
    "ncat":                {"pacman": "nmap",           "dnf": "nmap-ncat",     "brew": "nmap"},
    "socat":               {"pacman": "socat",          "dnf": "socat",         "brew": "socat"},
    "netcat-traditional":  {"pacman": "gnu-netcat",     "dnf": "nmap-ncat",     "brew": "netcat"},
    "tcpflow":             {"pacman": "tcpflow",        "dnf": "tcpflow",       "brew": "tcpflow"},
    "hping3":              {"pacman": "hping",          "dnf": None,            "brew": "hping"},
    "fping":               {"pacman": "fping",          "dnf": "fping",         "brew": "fping"},
    "yara":                {"pacman": "yara",           "dnf": "yara",          "brew": "yara"},
    "ssdeep":              {"pacman": "ssdeep",         "dnf": "ssdeep",        "brew": "ssdeep"},
    "lynis":               {"pacman": "lynis",          "dnf": "lynis",         "brew": "lynis"},
    "chkrootkit":          {"pacman": "chkrootkit",     "dnf": None,            "brew": None},
    "rkhunter":            {"pacman": "rkhunter",       "dnf": "rkhunter",      "brew": None},
    "proxychains4":        {"pacman": "proxychains-ng", "dnf": "proxychains-ng","brew": "proxychains-ng"},
    "whois":               {"pacman": "whois",          "dnf": "whois",         "brew": "whois"},
    "wpscan":              {"pacman": None,             "dnf": None,            "brew": "wpscan"},
    "mitmproxy":           {"pacman": "mitmproxy",      "dnf": None,            "brew": "mitmproxy"},
    "crunch":              {"pacman": "crunch",         "dnf": None,            "brew": None},
    "cewl":                {"pacman": "cewl",           "dnf": None,            "brew": None},
    "sslscan":             {"pacman": "sslscan",        "dnf": None,            "brew": "sslscan"},
    "sslyze":              {"pacman": "python-sslyze",  "dnf": None,            "brew": "sslyze"},
    "enum4linux":          {"pacman": "enum4linux",     "dnf": None,            "brew": None},
    "smbclient":           {"pacman": "smbclient",      "dnf": "samba-client",  "brew": "samba"},
    "bloodhound":          {"pacman": None,             "dnf": None,            "brew": None},
    "foremost":            {"pacman": "foremost",       "dnf": "foremost",      "brew": None},
    "testdisk":            {"pacman": "testdisk",       "dnf": "testdisk",      "brew": "testdisk"},
    "photorec":            {"pacman": "testdisk",       "dnf": "testdisk",      "brew": "testdisk"},
    "dnsrecon":            {"pacman": "dnsrecon",       "dnf": None,            "brew": None},
    "dnsenum":             {"pacman": "dnsenum",        "dnf": None,            "brew": None},
    "amass":               {"pacman": "amass",          "dnf": None,            "brew": "amass"},
    "recon-ng":            {"pacman": "recon-ng",       "dnf": None,            "brew": None},
    "kismet":              {"pacman": "kismet",         "dnf": None,            "brew": None},
    "reaver":              {"pacman": "reaver",         "dnf": None,            "brew": None},
    "bettercap":           {"pacman": "bettercap",      "dnf": None,            "brew": "bettercap"},
    "steghide":            {"pacman": "steghide",       "dnf": "steghide",      "brew": None},
    "bulk-extractor":      {"pacman": "bulk_extractor", "dnf": None,            "brew": "bulk_extractor"},
    "snmp-check":          {"pacman": None,             "dnf": None,            "brew": None},
    "ophcrack":            {"pacman": "ophcrack",       "dnf": None,            "brew": None},
    "ncrack":              {"pacman": None,             "dnf": None,            "brew": None},
    "patator":             {"pacman": "patator",        "dnf": None,            "brew": None},
    "nuclei":              {"pacman": "nuclei",         "dnf": None,            "brew": "nuclei"},
    "subfinder":           {"pacman": "subfinder",      "dnf": None,            "brew": "subfinder"},
    "ffuf":                {"pacman": "ffuf",           "dnf": None,            "brew": "ffuf"},
    "feroxbuster":         {"pacman": "feroxbuster",    "dnf": None,            "brew": "feroxbuster"},
    "chisel":              {"pacman": "chisel",         "dnf": None,            "brew": "chisel"},
    "sshuttle":            {"pacman": "sshuttle",       "dnf": None,            "brew": "sshuttle"},
    "rizin":               {"pacman": "rizin",          "dnf": None,            "brew": "rizin"},
    "apktool":             {"pacman": "apktool",        "dnf": None,            "brew": "apktool"},
    "wafw00f":             {"pacman": "wafw00f",        "dnf": None,            "brew": "wafw00f"},
    "sublist3r":           {"pacman": "sublist3r",      "dnf": None,            "brew": None},
    "sherlock":            {"pacman": "sherlock",       "dnf": None,            "brew": None},
    "spiderfoot":          {"pacman": "spiderfoot",     "dnf": None,            "brew": None},
    "whatweb":             {"pacman": "whatweb",        "dnf": None,            "brew": None},
    "dirsearch":           {"pacman": "dirsearch",      "dnf": None,            "brew": None},
    "dnschef":             {"pacman": "dnschef",        "dnf": None,            "brew": None},
    "smbmap":              {"pacman": "smbmap",         "dnf": None,            "brew": None},
    "metasploit-framework":{"pacman": "metasploit",     "dnf": None,            "brew": None},
    "exploitdb":           {"pacman": "exploitdb",      "dnf": None,            "brew": None},
    "xsser":               {"pacman": "xsser",          "dnf": None,            "brew": None},
    "commix":              {"pacman": "commix",         "dnf": None,            "brew": None},
    "cherrytree":          {"pacman": "cherrytree",     "dnf": "cherrytree",    "brew": None},
    "wapiti":              {"pacman": "wapiti",         "dnf": None,            "brew": None},
    "dirbuster":           {"pacman": None,             "dnf": None,            "brew": None},
    "dirb":                {"pacman": "dirb",           "dnf": None,            "brew": "dirb"},
    "enum4linux-ng":       {"pacman": "enum4linux-ng",  "dnf": None,            "brew": None},
    "nbtscan":             {"pacman": "nbtscan",        "dnf": "nbtscan",       "brew": None},
    "onesixtyone":         {"pacman": "onesixtyone",    "dnf": None,            "brew": None},
    "arping":              {"pacman": "arping",         "dnf": "iputils",       "brew": None},
    "arpwatch":            {"pacman": "arpwatch",       "dnf": "arpwatch",      "brew": None},
    "p0f":                 {"pacman": "p0f",            "dnf": None,            "brew": "p0f"},
    "fierce":              {"pacman": "fierce",         "dnf": None,            "brew": None},
    "dnsmap":              {"pacman": "dnsmap",         "dnf": None,            "brew": None},
    "dnswalk":             {"pacman": "dnswalk",        "dnf": None,            "brew": None},
    "maltego":             {"pacman": None,             "dnf": None,            "brew": None},
    "crackmapexec":        {"pacman": None,             "dnf": None,            "brew": None},
    "netexec":             {"pacman": None,             "dnf": None,            "brew": None},
    "evil-winrm":          {"pacman": None,             "dnf": None,            "brew": None},
    "mimikatz":            {"pacman": None,             "dnf": None,            "brew": None},
    "setoolkit":           {"pacman": None,             "dnf": None,            "brew": None},
    "airgeddon":           {"pacman": "airgeddon",      "dnf": None,            "brew": None},
    "wifite":              {"pacman": "wifite",         "dnf": None,            "brew": None},
    "cowpatty":            {"pacman": "cowpatty",       "dnf": None,            "brew": None},
    "pixiewps":            {"pacman": "pixiewps",       "dnf": None,            "brew": None},
    "wifiphisher":         {"pacman": None,             "dnf": None,            "brew": None},
    "fern-wifi-cracker":   {"pacman": None,             "dnf": None,            "brew": None},
    "hashid":              {"pacman": "python-hashid",  "dnf": None,            "brew": None},
    "hash-identifier":     {"pacman": None,             "dnf": None,            "brew": None},
    "stegosuite":          {"pacman": None,             "dnf": None,            "brew": None},
    "stegsnow":            {"pacman": "stegsnow",       "dnf": None,            "brew": None},
    "outguess":            {"pacman": None,             "dnf": None,            "brew": None},
    "binwalk3":            {"pacman": None,             "dnf": None,            "brew": None},
    "dc3dd":               {"pacman": "dc3dd",          "dnf": None,            "brew": None},
    "dcfldd":              {"pacman": "dcfldd",         "dnf": "dcfldd",        "brew": None},
    "guymager":            {"pacman": None,             "dnf": None,            "brew": None},
    "regripper":           {"pacman": None,             "dnf": None,            "brew": None},
    "pasco":               {"pacman": None,             "dnf": None,            "brew": None},
    "unhide":              {"pacman": "unhide",         "dnf": None,            "brew": None},
    "chntpw":              {"pacman": "chntpw",         "dnf": None,            "brew": None},
    "samdump2":            {"pacman": "samdump2",       "dnf": None,            "brew": None},
    "extundelete":         {"pacman": "extundelete",    "dnf": None,            "brew": None},
    "scalpel":             {"pacman": "scalpel",        "dnf": None,            "brew": None},
    "snmpcheck":           {"pacman": None,             "dnf": None,            "brew": None},
    "braa":                {"pacman": "braa",           "dnf": None,            "brew": None},
    "ike-scan":            {"pacman": "ike-scan",       "dnf": None,            "brew": "ike-scan"},
    "netsniff-ng":         {"pacman": "netsniff-ng",    "dnf": "netsniff-ng",   "brew": None},
    "driftnet":            {"pacman": "driftnet",       "dnf": None,            "brew": None},
    "dsniff":              {"pacman": "dsniff",         "dnf": "dsniff",        "brew": "dsniff"},
    "mdk3":                {"pacman": "mdk3",           "dnf": None,            "brew": None},
    "mactime":             {"pacman": None,             "dnf": None,            "brew": None},
    "pdfid":               {"pacman": "python-pdfid",   "dnf": None,            "brew": None},
    "pdf-parser":          {"pacman": None,             "dnf": None,            "brew": None},
    "weevely":             {"pacman": "weevely",        "dnf": None,            "brew": None},
    "sqlninja":            {"pacman": None,             "dnf": None,            "brew": None},
    "jsql":                {"pacman": None,             "dnf": None,            "brew": None},
    "skipfish":            {"pacman": "skipfish",       "dnf": None,            "brew": None},
    "joomscan":            {"pacman": "joomscan",       "dnf": None,            "brew": None},
    "davtest":             {"pacman": "davtest",        "dnf": None,            "brew": None},
    "httrack":             {"pacman": "httrack",        "dnf": "httrack",       "brew": "httrack"},
    "cutycapt":            {"pacman": None,             "dnf": None,            "brew": None},
    "eyewitness":          {"pacman": None,             "dnf": None,            "brew": None},
    "mitmf":               {"pacman": None,             "dnf": None,            "brew": None},
    "sslsplit":            {"pacman": "sslsplit",       "dnf": None,            "brew": "sslsplit"},
    "stunnel4":            {"pacman": "stunnel",        "dnf": "stunnel",       "brew": "stunnel"},
    "proxytunnel":         {"pacman": "proxytunnel",    "dnf": None,            "brew": None},
    "ptunnel":             {"pacman": "ptunnel",        "dnf": None,            "brew": None},
    "miredo":              {"pacman": "miredo",         "dnf": None,            "brew": None},
    "dns2tcpc":            {"pacman": "dns2tcp",        "dnf": None,            "brew": None},
    "iodine-client-start": {"pacman": "iodine",         "dnf": "iodine",        "brew": "iodine"},
    "slowhttptest":        {"pacman": "slowhttptest",   "dnf": None,            "brew": "slowhttptest"},
    "siege":               {"pacman": "siege",          "dnf": "siege",         "brew": "siege"},
    "goldeneye":           {"pacman": None,             "dnf": None,            "brew": None},
    "thc-ssl-dos":         {"pacman": None,             "dnf": None,            "brew": None},
    "hping3":              {"pacman": "hping",          "dnf": None,            "brew": "hping"},
    "yersinia":            {"pacman": "yersinia",       "dnf": None,            "brew": None},
    "macchanger":          {"pacman": "macchanger",     "dnf": None,            "brew": None},
    "veil":                {"pacman": None,             "dnf": None,            "brew": None},
    "shellter":            {"pacman": None,             "dnf": None,            "brew": None},
    "peass":               {"pacman": None,             "dnf": None,            "brew": None},
    "unix-privesc-check":  {"pacman": None,             "dnf": None,            "brew": None},
    "linpeas":             {"pacman": None,             "dnf": None,            "brew": None},
    "winpeas":             {"pacman": None,             "dnf": None,            "brew": None},
    "bloodyad":            {"pacman": None,             "dnf": None,            "brew": None},
    "krbrelayx":           {"pacman": None,             "dnf": None,            "brew": None},
    "kerberoast":          {"pacman": None,             "dnf": None,            "brew": None},
    "rubeus":              {"pacman": None,             "dnf": None,            "brew": None},
    "havoc":               {"pacman": None,             "dnf": None,            "brew": None},
    "villain":             {"pacman": None,             "dnf": None,            "brew": None},
    "hoaxshell":           {"pacman": None,             "dnf": None,            "brew": None},
    "adaptixclient":       {"pacman": None,             "dnf": None,            "brew": None},
    "powershell-empire":   {"pacman": None,             "dnf": None,            "brew": None},
    "ligolo-proxy":        {"pacman": None,             "dnf": None,            "brew": None},
    "ligolo-agent":        {"pacman": None,             "dnf": None,            "brew": None},
    "gitxray":             {"pacman": None,             "dnf": None,            "brew": None},
    "trufflehog":          {"pacman": None,             "dnf": None,            "brew": "trufflehog"},
    "photon":              {"pacman": None,             "dnf": None,            "brew": None},
    "gospider":            {"pacman": "gospider",       "dnf": None,            "brew": "gospider"},
    "finalrecon":          {"pacman": None,             "dnf": None,            "brew": None},
    "arjun":               {"pacman": "arjun",          "dnf": None,            "brew": None},
    "uro":                 {"pacman": None,             "dnf": None,            "brew": None},
    "dnstracer":           {"pacman": "dnstracer",      "dnf": "dnstracer",     "brew": None},
    "massdns":             {"pacman": "massdns",        "dnf": None,            "brew": "massdns"},
    "assetfinder":         {"pacman": "assetfinder",    "dnf": None,            "brew": "assetfinder"},
    "findomain":           {"pacman": "findomain",      "dnf": None,            "brew": "findomain"},
    "urlcrazy":            {"pacman": None,             "dnf": None,            "brew": None},
    "spiderfoot-cli":      {"pacman": None,             "dnf": None,            "brew": None},
    "instaloader":         {"pacman": "python-instaloader","dnf": None,         "brew": "instaloader"},
    "sherlock":            {"pacman": "sherlock",       "dnf": None,            "brew": None},
    "redeye-start":        {"pacman": None,             "dnf": None,            "brew": None},
    "dradis-start":        {"pacman": None,             "dnf": None,            "brew": None},
    "faraday-start":       {"pacman": None,             "dnf": None,            "brew": None},
}


def fetch_kali_apt_descriptions() -> dict[str, str]:
    """
    Download the Kali apt Packages index and return {package_name: description}.
    Uses the short Description field from the Debian package format.
    """
    print("Fetching Kali apt Packages index (this may take a moment)...")
    resp = requests.get(KALI_PACKAGES_URL, timeout=60, stream=True)
    resp.raise_for_status()

    raw = gzip.GzipFile(fileobj=io.BytesIO(resp.content)).read().decode("utf-8", errors="replace")

    descriptions: dict[str, str] = {}
    current_pkg = None
    for line in raw.splitlines():
        if line.startswith("Package: "):
            current_pkg = line[9:].strip()
        elif line.startswith("Description: ") and current_pkg:
            descriptions[current_pkg] = line[13:].strip()
            current_pkg = None  # only capture the first Description per stanza

    print(f"  Loaded descriptions for {len(descriptions)} packages.")
    return descriptions


def fetch_tool_names_and_categories() -> list[dict]:
    """
    Scrape kali.org/tools/ to get every tool name and its category.
    The page uses <a href="/tools/NAME/#..."> inside category sections.
    """
    print(f"Fetching {TOOLS_URL} ...")
    resp = requests.get(TOOLS_URL, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    tools: list[dict] = []
    seen: set[str] = set()
    current_category = "Uncategorized"

    # Walk all elements in document order; update category on heading, collect links
    for elem in soup.find_all(["h1", "h2", "h3", "h4", "a"]):
        if elem.name in ("h1", "h2", "h3", "h4"):
            text = elem.get_text(strip=True)
            if text and len(text) < 60:
                current_category = text
        elif elem.name == "a":
            href = elem.get("href", "")
            # Match /tools/TOOLNAME/#anything or /tools/TOOLNAME/
            m = re.match(r"^/tools/([^/#]+)(?:/|/#.+)?$", href)
            if not m:
                continue
            name = m.group(1)
            if name in seen or name.lower() in ("all", "tags", "top-10", ""):
                continue
            seen.add(name)
            tools.append({"name": name, "category": current_category, "description": ""})

    print(f"  Found {len(tools)} tools on kali.org/tools/")
    return tools


def build_tools_json(tools: list[dict], descriptions: dict[str, str]) -> list[dict]:
    entries = []
    for t in tools:
        name = t["name"]
        desc = descriptions.get(name, t.get("description", ""))
        overrides = PM_OVERRIDES.get(name, {})
        entries.append({
            "name": name,
            "description": desc,
            "category": t["category"],
            "packages": {
                "apt": name,
                "pacman": overrides.get("pacman", None),
                "dnf": overrides.get("dnf", None),
                "brew": overrides.get("brew", None),
            },
        })
    return entries


def main():
    parser = argparse.ArgumentParser(description="Generate Corvus tools.json from kali.org")
    parser.add_argument("--out", default="data/tools.json")
    parser.add_argument("--no-apt-descriptions", action="store_true",
                        help="Skip downloading the apt Packages index")
    args = parser.parse_args()

    tools = fetch_tool_names_and_categories()
    if not tools:
        print("No tools found — the page structure may have changed.", file=sys.stderr)
        sys.exit(1)

    descriptions = {}
    if not args.no_apt_descriptions:
        try:
            descriptions = fetch_kali_apt_descriptions()
        except Exception as e:
            print(f"Warning: could not fetch apt descriptions: {e}", file=sys.stderr)

    entries = build_tools_json(tools, descriptions)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(entries, indent=2))
    print(f"Wrote {len(entries)} tools to {out}")


if __name__ == "__main__":
    main()
