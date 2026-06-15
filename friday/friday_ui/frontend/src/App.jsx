import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stars } from '@react-three/drei';
import Orb from './components/Orb';
import Panel from './components/Panel';
import ChatPanel from './components/ChatPanel';
import StatusBar from './components/StatusBar';
import TownhallPanel from './components/TownhallPanel';
import MemoryGraph from './components/MemoryGraph';
import LogPanel from './components/LogPanel';
import VoiceControl from './components/VoiceControl';
import './App.css';

const API = 'http://localhost:8000';

function App() {
  const [system, setSystem] = useState(null);
  const [services, setServices] = useState(null);
  const [tools, setTools] = useState(null);
  const [memory, setMemory] = useState(null);
  const [codebase, setCodebase] = useState(null);
  const [agents, setAgents] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [orbPulse, setOrbPulse] = useState(0);
  const [time, setTime] = useState(new Date());
  const [activeView, setActiveView] = useState('dashboard');
  const [logs, setLogs] = useState([]);
  const [townhall, setTownhall] = useState(null);
  const [memoryEntities, setMemoryEntities] = useState([]);
  const [memoryGraph, setMemoryGraph] = useState({ nodes: [], edges: [] });
  const [gitStatus, setGitStatus] = useState(null);
  const [healthStatus, setHealthStatus] = useState(null);
  const [securityStats, setSecurityStats] = useState(null);
  const wsRef = useRef(null);
  const systemStateRef = useRef({});

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const speak = useCallback((text) => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utt = new SpeechSynthesisUtterance(text);
    utt.rate = 0.95;
    utt.pitch = 0.9;
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v => v.name.includes('Google') && v.lang.startsWith('en')) ||
                     voices.find(v => v.name.includes('Samantha')) ||
                     voices.find(v => v.name.includes('Daniel')) ||
                     voices.find(v => v.lang.startsWith('en'));
    if (preferred) utt.voice = preferred;
    utt.onstart = () => setIsSpeaking(true);
    utt.onend = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utt);
  }, []);

  const proactiveGreeting = useCallback(() => {
    const hour = new Date().getHours();
    let greeting;
    if (hour < 12) greeting = 'Good morning, sir.';
    else if (hour < 17) greeting = 'Good afternoon, sir.';
    else greeting = 'Good evening, sir.';

    const parts = [greeting, 'All systems operational.'];
    if (system?.uptime_formatted) parts.push(`Uptime: ${system.uptime_formatted}.`);
    if (memory?.total_memories) parts.push(`Memory: ${memory.total_memories} memories, ${memory.total_entities} entities.`);
    if (townhall?.active_sessions) parts.push(`${townhall.active_sessions} active agent sessions.`);
    parts.push('I am ready.');

    const fullText = parts.join(' ');
    setChatHistory(prev => [...prev, { role: 'assistant', text: fullText, time: new Date().toISOString() }]);
    speak(fullText);
  }, [system, memory, townhall, speak]);

  useEffect(() => {
    const timer = setTimeout(proactiveGreeting, 1500);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!system || !healthStatus) return;
    const last = systemStateRef.current;
    const cpu = system.cpu_percent;
    const mem = system.memory_percent;
    const disk = system.disk_percent;

    if (cpu > 95 && (!last.cpuAlert || Date.now() - last.cpuAlert > 300000)) {
      speak(`Warning. CPU at ${cpu.toFixed(0)} percent.`);
      last.cpuAlert = Date.now();
    }
    if (mem > 95 && (!last.memAlert || Date.now() - last.memAlert > 300000)) {
      speak(`Warning. Memory at ${mem.toFixed(0)} percent.`);
      last.memAlert = Date.now();
    }
    if (disk > 98 && (!last.diskAlert || Date.now() - last.diskAlert > 600000)) {
      speak(`Critical. Disk at ${disk.toFixed(0)} percent.`);
      last.diskAlert = Date.now();
    }
  }, [system, healthStatus, speak]);

  useEffect(() => {
    const proactiveCheck = async () => {
      try {
        const [healthRes, memRes] = await Promise.all([
          fetch(`${API}/api/health/status`).then(r => r.json()).catch(() => null),
          fetch(`${API}/api/memory/stats`).then(r => r.json()).catch(() => null),
        ]);

        if (healthRes?.alerts?.length > 0) {
          const alert = healthRes.alerts[0];
          const msg = `Health alert: ${alert.message || alert}`;
          if (!systemStateRef.current.lastHealthAlert || Date.now() - systemStateRef.current.lastHealthAlert > 600000) {
            speak(msg);
            systemStateRef.current.lastHealthAlert = Date.now();
          }
        }

        if (memRes?.total_memories && memRes.total_memories > 0 && !systemStateRef.current.memoryAnnounced) {
          systemStateRef.current.memoryAnnounced = true;
        }

        const gitRes = await fetch(`${API}/api/git/status`).then(r => r.json()).catch(() => null);
        if (gitRes?.dirty_files > 10 && !systemStateRef.current.gitWarned) {
          systemStateRef.current.gitWarned = true;
        }
      } catch (e) {}
    };

    const timer = setTimeout(proactiveCheck, 5000);
    const interval = setInterval(proactiveCheck, 60000);
    return () => { clearTimeout(timer); clearInterval(interval); };
  }, []);

  const fetchData = useCallback(async () => {
    try {
      const [sysRes, svcRes, toolRes, memRes, codeRes, agentRes, thRes, gitRes, healthRes, secRes, graphRes, entRes] = await Promise.all([
        fetch(`${API}/api/system`).then(r => r.json()).catch(() => null),
        fetch(`${API}/api/services`).then(r => r.json()).catch(() => null),
        fetch(`${API}/api/tools`).then(r => r.json()).catch(() => null),
        fetch(`${API}/api/memory`).then(r => r.json()).catch(() => null),
        fetch(`${API}/api/codebase`).then(r => r.json()).catch(() => null),
        fetch(`${API}/api/agents`).then(r => r.json()).catch(() => null),
        fetch(`${API}/api/townhall/status`).then(r => r.json()).catch(() => null),
        fetch(`${API}/api/git/status`).then(r => r.json()).catch(() => null),
        fetch(`${API}/api/health/status`).then(r => r.json()).catch(() => null),
        fetch(`${API}/api/security/stats`).then(r => r.json()).catch(() => null),
        fetch(`${API}/api/memory/graph`).then(r => r.json()).catch(() => null),
        fetch(`${API}/api/memory/entities`).then(r => r.json()).catch(() => null),
      ]);
      if (sysRes) setSystem(sysRes);
      if (svcRes) setServices(svcRes);
      if (toolRes) setTools(toolRes);
      if (memRes) setMemory(memRes);
      if (codeRes) setCodebase(codeRes);
      if (agentRes) setAgents(agentRes);
      if (thRes) setTownhall(thRes);
      if (gitRes) setGitStatus(gitRes);
      if (healthRes) setHealthStatus(healthRes);
      if (secRes) setSecurityStats(secRes);
      if (graphRes) setMemoryGraph(graphRes);
      if (entRes) setMemoryEntities(entRes.entities || []);
    } catch (e) {
      console.error('Fetch error:', e);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  useEffect(() => {
    try {
      const ws = new WebSocket('ws://localhost:8000/ws');
      ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === 'chat_response') {
          setChatHistory(prev => [...prev, { role: 'assistant', text: data.response, time: new Date().toISOString() }]);
          setIsTyping(false);
          setOrbPulse(1);
          setTimeout(() => setOrbPulse(0), 1000);
          speak(data.response);
        } else if (data.type === 'voice_response') {
          setChatHistory(prev => [...prev, { role: 'assistant', text: data.response, time: new Date().toISOString() }]);
          setIsTyping(false);
          setOrbPulse(1);
          setTimeout(() => setOrbPulse(0), 1000);
          speak(data.response);
        } else if (data.type === 'log_entry') {
          setLogs(prev => [...prev.slice(-499), data.log]);
        } else if (data.type === 'log_history') {
          setLogs(data.logs || []);
        } else if (data.type === 'connected') {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'subscribe_logs' }));
          }
        }
      };
      ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'subscribe_logs' }));
      };
      ws.onclose = () => setTimeout(() => {}, 3000);
      wsRef.current = ws;
    } catch (e) {}
  }, []);

  const sendMessage = useCallback((msg) => {
    setChatHistory(prev => [...prev, { role: 'user', text: msg, time: new Date().toISOString() }]);
    setIsTyping(true);
    setOrbPulse(0.5);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'chat', message: msg }));
    } else {
      fetch(`${API}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg }),
      })
        .then(r => r.json())
        .then(data => {
          setChatHistory(prev => [...prev, { role: 'assistant', text: data.response, time: new Date().toISOString() }]);
          setIsTyping(false);
          setOrbPulse(1);
          setTimeout(() => setOrbPulse(0), 1000);
          speak(data.response);
        });
    }
  }, []);

  const sendVoice = useCallback((text) => {
    setChatHistory(prev => [...prev, { role: 'user', text: `[Voice] ${text}`, time: new Date().toISOString() }]);
    setIsTyping(true);
    setOrbPulse(0.7);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'voice', message: text }));
    }
  }, []);

  const toolCategories = useMemo(() => {
    if (!tools?.tools) return [];
    return Object.entries(tools.tools).map(([cat, items]) => ({
      category: cat,
      count: items.length,
      items: items.slice(0, 5),
    }));
  }, [tools]);

  const timeStr = time.toLocaleTimeString('en-US', { hour12: false });
  const dateStr = time.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

  return (
    <div className="jarvis">
      <div className="jarvis-bg" />
      <div className="jarvis-grid" />

      <header className="jarvis-header">
        <div className="header-left">
          <div className="jarvis-logo">F.R.I.D.A.Y.</div>
          <div className="jarvis-subtitle">Fully Responsive Intelligent Digital Assistant Youth</div>
        </div>
        <div className="header-center">
          <div className="header-time">{timeStr}</div>
          <div className="header-date">{dateStr}</div>
        </div>
        <div className="header-right">
          <div className="header-status">
            <span className="status-dot active" />
            <span>ONLINE</span>
          </div>
          <div className="header-session">SESSION: {system?.session_id || '---'}</div>
          <div className="header-version">v3.0.0</div>
        </div>
      </header>

      <nav className="jarvis-nav">
        {['dashboard', 'graph', 'logs', 'tools', 'townhall'].map(view => (
          <button
            key={view}
            className={`nav-btn ${activeView === view ? 'active' : ''}`}
            onClick={() => setActiveView(view)}
          >
            {view.toUpperCase()}
          </button>
        ))}
      </nav>

      <div className="jarvis-main">
        <div className="jarvis-sidebar left-sidebar">
          <Panel title="SYSTEM" delay={0}>
            <div className="stat-grid">
              <div className="stat">
                <div className="stat-label">CPU</div>
                <div className="stat-value">{system?.cpu_percent?.toFixed(1) || '0'}%</div>
                <div className="stat-bar"><div className="stat-fill" style={{ width: `${system?.cpu_percent || 0}%` }} /></div>
              </div>
              <div className="stat">
                <div className="stat-label">MEMORY</div>
                <div className="stat-value">{system?.memory_used_gb || 0}GB / {system?.memory_total_gb || 0}GB</div>
                <div className="stat-bar"><div className="stat-fill mem" style={{ width: `${system?.memory_percent || 0}%` }} /></div>
              </div>
              <div className="stat">
                <div className="stat-label">DISK</div>
                <div className="stat-value">{system?.disk_used_gb || 0}GB / {system?.disk_total_gb || 0}GB</div>
                <div className="stat-bar"><div className="stat-fill disk" style={{ width: `${system?.disk_percent || 0}%` }} /></div>
              </div>
              <div className="stat">
                <div className="stat-label">UPTIME</div>
                <div className="stat-value">{system?.uptime_formatted || '0h 0m 0s'}</div>
              </div>
              <div className="stat">
                <div className="stat-label">HOSTNAME</div>
                <div className="stat-value small">{system?.hostname || '---'}</div>
              </div>
              <div className="stat">
                <div className="stat-label">PID</div>
                <div className="stat-value">{system?.pid || '---'}</div>
              </div>
            </div>
          </Panel>

          <Panel title="AGENTS" delay={200}>
            <div className="agent-grid">
              <div className="agent-stat">
                <div className="agent-num">{agents?.active_agents || townhall?.active_sessions || 0}</div>
                <div className="agent-label">Active</div>
              </div>
              <div className="agent-stat">
                <div className="agent-num">{townhall?.agents_registered || 0}</div>
                <div className="agent-label">Registered</div>
              </div>
              <div className="agent-stat">
                <div className="agent-num">{townhall?.total_messages || 0}</div>
                <div className="agent-label">Messages</div>
              </div>
              <div className="agent-stat">
                <div className="agent-num">{townhall?.open_agenda_items || 0}</div>
                <div className="agent-label">Agenda</div>
              </div>
            </div>
          </Panel>

          <Panel title="MEMORY" delay={400}>
            <div className="memory-stats">
              <div className="mem-stat"><span>{memory?.total_memories || 0}</span> Memories</div>
              <div className="mem-stat"><span>{memory?.total_entities || 0}</span> Entities</div>
              <div className="mem-stat"><span>{memory?.total_relationships || 0}</span> Links</div>
              <div className="mem-stat"><span>{memoryEntities.length}</span> Graph Nodes</div>
            </div>
            {memory?.memory_types && (
              <div className="memory-types">
                {Object.entries(memory.memory_types).map(([type, count]) => (
                  <div key={type} className="mem-type">
                    <span className="mem-type-name">{type}</span>
                    <span className="mem-type-count">{count}</span>
                  </div>
                ))}
              </div>
            )}
          </Panel>

          <Panel title="HEALTH" delay={500}>
            <div className="health-grid">
              <div className="health-item">
                <span className={`health-dot ${healthStatus?.metrics?.cpu_percent < 80 ? 'good' : 'warn'}`} />
                <span>CPU {healthStatus?.metrics?.cpu_percent?.toFixed(1) || 0}%</span>
              </div>
              <div className="health-item">
                <span className={`health-dot ${healthStatus?.metrics?.memory_percent < 85 ? 'good' : 'warn'}`} />
                <span>MEM {healthStatus?.metrics?.memory_percent?.toFixed(1) || 0}%</span>
              </div>
              <div className="health-item">
                <span className={`health-dot ${healthStatus?.metrics?.disk_percent < 90 ? 'good' : 'warn'}`} />
                <span>DISK {healthStatus?.metrics?.disk_percent?.toFixed(1) || 0}%</span>
              </div>
              <div className="health-item">
                <span className="health-dot good" />
                <span>PROCS {healthStatus?.metrics?.process_count || 0}</span>
              </div>
            </div>
          </Panel>
        </div>

        <div className="jarvis-center">
          {activeView === 'dashboard' && (
            <div className="orb-container">
              <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
                <ambientLight intensity={0.1} />
                <pointLight position={[10, 10, 10]} intensity={0.5} />
                <Orb pulse={orbPulse} />
                <Stars radius={100} depth={50} count={3000} factor={4} saturation={0} fade speed={1} />
                <OrbitControls enableZoom={false} enablePan={false} autoRotate autoRotateSpeed={0.5} />
              </Canvas>
              <div className="orb-label">FRIDAY CORE</div>
              <div className="orb-ring ring-1" />
              <div className="orb-ring ring-2" />
              <div className="orb-ring ring-3" />
            </div>
          )}

          {activeView === 'graph' && (
            <MemoryGraph data={memoryGraph} entities={memoryEntities} />
          )}

          {activeView === 'logs' && (
            <LogPanel logs={logs} />
          )}

          {activeView === 'tools' && (
            <div className="tools-view">
              <Panel title="ALL TOOLS" delay={0}>
                <div className="tools-full-grid">
                  {toolCategories.map((cat, i) => (
                    <div key={i} className="tool-category">
                      <div className="tool-cat-header">
                        <span className="tool-cat-name">{cat.category}</span>
                        <span className="tool-cat-count">{cat.count}</span>
                      </div>
                      <div className="tool-cat-items">
                        {cat.items.map((t, j) => (
                          <div key={j} className="tool-item-full">
                            <span className="tool-name-full">{t.name}</span>
                            <span className="tool-desc-full">{t.description}</span>
                          </div>
                        ))}
                        {cat.count > 5 && <div className="tool-more">+{cat.count - 5} more</div>}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="tool-total-full">
                  <span>{tools?.total || 0}</span> TOTAL TOOLS ACROSS <span>{toolCategories.length}</span> CATEGORIES
                </div>
              </Panel>
            </div>
          )}

          {activeView === 'townhall' && (
            <div className="townhall-view">
              <TownhallPanel full />
            </div>
          )}
        </div>

        <div className="jarvis-sidebar right-sidebar">
          <Panel title="GIT" delay={100}>
            <div className="git-info">
              <div className="git-stat"><span className="git-label">Branch:</span> {gitStatus?.branch || '---'}</div>
              <div className="git-stat"><span className="git-label">Dirty:</span> {gitStatus?.dirty_files || 0} files</div>
              <div className="git-stat"><span className="git-label">Repo:</span> {gitStatus?.is_repo ? 'Yes' : 'No'}</div>
              {gitStatus?.latest_commit && (
                <div className="git-commit">
                  <span className="git-hash">{gitStatus.latest_commit.hash?.slice(0, 8)}</span>
                  <span className="git-msg">{gitStatus.latest_commit.message?.slice(0, 40)}</span>
                </div>
              )}
            </div>
          </Panel>

          <Panel title="CODEBASE" delay={200}>
            <div className="code-stats">
              <div className="code-stat"><span>{codebase?.total_files || 0}</span> Files</div>
              <div className="code-stat"><span>{(codebase?.total_lines_of_code || 0).toLocaleString()}</span> Lines</div>
              <div className="code-stat"><span>{codebase?.total_functions || 0}</span> Functions</div>
              <div className="code-stat"><span>{codebase?.total_classes || 0}</span> Classes</div>
              <div className="code-stat"><span>{codebase?.total_imports || 0}</span> Imports</div>
              <div className="code-stat"><span>{codebase?.num_cycles || 0}</span> Cycles</div>
            </div>
          </Panel>

          <Panel title="SECURITY" delay={300}>
            <div className="security-info">
              <div className="sec-stat"><span>Scans:</span> {securityStats?.total_scans || 0}</div>
              <div className="sec-stat"><span>Vulns:</span> {securityStats?.total_vulnerabilities || 0}</div>
              <div className="sec-status">
                <span className={`health-dot ${securityStats?.total_vulnerabilities === 0 ? 'good' : 'warn'}`} />
                {securityStats?.total_vulnerabilities === 0 ? 'SECURE' : 'ISSUES FOUND'}
              </div>
            </div>
          </Panel>

          <Panel title="SERVICES" delay={400}>
            <div className="service-list">
              {services?.services && Object.entries(services.services).map(([name, info], i) => {
                const status = typeof info === 'string' ? info : (info?.status || 'unknown');
                return (
                  <div key={i} className="service-item">
                    <span className={`svc-dot ${status === 'running' ? 'active' : ''}`} />
                    <span className="svc-name">{name}</span>
                    <span className="svc-status">{status}</span>
                  </div>
                );
              })}
            </div>
          </Panel>

          <Panel title="TOOLS BY CATEGORY" delay={500}>
            <div className="tool-grid">
              {toolCategories.map((t, i) => (
                <div key={i} className="tool-item">
                  <div className="tool-name">{t.category}</div>
                  <div className="tool-count">{t.count}</div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>

      <div className="jarvis-chat">
        <ChatPanel messages={chatHistory} onSend={sendMessage} isTyping={isTyping} />
      </div>

      <VoiceControl onVoice={sendVoice} />

      <StatusBar system={system} health={healthStatus} git={gitStatus} />
    </div>
  );
}

export default App;
