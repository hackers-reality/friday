"""Friday Gmail / Google Cloud Integration — unified Gmail + Calendar OAuth."""
from __future__ import annotations
import base64
import os
import json
import re
import urllib.parse
import threading
import http.server
from typing import Optional, Any

from dotenv import load_dotenv
load_dotenv()

from friday._paths import PROJECT_ROOT as _ROOT

# Unified scopes — single source from google_oauth.py
from friday.google_oauth import SCOPE_CLOUD_PLATFORM, SCOPES as _OAUTH_SCOPES
_SCOPES = [SCOPE_CLOUD_PLATFORM] + _OAUTH_SCOPES

_TOKEN_PATH = os.path.join(_ROOT, ".gmail_token.json")

# ─── Manual code exchange (bypasses google_auth_oauthlib SSL issues) ─────

def _exchange_code_manual(code: str, flow) -> Any:
    """Exchange authorization code for token using requests directly."""
    import requests as req
    try:
        import certifi
        verify = certifi.where()
    except ImportError:
        verify = True
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": flow.client_config["client_id"],
        "client_secret": flow.client_config["client_secret"],
        "redirect_uri": flow.redirect_uri,
        "grant_type": "authorization_code",
    }
    resp = req.post(token_url, data=data, verify=verify, timeout=30)
    resp.raise_for_status()
    token_json = resp.json()
    from google.oauth2.credentials import Credentials
    return Credentials(
        token=token_json.get("access_token"),
        refresh_token=token_json.get("refresh_token"),
        id_token=token_json.get("id_token"),
        token_uri=token_url,
        client_id=flow.client_config["client_id"],
        client_secret=flow.client_config["client_secret"],
        scopes=_SCOPES,
    )


def _run_local_server_with_fallback(flow) -> Any:
    """Run OAuth local server, fall back to manual exchange if SSL fails."""
    auth_code = []
    server_done = threading.Event()

    # Use port from flow.redirect_uri
    parsed = urllib.parse.urlparse(flow.redirect_uri or "http://localhost:8080/")
    host = parsed.hostname or "localhost"
    port = parsed.port or 8080

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            if "code" in params:
                auth_code.append(params["code"][0])
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body><h1>Authorized!</h1><p>Close this tab.</p></body></html>")
                server_done.set()
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing code")
        def log_message(self, *a):
            pass

    server = http.server.HTTPServer((host, port), Handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
    import webbrowser
    webbrowser.open(auth_url)

    if not server_done.wait(timeout=120):
        server.shutdown()
        raise TimeoutError("Authorization timed out after 120 seconds.")
    server.shutdown()

    code = auth_code[0]

    # Try manual exchange first (avoids google_auth_oauthlib SSL bugs)
    try:
        return _exchange_code_manual(code, flow)
    except Exception:
        pass

    flow.fetch_token(code=code)
    return flow.credentials


def _get_credentials(auto_auth: bool = True) -> Any | None:
    """Get cached OAuth credentials (Gmail + Calendar scopes).
    If auto_auth=False, skips OAuth flow and returns None if no cached token exists.
    """
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        
        creds = None
        if os.path.exists(_TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(_TOKEN_PATH, _SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
            elif auto_auth:
                creds_path = os.path.join(_ROOT, "credentials.json")
                if not os.path.exists(creds_path):
                    return None
                redirect_uri = _read_redirect_uri_from_config(creds_path)
                parsed = urllib.parse.urlparse(redirect_uri)
                port = parsed.port or 8080
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, _SCOPES)
                flow.redirect_uri = redirect_uri
                flow.open_browser = True
                try:
                    creds = flow.run_local_server(port=port, open_browser=True)
                except Exception:
                    creds = _run_local_server_with_fallback(flow)
                with open(_TOKEN_PATH, "w") as f:
                    f.write(creds.to_json())
            else:
                return None
        return creds
    except Exception:
        return None


def _get_gmail_service(auto_auth: bool = True):
    """Get authenticated Gmail service (uses unified .gmail_token.json).
    If auto_auth=False, skips OAuth flow if no cached token exists.
    """
    try:
        creds = _get_credentials(auto_auth=auto_auth)
        if not creds:
            return None
        from googleapiclient.discovery import build
        return build("gmail", "v1", credentials=creds)
    except Exception:
        return None


def google_authorize() -> str:
    """Authorize ALL Google services (Gmail + Calendar). Same as gmail_authorize."""
    return gmail_authorize()


def _read_redirect_uri_from_config(creds_path: str) -> str:
    """Read the first redirect_uri from credentials.json, fall back to localhost:8080/."""
    try:
        with open(creds_path) as f:
            cfg = json.load(f)
        uris = cfg.get("web", cfg.get("installed", {})).get("redirect_uris", [])
        if uris:
            return uris[0]
    except Exception:
        pass
    return "http://localhost:8080/"


def _start_local_server_on(uri: str) -> tuple[http.server.HTTPServer, int]:
    """Start an HTTP server on the host+port parsed from redirect URI."""
    parsed = urllib.parse.urlparse(uri)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8080
    server = http.server.HTTPServer((host, port), _OAuthHandler)
    return server, port


class _OAuthHandler(http.server.BaseHTTPRequestHandler):
    """Minimal OAuth callback handler — captures the code, responds OK."""
    auth_code: list[str] = []
    server_done: threading.Event | None = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            type(self).auth_code.append(params["code"][0])
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authorized!</h1><p>Close this tab.</p></body></html>")
            if type(self).server_done:
                type(self).server_done.set()
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing code")
    def log_message(self, *a):
        pass


def gmail_authorize() -> str:
    """Run unified OAuth flow for Gmail + Calendar. Opens browser for consent.
    Only needed once — subsequent calls reuse the saved token.

    Starts a local server on the port from credentials.json (or 8080)
    BEFORE opening the browser, so the OAuth redirect is caught automatically.
    """
    try:
        creds_path = os.path.join(_ROOT, "credentials.json")
        if not os.path.exists(creds_path):
            return (
                "[FAIL] credentials.json not found. Download from Google Cloud Console:\n"
                "  1. Go to https://console.cloud.google.com/\n"
                "  2. Create project → Enable Gmail API + Google Calendar API\n"
                "  3. Credentials → Create OAuth 2.0 Client ID (Desktop app)\n"
                "  4. Download JSON → save as credentials.json in the Friday folder"
            )

        if _get_credentials(auto_auth=False):
            return f"[OK] Already authorized. Token at {_TOKEN_PATH}"

        # Read the redirect URI from credentials.json so it matches the console config
        redirect_uri = _read_redirect_uri_from_config(creds_path)

        # Start local server on that URI BEFORE opening browser
        server, port = _start_local_server_on(redirect_uri)
        _OAuthHandler.auth_code = []
        _OAuthHandler.server_done = threading.Event()
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(creds_path, _SCOPES)
        flow.redirect_uri = redirect_uri
        auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")

        import webbrowser
        webbrowser.open(auth_url)
        print(f"\n  Browser opened to Google OAuth. Listening on {redirect_uri}")

        if not _OAuthHandler.server_done.wait(timeout=120):
            server.shutdown()
            return "[FAIL] Authorization timed out after 120 seconds. Try exchange_oauth_code() with the redirect URL from your browser."

        server.shutdown()
        code = _OAuthHandler.auth_code[0]

        # Exchange manually (avoids google_auth_oauthlib SSL bugs)
        creds = _exchange_code_manual(code, flow)
        if not creds:
            flow.fetch_token(code=code)
            creds = flow.credentials

        if creds:
            with open(_TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
            return f"[OK] Token saved! Gmail and Calendar are now ready."

        return "[FAIL] Authorization failed. Try exchange_oauth_code() with the redirect URL from your browser."
    except Exception as e:
        return f"[FAIL] Authorization failed: {e}"


def exchange_oauth_code(redirect_url: str) -> str:
    """Complete OAuth by pasting the browser redirect URL.
    Use this if the auto-flow fails — paste the full URL from the browser address bar.
    """
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        creds_path = os.path.join(_ROOT, "credentials.json")
        if not os.path.exists(creds_path):
            return "[FAIL] credentials.json not found in Friday folder."

        # Extract code from URL
        parsed = urllib.parse.urlparse(redirect_url)
        params = urllib.parse.parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        if not code:
            return "[FAIL] No authorization code found in URL. Make sure you paste the full redirect URL."

        redirect_uri = _read_redirect_uri_from_config(creds_path)
        flow = InstalledAppFlow.from_client_secrets_file(creds_path, _SCOPES)
        flow.redirect_uri = redirect_uri
        creds = _exchange_code_manual(code, flow)

        with open(_TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

        # Sync to google_oauth credential store
        try:
            from friday.google_oauth import _save_credentials
            from datetime import datetime, timedelta
            _save_credentials({
                "access_token": creds.token,
                "refresh_token": creds.refresh_token,
                "expires_at": (datetime.utcnow() + timedelta(seconds=3600)).isoformat() if creds.expiry is None else creds.expiry.isoformat(),
                "scope": " ".join(creds.scopes),
                "token_type": "Bearer",
                "created_at": datetime.utcnow().isoformat(),
            })
        except Exception:
            pass

        old_cal_token = os.path.join(os.path.dirname(_ROOT), "friday_memory", "calendar_token.json")
        if os.path.exists(old_cal_token):
            os.remove(old_cal_token)

        return f"[OK] Token saved! Gmail and Calendar are now ready."
    except Exception as e:
        return f"[FAIL] Code exchange failed: {e}"


def gmail_list_messages(query: str = "is:unread", max_results: int = 10) -> str:
    """List Gmail messages matching query."""
    try:
        service = _get_gmail_service(auto_auth=False)
        if not service:
            return "Gmail not configured. Place credentials.json in Friday folder."
        
        result = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        
        messages = result.get("messages", [])
        if not messages:
            return "No messages found."
        
        lines = [f"### Gmail Messages ({len(messages)})"]
        for msg in messages[:10]:
            m = service.users().messages().get(
                userId="me", id=msg["id"], format="metadata"
            ).execute()
            headers = {h["name"]: h["value"] for h in m["payload"]["headers"]}
            lines.append(f"{headers.get('From', 'Unknown')}: {headers.get('Subject', '(No Subject)')}")
        
        return "\n".join(lines)
    except Exception as e:
        return f"Gmail error: {e}"


def gmail_send(to: str, subject: str, body: str) -> str:
    """Send email via Gmail API."""
    try:
        from email.mime.text import MIMEText
        
        service = _get_gmail_service(auto_auth=False)
        if not service:
            return "Gmail not configured."
        
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        
        return f"Email sent to {to}."
    except Exception as e:
        return f"Send error: {e}"


def gmail_draft(to: str, subject: str, body: str) -> str:
    """Create draft email."""
    try:
        from email.mime.text import MIMEText
        
        service = _get_gmail_service(auto_auth=False)
        if not service:
            return "Gmail not configured."
        
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().drafts().create(
            userId="me", body={"message": {"raw": raw}}
        ).execute()
        
        return f"Draft saved for {to}."
    except Exception as e:
        return f"Draft error: {e}"


def gmail_read_message(message_id: str) -> str:
    """Read a specific Gmail message."""
    try:
        service = _get_gmail_service(auto_auth=False)
        if not service:
            return "Gmail not configured."
        
        m = service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()
        
        headers = {h["name"]: h["value"] for h in m["payload"]["headers"]}
        body = ""
        if "parts" in m["payload"]:
            for part in m["payload"]["parts"]:
                if part["mimeType"] == "text/plain":
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode()
                    break
        
        return f"From: {headers.get('From', '')}\nSubject: {headers.get('Subject', '')}\n\n{body[:500]}"
    except Exception as e:
        return f"Read error: {e}"
