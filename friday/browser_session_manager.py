"""
FRIDAY Browser Session Manager — manages named browser sessions (contexts).
Each session has its own Chrome profile, cookies, and settings.

Default sessions:
  - personal: main Chrome profile (auto-detected)
  - incognito: fresh context with no cookies

User can say "use my work browser" → switch to work session.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from friday.logging_utils import configure_logging
from friday.orchestration_config import ensure_config

logger = configure_logging(__name__)


@dataclass
class SessionConfig:
    name: str
    profile_dir: str = ""
    headless: bool = True
    description: str = ""


class BrowserSessionManager:
    """
    Manages session configs and switching between named browser profiles.
    Works with browser_manager.py to switch the active context.

    Sessions defined in config.yaml browser.sessions section.
    """

    def __init__(self):
        self._sessions: dict[str, SessionConfig] = {}
        self._active: str = "personal"
        self._load_config()

    def _load_config(self):
        """Load session configs from config.yaml."""
        cfg = ensure_config().get("browser", {}).get("sessions", {})

        # Personal session: auto-detect or configured
        personal_profile = cfg.get("personal", {}).get("profile_dir", "")
        if not personal_profile:
            personal_profile = self._auto_detect_profile()

        self._sessions["personal"] = SessionConfig(
            name="personal",
            profile_dir=personal_profile or "",
            headless=cfg.get("personal", {}).get("headless", True),
            description="Your main Chrome profile with all cookies and sessions",
        )

        # Incognito: always fresh (no profile)
        self._sessions["incognito"] = SessionConfig(
            name="incognito",
            profile_dir="",
            headless=True,
            description="Fresh browser with no cookies or saved data",
        )

        # Additional sessions from config
        for sname, sdata in cfg.items():
            if sname in ("personal",):
                continue
            profile_dir = sdata.get("profile_dir", "")
            if profile_dir and os.path.isdir(profile_dir):
                self._sessions[sname] = SessionConfig(
                    name=sname,
                    profile_dir=profile_dir,
                    headless=sdata.get("headless", True),
                    description=sdata.get("description", f"Chrome profile: {profile_dir}"),
                )

        logger.info("Loaded %d browser sessions: %s", len(self._sessions), list(self._sessions.keys()))

    @staticmethod
    def _auto_detect_profile() -> str:
        """Auto-detect Chrome profile."""
        if os.name == "nt":
            base = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
            if os.path.isdir(base):
                return base
        elif os.uname().sysname == "Darwin":
            base = os.path.expanduser("~/Library/Application Support/Google/Chrome")
            if os.path.isdir(base):
                return base
        else:
            for p in ("~/.config/google-chrome", "~/.config/chromium"):
                expanded = os.path.expanduser(p)
                if os.path.isdir(expanded):
                    return expanded
        return ""

    def get_session(self, name: str) -> Optional[SessionConfig]:
        return self._sessions.get(name)

    def list_sessions(self) -> list[dict]:
        return [
            {"name": s.name, "profile_dir": s.profile_dir, "headless": s.headless,
             "description": s.description, "active": s.name == self._active}
            for s in self._sessions.values()
        ]

    def switch_to(self, name: str) -> bool:
        """Switch active session. Returns False if session not found."""
        if name not in self._sessions:
            logger.warning("Session not found: %s. Available: %s", name, list(self._sessions.keys()))
            return False
        self._active = name
        return True

    def active_session(self) -> str:
        return self._active

    def active_config(self) -> Optional[SessionConfig]:
        return self._sessions.get(self._active)
