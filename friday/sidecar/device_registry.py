"""In-memory device registry for Friday sidecars.

Tracks connected devices and supports command RPC with timeout-backed futures.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Tuple


@dataclass
class DeviceRecord:
    device_id: str
    device_name: str
    capabilities: list[str]
    ws: Any = None
    status: str = "online"
    last_seen: Optional[str] = None
    last_pong: Optional[str] = None
    telemetry_latest: dict = field(default_factory=dict)


@dataclass
class SidecarCommand:
    capability: str
    action: str
    params: dict = field(default_factory=dict)
    command_id: str = field(default_factory=lambda: f"cmd_{uuid.uuid4().hex[:10]}")

    def to_wire(self) -> dict:
        return {
            "type": "command",
            "command_id": self.command_id,
            "capability": self.capability,
            "action": self.action,
            "params": self.params,
        }


class DeviceRegistry:
    def __init__(self):
        self._devices: Dict[str, DeviceRecord] = {}
        self._command_waiters: Dict[str, Tuple[asyncio.AbstractEventLoop, asyncio.Future]] = {}
        self._lock = asyncio.Lock()

    async def register(self, device_name: str, capabilities: list[str], ws: Any, device_id: Optional[str] = None) -> DeviceRecord:
        async with self._lock:
            rec = DeviceRecord(
                device_id=device_id or f"dev_{uuid.uuid4().hex[:10]}",
                device_name=device_name,
                capabilities=capabilities,
                ws=ws,
                status="online",
                last_seen=datetime.utcnow().isoformat(),
                last_pong=datetime.utcnow().isoformat(),
            )
            self._devices[device_name] = rec
            return rec

    async def deregister(self, device_name: str):
        async with self._lock:
            rec = self._devices.get(device_name)
            if rec is None:
                return
            rec.status = "offline"
            rec.ws = None
            rec.last_seen = datetime.utcnow().isoformat()

    def get(self, device_name: str) -> Optional[DeviceRecord]:
        return self._devices.get(device_name)

    def list_online(self) -> list[DeviceRecord]:
        return [device for device in self._devices.values() if device.status == "online" and device.ws is not None]

    def mark_pong(self, device_name: str) -> None:
        rec = self._devices.get(device_name)
        if rec:
            now = datetime.utcnow().isoformat()
            rec.last_seen = now
            rec.last_pong = now

    def mark_stale(self, device_name: str) -> None:
        rec = self._devices.get(device_name)
        if rec:
            rec.status = "stale"
            rec.last_seen = datetime.utcnow().isoformat()

    async def update_telemetry(self, device_name: str, payload: dict) -> None:
        rec = self._devices.get(device_name)
        if not rec:
            return
        rec.telemetry_latest = payload
        rec.last_seen = datetime.utcnow().isoformat()

    async def send_command(self, device_name: str, command: SidecarCommand | dict, timeout: int = 30) -> dict:
        rec = self._devices.get(device_name)
        if not rec or not rec.ws:
            raise KeyError(f"Device not online: {device_name}")

        payload = command.to_wire() if isinstance(command, SidecarCommand) else dict(command)

        command_id = payload.get("command_id")
        if not command_id:
            raise ValueError("command must include command_id")
        if payload.get("type") != "command":
            payload["type"] = "command"

        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._command_waiters[command_id] = (loop, fut)

        try:
            await rec.ws.send_json(payload)
            rec.last_seen = datetime.utcnow().isoformat()
        except Exception:
            self._command_waiters.pop(command_id, None)
            raise

        try:
            res = await asyncio.wait_for(fut, timeout=timeout)
            return res
        finally:
            self._command_waiters.pop(command_id, None)

    async def handle_command_result(self, command_id: str, result: dict) -> None:
        waiter = self._command_waiters.get(command_id)
        if not waiter:
            return
        loop, fut = waiter
        if fut.done():
            return
        loop.call_soon_threadsafe(fut.set_result, result)

    async def broadcast(self, command: SidecarCommand | dict, timeout: int = 30) -> dict:
        results: dict = {}
        devices = [d.device_name for d in self.list_online()]
        for device_name in devices:
            try:
                results[device_name] = await self.send_command(device_name, command, timeout=timeout)
            except Exception as exc:
                results[device_name] = {"error": str(exc)}
        return results


_REGISTRY: Optional[DeviceRegistry] = None


def get_registry() -> DeviceRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = DeviceRegistry()
    return _REGISTRY
