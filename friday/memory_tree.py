"""
FRIDAY Memory Tree — persistent local Markdown knowledge base.
Generates and maintains structured memory as editable Markdown files under friday_memory/memory_tree/.

Inspired by OpenHuman's Memory Tree concept: compressed local knowledge wiki
with sources, confidence, freshness, and backlinks.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date
import json
import os
import re
import threading

from friday._paths import FRIDAY_MEMORY

_MEMORY_TREE_DIR = os.path.join(FRIDAY_MEMORY, "memory_tree")
_DAILY_NOTES_DIR = os.path.join(_MEMORY_TREE_DIR, "daily_notes")
_LOCK = threading.Lock()

# ─── Core Files ──────────────────────────────────────────

CORE_FILES = {
    "index.md": "Memory Tree index — map of all knowledge files",
    "people.md": "People I know — relationships, roles, preferences",
    "projects.md": "Projects I'm working on — goals, status, notes",
    "goals.md": "My goals and OKRs — tracked objectives",
    "preferences.md": "My preferences — communication, tools, habits, style",
    "tools.md": "Tools and systems I use — configs, tips",
    "timeline.md": "Important events and changes over time",
    "current_context.md": "Current active context — what I'm doing right now",
}

BACKLINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")


def _ensure_dirs():
    os.makedirs(_MEMORY_TREE_DIR, exist_ok=True)
    os.makedirs(_DAILY_NOTES_DIR, exist_ok=True)


def _resolve_path(filename: str) -> str:
    if filename.endswith(".md"):
        return os.path.join(_MEMORY_TREE_DIR, filename)
    return os.path.join(_MEMORY_TREE_DIR, f"{filename}.md")


def _read_file(path: str) -> str:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def _write_file(path: str, content: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _now() -> str:
    return datetime.now().isoformat()[:19]


def _today() -> str:
    return date.today().isoformat()


# ─── Index Building ──────────────────────────────────────

def build_index() -> str:
    """Build or rebuild index.md with links to all memory tree files."""
    _ensure_dirs()
    files = {}
    for fname in sorted(os.listdir(_MEMORY_TREE_DIR)):
        if fname.endswith(".md") and fname != "index.md":
            path = os.path.join(_MEMORY_TREE_DIR, fname)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            # Extract first heading and line count
            first_line = content.strip().split("\n")[0] if content.strip() else "No content"
            line_count = len(content.strip().split("\n")) if content.strip() else 0
            files[fname] = {
                "heading": first_line.lstrip("# ").strip(),
                "lines": line_count,
                "modified": datetime.fromtimestamp(os.path.getmtime(path)).isoformat()[:19],
            }

    # Also list daily notes
    daily_notes = []
    if os.path.exists(_DAILY_NOTES_DIR):
        for fname in sorted(os.listdir(_DAILY_NOTES_DIR), reverse=True)[:30]:
            if fname.endswith(".md"):
                daily_notes.append(fname.replace(".md", ""))

    lines = [
        f"# Memory Tree Index",
        f"",
        f"_Generated: {_now()}_",
        f"",
        f"## Knowledge Files",
        f"",
        f"| File | Description | Lines | Last Modified |",
        f"|------|-------------|-------|---------------|",
    ]
    for fname, info in sorted(files.items()):
        desc = CORE_FILES.get(fname, "—")
        lines.append(f"| [[{fname.replace('.md','')}]] | {desc} | {info['lines']} | {info['modified']} |")

    lines.extend([
        "",
        f"## Daily Notes ({len(daily_notes)} total)",
        "",
    ])
    for d in daily_notes[:10]:
        lines.append(f"- [[daily_notes/{d}]]")

    lines.extend([
        "",
        "## Backlinks",
        "",
        "To create a backlink, use [[PageName]] in any file.",
    ])

    content = "\n".join(lines)
    _write_file(_resolve_path("index.md"), content)
    return content


# ─── Daily Notes ─────────────────────────────────────────

def get_daily_note(dt: Optional[str] = None) -> str:
    """Get or create today's daily note."""
    dt = dt or _today()
    path = os.path.join(_DAILY_NOTES_DIR, f"{dt}.md")
    if os.path.exists(path):
        return _read_file(path)

    content = (
        f"# Daily Note — {dt}\n"
        f"\n"
        f"_Created: {_now()}_\n"
        f"\n"
        f"## Today's Focus\n"
        f"\n"
        f"\n"
        f"## Tasks\n"
        f"- [ ] \n"
        f"\n"
        f"## Notes\n"
        f"\n"
        f"\n"
        f"## Reflections\n"
        f"\n"
    )
    _write_file(path, content)
    return content


def list_daily_notes(limit: int = 30) -> List[str]:
    """List recent daily notes."""
    _ensure_dirs()
    notes = []
    if os.path.exists(_DAILY_NOTES_DIR):
        for fname in sorted(os.listdir(_DAILY_NOTES_DIR), reverse=True)[:limit]:
            if fname.endswith(".md"):
                notes.append(fname.replace(".md", ""))
    return notes


# ─── Read / Write / Search ───────────────────────────────

def read_page(name: str) -> Optional[str]:
    """Read a memory tree page by name."""
    path = _resolve_path(name)
    if os.path.exists(path):
        return _read_file(path)
    # Check daily notes
    dpath = os.path.join(_DAILY_NOTES_DIR, f"{name}.md")
    if os.path.exists(dpath):
        return _read_file(dpath)
    return None


def write_page(name: str, content: str) -> str:
    """Write content to a memory tree page."""
    path = _resolve_path(name)
    _write_file(path, content)
    build_index()
    return f"[OK] Written to {path}"


def search_memory_tree(query: str) -> List[Dict[str, Any]]:
    """Full-text search across all memory tree files."""
    _ensure_dirs()
    results = []
    query_lower = query.lower()

    all_files = []
    for fname in os.listdir(_MEMORY_TREE_DIR):
        if fname.endswith(".md"):
            all_files.append((os.path.join(_MEMORY_TREE_DIR, fname), fname))
    if os.path.exists(_DAILY_NOTES_DIR):
        for fname in os.listdir(_DAILY_NOTES_DIR):
            if fname.endswith(".md"):
                all_files.append((os.path.join(_DAILY_NOTES_DIR, fname), f"daily_notes/{fname}"))

    for fpath, fname in all_files:
        content = _read_file(fpath)
        if query_lower in content.lower():
            # Find matching lines with context
            matches = []
            for i, line in enumerate(content.split("\n")):
                if query_lower in line.lower():
                    matches.append({
                        "line": i + 1,
                        "text": line.strip()[:150],
                    })
            if matches:
                results.append({
                    "file": fname,
                    "matches": len(matches),
                    "snippets": matches[:5],
                })

    return sorted(results, key=lambda r: -r["matches"])


def extract_backlinks(content: str) -> List[str]:
    """Extract [[PageName]] backlinks from content."""
    return BACKLINK_PATTERN.findall(content)


# ─── Auto-Update from Memory Profile ─────────────────────

def update_from_profile() -> str:
    """Sync profile data into memory tree pages."""
    _ensure_dirs()
    profile_path = os.path.join(FRIDAY_MEMORY, "user_profile.json")
    if not os.path.exists(profile_path):
        return "[FAIL] No profile found"

    with open(profile_path, "r") as f:
        profile = json.load(f)

    changes = []

    # People
    people_content = "# People I Know\n\n"
    if profile.get("name"):
        people_content += f"- **Me**: {profile['name']}"
        if profile.get("age"):
            people_content += f" ({profile['age']})"
        if profile.get("location"):
            people_content += f" — {profile['location']}"
        people_content += "\n"
    people_content += "\n_Source: user_profile.json_\n"
    _write_file(_resolve_path("people.md"), people_content)
    changes.append("people.md")

    # Preferences
    prefs = []
    for field in ("communication_style", "preferences", "personality", "favorites"):
        items = profile.get(field, [])
        for item in items if isinstance(items, list) else []:
            if isinstance(item, dict) and "item" in item:
                confidence = item.get("_confidence", item.get("confidence", 0))
                prefs.append(f"- {item['item']} (confidence: {confidence})")
    prefs_content = "# Preferences\n\n" + "\n".join(prefs) if prefs else "# Preferences\n\n_No preferences extracted yet._\n"
    prefs_content += "\n\n_Source: user_profile.json_\n"
    _write_file(_resolve_path("preferences.md"), prefs_content)
    changes.append("preferences.md")

    # Goals
    goals = profile.get("goals", [])
    goals_content = "# Goals & OKRs\n\n"
    if goals and isinstance(goals, list):
        for g in goals:
            if isinstance(g, dict) and "item" in g:
                goals_content += f"- [ ] {g['item']}\n"
    else:
        goals_content += "_No goals found in profile._\n"
    goals_content += "\n_Source: user_profile.json_\n"
    _write_file(_resolve_path("goals.md"), goals_content)
    changes.append("goals.md")

    # Projects (from goals with categories)
    projects = profile.get("professional_skills", [])
    proj_content = "# Projects\n\n"
    if projects and isinstance(projects, list):
        for p in projects:
            if isinstance(p, dict) and "item" in p:
                proj_content += f"- {p['item']}\n"
    proj_content += "\n_Source: user_profile.json_\n"
    _write_file(_resolve_path("projects.md"), proj_content)
    changes.append("projects.md")

    # Tools / Tech Stack
    tech = profile.get("tech_stack", [])
    tools_content = "# Tools & Systems\n\n"
    if tech and isinstance(tech, list):
        for t in tech:
            if isinstance(t, dict) and "item" in t:
                tools_content += f"- {t['item']}\n"
    tools_content += "\n_Source: user_profile.json_\n"
    _write_file(_resolve_path("tools.md"), tools_content)
    changes.append("tools.md")

    build_index()
    return f"[OK] Updated {len(changes)} pages: {', '.join(changes)}"


# ─── Context Injection ───────────────────────────────────

def build_memory_tree_context() -> str:
    """Build a concise context block for system prompt injection."""
    _ensure_dirs()
    ctx_parts = []

    # Current context
    cc = read_page("current_context.md")
    if cc and len(cc.strip()) > 20:
        ctx_parts.append(f"[Current Context]\n{cc.strip()[:500]}\n")

    # Today's daily note
    dn = get_daily_note()
    if dn:
        lines = dn.strip().split("\n")
        focus_lines = [l for l in lines if l.startswith("## Today's Focus") or l.startswith("-")]
        if focus_lines:
            ctx_parts.append(f"[Today's Focus]\n" + "\n".join(focus_lines[:5]))

    # Key backlinks from current context
    if cc:
        backlinks = extract_backlinks(cc)
        for link in backlinks[:3]:
            page = read_page(link)
            if page:
                summary = "\n".join(page.strip().split("\n")[:5])
                ctx_parts.append(f"[{link}]\n{summary}\n")

    return "\n".join(ctx_parts) if ctx_parts else ""


# ─── Tool Function ───────────────────────────────────────

def memory_tree_tool(action: str = "status", **kwargs) -> str:
    """FRIDAY tool: Memory Tree — persistent Markdown knowledge base.

    Actions:
        status        - Show memory tree overview
        build_index   - Rebuild the index page
        read          - Read a page by name
        write         - Write content to a page
        search        - Search across all pages
        daily_note    - Get or create today's daily note
        daily_notes   - List recent daily notes
        update        - Sync from user profile into memory tree
        context       - Build context block for LLM injection
    """
    action = action.lower()

    if action == "status":
        _ensure_dirs()
        file_count = len([f for f in os.listdir(_MEMORY_TREE_DIR) if f.endswith(".md")])
        daily_count = len(list_daily_notes(999))
        index = read_page("index.md")
        first_lines = "\n".join(index.split("\n")[:5]) if index else "No index"
        return (
            f"### MEMORY TREE\n\n"
            f"Location: {_MEMORY_TREE_DIR}\n"
            f"Knowledge pages: {file_count}\n"
            f"Daily notes: {daily_count}\n"
            f"\n{first_lines}"
        )

    if action == "build_index":
        build_index()
        return "[OK] Index rebuilt"

    if action == "read":
        name = kwargs.get("name", "")
        if not name:
            return "[FAIL] Provide 'name' of page to read."
        content = read_page(name)
        if content is None:
            return f"[FAIL] Page '{name}' not found."
        return content

    if action == "write":
        name = kwargs.get("name", "")
        content = kwargs.get("content", "")
        if not name or not content:
            return "[FAIL] Provide both 'name' and 'content'."
        return write_page(name, content)

    if action == "search":
        query = kwargs.get("query", "")
        if not query:
            return "[FAIL] Provide 'query' to search."
        results = search_memory_tree(query)
        if not results:
            return f"[OK] No results for '{query}'."
        lines = [f"### Search Results: '{query}' ({len(results)} files)\n"]
        for r in results:
            lines.append(f"\n**{r['file']}** ({r['matches']} matches):")
            for s in r["snippets"][:3]:
                lines.append(f"  L{s['line']}: {s['text']}")
        return "\n".join(lines)

    if action == "daily_note":
        dt = kwargs.get("date", _today())
        return get_daily_note(dt)

    if action == "daily_notes":
        notes = list_daily_notes()
        if not notes:
            return "[OK] No daily notes yet."
        return "### Recent Daily Notes\n" + "\n".join(f"- {n}" for n in notes)

    if action == "update":
        return update_from_profile()

    if action == "context":
        ctx = build_memory_tree_context()
        if not ctx:
            return ""
        return ctx

    return f"[FAIL] Unknown action: {action}. Available: status, build_index, read, write, search, daily_note, daily_notes, update, context"
