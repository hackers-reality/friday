"""Friday Crash Watcher — monitors Windows Application Event Log for crashes,
captures fault details, and suggests fixes. No GPU needed, purely event log polling."""

from __future__ import annotations
import os
import json
import subprocess
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from friday._paths import FRIDAY_MEMORY

_CRASH_FILE = os.path.join(FRIDAY_MEMORY, "crash_log.json")
_watch_thread: Optional[threading.Thread] = None
_watch_stop = threading.Event()


def _load_crashes() -> list:
    if os.path.exists(_CRASH_FILE):
        try:
            with open(_CRASH_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_crashes(crashes: list):
    os.makedirs(os.path.dirname(_CRASH_FILE), exist_ok=True)
    try:
        with open(_CRASH_FILE, "w") as f:
            json.dump(crashes[-200:], f, indent=2)
    except Exception:
        pass


def _query_event_log(minutes_back: int = 5) -> list:
    """Query Windows Application event log for Error/Warning events from the last N minutes."""
    since = (datetime.now() - timedelta(minutes=minutes_back)).strftime("%Y-%m-%dT%H:%M:%S")
    query = f"""
    Get-WinEvent -FilterHashtable @{{LogName='Application'; Level=2; StartTime='{since}'}} -MaxEvents 20 |
    Select-Object TimeCreated, Id, LevelDisplayName, ProviderName, Message |
    ConvertTo-Json -Compress
    """
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", query],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return []
        data = json.loads(r.stdout.strip())
        if isinstance(data, dict):
            data = [data]
        return data
    except Exception:
        return []


def _is_crash_event(event: dict) -> bool:
    """Check if an event looks like an application crash (not just info/warning)."""
    level = event.get("LevelDisplayName", "")
    if level.lower() != "error":
        return False
    msg = (event.get("Message", "") or "").lower()
    crash_keywords = ["fault", "crash", "exception", "stopped working", "unhandled",
                      "0xc000", "access violation", "stack overflow", "segfault",
                      "application error", "hang"]
    eid = event.get("Id", 0)
    crash_ids = {1000, 1001, 1002, 1003, 1026, 1005}  # Windows Error Reporting IDs
    if eid in crash_ids:
        return True
    return any(kw in msg for kw in crash_keywords)


def _check_crashes() -> list:
    """Poll for recent crashes and return new ones."""
    events = _query_event_log(minutes_back=2)
    crashes = _load_crashes()
    known_ids = {c.get("event_id", "") for c in crashes}

    new_crashes = []
    for ev in events:
        eid = f"{ev.get('TimeCreated', '')}_{ev.get('Id', '')}_{ev.get('ProviderName', '')}"
        if eid in known_ids:
            continue
        if not _is_crash_event(ev):
            continue
        crash = {
            "event_id": eid,
            "timestamp": ev.get("TimeCreated", datetime.now().isoformat()),
            "process": ev.get("ProviderName", "Unknown"),
            "code": ev.get("Id", 0),
            "message": (ev.get("Message", "") or "")[:500],
            "detected_at": datetime.now().isoformat(),
            "analyzed": False,
        }
        crashes.append(crash)
        new_crashes.append(crash)
    _save_crashes(crashes)
    return new_crashes


def recent(limit: int = 10) -> str:
    crashes = _load_crashes()
    if not crashes:
        return "No crashes recorded."
    lines = ["### RECENT CRASHES"]
    for c in crashes[-limit:]:
        ts = c.get("timestamp", "?")[:19]
        proc = c.get("process", "?")
        code = c.get("code", "?")
        analyzed = "[ANALYZED]" if c.get("analyzed") else ""
        lines.append(f"  [{ts}] {proc} (0x{code:x}) {analyzed}")
        msg = c.get("message", "")[:120]
        if msg:
            lines.append(f"       {msg}")
    return "\n".join(lines)


def analyze_crash(index: int = -1) -> str:
    """Deep analyze a crash: extract fault info and search for solutions."""
    crashes = _load_crashes()
    if not crashes:
        return "No crashes to analyze."
    crash = crashes[index] if index < 0 else crashes[min(index, len(crashes) - 1)]
    msg = crash.get("message", "")
    proc = crash.get("process", "Unknown")
    code = crash.get("code", 0)

    # Extract fault details
    fault = "Unknown"
    for line in msg.split("\n"):
        line_lower = line.lower()
        for kw in ["faulting module", "fault offset", "exception code", "faulting application path"]:
            if kw in line_lower:
                fault = line.strip()[:200]
                break

    crash["analyzed"] = True
    _save_crashes(crashes)

    return (
        f"### CRASH ANALYSIS\n"
        f"Process: {proc}\n"
        f"Code: 0x{code:X}\n"
        f"Time: {crash.get('timestamp', '?')[:19]}\n"
        f"Fault: {fault}\n\n"
        f"To find a fix: web_search('{proc} error 0x{code:X} fix')"
    )


def start_watcher():
    global _watch_thread, _watch_stop
    if _watch_thread and _watch_thread.is_alive():
        return
    _watch_stop.clear()

    def _loop():
        while not _watch_stop.is_set():
            try:
                new = _check_crashes()
                if new:
                    for c in new:
                        proc = c.get("process", "?")
                        print(f"[CRASH] {proc} crashed at {c.get('timestamp', '?')[:19]}")
            except Exception:
                pass
            _watch_stop.wait(30)

    _watch_thread = threading.Thread(target=_loop, daemon=True)
    _watch_thread.start()


def stop_watcher():
    _watch_stop.set()


def crash_tool(action: str = "status", **kwargs) -> str:
    """Crash watcher: monitors Windows app crashes in real-time. Actions: status (show state), recent (list crashes), analyze (deep dive into last crash, index=N for specific), watch (start watching), stop (stop)."""
    try:
        if action == "status":
            crashes = _load_crashes()
            running = _watch_thread is not None and _watch_thread.is_alive()
            total = len(crashes)
            unanalyzed = sum(1 for c in crashes if not c.get("analyzed"))
            return (
                f"Crash Watcher: {'ACTIVE' if running else 'IDLE'}\n"
                f"Total crashes logged: {total}\n"
                f"Unanalyzed: {unanalyzed}"
            )
        elif action == "recent":
            return recent(limit=kwargs.get("limit", 10))
        elif action == "analyze":
            idx = kwargs.get("index", -1)
            return analyze_crash(index=idx)
        elif action == "watch":
            start_watcher()
            return "[OK] Crash watcher started (30s polling)."
        elif action == "stop":
            stop_watcher()
            return "[OK] Crash watcher stopped."
        else:
            return f"[FAIL] Unknown action: {action}"
    except Exception as e:
        return f"[FAIL] Crash watcher error: {e}"
