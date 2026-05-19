"""
Tests for name_resolver.py — fuzzy matching, @mention extraction, multi-resolve.
"""

import pytest
from friday.base_agent import AgentDef
from friday.name_resolver import resolve, resolve_multi, extract_mentions


@pytest.fixture
def agents():
    return [
        AgentDef(id="research_agent", name="Veronica",
                 task_types=["research"], enabled=True),
        AgentDef(id="code_agent", name="Forge",
                 task_types=["code_gen"], enabled=True),
        AgentDef(id="communicator_agent", name="Jarvis",
                 task_types=["summarization"], enabled=True),
        AgentDef(id="organizer_agent", name="Nova",
                 task_types=["general"], enabled=True),
    ]


class TestResolve:
    def test_exact_name_match(self, agents):
        match = resolve("Veronica", agents)
        assert match is not None
        assert match.id == "research_agent"

    def test_exact_id_match(self, agents):
        match = resolve("research_agent", agents)
        assert match is not None
        assert match.name == "Veronica"

    def test_case_insensitive(self, agents):
        match = resolve("veronica", agents)
        assert match is not None
        assert match.id == "research_agent"

    def test_at_mention_stripped(self, agents):
        match = resolve("@Veronica", agents)
        assert match is not None
        assert match.id == "research_agent"

    def test_fuzzy_match_high_similarity(self, agents):
        match = resolve("Veroncia", agents)  # typo
        assert match is not None
        # Should match Veronica via WRatio
        assert match.name == "Veronica"

    def test_fuzzy_match_low_similarity_returns_none(self, agents):
        match = resolve("Xylophone", agents, threshold=70)
        assert match is None

    def test_fuzzy_match_with_lower_threshold(self, agents):
        # "Jarvis" → "Jarvis" should be exact
        match = resolve("Jarvis", agents)
        assert match is not None
        assert match.name == "Jarvis"


class TestResolveMulti:
    def test_multiple_names(self, agents):
        results = resolve_multi(["Veronica", "Forge", "Nobody"], agents)
        assert len(results) == 3
        assert results[0][1] is not None  # Veronica
        assert results[1][1] is not None  # Forge
        assert results[2][1] is None      # Nobody

    def test_empty_list(self, agents):
        assert resolve_multi([], agents) == []


class TestExtractMentions:
    def test_at_mention(self):
        assert extract_mentions("ask @Veronica to research") == ["Veronica"]

    def test_ask_name_to(self):
        mentions = extract_mentions("ask Veronica to research quantum computing")
        assert "Veronica" in mentions

    def test_tell_name_and_name(self):
        mentions = extract_mentions("tell Forge and Veronica to help")
        assert "Forge" in mentions
        assert "Veronica" in mentions

    def test_delegate_keyword(self):
        mentions = extract_mentions("delegate to Jarvis: check email")
        assert "Jarvis" in mentions

    def test_no_mentions(self):
        assert extract_mentions("hello world") == []

    def test_capture_broadcast_keywords(self):
        mentions = extract_mentions("capture Nova: plan my day")
        assert "Nova" in mentions

    def test_multiple_at_mentions(self):
        mentions = extract_mentions("@Veronica @Forge collaborate on this")
        assert "Veronica" in mentions
        assert "Forge" in mentions
