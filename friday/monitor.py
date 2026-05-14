"""Friday Proactive Desktop Monitor — autonomous system surveillance.
Detects CPU spikes, crashes, memory pressure, and responds automatically."""

from __future__ import annotations
import os
import json
import time
import threading
from datetime import datetime
from collections import defaultdict
from typing import Optional

from friday._paths import FRIDAY_MEMORY

_MONITOR_STATE_FILE = os.path.join(FRIDAY_MEMORY, "monitor_state.json")
_monitor_thread: Optional[threading.Thread] = None
_monitor_stop = threading.Event()

_DEFAULT_CONFIG = {
    "cpu_threshold": 90,
    "memory_threshold": 90,
    "check_interval": 30,
    "crash_monitor": True,
    "auto_response": True,
    "enabled": True,
}


def _load_state() -> dict:
    if os.path.exists(_MONITOR_STATE_FILE):
        try:
            with open(_MONITOR_STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"config": dict(_DEFAULT_CONFIG), "alerts": [], "incidents": 0, "last_check": None}


def _save_state(state: dict):
    os.makedirs(os.path.dirname(_MONITOR_STATE_FILE), exist_ok=True)
    try:
        with open(_MONITOR_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


def _get_cpu() -> float:
    try:
        from friday.system_monitor import get_cpu_usage
        return get_cpu_usage()
    except Exception:
        return -1


def _get_memory() -> dict:
    try:
        from friday.system_monitor import get_memory_usage
        return get_memory_usage()
    except Exception:
        return {"percent": 0}


def _get_processes() -> list:
    try:
        from friday.system_monitor import get_process_list
        return get_process_list(sort_by="cpu", limit=30)
    except Exception:
        return []


def _send_alert(title: str, message: str, severity: str = "warning"):
    """Fire a desktop notification about a detected issue."""
    try:
        from friday.notify import send_notification
        send_notification(title=title, message=message, urgency=severity)
    except Exception:
        pass


def _detect_crashes(state: dict) -> list:
    """Check for recently crashed processes by comparing process lists."""
    crashes = []
    known = state.get("known_processes", {})
    if not known:
        return crashes

    current = {}
    for p in _get_processes():
        name = p.get("name", "")
        pid = p.get("pid", 0)
        if name and pid:
            current[name] = current.get(name, 0) + 1

    for name, count in known.items():
        # Process was running but is now gone
        if name not in current and not name.lower().endswith(".exe"):
            continue
        if name not in current:
            # Check if it might have crashed vs. normal exit
            crashes.append(name)

    return crashes


def _check_system(state: dict) -> list:
    """Run a single system check, return list of alert messages."""
    alerts = []
    config = state.get("config", _DEFAULT_CONFIG)

    # CPU check
    cpu = _get_cpu()
    threshold = config.get("cpu_threshold", 90)
    if cpu >= 0 and cpu >= threshold:
        alerts.append({"type": "cpu_spike", "value": cpu, "threshold": threshold,
                        "message": f"CPU spike: {cpu:.0f}% (threshold: {threshold}%)",
                        "severity": "critical" if cpu >= 95 else "warning",
                        "time": datetime.now().isoformat()})

    # Memory check
    mem = _get_memory()
    mem_pct = mem.get("percent", 0)
    mem_threshold = config.get("memory_threshold", 90)
    if mem_pct >= mem_threshold:
        alerts.append({"type": "memory_pressure", "value": mem_pct, "threshold": mem_threshold,
                        "message": f"Memory pressure: {mem_pct}% (threshold: {mem_threshold}%)",
                        "severity": "critical" if mem_pct >= 95 else "warning",
                        "time": datetime.now().isoformat()})

    # Crash detection
    if config.get("crash_monitor", True):
        crashes = _detect_crashes(state)
        for c in crashes:
            alerts.append({"type": "crash", "process": c,
                            "message": f"Application crash detected: {c}",
                            "severity": "critical",
                            "time": datetime.now().isoformat()})

    return alerts


def _handle_alerts(alerts: list):
    """Take action on detected alerts."""
    for alert in alerts:
        _send_alert(
            f"⚠️ FRIDAY Alert: {alert['type']}",
            alert['message'],
            alert.get('severity', 'warning')
        )
        # Auto-response: kill top resource hogs on critical CPU/memory
        if alert.get('type') in ('cpu_spike', 'memory_pressure') and alert.get('severity') == 'critical':
            try:
                from friday.system_monitor import get_top_resource_hogs, kill_process_by_name
                hogs = get_top_resource_hogs()
                if "chrome" in hogs.lower()[:100].split():
                    kill_process_by_name("chrome.exe")
            except Exception:
                pass


def _monitor_loop():
    """Main monitoring loop — runs in background thread."""
    while not _monitor_stop.is_set():
        try:
            state = _load_state()
            config = state.get("config", _DEFAULT_CONFIG)
            if not config.get("enabled", True):
                _monitor_stop.wait(config.get("check_interval", 30))
                continue

            # Record current processes for crash detection
            state["known_processes"] = {}
            for p in _get_processes():
                name = p.get("name", "")
                if name:
                    state["known_processes"][name] = state["known_processes"].get(name, 0) + 1

            alerts = _check_system(state)
            if alerts:
                state.setdefault("alerts", []).extend(alerts)
                state["alerts"] = state["alerts"][-50:]
                state["incidents"] = state.get("incidents", 0) + len(alerts)
                if config.get("auto_response", True):
                    _handle_alerts(alerts)

            state["last_check"] = datetime.now().isoformat()
            _save_state(state)

        except Exception:
            pass
        _monitor_stop.wait(config.get("check_interval", 30))


def monitor_tool(action: str = "status", **kwargs) -> str:
    """Proactive desktop monitoring: CPU spikes, crash detection, auto-response.
    Actions: status, alerts, config (show/set thresholds), start, stop."""
    global _monitor_thread, _monitor_stop

    if action == "status":
        state = _load_state()
        config = state.get("config", _DEFAULT_CONFIG)
        running = _monitor_thread is not None and _monitor_thread.is_alive()
        return (
            f"Proactive Monitor: {'ACTIVE' if running else 'IDLE'}\n"
            f"  CPU threshold: {config.get('cpu_threshold', 90)}%\n"
            f"  Memory threshold: {config.get('memory_threshold', 90)}%\n"
            f"  Check interval: {config.get('check_interval', 30)}s\n"
            f"  Crash monitor: {'ON' if config.get('crash_monitor', True) else 'OFF'}\n"
            f"  Auto-response: {'ON' if config.get('auto_response', True) else 'OFF'}\n"
            f"  Incidents detected: {state.get('incidents', 0)}\n"
            f"  Last check: {state.get('last_check', 'never')}"
        )

    elif action == "alerts":
        state = _load_state()
        alerts = state.get("alerts", [])
        if not alerts:
            return "No alerts recorded."
        lines = ["### RECENT ALERTS"]
        for a in alerts[-10:]:
            ts = a.get("time", "?")[11:19] if len(a.get("time", "")) > 19 else a.get("time", "?")
            lines.append(f"  [{ts}] [{a.get('severity','info').upper()}] {a.get('message','')}")
        return "\n".join(lines)

    elif action == "config":
        config = _load_state().get("config", _DEFAULT_CONFIG)
        for key in ("cpu_threshold", "memory_threshold", "check_interval"):
            if key in kwargs:
                config[key] = int(kwargs[key])
        for key in ("crash_monitor", "auto_response", "enabled"):
            if key in kwargs:
                val = str(kwargs[key]).lower()
                config[key] = val in ("true", "1", "yes", "on")
        state = _load_state()
        state["config"] = config
        _save_state(state)
        return f"[OK] Monitor config updated: CPU>{config['cpu_threshold']}%, Mem>{config['memory_threshold']}%, interval={config['check_interval']}s"

    elif action == "start":
        if _monitor_thread and _monitor_thread.is_alive():
            return "[INFO] Monitor already running."
        _monitor_stop.clear()
        _monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
        _monitor_thread.start()
        return "[OK] Proactive monitor started."

    elif action == "stop":
        _monitor_stop.set()
        if _monitor_thread:
            _monitor_thread.join(timeout=3)
        _monitor_thread = None
        state = _load_state()
        state["known_processes"] = {}
        _save_state(state)
        return "[OK] Proactive monitor stopped."

    elif action == "check":
        """Run a single manual check cycle."""
        state = _load_state()
        alerts = _check_system(state)
        if alerts:
            state.setdefault("alerts", []).extend(alerts)
            state["alerts"] = state["alerts"][-50:]
            state["incidents"] = state.get("incidents", 0) + len(alerts)
        state["last_check"] = datetime.now().isoformat()
        _save_state(state)
        if not alerts:
            return "[OK] System check passed. CPU and memory are within normal ranges."
        lines = ["[WARN] Issues detected:"]
        for a in alerts:
            lines.append(f"  [{a.get('severity','info').upper()}] {a.get('message','')}")
        return "\n".join(lines)

    else:
        return f"[FAIL] Unknown action: {action}"


def start_monitor_on_boot():
    """Auto-start proactive monitor on boot."""
    try:
        state = _load_state()
        config = state.get("config", _DEFAULT_CONFIG)
        if config.get("enabled", True):
            monitor_tool("start")
    except Exception:
        pass
