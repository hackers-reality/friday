"""
FRIDAY Base Agent — stateless abstract agent following OpenHands
Action-Execution-Observation pattern. Each agent has no instance state
between calls; all state flows through AgentTask context_snapshot.

Agents emit events to context_bus.py on start, progress, completion.
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AgentTask:
    """A unit of work for an agent. Stateless — all context in snapshot."""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str = "general"
    payload: str = ""
    context_snapshot: dict[str, Any] = field(default_factory=dict)
    requester: str = "user"
    max_tokens: int = 4096
    temperature: float = 0.7


@dataclass
class AgentResult:
    """Result of an agent execution."""

    task_id: str = ""
    agent_id: str = ""
    status: str = "pending"  # pending | running | completed | failed
    output: str = ""
    error: str = ""
    duration_ms: int = 0
    tokens_used: dict[str, int] = field(default_factory=dict)
    model: str = ""


@dataclass
class AgentDef:
    """Agent definition loaded from config.yaml agents[]."""

    id: str = ""
    name: str = ""
    task_types: list[str] = field(default_factory=list)
    nim_model: str = ""
    tools: list[str] = field(default_factory=list)
    enabled: bool = False
    system_prompt: str = ""


class BaseAgent(ABC):
    """
    Abstract base for all FRIDAY agents.

    Stateless per OpenHands pattern: no instance state between execute() calls.
    All context flows through AgentTask.context_snapshot.

    Subclasses implement:
      - execute(task) -> AgentResult
    """

    def __init__(self, defn: AgentDef):
        self.id = defn.id
        self.name = defn.name
        self.task_types = defn.task_types
        self.nim_model = defn.nim_model
        self.tools = defn.tools
        self.system_prompt = defn.system_prompt or self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        return (
            f"You are {self.name}, a specialist FRIDAY agent. "
            f"Your task types: {', '.join(self.task_types)}. "
            f"Available tools: {', '.join(self.tools)}. "
            "Complete the assigned task and return a clear result."
        )

    @abstractmethod
    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute a task and return the result."""
        ...

    def _make_result(self, task: AgentTask, status: str, output: str = "",
                     error: str = "", duration_ms: int = 0,
                     tokens: Optional[dict] = None, model: str = "") -> AgentResult:
        return AgentResult(
            task_id=task.task_id,
            agent_id=self.id,
            status=status,
            output=output,
            error=error,
            duration_ms=duration_ms,
            tokens_used=tokens or {},
            model=model or self.nim_model,
        )
