"""
FRIDAY Knowledge Store — persistent research knowledge.
Saves research results as structured JSON + optional ChromaDB embeddings so FRIDAY
can recall them and "become an expert" on any researched topic without the web.
"""
from __future__ import annotations

import os
import json
import time
import hashlib
from datetime import datetime
from typing import Any, Optional
from friday._paths import FRIDAY_MEMORY

KNOWLEDGE_DIR = os.path.join(FRIDAY_MEMORY, "knowledge")
os.makedirs(KNOWLEDGE_DIR, exist_ok=True)


def _slug(topic: str) -> str:
    return hashlib.md5(topic.encode()).hexdigest()[:12]


def save_research(
    topic: str,
    sources: list[dict],
    content: str,
    metadata: dict | None = None,
) -> str:
    """Save a research result to persistent knowledge store."""
    entry = {
        "topic": topic,
        "timestamp": datetime.now().isoformat(),
        "sources": sources,
        "content": content,
        "word_count": len(content.split()),
        "metadata": metadata or {},
    }
    fname = f"research_{_slug(topic)}_{int(time.time())}.json"
    path = os.path.join(KNOWLEDGE_DIR, fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2, ensure_ascii=False)
    return path


def load_research(topic: str) -> list[dict]:
    """Load all saved research entries matching a topic."""
    results = []
    topic_lower = topic.lower()
    for fname in os.listdir(KNOWLEDGE_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(KNOWLEDGE_DIR, fname), "r", encoding="utf-8") as f:
                data = json.load(f)
            if topic_lower in data.get("topic", "").lower():
                results.append(data)
        except Exception:
            continue
    return results


def get_all_research_topics() -> list[str]:
    """List all unique research topics stored."""
    topics = set()
    for fname in os.listdir(KNOWLEDGE_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(KNOWLEDGE_DIR, fname), "r", encoding="utf-8") as f:
                data = json.load(f)
            topics.add(data.get("topic", "Unknown"))
        except Exception:
            continue
    return sorted(topics)


def search_knowledge(query: str, max_results: int = 5) -> str:
    """Search saved knowledge for relevant content using keyword matching."""
    q = query.lower()
    scored = []
    for fname in os.listdir(KNOWLEDGE_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(KNOWLEDGE_DIR, fname), "r", encoding="utf-8") as f:
                data = json.load(f)
            text = (data.get("topic", "") + " " + data.get("content", "")).lower()
            score = text.count(q)
            if score > 0:
                scored.append((score, data))
        except Exception:
            continue
    scored.sort(key=lambda x: -x[0])
    if not scored:
        return ""
    parts = []
    for _, data in scored[:max_results]:
        parts.append(f"Topic: {data['topic']}")
        parts.append(f"Content: {data['content'][:2000]}")
        parts.append("---")
    return "\n".join(parts)


def get_knowledge_context(topic: str, max_chars: int = 6000) -> str:
    """Build a context string for FRIDAY from saved research on a topic."""
    entries = load_research(topic)
    if not entries:
        return ""
    parts = [f"[KNOWLEDGE: {topic}]"]
    chars = 0
    for entry in entries:
        snippet = entry.get("content", "")[:max_chars]
        parts.append(snippet)
        chars += len(snippet)
        if chars >= max_chars:
            break
    return "\n\n".join(parts)
