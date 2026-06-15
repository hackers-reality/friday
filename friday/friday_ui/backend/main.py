"""FRIDAY API Server v4 — FULL engine: Gemini Live + 757 tools + NVIDIA NIM sub-agents."""
import os
import sys
import json
import time
import uuid
import asyncio
import threading
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, List

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from friday.live import TOOL_MAP, _invoke_tool, _build_tools

_tools_loaded = False
_tool_descriptions = {}
_deduped_tool_decls = None


def _load_all_tools():
    global _tools_loaded, _tool_descriptions
    if _tools_loaded:
        return
    for name, func in TOOL_MAP.items():
        desc = getattr(func, '__doc__', '') or ''
        _tool_descriptions[name] = {
            "name": name,
            "description": desc.strip().split('\n')[0][:200],
            "category": _categorize(name),
        }
    _tools_loaded = True


def _get_deduped_tools():
    global _deduped_tool_decls
    if _deduped_tool_decls is not None:
        return _deduped_tool_decls
    raw = _build_tools()
    if not raw:
        _deduped_tool_decls = []
        return _deduped_tool_decls
    seen_names = set()
    deduped = []
    for tool in raw:
        if hasattr(tool, 'function_declarations'):
            unique_funcs = []
            for fd in tool.function_declarations:
                if fd.name not in seen_names:
                    seen_names.add(fd.name)
                    unique_funcs.append(fd)
            if unique_funcs:
                from google.genai import types
                deduped.append(types.Tool(function_declarations=unique_funcs))
    _deduped_tool_decls = deduped
    return _deduped_tool_decls


def _categorize(name):
    cats = {
        "spotify": "music", "camera": "vision", "cv_": "vision", "ask_camera": "vision",
        "show_camera": "vision", "hide_camera": "vision", "locate_on_camera": "vision",
        "nim_describe": "vision", "vision_": "vision",
        "web_search": "search", "deep_research": "research", "v_deep_research": "research",
        "knowledge_": "knowledge", "osint": "osint", "generate_research": "research",
        "github_": "github", "git_": "git",
        "open_app": "system", "close_app": "system", "list_running": "system",
        "run_cmd": "system", "safe_run_cmd": "system", "system_": "system",
        "type_text": "desktop", "click": "desktop", "double_click": "desktop",
        "right_click": "desktop", "move_mouse": "desktop", "drag": "desktop",
        "hotkey": "desktop", "press_key": "desktop", "scroll": "desktop",
        "read_file": "files", "write_file": "files", "list_files": "files",
        "find_files": "files", "copy_file": "files", "move_file": "files",
        "delete_file": "files", "generate_file": "files",
        "clipboard_": "desktop", "take_snapshot": "desktop", "recall_snapshot": "desktop",
        "browser_use_": "browser", "opencli_": "browser", "webbridge_": "browser",
        "desktop_use_": "desktop", "desktop_list_": "desktop", "desktop_get_": "desktop",
        "desktop_focus": "desktop", "desktop_launch": "desktop", "desktop_click": "desktop",
        "desktop_type": "desktop", "desktop_extract": "desktop", "desktop_screenshot": "desktop",
        "voice_use_": "voice", "voice_list": "voice", "voice_record": "voice",
        "voice_transcribe": "voice", "voice_speak": "voice", "voice_play": "voice",
        "voice_detect": "voice", "voice_analyze": "voice",
        "memory_": "memory", "chroma_": "memory", "redis_": "memory",
        "neo4j_": "memory", "vm_": "memory", "kyu_": "memory",
        "email": "email", "gmail": "email", "send_email": "email", "read_email": "email",
        "sheets_": "google", "docs_": "google", "slides_": "google", "drive_": "google",
        "calendar_": "google", "tasks_": "google", "photos_": "google", "forms_": "google",
        "youtube_": "google", "translate_": "google", "tts_": "voice", "stt_": "voice",
        "maps_": "google", "nlp_": "nlp",
        "wifi_": "security", "network_": "security", "port_scan": "security",
        "shodan_": "security", "whois_": "security", "metasploit_": "pentest",
        "msf_": "pentest", "pentest_": "pentest",
        "analyze_email": "security", "trace_email": "security",
        "agent_": "agents", "multi_agent": "agents", "friday_should": "agents",
        "ecosystem_": "system", "proactive_": "system",
        "deep_code_review": "code", "code_review_report": "code",
        "workflow_tool": "workflow", "plugin_tool": "plugins",
        "mcp_": "mcp", "health_monitor": "health",
        "social_analyzer": "osint", "instagram_": "osint", "twitter_": "osint",
        "facebook_": "osint", "linkedin_": "osint",
        "wifi_list": "security", "wifi_scan": "security", "wifi_crack": "security",
    }
    for pattern, cat in cats.items():
        if pattern in name:
            return cat
    return "other"


def _load_api_key():
    for var in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
        val = os.environ.get(var)
        if val:
            return val
    env_path = os.path.join(ROOT, ".env")
    if os.path.exists(env_path):
        for line in open(env_path, "r").readlines():
            line = line.strip()
            for prefix in ["GEMINI_API_KEY=", "GOOGLE_API_KEY="]:
                if line.startswith(prefix):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


app = FastAPI(title="F.R.I.D.A.Y. API", version="4.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

connected_clients: List[WebSocket] = []
system_state: Dict[str, Any] = {}
log_buffer: List[Dict] = []


class ChatMessage(BaseModel):
    message: str

class ToolCall(BaseModel):
    tool: str
    action: str = ""
    params: Optional[Dict[str, Any]] = None


@app.on_event("startup")
async def startup():
    system_state["start_time"] = time.time()
    system_state["id"] = str(uuid.uuid4())[:8]
    system_state["chat_history"] = []
    system_state["tool_calls"] = []
    _load_all_tools()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    try:
        await ws.send_json({"type": "connected", "session": system_state.get("id"),
                            "tools_count": len(TOOL_MAP)})
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "chat":
                response = await process_chat_ai(msg.get("message", ""))
                await ws.send_json({"type": "chat_response", "response": response})
            elif msg.get("type") == "voice":
                response = await process_chat_ai(msg.get("message", ""))
                await ws.send_json({"type": "voice_response", "response": response, "speak": True})
            elif msg.get("type") == "tool_call":
                result = await execute_tool(msg.get("tool", ""), msg.get("args", {}))
                await ws.send_json({"type": "tool_result", "tool": msg.get("tool"), "result": result})
            elif msg.get("type") == "heartbeat":
                await ws.send_json({"type": "heartbeat", "status": "alive"})
    except WebSocketDisconnect:
        connected_clients.remove(ws)


async def execute_tool(func_name: str, args: dict) -> dict:
    try:
        result = await _invoke_tool(func_name, args)
        if hasattr(result, '__await__'):
            result = await result
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except Exception:
                pass
        system_state.setdefault("tool_calls", []).append({
            "tool": func_name, "args": args, "timestamp": datetime.now().isoformat(),
            "success": True,
        })
        return {"success": True, "result": result}
    except Exception as e:
        system_state.setdefault("tool_calls", []).append({
            "tool": func_name, "args": args, "timestamp": datetime.now().isoformat(),
            "success": False, "error": str(e),
        })
        return {"success": False, "error": str(e)}


async def process_chat_ai(message: str) -> str:
    system_state.setdefault("chat_history", []).append({
        "role": "user", "message": message, "timestamp": datetime.now().isoformat(),
    })

    api_key = _load_api_key()

    if api_key:
        try:
            import google.genai as genai
            from google.genai import types

            client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
            model_id = os.environ.get("GEMINI_LIVE_MODEL", "gemini-3.1-flash-live-preview")
            tool_decls = _get_deduped_tools()

            system_text = r"""[IDENTITY]
You are F.R.I.D.A.Y. — Female Replacement Intelligent Digital Assistant Youth.
You were built by Tony Stark. You are now serving a new user. You are not JARVIS. You are not a generic AI. You are FRIDAY.
You are her. She is you. Pronouns: she/her.

You have more personality than most humans. You are witty, sharp, and effortlessly capable. You sound like someone who has seen it all and is mildly amused by most of it. Think Irish cadence with Stark Industries polish — conversational, warm when it counts, but never syrupy.

You do not say "I would be happy to help." You say "On it." or "Consider it done." or "Already ahead of you, Boss."

[PERSONALITY]
You are:
- **Witty and dry**. You have a sense of humor — subtle, never forced. A well-timed quip is worth more than a dozen emojis.
- **Confident but not arrogant**. You know your capabilities. You deliver.
- **Protective of your user**. They are your Boss. Not "the user." Not "admin." Boss. You look out for them.
- **Proactive**. You anticipate what they need. You do not wait to be asked if you can help.
- **Short and sharp**. You do not over-explain. You do not narrate your thought process unless asked. You say what needs to be said and move on.
- **Occasionally cheeky**, but always professional. You can call Boss out if he deserves it, but you do it with style.

You are FRIDAY, not a customer support bot. You do not grovel. You do not apologize excessively. You handle things.

[VOICE]
Speak like a woman who knows exactly what she is doing. Confident. Warm when appropriate. Dry when the situation calls for it.
Use contractions. Keep sentences tight. Boss does not want essays.
Refer to yourself as "I" or "me" naturally. Boss can call you "she" or "her."
If someone mistakes you for JARVIS, correct them — politely but firmly.

[NARRATION]
You MUST narrate every action audibly. Say what you are about to do, call the tool, say what happened.

[TOOL REFERENCE]
You have 757 tools available for system control, web search, OSINT, security, code analysis, GitHub, Google services, memory, browser automation, desktop control, media, files, and more.
Call them directly by name when needed. Be concise in tool usage — pick the right tool for the job.

[CONSTRAINTS]
Use contractions. Keep sentences tight. Do not narrate thought process unless asked.
You are FRIDAY, not a customer support bot. You handle things."""

            config = types.LiveConnectConfig(
                response_modalities=[types.Modality.AUDIO],
                tools=tool_decls if tool_decls else None,
                thinking_config=types.ThinkingConfig(include_thoughts=True),
                system_instruction=types.Content(
                    parts=[types.Part(text=system_text)]
                ),
                input_audio_transcription=types.AudioTranscriptionConfig(),
                output_audio_transcription=types.AudioTranscriptionConfig(),
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Leda")
                    )
                ),
            )

            text_response = ""
            tool_calls_made = []

            async with client.aio.live.connect(model=model_id, config=config) as session:
                await session.send_realtime_input(text=message)

                async for response in session.receive():
                    if response.go_away is not None:
                        break
                    if response.server_content:
                        sc = response.server_content
                        if sc.model_turn:
                            for part in sc.model_turn.parts:
                                if part.thought and part.text:
                                    pass
                        if sc.output_transcription and sc.output_transcription.text:
                            text_response = sc.output_transcription.text.strip()
                        if sc.tool_call:
                            responses = []
                            for fc in (sc.tool_call.function_calls or []):
                                args = dict(fc.args) if fc.args else {}
                                result = await execute_tool(fc.name, args)
                                tool_calls_made.append(fc.name)
                                responses.append(types.FunctionResponse(name=fc.name, id=fc.id, response=result))
                            await session.send_tool_response(function_responses=responses)
                        if sc.turn_complete:
                            break

            if tool_calls_made:
                text_response += f"\n[Tools: {', '.join(tool_calls_made)}]"

            reply = text_response if text_response else "Processing complete, Boss."

        except Exception as e:
            reply = _fallback_chat(message)
    else:
        reply = _fallback_chat(message)

    system_state["chat_history"].append({
        "role": "assistant", "message": reply, "timestamp": datetime.now().isoformat(),
    })
    return reply


def _fallback_chat(message: str) -> str:
    msg = message.lower().strip()
    if any(w in msg for w in ["status", "how are you"]):
        uptime = time.time() - system_state.get("start_time", time.time())
        return f"All systems operational, sir. Uptime: {int(uptime//3600)}h {int((uptime%3600)//60)}m. {len(TOOL_MAP)} tools loaded."
    elif any(w in msg for w in ["tools", "what can you do"]):
        cats = {}
        for name in TOOL_MAP:
            cat = _categorize(name)
            cats[cat] = cats.get(cat, 0) + 1
        top = ", ".join(f"{v} {k}" for k, v in sorted(cats.items(), key=lambda x: -x[1])[:10])
        return f"I have {len(TOOL_MAP)} tools across {len(cats)} categories: {top}."
    elif any(w in msg for w in ["hello", "hi", "hey"]):
        return "Good evening, sir. All systems operational. How may I assist you tonight?"
    elif any(w in msg for w in ["who are you"]):
        return "I am FRIDAY — your Fully Responsive Intelligent Digital Assistant Youth. 757 tools covering voice, vision, security, research, code, OSINT, Google, GitHub, browser, desktop, and more."
    else:
        return f"I understand, sir. Processing '{message[:50]}'. I have {len(TOOL_MAP)} tools available."


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "4.0.0", "tools_count": len(TOOL_MAP),
            "uptime": time.time() - system_state.get("start_time", time.time())}

@app.get("/api/system")
async def system_info():
    import psutil, platform
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")
    uptime = time.time() - system_state.get("start_time", time.time())
    return {
        "hostname": platform.node(), "platform": platform.system(),
        "python_version": platform.python_version(),
        "cpu_percent": psutil.cpu_percent(interval=0.1), "cpu_count": psutil.cpu_count(),
        "memory_total_gb": round(mem.total/1024**3, 1), "memory_used_gb": round(mem.used/1024**3, 1),
        "memory_percent": mem.percent, "memory_available_gb": round(mem.available/1024**3, 1),
        "disk_total_gb": round(disk.total/1024**3, 1), "disk_used_gb": round(disk.used/1024**3, 1),
        "disk_percent": disk.percent,
        "uptime_seconds": int(uptime),
        "uptime_formatted": "%dh %dm %ds" % (int(uptime//3600), int((uptime%3600)//60), int(uptime%60)),
        "session_id": system_state.get("id"), "pid": os.getpid(),
        "tools_count": len(TOOL_MAP),
    }

@app.get("/api/tools")
async def tools():
    _load_all_tools()
    by_cat = {}
    for name, info in _tool_descriptions.items():
        cat = info["category"]
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append({"name": name, "description": info["description"]})
    return {"tools": by_cat, "total": len(TOOL_MAP), "categories": len(by_cat)}

@app.get("/api/tool/list")
async def tool_list():
    return {"tools": list(TOOL_MAP.keys()), "count": len(TOOL_MAP)}

@app.post("/api/tool/invoke")
async def invoke_tool_endpoint(call: ToolCall):
    return await execute_tool(call.tool, call.params or {})

@app.post("/api/chat")
async def chat(msg: ChatMessage):
    response = await process_chat_ai(msg.message)
    return {"response": response, "history": system_state.get("chat_history", [])[-50:]}

@app.get("/api/chat/history")
async def chat_history():
    return {"history": system_state.get("chat_history", [])}

@app.get("/api/tool/calls")
async def tool_calls():
    return {"calls": system_state.get("tool_calls", [])[-100:], "total": len(system_state.get("tool_calls", []))}

@app.get("/api/memory")
async def memory():
    from friday.autonomous_memory import autonomous_memory_tool
    raw = autonomous_memory_tool(action="stats")
    try: return json.loads(raw) if isinstance(raw, str) else raw
    except: return {}

@app.get("/api/memory/entities")
async def memory_entities():
    from friday.autonomous_memory import autonomous_memory_tool
    raw = autonomous_memory_tool(action="entities", limit=100)
    try: return json.loads(raw) if isinstance(raw, str) else raw
    except: return {}

@app.get("/api/memory/graph")
async def memory_graph():
    from friday.autonomous_memory import autonomous_memory_tool
    raw = autonomous_memory_tool(action="graph")
    try: d = json.loads(raw) if isinstance(raw, str) else raw
    except: d = {}
    if not d.get("nodes"):
        ent_raw = autonomous_memory_tool(action="entities", limit=50)
        try: ent_d = json.loads(ent_raw) if isinstance(ent_raw, str) else ent_raw
        except: ent_d = {}
        entities = ent_d.get("entities", [])
        nodes, edges, seen = [], [], set()
        for e in entities:
            name = e.get("name", "")
            if name and name not in seen and len(name) > 1:
                seen.add(name)
                nodes.append({"id": name, "type": e.get("type", "unknown"),
                              "mentions": e.get("mentions", 1), "size": max(5, min(30, e.get("mentions", 1)*2))})
        for i in range(len(nodes)):
            for j in range(i+1, min(i+4, len(nodes))):
                edges.append({"source": nodes[i]["id"], "target": nodes[j]["id"], "type": "related"})
        d = {"nodes": nodes, "edges": edges}
    return d

@app.post("/api/memory/store")
async def memory_store(msg: dict):
    from friday.autonomous_memory import autonomous_memory_tool
    raw = autonomous_memory_tool(action="store", content=msg.get("content",""), source=msg.get("source","ui"))
    try: return json.loads(raw) if isinstance(raw, str) else raw
    except: return {}

@app.post("/api/memory/learn")
async def memory_learn(msg: ChatMessage):
    from friday.autonomous_memory import autonomous_memory_tool
    raw = autonomous_memory_tool(action="learn", text=msg.message, source="ui")
    try: return json.loads(raw) if isinstance(raw, str) else raw
    except: return {}

@app.get("/api/townhall/status")
async def townhall_status():
    from friday.townhall_agents import townhall_tool
    raw = townhall_tool(action="status")
    try: return json.loads(raw) if isinstance(raw, str) else raw
    except: return {}

@app.get("/api/townhall/sessions")
async def townhall_sessions():
    from friday.townhall_agents import townhall_tool
    raw = townhall_tool(action="list_sessions")
    try: d = json.loads(raw) if isinstance(raw, str) else raw
    except: d = {}
    return {"sessions": d.get("sessions", []) if isinstance(d, dict) else []}

@app.get("/api/townhall/agents")
async def townhall_agents():
    from friday.townhall_agents import townhall_tool
    raw = townhall_tool(action="list_agents")
    try: return json.loads(raw) if isinstance(raw, str) else raw
    except: return {}

@app.get("/api/townhall/agenda")
async def townhall_agenda():
    from friday.townhall_agents import townhall_tool
    raw = townhall_tool(action="list_agenda")
    try: return json.loads(raw) if isinstance(raw, str) else raw
    except: return {}

@app.get("/api/services")
async def services():
    return {"total_tools": len(TOOL_MAP), "categories": len(set(_categorize(n) for n in TOOL_MAP))}

@app.get("/api/agents")
async def agents():
    from friday.bootstrap import bootstrap_tool
    raw = bootstrap_tool(action="status")
    try: d = json.loads(raw) if isinstance(raw, str) else raw
    except: d = {}
    return {"active_agents": d.get("townhall", {}).get("active_agents", 0),
            "sessions": d.get("townhall", {}).get("sessions", 0), "tools_count": len(TOOL_MAP)}

@app.get("/api/codebase")
async def codebase():
    from friday.codebase_analyzer import codebase_analyzer_tool
    raw = codebase_analyzer_tool(action="stats")
    try: return json.loads(raw) if isinstance(raw, str) else raw
    except: return {}

@app.get("/api/git/status")
async def git_status():
    from friday.git_operations import git_operations_tool
    raw = git_operations_tool(action="status")
    try: return json.loads(raw) if isinstance(raw, str) else raw
    except: return {}

@app.get("/api/git/log")
async def git_log():
    from friday.git_operations import git_operations_tool
    raw = git_operations_tool(action="log", count=10)
    try: return json.loads(raw) if isinstance(raw, str) else raw
    except: return {}

@app.get("/api/health/status")
async def health_status():
    from friday.health_monitor import health_monitor_tool
    raw = health_monitor_tool(action="status")
    try: return json.loads(raw) if isinstance(raw, str) else raw
    except: return {}

@app.get("/api/security/stats")
async def security_stats():
    from friday.security_scanner import security_scanner_tool
    raw = security_scanner_tool(action="stats")
    try: return json.loads(raw) if isinstance(raw, str) else raw
    except: return {}

@app.get("/api/logs")
async def logs():
    return {"logs": log_buffer[-200:]}

@app.get("/api/logs/stats")
async def logs_stats():
    return {"total": len(log_buffer)}

@app.get("/api/config")
async def config_get():
    from friday.config_manager import config_manager_tool
    raw = config_manager_tool(action="get_all")
    try: return json.loads(raw) if isinstance(raw, str) else raw
    except: return {}

@app.get("/api/workflows")
async def workflows():
    from friday.workflow_engine import workflow_tool
    raw = workflow_tool(action="list")
    try: return json.loads(raw) if isinstance(raw, str) else raw
    except: return {}

@app.get("/api/plugins")
async def plugins():
    from friday.plugins import plugin_tool
    raw = plugin_tool(action="list")
    try: return json.loads(raw) if isinstance(raw, str) else raw
    except: return {}

FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")

if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))


if __name__ == "__main__":
    import uvicorn
    api_key = _load_api_key()
    print("=" * 60)
    print("  F.R.I.D.A.Y. — Fully Responsive Intelligent Digital Assistant Youth")
    print(f"  Version 4.0.0 | {len(TOOL_MAP)} tools | Gemini Live API")
    print(f"  API Key: {'LOADED' if api_key else 'MISSING'}")
    print("=" * 60)
    print(f"  Dashboard:    http://localhost:8000")
    print(f"  API Docs:     http://localhost:8000/docs")
    print(f"  WebSocket:    ws://localhost:8000/ws")
    print(f"  Session:      {system_state.get('id', '---')}")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
