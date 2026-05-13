"""Friday Notification System with Windows Desktop Toasts."""

from __future__ import annotations
import threading
from datetime import datetime
from typing import Optional
import subprocess
import os

_notif_queue = []
_notif_lock = threading.Lock()


def send_notification(message: str, urgency: str = "normal", task_id: str = "") -> str:
    """Send a Windows desktop toast notification."""
    _deliver_notification(message, urgency)
    with _notif_lock:
        _notif_queue.append({
            "message": message,
            "urgency": urgency,
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "delivered": True
        })
    return f"[OK] Notification sent: {message[:50]}..."


def _deliver_notification(message: str, urgency: str):
    """Deliver Windows toast via PowerShell or plyer fallback."""
    safe_msg = message[:200].replace('"', '`"').replace("'", "''")
    try:
        ps_script = f'''
$null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$textNodes = $template.GetElementsByTagName("text")
$textNodes.Item(0).AppendChild($template.CreateTextNode("Friday")) > $null
$textNodes.Item(1).AppendChild($template.CreateTextNode("{safe_msg}")) > $null
$toast = [Windows.UI.Notifications.ToastNotification]::new($template)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Friday").Show($toast)
'''
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, timeout=5
        )
        return
    except Exception:
        pass
    try:
        from plyer import notification
        notification.notify(title="Friday", message=safe_msg, timeout=6)
        return
    except Exception:
        pass
    print(f"[NOTIFICATION - {urgency.upper()}] {message}")


def get_pending_notifications(urgency_filter: str = "") -> str:
    """Get pending notifications, optionally filtered by urgency."""
    with _notif_lock:
        if not _notif_queue:
            return "No pending notifications."
        
        filtered = _notif_queue
        if urgency_filter:
            filtered = [n for n in _notif_queue if n["urgency"] == urgency_filter]
        
        lines = [f"### Pending Notifications ({len(filtered)})"]
        for i, n in enumerate(filtered[:20]):
            lines.append(f"{i+1}. [{n['urgency'].upper()}] {n['message'][:60]}...")
        return "\n".join(lines)


def clear_notifications(task_id: str = "") -> str:
    """Clear delivered notifications, or specific task_id."""
    global _notif_queue
    with _notif_lock:
        if task_id:
            before = len(_notif_queue)
            _notif_queue = [n for n in _notif_queue if n["task_id"] != task_id]
            removed = before - len(_notif_queue)
            return f"Cleared {removed} notifications for task {task_id}."
        else:
            count = len(_notif_queue)
            _notif_queue.clear()
            return f"Cleared all {count} notifications."
