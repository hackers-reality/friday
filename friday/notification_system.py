"""FRIDAY Notification System — email, webhook, desktop notifications with queue and history."""
import os
import json
import time
import uuid
import hashlib
import threading
import urllib.request
import urllib.parse
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from collections import deque
from datetime import datetime


@dataclass
class Notification:
    notification_id: str
    title: str
    message: str
    channel: str
    severity: str
    timestamp: float
    sent: bool = False
    error: str = ""
    metadata: Dict = field(default_factory=dict)
    recipient: str = ""
    read: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass
class NotificationChannel:
    name: str
    channel_type: str
    enabled: bool = True
    config: Dict = field(default_factory=dict)
    created_at: float = 0.0

    def to_dict(self):
        return asdict(self)


class EmailNotifier:
    def __init__(self, config: Dict):
        self.smtp_host = config.get("smtp_host", "smtp.gmail.com")
        self.smtp_port = config.get("smtp_port", 587)
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.from_addr = config.get("from_addr", self.username)

    def send(self, to: str, subject: str, body: str) -> Dict:
        try:
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = self.from_addr
            msg["To"] = to
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.sendmail(self.from_addr, to, msg.as_string())
            return {"success": True, "channel": "email"}
        except Exception as e:
            return {"success": False, "error": str(e)}


class WebhookNotifier:
    def __init__(self, config: Dict):
        self.url = config.get("url", "")
        self.method = config.get("method", "POST")
        self.headers = config.get("headers", {"Content-Type": "application/json"})
        self.secret = config.get("secret", "")

    def send(self, title: str, message: str, severity: str = "info") -> Dict:
        if not self.url:
            return {"success": False, "error": "No webhook URL configured"}
        try:
            payload = {
                "text": f"*{title}*\n{message}",
                "title": title,
                "message": message,
                "severity": severity,
                "timestamp": time.time(),
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(self.url, data=data, headers=self.headers, method=self.method)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return {"success": True, "channel": "webhook", "status": resp.status}
        except Exception as e:
            return {"success": False, "error": str(e)}


class DesktopNotifier:
    def send(self, title: str, message: str) -> Dict:
        try:
            if os.name == "nt":
                try:
                    from win10toast import ToastNotifier
                    toaster = ToastNotifier()
                    toaster.show_toast(title, message, duration=5, threaded=True)
                    return {"success": True, "channel": "desktop"}
                except ImportError:
                    pass
            return {"success": False, "error": "Desktop notifications not available"}
        except Exception as e:
            return {"success": False, "error": str(e)}


class ConsoleNotifier:
    def send(self, title: str, message: str, severity: str = "info") -> Dict:
        colors = {"info": "\033[94m", "warning": "\033[93m", "error": "\033[91m", "critical": "\033[95m"}
        reset = "\033[0m"
        color = colors.get(severity, "")
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{color}[{timestamp}] [{severity.upper()}] {title}: {message}{reset}")
        return {"success": True, "channel": "console"}


class NotificationSystem:
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.expanduser("~"), ".friday", "notifications")
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        self._channels: Dict[str, NotificationChannel] = {}
        self._notifiers: Dict[str, Any] = {}
        self._history: deque = deque(maxlen=5000)
        self._queue: deque = deque(maxlen=1000)
        self._lock = threading.Lock()

        self._load_channels()
        self._register_defaults()

    def _register_defaults(self):
        self._channels["console"] = NotificationChannel(
            name="console", channel_type="console", enabled=True,
            created_at=time.time(),
        )
        self._notifiers["console"] = ConsoleNotifier()

    def _channels_file(self) -> str:
        return os.path.join(self.data_dir, "channels.json")

    def _history_file(self) -> str:
        return os.path.join(self.data_dir, "history.json")

    def _load_channels(self):
        if os.path.exists(self._channels_file()):
            try:
                with open(self._channels_file(), "r") as f:
                    data = json.load(f)
                for name, cdata in data.items():
                    self._channels[name] = NotificationChannel(**cdata)
            except Exception:
                pass

    def _save_channels(self):
        try:
            data = {name: c.to_dict() for name, c in self._channels.items()}
            with open(self._channels_file(), "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass

    def _load_history(self):
        if os.path.exists(self._history_file()):
            try:
                with open(self._history_file(), "r") as f:
                    data = json.load(f)
                for item in data[-500:]:
                    self._history.append(Notification(**item))
            except Exception:
                pass

    def _save_history(self):
        try:
            data = [n.to_dict() for n in list(self._history)[-500:]]
            with open(self._history_file(), "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass

    def add_channel(self, channel: NotificationChannel):
        with self._lock:
            self._channels[channel.name] = channel
            if channel.channel_type == "webhook":
                self._notifiers[channel.name] = WebhookNotifier(channel.config)
            elif channel.channel_type == "email":
                self._notifiers[channel.name] = EmailNotifier(channel.config)
            elif channel.channel_type == "desktop":
                self._notifiers[channel.name] = DesktopNotifier()
            self._save_channels()

    def remove_channel(self, name: str) -> bool:
        with self._lock:
            if name in self._channels and name != "console":
                del self._channels[name]
                self._notifiers.pop(name, None)
                self._save_channels()
                return True
            return False

    def list_channels(self) -> List[Dict]:
        with self._lock:
            return [c.to_dict() for c in self._channels.values()]

    def send(self, title: str, message: str, channel: str = "console",
             severity: str = "info", recipient: str = "", metadata: Dict = None) -> Dict:
        notification = Notification(
            notification_id=f"notif-{uuid.uuid4().hex[:8]}",
            title=title,
            message=message,
            channel=channel,
            severity=severity,
            timestamp=time.time(),
            recipient=recipient,
            metadata=metadata or {},
        )

        notifier = self._notifiers.get(channel)
        if not notifier:
            notification.error = f"Channel not found: {channel}"
            with self._lock:
                self._history.append(notification)
            return {"success": False, "error": notification.error}

        try:
            if isinstance(notifier, WebhookNotifier):
                result = notifier.send(title, message, severity)
            elif isinstance(notifier, EmailNotifier):
                result = notifier.send(recipient, title, message)
            elif isinstance(notifier, ConsoleNotifier):
                result = notifier.send(title, message, severity)
            elif isinstance(notifier, DesktopNotifier):
                result = notifier.send(title, message)
            else:
                result = {"success": False, "error": "Unknown notifier type"}

            notification.sent = result.get("success", False)
            if not result.get("success"):
                notification.error = result.get("error", "Unknown error")
        except Exception as e:
            notification.sent = False
            notification.error = str(e)

        with self._lock:
            self._history.append(notification)
            if len(self._history) % 10 == 0:
                self._save_history()

        return {"success": notification.sent, "notification_id": notification.notification_id,
                "error": notification.error}

    def send_many(self, title: str, message: str, channels: List[str] = None,
                  severity: str = "info") -> List[Dict]:
        if channels is None:
            channels = list(self._channels.keys())
        results = []
        for channel in channels:
            result = self.send(title, message, channel, severity)
            results.append(result)
        return results

    def get_history(self, channel: str = None, limit: int = 50) -> List[Dict]:
        with self._lock:
            history = list(self._history)
        if channel:
            history = [n for n in history if n.channel == channel]
        return [n.to_dict() for n in history[-limit:]]

    def get_unread(self, limit: int = 50) -> List[Dict]:
        with self._lock:
            unread = [n for n in self._history if not n.read]
        return [n.to_dict() for n in unread[-limit:]]

    def mark_read(self, notification_id: str) -> bool:
        with self._lock:
            for n in self._history:
                if n.notification_id == notification_id:
                    n.read = True
                    return True
            return False

    def clear_history(self):
        with self._lock:
            self._history.clear()
            self._save_history()

    def get_stats(self) -> Dict:
        with self._lock:
            history = list(self._history)
            total = len(history)
            sent = sum(1 for n in history if n.sent)
            failed = sum(1 for n in history if not n.sent and n.error)
            by_channel = {}
            by_severity = {}
            for n in history:
                by_channel[n.channel] = by_channel.get(n.channel, 0) + 1
                by_severity[n.severity] = by_severity.get(n.severity, 0) + 1
            return {
                "total": total,
                "sent": sent,
                "failed": failed,
                "success_rate": round(sent / total * 100, 2) if total > 0 else 0,
                "by_channel": by_channel,
                "by_severity": by_severity,
                "channels": len(self._channels),
            }


_system = None


def _get_system() -> NotificationSystem:
    global _system
    if _system is None:
        _system = NotificationSystem()
    return _system


def notification_system_tool(action: str = "send", **kwargs) -> Any:
    """Notification system tool dispatcher."""
    try:
        system = _get_system()

        if action == "send":
            title = kwargs.get("title", "")
            message = kwargs.get("message", "")
            channel = kwargs.get("channel", "console")
            severity = kwargs.get("severity", "info")
            recipient = kwargs.get("recipient", "")
            if not title or not message:
                return {"error": "title and message required"}
            return system.send(title, message, channel, severity, recipient)

        elif action == "send_many":
            title = kwargs.get("title", "")
            message = kwargs.get("message", "")
            channels = kwargs.get("channels")
            severity = kwargs.get("severity", "info")
            if not title or not message:
                return {"error": "title and message required"}
            return {"results": system.send_many(title, message, channels, severity)}

        elif action == "channels":
            return {"channels": system.list_channels()}

        elif action == "add_channel":
            channel_data = kwargs.get("channel", {})
            channel = NotificationChannel(**channel_data)
            system.add_channel(channel)
            return {"success": True}

        elif action == "remove_channel":
            name = kwargs.get("name", "")
            ok = system.remove_channel(name)
            return {"success": ok}

        elif action == "history":
            channel = kwargs.get("channel")
            limit = kwargs.get("limit", 50)
            return {"history": system.get_history(channel, limit)}

        elif action == "unread":
            limit = kwargs.get("limit", 50)
            return {"unread": system.get_unread(limit)}

        elif action == "mark_read":
            notification_id = kwargs.get("notification_id", "")
            ok = system.mark_read(notification_id)
            return {"success": ok}

        elif action == "clear":
            system.clear_history()
            return {"success": True}

        elif action == "stats":
            return system.get_stats()

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        return {"error": str(e)}
