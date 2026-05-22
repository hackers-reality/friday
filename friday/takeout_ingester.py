"""
FRIDAY Takeout Ingester — orchestrates extraction from Google Takeout ZIP.
Detects available Google services in the ZIP, dispatches to extractors,
synthesizes results into MemoryChunks, and stores in ChromaDB with dedup.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Thread
from typing import Optional

from friday.context_bus import get_bus
from friday.extractors import (
    extract_youtube_history,
    extract_gmail_sent,
    extract_location_history,
    extract_search_history,
)
from friday.logging_utils import configure_logging
from friday.memory_extractor import synthesize_memory_chunks
from friday.orchestration_config import ensure_config

logger = configure_logging(__name__)


@dataclass
class IngestionReport:
    zip_name: str
    services_found: list[str] = field(default_factory=list)
    chunks_added: int = 0
    chunks_skipped_dedup: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


def _detect_services(zf: zipfile.ZipFile) -> list[str]:
    names = set(zf.namelist())
    services = []
    if any("Takeout/YouTube" in n for n in names):
        services.append("youtube_history")
    if any("Takeout/Mail" in n for n in names):
        services.append("gmail_sent")
    if any("Takeout/Location History" in n for n in names):
        services.append("location_history")
    if any("Takeout/MyActivity" in n for n in names):
        services.append("search_history")
    return services


def _publish_progress(percent: float, status: str):
    try:
        import asyncio
        asyncio.run(get_bus().publish("memory.ingestion.progress", {
            "percent": percent,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }))
    except Exception:
        pass


class TakeoutIngester:
    """Process one Takeout ZIP at a time. Run in background thread."""

    def __init__(self):
        self._running = False

    def ingest(self, zip_path: Path) -> IngestionReport:
        """Process a single Takeout ZIP. Returns report."""
        report = IngestionReport(zip_name=zip_path.name)
        import time
        t0 = time.time()

        try:
            with zipfile.ZipFile(str(zip_path)) as zf:
                services = _detect_services(zf)
                report.services_found = services
                _publish_progress(5, f"Detected services: {', '.join(services)}")

                all_raw: list[dict] = []
                total_services = len(services)
                for i, svc in enumerate(services):
                    try:
                        if svc == "youtube_history":
                            chunks = extract_youtube_history(zf)
                        elif svc == "gmail_sent":
                            chunks = extract_gmail_sent(zf)
                        elif svc == "location_history":
                            chunks = extract_location_history(zf)
                        elif svc == "search_history":
                            chunks = extract_search_history(zf)
                        else:
                            continue
                        all_raw.extend(chunks)
                        logger.info("Extracted %d chunks from %s", len(chunks), svc)
                    except Exception as exc:
                        report.errors.append(f"{svc}: {exc}")
                        logger.exception("Extractor failed: %s", svc)

                    pct = 10 + int((i + 1) / total_services * 60)
                    _publish_progress(pct, f"Extracted: {svc}")

                _publish_progress(75, "Synthesizing memory chunks...")
                result = synthesize_memory_chunks(all_raw)
                report.chunks_added = result["added"]
                report.chunks_skipped_dedup = result["skipped_dedup"]
                report.errors.extend(result["errors"])

        except zipfile.BadZipFile:
            report.errors.append("Bad ZIP file")
        except Exception as exc:
            report.errors.append(str(exc))
            logger.exception("Takeout ingestion failed: %s", exc)

        report.duration_seconds = round(time.time() - t0, 2)
        _publish_progress(100, f"Complete: {report.chunks_added} chunks added")
        logger.info("Takeout ingestion complete: %s", report)
        return report

    def ingest_async(self, zip_path: Path, callback=None):
        """Run ingestion in background thread."""
        def _run():
            self._running = True
            report = self.ingest(zip_path)
            self._running = False
            if callback:
                try:
                    callback(report)
                except Exception:
                    pass

        Thread(target=_run, name="TakeoutIngester", daemon=True).start()


def _auto_ingest_new_takeouts():
    """Utility: find unprocessed ZIPs and ingest them."""
    from friday.takeout_watcher import TAKEOUT_DIR, PROCESSED_DIR, _is_valid_takeout_zip
    ingester = TakeoutIngester()
    for fpath in sorted(TAKEOUT_DIR.iterdir()):
        if fpath.name.endswith(".zip") and _is_valid_takeout_zip(fpath):
            report = ingester.ingest(fpath)
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            dest = PROCESSED_DIR / f"{ts}_{fpath.name}"
            fpath.rename(dest)
            logger.info("Auto-ingested %s: %d chunks", fpath.name, report.chunks_added)
