# FRIDAY Architecture Manifest

## Overview
FRIDAY is a Windows-native, Iron-Man-inspired personal AI OS assistant built on top of Gemini Live API with 76+ modules, 150+ tools, and comprehensive memory/authority/autonomy systems.

## Root Structure
- `FRIDAY_MANIFEST.md` — This file. The architectural map. Do not delete.
- `friday/` — All FRIDAY modules (76 Python files)
- `friday_memory/` — Persistent memory: user profile, vector DB, episodic, sidecars, snapshots, authority logs
- `friday_reports/` — Auto-generated reports (capability matrix, etc.)
- `friday_plugins/` — Plugin directory
- `test_*.py` — Comprehensive test suites (10 files, 169+ tests)

## Core Architecture
- `friday/live.py` — Main event loop: Gemini Live API ↔ tools ↔ memory ↔ hooks
- `friday/tools.py` — 150+ tool wrappers across 15+ categories
- `friday/hooks.py` — Pre/post/error hook system (logging, KG, KYU, episodic, skills)
- `friday/memory_import.py` — Full memory pipeline: import → extract → TF-IDF → audit → clean → confidence → inject
- `friday/authority.py` — Tool risk classification (9 levels), configurable policy, audit log
- `friday/autonomy.py` — Durable task queue with retry/reflection/pause
- `friday/sidecar.py` — Sidecar registry and heartbeat
- `friday/snapshots.py` — File/directory snapshot with restore and diff
- `friday/tool_registry.py` — Central metadata for all 150+ tools
- `friday/capabilities.py` — Capability matrix (40+ systems)
- `friday/dashboard_api.py` — REST API (17 endpoints, port 8090)
- `friday/dashboard.py` — HTML dashboard (port 8080)

## Key Capabilities
- **Voice**: Gemini Live bidirectional audio streaming (stable)
- **Vision**: Screen capture, analysis, vision-click (stable)
- **Memory**: Profile extraction, TF-IDF, vector search, episodic FTS5, knowledge graph, confidence scoring, redaction, conflict detection, decay, review, doctor (stable)
- **Desktop Control**: Mouse, keyboard, app/window management (stable)
- **Browser Control**: OpenCLI-based automation, multi-tab, eval (stable)
- **Code**: Deep AI code review, file generation, self-modification (stable)
- **GitHub**: Full API (files, PRs, issues, repos, search) (stable)
- **Smart Home**: Alexa, Home Assistant, IoT (partial)
- **Self-Improvement**: Skill auto-creation, reflection, improvement queue (stable)
- **Dashboard**: HTML UI + JSON REST API (stable)

## Rules for Self-Modification
1. Always read the relevant docs/ files before making changes.
2. Run tests after every change: `python test_memory_context.py` + all `test_*.py`
3. Run compile check: `python -m compileall -q friday`
4. Commit small coherent units with clear messages.
5. Never commit secrets, .env files, tokens, or personal memory data.