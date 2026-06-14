"""FRIDAY JARVIS — Backend API Server."""
import os
import sys
import json
import time
import uuid
import psutil
import platform
from datetime import datetime
from typing import Optional, Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
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

app = FastAPI(title="F.R.I.D.A.Y. API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

connected_clients: List[WebSocket] = []
system_state: Dict[str, Any] = {}


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
            elif msg.get("type") == "heartbeat":
                await ws.send_json({"type": "heartbeat", "status": "alive"})
    except WebSocketDisconnect:
        connected_clients.remove(ws)


async def broadcast(msg: dict):
    for client in connected_clients[:]:
        try:
            await client.send_json(msg)
        except Exception:
            connected_clients.remove(client)


def process_chat(message: str) -> str:
    msg = message.lower().strip()
    system_state.setdefault("chat_history", []).append({"role": "user", "message": message})

    if any(w in msg for w in ["status", "how are you", "how's it going"]):
        uptime = time.time() - system_state.get("start_time", time.time())
        hours = int(uptime // 3600)
        mins = int((uptime % 3600) // 60)
        response = f"All systems operational, sir. Uptime: {hours}h {mins}m. Memory: {get_memory_usage()}MB."
    elif any(w in msg for w in ["tools", "what can you do"]):
        response = "I manage %d tools across %d categories. I can validate code, analyze codebases, manage workflows, review code, and coordinate autonomous agents." % (380, 10)
    elif any(w in msg for w in ["memory", "remember"]):
        raw = autonomous_memory_tool(action="stats")
        d = _safe_json(raw)
        response = f"My memory contains {d.get('total_memories', 0)} memories across {d.get('total_entities', 0)} entities. {d.get('total_relationships', 0)} relationships stored."
    elif any(w in msg for w in ["agent", "townhall", "deliberate"]):
        raw = bootstrap_tool(action="status")
        d = _safe_json(raw)
        agents = d.get("townhall", {}).get("active_agents", 0)
        response = f"Currently tracking {agents} active agents. Townhall deliberations are proceeding normally."
    elif any(w in msg for w in ["review", "code review"]):
        response = "Ready to review code, sir. Submit your code and I will analyze it for security vulnerabilities, performance issues, style violations, and potential bugs."
    elif any(w in msg for w in ["workflow", "pipeline"]):
        raw = workflow_tool(action="list")
        d = _safe_json(raw)
        count = len(d.get('workflows', []))
        response = f"I have {count} workflows available. I can create custom pipelines for any task."
    elif any(w in msg for w in ["hello", "hi", "hey"]):
        response = "Good evening, sir. How may I assist you tonight?"
    elif any(w in msg for w in ["who are you", "what are you"]):
        response = "I am FRIDAY — your Fully Responsive Intelligent Digital Assistant Youth. I manage your systems, analyze your code, and coordinate your agents."
    else:
        response = "I understand, sir. Processing your request. You can ask me about status, tools, memory, agents, code review, or workflows."

    system_state["chat_history"].append({"role": "assistant", "message": response})
    return response


def get_memory_usage() -> int:
    try:
        return int(psutil.Process().memory_info().rss / 1024 / 1024)
    except Exception:
        return 0


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "uptime": time.time() - system_state.get("start_time", time.time())}


@app.get("/api/system")
async def system_info():
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.1)
    disk = psutil.disk_usage("/" if os.name != "nt" else "C:\\")
    uptime = time.time() - system_state.get("start_time", time.time())

    bootstrap_raw = bootstrap_tool(action="status")
    bootstrap_status = _safe_json(bootstrap_raw)
    memory_raw = autonomous_memory_tool(action="stats")
    memory_stats = _safe_json(memory_raw)

    return {
        "hostname": platform.node(),
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "cpu_percent": cpu,
        "memory_total_gb": round(mem.total / 1024**3, 1),
        "memory_used_gb": round(mem.used / 1024**3, 1),
        "memory_percent": mem.percent,
        "disk_total_gb": round(disk.total / 1024**3, 1),
        "disk_used_gb": round(disk.used / 1024**3, 1),
        "disk_percent": disk.percent,
        "uptime_seconds": int(uptime),
        "uptime_formatted": "%dh %dm" % (int(uptime // 3600), int((uptime % 3600) // 60)),
        "services": bootstrap_status.get("services", {}),
        "memory_entities": memory_stats.get("entities", 0),
        "memory_topics": memory_stats.get("topics", 0),
        "session_id": system_state.get("id"),
    }


@app.get("/api/services")
async def services():
    raw = bootstrap_tool(action="status")
    status = _safe_json(raw)
    return {
        "services": status.get("services", {}),
        "total_tools": 380,
        "categories": 10,
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
    result = autonomous_memory_tool(action="recall", query="", limit=10)
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except Exception:
            result = []
    return {"items": result if isinstance(result, list) else []}


@app.get("/api/codebase")
async def codebase():
    raw = codebase_analyzer_tool(action="stats")
    return _safe_json(raw)


@app.post("/api/chat")
async def chat(msg: ChatMessage):
    response = process_chat(msg.message)
    return {"response": response}


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
    }
    tool_fn = tools.get(call.tool)
    if not tool_fn:
        return JSONResponse(status_code=400, content={"error": f"Unknown tool: {call.tool}"})
    try:
        result = tool_fn(action=call.action, **(call.params or {}))
        return {"result": _safe_json(result) if isinstance(result, (str, dict, list)) else result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


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
    return _safe_json(logging_tool(action="get_recent", count=100))


@app.get("/api/logs/stats")
async def logs_stats():
    return _safe_json(logging_tool(action="stats"))


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
    print("[FRIDAY] Starting F.R.I.D.A.Y. API Server...")
    print("[FRIDAY] http://localhost:8000")
    print("[FRIDAY] Docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
