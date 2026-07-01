"""FRIDAY TUI — three-column command center."""

from __future__ import annotations

import asyncio
import datetime
import os
import subprocess
import sys
from pathlib import Path

from rich.markdown import Markdown as RMD
from rich.text import Text as RTxt
from rich.panel import Panel as RPanel
from rich.table import Table as RTable
from rich.columns import Columns as RColumns
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widgets import Header, Footer, Input, RichLog, Static, Label, ListView, ListItem, Button, TextArea
from textual import events

THEMES = [
    {
        "name": "Neon Dark",
        "p": "#00BFFF", "s": "#00FF87", "a": "#FFD700",
        "bg": "#050510", "sf": "#0A0A1A", "sb": "#0C0C20",
        "bd": "#1A1A3A", "m": "#686898",
        "cb": "#080818", "ib": "#10102A", "if": "#00FF87",
    },
    {
        "name": "Matrix",
        "p": "#00FF41", "s": "#00CC33", "a": "#FFFFFF",
        "bg": "#000000", "sf": "#001000", "sb": "#000800",
        "bd": "#003300", "m": "#005500",
        "cb": "#000800", "ib": "#001000", "if": "#00FF41",
    },
    {
        "name": "Dawn",
        "p": "#0066CC", "s": "#009944", "a": "#CC6600",
        "bg": "#F5F0EB", "sf": "#FFFFFF", "sb": "#EDE8E3",
        "bd": "#D0C8C0", "m": "#888080",
        "cb": "#FFFFFF", "ib": "#F5F0EB", "if": "#222222",
    },
    {
        "name": "Amber",
        "p": "#FFB000", "s": "#FF8800", "a": "#FFDD44",
        "bg": "#000000", "sf": "#0A0800", "sb": "#080600",
        "bd": "#332200", "m": "#665522",
        "cb": "#000000", "ib": "#0A0800", "if": "#FFB000",
    },
]

def css(t: dict) -> str:
    return f"""
Screen {{ background: {t['bg']}; }}
Header {{ background: {t['sf']}; color: {t['p']}; border-bottom: solid {t['bd']}; }}
#row {{ layout: horizontal; height: 1fr; }}
#left {{ width: 26; height: 1fr; background: {t['sb']}; border: solid {t['bd']}; margin: 1 0 1 1; padding: 0 1; overflow-y: auto; }}
#left > Label {{ color: {t['p']}; text-style: bold; margin: 1 0; }}
#left > Static {{ color: {t['m']}; }}
.si {{ color: {t['m']}; margin: 0 0 0 1; }}
#center {{ layout: vertical; width: 1fr; height: 1fr; background: {t['bg']}; border-top: solid {t['bd']}; border-bottom: solid {t['bd']}; margin: 1 0 1 0; }}
#log {{ height: 1fr; background: {t['cb']}; border: none; padding: 0 1; min-height: 1; }}
#sw {{ height: auto; background: {t['bg']}; color: {t['p']}; padding: 0 1; border-top: dashed {t['bd']}; }}
#tray {{ height: auto; background: {t['sf']}; padding: 1; border-top: solid {t['bd']}; }}
#inp {{ background: {t['ib']}; color: {t['if']}; border: solid {t['bd']}; padding: 0 1; height: 3; }}
#inp:focus {{ border: solid {t['p']}; }}
#right {{ width: 34; height: 1fr; background: {t['sb']}; border: solid {t['bd']}; margin: 1 1 1 0; padding: 0 1; overflow-y: auto; }}
#right > Label {{ color: {t['p']}; text-style: bold; margin: 1 0; }}
#right > Static {{ color: {t['m']}; }}
#status {{ background: {t['sf']}; color: {t['m']}; height: 1; padding: 0 1; border-top: solid {t['bd']}; }}
"""


class StreamWidget(Static):
    def on_mount(self):
        self.display = False
    def start(self):
        self.display = True
        self.update("...")
    def put(self, t):
        self.display = True
        self.update(t)
    def done(self):
        self.display = False
        self.update("")


class DashboardData:
    def __init__(self):
        self._tasks = []
        self._notifications = []
        self._system = {}
        self._memory = ""
        self._schedule = ""
        self._subagents = {}
        self._tokens_used = 0
        self._ctx_limit = 128000
        self._last_update = None

    def _touch(self):
        self._last_update = datetime.datetime.now().strftime("%H:%M:%S")

    def update_tasks(self, tasks): self._tasks = tasks; self._touch()
    def update_notifications(self, notifs): self._notifications = notifs; self._touch()
    def update_system(self, sysinfo): self._system = sysinfo; self._touch()
    def update_memory(self, mem): self._memory = mem; self._touch()
    def update_schedule(self, sched): self._schedule = sched; self._touch()
    def update_subagents(self, agents): self._subagents = agents; self._touch()
    def update_tokens(self, used, limit): self._tokens_used = used; self._ctx_limit = limit; self._touch()


class KeysPalette(Screen):
    def __init__(self):
        super().__init__()
        self._detected = self._detect_keys()

    def _detect_keys(self):
        detected = {}
        env_map = {
            "GOOGLE_API_KEY": ("Google AI (Gemini)", "https://aistudio.google.com/apikey"),
            "OPENAI_API_KEY": ("OpenAI (GPT)", "https://platform.openai.com/api-keys"),
            "ANTHROPIC_API_KEY": ("Anthropic (Claude)", "https://console.anthropic.com/"),
            "GROQ_API_KEY": ("Groq", "https://console.groq.com/keys"),
            "OPENCODE_ZEN_API_KEY": ("OpenCode Zen", None),
            "NVIDIA_API_KEY": ("NVIDIA", "https://build.nvidia.com/explore/"),
            "GITHUB_TOKEN": ("GitHub", "https://github.com/settings/tokens"),
            "SERPER_API_KEY": ("Serper (Search)", "https://serper.dev/"),
            "TAVILY_API_KEY": ("Tavily (Search)", "https://tavily.com/"),
            "BRAVE_API_KEY": ("Brave Search", "https://brave.com/search/api/"),
            "ELEVENLABS_API_KEY": ("ElevenLabs (Voice)", "https://elevenlabs.io/"),
        }
        for var, (name, url) in env_map.items():
            val = os.environ.get(var, "")
            src = "env" if val else ""
            if not src and Path(".env").exists():
                try:
                    for line in Path(".env").read_text().splitlines():
                        if line.strip() and not line.strip().startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            if k.strip() == var and v.strip():
                                src = ".env"
                                break
                except: pass
            detected[var] = {"name": name, "url": url, "status": "configured" if val else (f"found in {src}" if src else "missing"), "value": bool(val)}
        return detected

    def compose(self):
        yield Container(
            Label("API Keys Configuration", id="keys-title"),
            Static(""),
            *[self._key_row(var, info) for var, info in self._detected.items()],
            Static(""),
            Label("  Ctrl+Q to close", classes="hint"),
            id="keys-container",
        )

    def _key_row(self, var, info):
        status = info["status"]
        if "configured" in status:
            icon = "[bold green]\u2713[/bold green]"
        elif "found" in status:
            icon = "[bold yellow]\u25cf[/bold yellow]"
        else:
            icon = "[bold red]\u2717[/bold red]"
        name = info["name"]
        url = info["url"]
        url_str = f"  [link={url}]{url}[/link]" if url else ""
        return Static(f"{icon} {name} ({var}){url_str}", classes=f"key-row key-{'ok' if info['value'] else 'miss'}")

    CSS = """
    Screen { background: #0A0A1A; }
    #keys-container { padding: 2 4; }
    #keys-title { color: #00BFFF; text-style: bold; text-align: center; text-style: bold; margin: 1 0; }
    .key-row { color: #686898; margin: 0 0; padding: 0 1; }
    .key-ok { color: #00FF87; }
    .key-miss { color: #FF6B6B; }
    .hint { color: #444466; text-align: center; }
    """
    BINDINGS = [Binding("ctrl+q", "quit", "Close")]
    def action_quit(self): self.app.pop_screen()


class AgentStatusWidget(Static):
    agents = reactive({
        "FRIDAY": {"status": "working", "task": "System core online"},
        "JARVIS": {"status": "idle", "task": ""},
        "NOVA": {"status": "idle", "task": ""},
        "ATLAS": {"status": "idle", "task": ""},
        "SENTRY": {"status": "idle", "task": ""},
        "FORGE": {"status": "idle", "task": ""},
        "ECHO": {"status": "idle", "task": ""},
        "AEGIS": {"status": "idle", "task": ""},
        "CRUX": {"status": "idle", "task": ""},
        "VERSE": {"status": "idle", "task": ""},
        "LORE": {"status": "idle", "task": ""},
    })

    def render(self):
        lines = []
        for name, info in self.agents.items():
            status = info.get("status", "idle")
            task = info.get("task", "")
            dot_colors = {"idle": "gray", "working": "green", "waiting": "yellow", "chatting": "cyan", "dreaming": "blue"}
            c = dot_colors.get(status, "gray")
            dots = {"idle": "\u25cb", "working": "\u25cf", "waiting": "\u25d0", "chatting": "\u25c9", "dreaming": "\u25b6"}
            d = dots.get(status, "\u25cb")
            line = f"[bold {c}]{d}[/bold {c}] {name}"
            if task:
                line += f" [dim]{task[:20]}[/dim]"
            lines.append(line)
        return "\n".join(lines)

    def update_agent(self, name: str, status: str, task: str = ""):
        d = dict(self.agents)
        d[name] = {"status": status, "task": task}
        self.agents = d


class DashboardPanel(Static):
    data = reactive(DashboardData())
    pc = reactive("#00BFFF")
    sc = reactive("#00FF87")
    ac = reactive("#FFD700")
    mc = reactive("#686898")

    def set_theme_colors(self, p: str, s: str, a: str, m: str):
        self.pc = p
        self.sc = s
        self.ac = a
        self.mc = m

    def render(self):
        d = self.data
        p = self.pc
        s = self.sc
        a = self.ac
        m = self.mc
        lines = []
        lines.append(f"[bold {p}]\u2699 System[/bold {p}]")
        sys = d._system
        cpu = sys.get("cpu", "?")
        mem = sys.get("memory", "?")
        disk = sys.get("disk", "?")
        lines.append(f"  [bold {s}]CPU:[/bold {s}] {cpu}%  [bold {s}]RAM:[/bold {s}] {mem}%  [bold {s}]DISK:[/bold {s}] {disk}%")
        lines.append("")
        lines.append(f"[bold {p}]\u23f3 Tasks ({len(d._tasks)})[/bold {p}]")
        for t in d._tasks[-3:]:
            lines.append(f"  [{m}]{str(t)[:40]}[/{m}]")
        lines.append("")
        lines.append(f"[bold {p}]\u2302 Notifications ({len(d._notifications)})[/bold {p}]")
        for n in d._notifications[-3:]:
            lines.append(f"  [{m}]{str(n)[:40]}[/{m}]")
        lines.append("")
        lines.append(f"[bold {p}]\ud83e\udde0 Memory[/bold {p}]")
        if d._memory:
            lines.append(f"  [{m}]{d._memory[:50]}[/{m}]")
        lines.append("")
        lines.append(f"[bold {p}]\ud83d\udcc5 Schedule[/bold {p}]")
        if d._schedule:
            lines.append(f"  [{m}]{d._schedule[:50]}[/{m}]")
        lines.append("")
        lines.append(f"[bold {p}]\ud83e\udd16 Subagents[/bold {p}]")
        for name, info in d._subagents.items():
            lines.append(f"  {name}: {info.get('status','?')}")
        lines.append("")
        lines.append(f"[bold {p}]\ud83d\udcca Tokens[/bold {p}]")
        lines.append(f"  [{m}]{d._tokens_used:,}/{d._ctx_limit:,}[/{m}]")
        if d._last_update:
            lines.append(f"  [{m}]Updated: {d._last_update}[/{m}]")
        return "\n".join(lines)


class FridayApp(App):
    TITLE = "F.R.I.D.A.Y"
    SUB_TITLE = "Sovereign AI Agent"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("ctrl+s", "side", "Sidebar"),
        Binding("ctrl+r", "right", "Right Panel"),
        Binding("ctrl+t", "theme", "Theme"),
        Binding("ctrl+p", "palette", "Palette"),
        Binding("ctrl+n", "townhall", "Townhall"),
    ]

    def __init__(self, *, model_id="gemini-2.5-flash-native-audio-preview-12-2025", tools_count=0):
        super().__init__()
        self.mid = model_id
        self.tcnt = tools_count
        self._cb = None
        self._sh = True
        self._rh = True
        self._ti = 0
        self._buf = ""
        self._sa = False
        self._search_mode = False
        self._active_tool = None
        self._tool_results = []
        self._msg_count = 0
        self._unanswered_count = 0
        self._dashboard = DashboardData()
        self._agents_widget = None
        self._dashboard_widget = None
        self._agent_status = self._make_agent_status()

    def _make_agent_status(self):
        return {
            "FRIDAY": {"status": "working", "task": "System core online"},
            "JARVIS": {"status": "idle", "task": ""},
            "NOVA": {"status": "idle", "task": ""},
            "ATLAS": {"status": "idle", "task": ""},
            "SENTRY": {"status": "idle", "task": ""},
            "FORGE": {"status": "idle", "task": ""},
            "ECHO": {"status": "idle", "task": ""},
            "AEGIS": {"status": "idle", "task": ""},
            "CRUX": {"status": "idle", "task": ""},
            "VERSE": {"status": "idle", "task": ""},
            "LORE": {"status": "idle", "task": ""},
        }

    @property
    def T(self): return THEMES[self._ti % len(THEMES)]

    def action_theme(self):
        self._ti = (self._ti + 1) % len(THEMES)
        self.css = css(self.T)
        try:
            dw = self._dashboard_widget
            if dw:
                dw.set_theme_colors(self.T["p"], self.T["s"], self.T["a"], self.T["m"])
        except Exception:
            pass
        self.refresh()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="row"):
            with Container(id="left"):
                yield Label("\u25c8 F.R.I.D.A.Y")
                yield AgentStatusWidget(id="agent-status")
                yield Static("")
                yield Label("\u2699 System")
                yield Static(f"Model: {self.mid}", classes="si")
                yield Static(f"Tools: {self.tcnt}", classes="si")
                yield Static("", id="si-c", classes="si")
                yield Static("")
                yield Label("\u2318 Commands")
                yield Static("  !townhall  !search", classes="si")
                yield Static("  !theme    !status", classes="si")
                yield Static("  !help     !keys", classes="si")
                yield Static("")
                yield Label("\u2328 Shortcuts")
                yield Static("  C-c quit   C-l clear", classes="si")
                yield Static("  C-s left   C-r right", classes="si")
                yield Static("  C-t theme  C-p keys", classes="si")
                yield Static("  C-n townhall", classes="si")
            with Container(id="center"):
                yield RichLog(id="log", highlight=True, markup=True)
                yield StreamWidget(id="sw")
                with Container(id="tray"):
                    yield Input(id="inp", placeholder="Message FRIDAY...")
            with Container(id="right"):
                yield DashboardPanel(id="dashboard")
        yield Container(id="status")

    def on_mount(self):
        self.css = css(self.T)
        self._agents_widget = self.query_one("#agent-status", AgentStatusWidget)
        self._dashboard_widget = self.query_one("#dashboard", DashboardPanel)
        self._dashboard_widget.set_theme_colors(
            self.T["p"], self.T["s"], self.T["a"], self.T["m"])
        self._refresh_system_info()
        self.query_one("#log", RichLog).write(
            RPanel(RTxt("  FRIDAY — Sovereign AI Agent\n  Neural link initializing...", style="bold cyan"), border_style="cyan"))
        self.set_interval(30, self._refresh_dashboard)
        self.set_interval(60, self._refresh_system_info)

    def _refresh_system_info(self):
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0)
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage("/").percent
            self._dashboard.update_system({"cpu": cpu, "memory": mem, "disk": disk})
        except: pass
        try:
            from friday.tools_flat import get_pending_notifications
            n = get_pending_notifications()
            if isinstance(n, list):
                self._dashboard.update_notifications(n)
        except: pass

    def _refresh_dashboard(self):
        self._refresh_system_info()
        try:
            from friday.tools_flat import memory_retrieve
            m = memory_retrieve("recent_context")
            if m: self._dashboard.update_memory(str(m)[:200])
        except: pass
        try:
            from friday.tools_flat import calendar_tool_handler
            s = calendar_tool_handler("list", {"max": 3})
            if s: self._dashboard.update_schedule(str(s)[:200])
        except: pass
        if self._dashboard_widget:
            self._dashboard_widget.data = self._dashboard

    def on_input_submitted(self, e):
        t = e.value.strip()
        if not t:
            return
        inp = self.query_one("#inp", Input)

        if t.startswith("!"):
            self._cmd(t)
            inp.clear()
            return

        if self._search_mode:
            self._search_mode = False
            self.query_one("#inp", Input).placeholder = "Message FRIDAY..."

        self._msg_count += 1
        self._unanswered_count += 1
        self._msg("You", t, "green")
        # Signal townhall that FRIDAY is busy
        try:
            from friday._singletons import signal_townhall_bother
            signal_townhall_bother()
        except Exception:
            pass
        if self._cb:
            self._cb(t)
        inp.clear()

        if self._unanswered_count >= 5:
            ts2 = datetime.datetime.now().strftime("%H:%M")
            log = self.query_one("#log", RichLog)
            log.write(f"  {ts2}  \u25b6 [bold blue]FRIDAY entering dream mode after {self._unanswered_count} unanswered messages[/bold blue]")
            log.write(f"  {ts2}  \u25b6 [bold blue]Opening Townhall for agent processing...[/bold blue]")
            self.action_townhall()
            self._unanswered_count = 0

    def _cmd(self, c):
        log = self.query_one("#log", RichLog)
        ts = datetime.datetime.now().strftime("%H:%M")
        c = c.strip().lower()
        args = c.split(maxsplit=1)
        cmd = args[0] if args else c

        if cmd in ("!townhall", "!tn"):
            try:
                from friday.townhall_app import launch_townhall
                r = launch_townhall()
                log.write(f"  {ts}  \u2192 Townhall PID {r.get('pid','?')}" if r.get("success") else f"  {ts}  \u2717 {r.get('error')}")
            except Exception as ex:
                log.write(f"  {ts}  \u2717 {ex}")

        elif cmd in ("!help", "!h"):
            log.write(f"  {ts}  Commands: !townhall !search <q> !status !theme !keys !help")
            log.write(f"  {ts}  Shortcuts: Ctrl+C quit, Ctrl+L clear, Ctrl+S left panel, Ctrl+R right panel, Ctrl+T theme, Ctrl+P keys palette, Ctrl+N townhall")

        elif cmd == "!status":
            log.write(f"  {ts}  Model: {self.mid}  Tools: {self.tcnt}  Theme: {self.T['name']}  Messages: {self._msg_count}")

        elif cmd == "!theme":
            self.action_theme()
            log.write(f"  {ts}  Theme: {self.T['name']}")

        elif cmd == "!keys":
            self.push_screen(KeysPalette())

        elif cmd == "!search":
            self._search_mode = True
            self.query_one("#inp", Input).placeholder = "Search: enter query..."
            log.write(f"  {ts}  Search mode active. Type your query.")

        elif cmd == "!clear":
            self.action_clear()

        elif cmd.startswith("!search "):
            q = args[1] if len(args) > 1 else ""
            if not q:
                log.write(f"  {ts}  Usage: !search <query>")
                return
            log.write(f"  {ts}  Searching for: {q}")
            asyncio.create_task(self._perform_search(q))

        else:
            log.write(f"  {ts}  \u2717 Unknown: {c}. Type !help for commands.")

    async def _perform_search(self, query: str):
        log = self.query_one("#log", RichLog)
        ts = datetime.datetime.now().strftime("%H:%M")
        log.write(f"  {ts}  \u25b6 [bright_yellow]search[/bright_yellow] executing...")
        self._start_tool("search")
        try:
            import friday.tools_flat as tf
            results = ""
            if hasattr(tf, "web_search"):
                results = tf.web_search(query)
            elif hasattr(tf, "grep_tool"):
                results = tf.grep_tool(query)
            else:
                results = f"Searched: {query}"
            log.write(f"  {ts}  \u2713 [bright_green]search[/bright_green] found results")
            self._tool_results.append({"query": query, "results": str(results)[:200]})
            log.write(f"  {ts}  Results: {str(results)[:200]}")
            self._dashboard.update_tasks(self._tool_results)
        except Exception as ex:
            log.write(f"  {ts}  \u2717 [red]search error: {ex}[/red]")
        self._end_tool()

    def _start_tool(self, name):
        self._active_tool = name
        try:
            sw = self._agents_widget
            if sw: sw.update_agent("FRIDAY", "working", name)
        except: pass

    def _end_tool(self):
        self._active_tool = None
        try:
            sw = self._agents_widget
            if sw: sw.update_agent("FRIDAY", "working", "idle")
        except: pass

    def set_input_callback(self, cb):
        self._cb = cb

    def action_side(self):
        self._sh = not self._sh
        self.query_one("#left").display = self._sh

    def action_right(self):
        self._rh = not self._rh
        self.query_one("#right").display = self._rh

    def action_clear(self):
        self.query_one("#log", RichLog).clear()

    def action_palette(self):
        self.push_screen(KeysPalette())

    def action_townhall(self):
        try:
            from friday.townhall_app import launch_townhall
            r = launch_townhall()
            ts = datetime.datetime.now().strftime("%H:%M")
            log = self.query_one("#log", RichLog)
            log.write(f"  {ts}  \u2192 Townhall PID {r.get('pid','?')}" if r.get("success") else f"  {ts}  \u2717 {r.get('error')}")
        except Exception as ex:
            pass

    def _msg(self, who, text, border):
        ts = datetime.datetime.now().strftime("%H:%M")
        try:
            self.query_one("#log", RichLog).write(
                RPanel(RMD(text), title=f"[bold {border}]{who}[/bold {border}]",
                       subtitle=f"[dim]{ts}[/dim]", border_style=border))
        except:
            self.query_one("#log", RichLog).write(
                RPanel(RTxt(text, style=f"bold {border}"),
                       title=f"[bold {border}]{who}[/bold {border}]",
                       subtitle=f"[dim]{ts}[/dim]", border_style=border))

    def add_user_message(self, t):
        self._msg("You", t, "green")

    def add_friday_message(self, t):
        self._msg("FRIDAY", t, "cyan")

    def add_thought(self, t):
        ts = datetime.datetime.now().strftime("%H:%M")
        self.query_one("#log", RichLog).write(
            RPanel(RTxt(t, style="italic gray50"), title=f"[dim]Thought ({ts})[/dim]", border_style="gray37"))

    def add_system(self, t):
        ts = datetime.datetime.now().strftime("%H:%M")
        self.query_one("#log", RichLog).write(f"  {ts}  {t}")

    def add_tool_call(self, name, args=None):
        ts = datetime.datetime.now().strftime("%H:%M")
        a = ""
        if args:
            a = " " + ", ".join(f"{k}={str(v)[:30]}" for k, v in list(args.items())[:3])
        self.query_one("#log", RichLog).write(f"  {ts}  \u25b6 [bright_yellow]{name}{a}[/bright_yellow]")
        self._start_tool(name)

    def add_tool_result(self, name, result):
        ts = datetime.datetime.now().strftime("%H:%M")
        self.query_one("#log", RichLog).write(
            f"  {ts}  \u2713 [bright_green]{name} \u2192 {str(result)[:120]}[/bright_green]")
        self._tool_results.append({name: str(result)[:200]})
        self._dashboard.update_tasks(self._tool_results)

    def add_error(self, t):
        ts = datetime.datetime.now().strftime("%H:%M")
        self.query_one("#log", RichLog).write(
            RPanel(RTxt(t, style="bold red"), title=f"[bold red]Error ({ts})[/bold red]", border_style="red"))

    def start_stream(self):
        self._buf = ""
        self._sa = True
        try:
            self.query_one("#sw", StreamWidget).start()
        except Exception:
            pass

    def append_stream(self, t):
        if not self._sa:
            return
        self._buf += t
        try:
            self.query_one("#sw", StreamWidget).put(self._buf)
        except Exception:
            pass

    def finalize_stream(self, t):
        self._sa = False
        if t:
            self._buf = t
            self.add_friday_message(t)
            self._unanswered_count = 0
            # Signal townhall that FRIDAY is free
            try:
                from friday._singletons import signal_townhall_return
                signal_townhall_return()
            except Exception:
                pass
        try:
            self.query_one("#sw", StreamWidget).done()
        except Exception:
            pass
        self._buf = ""

    def cancel_stream(self):
        self._sa = False
        self._buf = ""
        try:
            self.query_one("#sw", StreamWidget).done()
        except Exception:
            pass

    def set_connection_status(self, s):
        colors = {"connected": "green", "connecting": "yellow", "disconnected": "red",
                  "error": "red", "dreaming": "blue", "standby": "gray"}
        c = colors.get(s, "yellow")
        try:
            self.query_one("#si-c", Static).update(f"[bold {c}]\u25cf {s}[/bold {c}]")
        except Exception:
            pass
