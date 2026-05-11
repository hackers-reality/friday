"""
Friday Message Channels - Multi-platform messaging.
Send and receive messages across Telegram, Discord, and webhook channels.
"""
from __future__ import annotations

import json
import os
import requests
from typing import Dict, Any, Optional


#  Telegram Channel  #

class TelegramChannel:
    """Send/receive messages via Telegram Bot API."""

    def __init__(self, token: str = None):
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else None

    def is_configured(self) -> bool:
        return bool(self.token)

    def send_message(self, chat_id: str, text: str) -> str:
        """Send a Telegram message."""
        if not self.is_configured():
            return "[FAIL] Telegram not configured. Set TELEGRAM_BOT_TOKEN"
        try:
            resp = requests.post(
                f"{self.base_url}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                timeout=10,
            )
            if resp.status_code == 200:
                return f"[OK] Telegram message sent to {chat_id}"
            return f"[FAIL] Telegram error: {resp.status_code} - {resp.text}"
        except Exception as e:
            return f"[FAIL] Telegram error: {e}"

    def get_updates(self, limit: int = 10) -> str:
        """Get recent Telegram messages."""
        if not self.is_configured():
            return "[FAIL] Telegram not configured. Set TELEGRAM_BOT_TOKEN"
        try:
            resp = requests.get(
                f"{self.base_url}/getUpdates",
                params={"limit": limit, "timeout": 5},
                timeout=10,
            )
            if resp.status_code != 200:
                return f"[FAIL] Telegram error: {resp.status_code}"
            data = resp.json()
            if not data.get("ok") or not data.get("result"):
                return "[OK] No new Telegram messages."
            results = data["result"]
            lines = ["### TELEGRAM MESSAGES"]
            for msg in results[-limit:]:
                message = msg.get("message", {})
                chat = message.get("chat", {})
                text = message.get("text", "[non-text]")
                from_user = message.get("from", {}).get("first_name", "Unknown")
                lines.append(f"- [{chat.get('title', chat.get('id', '?'))}] {from_user}: {text}")
            return "\n".join(lines)
        except Exception as e:
            return f"[FAIL] Telegram error: {e}"


#  Discord Channel  #

class DiscordChannel:
    """Send messages via Discord webhook."""

    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL")

    def is_configured(self) -> bool:
        return bool(self.webhook_url)

    def send_message(self, content: str, username: str = "Friday") -> str:
        """Send a Discord message via webhook."""
        if not self.is_configured():
            return "[FAIL] Discord not configured. Set DISCORD_WEBHOOK_URL"
        try:
            resp = requests.post(
                self.webhook_url,
                json={"content": content, "username": username},
                timeout=10,
            )
            if resp.status_code in (200, 204):
                return f"[OK] Discord message sent as {username}"
            return f"[FAIL] Discord error: {resp.status_code}"
        except Exception as e:
            return f"[FAIL] Discord error: {e}"


#  Generic Webhook Channel  #

class WebhookChannel:
    """Send messages to any webhook URL."""

    def send_message(self, url: str, payload: Dict[str, Any]) -> str:
        """Send a message to a custom webhook."""
        try:
            resp = requests.post(url, json=payload, timeout=10)
            if resp.status_code in (200, 201, 202, 204):
                return f"[OK] Webhook message sent to {url}"
            return f"[FAIL] Webhook error: {resp.status_code}"
        except Exception as e:
            return f"[FAIL] Webhook error: {e}"


#  Message Channel Manager  #

class MessageChannelManager:
    """Manages all message channels."""

    def __init__(self):
        self.telegram = TelegramChannel()
        self.discord = DiscordChannel()
        self.webhook = WebhookChannel()
        self._message_log: list = []

    def send(self, channel: str, target: str, message: str) -> str:
        """Send a message via the specified channel."""
        self._message_log.append({"channel": channel, "target": target, "message": message, "direction": "out"})

        if channel == "telegram":
            return self.telegram.send_message(target, message)
        elif channel == "discord":
            return self.discord.send_message(message, username=target or "Friday")
        elif channel == "webhook":
            return self.webhook.send_message(target, {"text": message})
        else:
            return f"[FAIL] Unknown channel: {channel}. Available: telegram, discord, webhook"

    def receive(self, channel: str, limit: int = 10) -> str:
        """Receive messages from a channel."""
        if channel == "telegram":
            return self.telegram.get_updates(limit=limit)
        elif channel == "discord":
            return "[INFO] Discord receive requires bot intents. Use webhook for outgoing only."
        else:
            return f"[FAIL] Unknown channel: {channel}"

    def status(self) -> str:
        """Get status of all channels."""
        lines = ["### MESSAGE CHANNELS STATUS"]
        lines.append(f"**Telegram**: {'[OK]' if self.telegram.is_configured() else '[OFF]'} (set TELEGRAM_BOT_TOKEN)")
        lines.append(f"**Discord**: {'[OK]' if self.discord.is_configured() else '[OFF]'} (set DISCORD_WEBHOOK_URL)")
        lines.append(f"**Message log**: {len(self._message_log)} messages")
        return "\n".join(lines)


#  Singleton  #

_manager: Optional[MessageChannelManager] = None


def get_channel_manager() -> MessageChannelManager:
    global _manager
    if _manager is None:
        _manager = MessageChannelManager()
    return _manager


#  Tool Function for Friday  #

def message_channel_tool(
    action: str = "status",
    channel: str = None,
    target: str = None,
    message: str = None,
    limit: int = 10,
) -> str:
    """
    Friday tool for multi-platform messaging.
    Actions: status (check config), send (send message), receive (get messages)
    Channels: telegram, discord, webhook
    """
    manager = get_channel_manager()

    if action == "status":
        return manager.status()

    if action == "send":
        if not channel or not message:
            return "[FAIL] channel and message required."
        return manager.send(channel.lower(), target or "", message)

    if action == "receive":
        if not channel:
            return "[FAIL] channel required."
        return manager.receive(channel.lower(), limit=limit)

    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Message Channels...\n")
    manager = get_channel_manager()
    print(manager.status())
