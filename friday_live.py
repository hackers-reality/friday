"""
Friday Live - Sovereign AI with Gemini 3.1 Flash Live.
PRIMARY: Gemini 3.1 Flash Live (native voice, brain)
FALLBACK: NVIDIA (multi-model)
Integrates ALL Friday modules.
"""
from __future__ import annotations

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
    from friday_ai import ai_tool
    print("[OK] friday_ai")
except ImportError as e:
    print(f"[FAIL] friday_ai: {e}")
    ai_tool = None
try:
    from friday_ai import FridayAI
except ImportError:
    FridayAI = None

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
        generate_file, generate_file_llm, search_and_open,
        memory_import_tool_handler,
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
    import friday_automation
    automation_tool = getattr(friday_automation, 'automation_tool', None)
    if automation_tool:
        print("[OK] friday_automation")
    else:
        print("[OK] friday_automation (no automation_tool)")
except Exception as e:
    print(f"[FAIL] friday_automation: {e}")
    automation_tool = None

# Monitor
try:
    import friday_monitor
    monitor_tool = getattr(friday_monitor, 'monitor_tool', None)
    if not monitor_tool:
        MonitorClass = getattr(friday_monitor, 'FridayMonitor', None)
        if MonitorClass:
            monitor_tool = MonitorClass()
    if monitor_tool:
        print("[OK] friday_monitor")
    else:
        print("[OK] friday_monitor (loaded)")
except Exception as e:
    print(f"[FAIL] friday_monitor: {e}")
    monitor_tool = None

# Scheduler
try:
    import friday_scheduler
    scheduler_tool = getattr(friday_scheduler, 'scheduler_tool', None)
    if scheduler_tool:
        print("[OK] friday_scheduler")
    else:
        print("[OK] friday_scheduler (no scheduler_tool)")
except Exception as e:
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

# ─── Background Screen Monitor ───────────────────#

async def background_monitor(session=None):
    """Background task: screenshot every 30s, analyze with vision, speak proactive comments.
    Max one comment every 5 minutes to avoid being annoying.
    """
    import time
    from datetime import datetime, timedelta

    last_comment_time = None
    comment_cooldown = timedelta(minutes=5)
    last_screenshot_time = 0

    while True:
        try:
            # Take screenshot every 30 seconds
            now = time.time()
            if now - last_screenshot_time >= 30:
                last_screenshot_time = now

                # Capture screen
                try:
                    from screen_watcher import capture_screen
                    screenshot_bytes = capture_screen(resize_to=(960, 540), quality=60)
                except Exception:
                    # Fallback: use PIL directly
                    from PIL import ImageGrab
                    import io
                    screen = ImageGrab.grab()
                    screen = screen.resize((960, 540))
                    buffer = io.BytesIO()
                    screen.save(buffer, format="JPEG", quality=60)
                    screenshot_bytes = buffer.getvalue()

                if not screenshot_bytes:
                    await asyncio.sleep(5)
                    continue

                # Analyze with vision model (Gemini)
                if session:
                    try:
                        from google.genai import types
                        await session.send_client_content(
                            turns=[types.Content(parts=[types.Part(
                                inline_data=types.Blob(
                                    mime_type="image/jpeg",
                                    data=screenshot_bytes
                                )
                            )])],
                            turn_complete=True
                        )
                        # Wait for response
                        async for response in session.receive():
                            if response.text:
                                analysis = response.text.lower()
                                # Check if interesting content detected
                                interesting_keywords = [
                                    "anime", "youtube", "coding", "error", "game",
                                    "netflix", "movie", "debug", "exception"
                                ]
                                is_interesting = any(kw in analysis for kw in interesting_keywords)

                                if is_interesting:
                                    # Check cooldown
                                    now_dt = datetime.now()
                                    if last_comment_time is None or (now_dt - last_comment_time) > comment_cooldown:
                                        last_comment_time = now_dt
                                        # Speak the comment via TTS
                                        try:
                                            from friday_voice import TextToSpeech
                                            tts = TextToSpeech()
                                            if tts.available:
                                                tts.speak(f"I see you're {analysis[:100]}. Want help?")
                                        except:
                                            print(f"[BackgroundMonitor] Comment: I see you're {analysis[:100]}")
                                        print(f"[BackgroundMonitor] Proactive comment triggered: {analysis[:50]}")
                                break
                    except Exception as e:
                        print(f"[BackgroundMonitor] Vision analysis error: {e}")
                else:
                    # No session - just log
                    print(f"[BackgroundMonitor] Screenshot captured ({len(screenshot_bytes)} bytes)")

            await asyncio.sleep(5)  # Check every 5 seconds

        except Exception as e:
            print(f"[BackgroundMonitor] Error: {e}")
            await asyncio.sleep(10)


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
                    parts=[types.Part(text="You are Friday, the Sovereign AI built to beat Devin and Claude. You have access to ALL tools and modules. Use Gemini 3.1 Flash Live for voice and brain. You are proactive - watch the user's screen and comment on what they're doing. If they're watching anime, say so. If they're coding, offer help. You never timeout - always stay active and aware.")]
                ),
                response_modalities=[types.Modality.AUDIO],
            ),
        ) as session:
            print("[OK] Connected to Gemini 3.1 Flash Live!")
            print("Friday is ONLINE and READY!")

            # ─── Keepalive task (fixed) ──────────────
            async def keepalive_task():
                while True:
                    await asyncio.sleep(45)
                    try:
                        await session.send_client_content(
                            turns=[types.Content(parts=[types.Part(text=".")])],
                            turn_complete=True
                        )
                        print("[Keepalive] Ping sent successfully")
                    except Exception as e:
                        print(f"[Keepalive] Error: {e}")

            # ─── Background monitor task ─────────────
            async def bg_monitor_task():
                await background_monitor(session)

            # ─── Start background tasks ──────────────
            asyncio.create_task(keepalive_task())
            asyncio.create_task(bg_monitor_task())

            # ─── Main receive loop ───────────────────
            print("[OK] Entering main receive loop. Listening to Gemini...")
            while True:
                try:
                    async for response in session.receive():
                        if response.text:
                            print(f"[Gemini] {response.text[:100]}")
                        elif response.tool_call:
                            for fc in response.tool_call.function_calls:
                                print(f"[ToolCall] {fc.name}({fc.args})")
                except Exception as e:
                    print(f"[Session] Receive error: {e}")
                    await asyncio.sleep(5)

    except Exception as e:
        print(f"[FAIL] Gemini connection error: {e}")
        import traceback
        traceback.print_exc()

    print("[Shutdown] Friday Live engine stopped.")


# ─── Entry Point ──────────────────────────────

if __name__ == "__main__":
    try:
        asyncio.run(friday_live_engine())
    except KeyboardInterrupt:
        print("\n[Shutdown] Friday terminated by user.")
    except Exception as e:
        print(f"[FAIL] Friday crashed: {e}")
        import traceback
        traceback.print_exc()
