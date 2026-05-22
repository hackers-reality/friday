"""
FRIDAY Takeout Watcher — monitors /data/takeout/ for new Google Takeout ZIPs
using watchdog. Validates and queues for ingestion.
"""

from __future__ import annotations

import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from threading import Event, Thread
from typing import Optional

from friday._paths import FRIDAY_MEMORY
from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

TAKEOUT_DIR = Path(FRIDAY_MEMORY) / "takeout"
PROCESSED_DIR = TAKEOUT_DIR / "processed"


def _ensure_dirs():
    TAKEOUT_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def _is_valid_takeout_zip(path: Path) -> bool:
    """Check that a ZIP file contains a 'Takeout/' root directory."""
    import zipfile
    try:
        with zipfile.ZipFile(str(path)) as zf:
            names = zf.namelist()
            return any(n.startswith("Takeout/") for n in names)
    except zipfile.BadZipFile:
        return False
    except Exception:
        return False


class TakeoutWatcher:
    """Watch /data/takeout/ for new Google Takeout ZIPs using watchdog."""

    def __init__(self, callback=None):
        _ensure_dirs()
        self._callback = callback
        self._stop_event = Event()
        self._thread: Optional[Thread] = None
        self._seen: set[str] = set()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = Thread(target=self._poll_loop, name="TakeoutWatcher", daemon=True)
        self._thread.start()
        logger.info("Takeout watcher started (polling %s)", TAKEOUT_DIR)

    def stop(self):
        self._stop_event.set()

    def _poll_loop(self):
        _ensure_dirs()
        while not self._stop_event.is_set():
            try:
                for fpath in sorted(TAKEOUT_DIR.iterdir()):
                    if not fpath.name.endswith(".zip"):
                        continue
                    if fpath.name in self._seen:
                        continue
                    if not _is_valid_takeout_zip(fpath):
                        logger.warning("Invalid Takeout ZIP (skipping): %s", fpath.name)
                        self._seen.add(fpath.name)
                        continue
                    self._seen.add(fpath.name)
                    logger.info("New Takeout ZIP detected: %s", fpath.name)
                    if self._callback:
                        try:
                            self._callback(fpath)
                        except Exception as exc:
                            logger.exception("Takeout callback failed: %s", exc)
            except Exception as exc:
                logger.warning("Takeout poll error: %s", exc)
            time.sleep(30)

    def mark_processed(self, path: Path):
        """Move processed ZIP to processed/ with timestamp prefix."""
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        dest = PROCESSED_DIR / f"{ts}_{path.name}"
        try:
            shutil.move(str(path), str(dest))
            logger.info("Moved processed Takeout: %s -> %s", path.name, dest.name)
        except Exception as exc:
            logger.warning("Failed to move processed Takeout: %s", exc)
