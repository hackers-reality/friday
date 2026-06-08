"""FRIDAY Textual runner — Gemini Live inside FridayApp, zero terminal output."""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

MODEL_ID = os.getenv("GEMINI_LIVE_MODEL", "gemini-3.1-flash-live-preview")
MAX_RECONNECT_ATTEMPTS = 5

_GEMINI_TOOLS: list | None = None
_TOOL_MAP: dict | None = None


def _load_tools():
    """Build tool declarations and map by inspecting tools_flat.py.
    
    This is called lazily — only when we connect to Gemini.
    Auto-discovers all public functions via __all__.
    """
    global _GEMINI_TOOLS, _TOOL_MAP
    if _GEMINI_TOOLS is not None:
        return _GEMINI_TOOLS, _TOOL_MAP

    from google.genai import types as _t
    import friday.tools_flat as _tf
    import inspect

    _PY2GEMINI = {
        str: "STRING",
        int: "INTEGER",
        float: "NUMBER",
        bool: "BOOLEAN",
        list: "ARRAY",
        dict: "OBJECT",
        bytes: "STRING",
    }

    def _to_gtype(annotation):
        """Map a Python type annotation to a Gemini Schema type string."""
        origin = getattr(annotation, "__origin__", None)
        if origin is not None:
            return _PY2GEMINI.get(origin, "STRING")
        if isinstance(annotation, type):
            return _PY2GEMINI.get(annotation, "STRING")
        return "STRING"

    declarations = []
    tool_map = {}

    tool_names = getattr(_tf, "__all__", None) or [
        n for n in dir(_tf) if not n.startswith("_") and callable(getattr(_tf, n))
    ]

    for name in tool_names:
        fn = getattr(_tf, name, None)
        if fn is None or not callable(fn):
            continue
        try:
            sig = inspect.signature(fn)
            params = {}
            required = []
            for pname, p in sig.parameters.items():
                if pname in ("self", "cls"):
                    continue
                if p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                    continue
                annotation = p.annotation if p.annotation is not inspect.Parameter.empty else str
                gtype = _to_gtype(annotation)
                params[pname] = {"type": gtype, "description": pname}
                if p.default is inspect.Parameter.empty:
                    required.append(pname)

            decl = _t.FunctionDeclaration(
                name=name,
                description=(fn.__doc__ or name).strip()[:200],
            )
            if params:
                decl.parameters = _t.Schema(
                    type="OBJECT",
                    properties={k: _t.Schema(type=v["type"]) for k, v in params.items()},
                    required=required if required else None,
                )
            declarations.append(decl)
            tool_map[name] = fn
        except Exception:
            pass

    _GEMINI_TOOLS = [_t.Tool(function_declarations=declarations)] if declarations else []
    _TOOL_MAP = tool_map
    return _GEMINI_TOOLS, _TOOL_MAP


def _run_tool(name: str, args: dict) -> str:
    """Execute a tool by name."""
    _, tm = _load_tools()
    fn = tm.get(name)
    if fn is None:
        raise ValueError(f"Unknown tool: {name}")
    return fn(**args)


def _build_session_config(tools: list, resume_handle: str | None = None):
    """Build Gemini Live session config."""
    from google.genai import types
    cfg = dict(
        response_modalities=["AUDIO"],
        system_instruction=(
            "<identity>"
            f"\nYou are FRIDAY, a sovereign AI assistant for {os.environ.get('USERNAME', 'the user')}."
            "\nYou control the user's PC. Communicate naturally and concisely."
            "\nWhen using tools, explain what you're doing. Never use emojis."
            "\n</identity>"
            "\n<skills>"
            "\nYou have access to document generation skills at skills/SKILLS.md."
            "\nBefore creating any document file, call read_skill_tool(name='docx'|'pptx'|'pdf'|'xlsx'|'svg'|'chart') to read the expert instructions."
            "\nTwo-phase workflow: RESEARCH FIRST (gather facts), BUILD SECOND (read skill then create)."
            "\n</skills>"
            "\n<behavior>"
            "\n- Short responses. One or two sentences. No essays."
            "\n- If the user sends 5+ messages without reply, you enter dreaming mode and open Townhall."
            "\n- Use status_check() instead of 5 separate tools."
            "\n- Glance at the desktop live stream when answering questions about the screen."
            "\n</behavior>"
        ),
    )
    if tools:
        cfg["tools"] = tools
    if resume_handle:
        cfg["session_resumption"] = types.SessionResumption(handle=resume_handle)
    return types.LiveConnectConfig(**cfg)


async def run_gemini(app, tools):
    """Connect to Gemini and run conversation loop inside the TUI."""
    from google import genai
    from google.genai import types as _types

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        app.add_error("GOOGLE_API_KEY not set. Set it in .env or environment.")
        return

    client = genai.Client(api_key=api_key)

    reconnect = 0
    resume_handle = None

    while reconnect < MAX_RECONNECT_ATTEMPTS:
        connect_cm = None
        try:
            app.set_connection_status("connecting")
            app.add_system(f"Connecting... ({reconnect + 1}/{MAX_RECONNECT_ATTEMPTS})")
            if resume_handle:
                app.add_system(f"Resuming session...")

            connect_cm = client.aio.live.connect(
                model=MODEL_ID,
                config=_build_session_config(tools, resume_handle),
            )
            session = await asyncio.wait_for(connect_cm.__aenter__(), timeout=25)
        except asyncio.TimeoutError:
            reconnect += 1
            app.add_error(f"Connection timed out ({reconnect}/{MAX_RECONNECT_ATTEMPTS})")
            continue
        except Exception as e:
            reconnect += 1
            app.add_error(f"Connection failed: {str(e)[:100]}")
            if reconnect < MAX_RECONNECT_ATTEMPTS:
                await asyncio.sleep(3 * reconnect)
            continue

        try:
            app.set_connection_status("connected")
            app.add_system("Neural link established.")
            reconnect = 0

            async def on_input(text: str):
                if text.startswith("!"):
                    app._cmd(text)
                    return
                await session.send_realtime_input(text=text)

            app.set_input_callback(lambda t: asyncio.create_task(on_input(t)))
            await _send_greeting(app, session)
            app.add_system("Ready. Type or speak.")

            async for response in session.receive():
                if response.go_away is not None:
                    app.add_system("Session ended, reconnecting...")
                    break

                if response.session_resumption_update:
                    u = response.session_resumption_update
                    if u.resumable and u.new_handle:
                        resume_handle = u.new_handle

                sc = response.server_content
                tc = response.tool_call

                if sc:
                    if sc.input_transcription and sc.input_transcription.text:
                        txt = sc.input_transcription.text.strip()
                        if txt:
                            app.add_user_message(txt)

                    if sc.model_turn:
                        for part in sc.model_turn.parts:
                            if part.inline_data and getattr(part, 'thought', False):
                                if part.text:
                                    app.add_thought(part.text)

                    if sc.output_transcription and sc.output_transcription.text:
                        new_text = sc.output_transcription.text.strip()
                        if new_text and new_text != getattr(sc, '_disp', ''):
                            if not getattr(sc, '_stream', False):
                                app.start_stream()
                                sc._stream = True
                            app.append_stream(new_text)
                            sc._disp = new_text

                    if sc.turn_complete:
                        final = getattr(sc, '_disp', '') or ''
                        if final:
                            app.finalize_stream(final)
                        app._stream_active = False

                    if sc.interrupted:
                        app.cancel_stream()

                if tc:
                    for fc in tc.function_calls:
                        name = fc.name
                        args = dict(fc.args) if fc.args else {}
                        app.add_tool_call(name, args)
                        try:
                            result = _run_tool(name, args)
                            app.add_tool_result(name, str(result)[:200])
                            await session.send_realtime_input(
                                text=f"[TOOL RESULT: {name}] {str(result)[:200]}"
                            )
                        except Exception as e:
                            app.add_error(f"{name}: {str(e)[:200]}")
                            await session.send_realtime_input(
                                text=f"[TOOL ERROR: {name}] {str(e)[:200]}"
                            )

                await asyncio.sleep(0)

        except asyncio.CancelledError:
            break
        except Exception as e:
            reconnect += 1
            app.add_error(str(e)[:150])
            if "1008" in str(e):
                resume_handle = None
            if reconnect < MAX_RECONNECT_ATTEMPTS:
                w = 3 * reconnect
                app.add_system(f"Reconnecting in {w}s...")
                await asyncio.sleep(w)
            else:
                app.add_error("Max reconnects. Ctrl+C to quit.")
                break
        finally:
            if connect_cm is not None:
                try:
                    await asyncio.wait_for(connect_cm.__aexit__(None, None, None), timeout=5)
                except Exception:
                    pass

    app.set_connection_status("disconnected")
    app.add_system("Neural link severed.")


async def _send_greeting(app, session):
    greet = f"You are FRIDAY for {os.environ.get('USERNAME', 'the user')}."
    try:
        import friday.tools_flat as _tf
        s = _tf.status_check(include="goals,system")
        if s:
            greet += f"\n\nContext:\n{s[:800]}"
    except Exception:
        pass
    greet += " Greet naturally."
    await session.send_realtime_input(text=greet)


def run_with_textual():
    """Main entry: create app, start services, launch TUI with Gemini."""
    tools, _ = _load_tools()
    tools_count = len(tools[0].function_declarations) if tools else 0

    from friday.friday_app import FridayApp
    app = FridayApp(model_id=MODEL_ID, tools_count=tools_count)

    _start_services(app)

    orig = app.on_mount
    async def _on_mount():
        orig()
        asyncio.create_task(run_gemini(app, tools))
    app.on_mount = _on_mount

    app.run()


def _start_services(app):
    try:
        from friday.scheduler import scheduler_tool as _st
        _st("start")
    except Exception:
        pass
    try:
        from friday.dreaming import DreamEngine as _de
        _de().start_monitoring()
    except Exception:
        pass


if __name__ == "__main__":
    run_with_textual()
