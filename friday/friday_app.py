"""FRIDAY TUI — polished, precise layout."""

from __future__ import annotations

import datetime

from rich.markdown import Markdown as RMD
from rich.text import Text as RTxt
from rich.panel import Panel as RPanel
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.widgets import Header, Footer, Input, RichLog, Static, Label

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
Header {{ background: {t['sf']}; color: {t['p']}; text-style: bold; }}
Footer {{ background: {t['sf']}; color: {t['m']}; }}
#row {{ layout: horizontal; height: 1fr; }}
#side {{ width: 26; background: {t['sb']}; border-right: solid {t['bd']}; padding: 1 0 1 1; }}
#side > #side-scroll {{ layout: vertical; height: 100%; overflow-y: auto; }}
#side > #side-scroll > Label {{ color: {t['p']}; text-style: bold; margin: 0 0 0 1; }}
#side > #side-scroll > Rule {{ color: {t['bd']}; margin: 0 1 0 1; }}
.si {{ color: {t['m']}; margin: 0 0 0 1; }}
.si-v {{ color: {t['p']}; }}
#col {{ layout: vertical; width: 1fr; background: {t['bg']}; }}
#log {{ background: {t['cb']}; border: solid {t['bd']}; padding: 0 1; height: 1fr; min-height: 1; }}
#log:focus-within {{ border: solid {t['p']}; }}
#sw {{ background: {t['bg']}; color: {t['p']}; padding: 0 1; min-height: 1; border-top: solid {t['bd']}; }}
#tray {{ height: 5; background: {t['sf']}; border-top: solid {t['bd']}; padding: 1; }}
#inp {{ background: {t['ib']}; color: {t['if']}; border: solid {t['bd']}; padding: 0 1; height: 3; }}
#inp:focus {{ border: solid {t['p']}; }}
"""


class SB(Static):
    conn = reactive("connecting")
    def watch_conn(self, v):
        c = {"connected":"green","connecting":"yellow","disconnected":"red","error":"red","dreaming":"blue","standby":"gray"}
        self.update(f"[bold {c.get(v,'yellow')}]\u25cf {v}[/bold {c.get(v,'yellow')}]")


class SW(Static):
    def start(self): self.visible=True; self.display=True; self.update("...")
    def put(self, t): self.visible=True; self.display=True; self.update(t)
    def done(self): self.visible=False; self.display=False; self.update("")


class SideScroll(Container):
    """Scrollable sidebar content."""
    pass


class FridayApp(App):
    TITLE = "F.R.I.D.A.Y"
    SUB_TITLE = "Sovereign AI Agent"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("ctrl+s", "side", "Sidebar"),
        Binding("ctrl+t", "theme", "Theme"),
    ]

    def __init__(self, *, model_id="gemini-3.1-flash-live-preview", tools_count=0):
        super().__init__()
        self.mid = model_id
        self.tcnt = tools_count
        self._cb = None
        self._sh = True
        self._ti = 0
        self._buf = ""
        self._sa = False

    @property
    def T(self): return THEMES[self._ti % len(THEMES)]

    def action_theme(self):
        self._ti = (self._ti + 1) % len(THEMES)
        self.css = css(self.T)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="row"):
            with Container(id="side"):
                with SideScroll(id="side-scroll"):
                    yield Label("F.R.I.D.A.Y")
                    yield Static("", classes="si")
                    yield Label("\u2699 System")
                    yield Static("", id="si-m", classes="si")
                    yield Static("", id="si-t", classes="si")
                    yield Static("", id="si-c", classes="si")
                    yield Static("", classes="si")
                    yield Label("\u2318 Commands")
                    yield Static("  !townhall", classes="si")
                    yield Static("  !status", classes="si")
                    yield Static("  !theme", classes="si")
                    yield Static("  !help", classes="si")
                    yield Static("", classes="si")
                    yield Label("\u2328 Keys")
                    yield Static("  C-c quit", classes="si")
                    yield Static("  C-l clear", classes="si")
                    yield Static("  C-s sidebar", classes="si")
                    yield Static("  C-t theme", classes="si")
            with Container(id="col"):
                yield RichLog(id="log", highlight=True, markup=True)
                yield SW(id="sw")
                with Container(id="tray"):
                    yield Input(id="inp", placeholder="Message FRIDAY...")
        yield Footer()

    def on_mount(self):
        self.css = css(self.T)
        self.query_one("#si-m", Static).update(f"Model: {self.mid}")
        self.query_one("#si-t", Static).update(f"Tools: {self.tcnt}")
        self.query_one("#si-c", Static).update("[yellow]\u25cf connecting[/yellow]")
        self.query_one("#log", RichLog).write(
            RPanel(RTxt("  FRIDAY — Sovereign AI Agent\n  Neural link initializing...", style="bold cyan"), border_style="cyan"))

    def on_input_submitted(self, e):
        t = e.value.strip()
        if not t: return
        inp = self.query_one("#inp", Input)
        if t.startswith("!"):
            self._cmd(t); inp.clear(); return
        self._msg("You", t, "green")
        if self._cb: self._cb(t)
        inp.clear()

    def _cmd(self, c):
        log = self.query_one("#log", RichLog); ts = datetime.datetime.now().strftime("%H:%M")
        c = c.strip().lower()
        if c == "!townhall":
            try:
                from friday.townhall_app import launch_townhall
                r = launch_townhall()
                log.write(f"  {ts}  \u2192 Townhall PID {r.get('pid','?')}" if r.get("success") else f"  {ts}  \u2717 {r.get('error')}")
            except Exception as ex: log.write(f"  {ts}  \u2717 {ex}")
        elif c in ("!help","!h"): log.write(f"  {ts}  Commands: !townhall !status !theme !help")
        elif c == "!status": log.write(f"  {ts}  Model: {self.mid} | Tools: {self.tcnt} | Theme: {self.T['name']}")
        elif c == "!theme": self.action_theme()
        else: log.write(f"  {ts}  \u2717 unknown: {c}")

    def set_input_callback(self, cb): self._cb = cb
    def action_side(self): self._sh = not self._sh; self.query_one("#side").display = self._sh
    def action_clear(self): self.query_one("#log", RichLog).clear()

    def _msg(self, who, text, border):
        ts = datetime.datetime.now().strftime("%H:%M")
        try: self.query_one("#log", RichLog).write(RPanel(RMD(text), title=f"[bold {border}]{who}[/bold {border}]", subtitle=f"[dim]{ts}[/dim]", border_style=border))
        except: self.query_one("#log", RichLog).write(RPanel(RTxt(text, style=f"bold {border}"), title=f"[bold {border}]{who}[/bold {border}]", subtitle=f"[dim]{ts}[/dim]", border_style=border))

    def add_user_message(self, t): self._msg("You", t, "green")
    def add_friday_message(self, t): self._msg("FRIDAY", t, "cyan")
    def add_thought(self, t):
        ts = datetime.datetime.now().strftime("%H:%M")
        self.query_one("#log", RichLog).write(RPanel(RTxt(t, style="italic gray50"), title=f"[dim]Thought ({ts})[/dim]", border_style="gray37"))
    def add_system(self, t):
        ts = datetime.datetime.now().strftime("%H:%M")
        self.query_one("#log", RichLog).write(f"  {ts}  {t}")
    def add_tool_call(self, name, args=None):
        ts = datetime.datetime.now().strftime("%H:%M"); a = ""
        if args: a = " " + ", ".join(f"{k}={str(v)[:30]}" for k,v in list(args.items())[:3])
        self.query_one("#log", RichLog).write(f"  {ts}  \u25b6 [bright_yellow]{name}{a}[/bright_yellow]")
    def add_tool_result(self, name, result):
        ts = datetime.datetime.now().strftime("%H:%M")
        self.query_one("#log", RichLog).write(f"  {ts}  \u2713 [bright_green]{name} \u2192 {str(result)[:120]}[/bright_green]")
    def add_error(self, t):
        ts = datetime.datetime.now().strftime("%H:%M")
        self.query_one("#log", RichLog).write(RPanel(RTxt(t, style="bold red"), title=f"[bold red]Error ({ts})[/bold red]", border_style="red"))

    def start_stream(self):
        self._buf = ""; self._sa = True
        try: self.query_one("#sw", SW).start()
        except: pass

    def append_stream(self, t):
        if not self._sa: return
        self._buf += t
        try: self.query_one("#sw", SW).put(self._buf)
        except: pass

    def finalize_stream(self, t):
        self._sa = False
        if t: self._buf = t; self.add_friday_message(t)
        try: self.query_one("#sw", SW).done()
        except: pass
        self._buf = ""

    def cancel_stream(self):
        self._sa = False; self._buf = ""
        try: self.query_one("#sw", SW).done()
        except: pass

    def set_connection_status(self, s):
        c = {"connected":"green","connecting":"yellow","disconnected":"red","error":"red","dreaming":"blue","standby":"gray"}
        cl = c.get(s, "yellow")
        try: self.query_one("#si-c", Static).update(f"[bold {cl}]\u25cf {s}[/bold {cl}]")
        except: pass
