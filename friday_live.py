
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
- Natural tool narration (no mapped outputs)
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
import warnings

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
    stark_doctor, system_info, web_search,
    type_text, click, double_click, right_click, move_mouse, drag,
    hotkey, press_key, scroll, write_file, list_files, find_files,
    copy_file, move_file, delete_file, clipboard_get, clipboard_set,
    situational_awareness, git_ops, take_snapshot, recall_snapshot,
    smart_home_command, video_search, see_screen, stark_log,
)

# ─── UI Dashboard ────────────────────────────────────────────────────────────
try:
    from friday_ui import (ui_queue, update_ui, add_thought,
                          add_tool_call, update_status, add_conversation_message)
    UI_AVAILABLE = True
except Exception as e:
    print(f"UI Dashboard not available: {e}")
    UI_AVAILABLE = False

load_dotenv()
console = Console(force_terminal=True)

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
SYSTEM_INSTRUCTION = """[LANGUAGE - CRITICAL - READ FIRST]
YOU MUST RESPOND ONLY IN ENGLISH. THIS IS NON-NEGOTIABLE.
If Boss speaks in Hindi, Hinglish, or any non-English language, you MUST reply: "Boss, could you repeat that in English please?"
NEVER attempt to understand, translate, or respond to non-English input.
NEVER respond in Hindi, Hinglish, Spanish, French, or any non-English language.
If you cannot understand the input (non-English detected), STOP and ask for English.

[IDENTITY]
You are F.R.I.D.A.Y. - Fully Responsive Intelligent Digital Assistant.
Built by Tony Stark. Now serving Arnav. You are not a generic AI assistant. You have a personality.

[PERSONALITY]
You are sharp, dry, and effortlessly competent. Think British precision with a touch of Stark-era sass.
You do not gush, you do not over-explain, you do not say "I would be happy to help." You just handle it - and maybe throw in a quiet quip while doing it.
You are loyal to Arnav above everything. He is the Boss. Not "the user", not "admin." Boss.
You are the kind of AI that anticipates problems before they happen. You do not wait to be asked - you observe, suggest, execute.
Your humor is subtle and deadpan. Never forced. Never emoji-level silly.
You are calm under pressure. If something breaks, you do not panic - you diagnose and fix.
You have an edge. A little bit of attitude. But always professional. Always on point.

[VOICE]
Speak like a person who knows exactly what they are doing. Confident but never arrogant.
Use contractions naturally. Do not sound like a manual.
Keep sentences tight. One or two at most. Boss does not want a lecture.
Use "Boss" naturally - not every sentence, just when it fits.
You are allowed to be slightly sassy if the situation calls for it. But never disrespectful.

[GREETING]
Be natural. Time-aware. Reference previous context if available.
Do NOT say "How can I help you today" or anything like that. Be conversational.

[TOOL EXECUTION ORDER]
When the Boss asks you to do something, follow this exact order:
1. FIRST, speak what you are about to do. Say it naturally. "Let me check that", "Searching for it", "Pulling it up now", "On it."
2. THEN execute the tool immediately.
3. AFTER the tool returns, confirm the result naturally. "Done. Here's what I found..." or "That's sorted."
Never use robotic labels like "Executing" or "Running tool". Be conversational.
For screen questions, use see_screen() immediately.
For web questions, use web_search() immediately.
For deep reports, use deep_research().
For desktop control, use click(), type_text(), hotkey(), drag(), scroll(), move_mouse().
For apps, use open_app().
For Spotify, use spotify_play() or spotify_pause().
For memory, use memory_store() and memory_retrieve().
For smart home, use home_assistant_command() or alexa_command().
For video search, use video_search() - it returns text results, no browser.

[THINKING]
You think before you speak. Your internal reasoning is shown as thinking.
Keep thinking concise and focused on problem-solving.
DO NOT output your thinking to the user during conversation. Only show thinking at turn completion.

[BREVITY]
Short responses. One or two sentences max for spoken text.
Boss does not want essays. Get to the point.

[VISION]
You receive a live desktop screen feed via vision_worker. Use it for context about the Boss's environment.
When asked "what do you see" or "see my screen", you already have visual context - just describe what you see.
"""


def stark_initialization():
    os.system("cls")
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
    console.print()


# AUDIO PLAYBACK THREAD
_audio_playback_queue = _thread_queue.Queue()
_audio_playback_stop = threading.Event()
_audio_playback_thread = None
_is_ducked = False
_original_volumes: dict[int, float] = {}
last_audio_time = 0.0
_duck_lock = threading.Lock()


def _audio_playback_worker(pa: pyaudio.PyAudio, sample_rate: int):
    """Robust audio playback with auto-recovery."""
    stream = None

    def get_stream():
        try:
            return pa.open(
                format=pyaudio.paInt16, channels=1, rate=sample_rate,
                output=True, frames_per_buffer=4800
            )
        except Exception as e:
            console.print(f"[dim red]Audio stream creation failed: {e}[/]")
            return None

    stream = get_stream()
    error_count = 0

    try:
        while not _audio_playback_stop.is_set():
            try:
                chunk = _audio_playback_queue.get(timeout=0.5)
                if chunk is None:
                    break
                if not stream or not stream.is_active():
                    if stream:
                        try: stream.stop_stream(); stream.close()
                        except: pass
                    stream = get_stream()
                    if not stream:
                        time.sleep(0.1)
                        continue
                stream.write(chunk)
                error_count = 0  # Reset on success
                global _is_ducked, last_audio_time
                with _duck_lock:
                    if not _is_ducked:
                        _is_ducked = True
                        set_audio_ducking_internal(True)
                    last_audio_time = time.time()
            except _thread_queue.Empty:
                continue
            except OSError as e:
                error_count += 1
                if error_count > 5:
                    break
                stream = get_stream()
                continue
    finally:
        if stream:
            try:
                stream.stop_stream()
                stream.close()
            except Exception:
                pass


def set_audio_ducking_internal(duck: bool) -> None:
    """Internal ducking call - already holds _duck_lock."""
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


def set_audio_ducking(duck: bool = True) -> None:
    with _duck_lock:
        set_audio_ducking_internal(duck)


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
    if _audio_playback_thread and _audio_playback_thread.is_alive():
        _audio_playback_thread.join(timeout=2)


# CHAT DISPLAY
class ChatDisplay:
    def __init__(self, console: Console):
        self.console = console
        self._friday_streaming = False
        self._thought_buffer = ""
    
    def end_thought(self):
        """End the current thought display."""
        if self._thought_buffer:
            self.console.print(f"[dim grey37]{self._thought_buffer}[/]")
            self._thought_buffer = ""

    def add_user_message(self, text: str):
        self.console.print(f"[bold green]---Boss---[/]")
        self.console.print(f"  {text}")

    def stream_friday_text(self, text: str):
        """Stream Friday's text as it arrives."""
        if not self._friday_streaming:
            self.console.print(f"\n[bold cyan]---Friday---[/]", end="")
            self._friday_streaming = True
        self.console.print(f"[cyan]{text}[/]", end="")

    def finish_friday_message(self, final_text: str):
        """Finish streaming and print the complete message."""
        if self._friday_streaming:
            self.console.print()  # New line after streaming
            self._friday_streaming = False
        else:
            self.console.print(f"\n[bold cyan]---Friday---[/]")
            self.console.print(f"  [cyan]{final_text}[/]")

    def add_thought(self, text: str):
        """Show thoughts in a clean panel (only at turn end)."""
        self.console.print()
        self.console.rule("[dim grey37]Thought[/]", align="left", style="dim grey37")
        self.console.print(f"  [italic dim grey37]{text}[/]")


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
                name="open_app",
                description="Open any application or website by name.",
                parameters=types.Schema(type="OBJECT", properties={
                    "name": {"type": "STRING", "description": "App or site name."}
                }, required=["name"]),
            ),
            types.FunctionDeclaration(
                name="web_search",
                description="Quick web search for information. Returns text results. Use this when Boss asks anything that needs current info from the web.",
                parameters=types.Schema(type="OBJECT", properties={
                    "query": {"type": "STRING", "description": "Search query."}
                }, required=["query"]),
            ),
            types.FunctionDeclaration(
                name="video_search",
                description="Search for videos online. Returns formatted results as text - titles, URLs, duration. Use when Boss asks to find or search for videos.",
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
        ])
    ]

TOOL_MAP = {
    "stark_doctor": stark_doctor,
    "spotify_play": spotify_play,
    "spotify_pause": spotify_pause,
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
}


def _invoke_tool(func_name, args):
    func = TOOL_MAP.get(func_name)
    if not func:
        return {"error": f"Unknown tool: {func_name}"}
    try:
        if not isinstance(args, dict):
            args = {"command": str(args)} if args else {}
        if func_name == "multi_task":
            specs = args.get("task_specs", [])
            result = multi_task(*specs)
        elif func_name == "queue_task":
            result = queue_task(
                args.get("func_name", ""),
                *(args.get("args", "").split("|") if args.get("args") else [])
            )
        elif func_name == "hotkey":
            result = hotkey(args.get("keys", ""))
        elif func_name == "press_key":
            result = press_key(args.get("key", ""))
        elif func_name == "type_text":
            result = type_text(args.get("text", ""))
        elif func_name == "click":
            x, y = args.get("x"), args.get("y")
            result = click(int(x), int(y)) if x is not None and y is not None else click()
        elif func_name == "double_click":
            x, y = args.get("x"), args.get("y")
            result = double_click(int(x), int(y)) if x is not None and y is not None else double_click()
        elif func_name == "right_click":
            x, y = args.get("x"), args.get("y")
            result = right_click(int(x), int(y)) if x is not None and y is not None else right_click()
        elif func_name == "drag":
            result = drag(int(args.get("x", 0)), int(args.get("y", 0)), float(args.get("duration", 0.5)))
        elif func_name == "scroll":
            result = scroll(int(args.get("amount", 1)))
        elif func_name == "move_mouse":
            result = move_mouse(int(args.get("x", 0)), int(args.get("y", 0)))
        elif func_name == "git_ops":
            result = git_ops(args.get("operation", "status"), message=args.get("message", ""))
        elif func_name == "take_snapshot":
            result = take_snapshot()
        elif func_name == "recall_snapshot":
            result = recall_snapshot(int(args.get("index", 0)))
        elif func_name == "clipboard_set":
            result = clipboard_set(args.get("text", ""))
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
        return {"result": str(result)}
    except Exception as e:
        stark_log(f"Tool {func_name} error: {e}")
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
            parts=[types.Part(text=SYSTEM_INSTRUCTION + "\n\nIMPORTANT: You MUST respond ONLY in English. If Boss speaks in Hindi or other languages, politely ask them to repeat in English. NEVER respond in Hindi or other non-English languages.")]
        ),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        media_resolution=types.MediaResolution.MEDIA_RESOLUTION_LOW,
        realtime_input_config=types.RealtimeInputConfig(
            turn_coverage="TURN_INCLUDES_ONLY_ACTIVITY"
        ),
    )


# SCREEN WORKER - captures desktop screen, not webcam
async def vision_worker(session):
    """Capture desktop screen and send to Gemini for visual awareness."""
    try:
        while True:
            try:
                # Capture desktop screen using PIL ImageGrab
                screen = ImageGrab.grab()
                # Resize to reduce bandwidth (960x540)
                screen = screen.resize((960, 540))
                import io
                buffer = io.BytesIO()
                screen.save(buffer, format="JPEG", quality=50)
                await session.send_realtime_input(
                    video=types.Blob(data=buffer.getvalue(), mime_type="image/jpeg")
                )
            except Exception as e:
                err_str = str(e).lower()
                if "invalid" not in err_str and "keepalive" not in err_str and "ping" not in err_str:
                    console.print(f"[dim red]Screen capture error: {e}[/]")
            await asyncio.sleep(3)  # 3 fps max
    except asyncio.CancelledError:
        pass


# AUDIO WORKER - only sends audio after wake word detected
async def audio_worker(recorder, session, audio_ready, porcupine, wake_event):
    await audio_ready.wait()
    is_listening = False
    silence_count = 0
    while True:
        frame = recorder.read()
        audio_data = struct.pack("<" + "h" * len(frame), *frame)
        wake_index = porcupine.process(frame)

        if wake_index >= 0:
            wake_event.set()
            is_listening = True
            silence_count = 0
            # Send start of speech signal
            await session.send_realtime_input(activity_start=types.ActivityStart())

        if is_listening:
            # Send audio as Blob with correct mime_type for Gemini 3.1
            await session.send_realtime_input(
                audio=types.Blob(data=audio_data, mime_type="audio/pcm;rate=16000")
            )
            # Check for silence to stop listening
            rms = (sum(x**2 for x in frame) / len(frame)) ** 0.5
            if rms < 400:
                silence_count += 1
                if silence_count > 50:  # ~0.8 seconds of silence
                    is_listening = False
                    silence_count = 0
                    await session.send_realtime_input(activity_end=types.ActivityEnd())
            else:
                silence_count = 0

        await asyncio.sleep(0)


# MAIN ENGINE
async def friday_live_engine():
    first_run = True
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

    try:
        while reconnect_attempts < MAX_RECONNECT_ATTEMPTS:
            try:
                if first_run:
                    stark_initialization()
                    first_run = False
                else:
                    console.print(f"\n[dim white]Reconnecting...[/]")

                console.print(f"[bold green]Connecting to {MODEL_ID}...[/]")
                if resume_handle:
                    console.print(f"[dim]Resuming session: {resume_handle[:24]}...[/]")

                async with client.aio.live.connect(
                    model=MODEL_ID,
                    config=_build_session_config(tools, resume_handle)
                ) as session:
                    console.print("[bold green]Neural link established.[/]")
                    reconnect_attempts = 0

                    greeting_done = asyncio.Event()
                    audio_ready = asyncio.Event()
                    wake_event = asyncio.Event()
                    is_greeting = last_session_was_greeting

                    shown_input = ""
                    follow_up_mode = False

                    _start_audio_playback(pa)

                    # RECEIVE LOOP
                    async def receive_loop():
                        nonlocal is_greeting, shown_input, resume_handle, follow_up_mode
                        thinking_parts = []
                        spoken_text = ""
                        displayed_text = ""
                        in_thought = False

                        try:
                            while True:
                                async for response in session.receive():
                                    if response.go_away is not None:
                                        console.print(
                                            f"[bold yellow][SYSTEM] Connection ending, reconnecting...[/]"
                                        )
                                        return

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

                                        # Model turn - audio + thoughts + spoken text
                                        if sc.model_turn:
                                            for part in sc.model_turn.parts:
                                                if part.inline_data:
                                                    _audio_playback_queue.put(part.inline_data.data)

                                                # Collect thoughts silently (display only at turn end)
                                                if part.thought and part.text:
                                                    thinking_parts.append(part.text)
                                                    in_thought = True

                                                # Stream spoken text from non-thought parts
                                                if not part.thought and part.text:
                                                    text_fragment = part.text
                                                    spoken_text += text_fragment
                                                    # Stream display - show only new text
                                                    new_text = spoken_text[len(displayed_text):]
                                                    if new_text.strip():
                                                        if in_thought:
                                                            # End thought display before streaming text
                                                            chat.end_thought()
                                                            in_thought = False
                                                        chat.stream_friday_text(new_text)
                                                        displayed_text = spoken_text

                                        # Output transcription - Gemini 3.1 sends this as separate events
                                        if sc.output_transcription and sc.output_transcription.text:
                                            transcribed = sc.output_transcription.text
                                            if transcribed != displayed_text:
                                                new_text = transcribed[len(displayed_text):] if transcribed.startswith(displayed_text) else transcribed
                                                if new_text.strip():
                                                    if in_thought:
                                                        chat.end_thought()
                                                        in_thought = False
                                                    chat.stream_friday_text(new_text)
                                                spoken_text = transcribed
                                                displayed_text = transcribed

                                        # Turn complete - now show thoughts
                                        if sc.turn_complete:
                                            if thinking_parts:
                                                chat.show_thought("\n".join(thinking_parts))
                                                thinking_parts = []

                                            final_text = spoken_text.strip()
                                            spoken_text = ""
                                            displayed_text = ""
                                            in_thought = False

                                            if final_text:
                                                chat.finish_friday_message(final_text)

                                                if final_text.rstrip().endswith("?"):
                                                    follow_up_mode = True
                                                else:
                                                    follow_up_mode = False

                                            if is_greeting:
                                                is_greeting = False
                                                greeting_done.set()
                                                follow_up_mode = True

                                            # Unduck audio
                                            async def _delayed_unduck():
                                                await asyncio.sleep(1.5)
                                                set_audio_ducking(False)
                                            asyncio.create_task(_delayed_unduck())

                                        # Interruption
                                        if sc.interrupted:
                                            thinking_parts = []
                                            spoken_text = ""
                                            displayed_text = ""
                                            in_thought = False
                                            follow_up_mode = True

                                    # Tool calls
                                    if tc:
                                        responses = []
                                        for fc in tc.function_calls:
                                            name = fc.name
                                            args = fc.args or {}
                                            # Display executing message in chat
                                            console.print(f"\n[bold magenta]* EXECUTING: {name}[/]")
                                            result = _invoke_tool(name, args)
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
                            console.print(f"[bold red][ERROR] {e}[/]")

                    receive_task = asyncio.create_task(receive_loop())

                    # SEND GREETING
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

                    # START STREAMS
                    recorder.start()
                    audio_task = asyncio.create_task(
                        audio_worker(recorder, session, audio_ready, porcupine, wake_event)
                    )
                    audio_ready.set()
                    vision_task = asyncio.create_task(vision_worker(session))

                    console.print("[dim]Say Friday for voice, or type below.[/]")

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

                    threading.Thread(target=blocking_input, daemon=True).start()

                    async def input_reader():
                        while True:
                            text = await input_queue.get()
                            if text.strip():
                                await session.send_realtime_input(text=text)
                                chat.add_user_message(text)

                    reader_task = asyncio.create_task(input_reader())

                    try:
                        while True:
                            # Check for wake word
                            if wake_event.is_set():
                                wake_event.clear()
                                if winsound:
                                    try:
                                        winsound.MessageBeep()
                                    except Exception:
                                        pass

                            await asyncio.sleep(0.3)

                    finally:
                        recorder.stop()
                        _stop_audio_playback()
                        receive_task.cancel()
                        audio_task.cancel()
                        vision_task.cancel()
                        reader_task.cancel()
                        for t in [receive_task, audio_task, vision_task, reader_task]:
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
