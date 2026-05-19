"""Friday's multi-agent orchestrator.

Coordinates name resolution, task typing, NIM-backed agent execution,
parallel fan-out, context bus updates, memory writes, and scheduled jobs.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
except ImportError:  # pragma: no cover - scheduler is optional until dependencies are installed
    AsyncIOScheduler = None
    CronTrigger = None

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover - Gemini fallback only works when installed
    genai = None
    types = None

from friday.agent_registry import AgentProfile, AgentRegistry, get_registry
from friday.base_agent import AgentResult, AgentTask
from friday.context_bus import ContextBus, get_bus
from friday.logging_utils import configure_logging
from friday.memory_context import build_relevant_memory_context
from friday.name_resolver import AgentNameResolver
from friday.nim_client import NIMClient
from friday.nim_router import NIMRouter, get_router
from friday.orchestration_config import ensure_config


logger = configure_logging(__name__)


class FridayOrchestrator:
    """Coordinate Friday's multi-agent execution flow."""

    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        router: Optional[NIMRouter] = None,
        client: Optional[NIMClient] = None,
        bus: Optional[ContextBus] = None,
    ) -> None:
        config = ensure_config()
        nim_cfg = config.get("nim", {})

        self.registry = registry or get_registry()
        self.router = router or get_router()
        self.bus = bus or get_bus()
        self.client = client
        if self.client is None:
            try:
                self.client = NIMClient(
                    api_base=str(nim_cfg.get("api_base", "https://integrate.api.nvidia.com/v1")),
                    rate_limit_rpm=int(nim_cfg.get("rate_limit_rpm", 40)),
                )
            except Exception as exc:
                logger.warning("NIM client is not available yet: %s", exc)
        self.name_resolver = AgentNameResolver(self.registry.list_all())
        self.scheduler = AsyncIOScheduler() if AsyncIOScheduler is not None else None
        self.status: Dict[str, Dict[str, Any]] = {}
        self._event_tasks: List[asyncio.Task] = []
        self._initialized = False
        self._gemini_model = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.0-flash")

    async def initialize(self) -> None:
        """Validate agents, warm the catalog, and start background listeners."""
        if self._initialized:
            return

        await self.registry.validate_models(client=self.client)
        self._ensure_scheduler_started()
        await self._start_event_watchers()
        self._initialized = True
        logger.info("Friday orchestrator initialized with %d agents", len(self.registry.list_all()))

    def _ensure_scheduler_started(self) -> None:
        if self.scheduler is None:
            logger.warning("APScheduler is unavailable; scheduled agent tasks are disabled until the dependency is installed")
            return
        if not self.scheduler.running:
            self.scheduler.start()

    async def _start_event_watchers(self) -> None:
        for profile in self.registry.list_all():
            topic = f"agent.{profile.agent_id}.status"
            result_topic = f"agent.{profile.agent_id}.result"
            self._event_tasks.append(asyncio.create_task(self._mirror_topic(profile.agent_id, topic)))
            self._event_tasks.append(asyncio.create_task(self._mirror_topic(profile.agent_id, result_topic)))
        self._event_tasks.append(asyncio.create_task(self._mirror_topic("system", "system.events")))

    async def _mirror_topic(self, agent_id: str, topic: str) -> None:
        async for payload in self.bus.subscribe(topic):
            record = self.status.setdefault(agent_id, {"status": "idle", "current_task": None, "last_result": None, "last_seen": None})
            record["last_seen"] = datetime.utcnow().isoformat()
            if topic.endswith(".status"):
                record["status"] = payload.get("status", record.get("status", "idle"))
                record["current_task"] = payload.get("task_id") or record.get("current_task")
            elif topic.endswith(".result"):
                record["status"] = payload.get("status", "completed")
                record["last_result"] = payload.get("output")
                record["current_task"] = payload.get("task_id")
            else:
                record.setdefault("events", []).append(payload)

    def classify_task_type(self, utterance: str) -> str:
        """Classify a user utterance into a task type."""
        text = utterance.lower()
        keyword_map = {
            "image_analysis": ["image", "photo", "picture", "screenshot", "camera", "vision", "see", "look"],
            "code_gen": ["code", "implement", "debug", "fix", "refactor", "class", "function", "api", "endpoint"],
            "research": ["research", "analyze", "compare", "investigate", "find", "search", "look up"],
            "summarization": ["summarize", "summary", "recap", "tl;dr", "brief"],
            "reasoning": ["reason", "why", "decide", "plan", "optimize", "solve"],
        }
        scored: Dict[str, int] = {}
        for task_type, keywords in keyword_map.items():
            scored[task_type] = sum(1 for keyword in keywords if keyword in text)
        best_task = max(scored.items(), key=lambda item: item[1])
        return best_task[0] if best_task[1] > 0 else "general"

    def _context_snapshot(self, utterance: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        snapshot = {
            "utterance": utterance,
            "timestamp": datetime.utcnow().isoformat(),
            "memory": build_relevant_memory_context(utterance),
        }
        if context:
            snapshot["context"] = context
        return snapshot

    async def _gemini_fallback(self, *, messages: Sequence[Dict[str, Any]], task_type: str, max_tokens: int = 2048) -> Dict[str, Any]:
        """Use Gemini only after NIM retries are exhausted."""
        if genai is None or types is None:
            raise RuntimeError("Gemini client library is not installed")
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Gemini fallback is unavailable because GOOGLE_API_KEY is not configured")

        def _invoke() -> str:
            client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
            prompt = "\n\n".join(str(message.get("content", "")) for message in messages)
            response = client.models.generate_content(
                model=self._gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=max_tokens,
                ),
            )
            return getattr(response, "text", "") or str(response)

        content = await asyncio.to_thread(_invoke)
        return {"model": self._gemini_model, "content": content, "tokens_used": 0}

    async def _run_profile(self, profile: AgentProfile, task: AgentTask) -> AgentResult:
        if self.client is None:
            return await self._run_profile_via_gemini(profile, task)
        agent = self.registry.instantiate(profile.agent_id, client=self.client, bus=self.bus, fallback_handler=self._gemini_fallback)
        return await agent.execute(task)

    async def _run_profile_via_gemini(self, profile: AgentProfile, task: AgentTask) -> AgentResult:
        start = asyncio.get_running_loop().time()
        prompt = (
            f"You are {profile.display_name}, a Friday specialist agent.\n"
            f"Task type: {task.task_type}\n"
            f"Tools: {', '.join(profile.tools) or 'none'}\n"
            f"Requestor: {task.requester}\n"
            f"Context snapshot: {task.context_snapshot}\n"
            f"Task payload: {task.payload}\n"
            "Return a concise, actionable result."
        )
        await self.bus.publish(f"agent.{profile.agent_id}.status", {"status": "started", "task_id": task.task_id, "task_type": task.task_type})
        fallback = await self._gemini_fallback(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": task.payload.get("utterance", str(task.payload))},
            ],
            task_type=task.task_type,
        )
        result = AgentResult(
            task_id=task.task_id,
            agent_id=profile.agent_id,
            status="completed",
            output=str(fallback.get("content", "")),
            error=None,
            duration_ms=int((asyncio.get_running_loop().time() - start) * 1000),
            tokens_used=int(fallback.get("tokens_used", 0) or 0),
        )
        await self.bus.publish(f"agent.{profile.agent_id}.result", result.to_dict())
        return result

    def _resolve_targets(self, utterance: str, preferred_agent: Optional[str] = None) -> List[AgentProfile]:
        if preferred_agent:
            profile = self.registry.get_by_id(preferred_agent) or self.registry.get_by_name(preferred_agent)
            return [profile] if profile else []

        matches = self.name_resolver.resolve_many(utterance)
        profiles: List[AgentProfile] = []
        for match in matches:
            profile = self.registry.get_by_id(match.agent_id)
            if profile and profile not in profiles:
                profiles.append(profile)
        return profiles

    async def delegate(
        self,
        user_utterance: str,
        context: Optional[Dict[str, Any]] = None,
        preferred_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Route an utterance to one or more agents and return structured results."""
        await self.initialize()

        targets = self._resolve_targets(user_utterance, preferred_agent=preferred_agent)
        if not targets:
            available = ", ".join(profile.display_name for profile in self.registry.list_all())
            return {
                "status": "needs_clarification",
                "prompt": f"Which agent? Available: {available}",
                "results": [],
            }

        task_type = self.classify_task_type(user_utterance)
        task = AgentTask(
            task_id=f"task_{uuid.uuid4().hex[:8]}",
            task_type=task_type,
            payload={"utterance": user_utterance},
            context_snapshot=self._context_snapshot(user_utterance, context),
            requester=str((context or {}).get("requester", "gemini-live")),
        )

        await self.bus.publish(
            "system.events",
            {
                "event": "orchestrator.delegate.started",
                "task_id": task.task_id,
                "task_type": task_type,
                "targets": [profile.agent_id for profile in targets],
            },
        )

        if len(targets) == 1:
            results = [await self._run_profile(targets[0], task)]
        else:
            results = list(await asyncio.gather(*(self._run_profile(profile, task) for profile in targets)))

        for result in results:
            await self._store_result(result, task)

        summary = self._merge_results(results)
        return {
            "status": "completed",
            "task_id": task.task_id,
            "task_type": task_type,
            "results": [result.to_dict() for result in results],
            "summary": summary,
        }

    async def _store_result(self, result: AgentResult, task: AgentTask) -> None:
        """Persist results into the memory system and status bus."""
        await self.bus.publish(f"agent.{result.agent_id}.result", result.to_dict())
        self.status.setdefault(result.agent_id, {})
        self.status[result.agent_id].update(
            {
                "status": result.status,
                "current_task": task.task_id,
                "last_result": result.output,
                "last_seen": datetime.utcnow().isoformat(),
            }
        )

        try:
            from friday.vector_memory import get_vector_memory

            vm = get_vector_memory()
            if vm and vm.is_available():
                vm.add(
                    text=f"{result.agent_id}:{task.task_type}:{result.output}",
                    metadata={
                        "source": "orchestrator",
                        "agent_id": result.agent_id,
                        "task_id": task.task_id,
                        "task_type": task.task_type,
                    },
                    id=f"{task.task_id}:{result.agent_id}",
                )
        except Exception as exc:  # pragma: no cover - memory is optional
            logger.warning("Unable to store orchestrator result in vector memory: %s", exc)

    def _merge_results(self, results: Sequence[AgentResult]) -> str:
        """Combine one or more agent results into a concise summary."""
        if len(results) == 1:
            return results[0].output
        lines = []
        for result in results:
            lines.append(f"[{result.agent_id}] {result.output}")
        return "\n".join(lines)

    async def schedule(self, agent_id: str, task_payload: Dict[str, Any], cron_expr: str) -> str:
        """Schedule a recurring task with APScheduler."""
        await self.initialize()
        profile = self.registry.get_by_id(agent_id)
        if profile is None:
            raise KeyError(f"Unknown agent id: {agent_id}")

        if self.scheduler is None or CronTrigger is None:
            raise RuntimeError("APScheduler is not available, so scheduling cannot be enabled")

        trigger = CronTrigger.from_crontab(cron_expr)

        async def _scheduled_job() -> None:
            await self.delegate(
                task_payload.get("utterance", task_payload.get("task", "")),
                context={"requester": "scheduler", "schedule": cron_expr},
                preferred_agent=agent_id,
            )

        job_id = f"scheduled_{agent_id}_{uuid.uuid4().hex[:8]}"
        self.scheduler.add_job(_scheduled_job, trigger=trigger, id=job_id, replace_existing=True)
        self.status.setdefault(agent_id, {}).update(
            {
                "status": "scheduled",
                "current_task": task_payload,
                "last_seen": datetime.utcnow().isoformat(),
            }
        )
        await self.bus.publish(
            "system.events",
            {
                "event": "orchestrator.schedule.created",
                "agent_id": agent_id,
                "cron": cron_expr,
                "job_id": job_id,
            },
        )
        return job_id

    def get_status(self, agent_id: str) -> Dict[str, Any]:
        """Return the live status snapshot for a specific agent."""
        return self.status.get(agent_id, {"status": "idle", "current_task": None, "last_result": None, "last_seen": None})


_ORCHESTRATOR: FridayOrchestrator | None = None


def get_orchestrator() -> FridayOrchestrator:
    """Return the shared orchestrator instance."""
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        _ORCHESTRATOR = FridayOrchestrator()
    return _ORCHESTRATOR


def run_delegate_sync(user_utterance: str, context: Optional[Dict[str, Any]] = None, preferred_agent: Optional[str] = None) -> Dict[str, Any]:
    """Convenience bridge for synchronous tool callers.

    If an event loop is already running in the current thread, a task is
    scheduled and a pending acknowledgement is returned to avoid blocking.
    """
    orchestrator = get_orchestrator()
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(orchestrator.delegate(user_utterance, context=context, preferred_agent=preferred_agent))

    asyncio.create_task(orchestrator.delegate(user_utterance, context=context, preferred_agent=preferred_agent))
    return {
        "status": "scheduled",
        "prompt": "Agent task queued on the running event loop.",
        "results": [],
    }
