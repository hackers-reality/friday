"""Friday Self-Improvement Pipeline — propose, review, apply code changes.
FRIDAY reads her own source, proposes improvements, user approves/rejects."""

from __future__ import annotations
import os
import json
import difflib
import subprocess
from datetime import datetime
from typing import Optional

from friday._paths import FRIDAY_MEMORY

_PENDING_FILE = os.path.join(FRIDAY_MEMORY, "pending_changes.json")


def _load_pending() -> list:
    if os.path.exists(_PENDING_FILE):
        try:
            with open(_PENDING_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_pending(changes: list):
    os.makedirs(os.path.dirname(_PENDING_FILE), exist_ok=True)
    try:
        with open(_PENDING_FILE, "w") as f:
            json.dump(changes, f, indent=2)
    except Exception:
        pass


def _compute_diff(original: str, new: str) -> str:
    return "\n".join(difflib.unified_diff(
        original.splitlines(keepends=True),
        new.splitlines(keepends=True),
        lineterm="",
    ))


def _git_commit(file_path: str, description: str) -> str:
    try:
        subprocess.run(["git", "add", file_path], capture_output=True, text=True, timeout=10)
        r = subprocess.run(
            ["git", "commit", "-m", f"[Self-Improve] {description[:80]}"],
            capture_output=True, text=True, timeout=15,
        )
        return r.stdout.strip() or r.stderr.strip()
    except Exception as e:
        return str(e)


def propose(file_path: str, description: str, new_content: str) -> str:
    """Propose a change to a file. Returns the change ID."""
    if not os.path.exists(file_path):
        return f"[FAIL] File not found: {file_path}"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            original = f.read()
    except Exception as e:
        return f"[FAIL] Could not read {file_path}: {e}"

    if original == new_content:
        return "[INFO] No changes to propose — content is identical."

    change_id = f"imp_{int(datetime.now().timestamp())}"
    diff = _compute_diff(original, new_content)

    pending = _load_pending()
    pending.append({
        "id": change_id,
        "file_path": file_path,
        "description": description,
        "original": original,
        "new_content": new_content,
        "diff": diff[:2000],
        "status": "proposed",
        "created": datetime.now().isoformat(),
    })
    _save_pending(pending)
    return f"[OK] Proposed change '{change_id}' for {file_path}\n{diff[:1000]}"


def list_pending() -> str:
    pending = _load_pending()
    if not pending:
        return "No pending changes."
    lines = ["### PENDING SELF-IMPROVEMENTS"]
    for c in pending:
        status = c.get("status", "proposed")
        lines.append(f"  [{c['id']}] {c.get('description', '?')[:80]}")
        lines.append(f"       File: {c.get('file_path', '?')} | Status: {status}")
    return "\n".join(lines)


def show_diff(change_id: str) -> str:
    pending = _load_pending()
    for c in pending:
        if c["id"] == change_id:
            diff = c.get("diff", "")
            return f"### DIFF for {change_id}\n{c.get('description', '?')}\n\n{diff[:3000]}"
    return f"[FAIL] No pending change: {change_id}"


def apply_change(change_id: str, commit: bool = True) -> str:
    """Apply an approved change. Writes file + optionally commits."""
    pending = _load_pending()
    for c in pending:
        if c["id"] == change_id:
            if c.get("status") == "applied":
                return f"[INFO] Change '{change_id}' already applied."
            file_path = c["file_path"]
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(c["new_content"])
            except Exception as e:
                return f"[FAIL] Could not write {file_path}: {e}"
            c["status"] = "applied"
            c["applied_at"] = datetime.now().isoformat()
            _save_pending(pending)
            result = f"[OK] Applied change '{change_id}' to {file_path}"
            if commit:
                git_result = _git_commit(file_path, c.get("description", "self-improvement"))
                result += f"\nGit: {git_result[:200]}"
            return result
    return f"[FAIL] No pending change: {change_id}"


def reject_change(change_id: str) -> str:
    """Reject a proposed change."""
    pending = _load_pending()
    for c in pending:
        if c["id"] == change_id:
            c["status"] = "rejected"
            c["rejected_at"] = datetime.now().isoformat()
            _save_pending(pending)
            return f"[OK] Rejected change '{change_id}'"
    return f"[FAIL] No pending change: {change_id}"


def status() -> str:
    pending = _load_pending()
    proposed = sum(1 for c in pending if c.get("status") == "proposed")
    applied = sum(1 for c in pending if c.get("status") == "applied")
    rejected = sum(1 for c in pending if c.get("status") == "rejected")
    return (
        f"Self-Improvement Pipeline:\n"
        f"  Proposed: {proposed}\n"
        f"  Applied: {applied}\n"
        f"  Rejected: {rejected}\n"
        f"  Total: {len(pending)}"
    )


def self_improve_tool(action: str = "status", **kwargs) -> str:
    """Self-improvement pipeline: propose, review, and apply code changes.
    Actions: propose (suggest change), list (show pending), diff (show diff),
    apply (approve + write), reject (discard), status."""
    try:
        if action == "propose":
            fp = kwargs.get("file_path", "")
            desc = kwargs.get("description", "")
            content = kwargs.get("content", "")
            if not fp or not desc or not content:
                return "[FAIL] file_path, description, and content required."
            return propose(fp, desc, content)
        elif action == "list":
            return list_pending()
        elif action == "diff":
            cid = kwargs.get("id", "")
            if not cid:
                return "[FAIL] id required."
            return show_diff(cid)
        elif action == "apply":
            cid = kwargs.get("id", "")
            commit = kwargs.get("commit", True)
            if not cid:
                return "[FAIL] id required."
            return apply_change(cid, commit=commit)
        elif action == "reject":
            cid = kwargs.get("id", "")
            if not cid:
                return "[FAIL] id required."
            return reject_change(cid)
        elif action == "status":
            return status()
        else:
            return f"[FAIL] Unknown action: {action}"
    except Exception as e:
        return f"[FAIL] Self-improve error: {e}"
