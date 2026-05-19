"""
FRIDAY Agent Registry — loads agent definitions from config.yaml,
validates NIM model health on startup, provides lookup by id/name/task_type.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import yaml

from friday.base_agent import AgentDef
from friday.nim_client import InferenceClient


class AgentRegistry:
    """
    Single source of truth for agent definitions.

    Usage:
        reg = AgentRegistry()
        await reg.load()              # load from config.yaml
        await reg.validate_models()   # health-check all NIM models
        veronica = reg.get_by_name("Veronica")
    """

    def __init__(self):
        self._agents: dict[str, AgentDef] = {}  # id -> def
        self._name_index: dict[str, str] = {}   # lower(name) -> id
        self._task_index: dict[str, list[str]] = {}  # task_type -> [id, ...]
        self.unavailable_models: set[str] = set()
        self.loaded = False

    async def load(self, path: Optional[Path] = None) -> int:
        """Load agent definitions from config.yaml. Returns count loaded."""
        path = path or Path.cwd() / "config.yaml"
        if not path.exists():
            self.loaded = True
            return 0

        with open(path) as f:
            cfg = yaml.safe_load(f) or {}

        raw_agents: list[dict] = cfg.get("agents", [])
        count = 0
        for entry in raw_agents:
            if not entry.get("id"):
                continue
            defn = AgentDef(
                id=entry["id"],
                name=entry.get("name", entry["id"]),
                task_types=entry.get("task_types", ["general"]),
                nim_model=entry.get("nim_model", ""),
                tools=entry.get("tools", []),
                enabled=entry.get("enabled", False),
                system_prompt=entry.get("system_prompt", ""),
            )
            self._agents[defn.id] = defn
            self._name_index[defn.name.lower()] = defn.id
            self._name_index[defn.id.lower()] = defn.id
            for tt in defn.task_types:
                self._task_index.setdefault(tt, []).append(defn.id)
            count += 1

        self.loaded = True
        return count

    async def validate_models(self, client: Optional[InferenceClient] = None) -> dict[str, bool]:
        """Health-check all NIM models across all agents. Returns {model: ok}."""
        if not client:
            client = InferenceClient()
        seen: set[str] = set()
        results: dict[str, bool] = {}
        for defn in self._agents.values():
            if defn.nim_model and defn.nim_model not in seen:
                seen.add(defn.nim_model)
                ok = await client.health_check(defn.nim_model)
                results[defn.nim_model] = ok
                if not ok:
                    self.unavailable_models.add(defn.nim_model)
        return results

    def get_by_id(self, agent_id: str) -> Optional[AgentDef]:
        return self._agents.get(agent_id)

    def get_by_name(self, name: str) -> Optional[AgentDef]:
        key = self._name_index.get(name.lower())
        return self._agents.get(key) if key else None

    def get_by_task_type(self, task_type: str) -> list[AgentDef]:
        ids = self._task_index.get(task_type, [])
        return [self._agents[i] for i in ids if i in self._agents]

    def list_all(self, enabled_only: bool = True) -> list[AgentDef]:
        agents = list(self._agents.values())
        if enabled_only:
            agents = [a for a in agents if a.enabled]
        return agents

    def list_names(self, enabled_only: bool = True) -> list[str]:
        return [a.name for a in self.list_all(enabled_only=enabled_only)]
