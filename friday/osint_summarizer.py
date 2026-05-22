"""
FRIDAY OSINT Summarizer — compiles raw OSINT scan results into
a human-readable summary via NIM call (summarization task type).

Full report saved to /friday_reports/osint_{target}_{timestamp}.md
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from friday.logging_utils import configure_logging
from friday.nim_client import InferenceClient
from friday.nim_router import resolve_model

logger = configure_logging(__name__)

_REPORTS_DIR = Path("friday_reports")


def _format_sherlock(result: dict) -> str:
    found = result.get("found", [])
    not_found = result.get("not_found", [])
    lines = [f"## Sherlock — Username: {result.get('username', '?')}"]
    lines.append(f"Scan time: {result.get('scan_time_s', 0)}s")
    if result.get("timed_out"):
        lines.append("⚠ Timed out — partial results")
    if found:
        lines.append(f"\n**Found on {len(found)} platforms:**")
        for p in found[:20]:
            lines.append(f"- {p.get('platform')}: {p.get('url')}")
    if not_found:
        lines.append(f"\n**Not found on {len(not_found)} platforms**")
    if not found and not not_found:
        lines.append("\nNo results returned.")
    return "\n".join(lines)


def _format_exiftool(result: dict) -> str:
    lines = ["## ExifTool — Metadata Extraction"]
    lines.append(f"File: {result.get('file_path', '?')}")
    if not result.get("success"):
        lines.append(f"Error: {result.get('error', 'Unknown')}")
        return "\n".join(lines)

    if result.get("has_gps"):
        lines.append(f"\n⚠ **GPS Location Found**")
        lines.append(f"  Coordinates: {result.get('gps_latitude')}, {result.get('gps_longitude')}")
        if result.get("location_name"):
            lines.append(f"  Approx: {result['location_name']}")
    if result.get("camera_make") or result.get("camera_model"):
        lines.append(f"\n**Camera:** {result.get('camera_make', '')} {result.get('camera_model', '')}")
    if result.get("datetime_original"):
        lines.append(f"**Captured:** {result['datetime_original']}")
    if result.get("software"):
        lines.append(f"**Software:** {result['software']}")
        if result.get("is_edited"):
            lines.append("⚠ Image has been edited")
    if result.get("has_sensitive_metadata"):
        lines.append("\n⚠ Warning: Image contains sensitive metadata (GPS, timestamps)")
    return "\n".join(lines)


def _format_spiderfoot(result: dict) -> str:
    entities = result.get("entities", [])
    threats = result.get("threats", [])
    lines = [f"## SpiderFoot — Target: {result.get('target', '?')}"]
    lines.append(f"Scan ID: {result.get('scan_id', '?')}")
    lines.append(f"Duration: {result.get('scan_duration_s', 0)}s")
    if result.get("timed_out"):
        lines.append("⚠ Timed out — partial results")
    if result.get("error"):
        lines.append(f"Error: {result['error']}")
    if threats:
        lines.append(f"\n### Threats ({len(threats)} found)")
        for t in threats[:15]:
            lines.append(f"- [{t.get('threat_type')}] {t.get('entity')} — {t.get('description', '')}")
    if entities:
        lines.append(f"\n### Entities ({len(entities)} found)")
        by_type: dict[str, int] = {}
        for e in entities:
            by_type[e.get("entity_type", "UNKNOWN")] = by_type.get(e.get("entity_type", "UNKNOWN"), 0) + 1
        for etype, count in sorted(by_type.items()):
            lines.append(f"- {etype}: {count}")
        lines.append("\n**Sample entities:**")
        for e in entities[:10]:
            lines.append(f"- {e.get('entity_type')}: {e.get('data', e.get('name', ''))}")
    if not entities and not threats and not result.get("error"):
        lines.append("\nNo entities or threats discovered.")
    return "\n".join(lines)


async def generate_osint_summary(
    raw_results: dict[str, Any],
    use_nim: bool = True,
) -> str:
    """
    Compile OSINT scan results into a human-readable summary.

    If use_nim is True, the summary is enhanced via NIM LLM call.
    Full report saved to friday_reports/.
    """
    target = raw_results.get("_target", "unknown")
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_filename = f"osint_{target}_{timestamp}.md"

    # Build sections
    sections = []

    sherlock = raw_results.get("sherlock")
    if sherlock:
        sections.append(_format_sherlock(sherlock))

    exiftool = raw_results.get("exiftool")
    if exiftool:
        sections.append(_format_exiftool(exiftool))

    spiderfoot = raw_results.get("spiderfoot")
    if spiderfoot:
        sections.append(_format_spiderfoot(spiderfoot))

    if not sections:
        sections.append("## No OSINT results to summarize.")

    raw_text = "\n\n---\n\n".join(sections)

    # NIM enhancement (optional)
    if use_nim:
        try:
            client = InferenceClient()
            model = resolve_model("summarization") or "meta/llama-3.3-70b-instruct"
            summary_prompt = (
                "You are Friday, an AI assistant. Summarize this OSINT scan result "
                f"for the user. Be concise, highlight threats and key findings.\n\nData:\n{raw_text[:4000]}"
            )
            response = await client.chat(
                model=model,
                messages=[{"role": "user", "content": summary_prompt}],
                max_tokens=1024,
            )
            if response.content and "error" not in response.content.lower():
                summary = response.content.strip()
                raw_text = f"## AI Summary\n\n{summary}\n\n---\n\n{raw_text}"
        except Exception as exc:
            logger.warning("NIM summarization failed: %s", exc)

    # Save report
    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = _REPORTS_DIR / report_filename
    report_path.write_text(raw_text, encoding="utf-8")
    logger.info("OSINT report saved to %s", report_path)

    return raw_text
