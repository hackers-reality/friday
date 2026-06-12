"""
Proactive Scheduler — pattern learning + context-aware smart scheduling.
Extends the base scheduler with:
  1. Usage pattern learning: tracks tool usage per hour/day to find user habits
  2. Smart recommendations: suggests tasks based on learned patterns
  3. Context-aware reminders: considers active window, system load, time of day
  4. Auto-scheduling: automatically creates tasks for recurring patterns
"""
from __future__ import annotations

import json
import os
import time
import threading
import uuid
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Any, Optional

from friday._paths import FRIDAY_MEMORY

_PATTERNS_FILE = os.path.join(FRIDAY_MEMORY, "usage_patterns.json")
_INSIGHTS_FILE = os.path.join(FRIDAY_MEMORY, "scheduler_insights.json")
_REMINDERS_FILE = os.path.join(FRIDAY_MEMORY, "reminders.json")
_LEARNING_LOCK = threading.Lock()

MIN_OBSERVATIONS = 3
PATTERN_WINDOW_DAYS = 30


def _load_json(path: str, default=None):
    if default is None:
        default = {}
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return default


def _save_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _get_hour_bucket() -> str:
    return f"{datetime.now().hour:02d}:00"


def _get_day_bucket() -> str:
    return datetime.now().strftime("%A").lower()


def record_usage(tool_name: str, action: str = "", metadata: Optional[dict] = None):
    """Record a tool usage event for pattern learning."""
    with _LEARNING_LOCK:
        patterns = _load_json(_PATTERNS_FILE, {})
        key = f"{tool_name}:{action}" if action else tool_name
        hour = _get_hour_bucket()
        day = _get_day_bucket()
        now = datetime.now().isoformat()

        if key not in patterns:
            patterns[key] = {
                "tool": tool_name,
                "action": action,
                "first_seen": now,
                "total_count": 0,
                "by_hour": {},
                "by_day": {},
                "recent_timestamps": [],
            }
        p = patterns[key]
        p["total_count"] += 1
        p["by_hour"][hour] = p["by_hour"].get(hour, 0) + 1
        p["by_day"][day] = p["by_day"].get(day, 0) + 1
        p["recent_timestamps"].append(now)
        p["recent_timestamps"] = p["recent_timestamps"][-50:]
        if metadata:
            p.setdefault("metadata_history", []).append(metadata)
            p["metadata_history"] = p["metadata_history"][-20:]
        _save_json(_PATTERNS_FILE, patterns)


def analyze_patterns() -> str:
    """Analyze usage patterns and return insights."""
    patterns = _load_json(_PATTERNS_FILE, {})
    if not patterns:
        return "No usage data collected yet. Patterns will emerge after a few days of use."

    now = datetime.now()
    insights = []
    suggestions = []

    for key, p in sorted(patterns.items(), key=lambda x: x[1]["total_count"], reverse=True):
        tool = p["tool"]
        action = p.get("action", "")
        total = p["total_count"]
        label = f"{tool}({action})" if action else tool

        # Find peak hour
        if p["by_hour"]:
            peak_hour = max(p["by_hour"], key=p["by_hour"].get)
            peak_count = p["by_hour"][peak_hour]
        else:
            peak_hour = ""
            peak_count = 0

        # Find peak day
        if p["by_day"]:
            peak_day = max(p["by_day"], key=p["by_day"].get)
        else:
            peak_day = ""

        # Check if pattern is recurring
        timestamps = p.get("recent_timestamps", [])
        recent_days = set()
        for ts_str in timestamps:
            try:
                recent_days.add(datetime.fromisoformat(ts_str).date().isoformat())
            except Exception:
                pass
        unique_days = len(recent_days)

        if total >= MIN_OBSERVATIONS and unique_days >= 2:
            insights.append({
                "pattern": label,
                "total_uses": total,
                "unique_days": unique_days,
                "peak_hour": peak_hour,
                "peak_day": peak_day,
                "peak_hour_count": peak_count,
            })

            # Generate suggestion if pattern is strong
            if unique_days >= 3 and peak_count >= 2:
                suggestions.append({
                    "tool": tool,
                    "action": action,
                    "suggested_schedule": f"daily at {peak_hour.replace(':00', ':00')}" if peak_hour else "daily",
                    "confidence": min(1.0, (unique_days / 7) * (peak_count / total)),
                    "reason": f"Used {total}x across {unique_days} days, peak at {peak_hour} on {peak_day}s",
                })

    _save_json(_INSIGHTS_FILE, {"insights": insights, "suggestions": suggestions, "analyzed_at": now.isoformat()})

    result = []
    result.append(f"### Usage Pattern Analysis ({len(patterns)} tools tracked)")
    if insights:
        result.append(f"\nPatterns found ({len(insights)}):")
        for ins in insights[:10]:
            result.append(f"  - {ins['pattern']}: {ins['total_uses']} uses across {ins['unique_days']} days, "
                         f"peak {ins['peak_hour']} on {ins['peak_day']}s")
    else:
        result.append("\nNot enough data yet. Keep using FRIDAY and patterns will emerge.")

    if suggestions:
        result.append(f"\nSmart Suggestions ({len(suggestions)}):")
        for sug in suggestions[:5]:
            result.append(f"  - Schedule '{sug['tool']}' {sug['suggested_schedule']} "
                         f"(confidence: {sug['confidence']:.0%})")
    else:
        result.append("\nNo auto-scheduling suggestions yet.")

    return "\n".join(result)


def get_smart_suggestions() -> list[dict]:
    """Get auto-scheduling suggestions for the proactive scheduler."""
    insights = _load_json(_INSIGHTS_FILE, {})
    return insights.get("suggestions", [])


def auto_schedule_suggestions() -> str:
    """Automatically schedule tasks based on learned patterns."""
    suggestions = get_smart_suggestions()
    if not suggestions:
        return "No suggestions to auto-schedule."

    # Import scheduler directly to add tasks
    from friday.scheduler import scheduler_tool as base_sched
    results = []
    added = 0
    for sug in suggestions:
        if sug.get("confidence", 0) < 0.5:
            continue
        action_type = "status_check"
        tool = sug.get("tool", "")
        if "system" in tool:
            action_type = "system_check"
        elif "goal" in tool:
            action_type = "goals_review"
        elif "dream" in tool:
            action_type = "dream_cycle"
        schedule = sug.get("suggested_schedule", "daily")
        name = f"proactive_{tool}_{sug.get('action', 'routine')}_{uuid.uuid4().hex[:4]}"
        result = base_sched("add", name=name, schedule=schedule, action_type=action_type)
        if "[OK]" in result:
            added += 1
            results.append(result)

    if added:
        return f"[OK] Auto-scheduled {added} task(s) based on learned patterns."
    return "No new tasks auto-scheduled (confidence thresholds not met)."


def add_reminder(message: str, remind_at: str, repeat: str = "", category: str = "general") -> str:
    """Add a smart reminder. remind_at: ISO datetime or 'in 30m' / 'tomorrow 9am'."""
    reminders = _load_json(_REMINDERS_FILE, [])

    remind_dt = _parse_remind_time(remind_at)
    if remind_dt is None:
        return f"[FAIL] Could not parse time: {remind_at}"

    reminder = {
        "id": uuid.uuid4().hex[:8],
        "message": message,
        "remind_at": remind_dt.isoformat(),
        "repeat": repeat,
        "category": category,
        "created": datetime.now().isoformat(),
        "acknowledged": False,
    }
    reminders.append(reminder)
    _save_json(_REMINDERS_FILE, reminders)

    delta = (remind_dt - datetime.now()).total_seconds()
    if delta > 0:
        threading.Timer(min(delta, 86400 * 30), _fire_reminder, args=[reminder]).start()

    return f"[OK] Reminder set for {remind_dt.strftime('%Y-%m-%d %H:%M')} ({message[:60]}...)"


def _parse_remind_time(expr: str) -> Optional[datetime]:
    expr = expr.strip().lower()
    now = datetime.now()

    if expr == "now":
        return now

    # "in X minutes/hours"
    if expr.startswith("in "):
        try:
            parts = expr.split()
            amount = int(parts[1])
            unit = parts[2] if len(parts) > 2 else "minutes"
            if unit.startswith("minute"):
                return now + timedelta(minutes=amount)
            elif unit.startswith("hour"):
                return now + timedelta(hours=amount)
            elif unit.startswith("day"):
                return now + timedelta(days=amount)
        except Exception:
            pass

    # "tomorrow HH:MM"
    if expr.startswith("tomorrow"):
        try:
            parts = expr.split()
            hhmm = parts[1] if len(parts) > 1 else "09:00"
            h, m = hhmm.split(":")
            tomorrow = now + timedelta(days=1)
            return tomorrow.replace(hour=int(h), minute=int(m), second=0)
        except Exception:
            pass

    # ISO datetime
    try:
        return datetime.fromisoformat(expr)
    except Exception:
        pass

    # "HH:MM" (today)
    try:
        h, m = expr.split(":")
        return now.replace(hour=int(h), minute=int(m), second=0)
    except Exception:
        pass

    return None


def _fire_reminder(reminder: dict):
    """Fire a reminder notification."""
    try:
        from friday.notify import send_notification
        send_notification(f"[REMINDER] {reminder['message']}", urgency="high")
    except Exception:
        pass

    if reminder.get("repeat"):
        try:
            new_time = _parse_remind_time(reminder["repeat"])
            if new_time:
                reminder["remind_at"] = new_time.isoformat()
                reminders = _load_json(_REMINDERS_FILE, [])
                for r in reminders:
                    if r["id"] == reminder["id"]:
                        r["remind_at"] = new_time.isoformat()
                        break
                _save_json(_REMINDERS_FILE, reminders)
                delta = (new_time - datetime.now()).total_seconds()
                if delta > 0:
                    threading.Timer(min(delta, 86400 * 30), _fire_reminder, args=[reminder]).start()
        except Exception:
            pass


def check_reminders() -> str:
    """Check for due reminders and fire them."""
    reminders = _load_json(_REMINDERS_FILE, [])
    now = datetime.now()
    fired = 0
    for r in reminders:
        if r.get("acknowledged"):
            continue
        try:
            remind_at = datetime.fromisoformat(r["remind_at"])
        except Exception:
            continue
        if now >= remind_at:
            _fire_reminder(r)
            r["acknowledged"] = True
            fired += 1
    if fired:
        _save_json(_REMINDERS_FILE, reminders)
    return f"[OK] Checked reminders: {fired} fired."


def list_reminders() -> str:
    reminders = _load_json(_REMINDERS_FILE, [])
    if not reminders:
        return "No reminders set."

    lines = [f"### Reminders ({len(reminders)})"]
    for r in reminders:
        status = "✓" if r.get("acknowledged") else "⏰"
        repeat = f" (repeats {r['repeat']})" if r.get("repeat") else ""
        lines.append(f"  {status} [{r['id']}] {r['message'][:60]} @ {r['remind_at'][:16]}{repeat}")
    return "\n".join(lines)


def get_context_score() -> str:
    """Compute context-awareness score: is this a good time to interrupt?"""
    now = datetime.now()
    hour = now.hour
    day = now.weekday()
    score = {"interrupt_ok": True, "reason": "default"}

    # Weekend vs weekday
    if day >= 5:
        score["weekend"] = True

    # Late night / early morning
    if hour < 8 or hour >= 22:
        score["interrupt_ok"] = False
        score["reason"] = "late_night"
    elif 12 <= hour <= 13:
        score["reason"] = "lunch_hour"
    elif hour >= 17:
        score["reason"] = "evening"

    # Check if system is idle
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        score["cpu_load"] = cpu
        if cpu > 80:
            score["interrupt_ok"] = False
            score["reason"] = "high_cpu"
    except Exception:
        pass

    score["hour"] = hour
    score["day"] = day
    return json.dumps(score, indent=2)


def proactive_scheduler_tool(action: str = "status", **kwargs) -> str:
    """Proactive scheduler with pattern learning and smart reminders.
    Actions:
      status - show scheduler status + pattern learning state
      analyze - run pattern analysis and show insights
      record - record a tool usage event (tool_name, action, metadata)
      auto_schedule - auto-schedule tasks based on learned patterns
      remind - add a smart reminder (message, remind_at, repeat, category)
      reminders - list pending reminders
      context - show context-awareness score for interrupt decisions
    """
    if action == "status":
        patterns = _load_json(_PATTERNS_FILE, {})
        reminders = _load_json(_REMINDERS_FILE, [])
        due_reminders = sum(1 for r in reminders if not r.get("acknowledged"))
        lines = [
            "### PROACTIVE SCHEDULER",
            f"  Tools tracked: {len(patterns)}",
            f"  Total usage events: {sum(p.get('total_count', 0) for p in patterns.values())}",
            f"  Pending reminders: {due_reminders}",
        ]
        return "\n".join(lines)

    elif action == "analyze":
        return analyze_patterns()

    elif action == "record":
        record_usage(
            tool_name=kwargs.get("tool_name", "unknown"),
            action=kwargs.get("action", ""),
            metadata=kwargs.get("metadata"),
        )
        return "[OK] Usage recorded."

    elif action == "auto_schedule":
        return auto_schedule_suggestions()

    elif action == "remind":
        return add_reminder(
            message=kwargs.get("message", ""),
            remind_at=kwargs.get("remind_at", "in 30 minutes"),
            repeat=kwargs.get("repeat", ""),
            category=kwargs.get("category", "general"),
        )

    elif action == "reminders":
        return list_reminders()

    elif action == "context":
        return get_context_score()

    else:
        return f"[FAIL] Unknown action: {action}"
