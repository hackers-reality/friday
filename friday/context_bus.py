"""Async pub/sub bus for Friday agent and orchestrator events.

Uses in-memory asyncio queues by default and can switch to Redis pub/sub
when REDIS_URL is present and the redis asyncio client is installed.
"""
from __future__ import annotations

import asyncio
import json
import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, AsyncIterator, DefaultDict, Dict, Optional

from friday.logging_utils import configure_logging


logger = configure_logging(__name__)


@dataclass(slots=True)
class BusMessage:
    """Envelope used for bus payloads and Redis serialization."""

    topic: str
    payload: Dict[str, Any]

    def to_json(self) -> str:
        return json.dumps({"topic": self.topic, "payload": self.payload}, ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> "BusMessage":
        data = json.loads(raw)
        return cls(topic=data["topic"], payload=data["payload"])


class ContextBus:
    """In-memory or Redis-backed asynchronous event bus."""

    def __init__(self) -> None:
        self._latest: Dict[str, Dict[str, Any]] = {}
        self._queues: DefaultDict[str, set[asyncio.Queue]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._redis_url = os.getenv("REDIS_URL")
        self._redis = None
        self._redis_available = False
        if self._redis_url:
            self._redis_available = self._try_init_redis()

    def _try_init_redis(self) -> bool:
        try:
            import redis.asyncio as redis  # type: ignore

            self._redis = redis.from_url(self._redis_url, decode_responses=True)
            logger.info("Context bus connected to Redis")
            return True
        except Exception as exc:
            logger.warning("Redis unavailable, falling back to in-memory bus: %s", exc)
            self._redis = None
            return False

    async def publish(self, topic: str, payload: Dict[str, Any]) -> None:
        """Publish a payload to a topic and store the latest value."""
        envelope = {"topic": topic, "payload": payload}
        self._latest[topic] = payload

        if self._redis_available and self._redis is not None:
            message = BusMessage(topic=topic, payload=payload).to_json()
            await self._redis.set(f"context_bus:latest:{topic}", message)
            await self._redis.publish(topic, message)
            return

        async with self._lock:
            for queue in list(self._queues.get(topic, set())):
                queue.put_nowait(envelope)

    async def subscribe(self, topic: str) -> AsyncIterator[Dict[str, Any]]:
        """Subscribe to a topic and yield payload dictionaries forever."""
        if self._redis_available and self._redis is not None:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(topic)
            try:
                async for message in pubsub.listen():
                    if message.get("type") != "message":
                        continue
                    envelope = BusMessage.from_json(message["data"])
                    yield envelope.payload
            finally:
                await pubsub.unsubscribe(topic)
                await pubsub.close()
            return

        queue: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._queues[topic].add(queue)
        try:
            while True:
                envelope = await queue.get()
                yield envelope["payload"]
        finally:
            async with self._lock:
                self._queues[topic].discard(queue)

    async def get_latest(self, topic: str) -> Optional[Dict[str, Any]]:
        """Return the latest payload published for a topic."""
        if topic in self._latest:
            return self._latest[topic]

        if self._redis_available and self._redis is not None:
            raw = await self._redis.get(f"context_bus:latest:{topic}")
            if raw:
                return BusMessage.from_json(raw).payload
        return None


_BUS = ContextBus()


def get_bus() -> ContextBus:
    """Return the shared context bus instance."""
    return _BUS
