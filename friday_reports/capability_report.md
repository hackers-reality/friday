# FRIDAY Capability Report

_Generated: 2026-05-24T10:30:17_

This report documents all major FRIDAY systems, their stability status, dependencies, and limitations.

## Status Key

| Status | Meaning |
|--------|---------|
| **stable** | Works reliably in production |
| **partial** | Works but has known limitations |
| **experimental** | Recently added, may have rough edges |
| **planned** | Not yet implemented |

---

## Stable (41)

### authority

Risk classification (9 levels), configurable policy, decision engine, dry_run/block_all modes, audit log, per-permission controls
  - *Dependencies: tool_registry (optional)*
  - _Deepcopy default to prevent mutation. Snapshot-before-destructive flag._

### autonomy

Durable task queue with retry, reflection, pause/resume, auto-retry with backoff, task summary
  - *Dependencies: None*
  - _JSON persistence. Retry policy per task. Failed tasks auto-retry or escalate._

### browser_control

OpenCLI-based browser automation with navigation, click, type, extract, screenshot, tabs, eval, network monitoring
  - *Dependencies: OpenCLI v1.7.18+*
  - _Bidirectional bridge. --session required for all commands. Supports multi-tab._

### browser_history

Browser history search, open history item, recent history listing
  - *Dependencies: browser_history.py*
  - _Reads Chrome/Edge SQLite history databases directly._

### code_generation

File generation from templates (generate_file), LLM-powered code generation (generate_file_llm)
  - *Dependencies: filegen.py*
  - _Template-based and LLM-based generation with safety validation._

### code_review

Deep AI code review (4 actions: analyze/fix/new_project/fork_pr), Gemini-powered review reports
  - *Dependencies: Gemini API key*
  - _Uses gemini-3.1-flash-lite (5s pacing for free tier)._

### crash_handling

Crash detection, analysis, recovery suggestions, crash_watcher background monitoring
  - *Dependencies: crash_watcher.py*
  - _Detects process crashes and Friday errors. Suggests recovery steps._

### dashboard

HTML dashboard (port 8080), REST API (port 8000, FastAPI/Flask), inline frontend, real-time status
  - *Dependencies: http.server (built-in)*
  - _Dashboard is self-contained. API skeleton exists but needs endpoint wiring. Dashboard and API not wired into main startup._

### desktop_control

Mouse control (click, drag, scroll), keyboard (type, hotkey, press), app launch/close, window management, clipboard
  - *Dependencies: pyautogui, psutil*
  - _Safe hotkey blocking for dangerous combos. Whitelist-based safe command execution._

### dreaming

Generative dreaming/creativity mode, dream tool, random thought generation
  - *Dependencies: Gemini API key*
  - _Lightweight creative exploration mode._

### github

Full GitHub API integration: files, PRs, issues, repos, branches, commits, search, auth
  - *Dependencies: PyGitHub, GitHub token*
  - _OAuth-based auth. Self-modify capability via github_self_modify._

### gmail

Email read, send, draft, OAuth authorization
  - *Dependencies: Google API credentials*
  - _OAuth-based. Supports multiple accounts._

### goals_okrs

Goal management, OKR tracking, task queue, parallel multi-task, scheduler
  - *Dependencies: goals.py, scheduler.py*
  - _Full CRUD for goals. Queue with status tracking._

### knowledge_graph

Entity-relation triples extracted from tool results, KG query tool, post-hook auto-extraction
  - *Dependencies: knowledge_graph.py*
  - _Integrated via hooks. Filters noisy tools (click, scroll, etc.)._

### kyu_adaptation

Know Your User personality adaptation, session-level and persistent learning
  - *Dependencies: kyu.py*
  - _Adapts response style based on user interaction patterns._

### mcp

Model Context Protocol bridge for Claude Desktop-style tool integration
  - *Dependencies: mcp.py, mcp_bridge.py, mcp_enhanced.py*
  - _Bidirectional MCP communication. Supports tool definitions and resource access._

### memory_conflicts

Age/location/name conflict detection across audit history, cross-category duplicate detection, auto-resolution with dedup
  - *Dependencies: None*
  - _Conflicts flagged in doctor report. Resolution keeps most-confident value._

### memory_context

[USER MEMORY] system prompt injection, [RELEVANT MEMORY CONTEXT] per-query retrieval, source-labeled blocks, 30s cooldown
  - *Dependencies: memory_profile, memory_vector, memory_episodic*
  - _Confidence-gated scalar injection (>=0.5). Per-item confidence filtering (>=0.3)._

### memory_decay

Aged memory removal (>10 audits without reconfirmation), stale scalar warnings, pinned item exemption
  - *Dependencies: None*
  - _Pinned items in profile._pinned[] are spared. Manual decay_profile action._

### memory_doctor

Full diagnostic: validation + conflict scan + decay preview + review queue + redaction test + profile size
  - *Dependencies: All memory subsystems*
  - _Read-only. One-shot holistic memory health report._

### memory_episodic

SQLite FTS5 full-text session search, auto-recording of tool calls, session recall
  - *Dependencies: None (SQLite3 built-in)*
  - _FTS5 for fast search. All tool calls auto-archived via hooks._

### memory_profile

Chat history import (Claude, ChatGPT, Gemini), TF-IDF NLP analysis, extractors for 20+ profile fields, confidence scoring, profile cleaning/validation/repair
  - *Dependencies: None (pure Python TF-IDF)*
  - _Version 5+ profile with _confidence metadata. Atomic save with .bak. Repair action available._

### memory_redaction

Sensitive text redaction for emails, tokens, API keys, JWTs, private IPs, webhooks, phone, SSN, CC numbers
  - *Dependencies: re (built-in)*
  - _Regex-based with multiple pattern types. Returns [REDACTED_*] labels._

### memory_review

Review queue for conflicts, low-confidence items, flagged memory. Approve/reject/pin/unpin via tool actions.
  - *Dependencies: None*
  - _Items with confidence <0.4 flagged. Doctor reports review queue status._

### memory_vector

ChromaDB semantic vector memory for facts, preferences, patterns, profile indexing
  - *Dependencies: chromadb*
  - _Graceful fallback if ChromaDB unavailable. Profile auto-indexed after audit._

### monitoring

System monitor (CPU, RAM, disk, network, processes), crash watcher, screen watcher, protector (anti-sleep, anti-shutdown)
  - *Dependencies: psutil, protector.py*
  - _Win32-specific protector. Lid-close/shutdown/Ctrl+C blocking._

### notifications

Desktop notifications, pending notification queue, send/get/clear
  - *Dependencies: notify.py*
  - _Windows toast notifications via win10toast or plyer._

### reasoning

Multi-step reasoning chain, structured thought process, chain-of-thought
  - *Dependencies: reasoning.py*
  - _Step-by-step reasoning with intermediate results._

### reflection

Self-reflection on recent tool calls, pattern detection, improvement suggestions
  - *Dependencies: reflection.py*
  - _Triggers periodically based on call count threshold._

### research

Deep multi-step research (deep_research), web search, video search
  - *Dependencies: research.py, web_search tool*
  - _Multi-step research with summarization. Engine fallback chain._

### scheduler

Task scheduling, cron-like timed execution, one-shot and recurring tasks
  - *Dependencies: scheduler.py*
  - _Persistent schedule storage. Supports datetime and interval triggers._

### self_improvement

Self-modify codebase via GitHub, self-improvement queue, skill auto-creation from repeated tool sequences
  - *Dependencies: GitHub token, self_modify.py*
  - _Safety-validated code generation. Skill auto-creation at 3-seq threshold._

### sidecars

Sidecar registry, heartbeat, capability reporting, command dispatch skeleton, disk persistence
  - *Dependencies: None*
  - _Supports 8 sidecar types. Dispatch skeleton for local/remote. JSON persistence._

### skills

Custom skill management, creation, deletion, listing, auto-creation from tool sequences
  - *Dependencies: skills.py*
  - _Skills stored as Python functions. Auto-created from repeated sequences._

### snapshots

File/directory snapshots with SHA-256 hashing, restore, diff (file-level and directory-level), indexed JSON registry
  - *Dependencies: shutil, hashlib*
  - _Stable snapshot IDs. Prune support available but not auto-run._

### spotify

Play/pause/next/prev/volume control, current playback status
  - *Dependencies: spotipy*
  - _Keyboard fallback if API unavailable._

### startup

Module auto-loading, dependency checks, graceful degradation, startup report
  - *Dependencies: startup.py*
  - _Imports and verifies all Friday modules at boot. Reports failures without crashing._

### tool_registry

Central metadata for 150+ tools with category, risk level, description. Introspection API, consistency checker.
  - *Dependencies: None*
  - _Consistency check requires live TOOL_MAP reference. All tools have valid risk/category._

### vision

Screen capture, image analysis, vision-click coordination, real-time screen watching
  - *Dependencies: PIL, screen capture access*
  - _Supports screenshot + LLM analysis for visual grounding. Integrated with click/type tools._

### voice

Gemini Live bidirectional voice streaming (input/output), audio capture via microphone, PCM processing, speech-to-text and text-to-speech
  - *Dependencies: Gemini API key, microphone, speakers*
  - _Uses gemini-2.0-flash-live for real-time voice. TTS fallback via gTTS/pyttsx3._

### workflows

Multi-step workflow definition, execution, management
  - *Dependencies: workflow.py*
  - _Step-by-step execution with state tracking._

---

## Partial (8)

### instagram

Instagram DM sending
  - *Dependencies: instagram_bot.py*
  - _Basic send-only. No message history or media support._

### multi_agent

Sub-agent delegation, parallel task execution, agent coordination
  - *Dependencies: multi_agent.py*
  - _Basic delegate. Advanced orchestration planned._

### multi_task

Parallel task execution across multiple sub-agents
  - *Dependencies: multi_task in tools.py*
  - _Basic concurrency. Limited to tool calls._

### plugins

Plugin management and loading
  - *Dependencies: plugins.py*
  - _Basic plugin support. Needs expansion for third-party plugins._

### proactivity

Proactive suggestion engine, predictive tool call patterns, habit detection
  - *Dependencies: proactivity.py, predictive.py*
  - _Basic pattern recording. Full proactive mode needs tuning._

### security

Port scanning, SSL analysis, hash checking, password strength, DNS security checks
  - *Dependencies: security.py*
  - _Read-only security analysis tools. No system hardening._

### smart_home

Alexa command/poll, Home Assistant command, smart home command
  - *Dependencies: Alexa skill, Home Assistant instance*
  - _Alexa integration requires skill setup. HA requires instance URL/token._

### stayfree

Stayfree digital wellness integration (status, today stats, week stats)
  - *Dependencies: Stayfree app + API*
  - _Read-only. Requires Stayfree desktop app running._

---

## Summary

| Metric | Count |
|--------|-------|
| Total capabilities | 49 |
| Stable | 41 |
| Partial | 8 |
| Experimental | 0 |
| Planned | 0 |
| Coverage | 84% stable |
