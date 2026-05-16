"""
Friday Capability Report — generate a comprehensive capability matrix for FRIDAY.

Outputs a markdown report at friday_reports/capability_report.md with
stable/partial/experimental/planned statuses for all major systems.
"""

from __future__ import annotations
from typing import Dict, List, Optional
import json
import os
from datetime import datetime

from friday._paths import FRIDAY_MEMORY

_REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "friday_reports")
os.makedirs(_REPORTS_DIR, exist_ok=True)

CAPABILITY_REPORT_FILE = os.path.join(_REPORTS_DIR, "capability_report.md")


CAPABILITIES: Dict[str, dict] = {
    "voice": {
        "status": "stable",
        "description": "Gemini Live bidirectional voice streaming (input/output), audio capture via microphone, PCM processing, speech-to-text and text-to-speech",
        "dependencies": ["Gemini API key", "microphone", "speakers"],
        "notes": "Uses gemini-2.0-flash-live for real-time voice. TTS fallback via gTTS/pyttsx3.",
    },
    "vision": {
        "status": "stable",
        "description": "Screen capture, image analysis, vision-click coordination, real-time screen watching",
        "dependencies": ["PIL", "screen capture access"],
        "notes": "Supports screenshot + LLM analysis for visual grounding. Integrated with click/type tools.",
    },
    "desktop_control": {
        "status": "stable",
        "description": "Mouse control (click, drag, scroll), keyboard (type, hotkey, press), app launch/close, window management, clipboard",
        "dependencies": ["pyautogui", "psutil"],
        "notes": "Safe hotkey blocking for dangerous combos. Whitelist-based safe command execution.",
    },
    "browser_control": {
        "status": "stable",
        "description": "OpenCLI-based browser automation with navigation, click, type, extract, screenshot, tabs, eval, network monitoring",
        "dependencies": ["OpenCLI v1.7.18+"],
        "notes": "Bidirectional bridge. --session required for all commands. Supports multi-tab.",
    },
    "memory_profile": {
        "status": "stable",
        "description": "Chat history import (Claude, ChatGPT, Gemini), TF-IDF NLP analysis, extractors for 20+ profile fields, confidence scoring, profile cleaning/validation/repair",
        "dependencies": ["None (pure Python TF-IDF)"],
        "notes": "Version 5+ profile with _confidence metadata. Atomic save with .bak. Repair action available.",
    },
    "memory_vector": {
        "status": "stable",
        "description": "ChromaDB semantic vector memory for facts, preferences, patterns, profile indexing",
        "dependencies": ["chromadb"],
        "notes": "Graceful fallback if ChromaDB unavailable. Profile auto-indexed after audit.",
    },
    "memory_episodic": {
        "status": "stable",
        "description": "SQLite FTS5 full-text session search, auto-recording of tool calls, session recall",
        "dependencies": ["None (SQLite3 built-in)"],
        "notes": "FTS5 for fast search. All tool calls auto-archived via hooks.",
    },
    "memory_context": {
        "status": "stable",
        "description": "[USER MEMORY] system prompt injection, [RELEVANT MEMORY CONTEXT] per-query retrieval, source-labeled blocks, 30s cooldown",
        "dependencies": ["memory_profile", "memory_vector", "memory_episodic"],
        "notes": "Confidence-gated scalar injection (>=0.5). Per-item confidence filtering (>=0.3).",
    },
    "memory_redaction": {
        "status": "stable",
        "description": "Sensitive text redaction for emails, tokens, API keys, JWTs, private IPs, webhooks, phone, SSN, CC numbers",
        "dependencies": ["re (built-in)"],
        "notes": "Regex-based with multiple pattern types. Returns [REDACTED_*] labels.",
    },
    "memory_conflicts": {
        "status": "stable",
        "description": "Age/location/name conflict detection across audit history, cross-category duplicate detection, auto-resolution with dedup",
        "dependencies": ["None"],
        "notes": "Conflicts flagged in doctor report. Resolution keeps most-confident value.",
    },
    "memory_decay": {
        "status": "stable",
        "description": "Aged memory removal (>10 audits without reconfirmation), stale scalar warnings, pinned item exemption",
        "dependencies": ["None"],
        "notes": "Pinned items in profile._pinned[] are spared. Manual decay_profile action.",
    },
    "memory_review": {
        "status": "stable",
        "description": "Review queue for conflicts, low-confidence items, flagged memory. Approve/reject/pin/unpin via tool actions.",
        "dependencies": ["None"],
        "notes": "Items with confidence <0.4 flagged. Doctor reports review queue status.",
    },
    "memory_doctor": {
        "status": "stable",
        "description": "Full diagnostic: validation + conflict scan + decay preview + review queue + redaction test + profile size",
        "dependencies": ["All memory subsystems"],
        "notes": "Read-only. One-shot holistic memory health report.",
    },
    "knowledge_graph": {
        "status": "stable",
        "description": "Entity-relation triples extracted from tool results, KG query tool, post-hook auto-extraction",
        "dependencies": ["knowledge_graph.py"],
        "notes": "Integrated via hooks. Filters noisy tools (click, scroll, etc.).",
    },
    "goals_okrs": {
        "status": "stable",
        "description": "Goal management, OKR tracking, task queue, parallel multi-task, scheduler",
        "dependencies": ["goals.py", "scheduler.py"],
        "notes": "Full CRUD for goals. Queue with status tracking.",
    },
    "sidecars": {
        "status": "stable",
        "description": "Sidecar registry, heartbeat, capability reporting, command dispatch skeleton, disk persistence",
        "dependencies": ["None"],
        "notes": "Supports 8 sidecar types. Dispatch skeleton for local/remote. JSON persistence.",
    },
    "autonomy": {
        "status": "stable",
        "description": "Durable task queue with retry, reflection, pause/resume, auto-retry with backoff, task summary",
        "dependencies": ["None"],
        "notes": "JSON persistence. Retry policy per task. Failed tasks auto-retry or escalate.",
    },
    "authority": {
        "status": "stable",
        "description": "Risk classification (9 levels), configurable policy, decision engine, dry_run/block_all modes, audit log, per-permission controls",
        "dependencies": ["tool_registry (optional)"],
        "notes": "Deepcopy default to prevent mutation. Snapshot-before-destructive flag.",
    },
    "snapshots": {
        "status": "stable",
        "description": "File/directory snapshots with SHA-256 hashing, restore, diff (file-level and directory-level), indexed JSON registry",
        "dependencies": ["shutil", "hashlib"],
        "notes": "Stable snapshot IDs. Prune support available but not auto-run.",
    },
    "tool_registry": {
        "status": "stable",
        "description": "Central metadata for 150+ tools with category, risk level, description. Introspection API, consistency checker.",
        "dependencies": ["None"],
        "notes": "Consistency check requires live TOOL_MAP reference. All tools have valid risk/category.",
    },
    "code_review": {
        "status": "stable",
        "description": "Deep AI code review (4 actions: analyze/fix/new_project/fork_pr), Gemini-powered review reports",
        "dependencies": ["Gemini API key"],
        "notes": "Uses gemini-3.1-flash-lite (5s pacing for free tier).",
    },
    "github": {
        "status": "stable",
        "description": "Full GitHub API integration: files, PRs, issues, repos, branches, commits, search, auth",
        "dependencies": ["PyGitHub", "GitHub token"],
        "notes": "OAuth-based auth. Self-modify capability via github_self_modify.",
    },
    "gmail": {
        "status": "stable",
        "description": "Email read, send, draft, OAuth authorization",
        "dependencies": ["Google API credentials"],
        "notes": "OAuth-based. Supports multiple accounts.",
    },
    "spotify": {
        "status": "stable",
        "description": "Play/pause/next/prev/volume control, current playback status",
        "dependencies": ["spotipy"],
        "notes": "Keyboard fallback if API unavailable.",
    },
    "smart_home": {
        "status": "partial",
        "description": "Alexa command/poll, Home Assistant command, smart home command",
        "dependencies": ["Alexa skill", "Home Assistant instance"],
        "notes": "Alexa integration requires skill setup. HA requires instance URL/token.",
    },
    "instagram": {
        "status": "partial",
        "description": "Instagram DM sending",
        "dependencies": ["instagram_bot.py"],
        "notes": "Basic send-only. No message history or media support.",
    },
    "self_improvement": {
        "status": "stable",
        "description": "Self-modify codebase via GitHub, self-improvement queue, skill auto-creation from repeated tool sequences",
        "dependencies": ["GitHub token", "self_modify.py"],
        "notes": "Safety-validated code generation. Skill auto-creation at 3-seq threshold.",
    },
    "reflection": {
        "status": "stable",
        "description": "Self-reflection on recent tool calls, pattern detection, improvement suggestions",
        "dependencies": ["reflection.py"],
        "notes": "Triggers periodically based on call count threshold.",
    },
    "dreaming": {
        "status": "stable",
        "description": "Generative dreaming/creativity mode, dream tool, random thought generation",
        "dependencies": ["Gemini API key"],
        "notes": "Lightweight creative exploration mode.",
    },
    "proactivity": {
        "status": "partial",
        "description": "Proactive suggestion engine, predictive tool call patterns, habit detection",
        "dependencies": ["proactivity.py", "predictive.py"],
        "notes": "Basic pattern recording. Full proactive mode needs tuning.",
    },
    "monitoring": {
        "status": "stable",
        "description": "System monitor (CPU, RAM, disk, network, processes), crash watcher, screen watcher, protector (anti-sleep, anti-shutdown)",
        "dependencies": ["psutil", "protector.py"],
        "notes": "Win32-specific protector. Lid-close/shutdown/Ctrl+C blocking.",
    },
    "skills": {
        "status": "stable",
        "description": "Custom skill management, creation, deletion, listing, auto-creation from tool sequences",
        "dependencies": ["skills.py"],
        "notes": "Skills stored as Python functions. Auto-created from repeated sequences.",
    },
    "workflows": {
        "status": "stable",
        "description": "Multi-step workflow definition, execution, management",
        "dependencies": ["workflow.py"],
        "notes": "Step-by-step execution with state tracking.",
    },
    "plugins": {
        "status": "partial",
        "description": "Plugin management and loading",
        "dependencies": ["plugins.py"],
        "notes": "Basic plugin support. Needs expansion for third-party plugins.",
    },
    "mcp": {
        "status": "stable",
        "description": "Model Context Protocol bridge for Claude Desktop-style tool integration",
        "dependencies": ["mcp.py", "mcp_bridge.py", "mcp_enhanced.py"],
        "notes": "Bidirectional MCP communication. Supports tool definitions and resource access.",
    },
    "dashboard": {
        "status": "stable",
        "description": "HTML dashboard (port 8080), REST API (port 8000, FastAPI/Flask), inline frontend, real-time status",
        "dependencies": ["http.server (built-in)"],
        "notes": "Dashboard is self-contained. API skeleton exists but needs endpoint wiring. Dashboard and API not wired into main startup.",
    },
    "startup": {
        "status": "stable",
        "description": "Module auto-loading, dependency checks, graceful degradation, startup report",
        "dependencies": ["startup.py"],
        "notes": "Imports and verifies all Friday modules at boot. Reports failures without crashing.",
    },
    "kyu_adaptation": {
        "status": "stable",
        "description": "Know Your User personality adaptation, session-level and persistent learning",
        "dependencies": ["kyu.py"],
        "notes": "Adapts response style based on user interaction patterns.",
    },
    "scheduler": {
        "status": "stable",
        "description": "Task scheduling, cron-like timed execution, one-shot and recurring tasks",
        "dependencies": ["scheduler.py"],
        "notes": "Persistent schedule storage. Supports datetime and interval triggers.",
    },
    "notifications": {
        "status": "stable",
        "description": "Desktop notifications, pending notification queue, send/get/clear",
        "dependencies": ["notify.py"],
        "notes": "Windows toast notifications via win10toast or plyer.",
    },
    "multi_agent": {
        "status": "partial",
        "description": "Sub-agent delegation, parallel task execution, agent coordination",
        "dependencies": ["multi_agent.py"],
        "notes": "Basic delegate. Advanced orchestration planned.",
    },
    "security": {
        "status": "partial",
        "description": "Port scanning, SSL analysis, hash checking, password strength, DNS security checks",
        "dependencies": ["security.py"],
        "notes": "Read-only security analysis tools. No system hardening.",
    },
    "code_generation": {
        "status": "stable",
        "description": "File generation from templates (generate_file), LLM-powered code generation (generate_file_llm)",
        "dependencies": ["filegen.py"],
        "notes": "Template-based and LLM-based generation with safety validation.",
    },
    "research": {
        "status": "stable",
        "description": "Deep multi-step research (deep_research), web search, video search",
        "dependencies": ["research.py", "web_search tool"],
        "notes": "Multi-step research with summarization. Engine fallback chain.",
    },
    "reasoning": {
        "status": "stable",
        "description": "Multi-step reasoning chain, structured thought process, chain-of-thought",
        "dependencies": ["reasoning.py"],
        "notes": "Step-by-step reasoning with intermediate results.",
    },
    "crash_handling": {
        "status": "stable",
        "description": "Crash detection, analysis, recovery suggestions, crash_watcher background monitoring",
        "dependencies": ["crash_watcher.py"],
        "notes": "Detects process crashes and Friday errors. Suggests recovery steps.",
    },
    "stayfree": {
        "status": "partial",
        "description": "Stayfree digital wellness integration (status, today stats, week stats)",
        "dependencies": ["Stayfree app + API"],
        "notes": "Read-only. Requires Stayfree desktop app running.",
    },
    "browser_history": {
        "status": "stable",
        "description": "Browser history search, open history item, recent history listing",
        "dependencies": ["browser_history.py"],
        "notes": "Reads Chrome/Edge SQLite history databases directly.",
    },
    "multi_task": {
        "status": "partial",
        "description": "Parallel task execution across multiple sub-agents",
        "dependencies": ["multi_task in tools.py"],
        "notes": "Basic concurrency. Limited to tool calls.",
    },
}


def generate_capability_report() -> str:
    """Generate the full capability report markdown."""
    now = datetime.now().isoformat()[:19]
    lines = [
        f"# FRIDAY Capability Report",
        f"",
        f"_Generated: {now}_",
        f"",
        "This report documents all major FRIDAY systems, their stability status, dependencies, and limitations.",
        "",
        "## Status Key",
        "",
        "| Status | Meaning |",
        "|--------|---------|",
        "| **stable** | Works reliably in production |",
        "| **partial** | Works but has known limitations |",
        "| **experimental** | Recently added, may have rough edges |",
        "| **planned** | Not yet implemented |",
        "",
        "---",
        "",
    ]

    # Group by status
    by_status: Dict[str, list] = {}
    for name, info in sorted(CAPABILITIES.items()):
        s = info.get("status", "planned")
        by_status.setdefault(s, []).append((name, info))

    for status in ("stable", "partial", "experimental", "planned"):
        items = by_status.get(status, [])
        if not items:
            continue
        lines.append(f"## {status.capitalize()} ({len(items)})")
        lines.append("")
        for name, info in items:
            deps = info.get("dependencies", [])
            dep_str = f"  - *Dependencies: {', '.join(deps)}*" if deps else ""
            notes = info.get("notes", "")
            notes_str = f"  - _{notes}_" if notes else ""
            lines.extend([
                f"### {name}",
                f"",
                f"{info.get('description', '')}",
                dep_str,
                notes_str,
                "",
            ])
        lines.append("---")
        lines.append("")

    total = len(CAPABILITIES)
    stable_count = len(by_status.get("stable", []))
    partial_count = len(by_status.get("partial", []))
    experimental_count = len(by_status.get("experimental", []))
    planned_count = len(by_status.get("planned", []))

    lines.extend([
        "## Summary",
        "",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Total capabilities | {total} |",
        f"| Stable | {stable_count} |",
        f"| Partial | {partial_count} |",
        f"| Experimental | {experimental_count} |",
        f"| Planned | {planned_count} |",
        f"| Coverage | {stable_count/total*100:.0f}% stable |",
        "",
    ])

    report = "\n".join(lines)

    # Write to file
    try:
        with open(CAPABILITY_REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(report)
    except Exception:
        pass

    return report


def get_capability_status(capability: str) -> Optional[str]:
    """Get the status of a specific capability."""
    info = CAPABILITIES.get(capability)
    if info:
        return info.get("status", "unknown")
    return None


def list_capabilities(status: str = "") -> list:
    """List all capabilities, optionally filtered by status."""
    if status:
        return [(k, v) for k, v in CAPABILITIES.items() if v.get("status") == status]
    return sorted(CAPABILITIES.items())


if __name__ == "__main__":
    print(generate_capability_report())
