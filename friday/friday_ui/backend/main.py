"""FRIDAY API Server v4 — FULL engine from live.py with all 500+ tools."""
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


def _categorize(name):
    categories = {
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
        "desktop_scroll": "desktop", "desktop_press": "desktop",
        "voice_use_": "voice", "voice_list": "voice", "voice_record": "voice",
        "voice_transcribe": "voice", "voice_speak": "voice", "voice_play": "voice",
        "voice_detect": "voice", "voice_analyze": "voice",
        "memory_": "memory", "chroma_": "memory", "redis_": "memory",
        "neo4j_": "memory", "vm_": "memory", "kyu_": "memory",
        "email": "email", "gmail": "email", "send_email": "email", "read_email": "email",
        "sheets_": "google", "docs_": "google", "slides_": "google", "drive_": "google",
        "calendar_": "google", "tasks_": "google", "photos_": "google", "forms_": "google",
        "analytics_": "google", "searchconsole_": "google", "books_": "google",
        "people_": "google", "bigquery_": "google", "storage_": "google", "firestore_": "google",
        "youtube_": "google", "translate_": "google", "tts_": "voice", "stt_": "voice",
        "maps_": "google", "nlp_": "nlp",
        "wifi_": "security", "network_": "security", "arp_": "security",
        "traceroute": "security", "dns_": "security", "port_scan": "security",
        "ping_": "security", "ssl_": "security",
        "shodan_": "security", "whois_": "security", "geoip_": "security", "hibp_": "security",
        "metasploit_": "pentest", "msf_": "pentest", "pentest_": "pentest",
        "analyze_email": "security", "trace_email": "security", "detect_email": "security",
        "check_spf": "security", "check_dkim": "security", "check_dmarc": "security",
        "email_security": "security", "verify_email": "security",
        "email_disposable": "security", "email_full": "security", "email_domain": "security",
        "email_trace": "security", "behind_the_email": "security",
        "forensic_": "security",
        "agent_": "agents", "multi_agent": "agents", "friday_should": "agents",
        "friday_parse": "agents", "friday_key": "agents", "friday_workflow": "agents",
        "friday_multi": "agents", "friday_quick": "agents", "close_all_agent": "agents",
        "ecosystem_": "system", "proactive_": "system", "predictive_": "system",
        "reflection_": "system", "context_": "system", "monitor_": "system",
        "dream_": "system", "scheduler_": "system", "skills_": "system",
        "self_improve": "system", "auto_update": "system", "crash_": "system",
        "pr_manager": "github", "protector_": "system",
        "deep_code_review": "code", "code_review_report": "code",
        "workflow_tool": "workflow", "plugin_tool": "plugins",
        "knowledge_graph": "knowledge",
        "mcp_": "mcp", "episodic_": "memory", "authority_": "system",
        "snapshot_": "system", "sidecar_": "system", "autonomy_": "system",
        "capabilities_": "system", "ironman_": "system",
        "memory_tree": "memory", "model_router": "ai", "extension_registry": "system",
        "diagnostics_": "system", "health_monitor": "health",
        "cookbook_": "system", "show_pointer": "ui", "show_cursor": "ui",
        "show_annotation": "ui", "clear_overlays": "ui",
        "social_analyzer": "osint", "instagram_": "osint", "twitter_": "osint",
        "facebook_": "osint", "linkedin_": "osint", "tiktok_": "osint",
        "telegram_": "osint", "reddit_": "osint",
        "holehe_": "osint", "email_rep": "osint", "username_search": "osint",
        "phone_": "osint", "dns_enum": "osint", "dns_bruteforce": "osint",
        "dns_zone": "osint", "dns_reverse": "osint",
        "spf_check": "osint", "dkim_check": "osint", "dmarc_check": "osint",
        "mx_lookup": "osint", "whatweb": "osint", "whatcms": "osint",
        "cdn_detect": "osint", "web_server_headers": "osint",
        "urlscan_": "osint", "virus_total": "osint",
        "wayback_": "osint", "leak_check": "osint", "intelx_": "osint", "dehashed_": "osint",
        "ip_": "osint", "domain_": "osint", "certificate_": "osint",
        "web_crawl": "osint", "email_extractor": "osint", "meta_extractor": "osint",
        "page_text": "osint", "security_headers": "osint", "cors_check": "osint",
        "hsts_check": "osint", "robots_txt": "osint",
        "btc_": "osint", "eth_": "osint",
        "format_osint": "osint", "summarize_osint": "osint", "osint_to_": "osint",
        "generate_smart": "security", "wifi_smart": "security", "wifi_capture": "security",
        "wifi_crack_handshake": "security", "download_wordlist": "security",
        "wordlist_stats": "security", "wifi_detect": "security",
        "wifi_list": "security", "wifi_show": "security", "wifi_scan": "security",
        "wifi_connection": "security", "wifi_crack": "security", "wifi_interface": "security",
        "wifi_all": "security",
        "generate_": "system", "see_screen": "vision", "open_url": "system",
        "climb_codebase": "code", "situational_awareness": "system",
        "get_time": "system", "open_roblox": "system", "open_microsoft": "system",
        "netflix_": "entertainment", "alexa_": "smart_home", "tell_alexa": "smart_home",
        "home_assistant": "smart_home", "smart_home": "smart_home",
        "queue_": "system", "multi_task": "system",
        "message_channel": "comms", "send_notification": "comms",
        "get_pending": "comms", "clear_notifications": "comms",
        "google_authorize": "google", "exchange_oauth": "google",
        "search_browser": "browser", "open_history": "browser",
        "stayfree_": "browser", "send_instagram": "social",
        "read_discord": "social", "read_slack": "social",
        "video_search": "search", "opencli_init": "browser",
    }
    for pattern, cat in categories.items():
        if pattern in name:
            return cat
    return "other"


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
    action: str
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

    try:
        import google.genai as genai
        from google.genai import types
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            for line in open(os.path.join(ROOT, ".env"), "r").readlines() if os.path.exists(os.path.join(ROOT, ".env")) else []:
                if line.strip().startswith("GEMINI_API_KEY=") or line.strip().startswith("GOOGLE_API_KEY="):
                    api_key = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                    break

        if api_key:
            client = genai.Client(api_key=api_key)
            tool_decls = _build_tools()

            contents = [types.Content(role="user", parts=[types.Part.from_text(text=message)])]

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    tools=tool_decls if tool_decls else None,
                    system_instruction="You are FRIDAY, an AI assistant. You have access to 500+ tools. Use them to help the user. Be concise and helpful. Always use tools when the user asks you to do something.",
                ),
            )

            text_parts = []
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if part.text:
                        text_parts.append(part.text)
                    if part.function_call:
                        fc = part.function_call
                        args = dict(fc.args) if fc.args else {}
                        result = await execute_tool(fc.name, args)
                        text_parts.append(f"[Used tool: {fc.name}]")

            reply = " ".join(text_parts) if text_parts else "I processed your request, sir."
        else:
            reply = _fallback_chat(message)

    except Exception as e:
        reply = _fallback_chat(message)

    system_state["chat_history"].append({
        "role": "assistant", "message": reply, "timestamp": datetime.now().isoformat(),
    })
    return reply


def _fallback_chat(message: str) -> str:
    msg = message.lower().strip()
    if any(w in msg for w in ["status", "how are you"]):
        uptime = time.time() - system_state.get("start_time", time.time())
        return f"All systems operational, sir. Uptime: {int(uptime//3600)}h {int((uptime%3600)//60)}m. {len(TOOL_MAP)} tools loaded and ready."
    elif any(w in msg for w in ["tools", "what can you do"]):
        cats = {}
        for name in TOOL_MAP:
            cat = _categorize(name)
            cats[cat] = cats.get(cat, 0) + 1
        top = ", ".join(f"{v} {k}" for k, v in sorted(cats.items(), key=lambda x: -x[1])[:10])
        return f"I have {len(TOOL_MAP)} tools across {len(cats)} categories: {top}. Ask me anything."
    elif any(w in msg for w in ["hello", "hi", "hey"]):
        return "Good evening, sir. All systems operational. How may I assist you tonight?"
    elif any(w in msg for w in ["who are you"]):
        return "I am FRIDAY — your Fully Responsive Intelligent Digital Assistant Youth. I have 500+ tools covering voice, vision, security, research, code, OSINT, Google, GitHub, browser, desktop, and more."
    elif any(w in msg for w in ["memory", "remember"]):
        from friday.autonomous_memory import autonomous_memory_tool
        raw = autonomous_memory_tool(action="stats")
        import json as _json
        d = _json.loads(raw) if isinstance(raw, str) else raw
        return f"Memory: {d.get('total_memories', 0)} memories, {d.get('total_entities', 0)} entities, {d.get('total_relationships', 0)} relationships."
    elif any(w in msg for w in ["agent", "townhall"]):
        from friday.townhall_agents import townhall_tool
        raw = townhall_tool(action="status")
        import json as _json
        d = _json.loads(raw) if isinstance(raw, str) else raw
        return f"Townhall: {d.get('active_sessions', 0)} active sessions, {d.get('agents_registered', 0)} agents, {d.get('total_messages', 0)} messages."
    else:
        return f"I understand, sir. Processing '{message[:50]}'. I have {len(TOOL_MAP)} tools available — ask me to use any of them."


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
    result = await execute_tool(call.tool, call.params or {})
    return result

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
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {}

@app.get("/api/memory/entities")
async def memory_entities():
    from friday.autonomous_memory import autonomous_memory_tool
    raw = autonomous_memory_tool(action="entities", limit=100)
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {}

@app.get("/api/memory/graph")
async def memory_graph():
    from friday.autonomous_memory import autonomous_memory_tool
    raw = autonomous_memory_tool(action="graph")
    try:
        d = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        d = {}
    if not d.get("nodes"):
        ent_raw = autonomous_memory_tool(action="entities", limit=50)
        try:
            ent_d = json.loads(ent_raw) if isinstance(ent_raw, str) else ent_raw
        except Exception:
            ent_d = {}
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
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {}

@app.post("/api/memory/learn")
async def memory_learn(msg: ChatMessage):
    from friday.autonomous_memory import autonomous_memory_tool
    raw = autonomous_memory_tool(action="learn", text=msg.message, source="ui")
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {}

@app.get("/api/townhall/status")
async def townhall_status():
    from friday.townhall_agents import townhall_tool
    raw = townhall_tool(action="status")
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {}

@app.get("/api/townhall/sessions")
async def townhall_sessions():
    from friday.townhall_agents import townhall_tool
    raw = townhall_tool(action="list_sessions")
    try:
        d = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        d = {}
    return {"sessions": d.get("sessions", []) if isinstance(d, dict) else []}

@app.get("/api/townhall/agents")
async def townhall_agents():
    from friday.townhall_agents import townhall_tool
    raw = townhall_tool(action="list_agents")
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {}

@app.get("/api/townhall/agenda")
async def townhall_agenda():
    from friday.townhall_agents import townhall_tool
    raw = townhall_tool(action="list_agenda")
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {}

@app.get("/api/services")
async def services():
    return {"total_tools": len(TOOL_MAP), "categories": len(set(_categorize(n) for n in TOOL_MAP))}

@app.get("/api/agents")
async def agents():
    from friday.bootstrap import bootstrap_tool
    raw = bootstrap_tool(action="status")
    try:
        d = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        d = {}
    return {"active_agents": d.get("townhall", {}).get("active_agents", 0),
            "sessions": d.get("townhall", {}).get("sessions", 0),
            "tools_count": len(TOOL_MAP)}

@app.get("/api/codebase")
async def codebase():
    from friday.codebase_analyzer import codebase_analyzer_tool
    raw = codebase_analyzer_tool(action="stats")
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {}

@app.get("/api/git/status")
async def git_status():
    from friday.git_operations import git_operations_tool
    raw = git_operations_tool(action="status")
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {}

@app.get("/api/git/log")
async def git_log():
    from friday.git_operations import git_operations_tool
    raw = git_operations_tool(action="log", count=10)
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {}

@app.get("/api/health/status")
async def health_status():
    from friday.health_monitor import health_monitor_tool
    raw = health_monitor_tool(action="status")
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {}

@app.get("/api/security/stats")
async def security_stats():
    from friday.security_scanner import security_scanner_tool
    raw = security_scanner_tool(action="stats")
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {}

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
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {}

@app.get("/api/workflows")
async def workflows():
    from friday.workflow_engine import workflow_tool
    raw = workflow_tool(action="list")
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {}

@app.get("/api/plugins")
async def plugins():
    from friday.plugins import plugin_tool
    raw = plugin_tool(action="list")
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {}

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
    print("=" * 60)
    print("  F.R.I.D.A.Y. — Fully Responsive Intelligent Digital Assistant Youth")
    print(f"  Version 4.0.0 | {len(TOOL_MAP)} tools loaded")
    print("=" * 60)
    print(f"  Dashboard:    http://localhost:8000")
    print(f"  API Docs:     http://localhost:8000/docs")
    print(f"  WebSocket:    ws://localhost:8000/ws")
    print(f"  Session:      {system_state.get('id', '---')}")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
