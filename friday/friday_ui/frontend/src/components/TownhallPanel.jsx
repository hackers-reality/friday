import React, { useState, useEffect } from 'react';
import Panel from './Panel';

const API = 'http://localhost:8000';

export default function TownhallPanel({ full }) {
  const [townhall, setTownhall] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [agents, setAgents] = useState([]);
  const [agenda, setAgenda] = useState([]);

  useEffect(() => {
    const fetchTownhall = async () => {
      try {
        const [statusRes, sessionsRes, agentsRes, agendaRes] = await Promise.all([
          fetch(`${API}/api/townhall/status`),
          fetch(`${API}/api/townhall/sessions`),
          fetch(`${API}/api/townhall/agents`),
          fetch(`${API}/api/townhall/agenda`),
        ]);
        if (statusRes.ok) setTownhall(await statusRes.json());
        if (sessionsRes.ok) {
          const data = await sessionsRes.json();
          setSessions(data.sessions || []);
        }
        if (agentsRes.ok) {
          const data = await agentsRes.json();
          setAgents(data.agents || data || []);
        }
        if (agendaRes.ok) {
          const data = await agendaRes.json();
          setAgenda(data.agenda || data || []);
        }
      } catch (e) {}
    };
    fetchTownhall();
    const interval = setInterval(fetchTownhall, 10000);
    return () => clearInterval(interval);
  }, []);

  if (full) {
    return (
      <div className="townhall-full">
        <Panel title="TOWNHALL — MULTI-AGENT DELIBERATION" delay={0}>
          <div className="th-full-grid">
            <div className="th-full-stats">
              <div className="th-full-stat">
                <div className="th-full-num">{townhall?.active_sessions || 0}</div>
                <div className="th-full-label">Active Sessions</div>
              </div>
              <div className="th-full-stat">
                <div className="th-full-num">{townhall?.total_sessions || 0}</div>
                <div className="th-full-label">Total Sessions</div>
              </div>
              <div className="th-full-stat">
                <div className="th-full-num">{townhall?.agents_registered || 0}</div>
                <div className="th-full-label">Agents</div>
              </div>
              <div className="th-full-stat">
                <div className="th-full-num">{townhall?.total_messages || 0}</div>
                <div className="th-full-label">Messages</div>
              </div>
              <div className="th-full-stat">
                <div className="th-full-num">{townhall?.total_votes_cast || 0}</div>
                <div className="th-full-label">Votes</div>
              </div>
              <div className="th-full-stat">
                <div className="th-full-num">{townhall?.open_action_items || 0}</div>
                <div className="th-full-label">Action Items</div>
              </div>
            </div>

            <div className="th-full-section">
              <div className="th-section-title">ACTIVE SESSIONS</div>
              {sessions.length === 0 && <div className="th-empty">No active sessions</div>}
              {sessions.map((s, i) => (
                <div key={i} className="th-session-full">
                  <div className="th-session-header">
                    <span className={`th-dot ${s.status === 'active' ? 'active' : ''}`} />
                    <span className="th-topic">{s.topic || 'Unnamed Session'}</span>
                    <span className="th-session-status">{s.status || 'unknown'}</span>
                  </div>
                  {s.agents && (
                    <div className="th-session-agents">
                      Agents: {Array.isArray(s.agents) ? s.agents.join(', ') : s.agents}
                    </div>
                  )}
                  {s.messages && (
                    <div className="th-session-messages">
                      {s.messages.slice(-3).map((m, j) => (
                        <div key={j} className="th-msg">
                          <span className="th-msg-role">{m.role || 'agent'}:</span>
                          <span className="th-msg-text">{(m.content || m.message || '').slice(0, 100)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="th-full-section">
              <div className="th-section-title">REGISTERED AGENTS</div>
              {agents.length === 0 && <div className="th-empty">No agents registered</div>}
              <div className="th-agents-grid">
                {agents.map((a, i) => (
                  <div key={i} className="th-agent-card">
                    <div className="th-agent-name">{a.name || a.id || `Agent ${i}`}</div>
                    <div className="th-agent-role">{a.role || a.type || 'general'}</div>
                    <div className="th-agent-status">{a.status || 'ready'}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="th-full-section">
              <div className="th-section-title">AGENDA ITEMS</div>
              {agenda.length === 0 && <div className="th-empty">No agenda items</div>}
              {agenda.map((item, i) => (
                <div key={i} className="th-agenda-item">
                  <span className="th-agenda-priority">{item.priority || 'normal'}</span>
                  <span className="th-agenda-text">{item.text || item.title || JSON.stringify(item)}</span>
                  <span className="th-agenda-status">{item.status || 'open'}</span>
                </div>
              ))}
            </div>
          </div>
        </Panel>
      </div>
    );
  }

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
              <span className="th-agents">{Array.isArray(s.agents) ? s.agents.length : 0} agents</span>
            </div>
          ))}
        </div>
      </div>
    </Panel>
  );
}
