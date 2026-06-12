"""YouTube API wrapper: Data API (API key) + Analytics (OAuth2) + quota tracking.
Uses unified google_oauth module for all OAuth flows (single consent for all scopes).
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

try:
    import requests
except ImportError:
    requests = None

from friday._paths import PROJECT_ROOT, FRIDAY_MEMORY
from friday.google_oauth import get_access_token as _unified_get_token
from friday.google_oauth import credentials_exist as _unified_creds_exist
from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

_QUOTA_DB = Path(FRIDAY_MEMORY) / "youtube_quota.db"
_QUOTA_DAILY_LIMIT = 10_000
_CREDENTIALS_PATH = Path(FRIDAY_MEMORY) / "youtube_credentials.json"


# ── Quota tracking ──────────────────────────────────────────

def _init_quota_db():
    _QUOTA_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_QUOTA_DB))
    conn.execute("CREATE TABLE IF NOT EXISTS quota (date TEXT PRIMARY KEY, units INTEGER DEFAULT 0)")
    conn.commit()
    return conn


def _get_used_quota() -> int:
    conn = _init_quota_db()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    row = conn.execute("SELECT units FROM quota WHERE date = ?", (today,)).fetchone()
    conn.close()
    return row[0] if row else 0


def _add_quota(units: int = 1):
    conn = _init_quota_db()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    conn.execute(
        "INSERT INTO quota (date, units) VALUES (?, ?) "
        "ON CONFLICT(date) DO UPDATE SET units = units + ?",
        (today, units, units),
    )
    conn.commit()
    conn.close()


def check_quota(min_remaining: int = 500) -> bool:
    """Return True if enough quota remaining."""
    used = _get_used_quota()
    remaining = _QUOTA_DAILY_LIMIT - used
    if remaining < min_remaining:
        logger.warning("YouTube API quota low: %d remaining", remaining)
    return remaining >= min_remaining


def quota_remaining() -> int:
    return _QUOTA_DAILY_LIMIT - _get_used_quota()


# ── OAuth2 helpers ──────────────────────────────────────────

def _load_credentials() -> Optional[dict]:
    if _CREDENTIALS_PATH.exists():
        try:
            return json.loads(_CREDENTIALS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def _save_credentials(creds: dict):
    _CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CREDENTIALS_PATH.write_text(json.dumps(creds, indent=2), encoding="utf-8")


def _get_oauth_token() -> Optional[str]:
    """Return a valid OAuth2 access token.
    Tries unified google_oauth credentials first, then falls back to youtube-specific.
    """
    # First try unified credentials (from google_oauth module)
    unified_token = _unified_get_token()
    if unified_token:
        return unified_token

    # Fall back to legacy youtube-specific credentials
    creds = _load_credentials()
    if not creds:
        return None

    token = creds.get("token") or creds.get("access_token")
    expiry = creds.get("expiry") or creds.get("expires_at", "")
    refresh_token = creds.get("refresh_token") or creds.get("_refresh_token", "")

    if expiry:
        try:
            exp_dt = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
            if datetime.utcnow() > (exp_dt - timedelta(minutes=5)):
                if refresh_token:
                    return _refresh_oauth_token(refresh_token)
                return None
        except Exception:
            pass

    return token


def _refresh_oauth_token(refresh_token: str) -> Optional[str]:
    """Use refresh token to get a new access token."""
    client_id = os.getenv("YOUTUBE_CLIENT_ID", "")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        logger.warning("YOUTUBE_CLIENT_ID/SECRET not set for token refresh")
        return None

    try:
        r = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }, timeout=10)
        r.raise_for_status()
        data = r.json()
        new_token = data.get("access_token")
        if new_token:
            creds = _load_credentials() or {}
            creds["access_token"] = new_token
            creds["expires_at"] = (datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))).isoformat()
            _save_credentials(creds)
        return new_token
    except Exception as exc:
        logger.warning("OAuth2 token refresh failed: %s", exc)
        return None


# ── Cost table ──────────────────────────────────────────────

_API_COST: dict[str, int] = {
    "channels": 1,
    "search": 100,
    "videos": 1,
    "commentThreads": 1,
    "videoCategories": 1,
}


# ── Client ──────────────────────────────────────────────────

class YouTubeClient:
    """YouTube Data API v3 + Analytics API v2 client with quota tracking."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY", "")
        self.data_base = "https://www.googleapis.com/youtube/v3"
        self.analytics_base = "https://youtubeanalytics.googleapis.com/v2"

    def _get(self, endpoint: str, params: dict, oauth: bool = False) -> dict:
        """Make a GET request with quota tracking."""
        if requests is None:
            raise RuntimeError("requests library unavailable")

        cost = _API_COST.get(endpoint, 10)
        if not check_quota(cost):
            raise RuntimeError(f"YouTube API quota exhausted ({quota_remaining()} remaining)")

        headers = {}
        url = f"{self.data_base}/{endpoint}"
        params["key"] = self.api_key

        if oauth:
            token = _get_oauth_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
                params.pop("key", None)
            else:
                logger.warning("OAuth token unavailable for %s; falling back to API key", endpoint)

        r = requests.get(url, params=params, headers=headers, timeout=15)
        _add_quota(cost)
        r.raise_for_status()
        return r.json()

    def get_channel_stats(self, channel_id: str) -> dict:
        data = self._get("channels", {"part": "statistics", "id": channel_id})
        items = data.get("items", [])
        if not items:
            return {}
        stats = items[0].get("statistics", {})
        return {
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "view_count": int(stats.get("viewCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
        }

    def get_recent_videos(self, channel_id: str, max_results: int = 10) -> list[dict]:
        data = self._get("search", {
            "part": "snippet", "channelId": channel_id,
            "order": "date", "maxResults": min(50, max_results), "type": "video",
        })
        videos = []
        for it in data.get("items", []):
            sn = it.get("snippet", {})
            videos.append({
                "video_id": it.get("id", {}).get("videoId") or it.get("id"),
                "title": sn.get("title"),
                "published_at": sn.get("publishedAt"),
            })
        return videos

    def get_video_stats(self, video_id: str) -> dict:
        data = self._get("videos", {"part": "statistics,contentDetails,snippet", "id": video_id})
        items = data.get("items", [])
        if not items:
            return {}
        stats = items[0].get("statistics", {})
        snippet = items[0].get("snippet", {})
        duration = items[0].get("contentDetails", {}).get("duration", "")
        return {
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)) if stats.get("likeCount") is not None else 0,
            "comments": int(stats.get("commentCount", 0)) if stats.get("commentCount") is not None else 0,
            "avg_view_duration": None,
            "duration_iso": duration,
            "category_id": snippet.get("categoryId", ""),
            "tags": snippet.get("tags", []),
            "description": snippet.get("description", "")[:500],
        }

    def get_comments_sample(self, video_id: str, max_results: int = 50) -> list[str]:
        data = self._get("commentThreads", {
            "part": "snippet", "videoId": video_id,
            "maxResults": min(100, max_results),
        })
        comments = []
        for it in data.get("items", []):
            top = it.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
            text = top.get("textDisplay")
            if text:
                comments.append(text)
        return comments

    def get_analytics(self, channel_id: str, start_date: str, end_date: str,
                      metrics: str = "views,estimatedMinutesWatched,averageViewDuration",
                      dimensions: str = "day") -> Optional[list[dict]]:
        """
        YouTube Analytics API v2 (requires OAuth2).
        Returns list of metric rows or None if unavailable.
        """
        if requests is None:
            return None
        token = _get_oauth_token()
        if not token:
            logger.warning("OAuth2 not configured for Analytics API. "
                           "Set YOUTUBE_CLIENT_ID + YOUTUBE_CLIENT_SECRET in .env "
                           "and run OAuth2 flow.")
            return None

        url = f"{self.analytics_base}/reports"
        params = {
            "ids": f"channel==MINE",
            "startDate": start_date,
            "endDate": end_date,
            "metrics": metrics,
            "dimensions": dimensions,
        }
        if channel_id:
            params["filters"] = f"channel=={channel_id}"

        try:
            r = requests.get(url, params=params,
                             headers={"Authorization": f"Bearer {token}"},
                             timeout=15)
            if r.status_code == 403:
                logger.warning("Analytics API 403: Analytics may not be enabled for this channel")
                return None
            r.raise_for_status()
            data = r.json()
            rows = data.get("rows", [])
            col_headers = [c.get("name", "") for c in data.get("columnHeaders", [])]
            result = []
            for row in rows:
                result.append(dict(zip(col_headers, row)))
            return result
        except Exception as exc:
            logger.warning("Analytics API call failed: %s", exc)
            return None

    def get_video_analytics(self, video_id: str, start_date: str, end_date: str) -> Optional[dict]:
        """Get per-video analytics (views, retention, etc)."""
        rows = self.get_analytics(
            "", start_date, end_date,
            metrics="views,estimatedMinutesWatched,averageViewDuration,videoAverageViewPercentage",
            dimensions="video",
        )
        if rows is None:
            return None
        for row in rows:
            if row.get("video") == video_id:
                return row
        return None

    def upload_video(self, file_path: str, title: str, description: str = "",
                     tags: Optional[list[str]] = None, category_id: str = "22",
                     privacy_status: str = "public", publish_at: str = "") -> dict:
        """Upload a video to YouTube using resumable media upload.
        
        Args:
            file_path: Path to the video file (MP4, MOV, etc.)
            title: Video title (max 100 chars)
            description: Video description
            tags: List of tags
            category_id: YouTube category ID (default 22 = People & Blogs)
            privacy_status: 'public', 'unlisted', or 'private'
            publish_at: ISO datetime string for scheduled publishing (requires privacy_status='private')
        
        Returns:
            dict with video_id, status, or error
        """
        if requests is None:
            return {"error": "requests library unavailable"}

        token = _get_oauth_token()
        if not token:
            return {"error": "OAuth2 token required for upload. Run OAuth2 flow first."}

        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return {"error": "File is empty"}

        body = {
            "snippet": {
                "title": str(title)[:100],
                "description": str(description)[:5000],
                "tags": tags or [],
                "categoryId": str(category_id),
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }
        if publish_at and privacy_status == "private":
            body["status"]["publishAt"] = publish_at

        # Step 1: Initiate resumable upload
        upload_url = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Length": str(file_size),
            "X-Upload-Content-Type": "video/*",
        }

        try:
            r = requests.post(upload_url, headers=headers, json=body, timeout=30)
            if r.status_code != 200:
                return {"error": f"Upload initiation failed: {r.status_code} {r.text[:500]}"}

            session_uri = r.headers.get("Location", "")
            if not session_uri:
                return {"error": "No upload session URI returned"}

            # Step 2: Upload video bytes
            with open(file_path, "rb") as f:
                video_data = f.read()

            upload_headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "video/*",
                "Content-Length": str(file_size),
            }

            r = requests.put(session_uri, headers=upload_headers, data=video_data, timeout=600)
            _add_quota(1600)

            if r.status_code in (200, 201):
                result = r.json()
                video_id = result.get("id", "")
                _log_history({
                    "event": "upload",
                    "video_id": video_id,
                    "title": title[:100],
                    "file": os.path.basename(file_path),
                    "privacy": privacy_status,
                    "timestamp": datetime.utcnow().isoformat(),
                })
                return {
                    "success": True,
                    "video_id": video_id,
                    "title": title[:100],
                    "url": f"https://youtu.be/{video_id}",
                    "privacy": privacy_status,
                }

            return {"error": f"Upload failed: HTTP {r.status_code} - {r.text[:500]}"}

        except requests.exceptions.Timeout:
            return {"error": "Upload timed out (large file?)"}
        except Exception as e:
            return {"error": f"Upload error: {e}"}

    def set_thumbnail(self, video_id: str, image_path: str) -> dict:
        """Set a custom thumbnail for a video.
        
        Args:
            video_id: YouTube video ID
            image_path: Path to thumbnail image (JPEG/PNG, max 2MB)
        
        Returns:
            dict with success or error
        """
        if requests is None:
            return {"error": "requests library unavailable"}

        token = _get_oauth_token()
        if not token:
            return {"error": "OAuth2 token required"}

        if not os.path.exists(image_path):
            return {"error": f"Thumbnail file not found: {image_path}"}

        try:
            url = f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={video_id}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "image/*",
            }
            with open(image_path, "rb") as f:
                img_data = f.read()

            r = requests.post(url, headers=headers, data=img_data, timeout=30)
            _add_quota(50)

            if r.status_code in (200, 201):
                return {"success": True, "video_id": video_id, "thumbnail": "custom"}
            return {"error": f"Thumbnail upload failed: HTTP {r.status_code}"}

        except Exception as e:
            return {"error": f"Thumbnail error: {e}"}

    # ── OAuth2 flow (delegates to unified google_oauth module) ──

    def get_auth_url(self) -> dict:
        """Generate OAuth2 auth URL with ALL Google API scopes (single consent)."""
        from friday.google_oauth import get_auth_url as _get_auth_url
        return _get_auth_url(redirect_port=8085)

    def handle_auth_callback(self, code: str) -> bool:
        """Exchange OAuth2 auth code for tokens (unified credentials)."""
        from friday.google_oauth import handle_auth_callback as _handle_callback
        return _handle_callback(code)
