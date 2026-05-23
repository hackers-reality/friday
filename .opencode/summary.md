# FRIDAY Sovereign AI — Project Summary

## Self-Monitoring & Health System (Just Built)

### Core Architecture

- **`friday/health_monitor.py`** (NEW) — Unified Health Monitor singleton that aggregates health data from all subsystems. Components register check functions; the monitor runs them periodically, publishes snapshots to the context bus (`system.health_snapshot` topic), persists state to `friday_memory/health_state.json`, and exposes a `health_monitor_tool()` for the Gemini agent.

  - Default registered checks: `system_resources` (CPU/memory), `browser`, `context_bus`, `disk_space`, `active_monitors`.
  - `health_monitor_tool(action)` supports: `status`, `alerts`, `components`, `refresh`.

- **`friday/terminal_health_display.py`** (NEW) — ASCII health dashboard builder. `build_health_dashboard(snapshot)` returns a color-coded terminal display. `compact_status_line()` returns a one-liner. `print_dashboard()` prints directly.

### Extended Files

- **`friday/browser_manager.py`** — Added **pyppeteer backend** (child process Chrome + CDP). `start(backend="pyppeteer")` launches Chrome as a subprocess with `--remote-debugging-port` and `--user-data-dir` pointing to the existing profile, then connects via `pyppeteer.connect()`. Falls back to Playwright if pyppeteer not available. Configurable via `config.yaml browser.backend` (auto/pyppeteer/playwright). Added `health_check()` method.

- **`friday/monitor.py`** — Added app-level health checks: `check_browser_health()`, `check_agent_health()`, `check_websocket_health()`, `app_health_report()`. Added `_publish_to_health_monitor()` to forward system alerts to the health monitor. `monitor_tool("app_health")` shows app-level health.

- **`friday/proactivity_monitor.py`** — Extended with `_get_health_context()` method that reads health monitor snapshot and enriches the AI vision prompt with system health state. Health-aware proactive comments (e.g., "System healthy", "Browser degraded").

- **`friday/diagnostics.py`** — Added `check_subsystem_interconnect()` to verify all subsystems can communicate. Added `deep_diagnostics()` for comprehensive deep-diagnostic including health monitor snapshot and performance benchmarks. Extended `diagnostics_tool()` with `deep` and `interconnect` actions.

- **`friday/morning_briefing.py`** — Extended `build_briefing()` to include system health section (overall status, uptime, today's alerts) alongside YouTube analytics.

- **`friday/tools.py`** — Rewrote `send_instagram_dm()` to use `browser_manager` (Playwright or pyppeteer CDP) instead of fragile `pygetwindow`/`pyautogui`. Now works headlessly, inherits existing Chrome sessions.

- **`friday/live.py`** — Added `health_monitor_tool` to imports, `_build_tools()`, and `TOOL_MAP`. Added `friday.health_monitor`, `friday.terminal_health_display` to module preload list.

### Dependency Added

- `pyppeteer>=1.0.2` in `requirements.txt`

### Key Design Decisions

- Health Monitor is a **pull-based registry**: components register check functions, the monitor calls them periodically. No component needs to know about the monitor (except for alert forwarding).
- Browser supports **dual backend**: pyppeteer child-process CDP (default) and Playwright (fallback). Both inherit the user's Chrome profile.
- All health data is published to the **context bus** (`system.health_snapshot`) so the AI agent, proactive speaker, and terminal display all read from one source.
- Deep diagnostics (`diagnostics_tool("deep")`) ties together standard diagnostics, subsystem interconnectivity checks, health monitor snapshot, and performance benchmarks.
