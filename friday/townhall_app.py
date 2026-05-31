"""FRIDAY Townhall — Textual TUI with n8n-style node connections."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from collections import deque
from datetime import datetime
from typing import Any

from rich.text import Text as RichText
from rich.panel import Panel as RichPanel
from rich.columns import Columns
from rich.style import Style

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Header, Input, RichLog, Static, Label, ListView, ListItem

from friday._paths import FRIDAY_MEMORY
from friday.agent_chat import (
    AGENT_STATUS_CHATTING,
    AGENT_STATUS_IDLE,
    AGENT_STATUS_WAITING,
    AGENT_STATUS_WORKING,
    AgentProfile,
)

TOWNHALL_STATE_PATH = os.path.join(FRIDAY_MEMORY, "townhall_state.json")

AGENT_PROFILES: list[tuple[str, str, str]] = [
    ("JARVIS", "System Core & Infrastructure", "cyan"),
    ("NOVA", "Research & Knowledge", "magenta"),
    ("ATLAS", "Data & Analytics", "blue"),
    ("SENTRY", "Security & Monitoring", "red"),
    ("FORGE", "Development & Tools", "yellow"),
    ("ECHO", "Communication & Outreach", "green"),
    ("AEGIS", "Protection & Compliance", "bright_blue"),
    ("CRUX", "Strategy & Planning", "bright_magenta"),
    ("VERSE", "Creative & Media", "bright_yellow"),
    ("LORE", "Memory & Context", "bright_green"),
]

AGENTS: list[AgentProfile] = [AgentProfile(name=n, role=r) for n, r, _ in AGENT_PROFILES]
AGENT_COLORS: dict[str, str] = {n: c for n, _, c in AGENT_PROFILES}

STATUS_SYMBOLS = {
    AGENT_STATUS_IDLE: "○",
    AGENT_STATUS_WORKING: "●",
    AGENT_STATUS_WAITING: "◐",
    AGENT_STATUS_CHATTING: "◉",
}

STATUS_COLORS = {
    AGENT_STATUS_IDLE: "gray",
    AGENT_STATUS_WORKING: "green",
    AGENT_STATUS_WAITING: "yellow",
    AGENT_STATUS_CHATTING: "cyan",
}


class AgentNode:
    def __init__(self, profile: AgentProfile):
        self.profile = profile
        self.status = AGENT_STATUS_IDLE
        self.last_seen = datetime.now()
        self.message_count = 0
        self.current_task = ""

    def to_dict(self) -> dict:
        return {
            "name": self.profile.name,
            "status": self.status,
            "last_seen": self.last_seen.isoformat(),
            "message_count": self.message_count,
            "current_task": self.current_task,
        }

    @classmethod
    def from_dict(cls, d: dict, profile: AgentProfile) -> AgentNode:
        n = cls(profile)
        n.status = d.get("status", AGENT_STATUS_IDLE)
        n.message_count = d.get("message_count", 0)
        n.current_task = d.get("current_task", "")
        return n


class TownhallApp(App):
    """Townhall — n8n-style node graph with agent seating chart."""

    TITLE = "TOWNHALL"
    SUB_TITLE = "Agent Command Center"

    CSS = """
    Screen {
        background: #050510;
    }

    Header {
        background: #0A0A1A;
        color: #00BFFF;
        text-style: bold;
    }

    #left-panel {
        width: 28;
        background: #080820;
        border-right: solid #1A1A3A;
        padding: 1;
    }

    #left-panel > Label {
        color: #00BFFF;
        text-style: bold;
        margin-bottom: 1;
    }

    #left-panel > Static {
        color: #AAAAAA;
        margin-bottom: 1;
    }

    #agent-list {
        height: 1fr;
    }

    #center-panel {
        height: 1fr;
        background: #050510;
        padding: 1;
    }

    #conference-chart {
        width: 100%;
        height: 100%;
    }

    #right-panel {
        width: 40;
        background: #080820;
        border-left: solid #1A1A3A;
    }

    #chat-log {
        height: 1fr;
        background: #080820;
        padding: 0 1;
    }

    #chat-input-container {
        height: 5;
        background: #0A0A1A;
        border-top: solid #1A1A3A;
        padding: 1;
    }

    #chat-input {
        background: #12122A;
        color: #00BFFF;
        border: solid #1A1A3A;
        padding: 0 1;
        height: 3;
    }

    #chat-input:focus {
        border: solid #00BFFF;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+r", "refresh", "Refresh"),
    ]

    def __init__(self):
        super().__init__()
        self.agents: list[AgentNode] = [AgentNode(p) for p in AGENTS]
        self._friday_status = AGENT_STATUS_IDLE
        self._current_channel = "general"
        self._selected_agent_idx = 0
        self._messages: deque[dict] = deque(maxlen=200)
        self._load_state()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(id="left-panel"):
            yield Label("F.R.I.D.A.Y")
            yield Static(id="friday-status")
            yield Static("")
            yield Label("AGENTS")
            yield ListView(id="agent-list")

        with Container(id="center-panel"):
            yield RichLog(id="conference-chart", highlight=True, markup=True)

        with Container(id="right-panel"):
            yield RichLog(id="chat-log", highlight=True, markup=True)
            with Container(id="chat-input-container"):
                yield Input(id="chat-input", placeholder="Message or @agent...")

    def on_mount(self):
        self._render_conference()
        self._render_agent_list()
        self._render_chat()
        self._update_friday_status()

    def _render_conference(self):
        chart = self.query_one("#conference-chart", RichLog)
        chart.clear()

        top_agents = self.agents[:3]
        top_cols = [self._make_agent_node(a) for a in top_agents]
        chart.write(Columns(top_cols, equal=True, padding=(0, 2)))
        chart.write(RichText("       │         │         │       ", style="dim gray37"))

        left = self._make_agent_node(self.agents[3]) if len(self.agents) > 3 else None
        right = self._make_agent_node(self.agents[4]) if len(self.agents) > 4 else None
        s = STATUS_SYMBOLS.get(self._friday_status, "●")
        c = STATUS_COLORS.get(self._friday_status, "green")
        friday = RichPanel(
            RichText(f" {s} F.R.I.D.A.Y\n  Sovereign AI", style=f"bold {c}", justify="center"),
            title="[bold cyan]FRIDAY[/bold cyan]",
            border_style="cyan",
            width=24,
            padding=(1, 2),
        )
        parts = []
        if left:
            parts.append(left)
        parts.append(RichText("─── ", style="dim gray37"))
        parts.append(friday)
        parts.append(RichText(" ───", style="dim gray37"))
        if right:
            parts.append(right)
        chart.write(Columns(parts, padding=(0, 1)))

        chart.write(RichText("       │         │         │       ", style="dim gray37"))

        bottom_agents = self.agents[5:8]
        if bottom_agents:
            chart.write(Columns(
                [self._make_agent_node(a) for a in bottom_agents],
                equal=True, padding=(0, 2),
            ))

        extra = self.agents[8:]
        if extra:
            chart.write(Columns(
                [self._make_agent_node(a) for a in extra],
                equal=True, padding=(0, 2),
            ))

    def _make_agent_node(self, agent: AgentNode) -> RichPanel:
        sym = STATUS_SYMBOLS.get(agent.status, "○")
        st_color = STATUS_COLORS.get(agent.status, "gray")
        ag_color = AGENT_COLORS.get(agent.profile.name, "white")
        task = f"\n[dim]{agent.current_task[:20]}[/dim]" if agent.current_task else ""
        return RichPanel(
            RichText(
                f" {sym} {agent.profile.name}\n [{st_color}]{agent.status.capitalize()}[/{st_color}]{task}",
                style=f"bold {ag_color}", justify="center",
            ),
            title=f"[{ag_color}]{agent.profile.role[:18]}[/{ag_color}]",
            border_style=st_color if agent.status == AGENT_STATUS_WORKING else "gray37",
            width=22, padding=(1, 1),
        )

    def _render_agent_list(self):
        lst = self.query_one("#agent-list", ListView)
        lst.clear()
        for a in self.agents:
            sym = STATUS_SYMBOLS.get(a.status, "○")
            color = STATUS_COLORS.get(a.status, "gray")
            task = f"\n  [dim]{a.current_task[:25]}[/dim]" if a.current_task else ""
            ag_color = AGENT_COLORS.get(a.profile.name, "white")
            lst.append(ListItem(
                Static(f"[{color}]{sym}[/{color}] [bold {ag_color}]{a.profile.name}[/bold {ag_color}]{task}")
            ))

    def _update_friday_status(self):
        w = self.query_one("#friday-status")
        sym = STATUS_SYMBOLS.get(self._friday_status, "●")
        color = STATUS_COLORS.get(self._friday_status, "green")
        w.update(f"[{color}]{sym}[/{color}] {self._friday_status.capitalize()}")

    def _render_chat(self):
        chat = self.query_one("#chat-log", RichLog)
        chat.clear()
        chat.write(RichText(f"Townhall — #{self._current_channel}", style="bold cyan"))
        for msg in self._messages:
            ts = msg.get("ts", "")
            sender = msg.get("sender", "")
            content = msg.get("content", "")
            kind = msg.get("kind", "message")
            if kind == "system":
                chat.write(RichText(f"  {ts}  {content}", style="dim gray"))
            elif kind == "mention":
                chat.write(RichText(f"  {ts}  @{sender}: {content}", style="bold yellow"))
            else:
                c = "cyan" if sender == "FRIDAY" else "green"
                chat.write(RichText(f"  {ts}  [{c}]{sender}[/{c}]: {content}", style="white"))

    def _add_message(self, sender: str, content: str, kind: str = "message"):
        self._messages.append({
            "ts": datetime.now().strftime("%H:%M"),
            "sender": sender,
            "content": content,
            "kind": kind,
        })
        self._render_chat()

    def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        if not text:
            return

        inp = self.query_one("#chat-input", Input)

        if "@" in text:
            mentioned = [a.profile.name for a in self.agents
                         if f"@{a.profile.name.lower()}" in text.lower()]
            if mentioned:
                for name in mentioned:
                    self._add_message(f"@{name}", text, "mention")
                inp.clear()
                self._save_state()
                return

        if text.startswith("/"):
            parts = text[1:].split()
            cmd = parts[0].lower()
            args = parts[1:]

            if cmd == "join" and args:
                self._current_channel = args[0]
                self._render_chat()
            elif cmd == "agents":
                names = "\n".join(f"  @{a.profile.name} — {a.profile.role}" for a in self.agents)
                self._add_message("SYSTEM", f"Available agents:\n{names}")
            elif cmd == "task" and len(args) >= 2:
                aname = args[0]
                task = " ".join(args[1:])
                for a in self.agents:
                    if a.profile.name.lower() == aname.lower():
                        a.current_task = task
                        a.status = AGENT_STATUS_WORKING
                        self._render_conference()
                        self._render_agent_list()
                        self._add_message("SYSTEM", f"Task assigned to @{aname}: {task}")
                        self._save_state()
                        break
            elif cmd == "clear":
                self._messages.clear()
                self._render_chat()
            elif cmd == "help":
                self._add_message("SYSTEM",
                    "/join <channel> — Switch channel\n"
                    "/task <agent> <desc> — Assign task\n"
                    "/agents — List agents\n"
                    "/clear — Clear chat\n"
                    "/help — This help"
                )

            inp.clear()
            return

        self._add_message("USER", text)
        self._save_state()
        inp.clear()

    def _save_state(self):
        try:
            os.makedirs(os.path.dirname(TOWNHALL_STATE_PATH), exist_ok=True)
            with open(TOWNHALL_STATE_PATH, "w") as f:
                json.dump({
                    "agents": [a.to_dict() for a in self.agents],
                    "current_channel": self._current_channel,
                    "friday_status": self._friday_status,
                }, f, indent=2)
        except Exception:
            pass

    def _load_state(self):
        try:
            if not os.path.exists(TOWNHALL_STATE_PATH):
                return
            with open(TOWNHALL_STATE_PATH) as f:
                data = json.load(f)
            for saved in data.get("agents", []):
                name = saved.get("name")
                for a in self.agents:
                    if a.profile.name == name:
                        a.status = saved.get("status", AGENT_STATUS_IDLE)
                        a.current_task = saved.get("current_task", "")
                        a.message_count = saved.get("message_count", 0)
            self._current_channel = data.get("current_channel", "general")
            self._friday_status = data.get("friday_status", AGENT_STATUS_IDLE)
        except Exception:
            pass

    def action_refresh(self):
        self._render_conference()
        self._render_agent_list()
        self._render_chat()
        self._update_friday_status()

    def update_agent_status(self, name: str, status: str, task: str = ""):
        for a in self.agents:
            if a.profile.name.lower() == name.lower():
                a.status = status
                if task:
                    a.current_task = task
                a.last_seen = datetime.now()
                self._render_conference()
                self._render_agent_list()
                self._save_state()
                return

    def set_friday_status(self, status: str):
        self._friday_status = status
        self._update_friday_status()
        self._render_conference()


def launch_townhall() -> dict:
    """Launch townhall in a new terminal window."""
    script = [
        sys.executable or "python",
        "-c",
        "import asyncio; from friday.townhall_app import TownhallApp; TownhallApp().run()",
    ]
    try:
        proc = subprocess.Popen(
            ["cmd.exe", "/c", "start", "Townhall", "/wait", *script],
            shell=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        return {"success": True, "pid": proc.pid}
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    TownhallApp().run()
