"""Abstract base types for Friday's multi-agent orchestration layer.

The orchestration system treats agents as stateless workers: every call
gets a fresh task payload and emits progress onto the context bus.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from time import monotonic
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class AgentTask:
    """A unit of work sent to an agent."""

    task_id: str
    task_type: str
    payload: Dict[str, Any]
    context_snapshot: Dict[str, Any]
    requester: str


@dataclass(slots=True)
class AgentResult:
    """Result emitted by an agent after execution."""

    task_id: str
    agent_id: str
    status: str
    output: str
    error: Optional[str]
    duration_ms: int
    tokens_used: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain dictionary for serialization."""
        return asdict(self)


class BaseAgent(ABC):
    """Abstract base class for stateless Friday agents."""

    def __init__(
        self,
        agent_id: str,
        display_name: str,
        task_types: List[str],
        tools: List[str],
        nim_model: str,
    ) -> None:
        self.agent_id = agent_id
        self.display_name = display_name
        self.task_types = list(task_types)
        self.tools = list(tools)
        self.nim_model = nim_model

    @abstractmethod
    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute a task and return a structured result."""

    async def emit_event(self, bus: Any, topic_suffix: str, payload: Dict[str, Any]) -> None:
        """Emit an event to the provided bus if one is available."""
        if bus is None:
            return
        topic = f"agent.{self.agent_id}.{topic_suffix}"
        await bus.publish(topic, payload)

    @staticmethod
    def elapsed_ms(start_mark: float) -> int:
        """Convert a monotonic start mark into milliseconds."""
        return int((monotonic() - start_mark) * 1000)
