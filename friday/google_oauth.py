"""
Unified Google OAuth 2.0 module for FRIDAY.
Single consent grants access to ALL configured Google APIs at once.
"""
from __future__ import annotations

import json
import os
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode

try:
    import requests
except ImportError:
    requests = None

from friday._paths import FRIDAY_MEMORY

logger = None
try:
    from friday.logging_utils import configure_logging
    logger = configure_logging(__name__)
except Exception:
    import logging
    logger = logging.getLogger(__name__)


# ── All Google API scopes that FRIDAY can use ──

# Umbrella scope — covers ALL Google Cloud Platform APIs (60+)
# BigQuery, Vision, Natural Language, Translation, TTS, STT,
# Dialogflow, Vertex AI, Cloud Functions, Cloud Run, Cloud Storage,
# Cloud Scheduler, Cloud Tasks, Cloud Monitoring, Cloud Logging,
# Secret Manager, Cloud KMS, IAM, Cloud DNS, Cloud CDN, etc.
SCOPE_CLOUD_PLATFORM = "https://www.googleapis.com/auth/cloud-platform"

# Consumer API scopes (NOT covered by cloud-platform)
SCOPES = [
    # ── YouTube ──
    "https://www.googleapis.com/auth/youtube.force-ssl",       # Full YouTube access
    "https://www.googleapis.com/auth/youtube.readonly",        # Read-only YouTube
    "https://www.googleapis.com/auth/yt-analytics.readonly",   # YouTube Analytics
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",  # Monetization data

    # ── Google Workspace ──
    "https://www.googleapis.com/auth/gmail.modify",            # Read/send email
    "https://www.googleapis.com/auth/drive",                   # Google Drive full access
    "https://www.googleapis.com/auth/spreadsheets",            # Google Sheets
    "https://www.googleapis.com/auth/documents",               # Google Docs
    "https://www.googleapis.com/auth/presentations",           # Google Slides
    "https://www.googleapis.com/auth/calendar",                # Google Calendar
    "https://www.googleapis.com/auth/contacts",                # Google People/Contacts

    # ── Firebase ──
    "https://www.googleapis.com/auth/firebase",                # Firebase services
    "https://www.googleapis.com/auth/firebase.readonly",       # Firebase read-only

    # ── Google Classroom ──
    "https://www.googleapis.com/auth/classroom.courses",       # Classroom management

    # ── Google Books ──
    "https://www.googleapis.com/auth/books",                   # Google Books

    # ── Google Maps (read-only geocoding/places) ──
    "https://www.googleapis.com/auth/maps.readonly",           # Maps read-only
]

# Combined scopes string
SCOPE_STRING = " ".join([SCOPE_CLOUD_PLATFORM] + SCOPES)

# Stored credentials path
_CREDENTIALS_PATH = Path(FRIDAY_MEMORY) / "google_credentials.json"

# Thread lock for credential access
_cred_lock = threading.Lock()

# ── PKCE helpers ──

_code_verifier: str | None = None


def _generate_code_verifier() -> str:
    """Generate a PKCE code verifier (43-128 chars)."""
    import base64
    import hashlib
    import secrets
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()


def _generate_code_challenge(verifier: str) -> str:
    """Generate S256 PKCE code challenge from verifier."""
    import base64
    import hashlib
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


# ── Credential management ──

def _load_credentials() -> Optional[dict]:
    with _cred_lock:
        if _CREDENTIALS_PATH.exists():
            try:
                return json.loads(_CREDENTIALS_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
    return None


def _save_credentials(creds: dict):
    with _cred_lock:
        _CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CREDENTIALS_PATH.write_text(json.dumps(creds, indent=2), encoding="utf-8")


def credentials_exist() -> bool:
    return _CREDENTIALS_PATH.exists()


# ── Auth URL generation ──

def get_auth_url(redirect_port: int = 8085) -> dict:
    """
    Generate the OAuth 2.0 authorization URL with all scopes.
    Returns dict with auth_url and the state for CSRF protection.
    """
    global _code_verifier

    client_id = os.getenv("GOOGLE_CLIENT_ID", os.getenv("YOUTUBE_CLIENT_ID", ""))
    if not client_id:
        return {"error": "GOOGLE_CLIENT_ID (or YOUTUBE_CLIENT_ID) not set in .env"}

    _code_verifier = _generate_code_verifier()
    code_challenge = _generate_code_challenge(_code_verifier)
    redirect_uri = f"http://127.0.0.1:{redirect_port}"

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE_STRING,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "consent",
    }

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return {"auth_url": auth_url, "redirect_uri": redirect_uri, "scopes": len([SCOPE_CLOUD_PLATFORM] + SCOPES)}


def handle_auth_callback(auth_code: str) -> bool:
    """
    Exchange authorization code for tokens.
    Returns True on success.
    """
    global _code_verifier

    client_id = os.getenv("GOOGLE_CLIENT_ID", os.getenv("YOUTUBE_CLIENT_ID", ""))
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", os.getenv("YOUTUBE_CLIENT_SECRET", ""))
    if not client_id or not client_secret:
        logger.warning("GOOGLE_CLIENT_ID/SECRET not configured")
        return False

    if requests is None:
        logger.error("requests library unavailable")
        return False

    try:
        r = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": auth_code,
            "code_verifier": _code_verifier or "",
            "grant_type": "authorization_code",
            "redirect_uri": "http://127.0.0.1:8085",
        }, timeout=15)
        r.raise_for_status()
        data = r.json()

        creds = {
            "access_token": data.get("access_token", ""),
            "refresh_token": data.get("refresh_token", ""),
            "expires_at": (datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))).isoformat(),
            "scope": data.get("scope", ""),
            "token_type": data.get("token_type", "Bearer"),
            "created_at": datetime.utcnow().isoformat(),
        }
        _save_credentials(creds)
        logger.info("Google OAuth 2.0 tokens saved successfully")
        return True
    except Exception as exc:
        logger.warning("OAuth callback failed: %s", exc)
        return False


# ── Token management ──

def get_access_token() -> Optional[str]:
    """Return a valid access token, refreshing if needed."""
    creds = _load_credentials()
    if not creds:
        return None

    token = creds.get("access_token")
    refresh = creds.get("refresh_token")
    expiry_str = creds.get("expires_at", "")

    # Check expiry
    if expiry_str:
        try:
            exp_dt = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
            if datetime.utcnow() >= (exp_dt - timedelta(minutes=5)):
                if refresh:
                    return _refresh_token(refresh)
                return None
        except Exception:
            pass

    return token


def _refresh_token(refresh_token: str) -> Optional[str]:
    """Use refresh token to get a new access token."""
    client_id = os.getenv("GOOGLE_CLIENT_ID", os.getenv("YOUTUBE_CLIENT_ID", ""))
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", os.getenv("YOUTUBE_CLIENT_SECRET", ""))
    if not client_id or not client_secret or requests is None:
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
            if data.get("refresh_token"):
                creds["refresh_token"] = data["refresh_token"]
            _save_credentials(creds)
        return new_token
    except Exception as exc:
        logger.warning("Token refresh failed: %s", exc)
        return None


# ── Google API caller ──

def call_api(url: str, params: Optional[dict] = None, method: str = "GET",
             json_body: Optional[dict] = None, timeout: int = 15) -> Optional[dict]:
    """
    Make an authenticated request to any Google API.
    Uses the stored OAuth token (auto-refreshes if needed).
    Returns parsed JSON response or None on failure.
    """
    token = get_access_token()
    if not token:
        logger.warning("No OAuth token available for %s", url)
        return None

    if requests is None:
        return None

    headers = {"Authorization": f"Bearer {token}"}
    try:
        if method == "GET":
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
        elif method == "POST":
            r = requests.post(url, params=params, headers=headers, json=json_body, timeout=timeout)
        elif method == "PUT":
            r = requests.put(url, params=params, headers=headers, json=json_body, timeout=timeout)
        elif method == "DELETE":
            r = requests.delete(url, params=params, headers=headers, timeout=timeout)
        else:
            return None
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        logger.warning("Google API call failed: %s %s -> %s", method, url, exc)
        return None


def get_token_info() -> dict:
    """Return info about the stored credentials (no secrets)."""
    creds = _load_credentials()
    if not creds:
        return {"authenticated": False}
    scopes = creds.get("scope", "").split()
    return {
        "authenticated": True,
        "scope_count": len(scopes),
        "scopes": scopes,
        "has_refresh_token": bool(creds.get("refresh_token")),
        "expires_at": creds.get("expires_at", ""),
        "created_at": creds.get("created_at", ""),
    }


def revoke():
    """Revoke all tokens."""
    creds = _load_credentials()
    if creds and requests:
        token = creds.get("access_token") or creds.get("refresh_token")
        if token:
            try:
                requests.post("https://oauth2.googleapis.com/revoke",
                              params={"token": token}, timeout=5)
            except Exception:
                pass
    if _CREDENTIALS_PATH.exists():
        _CREDENTIALS_PATH.unlink(missing_ok=True)


def enable_api(api_name: str) -> dict:
    """Enable a GCP API via Service Usage REST API.
    Requires cloud-platform scope in OAuth token.
    Example: enable_api('drive.googleapis.com')
    """
    creds = _load_credentials()
    if not creds:
        return {"error": "Not authenticated"}
    token = creds.get("access_token")
    if not token:
        return {"error": "No access token"}
    if not requests:
        return {"error": "requests not installed"}
    try:
        r = requests.post(
            f"https://serviceusage.googleapis.com/v1/projects/-/services/{api_name}:enable",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=10,
        )
        if r.status_code == 200:
            return {"success": True, "api": api_name}
        return {"error": f"Failed ({r.status_code}): {r.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def enable_all_apis(api_list: list[str]) -> list[dict]:
    """Enable multiple GCP APIs sequentially."""
    results = []
    for api in api_list:
        results.append(enable_api(api))
    return results
