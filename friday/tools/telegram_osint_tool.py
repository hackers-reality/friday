"""
Telegram OSINT Tool — channel scraping, user resolution, message history.
Wraps the Telethon library for FRIDAY OSINT profiling.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from friday.logging_utils import configure_logging

logger = configure_logging(__name__)


@dataclass
class TelegramMessage:
    id: int
    date: str
    text: str
    sender_id: Optional[int] = None
    sender_username: Optional[str] = None
    sender_name: Optional[str] = None
    views: Optional[int] = None
    forwards: Optional[int] = None


@dataclass
class TelegramChannelInfo:
    id: int
    title: str
    username: Optional[str] = None
    about: Optional[str] = None
    members_count: Optional[int] = None
    admins_count: Optional[int] = None
    photo: Optional[str] = None
    is_private: bool = False
    is_verified: bool = False
    is_scam: bool = False
    is_fake: bool = False


@dataclass
class TelegramUserInfo:
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    photo: Optional[str] = None
    is_bot: bool = False
    is_verified: bool = False
    is_scam: bool = False
    is_fake: bool = False
    last_online: Optional[str] = None


@dataclass
class TelegramResult:
    success: bool = False
    error: Optional[str] = None
    scan_time_s: float = 0.0
    channel: Optional[TelegramChannelInfo] = None
    user: Optional[TelegramUserInfo] = None
    messages: list[TelegramMessage] = field(default_factory=list)


def _get_credentials() -> tuple[str, str]:
    api_id = os.environ.get("TELEGRAM_API_ID", "")
    api_hash = os.environ.get("TELEGRAM_API_HASH", "")
    return api_id, api_hash


async def _ensure_telethon_installed() -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            _python(), "-c", "import telethon; print(telethon.__version__)",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=10)
        if proc.returncode == 0:
            return True
    except Exception:
        pass
    logger.info("telethon not found — attempting pip install telethon ...")
    try:
        proc = await asyncio.create_subprocess_exec(
            _python(), "-m", "pip", "install", "telethon",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode != 0:
            logger.warning("telethon install failed: %s", stderr.decode(errors="replace")[:200])
            return False
        return True
    except Exception as exc:
        logger.warning("telethon install exception: %s", exc)
        return False


def _python() -> str:
    import sys
    return sys.executable


async def resolve_telegram_user(
    identifier: str,
    timeout: int = 30,
) -> TelegramResult:
    """
    Resolve a Telegram user by username or phone number.

    Args:
        identifier: Username (without @), phone number, or user ID
        timeout: Timeout in seconds

    Returns:
        TelegramResult with user info
    """
    available = await _ensure_telethon_installed()
    if not available:
        return TelegramResult(error="telethon not installed")

    api_id, api_hash = _get_credentials()
    if not api_id or not api_hash:
        return TelegramResult(error="TELEGRAM_API_ID and TELEGRAM_API_HASH must be set")

    t0 = time.time()
    try:
        from telethon import TelegramClient
        from telethon.errors import UsernameNotOccupiedError, FloodWaitError

        session_name = f"friday_telegram_{abs(hash(identifier))}"
        client = TelegramClient(session_name, int(api_id), api_hash)

        try:
            await asyncio.wait_for(client.start(), timeout=timeout)
        except Exception:
            return TelegramResult(
                error="Telegram login failed — check API credentials or handle phone code",
                scan_time_s=round(time.time() - t0, 2),
            )

        try:
            entity = await asyncio.wait_for(
                client.get_entity(identifier), timeout=timeout
            )
        except UsernameNotOccupiedError:
            await client.disconnect()
            return TelegramResult(
                error=f"User/channel '{identifier}' not found",
                scan_time_s=round(time.time() - t0, 2),
            )
        except ValueError as e:
            await client.disconnect()
            return TelegramResult(
                error=f"Invalid identifier: {e}",
                scan_time_s=round(time.time() - t0, 2),
            )
        except FloodWaitError as e:
            await client.disconnect()
            return TelegramResult(
                error=f"Rate limited: wait {e.seconds}s",
                scan_time_s=round(time.time() - t0, 2),
            )

        result = TelegramResult(success=True, scan_time_s=round(time.time() - t0, 2))

        if hasattr(entity, "title"):
            result.channel = TelegramChannelInfo(
                id=entity.id,
                title=entity.title,
                username=entity.username,
                about=getattr(entity, "about", None),
                members_count=getattr(entity, "participants_count", None) or getattr(entity, "broadcast", None) and 0,
                is_private=getattr(entity, "username", None) is None,
                is_verified=getattr(entity, "verified", False),
                is_scam=getattr(entity, "scam", False),
                is_fake=getattr(entity, "fake", False),
            )
        else:
            result.user = TelegramUserInfo(
                id=entity.id,
                username=entity.username,
                first_name=getattr(entity, "first_name", None),
                last_name=getattr(entity, "last_name", None),
                phone=getattr(entity, "phone", None),
                is_bot=getattr(entity, "bot", False),
                is_verified=getattr(entity, "verified", False),
                is_scam=getattr(entity, "scam", False),
                is_fake=getattr(entity, "fake", False),
                last_online=str(getattr(entity, "last_online_date", "")) if hasattr(entity, "last_online_date") else None,
            )

        await client.disconnect()
        return result

    except asyncio.TimeoutError:
        return TelegramResult(
            error=f"Telegram request timed out after {timeout}s",
            scan_time_s=round(time.time() - t0, 2),
        )
    except Exception as exc:
        logger.exception("Telegram user resolve failed: %s", exc)
        return TelegramResult(
            error=str(exc),
            scan_time_s=round(time.time() - t0, 2),
        )


async def scrape_telegram_channel(
    channel_identifier: str,
    limit: int = 50,
    timeout: int = 60,
) -> TelegramResult:
    """
    Scrape recent messages from a public Telegram channel.

    Args:
        channel_identifier: Channel username or invite link
        limit: Maximum messages to retrieve (default 50, max 1000)
        timeout: Timeout in seconds

    Returns:
        TelegramResult with channel info and messages
    """
    available = await _ensure_telethon_installed()
    if not available:
        return TelegramResult(error="telethon not installed")

    api_id, api_hash = _get_credentials()
    if not api_id or not api_hash:
        return TelegramResult(error="TELEGRAM_API_ID and TELEGRAM_API_HASH must be set")

    t0 = time.time()
    try:
        from telethon import TelegramClient
        from telethon.errors import FloodWaitError

        session_name = f"friday_telegram_chan_{abs(hash(channel_identifier))}"
        client = TelegramClient(session_name, int(api_id), api_hash)

        try:
            await asyncio.wait_for(client.start(), timeout=timeout)
        except Exception:
            return TelegramResult(
                error="Telegram login failed",
                scan_time_s=round(time.time() - t0, 2),
            )

        try:
            entity = await asyncio.wait_for(
                client.get_entity(channel_identifier), timeout=timeout
            )
        except Exception as e:
            await client.disconnect()
            return TelegramResult(
                error=f"Cannot access channel: {e}",
                scan_time_s=round(time.time() - t0, 2),
            )

        result = TelegramResult(success=True, scan_time_s=round(time.time() - t0, 2))
        result.channel = TelegramChannelInfo(
            id=entity.id,
            title=entity.title,
            username=entity.username,
            about=getattr(entity, "about", None),
            members_count=getattr(entity, "participants_count", None),
            is_private=getattr(entity, "username", None) is None,
            is_verified=getattr(entity, "verified", False),
            is_scam=getattr(entity, "scam", False),
            is_fake=getattr(entity, "fake", False),
        )

        try:
            messages = []
            async for msg in client.iter_messages(entity, limit=min(limit, 1000)):
                m = TelegramMessage(
                    id=msg.id,
                    date=msg.date.isoformat() if msg.date else "",
                    text=(msg.text or "")[:1000],
                    sender_id=msg.sender_id,
                    views=getattr(msg, "views", None),
                    forwards=getattr(msg, "forwards", None),
                )
                if msg.sender:
                    m.sender_username = msg.sender.username
                    m.sender_name = getattr(msg.sender, "first_name", None)
                messages.append(m)
            result.messages = messages
        except FloodWaitError as e:
            result.error = f"Rate limited: wait {e.seconds}s"

        await client.disconnect()
        return result

    except asyncio.TimeoutError:
        return TelegramResult(
            error=f"Telegram scrape timed out after {timeout}s",
            scan_time_s=round(time.time() - t0, 2),
        )
    except Exception as exc:
        logger.exception("Telegram channel scrape failed: %s", exc)
        return TelegramResult(
            error=str(exc),
            scan_time_s=round(time.time() - t0, 2),
        )
