"""
FRIDAY Orchestrator — delegates tasks to agents, supports parallel execution,
APScheduler for background tasks, and live status tracking.

Core patterns:
  - delegate(utterance) -> AgentResult  (single agent)
  - delegate_parallel(utterances) -> list[AgentResult]
  - parse_and_route(utterance, known_agents) -> asyncio.gather
  - background_schedule(agent_id, cron, task_payload)
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from friday.agent_registry import AgentRegistry
from friday.base_agent import AgentDef, AgentTask, AgentResult
from friday.context_bus import ContextBus
from friday.name_resolver import resolve, extract_mentions
from friday.nim_client import InferenceClient
from friday.nim_router import resolve_model, classify_task_type


@dataclass
class LiveStatus:
    """Current status of a running agent."""

    agent_id: str
    task_id: str = ""
    task_type: str = ""
    state: str = "idle"  # idle | queued | running | completed | failed
    progress_pct: int = 0
    current_action: str = ""
    started_at: float = 0.0
    duration_ms: int = 0


class NimAgentExecutor:
    """
    A minimal Agent that delegates to InferenceClient for actual LLM inference.
    Used by Orchestrator for agents that don't have a custom subclass.
    """

    def __init__(self, defn: AgentDef, client: InferenceClient, bus: ContextBus):
        self.defn = defn
        self._client = client
        self._bus = bus

    async def execute(self, task: AgentTask) -> AgentResult:
        await self._bus.publish("agent.started", {
            "agent_id": self.defn.id,
            "task_id": task.task_id,
            "task_type": task.task_type,
        })
        t0 = time.monotonic()
        model = task.context_snapshot.get("nim_model", self.defn.nim_model) or \
                resolve_model(task.task_type) or "meta/llama-3.3-70b-instruct"
        messages = [{"role": "system", "content": self.defn.system_prompt}]
        messages.append({"role": "user", "content": task.payload})
        try:
            result = await self._client.chat(model=model, messages=messages,
                                             max_tokens=task.max_tokens,
                                             temperature=task.temperature)
            status = "completed" if "error" not in result.content.lower() else "failed"
            dur = result.duration_ms
            await self._bus.publish(f"agent.{status}", {
                "agent_id": self.defn.id,
                "task_id": task.task_id,
                "output": result.content,
                "duration_ms": dur,
            })
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.defn.id,
                status=status,
                output=result.content,
                duration_ms=dur,
                tokens_used=result.usage,
                model=result.model,
            )
        except Exception as e:
            dur = int((time.monotonic() - t0) * 1000)
            await self._bus.publish("agent.failed", {
                "agent_id": self.defn.id,
                "task_id": task.task_id,
                "error": str(e),
            })
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.defn.id,
                status="failed",
                error=str(e),
                duration_ms=dur,
            )


class Orchestrator:
    """
    Central orchestration engine for FRIDAY multi-agent system.

    Usage:
        orch = Orchestrator(registry, client, bus)
        await orch.init()

        # One agent
        result = await orch.delegate("Veronica", "research quantum computing")

        # Multiple in parallel (auto-routed)
        results = await orch.parse_and_route("research and write code for quantum sim")
    """

    def __init__(self, registry: AgentRegistry, client: InferenceClient, bus: ContextBus):
        self.reg = registry
        self._client = client
        self._bus = bus
        self._scheduler = AsyncIOScheduler()
        self._executors: dict[str, NimAgentExecutor] = {}
        self._statuses: dict[str, LiveStatus] = {}
        self._initialized = False

    async def init(self):
        """Load agents, build executors, start scheduler."""
        if self._initialized:
            return
        if not self.reg.loaded:
            await self.reg.load()
        for defn in self.reg.list_all(enabled_only=True):
            self._executors[defn.id] = NimAgentExecutor(defn, self._client, self._bus)
            self._statuses[defn.id] = LiveStatus(agent_id=defn.id, state="idle")
        self._scheduler.start()
        self._initialized = True

    # ── Single delegation ────────────────────────────────────

    async def delegate(self, agent_name: str, payload: str, task_type: str = "",
                       **overrides) -> AgentResult:
        """Delegate a single task to a named agent. Returns AgentResult."""
        agents = self.reg.list_all(enabled_only=True)
        defn = resolve(agent_name, agents)
        if defn is None:
            return AgentResult(
                agent_id="orchestrator", status="failed",
                error=f"Unknown or disabled agent: {agent_name}. "
                      f"Available: {[a.name for a in agents]}",
            )

        task_type = task_type or classify_task_type(payload)
        task = AgentTask(
            task_type=task_type,
            payload=payload,
            context_snapshot={"nim_model": defn.nim_model, **overrides},
        )
        self._statuses[defn.id].state = "running"
        self._statuses[defn.id].task_id = task.task_id
        self._statuses[defn.id].task_type = task_type
        self._statuses[defn.id].started_at = time.time()

        executor = self._executors.get(defn.id)
        if not executor:
            return AgentResult(
                agent_id=defn.id, status="failed",
                error=f"No executor found for {defn.id}",
            )
        result = await executor.execute(task)
        self._statuses[defn.id].duration_ms = result.duration_ms
        self._statuses[defn.id].state = result.status  # completed | failed
        return result

    # ── Parallel delegation ──────────────────────────────────

    async def delegate_parallel(self, tasks: list[tuple[str, str, str]]) -> list[AgentResult]:
        """
        Delegate multiple (agent_name, payload, task_type) tuples in parallel.
        Returns results in same order.
        """
        coros = [self.delegate(name, payload, tt) for name, payload, tt in tasks]
        return await asyncio.gather(*coros)

    # ── Parse-and-route from user utterance ──────────────────

    async def parse_and_route(self, utterance: str) -> list[AgentResult]:
        """
        Parse a natural-language utterance to extract agent mentions,
        then delegate to matched agents in parallel.

        Examples:
          "ask Veronica to research quantum computing"
          "delegate to Forge: write a REST API"
          "help me debug this code (Veronica analyze, Forge fix)"
        """
        agents = self.reg.list_all(enabled_only=True)
        mentions = extract_mentions(utterance)
        resolved: dict[str, AgentDef] = {}
        for m in mentions:
            match = resolve(m, agents)
            if match:
                resolved[m] = match

        if not resolved:
            # No agent mentioned — use task type routing
            tt = classify_task_type(utterance)
            matched = self.reg.get_by_task_type(tt)
            if matched:
                for defn in matched[:1]:  # use first match
                    resolved[defn.name] = defn

        if not resolved:
            return [AgentResult(
                agent_id="orchestrator", status="failed",
                error=f"No matching agents found for: {utterance}. "
                      f"Available: {[a.name for a in agents]}",
            )]

        tasks = [(defn.name, utterance, defn.task_types[0] if defn.task_types else "general")
                 for _, defn in resolved.items()]
        return await self.delegate_parallel(tasks)

    # ── Status ───────────────────────────────────────────────

    def status(self, agent_id: Optional[str] = None) -> dict[str, LiveStatus]:
        """Return live status for all agents or a single agent."""
        if agent_id:
            return {agent_id: self._statuses.get(agent_id, LiveStatus(agent_id=agent_id))}
        return dict(self._statuses)

    def status_summary(self) -> str:
        """Human-readable status summary."""
        parts = []
        for sid, st in self._statuses.items():
            state_icon = {"idle": "⚪", "running": "🔄", "completed": "✅", "failed": "❌"}.get(st.state, "⚪")
            extra = f" ({st.current_action})" if st.current_action else ""
            parts.append(f"{state_icon} **{sid}**: {st.state}{extra}")
        return "\n".join(parts) if parts else "No agents registered."

    # ── Background scheduling ────────────────────────────────

    def schedule(self, agent_id: str, cron: str, payload: str, task_type: str = "general"):
        """
        Schedule a recurring task for an agent via APScheduler.

        Args:
            agent_id: Agent id from config.yaml
            cron: cron expression e.g. "0 */6 * * *" (every 6 hours)
            payload: task payload string
            task_type: optional task type override
        """
        defn = self.reg.get_by_id(agent_id)
        if not defn:
            raise ValueError(f"Unknown agent: {agent_id}")
        if not defn.enabled:
            raise ValueError(f"Agent {agent_id} is disabled")

        async def job():
            await self.delegate(agent_id, payload, task_type)

        self._scheduler.add_job(job, "cron", id=f"{agent_id}_scheduled", cron=cron,
                                replace_existing=True)

    def list_scheduled_jobs(self) -> list[dict]:
        """Return list of scheduled jobs."""
        return [
            {"id": j.id, "next_run": str(j.next_run_time), "cron": str(j.trigger)}
            for j in self._scheduler.get_jobs()
        ]

    # ── Lifecycle ────────────────────────────────────────────

    async def shutdown(self):
        self._scheduler.shutdown(wait=False)
