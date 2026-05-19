"""Analyze historical performance to recommend posting times."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any

from friday.analytics_store import migrate, get_top_videos
from friday.analytics_store import _conn
from friday.logging_utils import configure_logging

logger = configure_logging(__name__)


def compute_peak_times(channel_id: str):
    migrate()
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT video_id, title, date, views FROM video_stats WHERE channel_id=?", (channel_id,))
    rows = cur.fetchall()
    conn.close()
    if len(rows) < 10:
        return []

    by_slot = defaultdict(list)
    for r in rows:
        try:
            pub = r["date"]
            dt = datetime.fromisoformat(pub.replace("Z", "")) if pub else None
            if not dt:
                continue
            slot = (dt.weekday(), dt.hour)
            by_slot[slot].append(r["views"])
        except Exception:
            continue

    scored = []
    for (dow, hour), views in by_slot.items():
        avg = sum(views) / len(views)
        scored.append({"day_of_week": dow, "hour": hour, "avg_views": avg, "count": len(views)})

    scored.sort(key=lambda x: x["avg_views"], reverse=True)
    return scored[:3]
