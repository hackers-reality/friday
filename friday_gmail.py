"""Friday Gmail / Google Cloud Integration."""

from __future__ import annotations
import base64
import os
import json
from typing import Optional

from dotenv import load_dotenv
load_dotenv()


def _get_gmail_service():
    """Get authenticated Gmail service."""
    try:
        from google.oauth2.credentials import Credentials
        from google.oauth2.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        
        SCOPES = [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.modify",
        ]
        
        creds = None
        token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".gmail_token.json")
        
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                creds_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json")
                if not os.path.exists(creds_path):
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, "w") as token:
                token.write(creds.to_json())
        
        return build("gmail", "v1", credentials=creds)
    except Exception:
        return None


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
