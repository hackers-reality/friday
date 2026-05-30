"""
Agent Communication Bus — allows spawned agents to communicate with each other
and with the main FRIDAY instance.

Pattern: publish/subscribe message bus where agents can:
- Publish results (e.g., "research_agent publishes its findings")
- Subscribe to events (e.g., "code_agent waits for research_agent.result")
- Query agent status
"""
from __future__ import annotations

import asyncio
import datetime
import json
import uuid
from typing import Any, Callable

# In-memory message store
_agent_messages: dict[str, list[dict[str, Any]]] = {}  # agent_id -> messages
_subscribers: dict[str, list[Callable]] = {}  # topic -> callbacks
_agent_results: dict[str, dict[str, Any]] = {}  # task_id -> result
_agent_errors: dict[str, str] = {}  # task_id -> error

# Events that agents can wait on
_agent_events: dict[str, asyncio.Event] = {}  # task_id -> event


async def publish(agent_id: str, topic: str, data: Any, task_id: str | None = None) -> dict[str, Any]:
    """Publish a message from an agent to a topic."""
    msg_id = f"msg_{uuid.uuid4().hex[:10]}"
    msg = {
        "id": msg_id,
        "agent_id": agent_id,
        "topic": topic,
        "data": data,
        "task_id": task_id,
        "timestamp": datetime.datetime.now().isoformat(),
    }
    if agent_id not in _agent_messages:
        _agent_messages[agent_id] = []
    _agent_messages[agent_id].append(msg)

    # If this is a result, store it and set event
    if topic.endswith(".result") and task_id:
        _agent_results[task_id] = {"agent_id": agent_id, "data": data, "timestamp": msg["timestamp"]}
        if task_id in _agent_events:
            _agent_events[task_id].set()

    # If this is an error, store it
    if topic.endswith(".error") and task_id:
        _agent_errors[task_id] = str(data)
        if task_id in _agent_events:
            _agent_events[task_id].set()

    # Notify subscribers
    if topic in _subscribers:
        for cb in _subscribers[topic]:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(msg)
                else:
                    cb(msg)
            except Exception:
                pass

    return msg


async def subscribe(topic: str, callback: Callable) -> None:
    """Subscribe to a topic. Callback receives message dict."""
    if topic not in _subscribers:
        _subscribers[topic] = []
    _subscribers[topic].append(callback)


def unsubscribe(topic: str, callback: Callable) -> None:
    if topic in _subscribers:
        _subscribers[topic] = [cb for cb in _subscribers[topic] if cb is not callback]


async def wait_for_result(task_id: str, timeout: float = 300.0) -> dict[str, Any] | None:
    """Wait for a task to complete and return its result."""
    if task_id in _agent_results:
        return _agent_results[task_id]

    if task_id not in _agent_events:
        _agent_events[task_id] = asyncio.Event()

    try:
        await asyncio.wait_for(_agent_events[task_id].wait(), timeout=timeout)
    except asyncio.TimeoutError:
        return None

    return _agent_results.get(task_id)


def get_agent_messages(agent_id: str, limit: int = 50) -> list[dict[str, Any]]:
    return (_agent_messages.get(agent_id) or [])[-limit:]


def get_all_messages(limit: int = 100) -> list[dict[str, Any]]:
    all_msgs = []
    for msgs in _agent_messages.values():
        all_msgs.extend(msgs)
    all_msgs.sort(key=lambda m: m["timestamp"])
    return all_msgs[-limit:]


def get_task_status(task_id: str) -> dict[str, Any]:
    result = _agent_results.get(task_id)
    error = _agent_errors.get(task_id)
    if result:
        return {"task_id": task_id, "status": "completed", "result": result}
    if error:
        return {"task_id": task_id, "status": "failed", "error": error}
    return {"task_id": task_id, "status": "running"}


def clear_agent_state(agent_id: str | None = None):
    if agent_id:
        _agent_messages.pop(agent_id, None)
    else:
        _agent_messages.clear()
        _agent_results.clear()
        _agent_errors.clear()
        _agent_events.clear()
