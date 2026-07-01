"""
Unified Google OAuth 2.0 module for FRIDAY.
Supports per-category authorization so users grant scopes in small batches (~5 per category)
instead of all ~70 at once (which causes Google consent screen errors).
"""
from __future__ import annotations

import http.server
import json
import os
import random
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode

try:
    import requests
    from requests.exceptions import SSLError
    try:
        from requests.packages.urllib3.exceptions import InsecureRequestWarning
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    except Exception:
        pass
except ImportError:
    requests = None
    SSLError = Exception

from friday._paths import FRIDAY_MEMORY

logger = None
try:
    from friday.logging_utils import configure_logging
    logger = configure_logging(__name__)
except Exception:
    import logging
    logger = logging.getLogger(__name__)

try:
    from friday._paths import PROJECT_ROOT as _ROOT
except Exception:
    _ROOT = Path.cwd()


def _read_client_creds() -> dict:
    """Read client_id + client_secret from credentials.json fallback."""
    for path in (Path(_ROOT) / "credentials.json", Path.cwd() / "credentials.json"):
        if path.exists():
            try:
                with open(path) as f:
                    cfg = json.load(f)
                info = cfg.get("web", cfg.get("installed", {}))
                cid = info.get("client_id", "")
                cs = info.get("client_secret", "")
                return {"client_id": cid, "client_secret": cs}
            except Exception:
                pass
    return {"client_id": "", "client_secret": ""}


# ── All Google API scopes that FRIDAY can use ──

# Umbrella scope — covers ALL Google Cloud Platform APIs (60+)
SCOPE_CLOUD_PLATFORM = "https://www.googleapis.com/auth/cloud-platform"

# Organised into categories of ~5 scopes each so users can authorise one at a time.
# Each batch includes openid+userinfo+profile automatically.
SCOPE_CATEGORIES: dict[str, list[str]] = {
    "Gmail": [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.labels",
        "https://www.googleapis.com/auth/gmail.insert",
        "https://www.googleapis.com/auth/gmail.metadata",
        "https://www.googleapis.com/auth/gmail.settings.basic",
        "https://www.googleapis.com/auth/gmail.settings.sharing",
    ],
    "Calendar": [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.events.readonly",
        "https://www.googleapis.com/auth/calendar.freebusy",
        "https://www.googleapis.com/auth/calendar.settings.readonly",
        "https://www.googleapis.com/auth/calendar.addons.execute",
        "https://www.googleapis.com/auth/calendar.acls",
        "https://www.googleapis.com/auth/calendar.acls.readonly",
    ],
    "Drive": [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/drive.metadata.readonly",
        "https://www.googleapis.com/auth/drive.appdata",
        "https://www.googleapis.com/auth/drive.scripts",
        "https://www.googleapis.com/auth/drive.photos.readonly",
        "https://www.googleapis.com/auth/drive.activity",
        "https://www.googleapis.com/auth/drive.activity.readonly",
        "https://www.googleapis.com/auth/drive.metadata",
        "https://www.googleapis.com/auth/drive.install",
        "https://www.googleapis.com/auth/drive.meet.readonly",
    ],
    "Sheets": [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.file",
    ],
    "Docs": [
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/documents.readonly",
        "https://www.googleapis.com/auth/drive.file",
    ],
    "Slides": [
        "https://www.googleapis.com/auth/presentations",
        "https://www.googleapis.com/auth/presentations.readonly",
        "https://www.googleapis.com/auth/drive.file",
    ],
    "YouTube": [
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/youtube.force-ssl",
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtubepartner",
        "https://www.googleapis.com/auth/youtubepartner-channel-audit",
        "https://www.googleapis.com/auth/yt-analytics.readonly",
        "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
    ],
    "People": [
        "https://www.googleapis.com/auth/contacts",
        "https://www.googleapis.com/auth/contacts.readonly",
        "https://www.googleapis.com/auth/contacts.other.readonly",
        "https://www.googleapis.com/auth/directory.readonly",
        "https://www.googleapis.com/auth/user.addresses.read",
        "https://www.googleapis.com/auth/user.birthday.read",
        "https://www.googleapis.com/auth/user.emails.read",
        "https://www.googleapis.com/auth/user.gender.read",
        "https://www.googleapis.com/auth/user.organization.read",
        "https://www.googleapis.com/auth/user.phonenumbers.readonly",
    ],
    "Tasks": [
        "https://www.googleapis.com/auth/tasks",
        "https://www.googleapis.com/auth/tasks.readonly",
    ],
    "Forms": [
        "https://www.googleapis.com/auth/forms",
        "https://www.googleapis.com/auth/forms.body",
        "https://www.googleapis.com/auth/forms.body.readonly",
        "https://www.googleapis.com/auth/forms.responses.readonly",
    ],
    "Photos": [
        "https://www.googleapis.com/auth/photoslibrary",
        "https://www.googleapis.com/auth/photoslibrary.readonly",
        "https://www.googleapis.com/auth/photoslibrary.sharing",
        "https://www.googleapis.com/auth/photoslibrary.appendonly",
        "https://www.googleapis.com/auth/photoslibrary.edit.appcreateddata",
    ],
    "Firebase": [
        "https://www.googleapis.com/auth/firebase",
        "https://www.googleapis.com/auth/firebase.readonly",
        "https://www.googleapis.com/auth/firebase.database",
        "https://www.googleapis.com/auth/firebase.messaging",
        "https://www.googleapis.com/auth/firebase.remoteconfig",
        "https://www.googleapis.com/auth/cloud-platform",
    ],
    "Books": [
        "https://www.googleapis.com/auth/books",
    ],
    "Analytics": [
        "https://www.googleapis.com/auth/analytics.readonly",
        "https://www.googleapis.com/auth/analytics",
        "https://www.googleapis.com/auth/analytics.edit",
        "https://www.googleapis.com/auth/analytics.manage.users",
        "https://www.googleapis.com/auth/analytics.manage.users.readonly",
        "https://www.googleapis.com/auth/analytics.provision",
    ],
    "Search Console": [
        "https://www.googleapis.com/auth/webmasters.readonly",
    ],
    "Translation": [
        "https://www.googleapis.com/auth/cloud-translation",
        "https://www.googleapis.com/auth/cloud-platform",
    ],
    "Natural Language": [
        "https://www.googleapis.com/auth/cloud-language",
        "https://www.googleapis.com/auth/cloud-platform",
    ],
    "BigQuery": [
        "https://www.googleapis.com/auth/bigquery",
        "https://www.googleapis.com/auth/bigquery.readonly",
        "https://www.googleapis.com/auth/bigquery.insertdata",
        "https://www.googleapis.com/auth/cloud-platform",
    ],
    "Cloud Storage": [
        "https://www.googleapis.com/auth/devstorage.full_control",
        "https://www.googleapis.com/auth/devstorage.read_only",
        "https://www.googleapis.com/auth/devstorage.read_write",
        "https://www.googleapis.com/auth/cloud-platform",
    ],
    "Cloud Platform": [
        SCOPE_CLOUD_PLATFORM,
        "https://www.googleapis.com/auth/cloud-platform.read-only",
        "https://www.googleapis.com/auth/cloud-platform.userinfo.email",
        "https://www.googleapis.com/auth/iam",
        "https://www.googleapis.com/auth/compute",
        "https://www.googleapis.com/auth/sqlservice.admin",
        "https://www.googleapis.com/auth/appengine.admin",
    ],
    "Classroom": [
        "https://www.googleapis.com/auth/classroom.courses.readonly",
        "https://www.googleapis.com/auth/classroom.courses",
        "https://www.googleapis.com/auth/classroom.coursework.readonly",
        "https://www.googleapis.com/auth/classroom.coursework.me",
        "https://www.googleapis.com/auth/classroom.coursework.students",
        "https://www.googleapis.com/auth/classroom.announcements.readonly",
        "https://www.googleapis.com/auth/classroom.announcements",
        "https://www.googleapis.com/auth/classroom.rosters.readonly",
        "https://www.googleapis.com/auth/classroom.rosters",
        "https://www.googleapis.com/auth/classroom.profile.emails",
        "https://www.googleapis.com/auth/classroom.profile.photos",
    ],
    "Gmail Readonly": [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.metadata",
    ],
    "Drive Readonly": [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/drive.metadata.readonly",
        "https://www.googleapis.com/auth/drive.activity.readonly",
    ],
}

# Identity scopes — always included with every batch
_IDENTITY_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# All scopes combined (backward compat — for gmail.py)
ALL_SCOPES: list[str] = [SCOPE_CLOUD_PLATFORM]
for _scopes in SCOPE_CATEGORIES.values():
    ALL_SCOPES.extend(_scopes)

def get_scope_string(category: str | None = None) -> str:
    """Build scope string for a category (or all if None)."""
    if category is None:
        return " ".join(ALL_SCOPES)
    scopes = list(_IDENTITY_SCOPES)
    cat_scopes = SCOPE_CATEGORIES.get(category, [])
    scopes.extend(cat_scopes)
    return " ".join(scopes)

def list_categories() -> dict[str, int]:
    """Return {category_name: scope_count} for all categories."""
    return {name: len(scopes) for name, scopes in SCOPE_CATEGORIES.items()}


# Stored credentials path
_CREDENTIALS_PATH = Path(FRIDAY_MEMORY) / "google_credentials.json"

# Thread lock for credential access
_cred_lock = threading.Lock()

# ── PKCE helpers ──

_code_verifier: str | None = None


def _generate_code_verifier() -> str:
    import base64, hashlib, secrets
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()


def _generate_code_challenge(verifier: str) -> str:
    import base64, hashlib
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


# ── Authorized categories tracking ──

def get_authorized_categories() -> list[str]:
    """Return list of category names that have been authorised."""
    creds = _load_credentials()
    if not creds:
        return []
    return creds.get("authorized_categories", [])


def is_category_authorized(category: str) -> bool:
    """Check if a specific category has been authorised."""
    return category in get_authorized_categories()


def get_unauthorized_categories() -> list[str]:
    """Return list of categories not yet authorised."""
    authd = set(get_authorized_categories())
    return [c for c in SCOPE_CATEGORIES if c not in authd]


def _add_authorized_category(category: str):
    """Mark a category as authorised in stored credentials."""
    creds = _load_credentials() or {}
    authd = set(creds.get("authorized_categories", []))
    authd.add(category)
    creds["authorized_categories"] = sorted(authd)
    _save_credentials(creds)


# ── Auth URL generation ──

def get_auth_url(redirect_port: int = 8085, category: str | None = None) -> dict:
    """
    Generate the OAuth 2.0 authorization URL.
    If category is given, only request scopes for that category + identity scopes.
    If category is None, request ALL scopes (original behaviour — may cause consent screen errors).
    
    IMPORTANT: Google Cloud Console redirect URIs must match.
    Add these to your GCP project:
      http://127.0.0.1:8085
      http://localhost:8085
      http://localhost
    """
    global _code_verifier

    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    if not client_id:
        client_id = os.getenv("YOUTUBE_CLIENT_ID", "")
    if not client_id:
        client_id = _read_client_creds().get("client_id", "")
    if not client_id:
        return {"error": "GOOGLE_CLIENT_ID not set in .env or credentials.json"}

    _code_verifier = _generate_code_verifier()
    code_challenge = _generate_code_challenge(_code_verifier)
    redirect_uri = f"http://127.0.0.1:{redirect_port}"

    scope_str = get_scope_string(category)
    scope_count = len(scope_str.split())

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope_str,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return {
        "auth_url": auth_url,
        "redirect_uri": redirect_uri,
        "scope_count": scope_count,
        "category": category or "ALL",
    }


def save_token_data(token_data: dict, category: str | None = None) -> bool:
    """Save pre-exchanged token data to credentials file. Used by settings dashboard."""
    try:
        existing = _load_credentials() or {}
        merged_scopes = existing.get("scope", "")
        new_scope = token_data.get("scope", "")
        if merged_scopes and new_scope and new_scope not in merged_scopes:
            merged_scopes = " ".join(set(merged_scopes.split() + new_scope.split()))
        elif new_scope:
            merged_scopes = new_scope

        expires_at = (datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))).isoformat()
        creds = {
            "access_token": token_data.get("access_token", existing.get("access_token", "")),
            "refresh_token": token_data.get("refresh_token", existing.get("refresh_token", "")),
            "expires_at": expires_at,
            "scope": merged_scopes,
            "token_type": token_data.get("token_type", "Bearer"),
            "created_at": existing.get("created_at", datetime.utcnow().isoformat()),
            "authorized_categories": existing.get("authorized_categories", []),
        }
        if category:
            authd = set(creds["authorized_categories"])
            authd.add(category)
            creds["authorized_categories"] = sorted(authd)

        # Also store Google-compatible keys
        try:
            from friday._paths import CREDENTIALS_JSON
            with open(CREDENTIALS_JSON) as cf:
                cdata = json.load(cf)
            info = cdata.get("web", cdata.get("installed", {}))
            cid = info.get("client_id", os.getenv("GOOGLE_CLIENT_ID", ""))
            cs = info.get("client_secret", os.getenv("GOOGLE_CLIENT_SECRET", ""))
        except Exception:
            cid = os.getenv("GOOGLE_CLIENT_ID", "")
            cs = os.getenv("GOOGLE_CLIENT_SECRET", "")
        creds["token"] = creds["access_token"]
        creds["token_uri"] = "https://oauth2.googleapis.com/token"
        creds["client_id"] = cid
        creds["client_secret"] = cs
        creds["scopes"] = merged_scopes.split()
        creds["expiry"] = expires_at

        _save_credentials(creds)
        logger.info("Google OAuth 2.0 tokens saved successfully (from dashboard)")
        return True
    except Exception as exc:
        logger.warning("save_token_data failed: %s", exc)
        return False


def handle_auth_callback(auth_code: str, category: str | None = None) -> bool:
    """
    Exchange authorization code for tokens.
    If category is provided, marks that category as authorised.
    Returns True on success.
    """
    global _code_verifier

    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    if not client_id:
        client_id = os.getenv("YOUTUBE_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    if not client_secret:
        client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        creds = _read_client_creds()
        if not client_id:
            client_id = creds.get("client_id", "")
        if not client_secret:
            client_secret = creds.get("client_secret", "")
    if not client_id or not client_secret:
        logger.warning("GOOGLE_CLIENT_ID/SECRET not configured in .env or credentials.json")
        return False

    if requests is None:
        logger.error("requests library unavailable")
        return False

    try:
        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": auth_code,
            "code_verifier": _code_verifier or "",
            "grant_type": "authorization_code",
            "redirect_uri": "http://127.0.0.1:8085",
        }
        try:
            r = requests.post(token_url, data=payload, timeout=15)
            r.raise_for_status()
        except SSLError:
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            r = requests.post(token_url, data=payload, timeout=15, verify=False)
            r.raise_for_status()
        data = r.json()

        existing = _load_credentials() or {}
        merged_scopes = existing.get("scope", "")
        new_scope = data.get("scope", "")
        if merged_scopes and new_scope and new_scope not in merged_scopes:
            merged_scopes = " ".join(set(merged_scopes.split() + new_scope.split()))
        elif new_scope:
            merged_scopes = new_scope

        expires_at = (datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))).isoformat()
        creds = {
            "access_token": data.get("access_token", existing.get("access_token", "")),
            "refresh_token": data.get("refresh_token", existing.get("refresh_token", "")),
            "expires_at": expires_at,
            "scope": merged_scopes,
            "token_type": data.get("token_type", "Bearer"),
            "created_at": existing.get("created_at", datetime.utcnow().isoformat()),
            "authorized_categories": existing.get("authorized_categories", []),
        }
        if category:
            authd = set(creds["authorized_categories"])
            authd.add(category)
            creds["authorized_categories"] = sorted(authd)

        # Also store Google-compatible keys so gmail.py can read via Credentials.from_authorized_user_file
        try:
            from friday._paths import CREDENTIALS_JSON
            with open(CREDENTIALS_JSON) as cf:
                cdata = json.load(cf)
            info = cdata.get("web", cdata.get("installed", {}))
            cid = info.get("client_id", client_id)
            cs = info.get("client_secret", client_secret)
        except Exception:
            cid, cs = client_id, client_secret
        creds["token"] = creds["access_token"]
        creds["token_uri"] = "https://oauth2.googleapis.com/token"
        creds["client_id"] = cid
        creds["client_secret"] = cs
        creds["scopes"] = merged_scopes.split()
        creds["expiry"] = expires_at

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
    client_id = os.getenv("GOOGLE_CLIENT_ID", os.getenv("YOUTUBE_CLIENT_ID", ""))
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", os.getenv("YOUTUBE_CLIENT_SECRET", ""))
    if not client_id or not client_secret:
        creds_cfg = _read_client_creds()
        if not client_id:
            client_id = creds_cfg.get("client_id", "")
        if not client_secret:
            client_secret = creds_cfg.get("client_secret", "")
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
            expires_at = (datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))).isoformat()
            creds = _load_credentials() or {}
            creds["access_token"] = new_token
            creds["expires_at"] = expires_at
            if data.get("refresh_token"):
                creds["refresh_token"] = data["refresh_token"]
            # Keep Google-compatible keys in sync so gmail.py can read them
            creds["token"] = new_token
            creds["expiry"] = expires_at
            creds["token_uri"] = "https://oauth2.googleapis.com/token"
            creds["client_id"] = creds.get("client_id", client_id)
            creds["client_secret"] = creds.get("client_secret", client_secret)
            _save_credentials(creds)
        return new_token
    except Exception as exc:
        logger.warning("Token refresh failed: %s", exc)
        return None


# ── Google API caller ──

_API_URL_TO_NAME: dict[str, str] = {
    "slides.googleapis.com": "slides.googleapis.com",
    "docs.googleapis.com": "docs.googleapis.com",
    "sheets.googleapis.com": "sheets.googleapis.com",
    "drive.googleapis.com": "drive.googleapis.com",
    "people.googleapis.com": "people.googleapis.com",
    "calendar.googleapis.com": "calendar.googleapis.com",
    "gmail.googleapis.com": "gmail.googleapis.com",
    "youtube.googleapis.com": "youtube.googleapis.com",
    "books.googleapis.com": "books.googleapis.com",
    "translate.googleapis.com": "translate.googleapis.com",
    "vision.googleapis.com": "vision.googleapis.com",
    "bigquery.googleapis.com": "bigquery.googleapis.com",
    "storage.googleapis.com": "storage.googleapis.com",
    "firestore.googleapis.com": "firestore.googleapis.com",
    "maps.googleapis.com": "maps.googleapis.com",
    "searchconsole.googleapis.com": "searchconsole.googleapis.com",
    "analytics.googleapis.com": "analytics.googleapis.com",
    "cloudresourcemanager.googleapis.com": "cloudresourcemanager.googleapis.com",
    "dfareporting.googleapis.com": "dfareporting.googleapis.com",
    "mybusiness.googleapis.com": "mybusiness.googleapis.com",
}

def _extract_api_name(url: str) -> str | None:
    """Extract the Google API service name from a URL for enable_api()."""
    for domain, api_name in _API_URL_TO_NAME.items():
        if domain in url:
            return api_name
    return None


def _do_request(method: str, url: str, headers: dict,
                params: Optional[dict] = None,
                json_body: Optional[dict] = None,
                timeout: int = 15) -> requests.Response:
    """Execute a single HTTP request, raising on HTTP errors."""
    if method == "GET":
        r = requests.get(url, params=params, headers=headers, timeout=timeout)
    elif method == "POST":
        r = requests.post(url, params=params, headers=headers, json=json_body, timeout=timeout)
    elif method == "PUT":
        r = requests.put(url, params=params, headers=headers, json=json_body, timeout=timeout)
    elif method == "DELETE":
        r = requests.delete(url, params=params, headers=headers, timeout=timeout)
    else:
        raise ValueError(f"Unsupported method: {method}")
    r.raise_for_status()
    return r


def call_api(url: str, params: Optional[dict] = None, method: str = "GET",
             json_body: Optional[dict] = None, timeout: int = 15,
             max_retries: int = 3) -> Optional[dict]:
    """Make an authenticated request to any Google API.
    Returns parsed JSON on success, None on failure (logs warnings).
    Auto-enables the API if a 403 is received, then retries once.
    Retries with exponential backoff on 429/5xx (up to max_retries).
    """
    token = get_access_token()
    if not token:
        logger.warning("No OAuth token available for %s", url)
        return None
    if requests is None:
        return None
    headers = {"Authorization": f"Bearer {token}"}

    for attempt in range(max_retries + 1):
        try:
            r = _do_request(method, url, headers, params, json_body, timeout)
            return r.json()
        except requests.HTTPError as exc:
            body = getattr(exc.response, "text", "")
            status = getattr(exc.response, "status_code", 0)

            # Insufficient scopes — never retry, give clear guidance
            if "insufficientPermissions" in body or "insufficient authentication scopes" in body.lower():
                logger.warning("Google API call failed (insufficient scopes): %s %s", method, url)
                return None

            # 403 — try auto-enable once, then stop
            if status == 403:
                api_name = _extract_api_name(url)
                if api_name:
                    logger.info("403 on %s — attempting to enable API %s", url, api_name)
                    enable_result = enable_api(api_name)
                    if enable_result.get("success"):
                        logger.info("API %s enabled successfully, retrying request", api_name)
                        try:
                            r = _do_request(method, url, headers, params, json_body, timeout)
                            return r.json()
                        except requests.HTTPError as retry_exc:
                            retry_body = getattr(retry_exc.response, "text", "")
                            retry_status = getattr(retry_exc.response, "status_code", 0)
                            logger.warning("Still failing after enabling API (%s): %s",
                                           retry_status, retry_body[:200])
                            return None
                        except Exception as retry_exc:
                            logger.warning("Retry failed after enabling API: %s", retry_exc)
                            return None
                    else:
                        logger.warning("Could not enable API %s: %s",
                                       api_name, enable_result.get('error', 'unknown'))
                        return None
                else:
                    logger.warning("Access forbidden (403) for %s. Check API is enabled.", url)
                    return None

            # 429 (rate limit) or 5xx (transient) — retry with backoff
            if status in (429,) or (500 <= status < 600):
                if attempt < max_retries:
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    logger.info("Rate limit / server error on %s (%s), retrying in %.1fs (attempt %d/%d)",
                                url, status, delay, attempt + 1, max_retries)
                    time.sleep(delay)
                    continue
                logger.warning("Google API call failed after %d retries: %s %s -> %s", max_retries, method, url, exc)
                return None

            # Other HTTP errors — not retryable
            logger.warning("Google API call failed: %s %s -> %s", method, url, exc)
            return None

        except (requests.ConnectionError, requests.Timeout) as exc:
            # Network errors — retry with backoff
            if attempt < max_retries:
                delay = (2 ** attempt) + random.uniform(0, 1)
                logger.info("Connection/timeout on %s, retrying in %.1fs (attempt %d/%d)",
                            url, delay, attempt + 1, max_retries)
                time.sleep(delay)
                continue
            logger.warning("Google API call failed after %d retries: %s %s -> %s", max_retries, method, url, exc)
            return None

        except Exception as exc:
            logger.warning("Google API call failed: %s %s -> %s", method, url, exc)
            return None

    return None


def get_token_info() -> dict:
    """Return info about stored credentials (no secrets)."""
    creds = _load_credentials()
    if not creds:
        return {"authenticated": False}
    scopes = creds.get("scope", "").split()
    authd = creds.get("authorized_categories", [])
    return {
        "authenticated": True,
        "scope_count": len(scopes),
        "scopes": scopes,
        "authorized_categories": authd,
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
    """Enable a GCP API via Service Usage REST API."""
    token = get_access_token()
    if not token:
        return {"error": "No access token (run google_authorize first)"}
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


# ── Local HTTP server to catch OAuth redirect ──

_auth_code_storage: list[str] = []
_server_done = threading.Event()


class _RedirectHandler(http.server.BaseHTTPRequestHandler):
    """Minimal HTTP server that captures the OAuth redirect."""
    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(self.path).query)
        code = qs.get("code", [None])[0]
        if code:
            _auth_code_storage.append(code)
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authorised!</h1><p>You can close this tab.</p></body></html>")
            _server_done.set()
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Missing code</h1></body></html>")
    def log_message(self, *a, **k):
        pass


def run_auth_server(redirect_port: int = 8085) -> str | None:
    """Start local HTTP server on port, return auth code or None on timeout."""
    _auth_code_storage.clear()
    _server_done.clear()
    try:
        server = http.server.HTTPServer(("127.0.0.1", redirect_port), _RedirectHandler)
    except OSError:
        alt_ports = [8080, 8085, 9090, 8000]
        for p in alt_ports:
            if p == redirect_port:
                continue
            try:
                server = http.server.HTTPServer(("127.0.0.1", p), _RedirectHandler)
                redirect_port = p
                break
            except OSError:
                continue
        else:
            return None
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    ok = _server_done.wait(timeout=120)
    server.shutdown()
    if ok and _auth_code_storage:
        return _auth_code_storage[0]
    return None
