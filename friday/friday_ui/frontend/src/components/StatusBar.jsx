import React from 'react';

export default function StatusBar({ system }) {
  return (
    <div className="status-bar">
      <div className="status-item">
        <span className="status-label">PLATFORM</span>
        <span className="status-val">{system?.platform || '---'}</span>
      </div>
      <div className="status-item">
        <span className="status-label">PYTHON</span>
        <span className="status-val">{system?.python_version || '---'}</span>
      </div>
      <div className="status-item">
        <span className="status-label">HOSTNAME</span>
        <span className="status-val">{system?.hostname || '---'}</span>
      </div>
      <div className="status-item">
        <span className="status-label">TOOLS</span>
        <span className="status-val">{system?.services?.tools || 0}</span>
      </div>
      <div className="status-item">
        <span className="status-label">MEMORY</span>
        <span className="status-val">{system?.memory_entities || 0} entities</span>
      </div>
      <div className="status-item">
        <span className="status-label">API</span>
        <span className="status-val online">ACTIVE</span>
      </div>
    </div>
  );
}
