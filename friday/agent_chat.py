"""
FRIDAY Inter-Agent Chat & Messaging System.

Enables agents to communicate via a shared townhall chat, private task channels,
@mentions, typing indicators, and persistent JSON-backed history.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from friday._paths import FRIDAY_MEMORY
from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

CHAT_STATE_FILE = os.path.join(FRIDAY_MEMORY, "agent_chat_state.json")
_LOCK: asyncio.Lock = asyncio.Lock()

# ── Status Constants ──────────────────────────────────────────

AGENT_STATUS_WORKING = "working"
AGENT_STATUS_WAITING = "waiting"
AGENT_STATUS_CHATTING = "chatting"
AGENT_STATUS_IDLE = "idle"

CHANNEL_TYPE_GENERAL = "general"
CHANNEL_TYPE_TASK = "task"
CHANNEL_TYPE_PRIVATE = "private"

# ── Data Models ───────────────────────────────────────────────


@dataclass
class AgentProfile:
    name: str
    role: str
    description: str = ""
    status: str = AGENT_STATUS_IDLE
    capabilities: List[str] = field(default_factory=list)
    current_task: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AgentProfile:
        return cls(**data)


@dataclass
class ChatMessage:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    content: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    channel: str = ""
    mentions: List[str] = field(default_factory=list)
    visible_thinking: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ChatMessage:
        return cls(**data)


@dataclass
class ChatChannel:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    type: str = CHANNEL_TYPE_GENERAL
    participants: List[str] = field(default_factory=list)
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "participants": self.participants,
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ChatChannel:
        messages = [ChatMessage.from_dict(m) for m in data.get("messages", [])]
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            type=data.get("type", CHANNEL_TYPE_GENERAL),
            participants=data.get("participants", []),
            messages=messages,
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
        )


# ── Chat System ───────────────────────────────────────────────


class AgentChatSystem:
    """Manages all chat channels, agent profiles, message routing, and persistence."""

    def __init__(self, state_file: str = CHAT_STATE_FILE) -> None:
        self.state_file: str = state_file
        self.agents: Dict[str, AgentProfile] = {}
        self.channels: Dict[str, ChatChannel] = {}
        self._pending_tasks: List[Dict[str, Any]] = []
        self._typing_indicators: Dict[str, Dict[str, float]] = {}  # channel_id -> {agent_name: timestamp}
        self._loaded: bool = False

    # ── Agent Management ──────────────────────────────────────

    async def register_agent(self, profile: AgentProfile) -> AgentProfile:
        async with _LOCK:
            self.agents[profile.name] = profile
            logger.info("Agent registered: %s (%s)", profile.name, profile.role)
            await self._save_state_locked()
            return profile

    async def set_agent_status(self, agent_name: str, status: str) -> Optional[AgentProfile]:
        async with _LOCK:
            agent = self.agents.get(agent_name)
            if agent is None:
                logger.warning("set_agent_status: unknown agent '%s'", agent_name)
                return None
            agent.status = status
            logger.info("Agent '%s' status -> %s", agent_name, status)
            await self._save_state_locked()
            return agent

    async def get_agent_info(self, agent_name: str) -> Optional[AgentProfile]:
        async with _LOCK:
            return self.agents.get(agent_name)

    async def list_agents(self) -> List[AgentProfile]:
        async with _LOCK:
            return list(self.agents.values())

    # ── Channel Management ────────────────────────────────────

    async def create_general_channel(self) -> ChatChannel:
        async with _LOCK:
            if "general" in self.channels:
                return self.channels["general"]
            channel = ChatChannel(
                id="general",
                name="Townhall Chat",
                type=CHANNEL_TYPE_GENERAL,
                participants=list(self.agents.keys()),
            )
            self.channels["general"] = channel
            logger.info("Created general channel")
            await self._save_state_locked()
            return channel

    async def create_task_channel(self, task_id: str, participants: List[str]) -> ChatChannel:
        async with _LOCK:
            channel_id = f"task_{task_id}"
            if channel_id in self.channels:
                return self.channels[channel_id]
            channel = ChatChannel(
                id=channel_id,
                name=f"Task: {task_id}",
                type=CHANNEL_TYPE_TASK,
                participants=participants,
            )
            self.channels[channel_id] = channel
            logger.info("Created task channel '%s' for %s", channel_id, participants)
            await self._save_state_locked()
            return channel

    # ── Messaging ─────────────────────────────────────────────

    async def send_message(
        self,
        sender: str,
        content: str,
        channel_id: str,
        mentions: Optional[List[str]] = None,
        thinking: Optional[str] = None,
    ) -> Optional[ChatMessage]:
        async with _LOCK:
            channel = self.channels.get(channel_id)
            if channel is None:
                logger.warning("send_message: unknown channel '%s'", channel_id)
                return None
            if sender not in self.agents:
                logger.warning("send_message: unknown sender '%s'", sender)
                return None

            msg = ChatMessage(
                sender=sender,
                content=content,
                channel=channel_id,
                mentions=mentions or [],
                visible_thinking=thinking,
            )
            channel.messages.append(msg)
            await self._save_state_locked()
            return msg

    async def get_channel_messages(self, channel_id: str, limit: int = 50) -> List[ChatMessage]:
        async with _LOCK:
            channel = self.channels.get(channel_id)
            if channel is None:
                return []
            return channel.messages[-limit:]

    async def mention_agent(self, agent_name: str, channel_id: str) -> Optional[str]:
        """Generate an @mention notification string for an agent."""
        async with _LOCK:
            channel = self.channels.get(channel_id)
            if channel is None:
                return None
            agent = self.agents.get(agent_name)
            if agent is None:
                return None
            return f"[MENTION] @{agent_name} has been called into channel '{channel.name}' ({channel_id})"

    # ── Thinking / Typing ─────────────────────────────────────

    async def add_thinking(
        self, agent_name: str, channel_id: str, thinking_text: str
    ) -> Optional[ChatMessage]:
        """Add a visible thinking block to a channel (shown as agent reasoning)."""
        async with _LOCK:
            channel = self.channels.get(channel_id)
            if channel is None:
                return None
            if agent_name not in self.agents:
                return None
            msg = ChatMessage(
                sender=agent_name,
                content="",
                channel=channel_id,
                visible_thinking=thinking_text,
            )
            channel.messages.append(msg)
            await self._save_state_locked()
            return msg

    async def set_typing(self, agent_name: str, channel_id: str, is_typing: bool) -> None:
        """Track typing indicator state for an agent in a channel."""
        async with _LOCK:
            if channel_id not in self._typing_indicators:
                self._typing_indicators[channel_id] = {}
            if is_typing:
                self._typing_indicators[channel_id][agent_name] = time.time()
            else:
                self._typing_indicators[channel_id].pop(agent_name, None)

    async def get_typing(self, channel_id: str) -> List[str]:
        """Return list of agent names currently typing in a channel."""
        async with _LOCK:
            now = time.time()
            indicators = self._typing_indicators.get(channel_id, {})
            active = []
            for agent_name, ts in indicators.items():
                if now - ts < 5.0:
                    active.append(agent_name)
            return active

    # ── Task Proposals ────────────────────────────────────────

    async def propose_task(
        self, proposer: str, description: str, required_agents: List[str]
    ) -> Dict[str, Any]:
        """Agent proposes a new task for approval and potential channel creation."""
        async with _LOCK:
            task_id = f"prop_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            proposal = {
                "task_id": task_id,
                "proposer": proposer,
                "description": description,
                "required_agents": required_agents,
                "status": "proposed",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._pending_tasks.append(proposal)
            logger.info(
                "Task proposed by '%s': %s (needs: %s)",
                proposer, description, required_agents,
            )
            await self._save_state_locked()
            return proposal

    async def approve_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Approve a proposed task and auto-create its channel."""
        async with _LOCK:
            for proposal in self._pending_tasks:
                if proposal["task_id"] == task_id:
                    proposal["status"] = "approved"
                    channel = await self._create_and_return_task_channel(
                        task_id, proposal["required_agents"]
                    )
                    proposal["channel_id"] = channel.id
                    await self._send_system_message(
                        channel.id,
                        f"Task approved. Proposed by @{proposal['proposer']}: {proposal['description']}",
                    )
                    logger.info("Task '%s' approved, channel created", task_id)
                    await self._save_state_locked()
                    return proposal
            return None

    async def reject_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        async with _LOCK:
            for proposal in self._pending_tasks:
                if proposal["task_id"] == task_id:
                    proposal["status"] = "rejected"
                    logger.info("Task '%s' rejected", task_id)
                    await self._save_state_locked()
                    return proposal
            return None

    async def list_pending_tasks(self) -> List[Dict[str, Any]]:
        async with _LOCK:
            return [p for p in self._pending_tasks if p["status"] == "proposed"]

    # ── Chat Summary (for memory injection) ───────────────────

    async def get_chat_summary(self, channel_id: str, max_messages: int = 20) -> str:
        """Return a concise summary of recent channel activity for prompt injection."""
        async with _LOCK:
            channel = self.channels.get(channel_id)
            if channel is None:
                return f"[Channel '{channel_id}' not found]"
            recent = channel.messages[-max_messages:]
            if not recent:
                return f"[No messages in '{channel.name}']"

            parts = [f"--- Chat Summary: {channel.name} ---"]
            for m in recent:
                prefix = f"[{m.sender}]"
                if m.visible_thinking:
                    prefix += " [thinking]"
                if m.mentions:
                    prefix += f" (mentions: {', '.join(m.mentions)})"
                body = m.content if m.content else "(thinking only)"
                parts.append(f"{prefix}: {body}")
            parts.append("--- End Summary ---")
            return "\n".join(parts)

    # ── Persistence ───────────────────────────────────────────

    async def save_state(self) -> None:
        async with _LOCK:
            await self._save_state_locked()

    async def load_state(self) -> None:
        async with _LOCK:
            await self._load_state_locked()

    async def _save_state_locked(self) -> None:
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        data = {
            "agents": {name: profile.to_dict() for name, profile in self.agents.items()},
            "channels": {cid: ch.to_dict() for cid, ch in self.channels.items()},
            "pending_tasks": self._pending_tasks,
            "typing_indicators": {
                cid: {name: ts for name, ts in agents.items()}
                for cid, agents in self._typing_indicators.items()
            },
            "_saved_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error("Failed to save chat state: %s", e)

    async def _load_state_locked(self) -> None:
        if not os.path.exists(self.state_file):
            self._loaded = True
            return
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load chat state (%s), starting fresh", e)
            self._loaded = True
            return

        self.agents = {}
        for name, profile_data in data.get("agents", {}).items():
            self.agents[name] = AgentProfile.from_dict(profile_data)

        self.channels = {}
        for cid, ch_data in data.get("channels", {}).items():
            self.channels[cid] = ChatChannel.from_dict(ch_data)

        self._pending_tasks = data.get("pending_tasks", [])
        self._typing_indicators = data.get("typing_indicators", {})
        self._loaded = True
        logger.info(
            "Loaded chat state: %d agents, %d channels, %d pending tasks",
            len(self.agents), len(self.channels), len(self._pending_tasks),
        )

    # ── Internals ─────────────────────────────────────────────

    async def _create_and_return_task_channel(self, task_id: str, participants: List[str]) -> ChatChannel:
        channel_id = f"task_{task_id}"
        if channel_id in self.channels:
            return self.channels[channel_id]
        channel = ChatChannel(
            id=channel_id,
            name=f"Task: {task_id}",
            type=CHANNEL_TYPE_TASK,
            participants=participants,
        )
        self.channels[channel_id] = channel
        return channel

    async def _send_system_message(self, channel_id: str, content: str) -> ChatMessage:
        channel = self.channels.get(channel_id)
        if channel is None:
            raise ValueError(f"Unknown channel: {channel_id}")
        msg = ChatMessage(
            sender="system",
            content=content,
            channel=channel_id,
        )
        channel.messages.append(msg)
        return msg


# ── Singleton ─────────────────────────────────────────────────

_system: Optional[AgentChatSystem] = None


def get_agent_chat_system() -> AgentChatSystem:
    """Return the global AgentChatSystem singleton, loading state if needed."""
    global _system
    if _system is None:
        _system = AgentChatSystem()
    return _system


# ── Memory Injection Helper ───────────────────────────────────


async def inject_chat_memory(agent_name: str, system_prompt: str) -> str:
    """Inject recent relevant chat history into an agent's system prompt.

    Reads the last 15 messages from channels the agent participates in
    and appends them to the prompt as context.
    """
    chat = get_agent_chat_system()
    if not chat._loaded:
        await chat.load_state()

    agent = await chat.get_agent_info(agent_name)
    if agent is None:
        return system_prompt

    summaries = []
    for cid, channel in chat.channels.items():
        if agent_name in channel.participants:
            summary = await chat.get_chat_summary(cid, max_messages=15)
            if "[No messages" not in summary:
                summaries.append(summary)

    if not summaries:
        return system_prompt

    memory_block = "\n\n".join(summaries)
    return f"{system_prompt}\n\n[CHAT CONTEXT]\n{memory_block}\n[/CHAT CONTEXT]"
