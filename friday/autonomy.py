"""
Friday Autonomy Engine — durable task queue with retry, reflection, and background improvement loop.

Allows FRIDAY to queue tasks, track progress, retry on failure, reflect on results,
and run a self-improvement loop in the background.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import json
import os
import time
import copy

from friday._paths import FRIDAY_MEMORY

_AUTONOMY_FILE = os.path.join(FRIDAY_MEMORY, "autonomy_queue.json")

# ─── Task states ───────────────────────────────────────────

TASK_STATES = ("queued", "running", "blocked", "failed", "completed", "paused")


def _load_queue() -> dict:
    """Load the autonomy queue from disk."""
    if os.path.exists(_AUTONOMY_FILE):
        try:
            with open(_AUTONOMY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"tasks": [], "next_id": 1, "budget": {}}


def _save_queue(data: dict) -> None:
    """Save the autonomy queue to disk."""
    os.makedirs(os.path.dirname(_AUTONOMY_FILE), exist_ok=True)
    with open(_AUTONOMY_FILE, "w") as f:
        json.dump(data, f, indent=4)


def _now() -> str:
    return datetime.now().isoformat()


def queue_task(
    description: str,
    tool_name: str = "",
    tool_args: dict = None,
    priority: int = 5,
    retry_policy: dict = None,
    metadata: dict = None,
) -> dict:
    """
    Queue a new autonomous task.

    Args:
        description: Human-readable description.
        tool_name: Name of the tool to call.
        tool_args: Arguments for the tool.
        priority: 1-10 (10 = highest).
        retry_policy: {"max_retries": int, "backoff": float seconds}.
        metadata: Additional metadata.

    Returns:
        dict with "id", "description", "status".
    """
    if not description:
        return {"error": "description is required"}

    data = _load_queue()
    task_id = data["next_id"]
    data["next_id"] += 1

    task = {
        "id": task_id,
        "description": description,
        "tool_name": tool_name,
        "tool_args": tool_args or {},
        "priority": max(1, min(10, priority)),
        "status": "queued",
        "retry_policy": retry_policy or {"max_retries": 2, "backoff": 1.0},
        "retry_count": 0,
        "error": "",
        "result": "",
        "reflection": "",
        "created_at": _now(),
        "started_at": "",
        "completed_at": "",
        "metadata": metadata or {},
    }

    data["tasks"].append(task)
    _save_queue(data)
    return {"success": True, "id": task_id, "description": description, "status": "queued"}


def get_task(task_id: int) -> Optional[dict]:
    """Get a task by ID."""
    data = _load_queue()
    for t in data["tasks"]:
        if t["id"] == task_id:
            return dict(t)
    return None


def list_tasks(status: str = "", limit: int = 50) -> list:
    """List tasks, optionally filtered by status, newest first."""
    data = _load_queue()
    tasks = data["tasks"]
    if status:
        tasks = [t for t in tasks if t.get("status") == status]
    tasks = sorted(tasks, key=lambda x: x.get("created_at", ""), reverse=True)
    return tasks[:limit]


def update_task(task_id: int, **updates) -> dict:
    """Update a task's fields."""
    data = _load_queue()
    for t in data["tasks"]:
        if t["id"] == task_id:
            for k, v in updates.items():
                if k in ("status", "result", "error", "reflection", "started_at", "completed_at", "retry_count"):
                    t[k] = v
            _save_queue(data)
            return {"success": True, "id": task_id}
    return {"error": f"Task {task_id} not found"}


def mark_running(task_id: int) -> dict:
    """Mark a task as running."""
    return update_task(task_id, status="running", started_at=_now())


def mark_completed(task_id: int, result: str = "", reflection: str = "") -> dict:
    """Mark a task as completed."""
    return update_task(task_id, status="completed", result=str(result)[:1000],
                       reflection=str(reflection)[:2000], completed_at=_now())


def mark_failed(task_id: int, error: str = "", reflection: str = "") -> dict:
    """Mark a task as failed, with optional auto-retry."""
    task = get_task(task_id)
    if not task:
        return {"error": f"Task {task_id} not found"}

    retry_policy = task.get("retry_policy", {"max_retries": 2, "backoff": 1.0})
    retry_count = task.get("retry_count", 0) + 1

    if retry_count <= retry_policy.get("max_retries", 2):
        # Auto-retry
        update_task(task_id, status="queued", retry_count=retry_count,
                    error=str(error)[:500], reflection=str(reflection)[:2000])
        return {"success": True, "id": task_id, "status": "queued", "retry_count": retry_count,
                "will_retry": True}
    else:
        update_task(task_id, status="failed", retry_count=retry_count,
                    error=str(error)[:500], reflection=str(reflection)[:2000],
                    completed_at=_now())
        return {"success": True, "id": task_id, "status": "failed", "retry_count": retry_count,
                "will_retry": False}


def pause_task(task_id: int) -> dict:
    """Pause a task."""
    task = get_task(task_id)
    if not task:
        return {"error": f"Task {task_id} not found"}
    if task["status"] not in ("queued", "running"):
        return {"error": f"Task {task_id} is {task['status']}, cannot pause"}
    return update_task(task_id, status="paused")


def resume_task(task_id: int) -> dict:
    """Resume a paused task."""
    task = get_task(task_id)
    if not task:
        return {"error": f"Task {task_id} not found"}
    if task["status"] != "paused":
        return {"error": f"Task {task_id} is {task['status']}, cannot resume"}
    return update_task(task_id, status="queued")


def task_summary() -> str:
    """Get a summary of all tasks."""
    data = _load_queue()
    tasks = data["tasks"]
    counts = {}
    for t in tasks:
        s = t.get("status", "unknown")
        counts[s] = counts.get(s, 0) + 1

    budget = data.get("budget", {})
    lines = ["### AUTONOMY TASK SUMMARY\n"]
    for state in TASK_STATES:
        c = counts.get(state, 0)
        lines.append(f"  {state}: {c}")
    lines.append(f"  Total: {len(tasks)}")
    if budget:
        lines.append(f"\n  Budget remaining: {budget.get('remaining', 'unlimited')}")
    return "\n".join(lines)


def autonomy_tool(action: str = "status", **kwargs) -> str:
    """
    Friday tool for the autonomy engine.
    Actions: status, summary, queue, list, get, pause, resume, fail, complete.
    """
    if action == "status":
        return task_summary()

    if action == "summary":
        return task_summary()

    if action == "queue":
        description = kwargs.get("description", "")
        if not description:
            return "[FAIL] Provide 'description'."
        tool_name = kwargs.get("tool", "")
        tool_args = kwargs.get("args", {})
        if isinstance(tool_args, str):
            try:
                tool_args = json.loads(tool_args)
            except (json.JSONDecodeError, TypeError):
                tool_args = {"raw": tool_args}
        priority = kwargs.get("priority", 5)
        retry_policy = {"max_retries": int(kwargs.get("max_retries", 2)),
                        "backoff": float(kwargs.get("backoff", 1.0))}

        result = queue_task(description, tool_name=tool_name, tool_args=tool_args,
                            priority=priority, retry_policy=retry_policy)
        if "error" in result:
            return f"[FAIL] {result['error']}"
        return f"[OK] Task #{result['id']} queued: {result['description'][:80]}"

    if action == "list":
        status_filter = kwargs.get("status", "")
        tasks = list_tasks(status=status_filter)
        if not tasks:
            return "[OK] No tasks found."
        lines = ["### AUTONOMY TASKS\n"]
        for t in tasks:
            lines.append(
                f"  [{t['id']}] {t.get('description','?')[:60]} "
                f"- {t.get('status','?')} "
                f"(retry: {t.get('retry_count',0)}/{t.get('retry_policy',{}).get('max_retries',2)})"
            )
        return "\n".join(lines)

    if action == "get":
        task_id = kwargs.get("id")
        if task_id is None:
            return "[FAIL] Provide 'id'."
        try:
            task_id = int(task_id)
        except (TypeError, ValueError):
            return "[FAIL] id must be an integer."
        task = get_task(task_id)
        if not task:
            return f"[FAIL] Task #{task_id} not found."
        lines = [f"### TASK #{task_id}\n"]
        for k, v in task.items():
            if isinstance(v, (dict, list)):
                lines.append(f"  {k}: {json.dumps(v, default=str)[:120]}")
            else:
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)

    if action == "pause":
        task_id = kwargs.get("id")
        if task_id is None:
            return "[FAIL] Provide 'id'."
        try:
            task_id = int(task_id)
        except (TypeError, ValueError):
            return "[FAIL] id must be an integer."
        result = pause_task(task_id)
        if "error" in result:
            return f"[FAIL] {result['error']}"
        return f"[OK] Task #{task_id} paused."

    if action == "resume":
        task_id = kwargs.get("id")
        if task_id is None:
            return "[FAIL] Provide 'id'."
        try:
            task_id = int(task_id)
        except (TypeError, ValueError):
            return "[FAIL] id must be an integer."
        result = resume_task(task_id)
        if "error" in result:
            return f"[FAIL] {result['error']}"
        return f"[OK] Task #{task_id} resumed."

    if action == "complete":
        task_id = kwargs.get("id")
        if task_id is None:
            return "[FAIL] Provide 'id'."
        try:
            task_id = int(task_id)
        except (TypeError, ValueError):
            return "[FAIL] id must be an integer."
        result_str = kwargs.get("result", "")
        reflection = kwargs.get("reflection", "")
        result = mark_completed(task_id, result=result_str, reflection=reflection)
        if "error" in result:
            return f"[FAIL] {result['error']}"
        return f"[OK] Task #{task_id} completed."

    return f"[FAIL] Unknown action: {action}. Available: status, summary, queue, list, get, pause, resume, complete"
