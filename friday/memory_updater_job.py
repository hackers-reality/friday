"""
FRIDAY Memory Updater Job — daily APScheduler job that:
- Re-runs extractors on new processed Takeout data
- Prunes MemoryChunks older than retention period
- Reports stats to context bus
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from friday._paths import FRIDAY_MEMORY
from friday.context_bus import get_bus
from friday.logging_utils import configure_logging
from friday.orchestration_config import ensure_config
from friday.vector_memory import get_vector_memory

logger = configure_logging(__name__)


def _get_retention_days() -> int:
    cfg = ensure_config()
    return int(cfg.get("memory", {}).get("retention_days", 365))


def run_memory_upkeep() -> dict:
    """
    Run the daily memory upkeep job.
    Returns report dict with chunks_pruned, total_chunks.
    """
    report = {"chunks_pruned": 0, "total_chunks": 0, "errors": []}

    vm = get_vector_memory()
    if not vm.is_available():
        report["errors"].append("ChromaDB unavailable")
        return report

    retention_days = _get_retention_days()
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    cutoff_str = cutoff.isoformat()

    # ChromaDB doesn't support date-range deletion natively.
    # Workaround: scan all, identify old ones, delete by ID.
    try:
        all_data = vm._collection.get(include=["metadatas"])
        if all_data and all_data.get("ids"):
            old_ids = []
            for i, meta in enumerate(all_data["metadatas"]):
                extracted = (meta or {}).get("extracted_at", "")
                if extracted and extracted < cutoff_str:
                    old_ids.append(all_data["ids"][i])

            if old_ids:
                for chunk_id in old_ids:
                    try:
                        vm.delete(chunk_id)
                        report["chunks_pruned"] += 1
                    except Exception as exc:
                        report["errors"].append(f"Delete failed {chunk_id}: {exc}")

            # Get updated total
            stats = vm.get_stats()
            report["total_chunks"] = stats.get("count", stats.get("total", 0))

    except Exception as exc:
        report["errors"].append(str(exc))
        logger.exception("Memory upkeep failed: %s", exc)

    # Push event to context bus
    try:
        import asyncio
        asyncio.run(get_bus().publish("memory.upkeep.complete", {
            "report": report,
            "timestamp": datetime.utcnow().isoformat(),
        }))
    except Exception:
        pass

    logger.info("Memory upkeep complete: %s", report)
    return report


def run_memory_upkeep_sync() -> dict:
    """Synchronous wrapper for the scheduler."""
    return run_memory_upkeep()
