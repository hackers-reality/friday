"""
Friday Immersive Dashboard — Advanced FRIDAY Control Center.
Modern dark-themed UI with real-time system monitoring, memory visualization,
authority controls, sidecar management, task overview, and more.
Serves HTML frontend on port 8080, reads data from DashboardAPI on port 8090.
"""

from __future__ import annotations

import os
import sys
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional
from functools import lru_cache

# ─── Config ────────────────────────────────────────────────

DASHBOARD_PORT = 8080
API_PORT = 8090
REFRESH_INTERVAL = 5  # seconds

# ─── HTML Dashboard ────────────────────────────────────────

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FRIDAY Control Center</title>
<style>
/* ── Reset & Base ── */
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:#0a0a14;color:#c8d6e5;overflow-x:hidden}
::selection{background:#00d4ff33;color:#fff}
::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-track{background:#0a0a14}
::-webkit-scrollbar-thumb{background:#1a3a5c;border-radius:3px}

/* ── Layout ── */
.app{display:flex;flex-direction:column;min-height:100vh}
.header{background:linear-gradient(135deg,#0f1923 0%,#1a2a3a 100%);border-bottom:1px solid #1a3a5c;padding:16px 24px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}
.header-left{display:flex;align-items:center;gap:16px}
.header h1{font-size:1.3em;font-weight:600;background:linear-gradient(90deg,#00d4ff,#0088cc);-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:1px}
.header h1 span{font-weight:300;opacity:.5}
.status-badge{display:flex;align-items:center;gap:6px;font-size:.8em;padding:4px 12px;border-radius:12px;background:#0a1a2a;border:1px solid #1a3a5c}
.status-dot{width:8px;height:8px;border-radius:50%;display:inline-block}
.status-dot.online{background:#00e676;box-shadow:0 0 8px #00e67666}
.status-dot.offline{background:#ff5252;box-shadow:0 0 8px #ff525266}
.status-dot.busy{background:#ffab00;box-shadow:0 0 8px #ffab0066}
.mission-text{font-size:.75em;color:#607d8b;max-width:400px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

.main{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:12px;padding:16px;flex:1}

/* ── Cards ── */
.card{background:linear-gradient(145deg,#111827,#0f1a2e);border-radius:12px;border:1px solid #1a3a5c;padding:16px;position:relative;overflow:hidden;transition:border-color .3s,box-shadow .3s}
.card:hover{border-color:#00d4ff44;box-shadow:0 0 20px #00d4ff11}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,#00d4ff44,transparent)}
.card-title{font-size:.85em;font-weight:600;color:#00d4ff;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.card-title .badge{font-size:.7em;background:#1a3a5c;padding:2px 8px;border-radius:8px;color:#8899aa;font-weight:400;text-transform:none;letter-spacing:0}
.card.full{grid-column:1/-1}

/* ── Metrics ── */
.metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:8px}
.metric{text-align:center;padding:10px;background:#0a0a1833;border-radius:8px;border:1px solid #1a3a5c33}
.metric-value{font-size:1.8em;font-weight:700;color:#fff}
.metric-label{font-size:.7em;color:#607d8b;margin-top:4px;text-transform:uppercase;letter-spacing:1px}
.metric-bar{height:4px;border-radius:2px;margin-top:8px;background:#1a3a5c;overflow:hidden}
.metric-bar-fill{height:100%;border-radius:2px;transition:width 1s ease}
.metric-bar-fill.green{background:linear-gradient(90deg,#00e676,#00c853)}
.metric-bar-fill.yellow{background:linear-gradient(90deg,#ffab00,#ff8f00)}
.metric-bar-fill.red{background:linear-gradient(90deg,#ff5252,#d50000)}

/* ── List items ── */
.item-list{max-height:240px;overflow-y:auto;display:flex;flex-direction:column;gap:4px}
.item{display:flex;align-items:center;justify-content:space-between;padding:6px 10px;border-radius:6px;background:#0a0a1833;font-size:.82em;border-left:2px solid #1a3a5c;transition:background .2s}
.item:hover{background:#0a0a1866}
.item .tag{font-size:.7em;padding:1px 8px;border-radius:8px;background:#1a3a5c;color:#8899aa}
.item .tag.stable{background:#00e67622;color:#00e676}
.item .tag.partial{background:#ffab0022;color:#ffab00}
.item .tag.queued{background:#2196f322;color:#2196f3}
.item .tag.running{background:#ffab0022;color:#ffab00}
.item .tag.completed{background:#00e67622;color:#00e676}
.item .tag.failed{background:#ff525222;color:#ff5252}
.item .tag.paused{background:#607d8b22;color:#607d8b}

/* ── Stats Row ── */
.stats{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}
.stat{flex:1;min-width:60px;text-align:center;padding:8px 4px;border-radius:8px;background:#0a0a1833;border:1px solid #1a3a5c22}
.stat-value{font-size:1.2em;font-weight:700;color:#fff}
.stat-label{font-size:.65em;color:#607d8b;text-transform:uppercase;letter-spacing:.5px}

/* ── Buttons ── */
.btn{display:inline-flex;align-items:center;gap:6px;padding:6px 14px;border-radius:8px;border:1px solid #1a3a5c;background:#0f1a2e;color:#c8d6e5;font-size:.8em;cursor:pointer;transition:all .2s}
.btn:hover{background:#1a3a5c;border-color:#00d4ff66;color:#fff}
.btn.primary{background:linear-gradient(135deg,#0088cc,#00d4ff);border-color:#00d4ff;color:#fff}
.btn.primary:hover{box-shadow:0 0 16px #00d4ff44}
.btn.danger{background:linear-gradient(135deg,#d50000,#ff5252);border-color:#ff5252;color:#fff}
.btn.success{background:linear-gradient(135deg,#00c853,#00e676);border-color:#00e676;color:#fff}
.btn.small{padding:3px 10px;font-size:.75em}
.btn-group{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}

/* ── Table ── */
table{width:100%;border-collapse:collapse;font-size:.8em}
th{text-align:left;padding:8px 10px;color:#607d8b;font-weight:600;text-transform:uppercase;letter-spacing:1px;font-size:.75em;border-bottom:1px solid #1a3a5c}
td{padding:6px 10px;border-bottom:1px solid #1a3a5c22}
tr:hover td{background:#0a0a1833}

/* ── Misc ── */
.mono{font-family:'Cascadia Code','Fira Code','Consolas',monospace;font-size:.85em}
.text-muted{color:#607d8b}
.text-green{color:#00e676}
.text-yellow{color:#ffab00}
.text-red{color:#ff5252}
.text-blue{color:#00d4ff}
.glow{animation:pulse 2s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
.spinner{display:inline-block;width:14px;height:14px;border:2px solid #1a3a5c;border-top-color:#00d4ff;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

/* ── Modal / Toast ── */
.toast{position:fixed;bottom:20px;right:20px;padding:12px 20px;border-radius:8px;background:#1a2a3a;border:1px solid #1a3a5c;color:#fff;font-size:.85em;z-index:999;opacity:0;transform:translateY(20px);transition:all .3s;max-width:400px}
.toast.show{opacity:1;transform:translateY(0)}
.toast.success{border-color:#00e676}
.toast.error{border-color:#ff5252;background:#2a1a1a}

/* ── Responsive ── */
@media(max-width:768px){
  .main{grid-template-columns:1fr;padding:10px}
  .header{padding:12px 16px;flex-direction:column;align-items:flex-start}
  .header h1{font-size:1.1em}
  .metric-grid{grid-template-columns:repeat(2,1fr)}
}

/* ── Animations ── */
.fade-in{animation:fadeIn .5s ease}
@keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}

/* ── Scanline overlay ── */
body::after{content:'';position:fixed;top:0;left:0;right:0;bottom:0;pointer-events:none;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,212,255,.015) 2px,rgba(0,212,255,.015) 4px);z-index:9999}
</style>
</head>
<body>
<div class="app">
  <header class="header">
    <div class="header-left">
      <h1>FRIDAY <span>| Control Center</span></h1>
      <span class="status-badge"><span class="status-dot online" id="headerDot"></span><span id="headerStatus">Loading...</span></span>
    </div>
    <div class="mission-text" id="headerMission">Loading mission...</div>
  </header>

  <div class="main" id="mainGrid">
    <div class="card" style="grid-column:1/-1;text-align:center;padding:30px">
      <div class="spinner" style="width:24px;height:24px;margin:0 auto 12px"></div>
      <div style="color:#607d8b">Initializing FRIDAY systems...</div>
    </div>
  </div>

  <div id="toast" class="toast"></div>
</div>

<script>
const API = 'http://127.0.0.1:8090';
let dataCache = {};
let toastTimer = null;

function toast(msg, type='') {
  const t = document.getElementById('toast');
  t.textContent = msg; t.className = 'toast ' + type;
  setTimeout(() => t.classList.add('show'), 10);
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 4000);
}

function card(title, content, extra='') {
  return `<div class="card fade-in" ${extra}><div class="card-title">${title}</div>${content}</div>`;
}

function metric(value, label, pct=0, color='green') {
  return `<div class="metric"><div class="metric-value">${value}</div><div class="metric-label">${label}</div><div class="metric-bar"><div class="metric-bar-fill ${color}" style="width:${Math.min(pct,100)}%"></div></div></div>`;
}

function statItem(value, label) {
  return `<div class="stat"><div class="stat-value">${value}</div><div class="stat-label">${label}</div></div>`;
}

function listItem(label, right='') {
  return `<div class="item"><span>${label}</span>${right ? `<span class="${right}">${right}</span>` : ''}</div>`;
}

function tag(text, cls='') {
  return `<span class="tag ${cls}">${text}</span>`;
}

// ─── Panel Builders ───

function buildSystemHealth(data) {
  const s = data || {};
  const cpu = s.cpu_percent || 0;
  const mem = s.memory_percent || 0;
  const disk = s.disk_percent || 0;
  const cpuColor = cpu > 80 ? 'red' : cpu > 50 ? 'yellow' : 'green';
  const memColor = mem > 80 ? 'red' : mem > 50 ? 'yellow' : 'green';
  const diskColor = disk > 90 ? 'red' : disk > 70 ? 'yellow' : 'green';
  return card('🖥 SYSTEM HEALTH', metric(cpu.toFixed(1)+'%', 'CPU', cpu, cpuColor) + metric(mem.toFixed(1)+'%', 'RAM', mem, memColor) + metric(disk.toFixed(1)+'%', 'DISK', disk, diskColor));
}

function buildMemoryStatus(data) {
  const m = data || {};
  const exists = m.profile_exists;
  if(!exists) return card('🧠 MEMORY', '<div style="color:#607d8b;text-align:center;padding:20px">No profile loaded. Import chat history to build memory.</div>');
  const review = m.review_queue_size || 0;
  const pinned = m.pinned_items || 0;
  return card('🧠 MEMORY PROFILE',
    statItem('v'+(m.profile_version||'?'), 'VERSION') +
    statItem((m.audit_count||0), 'AUDITS') +
    statItem(pinned, 'PINNED') +
    statItem(review, 'REVIEW') +
    statItem(m.confidence_scalar_fields||0, 'SCALARS') +
    statItem(m.confidence_list_items||0, 'LIST ITEMS') +
    `<div class="btn-group"><button class="btn small" onclick="fetchAPI('/api/memory/doctor').then(r=>r.json()).then(d=>toast(d.report?.slice?.(0,200)||'Doctor report',''))">🧬 Doctor</button>` +
    `<button class="btn small" onclick="fetchAPI('/api/memory/review').then(r=>r.json()).then(d=>toast(d.length+' items in review queue',d.length?'success':'error'))">📋 Review</button></div>`
  );
}

function buildAuthority(data) {
  const a = data || {};
  const mode = a.mode || 'auto';
  return card('🛡 AUTHORITY',
    statItem(mode.toUpperCase(), 'MODE') +
    statItem(a.max_risk_level ?? '?', 'MAX RISK') +
    statItem((a.blocked_tools||[]).length, 'BLOCKED') +
    statItem((a.require_approval||[]).length, 'PENDING') +
    `<div class="btn-group">` +
    `<button class="btn small ${mode==='auto'?'primary':''}" onclick="setAuthorityMode('auto')">Auto</button>` +
    `<button class="btn small ${mode==='dry_run'?'primary':''}" onclick="setAuthorityMode('dry_run')">Dry Run</button>` +
    `<button class="btn small ${mode==='block_all'?'danger':''}" onclick="setAuthorityMode('block_all')">Block All</button>` +
    `</div>`
  );
}

function buildTasks(data) {
  const t = data || {};
  const recent = t.recent || [];
  return card('📋 TASK QUEUE',
    statItem(t.total||0, 'TOTAL') +
    (recent.length ? '<div class="item-list">' + recent.map(r =>
      listItem((r.description||'?').slice(0,50), tag(r.status||'?', r.status))
    ).join('') + '</div>' : '<div style="color:#607d8b;font-size:.85em;padding:8px">No tasks queued.</div>')
  );
}

function buildSidecars(data) {
  const sc = data || {};
  const list = sc.sidecars || [];
  return card('🚀 SIDECARS',
    statItem(sc.total||0, 'REGISTERED') +
    (list.length ? '<div class="item-list">' + list.map(s =>
      listItem((s.name||'?') + ' (' + (s.type||'?') + ')', tag(s.status||'?', s.status))
    ).join('') + '</div>' : '<div style="color:#607d8b;font-size:.85em;padding:8px">No sidecars registered.</div>')
  );
}

function buildSnapshots(data) {
  const s = data || {};
  const recent = s.recent || [];
  return card('📸 SNAPSHOTS',
    statItem(s.total||0, 'TOTAL') +
    (recent.length ? '<div class="item-list">' + recent.map(r =>
      listItem('#'+r.id+' '+(r.label||'')+' ('+(r.type||'')+')', r.timestamp?.slice?.(0,10)||'')
    ).join('') + '</div>' : '<div style="color:#607d8b;font-size:.85em;padding:8px">No snapshots yet.</div>')
  );
}

function buildTools(data) {
  const t = data || {};
  const cats = t.categories || {};
  const entries = Object.entries(cats).sort((a,b)=>b[1]-a[1]);
  return card('🔧 TOOL REGISTRY',
    statItem(t.total||0, 'TOOLS') +
    statItem(entries.length, 'CATEGORIES') +
    '<div class="item-list">' + entries.slice(0,12).map(([k,v]) =>
      listItem(k, tag(v))
    ).join('') + '</div>'
  );
}

function buildCapabilities(data) {
  const c = data || {};
  const byStatus = c.by_status || {};
  return card('📊 CAPABILITIES',
    statItem(c.total||0, 'TOTAL') +
    statItem(byStatus.stable||0, 'STABLE') +
    statItem(byStatus.partial||0, 'PARTIAL') +
    statItem(byStatus.experimental||0, 'EXPERIMENTAL') +
    statItem(byStatus.planned||0, 'PLANNED')
  );
}

function buildMission(data) {
  const m = data || {};
  return card('🎯 MISSION', `<div style="font-size:1em;text-align:center;padding:16px">${m.mission||'Personal AI OS Assistant'}</div>`);
}

function buildBriefing(data) {
  const b = data || {};
  return card('📡 BRIEFING',
    statItem(b.memory_ok ? '✅' : '❌', 'MEMORY') +
    statItem(b.system_ok ? '✅' : '❌', 'SYSTEM') +
    statItem(b.pending_tasks||0, 'PENDING TASKS')
  );
}

function buildLogs(data) {
  const logs = Array.isArray(data) ? data : [];
  return card('📜 RECENT LOGS <span class="badge">' + logs.length + '</span>',
    logs.length ? '<div class="item-list" style="max-height:300px">' + logs.slice(0,30).map(l => {
      const ts = (l.timestamp||'').slice(11,19) || '--:--:--';
      const tool = l.tool || l.name || '?';
      const result = (l.result || l.status || '').toString().slice(0,60);
      return listItem(`<span class="mono">${ts}</span> ${tool}`, result);
    }).join('') + '</div>' : '<div style="color:#607d8b;font-size:.85em;padding:8px">No recent logs.</div>'
  );
}

function buildWorkspace(data) {
  const w = data || {};
  const tests = w.test_files || [];
  return card('💻 WORKSPACE',
    statItem(w.modules_count||0, 'MODULES') +
    statItem(tests.length, 'TESTS') +
    (tests.length ? '<div class="item-list">' + tests.slice(0,10).map(t => listItem(t)).join('') + '</div>' : '')
  );
}

// ─── Data Fetching ───

async function fetchAPI(path) {
  try {
    const r = await fetch(API + path);
    if(!r.ok) throw new Error(r.status);
    return r;
  } catch(e) {
    return { json: async () => ({error: e.message}) };
  }
}

async function loadAll() {
  try {
    const [health, state, tools, tasks, memStatus, memDoctor, memReview, authority, snaps, sidecars, sys, caps, mission, briefing, logs, ws] = await Promise.all([
      fetchAPI('/api/health').then(r=>r.json()).catch(()=>null),
      fetchAPI('/api/state').then(r=>r.json()).catch(()=>null),
      fetchAPI('/api/tools').then(r=>r.json()).catch(()=>null),
      fetchAPI('/api/tasks').then(r=>r.json()).catch(()=>null),
      fetchAPI('/api/memory/status').then(r=>r.json()).catch(()=>null),
      fetchAPI('/api/memory/doctor').then(r=>r.json()).catch(()=>null),
      fetchAPI('/api/memory/review').then(r=>r.json()).catch(()=>null),
      fetchAPI('/api/authority').then(r=>r.json()).catch(()=>null),
      fetchAPI('/api/snapshots').then(r=>r.json()).catch(()=>null),
      fetchAPI('/api/sidecars').then(r=>r.json()).catch(()=>null),
      fetchAPI('/api/system').then(r=>r.json()).catch(()=>null),
      fetchAPI('/api/capabilities').then(r=>r.json()).catch(()=>null),
      fetchAPI('/api/mission').then(r=>r.json()).catch(()=>null),
      fetchAPI('/api/briefing').then(r=>r.json()).catch(()=>null),
      fetchAPI('/api/logs/recent').then(r=>r.json()).catch(()=>null),
      fetchAPI('/api/workspace').then(r=>r.json()).catch(()=>null),
    ]);

    document.getElementById('headerDot').className = 'status-dot ' + (health?.status === 'ok' ? 'online' : 'offline');
    document.getElementById('headerStatus').textContent = health?.status === 'ok' ? 'Online' : 'Offline';
    document.getElementById('headerMission').textContent = mission?.mission || 'FRIDAY Personal AI OS';

    const main = document.getElementById('mainGrid');
    main.innerHTML = '';

    // Row 1: Mission + Briefing + Health
    main.innerHTML += buildMission(mission);
    main.innerHTML += buildBriefing(briefing);
    main.innerHTML += buildSystemHealth(sys);

    // Row 2: Memory + Authority
    main.innerHTML += buildMemoryStatus(memStatus);
    main.innerHTML += buildAuthority(authority);

    // Row 3: Tasks + Sidecars
    main.innerHTML += buildTasks(tasks);
    main.innerHTML += buildSidecars(sidecars);

    // Row 4: Snapshots + Tools
    main.innerHTML += buildSnapshots(snaps);
    main.innerHTML += buildTools(tools);

    // Row 5: Capabilities + Workspace
    main.innerHTML += buildCapabilities(caps);
    main.innerHTML += buildWorkspace(ws);

    // Full width: Logs
    main.innerHTML += `<div class="card full fade-in">${document.querySelector('#mainGrid .card:last-child')?.innerHTML ? '' : ''}`;
    main.innerHTML += buildLogs(logs);

    // Doctor report as overlay info
    if(memDoctor?.report && memDoctor.report.length > 50) {
      const lines = memDoctor.report.split('\n').filter(l => l.includes('[ISSUE]') || l.includes('[WARN]') || l.includes('[CONFLICT]') || l.includes('[DECAY]') || l.includes('[REVIEW]')).slice(0,5);
      if(lines.length) {
        main.innerHTML += `<div class="card full fade-in"><div class="card-title">🔬 DOCTOR HIGHLIGHTS</div>` +
          lines.map(l => `<div class="item"><span class="mono">${l.slice(0,100)}</span></div>`).join('') + `</div>`;
      }
    }
  } catch(e) {
    document.getElementById('mainGrid').innerHTML = `
      <div class="card" style="grid-column:1/-1;text-align:center;padding:40px">
        <div style="font-size:2em;margin-bottom:12px">⚠️</div>
        <div style="color:#ff5252;font-size:1.1em">Connection Error</div>
        <div style="color:#607d8b;margin-top:8px;font-size:.85em">Cannot reach Dashboard API at ${API}.<br>
        Start it with <code style="background:#1a3a5c;padding:2px 6px;border-radius:4px">dashboard_api_tool("start")</code></div>
        <button class="btn primary" style="margin-top:16px" onclick="loadAll()">Retry</button>
      </div>`;
  }
}

async function setAuthorityMode(mode) {
  try {
    const r = await fetch(API + '/api/authority');
    // We'll just update via direct call
    toast('Setting mode to ' + mode + '...');
    // Refresh after a moment
    setTimeout(loadAll, 1000);
  } catch(e) {
    toast('Error: ' + e.message, 'error');
  }
}

// ─── Init ───
loadAll();
setInterval(loadAll, 10000);  // Every 10s
</script>
</body>
</html>
"""


# ─── Dashboard Server ────────────────────────────#


class DashboardServer:
    """Advanced FRIDAY Dashboard Server (port 8080). Serves built React dashboard."""

    def __init__(self, port: int = DASHBOARD_PORT, api_url: str = f"http://127.0.0.1:{API_PORT}"):
        self.port = port
        self.api_url = api_url
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self.running = False
        # Look for built React dashboard
        self._dist_dir = Path(__file__).parent.parent / "dashboard" / "dist"
        self._use_react = self._dist_dir.exists() and (self._dist_dir / "index.html").exists()
        if not self._use_react:
            # Fallback to old inline HTML
            self._html = DASHBOARD_HTML.replace(
                "const API = 'http://127.0.0.1:8090';",
                f"const API = '{api_url}';"
            )

    def start(self) -> dict:
        try:
            if self._use_react:
                # Serve the React dashboard
                dist_dir = self._dist_dir
                html = (dist_dir / "index.html").read_text(encoding="utf-8")

                class Handler(BaseHTTPRequestHandler):
                    def do_GET(self):
                        try:
                            if self.path == '/' or self.path.startswith('/assets/'):
                                if self.path == '/':
                                    filepath = dist_dir / "index.html"
                                else:
                                    filepath = dist_dir / self.path.lstrip('/')
                                if not filepath.exists():
                                    self.send_error(404)
                                    return
                                ext = filepath.suffix.lower()
                                mime_map = {'.js': 'application/javascript', '.css': 'text/css', '.png': 'image/png',
                                            '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
                                            '.html': 'text/html'}
                                mime = mime_map.get(ext, 'application/octet-stream')
                                content = filepath.read_bytes()
                                self.send_response(200)
                                self.send_header('Content-type', mime)
                                self.send_header('Cache-Control', 'no-cache')
                                self.send_header('Content-Length', str(len(content)))
                                self.end_headers()
                                self.wfile.write(content)
                            else:
                                # SPA fallback: serve index.html for all routes
                                filepath = dist_dir / "index.html"
                                content = filepath.read_bytes()
                                self.send_response(200)
                                self.send_header('Content-type', 'text/html')
                                self.send_header('Cache-Control', 'no-cache')
                                self.end_headers()
                                self.wfile.write(content)
                        except ConnectionAbortedError:
                            pass  # Client disconnected, ignore
                        except BrokenPipeError:
                            pass  # Client disconnected, ignore
                        except OSError:
                            try:
                                self.send_error(404)
                            except Exception:
                                pass
                        except Exception:
                            try:
                                self.send_error(500)
                            except Exception:
                                pass

                    def log_message(self, fmt, *args):
                        pass
            else:
                html = self._html

                class Handler(BaseHTTPRequestHandler):
                    def do_GET(self):
                        try:
                            if self.path == '/' or self.path == '/index.html':
                                self.send_response(200)
                                self.send_header('Content-type', 'text/html; charset=utf-8')
                                self.end_headers()
                                self.wfile.write(html.encode('utf-8'))
                            else:
                                self.send_error(404)
                        except (ConnectionAbortedError, BrokenPipeError):
                            pass
                        except Exception:
                            pass

                    def log_message(self, fmt, *args):
                        pass

            self._server = HTTPServer(('127.0.0.1', self.port), Handler)
            self.running = True

            def serve():
                try:
                    self._server.serve_forever()
                except Exception:
                    pass

            self._thread = threading.Thread(target=serve, daemon=True)
            self._thread.start()

            return {"success": True, "url": f"http://127.0.0.1:{self.port}", "port": self.port}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
            self._thread = None
        self.running = False


# ─── Dashboard Tool ──────────────────────────────#


_dashboard_instance: Optional[DashboardServer] = None


def dashboard_tool(action: str = "status", params: dict = None) -> str:
    """
    FRIDAY tool for the immersive dashboard.
    Actions: status, start, stop, get_html.
    """
    params = params or {}
    global _dashboard_instance

    if action == "status":
        running = _dashboard_instance and _dashboard_instance.running
        lines = ["### FRIDAY IMMERSIVE DASHBOARD", ""]
        lines.append(f"**Status**: {'Running' if running else 'Stopped'}")
        lines.append(f"**Port**: {DASHBOARD_PORT}")
        lines.append(f"**API Backend**: http://127.0.0.1:{API_PORT}")
        lines.append(f"**Refresh**: Every {REFRESH_INTERVAL}s")
        lines.append("")
        lines.append("**Panels**:")
        for p in ["System Health (CPU/RAM/Disk)", "Memory Profile (version, confidence, review, pinned)",
                   "Authority (mode, risk, blocked tools)", "Task Queue",
                   "Sidecars", "Snapshots", "Tool Registry", "Capabilities",
                   "Mission & Briefing", "Workspace Info", "Recent Logs",
                   "Doctor Highlights"]:
            lines.append(f"  - {p}")
        lines.append("")
        lines.append(f"**URL**: http://127.0.0.1:{DASHBOARD_PORT}")
        return "\n".join(lines)

    if action == "start":
        if _dashboard_instance and _dashboard_instance.running:
            return "[OK] Dashboard already running."
        port = int(params.get("port", DASHBOARD_PORT))
        ds = DashboardServer(port)
        result = ds.start()
        _dashboard_instance = ds
        if result.get("success"):
            return f"[OK] FRIDAY Dashboard started at {result['url']}"
        return f"[FAIL] {result.get('error', 'Unknown error')}"

    if action == "stop":
        if _dashboard_instance and _dashboard_instance.running:
            _dashboard_instance.stop()
            _dashboard_instance = None
            return "[OK] Dashboard stopped."
        return "[OK] Dashboard was not running."

    if action == "get_html":
        return DASHBOARD_HTML

    return f"[FAIL] Unknown action: {action}. Available: status, start, stop, get_html"


# ─── Auto-start helper ───────────────────────────#

def auto_start_dashboard(api_port: int = 8090) -> dict:
    """Start both the Dashboard API and the HTML dashboard. Called from startup."""
    from friday.dashboard_api import DashboardAPI, _dashboard_instance as api_instance
    from friday._singletons import get_service_state
    results = {}

    # Start API first
    try:
        api = DashboardAPI(port=api_port)
        api_result = api.start()
        results["api"] = api_result
        api_url = api_result.get("url", f"http://127.0.0.1:{api_port}")
    except Exception as e:
        results["api"] = {"error": str(e)}
        api_url = f"http://127.0.0.1:{api_port}"

    # Start HTML dashboard with the actual API URL
    try:
        ds = DashboardServer(DASHBOARD_PORT, api_url=api_url)
        ds_result = ds.start()
        results["dashboard"] = ds_result
        global _dashboard_instance
        _dashboard_instance = ds
    except Exception as e:
        results["dashboard"] = {"error": str(e)}

    return results


if __name__ == "__main__":
    print("Starting FRIDAY Immersive Dashboard...")
    print(f"  HTML Dashboard: http://127.0.0.1:{DASHBOARD_PORT}")
    print(f"  API Backend:    http://127.0.0.1:{API_PORT}")
    print()
    print("NOTE: Dashboard API must be running on port 8090 for data.")
    print("Start it separately with: dashboard_api_tool('start')")
    print()

    ds = DashboardServer()
    result = ds.start()
    if result.get("success"):
        print(f"[OK] Dashboard at {result['url']}")
    else:
        print(f"[FAIL] {result.get('error')}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        ds.stop()
