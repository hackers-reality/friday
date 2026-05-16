# FRIDAY Iron Man Features

A practical take on Jarvis/FRIDAY-style features from the Iron Man films.

## Implemented

| Feature | Module | Status |
|---------|--------|--------|
| **Voice Interface** | `live.py` + `voice.py` | Stable - bidirectional Gemini Live |
| **Vision/See Screen** | `vision.py` + `screen_watcher.py` | Stable - real-time screen analysis |
| **Memory (Knows You)** | `memory_import.py` + `memory_context.py` | Stable - user profile, vector, episodic |
| **Tool-Rich** | `tools.py` (150+ tools) | Stable - desktop, browser, code, GitHub, etc. |
| **Proactive Briefing** | `dashboard_api.py` (`/api/briefing`) | Stable - memory/system/task status |
| **System Health** | `dashboard_api.py` (`/api/system`) | Stable - CPU, RAM, disk, processes |
| **Mission/Objective** | `dashboard_api.py` (`/api/mission`) | Stable - FRIDAY_MANIFEST.md driven |
| **Capability Matrix** | `capabilities.py` | Stable - 40+ capabilities documented |
| **Self-Improvement** | `self_modify.py` + `skills.py` | Stable - auto-create skills from sequences |
| **Reflection** | `reflection.py` | Stable - learn from tool call patterns |
| **Dreaming** | `dreaming.py` | Stable - generative creativity mode |
| **Scheduling** | `scheduler.py` | Stable - cron-like task scheduling |
| **Goals/OKRs** | `goals.py` | Stable - goal management |
| **Knowledge Graph** | `knowledge_graph.py` | Stable - entity-relation triple store |
| **System Protector** | `protector.py` | Stable - anti-shutdown/sleep/lid-close |
| **Crash Watcher** | `crash_watcher.py` | Stable - auto-detect and diagnose crashes |
| **Notifications** | `notify.py` | Stable - desktop notifications |
| **Black Box (Audit)** | `authority.py` (log) + `hooks.py` | Stable - all decisions logged |
| **Dashboard** | `dashboard.py` + `dashboard_api.py` | Stable - monitoring and control |
| **Workspace Awareness** | `dashboard_api.py` (`/api/workspace`) | Stable - module/file discovery |

## Partial

| Feature | Module | Limitation |
|---------|--------|------------|
| **Multi-Agent** | `multi_agent.py` | Basic delegate only |
| **Smart Home** | Alexa/HA integrations | Requires external setup |
| **Proactive Mode** | `proactivity.py` | Needs tuning |
| **Sidecar Agents** | `sidecar.py` | Dispatch skeleton only |
| **Mobile** | `sidecar.py` (placeholder) | Not implemented |

## Planned

| Feature | Notes |
|---------|-------|
| **Damage Report** | Consolidate errors/failures into structured report |
| **Suit Check** | Verify all systems operational at startup |
| **Focus Guardian** | Detect distraction patterns and suggest focus |
| **Morning Plan** | Auto-generate daily plan from goals and calendar |
| **Evening Review** | Auto-summarize day's activity |
| **What Changed** | Compare current state to last session |
| **Tool Failure Recovery** | Suggest fixes for failing tools |
| **Self-Benchmark** | Compare performance across sessions |
