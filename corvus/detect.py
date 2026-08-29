"""OS and package manager detection."""

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class SystemInfo:
    os_name: str          # e.g. "Linux", "Darwin"
    distro: str           # e.g. "ubuntu", "arch", "fedora", "kali", "macos"
    distro_version: str
    package_manager: str  # "apt" | "pacman" | "dnf" | "brew" | "unknown"
    is_root: bool


def detect() -> SystemInfo:
    """Detect the current OS, distribution, and package manager."""
    os_name = platform.system()

    if os_name == "Darwin":
        return SystemInfo(
            os_name="Darwin",
            distro="macos",
            distro_version=platform.mac_ver()[0],
            package_manager=_detect_brew(),
            is_root=(os.geteuid() == 0),
        )

    if os_name == "Linux":
        distro, version = _detect_linux_distro()
        pm = _detect_linux_pm(distro)
        return SystemInfo(
            os_name="Linux",
            distro=distro,
            distro_version=version,
            package_manager=pm,
            is_root=(os.geteuid() == 0),
        )

    return SystemInfo(
        os_name=os_name,
        distro="unknown",
        distro_version="",
        package_manager="unknown",
        is_root=False,
    )


def _detect_linux_distro() -> tuple[str, str]:
    """Read /etc/os-release to identify the distro."""
    os_release = {}
    try:
        with open("/etc/os-release") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    key, _, value = line.partition("=")
                    os_release[key] = value.strip('"')
    except FileNotFoundError:
        pass

    name = os_release.get("ID", "").lower()
    version = os_release.get("VERSION_ID", "")

    # Normalize common aliases
    alias_map = {
        "ubuntu": "ubuntu",
        "debian": "debian",
        "kali": "kali",
        "linuxmint": "ubuntu",  # Mint is apt-based like Ubuntu
        "pop": "ubuntu",
        "elementary": "ubuntu",
        "zorin": "ubuntu",
        "arch": "arch",
        "manjaro": "arch",
        "endeavouros": "arch",
        "garuda": "arch",
        "fedora": "fedora",
        "rhel": "fedora",
        "centos": "fedora",
        "rocky": "fedora",
        "almalinux": "fedora",
        "opensuse": "opensuse",
        "opensuse-leap": "opensuse",
        "opensuse-tumbleweed": "opensuse",
    }

    normalized = alias_map.get(name, name)
    return normalized, version


def _detect_linux_pm(distro: str) -> str:
    """Map distro to its primary package manager, verifying it exists."""
    pm_map = {
        "ubuntu": "apt",
        "debian": "apt",
        "kali": "apt",
        "arch": "pacman",
        "fedora": "dnf",
        "opensuse": "zypper",
    }
    candidate = pm_map.get(distro)

    if candidate and shutil.which(candidate):
        return candidate

    # Fallback: probe in order of preference
    for pm in ("apt", "apt-get", "pacman", "dnf", "yum", "zypper"):
        if shutil.which(pm):
            return "apt" if pm == "apt-get" else pm

    return "unknown"


def _detect_brew() -> str:
    if shutil.which("brew"):
        return "brew"
    return "unknown"


def elevate_hint(info: SystemInfo) -> str:
    """Return a human-readable hint about privilege requirements."""
    if info.is_root:
        return "running as root"
    pm_needs_sudo = {"apt", "pacman", "dnf", "zypper"}
    if info.package_manager in pm_needs_sudo:
        return "sudo will be required for installs"
    return ""
