from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict


def _normalize(path: str) -> str:
    return str(Path(path).expanduser().resolve())


def _blocked_path(path: str) -> bool:
    p = _normalize(path).lower()
    blocked = {
        "/etc/shadow",
        "/etc/sudoers",
        "/root",
        "c:\\windows\\system32",
        "c:\\windows\\system32\\config\\sam",
    }
    for item in blocked:
        if p.startswith(item.lower()):
            return True
    return False


async def handle(action: str, params: Dict[str, Any]) -> dict:
    path = str(params.get("path", "")).strip()
    if not path:
        return {"error": "path required"}
    if _blocked_path(path):
        return {"error": "path is blocked"}

    p = _normalize(path)
    if action == "list_dir":
        try:
            entries = []
            for name in os.listdir(p):
                item_path = os.path.join(p, name)
                entries.append({"name": name, "is_dir": os.path.isdir(item_path), "size": os.path.getsize(item_path) if os.path.isfile(item_path) else 0})
            return {"entries": entries}
        except Exception as exc:
            return {"error": str(exc)}

    if action == "read_file":
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                return {"content": f.read()}
        except Exception as exc:
            return {"error": str(exc)}

    if action == "write_file":
        content = str(params.get("content", ""))
        try:
            os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
            return {"ok": True}
        except Exception as exc:
            return {"error": str(exc)}

    if action == "delete_file":
        try:
            os.remove(p)
            return {"ok": True}
        except Exception as exc:
            return {"error": str(exc)}

    return {"error": f"unsupported filesystem action: {action}"}
