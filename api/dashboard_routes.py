"""FastAPI dashboard routes for the single-file premium UI.

Exposes JSON APIs, a broadcast WebSocket, and SSE feeds.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import socket
import time
from collections import deque
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from friday._paths import FRIDAY_MEMORY, STARK_LOGS
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
    # Prefer persisted peak_times table if available, fallback to compute.
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
                "job_id": j.get("id"),
                "job_name": j.get("name"),
                "next_run": j.get("schedule"),
                "last_run": j.get("last_run") or "never",
                "status": "enabled" if j.get("enabled", True) else "disabled",
            }
        )
    return out


@router.get("/api/status")
def get_status() -> dict:
    runtime = load_runtime_state()
    host = socket.gethostname()
    uptime_seconds = int(time.time() - _BOOT_TS)

    # Agents
    agents = []
    reg = get_agent_registry()
    orch = get_orchestrator()
    for p in reg.list_all():
        st = orch.get_status(p.agent_id)
        agents.append(
            {
                "agent_id": p.agent_id,
                "display_name": p.display_name,
                "status": st.get("status", "idle"),
                "current_task": st.get("current_task"),
                "last_result": st.get("last_result"),
                "nim_model": p.nim_model,
            }
        )

    # Devices
    dreg = get_device_registry()
    devices = []
    for d in dreg._devices.values():  # In-process registry state
        tel = d.telemetry_latest or {}
        platform_name = str(tel.get("platform") or tel.get("os") or "unknown")
        devices.append(
            {
                "device_id": d.device_id,
                "device_name": d.device_name,
                "platform": platform_name,
                "status": d.status,
                "last_seen": d.last_seen,
                "capabilities": d.capabilities,
                "telemetry": {
                    "cpu_percent": tel.get("cpu_percent", tel.get("cpu", 0)),
                    "ram_percent": tel.get("memory_percent", tel.get("ram", 0)),
                    "disk_percent": tel.get("disk_percent", tel.get("disk", 0)),
                },
            }
        )

    # YouTube aggregates
    youtube = {
        "subscriber_count": 0,
        "delta_7d": 0,
        "top_video": {"title": "n/a", "views": 0},
        "next_slot": "n/a",
        "pending_briefing": _load_pending_briefing(),
    }
    try:
        from friday.orchestration_config import ensure_config

        cfg = ensure_config().get("youtube", {})
        channel_id = str(cfg.get("channel_id", "")).strip()
        if channel_id:
            d = get_growth_delta(channel_id, days=7)
            tops = get_top_videos(channel_id, n=1)
            youtube["delta_7d"] = int(d.get("subscribers_delta", 0))
            if tops:
                youtube["top_video"] = {"title": tops[0].get("title"), "views": int(tops[0].get("views", 0))}
            youtube["next_slot"] = _read_peak_slot(channel_id)
            # Best-effort read most recent subscriber count
            import sqlite3

            if os.path.exists(DB_PATH):
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute(
                    "SELECT subscribers FROM channel_snapshots WHERE channel_id=? ORDER BY date DESC, id DESC LIMIT 1",
                    (channel_id,),
                )
                row = cur.fetchone()
                conn.close()
                if row:
                    youtube["subscriber_count"] = int(row["subscribers"])
    except Exception:
        pass

    # Memory
    vm = get_vector_memory()
    memory_count = 0
    if vm.is_available():
        try:
            memory_count = int(vm.collection.count())
        except Exception:
            memory_count = 0

    return {
        "brain": {
            "hostname": host,
            "uptime_seconds": uptime_seconds,
            "gemini_live_active": bool(runtime.get("live_engine", {}).get("status") == "running"),
            "runtime": runtime,
        },
        "agents": agents,
        "devices": devices,
        "youtube": youtube,
        "memory": {"total_chunks": memory_count},
        "scheduler_jobs": _scheduler_jobs(),
    }


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
    return {"frame_b64": b64, "cv_labels": labels}


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
                "source": md.get("source", "unknown"),
                "category": md.get("category", "general"),
                "extracted_at": md.get("timestamp", ""),
            }
        )
    return chunks


@router.delete("/api/memory/{chunk_id}")
def memory_delete(chunk_id: str) -> dict:
    vm = get_vector_memory()
    if not vm.is_available():
        raise HTTPException(status_code=503, detail="Vector memory unavailable")
    msg = vm.delete(chunk_id)
    ok = msg.startswith("[OK]")
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@router.post("/api/youtube/generate-metadata")
async def youtube_generate_metadata(payload: dict) -> dict:
    title = str(payload.get("title", "")).strip()
    description_draft = str(payload.get("description_draft", "") or payload.get("description", ""))
    topic = str(payload.get("video_topic", "") or payload.get("topic", ""))
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    return generate_metadata(title, description_draft, topic)


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


async def _sse_gen_transcription() -> AsyncGenerator[str, None]:
    # Send buffered items first
    for item in list(_TRANSCRIPT_BUFFER):
        yield f"data: {json.dumps(item)}\n\n"
    while True:
        await asyncio.sleep(1.0)
        # keepalive ping
        yield f"data: {json.dumps({'type': 'heartbeat', 'ts': _now_iso()})}\n\n"


@router.get("/events/transcription")
async def events_transcription() -> StreamingResponse:
    return StreamingResponse(_sse_gen_transcription(), media_type="text/event-stream")


async def _sse_gen_logs() -> AsyncGenerator[str, None]:
    # Bootstrap with recent file lines
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


@router.websocket("/ws")
async def websocket_hub(ws: WebSocket):
    await ws.accept()
    _WS_CLIENTS.add(ws)
    try:
        await ws.send_json({"type": "connected", "payload": {"ts": _now_iso()}})
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
