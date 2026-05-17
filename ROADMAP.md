# FRIDAY Roadmap

## v0.1 — Foundation (Done)
- [x] Voice interface with Gemini Live API
- [x] 140+ tools (system, browser, files, GitHub, apps)
- [x] Web search, video search, deep research
- [x] Screen vision + vision-click
- [x] Spotify, Alexa, Home Assistant integrations
- [x] Email (Gmail/Outlook), Instagram DM
- [x] Calendar, goals, workflow engine
- [x] Memory store/retrieve + vector memory
- [x] Multi-agent delegation
- [x] Scheduler, notifications, monitoring
- [x] Hooks system, snapshots, tool registry

## v0.2 — Personal AI OS (Current)
- [x] Camera CV Engine — real-time object detection, people tracking, scene analysis
- [x] Sidecar Network — LAN device discovery, JWT auth, remote command dispatch
- [x] Installable Sidecar Package — pip-installable `friday-sidecar` CLI agent
- [x] Iron Man Features — `damage_report`, `suit_check`, `morning_plan`, `evening_review`
- [x] Profile Schema Validation — JSON Schema for `user_profile.json`
- [x] Authority & Safety — pre-hook enforcement, mode switching, risk classification
- [x] Dashboard API — HTTP API with 23 endpoints, sidecar registration, CV context
- [x] Tool Capabilities Registry — capability matrix with status tracking
- [x] **Memory Tree** — persistent Markdown knowledge base with daily notes and backlinks
- [x] **Model Router** — multi-provider abstraction with fallback, cost tracking, health checks
- [x] **Extension/MCP Registry** — extension lifecycle management, capability discovery
- [x] **FRIDAY CLI** — `doctor`, `status`, `memory-tree`, `sidecar`, `snapshots`, `suit-check`, `damage-report`, etc.
- [x] **Diagnostics & Benchmarks** — system health checks, I/O/JSON/dict benchmarks
- [x] **Documentation** — GETTING_STARTED.md, CLI.md, EXTENSIONS.md, ROADMAP.md

## v0.3 — Memory & Learning (Next)
- [ ] **Episodic Memory** — structured event logging with embeddings-based retrieval
- [ ] **Progressive Learning** — extract patterns from sessions, build user model
- [ ] **Self-Learning Mode** — identify gaps, schedule practice, improve predictions
- [ ] **Memory Tree auto-tagging** — automated metadata + NLP tagging for knowledge pages
- [ ] **Conversation search** — full-text + semantic search over all past sessions

## v0.4 — Agents & Autonomy (Planned)
- [ ] **Autonomous Task Execution** — multi-step tasks with progress tracking (expand beyond current queue)
- [ ] **Background Agents** — persistent agents for monitoring, research, learning
- [ ] **Agent Recipes** — composable agent workflows with failure handling
- [ ] **Multi-Model Orchestration** — route sub-tasks to optimal models automatically
- [ ] **Sandboxed Code Execution** — Docker-based secure execution environment

## v0.5 — Developer Platform (Planned)
- [ ] **MCP Protocol SDK** — create MCP servers with Python decorators
- [ ] **Extension Marketplace** — community extension sharing via GitHub
- [ ] **Plugin API** — first-class plugin system with lifecycle hooks
- [ ] **Webhook System** — FRIDAY-triggered webhooks for integration
- [ ] **CLI Package** — `pip install friday-cli` for global access

## v0.6 — Deployment (Planned)
- [ ] **Docker Deployment** — single-container FRIDAY server
- [ ] **Headless Mode** — server-only operation without local GUI
- [ ] **API Tokens** — authenticated API access for external apps
- [ ] **Multi-User Support** — profile switching, user-specific memory
- [ ] **Remote Dashboard** — web-based full control panel

## v1.0 — Sovereign AI (Vision)
- [ ] **Offline Mode** — local LLM inference via llama.cpp or similar
- [ ] **Personal Knowledge Graph** — entity extraction + relationship mapping
- [ ] **Cross-Device Sync** — sync memory tree/snapshots across devices
- [ ] **Proactive Assistant** — anticipate needs, suggest actions, auto-schedule
- [ ] **Performance Optimization** — memory use, startup time, tool latency

## Backlog
- [ ] AR/VR interface for Iron Man HUD
- [ ] Smart glasses integration
- [ ] Voice cloning for FRIDAY's responses
- [ ] Multi-language support
- [ ] Emotion-aware responses
- [ ] Local RAG with personal documents
- [ ] Privacy mode — full local inference
- [ ] Mobile companion app

## Contributing

See [GitHub issues](https://github.com/hackers-reality/friday/issues) for current priorities.
Pull requests welcome — please maintain test coverage.
