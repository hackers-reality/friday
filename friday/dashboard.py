"""
FRIDAY Dashboard — real-time web dashboard for monitoring and control.
FastAPI-based web server showing:
  - System health (CPU, memory, disk)
  - Agent status (running/idle, last action)
  - Scheduled tasks
  - Episodic memory search
  - Tool usage patterns
  - YouTube analytics
  - Self-improvement history
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime
from typing import Any, Optional

try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.responses import HTMLResponse, JSONResponse
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from friday._paths import FRIDAY_MEMORY

app = FastAPI(title="FRIDAY Dashboard", version="5.3.0") if HAS_FASTAPI else None
_server_thread: Optional[threading.Thread] = None


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FRIDAY Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0a0a1a; color: #e0e0f0; min-height: 100vh; }
        .header { background: linear-gradient(135deg, #1a1a3e, #2a1a4e); padding: 20px 40px; border-bottom: 1px solid #3a2a5e; }
        .header h1 { font-size: 28px; background: linear-gradient(90deg, #8b5cf6, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .header span { color: #8888aa; font-size: 14px; margin-left: 16px; }
        .container { max-width: 1400px; margin: 0 auto; padding: 24px; display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }
        .card { background: #12122a; border: 1px solid #2a2a4a; border-radius: 12px; padding: 20px; transition: border-color 0.3s; }
        .card:hover { border-color: #4a3a7a; }
        .card h2 { font-size: 16px; color: #8b8bcf; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px; }
        .card .value { font-size: 32px; font-weight: 700; color: #fff; }
        .card .label { color: #8888aa; font-size: 12px; margin-top: 4px; }
        .card .row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #1a1a3a; }
        .card .row:last-child { border-bottom: none; }
        .good { color: #4ade80; }
        .warn { color: #fbbf24; }
        .bad { color: #f87171; }
        .info { color: #60a5fa; }
        .btn { background: #2a2a5a; border: 1px solid #3a3a6a; color: #e0e0f0; padding: 6px 16px; border-radius: 6px; cursor: pointer; font-size: 13px; }
        .btn:hover { background: #3a3a7a; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th { text-align: left; color: #8b8bcf; padding: 8px 4px; border-bottom: 1px solid #2a2a4a; }
        td { padding: 6px 4px; border-bottom: 1px solid #1a1a3a; }
        .nav { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
        .nav button { background: #1a1a3a; border: 1px solid #2a2a4a; color: #aaaacc; padding: 8px 20px; border-radius: 8px; cursor: pointer; }
        .nav button:hover, .nav button.active { background: #2a2a5a; border-color: #6b4fa0; color: #fff; }
        .section { display: none; }
        .section.active { display: block; }
        pre { font-family: 'Cascadia Code', 'Fira Code', monospace; font-size: 12px; color: #b0b0d0; overflow-x: auto; max-height: 400px; }
        .footer { text-align: center; color: #555; padding: 20px; font-size: 12px; }
        input, select { background: #1a1a3a; border: 1px solid #2a2a4a; color: #e0e0f0; padding: 6px 12px; border-radius: 6px; margin: 4px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>FRIDAY <span>v5.3.0 — Dashboard</span></h1>
        <div class="nav">
            <button class="active" onclick="showSection('overview')">Overview</button>
            <button onclick="showSection('agents')">Agents</button>
            <button onclick="showSection('tasks')">Tasks</button>
            <button onclick="showSection('memory')">Memory</button>
            <button onclick="showSection('improve')">Self-Improve</button>
        </div>
    </div>
    <div class="container" id="content">Loading...</div>
    <div class="footer">FRIDAY — Autonomous AI Assistant</div>
    <script>
        let autoRefresh = null;
        function showSection(name) {
            document.querySelectorAll('.nav button').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');
            loadSection(name);
            if (autoRefresh) clearInterval(autoRefresh);
            autoRefresh = setInterval(() => loadSection(name), 30000);
        }
        async function loadSection(name) {
            const container = document.getElementById('content');
            container.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px;color:#666">Loading...</div>';
            try {
                const resp = await fetch(`/api/${name}`);
                const html = await resp.text();
                container.innerHTML = html;
            } catch(e) {
                container.innerHTML = '<div class="card" style="grid-column:1/-1;color:#f87171">Error loading: ' + e.message + '</div>';
            }
        }
        window.onload = () => loadSection('overview');
    </script>
</body>
</html>
"""


def _system_stats() -> dict:
    stats = {"cpu": "N/A", "memory": "N/A", "disk": "N/A", "uptime": "N/A"}
    try:
        import psutil
        stats["cpu"] = f"{psutil.cpu_percent(interval=0.1)}%"
        mem = psutil.virtual_memory()
        stats["memory"] = f"{mem.percent}% ({mem.used // (1024**3)}GB/{mem.total // (1024**3)}GB)"
        disk = psutil.disk_usage("E:\\" if os.path.exists("E:\\") else "C:\\")
        stats["disk"] = f"{disk.percent}% ({disk.free // (1024**3)}GB free)"
        stats["uptime"] = datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    return stats


def _load_json(path: str, default=None):
    if default is None:
        default = {}
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return default


def _render_overview() -> str:
    stats = _system_stats()
    sched = _load_json(os.path.join(FRIDAY_MEMORY, "schedules.json"), [])
    patterns = _load_json(os.path.join(FRIDAY_MEMORY, "usage_patterns.json"), {})
    persist = _load_json(os.path.join(FRIDAY_MEMORY, "persistence", "agent_state.json"), {})
    total_events = sum(p.get("total_count", 0) for p in patterns.values())

    return f"""
    <div class="card">
        <h2>System Health</h2>
        <div class="row"><span>CPU</span><span class="{'good' if float(stats['cpu'].strip('%')) < 50 else 'warn'}">{stats['cpu']}</span></div>
        <div class="row"><span>Memory</span><span class="{'good' if float(stats['memory'].split('%')[0]) < 70 else 'warn'}">{stats['memory']}</span></div>
        <div class="row"><span>Disk</span><span class="{'bad' if float(stats['disk'].split('%')[0]) > 85 else 'good'}">{stats['disk']}</span></div>
        <div class="row"><span>Boot</span><span>{stats['uptime']}</span></div>
    </div>
    <div class="card">
        <h2>Scheduled Tasks</h2>
        <div class="value">{len(sched)}</div>
        <div class="label">active tasks</div>
        <div style="margin-top:12px;font-size:13px">
            {''.join(f'<div class="row"><span>{t.get("name","?")[:25]}</span><span>{t.get("schedule","")}</span></div>' for t in sched[:8])}
        </div>
    </div>
    <div class="card">
        <h2>Usage Patterns</h2>
        <div class="value">{len(patterns)}</div>
        <div class="label">tools tracked</div>
        <div class="value" style="font-size:20px">{total_events}</div>
        <div class="label">total events</div>
        <div style="margin-top:12px">
            {''.join(f'<div class="row"><span>{k[:30]}</span><span>{p["total_count"]}x</span></div>' for k,p in sorted(patterns.items(), key=lambda x:-x[1]["total_count"])[:5])}
        </div>
    </div>
    <div class="card">
        <h2>Persisted Agents</h2>
        <div class="value">{len(persist)}</div>
        <div class="label">saved states</div>
        {''.join(f'<div class="row"><span>{aid[:25]}</span><span>{e.get("saved_at","?")[:16]}</span></div>' for aid,e in list(persist.items())[:5])}
    </div>
    """


def _render_agents() -> str:
    profiles = _load_json(os.path.join(FRIDAY_MEMORY, "persistence", "agent_state.json"), {})
    states = _load_json(os.path.join(FRIDAY_MEMORY, "persistence", "agent_state.json"), {})

    rows = ""
    for agent_id, entry in states.items():
        state = entry.get("state", {})
        last_seen = entry.get("saved_at", "")[:19]
        rows += f"<tr><td>{agent_id}</td><td>{last_seen}</td><td><span class='good'>saved</span></td></tr>"
    if not rows:
        rows = "<tr><td colspan='3' style='color:#666'>No agent states persisted yet</td></tr>"

    return f"""
    <div class="card" style="grid-column:1/-1">
        <h2>Agent States</h2>
        <table>
            <tr><th>Agent</th><th>Last Saved</th><th>Status</th></tr>
            {rows}
        </table>
    </div>
    """


def _render_tasks() -> str:
    sched = _load_json(os.path.join(FRIDAY_MEMORY, "schedules.json"), [])
    tasks = _load_json(os.path.join(FRIDAY_MEMORY, "persistence", "task_queue.json"), {}).get("tasks", [])

    sched_rows = ""
    for t in sched:
        status = "active" if t.get("enabled", True) else "paused"
        last = t.get("last_run", "")[:16] or "never"
        sched_rows += f"<tr><td>{t.get('name','?')[:30]}</td><td>{t.get('schedule','')}</td><td>{status}</td><td>{last}</td><td>{t.get('run_count',0)}</td></tr>"

    task_rows = ""
    for t in tasks[:10]:
        desc = t.get("description", t.get("task", "?"))[:60]
        task_rows += f"<tr><td>{desc}</td><td>{t.get('status','pending')}</td></tr>"

    return f"""
    <div class="card" style="grid-column:1/-1">
        <h2>Scheduled Tasks ({len(sched)})</h2>
        <table>
            <tr><th>Name</th><th>Schedule</th><th>Status</th><th>Last Run</th><th>Count</th></tr>
            {sched_rows}
        </table>
    </div>
    <div class="card" style="grid-column:1/-1">
        <h2>Pending Task Queue ({len(tasks)})</h2>
        <table>
            <tr><th>Task</th><th>Status</th></tr>
            {task_rows}
        </table>
    </div>
    """


def _render_memory() -> str:
    persist_dir = os.path.join(FRIDAY_MEMORY, "persistence", "daily_summaries")
    summaries = []
    if os.path.exists(persist_dir):
        for f in sorted(os.listdir(persist_dir))[-7:]:
            with open(os.path.join(persist_dir, f)) as fh:
                try:
                    summaries.append(json.load(fh))
                except Exception:
                    pass

    rows = ""
    for s in summaries:
        date = s.get("date", "?")
        agents = s.get("persisted_agent_count", 0)
        tasks = s.get("pending_tasks", 0)
        events = s.get("events_today", 0)
        rows += f"<tr><td>{date}</td><td>{agents}</td><td>{tasks}</td><td>{events}</td></tr>"

    return f"""
    <div class="card" style="grid-column:1/-1">
        <h2>Daily Summaries</h2>
        <table>
            <tr><th>Date</th><th>Agents</th><th>Tasks</th><th>Events</th></tr>
            {rows or '<tr><td colspan="4" style="color:#666">No summaries yet</td></tr>'}
        </table>
    </div>
    """


def _render_improve() -> str:
    history_path = os.path.join(FRIDAY_MEMORY, "self_improve", "history.jsonl")
    entries = []
    if os.path.exists(history_path):
        with open(history_path) as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    continue

    rows = ""
    for e in entries[-20:]:
        ts = e.get("timestamp", e.get("started_at", "?"))[:19]
        status = e.get("status", "?")
        issues = e.get("issues_found", 0)
        proposals = e.get("proposals_generated", 0)
        rows += f"<tr><td>{ts}</td><td>{status}</td><td>{issues}</td><td>{proposals}</td></tr>"

    return f"""
    <div class="card" style="grid-column:1/-1">
        <h2>Self-Improvement History</h2>
        <table>
            <tr><th>Time</th><th>Status</th><th>Issues</th><th>Proposals</th></tr>
            {rows or '<tr><td colspan="4" style="color:#666">No improvement cycles yet</td></tr>'}
        </table>
    </div>
    """


# ── FastAPI Routes ──

if HAS_FASTAPI:
    @app.get("/")
    async def root():
        return HTMLResponse(HTML_TEMPLATE)

    @app.get("/api/overview")
    async def api_overview():
        return HTMLResponse(_render_overview())

    @app.get("/api/agents")
    async def api_agents():
        return HTMLResponse(_render_agents())

    @app.get("/api/tasks")
    async def api_tasks():
        return HTMLResponse(_render_tasks())

    @app.get("/api/memory")
    async def api_memory():
        return HTMLResponse(_render_memory())

    @app.get("/api/improve")
    async def api_improve():
        return HTMLResponse(_render_improve())

    @app.get("/api/health")
    async def api_health():
        return JSONResponse(_system_stats())


def start_dashboard(host: str = "0.0.0.0", port: int = 8765) -> str:
    if not HAS_FASTAPI:
        return "[FAIL] FastAPI not installed. pip install fastapi uvicorn"
    global _server_thread
    if _server_thread and _server_thread.is_alive():
        return f"[OK] Dashboard already running on http://{host}:{port}"
    _server_thread = threading.Thread(
        target=lambda: uvicorn.run(app, host=host, port=port, log_level="info"),
        daemon=True,
    )
    _server_thread.start()
    return f"[OK] FRIDAY Dashboard started at http://{host}:{port}"


def stop_dashboard() -> str:
    return "[OK] Dashboard stopped (thread will exit on shutdown)"


def dashboard_tool(action: str = "status", **kwargs) -> str:
    """FRIDAY Web Dashboard.
    
    Actions:
      status - Show dashboard status
      start [host] [port] - Start the web dashboard
      stop - Stop the dashboard
    """
    if action == "status":
        running = _server_thread is not None and _server_thread.is_alive()
        return json.dumps({
            "available": HAS_FASTAPI,
            "running": running,
            "url": "http://localhost:8765" if running else "not started",
        }, indent=2)
    elif action == "start":
        host = kwargs.get("host", "0.0.0.0")
        port = int(kwargs.get("port", 8765))
        return start_dashboard(host=host, port=port)
    elif action == "stop":
        return stop_dashboard()
    return f"[FAIL] Unknown action: {action}"
