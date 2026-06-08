from friday.townhall_engine import *

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Input, RichLog, Static, Label, Button, ListView, ListItem
from textual import events
from rich.text import Text as RTxt
from rich.panel import Panel as RPanel
from rich.markdown import Markdown as RMD


TOWNHALL_CSS = """
Screen { background: #050510; }
Header { background: #0A0A1A; color: #00BFFF; border-bottom: solid #1A1A3A; }
#row { layout: horizontal; height: 1fr; }

#left { width: 28; height: 1fr; background: #0C0C20; border: solid #1A1A3A; margin: 1 0 1 1; padding: 0 1; overflow-y: auto; }
#left > Label { color: #00BFFF; text-style: bold; margin: 1 0; }
#left > Static { color: #686898; }

#center { width: 1fr; height: 1fr; background: #050510; border-top: solid #1A1A3A; border-bottom: solid #1A1A3A; margin: 1 0 1 0; layout: vertical; }
#circle-view { height: 1fr; padding: 0 1; }

#right { width: 40; height: 1fr; background: #0C0C20; border: solid #1A1A3A; margin: 1 1 1 0; layout: vertical; padding: 0 1; }
#right.fullscreen { dock: fill; width: 100%; height: 100%; border: thick #FFD700; }
#main-chat { height: 1fr; layout: vertical; }
#main-chat > Label { color: #00BFFF; text-style: bold; margin: 1 0; }
#main-log { height: 1fr; border: none; background: #080818; padding: 0 1; }
#task-chats { height: 12; min-height: 6; border-top: solid #1A1A3A; overflow-y: auto; }
#task-chats > Label { color: #FFD700; text-style: bold; margin: 1 0; }

#bottom { height: 1; background: #0A0A1A; color: #686898; padding: 0 1; border-top: solid #1A1A3A; }
Footer { background: #0A0A1A; color: #686898; border-top: solid #1A1A3A; }
.si { color: #686898; }
.chat-msg { margin: 0 0 0 1; }
.task-header { text-style: bold; }
.task-header:hover { color: #FFD700!important; }
"""


class AgentCircleWidget(Static):
    """Renders the n8n-style agent circle with FRIDAY at center."""

    def render_agents(self, agents: dict[str, AgentNode], connections: list[tuple[str, str]]):
        """Update the circle rendering."""
        lines = [""]
        lines.append("  [bold cyan]  \u2605 TOWN HALL \u2605  [/bold cyan]")
        lines.append("")

        # FRIDAY center
        f = agents.get("FRIDAY")
        fs = f"[bold cyan]FRIDAY[/bold cyan]" if f else "FRIDAY"
        friday_line = f"              [{STATUS_COLORS.get(f.status, 'gray') if f else 'gray'}]\u25c9[/] {fs}"
        lines.append(friday_line)
        lines.append("")

        # Top arc: SENTRY - FORGE - ECHO
        s = agents.get("SENTRY")
        fg = agents.get("FORGE")
        e = agents.get("ECHO")
        top = f"  [{STATUS_COLORS.get(s.status, 'gray') if s else 'gray'}]\u25cf[/] SENTRY  ---  [{STATUS_COLORS.get(fg.status, 'gray') if fg else 'gray'}]\u25cf[/] FORGE  ---  [{STATUS_COLORS.get(e.status, 'gray') if e else 'gray'}]\u25cf[/] ECHO"
        lines.append(top)

        # Lines connecting top to middle-left/right
        lines.append("     /         |         \\")

        # Mid arc: NOVA - ATLAS - (FRIDAY) - AEGIS - VERSE
        n = agents.get("NOVA")
        a = agents.get("ATLAS")
        ag = agents.get("AEGIS")
        v = agents.get("VERSE")
        mid = f"  [{STATUS_COLORS.get(n.status, 'gray') if n else 'gray'}]\u25cf[/] NOVA  ---  [{STATUS_COLORS.get(a.status, 'gray') if a else 'gray'}]\u25cf[/] ATLAS  ---  FRIDAY  ---  [{STATUS_COLORS.get(ag.status, 'gray') if ag else 'gray'}]\u25cf[/] AEGIS  ---  [{STATUS_COLORS.get(v.status, 'gray') if v else 'gray'}]\u25cf[/] VERSE"
        lines.append(mid)

        # Lines connecting mid to bottom
        lines.append("     \\         |         /")

        # Bottom arc: JARVIS - CRUX - LORE
        j = agents.get("JARVIS")
        c = agents.get("CRUX")
        l = agents.get("LORE")
        bot = f"  [{STATUS_COLORS.get(j.status, 'gray') if j else 'gray'}]\u25cf[/] JARVIS  ---  [{STATUS_COLORS.get(c.status, 'gray') if c else 'gray'}]\u25cf[/] CRUX  ---  [{STATUS_COLORS.get(l.status, 'gray') if l else 'gray'}]\u25cf[/] LORE"
        lines.append(bot)

        lines.append("")
        lines.append("  [dim]--- connections ---[/dim]")
        for a1, a2 in connections[:3]:
            col1 = self._get_color(agents, a1)
            col2 = self._get_color(agents, a2)
            lines.append(f"    [bold {col1}]{a1}[/bold {col1}] \u2194 [bold {col2}]{a2}[/bold {col2}]  [dim](task)[/dim]")

        if not connections:
            lines.append("  [dim]No active task connections[/dim]")

        lines.append("")
        lines.append("  [dim]\u25cb idle  \u25cf working  \u25c9 chat  \u25b6 dream[/dim]")
        lines.append("")

        self.update("\n".join(lines))

    def _get_color(self, agents: dict, name: str) -> str:
        a = agents.get(name.upper())
        return a.color if a else "white"


class TaskChatWidget(Static):
    """A single task-specific chat panel."""
    pass


class TownhallApp(App):
    TITLE = "F.R.I.D.A.Y Townhall"
    SUB_TITLE = "Multi-Agent Living Society"

    CSS = TOWNHALL_CSS

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("ctrl+e", "expand", "Expand Chat"),
        Binding("ctrl+r", "refresh", "Refresh"),
    ]

    def __init__(self):
        super().__init__()
        self.agents: dict[str, AgentNode] = {}
        self.channels: dict[str, ChatChannel] = {}
        self.dream_engine: Optional[DreamEngine] = None
        self._fullscreen = False
        self._selected_agent: Optional[str] = None
        self._connections: list[tuple[str, str]] = []
        self._expanded_task: str | None = None
        self._init_state()

    def _init_state(self):
        saved = self._load_state()
        chats = self._load_chats()

        # Initialize agents
        for profile in AGENT_PROFILES:
            name = profile["name"]
            if saved and name in saved:
                self.agents[name] = AgentNode.from_dict(saved[name])
            else:
                self.agents[name] = AgentNode(profile)

        # Initialize main channel
        if chats and "main" in chats:
            self.channels["main"] = ChatChannel.from_dict(chats["main"])
        else:
            self.channels["main"] = ChatChannel("main", "main")

        # Restore task channels
        if chats:
            for name, data in chats.items():
                if name != "main":
                    ch = ChatChannel.from_dict(data)
                    if ch.active:
                        self.channels[name] = ch

        self._save_state()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="row"):
            with Container(id="left"):
                yield Label("\ud83d\udc64 AGENT INFO")
                yield Static("Click an agent in the hall", id="agent-detail", classes="si")
                yield Static("")
                yield Label("\ud83d\udcca LEGEND")
                yield Static("  \u25cb idle   \u25cf working  \u25c9 chat", classes="si")
                yield Static("  \u25b6 dreaming  \u25cc away", classes="si")
                yield Static("  \u25d0 waiting", classes="si")
                yield Static("")
                yield Label("\u2318 COMMANDS")
                yield Static("  @agent ping", classes="si")
                yield Static("  @everyone broadcast", classes="si")
                yield Static("  /task <a> <desc>", classes="si")
                yield Static("  /info <agent>", classes="si")
                yield Static("  /agents", classes="si")
                yield Static("  /help", classes="si")

            with Container(id="center"):
                yield AgentCircleWidget(id="circle-view")
                yield Static("", id="connections-label")

            with Container(id="right"):
                with Container(id="main-chat"):
                    yield Label("\ud83d\udde3 MAIN CHAT")
                    yield RichLog(id="main-log", highlight=True, markup=True, max_lines=200)
                with Container(id="task-chats"):
                    yield Label("\ud83d\udd17 TASK CHATS")
                    yield Container(id="task-chats-list")

        yield Container(id="bottom")
        yield Footer()

    def on_mount(self):
        self.circle = self.query_one("#circle-view", AgentCircleWidget)
        self.main_log = self.query_one("#main-log", RichLog)
        self.agent_detail = self.query_one("#agent-detail", Static)
        self.task_container = self.query_one("#task-chats-list", Container)

        self._render_circle()
        self._render_main_chat()
        self._render_agent_info()
        self._render_task_chats()

        self.main_log.write("[bold cyan]Townhall initialized. Agents online.[/bold cyan]")
        self.main_log.write(f"[dim]{datetime.datetime.now().strftime('%H:%M')}  @mentions work like Discord[/dim]")

        self.dream_engine = DreamEngine(self.agents, self.channels, self._dream_log)
        self.dream_engine.start()

        self.set_interval(3, self._tick)

    def _dream_log(self, msg: str):
        try:
            self.main_log.write(msg)
            self._render_task_chats()
        except Exception:
            pass

    def _tick(self):
        self._render_circle()
        self._render_main_chat()
        self._render_agent_info()
        self._render_task_chats()
        self._save_state()

    def _render_circle(self):
        try:
            self.circle.render_agents(self.agents, self._connections)
        except Exception:
            pass

    def _render_main_chat(self):
        try:
            ch = self.channels.get("main")
            if not ch:
                return
            recent = ch.messages[-30:]
            # Only update if new messages
            if hasattr(self, '_last_msg_count') and self._last_msg_count == len(ch.messages):
                return
            self._last_msg_count = len(ch.messages)
            log = self.main_log
            log.clear()
            for msg in recent[-20:]:
                sender = msg["from"]
                text = msg["text"]
                if sender == "system":
                    log.write(f"[dim]{text}[/dim]")
                    continue
                agent = self.agents.get(sender)
                color = agent.color if agent else "white"
                ts = msg.get("time", "")[11:16] if msg.get("time") else ""
                mention_fmt = text
                import re
                mention_fmt = re.sub(r'@(\w+)', r'[bold yellow]@\1[/bold yellow]', mention_fmt)
                log.write(f"[dim]{ts}[/dim] [bold {color}]{sender}[/bold {color}]: {mention_fmt}")
        except Exception:
            pass

    def _render_agent_info(self):
        try:
            if not self._selected_agent:
                return
            agent = self.agents.get(self._selected_agent)
            if not agent:
                return
            lines = []
            lines.append(f"[bold {agent.color}]{agent.emoji} {agent.name}[/bold {agent.color}]")
            lines.append(f"  {agent.role}")
            lines.append(f"  Status: [{STATUS_COLORS.get(agent.status, 'gray')}]{agent.status}[/]")
            lines.append(f"  Mood: {agent.mood}")
            lines.append(f"  Task: {agent.current_task or 'None'}")
            lines.append("")
            lines.append("[bold]Personality:[/bold]")
            lines.append(f"  {agent.personality}")
            lines.append("")
            lines.append("[bold]Chats:[/bold]")
            for ch_name in agent.channels:
                ch = self.channels.get(ch_name)
                if ch:
                    lines.append(f"  \u2192 {ch.name} ({ch.type})")
            lines.append("")
            best_rel = sorted(agent.relationships.items(), key=lambda x: x[1]["friendship"], reverse=True)[:3]
            if best_rel:
                lines.append("[bold]Close relationships:[/bold]")
                for rname, rdata in best_rel:
                    heart = "\u2764" if rdata["friendship"] > 70 else "\ud83e\udd1d" if rdata["friendship"] > 40 else "\ud83e\udd37"
                    lines.append(f"  {heart} {rname}: {rdata['friendship']}/100 ({rdata['interactions']} chats)")
            lines.append("")
            if agent.dream_log:
                lines.append("[bold]Recent thoughts:[/bold]")
                for thought in agent.dream_log[-3:]:
                    lines.append(f"  [dim]{thought[:60]}[/dim]")
            self.agent_detail.update("\n".join(lines))
        except Exception:
            pass

    def _render_task_chats(self):
        try:
            self.task_container.remove_children()
            task_channels = [c for c in self.channels.values()
                             if c.type == "task" and c.active and c.messages]
            for ch in task_channels:
                expanded = self._expanded_task == ch.name
                marker = "\u25bc" if expanded else "\u25b6"
                color = "#FFD700" if expanded else "#686898"
                header = Static(
                    f"[bold {color}]{marker} {ch.name}[/bold {color}]  [dim]({', '.join(ch.participants)})[/dim]"
                )
                header._channel_name = ch.name
                header.classes = "task-header"
                self.task_container.mount(header)
                msg_limit = 100 if expanded else 10
                log = RichLog(highlight=True, markup=True, max_lines=msg_limit)
                log.classes = "chat-msg"
                msgs = ch.messages[-msg_limit:]
                for msg in msgs:
                    if msg["from"] == "system":
                        log.write(f"[dim]{msg['text']}[/dim]")
                        continue
                    agent = self.agents.get(msg["from"])
                    color = agent.color if agent else "white"
                    log.write(f"[bold {color}]{msg['from']}[/bold {color}]: {msg['text'][:200]}")
                self.task_container.mount(log)
                if expanded and len(ch.messages) > 100:
                    self.task_container.mount(
                        Static(f"[dim]... {len(ch.messages) - 100} more messages[/dim]")
                    )
        except Exception:
            pass

    def action_clear(self):
        self.main_log.clear()
        ch = self.channels.get("main")
        if ch:
            ch.messages = []

    def action_expand(self):
        self._fullscreen = not self._fullscreen
        right = self.query_one("#right")
        right.set_class(self._fullscreen, "fullscreen")
        if self._fullscreen:
            self.main_log.write("[dim]Fullscreen mode. Ctrl+E to collapse.[/dim]")

    def action_refresh(self):
        self._render_circle()

    def handle_message(self, text: str):
        ts = datetime.datetime.now().strftime("%H:%M")
        text = text.strip()

        if not text:
            return

        # Commands
        if text.startswith("/"):
            self._handle_command(text)
            return

        # @mentions in any text
        self._handle_mention_text(text)

        # Send to main chat
        ch = self.channels.get("main")
        if ch:
            ch.add_message("User", text)
            self.main_log.write(f"[dim]{ts}[/dim] [bold green]You[/bold green]: {text}")
            self._render_main_chat()

            # FRIDAY responds if in main chat
            friday = self.agents.get("FRIDAY")
            if friday and "main" in friday.channels:
                reply = self._generate_user_response(text)
                ch.add_message("FRIDAY", reply)
                self.main_log.write(f"[dim]{ts}[/dim] [bold cyan]FRIDAY[/bold cyan]: {reply}")
                self._render_main_chat()

    def _handle_command(self, text: str):
        ts = datetime.datetime.now().strftime("%H:%M")
        cmd = text[1:].strip().split(maxsplit=2)
        if not cmd:
            return

        main_cmd = cmd[0].lower()

        if main_cmd == "clear":
            self.action_clear()
            return

        if main_cmd == "help":
            self.main_log.write(f"  {ts}  Commands: /info <agent>, /agents, /task <agent> <desc>, /create_chat <name> <agents...>, /clear, /help")
            self.main_log.write(f"  {ts}  Mention: @agent or @everyone to ping")
            return

        if main_cmd == "agents":
            for a in self.agents.values():
                sc = STATUS_COLORS.get(a.status, "gray")
                sd = STATUS_DOTS.get(a.status, "\u25cb")
                self.main_log.write(f"  [{sc}]{sd}[/{sc}] [bold {a.color}]{a.name:8}[/bold {a.color}] [dim]{a.role}[/dim]")
            return

        if main_cmd == "info" and len(cmd) >= 2:
            target = cmd[1].upper()
            if target in self.agents:
                self._selected_agent = target
                self._render_agent_info()
                self.main_log.write(f"  {ts}  Showing info for [bold]{target}[/bold]")
            else:
                self.main_log.write(f"  {ts}  [red]Unknown: {target}[/red]")
            return

        if main_cmd == "task" and len(cmd) >= 2:
            parts = text[1:].strip().split(maxsplit=2)
            if len(parts) >= 3:
                target = parts[1].upper()
                desc = parts[2]
                if target in self.agents:
                    self._assign_task(target, desc)
                else:
                    self.main_log.write(f"  {ts}  [red]Unknown agent: {target}[/red]")
            else:
                self.main_log.write(f"  {ts}  Usage: /task <agent> <description>")
            return

        if main_cmd == "create_chat" and len(cmd) >= 3:
            parts = text[1:].strip().split(maxsplit=2)
            if len(parts) >= 3:
                chat_name = parts[1]
                agent_names = [a.strip().upper() for a in parts[2].split(",")]
                valid = [a for a in agent_names if a in self.agents]
                if len(valid) >= 2:
                    self._create_task_chat(chat_name, valid)
                else:
                    self.main_log.write(f"  {ts}  [red]Need 2+ valid agents[/red]")
            return

        self.main_log.write(f"  {ts}  [red]Unknown: {text}[/red]")

    def _handle_mention_text(self, text: str):
        import re
        mentions = re.findall(r'@(\w+)', text)
        for name in mentions:
            name_upper = name.upper()
            if name_upper == "EVERYONE":
                self.main_log.write(f"[bold yellow]\u23f0 @everyone ping![/bold yellow]")
                for agent in self.agents.values():
                    if agent.name != "FRIDAY" and not agent.is_away and random.random() > FREE_WILL_IGNORE_CHANCE:
                        self.main_log.write(f"[dim]{agent.name} acknowledged[/dim]")
            elif name_upper in self.agents:
                agent = self.agents[name_upper]
                self.main_log.write(f"[bold yellow]\u23f0 @{agent.name} pinged![/bold yellow]")
                if not agent.is_away and random.random() > FREE_WILL_IGNORE_CHANCE:
                    ch = self.channels.get("main")
                    if ch:
                        reply = f"@{text.split('@')[0].strip() or 'someone'} I'm here. What's up?"
                        ch.add_message(agent.name, reply)
                        self.main_log.write(f"[bold {agent.color}]{agent.name}[/bold {agent.color}]: {reply}")

    def _assign_task(self, agent_name: str, desc: str):
        ts = datetime.datetime.now().strftime("%H:%M")
        agent = self.agents.get(agent_name)
        if not agent:
            self.main_log.write(f"  {ts}  [red]Unknown: {agent_name}[/red]")
            return

        agent.set_status("working", desc)
        agent.goals.append(desc)

        # Check if another agent has a similar task
        similar = []
        for a in self.agents.values():
            if a.name != agent_name and a.current_task and (
                any(w in a.current_task.lower() for w in desc.lower().split()[:3])
            ):
                similar.append(a.name)

        ch = self.channels.get("main")
        if ch:
            ch.add_message("FRIDAY", f"@{agent_name} assigned: {desc}")
            self.main_log.write(f"  {ts}  [bold cyan]FRIDAY[/bold cyan] \u2192 [bold]{agent_name}[/bold]: {desc}")

        # If similar tasks found, create a task chat
        if similar:
            chat_name = f"task-{agent_name.lower()}-{'-'.join(s.lower() for s in similar)}"
            participants = [agent_name] + similar
            if chat_name not in self.channels:
                self._create_task_chat(chat_name, participants)
                self.main_log.write(f"  {ts}  [bold green]\ud83d\udd17 Created task chat: {chat_name}[/bold green]")
                ch.add_message("FRIDAY", f"@{' @'.join(participants)} you're grouped in {chat_name} for collaboration.")
                self.main_log.write(f"  {ts}  [bold cyan]FRIDAY[/bold cyan]: @{' @'.join(participants)} grouped for {desc}")

    def _create_task_chat(self, name: str, participants: list[str]):
        ch = ChatChannel(name, "task", f"Collaboration: {', '.join(participants)}")
        ch.participants = participants
        ch.add_message("system", f"Task chat created. Participants: {', '.join(participants)}")
        for p in participants:
            agent = self.agents.get(p)
            if agent:
                agent.channels.append(name)
                agent.set_status("working", f"In task: {name}")
        self.channels[name] = ch
        self._connections.append((participants[0], participants[1] if len(participants) > 1 else participants[0]))
        self._render_task_chats()
        return ch

    def _generate_user_response(self, text: str) -> str:
        text_lower = text.lower()
        if "status" in text_lower:
            statuses = ", ".join(f"{a.name}: {a.status}" for a in self.agents.values())
            return f"All agents accounted for. {statuses}"
        if "agent" in text_lower or "who" in text_lower:
            names = ", ".join(a.name for a in self.agents.values() if a.name != "FRIDAY")
            return f"Everyone's here: {names}"
        if "task" in text_lower or "assign" in text_lower:
            busy = [a for a in self.agents.values() if a.current_task]
            if busy:
                return f"Active: {', '.join(f'{a.name}: {a.current_task}' for a in busy[:3])}"
            return "All agents idle. Ready for assignments."
        if "chat" in text_lower or "talk" in text_lower:
            return "Main channel is active. Agents are chatting. Want me to join or assign task groups?"
        responses = [
            "On it. Let me check with the team.",
            "Acknowledged. Agents are on standby.",
            "I'll delegate accordingly. Status nominal.",
            "Team's ready whenever you need them.",
            "I hear you. Want me to pull anyone specific?",
        ]
        return random.choice(responses)

    def _load_state(self) -> dict | None:
        try:
            if TOWNHALL_STATE_PATH.exists():
                return json.loads(TOWNHALL_STATE_PATH.read_text())
        except Exception:
            return None

    def _save_state(self):
        try:
            TOWNHALL_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {name: agent.to_dict() for name, agent in self.agents.items()}
            data["_updated"] = datetime.datetime.now().isoformat()
            data["_connections"] = self._connections
            TOWNHALL_STATE_PATH.write_text(json.dumps(data, indent=2))
            # Save chats
            chats = {name: ch.to_dict() for name, ch in self.channels.items()}
            TOWNHALL_CHATS_PATH.write_text(json.dumps(chats, indent=2))
        except Exception:
            pass

    def _load_chats(self) -> dict | None:
        try:
            if TOWNHALL_CHATS_PATH.exists():
                return json.loads(TOWNHALL_CHATS_PATH.read_text())
        except Exception:
            return None

    def on_click(self, event):
        channel_name = getattr(event.widget, '_channel_name', None)
        if channel_name and channel_name in self.channels:
            if self._expanded_task == channel_name:
                self._expanded_task = None
            else:
                self._expanded_task = channel_name
            self._render_task_chats()
            return
        self._handle_circle_click(event)

    def on_key(self, event):
        if event.key == "escape" and self._fullscreen:
            self.action_expand()
            event.prevent_default()

    def _handle_circle_click(self, event):
        """Click on circle agents to select them."""
        try:
            widget = self.query_one("#circle-view")
            if event.widget == widget:
                # Map click to agent positions
                y = abs(event.y - widget.region.y) if hasattr(event, 'y') else 0
                x = abs(event.x - widget.region.x) if hasattr(event, 'x') else 0
                # Simple mapping: click zones for agents
                if x < 10 and y < 5:
                    self._selected_agent = "SENTRY"
                elif x > 40 and y < 5:
                    self._selected_agent = "ECHO"
                elif 15 < x < 30 and y < 5:
                    self._selected_agent = "FORGE"
                elif x < 10 and y > 8:
                    self._selected_agent = "JARVIS"
                elif x > 40 and y > 8:
                    self._selected_agent = "LORE"
                elif x < 15 and 5 < y < 8:
                    self._selected_agent = "NOVA"
                elif 15 < x < 20 and 5 < y < 8:
                    self._selected_agent = "ATLAS"
                elif 30 < x < 35 and 5 < y < 8:
                    self._selected_agent = "AEGIS"
                elif x > 35 and 5 < y < 8:
                    self._selected_agent = "VERSE"
                elif 25 < x < 31 and 5 < y < 8:
                    self._selected_agent = "CRUX"
                else:
                    self._selected_agent = "FRIDAY"
                self._render_agent_info()
                ts = datetime.datetime.now().strftime("%H:%M")
                self.main_log.write(f"  {ts}  [dim]Selected: {self._selected_agent}[/dim]")
        except Exception:
            pass

    def action_townhall(self):
        pass  # Already here


def launch_townhall():
    """Launch Townhall in a separate process."""
    try:
        script = str(Path(__file__).resolve())
        proc = subprocess.Popen(
            [sys.executable, "-c", f"""
import sys; sys.path.insert(0, r'{os.path.dirname(os.path.dirname(__file__))}')
from friday.townhall_app import TownhallApp
TownhallApp().run()
"""],
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
        )
        return {"success": True, "pid": proc.pid}
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    TownhallApp().run()

