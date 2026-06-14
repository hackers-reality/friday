import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stars } from '@react-three/drei';
import Orb from './components/Orb';
import Panel from './components/Panel';
import ChatPanel from './components/ChatPanel';
import StatusBar from './components/StatusBar';
import './App.css';

const API = 'http://localhost:8000';

function App() {
  const [system, setSystem] = useState(null);
  const [services, setServices] = useState(null);
  const [tools, setTools] = useState(null);
  const [memory, setMemory] = useState(null);
  const [codebase, setCodebase] = useState(null);
  const [agents, setAgents] = useState(null);
  const [chatMessages, setChatMessages] = useState([
    { role: 'assistant', text: 'Good evening, sir. All systems operational.' }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const [orbPulse, setOrbPulse] = useState(0);
  const [time, setTime] = useState(new Date());
  const wsRef = useRef(null);

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const fetchData = useCallback(async () => {
    try {
      const [sysRes, svcRes, toolRes, memRes, codeRes, agentRes] = await Promise.all([
        fetch(`${API}/api/system`),
        fetch(`${API}/api/services`),
        fetch(`${API}/api/tools`),
        fetch(`${API}/api/memory`),
        fetch(`${API}/api/codebase`),
        fetch(`${API}/api/agents`),
      ]);
      setSystem(await sysRes.json());
      setServices(await svcRes.json());
      setTools(await toolRes.json());
      setMemory(await memRes.json());
      setCodebase(await codeRes.json());
      setAgents(await agentRes.json());
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
          setChatMessages(prev => [...prev, { role: 'assistant', text: data.response }]);
          setIsTyping(false);
          setOrbPulse(1);
          setTimeout(() => setOrbPulse(0), 1000);
        }
      };
      ws.onclose = () => setTimeout(() => {}, 3000);
      wsRef.current = ws;
    } catch (e) {}
  }, []);

  const sendMessage = useCallback((msg) => {
    setChatMessages(prev => [...prev, { role: 'user', text: msg }]);
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
          setChatMessages(prev => [...prev, { role: 'assistant', text: data.response }]);
          setIsTyping(false);
          setOrbPulse(1);
          setTimeout(() => setOrbPulse(0), 1000);
        });
    }
  }, []);

  const toolCategories = useMemo(() => {
    if (!tools?.tools) return [];
    return Object.entries(tools.tools).map(([cat, items]) => ({
      category: cat,
      count: items.length,
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
        </div>
      </header>

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
                <div className="stat-value">{system?.uptime_formatted || '0h 0m'}</div>
              </div>
            </div>
          </Panel>

          <Panel title="AGENTS" delay={200}>
            <div className="agent-grid">
              <div className="agent-stat">
                <div className="agent-num">{agents?.active_agents || 0}</div>
                <div className="agent-label">Active</div>
              </div>
              <div className="agent-stat">
                <div className="agent-num">{agents?.sessions || 0}</div>
                <div className="agent-label">Sessions</div>
              </div>
              <div className="agent-stat">
                <div className="agent-num">{agents?.deliberations || 0}</div>
                <div className="agent-label">Deliberations</div>
              </div>
            </div>
          </Panel>

          <Panel title="MEMORY" delay={400}>
            <div className="memory-stats">
              <div className="mem-stat"><span>{memory?.entities || 0}</span> Entities</div>
              <div className="mem-stat"><span>{memory?.topics || 0}</span> Topics</div>
              <div className="mem-stat"><span>{memory?.total_items || 0}</span> Items</div>
            </div>
          </Panel>
        </div>

        <div className="jarvis-center">
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
        </div>

        <div className="jarvis-sidebar right-sidebar">
          <Panel title="TOOLS" delay={100}>
            <div className="tool-grid">
              {toolCategories.map((t, i) => (
                <div key={i} className="tool-item">
                  <div className="tool-name">{t.category}</div>
                  <div className="tool-count">{t.count}</div>
                </div>
              ))}
              <div className="tool-total">
                <span>{tools?.total || 0}</span> TOTAL TOOLS
              </div>
            </div>
          </Panel>

          <Panel title="CODEBASE" delay={300}>
            <div className="code-stats">
              <div className="code-stat"><span>{codebase?.total_files || 0}</span> Files</div>
              <div className="code-stat"><span>{(codebase?.total_lines_of_code || 0).toLocaleString()}</span> Lines</div>
              <div className="code-stat"><span>{codebase?.total_functions || 0}</span> Functions</div>
              <div className="code-stat"><span>{codebase?.total_classes || 0}</span> Classes</div>
            </div>
          </Panel>

          <Panel title="SERVICES" delay={500}>
            <div className="service-list">
              {services?.services && Object.entries(services.services).map(([name, status], i) => (
                <div key={i} className="service-item">
                  <span className={`svc-dot ${status === 'running' ? 'active' : ''}`} />
                  <span className="svc-name">{name}</span>
                  <span className="svc-status">{status}</span>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>

      <div className="jarvis-chat">
        <ChatPanel messages={chatMessages} onSend={sendMessage} isTyping={isTyping} />
      </div>

      <StatusBar system={system} />
    </div>
  );
}

export default App;
