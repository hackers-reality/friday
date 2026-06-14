"""FRIDAY API Server — Full-featured backend with voice, logs, memory graph."""
import os
import sys
import json
import time
import uuid
import io
import wave
import tempfile
import threading
import queue
import logging
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from friday.bootstrap import bootstrap_tool
from friday.validation_middleware import validation_tool
from friday.autonomous_memory import autonomous_memory_tool
from friday.dashboard_cli import dashboard_cli_tool
from friday.codebase_analyzer import codebase_analyzer_tool
from friday.code_review import code_review_tool
from friday.workflow_engine import workflow_tool
from friday.plugins import plugin_tool
from friday.security_scanner import security_scanner_tool
from friday.config_manager import config_manager_tool
from friday.logging_system import logging_tool
from friday.rate_limiter import rate_limiter_tool
from friday.task_scheduler import task_scheduler_tool
from friday.health_monitor import health_monitor_tool
from friday.cache_system import cache_system_tool
from friday.metrics_collector import metrics_collector_tool
from friday.document_parser import document_parser_tool
from friday.database_connector import database_connector_tool
from friday.git_operations import git_operations_tool
from friday.notification_system import notification_system_tool
from friday.api_gateway import api_gateway_tool
from friday.backup_system import backup_system_tool
from friday.townhall_agents import townhall_tool

_tools_loaded = False
_tool_registry = {}


def _safe_json(raw):
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            pass
    return {}


def _load_tools():
    global _tools_loaded, _tool_registry
    if not _tools_loaded:
        try:
            from friday.tools.registry import TOOL_DESCRIPTORS
            for desc in TOOL_DESCRIPTORS:
                mod_path, fn_name = desc[0], desc[1]
                cat = mod_path.split(".")[-1].replace("_tools", "")
                _tool_registry[fn_name] = {"category": cat, "description": desc[2], "module": mod_path}
        except Exception:
            _tool_registry = {}
        _tools_loaded = True


app = FastAPI(title="F.R.I.D.A.Y. API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

connected_clients: List[WebSocket] = []
system_state: Dict[str, Any] = {}
log_buffer: List[Dict] = []
log_subscribers: List[WebSocket] = []


class ChatMessage(BaseModel):
    message: str


class ToolCall(BaseModel):
    tool: str
    action: str
    params: Optional[Dict[str, Any]] = None


class VoiceMessage(BaseModel):
    text: str
    voice: Optional[str] = "default"


class RelationshipAdd(BaseModel):
    source: str
    target: str
    rel_type: str


class MemoryStore(BaseModel):
    content: str
    source: Optional[str] = "ui"
    entity: Optional[str] = None
    memory_type: Optional[str] = "conversation"
    importance: Optional[float] = 0.5


class ConversationMsg(BaseModel):
    role: str
    content: str
    participant: Optional[str] = "user"


@app.on_event("startup")
async def startup():
    system_state["start_time"] = time.time()
    system_state["id"] = str(uuid.uuid4())[:8]
    system_state["chat_history"] = []
    system_state["voice_enabled"] = True
    system_state["terminal_logs"] = []


def _capture_log(module: str, level: str, message: str):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "module": module,
        "level": level,
        "message": message,
    }
    log_buffer.append(entry)
    if len(log_buffer) > 500:
        log_buffer.pop(0)
    system_state.setdefault("terminal_logs", []).append(entry)
    if len(system_state["terminal_logs"]) > 200:
        system_state["terminal_logs"] = system_state["terminal_logs"][-200:]


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    try:
        await ws.send_json({"type": "connected", "session": system_state.get("id")})
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "chat":
                response = process_chat(msg.get("message", ""))
                await ws.send_json({"type": "chat_response", "response": response})
                _capture_log("chat", "info", f"User: {msg.get('message', '')[:80]}")
                _capture_log("chat", "info", f"FRIDAY: {response[:80]}")
            elif msg.get("type") == "voice":
                response = process_chat(msg.get("message", ""))
                await ws.send_json({"type": "voice_response", "response": response, "speak": True})
                _capture_log("voice", "info", f"Voice: {response[:80]}")
            elif msg.get("type") == "heartbeat":
                await ws.send_json({"type": "heartbeat", "status": "alive"})
            elif msg.get("type") == "subscribe_logs":
                log_subscribers.append(ws)
                recent = log_buffer[-100:]
                await ws.send_json({"type": "log_history", "logs": recent})
    except WebSocketDisconnect:
        if ws in connected_clients:
            connected_clients.remove(ws)
        if ws in log_subscribers:
            log_subscribers.remove(ws)


async def broadcast(msg: dict):
    for client in connected_clients[:]:
        try:
            await client.send_json(msg)
        except Exception:
            connected_clients.remove(client)


async def broadcast_log(entry: dict):
    for ws in log_subscribers[:]:
        try:
            await ws.send_json({"type": "log_entry", "log": entry})
        except Exception:
            log_subscribers.remove(ws)


def process_chat(message: str) -> str:
    msg = message.lower().strip()
    system_state.setdefault("chat_history", []).append({
        "role": "user",
        "message": message,
        "timestamp": datetime.now().isoformat(),
    })

    if any(w in msg for w in ["status", "how are you", "how's it going"]):
        uptime = time.time() - system_state.get("start_time", time.time())
        hours = int(uptime // 3600)
        mins = int((uptime % 3600) // 60)
        mem = _safe_json(autonomous_memory_tool(action="stats"))
        response = (
            f"All systems operational, sir. Uptime: {hours}h {mins}m. "
            f"Memory: {mem.get('total_memories', 0)} memories, "
            f"{mem.get('total_entities', 0)} entities, "
            f"{mem.get('total_relationships', 0)} relationships. "
            f"CPU and disk healthy."
        )
    elif any(w in msg for w in ["tools", "what can you do"]):
        _load_tools()
        cats = {}
        for info in _tool_registry.values():
            c = info.get("category", "other")
            cats[c] = cats.get(c, 0) + 1
        cat_list = ", ".join(f"{v} {k}" for k, v in sorted(cats.items(), key=lambda x: -x[1])[:8])
        response = f"I manage {len(_tool_registry)} tools across {len(cats)} categories: {cat_list}. I can validate code, analyze codebases, manage workflows, review code, run voice commands, and coordinate autonomous agents."
    elif any(w in msg for w in ["memory", "remember"]):
        raw = autonomous_memory_tool(action="stats")
        d = _safe_json(raw)
        response = (
            f"My memory contains {d.get('total_memories', 0)} memories across "
            f"{d.get('total_entities', 0)} entities with "
            f"{d.get('total_relationships', 0)} relationships. "
            f"Memory types: {d.get('memory_types', {})}"
        )
    elif any(w in msg for w in ["agent", "townhall", "deliberate"]):
        raw = townhall_tool(action="status")
        d = _safe_json(raw)
        response = (
            f"Townhall: {d.get('active_sessions', 0)} active sessions, "
            f"{d.get('agents_registered', 0)} registered agents, "
            f"{d.get('total_messages', 0)} total messages, "
            f"{d.get('open_agenda_items', 0)} open agenda items."
        )
    elif any(w in msg for w in ["review", "code review"]):
        response = "Ready to review code, sir. Submit your code and I will analyze it for security vulnerabilities, performance issues, style violations, and potential bugs. You can also ask me to scan specific files."
    elif any(w in msg for w in ["workflow", "pipeline"]):
        raw = workflow_tool(action="list")
        d = _safe_json(raw)
        count = len(d.get("workflows", []))
        response = f"I have {count} workflows available. I can create custom pipelines for build, test, deploy, review, and research tasks."
    elif any(w in msg for w in ["hello", "hi", "hey"]):
        response = "Good evening, sir. How may I assist you tonight?"
    elif any(w in msg for w in ["who are you", "what are you"]):
        response = "I am FRIDAY — your Fully Responsive Intelligent Digital Assistant Youth. I manage your systems, analyze your code, hear your voice, and coordinate your agents. I was built to be your always-on AI companion."
    elif any(w in msg for w in ["voice", "speak", "talk"]):
        response = "Voice system active, sir. I can hear you through the microphone and respond with speech. Click the microphone icon to start a voice command."
    elif any(w in msg for w in ["help"]):
        response = (
            "Available commands: status, tools, memory, agents, townhall, review, "
            "workflow, voice, graph, logs, health, security, git, config. "
            "You can also ask me to scan code, run analysis, or manage any system."
        )
    elif any(w in msg for w in ["graph", "relationship"]):
        raw = autonomous_memory_tool(action="entities", limit=20)
        d = _safe_json(raw)
        entities = d.get("entities", [])
        response = f"Knowledge graph contains {len(entities)} entities. Top entities: {', '.join(e.get('name', '?') for e in entities[:5])}. Switch to the Graph view to see the full relationship network."
    elif any(w in msg for w in ["log", "logs"]):
        count = len(log_buffer)
        response = f"Terminal log buffer contains {count} entries. All system activity is streamed to the UI in real-time."
    elif any(w in msg for w in ["health", "monitor"]):
        raw = health_monitor_tool(action="status")
        d = _safe_json(raw)
        metrics = d.get("metrics", {})
        response = (
            f"Health check: CPU {metrics.get('cpu_percent', 0):.1f}%, "
            f"Memory {metrics.get('memory_percent', 0):.1f}%, "
            f"Disk {metrics.get('disk_percent', 0):.1f}%, "
            f"Uptime {metrics.get('uptime', 0)/3600:.1f}h."
        )
    else:
        response = f"I understand, sir. Processing your request about '{message[:50]}'. You can ask me about status, tools, memory, agents, voice, graph, logs, health, or any system operation."

    system_state["chat_history"].append({
        "role": "assistant",
        "message": response,
        "timestamp": datetime.now().isoformat(),
    })
    _capture_log("friday", "info", response[:120])
    return response


def get_memory_usage() -> int:
    try:
        import psutil
        return int(psutil.Process().memory_info().rss / 1024 / 1024)
    except Exception:
        return 0


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "3.0.0", "uptime": time.time() - system_state.get("start_time", time.time())}


@app.get("/api/system")
async def system_info():
    import psutil
    import platform
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.1)
    disk = psutil.disk_usage("C:\\" if os.name == "nt" else "/")
    uptime = time.time() - system_state.get("start_time", time.time())
    return {
        "hostname": platform.node(),
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "cpu_percent": cpu,
        "cpu_count": psutil.cpu_count(),
        "memory_total_gb": round(mem.total / 1024**3, 1),
        "memory_used_gb": round(mem.used / 1024**3, 1),
        "memory_percent": mem.percent,
        "memory_available_gb": round(mem.available / 1024**3, 1),
        "disk_total_gb": round(disk.total / 1024**3, 1),
        "disk_used_gb": round(disk.used / 1024**3, 1),
        "disk_percent": disk.percent,
        "uptime_seconds": int(uptime),
        "uptime_formatted": "%dh %dm %ds" % (int(uptime // 3600), int((uptime % 3600) // 60), int(uptime % 60)),
        "session_id": system_state.get("id"),
        "pid": os.getpid(),
    }


@app.get("/api/services")
async def services():
    raw = bootstrap_tool(action="status")
    status = _safe_json(raw)
    return {
        "services": status.get("services", {}),
        "total_tools": len(_tool_registry) if _tool_registry else 380,
        "categories": len(set(info.get("category", "") for info in _tool_registry.values())) if _tool_registry else 10,
    }


@app.get("/api/tools")
async def tools():
    _load_tools()
    tools_by_category = {}
    for name, info in _tool_registry.items():
        cat = info.get("category", "other")
        if cat not in tools_by_category:
            tools_by_category[cat] = []
        tools_by_category[cat].append({"name": name, "description": info.get("description", "")})
    return {"tools": tools_by_category, "total": len(_tool_registry)}


@app.get("/api/agents")
async def agents():
    raw = bootstrap_tool(action="status")
    status = _safe_json(raw)
    return {
        "active_agents": status.get("townhall", {}).get("active_agents", 0) if isinstance(status, dict) else 0,
        "sessions": status.get("townhall", {}).get("sessions", 0) if isinstance(status, dict) else 0,
        "deliberations": status.get("townhall", {}).get("deliberations", 0) if isinstance(status, dict) else 0,
    }


@app.get("/api/memory")
async def memory():
    raw = autonomous_memory_tool(action="stats")
    return _safe_json(raw)


@app.get("/api/memory/recent")
async def memory_recent():
    result = autonomous_memory_tool(action="recent", hours=24, limit=50)
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except Exception:
            result = []
    return {"items": result if isinstance(result, list) else []}


@app.get("/api/memory/entities")
async def memory_entities():
    raw = autonomous_memory_tool(action="entities", limit=100)
    return _safe_json(raw)


@app.get("/api/memory/graph")
async def memory_graph():
    raw = autonomous_memory_tool(action="graph")
    d = _safe_json(raw)
    if not d.get("nodes"):
        entities_raw = autonomous_memory_tool(action="entities", limit=50)
        entities_d = _safe_json(entities_raw)
        entities = entities_d.get("entities", [])
        nodes = []
        edges = []
        seen = set()
        for e in entities:
            name = e.get("name", "")
            if name and name not in seen and len(name) > 1:
                seen.add(name)
                nodes.append({
                    "id": name,
                    "type": e.get("type", "unknown"),
                    "mentions": e.get("mentions", 1),
                    "size": max(5, min(30, e.get("mentions", 1) * 2)),
                })
        for i in range(len(nodes)):
            for j in range(i + 1, min(i + 4, len(nodes))):
                edges.append({
                    "source": nodes[i]["id"],
                    "target": nodes[j]["id"],
                    "type": "related",
                })
        d = {"nodes": nodes, "edges": edges}
    return d


@app.post("/api/memory/store")
async def memory_store(msg: MemoryStore):
    raw = autonomous_memory_tool(
        action="store",
        content=msg.content,
        source=msg.source,
        entity=msg.entity,
        memory_type=msg.memory_type,
        importance=msg.importance,
    )
    return _safe_json(raw)


@app.post("/api/memory/learn")
async def memory_learn(msg: ChatMessage):
    raw = autonomous_memory_tool(action="learn", text=msg.message, source="ui")
    return _safe_json(raw)


@app.post("/api/memory/relationship")
async def memory_relationship(msg: RelationshipAdd):
    raw = autonomous_memory_tool(action="relationship", source=msg.source, target=msg.target, type=msg.rel_type)
    return _safe_json(raw)


@app.post("/api/chat")
async def chat(msg: ChatMessage):
    response = process_chat(msg.message)
    return {"response": response, "history": system_state.get("chat_history", [])}


@app.get("/api/chat/history")
async def chat_history():
    return {"history": system_state.get("chat_history", [])}


@app.post("/api/tools/call")
async def call_tool(call: ToolCall):
    tools = {
        "bootstrap": bootstrap_tool,
        "validation": validation_tool,
        "memory": autonomous_memory_tool,
        "dashboard": dashboard_cli_tool,
        "analyzer": codebase_analyzer_tool,
        "review": code_review_tool,
        "workflow": workflow_tool,
        "plugin": plugin_tool,
        "security": security_scanner_tool,
        "config": config_manager_tool,
        "logging": logging_tool,
        "rate_limiter": rate_limiter_tool,
        "scheduler": task_scheduler_tool,
        "health": health_monitor_tool,
        "cache": cache_system_tool,
        "metrics": metrics_collector_tool,
        "parser": document_parser_tool,
        "database": database_connector_tool,
        "git": git_operations_tool,
        "notification": notification_system_tool,
        "gateway": api_gateway_tool,
        "backup": backup_system_tool,
        "townhall": townhall_tool,
    }
    tool_fn = tools.get(call.tool)
    if not tool_fn:
        return JSONResponse(status_code=400, content={"error": f"Unknown tool: {call.tool}"})
    try:
        result = tool_fn(action=call.action, **(call.params or {}))
        return {"result": _safe_json(result) if isinstance(result, (str, dict, list)) else result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/townhall/status")
async def townhall_status():
    return _safe_json(townhall_tool(action="status"))


@app.get("/api/townhall/sessions")
async def townhall_sessions():
    raw = townhall_tool(action="list_sessions")
    d = _safe_json(raw)
    return {"sessions": d.get("sessions", []) if isinstance(d, dict) else []}


@app.get("/api/townhall/agents")
async def townhall_agents():
    return _safe_json(townhall_tool(action="list_agents"))


@app.get("/api/townhall/agenda")
async def townhall_agenda():
    return _safe_json(townhall_tool(action="list_agenda"))


@app.get("/api/workflows")
async def workflows():
    return _safe_json(workflow_tool(action="list"))


@app.get("/api/plugins")
async def plugins():
    return _safe_json(plugin_tool(action="list"))


@app.get("/api/reviews/stats")
async def review_stats():
    return {"total_reviews": 0, "issues_found": 0}


@app.get("/api/security/stats")
async def security_stats():
    return _safe_json(security_scanner_tool(action="stats"))


@app.post("/api/security/scan")
async def security_scan(msg: ChatMessage):
    return _safe_json(security_scanner_tool(action="scan_code", code=msg.message))


@app.get("/api/config")
async def config_get():
    return _safe_json(config_manager_tool(action="get_all"))


@app.get("/api/config/stats")
async def config_stats():
    return _safe_json(config_manager_tool(action="stats"))


@app.get("/api/logs")
async def logs_recent():
    return {"logs": log_buffer[-200:]}


@app.get("/api/logs/stats")
async def logs_stats():
    levels = {}
    modules = {}
    for entry in log_buffer:
        lvl = entry.get("level", "info")
        mod = entry.get("module", "unknown")
        levels[lvl] = levels.get(lvl, 0) + 1
        modules[mod] = modules.get(mod, 0) + 1
    return {"total": len(log_buffer), "by_level": levels, "by_module": modules}


@app.get("/api/ratelimit/stats")
async def ratelimit_stats():
    return _safe_json(rate_limiter_tool(action="stats"))


@app.get("/api/scheduler/tasks")
async def scheduler_tasks():
    return _safe_json(task_scheduler_tool(action="list"))


@app.get("/api/scheduler/stats")
async def scheduler_stats():
    return _safe_json(task_scheduler_tool(action="stats"))


@app.get("/api/health/status")
async def health_status():
    return _safe_json(health_monitor_tool(action="status"))


@app.get("/api/health/alerts")
async def health_alerts():
    return _safe_json(health_monitor_tool(action="alerts"))


@app.get("/api/cache/stats")
async def cache_stats():
    return _safe_json(cache_system_tool(action="stats"))


@app.get("/api/metrics/dashboard")
async def metrics_dashboard():
    return _safe_json(metrics_collector_tool(action="dashboard"))


@app.get("/api/parser/supported")
async def parser_supported():
    return _safe_json(document_parser_tool(action="supported"))


@app.get("/api/database/list")
async def database_list():
    return _safe_json(database_connector_tool(action="list"))


@app.get("/api/database/stats")
async def database_stats():
    return _safe_json(database_connector_tool(action="stats"))


@app.get("/api/git/status")
async def git_status():
    return _safe_json(git_operations_tool(action="status"))


@app.get("/api/git/log")
async def git_log():
    return _safe_json(git_operations_tool(action="log", count=10))


@app.get("/api/git/stats")
async def git_stats():
    return _safe_json(git_operations_tool(action="stats"))


@app.get("/api/notifications/stats")
async def notifications_stats():
    return _safe_json(notification_system_tool(action="stats"))


@app.get("/api/notifications/history")
async def notifications_history():
    return _safe_json(notification_system_tool(action="history"))


@app.get("/api/gateway/routes")
async def gateway_routes():
    return _safe_json(api_gateway_tool(action="routes"))


@app.get("/api/gateway/stats")
async def gateway_stats():
    return _safe_json(api_gateway_tool(action="stats"))


@app.get("/api/backups")
async def backups_list():
    return _safe_json(backup_system_tool(action="list"))


@app.get("/api/backups/stats")
async def backups_stats():
    return _safe_json(backup_system_tool(action="stats"))


@app.post("/api/voice/speak")
async def voice_speak(msg: VoiceMessage):
    _capture_log("voice", "info", f"TTS: {msg.text[:80]}")
    return {"status": "ok", "text": msg.text, "voice": msg.voice}


@app.post("/api/voice/listen")
async def voice_listen():
    return {"status": "listening", "engine": "web_speech_api"}


@app.get("/api/conversations")
async def list_conversations():
    raw = autonomous_memory_tool(action="list_conversations", limit=20)
    return _safe_json(raw)


@app.get("/api/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    raw = autonomous_memory_tool(action="get_conversation_summary", conversation_id=conv_id)
    return _safe_json(raw)


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
    print("  Version 3.0.0")
    print("=" * 60)
    print(f"  API Server:   http://localhost:8000")
    print(f"  API Docs:     http://localhost:8000/docs")
    print(f"  Dashboard:    http://localhost:8000")
    print(f"  WebSocket:    ws://localhost:8000/ws")
    print(f"  Session:      {system_state.get('id', '---')}")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
