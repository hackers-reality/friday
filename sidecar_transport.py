"""Transport abstraction for sidecar clients.

This allows swapping WebSocket transport for TCP/MQTT/gRPC in future.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SidecarTransport(ABC):
    @abstractmethod
    async def connect(self) -> None:
        ...

    @abstractmethod
    async def send_json(self, payload: dict) -> None:
        ...

    @abstractmethod
    async def recv_text(self) -> str:
        ...

    @abstractmethod
    async def close(self) -> None:
        ...
