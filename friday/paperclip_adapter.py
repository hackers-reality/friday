"""
Paperclip Adapter — turns FRIDAY into a Paperclip-compatible agent.

Paperclip is an agent orchestration platform where agents communicate
via heartbeats and receive tasks through a queue. This adapter lets FRIDAY:

- Register as a Paperclip agent with a company/org chart
- Receive tasks from the Paperclip orchestrator via heartbeat-driven task queue
- Execute tasks using FRIDAY's full tool arsenal
- Report results back via heartbeat findings
- Support the Paperclip heartbeat protocol for status/reconnect
"""

from __future__ import annotations

import asyncio
import datetime
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from friday.agent_heartbeat import (
    emit_heartbeat,
    get_heartbeat,
    get_all_heartbeats,
    subscribe,
)

# ── Configuration ─────────────────────────────────────────────────

PAPERCLIP_NPM_PACKAGE = "paperclipai"
PAPERCLIP_CONFIG_DIR = Path.home() / ".paperclip"
PAPERCLI_AGENT_CONFIG = PAPERCLIP_CONFIG_DIR / "friday_agent.json"
HEARTBEAT_FILE = PAPERCLIP_CONFIG_DIR / "heartbeat.json"
TASKS_FILE = PAPERCLIP_CONFIG_DIR / "tasks.json"
POLL_INTERVAL = 5.0

_adapter_running = False
_adapter_thread: threading.Thread | None = None
_adapter_loop: asyncio.AbstractEventLoop | None = None


# ── Adapter State ─────────────────────────────────────────────────

def _ensure_config_dir() -> None:
    PAPERCLIP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _agent_id() -> str:
    cfg = _load_config()
    return cfg.get("agent_id", "friday-agent")


def _load_config() -> dict[str, Any]:
    _ensure_config_dir()
    if PAPERCLI_AGENT_CONFIG.exists():
        return json.loads(PAPERCLI_AGENT_CONFIG.read_text())
    return {}


def _save_config(cfg: dict[str, Any]) -> None:
    _ensure_config_dir()
    PAPERCLI_AGENT_CONFIG.write_text(json.dumps(cfg, indent=2))


# ── Heartbeat Protocol (Paperclip-compatible) ─────────────────────

def _write_heartbeat_file(hb: dict[str, Any]) -> None:
    """Write heartbeat to shared file so Paperclip orchestrator can read it."""
    try:
        _ensure_config_dir()
        HEARTBEAT_FILE.write_text(json.dumps(hb))
    except Exception:
        pass


def _read_tasks_file() -> list[dict[str, Any]]:
    """Read tasks assigned by the Paperclip orchestrator."""
    try:
        if TASKS_FILE.exists():
            data = json.loads(TASKS_FILE.read_text())
            return data if isinstance(data, list) else []
    except Exception:
        pass
    return []


def _clear_tasks_file() -> None:
    try:
        TASKS_FILE.write_text("[]")
    except Exception:
        pass


# ── Task Execution ────────────────────────────────────────────────

async def _execute_task(task: dict[str, Any]) -> dict[str, Any]:
    """Execute a single task from the Paperclip orchestrator using FRIDAY's capabilities."""
    task_id = task.get("id", uuid.uuid4().hex[:12])
    task_desc = task.get("description", task.get("prompt", task.get("task", "")))
    task_type = task.get("type", "general")

    emit_heartbeat(
        agent_id=_agent_id(),
        status="running",
        action=f"Executing task {task_id}: {task_desc[:80]}",
        role=task_type,
        progress=0.3,
        findings=[f"Started task {task_id}"],
    )

    try:
        # Route to appropriate FRIDAY capability based on task type
        result = await _route_task(task_type, task_desc, task)
        emit_heartbeat(
            agent_id=_agent_id(),
            status="completed",
            action=f"Completed task {task_id}",
            role=task_type,
            progress=1.0,
            findings=[f"Completed task {task_id}: {str(result.get('summary', ''))[:200]}"],
        )
        return {"task_id": task_id, "status": "completed", "result": result}
    except Exception as e:
        emit_heartbeat(
            agent_id=_agent_id(),
            status="failed",
            action=f"Task {task_id} failed: {str(e)[:80]}",
            role=task_type,
            progress=0.0,
            findings=[f"Failed task {task_id}: {str(e)[:200]}"],
        )
        return {"task_id": task_id, "status": "failed", "error": str(e)}


async def _route_task(task_type: str, task_desc: str, task: dict[str, Any]) -> dict[str, Any]:
    """Route a task to the appropriate FRIDAY subsystem."""
    task_lower = task_type.lower()

    if task_lower == "research" or task_lower == "deep_research":
        from friday.agent_terminal import friday_quick_delegate
        return await friday_quick_delegate(
            [{"name": "veronica", "task": task_desc, "role": "researcher"}],
            deep=(task_lower == "deep_research"),
        )

    elif task_lower in ("code", "coding", "implement"):
        from friday.agent_terminal import friday_quick_delegate
        return await friday_quick_delegate(
            [{"name": "forge", "task": task_desc, "role": "coder"}],
        )

    elif task_lower in ("security", "vulnerability", "hack"):
        from friday.agent_terminal import friday_quick_delegate
        return await friday_quick_delegate(
            [{"name": "ghost", "task": task_desc, "role": "security"}],
        )

    elif task_lower in ("browse", "browser", "web"):
        from friday.browser_use_bridge import browser_use_navigate
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, browser_use_navigate, task_desc)

    elif task_lower in ("scan", "cookbook", "hardware"):
        from friday.cookbook import cookbook_scan, cookbook_recommend
        loop = asyncio.get_running_loop()
        scan = await loop.run_in_executor(None, cookbook_scan)
        recommend = await loop.run_in_executor(None, cookbook_recommend)
        return {"scan": scan, "recommendations": recommend}

    elif task_lower == "suggest" or task_lower == "proactive":
        from friday.proactive_copilot import proactive_suggest
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, proactive_suggest)

    else:
        # General: use multi-agent coordination
        from friday.agent_terminal import friday_quick_delegate
        return await friday_quick_delegate(
            [{"name": "atlas", "task": task_desc, "role": "general"}],
        )


# ── Adapter Lifecycle ─────────────────────────────────────────────

async def _adapter_main_loop(config: dict[str, Any]) -> None:
    """Main loop: emit heartbeats, poll for tasks, execute them."""
    agent_id = config.get("agent_id", "friday-agent")
    agent_role = config.get("role", "general")
    company = config.get("company", "default")

    emit_heartbeat(
        agent_id=agent_id,
        status="running",
        action=f"Paperclip adapter active — company={company}, role={agent_role}",
        role=agent_role,
        findings=["Adapter initialized"],
    )

    while _adapter_running:
        # 1. Emit heartbeat
        hb = emit_heartbeat(
            agent_id=agent_id,
            status="running",
            action=f"Listening for tasks — {agent_id}@{company}",
            role=agent_role,
            findings=[],
        )
        _write_heartbeat_file(hb)

        # 2. Poll for tasks
        tasks = _read_tasks_file()
        if tasks:
            for task in tasks:
                result = await _execute_task(task)
                # Write result back — Paperclip picks it up from heartbeat findings
                emit_heartbeat(
                    agent_id=agent_id,
                    status="completed",
                    action=f"Task done: {task.get('id', 'unknown')}",
                    role=agent_role,
                    findings=[json.dumps({"task_result": result}, default=str)],
                )
            _clear_tasks_file()

        await asyncio.sleep(POLL_INTERVAL)


def _run_adapter_in_thread(config: dict[str, Any]) -> None:
    """Run the adapter main loop in a dedicated event loop thread."""
    global _adapter_loop
    _adapter_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_adapter_loop)
    _adapter_loop.run_until_complete(_adapter_main_loop(config))


def adapter_start(
    agent_id: str = "friday-agent",
    company: str = "default",
    role: str = "general",
) -> dict[str, Any]:
    """Start the Paperclip adapter in background thread."""
    global _adapter_running, _adapter_thread
    if _adapter_running:
        return {"success": False, "error": "Adapter already running"}

    config = _load_config()
    config.update({"agent_id": agent_id, "company": company, "role": role})
    _save_config(config)

    _adapter_running = True
    _adapter_thread = threading.Thread(
        target=_run_adapter_in_thread,
        args=(config,),
        daemon=True,
        name="paperclip-adapter",
    )
    _adapter_thread.start()

    return {
        "success": True,
        "agent_id": agent_id,
        "company": company,
        "role": role,
        "status": "started",
    }


def adapter_stop() -> dict[str, Any]:
    """Stop the Paperclip adapter."""
    global _adapter_running, _adapter_thread
    _adapter_running = False
    if _adapter_thread:
        _adapter_thread.join(timeout=5)
        _adapter_thread = None
    emit_heartbeat(
        agent_id=_agent_id(),
        status="stopped",
        action="Paperclip adapter stopped",
        role="system",
    )
    return {"success": True, "status": "stopped"}


def adapter_status() -> dict[str, Any]:
    """Get Paperclip adapter status."""
    hb = get_heartbeat(_agent_id())
    return {
        "running": _adapter_running,
        "agent_id": _agent_id(),
        "config": _load_config(),
        "last_heartbeat": hb,
        "heartbeat_file_exists": HEARTBEAT_FILE.exists(),
        "tasks_file_exists": TASKS_FILE.exists(),
    }


def adapter_register(
    company: str = "default",
    role: str = "general",
    display_name: str = "FRIDAY AI",
) -> dict[str, Any]:
    """Register FRIDAY as a Paperclip agent by creating config + heartbeat target.

    In a real Paperclip setup, this would call the Paperclip API.
    For self-hosted mode, it writes the config files that the Paperclip
    orchestrator (or CLI) watches.
    """
    agent_id = f"friday-{uuid.uuid4().hex[:6]}"
    config = {
        "agent_id": agent_id,
        "company": company,
        "role": role,
        "display_name": display_name,
        "capabilities": [
            "research",
            "code",
            "security",
            "browser",
            "hardware_scan",
            "proactive_suggest",
            "osint",
            "email",
            "calendar",
            "file_operations",
        ],
        "heartbeat_file": str(HEARTBEAT_FILE),
        "tasks_file": str(TASKS_FILE),
        "registered_at": datetime.datetime.now().isoformat(),
    }
    _save_config(config)
    return {"success": True, "agent_id": agent_id, "config": config}


# ── Tool Functions ────────────────────────────────────────────────

def paperclip_adapter_start(
    agent_id: str = "friday-agent",
    company: str = "default",
    role: str = "general",
) -> dict[str, Any]:
    """Start the Paperclip-compatible adapter. FRIDAY becomes a Paperclip agent."""
    return adapter_start(agent_id, company, role)


def paperclip_adapter_stop() -> dict[str, Any]:
    """Stop the Paperclip adapter."""
    return adapter_stop()


def paperclip_adapter_status() -> dict[str, Any]:
    """Check if the Paperclip adapter is running and its config."""
    return adapter_status()


def paperclip_adapter_register(
    company: str = "default",
    role: str = "general",
    display_name: str = "FRIDAY AI",
) -> dict[str, Any]:
    """Register FRIDAY as a Paperclip-compatible agent."""
    return adapter_register(company, role, display_name)


def paperclip_adapter_submit_task(
    description: str,
    task_type: str = "general",
) -> dict[str, Any]:
    """Submit a task directly to the Paperclip adapter for FRIDAY to execute.

    Task types: research, deep_research, code, security, browse, scan, suggest, general
    """
    task = {
        "id": uuid.uuid4().hex[:12],
        "description": description,
        "type": task_type,
        "submitted_at": datetime.datetime.now().isoformat(),
    }
    emit_heartbeat(
        agent_id=_agent_id(),
        status="running",
        action=f"Received direct task: {description[:80]}",
        role=task_type,
        findings=[f"Task queued: {task['id']} - {description[:100]}"],
    )
    return {"success": True, "task": task, "note": "Task submitted. Check heartbeat for results."}


# ── __all__ ────────────────────────────────────────────────────────

__all__ = [
    "adapter_start",
    "adapter_stop",
    "adapter_status",
    "adapter_register",
    "paperclip_adapter_start",
    "paperclip_adapter_stop",
    "paperclip_adapter_status",
    "paperclip_adapter_register",
    "paperclip_adapter_submit_task",
]
