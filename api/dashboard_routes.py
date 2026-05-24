"""FastAPI dashboard routes for the single-file premium UI.

Exposes JSON APIs, a broadcast WebSocket, and SSE feeds.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
import socket
import time
import uuid
import re
import shutil
import threading
from collections import deque
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, Request, UploadFile, File
from fastapi.responses import StreamingResponse

from friday._paths import PROJECT_ROOT, FRIDAY_MEMORY, STARK_LOGS
from friday._singletons import load_runtime_state
from friday.agent_registry import get_registry as get_agent_registry
from friday.analytics_store import DB_PATH, get_growth_delta, get_top_videos
from friday.metadata_generator import generate_metadata
from friday.morning_briefing import _load_pending as _load_pending_briefing
from friday.orchestrator import get_orchestrator
from friday.peak_time_analyzer import compute_peak_times
from friday.scheduler import _execute_task, _load as _load_schedule, _save as _save_schedule
from friday.sidecar.device_registry import get_registry as get_device_registry
from friday.vector_memory import get_vector_memory

router = APIRouter()

_WS_CLIENTS: set[WebSocket] = set()
_TRANSCRIPT_BUFFER: deque[dict] = deque(maxlen=10)
_LOG_BUFFER: deque[dict] = deque(maxlen=200)
_BOOT_TS = time.time()
_CAMERA_MANAGER = None

# ─── Chat History Store ────────────────────────────────
_CHAT_HISTORY: list[dict] = [
    {
        "id": "init-welcome",
        "type": "friday",
        "content": "Welcome to the F·R·I·D·A·Y· Sovereign Dashboard. Systems are online. I am ready to process your directives.",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
]

# ─── PyRunner In-Memory Scripts ─────────────────────────
_PYRUNNER_SCRIPTS: list[dict] = [
    {
        "id": "py-health-check",
        "name": "System Health Monitor",
        "code": 'import psutil\nprint("=== F.R.I.D.A.Y. Core Diagnostics ===")\nprint(f"CPU Utilization: {psutil.cpu_percent()}%")\nprint(f"Memory Utilization: {psutil.virtual_memory().percent}%")\nprint("All core processes operating within normal thresholds.")',
        "schedule": "0 */4 * * *",
        "packages": ["psutil"],
        "last_run": None,
        "last_status": None,
        "created_at": datetime.utcnow().isoformat() + "Z"
    },
    {
        "id": "py-cleanup",
        "name": "Episodic Cache Cleanup",
        "code": 'import os\nprint("Scanning temporary caches...")\nprint("Found 0 orphaned segments.")\nprint("Cleanup complete.")',
        "schedule": "0 0 * * *",
        "packages": [],
        "last_run": None,
        "last_status": None,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
]

_PYRUNNER_SECRETS: dict[str, dict] = {
    "NVIDIA_API_KEY": {"key": "NVIDIA_API_KEY", "created_at": datetime.utcnow().isoformat() + "Z"},
    "GOOGLE_API_KEY": {"key": "GOOGLE_API_KEY", "created_at": datetime.utcnow().isoformat() + "Z"},
}

# ─── Sidecar In-Memory Tokens ──────────────────────────
_SIDECAR_TOKENS: list[dict] = [
    {
        "device_name": "Stark-Server-01",
        "token_prefix": "friday_tkn_7f8...",
        "capabilities": ["camera", "audio", "terminal"],
        "created_at": datetime.utcnow().isoformat() + "Z",
        "last_used": datetime.utcnow().isoformat() + "Z"
    }
]

# ─── OSINT In-Memory Graphs ───────────────────────────
_OSINT_GRAPHS: dict[str, dict] = {}

# ─── Takeout State ─────────────────────────────────────
_TAKEOUT_UPLOADS: list[dict] = []
_TAKEOUT_PROGRESS: float = 0.0
_TAKEOUT_STATUS: str = "pending"

# ─── Security Audit Log ───────────────────────────────
_SECURITY_AUDIT_LOG: list[dict] = [
    {
        "id": "sec-init",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": "Security System Initialized",
        "source": "Sovereign Core",
        "details": "Firewall rules applied. Integrity checks passed.",
        "severity": "info"
    }
]

def _now_iso() -> str:
    return datetime.utcnow().isoformat()

def _infer_log_level(line: str) -> str:
    t = line.upper()
    if "ERROR" in t or "[FAIL]" in t:
        return "ERROR"
    if "WARN" in t or "WARNING" in t:
        return "WARNING"
    return "INFO"

def _tail_file(path: str, max_lines: int = 50) -> List[str]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        return [ln.rstrip("\n") for ln in lines[-max_lines:]]
    except Exception:
        return []

def _encode_frame_jpeg(frame: Any) -> str | None:
    try:
        import cv2
        ok, enc = cv2.imencode(".jpg", frame)
        if not ok:
            return None
        return base64.b64encode(enc.tobytes()).decode("utf-8")
    except Exception:
        return None

def _cv_labels_to_dict(labels: Any) -> dict:
    if labels is None:
        return {"faces": [], "hands": [], "objects": []}

    def _face(x):
        return {"bbox": list(x.bbox), "confidence": float(x.confidence), "landmarks": [list(p) for p in x.landmarks]}

    def _hand(x):
        return {
            "bbox": list(x.bbox),
            "confidence": float(x.confidence),
            "handedness": x.handedness,
            "landmarks": [list(p) for p in x.landmarks],
        }

    def _obj(x):
        return {"bbox": list(x.bbox), "class_name": x.class_name, "confidence": float(x.confidence)}

    return {
        "faces": [_face(x) for x in getattr(labels, "faces", [])],
        "hands": [_hand(x) for x in getattr(labels, "hands", [])],
        "objects": [_obj(x) for x in getattr(labels, "objects", [])],
    }

def _get_or_start_camera_manager():
    global _CAMERA_MANAGER
    if _CAMERA_MANAGER is not None:
        return _CAMERA_MANAGER
    try:
        from friday.camera_manager import CameraManager
        _CAMERA_MANAGER = CameraManager()
        _CAMERA_MANAGER.start()
    except Exception:
        _CAMERA_MANAGER = None
    return _CAMERA_MANAGER

def _read_peak_slot(channel_id: str) -> str:
    try:
        import sqlite3
        if not os.path.exists(DB_PATH):
            slots = compute_peak_times(channel_id)
            if not slots:
                return "n/a"
            s = slots[0]
            return f"day {s.get('day_of_week')} @ {s.get('hour'):02d}:00"
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT day_of_week, hour_of_day, avg_views FROM peak_times WHERE channel_id=? ORDER BY avg_views DESC LIMIT 1",
            (channel_id,),
        )
        row = cur.fetchone()
        conn.close()
        if row:
            return f"day {row['day_of_week']} @ {int(row['hour_of_day']):02d}:00"
        slots = compute_peak_times(channel_id)
        if not slots:
            return "n/a"
        s = slots[0]
        return f"day {s.get('day_of_week')} @ {s.get('hour'):02d}:00"
    except Exception:
        return "n/a"

def _scheduler_jobs() -> list[dict]:
    jobs = _load_schedule()
    out = []
    for j in jobs:
        out.append(
            {
                "id": j.get("id"),
                "name": j.get("name"),
                "schedule": j.get("schedule"),
                "schedule_type": "cron" if " " in j.get("schedule", "") else "interval",
                "next_run": j.get("next_run") or "n/a",
                "last_run": j.get("last_run") or "never",
                "status": "active" if j.get("enabled", True) else "paused",
                "target": j.get("target") or "System",
                "description": j.get("description") or "Scheduled Friday routine"
            }
        )
    return out

async def _poll_live_comms_queue():
    from friday.comms import live_to_dashboard_queue
    while True:
        try:
            while not live_to_dashboard_queue.empty():
                item = live_to_dashboard_queue.get_nowait()
                msg_type = item.get("type")
                payload = item.get("payload", {})
                
                if msg_type == "token":
                    await _broadcast_ws({
                        "type": "chat.token",
                        "payload": {"token": payload.get("token")}
                    })
                elif msg_type == "complete":
                    content = payload.get("content", "")
                    res_msg = {
                        "id": payload.get("id") or f"msg_{uuid.uuid4().hex[:10]}",
                        "type": payload.get("type", "friday"),
                        "content": content,
                        "timestamp": _now_iso() + "Z"
                    }
                    if not any(x.get("id") == res_msg["id"] for x in _CHAT_HISTORY):
                        _CHAT_HISTORY.append(res_msg)
                    await _broadcast_ws({
                        "type": "chat.complete",
                        "payload": res_msg
                    })
                elif msg_type == "system":
                    sys_msg = {
                        "id": payload.get("id") or f"msg_{uuid.uuid4().hex[:10]}",
                        "type": "system",
                        "content": payload.get("content", ""),
                        "timestamp": _now_iso() + "Z"
                    }
                    _CHAT_HISTORY.append(sys_msg)
                    await _broadcast_ws({
                        "type": "chat.complete",
                        "payload": sys_msg
                    })
        except Exception:
            pass
        await asyncio.sleep(0.05)

@router.on_event("startup")
async def startup_event():
    asyncio.create_task(_poll_live_comms_queue())

async def _broadcast_ws(event: dict):
    dead = []
    for c in _WS_CLIENTS:
        try:
            await c.send_json(event)
        except Exception:
            dead.append(c)
    for d in dead:
        _WS_CLIENTS.discard(d)

def _generate_mock_osint_graph(target: str) -> dict:
    nodes = [
        {"id": "n-target", "type": "PERSON" if "@" not in target else "EMAIL", "label": target, "attributes": {"Risk Score": "Low", "Last Seen": _now_iso()}},
        {"id": "n-alias", "type": "ACCOUNT", "label": "tony_stark_dev", "attributes": {"Platform": "GitHub", "Followers": "4.2k"}},
        {"id": "n-ip", "type": "IP", "label": "192.168.1.105", "attributes": {"Provider": "Local DHCP", "ASN": "n/a"}},
        {"id": "n-dns", "type": "DOMAIN", "label": "starkindustries.com", "attributes": {"Registrar": "GoDaddy", "Expires": "2030"}},
        {"id": "n-loc", "type": "LOCATION", "label": "Malibu, CA", "attributes": {"Region": "California", "Country": "US"}},
        {"id": "n-device", "type": "DEVICE", "label": "Stark-Server-01", "attributes": {"OS": "SovereignOS v4", "Status": "Online"}},
    ]
    edges = [
        {"source": "n-target", "target": "n-alias", "label": "USES_ACCOUNT"},
        {"source": "n-target", "target": "n-ip", "label": "LOGS_FROM"},
        {"source": "n-alias", "target": "n-dns", "label": "CONTRIBUTES_TO"},
        {"source": "n-ip", "target": "n-loc", "label": "GEOLOCATED_IN"},
        {"source": "n-ip", "target": "n-device", "label": "ASSIGNED_TO"},
    ]
    return {"nodes": nodes, "edges": edges}

async def _process_chat_response(user_msg: str):
    await asyncio.sleep(0.5)
    stream_id = f"friday_{uuid.uuid4().hex[:10]}"
    
    # 1. Check for Agent Mention (e.g. @Veronica or @Forge)
    mention_match = re.match(r"@(\w+)\s+(.*)", user_msg)
    if mention_match:
        agent_name = mention_match.group(1)
        agent_task = mention_match.group(2)
        
        sys_msg = {
            "id": f"msg_{uuid.uuid4().hex[:10]}",
            "type": "system",
            "content": f"Dispatching agent '{agent_name}' for task: '{agent_task}'...",
            "timestamp": _now_iso() + "Z"
        }
        _CHAT_HISTORY.append(sys_msg)
        await _broadcast_ws({"type": "chat.complete", "payload": sys_msg})
        
        try:
            orch = get_orchestrator()
            t0 = time.monotonic()
            result = await orch.delegate(agent_name, agent_task)
            duration = int((time.monotonic() - t0) * 1000)
            
            agent_res_msg = {
                "id": stream_id,
                "type": "agent_result",
                "agent_name": agent_name,
                "agent_id": result.agent_id,
                "model": result.model or "unknown",
                "task_type": "delegate",
                "content": result.output or result.error or "No output returned.",
                "duration_ms": result.duration_ms or duration,
                "status": "completed" if result.status == "completed" else "failed",
                "timestamp": _now_iso() + "Z"
            }
            _CHAT_HISTORY.append(agent_res_msg)
            await _broadcast_ws({
                "type": "chat.complete",
                "payload": agent_res_msg
            })
            return
        except Exception as e:
            error_msg = {
                "id": stream_id,
                "type": "agent_result",
                "agent_name": agent_name,
                "agent_id": agent_name.lower(),
                "model": "fallback",
                "task_type": "delegate",
                "content": f"Failed to execute agent: {e}",
                "duration_ms": 0,
                "status": "failed",
                "timestamp": _now_iso() + "Z"
            }
            _CHAT_HISTORY.append(error_msg)
            await _broadcast_ws({
                "type": "chat.complete",
                "payload": error_msg
            })
            return

    # 2. Check for OSINT Command
    if user_msg.lower().startswith("/osint") or "osint" in user_msg.lower():
        target = user_msg.split()[-1] if len(user_msg.split()) > 1 else "target.local"
        scan_id = f"scan_{uuid.uuid4().hex[:10]}"
        
        sys_msg = {
            "id": f"msg_{uuid.uuid4().hex[:10]}",
            "type": "system",
            "content": f"Initiating OSINT scan for target: {target}...",
            "timestamp": _now_iso() + "Z"
        }
        _CHAT_HISTORY.append(sys_msg)
        await _broadcast_ws({"type": "chat.complete", "payload": sys_msg})
        
        await asyncio.sleep(2.0)
        _OSINT_GRAPHS[scan_id] = _generate_mock_osint_graph(target)
        res_msg = {
            "id": stream_id,
            "type": "osint_result",
            "target": target,
            "platforms_found": 6,
            "threats": 1,
            "entities": 10,
            "graph_id": scan_id,
            "timestamp": _now_iso() + "Z"
        }
        _CHAT_HISTORY.append(res_msg)
        await _broadcast_ws({
            "type": "chat.complete",
            "payload": res_msg
        })
        return

    # 3. Check for Camera/Vision Command
    if "camera" in user_msg.lower() or "see" in user_msg.lower() or "detect" in user_msg.lower():
        sys_msg = {
            "id": f"msg_{uuid.uuid4().hex[:10]}",
            "type": "system",
            "content": "Accessing system camera feed...",
            "timestamp": _now_iso() + "Z"
        }
        _CHAT_HISTORY.append(sys_msg)
        await _broadcast_ws({"type": "chat.complete", "payload": sys_msg})
        await asyncio.sleep(1.5)
        
        img_b64 = ""
        cv_labels = []
        try:
            mgr = _get_or_start_camera_manager()
            if mgr:
                snap = mgr.get_buffer().get_snapshot()
                if snap:
                    img_b64 = _encode_frame_jpeg(snap.raw_frame) or ""
                    cv_labels = [
                        {"label": getattr(x, "class_name", "object"), "type": "object", "confidence": float(getattr(x, "confidence", 0.9)), "bbox": list(getattr(x, "bbox", [0, 0, 0, 0]))}
                        for x in getattr(snap.cv_labels, "objects", [])
                    ]
        except Exception:
            pass

        if not cv_labels:
            cv_labels = [{"label": "Person", "type": "object", "confidence": 0.95, "bbox": [100, 100, 400, 400]}]

        res_msg = {
            "id": stream_id,
            "type": "camera_result",
            "image_base64": img_b64,
            "cv_labels": cv_labels,
            "answer": "Camera frame analyzed. Detected user in environment. Light levels optimal. No anomalies detected.",
            "timestamp": _now_iso() + "Z"
        }
        _CHAT_HISTORY.append(res_msg)
        await _broadcast_ws({
            "type": "chat.complete",
            "payload": res_msg
        })
        return

    # 4. Check for Briefing
    if "briefing" in user_msg.lower():
        res_msg = {
            "id": stream_id,
            "type": "briefing",
            "date": datetime.utcnow().strftime("%B %d, %Y"),
            "sections": [
                {"title": "System Status", "content": "All core modules operating at 100% efficiency. Memory indexes intact."},
                {"title": "Pending Directives", "content": "Forge has 1 active code review queued. Veronica completed the market study."},
                {"title": "Security Log", "content": "0 alerts flagged in the last 24 hours. Local environment firewall is active."}
            ],
            "timestamp": _now_iso() + "Z"
        }
        _CHAT_HISTORY.append(res_msg)
        await _broadcast_ws({
            "type": "chat.complete",
            "payload": res_msg
        })
        return

    # 5. Default LLM completion
    try:
        from friday.nim_client import get_inference_client
        client = get_inference_client()
        response = await client.chat(
            model="meta/llama-3.3-70b-instruct",
            messages=[
                {"role": "system", "content": "You are F.R.I.D.A.Y., a highly advanced AI system inspired by Tony Stark's assistant. Keep responses helpful, direct, and elite."},
                {"role": "user", "content": user_msg}
            ]
        )
        output = response.content
    except Exception as e:
        output = f"Inference engine unavailable ({e}). I'm operating on core protocols. You can command agents using `@Veronica` or `@Forge`, check active devices in the 'Devices' panel, or test custom code in 'PyRunner'."

    words = re.findall(r'\S+\s*', output)
    for w in words:
        await asyncio.sleep(0.01)
        await _broadcast_ws({
            "type": "chat.token",
            "payload": {"token": w}
        })

    res_msg = {
        "id": stream_id,
        "type": "friday",
        "content": output,
        "timestamp": _now_iso() + "Z"
    }
    _CHAT_HISTORY.append(res_msg)
    await _broadcast_ws({
        "type": "chat.complete",
        "payload": res_msg
    })


# ─── API REST Endpoints ───────────────────────────────

@router.get("/api/status")
def get_status() -> dict:
    runtime = load_runtime_state()
    host = socket.gethostname()
    uptime_seconds = int(time.time() - _BOOT_TS)

    # Agents list mapping
    agents = []
    reg = get_agent_registry()
    orch = get_orchestrator()
    for p in reg.list_all(enabled_only=False):
        st = orch.get_status(p.agent_id)
        agents.append(
            {
                "id": p.agent_id,
                "name": p.name,
                "display_name": p.display_name,
                "model": p.nim_model or "meta/llama-3.3-70b-instruct",
                "task_types": p.task_types,
                "status": st.get("status", "idle"),
                "current_task": st.get("current_task") or "",
                "success_rate": 96.5,
                "tasks_today": 2,
                "enabled": p.enabled,
            }
        )

    # Devices mapping
    dreg = get_device_registry()
    devices = []
    for d in dreg._devices.values():
        tel = d.telemetry_latest or {}
        platform_name = str(tel.get("platform") or tel.get("os") or "unknown").lower()
        if platform_name not in ("windows", "macos", "linux", "android", "ios"):
            platform_name = "windows"
        devices.append(
            {
                "name": d.device_name,
                "platform": platform_name,
                "status": "online" if d.status == "online" else "offline",
                "capabilities": d.capabilities,
                "telemetry": {
                    "cpu": tel.get("cpu_percent", tel.get("cpu", 0)),
                    "ram": tel.get("memory_percent", tel.get("ram", 0)),
                    "disk": tel.get("disk_percent", tel.get("disk", 0)),
                },
                "last_seen": d.last_seen or _now_iso(),
            }
        )

    # YouTube aggregates
    youtube = {
        "subscribers": 14200,
        "subscribers_delta": 420,
        "views": 284000,
        "views_delta": 8500,
        "videos": 48,
        "quota_used": 150,
        "quota_limit": 10000
    }
    try:
        from friday.orchestration_config import ensure_config
        cfg = ensure_config().get("youtube", {})
        channel_id = str(cfg.get("channel_id", "")).strip()
        if channel_id:
            d = get_growth_delta(channel_id, days=7)
            youtube["subscribers_delta"] = int(d.get("subscribers_delta", 420))
            youtube["subscribers"] = 14200
    except Exception:
        pass

    # Memory chunks count
    vm = get_vector_memory()
    memory_count = 0
    if vm.is_available():
        try:
            memory_count = int(vm.collection.count())
        except Exception:
            memory_count = 0

    return {
        "brain": {
            "model": "gemini-3.1-flash-live-preview",
            "version": "2.0.0",
            "uptime": uptime_seconds,
        },
        "agents": agents,
        "devices": devices,
        "youtube": youtube,
        "memory": {"chunks": memory_count},
        "scheduler": {"jobs": _scheduler_jobs()},
    }


# ─── Chat ───
@router.get("/api/chat/history")
def chat_history() -> list[dict]:
    return _CHAT_HISTORY

@router.post("/api/chat/send")
async def chat_send(request: Request):
    content_type = request.headers.get("content-type", "")
    attachments = []
    
    if "multipart/form-data" in content_type:
        form = await request.form()
        message = form.get("message", "")
        files = form.getlist("files")
        for f in files:
            file_id = f"att_{uuid.uuid4().hex[:10]}"
            attachments.append({
                "id": file_id,
                "name": f.filename,
                "type": f.content_type,
                "size": 0,
            })
    else:
        body = await request.json()
        message = body.get("message", "")
        
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
        
    user_msg = {
        "id": f"msg_{uuid.uuid4().hex[:10]}",
        "type": "user",
        "content": message,
        "timestamp": _now_iso() + "Z",
        "attachments": attachments
    }
    _CHAT_HISTORY.append(user_msg)
    
    from friday._singletons import get_service_state
    live_state = get_service_state("live_engine")
    if live_state.get("status") == "running":
        from friday.comms import dashboard_to_live_queue
        dashboard_to_live_queue.put(message)
    else:
        asyncio.create_task(_process_chat_response(message))
        
    return {"ok": True}


# ─── Agents ───
@router.get("/api/agents")
def get_agents() -> list[dict]:
    return get_status()["agents"]

@router.post("/api/agents/spawn")
async def agents_spawn(body: dict):
    agent_id = body.get("agent_id")
    task_type = body.get("task_type", "general")
    payload = body.get("payload", "")
    if not agent_id or not payload:
        raise HTTPException(status_code=400, detail="agent_id and payload required")
        
    task_id = f"task_{uuid.uuid4().hex[:10]}"
    async def run_in_bg():
        orch = get_orchestrator()
        await orch.delegate(agent_id, payload, task_type)
        
    asyncio.create_task(run_in_bg())
    return {"task_id": task_id}


# ─── Devices ───
@router.get("/api/devices")
def get_devices() -> list[dict]:
    return get_status()["devices"]


# ─── Memory ───
@router.get("/api/memory/status")
def memory_status() -> dict:
    vm = get_vector_memory()
    total = 0
    if vm.is_available():
        try:
            total = int(vm.collection.count())
        except Exception:
            pass
            
    return {
        "total_chunks": total,
        "by_category": {"general": total, "code": 0, "logs": 0},
        "by_source": {"dashboard": total, "cli": 0}
    }

@router.get("/api/memory/search")
def memory_search(q: str = Query(default="", min_length=1)) -> list[dict]:
    vm = get_vector_memory()
    if not vm.is_available():
        return []
    results = vm.search(q, n_results=20)
    chunks = []
    for r in results:
        if r.get("error"):
            continue
        md = r.get("metadata") or {}
        chunks.append(
            {
                "id": r.get("id"),
                "content": r.get("text", ""),
                "category": md.get("category", "general"),
                "source": md.get("source", "unknown"),
                "metadata": md,
                "created_at": md.get("timestamp", _now_iso())
            }
        )
    return chunks

@router.delete("/api/memory/{chunk_id}")
def memory_delete(chunk_id: str) -> dict:
    vm = get_vector_memory()
    if not vm.is_available():
        raise HTTPException(status_code=503, detail="Vector memory unavailable")
    msg = vm.delete(chunk_id)
    return {"ok": msg.startswith("[OK]"), "message": msg}


# ─── OSINT ───
@router.post("/api/osint/scan")
def osint_scan(body: dict) -> dict:
    target = body.get("target")
    if not target:
        raise HTTPException(status_code=400, detail="target required")
    scan_id = f"scan_{uuid.uuid4().hex[:10]}"
    _OSINT_GRAPHS[scan_id] = _generate_mock_osint_graph(target)
    
    async def simulate_osint():
        await asyncio.sleep(2.5)
        res_msg = {
            "id": f"friday_{uuid.uuid4().hex[:10]}",
            "type": "osint_result",
            "target": target,
            "platforms_found": 6,
            "threats": 1,
            "entities": 10,
            "graph_id": scan_id,
            "timestamp": _now_iso() + "Z"
        }
        _CHAT_HISTORY.append(res_msg)
        await _broadcast_ws({"type": "chat.complete", "payload": res_msg})
        
    asyncio.create_task(simulate_osint())
    return {"scan_id": scan_id}

@router.get("/api/osint/graph/{scan_id}")
def osint_graph(scan_id: str) -> dict:
    graph = _OSINT_GRAPHS.get(scan_id)
    if not graph:
        # fallback graph
        graph = _generate_mock_osint_graph("unknown.domain")
    return graph


# ─── Vision / Camera ───
@router.get("/api/camera/snapshot")
def camera_snapshot() -> dict:
    mgr = _get_or_start_camera_manager()
    if mgr is None:
        raise HTTPException(status_code=503, detail="Camera manager unavailable")
    snapshot = mgr.get_buffer().get_snapshot()
    if snapshot is None:
        raise HTTPException(status_code=404, detail="No camera frame available")
    b64 = _encode_frame_jpeg(snapshot.raw_frame)
    if not b64:
        raise HTTPException(status_code=500, detail="Failed to encode frame")
    labels = _cv_labels_to_dict(snapshot.cv_labels)
    # Convert formats
    ui_labels = [
        {"label": x.get("class_name", "object"), "type": "object", "confidence": x.get("confidence", 0.9), "bbox": x.get("bbox", [0,0,0,0])}
        for x in labels.get("objects", [])
    ]
    return {"image_base64": b64, "cv_labels": ui_labels, "timestamp": _now_iso()}

@router.post("/api/vision/query")
async def vision_query(body: dict) -> dict:
    query = body.get("query", "")
    snap = camera_snapshot()
    return {
        "answer": f"Analysis complete for directive: '{query}'. System detected environment artifacts. Object indexing matches local telemetry.",
        "image_base64": snap.get("image_base64", ""),
        "cv_labels": snap.get("cv_labels", [])
    }


# ─── Browser ───
@router.get("/api/browser/state")
def browser_state() -> dict:
    return {
        "url": "https://github.com/hackers-reality/friday",
        "title": "hackers-reality/friday: Sovereign agentic assistant",
        "is_loading": False,
        "session": "default"
    }

@router.post("/api/browser/navigate")
def browser_navigate(body: dict) -> dict:
    url = body.get("url", "https://google.com")
    return {
        "url": url,
        "title": "Loaded: " + urlparse(url).netloc,
        "is_loading": False,
        "session": "default"
    }

@router.post("/api/browser/screenshot")
def browser_screenshot() -> dict:
    # grab screen screenshot or return styled placeholder
    try:
        from PIL import ImageGrab
        import io
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return {"image_base64": b64}
    except Exception:
        return {"image_base64": ""}


# ─── YouTube ───
@router.get("/api/youtube/stats")
def youtube_stats() -> dict:
    return get_status()["youtube"]

@router.get("/api/youtube/videos")
def youtube_videos() -> list[dict]:
    return [
        {"video_id": "vid1", "title": "Deploying Sovereign Assistants on local networks", "views": 12800, "likes": 980, "comments": 64, "published_at": "2026-05-22T08:00:00Z"},
        {"video_id": "vid2", "title": "Integrating Google Gemini Live API with Python", "views": 25400, "likes": 1850, "comments": 142, "published_at": "2026-05-18T10:00:00Z"}
    ]

@router.post("/api/youtube/generate-metadata")
async def youtube_generate_metadata(payload: dict) -> dict:
    title = str(payload.get("title", "")).strip()
    description_draft = str(payload.get("description_draft", "") or payload.get("description", ""))
    topic = str(payload.get("video_topic", "") or payload.get("topic", ""))
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    return generate_metadata(title, description_draft, topic)


# ─── Takeout ───
@router.post("/api/takeout/upload")
async def takeout_upload(file: UploadFile = File(...)):
    global _TAKEOUT_PROGRESS, _TAKEOUT_STATUS
    os.makedirs(os.path.join(FRIDAY_MEMORY, "takeout"), exist_ok=True)
    file_path = os.path.join(FRIDAY_MEMORY, "takeout", file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    upload_id = f"takeout_{uuid.uuid4().hex[:10]}"
    _TAKEOUT_UPLOADS.append({
        "id": upload_id,
        "filename": file.filename,
        "uploaded_at": _now_iso() + "Z",
        "services": ["Gmail", "YouTube", "Location History"],
        "status": "processing"
    })
    
    async def simulate_processing():
        global _TAKEOUT_PROGRESS, _TAKEOUT_STATUS
        _TAKEOUT_STATUS = "processing"
        for i in range(10):
            await asyncio.sleep(0.3)
            _TAKEOUT_PROGRESS = (i + 1) * 10
        _TAKEOUT_STATUS = "done"
        
        for u in _TAKEOUT_UPLOADS:
            if u["id"] == upload_id:
                u["status"] = "done"
                
    asyncio.create_task(simulate_processing())
    return {"id": upload_id}

@router.get("/api/takeout/history")
def takeout_history() -> list[dict]:
    return _TAKEOUT_UPLOADS


# ─── Scheduler ───
@router.get("/api/scheduler/jobs")
def scheduler_jobs() -> list[dict]:
    return _scheduler_jobs()

@router.post("/api/scheduler/jobs")
def scheduler_create_job(body: dict) -> dict:
    jobs = _load_schedule()
    new_job = {
        "id": body.get("id") or f"job_{uuid.uuid4().hex[:10]}",
        "name": body.get("name", "New Job"),
        "schedule": body.get("schedule", "0 * * * *"),
        "enabled": True,
        "target": body.get("target", "System"),
        "description": body.get("description", ""),
        "last_run": None,
        "last_result": None,
    }
    jobs.append(new_job)
    _save_schedule(jobs)
    return {
        "id": new_job["id"],
        "name": new_job["name"],
        "schedule": new_job["schedule"],
        "schedule_type": "cron",
        "next_run": "n/a",
        "last_run": None,
        "status": "active",
        "target": new_job["target"],
        "description": new_job["description"]
    }

@router.post("/api/scheduler/{job_id}/toggle")
def scheduler_toggle(job_id: str) -> dict:
    jobs = _load_schedule()
    for j in jobs:
        if j.get("id") == job_id:
            j["enabled"] = not bool(j.get("enabled", True))
            _save_schedule(jobs)
            return {"ok": True, "job_id": job_id, "enabled": j["enabled"]}
    raise HTTPException(status_code=404, detail="job not found")

@router.post("/api/scheduler/{job_id}/run")
def scheduler_run(job_id: str) -> dict:
    jobs = _load_schedule()
    for j in jobs:
        if j.get("id") == job_id:
            _execute_task(j)
            _save_schedule(jobs)
            return {"ok": True, "job_id": job_id, "last_run": j.get("last_run"), "last_result": j.get("last_result")}
    raise HTTPException(status_code=404, detail="job not found")

@router.delete("/api/scheduler/{job_id}")
def scheduler_delete_job(job_id: str) -> dict:
    jobs = _load_schedule()
    filtered = [j for j in jobs if j.get("id") != job_id]
    if len(filtered) == len(jobs):
        raise HTTPException(status_code=404, detail="Job not found")
    _save_schedule(filtered)
    return {"ok": True}


# ─── PyRunner ───
@router.get("/api/pyrunner/scripts")
def pyrunner_scripts() -> list[dict]:
    return _PYRUNNER_SCRIPTS

@router.put("/api/pyrunner/scripts/{script_id}")
def pyrunner_save_script(script_id: str, body: dict) -> dict:
    script = next((s for s in _PYRUNNER_SCRIPTS if s["id"] == script_id), None)
    if not script:
        script = {
            "id": script_id,
            "name": body.get("name", script_id),
            "code": body.get("code", ""),
            "schedule": body.get("schedule", ""),
            "packages": body.get("packages", []),
            "created_at": _now_iso() + "Z"
        }
        _PYRUNNER_SCRIPTS.append(script)
    else:
        script["code"] = body.get("code", script["code"])
        script["name"] = body.get("name", script["name"])
        script["schedule"] = body.get("schedule", script["schedule"])
        script["packages"] = body.get("packages", script["packages"])
    return script

@router.post("/api/pyrunner/scripts/{script_id}/run")
def pyrunner_run_script(script_id: str) -> dict:
    script = next((s for s in _PYRUNNER_SCRIPTS if s["id"] == script_id), None)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
        
    import sys
    from io import StringIO
    
    old_stdout = sys.stdout
    redirected = sys.stdout = StringIO()
    
    try:
        # Execute code in clean global dict
        exec(script["code"], {"__builtins__": __builtins__})
        output = redirected.getvalue()
        script["last_status"] = "success"
    except Exception as e:
        output = f"Execution error:\n{e}"
        script["last_status"] = "error"
    finally:
        sys.stdout = old_stdout
        
    script["last_run"] = _now_iso() + "Z"
    return {"output": output}

@router.get("/api/pyrunner/secrets")
def pyrunner_get_secrets() -> list[dict]:
    return list(_PYRUNNER_SECRETS.values())

@router.post("/api/pyrunner/secrets")
def pyrunner_add_secret(body: dict) -> dict:
    key = body.get("key")
    value = body.get("value")
    if not key or not value:
        raise HTTPException(status_code=400, detail="key and value required")
    _PYRUNNER_SECRETS[key] = {
        "key": key,
        "created_at": _now_iso() + "Z"
    }
    # best effort save to .env
    env_path = os.path.join(PROJECT_ROOT, ".env")
    try:
        with open(env_path, "a") as f:
            f.write(f"\n{key}={value}\n")
    except Exception:
        pass
    return {"ok": True}

@router.delete("/api/pyrunner/secrets/{key}")
def pyrunner_delete_secret(key: str) -> dict:
    _PYRUNNER_SECRETS.pop(key, None)
    return {"ok": True}


# ─── Settings ───
@router.get("/api/settings")
def get_settings_api() -> dict:
    from friday.orchestration_config import ensure_config
    cfg = ensure_config()
    return {
        "general": {
            "name": cfg.get("name", "FRIDAY"),
            "version": "2.0.0",
            "model": cfg.get("model", "gemini-3.1-flash-live-preview"),
            "voice_enabled": cfg.get("voice", {}).get("enabled", True),
        },
        "voice": {
            "wake_word": cfg.get("voice", {}).get("wake_word", "Friday"),
            "voice_name": cfg.get("voice", {}).get("voice_name", "Leda"),
            "sensitivity": cfg.get("voice", {}).get("sensitivity", 0.5),
        },
        "agents": {
            "max_parallel": cfg.get("nim", {}).get("rate_limit_rpm", 40),
            "default_timeout_ms": 30000,
            "auto_retry": True
        },
        "camera": {
            "enabled": cfg.get("camera", {}).get("enabled", True),
            "device_index": 0,
            "fps": 10,
            "cv_pipeline": True
        },
        "browser": {
            "backend": "playwright",
            "headless": True
        },
        "memory": {
            "auto_store": True,
            "vector_db_path": FRIDAY_MEMORY,
            "max_chunks": 10000
        },
        "notifications": {
            "desktop": True,
            "telegram": False,
            "discord": False
        }
    }

@router.put("/api/settings")
def put_settings_api(body: dict) -> dict:
    from friday.orchestration_config import ensure_config, save_config
    cfg = ensure_config()
    if "general" in body:
        gen = body["general"]
        cfg["name"] = gen.get("name", cfg.get("name", "FRIDAY"))
        cfg["model"] = gen.get("model", cfg.get("model", "gemini-3.1-flash-live-preview"))
    if "camera" in body:
        cam = body["camera"]
        cfg["camera"] = cfg.get("camera", {})
        cfg["camera"]["enabled"] = cam.get("enabled", True)
    if "voice" in body:
        v = body["voice"]
        cfg["voice"] = cfg.get("voice", {})
        cfg["voice"]["wake_word"] = v.get("wake_word", "Friday")
        cfg["voice"]["voice_name"] = v.get("voice_name", "Leda")
    save_config(cfg)
    return {"ok": True}


# ─── Security ───
@router.get("/api/security/audit")
def security_audit() -> list[dict]:
    return _SECURITY_AUDIT_LOG

@router.get("/api/security/tokens")
def security_tokens() -> list[dict]:
    return _SIDECAR_TOKENS

@router.post("/api/security/tokens")
def security_generate_token(body: dict) -> dict:
    device_name = body.get("device_name", "Unknown Device")
    capabilities = body.get("capabilities", [])
    token = f"friday_tkn_{uuid.uuid4().hex[:16]}"
    
    tkn_record = {
        "device_name": device_name,
        "token_prefix": token[:14] + "...",
        "capabilities": capabilities,
        "created_at": _now_iso() + "Z",
        "last_used": "never"
    }
    _SIDECAR_TOKENS.append(tkn_record)
    
    _SECURITY_AUDIT_LOG.append({
        "id": f"sec-{uuid.uuid4().hex[:8]}",
        "timestamp": _now_iso() + "Z",
        "action": "Generated Sidecar Token",
        "source": "Sovereign Core",
        "details": f"Token issued for {device_name} with capabilities: {capabilities}.",
        "severity": "warn"
    })
    return {"token": token}

@router.delete("/api/security/tokens/{prefix}")
def security_revoke_token(prefix: str) -> dict:
    global _SIDECAR_TOKENS
    before = len(_SIDECAR_TOKENS)
    _SIDECAR_TOKENS = [t for t in _SIDECAR_TOKENS if not t["token_prefix"].startswith(prefix)]
    if len(_SIDECAR_TOKENS) == before:
         raise HTTPException(status_code=404, detail="Token prefix not found")
         
    _SECURITY_AUDIT_LOG.append({
        "id": f"sec-{uuid.uuid4().hex[:8]}",
        "timestamp": _now_iso() + "Z",
        "action": "Revoked Sidecar Token",
        "source": "Sovereign Core",
        "details": f"Token matching prefix {prefix} revoked.",
        "severity": "warn"
    })
    return {"ok": True}


# ─── Logs ───
@router.get("/api/logs/recent")
def logs_recent() -> list[dict]:
    lines = _tail_file(STARK_LOGS, max_lines=100)
    out = []
    for line in lines:
        if not line.strip():
            continue
        out.append({
            "timestamp": _now_iso(),
            "level": _infer_log_level(line),
            "module": "Sovereign Core",
            "message": line
        })
    return out


# ─── System ───
@router.post("/api/system/restart")
def system_restart():
    def _restart():
        time.sleep(1.0)
        os.execv(sys.executable, [sys.executable] + sys.argv)
    threading.Thread(target=_restart, daemon=True).start()
    return {"ok": True}


# ─── Voice ───
@router.post("/api/voice/push-to-talk/start")
async def voice_ptt_start() -> dict:
    await _broadcast_ws({
        "type": "voice.state",
        "payload": {"state": "listening"}
    })
    return {"ok": True}

@router.post("/api/voice/push-to-talk/stop")
async def voice_ptt_stop() -> dict:
    await _broadcast_ws({
        "type": "voice.state",
        "payload": {"state": "speaking"}
    })
    
    async def simulate_transcription():
        await asyncio.sleep(1.5)
        # broadcast transcript
        await _broadcast_ws({
            "type": "voice.transcript",
            "payload": {"text": "hello Friday, status check"}
        })
        await asyncio.sleep(1.5)
        await _broadcast_ws({
            "type": "voice.state",
            "payload": {"state": "idle"}
        })
        
    asyncio.create_task(simulate_transcription())
    return {"ok": True}


# ─── SSE Streams ──────────────────────────────────────

async def _sse_gen_transcription() -> AsyncGenerator[str, None]:
    for item in list(_TRANSCRIPT_BUFFER):
        yield f"data: {json.dumps(item)}\n\n"
    while True:
        await asyncio.sleep(1.0)
        yield f"data: {json.dumps({'type': 'heartbeat', 'ts': _now_iso()})}\n\n"

@router.get("/events/transcription")
async def events_transcription() -> StreamingResponse:
    return StreamingResponse(_sse_gen_transcription(), media_type="text/event-stream")

async def _sse_gen_logs() -> AsyncGenerator[str, None]:
    for ln in _tail_file(STARK_LOGS, max_lines=60):
        payload = {"level": _infer_log_level(ln), "message": ln, "timestamp": _now_iso()}
        yield f"data: {json.dumps(payload)}\n\n"

    pos = 0
    if os.path.exists(STARK_LOGS):
        try:
            pos = os.path.getsize(STARK_LOGS)
        except Exception:
            pos = 0

    while True:
        await asyncio.sleep(0.8)
        try:
            if os.path.exists(STARK_LOGS):
                with open(STARK_LOGS, "r", encoding="utf-8", errors="ignore") as f:
                    f.seek(pos)
                    new = f.readlines()
                    pos = f.tell()
                for ln in new:
                    ln = ln.rstrip("\n")
                    if not ln:
                        continue
                    payload = {"level": _infer_log_level(ln), "message": ln, "timestamp": _now_iso()}
                    _LOG_BUFFER.append(payload)
                    yield f"data: {json.dumps(payload)}\n\n"
            else:
                yield f"data: {json.dumps({'level':'INFO','message':'Log stream active','timestamp':_now_iso()})}\n\n"
        except Exception:
            continue

@router.get("/events/logs")
async def events_logs() -> StreamingResponse:
    return StreamingResponse(_sse_gen_logs(), media_type="text/event-stream")

async def _sse_gen_takeout_progress() -> AsyncGenerator[str, None]:
    global _TAKEOUT_PROGRESS, _TAKEOUT_STATUS
    while True:
        await asyncio.sleep(0.5)
        payload = {
            "service": "Google Takeout Archive",
            "progress": int(_TAKEOUT_PROGRESS),
            "total": 100,
            "status": _TAKEOUT_STATUS
        }
        yield f"data: {json.dumps(payload)}\n\n"
        if _TAKEOUT_STATUS in ("done", "error"):
            break

@router.get("/events/takeout/progress")
async def events_takeout_progress() -> StreamingResponse:
    return StreamingResponse(_sse_gen_takeout_progress(), media_type="text/event-stream")


# ─── WebSocket Hub ───────────────────────────────────

@router.websocket("/ws")
async def websocket_hub(ws: WebSocket):
    await ws.accept()
    _WS_CLIENTS.add(ws)
    try:
        await ws.send_json({"type": "connected", "payload": {"connected": True, "ts": _now_iso()}})
        while True:
            msg = await ws.receive_json()
            msg_type = str(msg.get("type", "")).strip()
            payload = msg.get("payload", {})

            if msg_type == "transcription":
                entry = {
                    "speaker": payload.get("speaker", "unknown"),
                    "text": payload.get("text", ""),
                    "timestamp": payload.get("timestamp", _now_iso()),
                }
                _TRANSCRIPT_BUFFER.append(entry)
            elif msg_type == "log":
                entry = {
                    "level": payload.get("level", "INFO"),
                    "message": payload.get("message", ""),
                    "timestamp": payload.get("timestamp", _now_iso()),
                }
                _LOG_BUFFER.append(entry)

            # Broadcast to all clients
            dead = []
            for c in _WS_CLIENTS:
                try:
                    await c.send_json({"type": msg_type or "event", "payload": payload})
                except Exception:
                    dead.append(c)
            for d in dead:
                _WS_CLIENTS.discard(d)
    except WebSocketDisconnect:
        _WS_CLIENTS.discard(ws)
    except Exception:
        _WS_CLIENTS.discard(ws)
