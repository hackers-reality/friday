"""
FRIDAY Memory Retriever — queries ChromaDB for context-relevant MemoryChunks.
Called by orchestrator and system prompt builder to inject personal context
into Gemini Live conversations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from friday.logging_utils import configure_logging
from friday.vector_memory import get_vector_memory

logger = configure_logging(__name__)

_MAX_CONTEXT_TOKENS = 500


def retrieve_context(query: str, context_type: Optional[str] = None, max_results: int = 5) -> str:
    """
    Query ChromaDB for relevant memory chunks, return formatted string.

    Args:
        query: Current user utterance or topic.
        context_type: Optional filter — interests, habits, relationships, locations, etc.
        max_results: Max chunks to return (default 5).

    Returns:
        Formatted context string: "Based on your history: {chunk1}. {chunk2}..."
        Empty string if no results.
    """
    vm = get_vector_memory()
    if not vm.is_available():
        return ""

    try:
        where_filter = {"category": context_type} if context_type else None
        results = vm.search(query, n_results=max_results, filter=where_filter)
    except Exception as exc:
        logger.warning("ChromaDB query failed: %s", exc)
        return ""

    if not results or not results.get("documents"):
        return ""

    chunks = []
    for i, doc in enumerate(results["documents"][:max_results]):
        chunks.append(doc.strip())

    if not chunks:
        return ""

    prefix = "Based on your history: "
    combined = prefix + ". ".join(chunks) + "."

    # Token budget: ~4 chars per token
    if len(combined) > _MAX_CONTEXT_TOKENS * 4:
        combined = combined[:_MAX_CONTEXT_TOKENS * 4]
        last_period = combined.rfind(".")
        if last_period > 0:
            combined = combined[:last_period + 1]

    return combined


def search_memory(keyword: str, n_results: int = 20) -> list[dict]:
    """
    Raw ChromaDB search for dashboard memory browser.
    Returns list of {id, content, metadata, distance}.
    """
    vm = get_vector_memory()
    if not vm.is_available():
        return []

    try:
        results = vm.search(keyword, n_results=n_results)
    except Exception as exc:
        logger.warning("Memory search failed: %s", exc)
        return []

    if not results or not results.get("documents"):
        return []

    out = []
    for i in range(len(results["documents"][0])):
        out.append({
            "id": results["ids"][0][i] if results.get("ids") else "",
            "content": results["documents"][0][i],
            "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
            "distance": results["distances"][0][i] if results.get("distances") else 0.0,
        })
    return out


def delete_memory(chunk_id: str) -> bool:
    """Delete a single memory chunk by ID."""
    vm = get_vector_memory()
    if not vm.is_available():
        return False
    try:
        vm.delete(chunk_id)
        return True
    except Exception as exc:
        logger.warning("Failed to delete chunk %s: %s", chunk_id, exc)
        return False


def get_memory_stats() -> dict:
    """Return count of stored memory chunks."""
    vm = get_vector_memory()
    if not vm.is_available():
        return {"total": 0}
    try:
        return vm.get_stats()
    except Exception:
        return {"total": 0}
