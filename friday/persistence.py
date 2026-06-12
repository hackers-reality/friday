"""
Multi-Day Autonomous Persistence Framework — FRIDAY edition.
Allows FRIDAY agents to persist state across sessions/days:
  1. Checkpoint agent state (memory, goals, task queues, active context)
  2. Restore agent state on restart
  3. Track continuity across sessions with daily summaries
  4. Auto-resume interrupted workflows

Architecture:
  - State snapshots saved as JSON/JSONL in FRIDAY_MEMORY
  - Active task queue persisted for resume
  - Daily summary generated on each shutdown
  - Continuity check on startup detects what was in progress
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from friday._paths import FRIDAY_MEMORY

_PERSISTENCE_DIR = os.path.join(FRIDAY_MEMORY, "persistence")
_STATE_FILE = os.path.join(_PERSISTENCE_DIR, "agent_state.json")
_TASK_QUEUE_FILE = os.path.join(_PERSISTENCE_DIR, "task_queue.json")
_CONTINUITY_FILE = os.path.join(_PERSISTENCE_DIR, "continuity.json")
_DAILY_SUMMARY_DIR = os.path.join(_PERSISTENCE_DIR, "daily_summaries")
_AUTO_CHECKPOINT_INTERVAL = 300  # 5 minutes

_auto_checkpointer: Optional[threading.Thread] = None
_auto_checkpointer_stop = threading.Event()


def _ensure_dirs():
    os.makedirs(_PERSISTENCE_DIR, exist_ok=True)
    os.makedirs(_DAILY_SUMMARY_DIR, exist_ok=True)


def save_state(
    agent_id: str,
    state: dict,
    metadata: Optional[dict] = None,
) -> str:
    """Save an agent's state for cross-session persistence."""
    _ensure_dirs()
    states = _load_json(_STATE_FILE, {})
    entry = {
        "agent_id": agent_id,
        "state": state,
        "metadata": metadata or {},
        "saved_at": datetime.now().isoformat(),
    }
    states[agent_id] = entry
    _save_json(_STATE_FILE, states)
    return f"[OK] State saved for agent '{agent_id}'"


def load_state(agent_id: str) -> Optional[dict]:
    """Load an agent's persisted state."""
    states = _load_json(_STATE_FILE, {})
    entry = states.get(agent_id)
    if entry:
        entry["_restored_at"] = datetime.now().isoformat()
        return entry
    return None


def list_saved_agents() -> str:
    """List all agents with saved state."""
    states = _load_json(_STATE_FILE, {})
    if not states:
        return "No persisted agent states found."

    lines = ["### Persisted Agent States"]
    for agent_id, entry in states.items():
        saved_at = entry.get("saved_at", "?")[:19]
        state_size = len(json.dumps(entry.get("state", {})))
        meta = entry.get("metadata", {})
        task_count = meta.get("task_count", "?")
        lines.append(f"  - {agent_id}: saved {saved_at} ({state_size}b, {task_count} tasks)")
    return "\n".join(lines)


def clear_state(agent_id: str) -> str:
    """Clear a specific agent's persisted state."""
    states = _load_json(_STATE_FILE, {})
    if agent_id in states:
        del states[agent_id]
        _save_json(_STATE_FILE, states)
        return f"[OK] Cleared state for '{agent_id}'"
    return f"[INFO] No state found for '{agent_id}'"


def save_task_queue(tasks: list[dict]) -> str:
    """Persist the active task queue for cross-session resume."""
    _ensure_dirs()
    entry = {
        "tasks": tasks,
        "count": len(tasks),
        "saved_at": datetime.now().isoformat(),
    }
    _save_json(_TASK_QUEUE_FILE, entry)
    return f"[OK] Task queue saved ({len(tasks)} tasks)"


def load_task_queue() -> list[dict]:
    """Load the persisted task queue."""
    entry = _load_json(_TASK_QUEUE_FILE, {})
    return entry.get("tasks", [])


def record_continuity(event: str, details: Optional[dict] = None) -> str:
    """Record a continuity event for session tracking."""
    _ensure_dirs()
    events = _load_json(_CONTINUITY_FILE, [])
    events.append({
        "event": event,
        "details": details or {},
        "timestamp": datetime.now().isoformat(),
        "session_id": _get_or_create_session_id(),
    })
    events = events[-1000:]
    _save_json(_CONTINUITY_FILE, events)
    return f"[OK] Continuity event recorded: {event}"


def _get_or_create_session_id() -> str:
    """Get or create a persistent session ID."""
    sid_file = os.path.join(FRIDAY_MEMORY, ".friday_session")
    try:
        if os.path.exists(sid_file):
            with open(sid_file) as f:
                sid = f.read().strip()
                if sid:
                    return sid
    except Exception:
        pass
    sid = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    try:
        with open(sid_file, "w") as f:
            f.write(sid)
    except Exception:
        pass
    return sid


def get_continuity_log(limit: int = 20) -> str:
    """Get the continuity event log."""
    events = _load_json(_CONTINUITY_FILE, [])
    if not events:
        return "No continuity events recorded yet."

    lines = [f"### Continuity Log ({len(events)} events)"]
    for ev in events[-limit:]:
        ts = ev.get("timestamp", "?")[:19]
        event = ev.get("event", "?")
        lines.append(f"  [{ts}] {event}")
    return "\n".join(lines)


def generate_daily_summary() -> str:
    """Generate a daily summary of all agent activity."""
    _ensure_dirs()
    today = datetime.now().strftime("%Y-%m-%d")

    states = _load_json(_STATE_FILE, {})
    task_queue = _load_json(_TASK_QUEUE_FILE, {})
    continuity = _load_json(_CONTINUITY_FILE, [])

    today_events = [
        e for e in continuity
        if e.get("timestamp", "").startswith(today)
    ]

    summary = {
        "date": today,
        "generated_at": datetime.now().isoformat(),
        "session_id": _get_or_create_session_id(),
        "persisted_agents": list(states.keys()),
        "persisted_agent_count": len(states),
        "pending_tasks": task_queue.get("count", 0),
        "events_today": len(today_events),
        "events": today_events[-20:],
        "continuity_ids": [e.get("timestamp", "") for e in today_events[-5:]],
    }

    path = os.path.join(_DAILY_SUMMARY_DIR, f"summary_{today}.json")
    _save_json(path, summary)
    return json.dumps(summary, indent=2)


def get_daily_summaries(days: int = 7) -> str:
    """Get recent daily summaries."""
    _ensure_dirs()
    today = datetime.now()
    summaries = []
    for i in range(days):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        path = os.path.join(_DAILY_SUMMARY_DIR, f"summary_{date_str}.json")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    summaries.append(json.load(f))
            except Exception:
                pass

    if not summaries:
        return "No daily summaries found yet."

    lines = [f"### Daily Summaries (last {len(summaries)} days)"]
    for s in summaries:
        date = s.get("date", "?")
        agents = s.get("persisted_agent_count", 0)
        tasks = s.get("pending_tasks", 0)
        events = s.get("events_today", 0)
        lines.append(f"  [{date}] {agents} agents, {tasks} tasks pending, {events} events")
    return "\n".join(lines)


def check_continuity_on_startup() -> str:
    """Check if there are pending tasks or saved states from previous sessions."""
    _ensure_dirs()

    task_queue = load_task_queue()
    states = _load_json(_STATE_FILE, {})

    if not task_queue and not states:
        record_continuity("clean_startup", {"note": "No pending state found"})
        return "Fresh start — no pending tasks or saved agent states."

    result_parts = ["### Continuity Check — Previous Session Found"]
    if task_queue:
        result_parts.append(f"\nPending tasks in queue: {len(task_queue)}")
        for t in task_queue[:5]:
            desc = t.get("description", t.get("task", "?"))

            result_parts.append(f"  - {desc[:80]}")
        if len(task_queue) > 5:
            result_parts.append(f"  ... and {len(task_queue) - 5} more")

    if states:
        result_parts.append(f"\nSaved agent states: {len(states)}")
        for aid, entry in states.items():
            saved_at = entry.get("saved_at", "?")[:19]
            result_parts.append(f"  - {aid} (saved {saved_at})")

    record_continuity("startup_with_pending", {
        "task_count": len(task_queue),
        "agent_count": len(states),
    })

    return "\n".join(result_parts)


def mark_completed(task_id: str) -> str:
    """Mark a persisted task as completed and remove from queue."""
    tasks = load_task_queue()
    before = len(tasks)
    tasks = [t for t in tasks if t.get("id") != task_id and t.get("task_id") != task_id]
    removed = before - len(tasks)
    if removed:
        save_task_queue(tasks)
        return f"[OK] Task {task_id} completed and removed from queue."
    return f"[INFO] Task {task_id} not found in queue."


def _auto_checkpoint_loop():
    """Background loop that auto-checkpoints state periodically."""
    while not _auto_checkpointer_stop.is_set():
        try:
            record_continuity("auto_checkpoint", {
                "checkpoint_at": datetime.now().isoformat(),
                "session_id": _get_or_create_session_id(),
            })
        except Exception:
            pass
        _auto_checkpointer_stop.wait(_AUTO_CHECKPOINT_INTERVAL)


def start_auto_checkpoint() -> str:
    """Start the automatic state checkpointing background thread."""
    global _auto_checkpointer, _auto_checkpointer_stop
    if _auto_checkpointer and _auto_checkpointer.is_alive():
        return "[OK] Auto-checkpointer already running."
    _auto_checkpointer_stop.clear()
    _auto_checkpointer = threading.Thread(target=_auto_checkpoint_loop, daemon=True)
    _auto_checkpointer.start()
    return "[OK] Auto-checkpointer started (every 5 minutes)"


def stop_auto_checkpoint() -> str:
    """Stop the automatic state checkpointing."""
    _auto_checkpointer_stop.set()
    if _auto_checkpointer:
        _auto_checkpointer.join(timeout=3)
    return "[OK] Auto-checkpointer stopped."


def persistence_tool(action: str = "status", **kwargs) -> str:
    """Multi-day autonomous persistence framework.
    
    Actions:
      status - Show persistence status
      save - Save agent state (agent_id, state JSON, metadata JSON)
      load - Load agent state (agent_id)
      agents - List all agents with saved state
      clear - Clear agent state (agent_id)
      task_queue - Show pending task queue
      continuity - Show continuity event log
      summary - Generate daily summary
      summaries - Show recent daily summaries
      startup_check - Check continuity on startup
      checkpoint_start - Start auto-checkpointing
      checkpoint_stop - Stop auto-checkpointing
    """
    if action == "status":
        states = _load_json(_STATE_FILE, {})
        tasks = load_task_queue()
        events = _load_json(_CONTINUITY_FILE, [])
        lines = [
            "### PERSISTENCE STATUS",
            f"  Persisted agents: {len(states)}",
            f"  Pending tasks: {len(tasks)}",
            f"  Continuity events recorded: {len(events)}",
            f"  Auto-checkpointer: {'running' if _auto_checkpointer and _auto_checkpointer.is_alive() else 'stopped'}",
        ]
        return "\n".join(lines)

    elif action == "save":
        agent_id = kwargs.get("agent_id", "")
        state_str = kwargs.get("state", "{}")
        meta_str = kwargs.get("metadata", "{}")
        if not agent_id:
            return "[FAIL] agent_id required"
        try:
            state = json.loads(state_str) if isinstance(state_str, str) else state_str
            meta = json.loads(meta_str) if isinstance(meta_str, str) else meta_str
        except Exception:
            return "[FAIL] state/metadata must be valid JSON"
        return save_state(agent_id, state, meta)

    elif action == "load":
        agent_id = kwargs.get("agent_id", "")
        if not agent_id:
            return "[FAIL] agent_id required"
        entry = load_state(agent_id)
        if entry:
            return json.dumps(entry, indent=2, default=str)
        return f"[INFO] No saved state for '{agent_id}'"

    elif action == "agents":
        return list_saved_agents()

    elif action == "clear":
        agent_id = kwargs.get("agent_id", "")
        if not agent_id:
            return "[FAIL] agent_id required"
        return clear_state(agent_id)

    elif action == "task_queue":
        tasks = load_task_queue()
        if not tasks:
            return "No pending tasks."
        lines = [f"### Pending Tasks ({len(tasks)})"]
        for t in tasks[:10]:
            desc = t.get("description", t.get("task", "?"))
            status = t.get("status", "pending")
            lines.append(f"  [{status}] {desc[:100]}")
        return "\n".join(lines)

    elif action == "continuity":
        return get_continuity_log(limit=kwargs.get("limit", 20))

    elif action == "summary":
        return generate_daily_summary()

    elif action == "summaries":
        return get_daily_summaries(days=kwargs.get("days", 7))

    elif action == "startup_check":
        return check_continuity_on_startup()

    elif action == "checkpoint_start":
        return start_auto_checkpoint()

    elif action == "checkpoint_stop":
        return stop_auto_checkpoint()

    else:
        return f"[FAIL] Unknown action: {action}"


# Helper
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
