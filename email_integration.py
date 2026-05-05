"""
Friday Email Integration - IMAP/SMTP for email operations.
Read, send, and manage emails programmatically.
"""
from __future__ import annotations

import os
import json
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
from datetime import datetime


# ─── Email Client ────────────────────────────────────#

class EmailClient:
    """Email client for IMAP/SMTP operations."""
    
    def __init__(self):
        self.imap_host = os.environ.get("EMAIL_IMAP_HOST", "imap.gmail.com")
        self.imap_port = int(os.environ.get("EMAIL_IMAP_PORT", "993"))
        self.smtp_host = os.environ.get("EMAIL_SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
        self.email = os.environ.get("EMAIL_ADDRESS")
        self.password = os.environ.get("EMAIL_PASSWORD")
        self.imap = None
    
    def is_configured(self) -> bool:
        """Check if email is configured."""
        return bool(self.email and self.password)
    
    def connect_imap(self) -> bool:
        """Connect to IMAP server."""
        if not self.is_configured():
            return False
        try:
            self.imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            self.imap.login(self.email, self.password)
            return True
        except Exception as e:
            print(f"[Email] IMAP connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from IMAP."""
        if self.imap:
            try:
                self.imap.close()
                self.imap.logout()
            except:
                pass
            self.imap = None
    
    def list_folders(self) -> List[str]:
        """List IMAP folders."""
        if not self.imap and not self.connect_imap():
            return ["❌ Not connected"]
        try:
            status, folders = self.imap.list()
            if status != "OK":
                return ["❌ Error listing folders"]
            return [f.decode().split('"/"')[-1].strip() for f in folders]
        except Exception as e:
            return [f"❌ Error: {e}"]
    
    def get_emails(self, folder: str = "INBOX", limit: int = 10, unread_only: bool = False) -> List[Dict]:
        """Get emails from folder."""
        if not self.imap and not self.connect_imap():
            return [{"error": "Not connected"}]
        
        try:
            self.imap.select(folder)
            
            search_criteria = "UNSEEN" if unread_only else "ALL"
            status, messages = self.imap.search(None, search_criteria)
            
            if status != "OK":
                return [{"error": "Search failed"}]
            
            email_ids = messages[0].split()
            email_ids = email_ids[-limit:]  # Get last 'limit' emails
            email_ids.reverse()  # Most recent first
            
            emails = []
            for eid in email_ids:
                status, msg_data = self.imap.fetch(eid, "(RFC822)")
                if status != "OK":
                    continue
                
                msg = email.message_from_bytes(msg_data[0][1])
                
                # Parse email
                subject = msg.get("Subject", "")
                from_addr = msg.get("From", "")
                date = msg.get("Date", "")
                
                # Get body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                            break
                else:
                    body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                
                emails.append({
                    "id": eid.decode(),
                    "subject": subject,
                    "from": from_addr,
                    "date": date,
                    "body": body[:500],  # Truncate
                    "snippet": body[:100],
                })
            
            return emails
            
        except Exception as e:
            return [{"error": str(e)}]
    
    def send_email(self, to: str, subject: str, body: str, html: bool = False) -> str:
        """Send an email via SMTP."""
        if not self.is_configured():
            return "❌ Email not configured. Set EMAIL_ADDRESS and EMAIL_PASSWORD."
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.email
            msg["To"] = to
            
            if html:
                msg.attach(MIMEText(body, "html"))
            else:
                msg.attach(MIMEText(body, "plain"))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.send_message(msg)
            
            return f"✅ Email sent to {to}"
            
        except Exception as e:
            return f"❌ Send error: {e}"
    
    def delete_email(self, email_id: str, folder: str = "INBOX") -> str:
        """Delete an email by ID."""
        if not self.imap and not self.connect_imap():
            return "❌ Not connected"
        
        try:
            self.imap.select(folder)
            self.imap.store(email_id, "+FLAGS", "\\Deleted")
            self.imap.expunge()
            return f"✅ Email {email_id} deleted"
        except Exception as e:
            return f"❌ Delete error: {e}"
    
    def mark_read(self, email_id: str, folder: str = "INBOX") -> str:
        """Mark email as read."""
        if not self.imap and not self.connect_imap():
            return "❌ Not connected"
        
        try:
            self.imap.select(folder)
            self.imap.store(email_id, "-FLAGS", "\\Seen")
            return f"✅ Email {email_id} marked as read"
        except Exception as e:
            return f"❌ Error: {e}"


# ─── Singleton Client ────────────────────────────────────#

_client: Optional[EmailClient] = None

def get_email_client() -> EmailClient:
    """Get or create email client."""
    global _client
    if _client is None:
        _client = EmailClient()
    return _client


# ─── Tool Function for Friday ────────────────────────────────────#

def email_tool(
    action: str = "status",
    to: str = None,
    subject: str = None,
    body: str = None,
    folder: str = "INBOX",
    limit: int = 10,
    email_id: str = None,
    unread_only: bool = False,
) -> str:
    """
    Friday tool for email operations.
    Actions: status, folders, list, send, delete, mark_read
    """
    client = get_email_client()
    
    if action == "status":
        if client.is_configured():
            return f"✅ Email configured: {client.email}"
        return "❌ Email not configured.\nSet EMAIL_ADDRESS and EMAIL_PASSWORD in .env"
    
    if action == "folders":
        if not client.connect_imap():
            return "❌ Could not connect to IMAP server."
        folders = client.list_folders()
        client.disconnect()
        return "### EMAIL FOLDERS\n" + "\n".join(f"- {f}" for f in folders)
    
    if action == "list":
        if not client.connect_imap():
            return "❌ Could not connect to IMAP server."
        emails = client.get_emails(folder, limit, unread_only)
        client.disconnect()
        
        if not emails:
            return "No emails found."
        if "error" in emails[0]:
            return f"❌ {emails[0]['error']}"
        
        lines = [f"### EMAILS ({folder}, {len(emails)} shown)", ""]
        for e in emails:
            lines.append(f"**{e['subject'] or '(No subject)'}**")
            lines.append(f"  From: {e['from']}")
            lines.append(f"  Date: {e['date']}")
            lines.append(f"  {e['snippet']}...")
            lines.append("")
        
        return "\n".join(lines)
    
    if action == "send":
        if not to or not subject or body is None:
            return "❌ 'to', 'subject', and 'body' required for send."
        return client.send_email(to, subject, body)
    
    if action == "delete":
        if not email_id:
            return "❌ email_id required for delete."
        if not client.connect_imap():
            return "❌ Could not connect."
        result = client.delete_email(email_id, folder)
        client.disconnect()
        return result
    
    if action == "mark_read":
        if not email_id:
            return "❌ email_id required for mark_read."
        if not client.connect_imap():
            return "❌ Could not connect."
        result = client.mark_read(email_id, folder)
        client.disconnect()
        return result
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Email Integration...")
    
    client = get_email_client()
    
    print("\n--- Status ---")
    print(email_tool("status"))
    
    if client.is_configured():
        print("\n--- Folders ---")
        print(email_tool("folders"))
        
        print("\n--- Recent Emails ---")
        print(email_tool("list", limit=5))
