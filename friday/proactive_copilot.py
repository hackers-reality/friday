"""
FRIDAY Proactive Copilot — Desktop-aware proactive assistant.
Inspired by Logical (YC F25) and Microsoft Copilot.
Monitors active window, clipboard, files, and generates context-aware suggestions.
"""
from __future__ import annotations

import json
import os
import platform
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Callable

from friday._paths import FRIDAY_MEMORY
from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

_STATE_PATH = os.path.join(FRIDAY_MEMORY, "proactive_copilot.json")
_HISTORY_PATH = os.path.join(FRIDAY_MEMORY, "proactive_copilot_history.jsonl")

# How often to re-evaluate context (seconds)
_SCAN_INTERVAL = 30
# Cooldown between proactive suggestions
_SUGGESTION_COOLDOWN = 120


def _load_state() -> dict:
    if os.path.exists(_STATE_PATH):
        try:
            with open(_STATE_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"enabled": True, "last_suggestion_time": 0, "suggestions_given": 0, "context_window": {}}


def _save_state(state: dict):
    os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
    try:
        with open(_STATE_PATH, "w") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


def _log_history(entry: dict):
    os.makedirs(os.path.dirname(_HISTORY_PATH), exist_ok=True)
    try:
        with open(_HISTORY_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def _get_active_window_info() -> dict:
    """Get info about the currently active window."""
    result = {"title": "", "process": "", "app": ""}
    try:
        import pygetwindow as gw
        active = gw.getActiveWindow()
        if active:
            result["title"] = active.title or ""
            result["app"] = "Unknown"
    except Exception:
        pass

    try:
        if platform.system() == "Windows":
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            hwnd = user32.GetForegroundWindow()
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value:
                try:
                    handle = kernel32.OpenProcess(0x0400 | 0x0010, False, pid.value)
                    if handle:
                        exe_name = ctypes.create_string_buffer(260)
                        kernel32.GetModuleBaseNameA(handle, None, exe_name, 260)
                        kernel32.CloseHandle(handle)
                        result["process"] = exe_name.value.decode() if exe_name.value else ""
                except Exception:
                    pass
    except Exception:
        pass

    return result


def _get_clipboard_text() -> str:
    """Get current clipboard text content."""
    try:
        import pyperclip
        text = pyperclip.paste()
        if text and isinstance(text, str):
            return text[:500]
    except Exception:
        pass
    return ""


def _get_recent_files(count: int = 5) -> list[str]:
    """Get recently modified files from common directories."""
    recent = []
    try:
        home = Path.home()
        search_dirs = [
            home / "Desktop",
            home / "Downloads",
            home / "Documents",
        ]
        for d in search_dirs:
            if d.exists():
                files = sorted(d.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:count]
                for f in files:
                    if f.is_file() and not f.name.startswith("."):
                        recent.append(str(f))
        return recent[:count]
    except Exception:
        return []


def _detect_context() -> dict:
    """Detect current user context — what they're working on."""
    window = _get_active_window_info()
    clipboard = _get_clipboard_text()
    recent_files = _get_recent_files()

    context = {
        "timestamp": datetime.now().isoformat(),
        "window_title": window.get("title", ""),
        "window_process": window.get("process", ""),
        "clipboard_preview": clipboard[:200] if clipboard else "",
        "has_clipboard": bool(clipboard),
        "recent_files": recent_files,
        "domain_hint": _guess_domain(window.get("title", ""), clipboard),
    }
    return context


def _guess_domain(window_title: str, clipboard: str) -> str:
    """Guess what domain the user is working in."""
    title_lower = window_title.lower()
    text_lower = clipboard.lower()

    if any(w in title_lower for w in ["code", "vscode", "vs code", "visual studio", "pycharm", "intellij", "sublime", "cursor"]):
        return "coding"
    if any(w in title_lower for w in ["chrome", "edge", "firefox", "browser", "opera", "brave"]):
        return "browsing"
    if any(w in title_lower for w in ["outlook", "gmail", "mail", "thunderbird"]):
        return "email"
    if any(w in title_lower for w in ["word", "document", "doc", "write", "libreoffice"]):
        return "writing"
    if any(w in title_lower for w in ["excel", "sheets", "spreadsheet", "numbers", "calc", "csv"]):
        return "spreadsheet"
    if any(w in title_lower for w in ["terminal", "cmd", "powershell", "bash", "wsl", "console"]):
        return "terminal"
    if any(w in title_lower for w in ["slack", "discord", "teams", "telegram", "whatsapp"]):
        return "communication"
    if "pdf" in title_lower or any(f.endswith(".pdf") for f in text_lower.split()):
        return "reading"
    return "general"


def _generate_suggestion(context: dict) -> str:
    """Generate a proactive suggestion based on detected context."""
    domain = context.get("domain_hint", "general")
    suggestions = {
        "coding": [
            "I see you're coding. Want me to review your recent changes or help debug something?",
            "You're in your editor. Need a code review, refactor, or documentation?",
            "Looks like you're deep in code. I can lint, format, or search for you.",
        ],
        "browsing": [
            "I can research what you're looking at and summarize it. Just ask.",
            "Need me to grab info from that page? I can extract and organize it.",
            "While you browse, I can search for related info or check facts.",
        ],
        "email": [
            "I can draft replies, organize your inbox, or remind you about important emails.",
            "Want me to check for urgent messages or draft a response?",
        ],
        "writing": [
            "Need a hand with that document? I can write, edit, or format it.",
            "I can help polish that text or suggest improvements.",
        ],
        "spreadsheet": [
            "Working with data? I can analyze, chart, or clean up that spreadsheet.",
            "Need formulas, pivot tables, or data analysis? I've got you.",
        ],
        "terminal": [
            "I see you in the terminal. Need help with a command or script?",
            "Running something complex? I can help build that pipeline.",
        ],
        "communication": [
            "If you need to send a message or schedule something, just say the word.",
            "Need me to draft a message or summarize a conversation?",
        ],
        "reading": [
            "That document looks interesting. Want me to summarize it or extract key points?",
            "I can read through that and give you the highlights.",
        ],
        "general": [
            "Everything running smoothly. Let me know if you need anything.",
            "I'm here if you need research, automation, or just a second opinion.",
        ],
    }

    domain_suggestions = suggestions.get(domain, suggestions["general"])
    idx = int(time.time()) % len(domain_suggestions)
    return domain_suggestions[idx]


def proactive_suggest(force: bool = False) -> str:
    """
    Get a proactive suggestion based on current desktop context.
    FRIDAY calls this periodically to offer timely help.
    Use force=True to bypass cooldown.
    """
    state = _load_state()
    now = time.time()

    if not force and not state.get("enabled", True):
        return "[OK] Proactive copilot is disabled. Enable with `proactive_copilot_enable`."

    last = state.get("last_suggestion_time", 0)
    since_last = now - last
    if not force:
        if since_last < _SUGGESTION_COOLDOWN:
            remaining = int(_SUGGESTION_COOLDOWN - since_last)
            return f"[OK] Suggestion cooldown active ({remaining}s remaining)."
    elif since_last < 30:
        # Even force=True has a 30s minimum cooldown to prevent loops
        return f"[OK] Too soon since last suggestion ({int(since_last)}s). Wait a moment."

    context = _detect_context()
    suggestion = _generate_suggestion(context)

    state["last_suggestion_time"] = now
    state["suggestions_given"] = state.get("suggestions_given", 0) + 1
    state["context_window"] = context
    _save_state(state)

    _log_history({
        "timestamp": datetime.now().isoformat(),
        "suggestion": suggestion,
        "context": context,
    })

    lines = ["### PROACTIVE SUGGESTION", "", suggestion, ""]
    lines.append(f"*Context: {context.get('domain_hint', 'general')} | "
                 f"Window: {context.get('window_title', 'unknown')[:60]}*")
    return "\n".join(lines)


def proactive_status() -> str:
    """Show proactive copilot status — enabled/disabled, recent context, suggestion count."""
    state = _load_state()
    context = state.get("context_window", {})

    lines = ["### PROACTIVE COPILOT STATUS", ""]
    lines.append(f"**Enabled**: {'Yes' if state.get('enabled', True) else 'No'}")
    lines.append(f"**Suggestions given**: {state.get('suggestions_given', 0)}")
    lines.append(f"**Cooldown**: {_SUGGESTION_COOLDOWN}s")
    lines.append("")
    lines.append("**Current context:**")
    lines.append(f"  Window: {context.get('window_title', 'N/A')}")
    lines.append(f"  Process: {context.get('window_process', 'N/A')}")
    lines.append(f"  Domain: {context.get('domain_hint', 'N/A')}")
    lines.append(f"  Clipboard: {'Yes' if context.get('has_clipboard') else 'No'}")

    if os.path.exists(_HISTORY_PATH):
        try:
            with open(_HISTORY_PATH) as f:
                count = sum(1 for _ in f)
            lines.append(f"  History entries: {count}")
        except Exception:
            pass

    return "\n".join(lines)


def proactive_copilot_enable(enabled: bool = True) -> str:
    """Enable or disable the proactive copilot."""
    state = _load_state()
    state["enabled"] = enabled
    _save_state(state)
    return f"[OK] Proactive copilot {'enabled' if enabled else 'disabled'}."


def proactive_context() -> str:
    """Get the current desktop context without generating a suggestion."""
    context = _detect_context()
    lines = ["### CURRENT CONTEXT", ""]
    lines.append(f"**Active Window**: {context.get('window_title', 'N/A')}")
    lines.append(f"**Process**: {context.get('window_process', 'N/A')}")
    lines.append(f"**Domain**: {context.get('domain_hint', 'general')}")
    lines.append(f"**Clipboard**: {'Content detected' if context.get('has_clipboard') else 'Empty'}")
    if context.get("recent_files"):
        lines.append("**Recent files**:")
        for f in context["recent_files"][:3]:
            lines.append(f"  - {Path(f).name}")
    return "\n".join(lines)
