"""Build daily morning briefing for YouTube and publish to context bus."""
from __future__ import annotations

import json
from pathlib import Path
from datetime import date, datetime
from typing import Dict

from friday._paths import FRIDAY_MEMORY
from friday.analytics_store import get_growth_delta, get_top_videos
from friday.context_bus import get_bus
from friday.orchestration_config import ensure_config
from friday.logging_utils import configure_logging

logger = configure_logging(__name__)
_PENDING_PATH = Path(FRIDAY_MEMORY) / "youtube_morning_briefing.json"


def _load_pending() -> Dict:
    if not _PENDING_PATH.exists():
        return {}
    try:
        return json.loads(_PENDING_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_pending(data: Dict) -> None:
    _PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PENDING_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _get_health_section() -> str:
    """Get system health summary for briefing."""
    try:
        from friday.health_monitor import get_health_monitor
        hm = get_health_monitor()
        snap = hm.snapshot()
        alerts = snap.get("alerts", [])
        today_alerts = [a for a in alerts if a.get("time", "").startswith(date.today().isoformat())] if alerts else []
        lines = [
            f"System health: {snap['overall']}",
            f"Uptime: {snap['uptime_human']}",
            f"Alerts today: {len(today_alerts)}",
        ]
        if today_alerts:
            for a in today_alerts[-3:]:
                lines.append(f"  - [{a.get('severity','info').upper()}] {a.get('source','?')}: {a.get('message','')}")
        return "\n".join(lines)
    except Exception:
        return "System health: unavailable"


def build_briefing(channel_id: str) -> str:
    delta = get_growth_delta(channel_id, days=1)
    top = get_top_videos(channel_id, n=1)
    top_title = top[0]["title"] if top else "No videos"
    lines = []
    lines.append(f"FRIDAY Morning Briefing — {date.today().isoformat()}")
    lines.append("")
    lines.append("[YouTube Analytics]")
    lines.append(f"  Subscriber change: {delta.get('subscribers_delta',0)}")
    lines.append(f"  Views change: {delta.get('views_delta',0)}")
    lines.append(f"  Top video: {top_title}")
    cfg = ensure_config().get("youtube", {})
    lines.append("  Pending content ideas: check dashboard")
    lines.append("")
    lines.append("[System Health]")
    lines.append(f"  {_get_health_section()}")
    return "\n".join(lines)


def publish_briefing(channel_id: str):
    briefing = build_briefing(channel_id)
    today = date.today().isoformat()

    # Persist pending briefing so Live can speak it on first interaction after 8am.
    _save_pending(
        {
            "date": today,
            "channel_id": channel_id,
            "briefing": briefing,
            "pending": True,
            "generated_at": datetime.utcnow().isoformat(),
            "delivered_at": "",
        }
    )

    try:
        import asyncio
        asyncio.run(get_bus().publish("youtube.morning_briefing", {"channel_id": channel_id, "briefing": briefing, "timestamp": datetime.utcnow().isoformat()}))
    except Exception:
        pass


def get_pending_briefing_for_delivery(min_hour: int = 8) -> Dict | None:
    data = _load_pending()
    if not data or not data.get("pending"):
        return None
    today = date.today().isoformat()
    if str(data.get("date", "")) != today:
        return None
    if datetime.now().hour < int(min_hour):
        return None
    return data


def mark_briefing_delivered() -> None:
    data = _load_pending()
    if not data:
        return
    data["pending"] = False
    data["delivered_at"] = datetime.utcnow().isoformat()
    _save_pending(data)
