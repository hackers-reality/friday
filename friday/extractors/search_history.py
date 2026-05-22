"""
Extract search patterns from Google Takeout MyActivity.
Parses MyActivity/Search/MyActivity.json for query patterns, topics, active hours.
Filters out sensitive queries (health, financial) — never stored.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

from friday.logging_utils import configure_logging
from friday.orchestration_config import ensure_config

logger = configure_logging(__name__)


def _load_sensitive_keywords() -> set[str]:
    cfg = ensure_config()
    return set(cfg.get("memory", {}).get("sensitive_keywords", [
        "symptom", "diagnosis", "prescription", "treatment", "medication",
        "disease", "cancer", "hiv", "std", "suicide", "depression",
        "bank account", "credit card", "ssn", "social security",
        "password", "login", "otp", "2fa",
    ]))


def _is_sensitive(text: str) -> bool:
    low = text.lower()
    for kw in _load_sensitive_keywords():
        if kw in low:
            return True
    return False


def _parse_timestamp_str(ts_str: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None


def _normalize_query(text: str) -> str:
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()[:100]


_QUESTION_PATTERNS = re.compile(
    r"\b(how\s+to|how\s+do|what\s+is|where\s+to|why\s+does|when\s+does|"
    r"can\s+I|should\s+I|is\s+it|are\s+there|do\s+I|does\s+this)\b",
    re.IGNORECASE,
)


def extract_search_history(zip_file) -> list[dict]:
    """Extract search query patterns from MyActivity JSON files."""
    chunks: list[dict] = []

    search_paths = [
        "Takeout/MyActivity/Search/MyActivity.json",
        "Takeout/MyActivity/Search/MyActivity.search.json",
    ]

    records: list[dict] = []
    for spath in search_paths:
        try:
            data = json.loads(zip_file.read(spath))
            records.extend(data if isinstance(data, list) else data.get("items", []))
            logger.info("Loaded %d records from %s", len(records), spath)
        except KeyError:
            continue
        except Exception as exc:
            logger.warning("Failed %s: %s", spath, exc)

    if not records:
        return chunks

    # Also check for Google App search data
    try:
        app_data = json.loads(zip_file.read("Takeout/MyActivity/MyActivity.json"))
        if isinstance(app_data, dict):
            records.extend(app_data.get("items", []))
    except Exception:
        pass

    queries: list[str] = []
    question_queries: list[str] = []
    hour_counter: Counter = Counter()

    for rec in records:
        text = rec.get("title", "").strip()
        # Google formats: "Searched for X" or query as title
        if "Searched for" in text:
            query = text.split("Searched for", 1)[-1].strip().strip('"').strip("'")
        else:
            query = text

        if not query or len(query) < 3:
            continue

        if _is_sensitive(query):
            continue

        normalized = _normalize_query(query)
        queries.append(normalized)

        if _QUESTION_PATTERNS.search(query):
            question_queries.append(normalized)

        ts_str = rec.get("time", "")
        dt = _parse_timestamp_str(ts_str)
        if dt:
            hour_counter[dt.hour] += 1

    if not queries:
        return chunks

    # --- Top search topics ---
    query_counter: Counter = Counter(queries)
    top50 = query_counter.most_common(50)
    if top50:
        lines = [f"  - \"{q}\" ({c}x)" for q, c in top50[:10]]
        chunks.append({
            "content": "User's most frequent search queries:\n" + "\n".join(lines),
            "source": "google_takeout/search_history",
            "category": "interests",
            "confidence": 0.85,
        })

    # --- Question patterns ---
    if len(question_queries) >= 5:
        top_questions = Counter(question_queries).most_common(10)
        lines = [f"  - \"{q}\" ({c}x)" for q, c in top_questions[:5]]
        chunks.append({
            "content": "User often asks questions about:\n" + "\n".join(lines),
            "source": "google_takeout/search_history",
            "category": "interests",
            "confidence": 0.80,
        })

    # --- Active search hours ---
    if hour_counter:
        peak_hour = hour_counter.most_common(1)[0][0]
        period = "AM" if peak_hour < 12 else "PM"
        display_hour = peak_hour if peak_hour <= 12 else peak_hour - 12
        if peak_hour == 0:
            display_hour = 12
        chunks.append({
            "content": f"User is most active searching around {display_hour}{period} "
                       f"(hour {peak_hour}) based on search history.",
            "source": "google_takeout/search_history",
            "category": "habits",
            "confidence": 0.75,
        })

    # --- Topic clusters (word frequency) ---
    word_counter: Counter = Counter()
    for q in queries:
        words = q.split()
        # Skip common stop words
        for w in words:
            if len(w) > 3 and w not in {"the", "this", "that", "with", "from",
                                         "what", "how", "why", "when", "where",
                                         "does", "have", "doesn", "don", "can",
                                         "for", "and", "not", "are", "you"}:
                word_counter[w] += 1

    top_words = word_counter.most_common(20)
    if top_words:
        lines = [f"  - {w} ({c}x)" for w, c in top_words[:10]]
        chunks.append({
            "content": "Recurring topics in user's search history:\n" + "\n".join(lines),
            "source": "google_takeout/search_history",
            "category": "interests",
            "confidence": 0.75,
        })

    return chunks
