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
            agent_instance = None
            if defn.id == "browser_agent":
                try:
                    from friday.browser_agent import BrowserAgent
                    agent_instance = BrowserAgent(defn)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning("Failed to load BrowserAgent for browser_agent: %s", e)
            elif defn.id == "osint_agent":
                try:
                    from friday.osint_agent import GhostAgent
                    agent_instance = GhostAgent(defn)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning("Failed to load GhostAgent for osint_agent: %s", e)
            elif defn.id == "research_agent":
                try:
                    from friday.research_agent import VeronicaAgent
                    agent_instance = VeronicaAgent(defn)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning("Failed to load VeronicaAgent for research_agent: %s", e)
            elif defn.id == "code_agent":
                try:
                    from friday.code_agent import ForgeAgent
                    agent_instance = ForgeAgent(defn)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning("Failed to load ForgeAgent for code_agent: %s", e)
            elif defn.id == "sandbox_runner_agent":
                try:
                    from friday.sandbox_runner import AutonomousSandboxRunner
                    agent_instance = AutonomousSandboxRunner(defn)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning("Failed to load AutonomousSandboxRunner for sandbox_runner_agent: %s", e)
            elif defn.id == "pr_reviewer_agent":
                try:
                    from friday.pr_agent import AutonomousPRReviewer
                    agent_instance = AutonomousPRReviewer(defn)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning("Failed to load AutonomousPRReviewer for pr_reviewer_agent: %s", e)

            if agent_instance:
                self._executors[defn.id] = agent_instance
            else:
                self._executors[defn.id] = NimAgentExecutor(defn, self._client, self._bus)
            self._statuses[defn.id] = LiveStatus(agent_id=defn.id, state="idle")
        self._scheduler.start()
        self._initialized = True

    # ── Single delegation ────────────────────────────────────

    def _verify_api_keys(self):
        """Interactively request missing API keys and save them to .env."""
        env_path = "e:/open-interpreter/.env"
        keys_updated = False
        
        nim_key = os.getenv("NVIDIA_NIM_API_KEY")
        if not nim_key:
            print("\n[STARK INDUSTRIES] ⚠️ NVIDIA NIM API Key is missing!", flush=True)
            new_key = input("Enter NVIDIA_NIM_API_KEY: ").strip()
            if new_key:
                os.environ["NVIDIA_NIM_API_KEY"] = new_key
                keys_updated = True
                
        opencode_key = os.getenv("OPENCODE_ZEN_API_KEY")
        if not opencode_key:
            print("\n[STARK INDUSTRIES] ⚠️ OpenCode Zen API Key is missing!", flush=True)
            new_key = input("Enter OPENCODE_ZEN_API_KEY: ").strip()
            if new_key:
                os.environ["OPENCODE_ZEN_API_KEY"] = new_key
                keys_updated = True
                
        if keys_updated and os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                new_lines = []
                has_nim = False
                has_opencode = False
                for line in lines:
                    if line.startswith("NVIDIA_NIM_API_KEY="):
                        new_lines.append(f"NVIDIA_NIM_API_KEY={os.getenv('NVIDIA_NIM_API_KEY')}\n")
                        has_nim = True
                    elif line.startswith("OPENCODE_ZEN_API_KEY="):
                        new_lines.append(f"OPENCODE_ZEN_API_KEY={os.getenv('OPENCODE_ZEN_API_KEY')}\n")
                        has_opencode = True
                    else:
                        new_lines.append(line)
                if not has_nim:
                    new_lines.append(f"NVIDIA_NIM_API_KEY={os.getenv('NVIDIA_NIM_API_KEY')}\n")
                if not has_opencode:
                    new_lines.append(f"OPENCODE_ZEN_API_KEY={os.getenv('OPENCODE_ZEN_API_KEY')}\n")
                with open(env_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                print("[STARK INDUSTRIES] API keys saved successfully to .env!\n", flush=True)
            except Exception as e:
                print(f"[STARK INDUSTRIES] Failed to save keys: {e}\n", flush=True)

    async def delegate(self, agent_name: str, payload: str, task_type: str = "",
                       **overrides) -> AgentResult:
        """Delegate a single task to a named agent. Returns AgentResult."""
        self._verify_api_keys()

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

        # Create log folder and tail command prompt popup
        from friday._paths import FRIDAY_MEMORY
        log_dir = os.path.join(FRIDAY_MEMORY, "agent_logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"{defn.id}.log")

        # Write prompt / init information to the log
        with open(log_file, "w", encoding="utf-8") as lf:
            lf.write(f"============================================================\n")
            lf.write(f"STARK INDUSTRIES OS — Dynamic Agent Active HUD\n")
            lf.write(f"Agent ID: {defn.id} | Name: {defn.name}\n")
            lf.write(f"Task ID: {task.task_id} | Task Type: {task_type}\n")
            lf.write(f"Started At: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            lf.write(f"============================================================\n\n")
            lf.write(f"[PROMPT]\n{payload}\n\n")
            lf.write(f"[PROGRESS] Subagent initialized. Starting execution...\n")
            lf.flush()

        # Spawn CMD window running powershell tail
        tail_proc = None
        try:
            # Command to launch CMD window: start cmd /k "powershell -Command Get-Content -Path 'log' -Wait -Tail 20"
            cmd_line = f'start "HUD: {defn.name} ({defn.id})" cmd /k "powershell -Command Get-Content -Path \'{log_file}\' -Wait -Tail 20"'
            tail_proc = subprocess.Popen(cmd_line, shell=True)
        except Exception as e:
            logger.warning("Failed to spawn CMD window tail: %s", e)

        # Inject helper callback into the executor or subclass to write progress to log_file
        def log_progress(msg: str):
            try:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}\n")
                    f.flush()
            except Exception:
                pass

        if hasattr(executor, "_update_status"):
            # Intercept state updates to log them to log_file
            orig_update = executor._update_status
            def wrapped_update(pct: int, action: str):
                log_progress(f"Progress {pct}% — {action}")
                orig_update(pct, action)
            executor._update_status = wrapped_update

        result = await executor.execute(task)

        # Log final result and clean up
        log_progress(f"Result Status: {result.status}")
        if result.status == "completed":
            log_progress(f"Output Preview:\n{result.output[:1000]}")
        else:
            log_progress(f"Error Context:\n{result.error}")
        log_progress(f"Execution complete. Press Ctrl+C in this console to exit.")

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

    def get_status(self, agent_id: str) -> dict:
        """Helper to get a dictionary summary of agent status."""
        st = self._statuses.get(agent_id)
        if st:
            return {
                "status": st.state,
                "current_task": st.task_id,
                "progress": st.progress_pct,
                "current_action": st.current_action,
                "started_at": st.started_at,
                "duration_ms": st.duration_ms
            }
        return {"status": "offline"}

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


_ORCHESTRATOR: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        from friday.agent_registry import get_registry
        from friday.nim_client import get_inference_client
        from friday.context_bus import get_bus
        _ORCHESTRATOR = Orchestrator(get_registry(), get_inference_client(), get_bus())
    return _ORCHESTRATOR


def run_delegate_sync(payload: str, context: dict = None, preferred_agent: str = None) -> Any:
    orch = get_orchestrator()
    loop = None
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        pass

    if not orch._initialized:
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(orch.init(), loop).result()
        else:
            asyncio.run(orch.init())

    coro = orch.delegate(preferred_agent, payload) if preferred_agent else orch.parse_and_route(payload)
    if loop and loop.is_running():
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()
    else:
        return asyncio.run(coro)
