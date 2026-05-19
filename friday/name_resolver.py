"""Fuzzy name resolution for Friday's agent invocation parser.

Recognizes direct mentions, short aliases, and fuzzy speech-to-text
variants such as "ask Veronica to..." or "the research agent".
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import List, Optional, Sequence, Tuple

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover - fallback for minimal environments
    class _FallbackFuzz:
        @staticmethod
        def WRatio(left: str, right: str) -> int:
            return int(SequenceMatcher(None, left, right).ratio() * 100)

    fuzz = _FallbackFuzz()

from friday.agent_registry import AgentProfile, get_registry
from friday.logging_utils import configure_logging


logger = configure_logging(__name__)


@dataclass(slots=True)
class NameMatch:
    """Fuzzy match result for a registered agent."""

    agent_id: str
    confidence: float


_LEADING_PHRASES = (
    "ask ",
    "tell ",
    "get ",
    "have ",
    "please ",
    "can you ",
    "could you ",
    "the ",
)


def _clean_utterance(text: str) -> str:
    cleaned = re.sub(r"[^\w@\s-]", " ", text.lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    for phrase in _LEADING_PHRASES:
        if cleaned.startswith(phrase):
            cleaned = cleaned[len(phrase):].strip()
    return cleaned


def _aliases_for(profile: AgentProfile) -> List[str]:
    aliases = set(profile.aliases())
    aliases.add(profile.display_name.lower())
    aliases.add(profile.agent_id.lower())
    aliases.add(profile.display_name.lower().replace(" ", ""))
    aliases.add(profile.agent_id.lower().replace("_", " "))
    return sorted(alias for alias in aliases if alias)


class AgentNameResolver:
    """Resolve agent names from raw user utterances."""

    def __init__(self, profiles: Optional[Sequence[AgentProfile]] = None, threshold: int = 70) -> None:
        self._profiles = list(profiles) if profiles is not None else get_registry().list_all()
        self._threshold = threshold

    @property
    def profiles(self) -> List[AgentProfile]:
        return list(self._profiles)

    def resolve(self, utterance: str) -> Optional[Tuple[str, float]]:
        """Return the best single agent match or None."""
        matches = self.resolve_many(utterance)
        if not matches:
            return None
        top = matches[0]
        return top.agent_id, top.confidence

    def resolve_many(self, utterance: str) -> List[NameMatch]:
        """Return all matching agents ordered by confidence."""
        cleaned = _clean_utterance(utterance)
        if not cleaned:
            return []

        matches: List[NameMatch] = []
        direct_mentions = re.findall(r"@([\w-]+)", cleaned)
        direct_lookup = {mention.lower() for mention in direct_mentions}

        for profile in self._profiles:
            aliases = _aliases_for(profile)
            best_score = 0.0

            if profile.display_name.lower() in direct_lookup or profile.agent_id.lower() in direct_lookup:
                best_score = 100.0
            else:
                for alias in aliases:
                    if not alias:
                        continue
                    if alias in cleaned:
                        best_score = 100.0
                        break
                    score = float(fuzz.WRatio(alias, cleaned))
                    if len(alias) <= 3 and cleaned.startswith(alias):
                        score = max(score, 90.0)
                    if score > best_score:
                        best_score = score

            if best_score >= self._threshold:
                matches.append(NameMatch(agent_id=profile.agent_id, confidence=best_score))

        matches.sort(key=lambda item: item.confidence, reverse=True)
        return matches


def resolve_agent_name(utterance: str, profiles: Optional[Sequence[AgentProfile]] = None) -> Optional[Tuple[str, float]]:
    """Convenience wrapper that returns one resolved agent id."""
    return AgentNameResolver(profiles=profiles).resolve(utterance)


def resolve_agent_names(utterance: str, profiles: Optional[Sequence[AgentProfile]] = None) -> List[Tuple[str, float]]:
    """Convenience wrapper that returns all resolved agents."""
    return [(match.agent_id, match.confidence) for match in AgentNameResolver(profiles=profiles).resolve_many(utterance)]
