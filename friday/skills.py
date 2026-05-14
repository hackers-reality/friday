"""Friday Skills System — self-improving procedural memory.
Inspired by Hermes Agent's skills system. Saves successful workflows
as reusable skills that load automatically in future sessions."""

from __future__ import annotations
import os
import json
import re
from datetime import datetime
from typing import Optional

from friday._paths import FRIDAY_MEMORY

_SKILLS_FILE = os.path.join(FRIDAY_MEMORY, "skills.json")
_MAX_SKILLS = 100


def _load() -> list:
    if os.path.exists(_SKILLS_FILE):
        try:
            with open(_SKILLS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save(skills: list):
    os.makedirs(os.path.dirname(_SKILLS_FILE), exist_ok=True)
    try:
        with open(_SKILLS_FILE, "w") as f:
            json.dump(skills[-_MAX_SKILLS:], f, indent=2)
    except Exception:
        pass


def skills_tool(action: str = "list", **kwargs) -> str:
    """Manage procedural skills. Actions: list, add, search, delete, stats, auto_create.
    Skills are reusable procedures that Friday learns from experience.
    """
    skills = _load()

    if action == "list":
        if not skills:
            return "No skills yet. Skills are created when I solve complex problems."
        lines = ["### SKILLS"]
        for i, s in enumerate(skills[-20:], 1):
            tags = ", ".join(s.get("tags", []))
            lines.append(
                f"  {i}. {s.get('name', 'Unnamed')}\n"
                f"     Trigger: {s.get('trigger', 'N/A')}\n"
                f"     Used: {s.get('use_count', 0)}x | Tags: {tags or 'none'}"
            )
        return "\n".join(lines)

    elif action == "add":
        name = kwargs.get("name", "")
        steps = kwargs.get("steps", "")
        trigger = kwargs.get("trigger", "")
        tags = kwargs.get("tags", "")

        if not name or not steps:
            return "[FAIL] Skill name and steps are required."

        skill = {
            "id": f"skill_{len(skills) + 1}_{int(datetime.now().timestamp())}",
            "name": name,
            "steps": steps,
            "trigger": trigger,
            "tags": [t.strip() for t in tags.split(",") if t.strip()],
            "created": datetime.now().isoformat(),
            "use_count": 0,
            "last_used": None,
            "success_rate": 1.0,
        }
        skills.append(skill)
        _save(skills)
        return f"[OK] Skill '{name}' saved ({skill['id']})."

    elif action == "search":
        query = kwargs.get("query", "")
        if not query:
            return "[FAIL] Search query required."
        q = query.lower()
        matches = []
        for s in skills:
            score = 0
            if q in s.get("name", "").lower():
                score += 3
            if q in s.get("trigger", "").lower():
                score += 2
            if any(q in t.lower() for t in s.get("tags", [])):
                score += 2
            if q in s.get("steps", "").lower():
                score += 1
            if score > 0:
                matches.append((score, s))
        matches.sort(key=lambda x: -x[0])
        if not matches:
            return f"No skills match '{query}'."
        lines = [f"### Skills matching '{query}'"]
        for score, s in matches[:10]:
            lines.append(f"  [{score}] {s.get('name')} (used {s.get('use_count', 0)}x)")
        return "\n".join(lines)

    elif action == "delete":
        skill_id = kwargs.get("id", "")
        name = kwargs.get("name", "")
        before = len(skills)
        skills = [
            s for s in skills
            if not ((skill_id and s.get("id") == skill_id) or (name and s.get("name") == name))
        ]
        removed = before - len(skills)
        if removed:
            _save(skills)
            return f"[OK] Removed {removed} skill(s)."
        return "[INFO] No matching skills found."

    elif action == "stats":
        if not skills:
            return "No skills yet."
        total = len(skills)
        total_uses = sum(s.get("use_count", 0) for s in skills)
        most_used = max(skills, key=lambda s: s.get("use_count", 0)) if skills else None
        archive = _load_archive()
        return (
            f"Skills: {total}\n"
            f"Total uses: {total_uses}\n"
            f"Archived: {len(archive)}\n"
            f"Most used: {most_used.get('name', 'N/A')} ({most_used.get('use_count', 0)}x)" if most_used else ""
        )

    elif action == "curate":
        return _curate()

    elif action == "auto_create":
        name = kwargs.get("name", "")
        steps = kwargs.get("steps", "")
        trigger = kwargs.get("trigger", "")
        tags = kwargs.get("tags", "")
        return skills_tool("add", name=name, steps=steps, trigger=trigger, tags=tags)

    else:
        return f"[FAIL] Unknown action: {action}"


def _load_archive() -> list:
    apath = os.path.join(FRIDAY_MEMORY, "skills_archive.json")
    if os.path.exists(apath):
        try:
            with open(apath) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_archive(archive: list):
    apath = os.path.join(FRIDAY_MEMORY, "skills_archive.json")
    try:
        with open(apath, "w") as f:
            json.dump(archive, f, indent=2)
    except Exception:
        pass


def _curate() -> str:
    """Auto-curate skills: archive stale, prune failing, suggest merges."""
    skills = _load()
    if not skills:
        return "[INFO] No skills to curate."
    now = datetime.now()
    archived = []
    pruned = []
    kept = []
    for s in skills:
        last_used = s.get("last_used")
        use_count = s.get("use_count", 0)
        success_rate = s.get("success_rate", 1.0)
        if use_count >= 5 and success_rate < 0.3:
            pruned.append(s)
            continue
        if last_used:
            try:
                days_since = (now - datetime.fromisoformat(last_used)).days
            except Exception:
                days_since = 999
            if days_since > 14 and use_count < 3:
                archived.append(s)
                continue
        kept.append(s)
    archive = _load_archive()
    archive.extend(archived)
    _save_archive(archive[-100:])
    _save(kept)
    lines = []
    if pruned:
        lines.append(f"Pruned {len(pruned)} failing skills:")
        for s in pruned:
            lines.append(f"  - {s.get('name')} ({s.get('success_rate', 0):.0%} success, {s.get('use_count', 0)} uses)")
    if archived:
        lines.append(f"Archived {len(archived)} stale skills:")
        for s in archived:
            lines.append(f"  - {s.get('name')}")
    if not pruned and not archived:
        lines.append("All skills healthy. No curation needed.")
    merge_suggestions = _suggest_merges(kept)
    if merge_suggestions:
        lines.append(f"Merge suggestions ({len(merge_suggestions)}):")
        for suggestion in merge_suggestions[:3]:
            lines.append(f"  - {suggestion}")
    lines.append(f"Active: {len(kept)} | Archived: {len(archived)} | Pruned: {len(pruned)}")
    return "\n".join(lines)


def _suggest_merges(skills: list) -> list:
    """Find skills with overlapping triggers or names. Deduplicates similar names."""
    suggestions = []
    seen_pairs = set()
    for i, a in enumerate(skills):
        for b in skills[i + 1:]:
            a_name = a.get("name", "").lower().strip()
            b_name = b.get("name", "").lower().strip()
            if a_name == b_name:
                continue
            pair_key = tuple(sorted([a_name, b_name]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            a_trigger = a.get("trigger", "").lower()
            b_trigger = b.get("trigger", "").lower()
            if a_trigger and b_trigger and (a_trigger in b_trigger or b_trigger in a_trigger):
                suggestions.append(f"'{a.get('name')[:40]}' <-> '{b.get('name')[:40]}' (overlapping triggers)")
            elif a_name and b_name and (a_name in b_name or b_name in a_name):
                suggestions.append(f"'{a.get('name')[:40]}' <-> '{b.get('name')[:40]}' (overlapping names)")
    return suggestions[:5]


def start_curator_on_boot():
    """Run curation cycle on boot."""
    try:
        _curate()
    except Exception:
        pass


def match_skill(context: str) -> Optional[dict]:
    """Find the best matching skill for a given context string."""
    skills = _load()
    if not skills or not context:
        return None

    ctx_lower = context.lower()
    best_match = None
    best_score = 0

    for s in skills:
        score = 0
        trigger = s.get("trigger", "").lower()
        tags = [t.lower() for t in s.get("tags", [])]
        name = s.get("name", "").lower()

        if trigger and trigger in ctx_lower:
            score += 5
        if name and name in ctx_lower:
            score += 3
        for tag in tags:
            if tag in ctx_lower:
                score += 2
        if score > best_score:
            best_score = score
            best_match = s

    return best_match if best_score >= 3 else None


def record_use(skill_id: str, success: bool = True):
    """Record a skill usage and update success rate."""
    skills = _load()
    for s in skills:
        if s.get("id") == skill_id:
            s["use_count"] = s.get("use_count", 0) + 1
            s["last_used"] = datetime.now().isoformat()
            n = s.get("use_count", 1)
            prev = s.get("success_rate", 1.0)
            s["success_rate"] = (prev * (n - 1) + (1.0 if success else 0.0)) / n
            break
    _save(skills)
