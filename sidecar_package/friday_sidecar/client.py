"""
FRIDAY Sidecar Client — runs on remote devices to extend FRIDAY's reach.
Connects to FRIDAY via persistent WebSocket with JWT auth.
Exposes: screen capture, clipboard, terminal, filesystem, process/window info.
"""

from __future__ import annotations
import argparse
import base64
import json
import os
import io
import platform
import socket
import struct
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Callable

SIDECAR_CONFIG_DIR = os.path.expanduser("~/.friday_sidecar")
CONFIG_FILE = os.path.join(SIDECAR_CONFIG_DIR, "config.json")

try:
    import websocket
except ImportError:
    websocket = None

try:
    from PIL import Image, ImageGrab
except ImportError:
    Image = None
    ImageGrab = None


# ─── Helpers ───────────────────────────────────────────────


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


def _hostname() -> str:
    return socket.gethostname()


# ─── Tool Handlers ──────────────────────────────────────────


def handle_ping(params: dict = None) -> dict:
    return {"status": "pong", "timestamp": datetime.now().isoformat()}


def handle_capabilities(params: dict = None) -> dict:
    config = _load_config()
    return {
        "capabilities": config.get("capabilities", []),
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
            "stdout": proc.stdout[-5000:],
            "stderr": proc.stderr[-2000:],
            "returncode": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}
    except Exception as e:
        return {"error": str(e)}


def handle_system_info(params: dict = None) -> dict:
    return {
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": sys.version,
    }


def handle_capture_screen(params: dict = None) -> dict:
    if ImageGrab is None:
        return {"error": "PIL not installed"}
    try:
        img = ImageGrab.grab(all_screens=True)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return {"image": b64, "width": img.width, "height": img.height, "format": "png"}
    except Exception as e:
        return {"error": str(e)}


def handle_clipboard_get(params: dict = None) -> dict:
    try:
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.OpenClipboard(None)
            handle = ctypes.windll.user32.GetClipboardData(13)
            ctypes.windll.user32.CloseClipboard()
            if handle:
                ptr = ctypes.windll.kernel32.GlobalLock(handle)
                text = ctypes.c_char_p(ptr).value.decode("utf-8", errors="replace") if ptr else ""
                ctypes.windll.kernel32.GlobalUnlock(handle)
                return {"text": text}
            return {"text": ""}
        else:
            result = subprocess.run(["pbpaste"] if sys.platform == "darwin" else ["xclip", "-o", "-selection", "clipboard"],
                                    capture_output=True, text=True, timeout=5)
            return {"text": result.stdout}
    except Exception as e:
        return {"error": str(e)}


def handle_clipboard_set(params: dict = None) -> dict:
    text = (params or {}).get("text", "")
    try:
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.OpenClipboard(None)
            ctypes.windll.user32.EmptyClipboard()
            data = text.encode("utf-16-le")
            mem = ctypes.windll.kernel32.GlobalAlloc(0x2000, len(data) + 2)
            ptr = ctypes.windll.kernel32.GlobalLock(mem)
            ctypes.windll.kernel32.RtlMoveMemory(ptr, data, len(data))
            ctypes.windll.kernel32.GlobalUnlock(mem)
            ctypes.windll.user32.SetClipboardData(13, mem)
            ctypes.windll.user32.CloseClipboard()
            return {"success": True}
        else:
            proc = subprocess.run(["pbcopy"] if sys.platform == "darwin" else ["xclip", "-selection", "clipboard"],
                                  input=text, text=True, timeout=5)
            return {"success": proc.returncode == 0}
    except Exception as e:
        return {"error": str(e)}


def handle_processes(params: dict = None) -> dict:
    try:
        if sys.platform == "win32":
            import ctypes
            procs = []
            for p in subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=10).stdout.strip().split("\n"):
                parts = p.strip('"').split('","')
                if len(parts) >= 2:
                    procs.append({"name": parts[0], "pid": parts[1]})
            return {"processes": procs[:200]}
        else:
            out = subprocess.run(["ps", "aux", "--no-headers"], capture_output=True, text=True, timeout=10).stdout
            procs = []
            for line in out.strip().split("\n"):
                parts = line.split(None, 10)
                if len(parts) >= 11:
                    procs.append({"name": parts[10], "pid": parts[1], "cpu": parts[2], "mem": parts[3]})
            return {"processes": procs[:200]}
    except Exception as e:
        return {"error": str(e)}


def handle_active_window(params: dict = None) -> dict:
    try:
        if sys.platform == "win32":
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            try:
                proc_name = subprocess.run(["tasklist", "/FI", f"PID eq {pid.value}", "/NH"],
                                           capture_output=True, text=True, timeout=5).stdout.strip()
            except Exception:
                proc_name = f"pid:{pid.value}"
            return {"title": buf.value, "pid": pid.value, "process": proc_name}
        elif sys.platform == "darwin":
            out = subprocess.run(["osascript", "-e", 'tell app "System Events" to get name of first process whose frontmost is true'],
                                 capture_output=True, text=True, timeout=5)
            return {"title": out.stdout.strip()}
        else:
            out = subprocess.run(["xdotool", "getactivewindow", "getwindowname"], capture_output=True, text=True, timeout=5)
            return {"title": out.stdout.strip()}
    except Exception as e:
        return {"error": str(e)}


def handle_file_read(params: dict = None) -> dict:
    path = (params or {}).get("path", "")
    if not path:
        return {"error": "No path provided"}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return {"content": content, "size": len(content)}
    except Exception as e:
        return {"error": str(e)}


def handle_file_write(params: dict = None) -> dict:
    path = (params or {}).get("path", "")
    content = (params or {}).get("content", "")
    if not path:
        return {"error": "No path provided"}
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def handle_file_list(params: dict = None) -> dict:
    path = (params or {}).get("path", ".")
    try:
        entries = []
        for name in os.listdir(path):
            full = os.path.join(path, name)
            try:
                st = os.stat(full)
                entries.append({"name": name, "size": st.st_size, "is_dir": os.path.isdir(full), "mod_time": datetime.fromtimestamp(st.st_mtime).isoformat()})
            except Exception:
                entries.append({"name": name, "size": 0, "is_dir": False, "mod_time": ""})
        return {"entries": entries, "path": os.path.abspath(path)}
    except Exception as e:
        return {"error": str(e)}


def handle_file_delete(params: dict = None) -> dict:
    path = (params or {}).get("path", "")
    if not path:
        return {"error": "No path provided"}
    try:
        if os.path.isdir(path):
            import shutil
            shutil.rmtree(path)
        else:
            os.remove(path)
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def handle_shutdown(params: dict = None) -> dict:
    t = threading.Thread(target=lambda: (time.sleep(0.5), os._exit(0)), daemon=True)
    t.start()
    return {"status": "shutting_down"}


DISCOVER_SEQUENCE: list[tuple[str, Callable, str]] = [
    ("capture_screen", handle_capture_screen, "screen capture"),
    ("clipboard", handle_clipboard_get, "clipboard access"),
    ("exec", handle_exec, "terminal execution"),
    ("filesystem", handle_file_list, "file system"),
    ("system_info", handle_system_info, "system info"),
    ("processes", handle_processes, "process listing"),
    ("active_window", handle_active_window, "active window"),
]


def discover_capabilities() -> list[str]:
    caps = ["ping", "capabilities"]
    for name, handler, _ in DISCOVER_SEQUENCE:
        try:
            result = handler({})
            if "error" not in result:
                caps.append(name)
        except Exception:
            pass
    return caps


COMMAND_HANDLERS = {
    "ping": handle_ping,
    "capabilities": handle_capabilities,
    "exec": handle_exec,
    "system_info": handle_system_info,
    "capture_screen": handle_capture_screen,
    "clipboard_get": handle_clipboard_get,
    "clipboard_set": handle_clipboard_set,
    "processes": handle_processes,
    "active_window": handle_active_window,
    "file_read": handle_file_read,
    "file_write": handle_file_write,
    "file_list": handle_file_list,
    "file_delete": handle_file_delete,
    "shutdown": handle_shutdown,
}


def dispatch_command(command: str, params: dict = None) -> dict:
    handler = COMMAND_HANDLERS.get(command)
    if not handler:
        return {"error": f"Unknown command: {command}"}
    try:
        return handler(params or {})
    except Exception as e:
        return {"error": str(e)}


# ─── WebSocket Client ──────────────────────────────────────


class SidecarWSClient:
    """Persistent WebSocket connection to FRIDAY."""

    def __init__(self, server_url: str, token: str, name: str, caps: list[str],
                 on_binary: Optional[Callable] = None):
        ws_url = server_url.replace("http://", "ws://").replace("https://", "wss://")
        self.ws_url = f"{ws_url.rstrip('/')}/ws/sidecar"
        self.token = token
        self.name = name
        self.caps = caps
        self.on_binary = on_binary
        self.ws: Optional[websocket.WebSocketApp] = None
        self.running = True
        self._reconnect_delay = 1
        self._last_capture = 0

    def _on_open(self, ws):
        print(f"[SIDECAR] WebSocket connected to {self.ws_url}")
        self._reconnect_delay = 1
        # Send auth handshake
        ws.send(json.dumps({
            "type": "auth",
            "token": self.token,
            "name": self.name,
            "capabilities": self.caps,
        }))
        # Start heartbeat
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            cmd_id = data.get("id", str(uuid.uuid4()))
            command = data.get("command", "")
            params = data.get("params", {})

            # Rate-limit screen capture to 1 per 2s
            if command == "capture_screen":
                now = time.time()
                if now - self._last_capture < 2:
                    ws.send(json.dumps({"id": cmd_id, "success": True, "result": {"rate_limited": True}}))
                    return
                self._last_capture = now

            result = dispatch_command(command, params)
            success = "error" not in result
            ws.send(json.dumps({
                "id": cmd_id,
                "success": success,
                "result": result if success else {},
                "error": result.get("error", ""),
            }))
        except Exception as e:
            try:
                ws.send(json.dumps({"id": "error", "success": False, "error": str(e)}))
            except Exception:
                pass

    def _on_error(self, ws, error):
        print(f"[SIDECAR] WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        print(f"[SIDECAR] WebSocket closed ({close_status_code})")
        if self.running:
            self._reconnect()

    def _heartbeat_loop(self):
        while self.running:
            time.sleep(15)
            try:
                if self.ws and self.ws.sock and self.ws.sock.connected:
                    self.ws.send(json.dumps({"type": "ping"}))
            except Exception:
                pass

    def _reconnect(self):
        delay = min(self._reconnect_delay, 60)
        print(f"[SIDECAR] Reconnecting in {delay}s...")
        time.sleep(delay)
        self._reconnect_delay = min(self._reconnect_delay * 2, 60)
        if self.running:
            self.connect()

    def connect(self):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "X-Sidecar-Name": self.name,
        }
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            header=headers,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self.ws.run_forever(ping_interval=30, ping_timeout=10)

    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()


# ─── HTTP Fallback Server ──────────────────────────────────


class SidecarHTTPHandler(BaseHTTPRequestHandler):
    """Fallback HTTP server when WebSocket is unavailable."""

    def _respond(self, data: dict, status: int = 200):
        try:
            body = json.dumps(data, default=str)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
        except Exception:
            pass

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
        config = _load_config()
        token = config.get("auth_token", "")
        auth = self.headers.get("Authorization", "")
        if token:
            if not auth.startswith("Bearer ") or auth[7:] != token:
                self._respond({"error": "Unauthorized"}, 401)
                return
        result = dispatch_command(command, params)
        success = "error" not in result
        self._respond(result if success else {"error": result["error"]},
                      200 if success else 400)

    def do_GET(self):
        if self.path == "/health":
            self._respond({"status": "alive", "name": _load_config().get("name", "unknown"), "time": datetime.now().isoformat()})
        else:
            self._respond({"error": "Not found"}, 404)

    def log_message(self, fmt, *args):
        pass


def run_http_server(host: str, port: int):
    server = HTTPServer((host, port), SidecarHTTPHandler)
    print(f"[SIDECAR] HTTP fallback on {host}:{port}")
    try:
        server.serve_forever()
    except Exception:
        pass


# ─── Registration ──────────────────────────────────────────


def register_with_friday(server_url: str, token: str, name: str,
                         sidecar_type: str, capabilities: list, port: int):
    hostname = socket.gethostname()
    try:
        ip = socket.gethostbyname(hostname)
    except Exception:
        ip = "0.0.0.0"
    payload = {
        "token": token, "name": name, "type": sidecar_type,
        "host": ip, "port": port, "capabilities": capabilities,
    }
    url = f"{server_url.rstrip('/')}/api/sidecars/register"
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        if result.get("success"):
            print(f"[SIDECAR] Registered as #{result.get('sidecar_id')}")
        else:
            print(f"[SIDECAR] Registration failed: {result.get('error', 'unknown')}")
    except Exception as e:
        print(f"[SIDECAR] Registration error: {e}")


def heartbeat_loop(server_url: str, name: str, interval: int = 30):
    while True:
        time.sleep(interval)
        try:
            url = f"{server_url.rstrip('/')}/api/sidecars/heartbeat"
            req = urllib.request.Request(url, data=json.dumps({"name": name, "status": "alive"}).encode("utf-8"),
                                         headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=5):
                pass
        except Exception:
            pass


# ─── CLI ────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="FRIDAY Sidecar — remote device extension")
    parser.add_argument("--server", help="FRIDAY server URL (e.g. http://192.168.1.100:8090)")
    parser.add_argument("--token", help="Auth token from FRIDAY")
    parser.add_argument("--name", default=_hostname(), help="Sidecar name (default: hostname)")
    parser.add_argument("--type", default="desktop", choices=["desktop", "browser", "filesystem", "system_monitor", "code_workspace", "smart_home"])
    parser.add_argument("--port", type=int, default=8095, help="HTTP fallback port")
    parser.add_argument("--install-token", help="Save a token to config and exit")
    parser.add_argument("--discover", action="store_true", help="Auto-discover capabilities")
    parser.add_argument("--no-websocket", action="store_true", help="Force HTTP only")

    args = parser.parse_args()

    if args.install_token:
        config = _load_config()
        config["auth_token"] = args.install_token
        _save_config(config)
        print(f"[SIDECAR] Token saved to {CONFIG_FILE}")
        return

    config = _load_config()
    token = args.token or config.get("auth_token", "")

    if not args.server:
        print("[SIDECAR] --server required. Get a token first: friday-sidecar --install-token TOKEN")
        sys.exit(1)

    if not token:
        print("[SIDECAR] No auth token. Use --token or --install-token first")
        sys.exit(1)

    name = args.name
    port = args.port

    # Discover capabilities
    if args.discover:
        caps = discover_capabilities()
        print(f"[SIDECAR] Discovered: {', '.join(caps)}")
    else:
        caps = config.get("capabilities", ["ping", "exec", "system_info", "capture_screen", "clipboard", "processes", "active_window", "file_read", "file_write", "file_list", "file_delete"])

    # Save config
    config["name"] = name
    config["type"] = args.type
    config["capabilities"] = caps
    config["server_url"] = args.server
    _save_config(config)

    print(f"╔══════════════════════════════════════╗")
    print(f"║     FRIDAY SIDECAR v2.0               ║")
    print(f"╚══════════════════════════════════════╝")
    print(f"  Name:     {name}")
    print(f"  Server:   {args.server}")
    print(f"  Type:     {args.type}")
    print(f"  Caps:     {', '.join(caps)}")

    # Start HTTP fallback server
    http_thread = threading.Thread(target=run_http_server, args=("0.0.0.0", port), daemon=True)
    http_thread.start()
    time.sleep(0.5)

    # Register with FRIDAY
    register_with_friday(args.server, token, name, args.type, caps, port)

    # Connect via WebSocket
    if websocket and not args.no_websocket:
        print(f"[SIDECAR] Connecting WebSocket to {args.server}...")
        client = SidecarWSClient(args.server, token, name, caps)
        ws_thread = threading.Thread(target=client.connect, daemon=True)
        ws_thread.start()
    else:
        print(f"[SIDECAR] HTTP mode (no WebSocket)")

    # Start heartbeat
    print(f"[SIDECAR] Heartbeat every 30s")
    heartbeat_loop(args.server, name)


if __name__ == "__main__":
    main()
