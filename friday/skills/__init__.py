"""FRIDAY Skill Loader — loads SKILL.md files on demand."""

from __future__ import annotations

import os
from pathlib import Path

_SKILLS_DIR = Path(__file__).parent

_skill_cache: dict[str, str] = {}


def load_skill(name: str) -> str:
    """Load a skill's SKILL.md file by name (e.g. 'docx', 'pptx', 'pdf', 'xlsx', 'svg', 'chart')."""
    name = name.lower().strip()
    if name in _skill_cache:
        return _skill_cache[name]

    skill_path = _SKILLS_DIR / name / "SKILL.md"
    if not skill_path.exists():
        return f"Skill '{name}' not found. Available: {list_skills()}"

    content = skill_path.read_text(encoding="utf-8")
    _skill_cache[name] = content
    return content


def list_skills() -> list[str]:
    """List all available skill names."""
    return sorted(
        d.name for d in _SKILLS_DIR.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    )


def read_skill_tool(name: str = None) -> str:
    """Tool: read a SKILL.md file for FRIDAY to follow when creating documents.

    Always call this before creating any document file. Available skills:
    docx (Word), pptx (PowerPoint), pdf, xlsx (Excel), svg (diagrams), chart.
    """
    if name:
        return load_skill(name)
    available = list_skills()
    return f"Available skills: {', '.join(available)}\n\nUse read_skill_tool(name='<skill_name>') to read a specific skill."


def start_curator_on_boot() -> None:
    """Preload skill index on boot (no-op if already cached)."""
    list_skills()
