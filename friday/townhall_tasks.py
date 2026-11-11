"""Townhall task board — shared, persistent, visible to agents and FRIDAY.

One JSON file (friday_memory/townhall_tasks.json, env-overridable for tests):
a flat list of task dicts:

    {"id": "T7", "title": "...", "notes": "...", "assignee": "NOVA",
     "status": "open|claimed|done", "created_by": "FRIDAY",
     "created_at": "...", "claimed_at": "...", "done_at": "..."}

Public API (tools) and helpers used by the DreamEngine:
    townhall_task_add(title, assignee="", notes="", created_by="FRIDAY") -> str
    townhall_task_list(status="") -> str
    townhall_task_assign(task_id, agent) -> str
    townhall_task_done(task_id) -> str
    claim_next_task(agent_name) -> dict | None      # oldest "open" task -> claimed
    complete_task(task_id) -> "" | task              # claimed -> done (internal)
    open_tasks_summary(max_items=4) -> str           # for agent prompts
    AGENT_ROSTER                                      # valid assignees
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path

try:
    from friday._paths import FRIDAY_MEMORY
except Exception:  # pragma: no cover
    FRIDAY_MEMORY = Path(__file__).resolve().parent.parent / "friday_memory"

TASKS_PATH = Path(os.getenv("TOWNHALL_TASKS_PATH", str(Path(FRIDAY_MEMORY) / "townhall_tasks.json")))

AGENT_ROSTER = ("FRIDAY", "JARVIS", "NOVA", "ATLAS", "SENTRY", "FORGE",
                "ECHO", "AEGIS", "CRUX", "VERSE", "LORE")

_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _load() -> list[dict]:
    try:
        data = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save(tasks: list[dict]) -> None:
    with _LOCK:
        TASKS_PATH.parent.mkdir(parents=True, exist_ok=True)
        TASKS_PATH.write_text(json.dumps(tasks, indent=2), encoding="utf-8")


def _next_id(tasks: list[dict]) -> str:
    best = 0
    for t in tasks:
        tid = str(t.get("id", ""))
        if tid.startswith("T") and tid[1:].isdigit():
            best = max(best, int(tid[1:]))
    return f"T{best + 1}"


def add_task(title: str, assignee: str = "", notes: str = "", created_by: str = "FRIDAY") -> dict | None:
    title = (title or "").strip()
    if not title:
        return None
    assignee = (assignee or "").strip().upper()
    if assignee and assignee not in AGENT_ROSTER:
        assignee = ""
    with _LOCK:
        tasks = _load()
        task = {
            "id": _next_id(tasks),
            "title": title[:200],
            "notes": (notes or "").strip()[:500],
            "assignee": assignee,
            "status": "claimed" if assignee else "open",
            "created_by": (created_by or "FRIDAY").strip().upper(),
            "created_at": _now(),
            "claimed_at": _now() if assignee else "",
            "done_at": "",
        }
        tasks.append(task)
        _save(tasks)
        return task


def list_tasks(status: str = "") -> list[dict]:
    status = (status or "").strip().lower()
    tasks = _load()
    if status in ("open", "claimed", "done"):
        return [t for t in tasks if t.get("status") == status]
    return tasks


def assign_task(task_id: str, agent: str) -> dict | None:
    agent = (agent or "").strip().upper()
    if agent not in AGENT_ROSTER:
        return None
    with _LOCK:
        tasks = _load()
        for t in tasks:
            if t.get("id") == (task_id or "").strip().upper():
                t["assignee"] = agent
                if t.get("status") == "open":
                    t["status"] = "claimed"
                    t["claimed_at"] = _now()
                _save(tasks)
                return t
    return None


def complete_task(task_id: str, done_by: str = "FRIDAY") -> dict | None:
    with _LOCK:
        tasks = _load()
        for t in tasks:
            if t.get("id") == (task_id or "").strip().upper():
                t["status"] = "done"
                t["done_at"] = _now()
                t["done_by"] = (done_by or "FRIDAY").upper()
                _save(tasks)
                return t
    return None


def claim_next_task(agent_name: str) -> dict | None:
    """DreamEngine hook: the agent picks up the oldest open (unassigned) task."""
    agent_name = (agent_name or "").strip().upper()
    if agent_name not in AGENT_ROSTER:
        return None
    with _LOCK:
        tasks = _load()
        for t in tasks:
            if t.get("status") == "open":
                t["status"] = "claimed"
                t["assignee"] = agent_name
                t["claimed_at"] = _now()
                _save(tasks)
                return t
    return None


def _fmt(t: dict) -> str:
    head = f"{t.get('id', '?')} [{t.get('status', '?').upper()}]"
    who = t.get("assignee") or "unassigned"
    return f"- {head} {t.get('title', '')} ({who})"


def open_tasks_summary(max_items: int = 4) -> str:
    tasks = [t for t in _load() if t.get("status") in ("open", "claimed")]
    if not tasks:
        return ""
    lines = ["[Open tasks on the board]"]
    for t in tasks[:max_items]:
        lines.append(_fmt(t))
    remaining = len(tasks) - max_items
    if remaining > 0:
        lines.append(f"… and {remaining} more")
    return "\n".join(lines)


# ── Tools (exposed to the Live agent FRIDAY) ─────────────────────────────

def townhall_task_add(title: str, assignee: str = "", notes: str = "") -> str:
    t = add_task(title, assignee=assignee, notes=notes)
    if t is None:
        return "[FAIL] townhall_task_add: title is required."
    who = t["assignee"] or "unassigned"
    return f"[OK] Task {t['id']} added to the board: {t['title']} ({who}). Agents will see it and may self-assign."


def townhall_task_list(status: str = "") -> str:
    tasks = list_tasks(status)
    if not tasks:
        return "Board is empty — no tasks yet. Create one with townhall_task_add."
    lines = [f"### Task board ({len(tasks)})"]
    for t in tasks:
        lines.append(_fmt(t))
    lines.append("Roster: " + ", ".join(AGENT_ROSTER))
    return "\n".join(lines)


def townhall_task_assign(task_id: str, agent: str) -> str:
    t = assign_task(task_id, agent)
    if t is None:
        return f"[FAIL] Task not found or unknown agent. Roster: {', '.join(AGENT_ROSTER)}"
    return f"[OK] {t['id']} -> {t['assignee']} ({t.get('status', '?')})"


def townhall_task_done(task_id: str) -> str:
    t = complete_task(task_id, done_by="FRIDAY")
    if t is None:
        return "[FAIL] Task not found."
    return f"[OK] {t['id']} marked done: {t['title']}"
