"""Tests for the memory context system — no API keys required."""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from friday._paths import FRIDAY_MEMORY

_PROFILE_PATH = os.path.join(FRIDAY_MEMORY, "user_profile.json")


def _save_profile_backup():
    """Read and return current profile content (or None)."""
    if os.path.exists(_PROFILE_PATH):
        with open(_PROFILE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return None


def _restore_profile(backup):
    """Restore profile from saved content."""
    if backup is not None:
        os.makedirs(os.path.dirname(_PROFILE_PATH), exist_ok=True)
        with open(_PROFILE_PATH, "w", encoding="utf-8") as f:
            f.write(backup)
    elif os.path.exists(_PROFILE_PATH):
        os.remove(_PROFILE_PATH)


SAMPLE_PROFILE = {
    "version": 5,
    "name": "TestUser",
    "location": "TestLocation",
    "age_grade": "Adult",
    "languages": ["English", "Hindi"],
    "education": ["B.Tech Computer Science"],
    "projects": ["Project Alpha", "Project Beta"],
    "tech_stack": ["Python", "React", "Docker"],
    "goals": ["Learn Rust", "Build an AI agent"],
    "preferences": {"browsers": ["Firefox"], "apps": ["VSCode"]},
    "interests_hobbies": {"hobbies": ["Playing guitar", "Reading"], "activities": ["Hiking"]},
    "learning": {"courses": ["ML Course"], "books": ["Deep Learning Book"]},
    "career": {"roles": ["Software Engineer"], "industries": ["Tech"]},
    "challenges": ["Time management"],
    "achievements": ["Won hackathon"],
    "last_tfidf_topics": ["python", "react", "docker", "ai"],
    "audits": [],
    "last_updated": "2026-01-01",
}


# ─── Test 1: build_user_memory_context with no profile ───

def test_build_context_no_profile():
    from friday.memory_import import build_user_memory_context
    backup = _save_profile_backup()
    if backup is not None:
        os.remove(_PROFILE_PATH)
    try:
        ctx = build_user_memory_context()
        assert ctx == "", f"Expected empty string, got {repr(ctx[:60])}"
    finally:
        _restore_profile(backup)
    print("[PASS] test_build_context_no_profile")


# ─── Test 2: build_user_memory_context with sample profile ───

def test_build_context_with_profile():
    from friday.memory_import import build_user_memory_context
    backup = _save_profile_backup()
    try:
        os.makedirs(os.path.dirname(_PROFILE_PATH), exist_ok=True)
        with open(_PROFILE_PATH, "w", encoding="utf-8") as f:
            json.dump(SAMPLE_PROFILE, f)

        ctx = build_user_memory_context()
        assert "[USER MEMORY]" in ctx, "Missing header"
        assert "TestUser" in ctx, "Missing name"
        assert "TestLocation" in ctx, "Missing location"
        assert "Python" in ctx, "Missing tech"
        assert "inferred from imported chat" in ctx, "Missing disclaimer"
        assert len(ctx) > 100, "Context too short"
        print(f"[PASS] test_build_context_with_profile ({len(ctx)} chars)")

        short = build_user_memory_context(max_chars=150)
        assert len(short) <= 170, f"Context too long: {len(short)}"
        assert "[TRUNCATED]" in short or len(short) < 150, "Missing truncation marker"
        print(f"[PASS] test_build_context_max_chars ({len(short)} chars)")
    finally:
        _restore_profile(backup)
    print("[PASS] test_build_context_with_profile (all)")


# ─── Test 3: build_relevant_memory_context with no vector memory ───

def test_relevant_context_no_vector():
    from friday.memory_context import build_relevant_memory_context
    ctx = build_relevant_memory_context("python programming", max_chars=2000)
    assert isinstance(ctx, str), "Must return a string"
    print(f"[PASS] test_relevant_context_no_vector ({len(ctx)} chars)")


# ─── Test 4: build_relevant_memory_context short query ───

def test_relevant_context_short_query():
    from friday.memory_context import build_relevant_memory_context
    ctx = build_relevant_memory_context("ok")
    assert ctx == "", "Short query should return empty"
    ctx2 = build_relevant_memory_context("no")
    assert ctx2 == "", "Very short query should return empty"
    print("[PASS] test_relevant_context_short_query")


# ─── Test 5: build_relevant_memory_context dedup/cooldown fields exist ───

def test_inject_signature():
    live_path = os.path.join(os.path.dirname(__file__), "friday", "live.py")
    with open(live_path, "r", encoding="utf-8") as f:
        source = f.read()
    assert "async def _inject_memory_context" in source, "Missing injection function"
    assert "_MEM_INJECT_COOLDOWN" in source, "Missing cooldown constant"
    assert "_injected_mem_signatures" in source, "Missing dedup set"
    print("[PASS] test_inject_signature")


# ─── Test 6: memory_context.py imports cleanly ───

def test_memory_context_import():
    from friday.memory_context import build_relevant_memory_context
    assert callable(build_relevant_memory_context)
    print("[PASS] test_memory_context_import")


# ─── Test 7: build_user_memory_context never crashes on bad data ───

def test_build_context_malformed():
    from friday.memory_import import build_user_memory_context
    backup = _save_profile_backup()
    try:
        with open(_PROFILE_PATH, "w", encoding="utf-8") as f:
            f.write("not valid json at all")
        ctx = build_user_memory_context()
        assert ctx == "", f"Malformed JSON should yield empty, got {repr(ctx[:40])}"
    finally:
        _restore_profile(backup)
    print("[PASS] test_build_context_malformed")


# ─── Test 8: build_user_memory_context includes all key sections ───

def test_build_context_key_fields():
    from friday.memory_import import build_user_memory_context
    backup = _save_profile_backup()
    try:
        os.makedirs(os.path.dirname(_PROFILE_PATH), exist_ok=True)
        with open(_PROFILE_PATH, "w", encoding="utf-8") as f:
            json.dump(SAMPLE_PROFILE, f)

        ctx = build_user_memory_context()
        for field in ["Name", "Location", "Languages", "Tech", "Projects",
                       "Goals", "Interests", "Key Topics"]:
            assert field in ctx, f"Missing field: {field}"
        print("[PASS] test_build_context_key_fields")
    finally:
        _restore_profile(backup)


# ─── Test 9: github_setup is in TOOL_MAP ───

def test_github_setup_in_tool_map():
    live_path = os.path.join(os.path.dirname(__file__), "friday", "live.py")
    with open(live_path, "r", encoding="utf-8") as f:
        source = f.read()
    assert '"github_setup"' in source, "github_setup not found in live.py"
    # Should appear at least in TOOL_MAP dict (not just FunctionDeclaration)
    tool_map_section = source.split("TOOL_MAP")[1].split("}")[0] if "TOOL_MAP" in source else ""
    has_in_map = '"github_setup"' in tool_map_section if tool_map_section else False
    assert has_in_map, "github_setup is not in TOOL_MAP dict"
    print("[PASS] test_github_setup_in_tool_map")


# ─── Run all ───

if __name__ == "__main__":
    tests = [
        test_build_context_no_profile,
        test_build_context_with_profile,
        test_build_context_malformed,
        test_build_context_key_fields,
        test_relevant_context_no_vector,
        test_relevant_context_short_query,
        test_inject_signature,
        test_memory_context_import,
        test_github_setup_in_tool_map,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    print(f"\n{'='*40}\nResults: {passed} passed, {failed} failed, {len(tests)} total")
