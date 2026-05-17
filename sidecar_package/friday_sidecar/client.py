"""
FRIDAY Sidecar Client — runs on remote devices to extend FRIDAY's reach.
Registers with the main FRIDAY instance, then serves an HTTP endpoint
for command dispatch (exec, ping, capabilities, shutdown).
"""

from __future__ import annotations
import argparse
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional


# ─── Configuration ───────────────────────────────────────

SIDECAR_CONFIG_DIR = os.path.expanduser("~/.friday_sidecar")
CONFIG_FILE = os.path.join(SIDECAR_CONFIG_DIR, "config.json")


def _load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_config(config: dict):
    os.makedirs(SIDECAR_CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


# ─── Command Handlers ────────────────────────────────────

def handle_ping(params: dict = None) -> dict:
    return {"status": "pong", "timestamp": datetime.now().isoformat()}


def handle_capabilities(params: dict = None) -> dict:
    config = _load_config()
    return {
        "capabilities": config.get("capabilities", ["ping", "exec", "system_info"]),
        "sidecar_type": config.get("type", "desktop"),
    }


def handle_exec(params: dict = None) -> dict:
    cmd = (params or {}).get("cmd", "")
    if not cmd:
        return {"error": "No cmd provided"}
    timeout = (params or {}).get("timeout", 30)
    try:
        use_shell = sys.platform == "win32"
        proc = subprocess.run(
            cmd if use_shell else cmd.split(),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=use_shell,
        )
        return {
            "stdout": proc.stdout[-2000:],
            "stderr": proc.stderr[-2000:],
            "returncode": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}
    except Exception as e:
        return {"error": str(e)}


def handle_system_info(params: dict = None) -> dict:
    import platform
    return {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "release": platform.release(),
        "python": sys.version,
    }


def handle_shutdown(params: dict = None) -> dict:
    t = threading.Thread(target=_delayed_shutdown, daemon=True)
    t.start()
    return {"status": "shutting_down"}


def _delayed_shutdown():
    time.sleep(0.5)
    os._exit(0)


COMMAND_HANDLERS = {
    "ping": handle_ping,
    "capabilities": handle_capabilities,
    "exec": handle_exec,
    "system_info": handle_system_info,
    "shutdown": handle_shutdown,
}


# ─── HTTP Server ─────────────────────────────────────────

class SidecarRequestHandler(BaseHTTPRequestHandler):
    """Handles command dispatch from FRIDAY."""

    def _respond(self, data: dict, status: int = 200):
        body = json.dumps(data, default=str)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            payload = json.loads(body) if body else {}
        except Exception:
            self._respond({"error": "Invalid JSON"}, 400)
            return

        command = payload.get("command", "")
        params = payload.get("params", {})

        # Verify JWT token if provided
        config = _load_config()
        token = config.get("auth_token", "")
        auth_header = self.headers.get("Authorization", "")
        if token:
            if not auth_header.startswith("Bearer "):
                self._respond({"error": "Missing Authorization header"}, 401)
                return
            if auth_header[7:] != token:
                self._respond({"error": "Invalid token"}, 403)
                return

        handler = COMMAND_HANDLERS.get(command)
        if not handler:
            self._respond({"error": f"Unknown command: {command}"}, 400)
            return

        try:
            result = handler(params)
            self._respond(result)
        except Exception as e:
            self._respond({"error": str(e)}, 500)

    def do_GET(self):
        if self.path == "/health":
            self._respond({"status": "alive", "name": _load_config().get("name", "unknown")})
        else:
            self._respond({"error": "Not found"}, 404)

    def log_message(self, format, *args):
        pass  # Suppress HTTP log spam


def run_http_server(host: str, port: int):
    """Run the HTTP command server."""
    server = HTTPServer((host, port), SidecarRequestHandler)
    print(f"[SIDECAR] HTTP server listening on {host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[SIDECAR] Shutting down...")
        server.shutdown()


# ─── Registration ────────────────────────────────────────

def register_with_friday(server_url: str, token: str, name: str,
                         sidecar_type: str, capabilities: list, port: int):
    """Register this sidecar with the main FRIDAY instance."""
    hostname = socket.gethostname()
    try:
        ip = socket.gethostbyname(hostname)
    except Exception:
        ip = "0.0.0.0"

    payload = {
        "token": token,
        "name": name,
        "type": sidecar_type,
        "host": ip,
        "port": port,
        "capabilities": capabilities,
    }

    url = f"{server_url.rstrip('/')}/api/sidecars/register"
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        if result.get("success"):
            print(f"[SIDECAR] Registered with FRIDAY as #{result.get('sidecar_id')}")
            return True
        else:
            print(f"[SIDECAR] Registration failed: {result.get('error', 'unknown')}")
            return False
    except urllib.error.HTTPError as e:
        print(f"[SIDECAR] HTTP {e.code}: {e.read().decode()[:200]}")
        return False
    except Exception as e:
        print(f"[SIDECAR] Registration error: {e}")
        return False


def heartbeat_loop(server_url: str, name: str, interval: int = 30):
    """Periodically send heartbeats to FRIDAY."""
    while True:
        try:
            url = f"{server_url.rstrip('/')}/api/sidecars/heartbeat"
            payload = json.dumps({"name": name, "status": "alive"}).encode("utf-8")
            req = urllib.request.Request(
                url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=5):
                pass
        except Exception:
            pass
        time.sleep(interval)


# ─── CLI ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="FRIDAY Sidecar — extend FRIDAY across your network",
    )
    parser.add_argument("--server", help="FRIDAY server URL (e.g. http://192.168.1.100:8090)")
    parser.add_argument("--token", help="Authentication token from FRIDAY")
    parser.add_argument("--name", default=socket.gethostname(), help="Sidecar name (default: hostname)")
    parser.add_argument("--type", default="desktop",
                        choices=["desktop", "browser", "filesystem", "system_monitor",
                                 "code_workspace", "smart_home"],
                        help="Sidecar type")
    parser.add_argument("--port", type=int, default=0, help="HTTP server port (default: auto)")
    parser.add_argument("--capabilities", default="ping,exec,system_info",
                        help="Comma-separated capabilities")
    parser.add_argument("--install-token", help="Save a token to config and exit")
    parser.add_argument("--server-port", type=int, default=8095,
                        help="Local HTTP server port (default: 8095)")

    args = parser.parse_args()

    # Handle --install-token: save token to config and exit
    if args.install_token:
        config = _load_config()
        config["auth_token"] = args.install_token
        _save_config(config)
        print(f"[SIDECAR] Token saved to {CONFIG_FILE}")
        return

    # Load config for token
    config = _load_config()
    token = args.token or config.get("auth_token", "")

    if not args.server:
        print("[SIDECAR] Error: --server is required to start sidecar")
        print("  First, get a token from FRIDAY:")
        print("    friday-sidecar --install-token YOUR_TOKEN")
        print("  Then start:")
        print("    friday-sidecar --server http://FRIDAY_IP:8090")
        sys.exit(1)

    if not token:
        print("[SIDECAR] Error: No authentication token.")
        print("  Use --token TOKEN or --install-token TOKEN first")
        sys.exit(1)

    name = args.name
    port = args.server_port
    caps = [c.strip() for c in args.capabilities.split(",")]

    # Save config
    config["name"] = name
    config["type"] = args.type
    config["capabilities"] = caps
    config["server_url"] = args.server
    _save_config(config)

    print(f"╔══════════════════════════════════════╗")
    print(f"║     FRIDAY SIDECAR v{__import__('friday_sidecar').__version__}          ║")
    print(f"╚══════════════════════════════════════╝")
    print(f"  Name:     {name}")
    print(f"  Server:   {args.server}")
    print(f"  Type:     {args.type}")
    print(f"  Port:     {port}")
    print(f"  Caps:     {', '.join(caps)}")
    print()

    # Run HTTP server in background
    server_thread = threading.Thread(
        target=run_http_server,
        args=("0.0.0.0", port),
        daemon=True,
    )
    server_thread.start()
    time.sleep(0.5)

    # Register with FRIDAY
    register_with_friday(args.server, token, name, args.type, caps, port)

    # Start heartbeat
    print(f"[SIDECAR] Heartbeat every 30s to {args.server}")
    heartbeat_loop(args.server, name)


if __name__ == "__main__":
    main()
