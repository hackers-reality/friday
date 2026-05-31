"""
FRIDAY Townhall Terminal — live agent seating chart, inter-agent chat,
task channels, status visualization, and @mention system.

Renders a split-screen terminal UI using rich.layout + rich.live:
  Left panel  — conference table with agents positioned around FRIDAY
  Right panel — main chat (top) and task-specific channels (bottom)

Interaction via keyboard commands and @mentions typed at the prompt.
State is persisted to JSON so the townhall survives restarts.
"""
from __future__ import annotations

import asyncio
import json
import os
import textwrap
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from rich.align import Align
from rich.box import HEAVY, HEAVY_EDGE, MINIMAL, ROUNDED, SQUARE
from rich.columns import Columns
from rich.console import Console, ConsoleOptions, RenderResult, RenderableType, Group
from rich.layout import Layout
from rich.live import Live
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.spinner import Spinner
from rich.style import Style
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from friday._paths import FRIDAY_MEMORY
from friday.agent_chat import (
    AGENT_STATUS_CHATTING,
    AGENT_STATUS_IDLE,
    AGENT_STATUS_WAITING,
    AGENT_STATUS_WORKING,
    AgentChatSystem,
    AgentProfile,
    ChatChannel,
    ChatMessage,
)
from friday.agent_profiles import AGENT_PROFILES

# ── Constants ──────────────────────────────────────────────────────────────

TOWNHALL_STATE_FILE = os.path.join(FRIDAY_MEMORY, "townhall_state.json")
REFRESH_INTERVAL = 0.25  # seconds between Live refresh

FRIDAY_COLOR = "bold bright_green"
FRIDAY_EMOJI = "🧠"

AGENT_COLORS: Dict[str, str] = {
    "veronica": "bright_yellow",
    "forge": "bright_blue",
    "ghost": "bright_red",
    "atlas": "bright_cyan",
    "jarvis": "bright_magenta",
    "organizer": "bright_cyan",
    "planner": "yellow",
    "sandbox_runner": "green",
    "pr_reviewer": "bright_magenta",
}

AGENT_EMOJIS: Dict[str, str] = {
    "veronica": "🔍",
    "forge": "⚙️",
    "ghost": "👻",
    "atlas": "🗺️",
    "jarvis": "🤖",
    "organizer": "📋",
    "planner": "📐",
    "sandbox_runner": "🛡️",
    "pr_reviewer": "📝",
    "friday": "🧠",
}

STATUS_DOTS: Dict[str, Tuple[str, str]] = {
    AGENT_STATUS_WORKING: ("●", "bold green"),
    AGENT_STATUS_WAITING: ("●", "bold blue"),
    AGENT_STATUS_CHATTING: ("●", "bold bright_magenta"),
    AGENT_STATUS_IDLE: ("○", "bright_black"),
}

MAX_CHAT_LINES = 80
MAX_VISIBLE_MESSAGES = 30

# Unicode box-drawing helpers
_HORIZ = "─"
_VERT = "│"
_CROSS = "┼"
_TEE_DOWN = "┬"
_TEE_UP = "┴"
_TEE_RIGHT = "├"
_TEE_LEFT = "┤"
_CORNER_TL = "┌"
_CORNER_TR = "┐"
_CORNER_BL = "└"
_CORNER_BR = "┘"
_DOT = "•"
_ARROW_R = "→"
_ARROW_D = "↓"


# ── Data Structures ────────────────────────────────────────────────────────


@dataclass
class TownhallState:
    """Persistent state for the Townhall UI."""
    agent_positions: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    expanded_chat: bool = False
    selected_agent: Optional[str] = None
    active_task_channels: List[str] = field(default_factory=list)
    visible_tasks: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_positions": {k: list(v) for k, v in self.agent_positions.items()},
            "expanded_chat": self.expanded_chat,
            "selected_agent": self.selected_agent,
            "active_task_channels": self.active_task_channels,
            "visible_tasks": self.visible_tasks,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TownhallState:
        positions = {}
        for k, v in data.get("agent_positions", {}).items():
            positions[k] = tuple(v)
        return cls(
            agent_positions=positions,
            expanded_chat=data.get("expanded_chat", False),
            selected_agent=data.get("selected_agent"),
            active_task_channels=data.get("active_task_channels", []),
            visible_tasks=data.get("visible_tasks", {}),
        )


# ── Seating Chart Renderable ───────────────────────────────────────────────


class AgentSeatingRenderable:
    """Custom renderable that draws the conference table with agents.

    Uses a 2D character-buffer approach so we can place box-drawing
    glyphs, agent labels, and connecting lines wherever we want.
    """

    TABLE_WIDTH = 50
    TABLE_HEIGHT = 22
    CELL_W = 12  # chars per cell column
    CELL_H = 3   # lines per cell row

    def __init__(
        self,
        agents: Dict[str, AgentProfile],
        agent_positions: Dict[str, Tuple[int, int]],
        collaborating_pairs: Set[Tuple[str, str]],
        selected_agent: Optional[str] = None,
    ) -> None:
        self.agents = agents
        self.agent_positions = agent_positions
        self.collaborating_pairs = collaborating_pairs
        self.selected_agent = selected_agent

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        lines = self._build_lines()
        for line in lines:
            yield line

    def _build_lines(self) -> List[Text]:
        """Build the seating chart as a list of Text lines."""
        buf: List[List[str]] = []
        for _ in range(self.TABLE_HEIGHT):
            buf.append([" "] * self.TABLE_WIDTH)
        # Colour buffer tracks which cells have which colour
        color_buf: List[List[Optional[str]]] = []
        for _ in range(self.TABLE_HEIGHT):
            color_buf.append([None] * self.TABLE_WIDTH)

        def _set(r: int, c: int, ch: str, color: Optional[str] = None) -> None:
            if 0 <= r < self.TABLE_HEIGHT and 0 <= c < self.TABLE_WIDTH:
                buf[r][c] = ch
                color_buf[r][c] = color

        def _write(
            r: int, c: int, text: str, color: Optional[str] = None
        ) -> None:
            for i, ch in enumerate(text):
                _set(r, c + i, ch, color)

        def _hline(r: int, c1: int, c2: int, color: Optional[str] = None) -> None:
            for c in range(c1, c2 + 1):
                if buf[r][c] in (" ", "─"):
                    _set(r, c, "─", color)

        def _vline(c: int, r1: int, r2: int, color: Optional[str] = None) -> None:
            for r in range(r1, r2 + 1):
                if buf[r][c] in (" ", "│"):
                    _set(r, c, "│", color)

        # ── Table border ───────────────────────────────────────────────
        table_top = 1
        table_bot = self.TABLE_HEIGHT - 2
        table_left = 2
        table_right = self.TABLE_WIDTH - 3

        # Border edges
        _hline(table_top, table_left, table_right, "bright_white")
        _hline(table_bot, table_left, table_right, "bright_white")
        _vline(table_left, table_top, table_bot, "bright_white")
        _vline(table_right, table_top, table_bot, "bright_white")

        # Corners
        _set(table_top, table_left, "┌", "bright_white")
        _set(table_top, table_right, "┐", "bright_white")
        _set(table_bot, table_left, "└", "bright_white")
        _set(table_bot, table_right, "┘", "bright_white")

        # Table title
        title = " TOWNHALL TABLE "
        tx = (table_left + table_right - len(title)) // 2
        _write(table_top, tx, title, "bright_white")

        # ── FRIDAY center ─────────────────────────────────────────────
        friday_row = 9
        friday_col = 18
        friday_label = f"  {FRIDAY_EMOJI} FRIDAY  "
        fl = len(friday_label)
        f_start = friday_col - fl // 2
        _set(friday_row, friday_col - 3, "╭", FRIDAY_COLOR)
        _set(friday_row, friday_col + 3, "╮", FRIDAY_COLOR)
        _set(friday_row + 2, friday_col - 3, "╰", FRIDAY_COLOR)
        _set(friday_row + 2, friday_col + 3, "╯", FRIDAY_COLOR)
        _vline(friday_col - 3, friday_row, friday_row + 2, FRIDAY_COLOR)
        _vline(friday_col + 3, friday_row, friday_row + 2, FRIDAY_COLOR)
        _hline(friday_row, friday_col - 2, friday_col + 2, FRIDAY_COLOR)
        _hline(friday_row + 2, friday_col - 2, friday_col + 2, FRIDAY_COLOR)
        _write(friday_row, friday_col - 5, friday_label, FRIDAY_COLOR)
        _write(friday_row + 1, friday_col - 6, "  orchestrator  ", "bright_green")

        # ── Agent positions around the table ──────────────────────────
        # We'll compute agent slot placements dynamically
        slots = [
            (2, 6, "top_left"),
            (2, 22, "top_mid"),
            (2, 36, "top_right"),
            (5, 2, "mid_left_1"),
            (5, 38, "mid_right_1"),
            (8, 2, "mid_left_2"),
            (8, 38, "mid_right_2"),
            (14, 6, "bot_left"),
            (14, 22, "bot_mid"),
            (14, 36, "bot_right"),
        ]

        sorted_agents = list(self.agents.items())
        placed: List[Tuple[str, int, int]] = []

        for i, (name, profile) in enumerate(sorted_agents):
            if name == "friday":
                continue
            if i < len(slots):
                sr, sc, _ = slots[i]
            else:
                sr, sc = 3 + (i * 2) % 12, 3 + (i * 6) % 34
            placed.append((name, sr, sc))
            self.agent_positions[name] = (sc, sr)

        # Draw each agent card
        for name, sr, sc in placed:
            profile = self.agents.get(name)
            if not profile:
                continue
            is_sel = name == self.selected_agent
            color = AGENT_COLORS.get(name, "white")
            if is_sel:
                color = f"bold reverse {color}"
            emoji = AGENT_EMOJIS.get(name, "🤖")
            status = profile.status if profile else AGENT_STATUS_IDLE
            sd, scolor = STATUS_DOTS.get(status, ("○", "bright_black"))
            short = name[:8].capitalize()

            # Card border
            card_w = 10
            card_h = 3
            _set(sr, sc, "┌", color)
            _set(sr, sc + card_w - 1, "┐", color)
            _set(sr + card_h - 1, sc, "└", color)
            _set(sr + card_h - 1, sc + card_w - 1, "┘", color)
            _hline(sr, sc + 1, sc + card_w - 2, color)
            _hline(sr + card_h - 1, sc + 1, sc + card_w - 2, color)
            _vline(sc, sr + 1, sr + card_h - 2, color)
            _vline(sc + card_w - 1, sr + 1, sr + card_h - 2, color)

            # Agent label
            label = f" {emoji} {short}"
            _write(sr, sc + 1, label[:card_w - 2], color)
            # Status & dot
            status_text = f" {sd} {status[:4]}"
            color_name = scolor if not is_sel else f"reverse {scolor}"
            _write(sr + 1, sc + 1, status_text[:card_w - 2], color_name)

        # ── Connecting lines: FRIDAY → each agent ────────────────────
        cx, cy = friday_col, friday_row + 1
        for name, sr, sc in placed:
            ax = sc + 5  # center of agent card
            ay = sr + 1
            self._draw_connection(buf, color_buf, cx, cy, ax, ay, name)

        # ── Collaborating pair lines ─────────────────────────────────
        for a1, a2 in self.collaborating_pairs:
            if a1 in self.agent_positions and a2 in self.agent_positions:
                x1, y1 = self.agent_positions[a1]
                x2, y2 = self.agent_positions[a2]
                # Adjust to agent card centers
                x1, y1 = x1 + 5, y1 + 1
                x2, y2 = x2 + 5, y2 + 1
                self._draw_dashed_line(buf, color_buf, x1, y1, x2, y2, "bright_yellow")

        # Convert buffer to Text lines
        result: List[Text] = []
        for r in range(self.TABLE_HEIGHT):
            line_parts: List[Tuple[str, Optional[str]]] = []
            for c in range(self.TABLE_WIDTH):
                line_parts.append((buf[r][c], color_buf[r][c]))
            t = Text()
            for ch, clr in line_parts:
                if clr:
                    t.append(ch, style=clr)
                else:
                    t.append(ch)
            result.append(t)

        return result

    def _draw_connection(
        self,
        buf: List[List[str]],
        color_buf: List[List[Optional[str]]],
        x1: int, y1: int,
        x2: int, y2: int,
        agent_name: str,
    ) -> None:
        """Draw a solid line between (x1,y1) and (x2,y2) using box drawing."""
        color = AGENT_COLORS.get(agent_name, "bright_white")
        dx = x2 - x1
        dy = y2 - y1
        steps = max(abs(dx), abs(dy))
        if steps == 0:
            return
        for i in range(1, steps):
            t = i / steps
            x = int(x1 + dx * t)
            y = int(y1 + dy * t)
            if 0 <= y < self.TABLE_HEIGHT and 0 <= x < self.TABLE_WIDTH:
                if buf[y][x] == " ":
                    if abs(dx) > abs(dy):
                        buf[y][x] = "─"
                    else:
                        buf[y][x] = "│"
                    color_buf[y][x] = color

    def _draw_dashed_line(
        self,
        buf: List[List[str]],
        color_buf: List[List[Optional[str]]],
        x1: int, y1: int,
        x2: int, y2: int,
        color: str,
    ) -> None:
        """Draw a dashed (collaboration) line between two points."""
        dx = x2 - x1
        dy = y2 - y1
        steps = max(abs(dx), abs(dy))
        if steps == 0:
            return
        for i in range(1, steps, 2):
            t = i / steps
            x = int(x1 + dx * t)
            y = int(y1 + dy * t)
            if 0 <= y < self.TABLE_HEIGHT and 0 <= x < self.TABLE_WIDTH:
                if buf[y][x] == " ":
                    buf[y][x] = "·"
                    color_buf[y][x] = color


# ── Townhall UI ────────────────────────────────────────────────────────────


class TownhallUI:
    """Main Townhall terminal renderer.

    Provides a live split-screen view of:
      - Agent seating chart with FRIDAY at the center
      - Townhall chat panel (top right)
      - Task-specific chat panels (bottom right)
      - Agent info dialogs (full-screen overlay when selected)

    Use :meth:`run` as the entry point.
    """

    def __init__(self, chat_system: AgentChatSystem) -> None:
        self.chat = chat_system
        self.console = Console()
        self.state = TownhallState()
        self._load_state()

        # Runtime buffers
        self.message_buffer: Dict[str, deque] = {}
        self._typing_agents: List[str] = []
        self._collaborating_pairs: Set[Tuple[str, str]] = set()
        self._pending_mentions: List[str] = []
        self._input_line = ""
        self._mode = "idle"  # idle | dialog | help
        self._running = True
        self._task_spinners: Dict[str, Spinner] = {}

    # ── Public API ─────────────────────────────────────────────────────────

    async def run(self) -> None:
        """Start the townhall render loop and input handler."""
        await self.chat.load_state()
        await self._ensure_general_channel()
        await self._sync_agents_from_profiles()

        # Start background tasks
        asyncio.create_task(self._periodic_refresh())
        asyncio.create_task(self._input_listener())

        # Main render loop
        layout = self._build_layout()
        try:
            with Live(
                layout,
                console=self.console,
                screen=True,
                auto_refresh=False,
                refresh_per_second=4,
            ) as live:
                while self._running:
                    layout = self._build_layout()
                    live.update(layout)
                    await asyncio.sleep(REFRESH_INTERVAL)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            self._save_state()
            self.console.print("\n[bold]Townhall session ended.[/bold]")

    # ── Layout Builder ─────────────────────────────────────────────────────

    def _build_layout(self) -> Layout:
        """Assemble the full terminal layout."""
        layout = Layout()
        layout.split_column(
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3),
        )

        if self._mode == "dialog" and self.state.selected_agent:
            layout["main"].split_row(
                Layout(name="dialog", ratio=40),
                Layout(name="seating", ratio=60),
            )
            layout["dialog"].update(self._render_agent_dialog(self.state.selected_agent))
        elif self._mode == "help":
            layout["main"].update(self._render_help_screen())
            layout["footer"].update(self._render_footer())
            return layout
        else:
            if self.state.expanded_chat:
                layout["main"].split_row(
                    Layout(name="seating", ratio=30),
                    Layout(name="chat_area", ratio=70),
                )
            else:
                layout["main"].split_row(
                    Layout(name="seating", ratio=50),
                    Layout(name="chat_area", ratio=50),
                )

        layout["seating"].update(self._render_agent_seating())

        # Right side: chat panels
        chat_area = Layout()
        chat_area.split_column(
            Layout(name="main_chat", ratio=6),
            Layout(name="task_chats", ratio=4),
        )
        chat_area["main_chat"].update(self._render_chat_panel())
        chat_area["task_chats"].update(self._render_task_chats())
        layout["chat_area"] = chat_area

        layout["footer"].update(self._render_footer())

        return layout

    # ── Agent Seating ──────────────────────────────────────────────────────

    def _render_agent_seating(self) -> Panel:
        """Render the conference table with seated agents."""
        agents = self.chat.agents
        seating = AgentSeatingRenderable(
            agents=agents,
            agent_positions=self.state.agent_positions,
            collaborating_pairs=self._collaborating_pairs,
            selected_agent=self.state.selected_agent,
        )

        # Legend
        legend_items = [
            Text("●", style="bold green") + Text(" Work", style="green"),
            Text("  ●", style="bold blue") + Text(" Wait", style="blue"),
            Text("  ●", style="bold bright_magenta") + Text(" Chat", style="bright_magenta"),
            Text("  ○", style="bright_black") + Text(" Idle", style="bright_black"),
        ]
        legend = Text("  ").join(legend_items)

        status_count = self._count_statuses()
        stats = Text(
            f"  🟢{status_count[AGENT_STATUS_WORKING]} 🔵{status_count[AGENT_STATUS_WAITING]} "
            f"💗{status_count[AGENT_STATUS_CHATTING]} ⚪{status_count[AGENT_STATUS_IDLE]}",
            style="bright_black",
        )

        content = Group(
            seating,
            Rule(style="dim"),
            Align.center(Group(legend, stats)),
        )

        subtitle = " | ".join(
            f"[{AGENT_COLORS.get(n, 'white')}]● {n.capitalize()}[/]"
            for n in sorted(self.chat.agents.keys())
            if n != "friday"
        )

        border_style = "bright_cyan"
        if self.state.selected_agent:
            border_style = "bold bright_yellow"

        return Panel(
            content,
            title="[bold]🤝 AGENT TABLE[/bold]",
            subtitle=f"[dim]{subtitle[:60]}[/dim]",
            border_style=border_style,
            padding=(0, 1),
            box=HEAVY_EDGE,
        )

    def _count_statuses(self) -> Dict[str, int]:
        counts: Dict[str, int] = {
            AGENT_STATUS_WORKING: 0,
            AGENT_STATUS_WAITING: 0,
            AGENT_STATUS_CHATTING: 0,
            AGENT_STATUS_IDLE: 0,
        }
        for p in self.chat.agents.values():
            s = p.status or AGENT_STATUS_IDLE
            if s in counts:
                counts[s] += 1
        return counts

    # ── Chat Panel ─────────────────────────────────────────────────────────

    def _render_chat_panel(self) -> Panel:
        """Main townhall chat panel showing recent messages."""
        channel = self.chat.channels.get("general")
        if not channel:
            return Panel(
                "[dim]No chat channel yet…[/dim]",
                title="[bold]💬 Townhall Chat[/bold]",
                border_style="bright_green",
                box=HEAVY_EDGE,
            )

        messages = channel.messages[-MAX_VISIBLE_MESSAGES:]
        renderables: List[RenderableType] = []

        for msg in messages:
            renderables.append(self._format_message(msg))

        # Typing indicators
        typing = self._typing_agents
        if typing:
            typing_text = Text(
                f"  {', '.join(t.capitalize() for t in typing)} typing" + ("…" if len(typing) == 1 else "…"),
                style="bright_black italic",
            )
            renderables.append(typing_text)

        if not renderables:
            renderables.append(Text("  [No messages yet. Type @agent to chat.]", style="dim italic"))

        content = Group(*renderables)

        # Header info
        agent_count = len(self.chat.agents)
        msg_count = len(channel.messages)
        header = f"[dim]{agent_count} agents • {msg_count} messages[/dim]"

        border = "bold bright_green" if self.state.expanded_chat else "bright_green"

        return Panel(
            content,
            title=f"[bold]💬 Townhall Chat[/bold] {header}",
            border_style=border,
            padding=(0, 1),
            box=HEAVY_EDGE,
            subtitle="[dim]!expand to toggle full width[/dim]" if not self.state.expanded_chat else "[bold]✦ EXPANDED[/bold]",
        )

    def _format_message(self, msg: ChatMessage) -> RenderableType:
        """Format a single chat message for display."""
        sender_color = AGENT_COLORS.get(msg.sender, "white")
        emoji = AGENT_EMOJIS.get(msg.sender, "💬")
        ts = ""
        try:
            dt = datetime.fromisoformat(msg.timestamp)
            ts = dt.strftime("%H:%M")
        except (ValueError, TypeError):
            ts = "??:??"

        # Header line
        header = Text()
        if msg.sender == "system":
            header.append(f"  ⚡ {msg.content}", style="bright_black italic")
            return header
        if msg.sender == "friday":
            header.append(f"  {FRIDAY_EMOJI} ", style=FRIDAY_COLOR)
        else:
            header.append(f"  {emoji} ", style=sender_color)

        header.append(f"[{msg.sender}]", style=sender_color)
        header.append(f" {ts}", style="dim")

        if msg.mentions:
            header.append(" 📢", style="bright_yellow")

        # Thinking indicator
        lines: List[RenderableType] = [header]
        if msg.visible_thinking:
            think_text = textwrap.shorten(msg.visible_thinking, width=50, placeholder="...")
            lines.append(
                Text(f"    🤔 {think_text}", style="bright_black italic")
            )

        # Content
        if msg.content:
            content_text = Text(f"    {msg.content}", style="white")
            lines.append(content_text)

        return Group(*lines)

    # ── Task Chat Panels ───────────────────────────────────────────────────

    def _render_task_chats(self) -> Panel:
        """Render task-specific chat panels stacked vertically."""
        task_channels = [
            ch for cid, ch in self.chat.channels.items()
            if ch.type == "task" and cid != "general"
        ]

        if not task_channels:
            return Panel(
                "[dim]No active task channels. Agents form teams automatically when needed.[/dim]",
                title="[bold]📋 Task Channels[/bold]",
                border_style="bright_blue",
                box=HEAVY_EDGE,
            )

        channel_views: List[RenderableType] = []
        for ch in task_channels[-4:]:  # show last 4
            visible = self.state.visible_tasks.get(ch.id, True)
            if not visible:
                continue
            msgs = ch.messages[-8:]
            msg_lines: List[RenderableType] = []
            for m in msgs:
                c = AGENT_COLORS.get(m.sender, "white")
                e = AGENT_EMOJIS.get(m.sender, "💬")
                txt = Text(f"  {e} [{m.sender}] ", style=c)
                if m.content:
                    summary = textwrap.shorten(m.content, width=40, placeholder="...")
                    txt.append(summary, style="white")
                elif m.visible_thinking:
                    txt.append("🤔 thinking…", style="bright_black italic")
                msg_lines.append(txt)

            if not msg_lines:
                msg_lines.append(Text("  [waiting for messages…]", style="dim italic"))

            # Task participants
            parts = Text(
                f"   [{', '.join(p.capitalize() for p in ch.participants[:4])}]",
                style="dim",
            )

            panel = Panel(
                Group(*msg_lines),
                title=f"[bold]{ch.name}[/bold]",
                subtitle=parts,
                border_style="bright_blue",
                box=MINIMAL,
                padding=(0, 1),
                height=6,
            )
            channel_views.append(panel)

        if not channel_views:
            channel_views.append(Text("[dim]No visible task channels[/dim]", style="dim italic"))

        return Panel(
            Group(*channel_views),
            title="[bold]📋 Active Tasks[/bold]",
            border_style="bright_blue",
            box=HEAVY_EDGE,
        )

    # ── Agent Dialog ───────────────────────────────────────────────────────

    def _render_agent_dialog(self, agent_name: str) -> Panel:
        """Full agent info dialog shown when an agent is selected."""
        profile = self.chat.agents.get(agent_name)
        if not profile:
            return Panel("[red]Agent not found[/red]", title="Error", border_style="red")

        proto = AGENT_PROFILES.get(agent_name, {})
        color = AGENT_COLORS.get(agent_name, "white")
        emoji = AGENT_EMOJIS.get(agent_name, "🤖")
        sd, scolor = STATUS_DOTS.get(profile.status or AGENT_STATUS_IDLE, ("○", "bright_black"))

        lines: List[RenderableType] = []

        # Identity
        id_table = Table.grid(padding=(0, 2))
        id_table.add_column(style="bold", width=16)
        id_table.add_column()
        id_table.add_row("Name", f"[{color}]{profile.name.capitalize()}[/{color}]")
        id_table.add_row("Role", f"[italic]{proto.get('description', profile.role)}[/italic]")
        id_table.add_row("Status", f"[{scolor}]{sd} {profile.status.upper()}[/{scolor}]")
        id_table.add_row("Current Task", profile.current_task or "[dim]None[/dim]")
        lines.append(id_table)

        lines.append(Rule(style="dim"))

        # Capabilities
        caps = profile.capabilities or proto.get("tools", [])
        if caps:
            cap_text = Text()
            for i, c in enumerate(caps[:12]):
                if i > 0:
                    cap_text.append(" • ", style="dim")
                cap_text.append(c, style="cyan")
            if len(caps) > 12:
                cap_text.append(f" … +{len(caps) - 12} more", style="dim")
            lines.append(Text("\nCapabilities:", style="bold underline"))
            lines.append(Padding(cap_text, (0, 2)))

        lines.append(Rule(style="dim"))

        # Collaborators
        collaborators = [
            n for n in self.chat.agents.keys()
            if n != agent_name and n != "friday"
        ]
        if collaborators:
            collab = Text("Collaborators: ", style="bold")
            for i, n in enumerate(collaborators):
                if i > 0:
                    collab.append("  ", style="dim")
                ac = AGENT_COLORS.get(n, "white")
                ae = AGENT_EMOJIS.get(n, "🤖")
                collab.append(f"{ae} {n.capitalize()}", style=ac)
            lines.append(collab)

        lines.append(Rule(style="dim"))
        lines.append(Text("  [Press 0 to close, or click another agent]", style="bright_black italic"))

        border_color = f"bold {color}" if color != "white" else "bold bright_white"

        return Panel(
            Group(*lines),
            title=f"[bold]{emoji} Agent Profile: {agent_name.capitalize()}[/bold]",
            border_style=border_color,
            box=HEAVY_EDGE,
            padding=(1, 2),
        )

    # ── Help Screen ────────────────────────────────────────────────────────

    def _render_help_screen(self) -> Panel:
        """Full help overlay."""
        help_table = Table.grid(padding=(0, 4))
        help_table.add_column(style="bold bright_yellow", width=24)
        help_table.add_column()

        help_table.add_row("!agent_name", "Show agent info dialog")
        help_table.add_row("!expand", "Toggle chat panel expansion")
        help_table.add_row("!help / !h", "Show this help screen")
        help_table.add_row("!quit / !q", "Exit Townhall")
        help_table.add_row("@name <msg>", "Mention & message an agent")
        help_table.add_row("@all <msg>", "Message all agents")
        help_table.add_row("!cls", "Clear screen")
        help_table.add_row("", "")
        help_table.add_row("Shortcut keys:", "")
        help_table.add_row("  1-9", "Select agent by position")
        help_table.add_row("  0 / Esc", "Close dialog / deselect")
        help_table.add_row("  Enter", "Send typed message")
        help_table.add_row("  Tab", "Cycle task channel focus")

        return Panel(
            Group(
                Text("[bold]TOWNHALL COMMANDS[/bold]", style="bold bright_white"),
                Rule(style="dim"),
                help_table,
                Rule(style="dim"),
                Text(
                    "Messages typed without @ prefix go to the townhall chat.\n"
                    "All agents see the general channel. Task channels are auto-created.",
                    style="bright_black italic",
                ),
            ),
            title="[bold]❓ Help[/bold]",
            border_style="bright_yellow",
            box=HEAVY_EDGE,
            padding=(1, 2),
        )

    # ── Footer ─────────────────────────────────────────────────────────────

    def _render_footer(self) -> Panel:
        """Bottom input bar with status info."""
        typing_count = len(self._typing_agents)
        status_text = []
        if typing_count:
            status_text.append(f"[bold bright_magenta]✍ {typing_count} typing[/bold bright_magenta]")
        if self.state.selected_agent:
            status_text.append(f"[bold yellow]► {self.state.selected_agent}[/bold yellow]")
        if self.state.expanded_chat:
            status_text.append("[green]▣ Expanded[/green]")

        status = "  ".join(status_text) if status_text else "[dim]● Ready[/dim]"
        agents_online = sum(1 for p in self.chat.agents.values() if p.status != AGENT_STATUS_IDLE)

        prompt = Text()
        prompt.append(" ⚡ ", style="bright_green")
        if self._input_line:
            prompt.append(self._input_line, style="white")
        else:
            prompt.append("Type @agent message or !help", style="bright_black italic")

        content = Group(
            Text(f"  {status}    |    [dim]{agents_online} agents online[/dim]", style="bright_black"),
            prompt,
        )

        return Panel(
            content,
            border_style="bright_black",
            box=SQUARE,
            padding=(0, 1),
        )

    # ── Input Handling ─────────────────────────────────────────────────────

    async def _input_listener(self) -> None:
        """Background task that reads keyboard input line by line."""
        while self._running:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input()
                )
            except (EOFError, KeyboardInterrupt):
                self._running = False
                break

            line = line.strip()
            if not line:
                continue

            self._input_line = line
            await self._handle_input(line)
            self._input_line = ""

    async def _handle_input(self, cmd: str) -> None:
        """Process a command or message line."""
        # Quit
        if cmd.lower() in ("!quit", "!q", "!exit"):
            self._running = False
            return

        # Help
        if cmd.lower() in ("!help", "!h", "?"):
            self._mode = "help" if self._mode != "help" else "idle"
            return

        # Clear
        if cmd.lower() == "!cls":
            self.console.clear()
            return

        # Expand chat
        if cmd.lower() in ("!expand", "!toggle"):
            self.state.expanded_chat = not self.state.expanded_chat
            self._save_state()
            return

        # Select agent by number
        if cmd.isdigit():
            num = int(cmd)
            agents = [n for n in sorted(self.chat.agents.keys()) if n != "friday"]
            if 1 <= num <= len(agents):
                self.state.selected_agent = agents[num - 1]
                self._mode = "dialog"
            elif num == 0:
                self.state.selected_agent = None
                self._mode = "idle"
            return

        # Select agent by !name
        if cmd.startswith("!"):
            name = cmd[1:].strip().lower()
            if name in self.chat.agents:
                if self.state.selected_agent == name:
                    self.state.selected_agent = None
                    self._mode = "idle"
                else:
                    self.state.selected_agent = name
                    self._mode = "dialog"
            else:
                # Try partial match
                matches = [a for a in self.chat.agents.keys() if a.startswith(name)]
                if matches:
                    self.state.selected_agent = matches[0]
                    self._mode = "dialog"
            return

        # @mentions
        if cmd.startswith("@"):
            await self._handle_mention(cmd)
            return

        # Regular message → general channel
        if cmd:
            await self.chat.send_message(
                sender="friday",
                content=cmd,
                channel_id="general",
            )

    async def _handle_mention(self, cmd: str) -> None:
        """Parse @mention command and route message."""
        parts = cmd.split(" ", 1)
        mention_part = parts[0].lstrip("@").lower()
        message = parts[1] if len(parts) > 1 else ""

        if mention_part == "all":
            targets = [n for n in self.chat.agents.keys() if n != "friday"]
        else:
            targets = [mention_part]
            if mention_part not in self.chat.agents:
                close = [a for a in self.chat.agents.keys() if a.startswith(mention_part)]
                if close:
                    targets = [close[0]]
                else:
                    await self.chat.send_message(
                        sender="friday",
                        content=f"Unknown agent @{mention_part}. Try: @all, "
                                f"@{', @'.join(sorted(self.chat.agents.keys())[:5])}",
                        channel_id="general",
                    )
                    return

        # Route to general or appropriate task channel
        channel_id = "general"
        if not message:
            message = f"Called {', '.join(t.capitalize() for t in targets)} to chat."

        msg = await self.chat.send_message(
            sender="friday",
            content=message,
            channel_id=channel_id,
            mentions=targets,
        )

        if msg:
            notif = await self.chat.mention_agent(targets[0], channel_id)
            if notif:
                await self.chat.send_message(
                    sender="system",
                    content=notif,
                    channel_id=channel_id,
                )

    # ── Periodic Refresh ───────────────────────────────────────────────────

    async def _periodic_refresh(self) -> None:
        """Background task: update typing indicators and collaborating pairs."""
        while self._running:
            try:
                # Typing indicators
                typing = await self.chat.get_typing("general")
                self._typing_agents = typing

                # Collaboration detection: agents on same task channel
                self._collaborating_pairs.clear()
                task_channels = [
                    ch for ch in self.chat.channels.values()
                    if ch.type == "task"
                ]
                for ch in task_channels:
                    parts = ch.participants
                    for i in range(len(parts)):
                        for j in range(i + 1, len(parts)):
                            self._collaborating_pairs.add((parts[i], parts[j]))

                # Save state periodically
                self._save_state()

                await asyncio.sleep(2.0)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(2.0)

    # ── Helpers ────────────────────────────────────────────────────────────

    async def _ensure_general_channel(self) -> None:
        """Make sure the general townhall channel exists."""
        await self.chat.create_general_channel()

    async def _sync_agents_from_profiles(self) -> None:
        """Sync known agent profiles into the chat system."""
        for agent_id, profile_data in AGENT_PROFILES.items():
            if agent_id not in self.chat.agents:
                profile = AgentProfile(
                    name=agent_id,
                    role=profile_data.get("description", agent_id)[:60],
                    description=profile_data.get("description", ""),
                    capabilities=profile_data.get("tools", []),
                    status=AGENT_STATUS_IDLE,
                )
                await self.chat.register_agent(profile)

        # Ensure FRIDAY is always registered
        if "friday" not in self.chat.agents:
            friday_profile = AgentProfile(
                name="friday",
                role="Orchestrator & System Core",
                description="Central AI orchestrator managing all sub-agents and communications.",
                capabilities=[
                    "agent_spawn", "agent_delegate", "orchestration",
                    "system_control", "memory", "chat",
                ],
                status=AGENT_STATUS_WORKING,
            )
            await self.chat.register_agent(friday_profile)

    # ── State Persistence ──────────────────────────────────────────────────

    def _load_state(self) -> None:
        """Load persisted townhall state from disk."""
        if not os.path.exists(TOWNHALL_STATE_FILE):
            return
        try:
            with open(TOWNHALL_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.state = TownhallState.from_dict(data)
        except (json.JSONDecodeError, OSError):
            pass

    def _save_state(self) -> None:
        """Persist current townhall state to disk."""
        os.makedirs(os.path.dirname(TOWNHALL_STATE_FILE), exist_ok=True)
        try:
            with open(TOWNHALL_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.state.to_dict(), f, indent=2, ensure_ascii=False)
        except OSError:
            pass


# ── Entry Point ────────────────────────────────────────────────────────────


def launch_townhall() -> dict:
    """Launch Townhall UI in a new terminal window (non-blocking).

    FRIDAY calls this tool to open the inter-agent chat UI.
    Can also be triggered via ``!townhall`` command.
    """
    import subprocess
    import sys

    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "townhall.py")
    title = "FRIDAY Townhall - Inter-Agent Terminal"

    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        proc = subprocess.Popen(
            ["cmd.exe", "/c", "start", title, "cmd.exe", "/k", f"python \"{script}\""],
            startupinfo=startupinfo,
        )
        return {"success": True, "pid": proc.pid, "message": "Townhall launched in new window"}
    except Exception as e:
        try:
            proc = subprocess.Popen(
                ["start", title, "cmd.exe", "/k", f"python \"{script}\""],
                shell=True,
            )
            return {"success": True, "pid": proc.pid, "message": "Townhall launched (fallback)"}
        except Exception as e2:
            return {"success": False, "error": f"Failed to launch townhall: {e}; fallback: {e2}"}


async def run_townhall() -> None:
    """Start the Townhall terminal UI.

    Call from an async context.  Example::

        from friday.agent_chat import get_agent_chat_system
        from friday.townhall import run_townhall

        chat = get_agent_chat_system()
        await chat.load_state()
        await run_townhall()
    """
    from friday.agent_chat import get_agent_chat_system

    chat = get_agent_chat_system()
    ui = TownhallUI(chat)
    await ui.run()


def main() -> None:
    """Sync entry point — runs the townhall UI in an asyncio event loop."""
    asyncio.run(run_townhall())


if __name__ == "__main__":
    main()
