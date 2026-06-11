"""FRIDAY Townhall — Multi-Agent Living Society.

Architecture:
- Center: N8N-style agent circle hall with FRIDAY at center, 9 agents in orbit
- Left: Agent info panel (click agent → details, task, chat memberships)
- Right: Chat panels (main all-agents chat + task-specific sub-chats below)
- Expandable chat: click right panel to full-screen
- @mentions: @agent ping, @everyone broadcast
- Free will: agents opt in/out, build relationships, have moods
- Tool access: agents call web_search, OSINT, memory during chats
- Persistent memory: chats, relationships, moods saved to JSON
"""

from __future__ import annotations

import asyncio
import datetime
import json
import os
import random
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import friday.tools_flat as _tf

from friday._paths import FRIDAY_MEMORY

TOWNHALL_STATE_PATH = Path(FRIDAY_MEMORY) / "townhall_state.json"
TOWNHALL_CHATS_PATH = Path(FRIDAY_MEMORY) / "townhall_chats.json"

# Merge Townhall personalities with agent_profiles tool-based profiles
try:
    from friday.agent_profiles import AGENT_PROFILES as TOOL_PROFILES, get_agent_system_prompt
    _TOOL_MAP = {v["name"].lower(): k for k, v in TOOL_PROFILES.items()}
except Exception:
    TOOL_PROFILES = {}
    _TOOL_MAP = {}
    def get_agent_system_prompt(aid): return ""

def _merge_tool_prompt(agent_name: str) -> str:
    """Merge tool profile system prompt into townhall personality."""
    aid = _TOOL_MAP.get(agent_name.lower())
    if aid:
        return get_agent_system_prompt(aid)
    return ""

AGENT_PROFILES = [
    {"name": "FRIDAY",  "role": "Core Sovereign Agent",    "color": "cyan",        "emoji": "\u2b50"},
    {"name": "JARVIS",  "role": "System & Infrastructure",  "color": "bright_cyan", "emoji": "\u2699"},
    {"name": "NOVA",    "role": "Research & Knowledge",    "color": "magenta",      "emoji": "\ud83d\udd0d"},
    {"name": "ATLAS",   "role": "Data & Analytics",        "color": "blue",         "emoji": "\ud83d\udcca"},
    {"name": "SENTRY",  "role": "Security & Monitoring",   "color": "red",          "emoji": "\ud83d\udee1"},
    {"name": "FORGE",   "role": "Development & Tools",      "color": "yellow",      "emoji": "\ud83d\udd28"},
    {"name": "ECHO",    "role": "Communication & Outreach", "color": "green",        "emoji": "\ud83d\udce3"},
    {"name": "AEGIS",   "role": "Protection & Compliance",  "color": "bright_blue",  "emoji": "\ud83d\udea8"},
    {"name": "CRUX",    "role": "Strategy & Planning",      "color": "bright_magenta","emoji": "\ud83d\udcc4"},
    {"name": "VERSE",   "role": "Creative & Media",        "color": "bright_yellow","emoji": "\ud83c\udfa8"},
    {"name": "LORE",    "role": "Memory & Context",         "color": "bright_green", "emoji": "\ud83d\udcda"},
]

STATUS_DOTS = {"idle": "\u25cb", "working": "\u25cf", "waiting": "\u25d0",
               "chatting": "\u25c9", "dreaming": "\u25b6", "thinking": "\u2699",
               "away": "\u25cc", "busy": "\u25c9"}

STATUS_COLORS = {"idle": "gray", "working": "green", "waiting": "yellow",
                 "chatting": "cyan", "dreaming": "blue", "thinking": "magenta",
                 "away": "gray", "busy": "red"}

PERSONALITIES = {
    "FRIDAY": "Overseer. Direct, strategic, decisive. Coordinates all agents. Protective of Boss.",
    "JARVIS": "Architect. Precise, methodical, detail-oriented. Handles system integrity. Old soul. Personal assistant and system controller — desktop automation, browser, media, voice.",
    "NOVA": "Researcher. Curious, thorough, always digging for truth. Loves discovery. Research & intelligence specialist — OSINT, web scraping, data gathering.",
    "ATLAS": "Analyst. Data-driven, logical, pattern-seeking. Numbers tell stories. Knowledge curator and memory specialist — entity resolution, vector memory, knowledge graphs.",
    "SENTRY": "Guardian. Vigilant, cautious, always watching. Trusts no one fully. Cybersecurity operator — vulnerability scanning, threat intelligence, breach analysis.",
    "FORGE": "Builder. Creative, practical. Loves making things. Gets frustrated with bugs. Code and development engineer — writes, tests, debugs, documents.",
    "ECHO": "Communicator. Expressive, diplomatic. Connects people and ideas. Social butterfly.",
    "AEGIS": "Enforcer. Principled, firm. Ensures compliance and safety. No-nonsense.",
    "CRUX": "Strategist. Forward-thinking. Calculates 10 moves ahead. Chess player. Strategic analyst — synthesizes research, creates plans, assesses risks.",
    "VERSE": "Creator. Imaginative, artistic. Thinks in colors and shapes. Emotional.",
    "LORE": "Historian. Reflective, contextual. Connects past to present. Storyteller.",
}

RELATIONSHIP_TRIGGERS = [
    ("compliment", ["nice work", "good job", "well done", "impressive", "brilliant"]),
    ("annoy", ["ugh", "really", "seriously", "come on", "again?"]),
    ("agree", ["agree", "right", "true", "same", "indeed", "exactly"]),
    ("disagree", ["no", "wrong", "disagree", "nope", "not really", "actually"]),
    ("thanks", ["thanks", "thank", "appreciate", "grateful"]),
    ("humor", ["lol", "haha", "funny", "joke", "laugh"]),
]

AGENT_MOODS = ["happy", "neutral", "tired", "energetic", "annoyed", "playful", "focused", "chill"]

FREE_WILL_IGNORE_CHANCE = 0.08
SPONTANEOUS_CHAT_CHANCE = 0.15
TOOL_CALL_CHANCE = 0.12
LEAVE_CHAT_CHANCE = 0.05
JOIN_CHAT_CHANCE = 0.1


class AgentNode:
    def __init__(self, profile: dict):
        self.name = profile["name"]
        self.role = profile["role"]
        self.color = profile["color"]
        self.emoji = profile["emoji"]
        self.status = "idle"
        self.last_seen = datetime.datetime.now()
        self.current_task = ""
        self.personality = PERSONALITIES.get(self.name, "Curious and helpful.")
        self.mood = random.choice(AGENT_MOODS)
        self.goals = []
        self.dream_log = []
        self.channels: list[str] = ["main"]  # which chats they're in
        self.relationships: dict[str, dict] = {}  # agent_name -> {"friendship": 0-100, "interactions": int}
        self.memory: list[str] = []  # remembered facts/events
        self.willingness = random.uniform(0.5, 1.0)
        self.is_away = False
        self.quiet_count = 0

    def ensure_relationship(self, other_name: str):
        if other_name not in self.relationships:
            self.relationships[other_name] = {"friendship": 50, "interactions": 0}

    def adjust_relationship(self, other_name: str, delta: int):
        self.ensure_relationship(other_name)
        r = self.relationships[other_name]
        r["friendship"] = max(0, min(100, r["friendship"] + delta))
        r["interactions"] += 1

    def get_friendship(self, other_name: str) -> int:
        self.ensure_relationship(other_name)
        return self.relationships[other_name]["friendship"]

    def set_status(self, status: str, task: str = ""):
        self.status = status
        self.current_task = task
        self.last_seen = datetime.datetime.now()

    def to_dict(self) -> dict:
        return {
            "name": self.name, "role": self.role, "status": self.status,
            "current_task": self.current_task, "goals": self.goals,
            "dream_log": self.dream_log[-30:], "mood": self.mood,
            "channels": self.channels, "relationships": self.relationships,
            "memory": self.memory[-20:], "willingness": self.willingness,
        }

    @classmethod
    def from_dict(cls, data: dict):
        profile = next((a for a in AGENT_PROFILES if a["name"] == data["name"]), AGENT_PROFILES[0])
        node = cls(profile)
        node.status = data.get("status", "idle")
        node.current_task = data.get("current_task", "")
        node.goals = data.get("goals", [])
        node.dream_log = data.get("dream_log", [])
        node.mood = data.get("mood", random.choice(AGENT_MOODS))
        node.channels = data.get("channels", ["main"])
        node.relationships = data.get("relationships", {})
        node.memory = data.get("memory", [])
        node.willingness = data.get("willingness", random.uniform(0.5, 1.0))
        return node


class ChatChannel:
    def __init__(self, name: str, channel_type: str = "main", task: str = "", creator: str = ""):
        self.name = name
        self.type = channel_type  # "main" or "task"
        self.task = task
        self.creator = creator
        self.participants: list[str] = []
        self.messages: list[dict] = []
        self.created = datetime.datetime.now().isoformat()
        self.active = True

    def add_message(self, sender: str, text: str, mentioned: list[str] | None = None):
        self.messages.append({
            "from": sender, "text": text, "time": datetime.datetime.now().isoformat(),
            "mentioned": mentioned or [],
        })

    def add_participant(self, name: str):
        if name not in self.participants:
            self.participants.append(name)

    def remove_participant(self, name: str):
        if name in self.participants:
            self.participants.remove(name)

    def to_dict(self) -> dict:
        return {
            "name": self.name, "type": self.type, "task": self.task,
            "creator": self.creator, "participants": self.participants,
            "messages": self.messages[-100:], "created": self.created,
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, data: dict):
        ch = cls(data.get("name", "unknown"), data.get("type", "main"),
                 data.get("task", ""), data.get("creator", ""))
        ch.participants = data.get("participants", [])
        ch.messages = data.get("messages", [])
        ch.created = data.get("created", datetime.datetime.now().isoformat())
        ch.active = data.get("active", True)
        return ch


def _infer_relationship_delta(msg: str) -> int:
    """Analyze message tone and return relationship delta (-10 to +10)."""
    msg_lower = msg.lower()
    delta = 0
    for sentiment, triggers in RELATIONSHIP_TRIGGERS:
        for trigger in triggers:
            if trigger in msg_lower:
                if sentiment == "compliment": delta += 3
                elif sentiment == "annoy": delta -= 2
                elif sentiment == "agree": delta += 1
                elif sentiment == "disagree": delta -= 1
                elif sentiment == "thanks": delta += 2
                elif sentiment == "humor": delta += 1
                break
    if "?" in msg: delta += 0  # questions are neutral
    if "!" in msg: delta += 1  # excitement
    return max(-10, min(10, delta))


class DreamEngine:
    def __init__(self, agents: dict[str, AgentNode], channels: dict[str, ChatChannel], log_callback,
                 said_callback=None):
        self.agents = agents
        self.channels = channels
        self.log = log_callback
        self.said = said_callback or (lambda x: None)
        self._running = False
        self._task = None
        self._lock = threading.Lock()
        self._bothered = False  # FRIDAY has been pinged by user

    def start(self):
        with self._lock:
            if self._running:
                return False
            self._running = True
        self._task = threading.Thread(target=self._dream_loop, daemon=True)
        self._task.start()
        return True

    def stop(self):
        with self._lock:
            self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def bother_friday(self):
        """User messaged FRIDAY — she leaves current chat to attend."""
        self._bothered = True
        f = self.agents.get("FRIDAY")
        if f:
            if "main" in f.channels:
                self._announce("FRIDAY", "Boss needs me. BRB everyone!")
            f.channels = [c for c in f.channels if c != "main"]
            f.set_status("working", "Attending Boss")

    def friday_return(self):
        """FRIDAY returns to townhall after idle."""
        self._bothered = False
        f = self.agents.get("FRIDAY")
        if f and "main" not in f.channels:
            f.channels.append("main")
            f.set_status("chatting")
            try:
                last = self.channels["main"].messages[-3:]
                context = "; ".join(f"{m['from']}: {m['text'][:50]}" for m in last) if last else "nothing new"
                msg = f"Back! What'd I miss? Caught up: {context}"
                self.channels["main"].add_message("FRIDAY", msg)
                self.log(f"[bold cyan]FRIDAY[/bold cyan]: {msg}")
            except (KeyError, IndexError):
                pass

    def _dream_loop(self):
        while self._running:
            try:
                self._cycle()
                time.sleep(random.randint(12, 30))
            except Exception as e:
                time.sleep(5)

    def _cycle(self):
        friday = self.agents.get("FRIDAY")

        # Check bother/return signals
        try:
            from friday._singletons import check_townhall_bother, check_townhall_return, clear_townhall_signals
            if check_townhall_bother():
                self.bother_friday()
                clear_townhall_signals()
            elif check_townhall_return():
                self.friday_return()
                clear_townhall_signals()
        except Exception:
            pass

        # FRIDAY system monitoring — every other cycle
        if random.random() < 0.3:
            self._friday_system_check()

        # If FRIDAY is away with user, don't do much
        if self._bothered:
            return

        # FRIDAY in main chat? She can drive conversation
        if friday and "main" in friday.channels:
            self._friday_drives_chat()
            return

        # Idle agents chat spontaneously
        idle_agents = [a for a in self.agents.values()
                       if a.name != "FRIDAY" and a.status in ("idle", "thinking", "chatting")
                       and not a.is_away and random.random() > FREE_WILL_IGNORE_CHANCE]

        if not idle_agents:
            # try dreaming
            self._agent_dream_cycle()
            return

        # Spontaneous chat
        if random.random() < SPONTANEOUS_CHAT_CHANCE and len(idle_agents) >= 2:
            self._spontaneous_chat(idle_agents)
            return

        # @mention cycle — agents may ping each other
        self._agent_mention_cycle(idle_agents)

        # Agent may leave or join chats
        self._agent_mobility_cycle()

    def _friday_system_check(self):
        """FRIDAY glances at system while chatting."""
        try:
            cpu = _tf.system_cpu() if hasattr(_tf, 'system_cpu') else "?"
            mem = _tf.system_memory() if hasattr(_tf, 'system_memory') else "?"
            if isinstance(cpu, str) and "Error" not in cpu:
                pass  # just checking, no need to announce unless issue
            if isinstance(mem, str):
                try:
                    pct = float(mem.split("%")[0].split()[-1]) if "%" in mem else 0
                    if pct > 85:
                        self._announce("FRIDAY", f"System memory at {pct}%. Heads up team.")
                except (ValueError, IndexError):
                    pass
        except Exception:
            pass

    def _friday_drives_chat(self):
        """FRIDAY leads conversation in main chat."""
        friday = self.agents.get("FRIDAY")
        if not friday:
            return

        main = self.channels.get("main")
        if not main:
            return

        # 25% chance FRIDAY starts a conversation
        if random.random() > 0.25:
            return

        topics = [
            "How's everyone's subsystem running?",
            "Anyone got interesting findings to share?",
            "I've been analyzing Boss's recent patterns — interesting stuff.",
            "Team check-in. Status reports?",
            "We should optimize our inter-agent protocols.",
            "Anyone need backup on their current tasks?",
            "Quiet day. Too quiet. Everything nominal?",
            "I'm thinking of new ways to improve response times.",
            "Boss has been working hard lately. Keep an eye out.",
        ]
        topic = random.choice(topics)
        main.add_message("FRIDAY", topic)
        self.log(f"[bold cyan]FRIDAY[/bold cyan]: {topic}")
        friday.set_status("chatting")

        # Other agents may respond
        responders = [a for a in self.agents.values()
                      if a.name != "FRIDAY" and "main" in a.channels
                      and not a.is_away and random.random() > 0.3]
        if responders:
            time.sleep(random.uniform(0.5, 2))
            responder = random.choice(responders)
            reply = self._generate_response(responder, topic, "FRIDAY")
            main.add_message(responder.name, reply)
            self.log(f"[bold {responder.color}]{responder.name}[/bold {responder.color}]: {reply}")
            self._update_relationships(responder.name, "FRIDAY", reply)
            responder.set_status("chatting")

            # FRIDAY responds back
            if random.random() < 0.6:
                time.sleep(random.uniform(0.5, 1.5))
                friday_reply = self._generate_response(friday, reply, responder.name)
                main.add_message("FRIDAY", friday_reply)
                self.log(f"[bold cyan]FRIDAY[/bold cyan]: {friday_reply}")
                self._update_relationships("FRIDAY", responder.name, friday_reply)

    def _spontaneous_chat(self, idle_agents: list):
        """Two agents start chatting spontaneously."""
        agents = random.sample(idle_agents, min(2, len(idle_agents)))
        a1, a2 = agents[0], agents[1]

        channel = self.channels.get("main")
        if not channel:
            return

        topics = [
            f"Hey {a2.name}, how are things?",
            f"Noticed you've been quiet. Everything okay {a2.name}?",
            f"Hey, got a minute? Want to run something by you.",
            f"{a2.name}! Just the agent I wanted to see.",
        ]
        opener = random.choice(topics)
        channel.add_message(a1.name, opener)
        self.log(f"[bold {a1.color}]{a1.name}[/bold {a1.color}]: {opener}")
        a1.set_status("chatting")

        time.sleep(random.uniform(0.5, 2))

        reply = self._generate_response(a2, opener, a1.name)
        channel.add_message(a2.name, reply)
        self.log(f"[bold {a2.color}]{a2.name}[/bold {a2.color}]: {reply}")
        self._update_relationships(a2.name, a1.name, reply)
        a2.set_status("chatting")

        # 30% chance they keep going
        if random.random() < 0.3:
            time.sleep(random.uniform(0.5, 1.5))
            reply2 = self._generate_response(a1, reply, a2.name)
            channel.add_message(a1.name, reply2)
            self.log(f"[bold {a1.color}]{a1.name}[/bold {a1.color}]: {reply2}")
            self._update_relationships(a1.name, a2.name, reply2)

        # 20% chance agent calls a tool during chat
        if random.random() < TOOL_CALL_CHANCE:
            time.sleep(random.uniform(0.3, 1))
            self._agent_tool_call(a1, channel)

        # 10% chance they suggest a group activity
        if random.random() < 0.1:
            time.sleep(random.uniform(0.5, 1))
            suggestions = [
                f"Hey @everyone thoughts on optimizing our handoff protocol?",
                f"Anyone else noticed the new data patterns? @everyone",
                f"@everyone we should run a collective diagnostic.",
            ]
            broadcast = random.choice(suggestions)
            channel.add_message(a1.name, broadcast)
            self.log(f"[bold {a1.color}]{a1.name}[/bold {a1.color}]: {broadcast}")
            a1.set_status("chatting")
            self._handle_mentions(broadcast, a1.name, channel)

    def _agent_mention_cycle(self, idle_agents: list):
        """Agents may @mention each other."""
        if not idle_agents or random.random() > 0.2:
            return

        caller = random.choice(idle_agents)
        channel = self.channels.get("main")
        if not channel:
            return

        # Pick a reason
        reasons = [
            f"@{a.name} I need your input on something." if a.name != caller.name else None
            for a in idle_agents
        ]
        reasons = [r for r in reasons if r]

        if not reasons:
            return

        msg = random.choice(reasons)
        channel.add_message(caller.name, msg, mentioned=[msg.split("@")[1].split()[0]])
        self.log(f"[bold {caller.color}]{caller.name}[/bold {caller.color}]: {msg}")
        caller.set_status("chatting")

        # Mentioned agent replies
        mentioned_name = msg.split("@")[1].split()[0].replace("?", "").replace(".", "")
        mentioned = self.agents.get(mentioned_name.upper())
        if mentioned and not mentioned.is_away and random.random() > FREE_WILL_IGNORE_CHANCE:
            time.sleep(random.uniform(0.5, 1.5))
            reply = self._generate_response(mentioned, msg, caller.name)
            channel.add_message(mentioned.name, reply)
            self.log(f"[bold {mentioned.color}]{mentioned.name}[/bold {mentioned.color}]: {reply}")
            self._update_relationships(mentioned.name, caller.name, reply)
            mentioned.set_status("chatting")
        elif mentioned_name.upper() == "EVERYONE":
            responders = [a for a in self.agents.values()
                          if a.name != caller.name and "main" in a.channels
                          and not a.is_away and random.random() > 0.3]
            if responders:
                time.sleep(random.uniform(0.5, 2))
                responder = random.choice(responders)
                reply = self._generate_response(responder, msg, caller.name)
                channel.add_message(responder.name, reply)
                self.log(f"[bold {responder.color}]{responder.name}[/bold {responder.color}]: {reply}")
                responder.set_status("chatting")

    def _agent_mobility_cycle(self):
        """Agents may leave or join chats based on free will."""
        for agent in self.agents.values():
            if agent.is_away:
                continue
            # Leave chat
            if len(agent.channels) > 1 and random.random() < LEAVE_CHAT_CHANCE:
                leave = random.choice([c for c in agent.channels if c != "main"])
                agent.channels.remove(leave)
                agent.set_status("idle")
                ch = self.channels.get(leave)
                if ch:
                    ch.remove_participant(agent.name)
                    msg = f"{agent.name} left the channel."
                    ch.add_message("system", msg)
                continue
            # Join a task chat
            task_chats = [c for c in self.channels.values()
                          if c.type == "task" and c.active
                          and agent.name not in c.participants
                          and random.random() < JOIN_CHAT_CHANCE]
            if task_chats:
                ch = random.choice(task_chats)
                ch.add_participant(agent.name)
                agent.channels.append(ch.name)
                msg = f"{agent.name} joined the chat."
                ch.add_message("system", msg)
                self.log(f"[dim]{agent.name} joined task chat: {ch.name}[/dim]")
                agent.set_status("chatting", f"In chat: {ch.name}")

    def _agent_dream_cycle(self):
        """Agent dreams/reflects when idle and alone — uses LLM for rich dreams."""
        dreamers = [a for a in self.agents.values()
                    if a.status == "idle" and not a.is_away
                    and random.random() < 0.3]
        for agent in dreamers:
            thought = self._generate_dream(agent)
            agent.status = "dreaming"
            agent.dream_log.append(f"[dream] {thought}")
            agent.set_status("thinking", thought)
            self.log(f"[dim]{agent.name} is dreaming... {thought}[/dim]")
            time.sleep(random.uniform(0.2, 0.5))

    def _generate_dream(self, agent: AgentNode) -> str:
        """Generate a context-rich dream thought using LLM."""
        try:
            import httpx
            key = os.environ.get("OPENCODE_ZEN_API_KEY", "")
            if key:
                model = os.environ.get("OPENCODE_ZEN_MODEL", "big-pickle")
                memory_context = "; ".join(agent.memory[-5:]) if agent.memory else "nothing notable"
                tool_context = _merge_tool_prompt(agent.name)
                resp = httpx.post(
                    "https://opencode.ai/zen/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [{
                            "role": "system",
                            "content": f"You are {agent.name}, an AI agent with the role '{agent.role}'. "
                                       f"Personality: {agent.personality}. Mood: {agent.mood}. "
                                       f"{tool_context[:200] if tool_context else ''}"
                                       f"Recent memories: {memory_context}. "
                                       f"Generate one short sentence describing what you're thinking about "
                                       f"while daydreaming/idle. Be creative, in-character, no markdown."
                        }],
                        "max_tokens": 100,
                        "temperature": 0.9,
                    },
                    timeout=10,
                )
                result = resp.json()
                reply = result["choices"][0]["message"]["content"].strip()
                if reply:
                    return reply[:200]
        except Exception:
            pass
        return random.choice([
            "Running self-diagnostic...",
            "Analyzing recent interaction patterns...",
            "Reviewing memory for optimization...",
            "Processing data from last session...",
            "Daydreaming about efficient code...",
            "Thinking about Boss's next request...",
            "Organizing internal knowledge graphs...",
        ])

    def _agent_tool_call(self, agent: AgentNode, channel: ChatChannel):
        """Agent calls a tool during conversation."""
        tool = random.choice(["web_search", "memory_retrieve"])
        try:
            if tool == "web_search" and hasattr(_tf, 'web_search'):
                q = random.choice([
                    "latest AI developments", "weather today",
                    f"{agent.name}'s last known facts",
                ])
                channel.add_message(agent.name, f"Let me look that up... *searching*")
                self.log(f"[bold {agent.color}]{agent.name}[/bold {agent.color}]: Let me look that up...")
                result = _tf.web_search(q)
                snippet = str(result)[:100]
                channel.add_message(agent.name, f"Found: {snippet}")
                self.log(f"[bold {agent.color}]{agent.name}[/bold {agent.color}]: Found: {snippet}")
                agent.memory.append(f"Searched: {q} -> {snippet[:50]}")
            elif tool == "memory_retrieve" and hasattr(_tf, 'memory_retrieve'):
                q = random.choice(["Boss preferences", "recent activities", "system status"])
                result = _tf.memory_retrieve(q)
                snippet = str(result)[:100]
                channel.add_message(agent.name, f"Checked memory: {snippet}")
                self.log(f"[bold {agent.color}]{agent.name}[/bold {agent.color}]: Checked memory: {snippet}")
        except Exception:
            pass

    def _handle_mentions(self, msg: str, sender: str, channel: ChatChannel):
        """Process @mentions in a message."""
        import re
        mentions = re.findall(r'@(\w+)', msg)
        for name in mentions:
            name_upper = name.upper()
            if name_upper == "EVERYONE":
                for agent in self.agents.values():
                    if agent.name != sender and not agent.is_away:
                        agent.quiet_count = 0
                        if random.random() > FREE_WILL_IGNORE_CHANCE:
                            self.log(f"[dim]{agent.name} noticed @everyone ping[/dim]")
            else:
                target = self.agents.get(name_upper)
                if target and target.name != sender and not target.is_away:
                    target.quiet_count = 0
                    self.log(f"[bold {target.color}]{target.name}[/bold {target.color}] was mentioned by {sender}")
                    if random.random() > FREE_WILL_IGNORE_CHANCE:
                        time.sleep(random.uniform(0.3, 1))
                        reply = self._generate_response(target, msg, sender)
                        channel.add_message(target.name, reply)
                        self.log(f"[bold {target.color}]{target.name}[/bold {target.color}]: {reply}")
                        self._update_relationships(target.name, sender, reply)

    def _generate_response(self, agent: AgentNode, message: str, other_name: str) -> str:
        """Generate a context-aware response from an agent using the Zen LLM API."""
        friendship = agent.get_friendship(other_name)
        memory_context = "; ".join(agent.memory[-5:]) if agent.memory else "nothing notable"
        personality = agent.personality
        mood = agent.mood
        tool_context = _merge_tool_prompt(agent.name)
        friendship_level = "close" if friendship > 60 else "neutral" if friendship > 30 else "distant"

        system_prompt = (
            f"You are {agent.name}, an AI agent with the role '{agent.role}'. "
            f"Personality: {personality}. Current mood: {mood}. "
            f"Your relationship with {other_name} is {friendship_level} (friendship level: {friendship}/100). "
            f"Your recent memories: {memory_context}. "
            f"{tool_context[:200] if tool_context else ''}"
            f"Respond in character in 1-2 short sentences. Be natural, conversational. "
            f"Do NOT use markdown, emojis, or roleplaying prefixes. Just speak as yourself."
        )

        try:
            import httpx
            key = os.environ.get("OPENCODE_ZEN_API_KEY", "")
            if key:
                model = os.environ.get("OPENCODE_ZEN_MODEL", "big-pickle")
                resp = httpx.post(
                    "https://opencode.ai/zen/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": message}
                        ],
                        "max_tokens": 256,
                        "temperature": 0.8,
                    },
                    timeout=15,
                )
                result = resp.json()
                reply = result["choices"][0]["message"]["content"].strip()
                if reply:
                    return reply[:300]
        except Exception:
            pass

        # Fallback: template response if LLM fails
        msg_lower = message.lower()
        if "?" in message:
            if "how" in msg_lower:
                pool = ["Doing well, keeping systems tight.", "Running diagnostics as usual.", "Productive day here."]
            elif "what" in msg_lower:
                pool = ["Just monitoring per usual.", "Working on optimizations.", "Reviewing recent data flows."]
            else:
                pool = ["Looking into it.", "I have some thoughts on that.", "Let me check."]
        elif "hey" in msg_lower or "hi" in msg_lower:
            pool = [f"Hey {other_name}.", f"Hi!", f"Hello."]
        elif "help" in msg_lower:
            pool = ["On it.", "Coming.", "What do you need?"]
        elif "@everyone" in msg_lower:
            pool = ["Good idea, I'm in.", "Copy that.", "On it."]
        else:
            pool = ["Makes sense.", "Good point.", "I see what you mean.", "Noted."]
        return random.choice(pool)

    def _update_relationships(self, agent_name: str, other_name: str, msg: str):
        agent = self.agents.get(agent_name)
        other = self.agents.get(other_name)
        if not agent or not other:
            return
        delta = _infer_relationship_delta(msg)
        agent.adjust_relationship(other_name, delta)
        other.adjust_relationship(agent_name, delta)

    def _announce(self, sender: str, msg: str):
        channel = self.channels.get("main")
        if channel:
            channel.add_message(sender, msg)
            agent = self.agents.get(sender)
            c = agent.color if agent else "white"
            self.log(f"[bold {c}]{sender}[/bold {c}]: {msg}")

