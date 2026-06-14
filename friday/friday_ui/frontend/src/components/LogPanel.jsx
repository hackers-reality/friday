import React, { useRef, useEffect, useState } from 'react';

export default function LogPanel({ logs }) {
  const logsEndRef = useRef(null);
  const [filter, setFilter] = useState('all');
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    if (autoScroll) {
      logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const filteredLogs = logs.filter(log => {
    if (filter === 'all') return true;
    return log.level === filter;
  });

  const levelColors = {
    info: '#00d4ff',
    warning: '#ffeaa7',
    error: '#ff6b6b',
    debug: '#636e72',
    critical: '#ff4757',
  };

  const levelCounts = logs.reduce((acc, log) => {
    acc[log.level] = (acc[log.level] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="log-panel">
      <div className="log-header">
        <div className="log-title">TERMINAL LOGS</div>
        <div className="log-filters">
          <button
            className={`log-filter-btn ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            ALL ({logs.length})
          </button>
          {Object.entries(levelCounts).map(([level, count]) => (
            <button
              key={level}
              className={`log-filter-btn ${filter === level ? 'active' : ''}`}
              onClick={() => setFilter(level)}
              style={{ borderColor: levelColors[level] }}
            >
              {level.toUpperCase()} ({count})
            </button>
          ))}
        </div>
        <div className="log-controls">
          <label className="auto-scroll-label">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
            />
            Auto-scroll
          </label>
        </div>
      </div>

      <div className="log-content">
        {filteredLogs.length === 0 && (
          <div className="log-empty">Waiting for logs...</div>
        )}
        {filteredLogs.map((log, i) => (
          <div key={i} className={`log-entry log-${log.level}`}>
            <span className="log-time">
              {log.timestamp ? new Date(log.timestamp).toLocaleTimeString('en-US', { hour12: false }) : ''}
            </span>
            <span className="log-level" style={{ color: levelColors[log.level] || '#8ec8e8' }}>
              [{(log.level || 'info').toUpperCase().padEnd(7)}]
            </span>
            <span className="log-module">{log.module || 'system'}</span>
            <span className="log-message">{log.message}</span>
          </div>
        ))}
        <div ref={logsEndRef} />
      </div>
    </div>
  );
}
