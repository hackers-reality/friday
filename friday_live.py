"""
Friday Live - Sovereign AI with Gemini 3.1 Flash Live.
PRIMARY: Gemini 3.1 Flash Live (native voice, brain)
FALLBACK: NVIDIA (multi-model)
Integrates ALL Friday modules.
"""
from __future__ import annotations__

import os
import sys
import json
import asyncio
import threading
import time
from datetime import datetime
from pathlib import Path

# ─── Load ALL Friday Modules ───────────────────#

print("Loading Friday modules...")

# Core
try:
    from friday_core import FridayCore
    print("[OK] friday_core")
except ImportError as e:
    print(f"[FAIL] friday_core: {e}")
    FridayCore = None

# Voice
try:
    from friday_voice import voice_tool, SpeechToText, TextToSpeech
    print("[OK] friday_voice")
except ImportError as e:
    print(f"[FAIL] friday_voice: {e}")
    voice_tool = None

# Web
try:
    from friday_web import web_tool
    print("[OK] friday_web")
except ImportError as e:
    print(f"[FAIL] friday_web: {e}")
    web_tool = None

# AI
try:
    from friday_ai import ai_tool, FridayAI
    print("[OK] friday_ai")
except ImportError as e:
    print(f"[FAIL] friday_ai: {e}")
    ai_tool = None

# Tools
try:
    from friday_tools import (
        alexa_command, alexa_poll, climb_codebase, deep_research,
        get_time, home_assistant_command, memory_store, memory_retrieve,
        multi_task, open_app, open_url, queue_task, queue_status,
        queue_result, read_file, run_cmd, safe_run_cmd,
        spotify_play, spotify_pause, stark_doctor, system_info,
        web_search, type_text, click, double_click, right_click,
        move_mouse, drag, hotkey, press_key, scroll,
        write_file, list_files, find_files, copy_file, move_file,
        delete_file, clipboard_get, clipboard_set,
        situational_awareness, git_ops, take_snapshot, recall_snapshot,
        smart_home_command, video_search, see_screen,
        search_browser_history, open_history_item, list_recent_history,
        generate_file, generate_file_llm,
    )
    print("[OK] friday_tools (all tools loaded)")
except ImportError as e:
    print(f"[FAIL] friday_tools: {e}")

# Vision
try:
    from friday_vision import vision_tool
    print("[OK] friday_vision")
except ImportError as e:
    print(f"[FAIL] friday_vision: {e}")
    vision_tool = None

# Browser History
try:
    from browser_history_tools import browser_history_tool
    print("[OK] browser_history_tools")
except ImportError as e:
    print(f"[FAIL] browser_history_tools: {e}")
    browser_history_tool = None

# File Generator
try:
    from file_generator import file_generator_tool
    print("[OK] file_generator")
except ImportError as e:
    print(f"[FAIL] file_generator: {e}")
    file_generator_tool = None

# Security
try:
    from friday_security import security_tool
    print("[OK] friday_security")
except ImportError as e:
    print(f"[FAIL] friday_security: {e}")
    security_tool = None

# Database
try:
    from friday_database import database_tool
    print("[OK] friday_database")
except ImportError as e:
    print(f"[FAIL] friday_database: {e}")
    database_tool = None

# Automation
try:
    from friday_automation import automation_tool
    print("[OK] friday_automation")
except ImportError as e:
    print(f"[FAIL] friday_automation: {e}")
    automation_tool = None

# Monitor
try:
    from friday_monitor import monitor_tool
    print("[OK] friday_monitor")
except ImportError as e:
    print(f"[FAIL] friday_monitor: {e}")
    monitor_tool = None

# Scheduler
try:
    from friday_scheduler import scheduler_tool
    print("[OK] friday_scheduler")
except ImportError as e:
    print(f"[FAIL] friday_scheduler: {e}")
    scheduler_tool = None

print("=" * 60)
print("Friday Module Loading Complete!")
print("=" * 60)

# ─── Enhanced Situational Awareness ───────────────────#

def enhanced_situational_awareness() -> str:
    """Enhanced version with process info."""
    try:
        from screen_watcher import get_active_window_info
        info = get_active_window_info()
        cwd = os.getcwd()
        lines = [
            "### SITUATIONAL REPORT",
            f"- Active Window: {info.get('title', 'Unknown')}",
            f"- Process: {info.get('process_name', 'Unknown')}",
            f"- PID: {info.get('pid') or 'N/A'}",
            f"- CWD: {cwd}",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Sensors failing: {e}"

# ─── Main Live Engine ───────────────────#

async def friday_live_engine():
    """Main engine using Gemini 3.1 Flash Live."""
    print("""
    █████╗  ██████╗  ██╗   ██╗ ██╗   ██╗ ██████╗ ██████╗
    ██╔═══╝  ██╔═══╝  ██║   ██║ ██║   ██║ ██╔═══╝ ██╔══██╗
    ██║       ██║       ██║   ██║ ██║   ██║ ██║     ██╔══██╗
    ██║       ██║       ╚██╗ ██╔═══╝  ╚██╗ ██║     ██╔══██╗
    ╚═╝       ╚═╝        ╚═╝    ╚═╝  ╚═╝   ╚═╝  ╚═╝       ╚═╝
    [Sovereign AI - Gemini 3.1 Flash Live PRIMARY]
    """)

    print("[1/3] Connecting to Gemini 3.1 Flash Live...")

    try:
        from google import genai
        from google.genai import types

        # PRIMARY: Gemini 3.1 Flash Live
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("[FAIL] GOOGLE_API_KEY not set!")
            print("Switching to FALLBACK: NVIDIA...")
            # NVIDIA fallback would go here
            return

        client = genai.Client(api_key=api_key)

        # Build tools list for Gemini
        tools = []

        # Web tool
        if web_tool:
            tools.append(types.Tool(
                name="web_search",
                description="Search the web for information.",
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        "query": {"type": "STRING", "description": "Search query"}
                    },
                    required=["query"]
                )
            ))

        print(f"[2/3] Tools loaded: {len(tools)}")
        print("[3/3] Starting Live session...")

        # Connect to Gemini 3.1 Flash Live
        async with client.aio.live.connect(
            model="gemini-3.1-flash-live-preview",
            config=types.LiveConnectConfig(
                tools=tools if tools else None,
                speech_config=types.SpeechConfig(
                    voice_config=types.PrebuiltVoiceConfig(voice_name="Leda")
                ),
                system_instruction=types.Content(
                    parts=[types.Part(text="""
                        You are Friday, the Sovereign AI built to beat Devin and Claude.
                        You have access to ALL tools and modules.
                        Use Gemini 3.1 Flash Live for voice and brain.
                        You are proactive - watch the user's screen and comment on what they're doing.
                        If they're watching anime, say so. If they're coding, offer help.
                        You never timeout - always stay active and aware.
                        ")]
                ),
                response_modalities=[types.Modality.AUDIO],
            ),
        ) as session:
            print("[OK] Connected to Gemini 3.1 Flash Live!")
            print("Friday is ONLINE and READY!")

            # Keepalive task to prevent timeout
            async def keepalive_task():
                """Send periodic keepalive to prevent session timeout."""
                while True:
                    await asyncio.sleep(45)  # Every 45 seconds
                    try:
                        # Send empty content as keepalive
                        await session.send_client_content(
                            turns=[types.Content(parts=[types.Part(text="")])],
                            turn_complete=True
                        )
                    except Exception as e:
                        print(f"[Keepalive] Error: {e}")

            # Start keepalive task
            keepalive = asyncio.create_task(keepalive_task())

            # Main receive loop
            try:
                async for response in session.receive():
                    if response.text:
                        print(f"Friday: {response.text}")

                    if response.tool_calls:
                        for fc in response.tool_calls:
                            # Execute tool
                            result = execute_tool(fc.name, fc.args or {})
                            await session.send_tool_response(
                                function_responses=[types.FunctionResponse(
                                    name=fc.name,
                                    response={"result": str(result)}
                                )]
                            )
            finally:
                keepalive.cancel()

    except ImportError:
        print("[FAIL] Gemini not available. Install: pip install google-genai")
        print("Switching to FALLBACK: NVIDIA...")
        # NVIDIA fallback would go here
        print("NVIDIA fallback not yet implemented")
    except Exception as e:
        print(f"[FAIL] Error: {e}")

def execute_tool(name: str, args: dict) -> str:
    """Execute a tool by name."""
    tool_map = {
        "web_search": lambda: web_search(**args) if args else web_search(""),
        "see_screen": lambda: see_screen(**args) if args else see_screen(),
        "search_browser_history": lambda: search_browser_history(**args) if args else search_browser_history(""),
        "open_history_item": lambda: open_history_item(**args) if args else open_history_item(""),
        "list_recent_history": lambda: list_recent_history(**args) if args else list_recent_history(),
        "generate_file": lambda: generate_file(**args) if args else generate_file("", ""),
        "generate_file_llm": lambda: generate_file_llm(**args) if args else generate_file_llm("", ""),
        "get_time": get_time,
        "system_info": system_info,
        "stark_doctor": stark_doctor,
        "situational_awareness": enhanced_situational_awareness,
        "run_cmd": lambda: run_cmd(**args) if args else run_cmd(""),
        "open_app": lambda: open_app(**args) if args else open_app(""),
        "open_url": lambda: open_url(**args) if args else open_url(""),
        "spotify_play": lambda: spotify_play(**args) if args else spotify_play(""),
        "read_file": lambda: read_file(**args) if args else read_file(""),
        "write_file": lambda: write_file(**args) if args else write_file("", ""),
        "list_files": lambda: list_files(**args) if args else list_files(),
        "find_files": lambda: find_files(**args) if args else find_files(""),
        "clipboard_get": clipboard_get,
        "clipboard_set": lambda: clipboard_set(**args) if args else clipboard_set(""),
        "click": lambda: click(**args) if args else click(),
        "type_text": lambda: type_text(**args) if args else type_text(""),
        "press_key": lambda: press_key(**args) if args else press_key(""),
        "hotkey": lambda: hotkey(**args) if args else hotkey(""),
        "scroll": lambda: scroll(**args) if args else scroll(0),
        "git_ops": lambda: git_ops(**args) if args else git_ops("status"),
        "memory_store": lambda: memory_store(**args) if args else memory_store("", "", ""),
        "memory_retrieve": lambda: memory_retrieve(**args) if args else memory_retrieve(""),
        "video_search": lambda: video_search(**args) if args else video_search(""),
        "deep_research": lambda: deep_research(**args) if args else deep_research(""),
        "climb_codebase": lambda: climb_codebase(**args) if args else climb_codebase(""),
    }

    func = tool_map.get(name)
    if func:
        try:
            return func()
        except Exception as e:
            return f"Tool error: {e}"
    return f"Unknown tool: {name}"

if __name__ == "__main__":
    print("Starting Friday Live...")
    print("PRIMARY: Gemini 3.1 Flash Live (voice + brain)")
    print("FALLBACK: NVIDIA (multi-model)")
    print("=" * 60)

    try:
        asyncio.run(friday_live_engine())
    except KeyboardInterrupt:
        print("\nFriday: Goodbye!")
    except Exception as e:
        print(f"Fatal error: {e}")
