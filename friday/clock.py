"""Friday Clock — alarms, timers, stopwatches, reminders, focus mode.
Integrates with the Windows Clock app GUI and manages features natively.
"""
from __future__ import annotations
import os
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Optional

from friday._paths import FRIDAY_MEMORY

_CLOCK_FILE = os.path.join(FRIDAY_MEMORY, "clock_state.json")
_alarm_threads = {}  # thread tracking for active alarms


def _load() -> dict:
    if os.path.exists(_CLOCK_FILE):
        try:
            with open(_CLOCK_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"alarms": [], "timers": [], "reminders": [], "focus_sessions": []}


def _save(state: dict) -> None:
    os.makedirs(os.path.dirname(_CLOCK_FILE), exist_ok=True)
    try:
        with open(_CLOCK_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"[Clock] Save error: {e}")


def _notify(title: str, message: str):
    """Send a desktop notification via plyer."""
    try:
        from plyer import notification
        notification.notify(title=f"Friday - {title}", message=message, timeout=10)
        return
    except Exception:
        pass
    try:
        from friday.notify import send_notification
        send_notification(f"[{title}] {message}", urgency="urgent")
    except Exception:
        pass


def _schedule_alarm(alarm_id: str, alarm_time: datetime, label: str):
    """Background thread that waits until alarm_time then fires."""
    def _waiter():
        now = datetime.now()
        delay = (alarm_time - now).total_seconds()
        if delay > 0:
            time.sleep(delay)
        _notify("ALARM", label or "Alarm!")
        # Remove from active list after firing
        state = _load()
        state["alarms"] = [a for a in state["alarms"] if a.get("id") != alarm_id]
        _save(state)
        _alarm_threads.pop(alarm_id, None)
        # Open Clock app
        _open_clock_app()

    t = threading.Thread(target=_waiter, daemon=True)
    t.start()
    _alarm_threads[alarm_id] = t


def _open_clock_app():
    """Open the Windows Clock app."""
    import subprocess
    try:
        subprocess.Popen("start ms-clock:", shell=True)
    except Exception:
        pass


def clock_alarm(action: str = "list", time_str: str = None, label: str = None, alarm_id: str = None) -> str:
    """Manage alarms. Actions: set, list, delete."""
    state = _load()
    if action == "set":
        if not time_str:
            return "[FAIL] Time required (HH:MM 24h format)."
        try:
            now = datetime.now()
            parts = time_str.split(":")
            alarm_time = now.replace(hour=int(parts[0]), minute=int(parts[1]), second=0, microsecond=0)
            if alarm_time <= now:
                alarm_time += timedelta(days=1)
            aid = f"alarm_{int(time.time())}"
            state["alarms"].append({
                "id": aid, "time": time_str, "label": label or "Alarm",
                "scheduled": alarm_time.isoformat(), "active": True
            })
            _save(state)
            _schedule_alarm(aid, alarm_time, label)
            return f"[OK] Alarm set for {time_str}{' - ' + label if label else ''}."
        except Exception as e:
            return f"[FAIL] Invalid time: {e}"
    elif action == "list":
        alarms = state.get("alarms", [])
        if not alarms:
            return "No alarms set."
        lines = ["### ALARMS"]
        for a in alarms:
            lines.append(f"  [{a['id']}] {a['time']} - {a.get('label', 'Alarm')}")
        return "\n".join(lines)
    elif action == "delete":
        if not alarm_id:
            return "[FAIL] alarm_id required."
        state["alarms"] = [a for a in state["alarms"] if a.get("id") != alarm_id]
        _save(state)
        _alarm_threads.pop(alarm_id, None)
        return f"[OK] Alarm {alarm_id} deleted."
    else:
        return f"[FAIL] Unknown action: {action}"


def clock_timer(action: str = "status", minutes: int = None, seconds: int = None, label: str = None, timer_id: str = None) -> str:
    """Manage countdown timers. Actions: start/set, status, stop."""
    state = _load()
    if action in ("start", "set"):
        total_minutes = (minutes or 0) + (seconds or 0) / 60.0
        if total_minutes < 1 / 60.0:  # less than 1 second
            return "[FAIL] Duration required — specify minutes, seconds, or both."
        tid = f"timer_{int(time.time())}"
        end_time = datetime.now() + timedelta(minutes=total_minutes)
        state["timers"].append({
            "id": tid, "minutes": total_minutes, "label": label or "Timer",
            "end": end_time.isoformat(), "remaining_minutes": total_minutes
        })
        _save(state)
        _schedule_timer_end(tid, end_time, label)
        total_secs = int(total_minutes * 60)
        if total_secs >= 3600:
            display = f"{total_secs // 3600}h {(total_secs % 3600) // 60}m"
        elif total_secs >= 60:
            display = f"{total_secs // 60}m {total_secs % 60}s"
        else:
            display = f"{total_secs}s"
        return f"[OK] Timer set for {display}{' - ' + label if label else ''}."
    elif action == "status":
        timers = state.get("timers", [])
        if not timers:
            return "No active timers."
        lines = ["### TIMERS"]
        for t in timers:
            remaining = max(0, (datetime.fromisoformat(t["end"]) - datetime.now()).total_seconds() / 60)
            lines.append(f"  [{t['id']}] {t.get('label', 'Timer')}: {remaining:.0f}m remaining")
        return "\n".join(lines)
    elif action == "stop" or action == "delete":
        if not timer_id:
            return "[FAIL] timer_id required."
        state["timers"] = [t for t in state["timers"] if t.get("id") != timer_id]
        _save(state)
        return f"[OK] Timer {timer_id} stopped."
    else:
        return f"[FAIL] Unknown action: {action}"


def _schedule_timer_end(timer_id: str, end_time: datetime, label: str):
    """Background thread to fire when timer ends."""
    def _waiter():
        now = datetime.now()
        delay = (end_time - now).total_seconds()
        if delay > 0:
            time.sleep(delay)
        _notify("TIMER UP", label or "Timer finished!")
        state = _load()
        state["timers"] = [t for t in state["timers"] if t.get("id") != timer_id]
        _save(state)

    t = threading.Thread(target=_waiter, daemon=True)
    t.start()


def clock_stopwatch(action: str = "status") -> str:
    """Simple stopwatch. Actions: start, stop, lap, status, reset."""
    state = _load()
    sw = state.get("stopwatch", {})
    if action == "start":
        if sw.get("running"):
            return "[INFO] Stopwatch already running."
        sw = {"running": True, "start": datetime.now().isoformat(), "laps": [], "elapsed_before": sw.get("elapsed_before", 0)}
        state["stopwatch"] = sw
        _save(state)
        return "[OK] Stopwatch started."
    elif action == "stop":
        if not sw.get("running"):
            return "[INFO] Stopwatch not running."
        elapsed = sw.get("elapsed_before", 0) + (datetime.now() - datetime.fromisoformat(sw["start"])).total_seconds()
        sw["running"] = False
        sw["elapsed_before"] = elapsed
        state["stopwatch"] = sw
        _save(state)
        return f"[OK] Stopwatch stopped at {elapsed:.1f}s."
    elif action == "lap":
        if not sw.get("running"):
            return "[INFO] Stopwatch not running."
        lap_time = (datetime.now() - datetime.fromisoformat(sw["start"])).total_seconds()
        total = sw.get("elapsed_before", 0) + lap_time
        laps = sw.get("laps", [])
        laps.append({"lap": len(laps) + 1, "time": f"{total:.1f}s", "split": f"{lap_time:.1f}s"})
        sw["laps"] = laps
        state["stopwatch"] = sw
        _save(state)
        return f"[OK] Lap {len(laps)}: {total:.1f}s (split: {lap_time:.1f}s)."
    elif action == "reset":
        state["stopwatch"] = {"running": False, "start": None, "laps": [], "elapsed_before": 0}
        _save(state)
        return "[OK] Stopwatch reset."
    else:
        # status
        if not sw or not sw.get("running"):
            return "Stopwatch not running."
        elapsed = sw.get("elapsed_before", 0) + (datetime.now() - datetime.fromisoformat(sw["start"])).total_seconds()
        return f"Stopwatch: {elapsed:.1f}s elapsed."


def clock_reminder(action: str = "list", text: str = None, time_str: str = None, reminder_id: str = None) -> str:
    """Manage reminders. Actions: set, list, delete."""
    state = _load()
    if action == "set":
        if not text:
            return "[FAIL] Reminder text required."
        if not time_str:
            return "[FAIL] Time required (HH:MM 24h format)."
        rid = f"reminder_{int(time.time())}"
        state["reminders"].append({
            "id": rid, "text": text, "time": time_str, "done": False
        })
        _save(state)
        # Schedule
        try:
            now = datetime.now()
            parts = time_str.split(":")
            remind_at = now.replace(hour=int(parts[0]), minute=int(parts[1]), second=0, microsecond=0)
            if remind_at <= now:
                remind_at += timedelta(days=1)
            _schedule_reminder(rid, remind_at, text)
        except Exception:
            pass
        return f"[OK] Reminder set: '{text}' at {time_str}."
    elif action == "list":
        reminders = state.get("reminders", [])
        active = [r for r in reminders if not r.get("done")]
        if not active:
            return "No pending reminders."
        lines = ["### REMINDERS"]
        for r in active:
            lines.append(f"  [{r['id']}] {r['time']} - {r['text']}")
        return "\n".join(lines)
    elif action == "delete" or action == "done":
        if not reminder_id:
            return "[FAIL] reminder_id required."
        state["reminders"] = [r for r in state["reminders"] if r.get("id") != reminder_id]
        _save(state)
        return f"[OK] Reminder {reminder_id} cleared."
    else:
        return f"[FAIL] Unknown action: {action}"


def _schedule_reminder(reminder_id: str, remind_at: datetime, text: str):
    def _waiter():
        now = datetime.now()
        delay = (remind_at - now).total_seconds()
        if delay > 0:
            time.sleep(delay)
        _notify("REMINDER", text)

    t = threading.Thread(target=_waiter, daemon=True)
    t.start()


def clock_focus(minutes: int = 25) -> str:
    """Start a focus session (Pomodoro-style). Opens Clock app."""
    if not minutes or minutes < 1:
        return "[FAIL] Duration in minutes required."
    state = _load()
    sessions = state.get("focus_sessions", [])
    now = datetime.now()
    end = now + timedelta(minutes=minutes)
    sessions.append({
        "start": now.isoformat(), "end": end.isoformat(),
        "minutes": minutes, "completed": False
    })
    state["focus_sessions"] = sessions
    _save(state)
    _open_clock_app()
    _schedule_focus_end(minutes)
    return f"[OK] Focus session started for {minutes} minutes. Stay locked in, Boss."


def _schedule_focus_end(minutes: int):
    def _waiter():
        time.sleep(minutes * 60)
        _notify("FOCUS COMPLETE", "Focus session finished. Take a break, Boss.")
    t = threading.Thread(target=_waiter, daemon=True)
    t.start()


def clock_open() -> str:
    """Open the Windows Clock app GUI."""
    _open_clock_app()
    return "[OK] Opening Windows Clock app."


def clock_status() -> str:
    """Get full clock status summary."""
    state = _load()
    lines = ["### CLOCK STATUS"]
    alarms = state.get("alarms", [])
    lines.append(f"Alarms: {len(alarms)} active" if alarms else "Alarms: none")
    timers = state.get("timers", [])
    lines.append(f"Timers: {len(timers)} active" if timers else "Timers: none")
    reminders = state.get("reminders", [])
    active_rem = [r for r in reminders if not r.get("done")]
    lines.append(f"Reminders: {len(active_rem)} pending" if active_rem else "Reminders: none")
    sw = state.get("stopwatch", {})
    if sw and sw.get("running"):
        elapsed = sw.get("elapsed_before", 0) + (datetime.now() - datetime.fromisoformat(sw["start"])).total_seconds()
        lines.append(f"Stopwatch: running ({elapsed:.1f}s)")
    else:
        lines.append("Stopwatch: stopped")
    return "\n".join(lines)
