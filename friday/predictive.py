"""Friday Predictive Analysis — anticipates user needs based on time patterns.
Learns from tool usage history to predict what the user typically does."""

from __future__ import annotations
import os
import json
from datetime import datetime
from collections import defaultdict
from typing import Optional

from friday._paths import FRIDAY_MEMORY

_PATTERN_FILE = os.path.join(FRIDAY_MEMORY, "usage_patterns.json")


def _load() -> dict:
    if os.path.exists(_PATTERN_FILE):
        try:
            with open(_PATTERN_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"hourly": {}, "daily": {}, "tools_by_hour": {}}


def _save(data: dict):
    os.makedirs(os.path.dirname(_PATTERN_FILE), exist_ok=True)
    try:
        with open(_PATTERN_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def record_activity(tool_name: str, active_window: str = ""):
    """Record a tool usage with temporal context for pattern learning."""
    data = _load()
    now = datetime.now()
    hour = str(now.hour)
    day = now.strftime("%A").lower()
    date = now.strftime("%Y-%m-%d")

    # Hourly tool counts
    if hour not in data["hourly"]:
        data["hourly"][hour] = {}
    data["hourly"][hour][tool_name] = data["hourly"][hour].get(tool_name, 0) + 1

    # Daily tool counts
    if day not in data["daily"]:
        data["daily"][day] = {}
    data["daily"][day][tool_name] = data["daily"][day].get(tool_name, 0) + 1

    # Tools by hour (for time-based predictions)
    if hour not in data["tools_by_hour"]:
        data["tools_by_hour"][hour] = {}
    data["tools_by_hour"][hour][tool_name] = data["tools_by_hour"][hour].get(tool_name, 0) + 1

    # Add window context
    if "windows" not in data:
        data["windows"] = {}
    if active_window:
        data["windows"][active_window] = data["windows"].get(active_window, 0) + 1

    data["last_updated"] = now.isoformat()
    data["total_recordings"] = data.get("total_recordings", 0) + 1
    _save(data)


def get_prediction(hour: Optional[int] = None, day: Optional[str] = None) -> str:
    """Predict what the user typically does at a given hour/day."""
    data = _load()
    now = datetime.now()
    hour = hour if hour is not None else now.hour
    day = (day or now.strftime("%A")).lower()

    hour_str = str(hour)
    predictions = []

    # Tools commonly used at this hour
    hour_tools = data.get("tools_by_hour", {}).get(hour_str, {})
    if hour_tools:
        sorted_tools = sorted(hour_tools.items(), key=lambda x: -x[1])
        top_tools = [t for t, c in sorted_tools[:5]]
        predictions.append(f"At {hour}:00, you typically use: {', '.join(top_tools)}")

    # Tools commonly used on this day
    day_tools = data.get("daily", {}).get(day, {})
    if day_tools:
        sorted_day = sorted(day_tools.items(), key=lambda x: -x[1])
        top_day = [t for t, c in sorted_day[:3]]
        predictions.append(f"On {day.capitalize()}s, you often use: {', '.join(top_day)}")

    # Common windows
    windows = data.get("windows", {})
    if windows:
        top_windows = sorted(windows.items(), key=lambda x: -x[1])[:3]
        predictions.append(f"Frequent apps: {', '.join(w for w, c in top_windows)}")

    if not predictions:
        return "Not enough data yet. I'll learn your patterns over time."

    total = data.get("total_recordings", 0)
    predictions.append(f"Based on {total} recorded activities.")
    return "\n".join(predictions)


def predictive_tool(action: str = "predict", **kwargs) -> str:
    """Predictive analysis: anticipate user needs. Actions: predict (what now?), patterns (all patterns), stats."""
    if action == "predict":
        return get_prediction(
            hour=kwargs.get("hour"),
            day=kwargs.get("day"),
        )
    elif action == "patterns":
        data = _load()
        total = data.get("total_recordings", 0)
        hours = len(data.get("tools_by_hour", {}))
        days = len(data.get("daily", {}))
        return (
            f"Usage patterns learned:\n"
            f"  Recordings: {total}\n"
            f"  Hours with data: {hours}\n"
            f"  Days with data: {days}\n"
            f"  Frequent apps tracked: {len(data.get('windows', {}))}"
        )
    elif action == "stats":
        data = _load()
        if not data.get("tools_by_hour"):
            return "No patterns learned yet."
        # Find peak hour
        peak_hour = max(data["tools_by_hour"].items(), key=lambda x: sum(x[1].values()))
        return (
            f"Peak usage hour: {peak_hour[0]}:00 ({sum(peak_hour[1].values())} tools)\n"
            f"Total learning data: {data.get('total_recordings', 0)} activities"
        )
    else:
        return f"[FAIL] Unknown action: {action}"
