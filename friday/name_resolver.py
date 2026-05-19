"""
FRIDAY Name Resolver — fuzzy matches agent names using rapidfuzz WRatio.
Supports @mention exact match and partial name resolution.

Examples:
    resolve("veronica")           -> AgentDef for "Veronica"
    resolve("@Veronica")          -> exact match
    resolve("code guy")           -> fuzzy match for Forge (WRatio >= 70)
    extract_mentions("ask @Veronica and Forge to help")
                                  -> ["@Veronica", "Forge"]
"""

from __future__ import annotations

import re
from typing import Optional

from rapidfuzz import fuzz

from friday.agent_registry import AgentDef


def resolve(name: str, agents: list[AgentDef], threshold: int = 70) -> Optional[AgentDef]:
    """
    Resolve a name string to an AgentDef via:
    1. Exact match (case-insensitive) on display_name or id
    2. Fuzzy WRatio match (threshold 70 by default)

    Returns None if no match or threshold not met.
    """
    clean = name.lstrip("@").strip()
    clean_lower = clean.lower()

    # Exact match on name or id
    for agent in agents:
        if agent.name.lower() == clean_lower or agent.id.lower() == clean_lower:
            return agent

    # Fuzzy match
    best_score = 0
    best_agent: Optional[AgentDef] = None
    for agent in agents:
        score = fuzz.WRatio(clean, agent.name)
        if score > best_score:
            best_score = score
            best_agent = agent

    if best_score >= threshold and best_agent is not None:
        return best_agent

    return None


def resolve_multi(names: list[str], agents: list[AgentDef],
                  threshold: int = 70) -> list[tuple[str, Optional[AgentDef]]]:
    """Resolve multiple names at once. Returns (input_name, agent_or_None) pairs."""
    return [(n, resolve(n, agents, threshold)) for n in names]


def extract_mentions(text: str) -> list[str]:
    """
    Extract @mentions and agent names from utterance text.

    Handles:
      - @ExplicitMention
      - "ask AgentName to ..."
      - "tell AgentName and AgentName2"
    """
    mentions: list[str] = []

    # @mentions
    at_mentions = re.findall(r"@(\w+)", text)
    mentions.extend(at_mentions)

    # "ask/tell/instruct/delegate {Name} to ..."
    for prefix in r"(?:ask|tell|instruct|delegate|capture|broadcast)":
        pattern = re.compile(rf"{prefix}\s+(\w[\w\s]{{0,30}}?)(?:\s+to|\s+and|\s*[,\.!?]|$)", re.IGNORECASE)
        for match in pattern.finditer(text):
            name = match.group(1).strip()
            if name and name not in mentions:
                mentions.append(name)

    # Split combined mentions like "Veronica and Forge"
    split_mentions: list[str] = []
    for m in mentions:
        parts = re.split(r"\s+and\s+", m)
        split_mentions.extend(p.strip() for p in parts if p.strip())

    return split_mentions or mentions
