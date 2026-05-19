"""Daily ingestion job for YouTube channel data.
Runnable as script: python -m friday.daily_ingestion_job
"""
from __future__ import annotations

import os
import sys
import json
import argparse
import datetime
import asyncio

from friday.youtube_client import YouTubeClient
from friday.analytics_store import save_snapshot, save_video_stats, set_meta, get_meta
from friday.orchestration_config import ensure_config
from friday.context_bus import get_bus
from friday.logging_utils import configure_logging

logger = configure_logging(__name__)


def _should_run_today() -> bool:
    cfg = ensure_config().get("youtube", {})
    ingest_time = cfg.get("ingest_time", "06:00")
    hour = int(ingest_time.split(":")[0]) if ":" in ingest_time else int(ingest_time)
    # Prevent multiple runs per day by checking meta
    last_run = get_meta("youtube.last_ingest_date")
    today = datetime.date.today().isoformat()
    if last_run == today:
        return False
    # Only run near the configured hour
    now_hour = datetime.datetime.now().hour
    return now_hour == hour


def run_ingest(channel_id: str = None):
    cfg = ensure_config().get("youtube", {})
    if not cfg.get("enabled", True):
        logger.info("YouTube ingestion disabled by config")
        return

    channel_id = channel_id or cfg.get("channel_id")
    if not channel_id:
        logger.warning("No channel_id configured for YouTube ingestion")
        return

    if not _should_run_today():
        logger.info("Ingestion skipped (already run today or outside scheduled hour)")
        return

    yt = YouTubeClient()
    try:
        stats = yt.get_channel_stats(channel_id)
    except Exception as e:
        logger.exception("Failed to fetch channel stats: %s", e)
        return

    today = datetime.date.today().isoformat()
    save_snapshot(channel_id, today, stats.get("subscriber_count", 0), stats.get("view_count", 0), stats.get("video_count", 0))

    max_videos = cfg.get("ingest_max_videos", 20)
    try:
        vids = yt.get_recent_videos(channel_id, max_results=max_videos)
    except Exception:
        vids = []

    for v in vids:
        vid = v.get("video_id")
        title = v.get("title")
        pub = v.get("published_at") or today
        try:
            vs = yt.get_video_stats(vid)
        except Exception:
            vs = {}
        save_video_stats(vid, channel_id, title, pub, vs.get("views", 0), vs.get("likes", 0), vs.get("comments", 0), vs.get("avg_view_duration"))

    # Mark as run today
    set_meta("youtube.last_ingest_date", today)

    # Publish event
    try:
        asyncio.run(get_bus().publish("youtube.ingestion.complete", {"channel_id": channel_id, "date": today, "videos_fetched": len(vids)}))
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", help="Channel ID to ingest", default=None)
    args = parser.parse_args()
    run_ingest(args.channel)


if __name__ == "__main__":
    main()
