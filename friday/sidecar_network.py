"""
FRIDAY Sidecar Network — multicast discovery, JWT authentication, remote registration.

Allows sidecars on other devices to discover and authenticate with the main FRIDAY instance.
Uses UDP multicast for discovery and HMAC-based JWT (no PyJWT dependency needed).
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import json
import os
import socket
import struct
import threading
import time
import hashlib
import hmac
import base64

from friday._paths import FRIDAY_MEMORY

_SIDECAR_NET_DIR = os.path.join(FRIDAY_MEMORY, "sidecar_network")
_TOKENS_FILE = os.path.join(_SIDECAR_NET_DIR, "tokens.json")
_DISCOVERY_PORT = 42069
_DISCOVERY_MULTICAST_GROUP = "239.255.42.69"
_DISCOVERY_INTERVAL = 5  # seconds between discovery announcements
_DISCOVERY_TTL = 2

# ─── Token Management (HMAC-based JWT) ─────────────────────

_TOKEN_SECRET_FILE = os.path.join(_SIDECAR_NET_DIR, "jwt_secret.txt")


def _ensure_dirs():
    os.makedirs(_SIDECAR_NET_DIR, exist_ok=True)


def _get_secret() -> str:
    """Get or generate the JWT HMAC secret."""
    _ensure_dirs()
    if os.path.exists(_TOKEN_SECRET_FILE):
        with open(_TOKEN_SECRET_FILE, "r") as f:
            return f.read().strip()
    secret = hashlib.sha256(os.urandom(64)).hexdigest()
    with open(_TOKEN_SECRET_FILE, "w") as f:
        f.write(secret)
    return secret


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def generate_token(name: str, no_expiry: bool = False) -> str:
    """Generate a JWT-like token for sidecar authentication.

    Args:
        name: Sidecar name/identifier.
        no_expiry: If True, token never expires.

    Returns:
        JWT-format token string.
    """
    secret = _get_secret()
    header = {"alg": "HS256", "typ": "JWT"}

    payload = {
        "sub": name,
        "iat": int(time.time()),
        "jt": hashlib.sha256(os.urandom(16)).hexdigest()[:16],  # jitter
    }
    if not no_expiry:
        payload["exp"] = int(time.time()) + 365 * 86400  # 1 year default
    else:
        payload["exp"] = 0  # 0 = no expiry

    # Encode
    header_b64 = _b64url_encode(json.dumps(header).encode())
    payload_b64 = _b64url_encode(json.dumps(payload).encode())

    # Sign
    sig_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(secret.encode(), sig_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(signature)

    token = f"{header_b64}.{payload_b64}.{sig_b64}"

    # Save to token registry
    _save_token(name, token, no_expiry)

    return token


def _save_token(name: str, token: str, no_expiry: bool):
    """Save a generated token to the local registry."""
    _ensure_dirs()
    tokens = {}
    if os.path.exists(_TOKENS_FILE):
        try:
            with open(_TOKENS_FILE, "r") as f:
                tokens = json.load(f)
            if not isinstance(tokens, dict):
                tokens = {}
        except Exception:
            tokens = {}
    tokens[name] = {
        "token": token,
        "created": datetime.now().isoformat(),
        "no_expiry": no_expiry,
    }
    with open(_TOKENS_FILE, "w") as f:
        json.dump(tokens, f, indent=2)


def list_tokens() -> Dict[str, dict]:
    """List all generated tokens."""
    if os.path.exists(_TOKENS_FILE):
        try:
            with open(_TOKENS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def revoke_token(name: str) -> bool:
    """Revoke a token by name."""
    tokens = list_tokens()
    if name in tokens:
        del tokens[name]
        with open(_TOKENS_FILE, "w") as f:
            json.dump(tokens, f, indent=2)
        return True
    return False


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify a JWT token and return its payload if valid.

    Returns payload dict if valid, None if invalid/expired.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, sig_b64 = parts

        # Verify signature
        secret = _get_secret()
        sig_input = f"{header_b64}.{payload_b64}".encode()
        expected_sig = hmac.new(secret.encode(), sig_input, hashlib.sha256).digest()
        actual_sig = _b64url_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        # Decode payload
        payload_json = _b64url_decode(payload_b64).decode()
        payload = json.loads(payload_json)

        # Check expiry
        exp = payload.get("exp", 0)
        if exp != 0 and time.time() > exp:
            return None  # Expired

        return payload
    except Exception:
        return None


# ─── UDP Multicast Discovery ───────────────────────────────

_discovery_running = False
_discovery_thread: Optional[threading.Thread] = None
_discovery_stop = threading.Event()

# Callbacks for when sidecars are discovered
_discovery_callbacks: List[Callable] = []


def on_sidecar_discovered(callback: Callable):
    """Register a callback for when a sidecar is discovered.

    Callback signature: fn(name: str, host: str, port: int, capabilities: list)
    """
    _discovery_callbacks.append(callback)


def _build_discovery_message() -> bytes:
    """Build the discovery announcement JSON message."""
    msg = {
        "type": "friday_sidecar_discovery",
        "protocol_version": 1,
        "host": socket.gethostname(),
        "timestamp": time.time(),
    }
    return json.dumps(msg).encode("utf-8")


def _parse_discovery_message(data: bytes, addr: tuple) -> Optional[dict]:
    """Parse a discovery message. Returns parsed dict if valid."""
    try:
        msg = json.loads(data.decode("utf-8"))
        if msg.get("type") == "friday_sidecar_discovery":
            msg["source_addr"] = addr[0]
            msg["source_port"] = addr[1]
            return msg
    except Exception:
        pass
    return None


def _discovery_listener():
    """Background thread: listen for sidecar discovery broadcasts."""
    global _discovery_running
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", _DISCOVERY_PORT))

        # Join multicast group
        mreq = struct.pack("4sl", socket.inet_aton(_DISCOVERY_MULTICAST_GROUP), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        sock.settimeout(1.0)
        _discovery_running = True

        while not _discovery_stop.is_set():
            try:
                data, addr = sock.recvfrom(2048)
                msg = _parse_discovery_message(data, addr)
                if msg:
                    for cb in _discovery_callbacks:
                        try:
                            cb(msg)
                        except Exception:
                            pass
            except socket.timeout:
                continue
            except Exception:
                break

        sock.close()
    except Exception as e:
        _discovery_running = False
        raise
    _discovery_running = False


def _discovery_announcer():
    """Background thread: periodically announce this FRIDAY instance."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, _DISCOVERY_TTL)
        sock.settimeout(1.0)

        msg = _build_discovery_message()

        while not _discovery_stop.is_set():
            try:
                sock.sendto(msg, (_DISCOVERY_MULTICAST_GROUP, _DISCOVERY_PORT))
            except Exception:
                pass
            _discovery_stop.wait(timeout=_DISCOVERY_INTERVAL)

        sock.close()
    except Exception:
        pass


discovered_sidecars: List[dict] = []
_discovered_lock = threading.Lock()


def _default_discovery_callback(msg: dict):
    """Default callback: record discovered sidecars."""
    with _discovered_lock:
        # Keep last 50 unique by host
        host = msg.get("source_addr", "")
        if host:
            for i, s in enumerate(discovered_sidecars):
                if s.get("host") == host:
                    discovered_sidecars[i] = msg
                    return
            discovered_sidecars.append(msg)
            if len(discovered_sidecars) > 50:
                discovered_sidecars.pop(0)


# Register default callback
on_sidecar_discovered(_default_discovery_callback)


def start_discovery() -> str:
    """Start the discovery listener and announcer background threads."""
    global _discovery_thread, _discovery_stop

    if _discovery_running:
        return "[OK] Discovery already running"

    _discovery_stop.clear()

    listener = threading.Thread(target=_discovery_listener, daemon=True)
    listener.start()
    time.sleep(0.2)

    announcer = threading.Thread(target=_discovery_announcer, daemon=True)
    announcer.start()

    _discovery_thread = listener
    return "[OK] Sidecar discovery started (multicast group: {}:{})".format(
        _DISCOVERY_MULTICAST_GROUP, _DISCOVERY_PORT
    )


def stop_discovery() -> str:
    """Stop the discovery threads."""
    global _discovery_running
    _discovery_stop.set()
    _discovery_running = False
    return "[OK] Sidecar discovery stopped"


def get_discovered_sidecars() -> List[dict]:
    """Get list of sidecars discovered on the network."""
    with _discovered_lock:
        return list(discovered_sidecars)


# ─── Registration HTTP Handler (for sidecar to call home) ──

def handle_sidecar_registration(data: dict) -> dict:
    """Handle a sidecar registration request.

    Expected input:
        {
            "token": "jwt-token-string",
            "name": "sidecar-name",
            "type": "desktop",
            "host": "192.168.1.x",
            "port": 8095,
            "capabilities": ["exec", "ping"],
        }

    Returns:
        dict with success/error and sidecar_id.
    """
    token = data.get("token", "")
    payload = verify_token(token)
    if not payload:
        return {"error": "Invalid or expired token"}

    name = data.get("name", payload.get("sub", "unknown"))
    sidecar_type = data.get("type", "desktop")
    host = data.get("host", "0.0.0.0")
    port = data.get("port", 0)
    capabilities = data.get("capabilities", [])

    try:
        from friday.sidecar import register_sidecar
        result = register_sidecar(
            name=name,
            sidecar_type=sidecar_type,
            endpoint=f"http://{host}:{port}",
            host=host,
            port=port,
            capabilities=capabilities,
            metadata={"auth": "jwt", "remote": True, "registered_at": datetime.now().isoformat()},
        )
        if "error" in result:
            return {"error": result["error"]}
        return {"success": True, "sidecar_id": result.get("id"), "name": name}
    except Exception as e:
        return {"error": str(e)}


# ─── Tool function ─────────────────────────────────────────

def sidecar_network_tool(action: str = "status", **kwargs) -> str:
    """FRIDAY tool: sidecar network discovery and token management.

    Actions:
        status               - Show network status
        start_discovery      - Start discovery listener
        stop_discovery       - Stop discovery listener
        discovered           - List discovered sidecars
        generate_token       - Generate auth token (args: name, no_expiry=True)
        list_tokens          - List all generated tokens
        revoke_token         - Revoke a token (args: name)
        verify_token         - Verify a token string (args: token)
    """
    if action == "status":
        tokens = list_tokens()
        discovered = get_discovered_sidecars()
        return (
            f"### SIDECAR NETWORK\n\n"
            f"Discovery: {'RUNNING' if _discovery_running else 'STOPPED'}\n"
            f"Tokens issued: {len(tokens)}\n"
            f"Discovered sidecars: {len(discovered)}\n"
            f"Multicast group: {_DISCOVERY_MULTICAST_GROUP}:{_DISCOVERY_PORT}"
        )

    if action == "start_discovery":
        return start_discovery()

    if action == "stop_discovery":
        return stop_discovery()

    if action == "discovered":
        sidecars = get_discovered_sidecars()
        if not sidecars:
            return "[OK] No sidecars discovered yet."
        lines = ["### DISCOVERED SIDECARS\n"]
        for s in sidecars:
            lines.append(
                f"  • {s.get('source_addr', '?')}:{s.get('source_port', '?')} "
                f"(hostname: {s.get('host', '?')})"
            )
        return "\n".join(lines)

    if action == "generate_token":
        name = kwargs.get("name", "")
        if not name:
            return "[FAIL] Provide 'name' for the token."
        no_expiry = kwargs.get("no_expiry", True)
        if isinstance(no_expiry, str):
            no_expiry = no_expiry.lower() in ("true", "1", "yes")
        token = generate_token(name, no_expiry=no_expiry)
        return f"[OK] Token for '{name}':\n{token}\n\nUse this token on the sidecar device to authenticate."

    if action == "list_tokens":
        tokens = list_tokens()
        if not tokens:
            return "[OK] No tokens generated yet."
        lines = ["### TOKENS\n"]
        for name, info in tokens.items():
            no_exp = " (no expiry)" if info.get("no_expiry") else ""
            lines.append(f"  {name}: created {info.get('created', '?')}{no_exp}")
        return "\n".join(lines)

    if action == "revoke_token":
        name = kwargs.get("name", "")
        if not name:
            return "[FAIL] Provide 'name' of token to revoke."
        if revoke_token(name):
            return f"[OK] Token '{name}' revoked."
        return f"[FAIL] Token '{name}' not found."

    if action == "verify_token":
        token = kwargs.get("token", "")
        if not token:
            return "[FAIL] Provide 'token' to verify."
        payload = verify_token(token)
        if payload:
            return f"[OK] Token valid. Subject: {payload.get('sub', '?')}"
        return "[FAIL] Token invalid or expired."

    return f"[FAIL] Unknown action: {action}. Available: status, start_discovery, stop_discovery, discovered, generate_token, list_tokens, revoke_token, verify_token"
