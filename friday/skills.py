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
        return (
            f"Skills: {total}\n"
            f"Total uses: {total_uses}\n"
            f"Most used: {most_used.get('name', 'N/A')} ({most_used.get('use_count', 0)}x)" if most_used else ""
        )

    elif action == "auto_create":
        name = kwargs.get("name", "")
        steps = kwargs.get("steps", "")
        trigger = kwargs.get("trigger", "")
        tags = kwargs.get("tags", "")
        return skills_tool("add", name=name, steps=steps, trigger=trigger, tags=tags)

    else:
        return f"[FAIL] Unknown action: {action}"


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
