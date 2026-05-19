"""Monitor camera events and publish significant proactive signals."""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Dict

from friday._paths import FRIDAY_MEMORY
from friday.context_bus import get_bus
from friday.logging_utils import configure_logging
from friday.orchestration_config import ensure_config


logger = configure_logging(__name__)


class ProactiveMonitor:
    """Consumes `camera.events` and forwards significant events with cooldown."""

    def __init__(self) -> None:
        cfg = ensure_config().get("camera", {})
        self.enabled = bool(cfg.get("proactive_events", True))
        self.allow_empty_event = bool(cfg.get("allow_no_one_detected", False))
        self.cooldown_seconds = 60
        self._last_emit: Dict[str, float] = {}
        self._bus = get_bus()
        self._log_path = Path(FRIDAY_MEMORY) / "camera_events.log"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    async def run(self) -> None:
        if not self.enabled:
            return
        async for event in self._bus.subscribe("camera.events"):
            await self._handle_event(event)

    async def _handle_event(self, event: dict) -> None:
        event_type = str(event.get("event_type", "unknown"))
        now = time.time()

        # Always retain a raw log for memory/context mining.
        with self._log_path.open("a", encoding="utf-8") as f:
            f.write(f"{event}\n")

        if event_type == "no_one_detected" and not self.allow_empty_event:
            return

        if event_type not in {"person_entered", "object_in_hand", "no_one_detected"}:
            return

        prev = self._last_emit.get(event_type, 0.0)
        if now - prev < self.cooldown_seconds:
            return
        self._last_emit[event_type] = now

        await self._bus.publish(
            "proactive.notifications",
            {
                "source": "camera",
                "event_type": event_type,
                "payload": event,
                "timestamp": now,
            },
        )
