"""
FRIDAY Agent-Use Bridge — unified multi-agent orchestration API.
Parallel to browser_use_bridge.py, desktop_use_bridge.py, voice_use_bridge.py.

Provides: spawn, delegate, track, list agents, run complete workflows.
All sync on the surface (async internals run in background thread).
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any

from friday._paths import FRIDAY_MEMORY
from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

_STATE_PATH = os.path.join(FRIDAY_MEMORY, "agent_use_state.json")


def _load_state() -> dict:
    if os.path.exists(_STATE_PATH):
        try:
            with open(_STATE_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"total_delegations": 0, "workflows_run": 0, "active_agents": 0}


def _save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
    with open(_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def _has_agent_terminal():
    try:
        from friday.agent_terminal import AgentTerminalManager
        return True
    except ImportError:
        return False


def _has_orchestrator():
    try:
        from friday.orchestrator import Orchestrator
        return True
    except ImportError:
        return False


def _has_agent_heartbeat():
    try:
        from friday.agent_heartbeat import get_all_heartbeats
        return True
    except ImportError:
        return False


# ── Public API ────────────────────────────────────────────────

def agent_use_status() -> str:
    """Check the multi-agent system health and available components."""
    backends = {
        "agent_terminal": _has_agent_terminal(),
        "orchestrator": _has_orchestrator(),
        "heartbeat": _has_agent_heartbeat(),
    }
    state = _load_state()
    active = []
    if backends["heartbeat"]:
        try:
            from friday.agent_heartbeat import get_all_heartbeats
            hb = get_all_heartbeats()
            if isinstance(hb, dict):
                active = list(hb.keys())
        except Exception:
            pass
    return json.dumps({
        "available": any(backends.values()),
        "backends": backends,
        "active_agents": active,
        "total_delegations": state["total_delegations"],
        "workflows_run": state["workflows_run"],
    }, indent=2)


def agent_use_list_agents() -> str:
    """List all available agent profiles."""
    try:
        from friday.agent_profiles import list_agents
        profiles = list_agents()
        return json.dumps({"agents": profiles, "count": len(profiles)}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def agent_use_spawn(name: str, task: str, role: str = "general") -> str:
    """Spawn a new agent with a terminal window to work on a task."""
    state = _load_state()
    try:
        import asyncio
        from friday.agent_terminal import agent_spawn_and_track
        result = asyncio.run(agent_spawn_and_track(name, task, role))
        state["total_delegations"] += 1
        state["active_agents"] += 1
        _save_state(state)
        if isinstance(result, str):
            try:
                return json.dumps({"success": True, "result": json.loads(result)}, indent=2)
            except Exception:
                return json.dumps({"success": True, "result": result[:500]}, indent=2)
        return json.dumps({"success": True, "agent": name, "role": role, "task": task[:200]}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def agent_use_delegate(task_description: str, role: str = "") -> str:
    """Delegate a task to the best-matching agent using the delegator."""
    state = _load_state()
    try:
        import asyncio
        from friday.agent_terminal import friday_should_delegate, friday_quick_delegate
        should = friday_should_delegate(task_description)
        if not should:
            return json.dumps({"success": True, "delegated": False, "reason": "Task too simple for delegation"}, indent=2)
        if role:
            tasks = [{"agent": role, "task": task_description}]
        else:
            tasks = [{"task": task_description}]
        result = asyncio.run(friday_quick_delegate(tasks, deep=False))
        state["total_delegations"] += 1
        _save_state(state)
        if isinstance(result, str):
            try:
                return json.dumps({"success": True, "result": json.loads(result)}, indent=2)
            except Exception:
                return json.dumps({"success": True, "result": str(result)[:500]}, indent=2)
        return json.dumps({"success": True, "task": task_description[:200]}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def agent_use_workflow(task_description: str) -> str:
    """Run a complete multi-step workflow (research -> analyze -> produce result)."""
    state = _load_state()
    try:
        import asyncio
        from friday.workflow import create_and_run_workflow
        result = asyncio.run(create_and_run_workflow(task_description))
        state["workflows_run"] += 1
        _save_state(state)
        if isinstance(result, str):
            try:
                return json.dumps({"success": True, "result": json.loads(result)}, indent=2)
            except Exception:
                return json.dumps({"success": True, "result": str(result)[:500]}, indent=2)
        return json.dumps({"success": True, "task": task_description[:200]}, indent=2)
    except Exception as e:
        # fallback: try multi-agent task
        try:
            import asyncio
            from friday.agent_terminal import friday_multi_agent_task
            result = asyncio.run(friday_multi_agent_task(task_description))
            state["workflows_run"] += 1
            _save_state(state)
            return json.dumps({"success": True, "fallback": "multi_agent", "task": task_description[:200]}, indent=2)
        except Exception as e2:
            return json.dumps({"error": f"workflow: {e}, fallback: {e2}"})


def agent_use_kill(name: str) -> str:
    """Kill a running agent by name."""
    try:
        from friday.agent_terminal import AgentTerminalManager
        mgr = AgentTerminalManager()
        mgr.close_agent_terminal(name)
        state = _load_state()
        state["active_agents"] = max(0, state["active_agents"] - 1)
        _save_state(state)
        return json.dumps({"success": True, "killed": name}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def agent_use_heartbeats() -> str:
    """Get all current agent heartbeats."""
    try:
        from friday.agent_heartbeat import get_all_heartbeats
        hb = get_all_heartbeats()
        if isinstance(hb, dict):
            summary = {aid: {"status": h.get("status", "unknown"), "role": h.get("role", ""), "action": str(h.get("action", ""))[:100]} for aid, h in hb.items()}
            return json.dumps({"heartbeats": summary, "count": len(summary)}, indent=2)
        return json.dumps({"heartbeats": {}, "count": 0}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
