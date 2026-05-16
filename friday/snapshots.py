"""
Friday Snapshot / Time Travel System — capture and restore file and memory snapshots.

Allows FRIDAY to snapshot state before risky operations (writes, deletes, memory repairs)
and restore or diff later.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import os
import shutil
import hashlib

from friday._paths import FRIDAY_MEMORY

_SNAPSHOTS_DIR = os.path.join(FRIDAY_MEMORY, "snapshots")
_SNAPSHOTS_INDEX = os.path.join(_SNAPSHOTS_DIR, "_index.json")


def _ensure_snapshots_dir():
    os.makedirs(_SNAPSHOTS_DIR, exist_ok=True)


def _load_index() -> dict:
    """Load the snapshots index, or return an empty structure."""
    _ensure_snapshots_dir()
    if os.path.exists(_SNAPSHOTS_INDEX):
        try:
            with open(_SNAPSHOTS_INDEX, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"snapshots": [], "next_id": 1}


def _save_index(index: dict) -> None:
    _ensure_snapshots_dir()
    with open(_SNAPSHOTS_INDEX, "w") as f:
        json.dump(index, f, indent=4)


def _compute_hash(filepath: str) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def create_snapshot(source_path: str, label: str = "", metadata: dict = None) -> dict:
    """
    Create a snapshot of a file or directory.

    Args:
        source_path: Path to the file or directory to snapshot.
        label: Human-readable label for the snapshot.
        metadata: Optional additional metadata dict.

    Returns:
        dict with snapshot id, path, label, timestamp, etc.
    """
    _ensure_snapshots_dir()
    source_path = os.path.abspath(source_path)
    if not os.path.exists(source_path):
        return {"error": f"Source not found: {source_path}"}

    index = _load_index()
    snap_id = index["next_id"]
    index["next_id"] += 1

    timestamp = datetime.now().isoformat()
    snap_dir = os.path.join(_SNAPSHOTS_DIR, f"snap_{snap_id:06d}")
    os.makedirs(snap_dir, exist_ok=True)

    entry = {
        "id": snap_id,
        "label": label or os.path.basename(source_path),
        "source": source_path,
        "timestamp": timestamp,
        "type": "file" if os.path.isfile(source_path) else "directory",
        "size": 0,
        "hash": "",
        "metadata": metadata or {},
    }

    try:
        if os.path.isfile(source_path):
            dest = os.path.join(snap_dir, os.path.basename(source_path))
            shutil.copy2(source_path, dest)
            entry["hash"] = _compute_hash(dest)
            entry["size"] = os.path.getsize(dest)
            entry["dest"] = dest
        elif os.path.isdir(source_path):
            dest = os.path.join(snap_dir, os.path.basename(source_path))
            shutil.copytree(source_path, dest, dirs_exist_ok=True)
            # Compute total size
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(dest):
                for fn in filenames:
                    fp = os.path.join(dirpath, fn)
                    if os.path.isfile(fp):
                        total_size += os.path.getsize(fp)
            entry["size"] = total_size
            entry["dest"] = dest
        else:
            return {"error": f"Unsupported source type: {source_path}"}
    except Exception as e:
        return {"error": str(e)}

    index["snapshots"].append(entry)
    _save_index(index)
    return {"success": True, "id": snap_id, "timestamp": timestamp, "dest": dest}


def restore_snapshot(snap_id: int, target_path: str = "") -> dict:
    """
    Restore a snapshot to its original location or a custom target path.

    Args:
        snap_id: Snapshot ID to restore.
        target_path: Optional custom restore path. Defaults to original source.

    Returns:
        dict with success/error, and path info.
    """
    index = _load_index()
    entry = None
    for e in index["snapshots"]:
        if e["id"] == snap_id:
            entry = e
            break

    if not entry:
        return {"error": f"Snapshot {snap_id} not found"}

    source = entry.get("dest", "")
    if not source or not os.path.exists(source):
        return {"error": f"Snapshot data not found at {source}"}

    target = target_path or entry.get("source", "")
    if not target:
        return {"error": "No target path specified"}

    try:
        # Backup current target if it exists
        if os.path.exists(target):
            backup_path = target + ".snapbak"
            if os.path.exists(backup_path):
                os.remove(backup_path)
            os.rename(target, backup_path)

        # Restore
        if entry["type"] == "file":
            os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
            shutil.copy2(source, target)
        elif entry["type"] == "directory":
            if os.path.exists(target):
                shutil.rmtree(target)
            shutil.copytree(source, target, dirs_exist_ok=True)

        return {"success": True, "restored_to": target, "from": source}
    except Exception as e:
        return {"error": str(e)}


def diff_snapshot(snap_id: int) -> dict:
    """
    Show differences between a snapshot and its current file.

    Args:
        snap_id: Snapshot ID.

    Returns:
        dict with "changed", "added", "removed" lists, or "identical".
    """
    index = _load_index()
    entry = None
    for e in index["snapshots"]:
        if e["id"] == snap_id:
            entry = e
            break

    if not entry:
        return {"error": f"Snapshot {snap_id} not found"}

    snapshot_path = entry.get("dest", "")
    current_path = entry.get("source", "")
    if not snapshot_path or not os.path.exists(snapshot_path):
        return {"error": "Snapshot data not found"}
    if not current_path or not os.path.exists(current_path):
        return {"error": "Current file not found", "info": entry.get("source", "")}

    # File-level diff
    if entry["type"] == "file":
        snap_hash = _compute_hash(snapshot_path)
        curr_hash = _compute_hash(current_path)
        if snap_hash == curr_hash:
            return {"status": "identical"}
        return {"status": "changed", "snapshot": snapshot_path, "current": current_path}

    # Directory-level diff
    snap_files = set()
    curr_files = set()

    for dirpath, dirnames, filenames in os.walk(snapshot_path):
        for fn in filenames:
            rel = os.path.relpath(os.path.join(dirpath, fn), snapshot_path)
            snap_files.add(rel)

    for dirpath, dirnames, filenames in os.walk(current_path):
        for fn in filenames:
            rel = os.path.relpath(os.path.join(dirpath, fn), current_path)
            curr_files.add(rel)

    removed = snap_files - curr_files
    added = curr_files - snap_files
    changed = []
    common = snap_files & curr_files
    for f in common:
        snap_f = os.path.join(snapshot_path, f)
        curr_f = os.path.join(current_path, f)
        if os.path.isfile(snap_f) and os.path.isfile(curr_f):
            if _compute_hash(snap_f) != _compute_hash(curr_f):
                changed.append(f)

    return {
        "status": "different" if (removed or added or changed) else "identical",
        "added": sorted(added),
        "removed": sorted(removed),
        "changed": sorted(changed),
    }


def list_snapshots(limit: int = 50) -> list:
    """List snapshots, newest first."""
    index = _load_index()
    snaps = sorted(index["snapshots"], key=lambda x: x.get("timestamp", ""), reverse=True)
    return snaps[:limit]


def snapshot_tool(action: str = "list", **kwargs) -> str:
    """
    Friday tool for snapshot management.
    Actions: list, create, restore, diff, info.
    """
    if action == "list":
        snaps = list_snapshots()
        if not snaps:
            return "[OK] No snapshots yet."
        lines = ["### SNAPSHOTS\n"]
        for s in snaps:
            lines.append(
                f"  [{s['id']}] {s.get('label','?')} ({s.get('type','?')}) "
                f"- {s.get('timestamp','')[:19]}"
            )
        lines.append(f"\nTotal: {len(snaps)} snapshots")
        return "\n".join(lines)

    if action == "create":
        source = kwargs.get("path", "")
        if not source:
            return "[FAIL] Provide 'path' to snapshot."
        if not os.path.exists(source):
            return f"[FAIL] Path not found: {source}"
        label = kwargs.get("label", "")
        result = create_snapshot(source, label=label)
        if "error" in result:
            return f"[FAIL] {result['error']}"
        return f"[OK] Snapshot #{result['id']} created: {result.get('dest','')}"

    if action == "restore":
        snap_id = kwargs.get("id", None)
        if snap_id is None:
            return "[FAIL] Provide 'id' of snapshot to restore."
        try:
            snap_id = int(snap_id)
        except (TypeError, ValueError):
            return "[FAIL] id must be an integer."
        target = kwargs.get("target", "")
        result = restore_snapshot(snap_id, target_path=target)
        if "error" in result:
            return f"[FAIL] {result['error']}"
        return f"[OK] Snapshot #{snap_id} restored to {result.get('restored_to','?')}"

    if action == "diff":
        snap_id = kwargs.get("id", None)
        if snap_id is None:
            return "[FAIL] Provide 'id' of snapshot to diff."
        try:
            snap_id = int(snap_id)
        except (TypeError, ValueError):
            return "[FAIL] id must be an integer."
        result = diff_snapshot(snap_id)
        if "error" in result:
            return f"[FAIL] {result['error']}"
        if result.get("status") == "identical":
            return f"[OK] Snapshot #{snap_id} is identical to current state."
        lines = [f"### SNAPSHOT #{snap_id} DIFF\n"]
        if result.get("added"):
            lines.append(f"  [ADDED] {', '.join(result['added'][:10])}")
        if result.get("removed"):
            lines.append(f"  [REMOVED] {', '.join(result['removed'][:10])}")
        if result.get("changed"):
            lines.append(f"  [CHANGED] {', '.join(result['changed'][:10])}")
        if not result.get("added") and not result.get("removed") and not result.get("changed"):
            lines.append("  (content changed - use file comparison)")
        return "\n".join(lines)

    if action == "info":
        snap_id = kwargs.get("id", None)
        if snap_id is None:
            return "[FAIL] Provide 'id'."
        try:
            snap_id = int(snap_id)
        except (TypeError, ValueError):
            return "[FAIL] id must be an integer."
        index = _load_index()
        for e in index["snapshots"]:
            if e["id"] == snap_id:
                lines = [f"### SNAPSHOT #{snap_id}\n"]
                for k, v in e.items():
                    lines.append(f"  {k}: {v}")
                return "\n".join(lines)
        return f"[FAIL] Snapshot #{snap_id} not found."

    return f"Unknown action: {action}. Available: list, create, restore, diff, info"
