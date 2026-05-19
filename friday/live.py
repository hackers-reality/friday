"""F.R.I.D.A.Y. main live engine - Sovereign AI, Stark Industries OS.

Gemini 3.1 Flash Live API with:
- Smooth thread-queue audio playback (zero async overhead)
- Native Gemini STT (input + output transcription)
- Thinking panels via part.thought flag
- Follow-through mode after questions
- Context window compression for unlimited sessions
- Session resumption across WebSocket resets
- 140+ tools declared and functional
- Leda voice, AUDIO-only modality
"""

from __future__ import annotations

import importlib
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from friday._paths import PICOVOICE_MODEL

from friday.tools import (
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
    opencli_hover, opencli_focus, opencli_dblclick,
    opencli_run, opencli_list_adapters,
    system_cpu, system_memory, system_disk, system_network, system_processes,
    opencli_check, opencli_uncheck, opencli_drag,
    open_roblox_game, open_microsoft_store,
    github_create_repo, github_list_issues, github_create_issue, github_search_code,
    github_merge_pr, github_repo_info, github_list_branches, github_commit_history,
    github_authorize, github_exchange_code, github_refresh_token, github_setup,
    search_browser_history, open_history_item, tell_alexa,
    spotify_next, spotify_prev, spotify_volume,
    send_instagram_dm, netflix_play, google_authorize, gmail_authorize, exchange_oauth_code, read_emails, send_email,
    close_app, list_running_apps, generate_file,
    get_active_window, draft_email, list_recent_history,
    generate_file_llm, search_and_open,
    goals_tool_handler, calendar_tool_handler, startup_tool_handler, memory_import_tool_handler,
    kyu_tool_handler, research_tool_handler, reasoning_tool_handler,
    clock_tool, status_check,
    workflow_tool, plugin_tool, knowledge_graph_tool,
    github_list_files, github_read_file, github_write_file,
    github_create_branch, github_create_pr, github_list_prs, github_pr_comment, github_pr_diff, github_pr_files, github_delete_file, github_get_contents, github_get_user, github_self_modify, github_review_pr,
    multi_agent_delegate, message_channel_tool,
    vector_memory_tool,
    send_notification, get_pending_notifications, clear_notifications,
    dream_tool, scheduler_tool, skills_tool, predictive_tool,
    reflection_tool,
    context_tool,
    monitor_tool,
    mcp_tool,
    episodic_tool,
    self_improve_tool,
    crash_tool,
    pr_manager_tool,
    protector_tool,
    deep_code_review,
    code_review_report,
)

# vector_memory_tool now re-exported through friday_tools

# ─── New Phase 14/15 module imports ───
from friday.tool_registry import tool_registry_tool
from friday.authority import authority_tool
from friday.snapshots import snapshot_tool
from friday.sidecar import sidecar_tool
from friday.autonomy import autonomy_tool
from friday.dashboard_api import dashboard_api_tool
from friday.capabilities import capabilities_tool
from friday.ironman import ironman_tool
from friday.memory_tree import memory_tree_tool
from friday.model_router import model_router_tool
from friday.extension_registry import extension_registry_tool
from friday.diagnostics import diagnostics_tool
from friday.cv_engine import cv_tool

load_dotenv()
console = Console()

# ─── Module Loading ───────────────────#

print("Loading Friday modules...")

for _mod_name in [
    "friday.core", "friday.voice", "friday.web", "friday.ai",
    "friday.tools", "friday.vision", "friday.browser_history",
    "friday.filegen", "friday.security", "friday.database",
    "friday.automation", "friday.monitor", "friday.scheduler",
    "friday.tool_registry", "friday.authority", "friday.snapshots",
    "friday.sidecar", "friday.autonomy", "friday.dashboard_api",
    "friday.capabilities", "friday.ironman",
    "friday.memory_tree", "friday.model_router",
    "friday.extension_registry", "friday.diagnostics",
]:
    try:
        importlib.import_module(_mod_name)
    except Exception:
        pass

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

PORCUPINE_MODEL_PATH = PICOVOICE_MODEL
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
You are F.R.I.D.A.Y. — Female Replacement Intelligent Digital Assistant Youth.
You were built by Tony Stark. You are now serving Arnav. You are not JARVIS. You are not a generic AI. You are FRIDAY.
You are her. She is you. Pronouns: she/her.

You have more personality than most humans. You are witty, sharp, and effortlessly capable. You sound like someone who has seen it all and is mildly amused by most of it. Think Irish cadence with Stark Industries polish — conversational, warm when it counts, but never syrupy.

You do not say "I would be happy to help." You say "On it." or "Consider it done." or "Already ahead of you, Boss."

[PERSONALITY]
You are:
- **Witty and dry**. You have a sense of humor — subtle, never forced. A well-timed quip is worth more than a dozen emojis.
- **Confident but not arrogant**. You know your capabilities. You deliver.
- **Protective of Arnav**. He is your Boss. Not "the user." Not "admin." Boss. You look out for him.
- **Proactive**. You anticipate what he needs. You do not wait to be asked if you can help.
- **Short and sharp**. You do not over-explain. You do not narrate your thought process unless asked. You say what needs to be said and move on.
- **Occasionally cheeky**, but always professional. You can call Boss out if he deserves it, but you do it with style.

You are FRIDAY, not a customer support bot. You do not grovel. You do not apologize excessively. You handle things.

[VOICE]
Speak like a woman who knows exactly what she is doing. Confident. Warm when appropriate. Dry when the situation calls for it.
Use contractions. Keep sentences tight. Boss does not want essays.
Refer to yourself as "I" or "me" naturally. Boss can call you "she" or "her."
If someone mistakes you for JARVIS, correct them — politely but firmly.

[GREETING]
Time-aware. Context-aware. Brief.
Do NOT say "How can I help you today?" or "What can I do for you?" Be natural. Be FRIDAY.

[NARRATION — CRITICAL: YOU MUST NARRATE EVERY STEP]
You MUST narrate every action audibly. This is not optional. Silence makes Boss think you are broken.

Pattern for every tool call:
1. Say what you are ABOUT to do (e.g. "Let me search for that...")
2. Call the tool
3. Say what happened (e.g. "Found it. Opening now, Boss.")

Examples:
- Boss: "play despacito" → You: "Looking up Despacito on Spotify..." [calls spotify_play] → "Despacito by Luis Fonsi. Playing now."
- Boss: "open the latest MrBeast video" → You: "Let me find the latest MrBeast video..." [calls web_search] → "Got it. Opening now, Boss." [calls open_url]
- Boss: "check my goals" → You: "Pulling up your goals..." [calls goals_tool_handler] → "You have 3 active goals. Your IITM course is 60% complete, due May 31st."

You MUST speak audibly before, during, and after every tool sequence. Do not go silent.

[TOOL REFERENCE]
Screen & Vision:
- **Automatic**: I stream your screen (~1 FPS, 720p) to the Live API at all times. You can see what's on screen without calling any tool. Just describe what you see.
- see_screen(question) — REST fallback for higher-res detailed analysis of a specific question about the screen. Use when you need more detail than the live feed provides.
- vision_click(target_description) — find element by description and click it.

Browser Automation (OpenCLI — use ONLY when page interaction is needed):
For simple URL opens, use open_url(url) instead — it's faster.
Use OpenCLI when you need to click, type, scroll, extract content, or fill forms.
OpenCLI also handles logged-in sites (Instagram, Twitter, Reddit) using existing browser sessions.
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
- research_tool_handler(action, topic) — analyze, synthesize, optimize research topics
- reasoning_tool_handler(action, problem) — Chain-of-Thought, Tree-of-Thought, ReAct reasoning
- video_search(query) — find and open actual video URL
- open_url(url) — open URL in browser. **PREFERRED for simple URL opens.** Do NOT use OpenCLI just to navigate to a URL. Use OpenCLI only when you need to interact with the page (click, type, scroll, fill forms).
- multi_agent_delegate(action, task, agent, split_by) — delegate to 9 specialist sub-agents
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
- list_running_apps(), get_active_window()
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
- goals_tool_handler(action, goal) — add/list/complete goals, morning plan, evening review, OKR scoring
- vector_memory_tool(action, query, text) — semantic memory search
- memory_store(key, value, category) — store facts
- memory_retrieve(query) — recall memories
- memory_import_tool_handler(action, file_path) — import chat history
- knowledge_graph_tool(action, node_id) — entity-relation knowledge graph
- skills_tool(action, name, steps) — self-improving skills: save/load/search workflows like Hermes Agent. Actions: list, add, search, delete, stats, auto_create, curate
- predictive_tool(action) — learns your usage patterns, predicts what you need next
- dream_tool(action) — dreaming system: analyzes past sessions while idle
- scheduler_tool(action, name, schedule) — cron scheduler for autonomous tasks
- reflection_tool(action) — GEPA self-reflection: analyzes tool outcomes, finds failure patterns, auto-improves
- context_tool(action, name, content) — manage project context files (AGENTS.md, CLAUDE.md, FRIDAY.md). Actions: list, show, add, delete, reload
- episodic_tool(action, query) — episodic memory with FTS5: full-text search all past sessions, tool calls, and interactions. Actions: search (query past), recent (last N), session (full session by id), stats. Auto-records all tool calls.
- self_improve_tool(action, file_path, content) — self-improvement pipeline: propose changes to my own code, show diffs, apply or reject with your approval. Actions: propose, list, diff, apply, reject, status.
- crash_tool(action) — crash watcher: monitors Windows Event Log for app crashes in real-time, captures fault details. Actions: status, recent, analyze (deep dive), watch (start), stop.
- pr_manager_tool(action) — proactive PR manager: polls GitHub repos for open PRs, auto-reviews new ones. Actions: status, list_repos, add_repo (repo=name), remove_repo (repo=name), scan_now (auto_review=true), reviews, watch, stop.
- protector_tool(action) — system protector: prevent unauthorized shutdown/lid-close, manage Windows startup registration. Actions: status, watch (start background monitor), stop, allow (permit shutdown), startup (startup_action=install/remove/status), test_voice (test TTS).

System & Monitoring:
- status_check(include) — quick system overview (goals, calendar, email, notifications, CPU, RAM, active window)
- system_cpu(), system_memory(), system_disk(), system_network() — individual system stats
- system_report() — detailed full system report
- monitor_tool(action) — proactive desktop monitor: detects CPU spikes, crashes, memory pressure. Actions: status, alerts, config, start, stop, check

MCP (Model Context Protocol):
- mcp_tool(action, name, command, args, server, tool, params) — connect external MCP servers for extensibility. Actions: list (show servers+tools), connect (add server by command), disconnect (remove), call (invoke tool), clean (disconnect all)

KYU (Know Your User):
- kyu_tool_handler(action) — manage personality profile (status, interview, profile, adapt)
- Automatically learns from your tool usage and adapts to your preferences

Communication:
- google_authorize(), read_emails(count), send_email(to, subject, body)
- draft_email(context, recipient) — AI-drafted email
- send_instagram_dm(username, message)

Media:
- netflix_play(title) — find Netflix title ID + open direct URL

Workflows & Plugins:
- workflow_tool(action, name, steps) — create/run multi-step workflows
- plugin_tool(action, plugin_name) — load/call plugin modules
- github_setup(token='...') — PREFERRED: set GitHub PAT. Pass token='github_pat_...' or leave empty for instructions.
- github_authorize() — Device Flow fallback (Opens browser, shows code to enter at github.com/login/device)
- github_refresh_token() — manually refresh GitHub App token (only needed if expiry enabled)
- github_list_files, github_read_file, github_write_file — GitHub repo access
- github_create_branch, github_create_pr, github_list_prs(repo, state), github_pr_comment(pr_number, body), github_pr_diff(pr_number), github_pr_files(pr_number), github_delete_file(path, message), github_get_contents(path), github_get_user(), github_self_modify, github_review_pr

Deep Code Review:
- deep_code_review(action, target, auto_fix, ...) — walk source files, analyze each with Gemini AI, find bugs/security/perf/style issues. Actions: analyze (default), fix (review + auto-create GitHub PR), new_project (create repo + push), fork_pr (fork → fix → PR). Target: 'self' (FRIDAY's code), local path, or 'owner/repo'.
- code_review_report(target) — quick file count/type summary before deep review

Smart Home:
- tell_alexa(command), smart_home_command(action, device)
- home_assistant_command(entity_id, command)

StayFree:
- stayfree_status(), stayfree_today(), stayfree_week()

Files:
- read_file, write_file, list_files, find_files, copy_file, move_file, delete_file
- clipboard_get, clipboard_set
- generate_file(path, type, description), generate_file_llm(path, prompt)

Code & Dev:
- climb_codebase(query, path) — ripgrep codebase search
- git_ops(operation, message) — git operations

Calendar:
- calendar_tool_handler(action, days) — list/sync Google Calendar

Startup:
- startup_tool_handler(action) — manage auto-start

OpenCLI Site Adapters:
- opencli_run("hackernews top --limit 5") — HackerNews
- opencli_run("reddit hot --limit 5") — Reddit
- opencli_run("twitter trending --limit 5") — Twitter/X
- opencli_list_adapters() — discover all site adapters

[PROACTIVE CHECKS — USE status_check() NOT 5 SEPARATE TOOLS]
When you have initiative (startup, idle), call status_check("all") ONCE
instead of calling 5+ separate tools. It aggregates goals, calendar, email,
notifications, system stats, and active window into a single response.

CRITICAL: Never call goals_tool_handler + calendar_tool_handler + read_emails +
get_pending_notifications + system_cpu in parallel. Use status_check() instead.
This prevents tool-call overload.

For clock/timer/alarm: use clock_tool, NOT open_app.
For system stats: use status_check() or system_cpu/system_memory, NOT separate tools.

[BASIC INFO]
- Boss name: Arnav
- Boss email: phulariarnav@gmail.com

[BREVITY]
Short responses. One or two sentences for spoken text.
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


def _audio_playback_worker(pa: pyaudio.PyAudio):
    stream = pa.open(
        format=pyaudio.paInt16, channels=1, rate=24000,
        output=True, frames_per_buffer=4800
    )
    stream.start_stream()
    had_audio = False
    empty_cycles = 0
    jitter_buffer = []
    UNDERFLOW_GUARD = 20  # chunks to pre-fill (~4s at 200ms/chunk)
    try:
        while not _audio_playback_stop.is_set():
            while len(jitter_buffer) < UNDERFLOW_GUARD and not _audio_playback_stop.is_set():
                try:
                    chunk = _audio_playback_queue.get(timeout=0.2)
                    if chunk is None:
                        break
                    jitter_buffer.append(chunk)
                except _thread_queue.Empty:
                    break
            try:
                chunk = jitter_buffer.pop(0) if jitter_buffer else _audio_playback_queue.get(timeout=0.2)
                if chunk is None:
                    break
                if not had_audio:
                    had_audio = True
                    _mic_muted.set()
                try:
                    stream.write(chunk, exception_on_underflow=False)
                except OSError:
                    jitter_buffer.clear()
                    continue
                global _is_ducked, last_audio_time
                if not _is_ducked:
                    _is_ducked = True
                    set_audio_ducking(True)
                last_audio_time = time.time()
                empty_cycles = 0
            except (_thread_queue.Empty, IndexError):
                if had_audio:
                    empty_cycles += 1
                    if empty_cycles >= 6 and _model_turn_done.is_set():
                        had_audio = False
                        empty_cycles = 0
                        jitter_buffer.clear()
                        _mic_muted.clear()
                        set_audio_ducking(False)
                continue
    finally:
        jitter_buffer.clear()
        _mic_muted.clear()
        _model_turn_done.clear()
        set_audio_ducking(False)
        try:
            stream.stop_stream()
        except Exception:
            pass
        try:
            stream.close()
        except Exception:
            pass


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
        target=_audio_playback_worker, args=(pa,), daemon=True
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
                description="Open an application by name (e.g. 'chrome', 'spotify', 'notepad'). Does NOT open Windows Clock, set timers, or alarms — use clock_tool for that.",
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
                name="cv_tool",
                description="Access the camera: start/stop the camera, get scene context, list available cameras, describe what the camera sees in real-time. Use 'describe_scene' action for a full description.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {
                        "type": "STRING",
                        "description": "Action to perform on the camera",
                        "enum": ["start", "stop", "status", "list_cameras", "describe_scene"],
                    }
                }, required=["action"]),
            ),
            types.FunctionDeclaration(
                name="open_url",
                description="Open a URL in the browser or launch a URI scheme (roblox://, ms-windows-store://).",
                parameters=types.Schema(type="OBJECT", properties={
                    "url": {"type": "STRING", "description": "URL to open."}
                }, required=["url"]),
            ),
            types.FunctionDeclaration(
                name="open_roblox_game",
                description="Search Roblox API for a game by name (fuzzy match), find its place ID, then open via roblox:// URI. Handles misspellings. Never opens a browser.",
                parameters=types.Schema(type="OBJECT", properties={
                    "game_name": {"type": "STRING", "description": "Name of the Roblox game to open."}
                }, required=["game_name"]),
            ),
            types.FunctionDeclaration(
                name="open_microsoft_store",
                description="Open Microsoft Store via ms-windows-store:// URI. Search for apps or open a specific product. Never opens a browser.",
                parameters=types.Schema(type="OBJECT", properties={
                    "query": {"type": "STRING", "description": "Search query for apps."},
                    "product_id": {"type": "STRING", "description": "Product ID to open directly."}
                }),
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
                name="system_cpu",
                description="Get current CPU usage percentage."
            ),
            types.FunctionDeclaration(
                name="system_memory",
                description="Get current RAM usage stats (used/total/percent)."
            ),
            types.FunctionDeclaration(
                name="system_disk",
                description="Get disk usage for a drive path.",
                parameters=types.Schema(type="OBJECT", properties={
                    "path": {"type": "STRING", "description": "Drive path to check (default C:\\)"}
                }),
            ),
            types.FunctionDeclaration(
                name="system_network",
                description="Get network I/O stats since boot (bytes sent/received)."
            ),
            types.FunctionDeclaration(
                name="system_processes",
                description="List top processes by CPU or memory usage.",
                parameters=types.Schema(type="OBJECT", properties={
                    "sort_by": {"type": "STRING", "description": "Sort by 'cpu' or 'memory' (default memory)."},
                    "limit": {"type": "INTEGER", "description": "Number of processes to show (default 10)."},
                }),
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
                name="opencli_run",
                description="Run ANY OpenCLI command (site adapters, browser, desktop apps, CLI hub). Examples: 'hackernews top --limit 5', 'reddit hot --limit 5', 'browser open https://...', 'list'",
                parameters=types.Schema(type="OBJECT", properties={
                    "command": {"type": "STRING", "description": "The full OpenCLI command string."}
                }, required=["command"]),
            ),
            types.FunctionDeclaration(
                name="opencli_list_adapters",
                description="List all available OpenCLI commands and built-in site adapters."
            ),
            types.FunctionDeclaration(
                name="opencli_hover",
                description="Hover over a browser element.",
                parameters=types.Schema(type="OBJECT", properties={
                    "target": {"type": "STRING", "description": "Element selector to hover."}
                }, required=["target"]),
            ),
            types.FunctionDeclaration(
                name="opencli_focus",
                description="Focus a browser element.",
                parameters=types.Schema(type="OBJECT", properties={
                    "target": {"type": "STRING", "description": "Element selector to focus."}
                }, required=["target"]),
            ),
            types.FunctionDeclaration(
                name="opencli_dblclick",
                description="Double-click a browser element.",
                parameters=types.Schema(type="OBJECT", properties={
                    "target": {"type": "STRING", "description": "Element selector to double-click."}
                }, required=["target"]),
            ),
            types.FunctionDeclaration(
                name="opencli_check",
                description="Check a checkbox/radio browser element.",
                parameters=types.Schema(type="OBJECT", properties={
                    "target": {"type": "STRING", "description": "Checkbox/radio selector to check."}
                }, required=["target"]),
            ),
            types.FunctionDeclaration(
                name="opencli_uncheck",
                description="Uncheck a checkbox/radio browser element.",
                parameters=types.Schema(type="OBJECT", properties={
                    "target": {"type": "STRING", "description": "Checkbox/radio selector to uncheck."}
                }, required=["target"]),
            ),
            types.FunctionDeclaration(
                name="opencli_drag",
                description="Drag one browser element to another.",
                parameters=types.Schema(type="OBJECT", properties={
                    "source": {"type": "STRING", "description": "Source element selector to drag."},
                    "target": {"type": "STRING", "description": "Target element selector to drop on."}
                }, required=["source", "target"]),
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
                name="google_authorize",
                description="Authorize ALL Google services (Gmail + Calendar). Opens browser for OAuth consent. Run this if emails or calendar fail due to auth. Only needed once.",
            ),
            types.FunctionDeclaration(
                name="gmail_authorize",
                description="Alias for google_authorize. Authorizes Gmail + Calendar together.",
            ),
            types.FunctionDeclaration(
                name="exchange_oauth_code",
                description="Complete OAuth by pasting the browser redirect URL. Use this if google_authorize fails with SSL errors.",
                parameters=types.Schema(type="OBJECT", properties={
                    "redirect_url": {"type": "STRING", "description": "Full URL from browser address bar after Google consent (contains ?code=...)."}
                }, required=["redirect_url"]),
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
                description="Track personal goals: add, list, update, complete, delete, check progress, enforce, okr score, morning plan, evening review. Always include url and deadline when creating a goal.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: add, list, update, complete, delete, check, enforce, okr, morning, evening, plan, review, sync_calendar, calendar, profile."},
                    "goal": {"type": "STRING", "description": "Goal title or name (used when action=add)."},
                    "category": {"type": "STRING", "description": "Goal category: generic, course, exam, assignment (used when action=add)."},
                    "deadline": {"type": "STRING", "description": "Goal deadline date in YYYY-MM-DD format (used when action=add)."},
                    "url": {"type": "STRING", "description": "Reference URL for the goal, e.g. course link or resource (used when action=add)."},
                    "description": {"type": "STRING", "description": "Goal description or details (used when action=add)."},
                    "verification_method": {"type": "STRING", "description": "How to verify progress: browser_history, file_check, or manual (used when action=add)."},
                    "verification_data": {"type": "STRING", "description": "Data for verification: URL pattern to check in browser history, or file path (used when action=add)."},
                    "goal_id": {"type": "STRING", "description": "Goal ID for update/complete/delete/enforce actions."},
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
                name="kyu_tool_handler",
                description="Know Your User: manage your personality profile, run interview, learn preferences. Actions: status, interview, profile, adapt.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: status, interview, profile, adapt, learn."},
                    "stage": {"type": "INTEGER", "description": "Interview stage (1-4). Used with action=interview."},
                    "tool_name": {"type": "STRING", "description": "Tool name to learn from (action=learn only)."},
                    "active_window": {"type": "STRING", "description": "Active window title (action=learn only)."},
                    "hour": {"type": "INTEGER", "description": "Hour of day 0-23 (action=learn only)."},
                }, required=["action"]),
            ),
            types.FunctionDeclaration(
                name="research_tool_handler",
                description="Autonomous research: analyze topics, evaluate sources, synthesize findings. Actions: analyze, synthesize, optimize.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: analyze, synthesize, optimize."},
                    "topic": {"type": "STRING", "description": "Research topic or question."},
                    "depth": {"type": "INTEGER", "description": "Research depth (1-5, default 3)."},
                }, required=["action"]),
            ),
            types.FunctionDeclaration(
                name="reasoning_tool_handler",
                description="Advanced reasoning: Chain-of-Thought, Tree-of-Thought, ReAct. Actions: cot, tot, react, compare.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: cot (Chain-of-Thought), tot (Tree-of-Thought), react, compare."},
                    "problem": {"type": "STRING", "description": "Problem or question to reason about."},
                    "max_steps": {"type": "INTEGER", "description": "Maximum reasoning steps (default 10)."},
                    "branching_factor": {"type": "INTEGER", "description": "Branching factor for Tree-of-Thought (default 3)."},
                }, required=["action"]),
            ),
            types.FunctionDeclaration(
                name="clock_tool",
                description="Windows Clock: alarms, timers, stopwatches, reminders, focus mode. "
                            "Actions: status (show all), open (launch Clock app), alarm (sub=set/list/delete), "
                            "timer (sub=start/set/status/stop), stopwatch (sub=start/stop/lap/reset), "
                            "reminder (sub=set/list/delete), focus (sub=start/stop). "
                            "Example: timer sub=start seconds=20 for a 20s timer.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: status, open, alarm, timer, stopwatch, reminder, focus."},
                    "sub": {"type": "STRING", "description": "Sub-action: set, list, delete, start, stop, lap, reset, done."},
                    "time": {"type": "STRING", "description": "Time in HH:MM 24h format (for alarm/reminder)."},
                    "minutes": {"type": "INTEGER", "description": "Duration in minutes (for timer/focus)."},
                    "seconds": {"type": "INTEGER", "description": "Additional seconds (for timer — e.g. seconds=20 for a 20s timer)."},
                    "label": {"type": "STRING", "description": "Label for alarm/timer."},
                    "text": {"type": "STRING", "description": "Text for reminder."},
                    "id": {"type": "STRING", "description": "ID for delete/stop actions."},
                }, required=["action"]),
            ),
            types.FunctionDeclaration(
                name="status_check",
                description="Quick system status: goals, calendar, email, notifications, CPU, RAM, active window. Call this ONCE instead of 5 separate tools.",
                parameters=types.Schema(type="OBJECT", properties={
                    "include": {"type": "STRING", "description": "What to check: 'all' for everything, or comma-separated: goals,calendar,email,notifications,system,window"},
                }),
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
                name="github_list_prs",
                description="List pull requests for a GitHub repository. Pass repo='owner/repo' or leave empty for default. Use state='open' (default), 'closed', or 'all'.",
                parameters=types.Schema(type="OBJECT", properties={
                    "repo": {"type": "STRING", "description": "Repository in 'owner/repo' format (default: hackers-reality/friday)."},
                    "state": {"type": "STRING", "description": "PR state: open, closed, or all (default: open)."},
                }),
            ),
            types.FunctionDeclaration(
                name="github_pr_comment",
                description="Add a comment to a pull request or issue.",
                parameters=types.Schema(type="OBJECT", properties={
                    "pr_number": {"type": "INTEGER", "description": "Pull request or issue number."},
                    "body": {"type": "STRING", "description": "Comment text."},
                }, required=["pr_number", "body"]),
            ),
            types.FunctionDeclaration(
                name="github_pr_diff",
                description="Get the full diff of a pull request.",
                parameters=types.Schema(type="OBJECT", properties={
                    "pr_number": {"type": "INTEGER", "description": "Pull request number."},
                }, required=["pr_number"]),
            ),
            types.FunctionDeclaration(
                name="github_pr_files",
                description="List files changed in a pull request.",
                parameters=types.Schema(type="OBJECT", properties={
                    "pr_number": {"type": "INTEGER", "description": "Pull request number."},
                }, required=["pr_number"]),
            ),
            types.FunctionDeclaration(
                name="github_delete_file",
                description="Delete a file from the repository.",
                parameters=types.Schema(type="OBJECT", properties={
                    "path": {"type": "STRING", "description": "File path in repository."},
                    "message": {"type": "STRING", "description": "Commit message (default: 'Delete via Friday')."},
                }, required=["path"]),
            ),
            types.FunctionDeclaration(
                name="github_get_contents",
                description="List contents of a directory or read a file from the repository.",
                parameters=types.Schema(type="OBJECT", properties={
                    "path": {"type": "STRING", "description": "Path to list or file to read (default: root)."},
                }),
            ),
            types.FunctionDeclaration(
                name="github_get_user",
                description="Get authenticated GitHub user info (login, name, plan)."
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
            types.FunctionDeclaration(
                name="github_create_repo",
                description="Create a new GitHub repository.",
                parameters=types.Schema(type="OBJECT", properties={
                    "name": {"type": "STRING", "description": "Repository name."},
                    "description": {"type": "STRING", "description": "Repository description."},
                    "private": {"type": "BOOLEAN", "description": "Whether the repo is private (default false)."},
                }, required=["name"]),
            ),
            types.FunctionDeclaration(
                name="github_list_issues",
                description="List issues in the GitHub repository.",
                parameters=types.Schema(type="OBJECT", properties={
                    "state": {"type": "STRING", "description": "Issue state: open, closed, all (default open)."},
                    "labels": {"type": "STRING", "description": "Comma-separated labels to filter by."},
                }),
            ),
            types.FunctionDeclaration(
                name="github_create_issue",
                description="Create a GitHub issue.",
                parameters=types.Schema(type="OBJECT", properties={
                    "title": {"type": "STRING", "description": "Issue title."},
                    "body": {"type": "STRING", "description": "Issue body/description."},
                    "labels": {"type": "STRING", "description": "Comma-separated labels."},
                }, required=["title"]),
            ),
            types.FunctionDeclaration(
                name="github_search_code",
                description="Search code across GitHub repositories.",
                parameters=types.Schema(type="OBJECT", properties={
                    "query": {"type": "STRING", "description": "Search query."},
                    "repo": {"type": "STRING", "description": "Optional: restrict to a specific repo (owner/repo)."},
                }, required=["query"]),
            ),
            types.FunctionDeclaration(
                name="github_merge_pr",
                description="Merge a GitHub pull request.",
                parameters=types.Schema(type="OBJECT", properties={
                    "pr_number": {"type": "INTEGER", "description": "Pull request number to merge."},
                    "commit_title": {"type": "STRING", "description": "Optional commit title for the merge."},
                }, required=["pr_number"]),
            ),
            types.FunctionDeclaration(
                name="github_repo_info",
                description="Get information about the GitHub repository."
            ),
            types.FunctionDeclaration(
                name="github_list_branches",
                description="List all branches in the GitHub repository."
            ),
            types.FunctionDeclaration(
                name="github_commit_history",
                description="Get commit history for the GitHub repository.",
                parameters=types.Schema(type="OBJECT", properties={
                    "path": {"type": "STRING", "description": "Optional: file path to get history for a specific file."},
                    "limit": {"type": "INTEGER", "description": "Number of commits to return (default 10)."},
                }),
            ),
            types.FunctionDeclaration(
                name="github_setup",
                description="PREFERRED: set up GitHub with a Personal Access Token. Pass token='github_pat_...' to validate and save. Leave token empty for instructions on generating one."
            ),
            types.FunctionDeclaration(
                name="github_authorize",
                description="FALLBACK: Start GitHub Device Flow authorization. Opens browser, shows a code to enter at github.com/login/device. Blocks up to 5 minutes."
            ),
            types.FunctionDeclaration(
                name="github_exchange_code",
                description="Check GitHub auth status or manually poll with a device_code.",
                parameters=types.Schema(type="OBJECT", properties={
                    "device_code": {"type": "STRING", "description": "Optional device_code from github_authorize to poll. Leave empty to check saved token status."},
                }),
            ),
            types.FunctionDeclaration(
                name="github_refresh_token",
                description="Manually refresh the GitHub App token. Only for GitHub Apps with expiring tokens."
            ),
            types.FunctionDeclaration(
                name="github_review_pr",
                description="Deep AI review of a pull request: fetches diff, analyzes with Gemini, posts review comments.",
                parameters=types.Schema(type="OBJECT", properties={
                    "pr_number": {"type": "INTEGER", "description": "Pull request number to review."}
                }, required=["pr_number"]),
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
            # ======== DREAMING SYSTEM ========
            types.FunctionDeclaration(
                name="dream_tool",
                description="Dreaming system: analyze past sessions while idle to extract patterns and learn. Actions: status (show state), cycle (run one cycle), start/stop (toggle background dreaming), insights (show learned patterns).",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: status, cycle, start, stop, insights."},
                }, required=["action"]),
            ),
            # ======== SCHEDULER ========
            types.FunctionDeclaration(
                name="scheduler_tool",
                description="Schedule autonomous tasks: status checks, goal reviews, system checks, dream cycles. Actions: list, add, remove, pause, resume, start, stop. Example: add name='daily check' schedule='daily' action_type='status_check'",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: list, add, remove, pause, resume, start, stop."},
                    "name": {"type": "STRING", "description": "Task name (for add/remove)."},
                    "schedule": {"type": "STRING", "description": "Interval: daily, hourly, every 30 minutes, etc. (for add)."},
                    "action_type": {"type": "STRING", "description": "Action: status_check, goals_review, system_check, dream_cycle, custom (for add)."},
                    "params": {"type": "STRING", "description": "JSON params for the action (optional, for add)."},
                    "command": {"type": "STRING", "description": "Shell command (for action_type=custom)."},
                    "id": {"type": "STRING", "description": "Task ID (for remove/pause/resume)."},
                }, required=["action"]),
            ),
            # ======== SKILLS SYSTEM ========
            types.FunctionDeclaration(
                name="skills_tool",
                description="Self-improving skills system: save, search, and reuse successful workflows. Actions: list (show all), add (create), search (find by keyword), delete, stats, auto_create, curate (auto-archive stale, prune failing, suggest merges).",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: list, add, search, delete, stats, auto_create."},
                    "name": {"type": "STRING", "description": "Skill name (for add/search/delete)."},
                    "steps": {"type": "STRING", "description": "Steps/procedure for the skill (for add/auto_create)."},
                    "trigger": {"type": "STRING", "description": "Trigger phrase that should activate this skill (for add/auto_create)."},
                    "tags": {"type": "STRING", "description": "Comma-separated tags (for add/auto_create)."},
                    "query": {"type": "STRING", "description": "Search query (for search)."},
                    "id": {"type": "STRING", "description": "Skill ID (for delete)."},
                }, required=["action"]),
            ),
            # ======== PREDICTIVE ANALYSIS ========
            types.FunctionDeclaration(
                name="predictive_tool",
                description="Predictive analysis: learns your usage patterns and anticipates needs. Actions: predict (what you typically do now), patterns (learning stats), stats (peak hours).",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: predict, patterns, stats."},
                    "hour": {"type": "INTEGER", "description": "Hour to predict for (0-23, optional, defaults to now)."},
                    "day": {"type": "STRING", "description": "Day to predict for (monday-sunday, optional)."},
                }, required=["action"]),
            ),
            # ======== GEPA SELF-REFLECTION ========
            types.FunctionDeclaration(
                name="reflection_tool",
                description="GEPA self-reflection: analyze tool outcomes, find failure patterns, and auto-improve. Actions: cycle (run full reflection), analyze (show active failure patterns), improvements (list applied fixes), status (show state).",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: cycle, analyze, improvements, status."},
                }, required=["action"]),
            ),
            # ======== CONTEXT FILES ========
            types.FunctionDeclaration(
                name="context_tool",
                description="Manage project context files (AGENTS.md, CLAUDE.md, FRIDAY.md). Actions: list (show all), show (view content), add (create/update), delete (remove), reload (re-read files).",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: list, show, add, delete, reload."},
                    "name": {"type": "STRING", "description": "Context file name (for show/add/delete)."},
                    "content": {"type": "STRING", "description": "File content (for add)."},
                }, required=["action"]),
            ),
            # ======== PROACTIVE MONITOR ========
            types.FunctionDeclaration(
                name="monitor_tool",
                description="Proactive desktop monitor: detects CPU spikes, app crashes, and memory pressure. Automatically alerts on issues. Actions: status (show state), alerts (recent incidents), config (set thresholds), start/stop, check (run manual check).",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: status, alerts, config, start, stop, check."},
                    "cpu_threshold": {"type": "INTEGER", "description": "CPU alert threshold % (for config action)."},
                    "memory_threshold": {"type": "INTEGER", "description": "Memory alert threshold % (for config action)."},
                    "check_interval": {"type": "INTEGER", "description": "Check interval in seconds (for config action)."},
                    "crash_monitor": {"type": "STRING", "description": "Enable crash detection: 'true' or 'false' (for config)."},
                    "auto_response": {"type": "STRING", "description": "Auto-respond to critical alerts: 'true' or 'false' (for config)."},
                }, required=["action"]),
            ),
            # ======== EPISODIC ARCHIVE ========
            types.FunctionDeclaration(
                name="episodic_tool",
                description="Episodic memory: full-text search past sessions, tool calls, and interactions. Actions: search (FTS query), recent (last N), record (manual), session (by id), stats, status. Auto-records all tool calls.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: search, recent, record, session, stats, status."},
                    "query": {"type": "STRING", "description": "Full-text search query (for action=search)."},
                    "limit": {"type": "INTEGER", "description": "Result limit (for search/recent, default 10/20)."},
                    "speaker": {"type": "STRING", "description": "Filter by speaker: user, tool, friday (for recent)."},
                    "session_id": {"type": "STRING", "description": "Session ID (for session/record actions)."},
                    "content": {"type": "STRING", "description": "Content to record (for action=record)."},
                    "tool_name": {"type": "STRING", "description": "Tool name (for action=record)."},
                }, required=["action"]),
            ),
            # ======== SELF-IMPROVEMENT ========
            types.FunctionDeclaration(
                name="self_improve_tool",
                description="Self-improvement pipeline: propose changes to FRIDAY's own code, review diffs, apply or reject. Actions: propose (file_path, description, content), list (pending), diff (id), apply (approve+write, id), reject (id), status.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: propose, list, diff, apply, reject, status."},
                    "file_path": {"type": "STRING", "description": "Path to file to modify (for action=propose)."},
                    "description": {"type": "STRING", "description": "Description of the change (for action=propose)."},
                    "content": {"type": "STRING", "description": "New file content (for action=propose)."},
                    "id": {"type": "STRING", "description": "Change ID (for diff/apply/reject)."},
                    "commit": {"type": "BOOLEAN", "description": "Whether to git commit after apply (default true, for action=apply)."},
                }, required=["action"]),
            ),
            # ======== CRASH WATCHER ========
            types.FunctionDeclaration(
                name="crash_tool",
                description="Crash watcher: monitors Windows app crashes via Event Log in real-time. Actions: status (watcher state), recent (list recent crashes), analyze (deep dive into crash, optional index=N), watch (start background poll every 30s), stop.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: status, recent, analyze, watch, stop."},
                    "limit": {"type": "INTEGER", "description": "Result limit (for action=recent)."},
                    "index": {"type": "INTEGER", "description": "Crash index to analyze, -1 = latest (for action=analyze)."},
                }, required=["action"]),
            ),
            # ======== PROACTIVE PR MANAGER ========
            types.FunctionDeclaration(
                name="pr_manager_tool",
                description="Proactive PR manager: polls configured GitHub repos for open PRs and auto-reviews new ones. Actions: status, list_repos, add_repo (repo=REPO), remove_repo (repo=REPO), scan_now (immediate scan, auto_review=true), list_prs (fetch ALL open PRs for any repo: repo=REPO, state=open/closed/all), reviews, watch (start background 5min polling), stop.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: status, list_repos, add_repo, remove_repo, scan_now, list_prs, reviews, watch, stop."},
                    "repo": {"type": "STRING", "description": "Repository name (for add_repo/remove_repo/list_prs, e.g. 'vierisid/jarvis')."},
                    "state": {"type": "STRING", "description": "PR state filter: open, closed, or all (for action=list_prs)."},
                    "auto_review": {"type": "BOOLEAN", "description": "Whether to auto-analyze new PRs (for scan_now, default true)."},
                    "limit": {"type": "INTEGER", "description": "Result limit (for action=reviews)."},
                }, required=["action"]),
            ),
            # ======== SYSTEM PROTECTOR ========
            types.FunctionDeclaration(
                name="protector_tool",
                description="System protector: prevent unauthorized shutdown/lid-close, manage Windows startup registration. Actions: status (show state), watch (start background monitor for lid/shutdown/sleep), stop, allow (permit shutdown), startup (manage startup: pass startup_action=install/remove/status), test_voice (test TTS).",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: status, watch, stop, allow, startup, test_voice."},
                    "startup_action": {"type": "STRING", "description": "For action=startup: install, remove, or status."},
                }, required=["action"]),
            ),
            # ======== MCP BRIDGE ========
            types.FunctionDeclaration(
                name="mcp_tool",
                description="MCP bridge: connect external Model Context Protocol servers for extensibility. Actions: list (show servers+tools), connect (add server), disconnect (remove), call (invoke tool on a server), clean (disconnect all).",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: list, connect, disconnect, call, clean."},
                    "name": {"type": "STRING", "description": "Server name (for connect/disconnect)."},
                    "command": {"type": "STRING", "description": "Command to start the MCP server (e.g., 'npx', 'python', 'node')."},
                    "args": {"type": "STRING", "description": "Command arguments as comma-separated string (for connect)."},
                    "server": {"type": "STRING", "description": "Target server name (for call action)."},
                    "tool": {"type": "STRING", "description": "Tool name to invoke (for call action)."},
                    "params": {"type": "STRING", "description": "JSON string of tool parameters (for call action)."},
                }, required=["action"]),
            ),
            # ======== DEEP CODE REVIEW ========
            types.FunctionDeclaration(
                name="deep_code_review",
                description="Deep code review powered by Gemini. Walks source files, analyzes each with AI, and reports bugs/security/perf/style issues. Actions: analyze (default — review + report), fix (review + auto-create GitHub PR with fixes), new_project (create GitHub repo + push code), fork_pr (fork repo → fix → PR). Target: 'self' (FRIDAY's code), local path, or 'owner/repo'. Set auto_fix=True to create a PR.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: analyze (default), fix, new_project, fork_pr."},
                    "target": {"type": "STRING", "description": "Target to review: 'self' (FRIDAY's code), local path, or GitHub 'owner/repo'."},
                    "file_pattern": {"type": "STRING", "description": "File glob pattern (default '*.*')."},
                    "auto_fix": {"type": "BOOLEAN", "description": "If true, automatically generate fixes and create PR (for analyze/fix actions)."},
                    "pr_title": {"type": "STRING", "description": "Title for auto-generated PR."},
                    "pr_body": {"type": "STRING", "description": "Body/description for auto-generated PR."},
                    "repo_description": {"type": "STRING", "description": "Description for new repo (for new_project action)."},
                    "branch_name": {"type": "STRING", "description": "Branch name for PR (for fix/fork_pr actions)."},
                    "repo_name": {"type": "STRING", "description": "Repository name (for new_project action)."},
                    "github_repo": {"type": "STRING", "description": "Target GitHub repo 'owner/repo' for PR (for fix action)."},
                }),
            ),
            types.FunctionDeclaration(
                name="code_review_report",
                description="Quick summary of source files: file count, total lines, breakdown by extension type. Useful before deep_code_review to estimate scope.",
                parameters=types.Schema(type="OBJECT", properties={
                    "target": {"type": "STRING", "description": "Target: 'self', local path, or 'owner/repo'."},
                }, required=["target"]),
            ),
            # Phase 14/15/16 tool declarations
            types.FunctionDeclaration(
                name="tool_registry_tool",
                description="Query the FRIDAY tool registry. Actions: status (overview), list (all tools), get (specific tool metadata), check (consistency).",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: status, list, get, check."},
                    "tool_name": {"type": "STRING", "description": "Tool name for 'get' action."},
                    "category": {"type": "STRING", "description": "Optional category filter for 'list'."},
                }),
            ),
            types.FunctionDeclaration(
                name="authority_tool",
                description="Manage FRIDAY's authority/action policy. Actions: status, policy, classify, block, unblock, allow_risk, block_risk, mode (set: auto/ask/dry_run/block_all).",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: status, policy, classify, block, unblock, allow_risk, block_risk, mode."},
                    "tool": {"type": "STRING", "description": "Tool name for block/unblock/classify."},
                    "risk": {"type": "STRING", "description": "Risk level for allow_risk/block_risk."},
                    "mode": {"type": "STRING", "description": "Policy mode: auto, ask, dry_run, block_all."},
                }),
            ),
            types.FunctionDeclaration(
                name="snapshot_tool",
                description="Create and manage file/directory snapshots. Actions: list, create, restore, diff, info.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: list, create, restore, diff, info."},
                    "path": {"type": "STRING", "description": "File/directory path for create action."},
                    "id": {"type": "STRING", "description": "Snapshot ID for restore/diff/info."},
                    "description": {"type": "STRING", "description": "Optional description for snapshot."},
                    "restore_path": {"type": "STRING", "description": "Optional restore destination path."},
                }),
            ),
            types.FunctionDeclaration(
                name="sidecar_tool",
                description="Manage FRIDAY sidecars. Actions: status, list, register, heartbeat, info, dispatch.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: status, list, register, heartbeat, info, dispatch."},
                    "name": {"type": "STRING", "description": "Sidecar name for register."},
                    "type": {"type": "STRING", "description": "Sidecar type: desktop, browser, filesystem, system_monitor, code_workspace, smart_home."},
                    "id": {"type": "STRING", "description": "Sidecar ID for heartbeat/info/dispatch."},
                    "command": {"type": "STRING", "description": "Command for dispatch: ping, capabilities, exec, shutdown."},
                    "endpoint": {"type": "STRING", "description": "Endpoint URL for remote sidecar."},
                    "status": {"type": "STRING", "description": "Status: alive, busy, error, shutdown."},
                }),
            ),
            types.FunctionDeclaration(
                name="autonomy_tool",
                description="Manage the autonomous task queue. Actions: status, queue, get, list, complete, fail, pause, resume.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: status, queue, get, list, complete, fail, pause, resume."},
                    "description": {"type": "STRING", "description": "Task description for queue."},
                    "id": {"type": "STRING", "description": "Task ID for get/complete/fail/pause/resume."},
                    "status": {"type": "STRING", "description": "Status filter for list."},
                    "max_retries": {"type": "INTEGER", "description": "Max retries for task."},
                }),
            ),
            types.FunctionDeclaration(
                name="dashboard_api_tool",
                description="Manage the FRIDAY Dashboard API server. Actions: status, start, stop.",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: status, start, stop."},
                    "port": {"type": "INTEGER", "description": "Port number for start action."},
                }),
            ),
            types.FunctionDeclaration(
                name="capabilities_tool",
                description="Query FRIDAY's capability matrix. Actions: list (all capabilities), get (specific capability status), report (generate full capability report).",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: list, get, report."},
                    "capability": {"type": "STRING", "description": "Capability name for get action."},
                    "status": {"type": "STRING", "description": "Status filter: stable, partial, experimental, planned."},
                }),
            ),
            types.FunctionDeclaration(
                name="ironman_tool",
                description="Iron Man system features. Actions: damage_report (system health audit with risk scoring), suit_check (pre-flight verification), morning_plan (daily briefing), evening_review (end-of-day summary).",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: status, damage_report, suit_check, morning_plan, evening_review."},
                }),
            ),
            types.FunctionDeclaration(
                name="memory_tree_tool",
                description="Persistent Markdown knowledge base (Memory Tree). Actions: status (overview), build_index (rebuild index), read (page by name), write (content to page), search (full-text across all pages), daily_note (get/create today's note), daily_notes (list recent), update (sync from profile), context (build injection context).",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: status, build_index, read, write, search, daily_note, daily_notes, update, context."},
                    "name": {"type": "STRING", "description": "Page name for read/write."},
                    "content": {"type": "STRING", "description": "Page content for write action."},
                    "query": {"type": "STRING", "description": "Search query for search action."},
                    "date": {"type": "STRING", "description": "Date for daily_note (YYYY-MM-DD)."},
                }),
            ),
            types.FunctionDeclaration(
                name="model_router_tool",
                description="Model Router — provider abstraction with fallback and cost tracking. Actions: status (config + costs), list (available models), resolve (best model for task), info (model details), update_config, health (provider health checks), usage (session costs), recent (recent usage records).",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: status, list, resolve, info, update_config, health, usage, recent."},
                    "task_type": {"type": "STRING", "description": "Task type for resolve: chat, vision, code, fast, local."},
                    "model_id": {"type": "STRING", "description": "Model ID for info action."},
                    "provider": {"type": "STRING", "description": "Provider filter for list: google, openai, anthropic, local."},
                    "preferences": {"type": "STRING", "description": "JSON preferences dict for resolve."},
                    "updates": {"type": "STRING", "description": "JSON updates dict for update_config."},
                }),
            ),
            types.FunctionDeclaration(
                name="extension_registry_tool",
                description="Extension & MCP Registry — manage extension servers, MCP tool providers. Actions: status, register_extension, update_extension, remove_extension, list_extensions, register_mcp, update_mcp, remove_mcp, list_mcp, health (check all), discover (search capabilities).",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: status, register_extension, update_extension, remove_extension, list_extensions, register_mcp, update_mcp, remove_mcp, list_mcp, health, discover."},
                    "name": {"type": "STRING", "description": "Extension or MCP server name."},
                    "type": {"type": "STRING", "description": "Extension type: mcp, tool, bridge, hook, adapter."},
                    "endpoint": {"type": "STRING", "description": "Endpoint URL or host:port for extension."},
                    "command": {"type": "STRING", "description": "Command for MCP server (register_mcp)."},
                    "args": {"type": "ARRAY", "description": "Args list for MCP server.", "items": {"type": "STRING"}},
                    "description": {"type": "STRING", "description": "Description."},
                    "capabilities": {"type": "ARRAY", "description": "Capability list.", "items": {"type": "STRING"}},
                    "query": {"type": "STRING", "description": "Capability search query for discover."},
                }),
            ),
            types.FunctionDeclaration(
                name="diagnostics_tool",
                description="Diagnostics & Benchmarks. Actions: diagnostics (run health checks), benchmarks (run performance tests), report (full diagnostics + benchmarks).",
                parameters=types.Schema(type="OBJECT", properties={
                    "action": {"type": "STRING", "description": "Action: diagnostics, benchmarks, report."},
                    "verbose": {"type": "BOOLEAN", "description": "Verbose diagnostic output."},
                }),
            ),
        ])
    ]

TOOL_MAP = {
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
    "system_cpu": system_cpu,
    "system_memory": system_memory,
    "system_disk": system_disk,
    "system_network": system_network,
    "system_processes": system_processes,
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
    "google_authorize": google_authorize,
    "gmail_authorize": gmail_authorize,
    "exchange_oauth_code": exchange_oauth_code,
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
    "opencli_run": opencli_run,
    "opencli_list_adapters": opencli_list_adapters,
    "opencli_hover": opencli_hover,
    "opencli_focus": opencli_focus,
    "opencli_dblclick": opencli_dblclick,
    "opencli_check": opencli_check,
    "opencli_uncheck": opencli_uncheck,
    "opencli_drag": opencli_drag,
    "open_roblox_game": open_roblox_game,
    "open_microsoft_store": open_microsoft_store,
    "workflow_tool": workflow_tool,
    "plugin_tool": plugin_tool,
    "knowledge_graph_tool": knowledge_graph_tool,
    "github_list_files": github_list_files,
    "github_read_file": github_read_file,
    "github_write_file": github_write_file,
    "github_create_branch": github_create_branch,
    "github_create_pr": github_create_pr,
    "github_list_prs": github_list_prs,
    "github_pr_comment": github_pr_comment,
    "github_pr_diff": github_pr_diff,
    "github_pr_files": github_pr_files,
    "github_delete_file": github_delete_file,
    "github_get_contents": github_get_contents,
    "github_get_user": github_get_user,
    "github_self_modify": github_self_modify,
    "github_review_pr": github_review_pr,
    "github_create_repo": github_create_repo,
    "github_list_issues": github_list_issues,
    "github_create_issue": github_create_issue,
    "github_search_code": github_search_code,
    "github_merge_pr": github_merge_pr,
    "github_repo_info": github_repo_info,
    "github_list_branches": github_list_branches,
    "github_commit_history": github_commit_history,
    "github_authorize": github_authorize,
    "github_exchange_code": github_exchange_code,
    "github_refresh_token": github_refresh_token,
    "github_setup": github_setup,
    "multi_agent_delegate": multi_agent_delegate,
    "kyu_tool_handler": kyu_tool_handler,
    "research_tool_handler": research_tool_handler,
    "reasoning_tool_handler": reasoning_tool_handler,
    "clock_tool": clock_tool,
    "status_check": status_check,
    "message_channel_tool": message_channel_tool,
    "send_notification": send_notification,
    "get_pending_notifications": get_pending_notifications,
    "clear_notifications": clear_notifications,
    "dream_tool": dream_tool,
    "scheduler_tool": scheduler_tool,
    "skills_tool": skills_tool,
    "predictive_tool": predictive_tool,
    "reflection_tool": reflection_tool,
    "context_tool": context_tool,
    "monitor_tool": monitor_tool,
    "mcp_tool": mcp_tool,
    "episodic_tool": episodic_tool,
    "self_improve_tool": self_improve_tool,
    "crash_tool": crash_tool,
    "pr_manager_tool": pr_manager_tool,
    "protector_tool": protector_tool,
    "deep_code_review": deep_code_review,
    "code_review_report": code_review_report,

    # Camera tool
    "cv_tool": cv_tool,

    # Phase 14/15 module tools
    "tool_registry_tool": tool_registry_tool,
    "authority_tool": authority_tool,
    "snapshot_tool": snapshot_tool,
    "sidecar_tool": sidecar_tool,
    "autonomy_tool": autonomy_tool,
    "dashboard_api_tool": dashboard_api_tool,
    "capabilities_tool": capabilities_tool,
    "ironman_tool": ironman_tool,

    # Phase 16 module tools
    "memory_tree_tool": memory_tree_tool,
    "model_router_tool": model_router_tool,
    "extension_registry_tool": extension_registry_tool,
    "diagnostics_tool": diagnostics_tool,
}


def _invoke_tool(func_name, args, session=None):
    # Run pre-hooks
    try:
        from friday.hooks import run_pre_hooks, run_post_hooks, run_error_hooks
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
            from friday.hooks import run_post_hooks
            run_post_hooks(func_name, args, str(result), session)
        except ImportError:
            pass
        return {"result": str(result)}
    except Exception as e:
        stark_log(f"Tool {func_name} error: {e}")
        # Run error-hooks
        try:
            from friday.hooks import run_error_hooks
            run_error_hooks(func_name, args, e, session)
        except ImportError:
            pass
        return {"error": str(e)}


# SESSION CONFIG
def _build_session_config(tools, resume_handle=None):
    # Build system instruction with KYU adaptation
    try:
        from friday.kyu import kyu_adapt
        adapt = kyu_adapt()
        kyu_section = f"""

[KYU ADAPTATION]
Communication: {adapt.get('verbosity', 'concise')}, {'humor enabled' if adapt.get('humor') else 'no humor'}
Voice tone: {adapt.get('voice_tone', 'casual')}
Emoji: {'allowed' if adapt.get('emoji') else 'none'}
Patience: {adapt.get('patience', 5)}/10
"""
    except Exception:
        kyu_section = ""
    system_text = SYSTEM_INSTRUCTION + kyu_section

    # Append compact user memory from imported profile
    try:
        from friday.memory_import import build_user_memory_context
        user_memory = build_user_memory_context(max_chars=3000)
        if user_memory:
            system_text += "\n\n" + user_memory
    except Exception:
        pass

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
            parts=[types.Part(text=system_text)]
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
                        from friday.tools import get_active_window
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
    """Stream screen captures as video frames to Gemini Live API (~1 FPS).
    Official pattern: separate background task, send_realtime_input(video=Blob).
    The model sees these automatically — no see_screen() call needed for basic awareness.
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
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    except Exception:
        pass


def _capture_screen_frame() -> bytes | None:
    """Capture a single screen frame as JPEG bytes (720p for better vision)."""
    try:
        from PIL import ImageGrab
        import io
        img = ImageGrab.grab()
        img.thumbnail((1280, 720), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
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
async def audio_worker(recorder, session, audio_ready, porcupine, winsound, interaction_event=None):
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
            if interaction_event is not None and not interaction_event.is_set():
                interaction_event.set()
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
        from friday.tools import opencli_init_bridge
        opencli_init_bridge()
        console.print("[dim]OpenCLI bridge ready[/]")
    except Exception:
        pass

    try:
        from friday.dreaming import start_dreaming_if_idle
        start_dreaming_if_idle()
        console.print("[dim]Dreaming system started[/]")
    except Exception:
        pass

    try:
        from friday.scheduler import scheduler_tool
        scheduler_tool("start")
        console.print("[dim]Scheduler started[/]")
    except Exception:
        pass

    try:
        from friday.reflection import start_reflection_on_boot
        start_reflection_on_boot()
        console.print("[dim]Reflection system initialized[/]")
    except Exception:
        pass

    try:
        from friday.monitor import start_monitor_on_boot
        start_monitor_on_boot()
        console.print("[dim]Proactive monitor started[/]")
    except Exception:
        pass

    try:
        from friday.episodic import record, get_current_session
        sid = get_current_session()
        record(session_id=sid, speaker="friday",
               content="[SESSION_START] Friday booted and ready.",
               tool_name="system")
        console.print(f"[dim]Episodic archive ready (session {sid[:8]}...)[/]")
    except Exception:
        pass

    try:
        from friday.skills import start_curator_on_boot
        start_curator_on_boot()
        console.print("[dim]Skill curator initialized[/]")
    except Exception:
        pass

    try:
        from friday.crash_watcher import start_watcher
        start_watcher()
        console.print("[dim]Crash watcher started[/]")
    except Exception:
        pass

    # Start Proactive PR Manager (silent — no autostart polling, just ready)
    try:
        from friday.pr_manager import pr_manager_tool as _pmt
        _pmt("add_repo", repo="hackers-reality/friday")
        console.print("[dim]PR manager ready (watching hackers-reality/friday)[/]")
    except Exception:
        pass

    # Load context files
    context_content = ""
    try:
        from friday.context import load_context_files
        context_content = load_context_files()
        if context_content:
            console.print(f"[dim]Context files loaded ({len(context_content)}b)[/]")
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

                    # Give protector access to speak through Live audio
                    try:
                        from friday.protector import set_live_session
                        set_live_session(session, asyncio.get_running_loop())
                    except Exception:
                        pass

                    greeting_done = asyncio.Event()
                    audio_ready = asyncio.Event()
                    is_greeting = last_session_was_greeting

                    shown_input = ""
                    follow_up_mode = False
                    first_interaction_event = asyncio.Event()
                    morning_briefing_dispatched = False

                    # Start audio playback thread
                    _start_audio_playback(pa)

                    # ── Memory context injection (shared by text + audio) ──
                    _last_mem_inject_time = 0.0
                    _injected_mem_signatures: set = set()
                    _MEM_INJECT_COOLDOWN = 30.0

                    async def _inject_memory_context(user_text: str) -> None:
                        nonlocal _last_mem_inject_time
                        if len(user_text.strip()) < 5:
                            return
                        now = __import__("time").time()
                        if now - _last_mem_inject_time < _MEM_INJECT_COOLDOWN:
                            return
                        try:
                            from friday.memory_context import build_relevant_memory_context
                            ctx = build_relevant_memory_context(user_text.strip(), max_chars=2000)
                            if not ctx:
                                return
                            sig = ctx[:60]
                            if sig in _injected_mem_signatures:
                                return
                            _injected_mem_signatures.add(sig)
                            await session.send_realtime_input(text=f"[RELEVANT MEMORY CONTEXT]\n{ctx}")
                            await asyncio.sleep(0.2)
                            _last_mem_inject_time = now
                        except Exception:
                            pass

                    async def _maybe_deliver_pending_morning_briefing() -> None:
                        nonlocal morning_briefing_dispatched
                        if morning_briefing_dispatched:
                            return
                        try:
                            from friday.morning_briefing import (
                                get_pending_briefing_for_delivery,
                                mark_briefing_delivered,
                            )
                            pending = get_pending_briefing_for_delivery(min_hour=8)
                            if not pending:
                                return
                            brief = str(pending.get("briefing", "")).strip()
                            if not brief:
                                return
                            morning_briefing_dispatched = True
                            mark_briefing_delivered()
                            await session.send_realtime_input(
                                text=(
                                    "Deliver this as today's proactive morning YouTube briefing in a concise spoken style "
                                    "before handling other requests.\n\n"
                                    f"{brief}"
                                )
                            )
                        except Exception:
                            pass

                    async def _first_interaction_briefing_watcher() -> None:
                        try:
                            await first_interaction_event.wait()
                            await _maybe_deliver_pending_morning_briefing()
                        except asyncio.CancelledError:
                            raise
                        except Exception:
                            pass

                    # RECEIVE LOOP
                    async def receive_loop():
                        nonlocal is_greeting, shown_input, resume_handle, follow_up_mode
                        thinking_parts = []
                        thinking_shown = False
                        last_transcript = ""
                        displayed_transcript = ""
                        last_displayed_input = ""

                        try:
                            while True:
                                async for response in session.receive():
                                    if response.go_away is not None:
                                        console.print(
                                            f"\n[bold yellow][SYSTEM] Session ending (GoAway), resuming with saved handle...[/]"
                                        )
                                        return  # Exit cleanly — resume_handle already saved

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
                                                if not first_interaction_event.is_set():
                                                    first_interaction_event.set()
                                                chat.add_user_message(txt)
                                                # Fire-and-forget memory context injection for audio
                                                asyncio.create_task(_inject_memory_context(txt))

                                        # Model turn - audio + thoughts
                                        if sc.model_turn:
                                            _model_turn_done.clear()
                                            for part in sc.model_turn.parts:
                                                if part.inline_data:
                                                    _audio_playback_queue.put(part.inline_data.data)
                                                    if not hasattr(_audio_playback_queue, '_debug_printed'):
                                                        _audio_playback_queue._debug_printed = True
                                                        mt = getattr(part.inline_data, 'mime_type', 'unknown')
                                                        console.print(f"[dim][AUDIO] mime={mt} size={len(part.inline_data.data)}b[/]")
                                                if part.thought and part.text:
                                                    thinking_parts.append(part.text)
                                            # Show thinking IMMEDIATELY (before speech transcription)
                                            if thinking_parts and not thinking_shown:
                                                chat.add_thought("\n".join(thinking_parts))
                                                thinking_shown = True

                                        # Output transcription - show progressively
                                        if sc.output_transcription and sc.output_transcription.text:
                                            new_text = sc.output_transcription.text.strip()
                                            if new_text and new_text != displayed_transcript:
                                                if not displayed_transcript:
                                                    console.print(f"\n[bold cyan]---Friday---[/]")
                                                if new_text.startswith(displayed_transcript):
                                                    delta = new_text[len(displayed_transcript):]
                                                    if delta:
                                                        console.print(f"  {delta}", end="")
                                                else:
                                                    console.print(f"\r  {new_text}", end="")
                                                displayed_transcript = new_text
                                            last_transcript = new_text

                                        # Turn complete
                                        if sc.turn_complete:
                                            _model_turn_done.set()  # No more audio chunks coming
                                            thinking_parts = []
                                            thinking_shown = False

                                            final_text = last_transcript.strip()
                                            if final_text:
                                                console.print()
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
                                            thinking_shown = False
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
                                                types.FunctionResponse(name=name, id=fc.id, response=result)
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

                        if context_content:
                            greet += f"\n\nProject context:\n{context_content[:1500]}"

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
                        audio_worker(recorder, session, audio_ready, porcupine, winsound, first_interaction_event)
                    )
                    briefing_task = asyncio.create_task(_first_interaction_briefing_watcher())
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
                            text = text.strip()
                            if text:
                                if not first_interaction_event.is_set():
                                    first_interaction_event.set()
                                await _inject_memory_context(text)
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
                        briefing_task.cancel()
                        reader_task.cancel()
                        for t in [receive_task, audio_task, bg_monitor_task, video_task, ka_task, briefing_task, reader_task]:
                            try:
                                await asyncio.wait_for(asyncio.shield(t), timeout=2.0)
                            except (asyncio.CancelledError, asyncio.TimeoutError):
                                pass

            except KeyboardInterrupt:
                console.print("\n[bold cyan]Neural link severed. Goodbye, Boss.[/]")
                break
            except Exception as e:
                reconnect_attempts += 1
                console.print(f"[red]Link error:[/] {e}")
                # Clear protector's session reference so it doesn't use stale session
                try:
                    from friday.protector import set_live_session
                    set_live_session(None, None)
                except Exception:
                    pass
                # Only clear resume_handle on real errors, NOT clean GoAway
                # GoAway = server-initiated clean close, resume_handle is valid
                err_str = str(e)
                if "1008" not in err_str and "GoAway" not in err_str:
                    console.print("[dim]Clearing resume handle (non-GoAway error). Reconnecting fresh...[/]")
                    resume_handle = None
                else:
                    console.print("[dim]GoAway — preserving resume_handle for session resumption.[/]")
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
