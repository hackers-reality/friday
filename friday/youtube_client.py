"""YouTube API wrapper: Data API (API key) + Analytics (OAuth2)"""
from __future__ import annotations

import os
import time
import json
import sqlite3
from typing import List, Dict, Any, Optional

try:
    import requests
except Exception:
    requests = None

from friday._paths import PROJECT_ROOT
from friday.logging_utils import configure_logging

logger = configure_logging(__name__)


def _retry(fn, retries=3, backoff=0.5):
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except Exception as e:
            if attempt == retries:
                raise
            time.sleep(backoff * (2 ** (attempt - 1)))


class YouTubeClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY")
        self.base = "https://www.googleapis.com/youtube/v3"

    def get_channel_stats(self, channel_id: str) -> Dict[str, Any]:
        if not self.api_key or requests is None:
            raise RuntimeError("YouTube API key or requests library unavailable")

        def call():
            url = f"{self.base}/channels"
            params = {"part": "statistics", "id": channel_id, "key": self.api_key}
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            items = data.get("items", [])
            if not items:
                return {}
            stats = items[0].get("statistics", {})
            return {
                "subscriber_count": int(stats.get("subscriberCount", 0)),
                "view_count": int(stats.get("viewCount", 0)),
                "video_count": int(stats.get("videoCount", 0)),
            }

        return _retry(call)

    def get_recent_videos(self, channel_id: str, max_results: int = 10) -> List[Dict[str, Any]]:
        if not self.api_key or requests is None:
            raise RuntimeError("YouTube API key or requests library unavailable")

        def call():
            # Use search.list to get recent uploads
            url = f"{self.base}/search"
            params = {
                "part": "snippet",
                "channelId": channel_id,
                "order": "date",
                "maxResults": min(50, max_results),
                "type": "video",
                "key": self.api_key,
            }
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            items = r.json().get("items", [])
            videos = []
            for it in items:
                sn = it.get("snippet", {})
                videos.append({
                    "video_id": it.get("id", {}).get("videoId") or it.get("id"),
                    "title": sn.get("title"),
                    "published_at": sn.get("publishedAt"),
                })
            return videos

        return _retry(call)

    def get_video_stats(self, video_id: str) -> Dict[str, Any]:
        if not self.api_key or requests is None:
            raise RuntimeError("YouTube API key or requests library unavailable")

        def call():
            url = f"{self.base}/videos"
            params = {"part": "statistics,contentDetails", "id": video_id, "key": self.api_key}
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            items = r.json().get("items", [])
            if not items:
                return {}
            stats = items[0].get("statistics", {})
            return {
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)) if stats.get("likeCount") is not None else 0,
                "comments": int(stats.get("commentCount", 0)) if stats.get("commentCount") is not None else 0,
                # avg_view_duration requires Analytics API; leave None here
                "avg_view_duration": None,
            }

        return _retry(call)

    def get_comments_sample(self, video_id: str, max_results: int = 50) -> List[str]:
        if not self.api_key or requests is None:
            raise RuntimeError("YouTube API key or requests library unavailable")

        def call():
            url = f"{self.base}/commentThreads"
            params = {"part": "snippet", "videoId": video_id, "maxResults": min(100, max_results), "key": self.api_key}
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            items = r.json().get("items", [])
            comments = []
            for it in items:
                top = it.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                text = top.get("textDisplay")
                if text:
                    comments.append(text)
            return comments

        return _retry(call)

    # Placeholder for OAuth2-based analytics (requires google-auth and oauthlib)
    def get_analytics(self, channel_id: str, start_date: str, end_date: str, metrics: str):
        raise NotImplementedError("OAuth2 analytics flow not implemented in this environment")
