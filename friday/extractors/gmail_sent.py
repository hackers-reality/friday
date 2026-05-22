"""
Extract communication patterns from Gmail Sent mailbox.
Uses mailbox.mbox (stdlib). NEVER stores email body content — only metadata.
"""

from __future__ import annotations

import mailbox
import re
import tempfile
import subprocess
from collections import Counter
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Optional

from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

_SENSITIVE_DOMAINS = {"info", "noreply", "notification", "newsletter", "mailer"}


def _is_sent_folder(name: str) -> bool:
    low = name.lower()
    return "sent" in low or "outbox" in low or "send" in low


def _domain_from_email(email_addr: str) -> str:
    match = re.search(r"@([\w.-]+)", email_addr)
    return match.group(1).lower() if match else ""


def _topic_from_subject(subj: str) -> Optional[str]:
    clean = re.sub(r"^(Re|Fwd|Fw):\s*", "", subj, flags=re.IGNORECASE).strip()
    if not clean or len(clean) < 4:
        return None
    return clean[:80]


def _readability_score(text: str) -> float:
    """Simple readability: avg words per sentence (higher = more formal/complex)."""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s for s in sentences if len(s.split()) > 1]
    if not sentences:
        return 0.0
    words = sum(len(s.split()) for s in sentences)
    return round(words / len(sentences), 1)


def extract_gmail_sent(zip_file, mbox_path: Optional[str] = None) -> list[dict]:
    """
    Extract Gmail Sent metadata from Takeout ZIP.
    Supports both direct MBOX extraction and pre-extracted MBOX path.
    """
    chunks: list[dict] = []

    mbox_data: Optional[bytes] = None
    if not mbox_path:
        # Try to find MBOX in Takeout structure
        mbox_candidates = [
            "Takeout/Mail/Sent.mbox",
            "Takeout/Mail/Sent.mbox/mbox",
            "Takeout/Mail/Sent.mbox/Sent.mbox",
        ]
        for cand in mbox_candidates:
            try:
                mbox_data = zip_file.read(cand)
                logger.info("Found MBOX at %s", cand)
                break
            except KeyError:
                continue
        if mbox_data is None:
            return chunks
    else:
        mbox_path_obj = Path(mbox_path)
        if mbox_path_obj.exists():
            mbox_data = mbox_path_obj.read_bytes()

    if not mbox_data:
        return chunks

    # Parse MBOX from bytes (supports large files via temp file)
    try:
        with tempfile.NamedTemporaryFile(suffix=".mbox", delete=False) as tmp:
            tmp.write(mbox_data)
            tmp_path = tmp.name

        mbox = mailbox.mbox(tmp_path)
        recipient_counter: Counter = Counter()
        subject_counter: Counter = Counter()
        lengths: list[int] = []
        total_words = 0
        total_sents = 0
        count = 0

        for msg in mbox:
            if count >= 2000:
                break
            to = str(msg.get("To", ""))
            cc = str(msg.get("Cc", ""))
            recipients = re.findall(r"[\w.%-]+@[\w.-]+[\w]", to + "," + cc)
            subj = str(msg.get("Subject", ""))

            # Skip auto-generated
            if any(d in subj.lower() for d in ("auto-reply", "out of office", "delivery")):
                continue

            for addr in recipients:
                domain = _domain_from_email(addr)
                if domain and domain.split(".")[0] not in _SENSITIVE_DOMAINS:
                    recipient_counter[addr] += 1

            topic = _topic_from_subject(subj)
            if topic:
                subject_counter[topic[:60]] += 1

            body_parts: list[str] = []
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body_parts.append(payload.decode("utf-8", errors="replace"))
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body_parts.append(payload.decode("utf-8", errors="replace"))

            body_text = " ".join(body_parts)
            word_count = len(body_text.split())
            lengths.append(word_count)
            total_words += word_count
            total_sents += len(re.split(r"[.!?]+", body_text))
            count += 1

        Path(tmp_path).unlink(missing_ok=True)

        if count == 0:
            return chunks

        # --- Top recipients ---
        top_recipients = recipient_counter.most_common(10)
        if top_recipients:
            lines = [f"  - {addr} ({cnt} emails)" for addr, cnt in top_recipients[:5]]
            chunks.append({
                "content": "User's most frequent email contacts:\n" + "\n".join(lines),
                "source": "google_takeout/gmail_sent",
                "category": "relationships",
                "confidence": 0.80,
            })

        # --- Common topics ---
        top_topics = subject_counter.most_common(10)
        if top_topics:
            lines = [f"  - \"{subj[:50]}\" ({cnt}x)" for subj, cnt in top_topics[:5]]
            chunks.append({
                "content": "Common email subject topics from sent mail:\n" + "\n".join(lines),
                "source": "google_takeout/gmail_sent",
                "category": "interests",
                "confidence": 0.70,
            })

        # --- Communication style ---
        avg_len = round(total_words / max(count, 1))
        readability = _readability_score(" ".join(str(s) for s in subject_counter.elements()))
        style = "formal" if readability > 20 else "casual" if readability < 12 else "mixed"
        chunks.append({
            "content": f"User's email communication style is {style} "
                       f"(avg {avg_len} words/email, readability score {readability}).",
            "source": "google_takeout/gmail_sent",
            "category": "communication_style",
            "confidence": 0.75,
        })

    except Exception as exc:
        logger.warning("Failed to parse MBOX: %s", exc)

    return chunks
