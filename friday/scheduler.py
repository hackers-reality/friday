"""Friday Scheduler — cron-style scheduled tasks.
Lets Friday autonomously run tasks on a schedule: reports, reminders, checks."""

from __future__ import annotations
import os
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Callable

from friday._paths import FRIDAY_MEMORY
from friday.orchestration_config import ensure_config

_SCHEDULE_FILE = os.path.join(FRIDAY_MEMORY, "schedules.json")
_scheduler_thread: Optional[threading.Thread] = None
_scheduler_stop = threading.Event()
_scheduler_lock = threading.Lock()


def _ensure_youtube_jobs_registered() -> None:
    """Ensure YouTube daily jobs are present when enabled, or disabled when off."""
    cfg = ensure_config().get("youtube", {})
    enabled = bool(cfg.get("enabled", False))
    ingest_time = str(cfg.get("ingest_time", "06:00"))
    briefing_time = str(cfg.get("briefing_time", "08:00"))

    schedules = _load()

    def _upsert(name: str, schedule: str, action: str, params: dict):
        for task in schedules:
            if task.get("name") == name:
                task["schedule"] = schedule
                task["action"] = action
                task["params"] = params
                task["enabled"] = True
                return
        import uuid
        schedules.append({
            "id": f"task_{uuid.uuid4().hex[:8]}",
            "name": name,
            "schedule": schedule,
            "action": action,
            "params": params,
            "enabled": True,
            "created": datetime.now().isoformat(),
            "last_run": "",
            "run_count": 0,
            "last_run_ts": 0,
        })

    # normalize schedule expressions for existing scheduler parser
    ingest_schedule = f"daily at {ingest_time}"
    briefing_schedule = f"daily at {briefing_time}"

    if enabled:
        channel_id = str(cfg.get("channel_id", "")).strip()
        _upsert(
            name="youtube_daily_ingestion",
            schedule=ingest_schedule,
            action="youtube_ingest",
            params={"channel_id": channel_id},
        )
        _upsert(
            name="youtube_morning_briefing",
            schedule=briefing_schedule,
            action="youtube_briefing",
            params={"channel_id": channel_id},
        )
    else:
        for task in schedules:
            if task.get("action") in {"youtube_ingest", "youtube_briefing"}:
                task["enabled"] = False

    _save(schedules)


def _load() -> list:
    if os.path.exists(_SCHEDULE_FILE):
        try:
            with open(_SCHEDULE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save(schedules: list):
    os.makedirs(os.path.dirname(_SCHEDULE_FILE), exist_ok=True)
    try:
        with open(_SCHEDULE_FILE, "w") as f:
            json.dump(schedules, f, indent=2)
    except Exception:
        pass


def _parse_interval(expr: str) -> int:
    """Parse a natural language or cron-like interval into seconds."""
    expr = expr.lower().strip()
    if expr == "daily" or expr == "every day":
        return 86400
    elif expr == "hourly" or expr == "every hour":
        return 3600
    elif expr == "every 30 minutes":
        return 1800
    elif expr == "every 15 minutes":
        return 900
    elif "minute" in expr:
        try:
            mins = int(expr.split()[1])
            return mins * 60
        except Exception:
            return 3600
    elif "hour" in expr:
        try:
            hrs = int(expr.split()[1])
            return hrs * 3600
        except Exception:
            return 86400
    return 86400  # default daily


def _is_daily_time_due(task: dict, now_dt: datetime) -> bool:
    """Handle `daily at HH:MM` schedules with one run per day."""
    expr = str(task.get("schedule", "")).lower().strip()
    if not expr.startswith("daily at "):
        return False

    hhmm = expr.replace("daily at ", "").strip()
    try:
        hour_s, minute_s = hhmm.split(":", 1)
        target_hour = int(hour_s)
        target_minute = int(minute_s)
    except Exception:
        return False

    if now_dt.hour != target_hour or now_dt.minute != target_minute:
        return False

    # Prevent repeated executions during the same minute/day.
    last_run = str(task.get("last_run", ""))
    if last_run.startswith(now_dt.date().isoformat()):
        try:
            prev = datetime.fromisoformat(last_run)
            return not (prev.hour == now_dt.hour and prev.minute == now_dt.minute)
        except Exception:
            return False
    return True


def _execute_task(task: dict):
    """Execute a scheduled task's action."""
    action = task.get("action", "")
    params = task.get("params", {})
    task_id = task.get("id", "unknown")

    try:
        if action == "status_check":
            from friday.tools import status_check
            result = status_check(params.get("include", "system"))
        elif action == "goals_review":
            from friday.tools import goals_tool_handler
            result = goals_tool_handler("list")
        elif action == "system_check":
            from friday.tools import system_cpu, system_memory, system_disk
            cpu = system_cpu()
            mem = system_memory()
            disk = system_disk()
            result = f"{cpu}\n{mem}\n{disk}"
        elif action == "dream_cycle":
            from friday.dreaming import dream_tool
            result = dream_tool("cycle")
        elif action == "custom":
            from friday.tools import run_cmd
            result = run_cmd(params.get("command", "echo no command"))
        elif action == "youtube_ingest":
            from friday.daily_ingestion_job import run_ingest
            run_ingest(params.get("channel_id"))
            result = "[OK] YouTube daily ingestion completed"
        elif action == "youtube_briefing":
            from friday.morning_briefing import publish_briefing
            ch = params.get("channel_id")
            if not ch:
                cfg = ensure_config().get("youtube", {})
                ch = cfg.get("channel_id", "")
            if ch:
                publish_briefing(ch)
                result = "[OK] YouTube morning briefing published"
            else:
                result = "[WARN] YouTube briefing skipped: channel_id missing"
        else:
            result = f"[Scheduler] Unknown action: {action}"

        # Log execution
        now = datetime.now().isoformat()
        task["last_run"] = now
        task["last_result"] = str(result)[:200]
        task["run_count"] = task.get("run_count", 0) + 1
    except Exception as e:
        task["last_error"] = str(e)
        task["last_run"] = datetime.now().isoformat()


def _scheduler_loop():
    """Background loop that checks and executes due tasks."""
    while not _scheduler_stop.is_set():
        try:
            schedules = _load()
            now = time.time()
            now_dt = datetime.now()
            for task in schedules:
                if not task.get("enabled", True):
                    continue
                schedule_expr = str(task.get("schedule", "")).lower().strip()
                if schedule_expr.startswith("daily at "):
                    if _is_daily_time_due(task, now_dt):
                        task["last_run_ts"] = now
                        _execute_task(task)
                        _save(schedules)
                    continue
                if _is_daily_time_due(task, now_dt):
                    task["last_run_ts"] = now
                    _execute_task(task)
                    _save(schedules)
                    continue
                interval = _parse_interval(task.get("schedule", "daily"))
                last_run = task.get("last_run_ts", 0)
                if now - last_run >= interval:
                    task["last_run_ts"] = now
                    _execute_task(task)
                    _save(schedules)
        except Exception:
            pass
        _scheduler_stop.wait(30)  # check every 30 seconds


def scheduler_tool(action: str = "list", **kwargs) -> str:
    """Manage scheduled tasks. Actions: list, add, remove, pause, resume.
    Parameters:
      action: list, add, remove, pause, resume
      name: task name (for add/remove/pause/resume)
      schedule: interval string like 'daily', 'hourly', 'every 30 minutes' (for add)
      action_type: action to run: status_check, goals_review, system_check, dream_cycle, custom (for add)
      params: JSON string of parameters for the action (for add)
      command: shell command (for action_type=custom)
    """
    global _scheduler_thread, _scheduler_stop

    if action == "list":
        tasks = _load()
        if not tasks:
            return "No scheduled tasks."
        lines = ["### SCHEDULED TASKS"]
        for t in tasks:
            status = "ACTIVE" if t.get("enabled", True) else "PAUSED"
            last_raw = t.get("last_run") or "never"
            last = str(last_raw)[:16]
            lines.append(
                f"  [{t['id']}] {t.get('name', 'Unnamed')} - {status}\n"
                f"       Schedule: {t.get('schedule', 'daily')}\n"
                f"       Last run: {last}\n"
                f"       Runs: {t.get('run_count', 0)}"
            )
        return "\n".join(lines)

    elif action == "add":
        name = kwargs.get("name", "")
        schedule = kwargs.get("schedule", "daily")
        action_type = kwargs.get("action_type", "status_check")
        params_str = kwargs.get("params", "{}")
        command = kwargs.get("command", "")

        if not name:
            return "[FAIL] Task name required."

        import uuid
        task = {
            "id": f"task_{uuid.uuid4().hex[:8]}",
            "name": name,
            "schedule": schedule,
            "action": action_type,
            "params": json.loads(params_str) if params_str else {},
            "command": command,
            "enabled": True,
            "created": datetime.now().isoformat(),
            "last_run": None,
            "run_count": 0,
            "last_run_ts": 0,
        }

        if action_type == "custom" and command:
            task["params"]["command"] = command

        schedules = _load()
        schedules.append(task)
        _save(schedules)

        return f"[OK] Task '{name}' added ({task['id']}). Schedule: {schedule}. Action: {action_type}."

    elif action == "remove":
        name = kwargs.get("name", "")
        task_id = kwargs.get("id", "")
        schedules = _load()
        before = len(schedules)
        schedules = [
            t for t in schedules
            if not ((name and t.get("name") == name) or (task_id and t.get("id") == task_id))
        ]
        removed = before - len(schedules)
        if removed:
            _save(schedules)
            return f"[OK] Removed {removed} task(s)."
        return "[INFO] No matching tasks found."

    elif action in ("pause", "resume"):
        enabled = action == "resume"
        name = kwargs.get("name", "")
        task_id = kwargs.get("id", "")
        schedules = _load()
        updated = 0
        for t in schedules:
            if (name and t.get("name") == name) or (task_id and t.get("id") == task_id):
                t["enabled"] = enabled
                updated += 1
        if updated:
            _save(schedules)
            return f"[OK] {action.capitalize()}d {updated} task(s)."
        return f"[INFO] No matching tasks found for {action}."

    elif action == "start":
        if _scheduler_thread and _scheduler_thread.is_alive():
            return "[INFO] Scheduler already running."
        # Sync default YouTube jobs before scheduler loop starts.
        try:
            _ensure_youtube_jobs_registered()
        except Exception:
            pass
        _scheduler_stop.clear()
        _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True)
        _scheduler_thread.start()
        return "[OK] Scheduler started."
    elif action == "stop":
        _scheduler_stop.set()
        if _scheduler_thread:
            _scheduler_thread.join(timeout=3)
        _scheduler_thread = None
        return "[OK] Scheduler stopped."
    else:
        return f"[FAIL] Unknown action: {action}"
