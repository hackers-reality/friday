"""FRIDAY Terminal UI — rich Live Layout with Markdown, status bar, bottom input."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Callable, Awaitable

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from rich import box
from rich.rule import Rule
from rich.markup import escape

# ─── Message Renderables ─────────────────────────────────


class Message:
    ts: str

    def render(self):
        raise NotImplementedError


class UserMessage(Message):
    def __init__(self, text: str):
        self.text = text
        self.ts = datetime.datetime.now().strftime("%H:%M:%S")

    def render(self):
        return Panel(
            Text(self.text, style="bold green", overflow="fold"),
            title="[bold green]👤 Boss[/bold green]",
            subtitle=f"[dim]{self.ts}[/dim]",
            border_style="green",
            box=box.ROUNDED,
            padding=(0, 1),
        )


class FridayMessage(Message):
    def __init__(self, text: str = ""):
        self.text = text
        self.ts = datetime.datetime.now().strftime("%H:%M:%S")

    def render(self):
        try:
            return Panel(
                Markdown(self.text),
                title="[bold cyan]🤖 FRIDAY[/bold cyan]",
                subtitle=f"[dim]{self.ts}[/dim]",
                border_style="cyan",
                box=box.ROUNDED,
                padding=(0, 1),
            )
        except Exception:
            return Panel(
                Text(self.text, style="bold cyan", overflow="fold"),
                title="[bold cyan]🤖 FRIDAY[/bold cyan]",
                subtitle=f"[dim]{self.ts}[/dim]",
                border_style="cyan",
                box=box.ROUNDED,
                padding=(0, 1),
            )


class StreamingFridayMessage(Message):
    """A FRIDAY message that accumulates text progressively."""

    def __init__(self):
        self.text = ""
        self.ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._finalized = False

    def append(self, delta: str):
        self.text += delta

    def finalize(self, full_text: str):
        self.text = full_text
        self._finalized = True

    def render(self):
        label = "[bold cyan]🤖 FRIDAY[/bold cyan]"
        if not self._finalized:
            label += " [dim]▌[/dim]"
        try:
            body = Markdown(self.text) if self._finalized else Text(self.text or "▌", style="bold cyan")
            return Panel(
                body,
                title=label,
                subtitle=f"[dim]{self.ts}[/dim]",
                border_style="cyan",
                box=box.ROUNDED,
                padding=(0, 1),
            )
        except Exception:
            return Panel(
                Text(self.text or "▌", style="bold cyan", overflow="fold"),
                title=label,
                subtitle=f"[dim]{self.ts}[/dim]",
                border_style="cyan",
                box=box.ROUNDED,
                padding=(0, 1),
            )


class ThoughtMessage(Message):
    def __init__(self, text: str):
        self.text = text
        self.ts = datetime.datetime.now().strftime("%H:%M:%S")

    def render(self):
        return Panel(
            Text(self.text, style="italic dim grey74", overflow="fold"),
            title=f"[dim]💭 Thought ({self.ts})[/dim]",
            border_style="grey46",
            box=box.ROUNDED,
            padding=(0, 1),
        )


class SystemMessage(Message):
    def __init__(self, text: str):
        self.text = text
        self.ts = datetime.datetime.now().strftime("%H:%M:%S")

    def render(self):
        icon = "⚡"
        lower = self.text.lower()
        if "mic" in lower or "listen" in lower:
            icon = "🎤"
        elif "standby" in lower:
            icon = "💤"
        elif "execut" in lower:
            icon = "🔧"
        elif "interrupt" in lower or "mute" in lower:
            icon = "⏹"
        elif "ready" in lower or "online" in lower:
            icon = "✅"
        return Text(f"  {self.ts}  {icon} {self.text}", style="dim", overflow="fold")


class ToolCallMessage(Message):
    def __init__(self, name: str, args: dict | None = None):
        self.name = name
        self.args = args
        self.ts = datetime.datetime.now().strftime("%H:%M:%S")

    def render(self):
        args_str = ""
        if self.args:
            parts = []
            for k, v in list(self.args.items())[:3]:
                v_str = str(v)[:40]
                parts.append(f"{k}={v_str}")
            if len(self.args) > 3:
                parts.append(f"...+{len(self.args)-3}")
            args_str = "  " + ", ".join(parts)
        return Text(
            f"  {self.ts}  ▶ {self.name}{args_str}",
            style="bright_yellow",
            overflow="fold",
        )


class ToolResultMessage(Message):
    def __init__(self, name: str, result: str):
        self.name = name
        self.result = str(result)[:120].replace("\n", " ")
        self.ts = datetime.datetime.now().strftime("%H:%M:%S")

    def render(self):
        return Text(
            f"  {self.ts}  ✓ {self.name} → {self.result}",
            style="bright_green",
            overflow="fold",
        )


class ErrorMessage(Message):
    def __init__(self, text: str):
        self.text = text
        self.ts = datetime.datetime.now().strftime("%H:%M:%S")

    def render(self):
        return Panel(
            Text(self.text, style="bold red"),
            title=f"[bold red]✗ Error ({self.ts})[/bold red]",
            border_style="red",
            box=box.ROUNDED,
        )


class TurnDivider(Message):
    def render(self):
        return Rule(style="dim grey35")


# ─── Main TUI Class ────────────────────────────────────


class FRIDAYTUI:
    """Enhanced terminal UI with persistent layout, Markdown, status bar, bottom input.

    API compatible with ChatDisplay (add_user_message, add_friday_message, …)
    plus extras: status bar, connection indicator, streaming, Markdown rendering.
    """

    def __init__(
        self,
        *,
        model_id: str = "gemini-3.1-flash-live-preview",
        tools_count: int = 0,
    ):
        self.console = Console()
        self.model_id = model_id
        self.tools_count = tools_count
        self._messages: list[Message] = []
        self._connection_status = "connecting"
        self._status_message = ""
        self._max_messages = 200
        self._stream_msg: StreamingFridayMessage | None = None
        self._last_body_text = ""
        self._last_header_text = ""
        self._last_footer_text = ""

        self.layout = Layout()
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=3),
        )

        self._live = Live(
            self.layout,
            console=self.console,
            screen=True,
            refresh_per_second=8,
            redirect_stdout=False,
        )

    # ── Layout Builders ────────────────────────────────

    def _build_header(self) -> Panel:
        status_colors = {
            "connected": "green",
            "connecting": "yellow",
            "disconnected": "red",
            "error": "red",
            "dreaming": "blue",
            "standby": "bright_black",
        }
        dot_color = status_colors.get(self._connection_status, "yellow")
        model_display = self.model_id or "gemini-3.1-flash-live-preview"

        grid = Table.grid(padding=(0, 2))
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)
        grid.add_column(ratio=0, width=20)
        grid.add_row(
            f"[bold cyan]⚡ F.R.I.D.A.Y[/bold cyan]",
            f"[dim]Model:[/dim] [bold]{model_display}[/bold]",
            f"[dim]Tools:[/dim] [bold]{self.tools_count}[/bold]",
            f"● [{dot_color}]{self._connection_status}[/{dot_color}]",
        )
        return Panel(grid, box=box.HEAVY_EDGE, border_style="cyan", padding=(0, 1))

    def _build_body(self) -> Panel:
        elements = []
        for msg in self._messages[-self._max_messages:]:
            try:
                elements.append(msg.render())
            except Exception:
                elements.append(Text("[render error]", style="dim red"))
        if not elements:
            elements.append(Text("  Waiting for input…", style="dim italic"))
        return Panel(
            Group(*elements),
            title="[dim]Conversation[/dim]",
            border_style="grey46",
            box=box.ROUNDED,
            padding=(0, 1),
        )

    def _build_footer(self) -> Panel:
        if self._status_message:
            status_part = f"[dim]│ {self._status_message}[/dim]"
        else:
            status_part = f"[dim]│ Ctrl+C to quit[/dim]"
        return Panel(
            Text.assemble(
                ("> █", "bold green"),
                ("  " + status_part, ""),
            ),
            box=box.HEAVY_EDGE,
            border_style="grey46",
            padding=(0, 1),
        )

    def _refresh(self):
        self.layout["header"].update(self._build_header())
        self.layout["body"].update(self._build_body())
        self.layout["footer"].update(self._build_footer())

    # ── Public API (matches ChatDisplay) ───────────────

    def add_user_message(self, text: str):
        self._messages.append(UserMessage(text))
        self._refresh()

    def add_friday_message(self, text: str):
        self._messages.append(FridayMessage(text))
        self._refresh()

    def add_thought(self, text: str):
        self._messages.append(ThoughtMessage(text))
        self._refresh()

    def add_system(self, text: str):
        self._messages.append(SystemMessage(text))
        self._refresh()

    def add_tool_call(self, name: str, args: dict | None = None):
        self._messages.append(ToolCallMessage(name, args))
        self._refresh()

    def add_tool_result(self, name: str, result: str):
        self._messages.append(ToolResultMessage(name, result))
        self._refresh()

    def add_error(self, text: str):
        self._messages.append(ErrorMessage(text))
        self._refresh()

    def add_turn_divider(self):
        self._messages.append(TurnDivider())
        self._refresh()

    def clear(self):
        self._messages.clear()
        self._refresh()

    # ── Streaming support ──────────────────────────────

    def start_stream(self):
        self._stream_msg = StreamingFridayMessage()
        self._messages.append(self._stream_msg)
        self._refresh()

    def append_stream(self, text: str):
        if self._stream_msg:
            self._stream_msg.append(text)
            self._refresh()

    def finalize_stream(self, text: str):
        if self._stream_msg:
            self._stream_msg.finalize(text)
            self._stream_msg = None
            self._refresh()

    def cancel_stream(self):
        if self._stream_msg:
            self._messages.pop()
            self._stream_msg = None
            self._refresh()

    # ── Status controls ────────────────────────────────

    def set_connection_status(self, status: str):
        self._connection_status = status
        self._refresh()

    def set_status_message(self, msg: str):
        self._status_message = msg
        self._refresh()

    def set_model_id(self, model_id: str):
        self.model_id = model_id
        self._refresh()

    def set_tools_count(self, count: int):
        self.tools_count = count
        self._refresh()

    # ── Lifecycle ──────────────────────────────────────

    async def start(self):
        self._refresh()
        self._live.start()

    async def stop(self):
        self._live.stop()

    def __enter__(self):
        self._live.__enter__()
        self._refresh()
        return self

    def __exit__(self, *args):
        self._live.__exit__(*args)


# ─── No‑Flicker ChatDisplay (plain console.print) ────────


class ChatDisplay:
    """Simple chat display using plain console.print — no Rich Live, no flicker.

    API compatible with FRIDAYTUI for drop‑in replacement in live.py.
    """

    def __init__(
        self,
        *,
        model_id: str = "gemini-3.1-flash-live-preview",
        tools_count: int = 0,
    ):
        self.console = Console()
        self.model_id = model_id
        self.tools_count = tools_count
        self._connection_status = "connecting"
        self._status_message = ""
        self._stream_buf = ""

    # ── Public API ──────────────────────────────────────

    def add_user_message(self, text: str):
        self.console.print(f"\n[bold green]── Boss ──[/]")
        self.console.print(f"  {text}")

    def add_friday_message(self, text: str):
        self.console.print(f"\n[bold cyan]── FRIDAY ──[/]")
        self.console.print(f"  {text}")

    def add_thought(self, text: str):
        self.console.print()
        self.console.rule("[dim]Thought[/]", align="left", style="dim grey37")
        self.console.print(f"  [italic dim]{text}[/]")

    def add_system(self, text: str):
        self.console.print(f"  [dim cyan][SYSTEM] {text}[/]")

    def add_tool_call(self, name: str, args: dict | None = None):
        args_str = ""
        if args:
            args_str = f"({json.dumps(args, default=str)})"
        self.console.print(f"  [yellow]🔧 {name}[/]{args_str}")

    def add_tool_result(self, name: str, result: str):
        preview = result[:120].replace("\n", " ")
        self.console.print(f"  [dim green]✓ {name}[/] [dim]{preview}[/]")

    def add_error(self, text: str):
        self.console.print(f"  [bold red]⚠ {text}[/]")

    def add_turn_divider(self):
        self.console.rule(style="dim")

    def clear(self):
        self.console.clear()

    # ── Streaming ───────────────────────────────────────

    def start_stream(self):
        self._stream_buf = ""
        sys.stdout.write("── FRIDAY ── ")
        sys.stdout.flush()

    def append_stream(self, text: str):
        self._stream_buf += text
        sys.stdout.write(text)
        sys.stdout.flush()

    def finalize_stream(self, text: str):
        sys.stdout.write("\n")
        sys.stdout.flush()

    def cancel_stream(self):
        self._stream_buf = ""
        sys.stdout.write("\n")
        sys.stdout.flush()

    # ── Status ──────────────────────────────────────────

    def set_connection_status(self, status: str):
        self._connection_status = status
        self.console.print(f"  [dim]Status: {status}[/]")

    def set_status_message(self, msg: str):
        self._status_message = msg

    def set_model_id(self, model_id: str):
        self.model_id = model_id

    def set_tools_count(self, count: int):
        self.tools_count = count

    # ── Lifecycle ───────────────────────────────────────

    async def start(self):
        self.console.print(f"[bold cyan]⚡ F.R.I.D.A.Y[/] [dim]({self.model_id}, {self.tools_count} tools)[/]")

    async def stop(self):
        self.console.print("[dim]Session ended.[/]")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass
