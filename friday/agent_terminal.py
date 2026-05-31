"""
Per-agent terminal window spawning, key verification, and the enhanced agent spawning
system for FRIDAY AI.

Provides:
  - KeyManager        — NVIDIA NIM & OpenCode Zen API key management with verification
  - AgentTerminalManager — per-agent CMD/PowerShell terminal windows with live status
  - AgentDelegator    — task complexity analysis, delegation decisions, workflow orchestration
  - AgentBusEnhanced  — real-time status publishing & agent-to-agent data passing
  - High-level tool functions that FRIDAY calls directly
"""

from __future__ import annotations

import asyncio
import datetime
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import uuid
from pathlib import Path
from threading import Lock
from typing import Any, Optional

import httpx

from friday._paths import FRIDAY_MEMORY, PROJECT_ROOT
from friday.agent_profiles import get_agent_tools
from friday.agent_bus import (
    _agent_results,
    _agent_errors,
    _agent_events,
    get_all_messages,
    get_task_status,
    publish as bus_publish,
    wait_for_result as bus_wait_for_result,
)

# ── ANSI Colour Constants ──────────────────────────────────────────

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[2m"
ANSI_RED = "\033[91m"
ANSI_GREEN = "\033[92m"
ANSI_YELLOW = "\033[93m"
ANSI_BLUE = "\033[94m"
ANSI_MAGENTA = "\033[95m"
ANSI_CYAN = "\033[96m"
ANSI_WHITE = "\033[97m"
ANSI_BG_RED = "\033[101m"
ANSI_BG_GREEN = "\033[102m"
ANSI_BG_YELLOW = "\033[103m"
ANSI_BG_BLUE = "\033[104m"
ANSI_BG_MAGENTA = "\033[105m"
ANSI_BG_CYAN = "\033[106m"

AGENT_COLORS: dict[str, str] = {
    "veronica": ANSI_YELLOW,
    "forge": ANSI_BLUE,
    "ghost": ANSI_RED,
    "atlas": ANSI_CYAN,
    "orchestrator": ANSI_MAGENTA,
    "friday": ANSI_GREEN,
    "default": ANSI_WHITE,
}

AGENT_ICONS: dict[str, str] = {
    "veronica": "[V]",
    "forge": "[F]",
    "ghost": "[G]",
    "atlas": "[A]",
    "orchestrator": "[O]",
    "friday": "[FRI]",
    "default": "[*]",
}

ENV_PATH = os.path.join(PROJECT_ROOT, ".env")

NVIDIA_API_BASE = os.getenv("NIM_API_BASE", "https://integrate.api.nvidia.com/v1")
ZEN_API_BASE = os.getenv("ZEN_API_BASE", "https://api.opencode.ai/v1")
NVIDIA_MODEL_CHECK = os.getenv("NVIDIA_MODEL_CHECK", "meta/llama-3.3-70b-instruct")

_TERMINAL_WATCHDOG_SCRIPT: Optional[str] = None
_TERMINAL_TEMP_DIR: Optional[str] = None

import logging as _logging
_LOG = _logging.getLogger(__name__)


# ── Helpers ─────────────────────────────────────────────────────────

def _color(text: str, color: str) -> str:
    return f"{color}{text}{ANSI_RESET}"


def _agent_color(agent_id: str) -> str:
    return AGENT_COLORS.get(agent_id.lower(), AGENT_COLORS["default"])


def _agent_icon(agent_id: str) -> str:
    return AGENT_ICONS.get(agent_id.lower(), AGENT_ICONS["default"])


def _format_agent_label(agent_id: str) -> str:
    c = _agent_color(agent_id)
    icon = _agent_icon(agent_id)
    return f"{c}{icon} {agent_id}{ANSI_RESET}"


def _timestamp() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")


def _iso_now() -> str:
    return datetime.datetime.now().isoformat()


def _short_id() -> str:
    return uuid.uuid4().hex[:10]


def _ensure_agent_log_dir() -> str:
    path = os.path.join(FRIDAY_MEMORY, "agent_logs")
    os.makedirs(path, exist_ok=True)
    return path


def _ensure_terminal_temp_dir() -> str:
    global _TERMINAL_TEMP_DIR
    if _TERMINAL_TEMP_DIR is None:
        _TERMINAL_TEMP_DIR = tempfile.mkdtemp(prefix="friday_agent_term_")
    return _TERMINAL_TEMP_DIR


def _write_env_file(updates: dict[str, str]) -> bool:
    """Update or append key=value pairs in .env file."""
    try:
        if os.path.exists(ENV_PATH):
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
        else:
            lines = []
        new_lines: list[str] = []
        updated_keys = set()
        for line in lines:
            stripped = line.strip()
            matched = False
            for key in updates:
                if stripped.startswith(f"{key}=") or stripped.startswith(f"#{key}="):
                    new_lines.append(f"{key}={updates[key]}\n")
                    updated_keys.add(key)
                    matched = True
                    break
            if not matched:
                new_lines.append(line)
        for key, value in updates.items():
            if key not in updated_keys:
                new_lines.append(f"{key}={value}\n")
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        for key, value in updates.items():
            os.environ[key] = value
        return True
    except Exception:
        return False


def _build_agent_terminal_display(data: dict[str, Any]) -> str:
    """Build the themed ANSI display string for an agent terminal window."""
    agent_id = data.get("agent_id", "unknown")
    name = data.get("name", agent_id)
    role = data.get("role", "general")
    status = data.get("status", "starting")
    action = data.get("action", "")
    progress = data.get("progress", 0)
    task = data.get("task", "")
    result_summary = data.get("result_summary", "")
    steps_completed = data.get("steps_completed", 0)
    total_steps = data.get("total_steps", 0)

    ac = _agent_color(agent_id)
    status_colors = {
        "starting": ANSI_YELLOW, "running": ANSI_GREEN,
        "completed": ANSI_CYAN, "failed": ANSI_RED, "idle": ANSI_DIM,
    }
    sc = status_colors.get(status, ANSI_WHITE)

    bar_len = 30
    filled = int(bar_len * progress / 100) if progress else 0
    bar_fill = f"{ANSI_GREEN}{'█' * filled}{ANSI_RESET}" if filled else ""
    bar_empty = f"{ANSI_DIM}{'░' * (bar_len - filled)}{ANSI_RESET}"

    lines: list[str] = []
    lines.append("")
    lines.append(f"{ANSI_CYAN}{ANSI_BOLD}╔{'═' * 58}╗{ANSI_RESET}")
    lines.append(f"{ANSI_CYAN}║{ANSI_RESET}  {ac}{ANSI_BOLD}{name}{ANSI_RESET}  {ANSI_DIM}({role}){ANSI_RESET}{' ' * max(0, 49 - len(name) - len(role))}{ANSI_CYAN}║{ANSI_RESET}")
    lines.append(f"{ANSI_CYAN}║{ANSI_RESET}  {ANSI_DIM}Agent ID:{ANSI_RESET} {agent_id}{' ' * max(0, 47 - len(agent_id))}{ANSI_CYAN}║{ANSI_RESET}")
    lines.append(f"{ANSI_CYAN}╠{'═' * 58}╣{ANSI_RESET}")
    # Status
    status_icons = {"starting": "◉", "running": "▶", "completed": "✔", "failed": "✘", "idle": "○"}
    si = status_icons.get(status, "●")
    lines.append(f"{ANSI_CYAN}║{ANSI_RESET}  {sc}{ANSI_BOLD}{si}{ANSI_RESET} {sc}{ANSI_BOLD}{status.upper()}{ANSI_RESET}{' ' * (50 - len(status))}{ANSI_CYAN}║{ANSI_RESET}")
    if task:
        t = task[:56]
        lines.append(f"{ANSI_CYAN}║{ANSI_RESET}  {ANSI_BOLD}Task:{ANSI_RESET} {t}{' ' * (56 - len(t))}{ANSI_CYAN}║{ANSI_RESET}")
    if action:
        a = action[:56]
        lines.append(f"{ANSI_CYAN}║{ANSI_RESET}  {ANSI_BOLD}Action:{ANSI_RESET} {a}{' ' * (54 - len(a))}{ANSI_CYAN}║{ANSI_RESET}")
    # Progress
    lines.append(f"{ANSI_CYAN}║{ANSI_RESET}  {ANSI_BOLD}Progress:{ANSI_RESET}  {bar_fill}{bar_empty}  {ANSI_BOLD}{progress:.0f}%{ANSI_RESET}{' ' * max(0, 43 - len(str(int(progress))))}{ANSI_CYAN}║{ANSI_RESET}")
    if total_steps > 0:
        lines.append(f"{ANSI_CYAN}║{ANSI_RESET}  {ANSI_BOLD}Steps:{ANSI_RESET} {steps_completed}/{total_steps}{' ' * (51 - len(f'{steps_completed}/{total_steps}'))}{ANSI_CYAN}║{ANSI_RESET}")
    if result_summary:
        r = result_summary[:56]
        lines.append(f"{ANSI_CYAN}║{ANSI_RESET}  {ANSI_BOLD}Result:{ANSI_RESET} {r}{' ' * (54 - len(r))}{ANSI_CYAN}║{ANSI_RESET}")
    # Bottom
    lines.append(f"{ANSI_CYAN}║{ANSI_RESET}  {ANSI_DIM}Last: {_timestamp()}{ANSI_RESET}{' ' * max(0, 50 - len(_timestamp()))}{ANSI_CYAN}║{ANSI_RESET}")
    lines.append(f"{ANSI_CYAN}╚{'═' * 58}╝{ANSI_RESET}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# KeyManager
# ═══════════════════════════════════════════════════════════════════

class KeyManager:
    """Manages NVIDIA NIM and OpenCode Zen API keys with verification.

    Stores keys in config/.env with secure file permissions.
    Follows singleton pattern — use get_key_manager() to access.
    """

    def __init__(self):
        self._nvidia_key: Optional[str] = None
        self._opencode_key: Optional[str] = None
        self._nvidia_verified: bool = False
        self._opencode_verified: bool = False
        self._lock = asyncio.Lock()
        self._http = httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0))
        self._load_from_env()

    def _load_from_env(self):
        self._nvidia_key = os.getenv("NVIDIA_NIM_API_KEY", "") or os.getenv("NVIDIA_API_KEY", "") or os.getenv("NIM_API_KEY", "") or None
        self._opencode_key = os.getenv("OPENCODE_ZEN_API_KEY", "") or os.getenv("ZEN_API_KEY", "") or os.getenv("OPENCODE_API_KEY", "") or None
        if self._nvidia_key:
            self._nvidia_verified = False
        if self._opencode_key:
            self._opencode_verified = False

    async def verify_nvidia_key(self, key: Optional[str] = None) -> dict[str, Any]:
        """Test a key (or the stored key) against the NVIDIA NIM API.

        Returns dict with verified (bool), latency_ms, model_available, error.
        """
        test_key = key or self._nvidia_key
        if not test_key:
            return {"verified": False, "latency_ms": 0, "model_available": False, "error": "No key provided"}
        t0 = time.monotonic()
        try:
            resp = await self._http.get(
                f"{NVIDIA_API_BASE}/models",
                headers={"Authorization": f"Bearer {test_key}"},
            )
            latency = int((time.monotonic() - t0) * 1000)
            if resp.status_code == 200:
                models = resp.json().get("data", [])
                model_available = any(
                    isinstance(m, dict) and NVIDIA_MODEL_CHECK in m.get("id", "")
                    for m in models
                )
                if key is None:
                    self._nvidia_verified = True
                return {"verified": True, "latency_ms": latency, "model_available": model_available, "error": None}
            elif resp.status_code == 401:
                return {"verified": False, "latency_ms": latency, "model_available": False, "error": "Invalid API key (401)"}
            else:
                return {"verified": False, "latency_ms": latency, "model_available": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except httpx.TimeoutException:
            latency = int((time.monotonic() - t0) * 1000)
            return {"verified": False, "latency_ms": latency, "model_available": False, "error": "Connection timeout"}
        except Exception as e:
            latency = int((time.monotonic() - t0) * 1000)
            return {"verified": False, "latency_ms": latency, "model_available": False, "error": str(e)}

    async def verify_opencode_key(self, key: Optional[str] = None) -> dict[str, Any]:
        """Test a key (or the stored key) against the OpenCode Zen API.

        Returns dict with verified (bool), latency_ms, error.
        """
        test_key = key or self._opencode_key
        if not test_key:
            return {"verified": False, "latency_ms": 0, "error": "No key provided"}
        t0 = time.monotonic()
        try:
            resp = await self._http.get(
                f"{ZEN_API_BASE}/models",
                headers={"Authorization": f"Bearer {test_key}"},
            )
            latency = int((time.monotonic() - t0) * 1000)
            if resp.status_code == 200:
                if key is None:
                    self._opencode_verified = True
                return {"verified": True, "latency_ms": latency, "error": None}
            elif resp.status_code == 401:
                return {"verified": False, "latency_ms": latency, "error": "Invalid API key (401)"}
            else:
                return {"verified": False, "latency_ms": latency, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except httpx.TimeoutException:
            latency = int((time.monotonic() - t0) * 1000)
            return {"verified": False, "latency_ms": latency, "error": "Connection timeout"}
        except Exception as e:
            latency = int((time.monotonic() - t0) * 1000)
            return {"verified": False, "latency_ms": latency, "error": str(e)}

    def get_nvidia_key(self) -> Optional[str]:
        return self._nvidia_key

    def get_opencode_key(self) -> Optional[str]:
        return self._opencode_key

    async def set_nvidia_key(self, key: str) -> dict[str, Any]:
        """Set a new NVIDIA NIM key, verify it, and persist to .env.

        Returns verification result dict.
        """
        async with self._lock:
            result = await self.verify_nvidia_key(key)
            if result["verified"]:
                self._nvidia_key = key
                self._nvidia_verified = True
                _write_env_file({"NVIDIA_NIM_API_KEY": key})
            return result

    async def set_opencode_key(self, key: str) -> dict[str, Any]:
        """Set a new OpenCode Zen key, verify it, and persist to .env.

        Returns verification result dict.
        """
        async with self._lock:
            result = await self.verify_opencode_key(key)
            if result["verified"]:
                self._opencode_key = key
                self._opencode_verified = True
                _write_env_file({"OPENCODE_ZEN_API_KEY": key})
            return result

    def have_valid_keys(self) -> bool:
        """Return True if both keys are present and verified."""
        return bool(self._nvidia_key and self._nvidia_verified and self._opencode_key and self._opencode_verified)

    def have_keys_present(self) -> bool:
        """Return True if both keys are present (whether verified or not)."""
        return bool(self._nvidia_key and self._opencode_key)

    async def prompt_for_missing_keys(self) -> dict[str, Any]:
        """Interactive CLI prompt asking user to paste missing keys.

        Returns dict with keys_updated (bool), nvidia_result, opencode_result.
        """
        result: dict[str, Any] = {"keys_updated": False, "nvidia_result": None, "opencode_result": None}
        print(f"\n{ANSI_BOLD}{ANSI_CYAN}╔══════════════════════════════════════════════╗{ANSI_RESET}")
        print(f"{ANSI_BOLD}{ANSI_CYAN}║     FRIDAY API KEY VERIFICATION              ║{ANSI_RESET}")
        print(f"{ANSI_BOLD}{ANSI_CYAN}╚══════════════════════════════════════════════╝{ANSI_RESET}{ANSI_RESET}")

        nvidia_key = self._nvidia_key
        if not nvidia_key or not self._nvidia_verified:
            if nvidia_key and not self._nvidia_verified:
                print(f"\n{ANSI_YELLOW}⚠ Stored NVIDIA NIM key is present but NOT verified.{ANSI_RESET}")
                verify_now = input(f"  Verify it now? (Y/n): ").strip().lower()
                if verify_now in ("", "y", "yes"):
                    v = await self.verify_nvidia_key(nvidia_key)
                    if v["verified"]:
                        self._nvidia_verified = True
                        result["nvidia_result"] = v
                        print(f"  {ANSI_GREEN}✔ NVIDIA NIM key verified!{ANSI_RESET}")
                    else:
                        print(f"  {ANSI_RED}✘ Verification failed: {v['error']}{ANSI_RESET}")
                        nvidia_key = None
                else:
                    nvidia_key = None
            if not nvidia_key or not self._nvidia_verified:
                print(f"\n{ANSI_BOLD}NVIDIA NIM API Key{ANSI_RESET}")
                print(f"  Get one at: https://build.nvidia.com/")
                new_key = input(f"  Paste key (or press Enter to skip): ").strip()
                if new_key:
                    v = await self.set_nvidia_key(new_key)
                    result["nvidia_result"] = v
                    if v["verified"]:
                        self._nvidia_verified = True
                        print(f"  {ANSI_GREEN}✔ Key verified and saved!{ANSI_RESET}")
                    else:
                        print(f"  {ANSI_RED}✘ Verification failed: {v['error']}{ANSI_RESET}")

        opencode_key = self._opencode_key
        if not opencode_key or not self._opencode_verified:
            if opencode_key and not self._opencode_verified:
                print(f"\n{ANSI_YELLOW}⚠ Stored OpenCode Zen key is present but NOT verified.{ANSI_RESET}")
                verify_now = input(f"  Verify it now? (Y/n): ").strip().lower()
                if verify_now in ("", "y", "yes"):
                    v = await self.verify_opencode_key(opencode_key)
                    if v["verified"]:
                        self._opencode_verified = True
                        result["opencode_result"] = v
                        print(f"  {ANSI_GREEN}✔ OpenCode Zen key verified!{ANSI_RESET}")
                    else:
                        print(f"  {ANSI_RED}✘ Verification failed: {v['error']}{ANSI_RESET}")
                        opencode_key = None
                else:
                    opencode_key = None
            if not opencode_key or not self._opencode_verified:
                print(f"\n{ANSI_BOLD}OpenCode Zen API Key{ANSI_RESET}")
                print(f"  Get one at: https://opencode.ai")
                new_key = input(f"  Paste key (or press Enter to skip): ").strip()
                if new_key:
                    v = await self.set_opencode_key(new_key)
                    result["opencode_result"] = v
                    if v["verified"]:
                        self._opencode_verified = True
                        print(f"  {ANSI_GREEN}✔ Key verified and saved!{ANSI_RESET}")
                    else:
                        print(f"  {ANSI_RED}✘ Verification failed: {v['error']}{ANSI_RESET}")

        result["keys_updated"] = self.have_valid_keys()
        if result["keys_updated"]:
            print(f"\n{ANSI_GREEN}✔ All required API keys are present and verified!{ANSI_RESET}")
        else:
            print(f"\n{ANSI_YELLOW}⚠ Some keys are missing or not verified.{ANSI_RESET}")
        return result

    def get_key_status(self) -> dict[str, Any]:
        """Dict with key presence and validity for all key types."""
        return {
            "nvidia": {
                "present": bool(self._nvidia_key),
                "verified": self._nvidia_verified,
                "key_preview": (self._nvidia_key[:8] + "..." + self._nvidia_key[-4:]) if self._nvidia_key and len(self._nvidia_key) > 16 else None,
            },
            "opencode": {
                "present": bool(self._opencode_key),
                "verified": self._opencode_verified,
                "key_preview": (self._opencode_key[:8] + "..." + self._opencode_key[-4:]) if self._opencode_key and len(self._opencode_key) > 16 else None,
            },
            "all_present": self.have_keys_present(),
            "all_verified": self.have_valid_keys(),
            "timestamp": _iso_now(),
        }

    async def close(self):
        await self._http.aclose()


_KEY_MANAGER: Optional[KeyManager] = None
_LOCK = Lock()


def get_key_manager() -> KeyManager:
    """Get or create the singleton KeyManager."""
    global _KEY_MANAGER
    if _KEY_MANAGER is None:
        with _LOCK:
            if _KEY_MANAGER is None:
                _KEY_MANAGER = KeyManager()
    return _KEY_MANAGER


# ═══════════════════════════════════════════════════════════════════
# AgentTerminalManager
# ═══════════════════════════════════════════════════════════════════

class AgentTerminalManager:
    """Manages per-agent terminal windows with real-time status display.

    Each agent gets its own CMD/PowerShell window showing:
      - Agent name, role, status
      - Task prompt FRIDAY gave
      - Current action being performed
      - Progress bar
      - Result summary when done

    Communication uses temp JSON files (status files) that the terminal
    watchdog script polls.
    """

    def __init__(self):
        self._terminals: dict[str, dict[str, Any]] = {}
        self._status_dir = _ensure_agent_log_dir()
        self._lock = Lock()

    def spawn_agent_terminal(
        self,
        agent_name: str,
        prompt: str,
        task_type: str = "general",
        role: str = "general",
    ) -> dict[str, Any]:
        """Open a new terminal window for an agent.

        Returns dict with agent_name, terminal_id, status_file, pid, success.
        """
        term_id = f"term_{agent_name}_{_short_id()}"
        status_file = os.path.join(self._status_dir, f"{term_id}.json")
        refresh_interval = 1.0

        initial_data = {
            "agent_id": agent_name,
            "name": agent_name,
            "role": role,
            "status": "starting",
            "action": "Initializing...",
            "progress": 0,
            "task": prompt,
            "task_type": task_type,
            "steps_completed": 0,
            "total_steps": 0,
            "result_summary": "",
            "timestamp": _iso_now(),
        }
        try:
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)
        except Exception as e:
            return {"success": False, "error": f"Failed to write status file: {e}"}

        watchdog_script = self._create_watchdog_script()
        if not watchdog_script:
            return {"success": False, "error": "Failed to create watchdog script"}

        title = f"FRIDAY Agent: {agent_name} [{role}]"
        powershell_cmd = (
            f'powershell.exe -NoExit -Command '
            f'& "{watchdog_script}" "{status_file}" "{refresh_interval}" "{title}"'
        )
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            proc = subprocess.Popen(
                ["cmd.exe", "/c", "start", title, "cmd.exe", "/k", powershell_cmd],
                shell=True,
                startupinfo=startupinfo,
            )
            pid = proc.pid
        except Exception as e1:
            try:
                proc = subprocess.Popen(
                    ["start", title, "cmd.exe", "/k", powershell_cmd],
                    shell=True,
                )
                pid = proc.pid
            except Exception as e2:
                return {"success": False, "error": f"Failed to spawn terminal: {e1}; {e2}"}

        term_info = {
            "agent_name": agent_name,
            "terminal_id": term_id,
            "status_file": status_file,
            "pid": pid,
            "spawned_at": _iso_now(),
            "title": title,
            "role": role,
            "task_type": task_type,
            "prompt": prompt,
            "current_status": "starting",
        }
        with self._lock:
            self._terminals[agent_name] = term_info

        return {
            "success": True,
            "agent_name": agent_name,
            "terminal_id": term_id,
            "status_file": status_file,
            "pid": pid,
        }

    def _create_watchdog_script(self) -> Optional[str]:
        """Create a self-contained Python watchdog script for terminal display.

        Returns path to the script file.
        """
        global _TERMINAL_WATCHDOG_SCRIPT
        if _TERMINAL_WATCHDOG_SCRIPT and os.path.exists(_TERMINAL_WATCHDOG_SCRIPT):
            return _TERMINAL_WATCHDOG_SCRIPT
        script_dir = _ensure_terminal_temp_dir()
        script_path = os.path.join(script_dir, "agent_terminal_watchdog.py")
        script_content = r'''"""
FRIDAY Agent Terminal Watchdog — themed live agent status in CMD window.
Usage: python agent_terminal_watchdog.py <status_file> <refresh_interval> <title>
"""
import json
import os
import sys
import time


# ANSI
R = "\033[0m"
B = "\033[1m"
D = "\033[2m"
I = "\033[3m"
K = "\033[90m"
Rc = "\033[91m"
G = "\033[92m"
Y = "\033[93m"
Bl = "\033[94m"
M = "\033[95m"
C = "\033[96m"
W = "\033[97m"


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def set_title(t: str):
    if os.name == "nt":
        os.system(f"title {t}")


def bar(filled: int, total: int = 30) -> str:
    f = min(filled, total)
    e = total - f
    return f"{G}{chr(9608) * f}{D}{chr(9617) * e}{R}"


def status_tag(s: str) -> str:
    tags = {
        "starting": f"{Y}{B}◉ STARTING{R}",
        "running":  f"{G}{B}▶ RUNNING{R}",
        "completed":f"{C}{B}✔ COMPLETED{R}",
        "failed":   f"{Rc}{B}✘ FAILED{R}",
        "idle":     f"{K}{B}○ IDLE{R}",
        "waiting":  f"{Bl}{B}◌ WAITING{R}",
    }
    return tags.get(s, f"{W}{s.upper()}{R}")


def agent_color(aid: str) -> str:
    colors = {
        "veronica": Y, "forge": Bl, "ghost": Rc,
        "atlas": C, "orchestrator": M, "friday": G,
    }
    return colors.get(aid.lower(), W)


def main():
    if len(sys.argv) < 3:
        input(f"{D}Usage: watchdog.py <status_file> <interval> [title]{R}\nPress Enter...")
        return
    status_file = sys.argv[1]
    interval = max(0.5, float(sys.argv[2])) if len(sys.argv) > 2 else 1.0
    title = sys.argv[3] if len(sys.argv) > 3 else "FRIDAY Agent"
    set_title(title)
    last = ""
    while True:
        try:
            if os.path.exists(status_file):
                with open(status_file, "r", encoding="utf-8") as f:
                    d = json.load(f)
            else:
                d = {"agent_id": "?", "name": "?", "status": "waiting", "action": "", "progress": 0}
            clear()
            aid = d.get("agent_id", "?")
            name = d.get("name", aid)
            role = d.get("role", "general")
            status = d.get("status", "?")
            action = d.get("action", "")
            prog = d.get("progress", 0)
            task = d.get("task", "")
            sc = d.get("steps_completed", 0)
            ts = d.get("total_steps", 0)
            res = d.get("result_summary", "")
            ac = agent_color(aid)

            lines = []
            # ── Top border ──
            lines.append(f"{C}{B}╔{'═' * 58}╗{R}")
            # ── Header ──
            lines.append(f"{C}║{R}  {ac}{B}{chr(9608)}{R}  {B}{name}{R}  {D}({role}){R}{' ' * max(0, 44 - len(name) - len(role))}{C}║{R}")
            lines.append(f"{C}║{R}  {D}Agent ID:{R} {aid}{' ' * max(0, 47 - len(aid))}{C}║{R}")
            lines.append(f"{C}╠{'═' * 58}╣{R}")
            # ── Status ──
            lines.append(f"{C}║{R}  {status_tag(status)}{' ' * max(0, 53 - len(status_tag(status)) + 10)}{C}║{R}")
            if task:
                t = task[:56]
                lines.append(f"{C}║{R}  {B}Task:{R} {t}{' ' * (56 - len(t))}{C}║{R}")
            if action:
                a = action[:56]
                lines.append(f"{C}║{R}  {B}Action:{R} {a}{' ' * (54 - len(a))}{C}║{R}")
            # ── Progress ──
            lines.append(f"{C}║{R}  {B}Progress:{R}  {bar(int(prog * 30 / 100))}  {B}{prog:.0f}%{R}{' ' * max(0, 43 - len(str(int(prog))))}{C}║{R}")
            if ts > 0:
                lines.append(f"{C}║{R}  {B}Steps:{R} {sc}/{ts}{' ' * (51 - len(f'{sc}/{ts}'))}{C}║{R}")
            if res:
                r = res[:56]
                lines.append(f"{C}║{R}  {B}Result:{R} {r}{' ' * (54 - len(r))}{C}║{R}")
            # ── Bottom ──
            lines.append(f"{C}║{R}  {D}Last: {d.get('timestamp', '?')}{R}{' ' * max(0, 50 - len(d.get('timestamp', '?')))}{C}║{R}")
            lines.append(f"{C}╚{'═' * 58}╝{R}")
            lines.append(f" {D}[This window auto-updates. Close to stop watching.]{R}")

            display = "\n".join(lines)
            if display != last:
                print(display)
                last = display
            if status in ("completed", "failed"):
                time.sleep(interval * 3)
            time.sleep(interval)
        except (KeyboardInterrupt, SystemExit):
            break
        except Exception:
            time.sleep(interval)


if __name__ == "__main__":
    main()
'''
        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)
            _TERMINAL_WATCHDOG_SCRIPT = script_path
            return script_path
        except Exception as e:
            return None

    def update_agent_terminal(
        self,
        agent_name: str,
        status: Optional[str] = None,
        action: Optional[str] = None,
        progress: Optional[float] = None,
        result_summary: Optional[str] = None,
        steps_completed: Optional[int] = None,
        total_steps: Optional[int] = None,
    ) -> bool:
        """Update the terminal display for an agent by writing to its status file."""
        with self._lock:
            term = self._terminals.get(agent_name)
            if not term:
                return False
            status_file = term.get("status_file")
            if not status_file or not os.path.exists(status_file):
                return False
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {"agent_id": agent_name, "name": agent_name, "role": term.get("role", "general"), "task": term.get("prompt", "")}
        if status is not None:
            data["status"] = status
            with self._lock:
                if agent_name in self._terminals:
                    self._terminals[agent_name]["current_status"] = status
        if action is not None:
            data["action"] = action
        if progress is not None:
            data["progress"] = progress
        if result_summary is not None:
            data["result_summary"] = result_summary
        if steps_completed is not None:
            data["steps_completed"] = steps_completed
        if total_steps is not None:
            data["total_steps"] = total_steps
        data["timestamp"] = _iso_now()
        try:
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False

    def close_agent_terminal(self, agent_name: str) -> dict[str, Any]:
        """Close the terminal window for a specific agent."""
        with self._lock:
            term = self._terminals.pop(agent_name, None)
        if not term:
            return {"success": False, "error": f"No terminal found for agent '{agent_name}'"}
        pid = term.get("pid")
        if pid:
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, timeout=3)
                else:
                    os.kill(pid, signal.SIGTERM)
            except Exception:
                pass
        status_file = term.get("status_file")
        if status_file and os.path.exists(status_file):
            try:
                os.remove(status_file)
            except Exception:
                pass
        return {"success": True, "agent_name": agent_name, "terminal_id": term.get("terminal_id")}

    def close_all_terminals(self) -> dict[str, Any]:
        """Close all agent terminal windows (cleanup on shutdown)."""
        closed: list[str] = []
        errors: list[str] = []
        with self._lock:
            agent_names = list(self._terminals.keys())
        for name in agent_names:
            result = self.close_agent_terminal(name)
            if result["success"]:
                closed.append(name)
            else:
                errors.append(f"{name}: {result.get('error', 'unknown')}")
        return {"success": len(errors) == 0, "closed": closed, "errors": errors, "count": len(closed)}

    def list_active_terminals(self) -> list[dict[str, Any]]:
        """Return list of dicts describing each active terminal."""
        results: list[dict[str, Any]] = []
        with self._lock:
            for name, info in self._terminals.items():
                status_file = info.get("status_file")
                current_data: dict[str, Any] = {}
                if status_file and os.path.exists(status_file):
                    try:
                        with open(status_file, "r", encoding="utf-8") as f:
                            current_data = json.load(f)
                    except Exception:
                        pass
                results.append({
                    "agent_name": name,
                    "terminal_id": info.get("terminal_id"),
                    "pid": info.get("pid"),
                    "status": info.get("current_status", current_data.get("status", "unknown")),
                    "role": info.get("role"),
                    "task_type": info.get("task_type"),
                    "prompt": info.get("prompt"),
                    "spawned_at": info.get("spawned_at"),
                    "current_action": current_data.get("action", ""),
                    "progress": current_data.get("progress", 0),
                    "result_summary": current_data.get("result_summary", ""),
                })
        return results

    def get_terminal_count(self) -> int:
        with self._lock:
            return len(self._terminals)

    def get_terminal(self, agent_name: str) -> Optional[dict[str, Any]]:
        with self._lock:
            return self._terminals.get(agent_name)

    def cleanup_temp_dir(self):
        global _TERMINAL_TEMP_DIR
        if _TERMINAL_TEMP_DIR and os.path.exists(_TERMINAL_TEMP_DIR):
            try:
                shutil.rmtree(_TERMINAL_TEMP_DIR)
            except Exception:
                pass
            _TERMINAL_TEMP_DIR = None
        global _TERMINAL_WATCHDOG_SCRIPT
        _TERMINAL_WATCHDOG_SCRIPT = None


_TERMINAL_MANAGER: Optional[AgentTerminalManager] = None
_TERMINAL_MANAGER_LOCK = Lock()


def get_terminal_manager() -> AgentTerminalManager:
    """Get or create the singleton AgentTerminalManager."""
    global _TERMINAL_MANAGER
    if _TERMINAL_MANAGER is None:
        with _TERMINAL_MANAGER_LOCK:
            if _TERMINAL_MANAGER is None:
                _TERMINAL_MANAGER = AgentTerminalManager()
    return _TERMINAL_MANAGER


# ═══════════════════════════════════════════════════════════════════
# AgentDelegator
# ═══════════════════════════════════════════════════════════════════

_COMPLEXITY_KEYWORDS: dict[str, int] = {
    "research": 15,
    "scan": 20,
    "vulnerability": 25,
    "exploit": 30,
    "osint": 20,
    "investigate": 15,
    "analyze": 10,
    "find": 5,
    "search": 5,
    "code": 20,
    "develop": 20,
    "build": 20,
    "implement": 20,
    "fix": 15,
    "debug": 15,
    "refactor": 15,
    "write": 10,
    "create": 15,
    "design": 20,
    "architecture": 25,
    "deploy": 25,
    "configure": 15,
    "optimize": 20,
    "document": 10,
    "test": 15,
    "review": 10,
    "monitor": 15,
    "automate": 20,
    "orchestrate": 30,
    "coordinate": 25,
    "multi": 25,
    "parallel": 25,
    "chain": 25,
    "workflow": 25,
    "pipeline": 25,
}

_TOOL_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "web_search": ["search", "find", "look up", "google", "research", "investigate", "information"],
    "osint": ["osint", "recon", "whois", "shodan", "dns", "footprint", "intelligence", "threat"],
    "vulnerability_scan": ["scan", "vulnerability", "nuclei", "nmap", "port", "cve", "exploit"],
    "code_development": ["code", "develop", "program", "write", "implement", "build", "create file"],
    "code_review": ["review", "audit", "inspect", "refactor", "quality"],
    "debugging": ["debug", "fix", "bug", "error", "issue", "crash", "broken"],
    "testing": ["test", "unit test", "integration", "coverage"],
    "documentation": ["document", "readme", "docs", "manual", "guide"],
    "deployment": ["deploy", "release", "ci/cd", "pipeline", "docker", "kubernetes"],
    "data_analysis": ["analyze", "data", "csv", "excel", "statistics", "chart", "report"],
    "memory": ["remember", "recall", "knowledge", "store", "retrieve", "memory"],
    "email": ["email", "mail", "gmail", "outlook", "send"],
    "social_media": ["twitter", "reddit", "instagram", "social", "post"],
    "browser": ["browse", "navigate", "click", "scrape", "extract", "automation"],
    "file_management": ["file", "folder", "organize", "copy", "move", "rename", "delete"],
    "system": ["system", "process", "service", "monitor", "health", "performance"],
    "git": ["git", "github", "commit", "push", "pull", "branch", "pr", "merge"],
    "security": ["security", "firewall", "encrypt", "auth", "permission", "access"],
}

_AGENT_TASK_MAP: dict[str, str] = {
    "veronica": "research",
    "ghost": "security",
    "forge": "code",
    "atlas": "memory",
}


class AgentDelegator:
    """Decides whether FRIDAY handles a task herself or delegates to sub-agents.

    Uses task complexity analysis, keyword matching, and available agent profiles
    to determine the optimal routing strategy.
    """

    def __init__(self):
        self._terminal_manager = get_terminal_manager()
        self._key_manager = get_key_manager()

    def analyze_task_complexity(self, task_description: str) -> dict[str, Any]:
        """Analyze a task and return complexity metrics and suggested agents.

        Returns dict with:
          - complexity_score (0-100)
          - requires_tools (list of tool categories)
          - subtasks (list of decomposed subtasks)
          - estimated_time (str)
          - suggested_agents (list of agent names)
        """
        desc_lower = task_description.lower()
        score = 0
        matched_categories: set[str] = set()
        seen_words = set()

        for keyword, weight in _COMPLEXITY_KEYWORDS.items():
            if keyword in desc_lower:
                occurrences = desc_lower.count(keyword)
                score += weight * min(occurrences, 3)
                seen_words.add(keyword)

        for category, keywords in _TOOL_CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in desc_lower:
                    matched_categories.add(category)
                    break

        len_bonus = min(len(task_description) / 10, 20)
        score += len_bonus
        has_bullets = task_description.count("\n") > 3
        if has_bullets:
            score += 10
        has_conditions = any(w in desc_lower for w in ["if", "when", "then", "otherwise", "but"])
        if has_conditions:
            score += 5
        has_multiple_steps = any(w in desc_lower for w in ["first", "then", "next", "finally", "step"])
        if has_multiple_steps:
            score += 10
        score = min(max(score, 0), 100)

        subtasks = self._decompose_task(desc_lower)
        suggested_agents = self._suggest_agents(desc_lower, list(matched_categories))

        estimated_time = self._estimate_time(score, len(subtasks))

        return {
            "complexity_score": round(score, 1),
            "requires_tools": sorted(matched_categories),
            "subtasks": subtasks,
            "estimated_time": estimated_time,
            "suggested_agents": suggested_agents,
            "has_subtasks": len(subtasks) > 1,
        }

    def _decompose_task(self, desc_lower: str) -> list[dict[str, Any]]:
        """Decompose a task description into structured subtasks."""
        subtasks: list[dict[str, Any]] = []
        lines = [l.strip() for l in desc_lower.split("\n") if l.strip()]
        explicit_steps = [l for l in lines if any(l.lower().startswith(p) for p in ["1.", "2.", "3.", "4.", "5.", "- ", "* ", "step", "first", "next", "then", "finally"])]
        if explicit_steps:
            for i, step in enumerate(explicit_steps):
                clean_step = step.lstrip("*-123456789. ").strip()
                if clean_step:
                    subtasks.append({
                        "id": f"sub_{_short_id()}",
                        "sequence": i + 1,
                        "description": clean_step,
                        "suggested_agent": self._suggest_single_agent(clean_step.lower()),
                    })
        else:
            seen_types: set[str] = set()
            if any(kw in desc_lower for kw in ["search", "research", "find", "investigate", "look up"]):
                subtasks.append({
                    "id": f"sub_{_short_id()}",
                    "sequence": 1,
                    "description": "Research and gather information",
                    "suggested_agent": "veronica",
                })
                seen_types.add("research")
            if any(kw in desc_lower for kw in ["scan", "vulnerability", "osint", "security", "recon", "threat"]):
                seq = len(subtasks) + 1
                subtasks.append({
                    "id": f"sub_{_short_id()}",
                    "sequence": seq,
                    "description": "Security analysis and vulnerability assessment",
                    "suggested_agent": "ghost",
                })
                seen_types.add("security")
            if any(kw in desc_lower for kw in ["code", "develop", "write", "program", "build", "implement", "create", "fix", "debug"]):
                seq = len(subtasks) + 1
                subtasks.append({
                    "id": f"sub_{_short_id()}",
                    "sequence": seq,
                    "description": "Code development and implementation",
                    "suggested_agent": "forge",
                })
                seen_types.add("code")
            if any(kw in desc_lower for kw in ["remember", "store", "memory", "knowledge", "graph"]):
                seq = len(subtasks) + 1
                subtasks.append({
                    "id": f"sub_{_short_id()}",
                    "sequence": seq,
                    "description": "Knowledge graph and memory operations",
                    "suggested_agent": "atlas",
                })
                seen_types.add("memory")
        return subtasks

    def _suggest_agents(self, desc_lower: str, categories: list[str]) -> list[dict[str, Any]]:
        """Suggest agents that can handle the task based on keywords."""
        suggestions: list[dict[str, Any]] = []
        for agent_id, task_type in _AGENT_TASK_MAP.items():
            keywords = _TOOL_CATEGORY_KEYWORDS.get(task_type, [])
            confidence = 0
            for kw in keywords:
                if kw in desc_lower:
                    confidence += 10
            if confidence > 0:
                suggestions.append({"agent_id": agent_id, "confidence": min(confidence, 100)})
        if any(c in categories for c in ["osint", "vulnerability_scan", "security"]):
            if not any(s["agent_id"] == "ghost" for s in suggestions):
                suggestions.append({"agent_id": "ghost", "confidence": 60})
        if any(c in categories for c in ["code_development", "debugging", "code_review"]):
            if not any(s["agent_id"] == "forge" for s in suggestions):
                suggestions.append({"agent_id": "forge", "confidence": 60})
        if any(c in categories for c in ["web_search", "research"]):
            if not any(s["agent_id"] == "veronica" for s in suggestions):
                suggestions.append({"agent_id": "veronica", "confidence": 60})
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        return suggestions

    def _suggest_single_agent(self, desc_lower: str) -> str:
        """Pick the single best agent for a subtask."""
        if any(kw in desc_lower for kw in ["search", "research", "find", "look up", "investigate", "information", "web"]):
            return "veronica"
        if any(kw in desc_lower for kw in ["scan", "vulnerability", "osint", "security", "recon", "threat", "exploit", "breach"]):
            return "ghost"
        if any(kw in desc_lower for kw in ["code", "write", "implement", "build", "create", "fix", "debug", "develop", "test", "refactor"]):
            return "forge"
        if any(kw in desc_lower for kw in ["memory", "store", "remember", "knowledge", "graph", "vector"]):
            return "atlas"
        return "forge"

    def _estimate_time(self, score: float, subtask_count: int) -> str:
        """Estimate time needed based on complexity score and subtask count."""
        mins = max(1, score * 0.3 + subtask_count * 2)
        if mins < 5:
            return "under 5 minutes"
        elif mins < 15:
            return "5-15 minutes"
        elif mins < 30:
            return "15-30 minutes"
        elif mins < 60:
            return "30-60 minutes"
        elif mins < 120:
            return "1-2 hours"
        else:
            return "2+ hours"

    def should_delegate(self, task_description: str, threshold: float = 35.0) -> bool:
        """Determine whether a task should be delegated to sub-agents.

        Args:
            task_description: The task to analyze.
            threshold: Complexity score above which delegation is recommended.

        Returns:
            True if the task should be delegated.
        """
        analysis = self.analyze_task_complexity(task_description)
        score = analysis["complexity_score"]
        if score >= threshold:
            return True
        has_multiple_agents = len(analysis.get("suggested_agents", [])) > 1
        if score >= threshold * 0.7 and has_multiple_agents:
            return True
        return False

    async def delegate_task(self, task_description: str, role: str = "general") -> dict[str, Any]:
        """Route a task to appropriate agent(s) based on analysis.

        Returns dict with task_id, delegation_type, agents, results.
        """
        task_id = f"delegate_{_short_id()}"
        analysis = self.analyze_task_complexity(task_description)
        subtasks = analysis.get("subtasks", [])
        suggested = analysis.get("suggested_agents", [])
        score = analysis["complexity_score"]

        result: dict[str, Any] = {
            "task_id": task_id,
            "task_description": task_description,
            "complexity_score": score,
            "delegation_type": "direct",
            "agents_delegated": [],
            "results": [],
            "status": "completed",
        }

        if not subtasks and suggested:
            agent_id = suggested[0]["agent_id"]
            result["delegation_type"] = "single"
            agent_result = await self._run_agent(agent_id, task_description, role)
            result["agents_delegated"].append(agent_id)
            result["results"].append(agent_result)
            return result

        if len(subtasks) > 1:
            result["delegation_type"] = "multi"
            for subtask in subtasks:
                agent_id = subtask.get("suggested_agent", "forge")
                agent_result = await self._run_agent(agent_id, subtask["description"], role)
                result["agents_delegated"].append({"agent": agent_id, "subtask": subtask["description"]})
                result["results"].append(agent_result)
            return result

        if suggested:
            agent_id = suggested[0]["agent_id"]
            result["delegation_type"] = "single"
            agent_result = await self._run_agent(agent_id, task_description, role)
            result["agents_delegated"].append(agent_id)
            result["results"].append(agent_result)
        else:
            result["status"] = "no_agent_found"
            result["message"] = "Could not determine which agent should handle this task"

        return result

    async def _run_agent(self, agent_id: str, task: str, role: str) -> dict[str, Any]:
        """Execute a task on a specific agent via the orchestrator."""
        term = self._terminal_manager.spawn_agent_terminal(
            agent_name=agent_id,
            prompt=task,
            task_type=role,
            role=role,
        )
        self._terminal_manager.update_agent_terminal(agent_id, status="running", action="Task delegated, starting execution...", progress=5)
        try:
            from friday.orchestrator import get_orchestrator
            orch = get_orchestrator()
            from friday.base_agent import AgentTask
            agent_task = AgentTask(
                task_type=role,
                payload=task,
                context_snapshot={"requester": "agent_delegator"},
            )
            self._terminal_manager.update_agent_terminal(agent_id, status="running", action="Executing via orchestrator...", progress=30)
            agent_result = await orch.delegate(agent_id, task)
            status = "completed" if agent_result.status == "completed" else "failed"
            progress_val = 100 if status == "completed" else 70
            self._terminal_manager.update_agent_terminal(
                agent_id,
                status=status,
                action="Finished execution",
                progress=progress_val,
                result_summary=agent_result.output[:300] if agent_result.output else (agent_result.error or "No output"),
            )
            return {
                "agent_id": agent_id,
                "task": task,
                "status": status,
                "output": agent_result.output,
                "error": agent_result.error,
                "duration_ms": agent_result.duration_ms,
            }
        except Exception as e:
            self._terminal_manager.update_agent_terminal(agent_id, status="failed", action=f"Error: {str(e)[:80]}", progress=0)
            return {
                "agent_id": agent_id,
                "task": task,
                "status": "failed",
                "error": str(e),
                "duration_ms": 0,
            }

    async def workflow_research_vuln_fix(self, target: str) -> dict[str, Any]:
        """Complete Research → Vulnerability Analysis → Fix workflow.

        Spawns Veronica (research) → gets report → spawns Ghost (vuln analysis)
        → gets vulns → spawns Forge (fix) → implements fixes.

        Each agent gets its own terminal window.
        Agents communicate via AgentBus.
        FRIDAY monitors all progress.
        Final report aggregated back to FRIDAY.

        Args:
            target: The target to research, analyze, and fix.

        Returns:
            Aggregated workflow result dict.
        """
        workflow_id = f"wf_rvf_{_short_id()}"
        start_time = time.monotonic()
        print(f"\n{ANSI_BOLD}{ANSI_CYAN}╔══════════════════════════════════════════════╗{ANSI_RESET}")
        print(f"{ANSI_BOLD}{ANSI_CYAN}║  Research → Vulnerability → Fix Workflow     ║{ANSI_RESET}")
        print(f"{ANSI_BOLD}{ANSI_CYAN}║  Target: {target:<33}║{ANSI_RESET}")
        print(f"{ANSI_BOLD}{ANSI_CYAN}╚══════════════════════════════════════════════╝{ANSI_RESET}")
        print(f"  Workflow ID: {workflow_id}")
        print(f"  Starting Research Phase...\n")

        bus = AgentBusEnhanced()
        await bus.publish_agent_status("friday", "running", f"Starting research->vuln->fix workflow on: {target}", 0, workflow_id)

        research_task = f"Research {target} thoroughly. Gather all available information including technologies used, architecture, public endpoints, and known issues. Provide a comprehensive research report."
        await bus.publish_agent_status("veronica", "running", research_task, 5, workflow_id)
        veronica_result = await self._run_agent("veronica", research_task, "research")
        research_report = veronica_result.get("output", "") or veronica_result.get("error", "No output")
        await bus.publish_agent_status("veronica", veronica_result["status"], "Research complete", 100 if veronica_result["status"] == "completed" else 0, workflow_id)
        if veronica_result["status"] == "failed":
            await bus.publish_agent_status("friday", "failed", f"Research phase failed: {research_report[:200]}", 0, workflow_id)
            return self._workflow_error_result(workflow_id, "research", veronica_result, start_time)

        print(f"\n{ANSI_GREEN}✔ Research phase complete.{ANSI_RESET}")
        print(f"  Starting Vulnerability Analysis Phase...\n")
        await bus.publish_agent_status("ghost", "running", f"Analyzing {target} for vulnerabilities using research data", 30, workflow_id)

        vuln_context = f"Research Report:\n{research_report[:2000]}\n\nTask: Analyze {target} for security vulnerabilities, misconfigurations, and weaknesses. Provide a detailed vulnerability assessment with severity ratings and remediation steps."
        await bus.publish_agent_status("ghost", "running", vuln_context, 35, workflow_id)
        ghost_result = await self._run_agent("ghost", vuln_context, "security")
        vuln_report = ghost_result.get("output", "") or ghost_result.get("error", "No output")
        await bus.publish_agent_status("ghost", ghost_result["status"], "Vulnerability analysis complete", 100 if ghost_result["status"] == "completed" else 0, workflow_id)
        if ghost_result["status"] == "failed":
            await bus.publish_agent_status("friday", "failed", f"Vulnerability analysis phase failed: {vuln_report[:200]}", 0, workflow_id)
            return self._workflow_error_result(workflow_id, "vulnerability", ghost_result, start_time)

        print(f"\n{ANSI_GREEN}✔ Vulnerability analysis phase complete.{ANSI_RESET}")
        print(f"  Starting Fix Implementation Phase...\n")
        await bus.publish_agent_status("forge", "running", f"Implementing fixes for {target} based on vulnerability report", 60, workflow_id)

        fix_context = f"Research Report:\n{research_report[:1500]}\n\nVulnerability Report:\n{vuln_report[:2000]}\n\nTask: Implement fixes and patches for all identified vulnerabilities in {target}. Write code, create patches, and document changes."
        await bus.publish_agent_status("forge", "running", fix_context, 65, workflow_id)
        forge_result = await self._run_agent("forge", fix_context, "code")
        fix_output = forge_result.get("output", "") or forge_result.get("error", "No output")
        await bus.publish_agent_status("forge", forge_result["status"], "Fix implementation complete", 100 if forge_result["status"] == "completed" else 0, workflow_id)

        duration_s = int(time.monotonic() - start_time)
        all_completed = all(
            r["status"] == "completed"
            for r in [veronica_result, ghost_result, forge_result]
        )

        aggregated = {
            "workflow_id": workflow_id,
            "workflow_type": "research_vuln_fix",
            "target": target,
            "status": "completed" if all_completed else "partial",
            "duration_seconds": duration_s,
            "research": {
                "agent": "veronica",
                "status": veronica_result["status"],
                "report_preview": research_report[:500],
                "full_length": len(research_report),
            },
            "vulnerability_analysis": {
                "agent": "ghost",
                "status": ghost_result["status"],
                "report_preview": vuln_report[:500],
                "full_length": len(vuln_report),
            },
            "fix_implementation": {
                "agent": "forge",
                "status": forge_result["status"],
                "fix_preview": fix_output[:500],
                "full_length": len(fix_output),
            },
            "phases_completed": sum(1 for r in [veronica_result, ghost_result, forge_result] if r["status"] == "completed"),
            "phases_total": 3,
        }

        final_status = "completed" if all_completed else "partial"
        await bus.publish_agent_status(
            "friday", final_status,
            f"Workflow completed in {duration_s}s. Research: {veronica_result['status']}, Vuln: {ghost_result['status']}, Fix: {forge_result['status']}",
            100, workflow_id,
        )

        print(f"\n{ANSI_BOLD}{'=' * 60}{ANSI_RESET}")
        print(f"{ANSI_BOLD}WORKFLOW COMPLETE{ANSI_RESET} {'✔' if all_completed else '⚠'}")
        print(f"  Target: {target}")
        print(f"  Duration: {duration_s}s")
        print(f"  Research phase:   {veronica_result['status']}")
        print(f"  Vuln analysis:    {ghost_result['status']}")
        print(f"  Fix phase:        {forge_result['status']}")
        print(f"{'=' * 60}")

        return aggregated

    def _workflow_error_result(self, workflow_id: str, phase: str, result: dict, start_time: float) -> dict:
        return {
            "workflow_id": workflow_id,
            "workflow_type": "research_vuln_fix",
            "status": "failed",
            "failed_phase": phase,
            "error": result.get("error", result.get("output", "Unknown error")),
            "duration_seconds": int(time.monotonic() - start_time),
        }

    async def multi_agent_coordinator(self, complex_task: str) -> dict[str, Any]:
        """Orchestrate a multi-agent workflow for a complex task.

        Breaks task into subtasks, determines dependencies, spawns agents
        for each subtask, monitors progress, and aggregates results.

        Args:
            complex_task: The complex multi-step task to coordinate.

        Returns:
            Aggregated results from all agents.
        """
        coord_id = f"coord_{_short_id()}"
        start_time = time.monotonic()
        analysis = self.analyze_task_complexity(complex_task)
        subtasks = analysis.get("subtasks", [])
        score = analysis["complexity_score"]

        print(f"\n{ANSI_BOLD}{ANSI_MAGENTA}╔══════════════════════════════════════════════╗{ANSI_RESET}")
        print(f"{ANSI_BOLD}{ANSI_MAGENTA}║  Multi-Agent Coordinator                    ║{ANSI_RESET}")
        print(f"{ANSI_BOLD}{ANSI_MAGENTA}║  Complexity: {score:.0f}/100{' ' * (29 - len(str(int(score))))}║{ANSI_RESET}")
        print(f"{ANSI_BOLD}{ANSI_MAGENTA}║  Subtasks: {len(subtasks)}{' ' * (33 - len(str(len(subtasks))))}║{ANSI_RESET}")
        print(f"{ANSI_BOLD}{ANSI_MAGENTA}╚══════════════════════════════════════════════╝{ANSI_RESET}")

        bus = AgentBusEnhanced()
        await bus.publish_agent_status("friday", "running", f"Coordinating multi-agent task with {len(subtasks)} subtasks", 0, coord_id)

        if not subtasks:
            from friday.orchestrator import get_orchestrator
            orch = get_orchestrator()
            agent_results = await self.delegate_task(complex_task)
            return {
                "coordination_id": coord_id,
                "status": "completed",
                "agent_results": agent_results,
                "duration_seconds": int(time.monotonic() - start_time),
                "note": "Task was not decomposed; routed directly",
            }

        phase_results: dict[str, Any] = {}
        agent_to_subtask: dict[str, dict] = {}
        dependency_map: dict[str, list[str]] = {}
        subtask_map: dict[str, dict] = {}

        for i, st in enumerate(subtasks):
            st_id = st["id"]
            subtask_map[st_id] = st
            agent_to_subtask[st["suggested_agent"]] = st
            deps = []
            for prev in subtasks[:i]:
                if prev.get("suggested_agent") != st.get("suggested_agent"):
                    deps.append(prev["id"])
            dependency_map[st_id] = deps

        completed_subtasks: set[str] = set()
        completed_agents: set[str] = set()

        print(f"\n{ANSI_BOLD}Executing {len(subtasks)} subtasks:{ANSI_RESET}")
        for i, st in enumerate(subtasks):
            agent_id = st["suggested_agent"]
            print(f"  {i + 1}. [{agent_id}] {st['description']}")

        await bus.publish_agent_status("friday", "running", f"Decomposed into {len(subtasks)} subtasks: {', '.join(s['description'][:40] for s in subtasks)}", 5, coord_id)

        sequential_phases: list[list[dict]] = []
        current_phase: list[dict] = []
        seen_agents_in_phase: set[str] = set()
        for st in subtasks:
            agent = st["suggested_agent"]
            if agent in seen_agents_in_phase and current_phase:
                sequential_phases.append(current_phase)
                current_phase = [st]
                seen_agents_in_phase = {agent}
            else:
                current_phase.append(st)
                seen_agents_in_phase.add(agent)
        if current_phase:
            sequential_phases.append(current_phase)

        overall_progress_base = 5.0
        phase_progress_share = 90.0 / max(len(sequential_phases), 1)

        for phase_idx, phase in enumerate(sequential_phases):
            phase_tasks: list[asyncio.Task] = []
            for st in phase:
                agent_id = st["suggested_agent"]
                task_desc = st["description"]
                term = self._terminal_manager.spawn_agent_terminal(agent_id, task_desc, "general", agent_id)
                self._terminal_manager.update_agent_terminal(agent_id, status="running", action=f"Starting: {task_desc[:60]}", progress=10)
                await bus.publish_agent_status(agent_id, "running", task_desc, overall_progress_base, coord_id)

            for st in phase:
                agent_id = st["suggested_agent"]
                task_desc = st["description"]
                combined_task = f"{complex_task}\n\nSubtask: {task_desc}" if len(subtasks) > 1 else complex_task
                phase_tasks.append(
                    asyncio.create_task(
                        self._run_agent_and_report(agent_id, combined_task, "general", coord_id, bus, phase_results)
                    )
                )

            phase_results_list = await asyncio.gather(*phase_tasks, return_exceptions=True)

            for i, (st, result_or_err) in enumerate(zip(phase, phase_results_list)):
                agent_id = st["suggested_agent"]
                if isinstance(result_or_err, Exception):
                    phase_results[agent_id] = {"agent_id": agent_id, "status": "failed", "error": str(result_or_err)}
                    self._terminal_manager.update_agent_terminal(agent_id, status="failed", action=f"Error: {str(result_or_err)[:80]}")
                else:
                    phase_results[agent_id] = result_or_err
                    s = result_or_err.get("status", "failed")
                    self._terminal_manager.update_agent_terminal(
                        agent_id,
                        status=s,
                        action="Completed" if s == "completed" else "Failed",
                        progress=100 if s == "completed" else 50,
                        result_summary=(result_or_err.get("output") or result_or_err.get("error") or "")[:300],
                    )
                    self._terminal_manager.close_agent_terminal(agent_id)

            overall_progress_base += phase_progress_share
            completed_count = sum(1 for v in phase_results.values() if v.get("status") == "completed")
            await bus.publish_agent_status(
                "friday", "running",
                f"Phase {phase_idx + 1}/{len(sequential_phases)} complete. {completed_count}/{len(subtasks)} subtasks done.",
                min(overall_progress_base, 95),
                coord_id,
            )

        final_status = "completed" if all(
            r.get("status") == "completed" for r in phase_results.values()
        ) else "partial"

        await bus.publish_agent_status("friday", final_status, "All subtasks completed", 100, coord_id)

        duration_s = int(time.monotonic() - start_time)
        return {
            "coordination_id": coord_id,
            "task": complex_task,
            "status": final_status,
            "complexity_score": score,
            "subtasks_planned": len(subtasks),
            "subtasks_completed": sum(1 for v in phase_results.values() if v.get("status") == "completed"),
            "duration_seconds": duration_s,
            "agent_results": phase_results,
            "phases_executed": len(sequential_phases),
        }

    async def _run_agent_and_report(
        self,
        agent_id: str,
        task: str,
        role: str,
        coord_id: str,
        bus: AgentBusEnhanced,
        phase_results: dict,
    ) -> dict[str, Any]:
        """Run a single agent and publish status updates to the bus."""
        try:
            await bus.publish_agent_status(agent_id, "running", task, 10, coord_id)
            from friday.orchestrator import get_orchestrator
            orch = get_orchestrator()
            agent_result = await orch.delegate(agent_id, task)
            status = "completed" if agent_result.status == "completed" else "failed"
            await bus.publish_agent_status(agent_id, status, agent_result.output[:200] if agent_result.output else (agent_result.error or ""), 100, coord_id)
            return {
                "agent_id": agent_id,
                "task": task,
                "status": status,
                "output": agent_result.output,
                "error": agent_result.error,
                "duration_ms": agent_result.duration_ms,
            }
        except Exception as e:
            await bus.publish_agent_status(agent_id, "failed", str(e)[:200], 0, coord_id)
            return {"agent_id": agent_id, "task": task, "status": "failed", "error": str(e), "duration_ms": 0}


_DELEGATOR: Optional[AgentDelegator] = None
_DELEGATOR_LOCK = Lock()


def get_delegator() -> AgentDelegator:
    """Get or create the singleton AgentDelegator."""
    global _DELEGATOR
    if _DELEGATOR is None:
        with _DELEGATOR_LOCK:
            if _DELEGATOR is None:
                _DELEGATOR = AgentDelegator()
    return _DELEGATOR


# ═══════════════════════════════════════════════════════════════════
# AgentBusEnhanced
# ═══════════════════════════════════════════════════════════════════

class AgentBusEnhanced:
    """Extends friday.agent_bus with real-time status, agent-to-agent passing,
    terminal window updates, and FRIDAY subscription to all agent topics.
    """

    def __init__(self):
        self._terminal_manager = get_terminal_manager()
        self._subscribed = False
        self._status_cache: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def publish_agent_status(
        self,
        agent_name: str,
        status: str,
        action: str,
        progress: float,
        task_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Publish agent status to the bus and update terminal display.

        Args:
            agent_name: Name of the agent.
            status: One of starting, running, completed, failed.
            action: Current action description.
            progress: Progress percentage (0-100).
            task_id: Optional task identifier for correlation.

        Returns:
            The published message dict.
        """
        topic = f"agent.{status}"
        data = {
            "agent_id": agent_name,
            "status": status,
            "action": action,
            "progress": progress,
            "task_id": task_id or "",
            "timestamp": _iso_now(),
        }
        async with self._lock:
            self._status_cache[agent_name] = data

        try:
            from friday.agent_bus import publish as bus_pub
            msg = await bus_pub(agent_name, topic, data, task_id=task_id)
        except Exception:
            msg = {"id": f"msg_{_short_id()}", "agent_id": agent_name, "topic": topic, "data": data, "task_id": task_id, "timestamp": _iso_now()}

        self._terminal_manager.update_agent_terminal(
            agent_name,
            status=status,
            action=action,
            progress=progress,
        )

        return msg

    async def subscribe_friday(self) -> bool:
        """Subscribe FRIDAY to all agent topics so she receives every update.

        Once subscribed, any publish by any agent will be forwarded to
        FRIDAY's handler for monitoring and coordination.
        """
        if self._subscribed:
            return True
        try:
            from friday.agent_bus import subscribe

            async def friday_handler(msg: dict):
                agent_id = msg.get("agent_id", "unknown")
                topic = msg.get("topic", "unknown")
                data = msg.get("data", {})
                async with self._lock:
                    self._status_cache[agent_id] = {
                        "agent_id": agent_id,
                        "status": data.get("status", topic.split(".")[-1]),
                        "action": data.get("action", ""),
                        "progress": data.get("progress", 0),
                        "task_id": data.get("task_id", ""),
                        "timestamp": data.get("timestamp", _iso_now()),
                    }

            for topic_suffix in ["started", "running", "progress", "completed", "failed", "error"]:
                topic = f"agent.{topic_suffix}"
                try:
                    await subscribe(topic, friday_handler)
                except Exception:
                    pass
            self._subscribed = True
            return True
        except Exception:
            return False

    def get_all_agent_statuses(self) -> dict[str, dict[str, Any]]:
        """Get a snapshot of all agent statuses known to the bus."""
        return dict(self._status_cache)

    async def wait_for_agent_chain(self, chain: list[dict[str, Any]], timeout: float = 300.0) -> dict[str, Any]:
        """Wait for a sequential chain of agents to complete.

        Each dict in chain must have:
          - agent_id: str
          - task: str
          - task_id: str (optional, auto-generated if missing)

        Agents run sequentially: the next starts after the previous completes.
        Their results are passed via agent_to_agent.

        Args:
            chain: Ordered list of agent task dicts.
            timeout: Max total seconds for the entire chain.

        Returns:
            Dict with chain_id, status, results per agent.
        """
        chain_id = f"chain_{_short_id()}"
        start_time = time.monotonic()
        results: list[dict[str, Any]] = []
        current_data: Optional[Any] = None

        for i, link in enumerate(chain):
            elapsed = time.monotonic() - start_time
            if elapsed > timeout:
                return {
                    "chain_id": chain_id,
                    "status": "timeout",
                    "completed": i,
                    "total": len(chain),
                    "results": results,
                    "error": f"Chain timed out after {elapsed:.0f}s",
                }

            agent_id = link["agent_id"]
            task = link["task"]
            link_task_id = link.get("task_id", f"{chain_id}_step_{i}")

            if current_data is not None:
                enriched_task = f"{task}\n\nPrevious agent data:\n{str(current_data)[:1000]}"
            else:
                enriched_task = task

            self._terminal_manager.spawn_agent_terminal(agent_id, enriched_task, "chain", agent_id)
            self._terminal_manager.update_agent_terminal(agent_id, status="running", action=f"Chain step {i + 1}/{len(chain)}", progress=10)

            try:
                from friday.orchestrator import get_orchestrator
                orch = get_orchestrator()
                agent_result = await orch.delegate(agent_id, enriched_task)
                step_status = "completed" if agent_result.status == "completed" else "failed"
                self._terminal_manager.update_agent_terminal(
                    agent_id,
                    status=step_status,
                    action="Chain step complete",
                    progress=100 if step_status == "completed" else 50,
                    result_summary=(agent_result.output or agent_result.error or "")[:300],
                )
                step_result = {
                    "step": i + 1,
                    "agent_id": agent_id,
                    "task": enriched_task,
                    "status": step_status,
                    "output": agent_result.output,
                    "error": agent_result.error,
                    "duration_ms": agent_result.duration_ms,
                }
                results.append(step_result)

                if current_data is not None:
                    await self.agent_to_agent(chain[i - 1]["agent_id"], agent_id, {
                        "source_step": i,
                        "source_agent": chain[i - 1]["agent_id"],
                        "result": agent_result.output,
                    })

                current_data = agent_result.output
                self._terminal_manager.close_agent_terminal(agent_id)

            except Exception as e:
                step_result = {
                    "step": i + 1,
                    "agent_id": agent_id,
                    "task": enriched_task,
                    "status": "failed",
                    "error": str(e),
                    "duration_ms": 0,
                }
                results.append(step_result)
                self._terminal_manager.update_agent_terminal(agent_id, status="failed", action=str(e)[:80])
                return {
                    "chain_id": chain_id,
                    "status": "failed",
                    "failed_step": i + 1,
                    "results": results,
                    "error": f"Step {i + 1} ({agent_id}) failed: {e}",
                }

        all_completed = all(r["status"] == "completed" for r in results)
        return {
            "chain_id": chain_id,
            "status": "completed" if all_completed else "partial",
            "steps_total": len(chain),
            "steps_completed": sum(1 for r in results if r["status"] == "completed"),
            "results": results,
            "duration_seconds": int(time.monotonic() - start_time),
        }

    async def agent_to_agent(self, from_agent: str, to_agent: str, data: Any) -> dict[str, Any]:
        """Pass data from one agent to another via the bus.

        Publishes on topic 'agent.{to_agent}.inbox' so the receiving agent
        can subscribe and process the incoming data.

        Args:
            from_agent: Sending agent name.
            to_agent: Receiving agent name.
            data: Any serializable data to pass.

        Returns:
            The published message dict.
        """
        topic = f"agent.{to_agent}.inbox"
        payload = {
            "from": from_agent,
            "to": to_agent,
            "data": data,
            "timestamp": _iso_now(),
            "type": "agent_to_agent",
        }
        try:
            from friday.agent_bus import publish as bus_pub
            msg = await bus_pub(from_agent, topic, payload)
        except Exception:
            msg = {"id": f"msg_{_short_id()}", "agent_id": from_agent, "topic": topic, "data": payload, "task_id": None, "timestamp": _iso_now()}
        return msg


_AGENT_BUS_ENHANCED: Optional[AgentBusEnhanced] = None


def get_agent_bus_enhanced() -> AgentBusEnhanced:
    """Get or create the singleton AgentBusEnhanced."""
    global _AGENT_BUS_ENHANCED
    if _AGENT_BUS_ENHANCED is None:
        _AGENT_BUS_ENHANCED = AgentBusEnhanced()
    return _AGENT_BUS_ENHANCED


# ═══════════════════════════════════════════════════════════════════
# High-Level Tool Functions (what FRIDAY calls)
# ═══════════════════════════════════════════════════════════════════

async def agent_spawn_and_track(name: str, task: str, role: str = "general") -> dict[str, Any]:
    """Spawn an agent and open its terminal window for tracking.

    FRIDAY calls this to create a visible, trackable agent session.

    Args:
        name: Agent name (e.g., 'veronica', 'forge', 'ghost').
        task: Task description/prompt for the agent.
        role: Agent role (e.g., 'research', 'code', 'security').

    Returns:
        Dict with spawn result and terminal info.
    """
    tm = get_terminal_manager()
    term = tm.spawn_agent_terminal(name, task, role, role)
    if not term.get("success"):
        return {"success": False, "error": term.get("error", "Failed to spawn terminal")}
    tm.update_agent_terminal(name, status="starting", action="Agent spawned, beginning task...", progress=0)
    try:
        from friday.agents_manager import spawn_agent
        agent_result = spawn_agent(name, task, role)
        status = "running" if agent_result.get("status") == "scheduled" else "failed"
        tm.update_agent_terminal(
            name,
            status=status,
            action=agent_result.get("message", "Task delegated"),
            progress=50,
        )
        return {
            "success": True,
            "agent_name": name,
            "task": task,
            "role": role,
            "spawn_result": agent_result,
            "terminal": term,
        }
    except Exception as e:
        tm.update_agent_terminal(name, status="failed", action=f"Error: {str(e)[:80]}")
        return {"success": False, "error": str(e), "terminal": term}


async def agent_delegate_with_terminal(name: str, task: str, role: str = "general") -> dict[str, Any]:
    """Delegate a task to an agent with a terminal window.

    Combines delegation and terminal tracking in one call.

    Args:
        name: Agent name.
        task: Task description.
        role: Agent role.

    Returns:
        Delegation result dict.
    """
    tm = get_terminal_manager()
    tm.spawn_agent_terminal(name, task, role, role)
    tm.update_agent_terminal(name, status="running", action="Delegating task...", progress=10)
    try:
        delegator = get_delegator()
        result = await delegator.delegate_task(task)
        status = result.get("status", "completed")
        tm.update_agent_terminal(
            name,
            status=status,
            action=f"Delegation {'complete' if status == 'completed' else 'failed'}",
            progress=100 if status == "completed" else 50,
        )
        return result
    except Exception as e:
        tm.update_agent_terminal(name, status="failed", action=str(e)[:80])
        return {"success": False, "error": str(e)}


def friday_should_delegate(task_description: str, threshold: float = 35.0) -> bool:
    """Quick check: should FRIDAY handle this herself or delegate to sub-agents?

    FRIDAY calls this to decide whether to keep a task or pass it off.

    Args:
        task_description: The task to evaluate.
        threshold: Complexity threshold for delegation.

    Returns:
        True if the task should be delegated.
    """
    delegator = get_delegator()
    return delegator.should_delegate(task_description, threshold=threshold)


async def friday_parse_and_delegate(utterance: str) -> dict[str, Any]:
    """Parse a natural language utterance from the user and auto-delegate.

    FRIDAY calls this when she receives a user request that should be
    routed to sub-agents. Decomposes the utterance, determines the best
    agent(s), spawns them with terminal windows, and returns results.

    Args:
        utterance: The user's natural language request.

    Returns:
        Delegation result with analysis.
    """
    delegator = get_delegator()
    analysis = delegator.analyze_task_complexity(utterance)
    score = analysis["complexity_score"]
    should_delegate = score >= 35.0 or len(analysis.get("subtasks", [])) > 1

    if not should_delegate:
        return {
            "delegated": False,
            "reason": f"Task complexity ({score:.0f}/100) is below threshold. FRIDAY will handle directly.",
            "analysis": analysis,
        }

    print(f"\n{ANSI_BOLD}{ANSI_CYAN}[FRIDAY] Parsing and delegating...{ANSI_RESET}")
    print(f"  Complexity: {score:.0f}/100")
    if analysis.get("subtasks"):
        print(f"  Subtasks ({len(analysis['subtasks'])}):")
        for st in analysis["subtasks"]:
            agent = st.get("suggested_agent", "?")
            print(f"    -> [{agent}] {st['description'][:60]}")
    if analysis.get("suggested_agents"):
        print(f"  Suggested agents: {', '.join(a['agent_id'] for a in analysis['suggested_agents'])}")

    if len(analysis.get("subtasks", [])) > 1:
        result = await delegator.multi_agent_coordinator(utterance)
    else:
        result = await delegator.delegate_task(utterance)

    result["delegated"] = True
    result["analysis"] = analysis
    return result


async def friday_key_check() -> dict[str, Any]:
    """Check all required API keys and prompt for any that are missing.

    FRIDAY calls this at startup to ensure all keys are configured.

    Returns:
        Key status dict.
    """
    km = get_key_manager()
    if not km.have_valid_keys():
        if not km.have_keys_present():
            result = await km.prompt_for_missing_keys()
        else:
            result: dict[str, Any] = {"keys_updated": False, "nvidia_result": None, "opencode_result": None}
            nv = await km.verify_nvidia_key(km.get_nvidia_key())
            oc = await km.verify_opencode_key(km.get_opencode_key())
            if nv["verified"]:
                result["nvidia_result"] = nv
            if oc["verified"]:
                result["opencode_result"] = oc
            result["keys_updated"] = km.have_valid_keys()
    else:
        result = {"keys_updated": True, "nvidia_result": {"verified": True}, "opencode_result": {"verified": True}}
    result["key_status"] = km.get_key_status()
    return result


async def friday_workflow_research_vuln_fix(target: str) -> dict[str, Any]:
    """Full research → vulnerability analysis → fix workflow.

    FRIDAY calls this for comprehensive security assessment and remediation.

    Args:
        target: The target system/service/codebase to analyze.

    Returns:
        Aggregated workflow result.
    """
    delegator = get_delegator()
    return await delegator.workflow_research_vuln_fix(target)


def agent_bus_status() -> dict[str, Any]:
    """Get status of all agents known to the enhanced bus.

    FRIDAY calls this to check on her agents.

    Returns:
        Dict with agent statuses and terminal count.
    """
    bus = get_agent_bus_enhanced()
    tm = get_terminal_manager()
    return {
        "agents": bus.get_all_agent_statuses(),
        "active_terminals": tm.list_active_terminals(),
        "terminal_count": tm.get_terminal_count(),
        "timestamp": _iso_now(),
    }


async def agent_chain_research_vuln_fix(target: str) -> dict[str, Any]:
    """Chain workflow: research → vulnerability analysis → fix.

    Uses sequential agent chaining where each agent gets the previous
    agent's results. Each agent gets its own terminal window.

    Args:
        target: The target to analyze.

    Returns:
        Chain result dict.
    """
    bus = get_agent_bus_enhanced()
    chain = [
        {
            "agent_id": "veronica",
            "task": f"Research {target} thoroughly. Gather all available information including technologies used, architecture, public endpoints, and known issues. Provide a comprehensive research report.",
            "task_id": f"chain_research_{_short_id()}",
        },
        {
            "agent_id": "ghost",
            "task": f"Analyze {target} for security vulnerabilities, misconfigurations, and weaknesses based on the research. Provide a detailed vulnerability assessment with severity ratings and remediation steps.",
            "task_id": f"chain_vuln_{_short_id()}",
        },
        {
            "agent_id": "forge",
            "task": f"Implement fixes and patches for all identified vulnerabilities in {target}. Write code, create patches, and document all changes thoroughly.",
            "task_id": f"chain_fix_{_short_id()}",
        },
    ]
    result = await bus.wait_for_agent_chain(chain, timeout=600.0)
    result["target"] = target
    result["workflow_type"] = "research_vuln_fix_chain"
    return result


async def friday_multi_agent_task(complex_task: str) -> dict[str, Any]:
    """Full multi-agent coordination for a complex task.

    FRIDAY calls this when a task requires multiple agents working together.

    Args:
        complex_task: The complex multi-step task.

    Returns:
        Coordinated multi-agent result.
    """
    delegator = get_delegator()
    return await delegator.multi_agent_coordinator(complex_task)


async def close_all_agent_resources() -> dict[str, Any]:
    """Cleanup: close all terminals, remove temp files.

    FRIDAY calls this on shutdown.

    Returns:
        Cleanup result dict.
    """
    tm = get_terminal_manager()
    term_result = tm.close_all_terminals()
    tm.cleanup_temp_dir()
    km = get_key_manager()
    await km.close()
    return {
        "terminals_closed": term_result.get("count", 0),
        "terminal_errors": term_result.get("errors", []),
        "success": term_result.get("success", False),
        "timestamp": _iso_now(),
    }


# ═══════════════════════════════════════════════════════════════════
# AGENT_TERMINAL_TOOL_DESCRIPTIONS — For FRIDAY's tool map
# ═══════════════════════════════════════════════════════════════════

AGENT_TERMINAL_TOOL_DESCRIPTIONS: dict[str, dict[str, Any]] = {
    "friday_key_check": {
        "name": "friday_key_check",
        "description": "Check all required API keys (NVIDIA NIM, OpenCode Zen) and prompt the user for any missing keys. Call at startup.",
        "parameters": {},
        "returns": {"type": "dict", "description": "Key status with verification results"},
    },
    "friday_should_delegate": {
        "name": "friday_should_delegate",
        "description": "Analyze a task and decide whether FRIDAY should delegate it to sub-agents or handle it directly.",
        "parameters": {
            "task_description": {"type": "string", "description": "The task to evaluate"},
            "threshold": {"type": "number", "description": "Complexity threshold (default 35)", "default": 35.0},
        },
        "returns": {"type": "bool", "description": "True if task should be delegated"},
    },
    "friday_parse_and_delegate": {
        "name": "friday_parse_and_delegate",
        "description": "Parse a user utterance, analyze complexity, and automatically delegate to the appropriate sub-agent(s) with terminal windows.",
        "parameters": {
            "utterance": {"type": "string", "description": "The user's natural language request"},
        },
        "returns": {"type": "dict", "description": "Delegation result with analysis and agent results"},
    },
    "friday_workflow_research_vuln_fix": {
        "name": "friday_workflow_research_vuln_fix",
        "description": "Execute a complete Research → Vulnerability Analysis → Fix workflow on a target. Spawns Veronica, Ghost, and Forge in sequence with terminal windows.",
        "parameters": {
            "target": {"type": "string", "description": "The target system/service/codebase to analyze"},
        },
        "returns": {"type": "dict", "description": "Aggregated workflow result from all phases"},
    },
    "friday_multi_agent_task": {
        "name": "friday_multi_agent_task",
        "description": "Coordinate multiple agents for a complex multi-step task. Breaks the task into subtasks, spawns agents in parallel/serial with dependency tracking.",
        "parameters": {
            "complex_task": {"type": "string", "description": "The complex multi-step task description"},
        },
        "returns": {"type": "dict", "description": "Coordinated multi-agent result"},
    },
    "agent_spawn_and_track": {
        "name": "agent_spawn_and_track",
        "description": "Spawn an agent with a terminal window for visual tracking. Creates a dedicated CMD window showing agent status, progress, and results.",
        "parameters": {
            "name": {"type": "string", "description": "Agent name (veronica, forge, ghost, atlas)"},
            "task": {"type": "string", "description": "Task description for the agent"},
            "role": {"type": "string", "description": "Agent role (research, code, security, memory)", "default": "general"},
        },
        "returns": {"type": "dict", "description": "Spawn result with terminal info"},
    },
    "agent_delegate_with_terminal": {
        "name": "agent_delegate_with_terminal",
        "description": "Delegate a task to an agent with a terminal window. Combines delegation routing and terminal tracking.",
        "parameters": {
            "name": {"type": "string", "description": "Agent name"},
            "task": {"type": "string", "description": "Task description"},
            "role": {"type": "string", "description": "Agent role", "default": "general"},
        },
        "returns": {"type": "dict", "description": "Delegation result"},
    },
    "agent_bus_status": {
        "name": "agent_bus_status",
        "description": "Get the status of all agents and active terminal windows. Returns a snapshot of the entire agent ecosystem.",
        "parameters": {},
        "returns": {"type": "dict", "description": "All agent statuses and terminal info"},
    },
    "agent_chain_research_vuln_fix": {
        "name": "agent_chain_research_vuln_fix",
        "description": "Chain workflow where Veronica researches, Ghost analyzes vulnerabilities, and Forge implements fixes — with results passed between agents.",
        "parameters": {
            "target": {"type": "string", "description": "The target to analyze"},
        },
        "returns": {"type": "dict", "description": "Chain workflow result"},
    },
    "close_all_agent_resources": {
        "name": "close_all_agent_resources",
        "description": "Cleanup all agent resources: close terminal windows, remove temp files, close HTTP connections. Call on shutdown.",
        "parameters": {},
        "returns": {"type": "dict", "description": "Cleanup result"},
    },
}


# ═══════════════════════════════════════════════════════════════════
# Module-level cleanup for atexit
# ═══════════════════════════════════════════════════════════════════

def _cleanup_on_exit():
    """Synchronous cleanup for atexit registration."""
    tm = get_terminal_manager()
    tm.close_all_terminals()
    tm.cleanup_temp_dir()


import atexit
atexit.register(_cleanup_on_exit)


# ═══════════════════════════════════════════════════════════════════
# OpenCode-style Delegation Depth Tracking
# ═══════════════════════════════════════════════════════════════════

_delegation_depth: dict[str, int] = {}
_MAX_DELEGATION_DEPTH = 5


def get_delegation_depth(task_id: str) -> int:
    return _delegation_depth.get(task_id, 0)


def _increment_depth(task_id: str) -> int:
    depth = _delegation_depth.get(task_id, 0) + 1
    _delegation_depth[task_id] = depth
    return depth


# ═══════════════════════════════════════════════════════════════════
# Permission-based Tool Restriction (OpenCode ruleset style)
# ═══════════════════════════════════════════════════════════════════

_ALLOW_TOOL_PATTERNS: dict[str, list[str]] = {}
_DENY_TOOL_PATTERNS: dict[str, list[str]] = {}


def set_tool_ruleset(agent_id: str, allow: list[str] | None = None, deny: list[str] | None = None) -> None:
    if allow is not None:
        _ALLOW_TOOL_PATTERNS[agent_id] = allow
    if deny is not None:
        _DENY_TOOL_PATTERNS[agent_id] = deny


def get_allowed_tools_for_agent(agent_id: str) -> list[str]:
    import fnmatch
    tools = get_agent_tools(agent_id)
    allow_patterns = _ALLOW_TOOL_PATTERNS.get(agent_id, [])
    deny_patterns = _DENY_TOOL_PATTERNS.get(agent_id, [])

    if not allow_patterns and not deny_patterns:
        return tools

    if allow_patterns:
        filtered = []
        for t in tools:
            for pat in allow_patterns:
                if fnmatch.fnmatch(t, pat):
                    filtered.append(t)
                    break
        tools = filtered

    if deny_patterns:
        filtered = []
        for t in tools:
            denied = False
            for pat in deny_patterns:
                if fnmatch.fnmatch(t, pat):
                    denied = True
                    break
            if not denied:
                filtered.append(t)
        tools = filtered

    return tools


# ═══════════════════════════════════════════════════════════════════
# OpenCode-style Delegation Prompt Crafting
# ═══════════════════════════════════════════════════════════════════

def friday_craft_delegation_prompt(
    task_description: str,
    agent_id: str,
    expected_output: str = "",
    verify_instructions: str = "",
    context: str = "",
) -> str:
    parts: list[str] = []
    parts.append("## Task")
    parts.append(task_description)
    parts.append("")

    if expected_output:
        parts.append("## Expected Output")
        parts.append(expected_output)
        parts.append("")

    if verify_instructions:
        parts.append("## Verification Instructions")
        parts.append(verify_instructions)
        parts.append("")

    if context:
        parts.append("## Context")
        parts.append(context)
        parts.append("")

    tools = get_allowed_tools_for_agent(agent_id)
    if tools:
        parts.append("## Available Tools")
        parts.append(", ".join(tools))
        parts.append("")

    task_id = _short_id()
    depth = _increment_depth(task_id)
    if depth > _MAX_DELEGATION_DEPTH:
        parts.append("## WARNING: Maximum delegation depth reached")
        parts.append(f"Depth: {depth}/{_MAX_DELEGATION_DEPTH}. Complete the task without further delegation.")
        parts.append("")

    parts.append("## Return Format")
    parts.append("Provide your final answer as a clear, structured response. Start with a summary of what was done, then present the results.")

    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════════
# High-level Delegation with Crafted Prompt
# ═══════════════════════════════════════════════════════════════════

async def friday_delegate_with_prompt(
    agent_id: str,
    task_description: str,
    expected_output: str = "",
    verify_instructions: str = "",
    context: str = "",
    role: str = "general",
) -> dict[str, Any]:
    task_id = _short_id()
    depth = _increment_depth(task_id)

    if depth > _MAX_DELEGATION_DEPTH:
        return {
            "task_id": task_id,
            "agent_id": agent_id,
            "status": "failed",
            "error": f"Delegation depth {depth} exceeds maximum {_MAX_DELEGATION_DEPTH}",
            "depth": depth,
        }

    prompt = friday_craft_delegation_prompt(
        task_description=task_description,
        agent_id=agent_id,
        expected_output=expected_output,
        verify_instructions=verify_instructions,
        context=context,
    )

    from friday.orchestrator import get_orchestrator
    orch = get_orchestrator()

    try:
        agent_result = await orch.delegate(agent_id, prompt)
        status = "completed" if agent_result.status == "completed" else "failed"
        return {
            "task_id": task_id,
            "agent_id": agent_id,
            "status": status,
            "output": agent_result.output,
            "error": agent_result.error,
            "depth": depth,
            "duration_ms": getattr(agent_result, "duration_ms", 0),
        }
    except Exception as e:
        return {
            "task_id": task_id,
            "agent_id": agent_id,
            "status": "failed",
            "error": str(e),
            "depth": depth,
        }


# ═══════════════════════════════════════════════════════════════════
# Session Isolation (per-agent conversation context)
# ═══════════════════════════════════════════════════════════════════

_agent_sessions: dict[str, list[dict[str, Any]]] = {}
_MAX_SESSION_MESSAGES = 50


def store_agent_session(agent_id: str, messages: list[dict[str, Any]]) -> None:
    _agent_sessions[agent_id] = messages[-_MAX_SESSION_MESSAGES:]


def get_agent_session(agent_id: str) -> list[dict[str, Any]]:
    return _agent_sessions.get(agent_id, [])


def clear_agent_session(agent_id: str) -> None:
    _agent_sessions.pop(agent_id, None)


# ═══════════════════════════════════════════════════════════════════
# Declarative Agent Config Support (JSON/YAML)
# ═══════════════════════════════════════════════════════════════════

def load_agent_config(path: str) -> dict[str, Any]:
    ext = os.path.splitext(path)[1].lower()
    with open(path, "r", encoding="utf-8") as f:
        if ext == ".json":
            return json.load(f)
        elif ext in (".yaml", ".yml"):
            try:
                import yaml
                return yaml.safe_load(f)
            except ImportError:
                raise ImportError("PyYAML is required to load .yaml files")
        else:
            raise ValueError(f"Unsupported config format: {ext}")


def agent_config_to_profile(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": config.get("name", config.get("id", "unknown")),
        "description": config.get("description", ""),
        "color": config.get("color", "#ffffff"),
        "icon": config.get("icon", "robot"),
        "system_prompt": config.get("system_prompt", ""),
        "tools": config.get("tools", []),
    }


# ═══════════════════════════════════════════════════════════════════
# __all__
# ═══════════════════════════════════════════════════════════════════

__all__ = [
    # Classes
    "KeyManager",
    "AgentTerminalManager",
    "AgentDelegator",
    "AgentBusEnhanced",
    # Singleton accessors
    "get_key_manager",
    "get_terminal_manager",
    "get_delegator",
    "get_agent_bus_enhanced",
    # High-level tool functions
    "agent_spawn_and_track",
    "agent_delegate_with_terminal",
    "friday_should_delegate",
    "friday_parse_and_delegate",
    "friday_key_check",
    "friday_workflow_research_vuln_fix",
    "agent_bus_status",
    "agent_chain_research_vuln_fix",
    "friday_multi_agent_task",
    "close_all_agent_resources",
    # Tool descriptions
    "AGENT_TERMINAL_TOOL_DESCRIPTIONS",
    # OpenCode-style delegation depth tracking
    "get_delegation_depth",
    # Permission-based tool restriction
    "set_tool_ruleset",
    "get_allowed_tools_for_agent",
    # Delegation prompt crafting
    "friday_craft_delegation_prompt",
    "friday_delegate_with_prompt",
    # Session isolation
    "store_agent_session",
    "get_agent_session",
    "clear_agent_session",
    # Declarative agent config
    "load_agent_config",
    "agent_config_to_profile",
]
