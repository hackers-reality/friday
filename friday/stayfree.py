"""
StayFree Bridge - reads local StayFree data for screen time and app usage.
StayFree stores data in JSON files at %LOCALAPPDATA%/StayFree.
"""

import os
import json
import glob
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


def _get_stayfree_dir() -> Optional[str]:
    """Locate the StayFree data directory. Checks 20+ possible locations + Windows Registry + running processes."""
    appdata = os.environ.get("LOCALAPPDATA", "")
    appdata_roaming = os.environ.get("APPDATA", "")
    userprofile = os.environ.get("USERPROFILE", "")
    programdata = os.environ.get("PROGRAMDATA", "")
    systemdrive = os.environ.get("SystemDrive", "C:")
    candidates = []

    # Standard StayFree app data dirs
    if appdata:
        candidates += [
            os.path.join(appdata, "StayFree"),
            os.path.join(appdata, "StayFree", "data"),
            os.path.join(appdata, "StayFree", "storage"),
            os.path.join(appdata, "StayFree", "app"),
            os.path.join(appdata, "StayFree", "usage-data"),
            os.path.join(appdata, "StayFree", "session-data"),
            os.path.join(appdata, "StayFree", "tracking-data"),
            os.path.join(appdata, "Programs", "StayFree"),
        ]
    if appdata_roaming:
        candidates += [
            os.path.join(appdata_roaming, "StayFree"),
            os.path.join(appdata_roaming, "StayFree", "data"),
        ]
    if userprofile:
        candidates += [
            os.path.join(userprofile, "StayFree"),
            os.path.join(userprofile, "StayFree", "data"),
            os.path.join(userprofile, "Documents", "StayFree"),
            os.path.join(userprofile, "AppData", "Local", "StayFree"),
            os.path.join(userprofile, "AppData", "Roaming", "StayFree"),
        ]
    if programdata:
        candidates += [
            os.path.join(programdata, "StayFree"),
        ]

    # Chrome / Edge / Brave extension storage
    browsers = [
        ("Google", "Chrome"),
        ("Microsoft", "Edge"),
        ("BraveSoftware", "Brave-Browser"),
    ]
    ext_ids = [
        "ccebnhfcmbpgkdapgkmbpgcpeblebili",  # StayFree original
        "ghhjkichblmhhlkjdldnlpiiifekikcp",  # StayFree alternative
        "laefbpnoejggpddomdfbejeghnhagonp",  # StayFree v2
        "mhgknjpnpcoeggcdmmogmndjlildgepd",  # StayFree focus
    ]
    if appdata:
        for vendor, browser in browsers:
            for ext_id in ext_ids:
                candidates += [
                    os.path.join(appdata, vendor, browser, "User Data", "Default", "Local Extension Settings", ext_id),
                    os.path.join(appdata, vendor, browser, "User Data", "Default", "Storage", "ext", ext_id),
                    os.path.join(appdata, vendor, browser, "User Data", "Default", "IndexedDB", f"chrome-extension_{ext_id}"),
                ]

    # Microsoft Store apps (per-user AppData)
    if userprofile:
        candidates += [
            os.path.join(userprofile, "AppData", "Local", "Packages", "StayFree"),
            os.path.join(userprofile, "AppData", "Local", "Packages", "StayFreeApp"),
            os.path.join(userprofile, "AppData", "Local", "Packages", "StayFreeApp_*"),
        ]

    # Direct root paths
    candidates += [
        os.path.join(systemdrive, "\\", "StayFree"),
        os.path.join(systemdrive, "\\", "Program Files", "StayFree"),
        os.path.join(systemdrive, "\\", "Program Files (x86)", "StayFree"),
    ]

    for c in candidates:
        if os.path.isdir(c):
            return c

    # Fallback: try Windows Registry to find StayFree install path
    try:
        for hive, key in [
            ("HKEY_LOCAL_MACHINE", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            ("HKEY_LOCAL_MACHINE", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            ("HKEY_CURRENT_USER", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]:
            result = subprocess.run(
                ["reg", "query", f"{hive}\\{key}", "/s", "/f", "StayFree", "/e"],
                capture_output=True, text=True, timeout=10
            )
            if "StayFree" in result.stdout:
                for line in result.stdout.splitlines():
                    if "InstallLocation" in line or "DisplayIcon" in line:
                        parts = line.strip().split("  ", 2)
                        if len(parts) >= 3:
                            path = parts[-1].strip()
                            if os.path.isdir(os.path.dirname(path)):
                                return os.path.dirname(path)
    except Exception:
        pass

    # Fallback: try `where stayfree` to find the executable
    try:
        result = subprocess.run(
            ["where", "stayfree"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            exe_path = result.stdout.strip().splitlines()[0]
            data_dir = os.path.join(os.path.dirname(exe_path), "data")
            if os.path.isdir(data_dir):
                return data_dir
            parent = os.path.dirname(exe_path)
            if os.path.isdir(parent):
                return parent
    except Exception:
        pass

    # Fallback: check StayFree process command line
    try:
        result = subprocess.run(
            ["wmic", "process", "where", "name='StayFree.exe'", "get", "ExecutablePath"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.endswith(".exe") and os.path.isfile(line):
                data_dir = os.path.join(os.path.dirname(line), "data")
                if os.path.isdir(data_dir):
                    return data_dir
                return os.path.dirname(line)
    except Exception:
        pass

    # Fallback: recursive scan entire LOCALAPPDATA for any StayFree folder
    try:
        appdata = os.environ.get("LOCALAPPDATA", "")
        if appdata:
            for root, dirs, _ in os.walk(appdata):
                if "StayFree" in root:
                    return root
                for d in dirs:
                    if "StayFree" in d:
                        return os.path.join(root, d)
    except Exception:
        pass

    return None


def _find_json_files(dirpath: str, pattern: str = "*.json") -> list:
    """Find JSON files matching pattern."""
    return glob.glob(os.path.join(dirpath, "**", pattern), recursive=True)


def stayfree_status() -> str:
    """Check if StayFree data is accessible."""
    sf_dir = _get_stayfree_dir()
    if sf_dir:
        files = _find_json_files(sf_dir)
        if files:
            return f"[OK] StayFree data directory: {sf_dir} ({len(files)} data files)"
        return f"[OK] StayFree directory found at {sf_dir} (waiting for data files)"
    # Check if StayFree process is running
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq StayFree.exe", "/NH"],
            capture_output=True, text=True, timeout=5
        )
        if "StayFree.exe" in result.stdout:
            return "[OK] StayFree process is running (no data directory found)"
    except Exception:
        pass
    return "[FAIL] StayFree not found. Install from https://stayfreeapps.com"


def stayfree_today() -> str:
    """Get today's screen time and app usage from StayFree."""
    try:
        sf_dir = _get_stayfree_dir()
        if not sf_dir:
            return "[FAIL] StayFree not found. Install from https://stayfreeapps.com"

        # Look for today's usage data
        files = _find_json_files(sf_dir)
        today = datetime.now().strftime("%Y-%m-%d")
        today_data = []

        for fpath in files:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    raw = f.read()
                # Try parsing as JSON or NDJSON (newline-delimited JSON)
                if raw.startswith("[") or raw.startswith("{"):
                    data = json.loads(raw)
                else:
                    # NDJSON — try each line
                    for line in raw.strip().splitlines():
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(data, dict):
                            entries = data.get("entries", data.get("data", data.get("usage", data.get("records", []))))
                            if isinstance(entries, list):
                                for entry in entries:
                                    date = str(entry.get("date", entry.get("day", entry.get("timestamp", ""))))
                                    if today in date:
                                        today_data.append(entry)
                            date = str(data.get("date", data.get("day", data.get("timestamp", ""))))
                            if today in date:
                                today_data.append(data)
                    continue  # NDJSON already processed
                if isinstance(data, dict):
                    entries = data.get("entries", data.get("data", data.get("usage", data.get("records", []))))
                    if isinstance(entries, list):
                        for entry in entries:
                            date = str(entry.get("date", entry.get("day", entry.get("timestamp", ""))))
                            if today in date:
                                today_data.append(entry)
                    date = str(data.get("date", data.get("day", data.get("timestamp", ""))))
                    if today in date:
                        today_data.append(data)
                elif isinstance(data, list):
                    for entry in data:
                        date = str(entry.get("date", entry.get("day", entry.get("timestamp", ""))))
                        if today in date:
                            today_data.append(entry)
            except Exception:
                continue

        if not today_data:
            return f"[OK] No StayFree data for today ({today}). Activity may not be tracked yet."

        # Aggregate
        total_minutes = 0
        apps = []
        for entry in today_data:
            minutes = entry.get("usage", entry.get("duration", entry.get("time", 0)))
            if isinstance(minutes, (int, float)):
                total_minutes += minutes / 60 if minutes > 1440 else minutes  # assume ms -> min
            app_name = entry.get("app", entry.get("name", entry.get("title", "")))
            if app_name:
                apps.append(f"  {app_name}: {int(minutes)} min")

        lines = [f"StayFree — Today ({today})"]
        if total_minutes > 0:
            lines.append(f"  Total screen time: {int(total_minutes)} min ({int(total_minutes/60)}h {int(total_minutes%60)}m)")
        if apps:
            lines.append("  Top apps:")
            lines.extend(apps[:10])
        return "\n".join(lines)

    except Exception as e:
        return f"[FAIL] StayFree read error: {e}"


def stayfree_week() -> str:
    """Get this week's screen time summary."""
    try:
        sf_dir = _get_stayfree_dir()
        if not sf_dir:
            return "[FAIL] StayFree not found."

        files = _find_json_files(sf_dir)
        week_data = []
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        for fpath in files:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    raw = f.read()
                if raw.startswith("[") or raw.startswith("{"):
                    data = json.loads(raw)
                else:
                    for line in raw.strip().splitlines():
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(data, dict):
                            for entry in [data] + data.get("entries", data.get("data", data.get("usage", data.get("records", [])))):
                                date = entry.get("date", entry.get("day", "")) if isinstance(entry, dict) else ""
                                if date >= week_ago:
                                    week_data.append(entry)
                    continue
                if isinstance(data, list):
                    for entry in data:
                        if isinstance(entry, dict):
                            date = entry.get("date", entry.get("day", ""))
                            if date >= week_ago:
                                week_data.append(entry)
                elif isinstance(data, dict):
                    entries = data.get("entries", data.get("data", data.get("usage", data.get("records", [data]))))
                    if isinstance(entries, list):
                        for entry in entries:
                            date = entry.get("date", entry.get("day", ""))
                            if date >= week_ago:
                                week_data.append(entry)
            except Exception:
                continue

        daily = {}
        for entry in week_data:
            date = entry.get("date", entry.get("day", "unknown"))
            minutes = entry.get("usage", entry.get("duration", entry.get("time", 0)))
            if isinstance(minutes, (int, float)):
                minutes = minutes / 60 if minutes > 1440 else minutes
            daily[date] = daily.get(date, 0) + minutes

        if not daily:
            return "[OK] No StayFree data for the past week."

        lines = ["StayFree — This Week"]
        total = 0
        for date, mins in sorted(daily.items()):
            lines.append(f"  {date}: {int(mins)} min ({int(mins/60)}h {int(mins%60)}m)")
            total += mins
        lines.append(f"  Total: {int(total)} min ({int(total/60)}h {int(total%60)}m)")
        return "\n".join(lines)

    except Exception as e:
        return f"[FAIL] StayFree read error: {e}"
