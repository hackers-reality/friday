"""Agent registry for Friday's NIM-powered orchestration layer.

Loads agent definitions from config.yaml, validates configured models,
and exposes lookup helpers for the orchestrator and resolver.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Any, Dict, List, Optional

from friday.base_agent import AgentResult, AgentTask, BaseAgent
from friday.context_bus import ContextBus, get_bus
from friday.logging_utils import configure_logging
from friday.nim_client import NIMClient, NIMCompletion
from friday.nim_router import NIMRouter, get_router
from friday.orchestration_config import ensure_config


logger = configure_logging(__name__)


@dataclass(slots=True)
class AgentProfile:
    """Static configuration for an agent loaded from config.yaml."""

    agent_id: str
    display_name: str
    task_types: List[str]
    nim_model: str
    tools: List[str]
    enabled: bool = True

    def aliases(self) -> List[str]:
        """Return common aliases used by the name resolver."""
        tokens = {self.display_name.lower(), self.agent_id.lower()}
        tokens.update(part for part in self.display_name.lower().split() if part)
        for task_type in self.task_types:
            normalized = task_type.replace("_", " ").lower()
            tokens.add(normalized)
            tokens.add(f"{normalized} agent")
        return sorted(tokens)


class NIMBackedAgent(BaseAgent):
    """Generic stateless agent that executes through NVIDIA NIM."""

    def __init__(
        self,
        profile: AgentProfile,
        client: NIMClient,
        router: NIMRouter,
        bus: ContextBus | None = None,
        fallback_handler: Optional[Any] = None,
    ) -> None:
        super().__init__(
            agent_id=profile.agent_id,
            display_name=profile.display_name,
            task_types=profile.task_types,
            tools=profile.tools,
            nim_model=profile.nim_model,
        )
        self._profile = profile
        self._client = client
        self._router = router
        self._bus = bus or get_bus()
        self._fallback_handler = fallback_handler

    async def execute(self, task: AgentTask) -> AgentResult:
        start = monotonic()
        await self.emit_event(self._bus, "status", {"status": "started", "task_id": task.task_id, "task_type": task.task_type})

        prompt = (
            f"You are {self.display_name}, a Friday specialist agent.\n"
            f"Task type: {task.task_type}\n"
            f"Tools: {', '.join(self.tools) or 'none'}\n"
            f"Requestor: {task.requester}\n"
            f"Context snapshot: {task.context_snapshot}\n"
            f"Task payload: {task.payload}\n"
            "Return a concise, actionable result."
        )

        await self.emit_event(self._bus, "status", {"status": "working", "task_id": task.task_id, "task_type": task.task_type})

        completion: NIMCompletion = await self._client.complete_chat(
            model_id=self.nim_model,
            fallback_models=self._router.get_candidates(task.task_type),
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": task.payload.get("utterance", str(task.payload))},
            ],
            task_type=task.task_type,
            fallback_handler=self._fallback_handler,
        )

        result = AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            status="completed",
            output=completion.content,
            error=None,
            duration_ms=self.elapsed_ms(start),
            tokens_used=completion.tokens_used,
        )
        await self.emit_event(self._bus, "result", result.to_dict())
        await self.emit_event(self._bus, "status", {"status": "completed", "task_id": task.task_id, "task_type": task.task_type})
        return result


class AgentRegistry:
    """Load and validate agent definitions from config.yaml."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_path = Path(config_path) if config_path else None
        self._config = ensure_config(self._config_path) if self._config_path else ensure_config()
        self._profiles = self._load_profiles()
        self._router = get_router()

    def _load_profiles(self) -> List[AgentProfile]:
        profiles: List[AgentProfile] = []
        for entry in self._config.get("agents", []) or []:
            if not isinstance(entry, dict):
                continue
            profiles.append(
                AgentProfile(
                    agent_id=str(entry.get("id", "")).strip(),
                    display_name=str(entry.get("name", "")).strip(),
                    task_types=[str(item) for item in entry.get("task_types", []) or []],
                    nim_model=str(entry.get("nim_model", "")).strip(),
                    tools=[str(item) for item in entry.get("tools", []) or []],
                    enabled=bool(entry.get("enabled", True)),
                )
            )
        return [profile for profile in profiles if profile.agent_id and profile.display_name]

    def reload(self) -> List[AgentProfile]:
        """Reload the registry from disk."""
        self._config = ensure_config(self._config_path) if self._config_path else ensure_config()
        self._profiles = self._load_profiles()
        return self._profiles

    def get_by_id(self, agent_id: str) -> Optional[AgentProfile]:
        """Return a profile by agent id."""
        target = agent_id.strip().lower()
        return next((profile for profile in self._profiles if profile.agent_id.lower() == target), None)

    def get_by_name(self, name: str) -> Optional[AgentProfile]:
        """Return a profile by display name."""
        target = name.strip().lower()
        return next((profile for profile in self._profiles if profile.display_name.lower() == target), None)

    def get_by_task_type(self, task_type: str) -> List[AgentProfile]:
        """Return all enabled agents that can handle a task type."""
        target = task_type.strip().lower().replace(" ", "_")
        return [
            profile
            for profile in self._profiles
            if profile.enabled and any(task.lower().replace(" ", "_") == target for task in profile.task_types)
        ]

    def list_all(self) -> List[AgentProfile]:
        """Return all loaded profiles."""
        return list(self._profiles)

    async def validate_models(self, client: Optional[NIMClient] = None) -> List[Dict[str, Any]]:
        """Validate all configured NIM models against the live NIM catalog."""
        nim_client = client
        created_client = False
        if nim_client is None:
            nim_cfg = self._config.get("nim", {})
            try:
                nim_client = NIMClient(
                    api_base=str(nim_cfg.get("api_base", "https://integrate.api.nvidia.com/v1")),
                    rate_limit_rpm=int(nim_cfg.get("rate_limit_rpm", 40)),
                )
                created_client = True
            except Exception as exc:
                logger.warning("Skipping live NIM validation because the client could not be created: %s", exc)
                return [
                    {
                        "agent_id": profile.agent_id,
                        "name": profile.display_name,
                        "nim_model": profile.nim_model,
                        "reachable": False,
                    }
                    for profile in self._profiles
                ]

        try:
            catalog = await self._router.refresh_catalog(nim_client)
        except Exception as exc:
            logger.warning("Unable to fetch NIM catalog during validation: %s", exc)
            catalog = set()
        finally:
            if created_client:
                await nim_client.aclose()

        findings: List[Dict[str, Any]] = []
        for profile in self._profiles:
            available = not catalog or profile.nim_model in catalog
            findings.append(
                {
                    "agent_id": profile.agent_id,
                    "name": profile.display_name,
                    "nim_model": profile.nim_model,
                    "reachable": available,
                }
            )
            if not available:
                logger.warning("Configured model %s for agent %s is not in the NIM catalog", profile.nim_model, profile.display_name)
        return findings

    def instantiate(self, agent_id: str, client: NIMClient, bus: ContextBus | None = None, fallback_handler: Optional[Any] = None) -> NIMBackedAgent:
        """Create a runnable agent instance for the given id."""
        profile = self.get_by_id(agent_id)
        if profile is None:
            raise KeyError(f"Unknown agent id: {agent_id}")
        return NIMBackedAgent(profile, client=client, router=self._router, bus=bus, fallback_handler=fallback_handler)


_REGISTRY = AgentRegistry()


def get_registry() -> AgentRegistry:
    """Return the shared registry instance."""
    return _REGISTRY
