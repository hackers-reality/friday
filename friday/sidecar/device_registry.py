"""In-memory device registry for Friday sidecars.

Provides registration, lookup, and command dispatch with result futures.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class DeviceRecord:
    device_id: str
    device_name: str
    capabilities: list[str]
    ws: Any = None
    status: str = "online"
    last_seen: Optional[str] = None
    telemetry_latest: dict = field(default_factory=dict)


class DeviceRegistry:
    def __init__(self):
        self._devices: Dict[str, DeviceRecord] = {}
        self._command_waiters: Dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()

    async def register(self, device_name: str, device_id: str, capabilities: list[str], ws: Any) -> DeviceRecord:
        async with self._lock:
            rec = DeviceRecord(device_id=device_id, device_name=device_name, capabilities=capabilities, ws=ws, last_seen=datetime.utcnow().isoformat())
            self._devices[device_name] = rec
            return rec

    async def deregister(self, device_name: str):
        async with self._lock:
            rec = self._devices.pop(device_name, None)
            if rec and hasattr(rec, "ws"):
                try:
                    await rec.ws.close()
                except Exception:
                    pass

    def get(self, device_name: str) -> Optional[DeviceRecord]:
        return self._devices.get(device_name)

    def list_online(self) -> list[DeviceRecord]:
        return list(self._devices.values())

    async def update_telemetry(self, device_name: str, payload: dict) -> None:
        rec = self._devices.get(device_name)
        if not rec:
            return
        rec.telemetry_latest = payload
        rec.last_seen = datetime.utcnow().isoformat()

    async def send_command(self, device_name: str, command: dict, timeout: int = 30) -> dict:
        rec = self._devices.get(device_name)
        if not rec or not rec.ws:
            raise KeyError(f"Device not online: {device_name}")

        command_id = command.get("command_id")
        if not command_id:
            raise ValueError("command must include command_id")

        fut = asyncio.get_running_loop().create_future()
        self._command_waiters[command_id] = fut

        try:
            await rec.ws.send_json(command)
        except Exception as exc:
            self._command_waiters.pop(command_id, None)
            raise

        try:
            res = await asyncio.wait_for(fut, timeout=timeout)
            return res
        finally:
            self._command_waiters.pop(command_id, None)

    async def handle_command_result(self, command_id: str, result: dict) -> None:
        fut = self._command_waiters.get(command_id)
        if fut and not fut.done():
            fut.set_result(result)


_REGISTRY: Optional[DeviceRegistry] = None


def get_registry() -> DeviceRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = DeviceRegistry()
    return _REGISTRY
