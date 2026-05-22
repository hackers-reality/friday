"""
FRIDAY Memory Extractor — synthesizes raw extraction data into structured
MemoryChunks, deduplicates against ChromaDB, and stores them.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Optional

from friday.logging_utils import configure_logging
from friday.vector_memory import get_vector_memory

logger = configure_logging(__name__)

_DEDUP_SIM_THRESHOLD = 0.92


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _is_duplicate(content: str, vm) -> bool:
    """Check ChromaDB for similar existing chunks."""
    if not vm or not vm.is_available():
        return False
    try:
        results = vm.search(content, n_results=3)
        if not results or "ids" not in results:
            return False
        for i, chunk_id in enumerate(results["ids"]):
            distances = results.get("distances", [])
            if distances and len(distances[0]) > i:
                # ChromaDB distance: lower = more similar. 0 = identical.
                if distances[0][i] < (1 - _DEDUP_SIM_THRESHOLD):
                    return True
    except Exception:
        pass
    return False


def synthesize_memory_chunks(raw_chunks: list[dict]) -> dict:
    """
    Take raw extraction output, deduplicate, and store in ChromaDB.

    Raw chunk format: {content, source, category, confidence}
    Stored chunk enriches with: extracted_at, id, hash

    Returns: {added: int, skipped_dedup: int, errors: list[str]}
    """
    result: dict[str, Any] = {"added": 0, "skipped_dedup": 0, "errors": []}

    if not raw_chunks:
        return result

    vm = get_vector_memory()
    if not vm.is_available():
        result["errors"].append("ChromaDB not available. Chunks not stored.")
        return result

    now = datetime.utcnow().isoformat()
    for chunk in raw_chunks:
        content = chunk.get("content", "").strip()
        if not content or len(content) < 20:
            continue

        # Dedup check
        if _is_duplicate(content, vm):
            result["skipped_dedup"] += 1
            continue

        # Build metadata
        chunk_id = f"takeout_{_content_hash(content)}_{result['added']}"
        metadata = {
            "source": chunk.get("source", "unknown"),
            "category": chunk.get("category", "general"),
            "confidence": chunk.get("confidence", 0.5),
            "extracted_at": now,
            "chunk_id": chunk_id,
        }

        try:
            vm.add(text=content, metadata=metadata, id=chunk_id)
            result["added"] += 1
        except Exception as exc:
            result["errors"].append(f"ChromaDB add failed: {exc}")
            logger.warning("Failed to store chunk: %s", exc)

    logger.info("Memory synthesis complete: %d added, %d dedup-skipped",
                result["added"], result["skipped_dedup"])
    return result
