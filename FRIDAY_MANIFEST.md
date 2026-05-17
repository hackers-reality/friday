# FRIDAY Architecture Manifest

## Overview
FRIDAY is a Windows-native, Iron-Man-inspired personal AI OS assistant built on top of Gemini Live API with 80+ modules, 160+ tools, and comprehensive memory/authority/autonomy/sidecar/CV systems.

## Root Structure
- `FRIDAY_MANIFEST.md` — This file. The architectural map. Do not delete.
- `friday/` — All FRIDAY modules (80+ Python files)
- `friday_memory/` — Persistent memory: user profile, vector DB, episodic, sidecars, snapshots, authority logs, CV state, sidecar network
- `friday_reports/` — Auto-generated reports (capability matrix, etc.)
- `friday_plugins/` — Plugin directory
- `sidecar_package/` — Installable sidecar package for remote devices
- `test_*.py` — Comprehensive test suites (15 files, 245+ tests)

## Core Architecture
- `friday/live.py` — Main event loop: Gemini Live API ↔ tools ↔ memory ↔ hooks
- `friday/tools.py` — 150+ tool wrappers across 15+ categories
- `friday/hooks.py` — Pre/post/error hook system (logging, KG, KYU, episodic, skills, authority enforcement, auto-snapshot)
- `friday/memory_import.py` — Full memory pipeline: import → extract → TF-IDF → audit → clean → confidence → inject
- `friday/authority.py` — Tool risk classification (9 levels), configurable policy, audit log
- `friday/autonomy.py` — Durable task queue with retry/reflection/pause
- `friday/sidecar.py` — Sidecar registry, heartbeat, HTTP remote dispatch, local command execution
- `friday/sidecar_network.py` — UDP multicast discovery, HMAC-based JWT token auth, token management
- `friday/snapshots.py` — File/directory snapshot with restore and diff
- `friday/tool_registry.py` — Central metadata for all 150+ tools
- `friday/capabilities.py` — Capability matrix (40+ systems), `capabilities_tool`
- `friday/dashboard_api.py` — REST API (19 endpoints, port 8090), POST support for sidecar registration
- `friday/dashboard.py` — HTML dashboard (port 8080) with 12+ panels
- `friday/ironman.py` — Iron Man features: damage_report, suit_check, morning_plan, evening_review
- `friday/cv_engine.py` — Background camera capture, OpenCV DNN object detection (MobileNet-SSD, COCO 80 classes), HOG people detection, motion detection, scene analysis. LLM-only — not shown to user.
- `friday/profile_schema.py` — JSON Schema validation for user_profile.json
- `friday/startup.py` — Windows startup integration, background service launcher

## Key Capabilities
- **Voice**: Gemini Live bidirectional audio streaming (stable)
- **Vision**: Screen capture, analysis, vision-click, **camera CV** (background object detection, people counting, motion detection, scene labeling — LLM only) (stable)
- **Memory**: Profile extraction, TF-IDF, vector search, episodic FTS5, knowledge graph, confidence scoring, redaction, conflict detection, decay, review, doctor, profile schema validation (stable)
- **Desktop Control**: Mouse, keyboard, app/window management (stable)
- **Browser Control**: OpenCLI-based automation, multi-tab, eval (stable)
- **Code**: Deep AI code review, file generation, self-modification (stable)
- **GitHub**: Full API (files, PRs, issues, repos, search) (stable)
- **Smart Home**: Alexa, Home Assistant, IoT (partial)
- **Self-Improvement**: Skill auto-creation, reflection, improvement queue (stable)
- **Dashboard**: HTML UI + JSON REST API (stable)
- **Iron Man**: Damage report with risk scoring, pre-flight suit check, morning briefing, evening review (stable)
- **Sidecar Network**: UDP multicast discovery, HMAC-JWT auth, remote command dispatch, installable sidecar package (stable)

## New in v0.2
- `friday/cv_engine.py` — Background camera CV (OpenCV DNN, MobileNet-SSD, HOG, motion detection). Runs silently; LLM consumes context via `cv_tool("context")`
- `friday/sidecar_network.py` — Network discovery (UDP multicast), token generation/verification (HMAC-based JWT, no PyJWT dep), no-expiry token support
- `friday/ironman.py` — `damage_report()`, `suit_check()`, `morning_plan()`, `evening_review()` with JSONL history
- `friday/profile_schema.py` — JSON Schema validation for user_profile.json
- `sidecar_package/` — `pip install .` → `friday-sidecar --server URL --token TOKEN` for remote devices
- Authority enforcement + auto-snapshot via hook system
- Dashboard API: POST `/api/sidecars/register`, `/api/sidecars/heartbeat`, GET `/api/cv`
- CV context integrated into `situational_awareness()` for LLM consumption
- All 245 tests pass, all modules compile clean

## Rules for Self-Modification
1. Always read the relevant docs/ files before making changes.
2. Run tests after every change: `python -m unittest discover -p "test_*.py"`
3. Run compile check: `python -m compileall -q friday`
4. Commit small coherent units with clear messages.
5. Never commit secrets, .env files, tokens, or personal memory data.