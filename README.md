# Corvus

Cross-distro Kali Linux tool installer. Detects your OS and package manager, walks through a curated list of 30 core pentest tools, handles dependency conflicts interactively, and writes a post-install report.

## Supported package managers

| Platform | Package manager |
|----------|----------------|
| Kali / Ubuntu / Debian | `apt` |
| Arch / Manjaro | `pacman` |
| Fedora / RHEL / CentOS | `dnf` |
| macOS | `brew` (stretch) |

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/caidensilverstein-svg/Corvus/main/install.sh | bash
```

Or manually:

```bash
git clone https://github.com/caidensilverstein-svg/Corvus
cd Corvus
pip install -r requirements.txt
python3 main.py --help
```

## Usage

```
corvus                           # install all tools available for your distro
corvus --tools nmap,sqlmap       # install specific tools
corvus --category "Web Application"
corvus --list                    # list all tools and availability
corvus --dry-run                 # preview commands without executing
```

## Tool categories

- Reconnaissance (nmap, masscan, dnsrecon, theHarvester…)
- Web Application (nikto, gobuster, sqlmap, burpsuite…)
- Password Attacks (john, hashcat, hydra, medusa…)
- Exploitation (metasploit, exploitdb, beef-xss…)
- Wireless (aircrack-ng, kismet, reaver…)
- Sniffing & Spoofing (wireshark, tcpdump, ettercap…)
- Forensics (volatility, autopsy, binwalk…)
- Reverse Engineering (gdb, radare2, ghidra…)

## Conflict resolution

When a dependency conflict is detected during install, Corvus pauses and presents:

```
Conflict detected while installing <tool>
<package manager error output>

How would you like to resolve this?
  (K)eep existing packages, skip this tool
  (R)eplace / reinstall
  (S)kip this tool entirely

Choice [s]:
```

Corvus never auto-resolves conflicts destructively.

## Report

After each run a plain-text report is written to `~/.corvus/last_report.txt` and printed to the terminal.

## Requirements

- Python 3.8+
- `rich` (installed automatically)
