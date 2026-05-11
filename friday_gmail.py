"""Friday Gmail / Google Cloud Integration — unified Gmail + Calendar OAuth."""
from __future__ import annotations
import base64
import os
import json
from typing import Optional, Any

from dotenv import load_dotenv
load_dotenv()

_ROOT = os.path.dirname(os.path.abspath(__file__))

# Unified scopes — covers both Gmail and Calendar
_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

_TOKEN_PATH = os.path.join(_ROOT, ".gmail_token.json")


def _get_credentials() -> Any | None:
    """Get cached OAuth credentials (Gmail + Calendar scopes)."""
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
            else:
                creds_path = os.path.join(_ROOT, "credentials.json")
                if not os.path.exists(creds_path):
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, _SCOPES)
                flow.open_browser = True
                creds = flow.run_local_server(port=8080)
            with open(_TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
        return creds
    except Exception:
        return None


def _get_gmail_service():
    """Get authenticated Gmail service (uses unified .gmail_token.json)."""
    try:
        creds = _get_credentials()
        if not creds:
            return None
        from googleapiclient.discovery import build
        return build("gmail", "v1", credentials=creds)
    except Exception:
        return None


def google_authorize() -> str:
    """Authorize ALL Google services (Gmail + Calendar). Same as gmail_authorize."""
    return gmail_authorize()


def gmail_authorize() -> str:
    """Run unified OAuth flow for Gmail + Calendar. Opens browser for consent.
    Only needed once — subsequent calls reuse the saved token.
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

        creds = _get_credentials()
        if creds:
            return f"[OK] Already authorized. Token at {_TOKEN_PATH}"
        
        # Force fresh authorization
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(creds_path, _SCOPES)
        creds = flow.run_local_server(port=8080, open_browser=True)
        
        with open(_TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

        # Clean up old Calendar token (now unified)
        old_cal_token = os.path.join(os.path.dirname(_ROOT), "friday_memory", "calendar_token.json")
        if os.path.exists(old_cal_token):
            os.remove(old_cal_token)

        return (
            f"[OK] Unified authorization complete! Token saved to {_TOKEN_PATH}\n"
            "Gmail and Google Calendar are now ready."
        )
    except Exception as e:
        return f"[FAIL] Authorization failed: {e}"


def gmail_list_messages(query: str = "is:unread", max_results: int = 10) -> str:
    """List Gmail messages matching query."""
    try:
        service = _get_gmail_service()
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
        
        service = _get_gmail_service()
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
        
        service = _get_gmail_service()
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
        service = _get_gmail_service()
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
