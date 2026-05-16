"""Friday Memory Context — contextual memory retrieval for live sessions.

Combines vector memory, episodic memory, keyword memory, and profile
topics to build relevant context for a given query.
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List
import os
import json

from friday._paths import FRIDAY_MEMORY


def build_relevant_memory_context(query: str, max_chars: int = 4000) -> str:
    """Build relevant memory context for a query from all available memory systems.

    Args:
        query: The user's current utterance to search against.
        max_chars: Maximum character length for output.

    Returns:
        A compact, source-labeled string of relevant memories,
        or empty string if nothing found / unavailable.
    """
    q = query.strip()
    if not q or len(q) < 5:
        return ""

    parts: List[str] = []

    # 1. Profile topic matches
    try:
        from friday.memory_import import load_profile

        profile = load_profile()
        if profile and profile.get("version", 0) >= 1:
            q_lower = q.lower()
            topics = profile.get("last_tfidf_topics", [])
            profile_matches = [t for t in topics if t.lower() in q_lower] if topics else []

            tech_stack = profile.get("tech_stack", [])
            tech_matches = [t for t in tech_stack if t.lower() in q_lower] if tech_stack else []

            interests = profile.get("interests_hobbies", {})
            all_interests: List[str] = []
            for v in interests.values():
                if isinstance(v, list):
                    all_interests.extend(str(i) for i in v)
            interest_matches = [
                i for i in all_interests
                if isinstance(i, str) and len(i) > 3 and i.lower() in q_lower
            ]

            profile_lines: List[str] = []
            if profile_matches:
                profile_lines.append(f"Profile topics match: {', '.join(profile_matches[:5])}")
            if tech_matches:
                profile_lines.append(f"Tech matches: {', '.join(tech_matches[:5])}")
            if interest_matches:
                profile_lines.append(f"Interest matches: {', '.join(interest_matches[:5])}")
            if profile_lines:
                parts.append("[RELEVANT PROFILE MEMORY]")
                parts.extend(profile_lines)
    except Exception:
        pass

    # 2. Vector memory search
    try:
        from friday.vector_memory import get_vector_memory

        vm = get_vector_memory()
        if vm and vm.is_available():
            results = vm.search(q, n_results=3)
            if results:
                vec_lines: List[str] = []
                for r in results[:3]:
                    text = r.get("text", "")
                    meta = r.get("metadata", {})
                    source = meta.get("source", "unknown")
                    distance = r.get("distance", 0)
                    snippet = text[:120].replace("\n", " ")
                    vec_lines.append(f"  [{source}] (d={distance:.3f}) {snippet}")
                if vec_lines:
                    parts.append("[RELEVANT SEMANTIC MEMORY]")
                    parts.extend(vec_lines)
    except Exception:
        pass

    # 3. Episodic memory search
    try:
        from friday.episodic import search

        episodes = search(q, limit=5)
        if episodes:
            epi_lines: List[str] = []
            for ep in episodes[:5]:
                if isinstance(ep, dict):
                    speaker = ep.get("speaker", "?")
                    content = ep.get("content", "")
                    ts = ep.get("timestamp", "")[:10]
                    snippet = str(content)[:100].replace("\n", " ")
                    epi_lines.append(f"  [{speaker}] {ts}: {snippet}")
            if epi_lines:
                parts.append("[RELEVANT EPISODIC MEMORY]")
                parts.extend(epi_lines)
    except Exception:
        pass

    # 4. Keyword memory (memory.json)
    try:
        memory_file = os.path.join(FRIDAY_MEMORY, "memory.json")
        if os.path.exists(memory_file):
            with open(memory_file, "r", encoding="utf-8") as f:
                memories: list = json.load(f)
            q_lower = q.lower()
            matches = [
                m for m in memories
                if q_lower in m.get("key", "").lower()
                or q_lower in m.get("value", "").lower()
            ] if memories else []
            if matches:
                mem_lines: List[str] = []
                for m in matches[:5]:
                    key = m.get("key", "")
                    value = str(m.get("value", ""))[:80]
                    mem_lines.append(f"  {key}: {value}")
                if mem_lines:
                    parts.append("[RELEVANT KEYWORD MEMORY]")
                    parts.extend(mem_lines)
    except Exception:
        pass

    if not parts:
        return ""

    result = "\n".join(parts)
    if len(result) > max_chars:
        result = result[:max_chars].rsplit("\n", 1)[0] + "\n[TRUNCATED]"
    return result
