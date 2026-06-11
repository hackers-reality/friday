"""FRIDAY Auto-Update System — git-pull based self-update with rollback."""
from __future__ import annotations
import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from friday._paths import PROJECT_ROOT, FRIDAY_MEMORY
from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

_UPDATE_STATE_PATH = Path(FRIDAY_MEMORY) / "update_state.json"
_UPDATE_HISTORY_PATH = Path(FRIDAY_MEMORY) / "update_history.jsonl"


def _load_state() -> dict:
    if _UPDATE_STATE_PATH.exists():
        try:
            return json.loads(_UPDATE_STATE_PATH.read_text())
        except Exception:
            pass
    return {"last_check": None, "last_update": None, "current_version": None, "update_available": False, "update_branch": "main"}


def _save_state(state: dict) -> None:
    _UPDATE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _UPDATE_STATE_PATH.write_text(json.dumps(state, indent=2))


def _log_history(entry: dict) -> None:
    _UPDATE_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _UPDATE_HISTORY_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def _run_git(*args: str, timeout: int = 30) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            ["git"] + list(args),
            capture_output=True, text=True, timeout=timeout,
            cwd=PROJECT_ROOT,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return -1, "", "git not found on PATH"
    except subprocess.TimeoutExpired:
        return -2, "", f"git command timed out after {timeout}s"


def check_version() -> str:
    """Return current FRIDAY version string."""
    try:
        from friday import __version__
        return __version__
    except ImportError:
        return "unknown"


def check_for_updates(branch: str = "main") -> str:
    """Check GitHub for newer commits without pulling."""
    state = _load_state()
    state["current_version"] = check_version()
    state["update_branch"] = branch

    rc, stdout, stderr = _run_git("fetch", "origin", branch, "--dry-run")
    if rc != 0:
        return json.dumps({"error": f"git fetch dry-run failed: {stderr}"})

    rc, local_commit, stderr = _run_git("rev-parse", "HEAD")
    rc2, remote_commit, stderr2 = _run_git("rev-parse", f"origin/{branch}")
    if rc != 0 or rc2 != 0:
        return json.dumps({"error": f"rev-parse failed: {stderr} {stderr2}"})

    if local_commit == remote_commit:
        state["update_available"] = False
        state["last_check"] = datetime.now().isoformat()
        _save_state(state)
        return json.dumps({"update_available": False, "version": state["current_version"], "message": "Already up to date"})

    rc, log_output, stderr = _run_git("log", f"{local_commit}..origin/{branch}", "--oneline", "-10")
    commits = [line.strip() for line in log_output.split("\n") if line.strip()] if rc == 0 else []

    state["update_available"] = True
    state["last_check"] = datetime.now().isoformat()
    state["remote_commit"] = remote_commit
    state["pending_commits"] = commits
    _save_state(state)

    return json.dumps({
        "update_available": True,
        "version": state["current_version"],
        "pending_commits": len(commits),
        "commits": commits[:10],
        "message": f"{len(commits)} new commit(s) available on {branch}",
    })


def apply_update(branch: str = "main", auto_stash: bool = True) -> str:
    """Pull latest changes from GitHub and apply them."""
    state = _load_state()
    state["current_version"] = check_version()
    state["update_branch"] = branch

    rc, stdout, stderr = _run_git("fetch", "origin", branch)
    if rc != 0:
        return json.dumps({"error": f"git fetch failed: {stderr}"})

    rc, local_commit, _ = _run_git("rev-parse", "HEAD")
    rc2, remote_commit, _ = _run_git("rev-parse", f"origin/{branch}")
    if rc != 0 or rc2 != 0:
        return json.dumps({"error": "rev-parse failed"})

    if local_commit == remote_commit:
        return json.dumps({"success": True, "message": "Already up to date", "version": check_version()})

    if auto_stash:
        _run_git("stash")

    rc, stdout, stderr = _run_git("pull", "--ff-only", "origin", branch)
    if rc != 0:
        if auto_stash:
            _run_git("stash", "pop")
        return json.dumps({"error": f"git pull failed: {stderr}"})

    if auto_stash:
        _run_git("stash", "pop")

    new_version = check_version()
    state["last_update"] = datetime.now().isoformat()
    state["update_available"] = False
    _save_state(state)

    _log_history({
        "timestamp": datetime.now().isoformat(),
        "action": "update",
        "from": local_commit[:8],
        "to": remote_commit[:8],
        "branch": branch,
        "version": new_version,
        "success": True,
    })

    return json.dumps({
        "success": True,
        "message": f"Updated from {local_commit[:8]} to {remote_commit[:8]}",
        "from_commit": local_commit[:8],
        "to_commit": remote_commit[:8],
        "version": new_version,
        "note": "Restart FRIDAY to apply changes" if "live.py" in stdout else "",
    })


def rollback(steps: int = 1) -> str:
    """Rollback to previous commit."""
    rc, stdout, stderr = _run_git("log", "--oneline", "-1")
    if rc != 0:
        return json.dumps({"error": f"git log failed: {stderr}"})
    current = stdout.split("\n")[0].split()[0] if stdout else ""

    rc, stdout, stderr = _run_git("reset", "--hard", f"HEAD~{steps}")
    if rc != 0:
        return json.dumps({"error": f"rollback failed: {stderr}"})

    rc, new_head, _ = _run_git("rev-parse", "--short", "HEAD")
    _log_history({
        "timestamp": datetime.now().isoformat(),
        "action": "rollback",
        "from": current[:8] if current else "?",
        "to": new_head.strip()[:8] if new_head else "?",
        "steps": steps,
    })
    return json.dumps({"success": True, "message": f"Rolled back {steps} commit(s)", "from": current[:8], "to": new_head.strip()[:8]})


def update_status() -> str:
    """Get full update system status."""
    state = _load_state()
    try:
        rc, branch, stderr = _run_git("rev-parse", "--abbrev-ref", "HEAD")
        git_branch = branch if rc == 0 else "unknown"
    except Exception:
        git_branch = "error"

    try:
        rc, commit, stderr = _run_git("rev-parse", "--short", "HEAD")
        git_commit = commit[:8] if rc == 0 else "unknown"
    except Exception:
        git_commit = "error"

    history = []
    if _UPDATE_HISTORY_PATH.exists():
        try:
            with _UPDATE_HISTORY_PATH.open() as f:
                history = [json.loads(line) for line in f if line.strip()][-5:]
        except Exception:
            pass

    return json.dumps({
        "version": check_version(),
        "branch": git_branch,
        "commit": git_commit,
        "last_check": state.get("last_check"),
        "last_update": state.get("last_update"),
        "update_available": state.get("update_available", False),
        "pending_commits": len(state.get("pending_commits", [])),
        "recent_history": history,
    }, indent=2)


def auto_update_tool(action: str = "status", branch: str = "main", steps: int = 1) -> str:
    """Auto-update tool: check, apply, rollback, status.

    Actions:
      status    — show update system status
      check     — check for updates without applying
      apply     — pull and apply latest changes
      rollback  — rollback N commits (default 1)
    """
    action_map = {
        "status": update_status,
        "check": lambda: check_for_updates(branch),
        "apply": lambda: apply_update(branch),
        "rollback": lambda: rollback(steps),
    }
    handler = action_map.get(action)
    if not handler:
        return json.dumps({"error": f"Unknown action: {action}. Use: status, check, apply, rollback"})
    try:
        return handler()
    except Exception as e:
        logger.exception("auto_update_tool failed")
        return json.dumps({"error": str(e)})
