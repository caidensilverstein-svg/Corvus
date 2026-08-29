# Corvus

Cross-distro Kali Linux tool installer. Detects your OS and package manager, walks through a curated list of 727 pentest tools, handles dependency conflicts interactively, and writes a post-install report.

## Supported package managers

| Platform | Package manager |
|----------|----------------|
| Kali / Ubuntu / Debian | `apt` |
| Arch / Manjaro | `pacman` |
| Fedora / RHEL / CentOS | `dnf` |
| OpenSUSE / Tumbleweed | `zypper` |
| macOS | `brew` |

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
corvus                           # install all tools for your distro
corvus -t nmap,sqlmap            # install specific tools
corvus -c "Web Application"      # install a category
corvus -l                        # list all tools and availability
corvus -d                        # dry run: log commands, don't execute
corvus -p                        # preview exact commands, then exit
corvus -v                        # verbose: stream package manager output live
corvus -V                        # print SHA-256 of the tool matrix
```

## Trust and verification

Corvus only talks to your system's native package manager — it does not add third-party repos, pipe scripts from the internet, or modify anything outside of what `apt`/`pacman`/`dnf`/`brew` controls.

**Before running, audit what will execute:**

```bash
corvus -p                        # table of every exact command that would run
corvus -p -t nmap,sqlmap         # same, for specific tools only
```

**Verify the tool matrix hasn't been tampered with:**

```bash
corvus -V
# Matrix:  /home/user/.local/corvus/data/tools.json
# SHA-256: 30037b0fa4bbd6566cea9c36158379c9f1744622dc71249b61e349761c014456
# Tools:   727
```

The published SHA-256 for each release is in the [Releases](https://github.com/caidensilverstein-svg/Corvus/releases) section. If the hash matches, you have an unmodified matrix.

**What the matrix is:** `data/tools.json` is a static list of tool names scraped from [kali.org/tools](https://www.kali.org/tools/), cross-referenced with each distro's package manager. It is a data file — it is not executed. You can read it directly: `cat ~/.local/corvus/data/tools.json`.

**Sudo usage:** Corvus runs installs with `sudo` where required. The exact command is always shown upfront via `-p`. When running as root (e.g. inside a container), `sudo` is omitted automatically.

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

After each run, a plain-text report is written to `~/.corvus/last_report.txt` and printed to the terminal. Use `-n` to skip.

## Requirements

- Python 3.8+
- `rich` (installed automatically by `install.sh`)
