"""
FRIDAY Memory-Use Bridge — unified memory, learning & knowledge graph toolkit.
Parallel to security_use_bridge.py but for vector memory, Redis, Neo4j, KYU.

Wraps existing modules (memory_tools, knowledge_tools, vector_memory, kyu)
into sync functions returning JSON strings.

Categories:
  - Status & Availability
  - Vector Memory (ChromaDB)
  - Key-Value Store (Redis)
  - Knowledge Graph (Neo4j)
  - Preference Learning (KYU)
  - Semantic Search (VectorMemory class)
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import os
from datetime import datetime, timezone
from typing import Any

from friday._paths import FRIDAY_MEMORY
from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

_STATE_PATH = os.path.join(FRIDAY_MEMORY, "memory_use_state.json")
_HISTORY_PATH = os.path.join(FRIDAY_MEMORY, "memory_use_history.jsonl")


def _load_state() -> dict:
    if os.path.exists(_STATE_PATH):
        try:
            with open(_STATE_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"operations": 0, "last_category": ""}


def _save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
    with open(_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def _log_history(entry: dict) -> None:
    os.makedirs(os.path.dirname(_HISTORY_PATH), exist_ok=True)
    with open(_HISTORY_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _record_action(category: str, action: str, status: str = "ok") -> None:
    state = _load_state()
    state["operations"] += 1
    state["last_category"] = category
    _save_state(state)
    _log_history({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "category": category,
        "action": action,
        "status": status,
    })


def _run_async(coro) -> Any:
    try:
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=120)
    except RuntimeError:
        return asyncio.run(coro)


# ═══════════════════════════════════════════════════════════════════
# 1. STATUS
# ═══════════════════════════════════════════════════════════════════

def memory_use_status() -> str:
    state = _load_state()
    import importlib
    backends = {}
    for mod_name in ("memory_tools", "knowledge_tools"):
        try:
            mod = importlib.import_module(f"friday.tools.{mod_name}")
            backends[mod_name] = {
                "chroma": getattr(mod, "HAS_CHROMA", False),
                "redis": getattr(mod, "HAS_REDIS", False),
                "mongodb": getattr(mod, "HAS_MONGO", False),
                "neo4j": getattr(getattr(mod, "knowledge_tools", None) or mod, "HAS_NEO4J", False),
            }
        except Exception:
            backends[mod_name] = {"available": False}
    try:
        from friday.vector_memory import get_vector_memory
        vm = get_vector_memory()
        backends["vector_memory"] = {"available": vm.is_available()}
    except Exception:
        backends["vector_memory"] = {"available": False}
    try:
        from friday.kyu import kyu_status
        kyu = json.loads(kyu_status())
        backends["kyu"] = {"available": kyu.get("initialized", False)}
    except Exception:
        backends["kyu"] = {"available": False}
    return json.dumps({
        "available": any(b.get("available", True) if isinstance(b, dict) else True for b in backends.values()),
        "backends": backends,
        "total_operations": state["operations"],
    }, indent=2)


# ═══════════════════════════════════════════════════════════════════
# 2. VECTOR MEMORY — ChromaDB (async -> sync)
# ═══════════════════════════════════════════════════════════════════

def chroma_create_collection(name: str) -> str:
    try:
        from friday.tools.memory_tools import chroma_create_collection as _impl
        r = _run_async(_impl(name))
        _record_action("chroma", "create_collection")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def chroma_add(collection: str, texts: list[str], ids: list[str],
               metadatas: list[dict] | None = None) -> str:
    try:
        from friday.tools.memory_tools import chroma_add as _impl
        r = _run_async(_impl(collection, texts, ids, metadatas))
        _record_action("chroma", "add")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def chroma_query(collection: str, query_text: str, n_results: int = 5) -> str:
    try:
        from friday.tools.memory_tools import chroma_query as _impl
        r = _run_async(_impl(collection, query_text, n_results))
        _record_action("chroma", "query")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def chroma_list_collections() -> str:
    try:
        from friday.tools.memory_tools import chroma_list_collections as _impl
        r = _run_async(_impl())
        _record_action("chroma", "list_collections")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# 3. KEY-VALUE STORE — Redis (async -> sync)
# ═══════════════════════════════════════════════════════════════════

def redis_set(key: str, value: str, ttl: int | None = None) -> str:
    try:
        from friday.tools.memory_tools import redis_set as _impl
        r = _run_async(_impl(key, value, ttl))
        _record_action("redis", "set")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def redis_get(key: str) -> str:
    try:
        from friday.tools.memory_tools import redis_get as _impl
        r = _run_async(_impl(key))
        _record_action("redis", "get")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def redis_delete(key: str) -> str:
    try:
        from friday.tools.memory_tools import redis_delete as _impl
        r = _run_async(_impl(key))
        _record_action("redis", "delete")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def redis_list_keys(pattern: str = "*") -> str:
    try:
        from friday.tools.memory_tools import redis_list_keys as _impl
        r = _run_async(_impl(pattern))
        _record_action("redis", "list_keys")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# 4. KNOWLEDGE GRAPH — Neo4j (async -> sync)
# ═══════════════════════════════════════════════════════════════════

def neo4j_run_query(query: str, params: dict | None = None) -> str:
    try:
        from friday.tools.knowledge_tools import neo4j_run_query as _impl
        r = _run_async(_impl(query, params))
        _record_action("neo4j", "run_query")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def neo4j_create_entity(label: str, properties: dict) -> str:
    try:
        from friday.tools.knowledge_tools import neo4j_create_entity as _impl
        r = _run_async(_impl(label, properties))
        _record_action("neo4j", "create_entity")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def neo4j_find_entities(label: str, limit: int = 50) -> str:
    try:
        from friday.tools.knowledge_tools import neo4j_find_entities as _impl
        r = _run_async(_impl(label, limit))
        _record_action("neo4j", "find_entities")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def create_graph_visualization(nodes: list[dict], edges: list[dict]) -> str:
    try:
        from friday.tools.knowledge_tools import create_graph_visualization as _impl
        r = _run_async(_impl(nodes, edges))
        _record_action("graph", "visualize")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# 5. VECTOR MEMORY CLASS (sync, from vector_memory.py)
# ═══════════════════════════════════════════════════════════════════

def vm_add(text: str, metadata: dict | None = None, id: str | None = None) -> str:
    try:
        from friday.vector_memory import get_vector_memory
        vm = get_vector_memory()
        r = json.loads(vm.add(text, metadata, id))
        _record_action("vm", "add")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def vm_search(query: str, n_results: int = 5) -> str:
    try:
        from friday.vector_memory import get_vector_memory
        vm = get_vector_memory()
        r = vm.search(query, n_results)
        _record_action("vm", "search")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def vm_stats() -> str:
    try:
        from friday.vector_memory import get_vector_memory
        vm = get_vector_memory()
        r = json.loads(vm.get_stats())
        _record_action("vm", "stats")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def vm_delete(id: str) -> str:
    try:
        from friday.vector_memory import get_vector_memory
        vm = get_vector_memory()
        r = json.loads(vm.delete(id))
        _record_action("vm", "delete")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def vm_clear() -> str:
    try:
        from friday.vector_memory import get_vector_memory
        vm = get_vector_memory()
        r = json.loads(vm.clear())
        _record_action("vm", "clear")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# 6. PREFERENCE LEARNING — KYU (sync, from kyu.py)
# ═══════════════════════════════════════════════════════════════════

def kyu_status() -> str:
    try:
        from friday.kyu import kyu_status as _impl
        r = _impl()
        _record_action("kyu", "status")
        if isinstance(r, str):
            return r
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def kyu_interview(stage: int | None = None) -> str:
    try:
        from friday.kyu import kyu_interview as _impl
        r = _impl(stage)
        _record_action("kyu", "interview")
        if isinstance(r, str):
            return r
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def kyu_learn(tool_name: str | None = None, active_window: str | None = None,
              hour: int | None = None) -> str:
    try:
        from friday.kyu import kyu_learn as _impl
        r = _impl(tool_name, active_window, hour)
        _record_action("kyu", "learn")
        if isinstance(r, str):
            return r
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def kyu_profile() -> str:
    try:
        from friday.kyu import kyu_profile as _impl
        r = _impl()
        _record_action("kyu", "profile")
        if isinstance(r, str):
            return r
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# 7. MEMORY IMPORT (sync, from memory_import.py)
# ═══════════════════════════════════════════════════════════════════

def memory_import_tool(action: str = "status", **kwargs) -> str:
    try:
        from friday.memory_import import memory_import_tool as _impl
        r = _impl(action, **kwargs)
        _record_action("memory_import", action)
        if isinstance(r, str):
            return r
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
