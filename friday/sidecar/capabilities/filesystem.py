"""Filesystem capability for sidecar client."""
from __future__ import annotations

import os
from typing import Dict


class FilesystemHandler:
    BLOCKLIST = ["/etc/shadow", "C:\\Windows\\System32"]

    def _is_blocked(self, path: str) -> bool:
        for b in self.BLOCKLIST:
            if path.startswith(b):
                return True
        return False

    async def handle(self, action: str, params: Dict) -> Dict:
        path = params.get("path")
        if not path:
            return {"error": "path required"}
        if self._is_blocked(path):
            return {"error": "path is blocked"}
        if action == "list_dir":
            try:
                entries = os.listdir(path)
                return {"entries": entries}
            except Exception as e:
                return {"error": str(e)}
        if action == "read_file":
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return {"content": f.read()}
            except Exception as e:
                return {"error": str(e)}
        if action == "write_file":
            content = params.get("content", "")
            try:
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                return {"ok": True}
            except Exception as e:
                return {"error": str(e)}
        if action == "delete_file":
            try:
                os.remove(path)
                return {"ok": True}
            except Exception as e:
                return {"error": str(e)}
        return {"error": "unknown action"}
