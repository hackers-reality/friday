import React from 'react';

export default function StatusBar({ system, health, git }) {
  return (
    <div className="jarvis-statusbar">
      <div className="statusbar-left">
        <div className="statusbar-item">
          <span className={`statusbar-dot ${system?.cpu_percent < 80 ? 'green' : system?.cpu_percent < 95 ? 'yellow' : 'red'}`} />
          <span>CPU {system?.cpu_percent?.toFixed(1) || 0}%</span>
        </div>
        <div className="statusbar-item">
          <span className={`statusbar-dot ${system?.memory_percent < 85 ? 'green' : system?.memory_percent < 95 ? 'yellow' : 'red'}`} />
          <span>MEM {system?.memory_percent?.toFixed(1) || 0}%</span>
        </div>
        <div className="statusbar-item">
          <span className={`statusbar-dot ${system?.disk_percent < 90 ? 'green' : system?.disk_percent < 95 ? 'yellow' : 'red'}`} />
          <span>DISK {system?.disk_percent?.toFixed(1) || 0}%</span>
        </div>
        <div className="statusbar-item">
          <span className="statusbar-dot green" />
          <span>PID {system?.pid || '---'}</span>
        </div>
      </div>
      <div className="statusbar-right">
        <div className="statusbar-item">
          <span>{system?.hostname || '---'}</span>
        </div>
        <div className="statusbar-item">
          <span>{system?.platform || '---'}</span>
        </div>
        <div className="statusbar-item">
          <span>SESSION {system?.session_id || '---'}</span>
        </div>
        <div className="statusbar-item">
          <span>UP {system?.uptime_formatted || '0h 0m 0s'}</span>
        </div>
        {git?.branch && (
          <div className="statusbar-item">
            <span className="statusbar-dot green" />
            <span>GIT {git.branch}</span>
          </div>
        )}
      </div>
    </div>
  );
}
