"""Friday Notification System with Urgency Detection."""

from __future__ import annotations
import threading
from datetime import datetime
from typing import Optional

import os

_notif_queue = []
_notif_lock = threading.Lock()


def send_notification(message: str, urgency: str = "normal", task_id: str = "") -> str:
    """Send notification with urgency detection."""
    with _notif_lock:
        _notif_queue.append({
            "message": message,
            "urgency": urgency,
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "delivered": False
        })
    
    # Immediate delivery for urgent
    if urgency == "urgent":
        _deliver_notification(message, urgency)
        return f"Urgent notification sent: {message[:50]}..."
    return f"Notification queued: {message[:50]}..."


def _deliver_notification(message: str, urgency: str):
    """Deliver notification via available channels."""
    try:
        try:
            from win10toast import ToastNotifier
            ToastNotifier().show_toast(
                "Friday",
                message[:200],
                duration=5,
                icon_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "friday.ico")
            )
        except ImportError:
            # Fallback to console
            print(f"[NOTIFICATION - {urgency.upper()}] {message}")
    except Exception:
        pass


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
