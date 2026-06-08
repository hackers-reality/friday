"""
FRIDAY ↔ OpenCode integration bridge.
Spawns sub-agents via opencode's REST API for parallel task execution.
Uses OPENCODE_ZEN_API_KEY for big-pickle model, or opencode serve for local server.
"""

import os
import json
import time
import httpx
import subprocess
import threading
from typing import Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

OPENCODE_ZEN_API_KEY = os.getenv("OPENCODE_ZEN_API_KEY", "")
OPENCODE_ZEN_MODEL = os.getenv("OPENCODE_ZEN_MODEL", "big-pickle")
NVIDIA_NIM_API_KEY = os.getenv("NVIDIA_NIM_API_KEY", "") or os.getenv("NVIDIA_API_KEY", "") or os.getenv("NIM_API_KEY", "")
NVIDIA_API_BASE = os.getenv("NIM_API_BASE", "https://integrate.api.nvidia.com/v1")
NVIDIA_MODEL = os.getenv("NVIDIA_SPAWN_MODEL", "meta/llama-3.1-8b-instruct")
OPENCODE_SERVER_URL = os.getenv("OPENCODE_SERVER_URL", "http://localhost:4096")
OPENCODE_SERVE_PORT = int(os.getenv("OPENCODE_SERVE_PORT", "4096"))
ZEN_API_URL = os.getenv("ZEN_API_URL", "https://opencode.ai/zen/v1")

@dataclass
class SubAgent:
    id: str
    name: str
    session_id: str
    task: str
    status: str  # "spawning", "running", "completed", "failed"
    created_at: str
    completed_at: Optional[str] = None
    result: Optional[str] = None
    parent_session: Optional[str] = None
    role: str = "general"
    current_step: Optional[str] = None
    steps_completed: Optional[int] = None
    total_steps: Optional[int] = None
    thought_process: list = field(default_factory=list)

class OpencodeBridge:
    """
    Manages opencode server lifecycle and sub-agent spawning.

    Usage:
        bridge = OpencodeBridge()
        bridge.start_server()  # starts opencode serve in background
        agent = bridge.spawn_agent("researcher", "Research Python async patterns")
        bridge.spawn_parallel([
            ("coder", "Write a FastAPI CRUD for users"),
            ("researcher", "Find best practices for WebSocket auth")
        ])
        bridge.stop_server()
    """

    def __init__(self):
        self.server_process: Optional[subprocess.Popen] = None
        self.client: Optional[httpx.Client] = None
        self.agents: dict[str, SubAgent] = {}
        self._event_listeners: list[Callable] = []
        self._lock = threading.Lock()
        self._zen_key: str = ""
        self._nvidia_key: str = ""
        self._use_zen = False
        self._use_nvidia = False
        self._spawn_counter = 0
        self._sse_thread: Optional[threading.Thread] = None
        self._refresh_key()

    def _refresh_key(self):
        """Re-read API keys from environment at runtime."""
        self._zen_key = os.environ.get("OPENCODE_ZEN_API_KEY", "")
        self._use_zen = bool(self._zen_key)
        self._nvidia_key = os.environ.get("NVIDIA_NIM_API_KEY", "") or os.environ.get("NVIDIA_API_KEY", "") or os.environ.get("NIM_API_KEY", "")
        self._use_nvidia = bool(self._nvidia_key)

    def start_server(self):
        """Start opencode serve as background process (if not using Zen or NVIDIA)."""
        self._refresh_key()
        if self._use_zen or self._use_nvidia:
            self.client = httpx.Client(base_url=ZEN_API_URL)
            return

        try:
            subprocess.run(["opencode", "--version"], capture_output=True, timeout=5)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            raise RuntimeError("opencode not found. Install with: npm install -g @anomalyco/opencode")

        self.server_process = subprocess.Popen(
            ["opencode", "serve", "--port", str(OPENCODE_SERVE_PORT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(3)
        self.client = httpx.Client(base_url=f"http://localhost:{OPENCODE_SERVE_PORT}")

    def stop_server(self):
        """Stop the opencode server."""
        if self.server_process:
            self.server_process.terminate()
            self.server_process = None

    def spawn_agent(self, name: str, task: str, model: str = "") -> SubAgent:
        """
        Spawn a sub-agent to work on a task.
        Returns immediately with the agent's session info.
        Round-robins between Zen API and NVIDIA NIM if both keys are available.
        """
        if not self._use_zen and not self._use_nvidia:
            return self._spawn_server_agent(name, task, model)

        # Round-robin between Zen and NVIDIA when both are available
        use_nvidia = False
        if self._use_zen and self._use_nvidia:
            self._spawn_counter += 1
            use_nvidia = (self._spawn_counter % 2 == 0)
        elif self._use_nvidia:
            use_nvidia = True

        return self._spawn_cloud_agent(name, task, model, use_nvidia)

    def _spawn_server_agent(self, name: str, task: str, model: str) -> SubAgent:
        """Spawn via opencode serve REST API."""
        session_resp = self.client.post("/session", json={
            "title": f"FRIDAY\u2192{name}"
        })
        session_id = session_resp.json()["id"]

        self.client.post(f"/session/{session_id}/message", json={
            "parts": [{"type": "text", "text": task}],
            "agent": name,
        })

        agent = SubAgent(
            id=f"agent_{len(self.agents)}",
            name=name,
            session_id=session_id,
            task=task,
            status="running",
            created_at=datetime.now().isoformat(),
        )

        with self._lock:
            self.agents[agent.id] = agent

        threading.Thread(target=self._monitor_agent, args=(agent,), daemon=True).start()

        return agent

    def spawn_parallel(self, tasks: list[tuple[str, str]]) -> list[SubAgent]:
        """
        Spawn multiple agents in parallel.
        Each tuple is (agent_name, task_description).
        """
        agents = []
        threads = []
        for name, task in tasks:
            t = threading.Thread(
                target=lambda n, tk: agents.append(self.spawn_agent(n, tk)),
                args=(name, task),
                daemon=True
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=5)

        return agents

    def get_agent_result(self, agent_id: str) -> Optional[SubAgent]:
        """Get the current state and result of an agent."""
        return self.agents.get(agent_id)

    def get_active_agents(self) -> list[SubAgent]:
        """Get all currently running agents."""
        return [
            a for a in self.agents.values()
            if a.status in ("spawning", "running")
        ]

    def get_all_results(self) -> list[dict]:
        """Get all agent results formatted for FRIDAY's context."""
        return [
            {
                "name": a.name,
                "status": a.status,
                "task": a.task,
                "result": a.result,
                "created_at": a.created_at,
                "completed_at": a.completed_at,
            }
            for a in self.agents.values()
        ]

    def _spawn_cloud_agent(self, name: str, task: str, model: str = "", use_nvidia: bool = False) -> SubAgent:
        """Spawn via cloud API (Zen or NVIDIA NIM) in background thread."""
        agent_id = f"agent_{len(self.agents)}"
        agent = SubAgent(
            id=agent_id,
            name=name,
            session_id="",
            task=task,
            status="running",
            created_at=datetime.now().isoformat(),
        )
        with self._lock:
            self.agents[agent.id] = agent

        threading.Thread(target=self._run_cloud_task, args=(agent, model, use_nvidia), daemon=True).start()

        return agent

    def _run_cloud_task(self, agent: SubAgent, model: str = "", use_nvidia: bool = False):
        """Execute a cloud API call in background — Zen API or NVIDIA NIM."""
        try:
            self._refresh_key()
            if use_nvidia:
                content = self._call_nvidia(agent, model)
            else:
                content = self._call_zen(agent, model)

            with self._lock:
                agent.status = "completed"
                agent.result = content
                agent.completed_at = datetime.now().isoformat()
                self._notify_listeners(agent)

        except Exception as e:
            with self._lock:
                agent.status = "failed"
                agent.result = f"Error: {str(e)}"
                agent.completed_at = datetime.now().isoformat()
                self._notify_listeners(agent)

    def _call_zen(self, agent: SubAgent, model: str = "") -> str:
        """Call Zen API chat completions. Returns content string."""
        model_name = model or OPENCODE_ZEN_MODEL
        resp = httpx.post(
            f"{ZEN_API_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._zen_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": f"You are {agent.name}, a sub-agent working for FRIDAY. Complete the assigned task and return results."},
                    {"role": "user", "content": agent.task},
                ],
                "max_tokens": 128000,
            },
            timeout=600,
        )
        result = resp.json()
        content = result["choices"][0]["message"]["content"]

        # Retry once if content is empty (reasoning-only response)
        if not content:
            resp = httpx.post(
                f"{ZEN_API_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._zen_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": f"You are {agent.name}, a sub-agent working for FRIDAY."},
                        {"role": "user", "content": agent.task},
                        {"role": "assistant", "content": "I will provide a complete, detailed response without extra thinking tags."},
                    ],
                    "max_tokens": 128000,
                },
                timeout=600,
            )
            result = resp.json()
            content = result["choices"][0]["message"]["content"] or ""

        return content

    def _call_nvidia(self, agent: SubAgent, model: str = "") -> str:
        """Call NVIDIA NIM chat completions. Returns content string."""
        model_name = model or NVIDIA_MODEL
        resp = httpx.post(
            f"{NVIDIA_API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._nvidia_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": f"You are {agent.name}, a sub-agent working for FRIDAY. Complete the assigned task and return results."},
                    {"role": "user", "content": agent.task},
                ],
                "max_tokens": 4096,
            },
            timeout=600,
        )
        result = resp.json()
        return result["choices"][0]["message"]["content"]

    def on_event(self, callback: Callable):
        """Register an event listener for agent status changes."""
        self._event_listeners.append(callback)

    def _notify_listeners(self, agent: SubAgent):
        for cb in self._event_listeners:
            try:
                cb(agent)
            except Exception:
                pass

    def _monitor_agent(self, agent: SubAgent):
        """Periodically check agent progress (for server-based agents)."""
        while agent.status == "running":
            time.sleep(3)
            try:
                msgs = self.client.get(f"/session/{agent.session_id}/message").json()
                if msgs and msgs[-1].get("role") == "assistant":
                    with self._lock:
                        agent.status = "completed"
                        agent.result = msgs[-1].get("content", "")
                        agent.completed_at = datetime.now().isoformat()
                        self._notify_listeners(agent)
            except Exception:
                pass
