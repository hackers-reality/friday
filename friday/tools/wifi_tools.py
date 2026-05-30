"""
WiFi & Network security analysis tools.
Requires admin/root privileges for wireless operations.
"""
from __future__ import annotations

import re
import subprocess
from typing import Optional

from friday.logging_utils import configure_logging

logger = configure_logging(__name__)


def wifi_list_profiles() -> list[dict]:
    """List saved WiFi profiles on Windows."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "profiles"],
            capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace",
        )
        profiles = []
        for line in result.stdout.splitlines():
            m = re.match(r"^\s*All User Profile\s*:\s*(.+)$", line)
            if m:
                profiles.append({"ssid": m.group(1).strip()})
        return profiles
    except Exception as exc:
        logger.warning("WiFi list profiles failed: %s", exc)
        return []


def wifi_show_password(ssid: str) -> dict:
    """Show WiFi password for a saved profile (requires admin)."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "profile", f"name={ssid}", "key=clear"],
            capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace",
        )
        password = ""
        for line in result.stdout.splitlines():
            m = re.match(r"^\s*Key Content\s*:\s*(.+)$", line)
            if m:
                password = m.group(1).strip()
                break
        return {"ssid": ssid, "password": password if password else None,
                "error": None if password else "Password not found or admin required"}
    except Exception as exc:
        return {"ssid": ssid, "password": None, "error": str(exc)}


def wifi_scan() -> list[dict]:
    """Scan for nearby WiFi networks."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "networks", "mode=Bssid"],
            capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace",
        )
        networks = []
        current = {}
        for line in result.stdout.splitlines():
            m = re.match(r"^\s*SSID\s*:\s*(.+)$", line)
            if m:
                current = {"ssid": m.group(1).strip()}
                networks.append(current)
            m = re.match(r"^\s*Authentication\s*:\s*(.+)$", line)
            if m and current:
                current["auth"] = m.group(1).strip()
            m = re.match(r"^\s*Encryption\s*:\s*(.+)$", line)
            if m and current:
                current["encryption"] = m.group(1).strip()
            m = re.match(r"^\s*Signal\s*:\s*(\d+)%", line)
            if m and current:
                current["signal"] = int(m.group(1))
            m = re.match(r"^\s*Channel\s*:\s*(\d+)", line)
            if m and current:
                current["channel"] = int(m.group(1))
            m = re.match(r"^\s*BSSID\s*:\s*(.+)$", line)
            if m and current:
                if "bssids" not in current:
                    current["bssids"] = []
                current["bssids"].append(m.group(1).strip())
        return networks
    except Exception as exc:
        logger.warning("WiFi scan failed: %s", exc)
        return []


def wifi_connection_status() -> dict:
    """Get current WiFi connection status."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace",
        )
        status = {}
        for line in result.stdout.splitlines():
            m = re.match(r"^\s*SSID\s*:\s*(.+)$", line)
            if m:
                status["ssid"] = m.group(1).strip()
            m = re.match(r"^\s*State\s*:\s*(.+)$", line)
            if m:
                status["state"] = m.group(1).strip()
            m = re.match(r"^\s*Signal\s*:\s*(\d+)%", line)
            if m:
                status["signal"] = int(m.group(1))
            m = re.match(r"^\s*Radio type\s*:\s*(.+)$", line)
            if m:
                status["radio"] = m.group(1).strip()
            m = re.match(r"^\s*Authentication\s*:\s*(.+)$", line)
            if m:
                status["auth"] = m.group(1).strip()
            m = re.match(r"^\s*Profile\s*:\s*(.+)$", line)
            if m:
                status["profile"] = m.group(1).strip()
        return status or {"error": "No WiFi interface found"}
    except Exception as exc:
        return {"error": str(exc)}


def network_connections() -> list[dict]:
    """List active network connections."""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace",
        )
        connections = []
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[0] in ("TCP", "UDP"):
                local_addr = parts[1] if len(parts) > 1 else ""
                remote_addr = parts[2] if len(parts) > 2 else ""
                state = parts[3] if len(parts) > 3 else ""
                pid = parts[-1] if parts[-1].isdigit() else ""
                connections.append({
                    "protocol": parts[0],
                    "local": local_addr,
                    "remote": remote_addr,
                    "state": state,
                    "pid": pid,
                })
        return connections
    except Exception as exc:
        logger.warning("Network connections failed: %s", exc)
        return []


def arp_table() -> list[dict]:
    """Get ARP table (IP to MAC mappings on local network)."""
    try:
        result = subprocess.run(
            ["arp", "-a"],
            capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace",
        )
        entries = []
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 3 and "." in parts[0]:
                entries.append({
                    "ip": parts[0],
                    "mac": parts[1],
                    "type": parts[2] if len(parts) > 2 else "dynamic",
                })
        return entries
    except Exception as exc:
        logger.warning("ARP table failed: %s", exc)
        return []


def traceroute(target: str, max_hops: int = 30) -> list[dict]:
    """Trace route to a target host."""
    try:
        result = subprocess.run(
            ["tracert", "-h", str(max_hops), target],
            capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace",
        )
        hops = []
        for line in result.stdout.splitlines():
            m = re.match(r"^\s*(\d+)\s+<?\s*(\d+)\s+ms\s+(\d+)\s+ms\s+(\d+)\s+ms\s+(.+)$", line)
            if m:
                hops.append({
                    "hop": int(m.group(1)),
                    "ip": m.group(5).strip(),
                    "rtt_ms": [int(m.group(2)), int(m.group(3)), int(m.group(4))],
                })
        return hops
    except Exception as exc:
        logger.warning("Traceroute failed: %s", exc)
        return []
