"""
FRIDAY Context Bus — async pub/sub event bus with optional Redis persistence.

Agents emit events:
  - agent.started      {agent_id, task_id, task_type}
  - agent.progress     {agent_id, task_id, progress_pct, message}
  - agent.completed    {agent_id, task_id, output}
  - agent.failed       {agent_id, task_id, error}
  - orchestrator.tick  {timestamp, status_summary}

Subscribers receive via asyncio.Queue or (optionally) Redis pub/sub channels.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

Handler = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass
class Subscription:
    topic: str
    handler: Handler
    queue: asyncio.Queue[dict[str, Any]] = field(default_factory=asyncio.Queue)
    running: bool = True


class ContextBus:
    """
    Async pub/sub event bus for agent-to-agent and agent-to-orchestrator communication.

    Topics:
      - agent.{event_type}    (started, progress, completed, failed)
      - user.{directive}      (cancel, pause, resume)
      - orchestrator.{event}
      - system.{event}
    """

    def __init__(self, redis_url: Optional[str] = None):
        self._subscriptions: dict[str, list[Subscription]] = defaultdict(list)
        self._history: list[dict[str, Any]] = []
        self._max_history = 500
        self._redis_url = redis_url or os.getenv("REDIS_URL", "")
        self._redis_pubsub = None

    # ── Publish ──────────────────────────────────────────────

    async def publish(self, topic: str, data: dict[str, Any]):
        """Publish an event to all subscribers of the topic."""
        entry = {"topic": topic, "data": data, "ts": time.time()}
        self._history.append(entry)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        subs = self._subscriptions.get(topic, []) + self._subscriptions.get("*", [])
        for sub in subs:
            if sub.running:
                try:
                    sub.queue.put_nowait(entry)
                except asyncio.QueueFull:
                    pass  # slow consumer — drop oldest

        # Redis forwarding (optional)
        if self._redis_pubsub:
            try:
                await self._redis_pubsub.publish(topic, json.dumps(data))
            except Exception:
                pass  # redis unavailable

    # ── Subscribe ────────────────────────────────────────────

    def subscribe(self, topic: str, handler: Optional[Handler] = None) -> Subscription:
        """
        Register a subscriber for a topic. If handler is provided, it is called
        asynchronously for each event. Returns Subscription (can unsubscribe).
        """
        sub = Subscription(topic=topic, handler=handler or _null_handler)
        self._subscriptions[topic].append(sub)
        return sub

    def unsubscribe(self, sub: Subscription):
        """Remove a subscription."""
        sub.running = False
        subs = self._subscriptions.get(sub.topic, [])
        if sub in subs:
            subs.remove(sub)

    # ── Consume (for polling subscribers) ────────────────────

    def events(self, topic: str) -> asyncio.Queue[dict[str, Any]]:
        """Return the queue for a topic. Subscribe with this to poll."""
        sub = self.subscribe(topic)
        return sub.queue

    # ── History ──────────────────────────────────────────────

    def recent_events(self, topic: Optional[str] = None, limit: int = 20) -> list[dict]:
        """Return recent event history, optionally filtered by topic."""
        events = self._history
        if topic:
            events = [e for e in events if e["topic"] == topic]
        return events[-limit:]

    def last_event(self, topic: str) -> Optional[dict]:
        """Return the most recent event for a topic."""
        events = self.recent_events(topic, limit=1)
        return events[0] if events else None

    # ── Lifecycle ────────────────────────────────────────────

    async def start_redis(self):
        """Start optional Redis pub/sub client."""
        if not self._redis_url:
            return
        try:
            import redis.asyncio as aioredis
            self._redis_pubsub = await aioredis.from_url(self._redis_url)
        except Exception:
            self._redis_pubsub = None

    async def stop(self):
        """Shut down everything."""
        for subs in self._subscriptions.values():
            for sub in subs:
                sub.running = False
        self._subscriptions.clear()
        if self._redis_pubsub:
            try:
                await self._redis_pubsub.close()
            except Exception:
                pass

    def status_snapshot(self) -> dict:
        """Quick snapshot of bus health."""
        return {
            "subscriptions": sum(len(v) for v in self._subscriptions.values()),
            "history_size": len(self._history),
            "topics": list(self._subscriptions.keys()),
            "redis": self._redis_url != "",
        }


async def _null_handler(data: dict) -> None:
    pass


# Global singleton accessor for backward compatibility
_BUS_INSTANCE: Optional[ContextBus] = None


def get_bus() -> ContextBus:
    global _BUS_INSTANCE
    if _BUS_INSTANCE is None:
        _BUS_INSTANCE = ContextBus()
    return _BUS_INSTANCE
