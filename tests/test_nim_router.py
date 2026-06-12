"""
Tests for nim_router.py — model resolution, task classification, config merging.
"""

import pytest
from friday.nim_router import (
    resolve_model,
    classify_task_type,
    list_task_types,
    list_all_models,
)


class TestResolveModel:
    def test_returns_model_for_known_task_type(self):
        model = resolve_model("code_gen")
        assert model is not None
        assert isinstance(model, str) and len(model) > 0

    def test_falls_back_to_general(self):
        model = resolve_model("nonexistent_task_type")
        assert model is not None

    def test_skips_unavailable_models(self):
        model = resolve_model("code_gen", unavailable={"nvidia/llama-3.1-nemotron-70b-instruct"})
        assert model is not None
        assert model != "nvidia/llama-3.1-nemotron-70b-instruct"

    def test_none_when_all_unavailable(self):
        model = resolve_model("image_analysis", unavailable={"nvidia/neva-22b", "microsoft/phi-3-vision-128k-instruct"})
        # Should return first candidate even if unavailable (no fallback past list)
        assert model is not None

    def test_returns_none_when_no_task_map_and_no_general(self):
        from friday.nim_router import _DEFAULT_MODEL_MAP
        import friday.nim_router
        saved = dict(_DEFAULT_MODEL_MAP)
        saved_cache = friday.nim_router._CONFIG_CACHE
        try:
            _DEFAULT_MODEL_MAP.clear()
            _DEFAULT_MODEL_MAP["general"] = []
            friday.nim_router._CONFIG_CACHE = {}
            assert resolve_model("code_gen") is None
        finally:
            _DEFAULT_MODEL_MAP.clear()
            _DEFAULT_MODEL_MAP.update(saved)
            friday.nim_router._CONFIG_CACHE = saved_cache


class TestClassifyTaskType:
    def test_code_keywords(self):
        assert classify_task_type("write a function to sort an array") == "code_gen"
        assert classify_task_type("debug this api endpoint") == "code_gen"

    def test_research_keywords(self):
        assert classify_task_type("research quantum computing") == "research"
        assert classify_task_type("what is the capital of France") == "research"

    def test_image_keywords(self):
        assert classify_task_type("what do you see in this image") == "image_analysis"
        assert classify_task_type("look at this picture") == "image_analysis"

    def test_summary_keywords(self):
        assert classify_task_type("summarize this article") == "summarization"
        assert classify_task_type("tl;dr") == "summarization"

    def test_reasoning_keywords(self):
        assert classify_task_type("why does this happen") == "reasoning"
        assert classify_task_type("explain how gravity works") == "reasoning"

    def test_general_default(self):
        assert classify_task_type("hello!") == "general"
        assert classify_task_type("") == "general"


class TestListFunctions:
    def test_list_task_types(self):
        types = list_task_types()
        assert "code_gen" in types
        assert "research" in types
        assert "general" in types

    def test_list_all_models_no_duplicates(self):
        models = list_all_models()
        assert len(models) == len(set(models))
        assert all(len(m) > 0 for m in models)
