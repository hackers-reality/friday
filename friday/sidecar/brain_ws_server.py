"""Brain WebSocket server for sidecar connections.

Mount `router` into an existing FastAPI app:

    from friday.sidecar.brain_ws_server import router as sidecar_router
    app.include_router(sidecar_router)

"""
from __future__ import annotations

import asyncio
import json
import uuid
import jwt
from datetime import datetime
from typing import Dict

from friday.orchestration_config import ensure_config
from friday.sidecar.device_registry import SidecarCommand, get_registry


def _get_fastapi():
    """Lazy FastAPI import to avoid crashing on missing module."""
    from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
    from fastapi.responses import JSONResponse
    return APIRouter, WebSocket, WebSocketDisconnect, Query, JSONResponse


try:
    APIRouter, WebSocket, WebSocketDisconnect, Query, JSONResponse = _get_fastapi()
    router = APIRouter()
    _HAS_FASTAPI = True
except ImportError:
    APIRouter = WebSocket = WebSocketDisconnect = Query = JSONResponse = None
    router = None
    _HAS_FASTAPI = False

_PONG_WAITERS: Dict[str, asyncio.Event] = {}


def _ensure_fastapi():
    if not _HAS_FASTAPI:
        raise RuntimeError("fastapi is required for sidecar WebSocket server. Install: pip install fastapi")


# ── Routes (only register if FastAPI is available) ──────

if _HAS_FASTAPI:

    @router.get("/sidecar/health")
    async def _health():
        return JSONResponse({"ok": True, "timestamp": datetime.utcnow().isoformat()})


    @router.websocket("/sidecar")
    async def sidecar_ws(websocket: WebSocket, token: str = Query(None)):
        if not token:
            await websocket.close(code=4001)
            return

        config = ensure_config()
        secret = config.get("SECRET_KEY") or config.get("sidecar", {}).get("secret_key")
        if not secret:
            await websocket.close(code=4001)
            return

        try:
            payload = jwt.decode(token, secret, algorithms=["HS256"])
        except Exception:
            await websocket.close(code=4001)
            return

        device_name = payload.get("device_name")
        device_id = payload.get("device_id")
        capabilities = payload.get("capabilities", [])
        if not device_name or not device_id:
            await websocket.close(code=4001)
            return

        await websocket.accept()
        registry = get_registry()
        await registry.register(device_name, capabilities, websocket, device_id=device_id)

        ping_task = asyncio.create_task(_ping_loop(device_name, websocket))
        try:
            while True:
                try:
                    data = await websocket.receive_text()
                except WebSocketDisconnect:
                    break
                try:
                    msg = json.loads(data)
                except Exception:
                    continue

                mtype = msg.get("type")
                if mtype == "telemetry":
                    await registry.update_telemetry(device_name, msg.get("payload", {}))
                elif mtype == "result":
                    command_id = msg.get("command_id")
                    await registry.handle_command_result(command_id, msg.get("payload", {}))
                elif mtype == "pong":
                    registry.mark_pong(device_name)
                    ping_id = msg.get("ping_id")
                    if ping_id and ping_id in _PONG_WAITERS:
                        _PONG_WAITERS[ping_id].set()
                elif mtype == "event":
                    pass

        finally:
            ping_task.cancel()
            await registry.deregister(device_name)


async def _ping_loop(device_name: str, websocket: WebSocket):
    registry = get_registry()
    try:
        while True:
            try:
                ping_id = f"ping_{uuid.uuid4().hex[:8]}"
                event = asyncio.Event()
                _PONG_WAITERS[ping_id] = event
                await websocket.send_json({"type": "ping", "ts": datetime.utcnow().isoformat(), "ping_id": ping_id})
                try:
                    await asyncio.wait_for(event.wait(), timeout=10)
                except asyncio.TimeoutError:
                    registry.mark_stale(device_name)
                    await websocket.close(code=4008)
                    break
                finally:
                    _PONG_WAITERS.pop(ping_id, None)
            except Exception:
                break
            await asyncio.sleep(30)
    finally:
        await registry.deregister(device_name)


async def send_command(device_name: str, capability: str, action: str, params: dict, timeout: int = 30) -> dict:
    """Convenience API for brain callers to send commands to a sidecar."""
    registry = get_registry()
    cmd = SidecarCommand(capability=capability, action=action, params=params)
    return await registry.send_command(device_name, cmd, timeout=timeout)
