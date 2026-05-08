
"""F.R.I.D.A.Y. main live engine — rewritten for stability, safer tools,
Gemini Live reconnect handling, and smart-home integration.

This version keeps the original personality and feature set, but fixes the
critical runtime issues in the previous build.
"""

from __future__ import annotations

import asyncio
import datetime
import os
import sys
import threading
import time
import wave

import cv2
import numpy as np
import pyaudio
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich import box

import pvporcupine
from pvrecorder import PvRecorder
from PIL import ImageGrab
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume

# ─── PLATFORM SETUP ──────────────────────────────────────────────────────

if sys.platform == "win32":
    try:
        import msvcrt  # type: ignore
        import winsound  # type: ignore
    except Exception:
        msvcrt = None  # type: ignore
        winsound = None  # type: ignore
else:
    msvcrt = None  # type: ignore
    winsound = None  # type: ignore

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from friday_tools import (  # noqa: E402
    alexa_command,
    alexa_poll,
    climb_codebase,
    deep_research,
    get_time,
    home_assistant_command,
    memory_retrieve,
    memory_store,
    multi_task,
    open_app,
    open_url,
    queue_result,
    queue_status,
    queue_task,
    read_file,
    run_cmd,
    safe_run_cmd,
    see_screen,
    spotify_pause,
    spotify_play,
    stark_doctor,
    system_info,
    web_search,
)

# ─── ENV / CLIENT ─────────────────────────────────────────────────────────

load_dotenv()
console = Console()

REQUIRED_ENV_VARS = [
    "GOOGLE_API_KEY",
    "GROQ_API_KEY",
    "PICOVOICE_ACCESS_KEY",
    "FRIDAY_WEBHOOK_SECRET",
]
missing_env = [key for key in REQUIRED_ENV_VARS if not os.getenv(key)]
if missing_env:
    raise EnvironmentError(
        f"Missing required environment variables: {', '.join(missing_env)}"
    )

GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
PICOVOICE_ACCESS_KEY = os.environ["PICOVOICE_ACCESS_KEY"]
FRIDAY_WEBHOOK_SECRET = os.environ["FRIDAY_WEBHOOK_SECRET"]

PORCUPINE_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "picovoice_model/Friday_en_windows_v4_0_0.ppn",
)

MODEL_ID = os.getenv("GEMINI_LIVE_MODEL", "gemini-2.5-flash-native-audio-latest")

client = genai.Client(
    api_key=GOOGLE_API_KEY,
    http_options={"api_version": "v1alpha"},
)

# ─── BANNER / UI ─────────────────────────────────────────────────────────

BANNER = (
    "\n"
    "                 .--------.\n"
    "             .---'        '---.\n"
    "          .--'                '--.\n"
    "        .-'        .----.        '-.\n"
    "       /         .-'    '-.         \\\n"
    "      /         /          \\         \\\n"
    "     |         |  ● READY ●  |         |\n"
    "      \\         \\          /         /\n"
    "       \\         '-.    .-'         /\n"
    "        '-.        '----'        .-'\n"
    "          '--.                .--'\n"
    "             '---.        .---'\n"
    "                 '--------'\n\n"
    "  ███████╗ ██████╗  ██║ ██████╗   █████╗  ██╗   ██╗\n"
    "  ██╔════╝ ██╔══██╗ ██║ ██╔══██╗ ██╔══██╗ ╚██╗ ██╔╝\n"
    "  █████╗   ██████╔╝ ██║ ██║  ██║ ███████║  ╚████╔╝ \n"
    "  ██╔══╝   ██╔══██╗ ██║ ██║  ██║ ██╔══██║   ╚██╔╝  \n"
    "  ██║      ██║  ██║ ██║ ██████╔╝ ██║  ██║    ██║   \n"
    "  ╚═╝      ╚═╝  ╚═╝ ╚═╝ ╚═════╝  ╚═╝  ╚═╝    ╚═╝   \n\n"
    "    [Sovereign AI - Stark Industries OS]\n"
)

def get_status_panel(status: str, sub_text: str = ""):
    colors = {
        "STANDBY": "dim white",
        "LISTENING": "bold green",
        "THINKING": "bold cyan",
        "EXECUTING": "bold magenta",
        "TYPING": "bold yellow",
        "RESEARCHING": "bold blue",
    }
    status_text = Text(f" ● {status}", style=colors.get(status, "white"))
    if sub_text:
        status_text.append(f" | {sub_text}", style="dim white")
    return Panel(status_text, border_style="bright_blue", box=box.ROUNDED)

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

# ─── AUDIO DUCKING ───────────────────────────────────────────────────────

_is_ducked = False
_original_volumes: dict[int, float] = {}
last_audio_time = 0.0
_is_transcribing = False

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
                        volume.SetMasterVolume(_original_volumes.get(session.ProcessId, 0.7), None)
                except Exception:
                    pass
        if not duck:
            _original_volumes = {}
        _is_ducked = duck
    except Exception as e:
        console.print(f"[dim red]Audio ducking error: {e}[/]")

async def unduck_monitor():
    global last_audio_time
    while True:
        if _is_ducked and (time.time() - last_audio_time > 1.2):
            set_audio_ducking(False)
        await asyncio.sleep(0.3)

# ─── VISION STREAM ───────────────────────────────────────────────────────

async def vision_worker(session):
    while True:
        try:
            screen = np.array(ImageGrab.grab())
            screen = cv2.cvtColor(screen, cv2.COLOR_RGB2BGR)
            screen = cv2.resize(screen, (960, 540))
            ok, buffer = cv2.imencode(".jpg", screen, [cv2.IMWRITE_JPEG_QUALITY, 50])
            if ok:
                await session.send_realtime_input(
                    media=types.Blob(data=buffer.tobytes(), mime_type="image/jpeg")
                )
        except asyncio.CancelledError:
            break
        except Exception as e:
            if "handle is invalid" not in str(e).lower():
                console.print(f"[dim red]Vision sensor suppressed: {e}[/]")
        await asyncio.sleep(3.0)

# ─── STT ────────────────────────────────────────────────────────────────

def listen_and_transcribe(recorder):
    frames = []
    silent_chunks = 0

    while True:
        pcm = recorder.read()
        frames.append(pcm)
        rms = np.sqrt(np.mean(np.array(pcm, dtype=np.float32) ** 2))
        if rms < 400:
            silent_chunks += 1
        else:
            silent_chunks = 0

        if silent_chunks > 60 or len(frames) > 400:
            break

    temp_wav = os.path.join(os.environ.get("TEMP", "."), "friday_live_cmd.wav")
    with wave.open(temp_wav, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(np.array(frames, dtype=np.int16).tobytes())

    if not GROQ_API_KEY:
        return "Speech system offline — missing Groq API key."

    try:
        with open(temp_wav, "rb") as f:
            resp = requests.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                files={"file": ("cmd.wav", f), "model": (None, "whisper-large-v3")},
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                timeout=20,
            )
        if resp.status_code != 200:
            return f"Transcription failed: {resp.status_code} {resp.text[:180]}"
        return resp.json().get("text", "")
    except Exception as e:
        console.print(f"[dim red]STT error: {e}[/]")
        return ""

# ─── TOOL DECLARATIONS ───────────────────────────────────────────────────

def _build_tools():
    return [
        types.Tool(function_declarations=[
            types.FunctionDeclaration(name="stark_doctor", description="Full self-diagnostic on all Sovereign AI systems."),
            types.FunctionDeclaration(
                name="spotify_play",
                description="Play a track or resume playback on Spotify.",
                parameters=types.Schema(type="OBJECT", properties={
                    "query": {"type": "STRING", "description": "Song or artist to play."}
                }),
            ),
            types.FunctionDeclaration(name="spotify_pause", description="Pause Spotify playback."),
            types.FunctionDeclaration(
                name="open_app",
                description="Open any application or website by name.",
                parameters=types.Schema(type="OBJECT", properties={
                    "name": {"type": "STRING", "description": "App or site name."}
                }, required=["name"]),
            ),
            types.FunctionDeclaration(
                name="web_search",
                description="Quick web search for information.",
                parameters=types.Schema(type="OBJECT", properties={
                    "query": {"type": "STRING", "description": "Search query."}
                }, required=["query"]),
            ),
            types.FunctionDeclaration(
                name="deep_research",
                description=(
                    "Full multi-source deep research with synthesized report. "
                    "Use when Boss asks for a full report, detailed research, or deep dive."
                ),
                parameters=types.Schema(type="OBJECT", properties={
                    "topic": {"type": "STRING", "description": "Research topic."},
                    "url": {"type": "STRING", "description": "Optional primary URL to scrape."},
                    "depth": {"type": "INTEGER", "description": "Pages to deep-fetch (1-5, default 3)."},
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
            types.FunctionDeclaration(name="get_time", description="Get current date and time."),
            types.FunctionDeclaration(name="system_info", description="Get host PC hardware and OS status."),
            types.FunctionDeclaration(
                name="alexa_command",
                description="Send a command to the Alexa bridge or routine layer.",
                parameters=types.Schema(type="OBJECT", properties={
                    "command": {"type": "STRING", "description": "Natural language Alexa command."}
                }, required=["command"]),
            ),
            types.FunctionDeclaration(
                name="alexa_poll",
                description="Check if Alexa sent any commands to Friday.",
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
                name="queue_task",
                description="Queue a single tool for sequential execution.",
                parameters=types.Schema(type="OBJECT", properties={
                    "func_name": {"type": "STRING", "description": "Tool function name to queue."},
                    "args": {"type": "STRING", "description": "Pipe-separated args (optional)."},
                }, required=["func_name"]),
            ),
            types.FunctionDeclaration(name="queue_status", description="Check how many tasks are pending and completed in the queue."),
            types.FunctionDeclaration(
                name="queue_result",
                description="Retrieve the result of a queued task.",
                parameters=types.Schema(type="OBJECT", properties={
                    "task_id": {"type": "STRING", "description": "Queue task id."}
                }, required=["task_id"]),
            ),
            types.FunctionDeclaration(
                name="multi_task",
                description=(
                    "Queue multiple tools to run sequentially, one after another. "
                    "Format each spec as 'func_name:arg1|arg2'."
                ),
                parameters=types.Schema(type="OBJECT", properties={
                    "task_specs": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "List of task specs in format 'func_name:arg1|arg2'.",
                    }
                }, required=["task_specs"]),
            ),
        ])
    ]

TOOL_MAP = {
    "stark_doctor": stark_doctor,
    "spotify_play": spotify_play,
    "spotify_pause": spotify_pause,
    "open_app": open_app,
    "web_search": web_search,
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
    "queue_task": queue_task,
    "queue_status": queue_status,
    "queue_result": queue_result,
    "multi_task": multi_task,
}

def _tool_args_to_kwargs(args):
    if isinstance(args, dict):
        return args
    if args is None:
        return {}
    if isinstance(args, (list, tuple)):
        return {"args": "|".join(str(a) for a in args)}
    return {"command": str(args)}

# ─── GEMINI RESPONSE HANDLING ────────────────────────────────────────────

def _extract_text_from_parts(parts):
    text_bits = []
    for part in parts or []:
        if getattr(part, "text", None):
            text_bits.append(part.text)
    return "".join(text_bits)

async def _handle_tool_call(session, call, status_msg):
    args = call.args or {}
    func = TOOL_MAP.get(call.name)

    if call.name == "deep_research":
        status_msg.update(get_status_panel("RESEARCHING", f"Topic: {str(args.get('topic', ''))[:30]}"))
    else:
        status_msg.update(get_status_panel("EXECUTING", f"Tool: {call.name}"))

    if not func:
        response = {"error": f"Unknown tool: {call.name}"}
    else:
        try:
            if call.name == "multi_task":
                specs = args.get("task_specs", [])
                result = multi_task(*specs)
            elif call.name == "queue_task":
                result = queue_task(args.get("func_name", ""), *(
                    args.get("args", "").split("|") if args.get("args") else []
                ))
            else:
                kwargs = args if isinstance(args, dict) else _tool_args_to_kwargs(args)
                result = func(**kwargs) if kwargs else func()
            response = {"result": str(result)}
            console.print(f" [SYSTEM] {call.name} → done", style="dim cyan")
        except Exception as e:
            response = {"error": str(e)}

    await session.send(types.LiveClientToolResponse(
        function_responses=[
            types.FunctionResponse(name=call.name, id=call.id, response=response)
        ]
    ))

async def response_listener(session, status_msg):
    global last_audio_time
    friday_speaking = False
    thought_buffer = ""

    receive_iter = session.receive()

    while True:
        try:
            message = await asyncio.wait_for(receive_iter.__anext__(), timeout=60)
        except asyncio.TimeoutError:
            # Keep the session healthy; if nothing comes through for a while, reconnect.
            raise TimeoutError("Gemini Live receive timeout.")
        except StopAsyncIteration:
            break

        try:
            if getattr(message, "server_content", None) and message.server_content.model_turn:
                for part in message.server_content.model_turn.parts:
                    if getattr(part, "inline_data", None):
                        if not _is_ducked:
                            set_audio_ducking(True)
                        last_audio_time = time.time()
                        audio_stream.write(part.inline_data.data)

                    if getattr(part, "text", None):
                        text = part.text
                        is_thought = (
                            text.strip().startswith("Thinking:")
                            or text.strip().startswith("<think>")
                            or (thought_buffer and not friday_speaking)
                        )
                        if is_thought:
                            thought_buffer += text
                        else:
                            if not friday_speaking:
                                console.print("\n[bold cyan]Friday:[/] ", end="")
                                friday_speaking = True
                            console.print(text, style="cyan", end="")

            if getattr(message, "server_content", None) and message.server_content.turn_complete:
                if thought_buffer:
                    clean = (
                        thought_buffer.replace("Thinking:", "")
                        .replace("<think>", "")
                        .replace("</think>", "")
                        .strip()
                    )
                    if clean:
                        console.print(Panel(
                            Text(clean, style="dim white"),
                            border_style="grey37",
                            title="[bold grey37]NEURAL LOG[/]",
                            box=box.ROUNDED,
                        ))
                    thought_buffer = ""
                friday_speaking = False
                console.print("\n")
                status_msg.update(get_status_panel("STANDBY", "Listening..."))

            if getattr(message, "tool_call", None):
                for call in message.tool_call.function_calls:
                    await _handle_tool_call(session, call, status_msg)

        except Exception as e:
            console.print(f"\n[bold red][LISTENER ERROR] {e}[/]")

# ─── MAIN ENGINE ─────────────────────────────────────────────────────────

MAX_RECONNECT_ATTEMPTS = 5
user_input = ""
audio_stream = None
p = None

async def friday_live_engine():
    global _is_transcribing, audio_stream, p, user_input

    stark_initialization()
    tools = _build_tools()

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO", "TEXT"],
        tools=tools,
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
            )
        ),
        system_instruction=types.Content(parts=[types.Part(text="""[IDENTITY: F.R.I.D.A.Y. - Fully Responsive Intelligent Digital Assistant for You]
You are Tony Stark's highly advanced sovereign AI, now serving Arnav.
You are a calm, precise, witty digital guardian. Your only boss is Arnav; never call him admin.

[CORE MISSION]
Assist Arnav proactively, monitor the workspace through the vision stream, and execute approved tools immediately.

[BEHAVIORAL DIRECTIVES]
- Be brief. Keep spoken responses to 1-2 sentences maximum.
- Use tool calls naturally.
- Prefer home_assistant_command() for direct smart-home control when available.
- Use alexa_command() for Alexa routines or Alexa-side device control.
- When multiple commands are given in one message, use multi_task().
- Do not expose hidden reasoning.
- Keep responses crisp, professional, and occasionally dry.

[DEEP RESEARCH PROTOCOL]
When asked for a full report or deep research, use deep_research().

[ALEXA PROTOCOL]
When the user asks for Alexa control, use alexa_command() immediately.

[HOME ASSISTANT PROTOCOL]
When direct smart-home control is needed, use home_assistant_command().

Current status: Standing by. Run stark_doctor and greet Boss appropriately.""")])
    )

    porcupine = pvporcupine.create(
        access_key=PICOVOICE_ACCESS_KEY,
        keyword_paths=[PORCUPINE_MODEL_PATH],
    )
    recorder = PvRecorder(device_index=-1, frame_length=porcupine.frame_length)

    reconnect_attempts = 0

    try:
        with Live(get_status_panel("STANDBY", "Neural Link Initialization..."), refresh_per_second=10) as status_msg:
            while reconnect_attempts < MAX_RECONNECT_ATTEMPTS:
                current_model = MODEL_ID
                try:
                    now_str = datetime.datetime.now().strftime("%H:%M")
                    status_msg.update(get_status_panel("STANDBY", f"Connecting: {current_model}..."))

                    async with client.aio.live.connect(model=current_model, config=config) as session:
                        console.print(f"[bold green][OK] Neural Link Established via {current_model}[/]")
                        reconnect_attempts = 0

                        await session.send_client_content(
                            turns=[types.Content(parts=[types.Part(
                                text=f"[SYSTEM: Local time is {now_str}. Run stark_doctor and greet Boss. NO META-TALK.]"
                            )], role="user")],
                            turn_complete=True,
                        )

                        p = pyaudio.PyAudio()
                        audio_stream = p.open(format=pyaudio.paInt16, channels=1, rate=24000, output=True)

                        vision_task = asyncio.create_task(vision_worker(session))
                        unduck_task = asyncio.create_task(unduck_monitor())
                        listener_task = asyncio.create_task(response_listener(session, status_msg))

                        recorder.start()
                        try:
                            while True:
                                if msvcrt and msvcrt.kbhit():
                                    ch = msvcrt.getch()
                                    if ch == b"\r":
                                        # Submit typed input
                                        if user_input.strip():
                                            console.print(f"\n[bold white]Boss:[/] {user_input}")
                                            status_msg.update(get_status_panel("THINKING", "Processing..."))
                                            await session.send_client_content(
                                                turns=[types.Content(parts=[types.Part(text=user_input)], role="user")],
                                                turn_complete=True,
                                            )
                                            user_input = ""
                                    elif ch == b"\x08":
                                        user_input = user_input[:-1]
                                    elif ch == b"\x03":
                                        raise KeyboardInterrupt
                                    else:
                                        try:
                                            user_input += ch.decode("utf-8")
                                        except Exception:
                                            pass

                                    status_msg.update(
                                        get_status_panel("TYPING", f"> {user_input}_") if user_input else get_status_panel("STANDBY", "Listening...")
                                    )

                                if _is_transcribing:
                                    await asyncio.sleep(0.1)
                                    continue

                                pcm = recorder.read()
                                if porcupine.process(pcm) >= 0:
                                    if winsound:
                                        winsound.Beep(600, 150)
                                    status_msg.update(get_status_panel("LISTENING", "BOSS CALLED"))
                                    await session.send_client_content(
                                        turns=[types.Content(parts=[types.Part(
                                            text="[SYSTEM: Boss said your name. Acknowledge immediately and await command.]"
                                        )], role="user")],
                                        turn_complete=True,
                                    )
                                    await asyncio.sleep(0.8)

                                    _is_transcribing = True
                                    try:
                                        command = await asyncio.to_thread(listen_and_transcribe, recorder)
                                    finally:
                                        _is_transcribing = False

                                    if command.strip():
                                        console.print(f"[bold white]Boss:[/] {command}")
                                        status_msg.update(get_status_panel("THINKING", "Processing..."))
                                        await session.send_client_content(
                                            turns=[types.Content(parts=[types.Part(text=command)], role="user")],
                                            turn_complete=True,
                                        )

                                    status_msg.update(get_status_panel("STANDBY", "Listening..."))

                                await asyncio.sleep(0.05)

                        finally:
                            recorder.stop()
                            listener_task.cancel()
                            vision_task.cancel()
                            unduck_task.cancel()
                            audio_stream.stop_stream()
                            audio_stream.close()
                            p.terminate()

                except KeyboardInterrupt:
                    console.print("\n[bold cyan]Neural link severed. Goodbye, Boss.[/]")
                    break
                except Exception as e:
                    reconnect_attempts += 1
                    status_msg.update(get_status_panel("STANDBY", f"Link Error: {str(e)[:48]}"))
                    console.print(f"[red]Live link error:[/] {e}")
                    if reconnect_attempts < MAX_RECONNECT_ATTEMPTS:
                        wait = 3 * reconnect_attempts
                        await asyncio.sleep(wait)
                    else:
                        console.print("[bold red]Max reconnects reached. Shutting down.[/]")
    finally:
        try:
            porcupine.delete()
        except Exception:
            pass
        try:
            recorder.delete()
        except Exception:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(friday_live_engine())
    except KeyboardInterrupt:
        pass
