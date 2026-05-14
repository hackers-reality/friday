"""Friday Context System — auto-loads project context files.
Inspired by CLAUDE.md / AGENTS.md conventions.
Provides persistent project-level instructions and context to FRIDAY."""

from __future__ import annotations
import os
import glob
from datetime import datetime
from typing import Optional

from friday._paths import PROJECT_ROOT

_CONTEXT_DIR = os.path.join(PROJECT_ROOT, ".friday_context")
_CONTEXT_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "FRIDAY.md",
    ".friday",
    "CONTEXT.md",
]


def _find_context_files() -> list:
    """Find all context files in the project root and .friday_context/ dir."""
    found = []
    for fname in _CONTEXT_FILES:
        path = os.path.join(PROJECT_ROOT, fname)
        if os.path.isfile(path):
            found.append(path)
    if os.path.isdir(_CONTEXT_DIR):
        for f in sorted(glob.glob(os.path.join(_CONTEXT_DIR, "*.md"))):
            found.append(f)
        for f in sorted(glob.glob(os.path.join(_CONTEXT_DIR, "*.txt"))):
            found.append(f)
    return found


def _read_file(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return None


def load_context_files() -> str:
    """Load all context files and return aggregated content."""
    files = _find_context_files()
    if not files:
        return ""
    sections = []
    for path in files:
        content = _read_file(path)
        if content:
            name = os.path.basename(path)
            sections.append(f"=== {name} ===\n{content}")
    return "\n\n".join(sections)


def _save_context_file(filename: str, content: str) -> str:
    """Save content to a context file."""
    if filename in _CONTEXT_FILES:
        path = os.path.join(PROJECT_ROOT, filename)
    else:
        os.makedirs(_CONTEXT_DIR, exist_ok=True)
        if not filename.endswith(".md"):
            filename += ".md"
        path = os.path.join(_CONTEXT_DIR, filename)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"[OK] Saved to {os.path.basename(path)}"
    except Exception as e:
        return f"[FAIL] Could not save: {e}"


def context_tool(action: str = "list", **kwargs) -> str:
    """Manage project context files. Actions: list, show, add, delete, reload.
    Context files provide persistent instructions and project knowledge."""
    if action == "list":
        files = _find_context_files()
        if not files:
            return "No context files found. Create AGENTS.md or CLAUDE.md in the project root."
        lines = ["### CONTEXT FILES"]
        for i, path in enumerate(files, 1):
            name = os.path.basename(path)
            size = os.path.getsize(path) if os.path.exists(path) else 0
            modified = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M") if os.path.exists(path) else "?"
            lines.append(f"  {i}. {name} ({size}b, modified {modified})")
        return "\n".join(lines)

    elif action == "show":
        name = kwargs.get("name", "")
        files = _find_context_files()
        if name:
            target = [f for f in files if name in f]
        else:
            target = files
        if not target:
            return f"No matching context files for '{name}'."
        content = _read_file(target[0])
        if content:
            return f"### {os.path.basename(target[0])}\n{content[:2000]}"
        return "[INFO] File is empty."

    elif action == "add":
        name = kwargs.get("name", "context")
        content = kwargs.get("content", "")
        if not content:
            return "[FAIL] Content is required."
        return _save_context_file(name, content)

    elif action == "delete":
        name = kwargs.get("name", "")
        files = _find_context_files()
        target = None
        if name:
            target = next((f for f in files if name in f), None)
        if not target:
            return f"[INFO] No context file matching '{name}'."
        try:
            os.remove(target)
            return f"[OK] Removed {os.path.basename(target)}"
        except Exception as e:
            return f"[FAIL] Could not remove: {e}"

    elif action == "reload":
        content = load_context_files()
        if content:
            return f"[OK] Loaded {len(_find_context_files())} context file(s). Content:\n\n{content[:1500]}"
        return "[INFO] No context files found."

    else:
        return f"[FAIL] Unknown action: {action}"
