"""
Friday Multi-Agent Delegation System (v2 — Peer-to-Peer).
Delegates complex tasks to specialist sub-agents, splits work across them,
and merges results. Supports parallel execution and cross-agent handoff.
"""
from __future__ import annotations

import json
import os
import time
import threading
from typing import Dict, Any, List, Optional, Callable, Tuple
from datetime import datetime
from pathlib import Path


#  Agent Roles  #

AGENT_ROLES = {
    "coder": {
        "description": "Specialist in writing, reading, and debugging code",
        "capabilities": ["read_file", "write_file", "run_cmd", "git_ops", "generate_file", "github_review_pr"],
    },
    "researcher": {
        "description": "Specialist in web research and information gathering",
        "capabilities": ["web_search", "deep_research", "video_search", "see_screen", "search_browser_history"],
    },
    "organizer": {
        "description": "Specialist in file management and system organization",
        "capabilities": ["list_files", "find_files", "copy_file", "move_file", "delete_file", "open_app", "close_app"],
    },
    "communicator": {
        "description": "Specialist in email, messages, and notifications",
        "capabilities": ["read_emails", "send_email", "draft_email", "send_instagram_dm", "gmail_authorize"],
    },
    "automator": {
        "description": "Specialist in browser automation and web tasks",
        "capabilities": ["opencli_navigate", "opencli_click", "opencli_type", "opencli_extract", "opencli_screenshot"],
    },
    "planner": {
        "description": "Specialist in scheduling, calendar, and goals",
        "capabilities": ["calendar_tool_handler", "goals_tool_handler", "memory_retrieve", "memory_store"],
    },
}


#  Agent  #

class Agent:
    """A specialist sub-agent with a defined role."""

    def __init__(self, name: str, role: str, description: str = ""):
        self.name = name
        self.role = role
        self.description = description or AGENT_ROLES.get(role, {}).get("description", "")
        self.capabilities = AGENT_ROLES.get(role, {}).get("capabilities", [])
        self.status = "idle"
        self.task_history: List[Dict[str, Any]] = []

    def can_handle(self, task: str, required_tools: List[str] = None) -> bool:
        if not required_tools:
            return True
        return all(tool in self.capabilities for tool in required_tools)

    def assign_task(self, task_id: str, description: str, tools: Dict[str, Callable] = None) -> str:
        self.status = "busy"
        self.task_history.append({
            "task_id": task_id,
            "description": description,
            "assigned_at": datetime.now().isoformat(),
        })
        result = json.dumps({"agent": self.name, "role": self.role, "task": description, "status": "assigned"})
        self.status = "idle"
        return result

    def get_summary(self) -> str:
        return f"{self.name} ({self.role}): {self.description} | Tools: {', '.join(self.capabilities)} | Tasks done: {len(self.task_history)}"


#  Multi-Agent System (v2 with peer-to-peer)  #

class MultiAgentSystem:
    """Manages a team of specialist sub-agents with peer-to-peer delegation."""

    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self._init_default_agents()
        self._task_counter = 0
        self._results: Dict[str, List[Dict]] = {}

    def _init_default_agents(self):
        for role_name in AGENT_ROLES:
            agent = Agent(name=f"{role_name}-agent", role=role_name)
            self.agents[agent.name] = agent

    def add_agent(self, agent: Agent):
        self.agents[agent.name] = agent

    def remove_agent(self, name: str) -> bool:
        if name in self.agents:
            del self.agents[name]
            return True
        return False

    def get_agent(self, name: str) -> Optional[Agent]:
        return self.agents.get(name)

    def list_agents(self) -> str:
        if not self.agents:
            return "No agents available."
        lines = ["### MULTI-AGENT SYSTEM (Peer-to-Peer)", ""]
        for name, agent in self.agents.items():
            lines.append(f"**{name}** — {agent.description or agent.role}")
            lines.append(f"  Status: {agent.status}, Tasks done: {len(agent.task_history)}")
            lines.append("")
        return "\n".join(lines)

    def _score_agent(self, agent: Agent, task_lower: str) -> int:
        """Score how well an agent matches a task description."""
        score = 0
        for word in agent.role.split("_"):
            if word in task_lower:
                score += 2
        for cap in agent.capabilities:
            cap_words = cap.replace("_", " ").lower()
            for word in cap_words.split():
                if word in task_lower:
                    score += 1
        return score

    def delegate(self, task_description: str, preferred_agent: str = None) -> str:
        """Delegate a task to the most suitable agent (single)."""
        self._task_counter += 1
        task_id = f"task_{int(time.time())}_{self._task_counter}"

        if preferred_agent and preferred_agent in self.agents:
            agent = self.agents[preferred_agent]
        else:
            task_lower = task_description.lower()
            best_match = list(self.agents.values())[0]
            best_score = 0
            for agent in self.agents.values():
                score = self._score_agent(agent, task_lower)
                if score > best_score:
                    best_score = score
                    best_match = agent
            agent = best_match
            preferred_agent = agent.name

        agent.assign_task(task_id, task_description, {})
        return (
            f"### DELEGATION\n\n"
            f"**Task**: {task_description}\n"
            f"**Delegated to**: {preferred_agent} ({agent.description})\n"
            f"**Capabilities**: {', '.join(agent.capabilities)}\n"
            f"**Task ID**: {task_id}\n\n"
            f"Now execute the subtask. When done, report back."
        )

    def delegate_parallel(self, task_description: str, split_by: str = "auto") -> str:
        """
        Peer-to-peer: split a complex task across multiple agents, run in parallel.
        Returns merged results from all agents.
        """
        self._task_counter += 1
        task_id = f"ptask_{int(time.time())}_{self._task_counter}"
        task_lower = task_description.lower()

        # Score all agents and pick top matches
        scored = [(self._score_agent(a, task_lower), a) for a in self.agents.values()]
        scored.sort(key=lambda x: -x[0])
        top_agents = [a for _, a in scored if _ > 0]
        if not top_agents:
            top_agents = list(self.agents.values())[:1]

        # Assign to each agent in parallel (simulated)
        results = []
        for agent in top_agents:
            subtask_id = f"{task_id}_{agent.name}"
            agent.assign_task(subtask_id, f"{task_description} (handled by {agent.role})", {})
            results.append({
                "agent": agent.name,
                "role": agent.role,
                "capabilities": agent.capabilities,
                "status": "assigned",
            })

        self._results[task_id] = results

        lines = [f"### PEER-TO-PEER DELEGATION", f"**Task**: {task_description}", f"**Task ID**: {task_id}", ""]
        for r in results:
            lines.append(f"**{r['agent']}** ({r['role']})")
            lines.append(f"  Tools: {', '.join(r['capabilities'])}")
            lines.append(f"  Status: {r['status']}")
            lines.append("")
        lines.append("Execute each subtask independently and merge results when all complete.")
        return "\n".join(lines)

    def get_peer_results(self, task_id: str) -> str:
        """Get merged results from a peer-to-peer delegation."""
        results = self._results.get(task_id)
        if not results:
            return f"[FAIL] No results found for task: {task_id}"
        lines = [f"### MERGED RESULTS: {task_id}", ""]
        for r in results:
            lines.append(f"**{r['agent']}**: {r.get('result', 'pending')}")
        return "\n".join(lines)


#  Singleton  #

_system: Optional[MultiAgentSystem] = None


def get_multi_agent_system() -> MultiAgentSystem:
    global _system
    if _system is None:
        _system = MultiAgentSystem()
    return _system


#  Tool Function for Friday  #

def multi_agent_delegate(
    action: str = "list",
    task: str = None,
    agent: str = None,
    split_by: str = "auto",
) -> str:
    """
    Friday tool for multi-agent task delegation (peer-to-peer).
    Actions:
      list — show available agents
      delegate — assign to best single agent
      parallel — split work across multiple agents (peer-to-peer)
      agent_info — show agent details
    """
    system = get_multi_agent_system()

    if action == "list":
        return system.list_agents()

    if action == "delegate":
        if not task:
            return "[FAIL] Task description required."
        return system.delegate(task, preferred_agent=agent)

    if action == "parallel":
        if not task:
            return "[FAIL] Task description required."
        return system.delegate_parallel(task, split_by=split_by)

    if action == "results":
        if not task:
            return "[FAIL] Task ID required."
        return system.get_peer_results(task)

    if action == "agent_info":
        if not agent:
            return "[FAIL] Agent name required."
        a = system.get_agent(agent)
        if not a:
            return f"[FAIL] Agent not found: {agent}"
        return a.get_summary()

    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Multi-Agent System (v2 Peer-to-Peer)...\n")
    system = get_multi_agent_system()
    print(system.list_agents())
    print("\n--- Single Delegation ---")
    print(multi_agent_delegate("delegate", task="write a Python script"))
    print("\n--- Peer-to-Peer Delegation ---")
    print(multi_agent_delegate("parallel", task="research and code a web scraper"))
