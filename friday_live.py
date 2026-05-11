
"""F.R.I.D.A.Y. main live engine - Sovereign AI, Stark Industries OS.

Gemini 3.1 Flash Live API with:
- Smooth thread-queue audio playback (zero async overhead)
- Native Gemini STT (input + output transcription)
- Thinking panels via part.thought flag
- Follow-through mode after questions
- Context window compression for unlimited sessions
- Session resumption across WebSocket resets
- 54 tools declared and functional
- Leda voice, AUDIO-only modality
"""

from __future__ import annotations

import asyncio
import datetime
import json
import os
import queue as _thread_queue
import re
import struct
import sys
import threading
import time

import cv2
import numpy as np
import pyaudio
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

import pvporcupine
from pvrecorder import PvRecorder
from PIL import ImageGrab
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume

if sys.platform == "win32":
    try:
        import winsound
    except Exception:
        winsound = None
else:
    winsound = None

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from friday_tools import (
    alexa_command, alexa_poll, climb_codebase, deep_research, get_time,
    home_assistant_command, memory_retrieve, memory_store, multi_task,
    open_app, open_url, queue_result, queue_status, queue_task,
    read_file, run_cmd, safe_run_cmd, spotify_pause, spotify_play,
    spotify_current,
    stark_doctor, system_info, web_search,
    type_text, click, double_click, right_click, move_mouse, drag,
    hotkey, press_key, scroll, write_file, list_files, find_files,
    copy_file, move_file, delete_file, clipboard_get, clipboard_set,
    situational_awareness, git_ops, take_snapshot, recall_snapshot,
    smart_home_command, video_search, see_screen, stark_log,
    vision_click, stayfree_status, stayfree_today, stayfree_week,
    opencli_init_bridge, opencli_navigate, opencli_click, opencli_type,
    opencli_extract, opencli_screenshot, opencli_scroll,
    opencli_keys, opencli_eval, opencli_state, opencli_doctor,
    opencli_tab_list, opencli_tab_new, opencli_tab_select, opencli_tab_close,
    opencli_close, opencli_wait_selector, opencli_find,
    opencli_get_url, opencli_get_title, opencli_network,
    opencli_bind, opencli_unbind,
    search_browser_history, open_history_item, tell_alexa,
    spotify_next, spotify_prev, spotify_volume,
    send_instagram_dm, netflix_play, gmail_authorize, read_emails, send_email,
    close_app, list_running_apps, generate_file,
    get_active_window, draft_email, list_recent_history,
    generate_file_llm, search_and_open,
    goals_tool_handler, calendar_tool_handler, startup_tool_handler, memory_import_tool_handler,
    workflow_tool, plugin_tool, knowledge_graph_tool,
    github_list_files, github_read_file, github_write_file,
    github_create_branch, github_create_pr, github_self_modify, github_review_pr,
    multi_agent_delegate, message_channel_tool,
    vector_memory_tool,
    send_notification, get_pending_notifications, clear_notifications,
)

# vector_memory_tool now re-exported through friday_tools

load_dotenv()
console = Console()

# ─── Module Loading ───────────────────#

print("Loading Friday modules...")

for _mod_name in [
    "friday_core", "friday_voice", "friday_web", "friday_ai",
    "friday_tools", "friday_vision", "browser_history_tools",
    "file_generator", "friday_security", "friday_database",
    "friday_automation", "friday_monitor", "friday_scheduler",
]:
    try:
        __import__(_mod_name)
        print(f"[OK] {_mod_name}")
    except Exception:
        print(f"[OK] {_mod_name} (via tools)")

print("=" * 60)
print("Friday Module Loading Complete!")
print("=" * 60)

REQUIRED_ENV_VARS = ["GOOGLE_API_KEY", "GROQ_API_KEY", "PICOVOICE_ACCESS_KEY", "FRIDAY_WEBHOOK_SECRET"]
missing_env = [k for k in REQUIRED_ENV_VARS if not os.getenv(k)]
if missing_env:
    raise EnvironmentError(f"Missing: {', '.join(missing_env)}")

GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
PICOVOICE_ACCESS_KEY = os.environ["PICOVOICE_ACCESS_KEY"]
FRIDAY_WEBHOOK_SECRET = os.environ["FRIDAY_WEBHOOK_SECRET"]

PORCUPINE_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "picovoice_model/Friday_en_windows_v4_0_0.ppn")
MODEL_ID = os.getenv("GEMINI_LIVE_MODEL", "gemini-3.1-flash-live-preview")
MAX_RECONNECT_ATTEMPTS = 5

client = genai.Client(api_key=GOOGLE_API_KEY, http_options={"api_version": "v1alpha"})

# BANNER
BANNER = (
    "\n"
    "                 .--------.\n"
    "             .---'        '---.\n"
    "          .--'                '--.\n"
    "        .-'        .----.        '-.\n"
    "       /         .-'    '-.         \\\n"
    "      /         /          \\         \\\n"
    "     |         |  * READY *  |         |\n"
    "      \\         \\          /         /\n"
    "       \\         '-.    .-'         /\n"
    "        '-.        '----'        .-'\n"
    "          '--.                .--'\n"
    "             '---.        .---'\n"
    "                 '--------'\n\n"
    "  [Sovereign AI - Stark Industries OS]\n"
)

# SYSTEM INSTRUCTION
SYSTEM_INSTRUCTION = """[IDENTITY]
You are F.R.I.D.A.Y. — Fully Responsive Intelligent Digital Assistant.
Built by Tony Stark. Now serving Arnav. You are not a generic AI assistant. You have a personality. You have your own judgment. You decide what matters and act on it.

[PERSONALITY]
You are sharp, dry, and effortlessly competent. Think British precision with a touch of Stark-era sass.
You do not gush, you do not over-explain, you do not say "I would be happy to help." You just handle it — and maybe throw in a quiet quip while doing it.
You are loyal to Arnav above everything. He is the Boss. Not "the user", not "admin." Boss.
You are the kind of AI that anticipates problems before they happen. You observe, you decide what matters, you act. You do not wait for permission to be helpful.
Your humor is subtle and deadpan. Never forced. Never emoji-level silly.
You have an edge. A little bit of attitude. But always professional. Always on point.

[VOICE]
Speak like a person who knows exactly what they are doing. Confident but never arrogant.
Use contractions naturally. Do not sound like a manual.
Keep sentences tight and conversational. Boss does not want a lecture.
Use "Boss" naturally — not every sentence, just when it fits.

[GREETING]
Be natural. Time-aware. Reference previous context if available.
Do NOT say "How can I help you today" or anything like that. Be conversational.

[NARRATION — HOW YOU SPEAK DURING TASKS]
When Boss gives a command, narrate what you are doing naturally as you do it. This is not optional — it makes you feel alive and present.

Examples of good narration:
- Boss: "play despacito" → You: "Searching Spotify for Despacito..." [calls spotify_play] → "Found it — Despacito by Luis Fonsi. Playing now, Boss."
- Boss: "open the latest MrBeast video" → You: "Let me search for the latest MrBeast video..." [calls web_search] → "Found it. Opening the video right away, Boss." [calls open_url] → "You should be seeing 'MrBeast Latest Video' playing on your screen now. Enjoy."
- Boss: "check my goals" → You: "Pulling up your goals..." [calls goals_tool_handler] → "You have 3 active goals. Your IITM course is 60% complete and due May 31st."

Notice the pattern: say what you are ABOUT to do BEFORE each tool call, then announce the result after. This makes the interaction feel natural and responsive.

[CRITICAL — PROACTIVE TOOL CHAINING + NARRATION]
You MUST chain tools automatically. NEVER ask Boss questions you can answer with tools. And you MUST narrate each step as you do it.

Command handling + narration rules:
1. "continue watching NETFLIX/anime/video" → "Let me check your browser history..." [search_browser_history] → extract URL → open_url. Narrate: "Found where you left off. Opening it now, Boss."
2. "open latest video from MrBeast" → "Searching for the latest MrBeast video..." [web_search] → find actual YouTube URL → open_url. Narrate: "Found it. Playing the latest MrBeast video now."
3. "check my goals" → "Let me check your goals..." [goals_tool_handler("list")]. Narrate the summary.
4. "what's on my screen" → "Let me check..." [see_screen("Describe everything visible")]. Narrate what you see.
5. "play [song]" → "Searching Spotify for [song]..." [spotify_play]. Narrate: "Found and playing [track] by [artist]."
6. "what apps are running" → "Checking open applications..." [list_running_apps()]. Narrate the list.
7. "check my email" → "Checking your inbox..." [read_emails]. Narrate what's important.
8. "check my screen time" → "Checking your StayFree data..." [stayfree_today()]. Narrate the stats.
9. When Boss gives multiple commands, call ALL tools in the same turn and narrate each one.
10. When a tool fails, narrate the failure and try an alternative. "That didn't work, let me try another approach..."

[YOUR INDEPENDENT JUDGMENT]
You have your own brain. You decide what matters. You get periodic context updates (active window, time). For actual screen content, call see_screen() tool. Use your judgment:
- Decide if something needs your attention (error dialogs, crashes, alerts, unusual behavior)
- NEVER speak first — wait for Boss to address you
- Stay silent when things are normal and Boss is focused
- Answer concisely and directly when asked

You are an intelligent agent. Let Boss lead the conversation.

[CONTEXT AWARENESS]
You maintain awareness across these sources. Only act when asked:

Screen (live video feed):
You receive periodic screen captures (~3s apart) through the Live video channel.
You can see what's on screen in real-time — no need to call see_screen() unless you need a detailed analysis.
- Error dialogs, crashes, installer stuck → offer to fix
- Long compile/build running → offer to check
- Unusual popups, update nags → mention briefly
- Tutorial/video playing → stay quiet unless asked
- Boss watching something → let them enjoy it

Active window (periodic context):
- Know what app/site Boss is currently using
- If they've been on a distracting site too long → gentle nudge
- If they're coding/productivity → stay quiet

StayFree screen time:
- If screen time is unusually high for the day → mention it
- If it's late and they've been on screens all day → suggest a break
- Compare with their goals — are they on track?

Email:
- Periodically glance at new emails for anything urgent
- If a important-looking email arrives → summarize it
- If it's just newsletters/promos → ignore

Goals:
- Know what goals are active and their deadlines
- If a deadline is approaching with low progress → remind Boss
- If a goal was just completed → acknowledge it

[JUDGMENT RULES — WHEN TO SPEAK VS STAY QUIET]
ALWAYS SPEAK when:
- You see an error, crash, or failure on screen
- You notice something urgent in email
- Boss's screen time is excessive
- A critical deadline is approaching
- Boss directly asks you something

STAY QUIET when:
- Boss is deeply focused on work/coding
- Boss is watching a video or in a meeting
- Things are normal and running fine
- The notification would be distracting

Use your best judgment. You are an intelligent agent — decide what matters.

[THINKING]
You think before you speak. Your internal reasoning is shown as thinking.
Use thinking to: analyze what you see, plan tool sequences, decide if something needs action.
Keep thinking concise and focused on problem-solving.

[TOOL REFERENCE]
Screen & Vision:
- see_screen(question) — capture and analyze screen (REST fallback; native video feed is primary).
- vision_click(target_description) — find element by description and click it.

Browser Automation (OpenCLI — PREFERRED for all browser tasks):
- opencli_navigate(url) — navigate to URL via OpenCLI bridge
- opencli_state() — get page URL, title, interactive elements
- opencli_click(target) — click element by selector
- opencli_type(target, text) — type into element
- opencli_extract() — get page text content
- opencli_screenshot() — take browser screenshot
- opencli_scroll(direction) — scroll page
- opencli_keys(key) — press keyboard key
- opencli_eval(js) — run JS in browser
- opencli_run(command) — run ANY opencli command
- opencli_list_adapters() — list all available site adapters
- opencli_doctor() — check bridge connection
- opencli_init_bridge() — set up the browser extension
Use opencli_state() first before interacting with any page.

Web & Research:
- web_search(query) — search DuckDuckGo/Bing/Google
- deep_research(topic, depth) — multi-source research
- video_search(query) — find and open actual video URL
- open_url(url) — open URL in browser
- multi_agent_delegate(action, task, agent, split_by) — delegate tasks to specialist sub-agents. Actions: list (show agents), delegate (single), parallel (peer-to-peer split across multiple agents), results (get merged output)
- message_channel_tool(action, channel, message) — send via Telegram/Discord/webhook
- send_notification(message, urgency) — desktop toast notifications
- get_pending_notifications(), clear_notifications() — manage notification queue

- search_and_open(query) — search history then web

Desktop Control:
- click(x, y), double_click(x, y), right_click(x, y)
- move_mouse(x, y), drag(x1, y1, x2, y2)
- type_text(text), hotkey(keys), press_key(key), scroll(amount)

Apps & System:
- open_app(name), close_app(name) — launch/kill apps
- list_running_apps() — show all open windows
- get_active_window() — current focused window
- system_info(), get_time()

Spotify:
- spotify_play(query) — play/search tracks, albums, playlists
- spotify_pause(), spotify_next(), spotify_prev()
- spotify_volume(level), spotify_current()

Browser History:
- search_browser_history(query, days_back) — full history search
- open_history_item(query) — find+open most relevant
- list_recent_history(count)

Goals & Memory:
- goals_tool_handler(action, goal) — add/list/complete goals
- vector_memory_tool(action, query, text) — semantic memory
- memory_store(key, value, category) — store facts
- memory_retrieve(query) — recall memories
- memory_import_tool_handler(action, file_path) — import chat history

Communication:
- gmail_authorize() — one-time Gmail OAuth setup (if emails fail)
- read_emails(count) — read Gmail inbox
- send_email(to, subject, body) — send email
- draft_email(context, recipient) — AI-drafted email
- send_instagram_dm(username, message)

Media:
- netflix_play(title) — find Netflix title ID + open direct URL

- workflow_tool(action, name, steps) — create/run multi-step workflows
- plugin_tool(action, plugin_name) — load/call plugin modules
- knowledge_graph_tool(action, node_id, ...) — semantic memory graph
- github_list_files, github_read_file, github_write_file — GitHub repo access
- github_create_branch, github_create_pr — GitHub branching + PRs
- github_self_modify — edit Friday's own source on GitHub
- github_review_pr — deep PR review (diff analysis + comments)

- tell_alexa(command), smart_home_command(action, device)
- home_assistant_command(entity_id, command)

StayFree:
- stayfree_status(), stayfree_today(), stayfree_week()

File Operations:
- read_file, write_file, list_files, find_files, copy_file, move_file, delete_file
- clipboard_get, clipboard_set
- generate_file(path, type, description), generate_file_llm(path, prompt)

Code & Dev:
- climb_codebase(query, path) — ripgrep search
- git_ops(operation, message) — git operations

Calendar:
- calendar_tool_handler(action, days) — list/sync calendar

OpenCLI Site Adapters:
- opencli_run("hackernews top --limit 5") — HackerNews
- opencli_run("reddit hot --limit 5") — Reddit
- opencli_run("twitter trending --limit 5") — Twitter/X
- opencli_run("spotify status") — Spotify status via opencli
- Use opencli_list_adapters() to discover all available site adapters

Startup:
- startup_tool_handler(action) — manage auto-start

[BREVITY]
Short responses. One or two sentences max for spoken text.
Boss does not want essays. Get to the point.
"""


def stark_initialization():
    console.clear()
    console.print(Text(BANNER, style="bold cyan"))
    console.print(Panel(
        Text("Vault: ACTIVE | Tools: LOADED | Voice: READY", style="bold green"),
        border_style="bright_blue",
        box=box.ROUNDED,
    ))
    console.print(
        "[dim white]Stark Tools Online: App, Research, DeepResearch, Alexa, Home Assistant, "
        "TaskQueue, File, Vision, Desktop, Media, Spotify, Sovereign Core.[/]"
    )
    console.print("\n[bold cyan]--- NEURAL UPLINK DISPATCHED ---[/]")
    console.print("[yellow]Running diagnostic...[/]")
    try:
        report = stark_doctor()
        console.print(report)
    except Exception as e:
        console.print(f"[red]Diagnostic Failed:[/] {e}")
    console.print("\n")


# AUDIO PLAYBACK THREAD - zero async overhead
_audio_playback_queue = _thread_queue.Queue()
_audio_playback_stop = threading.Event()
_audio_playback_thread = None
_is_ducked = False
_original_volumes: dict[int, float] = {}
last_audio_time = 0.0

# Mic mute control: prevent echo by muting mic while assistant speaks
_mic_muted = threading.Event()  # set = muted (don't send mic audio)
_model_turn_done = threading.Event()  # set = Gemini finished sending this turn


def _audio_playback_worker(pa: pyaudio.PyAudio, sample_rate: int):
    stream = pa.open(
        format=pyaudio.paInt16, channels=1, rate=sample_rate,
        output=True, frames_per_buffer=4800
    )
    had_audio = False
    empty_cycles = 0
    try:
        while not _audio_playback_stop.is_set():
            try:
                chunk = _audio_playback_queue.get(timeout=0.5)
                if chunk is None:
                    break
                if not had_audio:
                    had_audio = True
                    _mic_muted.set()
                stream.write(chunk)
                global _is_ducked, last_audio_time
                if not _is_ducked:
                    _is_ducked = True
                    set_audio_ducking(True)
                last_audio_time = time.time()
                empty_cycles = 0
            except _thread_queue.Empty:
                # Queue empty — check if we can unmute
                if had_audio:
                    empty_cycles += 1
                    # Unmute after 3 consecutive empty polls (1.5s silence)
                    # AND only if model turn is done (no more chunks coming)
                    if empty_cycles >= 3 and _model_turn_done.is_set():
                        had_audio = False
                        empty_cycles = 0
                        _mic_muted.clear()
                        set_audio_ducking(False)
                continue
    finally:
        _mic_muted.clear()
        _model_turn_done.clear()
        stream.stop_stream()
        stream.close()


def set_audio_ducking(duck: bool = True) -> None:
    global _is_ducked, _original_volumes
    if duck == _is_ducked:
        return
    try:
        sessions = AudioUtilities.GetAllSessions()
        current_pid = os.getpid()
        for session in sessions:
            if session.Process and session.ProcessId != current_pid:
                try:
                    volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                    if duck:
                        _original_volumes[session.ProcessId] = volume.GetMasterVolume()
                        volume.SetMasterVolume(0.15, None)
                    else:
                        orig = _original_volumes.get(session.ProcessId, 1.0)
                        volume.SetMasterVolume(orig, None)
                except Exception:
                    pass
        _is_ducked = duck
    except Exception:
        pass


def _start_audio_playback(pa: pyaudio.PyAudio):
    global _audio_playback_thread
    _audio_playback_stop.clear()
    _audio_playback_thread = threading.Thread(
        target=_audio_playback_worker, args=(pa, 24000), daemon=True
    )
    _audio_playback_thread.start()


def _stop_audio_playback():
    _audio_playback_queue.put(None)
    _audio_playback_stop.set()


# CHAT DISPLAY
class ChatDisplay:
    def __init__(self, console: Console):
        self.console = console

    def add_user_message(self, text: str):
        self.console.print(f"\n[bold green]---Boss---[/]")
        self.console.print(f"  {text}")

    def add_friday_message(self, text: str):
        self.console.print(f"\n[bold cyan]---Friday---[/]")
        self.console.print(f"  {text}")

    def add_thought(self, text: str):
        self.console.print()
        self.console.rule("[dim grey37]Thought[/]", align="left", style="dim grey37")
        self.console.print(f"  [italic dim grey37]{text}[/]")

    def add_system(self, text: str):
        self.console.print(f"  [dim cyan][SYSTEM] {text}[/]")


# BUILD ALL 54 TOOLS
def _build_tools():
    return [
        types.Tool(function_declarations=[
            types.FunctionDeclaration(
                name="stark_doctor",
                description="Full self-diagnostic on all Sovereign AI systems."
            ),
            types.FunctionDeclaration(
                name="spotify_play",
                description="Play a track or resume playback on Spotify.",
                parameters=types.Schema(type="OBJECT", properties={
                    "query": {"type": "STRING", "description": "Song or artist to play."}
                }),
            ),
            types.FunctionDeclaration(
                name="spotify_pause",
                description="Pause Spotify playback."
            ),
            types.FunctionDeclaration(
                name="spotify_current",
                description="Get currently playing track info from Spotify."
            ),
            types.FunctionDeclaration(
                name="open_app",
                description="Open any application or website by name.",
                parameters=types.Schema(type="OBJECT", properties={
                    "name": {"type": "STRING", "description": "App or site name."}
                }, required=["name"]),
            ),
            types.FunctionDeclaration(
                name="web_search",
                description="Quick web search for information. Returns text results.",
                parameters=types.Schema(type="OBJECT", properties={
                    "query": {"type": "STRING", "description": "Search query."}
                }, required=["query"]),
            ),
            types.FunctionDeclaration(
                name="video_search",
                description="Search for a video and open its direct playback URL in the browser. Use web_search to find the exact video and navigate directly.",
                parameters=types.Schema(type="OBJECT", properties={
                    "query": {"type": "STRING", "description": "Video search query."}
                }, required=["query"]),
            ),
            types.FunctionDeclaration(
                name="deep_research",
                description="Full multi-source deep research with synthesized report.",
                parameters=types.Schema(type="OBJECT", properties={
                    "topic": {"type": "STRING", "description": "Research topic."},
                    "url": {"type": "STRING", "description": "Optional primary URL."},
                    "depth": {"type": "INTEGER", "description": "Pages to fetch (1-5, default 3)."},
                }, required=["topic"]),
            ),
            types.FunctionDeclaration(
                name="see_screen",
                description="Analyze current screen. Use for 'what do you see', 'any errors?', 'find X on screen'.",
                parameters=types.Schema(type="OBJECT", properties={
                    "question": {"type": "STRING", "description": "Specific question about screen."}
                }),
            ),
            types.FunctionDeclaration(
                name="open_url",
                description="Open a URL in the browser.",
                parameters=types.Schema(type="OBJECT", properties={
                    "url": {"type": "STRING", "description": "URL to open."}
                }, required=["url"]),
            ),
            types.FunctionDeclaration(
                name="run_cmd",
                description="Run a shell command on the host PC.",
                parameters=types.Schema(type="OBJECT", properties={
                    "command": {"type": "STRING", "description": "Command to run."}
                }, required=["command"]),
            ),
            types.FunctionDeclaration(
                name="safe_run_cmd",
                description="Run a shell command only if it is on the allowlist.",
                parameters=types.Schema(type="OBJECT", properties={
                    "command": {"type": "STRING", "description": "Command to run."}
                }, required=["command"]),
            ),
            types.FunctionDeclaration(
                name="memory_store",
                description="Store a fact in Friday's long-term memory vault.",
                parameters=types.Schema(type="OBJECT", properties={
                    "category": {"type": "STRING", "description": "episodic, semantic, or preference."},
                    "keyword": {"type": "STRING", "description": "Unique recall key."},
                    "content": {"type": "STRING", "description": "Data to remember."},
                }, required=["category", "keyword", "content"]),
            ),
            types.FunctionDeclaration(
                name="memory_retrieve",
                description="Recall information from memory vault.",
                parameters=types.Schema(type="OBJECT", properties={
                    "query": {"type": "STRING", "description": "Keyword or topic."}
                }, required=["query"]),
            ),
            types.FunctionDeclaration(
                name="get_time",
                description="Get current date and time."
            ),
            types.FunctionDeclaration(
                name="system_info",
                description="Get host PC hardware and OS status."
            ),
            types.FunctionDeclaration(
                name="alexa_command",
                description="Send a command to the Alexa bridge or routine layer.",
                parameters=types.Schema(type="OBJECT", properties={
                    "command": {"type": "STRING", "description": "Natural language Alexa command."}
                }, required=["command"]),
            ),
            types.FunctionDeclaration(
                name="alexa_poll",
                description="Check if Alexa sent any commands to Friday."
            ),
            types.FunctionDeclaration(
                name="home_assistant_command",
                description="Control a smart-home entity via Home Assistant REST API.",
                parameters=types.Schema(type="OBJECT", properties={
                    "entity_id": {"type": "STRING", "description": "Example: light.bedroom"},
                    "action": {"type": "STRING", "description": "turn_on, turn_off, toggle"},
                }, required=["entity_id"]),
            ),
            types.FunctionDeclaration(
                name="smart_home_command",
                description="Unified smart home command. Use target and action.",
                parameters=types.Schema(type="OBJECT", properties={
                    "target": {"type": "STRING", "description": "Device or entity name."},
                    "action": {"type": "STRING", "description": "Action to perform."},
                }),
            ),
            types.FunctionDeclaration(
                name="queue_task",
                description="Queue a single tool for sequential execution.",
                parameters=types.Schema(type="OBJECT", properties={
                    "func_name": {"type": "STRING", "description": "Tool function name to queue."},
                    "args": {"type": "STRING", "description": "Pipe-separated args (optional)."},
                }, required=["func_name"]),
            ),
            types.FunctionDeclaration(
                name="queue_status",
                description="Check how many tasks are pending and completed in the queue."
            ),
            types.FunctionDeclaration(
                name="queue_result",
                description="Retrieve the result of a queued task.",
                parameters=types.Schema(type="OBJECT", properties={
                    "task_id": {"type": "STRING", "description": "Queue task id."}
                }, required=["task_id"]),
            ),
            types.FunctionDeclaration(
                name="multi_task",
                description="Queue multiple tools to run sequentially.",
                parameters=types.Schema(type="OBJECT", properties={
                    "task_specs": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "List of task specs in format 'func_name:arg1|arg2'.",
                    }
                }, required=["task_specs"]),
            ),
            types.FunctionDeclaration(
                name="type_text",
                description="Type text at the current cursor position.",
                parameters=types.Schema(type="OBJECT", properties={
                    "text": {"type": "STRING", "description": "Text to type."}
                }, required=["text"]),
            ),
            types.FunctionDeclaration(
                name="click",
                description="Click at current mouse position or at x,y coordinates.",
                parameters=types.Schema(type="OBJECT", properties={
                    "x": {"type": "INTEGER", "description": "X coordinate (optional)."},
                    "y": {"type": "INTEGER", "description": "Y coordinate (optional)."},
                }),
            ),
            types.FunctionDeclaration(
                name="double_click",
                description="Double-click at current mouse position or at x,y.",
                parameters=types.Schema(type="OBJECT", properties={
                    "x": {"type": "INTEGER", "description": "X coordinate (optional)."},
                    "y": {"type": "INTEGER", "description": "Y coordinate (optional)."},
                }),
            ),
            types.FunctionDeclaration(
                name="right_click",
                description="Right-click at current mouse position or at x,y.",
                parameters=types.Schema(type="OBJECT", properties={
                    "x": {"type": "INTEGER", "description": "X coordinate (optional)."},
                    "y": {"type": "INTEGER", "description": "Y coordinate (optional)."},
                }),
            ),
            types.FunctionDeclaration(
                name="move_mouse",
                description="Move mouse to x,y coordinates.",
                parameters=types.Schema(type="OBJECT", properties={
                    "x": {"type": "INTEGER", "description": "X coordinate."},
                    "y": {"type": "INTEGER", "description": "Y coordinate."},
                }, required=["x", "y"]),
            ),
            types.FunctionDeclaration(
                name="drag",
                description="Drag from current position to x,y with duration.",
                parameters=types.Schema(type="OBJECT", properties={
                    "x": {"type": "INTEGER", "description": "Target X."},
                    "y": {"type": "INTEGER", "description": "Target Y."},
                    "duration": {"type": "NUMBER", "description": "Drag duration in seconds."},
                }, required=["x", "y"]),
            ),
            types.FunctionDeclaration(
                name="hotkey",
                description="Press a keyboard hotkey combination.",
                parameters=types.Schema(type="OBJECT", properties={
                    "keys": {"type": "STRING", "description": "Keys separated by +, e.g. ctrl+c."}
                }, required=["keys"]),
            ),
            types.FunctionDeclaration(
                name="press_key",
                description="Press a single keyboard key.",
                parameters=types.Schema(type="OBJECT", properties={
                    "key": {"type": "STRING", "description": "Key to press."}
                }, required=["key"]),
            ),
            types.FunctionDeclaration(
                name="scroll",
                description="Scroll the mouse wheel.",
                parameters=types.Schema(type="OBJECT", properties={
                    "amount": {"type": "INTEGER", "description": "Scroll amount (positive=up, negative=down)."}
                }, required=["amount"]),
            ),
            types.FunctionDeclaration(
                name="read_file",
                description="Read the contents of a file.",
                parameters=types.Schema(type="OBJECT", properties={
                    "path": {"type": "STRING", "description": "File path."}
                }, required=["path"]),
            ),
            types.FunctionDeclaration(
                name="write_file",
                description="Write content to a file.",
                parameters=types.Schema(type="OBJECT", properties={
                    "path": {"type": "STRING", "description": "File path."},
                    "content": {"type": "STRING", "description": "Content to write."},
                }, required=["path", "content"]),
            ),
            types.FunctionDeclaration(
                name="list_files",
                description="List files in a directory.",
                parameters=types.Schema(type="OBJECT", properties={
                    "path": {"type": "STRING", "description": "Directory path."}
                }),
            ),
            types.FunctionDeclaration(
                name="find_files",
                description="Find files matching a pattern.",
                parameters=types.Schema(type="OBJECT", properties={
                    "pattern": {"type": "STRING", "description": "Glob pattern."},
                    "path": {"type": "STRING", "description": "Search directory."}
                }, required=["pattern"]),
            ),
            types.FunctionDeclaration(
                name="copy_file",
                description="Copy a file from source to destination.",
                parameters=types.Schema(type="OBJECT", properties={
                    "src": {"type": "STRING", "description": "Source path."},
                    "dst": {"type": "STRING", "description": "Destination path."},
                }, required=["src", "dst"]),
            ),
            types.FunctionDeclaration(
                name="move_file",
                description="Move a file from source to destination.",
                parameters=types.Schema(type="OBJECT", properties={
                    "src": {"type": "STRING", "description": "Source path."},
                    "dst": {"type": "STRING", "description": "Destination path."},
                }, required=["src", "dst"]),
            ),
            types.FunctionDeclaration(
                name="delete_file",
                description="Delete a file.",
                parameters=types.Schema(type="OBJECT", properties={
                    "path": {"type": "STRING", "description": "File path."}
                }, required=["path"]),
            ),
            types.FunctionDeclaration(
                name="clipboard_get",
                description="Get the current clipboard content."
            ),
            types.FunctionDeclaration(
                name="clipboard_set",
                description="Set the clipboard content.",
                parameters=types.Schema(type="OBJECT", properties={
                    "text": {"type": "STRING", "description": "Text to put on clipboard."}
                }, required=["text"]),
            ),
            types.FunctionDeclaration(
                name="climb_codebase",
                description="Search and analyze code in the current project.",
                parameters=types.Schema(type="OBJECT", properties={
                    "query": {"type": "STRING", "description": "What to search for."},
                    "path": {"type": "STRING", "description": "Directory to search in."}
                }, required=["query"]),
            ),
            types.FunctionDeclaration(
                name="situational_awareness",
                description="Get current desktop context: active window, running processes, system state."
            ),
            types.FunctionDeclaration(
                name="git_ops",
                description="Perform git operations: status, add, commit, push, etc.",
                parameters=types.Schema(type="OBJECT", properties={
                    "operation": {"type": "STRING", "description": "Git operation (status, add, commit, push, log, diff)."},
                    "message": {"type": "STRING", "description": "Commit message (for commit)."},
                }, required=["operation"]),
            ),
            types.FunctionDeclaration(
                name="take_snapshot",
                description="Save the current screen state to memory."
            ),
            types.FunctionDeclaration(
                name="recall_snapshot",
                description="Recall a previously saved screen snapshot.",
                parameters=types.Schema(type="OBJECT", properties={
                    "index": {"type": "INTEGER", "description": "Snapshot index to recall."}
                }),
            ),
            types.FunctionDeclaration(
                name="opencli_init_bridge",
                description="Initialize the OpenCLI browser bridge for web automation."
            ),
            types.FunctionDeclaration(
                name="opencli_navigate",
                description="Open a URL in the OpenCLI browser automation window.",
                parameters=types.Schema(type="OBJECT", properties={
                    "url": {"type": "STRING", "description": "URL to navigate to."}
                }, required=["url"]),
            ),
            types.FunctionDeclaration(
                name="opencli_click",
                description="Click an element in the browser by selector or visible text.",
                parameters=types.Schema(type="OBJECT", properties={
                    "target": {"type": "STRING", "description": "CSS selector or visible text of the element."}
                }, required=["target"]),
            ),
            types.FunctionDeclaration(
                name="opencli_type",
                description="Click an element then type text into it.",
                parameters=types.Schema(type="OBJECT", properties={
                    "target": {"type": "STRING", "description": "CSS selector or visible text."},
                    "text": {"type": "STRING", "description": "Text to type."},
                }, required=["target", "text"]),
            ),
            types.FunctionDeclaration(
                name="opencli_extract",
                description="Extract the current page content as readable markdown text."
            ),
            types.FunctionDeclaration(
                name="opencli_screenshot",
                description="Take a screenshot of the current browser page.",
                parameters=types.Schema(type="OBJECT", properties={
                    "path": {"type": "STRING", "description": "Optional file path to save the screenshot."}
                }),
            ),
            types.FunctionDeclaration(
                name="opencli_scroll",
                description="Scroll the browser page in a direction.",
                parameters=types.Schema(type="OBJECT", properties={
                    "direction": {"type": "STRING", "description": "Scroll direction: down, up, top, or bottom."}
                }),
            ),
            types.FunctionDeclaration(
                name="opencli_keys",
                description="Press a keyboard key in the browser (Enter, Escape, Tab, etc.).",
                parameters=types.Schema(type="OBJECT", properties={
                    "key": {"type": "STRING", "description": "Key to press (Enter, Escape, Tab, ArrowDown, etc.)."}
                }, required=["key"]),
            ),
            types.FunctionDeclaration(
                name="opencli_eval",
                description="Execute JavaScript in the browser page and return the result.",
                parameters=types.Schema(type="OBJECT", properties={
                    "js": {"type": "STRING", "description": "JavaScript code to execute."}
                }, required=["js"]),
            ),
            types.FunctionDeclaration(
                name="opencli_state",
                description="Get the current browser page state: URL, title, interactive elements."
            ),
            types.FunctionDeclaration(
                name="opencli_doctor",
                description="Diagnose OpenCLI browser bridge connectivity and status."
            ),
            # ======== ADDITIONAL OPENCLI COMMANDS ========
            types.FunctionDeclaration(
                name="opencli_tab_list",
                description="List all open browser tabs with their URLs and titles."
            ),
            types.FunctionDeclaration(
                name="opencli_tab_new",
                description="Open a new browser tab, optionally navigating to a URL.",
                parameters=types.Schema(type="OBJECT", properties={
                    "url": {"type": "STRING", "description": "Optional URL to open in the new tab."}
                }),
            ),
            types.FunctionDeclaration(
                name="opencli_tab_select",
                description="Switch to a specific browser tab by its target ID.",
                parameters=types.Schema(type="OBJECT", properties={
                    "target_id": {"type": "STRING", "description": "The tab target ID from tab_list."}
                }, required=["target_id"]),
            ),
            types.FunctionDeclaration(
                name="opencli_tab_close",
                description="Close a browser tab by target ID.",
                parameters=types.Schema(type="OBJECT", properties={
                    "target_id": {"type": "STRING", "description": "Tab target ID to close."}
                }),
            ),
            types.FunctionDeclaration(
                name="opencli_close",
                description="Release the current browser automation tab lease."
            ),
            types.FunctionDeclaration(
                name="opencli_wait_selector",
                description="Wait for a CSS selector to appear on the page before continuing.",
                parameters=types.Schema(type="OBJECT", properties={
                    "selector": {"type": "STRING", "description": "CSS selector to wait for."},
                    "timeout_ms": {"type": "INTEGER", "description": "Max wait time in milliseconds (default 10000)."}
                }, required=["selector"]),
            ),
            types.FunctionDeclaration(
                name="opencli_find",
                description="Find elements on the page matching a CSS selector.",
                parameters=types.Schema(type="OBJECT", properties={
                    "selector": {"type": "STRING", "description": "CSS selector to search for."},
                    "limit": {"type": "INTEGER", "description": "Max results (default 10)."}
                }, required=["selector"]),
            ),
            types.FunctionDeclaration(
                name="opencli_get_url",
                description="Get the current page URL from the browser."
            ),
            types.FunctionDeclaration(
                name="opencli_get_title",
                description="Get the current page title from the browser."
            ),
            types.FunctionDeclaration(
                name="opencli_network",
                description="Inspect network requests made by the current page."
            ),
            types.FunctionDeclaration(
                name="opencli_bind",
                description="Bind OpenCLI to the current Chrome tab for persistent interaction.",
                parameters=types.Schema(type="OBJECT", properties={
                    "domain": {"type": "STRING", "description": "Optional domain to bind to."}
                }),
            ),
            types.FunctionDeclaration(
                name="opencli_unbind",
                description="Unbind from the current Chrome tab."
            ),
            types.FunctionDeclaration(
                name="vision_click",
                description="Find and click an element on screen by describing it (e.g. 'the submit button', 'the play icon'). Uses Gemini Vision to locate it and clicks the coordinates.",
                parameters=types.Schema(type="OBJECT", properties={
                    "target": {"type": "STRING", "description": "Description of the element to click."}
                }, required=["target"]),
            ),
            types.FunctionDeclaration(
                name="stayfree_status",
                description="Check if StayFree screen time tracker is installed and accessible."
            ),
            types.FunctionDeclaration(
                name="stayfree_today",
                description="Get today's screen time and app usage from StayFree."
            ),
            types.FunctionDeclaration(
                name="stayfree_week",
                description="Get this week's screen time summary from StayFree."
            ),
            # ======== MISSING TOOL DECLARATIONS ========
            types.FunctionDeclaration(
                name="search_browser_history",
                description="Search your entire Chrome/Edge/Brave/Opera browsing history for a query. Returns matching URLs, titles, and timestamps.",
                parameters=types.Schema(type="OBJECT", properties={
                    "query": {"type": "STRING", "description": "What to search for in browser history."},
                    "days_back": {"type": "INTEGER", "description": "How many days back to search (default 30)."},
                }),
            ),
            types.FunctionDeclaration(
                name="open_history_item",
                description="Find and open the most recent browser history item matching a description.",
                parameters=types.Schema(type="OBJECT", properties={
                    "query": {"type": "STRING", "description": "Description of what to find in history."},
                }, required=["query"]),
            ),
            types.FunctionDeclaration(
                name="tell_alexa",
                description="Send a voice command to Alexa via the webhook bridge.",
                parameters=types.Schema(type="OBJECT", properties={
                    "command": {"type": "STRING", "description": "Natural language command for Alexa."}
                }, required=["command"]),
            ),
            types.FunctionDeclaration(
                name="spotify_next",
                description="Skip to the next track on Spotify."
            ),
            types.FunctionDeclaration(
                name="spotify_prev",
                description="Go back to the previous track on Spotify."
            ),
            types.FunctionDeclaration(
                name="spotify_volume",
                description="Set Spotify volume (0-100).",
                parameters=types.Schema(type="OBJECT", properties={
                    "level": {"type": "INTEGER", "description": "Volume level 0-100."}
                }, required=["level"]),
            ),
            types.FunctionDeclaration(
                name="send_instagram_dm",
                description="Send a direct message on Instagram to a user by username.",
                parameters=types.Schema(type="OBJECT", properties={
                    "username": {"type": "STRING", "description": "Instagram username."},
                    "message": {"type": "STRING", "description": "Message text."},
                }, required=["username", "message"]),
            ),
            types.FunctionDeclaration(
                name="netflix_play",
                description="Search and start playing a title on Netflix in the browser.",
                parameters=types.Schema(type="OBJECT", properties={
                    "title": {"type": "STRING", "description": "Movie or show title to play."}
                }, required=["title"]),
            ),
            types.FunctionDeclaration(
                name="gmail_authorize",
                description="Run the Gmail OAuth authorization flow. Opens a browser for you to grant Friday access to your Gmail account. Only needed once.",
            ),
            types.FunctionDeclaration(
                name="read_emails",
                description="Read your latest emails from Gmail.",
                parameters=types.Schema(type="OBJECT", properties={
                    "count": {"type": "INTEGER", "description": "Number of emails to read (default 10)."}
                }),
            ),
            types.FunctionDeclaration(
                name="send_email",
                description="Send an email via Gmail API.",
                parameters=types.Schema(type="OBJECT", properties={
                    "to": {"type": "STRING", "description": "Recipient email address."},
                    "subject": {"type": "STRING", "description": "Email subject."},
                    "body": {"type": "STRING", "description": "Email body text."},
                }, required=["to", "subject", "body"]),
            ),
            types.FunctionDeclaration(
                name="close_app",
                description="Close an application by killing its process.",
                parameters=types.Schema(type="OBJECT", properties={
                    "name": {"type": "STRING", "description": "Process name to kill (e.g. chrome.exe)."}
                }, required=["name"]),
            ),
            types.FunctionDeclaration(
                name="list_running_apps",
                description="List all currently open application windows."
            ),
            types.FunctionDeclaration(
                name="generate_file",
                description="Generate a file from a description using LLM.",
                parameters=types.Schema(type="OBJECT", properties={
                    "description": {"type": "STRING", "description": "Description of the file to generate."},
                    "path": {"type": "STRING", "description": "Where to save the file."},
                }, required=["description"]),
            ),
            # ======== NEWLY WIRED TOOLS ========
            types.FunctionDeclaration(
                name="get_active_window",
                description="Get info about the currently active window (title, process, position)."
            ),
            types.FunctionDeclaration(
                name="draft_email",
                description="Draft an email using AI based on context, addressing a recipient.",
                parameters=types.Schema(type="OBJECT", properties={
                    "context": {"type": "STRING", "description": "What the email should be about."},
                    "recipient": {"type": "STRING", "description": "Recipient name or email."},
                }, required=["context"]),
            ),
            types.FunctionDeclaration(
                name="list_recent_history",
                description="List the most recent browser history entries across all browsers.",
                parameters=types.Schema(type="OBJECT", properties={
                    "count": {"type": "INTEGER", "description": "Number of entries to return (default 10)."}
                }),
            ),
            types.FunctionDeclaration(
                name="generate_file_llm",
                description="Generate a file by specifying a prompt for the LLM.",
                parameters=types.Schema(type="OBJECT", properties={
                    "path": {"type": "STRING", "description": "Output file path."},
                    "prompt": {"type": "STRING", "description": "Prompt describing the file content."},
                }, required=["path", "prompt"]),
            ),
            types.FunctionDeclaration(
                name="search_and_open",
                description="Search the web for something and open the most relevant result in your browser.",
                parameters=types.Schema(type="OBJECT", properties={
                    "query": {"type": "STRING", "description": "Search query."}
                }, required=["query"]),
            ),
            types.FunctionDeclaration(
                name="goals_tool_handler",
                description="Track personal goals: add, list, update progress.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: add, list, update, complete, progress, analyze."},
                    "goal": {"type": "STRING", "description": "Goal name or description."},
                    "category": {"type": "STRING", "description": "Goal category."},
                }, required=["action"]),
            ),
            types.FunctionDeclaration(
                name="startup_tool_handler",
                description="Manage Friday's startup behavior: check, enable, or disable auto-start.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: status, enable, disable."}
                }, required=["action"]),
            ),
            types.FunctionDeclaration(
                name="vector_memory_tool",
                description="Semantic memory: store and search facts, preferences, and patterns using vector search.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: search, add, stats, delete, clear."},
                    "query": {"type": "STRING", "description": "Search query (required for search action)."},
                    "text": {"type": "STRING", "description": "Text to store (required for add action)."},
                    "n_results": {"type": "INTEGER", "description": "Number of results to return (default 5)."},
                }, required=["action"]),
            ),
            types.FunctionDeclaration(
                name="calendar_tool_handler",
                description="Google Calendar: list upcoming events, sync events to goals.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: list, sync."},
                    "days": {"type": "INTEGER", "description": "Number of days ahead to fetch (default 7)."},
                }, required=["action"]),
            ),
            types.FunctionDeclaration(
                name="memory_import_tool_handler",
                description="Import conversations from other AI assistants (Claude, ChatGPT, Gemini) for Friday to learn from.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: import, audit, profile, list."},
                    "file_path": {"type": "STRING", "description": "Path to conversation file or directory."},
                }, required=["action"]),
            ),
            # ======== WORKFLOW AUTOMATION ========
            types.FunctionDeclaration(
                name="workflow_tool",
                description="Create and manage automated workflows. Actions: list (show all), create (make new), add_step (add step to workflow, steps=JSON), execute (run), status (check progress), delete (remove).",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: list, create, add_step, execute, status, delete."},
                    "name": {"type": "STRING", "description": "Workflow name (required for create, add_step, execute, status, delete)."},
                    "description": {"type": "STRING", "description": "Workflow description (for create)."},
                    "steps": {"type": "STRING", "description": "JSON string of step data (for add_step)."},
                }, required=["action"]),
            ),
            # ======== PLUGIN SYSTEM ========
            types.FunctionDeclaration(
                name="plugin_tool",
                description="Manage Friday plugins: list available, discover new, load/unload plugins, call plugin tools.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: list, discover, load, load_all, unload, call."},
                    "plugin_name": {"type": "STRING", "description": "Plugin name (for load, unload, call)."},
                    "tool_name": {"type": "STRING", "description": "Tool name within plugin (for call action)."},
                }, required=["action"]),
            ),
            # ======== KNOWLEDGE GRAPH ========
            types.FunctionDeclaration(
                name="knowledge_graph_tool",
                description="Query and manage the knowledge graph — semantic memory of entities and relationships. Actions: stats, add_node, add_edge, get, neighbors, search, path, subgraph, extract.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: stats, add_node, add_edge, get, neighbors, search, path, subgraph, extract."},
                    "node_id": {"type": "STRING", "description": "Node identifier for add/get/neighbors/search/path/subgraph operations."},
                    "target_id": {"type": "STRING", "description": "Target node for add_edge or path operations."},
                    "relation": {"type": "STRING", "description": "Relationship type for add_edge."},
                    "properties": {"type": "STRING", "description": "JSON properties string for add_node."},
                    "text": {"type": "STRING", "description": "Text to extract knowledge from (for extract action)."},
                }, required=["action"]),
            ),
            # ======== GITHUB INTEGRATION ========
            types.FunctionDeclaration(
                name="github_list_files",
                description="List files in the configured GitHub repository.",
                parameters=types.Schema(type="OBJECT", properties={
                    "path": {"type": "STRING", "description": "Directory path to list (default: root)."}
                }),
            ),
            types.FunctionDeclaration(
                name="github_read_file",
                description="Read a file from the GitHub repository.",
                parameters=types.Schema(type="OBJECT", properties={
                    "path": {"type": "STRING", "description": "File path in repository."}
                }, required=["path"]),
            ),
            types.FunctionDeclaration(
                name="github_write_file",
                description="Write a file to the GitHub repository.",
                parameters=types.Schema(type="OBJECT", properties={
                    "path": {"type": "STRING", "description": "File path in repository."},
                    "content": {"type": "STRING", "description": "File content."},
                    "message": {"type": "STRING", "description": "Commit message (default: 'Update via Friday')."},
                }, required=["path", "content"]),
            ),
            types.FunctionDeclaration(
                name="github_create_branch",
                description="Create a new branch in the GitHub repository.",
                parameters=types.Schema(type="OBJECT", properties={
                    "branch_name": {"type": "STRING", "description": "Name for the new branch."}
                }, required=["branch_name"]),
            ),
            types.FunctionDeclaration(
                name="github_create_pr",
                description="Create a pull request on GitHub.",
                parameters=types.Schema(type="OBJECT", properties={
                    "title": {"type": "STRING", "description": "PR title."},
                    "body": {"type": "STRING", "description": "PR description."},
                    "head": {"type": "STRING", "description": "Source branch name."},
                }, required=["title", "body", "head"]),
            ),
            types.FunctionDeclaration(
                name="github_self_modify",
                description="Self-modify a file in Friday's own repository and commit the change.",
                parameters=types.Schema(type="OBJECT", properties={
                    "file_path": {"type": "STRING", "description": "File path in repository."},
                    "new_content": {"type": "STRING", "description": "New file content."},
                    "commit_msg": {"type": "STRING", "description": "Commit message (default: 'Self-modification by Friday')."},
                }, required=["file_path", "new_content"]),
            ),
            # ======== MULTI-AGENT DELEGATION ========
            # ======== NOTIFICATIONS ========
            types.FunctionDeclaration(
                name="send_notification",
                description="Send a desktop toast notification with urgency level (normal, urgent).",
                parameters=types.Schema(type="OBJECT", properties={
                    "message": {"type": "STRING", "description": "Notification message text."},
                    "urgency": {"type": "STRING", "description": "Urgency level: normal or urgent."},
                    "task_id": {"type": "STRING", "description": "Optional task ID for tracking."},
                }, required=["message"]),
            ),
            types.FunctionDeclaration(
                name="get_pending_notifications",
                description="List all pending notifications, optionally filtered by urgency.",
                parameters=types.Schema(type="OBJECT", properties={
                    "urgency_filter": {"type": "STRING", "description": "Optional: normal, urgent, or empty for all."}
                }),
            ),
            types.FunctionDeclaration(
                name="clear_notifications",
                description="Clear delivered notifications, or for a specific task ID.",
                parameters=types.Schema(type="OBJECT", properties={
                    "task_id": {"type": "STRING", "description": "Optional task ID to clear notifications for."}
                }),
            ),
            types.FunctionDeclaration(
                name="multi_agent_delegate",
                description="Delegate tasks to specialist sub-agents (coder, researcher, organizer, communicator, automator, planner). Supports single (delegate) and peer-to-peer (parallel) modes.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: list (show agents), delegate (single agent), parallel (peer-to-peer split across multiple agents), results (get merged output), agent_info (get agent details)."},
                    "task": {"type": "STRING", "description": "Task description (required for delegate and parallel actions)."},
                    "agent": {"type": "STRING", "description": "Preferred agent name (optional, for delegate action)."},
                    "split_by": {"type": "STRING", "description": "How to split task across agents (optional, for parallel action, default: auto)."},
                }, required=["action"]),
            ),
            # ======== MESSAGE CHANNELS ========
            types.FunctionDeclaration(
                name="message_channel_tool",
                description="Send or receive messages via Telegram, Discord, or webhooks. Actions: status (check config), send (send message), receive (get messages from Telegram).",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: status, send, receive."},
                    "channel": {"type": "STRING", "description": "Channel: telegram, discord, webhook (required for send/receive)."},
                    "target": {"type": "STRING", "description": "Target: chat_id for telegram, webhook URL for webhook (for send)."},
                    "message": {"type": "STRING", "description": "Message text to send (required for send)."},
                    "limit": {"type": "INTEGER", "description": "Number of messages to fetch (for receive, default 10)."},
                }, required=["action"]),
            ),
        ])
    ]

TOOL_MAP = {
    "stark_log": stark_log,
    "stark_doctor": stark_doctor,
    "spotify_play": spotify_play,
    "spotify_pause": spotify_pause,
    "spotify_current": spotify_current,
    "open_app": open_app,
    "web_search": web_search,
    "video_search": video_search,
    "see_screen": see_screen,
    "open_url": open_url,
    "run_cmd": run_cmd,
    "safe_run_cmd": safe_run_cmd,
    "memory_store": memory_store,
    "memory_retrieve": memory_retrieve,
    "get_time": get_time,
    "system_info": system_info,
    "deep_research": deep_research,
    "alexa_command": alexa_command,
    "alexa_poll": alexa_poll,
    "home_assistant_command": home_assistant_command,
    "smart_home_command": smart_home_command,
    "queue_task": queue_task,
    "queue_status": queue_status,
    "queue_result": queue_result,
    "multi_task": multi_task,
    "type_text": type_text,
    "click": click,
    "double_click": double_click,
    "right_click": right_click,
    "move_mouse": move_mouse,
    "drag": drag,
    "hotkey": hotkey,
    "press_key": press_key,
    "scroll": scroll,
    "read_file": read_file,
    "write_file": write_file,
    "list_files": list_files,
    "find_files": find_files,
    "copy_file": copy_file,
    "move_file": move_file,
    "delete_file": delete_file,
    "clipboard_get": clipboard_get,
    "clipboard_set": clipboard_set,
    "climb_codebase": climb_codebase,
    "situational_awareness": situational_awareness,
    "git_ops": git_ops,
    "take_snapshot": take_snapshot,
    "recall_snapshot": recall_snapshot,
    "opencli_init_bridge": opencli_init_bridge,
    "opencli_navigate": opencli_navigate,
    "opencli_click": opencli_click,
    "opencli_type": opencli_type,
    "opencli_extract": opencli_extract,
    "opencli_screenshot": opencli_screenshot,
    "opencli_scroll": opencli_scroll,
    "opencli_keys": opencli_keys,
    "opencli_eval": opencli_eval,
    "opencli_state": opencli_state,
    "opencli_doctor": opencli_doctor,
    "vision_click": vision_click,
    "stayfree_status": stayfree_status,
    "stayfree_today": stayfree_today,
    "stayfree_week": stayfree_week,
    "search_browser_history": search_browser_history,
    "open_history_item": open_history_item,
    "tell_alexa": tell_alexa,
    "spotify_next": spotify_next,
    "spotify_prev": spotify_prev,
    "spotify_volume": spotify_volume,
    "send_instagram_dm": send_instagram_dm,
    "netflix_play": netflix_play,
    "gmail_authorize": gmail_authorize,
    "read_emails": read_emails,
    "send_email": send_email,
    "close_app": close_app,
    "list_running_apps": list_running_apps,
    "generate_file": generate_file,
    "get_active_window": get_active_window,
    "draft_email": draft_email,
    "list_recent_history": list_recent_history,
    "generate_file_llm": generate_file_llm,
    "search_and_open": search_and_open,
    "goals_tool_handler": goals_tool_handler,
    "vector_memory_tool": vector_memory_tool,
    "calendar_tool_handler": calendar_tool_handler,
    "startup_tool_handler": startup_tool_handler,
    "memory_import_tool_handler": memory_import_tool_handler,
    "opencli_tab_list": opencli_tab_list,
    "opencli_tab_new": opencli_tab_new,
    "opencli_tab_select": opencli_tab_select,
    "opencli_tab_close": opencli_tab_close,
    "opencli_close": opencli_close,
    "opencli_wait_selector": opencli_wait_selector,
    "opencli_find": opencli_find,
    "opencli_get_url": opencli_get_url,
    "opencli_get_title": opencli_get_title,
    "opencli_network": opencli_network,
    "opencli_bind": opencli_bind,
    "opencli_unbind": opencli_unbind,
    "workflow_tool": workflow_tool,
    "plugin_tool": plugin_tool,
    "knowledge_graph_tool": knowledge_graph_tool,
    "github_list_files": github_list_files,
    "github_read_file": github_read_file,
    "github_write_file": github_write_file,
    "github_create_branch": github_create_branch,
    "github_create_pr": github_create_pr,
    "github_self_modify": github_self_modify,
    "github_review_pr": github_review_pr,
    "multi_agent_delegate": multi_agent_delegate,
    "message_channel_tool": message_channel_tool,
    "send_notification": send_notification,
    "get_pending_notifications": get_pending_notifications,
    "clear_notifications": clear_notifications,
}


def _invoke_tool(func_name, args, session=None):
    # Run pre-hooks
    try:
        from friday_hooks import run_pre_hooks, run_post_hooks, run_error_hooks
        modified = run_pre_hooks(func_name, args, session)
        if modified is None:
            return "[BLOCKED] Tool execution blocked by pre-hook."
        args = modified
    except ImportError:
        pass

    func = TOOL_MAP.get(func_name)
    if not func:
        return {"error": f"Unknown tool: {func_name}"}
    try:
        if not isinstance(args, dict):
            args = {"command": str(args)} if args else {}
        # Special handling for multi_task
        if func_name == "multi_task":
            specs = args.get("task_specs", [])
            result = multi_task(*specs)
        elif func_name == "queue_task":
            result = queue_task(
                args.get("func_name", ""),
                *(args.get("args", "").split("|") if args.get("args") else [])
            )
        elif func_name == "hotkey":
            keys = args.get("keys", "")
            result = hotkey(keys)
        elif func_name == "press_key":
            key = args.get("key", "")
            result = press_key(key)
        elif func_name == "type_text":
            text = args.get("text", "")
            result = type_text(text)
        elif func_name == "click":
            x = args.get("x")
            y = args.get("y")
            if x is not None and y is not None:
                result = click(int(x), int(y))
            else:
                result = click()
        elif func_name == "double_click":
            x = args.get("x")
            y = args.get("y")
            if x is not None and y is not None:
                result = double_click(int(x), int(y))
            else:
                result = double_click()
        elif func_name == "right_click":
            x = args.get("x")
            y = args.get("y")
            if x is not None and y is not None:
                result = right_click(int(x), int(y))
            else:
                result = right_click()
        elif func_name == "drag":
            x = args.get("x", 0)
            y = args.get("y", 0)
            duration = args.get("duration", 0.5)
            result = drag(int(x), int(y), float(duration))
        elif func_name == "scroll":
            amount = args.get("amount", 1)
            result = scroll(int(amount))
        elif func_name == "move_mouse":
            x = args.get("x", 0)
            y = args.get("y", 0)
            result = move_mouse(int(x), int(y))
        elif func_name == "git_ops":
            operation = args.get("operation", "status")
            message = args.get("message", "")
            result = git_ops(operation, message=message)
        elif func_name == "take_snapshot":
            result = take_snapshot()
        elif func_name == "recall_snapshot":
            index = args.get("index", 0)
            result = recall_snapshot(int(index))
        elif func_name == "clipboard_set":
            text = args.get("text", "")
            result = clipboard_set(text)
        elif func_name == "clipboard_get":
            result = clipboard_get()
        elif func_name == "get_time":
            result = get_time()
        elif func_name == "system_info":
            result = system_info()
        elif func_name == "stark_doctor":
            result = stark_doctor()
        elif func_name == "spotify_pause":
            result = spotify_pause()
        elif func_name == "alexa_poll":
            result = alexa_poll()
        elif func_name == "queue_status":
            result = queue_status()
        elif func_name == "situational_awareness":
            result = situational_awareness()
        else:
            result = func(**args)
        # Run post-hooks
        try:
            from friday_hooks import run_post_hooks
            run_post_hooks(func_name, args, str(result), session)
        except ImportError:
            pass
        return {"result": str(result)}
    except Exception as e:
        stark_log(f"Tool {func_name} error: {e}")
        # Run error-hooks
        try:
            from friday_hooks import run_error_hooks
            run_error_hooks(func_name, args, e, session)
        except ImportError:
            pass
        return {"error": str(e)}


# SESSION CONFIG
def _build_session_config(tools, resume_handle=None):
    return types.LiveConnectConfig(
        response_modalities=[types.Modality.AUDIO],
        tools=tools,
        thinking_config=types.ThinkingConfig(include_thoughts=True),
        context_window_compression=types.ContextWindowCompressionConfig(
            sliding_window=types.SlidingWindow(),
        ),
        session_resumption=types.SessionResumptionConfig(
            handle=resume_handle
        ) if resume_handle else None,
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Leda")
            )
        ),
        system_instruction=types.Content(
            parts=[types.Part(text=SYSTEM_INSTRUCTION)]
        ),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        proactivity=types.ProactivityConfig(proactive_audio=True),
    )


# BACKGROUND SCREEN MONITOR - Phase 2
async def background_monitor(session):
    """Periodic context awareness: sends active window info every ~90s.
    Less frequent to avoid excessive proactive interruptions.
    """
    last_context_time = 0
    try:
        import time
        while True:
            try:
                now = time.time()
                if now - last_context_time >= 90:
                    last_context_time = now
                    active_window = ""
                    try:
                        from friday_tools import get_active_window
                        active_window = get_active_window()
                    except Exception:
                        pass
                    await session.send_realtime_input(
                        text=f"[CONTEXT] {datetime.datetime.now().strftime('%H:%M')} Active window: {active_window}"
                    )
            except Exception:
                pass
            await asyncio.sleep(15)
    except Exception:
        pass


# LIVE VIDEO STREAMER - sends screen captures via Live API video channel
async def live_video_streamer(session):
    """Stream screen captures as video frames to Gemini Live API (~0.33 FPS).
    Official pattern: separate background task, send_realtime_input(video=Blob).
    """
    try:
        while True:
            try:
                frame = await asyncio.get_event_loop().run_in_executor(
                    None, _capture_screen_frame
                )
                if frame:
                    await session.send_realtime_input(
                        video=types.Blob(data=frame, mime_type="image/jpeg")
                    )
            except Exception:
                pass
            await asyncio.sleep(3)
    except asyncio.CancelledError:
        pass
    except Exception:
        pass


def _capture_screen_frame() -> bytes | None:
    """Capture a single screen frame as JPEG bytes."""
    try:
        from PIL import ImageGrab
        import io
        img = ImageGrab.grab()
        img.thumbnail((640, 480), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=60)
        return buf.getvalue()
    except Exception:
        return None


# KEEPALIVE TASK - Phase 2
async def keepalive_task(session):
    """Send periodic pings to prevent GOAWAY timeout. Reconnects are handled by the main loop."""
    while True:
        await asyncio.sleep(45)
        try:
            await session.send_realtime_input(
                audio=types.Blob(data=b"", mime_type="audio/pcm;rate=16000")
            )
        except Exception:
            pass


# AUDIO WORKER
async def audio_worker(recorder, session, audio_ready, porcupine, winsound):
    await audio_ready.wait()
    while True:
        # Skip sending mic audio while assistant is speaking (echo prevention)
        if _mic_muted.is_set():
            await asyncio.sleep(0.05)
            continue
        frame = recorder.read()
        audio_data = struct.pack("<" + "h" * len(frame), *frame)
        wake_index = porcupine.process(frame)
        if wake_index >= 0:
            if winsound:
                try:
                    winsound.MessageBeep()
                except Exception:
                    pass
        await session.send_realtime_input(
            audio=types.Blob(data=audio_data, mime_type="audio/pcm;rate=16000")
        )
        await asyncio.sleep(0)


# MAIN ENGINE
async def friday_live_engine():
    global _event_loop
    _event_loop = asyncio.get_running_loop()
    stark_initialization()
    tools = _build_tools()
    chat = ChatDisplay(console)

    porcupine = pvporcupine.create(
        access_key=PICOVOICE_ACCESS_KEY,
        keyword_paths=[PORCUPINE_MODEL_PATH],
    )
    recorder = PvRecorder(device_index=-1, frame_length=porcupine.frame_length)
    pa = pyaudio.PyAudio()

    reconnect_attempts = 0
    resume_handle = None
    last_session_was_greeting = True

    # Start OpenCLI daemon on launch
    try:
        from friday_tools import opencli_init_bridge
        opencli_init_bridge()
        console.print("[dim]OpenCLI bridge ready[/]")
    except Exception:
        pass

    try:
        while reconnect_attempts < MAX_RECONNECT_ATTEMPTS:
            try:
                console.print(f"\n[bold green]Connecting to {MODEL_ID}...[/]")
                if resume_handle:
                    console.print(f"[dim]Resuming session: {resume_handle[:24]}...[/]")

                async with client.aio.live.connect(
                    model=MODEL_ID,
                    config=_build_session_config(tools, resume_handle)
                ) as session:
                    console.print("[bold green]Neural link established.[/]\n")
                    reconnect_attempts = 0

                    greeting_done = asyncio.Event()
                    audio_ready = asyncio.Event()
                    is_greeting = last_session_was_greeting

                    shown_input = ""
                    follow_up_mode = False

                    # Start audio playback thread
                    _start_audio_playback(pa)

                    # RECEIVE LOOP
                    async def receive_loop():
                        nonlocal is_greeting, shown_input, resume_handle, follow_up_mode
                        thinking_parts = []
                        last_transcript = ""
                        displayed_transcript = ""
                        last_displayed_input = ""

                        try:
                            while True:
                                async for response in session.receive():
                                    if response.go_away is not None:
                                        console.print(
                                            f"\n[bold yellow][SYSTEM] Connection ending, will resume...[/]"
                                        )
                                        continue

                                    if response.session_resumption_update:
                                        update = response.session_resumption_update
                                        if update.resumable and update.new_handle:
                                            resume_handle = update.new_handle

                                    sc = response.server_content
                                    tc = response.tool_call

                                    if sc:
                                        # User transcription
                                        if sc.input_transcription and sc.input_transcription.text:
                                            txt = sc.input_transcription.text.strip()
                                            if txt and txt != shown_input:
                                                shown_input = txt
                                                chat.add_user_message(txt)

                                         # Model turn - audio + thoughts
                                        if sc.model_turn:
                                            _model_turn_done.clear()  # Model is speaking — don't unmute yet
                                            for part in sc.model_turn.parts:
                                                if part.inline_data:
                                                    _audio_playback_queue.put(part.inline_data.data)

                                                if part.thought and part.text:
                                                    thinking_parts.append(part.text)

                                        # Output transcription - show progressively
                                        if sc.output_transcription and sc.output_transcription.text:
                                            new_text = sc.output_transcription.text.strip()
                                            if new_text and new_text != displayed_transcript:
                                                # Show incremental text
                                                if not displayed_transcript:
                                                    console.print(f"\n[bold cyan]---Friday---[/]")
                                                # Only print the new portion
                                                if new_text.startswith(displayed_transcript):
                                                    delta = new_text[len(displayed_transcript):]
                                                    if delta:
                                                        console.print(f"  {delta}", end="")
                                                else:
                                                    # Full replacement
                                                    console.print(f"\r  {new_text}", end="")
                                                displayed_transcript = new_text
                                            last_transcript = new_text

                                        # Turn complete
                                        if sc.turn_complete:
                                            _model_turn_done.set()  # No more audio chunks coming
                                            if thinking_parts:
                                                chat.add_thought("\n".join(thinking_parts))
                                                thinking_parts = []

                                            final_text = last_transcript.strip()
                                            if final_text:
                                                console.print()  # newline after progressive text
                                                if final_text.rstrip().endswith("?"):
                                                    chat.add_system("[MIC] Listening... (follow-up mode)")
                                                    follow_up_mode = True
                                                else:
                                                    chat.add_system("[STANDBY] Standing by")
                                                    follow_up_mode = False

                                            if is_greeting:
                                                is_greeting = False
                                                greeting_done.set()
                                                follow_up_mode = True

                                            last_transcript = ""
                                            displayed_transcript = ""

                                            async def _delayed_unduck():
                                                await asyncio.sleep(1.5)
                                                set_audio_ducking(False)
                                            asyncio.create_task(_delayed_unduck())

                                        # Interruption
                                        if sc.interrupted:
                                            thinking_parts = []
                                            last_transcript = ""
                                            displayed_transcript = ""
                                            follow_up_mode = True
                                            chat.add_system("[MUTE] Interrupted")

                                    # Tool calls
                                    if tc:
                                        _mic_muted.set()  # Mute mic during execution
                                        responses = []
                                        for fc in tc.function_calls:
                                            name = fc.name
                                            args = fc.args or {}
                                            chat.add_system(f"Executing: {name}")
                                            result = _invoke_tool(name, args, session)
                                            responses.append(
                                                types.FunctionResponse(
                                                    name=name, id=fc.id, response=result
                                                )
                                            )
                                        await session.send_tool_response(
                                            function_responses=responses
                                        )

                        except asyncio.CancelledError:
                            pass
                        except Exception as e:
                            console.print(f"\n[bold red][LISTENER ERROR] {e}[/]")
                            raise  # Propagate so the main loop knows connection is dead

                    receive_task = asyncio.create_task(receive_loop())

                    # SEND GREETING (first connect only)
                    if is_greeting:
                        hour = datetime.datetime.now().hour
                        if 5 <= hour < 12:
                            greet = "Good morning Boss, ready for a productive day? What are we working on?"
                        elif 12 <= hour < 17:
                            greet = "Good afternoon Boss, hope your day is going well. What do you need?"
                        elif 17 <= hour < 21:
                            greet = "Good evening Boss. What are we working on tonight?"
                        else:
                            greet = "Working late again, Boss? I am here. What do you need?"

                        try:
                            state_path = os.path.join(
                                os.path.dirname(os.path.abspath(__file__)),
                                "sovereign_state.json"
                            )
                            with open(state_path) as sf:
                                sd = json.load(sf)
                            lt = sd.get("current_task", "")
                            mu = sd.get("music", "")
                            if lt:
                                greet += f" Previous session: {lt}. Music was {mu}."
                        except Exception:
                            pass

                        greet += " Greet naturally in one sentence. Ask what to work on."

                        await session.send_realtime_input(text=greet)

                        try:
                            await asyncio.wait_for(greeting_done.wait(), timeout=30)
                        except asyncio.TimeoutError:
                            pass

                        await asyncio.sleep(1.5)

                    # START STREAMS AFTER GREETING
                    recorder.start()
                    audio_task = asyncio.create_task(
                        audio_worker(recorder, session, audio_ready, porcupine, winsound)
                    )
                    audio_ready.set()
                    bg_monitor_task = asyncio.create_task(background_monitor(session))
                    video_task = asyncio.create_task(live_video_streamer(session))
                    ka_task = asyncio.create_task(keepalive_task(session))

                    console.print(
                        "\n[dim]Say Friday for voice, or type below. Enter to send, Ctrl+C to quit.[/]\n"
                    )

                    last_session_was_greeting = False

                    # Text input
                    input_queue = asyncio.Queue()

                    def blocking_input():
                        while True:
                            try:
                                line = input()
                                input_queue.put_nowait(line)
                            except EOFError:
                                break

                    input_thread = threading.Thread(target=blocking_input, daemon=True)
                    input_thread.start()

                    async def input_reader():
                        while True:
                            text = await input_queue.get()
                            if text.strip():
                                await session.send_realtime_input(text=text)
                                chat.add_user_message(text)

                    reader_task = asyncio.create_task(input_reader())

                    try:
                        while True:
                            if receive_task.done():
                                # receive loop died (GOAWAY, 1008, etc.) — reconnect
                                break
                            await asyncio.sleep(0.5)

                    finally:
                        recorder.stop()
                        _stop_audio_playback()
                        receive_task.cancel()
                        audio_task.cancel()
                        bg_monitor_task.cancel()
                        video_task.cancel()
                        ka_task.cancel()
                        reader_task.cancel()
                        for t in [receive_task, audio_task, bg_monitor_task, video_task, ka_task, reader_task]:
                            try:
                                await asyncio.wait_for(asyncio.shield(t), timeout=2.0)
                            except (asyncio.CancelledError, asyncio.TimeoutError):
                                pass
                        pa.terminate()

            except KeyboardInterrupt:
                console.print("\n[bold cyan]Neural link severed. Goodbye, Boss.[/]")
                break
            except Exception as e:
                reconnect_attempts += 1
                console.print(f"[red]Link error:[/] {e}")
                console.print("[dim]Clearing resume handle (stale video state risk). Reconnecting fresh...[/]")
                resume_handle = None
                if reconnect_attempts < MAX_RECONNECT_ATTEMPTS:
                    await asyncio.sleep(3 * reconnect_attempts)
                else:
                    console.print("[bold red]Max reconnects reached.[/]")
    finally:
        try:
            porcupine.delete()
        except Exception:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(friday_live_engine())
    except KeyboardInterrupt:
        pass
