# FRIDAY Dashboard

## Overview

FRIDAY provides two web interfaces for monitoring and control: an HTML dashboard and a REST API.

## HTML Dashboard (`dashboard.py`)

- **Port**: 8080
- **Type**: Self-contained inline HTML/JS
- **Status**: Stable
- **Auto-refresh**: 30 seconds
- **Panels**: System status, command input, modules, quick actions, AI chat, metrics

### To Start

```python
from friday.dashboard import dashboard_tool
dashboard_tool("start", port=8080)
```

Or directly: `python friday/dashboard.py`

## REST API (`dashboard_api.py`)

- **Port**: 8090
- **Type**: JSON REST API
- **Status**: Stable
- **Auth**: Localhost-only (127.0.0.1)
- **Format**: All endpoints return JSON

### Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Basic health check (status, version, uptime) |
| `GET /api/state` | FRIDAY's operational state (mode, tools, memory) |
| `GET /api/tools` | Tool registry summary (counts by category) |
| `GET /api/tasks` | Autonomy task queue (recent tasks) |
| `GET /api/memory/status` | Memory subsystem health (profile, vector, episodic) |
| `GET /api/memory/doctor` | Full memory diagnostic report |
| `GET /api/memory/review` | Review queue items needing attention |
| `GET /api/authority` | Authority policy (mode, risk levels, blocked tools) |
| `GET /api/snapshots` | Snapshot list (recent snapshots) |
| `GET /api/sidecars` | Sidecar registry (all registered sidecars) |
| `GET /api/goals` | Goals/productivity status |
| `GET /api/system` | System health (CPU, RAM, disk, processes) |
| `GET /api/logs/recent` | Recent tool call log entries |
| `GET /api/capabilities` | Capability matrix summary |
| `GET /api/mission` | Current mission/objective |
| `GET /api/briefing` | Proactive briefing data |
| `GET /api/workspace` | Workspace info (modules, test files) |

### To Start

```python
from friday.dashboard_api import dashboard_api_tool
dashboard_api_tool("start", port=8090)
```

## Legacy API (`api.py`)

- **Port**: 8000
- **Type**: FastAPI/Flask skeleton (most endpoints not wired)
- **Status**: Partial - endpoints are aspirational

## Integration

Neither dashboard is currently wired into the main Friday startup loop. They must be started explicitly via tools or direct execution.
