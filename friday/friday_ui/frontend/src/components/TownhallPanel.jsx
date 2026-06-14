import React, { useState, useEffect } from 'react';
import Panel from './Panel';

const API = 'http://localhost:8000';

export default function TownhallPanel() {
  const [townhall, setTownhall] = useState(null);
  const [sessions, setSessions] = useState([]);

  useEffect(() => {
    const fetchTownhall = async () => {
      try {
        const [statusRes, sessionsRes] = await Promise.all([
          fetch(`${API}/api/townhall/status`),
          fetch(`${API}/api/townhall/sessions`),
        ]);
        if (statusRes.ok) setTownhall(await statusRes.json());
        if (sessionsRes.ok) {
          const data = await sessionsRes.json();
          setSessions(data.sessions || []);
        }
      } catch (e) {}
    };
    fetchTownhall();
    const interval = setInterval(fetchTownhall, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Panel title="TOWNHALL" delay={600}>
      <div className="townhall-panel">
        <div className="th-grid">
          <div className="th-stat">
            <div className="th-num">{townhall?.active_sessions || 0}</div>
            <div className="th-label">Active</div>
          </div>
          <div className="th-stat">
            <div className="th-num">{townhall?.total_sessions || 0}</div>
            <div className="th-label">Sessions</div>
          </div>
          <div className="th-stat">
            <div className="th-num">{townhall?.agents_registered || 0}</div>
            <div className="th-label">Agents</div>
          </div>
          <div className="th-stat">
            <div className="th-num">{townhall?.total_messages || 0}</div>
            <div className="th-label">Messages</div>
          </div>
        </div>
        <div className="th-sessions">
          {sessions.length === 0 && <div className="th-empty">No active sessions</div>}
          {sessions.slice(0, 5).map((s, i) => (
            <div key={i} className="th-session">
              <span className={`th-dot ${s.status === 'active' ? 'active' : ''}`} />
              <span className="th-topic">{s.topic || 'Unnamed'}</span>
              <span className="th-agents">{s.agents?.length || 0} agents</span>
            </div>
          ))}
        </div>
      </div>
    </Panel>
  );
}
