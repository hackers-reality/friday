"""
High-level agent management for FRIDAY.
FRIDAY calls these tools: "spawn X", "delegate to Y", "what are my agents doing"
"""

from friday.opencode_bridge import OpencodeBridge, SubAgent
from datetime import datetime

_manager = None

def get_manager():
    global _manager
    if _manager is None:
        _manager = OpencodeBridge()
    return _manager

def _format_agent(agent: SubAgent) -> dict:
    """Format an agent with full detail for the dashboard."""
    now = datetime.now()
    created = datetime.fromisoformat(agent.created_at) if agent.created_at else now
    completed = datetime.fromisoformat(agent.completed_at) if agent.completed_at else None
    elapsed = (completed - created).total_seconds() if completed else (now - created).total_seconds()

    return {
        "name": agent.name,
        "id": agent.id,
        "role": getattr(agent, "role", "general"),
        "status": agent.status,
        "task": agent.task,
        "result": agent.result,
        "current_step": getattr(agent, "current_step", None),
        "steps_completed": getattr(agent, "steps_completed", None),
        "total_steps": getattr(agent, "total_steps", None),
        "thought_process": getattr(agent, "thought_process", []),
        "created_at": agent.created_at,
        "completed_at": agent.completed_at,
        "is_running": agent.status == "running",
        "elapsed_seconds": round(elapsed),
    }

def spawn_agent(name: str, task: str, role: str = "general") -> dict:
    """Spawn a named agent for a task. FRIDAY's entry point."""
    # Prefer the orchestrator if available for configured agents
    try:
        from friday.orchestrator import get_orchestrator, run_delegate_sync
        from friday.agent_registry import get_registry
        registry = get_registry()
        profile = registry.get_by_id(name) or registry.get_by_name(name)
        if profile:
            # Delegate via orchestrator (non-blocking if event loop present)
            result = run_delegate_sync(task, context={"requester": "agents_manager", "role": role}, preferred_agent=profile.agent_id)
            return {"name": profile.display_name, "id": profile.agent_id, "role": role, "status": "scheduled", "message": "Delegated via orchestrator", "result": result}
    except Exception:
        # Fall through to legacy OpencodeBridge
        pass

    bridge = get_manager()
    try:
        agent = bridge.spawn_agent(name, task)
        agent.role = role
        return {
            "name": agent.name,
            "id": agent.id,
            "role": role,
            "status": agent.status,
            "message": f"Agent '{name}' ({role}) spawned and working on task.",
        }
    except Exception as e:
        return {"error": f"Failed to spawn agent via OpencodeBridge: {e}"}

def delegate(name: str, task: str) -> dict:
    """Delegate a task to an existing or new agent."""
    return spawn_agent(name, task)

def list_agents() -> list[dict]:
    """List all agents with full detail for the dashboard."""
    bridge = get_manager()
    return [_format_agent(a) for a in bridge.agents.values()]

def agent_status(name: str) -> dict:
    """Get a specific agent's status."""
    bridge = get_manager()
    for agent in bridge.agents.values():
        if agent.name.lower() == name.lower():
            return _format_agent(agent)
    return {"error": f"Agent '{name}' not found"}

def spawn_team(tasks: list[tuple[str, str]]) -> list[dict]:
    """Spawn multiple agents in parallel for a team effort."""
    bridge = get_manager()
    agents = bridge.spawn_parallel(tasks)
    return [_format_agent(a) for a in agents]
