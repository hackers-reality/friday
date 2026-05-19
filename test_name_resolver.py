"""Tests for Friday agent name resolution."""

from friday.agent_registry import AgentProfile
from friday.name_resolver import AgentNameResolver, resolve_agent_name, resolve_agent_names


def build_profiles():
    return [
        AgentProfile(
            agent_id="research_agent",
            display_name="Veronica",
            task_types=["research", "summarization"],
            nim_model="meta/llama-3.1-405b-instruct",
            tools=["web_search"],
            enabled=True,
        ),
        AgentProfile(
            agent_id="code_agent",
            display_name="Forge",
            task_types=["code_gen", "reasoning"],
            nim_model="nvidia/llama-3.1-nemotron-70b-instruct",
            tools=["read_file"],
            enabled=True,
        ),
    ]


def test_direct_mention_resolves():
    resolver = AgentNameResolver(build_profiles())
    result = resolver.resolve("@Veronica summarize this")
    assert result == ("research_agent", 100.0)


def test_fuzzy_alias_resolves():
    resolver = AgentNameResolver(build_profiles())
    result = resolver.resolve("ask Vero on this research")
    assert result is not None
    assert result[0] == "research_agent"
    assert result[1] >= 70


def test_role_phrase_resolves():
    resolver = AgentNameResolver(build_profiles())
    result = resolver.resolve("tell the research agent to summarize this")
    assert result is not None
    assert result[0] == "research_agent"


def test_no_match_returns_none():
    resolver = AgentNameResolver(build_profiles())
    assert resolver.resolve("do something unrelated") is None


def test_multi_match_returns_both_in_order():
    result = resolve_agent_names("ask Veronica and Forge to help", build_profiles())
    assert [item[0] for item in result] == ["research_agent", "code_agent"]


def test_convenience_wrapper():
    result = resolve_agent_name("tell Forge to fix this", build_profiles())
    assert result == ("code_agent", 100.0)
