"""
Friday Dashboard - Web UI for Friday.
Simple HTML/JS dashboard to interact with Friday.
"""
from __future__ import annotations

import os
import sys
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path


# ─── Dashboard HTML ────────────────────────────#

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Friday Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: #eee; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { color: #0f4c75; margin-bottom: 30px; text-align: center; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: #16213e; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .card h2 { color: #0f4c75; margin-bottom: 15px; font-size: 1.2em; }
        .status { display: flex; align-items: center; margin: 10px 0; }
        .status-dot { width: 10px; height: 10px; border-radius: 50%; margin-right: 10px; }
        .status-dot.online { background: #4CAF50; }
        .status-dot.offline { background: #f44336; }
        button { background: #0f4c75; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 5px; }
        button:hover { background: #0a3d62; }
        input, select, textarea { width: 100%; padding: 10px; margin: 5px 0; background: #1a1a2e; color: #eee; border: 1px solid #0f4c75; border-radius: 5px; }
        .output { background: #0a0a1e; padding: 10px; border-radius: 5px; margin-top: 10px; max-height: 200px; overflow-y: auto; font-family: monospace; font-size: 0.9em; }
        .module-list { display: flex; flex-wrap: wrap; gap: 10px; }
        .module-tag { background: #0f4c75; padding: 5px 10px; border-radius: 15px; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Friday Dashboard</h1>
        
        <div class="grid">
            <!-- Status Card -->
            <div class="card">
                <h2>📊 System Status</h2>
                <div class="status">
                    <span class="status-dot online"></span>
                    <span>Friday Online</span>
                </div>
                <p>Uptime: <span id="uptime">--</span></p>
                <p>Modules: <span id="module-count">--</span></p>
                <button onclick="checkStatus()">Refresh</button>
            </div>
            
            <!-- Command Card -->
            <div class="card">
                <h2>💬 Send Command</h2>
                <input type="text" id="command-input" placeholder="Enter command (e.g., status, help)" />
                <button onclick="sendCommand()">Send</button>
                <div class="output" id="command-output"></div>
            </div>
            
            <!-- Modules Card -->
            <div class="card">
                <h2>📦 Modules</h2>
                <div class="module-list" id="module-list">
                    <span class="module-tag">Loading...</span>
                </div>
                <button onclick="listModules()">Refresh</button>
            </div>
            
            <!-- Quick Actions Card -->
            <div class="card">
                <h2>⚡ Quick Actions</h2>
                <button onclick="sendCommandAction('network status')">Network Status</button>
                <button onclick="sendCommandAction('crypto status')">Crypto Status</button>
                <button onclick="sendCommandAction('web status')">Web Status</button>
                <button onclick="sendCommandAction('vision status')">Vision Status</button>
                <button onclick="sendCommandAction('security status')">Security Status</button>
                <button onclick="sendCommandAction('monitor status')">Monitor Status</button>
            </div>
            
            <!-- AI Chat Card -->
            <div class="card">
                <h2>🧠 AI Chat</h2>
                <textarea id="chat-input" rows="3" placeholder="Ask Friday..."></textarea>
                <button onclick="sendChat()">Send</button>
                <div class="output" id="chat-output"></div>
            </div>
            
            <!-- System Metrics Card -->
            <div class="card">
                <h2>📈 System Metrics</h2>
                <p>CPU: <span id="cpu-usage">--</span>%</p>
                <p>Memory: <span id="mem-usage">--</span>%</p>
                <p>Disk: <span id="disk-usage">--</span>%</p>
                <button onclick="getMetrics()">Refresh</button>
            </div>
        </div>
    </div>
    
    <script>
        const API_BASE = 'http://127.0.0.1:8000';
        
        function checkStatus() {
            fetch(`${API_BASE}/api/status`)
                .then(r => r.json())
                .then(data => {
                    document.getElementById('uptime').textContent = data.uptime || '--';
                    document.getElementById('module-count').textContent = data.module_count || '--';
                })
                .catch(e => console.error('Status error:', e));
        }
        
        function sendCommand() {
            const input = document.getElementById('command-input');
            const output = document.getElementById('command-output');
            const cmd = input.value.trim();
            
            if (!cmd) return;
            
            output.textContent = 'Processing...';
            
            fetch(`${API_BASE}/api/command`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({command: cmd})
            })
            .then(r => r.json())
            .then(data => {
                output.textContent = JSON.stringify(data, null, 2);
                input.value = '';
            })
            .catch(e => {
                output.textContent = 'Error: ' + e.message;
            });
        }
        
        function sendCommandAction(cmd) {
            document.getElementById('command-input').value = cmd;
            sendCommand();
        }
        
        function listModules() {
            fetch(`${API_BASE}/api/modules`)
                .then(r => r.json())
                .then(data => {
                    const list = document.getElementById('module-list');
                    list.innerHTML = '';
                    (data.modules || []).forEach(m => {
                        const tag = document.createElement('span');
                        tag.className = 'module-tag';
                        tag.textContent = m.name || m;
                        list.appendChild(tag);
                    });
                })
                .catch(e => console.error('Modules error:', e));
        }
        
        function sendChat() {
            const input = document.getElementById('chat-input');
            const output = document.getElementById('chat-output');
            const message = input.value.trim();
            
            if (!message) return;
            
            output.textContent = 'Thinking...';
            
            fetch(`${API_BASE}/api/ai/chat`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message: message})
            })
            .then(r => r.json())
            .then(data => {
                output.textContent = data.response || JSON.stringify(data);
                input.value = '';
            })
            .catch(e => {
                output.textContent = 'Error: ' + e.message;
            });
        }
        
        function getMetrics() {
            fetch(`${API_BASE}/api/monitor/metrics`)
                .then(r => r.json())
                .then(data => {
                    document.getElementById('cpu-usage').textContent = data.cpu?.percent || '--';
                    document.getElementById('mem-usage').textContent = data.memory?.percent || '--';
                    document.getElementById('disk-usage').textContent = data.disk?.percent || '--';
                })
                .catch(e => console.error('Metrics error:', e));
        }
        
        // Initialize
        checkStatus();
        listModules();
        getMetrics();
        
        // Auto-refresh every 30 seconds
        setInterval(() => {
            checkStatus();
            getMetrics();
        }, 30000);
    </script>
</body>
</html>
"""


# ─── Dashboard Server ────────────────────────────#

class DashboardServer:
    """Simple HTTP server for dashboard."""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.server = None
        self.running = False
        
    def start(self):
        """Start the dashboard server."""
        try:
            from http.server import HTTPServer, SimpleHTTPRequestHandler
            import threading
            
            class Handler(SimpleHTTPRequestHandler):
                def do_GET(self):
                    if self.path == '/' or self.path == '/index.html':
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        self.wfile.write(DASHBOARD_HTML.encode())
                    else:
                        self.send_error(404)
                
                def log_message(self, format, *args):
                    pass  # Suppress logs
            
            self.server = HTTPServer(('0.0.0.0', self.port), Handler)
            self.running = True
            
            def serve():
                try:
                    self.server.serve_forever()
                except:
                    pass
            
            thread = threading.Thread(target=serve, daemon=True)
            thread.start()
            
            return {
                "success": True,
                "url": f"http://localhost:{self.port}",
                "port": self.port,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def stop(self):
        """Stop the dashboard server."""
        if self.server:
            self.server.shutdown()
            self.running = False


# ─── Dashboard Tool for Friday ────────────────────────────#

def dashboard_tool(
    action: str = "status",
    params: Dict = None,
) -> str:
    """
    Friday tool for dashboard operations.
    Actions: status, start, stop, get_html
    """
    params = params or {}
    
    if action == "status":
        lines = ["### DASHBOARD STATUS", ""]
        lines.append("**Available Features**:")
        lines.append("  - System status overview")
        lines.append("  - Command interface")
        lines.append("  - Module listing")
        lines.append("  - Quick action buttons")
        lines.append("  - AI chat interface")
        lines.append("  - System metrics display")
        lines.append("")
        lines.append("**Default Port**: 8080")
        return "\n".join(lines)
    
    if action == "start":
        port = params.get("port", 8080)
        server = DashboardServer(port)
        result = server.start()
        if result.get("success"):
            return f"### DASHBOARD START\n\n✅ Dashboard started at {result['url']}"
        else:
            return f"❌ Start error: {result.get('error', 'Unknown')}"
    
    if action == "stop":
        # In reality, would need to keep reference to server
        return "### DASHBOARD STOP\n\n✅ Stop signal sent (not fully implemented)."
    
    if action == "get_html":
        return DASHBOARD_HTML
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Friday Dashboard...\n")
    
    # Test start
    print("--- Dashboard Start ---")
    print(dashboard_tool("start", params={"port": 8080}))
    print("\nDashboard running at http://localhost:8080")
    print("Press Ctrl+C to stop.")
    
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping dashboard...")
