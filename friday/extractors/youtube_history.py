"""
Extract YouTube watch history from Google Takeout.
Parses watch-history.json → top channels, categories, active hours, binge sessions.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

CONTENT_CATEGORIES: dict[str, list[str]] = {
    "tech": ["python", "javascript", "coding", "programming", "web dev", "software",
             "linux", "docker", "kubernetes", "ai", "machine learning", "rust", "golang"],
    "gaming": ["game", "gameplay", "walkthrough", "lets play", "minecraft", "valorant",
               "fortnite", "gta", "r6", "rocket league", "fifa", "warzone"],
    "music": ["music", "song", "album", "lyrics", "beat", "instrumental", "remix",
              "live session", "concert", "playlist"],
    "education": ["tutorial", "course", "learn", "lecture", "class", "lesson",
                  "training", "how to", "guide", "explained"],
    "entertainment": ["vlog", "comedy", "funny", "prank", "challenge", "reaction",
                      "review", "unboxing", "try not to laugh"],
    "news": ["news", "breaking", "update", "report", "headlines", "politics",
             "economy", "world", "current affairs"],
    "sports": ["sports", "football", "cricket", "basketball", "ufc", "wwe",
               "f1", "nba", "nfl", "highlights"],
    "science": ["science", "physics", "space", "nasa", "biology", "chemistry",
                "research", "discovery", "technology"],
}


def _categorize_video(title: str) -> list[str]:
    low = title.lower()
    matches: list[str] = []
    for cat, keywords in CONTENT_CATEGORIES.items():
        for kw in keywords:
            if kw in low:
                matches.append(cat)
                break
    return matches or ["uncategorized"]


def _parse_timestamp_str(ts_str: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None


def extract_youtube_history(zip_file) -> list[dict]:
    """Parse Takeout/YouTube and YouTube Music history JSONs from ZIP."""
    chunks: list[dict] = []

    history_paths = [
        "Takeout/YouTube/history/watch-history.json",
        "Takeout/YouTube and YouTube Music/history/watch-history.json",
    ]

    records: list[dict] = []
    for hpath in history_paths:
        try:
            data = json.loads(zip_file.read(hpath))
            if isinstance(data, list):
                records.extend(data)
            elif isinstance(data, dict):
                records.extend(data.get("events", data.get("items", [])))
            logger.info("Loaded %d records from %s", len(records), hpath)
        except KeyError:
            continue
        except Exception as exc:
            logger.warning("Failed to parse %s: %s", hpath, exc)

    if not records:
        return chunks

    # --- Channel frequency ---
    channel_counter: Counter = Counter()
    channel_titles: dict[str, str] = {}
    for rec in records:
        subs = rec.get("subtitles") or []
        if subs:
            ch_name = subs[0].get("name", "").strip()
            if ch_name:
                channel_counter[ch_name] += 1
                if not ch_name.startswith("http"):
                    channel_titles[ch_name] = rec.get("title", "")

    top_20 = channel_counter.most_common(20)
    if top_20:
        lines = [f"  - {name} ({count} videos)" for name, count in top_20[:10]]
        chunks.append({
            "content": "User's most-watched YouTube channels:\n" + "\n".join(lines),
            "source": "google_takeout/youtube_history",
            "category": "interests",
            "confidence": 0.85,
        })

    # --- Content category breakdown ---
    cat_counter: Counter = Counter()
    for rec in records:
        title = rec.get("title", "") or ""
        cats = _categorize_video(title)
        for c in cats:
            cat_counter[c] += 1

    if cat_counter:
        total = sum(cat_counter.values())
        top_cats = cat_counter.most_common(5)
        lines = [f"  - {cat}: {round(cnt/total*100)}%" for cat, cnt in top_cats]
        chunks.append({
            "content": "YouTube content category breakdown:\n" + "\n".join(lines),
            "source": "google_takeout/youtube_history",
            "category": "interests",
            "confidence": 0.80,
        })

    # --- Active hours histogram ---
    hour_counter: Counter = Counter()
    for rec in records:
        ts_str = rec.get("time") or ""
        dt = _parse_timestamp_str(ts_str)
        if dt:
            hour_counter[dt.hour] += 1

    if hour_counter:
        peak_hour = hour_counter.most_common(1)[0][0]
        period = "AM" if peak_hour < 12 else "PM"
        display_hour = peak_hour if peak_hour <= 12 else peak_hour - 12
        if peak_hour == 0:
            display_hour = 12
        chunks.append({
            "content": f"User is most active on YouTube around {display_hour}{period} "
                       f"(hour {peak_hour}) based on watch history timestamps.",
            "source": "google_takeout/youtube_history",
            "category": "habits",
            "confidence": 0.75,
        })

    # --- Binge sessions: >3 videos same channel within 1 hour ---
    if records:
        by_channel: dict[str, list[datetime]] = defaultdict(list)
        for rec in records:
            ts_str = rec.get("time") or ""
            dt = _parse_timestamp_str(ts_str)
            if not dt:
                continue
            subs = rec.get("subtitles") or []
            if subs:
                ch_name = subs[0].get("name", "").strip()
                if ch_name:
                    by_channel[ch_name].append(dt)

        binge_channels: list[str] = []
        for ch_name, times in by_channel.items():
            times.sort()
            for i in range(len(times) - 2):
                if (times[i + 2] - times[i]).total_seconds() <= 3600:
                    binge_channels.append(ch_name)
                    break

        if binge_channels:
            chunks.append({
                "content": "User frequently binge-watches content from: "
                           + ", ".join(binge_channels[:5]),
                "source": "google_takeout/youtube_history",
                "category": "habits",
                "confidence": 0.70,
            })

    return chunks
