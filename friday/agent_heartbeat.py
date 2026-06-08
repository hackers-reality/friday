"""
Agent Heartbeat Protocol — Paperclip-inspired real-time agent status broadcasting.

Every running agent emits heartbeats at a configurable interval with:
- agent_id, status (spawning/running/completed/failed), current action
- findings discovered so far (for cross-agent reactivity)
- memory/context summary

A background daemon tracks all heartbeats. Other agents can:
- Subscribe to specific agent types (researcher, coder, etc.)
- Trigger cross-agent reactions (researcher finds X → coder gets notified)
- Query current state of any agent
"""

from __future__ import annotations

import asyncio
import datetime
import json
import threading
import time
import uuid
from typing import Any, Callable

# ── In-memory heartbeat store ─────────────────────────────────────

_heartbeats: dict[str, dict[str, Any]] = {}
_heartbeat_history: dict[str, list[dict[str, Any]]] = {}
_subscribers: dict[str, list[Callable]] = {}
_cross_agent_triggers: dict[str, list[dict[str, Any]]] = {}
_daemon_running = False
_daemon_loop: asyncio.AbstractEventLoop | None = None
_heartbeat_lock = threading.Lock()
DEFAULT_INTERVAL = 15.0
MAX_HISTORY = 100


# ── Heartbeat CRUD ────────────────────────────────────────────────

def emit_heartbeat(
    agent_id: str,
    status: str = "running",
    action: str = "",
    findings: list[str] | None = None,
    role: str = "general",
    progress: float = 0.0,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record a heartbeat for an agent. Thread-safe."""
    now = time.time()
    hb = {
        "agent_id": agent_id,
        "status": status,
        "action": action,
        "findings": findings or [],
        "role": role,
        "progress": progress,
        "metadata": metadata or {},
        "timestamp": now,
        "timestamp_iso": datetime.datetime.now().isoformat(),
        "heartbeat_id": uuid.uuid4().hex[:12],
    }
    with _heartbeat_lock:
        _heartbeats[agent_id] = hb
        if agent_id not in _heartbeat_history:
            _heartbeat_history[agent_id] = []
        _heartbeat_history[agent_id].append(hb)
        if len(_heartbeat_history[agent_id]) > MAX_HISTORY:
            _heartbeat_history[agent_id] = _heartbeat_history[agent_id][-MAX_HISTORY:]

    # Notify subscribers for this agent or role or wildcard
    _notify_sync("agent." + agent_id, hb)
    _notify_sync("role." + role, hb)
    _notify_sync("heartbeat.*", hb)

    # Check cross-agent triggers
    _check_triggers(agent_id, role, findings or [], hb)

    return hb


def get_heartbeat(agent_id: str) -> dict[str, Any] | None:
    with _heartbeat_lock:
        return _heartbeats.get(agent_id)


def get_all_heartbeats() -> dict[str, dict[str, Any]]:
    with _heartbeat_lock:
        return dict(_heartbeats)


def get_heartbeat_history(agent_id: str, limit: int = 20) -> list[dict[str, Any]]:
    with _heartbeat_lock:
        return (_heartbeat_history.get(agent_id) or [])[-limit:]


def clear_heartbeat(agent_id: str) -> None:
    with _heartbeat_lock:
        _heartbeats.pop(agent_id, None)


def clear_all_heartbeats() -> None:
    with _heartbeat_lock:
        _heartbeats.clear()
        _heartbeat_history.clear()


# ── Subscription ──────────────────────────────────────────────────

def subscribe(topic: str, callback: Callable) -> None:
    """Subscribe to a heartbeat topic.

    Topics:
        agent.<agent_id>  — heartbeats from a specific agent
        role.<role>       — heartbeats from agents of a role
        heartbeat.*       — all heartbeats
    """
    if topic not in _subscribers:
        _subscribers[topic] = []
    _subscribers[topic].append(callback)


def unsubscribe(topic: str, callback: Callable) -> None:
    if topic in _subscribers:
        _subscribers[topic] = [cb for cb in _subscribers[topic] if cb is not callback]


def _notify_sync(topic: str, hb: dict[str, Any]) -> None:
    """Synchronously notify subscribers of a topic."""
    for cb in _subscribers.get(topic, []):
        try:
            cb(hb)
        except Exception:
            pass


async def _notify_async(topic: str, hb: dict[str, Any]) -> None:
    for cb in _subscribers.get(topic, []):
        try:
            if asyncio.iscoroutinefunction(cb):
                await cb(hb)
            else:
                cb(hb)
        except Exception:
            pass


# ── Cross-Agent Triggers ──────────────────────────────────────────

def add_trigger(
    trigger_id: str,
    source_role: str,
    keyword: str,
    target_agent: str,
    target_task_template: str,
) -> dict[str, Any]:
    """Register a cross-agent trigger.

    When an agent of source_role emits a finding containing keyword,
    a task is created for target_agent using target_task_template
    (which can contain {finding} and {source_agent} placeholders).
    """
    trigger = {
        "trigger_id": trigger_id,
        "source_role": source_role,
        "keyword": keyword.lower(),
        "target_agent": target_agent,
        "target_task_template": target_task_template,
        "enabled": True,
    }
    if source_role not in _cross_agent_triggers:
        _cross_agent_triggers[source_role] = []
    _cross_agent_triggers[source_role].append(trigger)
    return trigger


def remove_trigger(trigger_id: str) -> bool:
    for role in list(_cross_agent_triggers.keys()):
        _cross_agent_triggers[role] = [
            t for t in _cross_agent_triggers[role] if t["trigger_id"] != trigger_id
        ]
        if not _cross_agent_triggers[role]:
            del _cross_agent_triggers[role]
    return True


def list_triggers() -> dict[str, list[dict[str, Any]]]:
    return dict(_cross_agent_triggers)


def _check_triggers(
    agent_id: str, role: str, findings: list[str], hb: dict[str, Any]
) -> None:
    """Check if any triggers match the given agent's findings."""
    triggers = _cross_agent_triggers.get(role, [])
    if not triggers:
        return

    findings_lower = [f.lower() for f in findings]
    for trigger in triggers:
        if not trigger.get("enabled", True):
            continue
        keyword = trigger["keyword"]
        matched = any(keyword in f for f in findings_lower)
        if matched:
            try:
                task = trigger["target_task_template"].format(
                    finding=findings[0] if findings else "",
                    source_agent=agent_id,
                )
                _fire_trigger(trigger["target_agent"], task, trigger["trigger_id"])
            except Exception:
                pass


def _fire_trigger(target_agent: str, task: str, trigger_id: str) -> None:
    """Fire a trigger by publishing a cross-agent event."""
    event = {
        "trigger_id": trigger_id,
        "target_agent": target_agent,
        "task": task,
        "timestamp": datetime.datetime.now().isoformat(),
        "event_id": uuid.uuid4().hex[:12],
    }
    _notify_sync("trigger." + target_agent, event)
    _notify_sync("trigger.*", event)


# ── Background Heartbeat Daemon ───────────────────────────────────

async def heartbeat_daemon_start(interval: float = DEFAULT_INTERVAL) -> None:
    """Start the background heartbeat daemon.

    The daemon periodically emits a "daemon.alive" heartbeat so subscribers
    know the system is running, and prunes stale heartbeats.
    """
    global _daemon_running, _daemon_loop
    if _daemon_running:
        return
    _daemon_running = True
    _daemon_loop = asyncio.get_running_loop()
    while _daemon_running:
        emit_heartbeat(
            agent_id="__daemon__",
            status="running",
            action=f"Monitoring {len(_heartbeats)} agents",
            role="system",
        )
        # Prune stale heartbeats (older than 5 minutes)
        now = time.time()
        stale = [aid for aid, hb in _heartbeats.items()
                 if aid != "__daemon__" and now - hb["timestamp"] > 300]
        for aid in stale:
            with _heartbeat_lock:
                _heartbeats.pop(aid, None)
        await asyncio.sleep(interval)


async def heartbeat_daemon_stop() -> None:
    global _daemon_running
    _daemon_running = False


def heartbeat_daemon_status() -> dict[str, Any]:
    return {
        "running": _daemon_running,
        "agents_tracked": len([a for a in _heartbeats if a != "__daemon__"]),
        "stale_threshold_seconds": 300,
        "heartbeat_interval_seconds": DEFAULT_INTERVAL,
    }


# ── Cross-Agent Message Router ────────────────────────────────────

async def route_finding_to_agent(
    source_agent_id: str,
    finding: str,
    target_agent_id: str,
    task_description: str,
) -> dict[str, Any]:
    """Route a finding from one agent to another as a new task.

    This is the Paperclip-style reactive handoff: when agent A discovers X,
    FRIDAY spawns a task for agent B to process it.
    """
    enriched_task = f"[Cross-agent handoff from {source_agent_id}]\n{task_description}\n\nFinding: {finding}"
    from friday.agent_terminal import friday_quick_delegate

    result = await friday_quick_delegate([
        {"name": target_agent_id, "task": enriched_task, "role": "general"},
    ])
    emit_heartbeat(
        agent_id="__router__",
        status="completed" if result.get("success") else "failed",
        action=f"Routed finding from {source_agent_id} to {target_agent_id}",
        findings=[f"Routed: {finding[:100]}"],
        role="system",
    )
    return result


# ── Tool Functions ────────────────────────────────────────────────

def agent_heartbeat_status() -> dict[str, Any]:
    """Get current status of all agents via heartbeat protocol."""
    hbs = get_all_heartbeats()
    return {
        "agents": {
            aid: {
                "status": hb["status"],
                "action": hb["action"],
                "role": hb["role"],
                "progress": hb["progress"],
                "findings": hb.get("findings", []),
                "last_seen": hb["timestamp_iso"],
            }
            for aid, hb in hbs.items()
            if aid != "__daemon__"
        },
        "daemon": heartbeat_daemon_status(),
        "count": len([a for a in hbs if a != "__daemon__"]),
    }


def agent_heartbeat_get(agent_id: str) -> dict[str, Any] | None:
    """Get heartbeat for a specific agent."""
    hb = get_heartbeat(agent_id)
    if not hb:
        return None
    return {
        "agent_id": hb["agent_id"],
        "status": hb["status"],
        "action": hb["action"],
        "role": hb["role"],
        "progress": hb["progress"],
        "findings": hb.get("findings", []),
        "last_seen": hb["timestamp_iso"],
    }


def agent_heartbeat_add_trigger(
    trigger_id: str,
    source_role: str,
    keyword: str,
    target_agent: str,
    target_task_template: str,
) -> dict[str, Any]:
    """Add a cross-agent trigger: when source_role finds keyword, spawn task for target_agent."""
    return add_trigger(trigger_id, source_role, keyword, target_agent, target_task_template)


def agent_heartbeat_remove_trigger(trigger_id: str) -> dict[str, Any]:
    """Remove a cross-agent trigger."""
    ok = remove_trigger(trigger_id)
    return {"success": ok, "trigger_id": trigger_id}


def agent_heartbeat_list_triggers() -> dict[str, Any]:
    """List all registered cross-agent triggers."""
    return {"triggers": list_triggers()}


def agent_heartbeat_route_finding(
    source_agent_id: str,
    finding: str,
    target_agent_id: str,
    task_description: str,
) -> dict[str, Any]:
    """Route a finding from one agent to another as a new task."""
    import asyncio
    loop = asyncio.get_running_loop()
    return asyncio.run_coroutine_threadsafe(
        route_finding_to_agent(source_agent_id, finding, target_agent_id, task_description),
        loop,
    )


# ── Helpers ───────────────────────────────────────────────────────

def emit_agent_heartbeat(
    agent_id: str,
    status: str = "running",
    action: str = "",
    findings: list[str] | None = None,
    role: str = "general",
    progress: float = 0.0,
) -> dict[str, Any]:
    """Convenience wrapper for agents to emit their own heartbeat."""
    return emit_heartbeat(agent_id, status, action, findings, role, progress)


# ── __all__ ────────────────────────────────────────────────────────

__all__ = [
    "emit_heartbeat",
    "emit_agent_heartbeat",
    "get_heartbeat",
    "get_all_heartbeats",
    "get_heartbeat_history",
    "clear_heartbeat",
    "clear_all_heartbeats",
    "subscribe",
    "unsubscribe",
    "add_trigger",
    "remove_trigger",
    "list_triggers",
    "heartbeat_daemon_start",
    "heartbeat_daemon_stop",
    "heartbeat_daemon_status",
    "route_finding_to_agent",
    "agent_heartbeat_status",
    "agent_heartbeat_get",
    "agent_heartbeat_add_trigger",
    "agent_heartbeat_remove_trigger",
    "agent_heartbeat_list_triggers",
    "agent_heartbeat_route_finding",
]
