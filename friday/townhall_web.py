"""Self-hosted web Townhall for FRIDAY's agent society."""

from __future__ import annotations

import asyncio
import datetime
import json
import os
import sys
import random
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from friday.townhall_engine import (
    AgentNode, ChatChannel, DreamEngine,
    AGENT_PROFILES, STATUS_COLORS, STATUS_DOTS,
    TOWNHALL_STATE_PATH, TOWNHALL_CHATS_PATH,
)
from friday.settings_dashboard import register_settings_routes

app = FastAPI(title="FRIDAY Townhall")
register_settings_routes(app)

_agents: dict[str, AgentNode] = {}
_channels: dict[str, ChatChannel] = {}
_dream_engine: DreamEngine | None = None
_ws_connections: list[WebSocket] = []
_loop: asyncio.AbstractEventLoop | None = None


def _on_agent_chat(msg: str):
    """Callback from DreamEngine when an agent speaks. Receives a single formatted string."""
    import re
    m = re.match(r'\[bold[^\]]*\]([^[/]+)\[/bold[^\]]*\]:\s*(.*)', msg)
    agent_name = m.group(1).strip() if m else "System"
    text = m.group(2).strip() if m else msg
    ch = _channels.get("main")
    if ch:
        ch.messages.append({
            "speaker": agent_name,
            "text": text,
            "ts": datetime.datetime.now().isoformat(),
        })
    _broadcast("chat", {"agent": agent_name, "text": text, "channel": "main"})


def _init():
    global _agents, _channels, _dream_engine
    saved = _load_state()
    chats = _load_chats()

    for profile in AGENT_PROFILES:
        name = profile["name"]
        if saved and name in saved:
            _agents[name] = AgentNode.from_dict(saved[name])
        else:
            _agents[name] = AgentNode(profile)

    _channels["main"] = (
        ChatChannel.from_dict(chats["main"]) if chats and "main" in chats
        else ChatChannel("main", "main")
    )
    if chats:
        for name, data in chats.items():
            if name != "main":
                ch = ChatChannel.from_dict(data)
                if ch.active:
                    _channels[name] = ch

    _dream_engine = DreamEngine(_agents, _channels, log_callback=_on_agent_chat)
    _dream_engine.start()
    _save()


def _load_state() -> dict | None:
    try:
        if TOWNHALL_STATE_PATH.exists():
            return json.loads(TOWNHALL_STATE_PATH.read_text())
    except Exception:
        return None


def _load_chats() -> dict | None:
    try:
        if TOWNHALL_CHATS_PATH.exists():
            return json.loads(TOWNHALL_CHATS_PATH.read_text())
    except Exception:
        return None


def _save():
    try:
        TOWNHALL_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {n: a.to_dict() for n, a in _agents.items()}
        data["_updated"] = datetime.datetime.now().isoformat()
        TOWNHALL_STATE_PATH.write_text(json.dumps(data, indent=2))
        chats = {n: c.to_dict() for n, c in _channels.items()}
        TOWNHALL_CHATS_PATH.write_text(json.dumps(chats, indent=2))
    except Exception:
        pass


_COLOR_MAP = {
    "cyan": "#00FFFF", "bright_cyan": "#66FFFF",
    "magenta": "#FF00FF", "bright_magenta": "#FF66FF",
    "blue": "#4488FF", "bright_blue": "#66AAFF",
    "red": "#FF4444",
    "yellow": "#FFDD44", "bright_yellow": "#FFEE66",
    "green": "#44FF44", "bright_green": "#66FF66",
    "white": "#FFFFFF", "bright_white": "#FFFFFF",
    "black": "#000000", "grey": "#888888", "gray": "#888888",
    "bright_red": "#FF6666", "bright_green": "#66FF66",
    "bright_blue": "#66AAFF",
}


def _hex_color(c: str) -> str:
    return _COLOR_MAP.get(c.lower(), c)


def _clean(val: str) -> str:
    if not isinstance(val, str):
        return val
    return val.encode("utf-8", errors="replace").decode("utf-8")


def _serialize():
    agents = {}
    for name, a in _agents.items():
        agents[name] = {
            "name": _clean(a.name),
            "role": _clean(a.role),
            "status": _clean(a.status),
            "mood": _clean(a.mood),
            "color": _hex_color(_clean(a.color)),
            "emoji": _clean(a.emoji),
            "current_task": _clean(a.current_task or ""),
            "personality": _clean(a.personality[:100] if a.personality else ""),
            "friendship": dict(sorted(
                {rn: rd["friendship"] for rn, rd in a.relationships.items()}.items(),
                key=lambda x: x[1], reverse=True
            )),
        }
    channels = {}
    for name, c in _channels.items():
        channels[name] = {
            "name": _clean(c.name),
            "type": _clean(c.type),
            "participants": [_clean(p) for p in c.participants],
            "active": c.active,
            "messages": [
                {"from": _clean(m.get("from", "")), "text": _clean(m.get("text", "")), "time": m.get("time", "")}
                for m in c.messages[-50:]
            ],
        }
    return {"agents": agents, "channels": channels}


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FRIDAY Townhall</title>
<script type="importmap">
{
  "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/"
  }
}
</script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #050510; color: #c8c8d8; font-family: 'Segoe UI', system-ui, sans-serif; height: 100vh; overflow: hidden; }
#three-container { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 0; }

#sidebar-left { position: fixed; top: 0; left: 0; width: 280px; height: 100%; z-index: 1; background: rgba(10,10,26,0.85); border-right: 1px solid rgba(26,26,58,0.8); backdrop-filter: blur(12px); display: flex; flex-direction: column; overflow-y: auto; transition: transform 0.3s; }
#sidebar-left.hidden { transform: translateX(-280px); }
#sidebar-right { position: fixed; top: 0; right: 0; width: 340px; height: 100%; z-index: 1; background: rgba(10,10,26,0.85); border-left: 1px solid rgba(26,26,58,0.8); backdrop-filter: blur(12px); display: flex; flex-direction: column; overflow-y: auto; transition: transform 0.3s; }
#sidebar-right.hidden { transform: translateX(340px); }

.section-title { color: #00bfff; font-size: 10px; text-transform: uppercase; padding: 14px 16px 4px; letter-spacing: 1.5px; opacity: 0.7; }
.divider { border-top: 1px solid rgba(26,26,58,0.5); margin: 6px 16px; }
.pad { padding: 2px 16px; font-size: 13px; line-height: 1.6; }

#agent-info { min-height: 60px; }
.agent-status-item { display: flex; align-items: center; gap: 8px; padding: 3px 16px; font-size: 12px; cursor: pointer; }
.agent-status-item:hover { background: rgba(255,255,255,0.03); }
.agent-status-item .dot { font-size: 10px; width: 14px; text-align: center; }
.agent-status-item .name { font-weight: 600; }
.agent-status-item .task { color: #686898; font-size: 11px; margin-left: auto; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 120px; }

#toggle-btn { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); z-index: 2; background: rgba(10,10,26,0.7); border: 1px solid rgba(26,26,58,0.6); color: #686898; padding: 6px 18px; border-radius: 16px; cursor: pointer; font-size: 11px; backdrop-filter: blur(6px); transition: all 0.3s; }
#toggle-btn:hover { border-color: #00bfff; color: #00bfff; }

#agent-list { flex: 1; overflow-y: auto; }
#status-bar { position: fixed; top: 14px; left: 50%; transform: translateX(-50%); z-index: 2; background: rgba(10,10,26,0.6); border: 1px solid rgba(26,26,58,0.5); backdrop-filter: blur(6px); padding: 4px 16px; border-radius: 12px; font-size: 11px; color: #686898; display: flex; align-items: center; gap: 10px; pointer-events: none; }
#status-bar .badge { color: #00FF87; }

::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(26,26,58,0.5); border-radius: 2px; }
</style>
</head>
<body>
<div id="three-container"></div>

<div id="status-bar"><span class="badge">&#9679;</span> Townhall <span style="color:#484868">|</span> <span id="conn-status">connecting...</span> <span style="color:#484868">|</span> <a href="/settings" style="color:#00bfff;text-decoration:none;pointer-events:auto" target="_blank">&#9881; Settings</a></div>

<div id="sidebar-left">
  <div class="section-title">&#9679; Selected Agent</div>
  <div id="agent-info" class="pad" style="min-height:60px">Click an agent sphere or list entry</div>
  <div class="divider"></div>
  <div class="section-title">&#9432; Status Colors</div>
  <div class="pad" style="font-size:11px;color:#686898">
    <span style="color:#00FF87">&#9679;</span> working
    <span style="color:#666;margin-left:6px">&#9679;</span> idle
    <span style="color:#00BFFF;margin-left:6px">&#9679;</span> chat
    <span style="color:#8888FF;margin-left:6px">&#9679;</span> dream
  </div>
</div>

<div id="sidebar-right">
  <div class="section-title">&#9679; Agent Status</div>
  <div id="agent-list"></div>
  <div class="divider"></div>
  <div id="chat-section">
    <div class="section-title">&#128172; Main Chat</div>
    <div id="chat-log" style="flex:none;max-height:200px;overflow-y:auto;padding:0 16px 4px;font-size:12px"></div>
  </div>
  <div class="divider"></div>
  <div id="task-section"></div>
</div>

<button id="toggle-btn">&#9664; Toggle Panels</button>

<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const STATUS_ORDER = { working: 0, chatting: 1, dreaming: 2, waiting: 3, idle: 4 };
const STATUS_COLORS = { working: '#00FF87', idle: '#666666', chatting: '#00BFFF', dreaming: '#8888FF', waiting: '#FFD700' };

const ws = new WebSocket('ws://' + location.host + '/ws');
const container = document.getElementById('three-container');
const agentInfo = document.getElementById('agent-info');
const agentList = document.getElementById('agent-list');
const taskSection = document.getElementById('task-section');
const chatLog = document.getElementById('chat-log');
const connStatus = document.getElementById('conn-status');

let state = { agents: {}, channels: {} };
let agentMeshes = {};
let agentLabels = {};
let agentGlows = {};
let selectedName = null;

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x050510);

const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 100);
camera.position.set(10, 6, 12);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(container.clientWidth, container.clientHeight);
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.2;
container.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.autoRotate = true;
controls.autoRotateSpeed = 0.6;
controls.minDistance = 3;
controls.maxDistance = 22;
controls.target.set(0, 0, 0);

const ambientLight = new THREE.AmbientLight(0x334466, 0.4);
scene.add(ambientLight);
const pLight = new THREE.PointLight(0x4488ff, 2, 30);
pLight.position.set(5, 10, 5);
scene.add(pLight);
const pLight2 = new THREE.PointLight(0xff4488, 0.8, 30);
pLight2.position.set(-5, -3, -5);
scene.add(pLight2);

const stars = new Float32Array(2000 * 3);
for (let i = 0; i < 6000; i++) stars[i] = (Math.random() - 0.5) * 100;
const sGeo = new THREE.BufferGeometry();
sGeo.setAttribute('position', new THREE.BufferAttribute(stars, 3));
scene.add(new THREE.Points(sGeo, new THREE.PointsMaterial({ color: 0x666688, size: 0.07, sizeAttenuation: true })));

const grid = new THREE.GridHelper(20, 20, 0x1a1a3a, 0x111133);
grid.position.y = -1.5;
grid.material.transparent = true;
grid.material.opacity = 0.25;
scene.add(grid);

function makeSphere(radius, hex) {
  const geo = new THREE.SphereGeometry(radius, 32, 32);
  const mat = new THREE.MeshPhongMaterial({
    color: hex, emissive: hex, emissiveIntensity: 0.4, shininess: 50, transparent: true, opacity: 0.95,
  });
  return new THREE.Mesh(geo, mat);
}

function makeGlow(radius, hex) {
  const g = new THREE.Mesh(
    new THREE.SphereGeometry(radius * 2.0, 16, 16),
    new THREE.MeshBasicMaterial({ color: hex, transparent: true, opacity: 0.10, depthWrite: false })
  );
  return g;
}

function makeLabel(name, color) {
  const c = document.createElement('canvas');
  c.width = 256; c.height = 64;
  const ctx = c.getContext('2d');
  ctx.shadowColor = 'rgba(0,0,0,0.9)'; ctx.shadowBlur = 10;
  ctx.fillStyle = color; ctx.font = 'bold 26px "Segoe UI",sans-serif';
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText(name, 128, 32);
  const tex = new THREE.CanvasTexture(c);
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false }));
  sp.scale.set(2.5, 0.7, 1);
  return sp;
}

function buildScene() {
  for (const k in agentMeshes) { scene.remove(agentMeshes[k]); scene.remove(agentLabels[k]); }
  agentMeshes = {}; agentLabels = {}; agentGlows = {};

  const A = state.agents;
  if (!A || !A.FRIDAY) return;

  const others = Object.keys(A).filter(n => n !== 'FRIDAY');
  const count = others.length;
  const R = 5.5;
  const pos = {};
  others.forEach((n, i) => {
    const a = (i / count) * Math.PI * 2 - Math.PI / 2;
    pos[n] = { x: Math.cos(a) * R, y: Math.sin(a * 2) * 0.8, z: Math.sin(a) * R };
  });

  for (const [name, data] of Object.entries(A)) {
    const isCenter = name === 'FRIDAY';
    const r = isCenter ? 1.0 : 0.5;
    const hex = parseInt((data.color || '#ffffff').replace('#', ''), 16);
    const mesh = makeSphere(r, hex);
    mesh.userData.agentName = name;
    agentGlows[name] = makeGlow(r, hex);
    mesh.add(agentGlows[name]);

    if (isCenter) {
      mesh.position.set(0, 0, 0);
      [0.15, 0.08].forEach((op, i) => {
        const ring = new THREE.Mesh(
          new THREE.RingGeometry(2.0 + i * 0.3, 2.8 + i * 0.3, 48),
          new THREE.MeshBasicMaterial({ color: 0x00bfff, transparent: true, opacity: op, side: THREE.DoubleSide, depthWrite: false })
        );
        ring.rotation.x = -Math.PI / 3 + i * 0.5;
        mesh.add(ring);
      });
    } else {
      const p = pos[name];
      mesh.position.set(p.x, p.y, p.z);
    }

    scene.add(mesh);
    agentMeshes[name] = mesh;

    const label = makeLabel(name, data.color || '#ffffff');
    label.position.set(mesh.position.x, mesh.position.y - r - 0.9, mesh.position.z);
    scene.add(label);
    agentLabels[name] = label;
  }

  const lineMat = new THREE.LineBasicMaterial({ color: 0x1a1a3a, transparent: true, opacity: 0.25 });
  const center = agentMeshes['FRIDAY'];
  if (center) {
    for (const [name, mesh] of Object.entries(agentMeshes)) {
      if (name === 'FRIDAY') continue;
      const g = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), mesh.position.clone()]);
      scene.add(new THREE.Line(g, lineMat));
    }
  }
}

function updateStatus(name, status) {
  const m = agentMeshes[name];
  if (!m) return;
  const hex = parseInt((STATUS_COLORS[status] || '#666666').replace('#', ''), 16);
  m.material.color.setHex(hex);
  m.material.emissive.setHex(hex);
  m.userData.status = status;
}

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  const t = performance.now() / 1000;
  for (const [name, mesh] of Object.entries(agentMeshes)) {
    const s = mesh.userData.status || 'idle';
    let sc = 1, yo = 0, gi = 0.1;
    switch (s) {
      case 'working': sc = 1 + Math.sin(t * 3) * 0.04; gi = 0.15 + Math.sin(t * 4) * 0.08; break;
      case 'chatting': yo = Math.sin(t * 2.5) * 0.1; gi = 0.12 + Math.sin(t * 3) * 0.06; break;
      case 'dreaming': sc = 1 + Math.sin(t * 1.5) * 0.02; gi = 0.2 + Math.sin(t * 2) * 0.1; break;
      case 'waiting': gi = 0.1 + Math.sin(t * 2) * 0.05; break;
      default: gi = 0.06;
    }
    mesh.scale.set(sc, sc, sc);
    mesh.position.y = (mesh.userData.baseY || 0) + yo;
    const g = agentGlows[name];
    if (g) { g.material.opacity = gi; g.scale.set(sc, sc, sc); }
    if (name === 'FRIDAY') mesh.rotation.y = t * 0.08;
  }
  renderer.render(scene, camera);
}

function syncScene() {
  for (const [name, data] of Object.entries(state.agents || {})) {
    const m = agentMeshes[name];
    if (m) {
      updateStatus(name, data.status);
      m.userData.baseY = m.position.y;
    }
    const l = agentLabels[name];
    if (l) {
      const nl = makeLabel(name, data.color || '#ffffff');
      nl.position.copy(l.position);
      scene.remove(l); scene.add(nl);
      agentLabels[name] = nl;
    }
  }
}

function hitAgentName(hits) {
  for (const h of hits) {
    let o = h.object;
    while (o) { if (o.userData.agentName) return o.userData.agentName; o = o.parent; }
  }
  return null;
}

renderer.domElement.addEventListener('click', (e) => {
  const r = renderer.domElement.getBoundingClientRect();
  pointer.x = ((e.clientX - r.left) / r.width) * 2 - 1;
  pointer.y = -((e.clientY - r.top) / r.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObjects(Object.values(agentMeshes), true);
  const name = hitAgentName(hits);
  if (name) { selectedName = name; renderAgentInfo(name); }
});

renderer.domElement.addEventListener('mousemove', (e) => {
  const r = renderer.domElement.getBoundingClientRect();
  pointer.x = ((e.clientX - r.left) / r.width) * 2 - 1;
  pointer.y = -((e.clientY - r.top) / r.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObjects(Object.values(agentMeshes), true);
  renderer.domElement.style.cursor = hitAgentName(hits) ? 'pointer' : 'default';
});

ws.onopen = () => connStatus.textContent = 'connected';
ws.onclose = () => connStatus.textContent = 'disconnected';
function renderChat() {
  const ch = state.channels && state.channels.main;
  if (!ch || !ch.messages) { chatLog.innerHTML = ''; return; }
  chatLog.innerHTML = ch.messages.slice(-20).map(m => {
    if (m.from === 'system') return `<div style="color:#686898;font-style:italic;font-size:11px">${escapeHtml(m.text)}</div>`;
    const a = state.agents[m.from]; const c = a ? a.color : '#c8c8d8';
    const ts = m.time ? m.time.slice(11, 16) : '';
    return `<div><span style="color:#484868;font-size:10px">${ts}</span> <span style="color:${c};font-weight:600">${m.from}</span>: ${escapeHtml(m.text)}</div>`;
  }).join('');
  chatLog.scrollTop = chatLog.scrollHeight;
}

function escapeHtml(t) {
  const d = document.createElement('div'); d.textContent = t; return d.innerHTML;
}

ws.onmessage = (e) => {
  const data = JSON.parse(e.data);
  if (data.type === 'state') {
    state = data; buildScene();
    for (const a of Object.values(state.agents)) { if (agentMeshes[a.name]) updateStatus(a.name, a.status); }
    syncScene(); renderAgentList(); renderChat();
  } else if (data.type === 'update') {
    if (data.agents) Object.assign(state.agents, data.agents);
    if (data.channels) Object.assign(state.channels, data.channels);
    syncScene(); renderAgentList(); renderChat();
    if (selectedName) renderAgentInfo(selectedName);
  }
};

function renderAgentInfo(name) {
  const a = name ? state.agents[name] : null;
  if (!a) { agentInfo.innerHTML = 'Click an agent sphere'; return; }
  const sc = STATUS_COLORS[a.status] || '#666';
  agentInfo.innerHTML = `
    <div style="font-weight:bold;color:${a.color};font-size:15px;margin-bottom:2px">${a.emoji||''} ${a.name}</div>
    <div style="color:#686898;font-size:11px;margin-bottom:4px">${a.role}</div>
    <div style="margin:1px 0"><span style="color:${sc}">&#9679;</span> ${a.status} &middot; ${a.mood||'neutral'}</div>
    <div style="color:#686898;font-size:12px">task: ${a.current_task||'idle'}</div>
    ${a.personality ? `<div style="margin-top:4px;color:#484868;font-size:11px;font-style:italic">${a.personality.slice(0,80)}</div>` : ''}
    ${a.friendship && Object.keys(a.friendship).length ? `
      <div style="margin-top:6px"><b style="font-size:10px;color:#686898;text-transform:uppercase;letter-spacing:1px">Relationships</b></div>
      ${Object.entries(a.friendship).slice(0,4).map(([rn,rs]) => {
        const h = rs > 70 ? '\u2764' : rs > 40 ? '\u{1F91D}' : '\u{1F937}';
        return `<div style="font-size:11px;color:#888;margin:1px 0">${h} ${rn} ${'\u2581'.repeat(Math.ceil(rs/10))} ${rs}</div>`;
      }).join('')}
    ` : ''}
  `;
}

function selectAgent(name) {
  selectedName = name;
  renderAgentInfo(name);
}

agentList.addEventListener('click', (e) => {
  const item = e.target.closest('.agent-status-item');
  if (item) selectAgent(item.dataset.name);
});

function renderAgentList() {
  const entries = Object.entries(state.agents || {})
    .sort((a, b) => (STATUS_ORDER[a[1].status] ?? 99) - (STATUS_ORDER[b[1].status] ?? 99));
  agentList.innerHTML = entries.map(([name, a]) => `
    <div class="agent-status-item" data-name="${name}">
      <span class="dot" style="color:${STATUS_COLORS[a.status]||'#666'}">&#9679;</span>
      <span class="name" style="color:${a.color}">${name}</span>
      <span class="task" title="${a.current_task||''}">${a.current_task||''}</span>
    </div>
  `).join('');
}

function renderTasks() {
  const chs = Object.values(state.channels || {}).filter(c => c.type === 'task' && c.active && c.messages?.length);
  taskSection.innerHTML = chs.length
    ? '<div class="section-title" style="margin-top:0">&#128279; Tasks</div>' + chs.map(ch => {
        const last = ch.messages.slice(-1)[0];
        return `<div class="pad" style="font-size:11px;padding:2px 16px;color:#686898">
          <span style="color:#ffd700">&#9656;</span> ${ch.name}
          <span style="color:#484868">${ch.participants.join(', ')}</span>
          ${last ? `<div style="padding-left:14px;color:#484868;font-size:10px">${last.from}: ${(last.text||'').slice(0,40)}</div>` : ''}
        </div>`;
      }).join('')
    : '';
}

document.getElementById('toggle-btn').addEventListener('click', () => {
  document.getElementById('sidebar-left').classList.toggle('hidden');
  document.getElementById('sidebar-right').classList.toggle('hidden');
  document.getElementById('toggle-btn').textContent =
    document.getElementById('sidebar-left').classList.contains('hidden') ? '\u25b6 Show Panels' : '\u25c4 Hide Panels';
});

window.addEventListener('resize', () => {
  const w = container.clientWidth, h = container.clientHeight;
  camera.aspect = w / h; camera.updateProjectionMatrix();
  renderer.setSize(w, h);
});

animate();
</script>
</body>
</html>
"""


@app.on_event("startup")
def _store_loop():
    global _loop
    _loop = asyncio.get_running_loop()


@app.get("/")
async def root():
    return HTMLResponse(HTML_PAGE)


@app.get("/state")
async def get_state():
    return _serialize()


@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws.accept()
    _ws_connections.append(ws)
    await ws.send_json({"type": "state", **_serialize()})
    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type")
            if msg_type == "select":
                agent_name = data.get("agent", "").upper()
                if agent_name in _agents:
                    await ws.send_json({
                        "type": "agent_info",
                        **_agent_serialize(_agents[agent_name]),
                    })
    except WebSocketDisconnect:
        pass
    finally:
        if ws in _ws_connections:
            _ws_connections.remove(ws)


def _broadcast(msg_type, data):
    msg = json.dumps({"type": msg_type, **data})
    for ws in _ws_connections[:]:
        try:
            if _loop is not None and _loop.is_running():
                asyncio.run_coroutine_threadsafe(ws.send_text(msg), _loop)
            else:
                asyncio.create_task(ws.send_text(msg))
        except Exception:
            pass


def _agent_serialize(a: AgentNode) -> dict:
    return {
        "name": _clean(a.name),
        "role": _clean(a.role),
        "status": _clean(a.status),
        "mood": _clean(a.mood),
        "color": _clean(a.color),
        "emoji": _clean(a.emoji),
        "current_task": _clean(a.current_task or ""),
        "personality": _clean(a.personality[:100] if a.personality else ""),
        "friendship": {rn: rd["friendship"] for rn, rd in a.relationships.items()},
    }


def _generate_response(text: str) -> str:
    tl = text.lower()
    if "status" in tl:
        s = ", ".join(f"{a.name}: {a.status}" for a in _agents.values())
        return f"All agents accounted for. {s}"
    if "agent" in tl or "who" in tl:
        names = ", ".join(a.name for a in _agents.values() if a.name != "FRIDAY")
        return f"Everyone's here: {names}"
    if "task" in tl:
        busy = [a for a in _agents.values() if a.current_task]
        if busy:
            return f"Active: {', '.join(f'{a.name}: {a.current_task}' for a in busy[:3])}"
        return "All agents idle."
    r = [
        "On it. Let me check with the team.",
        "Acknowledged. Agents are on standby.",
        "I'll delegate accordingly. Status nominal.",
        "Team's ready whenever you need them.",
    ]
    return random.choice(r)


_init()


def start_townhall_web(port: int = 7071) -> dict:
    """Start the Townhall web server in a background daemon thread.

    Returns {"success": True, "port": port} or {"error": ...}.
    """
    try:
        import threading
        t = threading.Thread(
            target=uvicorn.run,
            args=(app,),
            kwargs={"host": "127.0.0.1", "port": port, "log_level": "info"},
            daemon=True,
        )
        t.start()
        return {"success": True, "port": port}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    port = int(os.environ.get("TOWNHALL_PORT", "7071"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
