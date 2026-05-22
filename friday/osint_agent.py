"""
FRIDAY OSINT Agent — "Ghost"
Registered agent with task_type=osint for reconnaissance operations.

Wraps Sherlock, ExifTool, and SpiderFoot as async tools.
Feeds all discovered entities and relationships into the knowledge graph.
Exposes natural language interface to Gemini Live.

Natural language triggers:
  "Friday, find [username] on social media" → sherlock
  "Friday, analyze this photo's metadata" → exiftool
  "Friday, scan [IP/domain] for threats" → spiderfoot
  "Friday, show me what you know about [entity]" → graph_query
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Optional

from friday.base_agent import BaseAgent, AgentDef, AgentTask, AgentResult
from friday.context_bus import get_bus
from friday.graph_builder import get_graph_builder
from friday.logging_utils import configure_logging
from friday.nim_client import InferenceClient
from friday.nim_router import classify_task_type, resolve_model
from friday.osint_summarizer import generate_osint_summary
from friday.tools.exiftool_tool import ExifResult, run_exiftool, strip_metadata
from friday.tools.sherlock_tool import SherlockResult, run_sherlock
from friday.tools.spiderfoot_tool import SpiderFootResult, run_spiderfoot

logger = configure_logging(__name__)


class GhostAgent(BaseAgent):
    """
    FRIDAY's OSINT intelligence agent — Ghost.

    Routes task.payload to the correct OSINT tool based on
    task.task_type or content heuristics.
    """

    def __init__(self, defn: AgentDef):
        super().__init__(defn)
        self._bus = get_bus()
        self._graph = get_graph_builder()

    async def execute(self, task: AgentTask) -> AgentResult:
        t0 = time.monotonic()
        await self._bus.publish("agent.started", {
            "agent_id": self.id,
            "task_id": task.task_id,
            "task_type": task.task_type,
        })

        try:
            task_type = task.task_type or classify_task_type(task.payload)

            if task_type in ("username_lookup", "sherlock"):
                result = await self._do_sherlock(task)
            elif task_type in ("image_analysis", "exiftool"):
                result = await self._do_exiftool(task)
            elif task_type in ("ip_scan", "domain_scan", "spiderfoot"):
                result = await self._do_spiderfoot(task)
            elif task_type in ("graph_query", "osint_query"):
                result = await self._do_graph_query(task)
            elif task_type == "strip_metadata":
                result = await self._do_strip_metadata(task)
            elif task_type == "osint_scan":
                # Multi-tool OSINT scan based on payload heuristics
                result = await self._do_multi_scan(task)
            else:
                result = AgentResult(
                    task_id=task.task_id, agent_id=self.id,
                    status="failed",
                    error=f"Unknown OSINT task_type: {task_type}",
                    duration_ms=int((time.monotonic() - t0) * 1000),
                )

            result.duration_ms = int((time.monotonic() - t0) * 1000)
            await self._bus.publish(
                "agent.completed" if result.status == "completed" else "agent.failed",
                {"agent_id": self.id, "task_id": task.task_id, "output": result.output[:500]},
            )
            return result

        except Exception as exc:
            logger.exception("Ghost agent execution failed: %s", exc)
            dur = int((time.monotonic() - t0) * 1000)
            await self._bus.publish("agent.failed", {
                "agent_id": self.id, "task_id": task.task_id, "error": str(exc),
            })
            return AgentResult(
                task_id=task.task_id, agent_id=self.id,
                status="failed", error=str(exc), duration_ms=dur,
            )

    # ── Sherlock ─────────────────────────────────────────────

    async def _do_sherlock(self, task: AgentTask) -> AgentResult:
        username = task.payload.strip() if task.payload else ""
        if not username or len(username) > 64:
            return AgentResult(
                task_id=task.task_id, agent_id=self.id,
                status="failed", error="Invalid or empty username",
            )

        result: SherlockResult = await run_sherlock(username)

        # Feed into graph
        for profile in result.found:
            self._graph.add_social_profile(username, profile.platform, profile.url)

        # Format output
        lines = [f"## Sherlock Scan: @{username}"]
        lines.append(f"Scanned {len(result.found) + len(result.not_found)} platforms in {result.scan_time_s}s")
        if result.timed_out:
            lines.append("⚠ Scan timed out — results may be partial")
        if result.found:
            lines.append(f"\n**Found on {len(result.found)} platforms:**")
            for p in result.found[:30]:
                lines.append(f"- {p.platform}: {p.url}")
        if result.not_found:
            lines.append(f"\n**Not found on {len(result.not_found)} platforms**")
        if not result.found and not result.timed_out:
            lines.append("\nNo accounts found for this username on any checked platform.")

        output = "\n".join(lines)

        return AgentResult(
            task_id=task.task_id, agent_id=self.id,
            status="completed", output=output,
        )

    # ── ExifTool ─────────────────────────────────────────────

    async def _do_exiftool(self, task: AgentTask) -> AgentResult:
        file_path = task.context_snapshot.get("file_path", task.payload.strip())
        if not file_path:
            return AgentResult(
                task_id=task.task_id, agent_id=self.id,
                status="failed", error="No file path provided. Drop an image or specify a path.",
            )

        exif: ExifResult = await run_exiftool(file_path, reverse_geocode=True)

        # Feed into graph
        if exif.success:
            self._graph.add_entity(str(Path(file_path).name), "IMAGE", {
                "path": file_path,
                "camera": f"{exif.camera_make or ''} {exif.camera_model or ''}".strip(),
                "captured": exif.datetime_original or "",
                "has_gps": exif.has_gps,
            })
            if exif.has_gps:
                self._graph.add_entity(
                    f"coord_{round(exif.gps_latitude or 0, 4)}_{round(exif.gps_longitude or 0, 4)}",
                    "LOCATION",
                    {"lat": exif.gps_latitude, "lon": exif.gps_longitude,
                     "name": exif.location_name or ""},
                )

        # Format output
        lines = [f"## ExifTool: {Path(file_path).name}"]
        if not exif.success:
            lines.append(f"Error: {exif.error}")
        else:
            if exif.has_gps:
                lines.append(f"\n⚠ **GPS: {exif.gps_latitude}, {exif.gps_longitude}**")
                if exif.location_name:
                    lines.append(f"   Location: {exif.location_name}")
            if exif.camera_make or exif.camera_model:
                lines.append(f"**Camera:** {exif.camera_make or ''} {exif.camera_model or ''}".strip())
            if exif.datetime_original:
                lines.append(f"**Captured:** {exif.datetime_original}")
            if exif.software:
                edit_warn = " (edited)" if exif.is_edited else ""
                lines.append(f"**Software:** {exif.software}{edit_warn}")
            if exif.has_sensitive_metadata:
                lines.append("\n**Sensitive metadata detected.** You can strip it with /strip.")

        output = "\n".join(lines) if lines else "No metadata extracted."

        return AgentResult(
            task_id=task.task_id, agent_id=self.id,
            status="completed" if exif.success else "failed",
            output=output,
        )

    async def _do_strip_metadata(self, task: AgentTask) -> AgentResult:
        file_path = task.context_snapshot.get("file_path", task.payload.strip())
        if not file_path:
            return AgentResult(
                task_id=task.task_id, agent_id=self.id,
                status="failed", error="No file path provided.",
            )

        strip_result = await strip_metadata(file_path)
        if strip_result.get("success"):
            return AgentResult(
                task_id=task.task_id, agent_id=self.id,
                status="completed",
                output=f"Metadata stripped from {file_path}. All EXIF data removed.",
            )
        return AgentResult(
            task_id=task.task_id, agent_id=self.id,
            status="failed", error=strip_result.get("error", "Strip failed"),
        )

    # ── SpiderFoot ───────────────────────────────────────────

    async def _do_spiderfoot(self, task: AgentTask) -> AgentResult:
        target = task.payload.strip() if task.payload else task.context_snapshot.get("target", "")
        if not target:
            return AgentResult(
                task_id=task.task_id, agent_id=self.id,
                status="failed", error="No target provided. Specify an IP, domain, or email.",
            )

        scan_type = task.context_snapshot.get("scan_type") or self._infer_scan_type(target)
        sf_result: SpiderFootResult = await run_spiderfoot(target, scan_type=scan_type)

        # Feed into graph
        for entity in sf_result.entities:
            etype = entity.entity_type
            if "IP" in etype:
                self._graph.add_entity(f"ip_{entity.name}", "IP", {"address": entity.name})
            elif "DOMAIN" in etype:
                self._graph.add_entity(f"domain_{entity.name}", "DOMAIN", {"domain": entity.name})
            elif "EMAIL" in etype:
                self._graph.add_entity(f"email_{entity.name}", "EMAIL", {"email": entity.name})

        # Format output
        lines = [f"## SpiderFoot Scan: {target}"]
        lines.append(f"Scan type: {scan_type}")
        lines.append(f"Duration: {sf_result.scan_duration_s}s")
        if sf_result.error:
            lines.append(f"Error: {sf_result.error}")
        if sf_result.timed_out:
            lines.append("⚠ Scan timed out — partial results")

        if sf_result.threats:
            lines.append(f"\n### Threats ({len(sf_result.threats)})")
            for t in sf_result.threats[:15]:
                lines.append(f"- [{t.threat_type}] {t.entity}")
        if sf_result.entities:
            lines.append(f"\n### Entities Found ({len(sf_result.entities)})")
            by_type: dict[str, int] = {}
            for e in sf_result.entities:
                by_type[e.entity_type] = by_type.get(e.entity_type, 0) + 1
            for etype, count in sorted(by_type.items()):
                lines.append(f"- {etype}: {count}")

        output = "\n".join(lines)
        status = "completed" if not sf_result.error else "failed"

        return AgentResult(
            task_id=task.task_id, agent_id=self.id,
            status=status, output=output,
        )

    # ── Graph Query ──────────────────────────────────────────

    async def _do_graph_query(self, task: AgentTask) -> AgentResult:
        entity_id = task.payload.strip()
        if not entity_id:
            # Return full graph stats
            stats = self._graph.get_stats()
            lines = ["## OSINT Knowledge Graph"]
            lines.append(f"Total entities: {stats.get('total_nodes', 0)}")
            lines.append(f"Total relationships: {stats.get('total_edges', 0)}")
            if stats.get("node_types"):
                lines.append("\nBy type:")
                for ntype, count in stats["node_types"].items():
                    lines.append(f"- {ntype}: {count}")
            output = "\n".join(lines)
        else:
            result = self._graph.query_entity(entity_id)
            if "error" in result:
                # Try fuzzy search via KnowledgeGraph
                kg = self._graph._kg
                matches = kg.search_nodes(entity_id)
                if matches:
                    lines = [f"Entities matching '{entity_id}':"]
                    for m in matches[:10]:
                        lines.append(f"- {m.id} ({m.type})")
                    output = "\n".join(lines)
                else:
                    output = f"No entity found matching '{entity_id}'."
            else:
                entity = result.get("entity", {})
                rels = result.get("relationships", [])
                lines = [f"## Entity: {entity.get('id', '?')}"]
                lines.append(f"Type: {entity.get('type', '?')}")
                props = entity.get("properties", {})
                if props:
                    lines.append("Properties:")
                    for k, v in props.items():
                        lines.append(f"- {k}: {v}")
                if rels:
                    lines.append(f"\nRelationships ({len(rels)}):")
                    for r in rels[:20]:
                        lines.append(f"- {r.get('relation')} -> {r.get('target_id')} ({r.get('target_type')})")
                output = "\n".join(lines)

        return AgentResult(
            task_id=task.task_id, agent_id=self.id,
            status="completed", output=output,
        )

    # ── Multi-scan ───────────────────────────────────────────

    async def _do_multi_scan(self, task: AgentTask) -> AgentResult:
        """
        Run multiple OSINT tools based on payload heuristics.
        Returns NIM-summarized report.
        """
        payload = task.payload.strip()
        raw_results: dict[str, Any] = {"_target": payload[:50]}

        # Sherlock if it looks like a username
        if payload and len(payload.split()) == 1 and not payload.replace(".", "").isdigit():
            sherlock_result = await run_sherlock(payload)
            raw_results["sherlock"] = {
                "username": payload,
                "found": [{"platform": p.platform, "url": p.url} for p in sherlock_result.found],
                "not_found": sherlock_result.not_found[:20],
                "scan_time_s": sherlock_result.scan_time_s,
                "timed_out": sherlock_result.timed_out,
            }

        # SpiderFoot if IP/domain
        scan_type = self._infer_scan_type(payload)
        if scan_type:
            sf_result = await run_spiderfoot(payload, scan_type=scan_type, timeout=120)
            raw_results["spiderfoot"] = {
                "target": payload,
                "scan_id": sf_result.scan_id,
                "entities": [{"entity_type": e.entity_type, "data": e.data, "name": e.name}
                             for e in sf_result.entities[:50]],
                "threats": [{"threat_type": t.threat_type, "entity": t.entity, "description": t.description}
                            for t in sf_result.threats[:50]],
                "scan_duration_s": sf_result.scan_duration_s,
                "timed_out": sf_result.timed_out,
                "error": sf_result.error,
            }

        # Generate summary
        summary = await generate_osint_summary(raw_results, use_nim=True)

        return AgentResult(
            task_id=task.task_id, agent_id=self.id,
            status="completed", output=summary[:4000],
            model=resolve_model("summarization") or "meta/llama-3.3-70b-instruct",
        )

    # ── Helpers ──────────────────────────────────────────────

    @staticmethod
    def _infer_scan_type(target: str) -> str:
        """Heuristic to determine scan type from target string."""
        target = target.strip().lower()
        # Email
        if "@" in target and "." in target.split("@")[-1]:
            return "email_scan"
        # IP address
        parts = target.replace(".", " ").split()
        if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
            return "ip_scan"
        # Domain
        if "." in target and not target.startswith("http"):
            return "domain_scan"
        return ""
