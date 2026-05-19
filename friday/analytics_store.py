"""SQLite-backed store for YouTube analytics and computed insights."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from friday._paths import PROJECT_ROOT

DB_PATH = os.path.join(PROJECT_ROOT, "data", "youtube_analytics.db")


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def migrate():
    conn = _conn()
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("CREATE TABLE IF NOT EXISTS schema_meta (k TEXT PRIMARY KEY, v TEXT)")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS channel_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT,
            date TEXT,
            subscribers INTEGER,
            views INTEGER,
            videos INTEGER,
            created_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS video_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT,
            channel_id TEXT,
            title TEXT,
            date TEXT,
            views INTEGER,
            likes INTEGER,
            comments INTEGER,
            avg_view_duration REAL,
            created_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS content_ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT,
            idea TEXT,
            reasoning TEXT,
            score REAL,
            created_at TEXT,
            used INTEGER DEFAULT 0
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS peak_times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT,
            hour_of_day INTEGER,
            day_of_week INTEGER,
            avg_views REAL,
            computed_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)
        """
    )
    conn.commit()
    conn.close()


def save_snapshot(channel_id: str, date_str: str, subscribers: int, views: int, videos: int):
    migrate()
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO channel_snapshots (channel_id, date, subscribers, views, videos, created_at) VALUES (?,?,?,?,?,?)",
        (channel_id, date_str, subscribers, views, videos, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def save_video_stats(video_id: str, channel_id: str, title: str, date_str: str, views: int, likes: int, comments: int, avg_view_duration: Optional[float]):
    migrate()
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO video_stats (video_id, channel_id, title, date, views, likes, comments, avg_view_duration, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (video_id, channel_id, title, date_str, views, likes, comments, avg_view_duration, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def save_content_idea(channel_id: str, idea: str, reasoning: str, score: float = 0.0):
    migrate()
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO content_ideas (channel_id, idea, reasoning, score, created_at) VALUES (?,?,?,?,?)",
        (channel_id, idea, reasoning, score, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_growth_delta(channel_id: str, days: int = 7) -> Dict[str, Any]:
    migrate()
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT date, subscribers, views FROM channel_snapshots WHERE channel_id=? ORDER BY date DESC LIMIT ?",
        (channel_id, days + 1),
    )
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return {"subscribers_delta": 0, "views_delta": 0}
    newest = rows[0]
    oldest = rows[-1] if len(rows) > 1 else rows[0]
    return {"subscribers_delta": newest["subscribers"] - oldest["subscribers"], "views_delta": newest["views"] - oldest["views"]}


def get_top_videos(channel_id: str, n: int = 5) -> List[Dict[str, Any]]:
    migrate()
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT video_id, title, MAX(views) as max_views FROM video_stats WHERE channel_id=? GROUP BY video_id ORDER BY max_views DESC LIMIT ?",
        (channel_id, n),
    )
    rows = cur.fetchall()
    conn.close()
    return [{"video_id": r["video_id"], "title": r["title"], "views": r["max_views"]} for r in rows]


def set_meta(k: str, v: str):
    migrate()
    conn = _conn()
    cur = conn.cursor()
    cur.execute("REPLACE INTO meta (k,v) VALUES (?,?)", (k, v))
    conn.commit()
    conn.close()


def get_meta(k: str) -> Optional[str]:
    migrate()
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT v FROM meta WHERE k=?", (k,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None
