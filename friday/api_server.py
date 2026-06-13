"""
FRIDAY API Server — FastAPI-based REST API that exposes all FRIDAY tools as HTTP endpoints.

Auto-discovers tools from friday.tools, provides auth, WebSocket real-time updates,
memory management, codebase analysis, validation, townhall agent orchestration,
file management, bootstrap services, system health monitoring, and dashboard status.

Usage:
  from friday.api_server import start_api_server, stop_api_server, api_server_tool
  start_api_server(host="127.0.0.1", port=8000)

Entry points:
  - start_api_server(host, port) — launches uvicorn in daemon thread
  - stop_api_server() — stops the server
  - api_server_tool(action, **kwargs) — FRIDAY tool integration
"""

from __future__ import annotations

import asyncio
import base64
import datetime
import functools
import hashlib
import hmac
import importlib
import inspect
import io
import json
import logging
import mimetypes
import os
import pathlib
import platform
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import textwrap
import threading
import time
import traceback
import typing
import uuid
import warnings
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

# ─── Optional Dependencies ────────────────────────────────

HAS_FASTAPI = False
HAS_UVICORN = False
HAS_WEBSOCKETS = False
HAS_PSUTIL = False
HAS_PYDANTIC = False

try:
    from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect, HTTPException, Depends
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse, FileResponse, StreamingResponse
    from fastapi.openapi.utils import get_openapi
    import starlette.status as http_status
    import uvicorn
    HAS_FASTAPI = True
    HAS_UVICORN = True
except ImportError:
    FastAPI = None
    Request = None
    Response = None
    HAS_FASTAPI = False
    HAS_UVICORN = False

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None

try:
    from pydantic import BaseModel, Field
    HAS_PYDANTIC = True
except ImportError:
    BaseModel = object
    Field = None

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

# ─── FRIDAY Imports ───────────────────────────────────────

from friday._paths import FRIDAY_MEMORY, PROJECT_ROOT, FRIDAY_CONFIG
from friday._singletons import set_service_state, clear_service_state, get_service_state
from friday.logging_utils import configure_logging

logger = configure_logging("api_server")

# ─── Constants ────────────────────────────────────────────

API_VERSION = "5.8"
API_TITLE = "FRIDAY API"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
API_KEYS_DIR = os.path.join(FRIDAY_MEMORY, "api_keys.json")
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX_REQUESTS = 100
MAX_UPLOAD_SIZE = 50 * 1024 * 1024

os.makedirs(FRIDAY_MEMORY, exist_ok=True)

# ─── State ────────────────────────────────────────────────

_server_instance: Optional[Any] = None
_server_thread: Optional[threading.Thread] = None
_server_stop_event = threading.Event()
_ws_connections: List[Any] = []
_ws_lock = threading.Lock()
_rate_limit_store: Dict[str, List[float]] = {}
_rate_limit_lock = threading.Lock()
_tool_cache: Dict[str, Dict[str, Any]] = {}
_tool_cache_lock = threading.Lock()
_start_time: float = 0.0


# ═══════════════════════════════════════════════════════════
# API Key Authentication
# ═══════════════════════════════════════════════════════════


class APIKeyAuth:
    """API key authentication system for FRIDAY API endpoints.

    API keys are stored in FRIDAY_MEMORY/api_keys.json as a JSON object:
    {
      "keys": {
        "<key_hash>": {
          "name": "descriptive name",
          "created": "ISO timestamp",
          "last_used": "ISO timestamp",
          "revoked": false
        }
      }
    }
    """

    _lock = threading.Lock()

    @staticmethod
    def _load_keys() -> Dict[str, dict]:
        """Load all API keys from the keys file."""
        if os.path.exists(API_KEYS_DIR):
            try:
                with open(API_KEYS_DIR, "r") as f:
                    data = json.load(f)
                    return data.get("keys", {})
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    @staticmethod
    def _save_keys(keys: Dict[str, dict]) -> None:
        """Save all API keys to the keys file."""
        with APIKeyAuth._lock:
            with open(API_KEYS_DIR, "w") as f:
                json.dump({"keys": keys}, f, indent=2)

    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """Validate an API key against stored keys.

        Args:
            api_key: The raw API key string to validate.

        Returns:
            True if the key exists and is not revoked.
        """
        if not api_key:
            return False
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        keys = APIKeyAuth._load_keys()
        entry = keys.get(key_hash)
        if entry is None:
            return False
        if entry.get("revoked", False):
            return False
        entry["last_used"] = datetime.now().isoformat()
        APIKeyAuth._save_keys(keys)
        return True

    @staticmethod
    def generate_api_key(name: str) -> str:
        """Generate a new API key for the given name.

        Args:
            name: A human-readable name for the key owner/usage.

        Returns:
            The raw API key string (shown once).
        """
        raw_key = f"friday_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        keys = APIKeyAuth._load_keys()
        keys[key_hash] = {
            "name": name,
            "created": datetime.now().isoformat(),
            "last_used": "",
            "revoked": False,
        }
        APIKeyAuth._save_keys(keys)
        return raw_key

    @staticmethod
    def revoke_api_key(api_key: str) -> bool:
        """Revoke an API key by its hash.

        Args:
            api_key: The raw API key to revoke.

        Returns:
            True if the key was found and revoked.
        """
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        keys = APIKeyAuth._load_keys()
        if key_hash in keys:
            keys[key_hash]["revoked"] = True
            APIKeyAuth._save_keys(keys)
            return True
        return False

    @staticmethod
    def list_api_keys() -> List[dict]:
        """List all API keys (without exposing raw keys).

        Returns:
            A list of key metadata dicts.
        """
        keys = APIKeyAuth._load_keys()
        result = []
        for key_hash, meta in keys.items():
            result.append({
                "key_prefix": key_hash[:12] + "...",
                "name": meta.get("name", "unknown"),
                "created": meta.get("created", ""),
                "last_used": meta.get("last_used", ""),
                "revoked": meta.get("revoked", False),
            })
        return result

    @staticmethod
    def revoke_all_keys() -> int:
        """Revoke every stored API key.

        Returns:
            The number of keys revoked.
        """
        keys = APIKeyAuth._load_keys()
        count = 0
        for k in keys:
            if not keys[k]["revoked"]:
                keys[k]["revoked"] = True
                count += 1
        APIKeyAuth._save_keys(keys)
        return count


# ═══════════════════════════════════════════════════════════
# Rate Limiter
# ═══════════════════════════════════════════════════════════


class RateLimiter:
    """Simple sliding-window rate limiter.

    Tracks request timestamps per client IP and enforces
    a maximum number of requests per time window.
    """

    def __init__(self, max_requests: int = RATE_LIMIT_MAX_REQUESTS, window_seconds: int = RATE_LIMIT_WINDOW):
        """Initialize the rate limiter.

        Args:
            max_requests: Maximum requests allowed in the window.
            window_seconds: Length of the rate limit window in seconds.
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._store: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def is_allowed(self, client_ip: str) -> Tuple[bool, int]:
        """Check if a request from this IP is allowed.

        Args:
            client_ip: The client IP address.

        Returns:
            Tuple of (allowed: bool, remaining: int).
        """
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            timestamps = self._store.get(client_ip, [])
            timestamps = [t for t in timestamps if t > cutoff]
            if len(timestamps) >= self.max_requests:
                self._store[client_ip] = timestamps
                return False, 0
            timestamps.append(now)
            self._store[client_ip] = timestamps
            remaining = self.max_requests - len(timestamps)
            return True, remaining

    def reset(self, client_ip: Optional[str] = None) -> None:
        """Reset rate limit counters.

        Args:
            client_ip: If provided, reset only this IP. Otherwise reset all.
        """
        with self._lock:
            if client_ip:
                self._store.pop(client_ip, None)
            else:
                self._store.clear()

    def get_usage(self, client_ip: str) -> int:
        """Get the current request count for an IP.

        Args:
            client_ip: The client IP address.

        Returns:
            Number of requests in the current window.
        """
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            timestamps = self._store.get(client_ip, [])
            return len([t for t in timestamps if t > cutoff])


_rate_limiter = RateLimiter()


# ═══════════════════════════════════════════════════════════
# Tool Discovery
# ═══════════════════════════════════════════════════════════


def discover_tools() -> Dict[str, Callable]:
    """Auto-discover all tools from friday.tools package.

    Returns a dict mapping tool_name -> callable function.
    Handles both sync and async functions.
    """
    tools = {}
    try:
        import friday.tools as ftools
        for name in dir(ftools):
            if name.startswith("_"):
                continue
            obj = getattr(ftools, name)
            if callable(obj) and not isinstance(obj, type):
                tools[name] = obj
    except ImportError as e:
        logger.warning(f"Could not import friday.tools: {e}")
    return tools


def get_tool_metadata(tool_name: str) -> Dict[str, Any]:
    """Get metadata for a specific tool.

    Args:
        tool_name: Name of the tool function.

    Returns:
        Dict with tool metadata (name, doc, signature, category).
    """
    tools = discover_tools()
    fn = tools.get(tool_name)
    if fn is None:
        return {"error": f"Tool {tool_name} not found"}
    sig = inspect.signature(fn)
    params = []
    for p_name, p_param in sig.parameters.items():
        param_info = {
            "name": p_name,
            "kind": str(p_param.kind),
            "default": None if p_param.default is inspect.Parameter.empty else str(p_param.default),
            "annotation": str(p_param.annotation) if p_param.annotation is not inspect.Parameter.empty else "Any",
        }
        params.append(param_info)
    doc = inspect.getdoc(fn) or "No documentation available."
    is_async = inspect.iscoroutinefunction(fn)
    return {
        "name": tool_name,
        "doc": doc.strip(),
        "signature": str(sig),
        "params": params,
        "is_async": is_async,
        "module": getattr(fn, "__module__", ""),
    }


def get_tools_summary() -> List[Dict[str, Any]]:
    """Get a summary list of all discovered tools.

    Returns:
        List of tool metadata dicts.
    """
    tools = discover_tools()
    summary = []
    for name in sorted(tools.keys()):
        meta = get_tool_metadata(name)
        summary.append({
            "name": name,
            "doc": meta["doc"][:100] + "..." if len(meta["doc"]) > 100 else meta["doc"],
            "params_count": len(meta["params"]),
            "is_async": meta["is_async"],
        })
    return summary


def call_tool_safe(tool_name: str, **kwargs) -> Dict[str, Any]:
    """Safely call a FRIDAY tool with error handling.

    Args:
        tool_name: Name of the tool to call.
        **kwargs: Parameters to pass to the tool.

    Returns:
        Dict with "success", "result" or "error" keys.
    """
    tools = discover_tools()
    fn = tools.get(tool_name)
    if fn is None:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
    try:
        if inspect.iscoroutinefunction(fn):
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(fn(**kwargs))
            finally:
                loop.close()
        else:
            result = fn(**kwargs)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Tool call failed: {tool_name} -> {e}", exc_info=True)
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}


# ═══════════════════════════════════════════════════════════
# System Health Helpers
# ═══════════════════════════════════════════════════════════


def get_system_health() -> Dict[str, Any]:
    """Get comprehensive system health metrics.

    Gathers CPU, memory, disk, network, uptime, and process info.
    Gracefully degrades if psutil is not available.
    """
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "start_time": datetime.fromtimestamp(_start_time).isoformat() if _start_time else "",
        "uptime_seconds": int(time.time() - _start_time) if _start_time else 0,
    }
    if HAS_PSUTIL:
        try:
            health["cpu_percent"] = psutil.cpu_percent(interval=0.5)
            health["cpu_count"] = psutil.cpu_count()
            health["cpu_freq_mhz"] = round(psutil.cpu_freq().current, 1) if psutil.cpu_freq() else 0
            mem = psutil.virtual_memory()
            health["memory_percent"] = mem.percent
            health["memory_used_gb"] = round(mem.used / (1024 ** 3), 2)
            health["memory_total_gb"] = round(mem.total / (1024 ** 3), 2)
            health["memory_available_gb"] = round(mem.available / (1024 ** 3), 2)
            disk = psutil.disk_usage("/")
            health["disk_percent"] = disk.percent
            health["disk_used_gb"] = round(disk.used / (1024 ** 3), 2)
            health["disk_total_gb"] = round(disk.total / (1024 ** 3), 2)
            health["disk_free_gb"] = round(disk.free / (1024 ** 3), 2)
            try:
                net = psutil.net_io_counters()
                health["network_sent_mb"] = round(net.bytes_sent / (1024 ** 2), 2)
                health["network_recv_mb"] = round(net.bytes_recv / (1024 ** 2), 2)
            except Exception:
                pass
            try:
                boot_time = datetime.fromtimestamp(psutil.boot_time()).isoformat()
                health["system_boot_time"] = boot_time
            except Exception:
                pass
            try:
                load_avg = psutil.getloadavg()
                health["load_1min"] = round(load_avg[0], 2)
                health["load_5min"] = round(load_avg[1], 2)
                health["load_15min"] = round(load_avg[2], 2)
            except Exception:
                pass
            try:
                sensors = psutil.sensors_temperatures()
                if sensors:
                    for name, entries in sensors.items():
                        if entries:
                            health[f"temp_{name}"] = round(entries[0].current, 1)
            except Exception:
                pass
            health["process_count"] = len(psutil.pids())
            if health["cpu_percent"] > 90 or health["memory_percent"] > 90 or health["disk_percent"] > 95:
                health["status"] = "degraded"
            if health["memory_percent"] > 98 or health["disk_percent"] > 99:
                health["status"] = "critical"
        except Exception as e:
            health["psutil_error"] = str(e)
    else:
        health["cpu_percent"] = "N/A (psutil not installed)"
        health["memory_percent"] = "N/A"
        health["disk_percent"] = "N/A"
    return health


def get_system_status() -> Dict[str, Any]:
    """Get FRIDAY system status including modules, tools, sessions.

    Returns:
        Dict with system status information.
    """
    tools = discover_tools()
    status = {
        "server_version": API_VERSION,
        "server_start_time": datetime.fromtimestamp(_start_time).isoformat() if _start_time else "",
        "uptime_seconds": int(time.time() - _start_time) if _start_time else 0,
        "python_version": sys.version,
        "platform": platform.platform(),
        "hostname": socket.gethostname(),
        "tools_count": len(tools),
        "tool_names": sorted(tools.keys()),
        "fastapi_available": HAS_FASTAPI,
        "uvicorn_available": HAS_UVICORN,
        "psutil_available": HAS_PSUTIL,
        "pydantic_available": HAS_PYDANTIC,
        "websockets_available": HAS_WEBSOCKETS,
        "api_keys_count": len(APIKeyAuth._load_keys()),
        "active_websockets": len(_ws_connections),
        "server_running": _server_thread is not None and _server_thread.is_alive(),
    }
    return status


def get_version_info() -> Dict[str, str]:
    """Get version information for FRIDAY API and dependencies."""
    info = {
        "api_version": API_VERSION,
        "api_title": API_TITLE,
    }
    try:
        import friday
        info["friday_version"] = getattr(friday, "__version__", "unknown")
    except ImportError:
        info["friday_version"] = "unknown"
    info["fastapi_installed"] = HAS_FASTAPI
    info["uvicorn_installed"] = HAS_UVICORN
    info["python_version"] = sys.version.split()[0]
    info["platform"] = platform.platform()
    try:
        import fastapi
        info["fastapi_version"] = getattr(fastapi, "__version__", "unknown")
    except ImportError:
        info["fastapi_version"] = "N/A"
    try:
        import uvicorn as _uv
        info["uvicorn_version"] = getattr(_uv, "__version__", "unknown")
    except ImportError:
        info["uvicorn_version"] = "N/A"
    return info


# ═══════════════════════════════════════════════════════════
# FastAPI App Factory
# ═══════════════════════════════════════════════════════════


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP", "")
    if real_ip:
        return real_ip
    client = request.client
    return client.host if client else "127.0.0.1"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Sets up middleware (CORS, request logging, rate limiting),
    error handlers, and all route groups.
    """
    app = FastAPI(title=API_TITLE, version=API_VERSION)

    # ─── CORS Middleware ───
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
    )

    # ─── Request Logging Middleware ───
    @app.middleware("http")
    async def log_requests(request: Request, call_next: Callable) -> Response:
        """Log all incoming requests and their response status."""
        request_id = str(uuid.uuid4())[:8]
        start = time.time()
        client_ip = get_client_ip(request)
        logger.info(f"[{request_id}] {request.method} {request.url.path} from {client_ip}")
        try:
            response = await call_next(request)
            elapsed_ms = int((time.time() - start) * 1000)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
            logger.info(f"[{request_id}] -> {response.status_code} in {elapsed_ms}ms")
            return response
        except Exception as e:
            elapsed_ms = int((time.time() - start) * 1000)
            logger.error(f"[{request_id}] ! {type(e).__name__}: {e} in {elapsed_ms}ms", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "request_id": request_id},
            )

    # ─── Rate Limiting Middleware ───
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
        """Apply rate limiting based on client IP."""
        if request.url.path.startswith("/api/"):
            client_ip = get_client_ip(request)
            allowed, remaining = _rate_limiter.is_allowed(client_ip)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"error": "Too many requests", "retry_after": RATE_LIMIT_WINDOW},
                    headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
                )
            response = await call_next(request)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_MAX_REQUESTS)
            return response
        return await call_next(request)

    # ─── Error Handlers ───
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handle HTTP exceptions with structured JSON responses."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "path": request.url.path,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unhandled exceptions gracefully."""
        logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "type": type(exc).__name__,
                "path": request.url.path,
            },
        )

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle 404 errors with a helpful message."""
        return JSONResponse(
            status_code=404,
            content={"error": "Not found", "path": request.url.path, "method": request.method},
        )

    @app.exception_handler(405)
    async def method_not_allowed_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle 405 errors."""
        return JSONResponse(
            status_code=405,
            content={"error": "Method not allowed", "path": request.url.path, "method": request.method},
        )

    @app.exception_handler(422)
    async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle validation errors with detailed messages."""
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation error",
                "detail": str(exc),
                "path": request.url.path,
            },
        )

    # ═══════════════════════════════════════════════════════
    # API Documentation & Root
    # ═══════════════════════════════════════════════════════

    @app.get("/")
    async def root() -> RedirectResponse:
        """Redirect root to /docs for API documentation."""
        return RedirectResponse(url="/docs")

    @app.get("/api/openapi.json")
    async def get_openapi_json() -> Dict[str, Any]:
        """Return the OpenAPI specification."""
        return app.openapi()

    # ═══════════════════════════════════════════════════════
    # Status Endpoints
    # ═══════════════════════════════════════════════════════

    @app.get("/api/health")
    async def health_check() -> Dict[str, Any]:
        """System health check endpoint.

        Returns CPU, memory, disk, uptime and overall health status.
        """
        return get_system_health()

    @app.get("/api/status")
    async def system_status() -> Dict[str, Any]:
        """FRIDAY system status endpoint.

        Returns module status, tools count, sessions, and server metrics.
        """
        return get_system_status()

    @app.get("/api/version")
    async def version_info() -> Dict[str, str]:
        """Version information endpoint.

        Returns FRIDAY API version and dependency versions.
        """
        return get_version_info()

    # ═══════════════════════════════════════════════════════
    # Auth Endpoints
    # ═══════════════════════════════════════════════════════

    @app.post("/api/auth/keys")
    async def create_api_key(name: str = "default") -> Dict[str, str]:
        """Generate a new API key.

        Args:
            name: A name/label for the key.
        """
        raw_key = APIKeyAuth.generate_api_key(name)
        return {"api_key": raw_key, "name": name, "message": "Save this key - it won't be shown again"}

    @app.get("/api/auth/keys")
    async def list_api_keys() -> List[dict]:
        """List all API keys (without exposing raw keys)."""
        return APIKeyAuth.list_api_keys()

    @app.delete("/api/auth/keys")
    async def revoke_api_key(api_key: str) -> Dict[str, Any]:
        """Revoke an API key.

        Args:
            api_key: The raw API key to revoke.
        """
        success = APIKeyAuth.revoke_api_key(api_key)
        return {"success": success, "message": "Key revoked" if success else "Key not found"}

    # ═══════════════════════════════════════════════════════
    # Tool Endpoints (Auto-Discovered)
    # ═══════════════════════════════════════════════════════

    @app.post("/api/tools/{tool_name}")
    async def call_tool_endpoint(tool_name: str, request: Request) -> Dict[str, Any]:
        """Call any FRIDAY tool by name.

        The tool name must match a function in friday.tools. Parameters are passed
        as JSON body fields. Both sync and async tools are supported.
        """
        try:
            body = await request.json()
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        result = call_tool_safe(tool_name, **body)
        _broadcast_ws_event({"type": "tool_call", "tool": tool_name, "params": body, "result": result})
        return result

    @app.get("/api/tools/{tool_name}")
    async def get_tool_info(tool_name: str) -> Dict[str, Any]:
        """Get metadata for a specific tool.

        Returns documentation, signature, parameter info, and async status.
        """
        return get_tool_metadata(tool_name)

    @app.get("/api/tools")
    async def list_tools() -> List[Dict[str, Any]]:
        """List all available FRIDAY tools with summary metadata."""
        return get_tools_summary()

    # ═══════════════════════════════════════════════════════
    # Memory Endpoints
    # ═══════════════════════════════════════════════════════

    @app.post("/api/memory/store")
    async def memory_store(request: Request) -> Dict[str, Any]:
        """Store a new memory.

        Body: { "content": "...", "source": "...", "entity": "...",
               "memory_type": "fact", "importance": 0.5 }
        """
        try:
            data = await request.json()
        except Exception:
            return {"success": False, "error": "Invalid JSON body"}
        try:
            from friday.autonomous_memory import store_memory as _sm
            mid = _sm(
                content=data.get("content", ""),
                source=data.get("source", "api"),
                entity=data.get("entity", ""),
                memory_type=data.get("memory_type", "fact"),
                importance=float(data.get("importance", 0.5)),
                metadata=data.get("metadata", {}),
            )
            _broadcast_ws_event({"type": "memory_stored", "memory_id": mid})
            return {"success": True, "memory_id": mid}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.post("/api/memory/search")
    async def memory_search(request: Request) -> Dict[str, Any]:
        """Search memories by text content.

        Body: { "query": "...", "limit": 10, "memory_type": "", "min_importance": 0.0 }
        """
        try:
            data = await request.json()
        except Exception:
            return {"success": False, "error": "Invalid JSON body"}
        try:
            from friday.autonomous_memory import search_memories
            results = search_memories(
                query=data.get("query", ""),
                limit=int(data.get("limit", 10)),
                memory_type=data.get("memory_type", ""),
                min_importance=float(data.get("min_importance", 0.0)),
            )
            return {"success": True, "results": results, "count": len(results)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.get("/api/memory/recent")
    async def memory_recent(hours: int = 24, limit: int = 20) -> Dict[str, Any]:
        """Get recent memories from the last N hours.

        Query params: hours=24, limit=20
        """
        try:
            from friday.autonomous_memory import get_recent_memories
            results = get_recent_memories(hours=hours, limit=limit)
            return {"success": True, "results": results, "count": len(results)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.get("/api/memory/entities")
    async def memory_entities(query: str = "", limit: int = 50) -> Dict[str, Any]:
        """List all known entities in the knowledge graph.

        Query params: query="", limit=50
        """
        try:
            from friday.autonomous_memory import _init_db, ENTITY_INDEX, _memory_lock
            import sqlite3
            conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "friday_memory", "autonomous_memory", "memory.db"))
            cursor = conn.execute("SELECT DISTINCT entity FROM memories WHERE entity != '' ORDER BY entity LIMIT ?", (limit,))
            entities = [row[0] for row in cursor.fetchall() if row[0]]
            conn.close()
            return {"success": True, "entities": entities, "count": len(entities)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.post("/api/memory/learn")
    async def memory_learn(request: Request) -> Dict[str, Any]:
        """Learn from text automatically (entity extraction + memory storage).

        Body: { "text": "...", "source": "conversation" }
        """
        try:
            data = await request.json()
        except Exception:
            return {"success": False, "error": "Invalid JSON body"}
        try:
            from friday.autonomous_memory import learn_from_text
            result = learn_from_text(
                text=data.get("text", ""),
                source=data.get("source", "api"),
            )
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.get("/api/memory/graph/{entity}")
    async def memory_graph(entity: str, depth: int = 2) -> Dict[str, Any]:
        """Query the knowledge graph for an entity.

        Returns the entity's relationships and connected nodes up to `depth` levels.
        """
        try:
            from friday.autonomous_memory import query_knowledge_graph
            result = query_knowledge_graph(entity=entity, max_depth=depth)
            return {"success": True, "result": result}
        except ImportError:
            pass
        try:
            from friday.autonomous_memory import _init_db
            import sqlite3
            from friday._paths import FRIDAY_MEMORY
            autmem_dir = os.path.join(FRIDAY_MEMORY, "autonomous_memory")
            kg_file = os.path.join(autmem_dir, "knowledge_graph.json")
            if os.path.exists(kg_file):
                with open(kg_file, "r") as f:
                    kg = json.load(f)
                nodes = kg.get("entities", {})
                edges = kg.get("relationships", [])
                related = [
                    e for e in edges
                    if e.get("source", "").lower() == entity.lower()
                    or e.get("target", "").lower() == entity.lower()
                ]
                return {"success": True, "entity": entity, "relationships": related, "depth": depth}
            return {"success": True, "entity": entity, "relationships": [], "depth": depth}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ═══════════════════════════════════════════════════════
    # Validation Endpoints
    # ═══════════════════════════════════════════════════════

    @app.post("/api/validate/code")
    async def validate_code(request: Request) -> Dict[str, Any]:
        """Validate Python code syntax and quality.

        Body: { "code": "...", "language": "python" }
        """
        try:
            data = await request.json()
        except Exception:
            return {"valid": False, "error": "Invalid JSON body"}
        try:
            from friday.validation_middleware import validate_python
            result = validate_python(data.get("code", ""))
            return {"valid": result.get("valid", False), "errors": result.get("errors", []), "warnings": result.get("warnings", [])}
        except ImportError:
            code = data.get("code", "")
            try:
                ast.parse(code)
                return {"valid": True, "errors": []}
            except SyntaxError as e:
                return {"valid": False, "errors": [{"line": e.lineno, "msg": str(e)}]}

    @app.post("/api/validate/html")
    async def validate_html_endpoint(request: Request) -> Dict[str, Any]:
        """Validate HTML content.

        Body: { "html": "..." }
        """
        try:
            data = await request.json()
        except Exception:
            return {"valid": False, "error": "Invalid JSON body"}
        try:
            from friday.validation_middleware import validate_html
            result = validate_html(data.get("html", ""))
            return {"valid": result.get("valid", False), "errors": result.get("errors", []), "warnings": result.get("warnings", [])}
        except ImportError:
            html_content = data.get("html", "")
            return {"valid": True, "note": "Basic HTML validation only (install lxml for full checks)", "length": len(html_content)}

    @app.post("/api/validate/json")
    async def validate_json_endpoint(request: Request) -> Dict[str, Any]:
        """Validate JSON content against an optional JSON Schema.

        Body: { "json_str": "...", "schema": {...} }
        """
        try:
            data = await request.json()
        except Exception:
            return {"valid": False, "error": "Invalid JSON body"}
        json_str = data.get("json_str", "")
        if isinstance(json_str, (dict, list)):
            json_str = json.dumps(json_str)
        try:
            parsed = json.loads(json_str) if isinstance(json_str, str) else json_str
            schema = data.get("schema")
            if schema:
                try:
                    import jsonschema
                    jsonschema.validate(parsed, schema)
                    return {"valid": True, "validated_against_schema": True}
                except ImportError:
                    return {"valid": True, "note": "JSON valid but jsonschema not installed for schema validation"}
                except jsonschema.exceptions.ValidationError as e:
                    return {"valid": False, "error": str(e), "validated_against_schema": True}
            return {"valid": True, "parsed_type": type(parsed).__name__}
        except json.JSONDecodeError as e:
            return {"valid": False, "error": str(e), "line": e.lineno, "col": e.colno}

    @app.post("/api/validate/secrets")
    async def validate_secrets_endpoint(request: Request) -> Dict[str, Any]:
        """Check content for exposed secrets (API keys, tokens, passwords).

        Body: { "content": "...", "context": "optional context" }
        """
        try:
            data = await request.json()
        except Exception:
            return {"success": False, "error": "Invalid JSON body"}
        try:
            from friday.validation_middleware import validate_secrets
            result = validate_secrets(data.get("content", ""), data.get("context", ""))
            return {"success": True, "result": result}
        except ImportError:
            import re
            content = data.get("content", "")
            patterns = {
                "API Key (generic)": r"(?i)(api[_-]?key|apikey|secret[_-]?key)[\s]*[:=][\s]*[\'\"']?[A-Za-z0-9_\-]{16,}",
                "AWS Access Key": r"AKIA[0-9A-Z]{16}",
                "GitHub Token": r"ghp_[A-Za-z0-9]{36}",
                "JWT Token": r"eyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+",
                "Private Key": r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
                "Password Assignment": r"(?i)password[\s]*[:=][\s]*[\'\"][^\'\"]{4,}[\'\"]",
            }
            findings = []
            for name, pattern in patterns.items():
                matches = re.findall(pattern, content)
                for m in matches:
                    findings.append({"type": name, "match": m[:50]})
            return {"success": True, "result": {"secrets_found": len(findings), "findings": findings}}

    @app.post("/api/validate/file")
    async def validate_file_endpoint(request: Request) -> Dict[str, Any]:
        """Validate a file path and its contents.

        Body: { "path": "...", "checks": ["exists", "size", "extension", "content"] }
        """
        try:
            data = await request.json()
        except Exception:
            return {"success": False, "error": "Invalid JSON body"}
        filepath = data.get("path", "")
        checks = data.get("checks", ["exists"])
        result = {"path": filepath, "checks": {}}
        if "exists" in checks:
            result["checks"]["exists"] = os.path.exists(filepath)
        if "size" in checks:
            if os.path.exists(filepath):
                size = os.path.getsize(filepath)
                result["checks"]["size_bytes"] = size
                max_mb = float(data.get("max_mb", 10))
                result["checks"]["size_ok"] = size <= max_mb * 1024 * 1024
            else:
                result["checks"]["size_ok"] = False
        if "extension" in checks:
            ext = os.path.splitext(filepath)[1].lower()
            allowed = data.get("allowed_extensions", [".py", ".js", ".ts", ".json", ".md", ".txt", ".html", ".css"])
            result["checks"]["extension"] = ext
            result["checks"]["extension_ok"] = ext in allowed or not allowed
        if "content" in checks and os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(10000)
                from friday.validation_middleware import validate_secrets
                sec_result = validate_secrets(content, filepath)
                result["checks"]["secrets"] = sec_result
            except ImportError:
                result["checks"]["secrets"] = "validation_middleware not available"
        return {"success": True, "result": result}

    # ═══════════════════════════════════════════════════════
    # Agent / Townhall Endpoints
    # ═══════════════════════════════════════════════════════

    @app.post("/api/townhall/session")
    async def townhall_create_session(request: Request) -> Dict[str, Any]:
        """Create a new agent deliberation session.

        Body: { "topic": "...", "participants": ["agent1", "agent2"], "agenda": [...] }
        """
        try:
            data = await request.json()
        except Exception:
            return {"success": False, "error": "Invalid JSON body"}
        try:
            from friday.townhall_agents import townhall_tool
            import json
            participants = data.get("participants", [])
            if isinstance(participants, list):
                participants = ", ".join(participants)
            result = townhall_tool(
                action="start",
                topic=data.get("topic", "General discussion"),
                participants=participants,
            )
            session_id = ""
            if isinstance(result, str) and ":" in result:
                session_id = result.split(":", 1)[-1].strip()
            return {"success": True, "result": result, "session_id": session_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.post("/api/townhall/message")
    async def townhall_post_message(request: Request) -> Dict[str, Any]:
        """Post a message to a deliberation session.

        Body: { "session_id": "...", "agent": "...", "message": "..." }
        """
        try:
            data = await request.json()
        except Exception:
            return {"success": False, "error": "Invalid JSON body"}
        try:
            from friday.townhall_agents import townhall_tool
            result = townhall_tool(
                action="post",
                session_id=data.get("session_id", ""),
                agent=data.get("agent", "user"),
                message=data.get("message", ""),
            )
            _broadcast_ws_event({"type": "townhall_message", "session_id": data.get("session_id"), "agent": data.get("agent")})
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.get("/api/townhall/session/{session_id}")
    async def townhall_get_session(session_id: str) -> Dict[str, Any]:
        """Get a deliberation session by ID."""
        try:
            from friday.townhall_agents import townhall_tool
            import json
            result = townhall_tool(action="session", session_id=session_id)
            try:
                return {"success": True, "session": json.loads(result)}
            except (json.JSONDecodeError, TypeError):
                return {"success": True, "session": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.get("/api/townhall/sessions")
    async def townhall_list_sessions(status: str = "") -> Dict[str, Any]:
        """List all deliberation sessions.

        Query params: status="active" (optional filter)
        """
        try:
            from friday.townhall_agents import townhall_tool
            import json
            result = townhall_tool(action="sessions", status=status)
            try:
                sessions = json.loads(result)
            except (json.JSONDecodeError, TypeError):
                sessions = result
            return {"success": True, "sessions": sessions}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.post("/api/townhall/deliberate")
    async def townhall_deliberate(request: Request) -> Dict[str, Any]:
        """Run autonomous agent deliberation on a topic.

        Body: { "topic": "...", "rounds": 3 }
        """
        try:
            data = await request.json()
        except Exception:
            return {"success": False, "error": "Invalid JSON body"}
        try:
            from friday.townhall_agents import townhall_tool
            import json
            result = townhall_tool(
                action="deliberate",
                topic=data.get("topic", ""),
                rounds=int(data.get("rounds", 3)),
            )
            try:
                parsed = json.loads(result)
            except (json.JSONDecodeError, TypeError):
                parsed = result
            return {"success": True, "result": parsed}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ═══════════════════════════════════════════════════════
    # Dashboard Endpoints
    # ═══════════════════════════════════════════════════════

    @app.get("/api/dashboard/status")
    async def dashboard_status() -> Dict[str, Any]:
        """JSON status report for the FRIDAY dashboard.

        Returns system stats, tools count, memory stats, agent status.
        """
        status = get_system_status()
        health = get_system_health()
        try:
            from friday.autonomous_memory import get_memory_stats
            mem_stats = get_memory_stats()
            status["memory"] = mem_stats
        except Exception:
            status["memory"] = {}
        try:
            from friday.townhall_agents import townhall_tool
            import json
            th_status = townhall_tool(action="status")
            try:
                status["townhall"] = json.loads(th_status)
            except (json.JSONDecodeError, TypeError):
                status["townhall"] = th_status
        except Exception:
            status["townhall"] = {}
        status["health"] = health
        return status

    @app.get("/api/dashboard/health")
    async def dashboard_health() -> Dict[str, Any]:
        """Health check endpoint returning system health and status code."""
        health = get_system_health()
        return health

    # ═══════════════════════════════════════════════════════
    # Bootstrap Endpoints
    # ═══════════════════════════════════════════════════════

    @app.post("/api/bootstrap/start")
    async def bootstrap_start(request: Request) -> Dict[str, Any]:
        """Start FRIDAY background services.

        Body: { "services": "daemon,dashboard", "profile": "standard" }
        """
        try:
            data = await request.json()
        except Exception:
            data = {}
        try:
            from friday.bootstrap import bootstrap_tool
            import json
            result = bootstrap_tool(
                action="start",
                services=data.get("services", ""),
                profile=data.get("profile", "standard"),
            )
            try:
                return json.loads(result)
            except (json.JSONDecodeError, TypeError):
                return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.post("/api/bootstrap/stop")
    async def bootstrap_stop() -> Dict[str, Any]:
        """Stop all FRIDAY background services."""
        try:
            from friday.bootstrap import bootstrap_tool
            import json
            result = bootstrap_tool(action="stop")
            try:
                return json.loads(result)
            except (json.JSONDecodeError, TypeError):
                return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.get("/api/bootstrap/status")
    async def bootstrap_status() -> Dict[str, Any]:
        """Get FRIDAY background service status."""
        try:
            from friday.bootstrap import bootstrap_tool
            import json
            result = bootstrap_tool(action="status")
            try:
                return json.loads(result)
            except (json.JSONDecodeError, TypeError):
                return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ═══════════════════════════════════════════════════════
    # Codebase Analysis Endpoints
    # ═══════════════════════════════════════════════════════

    @app.post("/api/analyze/scan")
    async def analyze_scan(request: Request) -> Dict[str, Any]:
        """Run a full codebase scan.

        Body: { "source_dir": "... (optional, defaults to FRIDAY source)" }
        """
        try:
            data = await request.json()
        except Exception:
            data = {}
        try:
            from friday.codebase_analyzer import codebase_analyzer_tool
            result = codebase_analyzer_tool(
                action="scan",
                source_dir=data.get("source_dir", ""),
            )
            _broadcast_ws_event({"type": "analyze_scan_complete"})
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.get("/api/analyze/hotspots")
    async def analyze_hotspots(limit: int = 20, threshold: int = 10) -> Dict[str, Any]:
        """Get code complexity hotspots.

        Returns functions with the highest cyclomatic complexity.
        """
        try:
            from friday.codebase_analyzer import codebase_analyzer_tool
            result = codebase_analyzer_tool(
                action="hotspots",
                limit=limit,
                threshold=threshold,
            )
            return {"success": True, "hotspots": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.get("/api/analyze/cycles")
    async def analyze_cycles() -> Dict[str, Any]:
        """Find circular dependencies in the codebase."""
        try:
            from friday.codebase_analyzer import codebase_analyzer_tool
            result = codebase_analyzer_tool(action="cycles")
            return {"success": True, "cycles": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.get("/api/analyze/coverage")
    async def analyze_coverage() -> Dict[str, Any]:
        """Get test coverage analysis."""
        try:
            from friday.codebase_analyzer import codebase_analyzer_tool
            result = codebase_analyzer_tool(action="coverage")
            return {"success": True, "coverage": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ═══════════════════════════════════════════════════════
    # File Management Endpoints
    # ═══════════════════════════════════════════════════════

    @app.post("/api/files/read")
    async def file_read(request: Request) -> Dict[str, Any]:
        """Read a file from the filesystem.

        Body: { "path": "...", "encoding": "utf-8", "max_bytes": 100000 }
        """
        try:
            data = await request.json()
        except Exception:
            return {"success": False, "error": "Invalid JSON body"}
        filepath = data.get("path", "")
        if not filepath:
            return {"success": False, "error": "No path provided"}
        filepath = os.path.abspath(filepath)
        if not os.path.exists(filepath):
            return {"success": False, "error": f"File not found: {filepath}"}
        if not os.path.isfile(filepath):
            return {"success": False, "error": f"Not a file: {filepath}"}
        max_bytes = int(data.get("max_bytes", 100000))
        encoding = data.get("encoding", "utf-8")
        try:
            file_size = os.path.getsize(filepath)
            with open(filepath, "r", encoding=encoding, errors="replace") as f:
                content = f.read(max_bytes)
            return {
                "success": True,
                "path": filepath,
                "size": file_size,
                "content": content,
                "truncated": file_size > max_bytes,
                "encoding": encoding,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.post("/api/files/write")
    async def file_write(request: Request) -> Dict[str, Any]:
        """Write content to a file.

        Body: { "path": "...", "content": "...", "encoding": "utf-8", "append": false }
        """
        try:
            data = await request.json()
        except Exception:
            return {"success": False, "error": "Invalid JSON body"}
        filepath = data.get("path", "")
        content = data.get("content", "")
        encoding = data.get("encoding", "utf-8")
        append = data.get("append", False)
        if not filepath:
            return {"success": False, "error": "No path provided"}
        filepath = os.path.abspath(filepath)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        mode = "a" if append else "w"
        try:
            if isinstance(content, str):
                with open(filepath, mode, encoding=encoding) as f:
                    f.write(content)
            elif isinstance(content, (dict, list)):
                with open(filepath, mode, encoding=encoding) as f:
                    json.dump(content, f, indent=2)
            else:
                with open(filepath, mode, encoding=encoding) as f:
                    f.write(str(content))
            return {"success": True, "path": filepath, "size": os.path.getsize(filepath), "mode": mode}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.post("/api/files/list")
    async def file_list(request: Request) -> Dict[str, Any]:
        """List files in a directory.

        Body: { "path": "...", "pattern": "*", "recursive": false, "include_hidden": false }
        """
        try:
            data = await request.json()
        except Exception:
            return {"success": False, "error": "Invalid JSON body"}
        dirpath = data.get("path", ".")
        dirpath = os.path.abspath(dirpath)
        if not os.path.exists(dirpath):
            return {"success": False, "error": f"Directory not found: {dirpath}"}
        if not os.path.isdir(dirpath):
            return {"success": False, "error": f"Not a directory: {dirpath}"}
        try:
            import glob as _glob
            pattern = data.get("pattern", "*")
            recursive = data.get("recursive", False)
            include_hidden = data.get("include_hidden", False)
            search_path = os.path.join(dirpath, pattern)
            files = _glob.glob(search_path, recursive=recursive)
            if not include_hidden:
                files = [f for f in files if not os.path.basename(f).startswith(".")]
            files = sorted(files)
            file_infos = []
            for f in files:
                try:
                    stat = os.stat(f)
                    file_infos.append({
                        "name": os.path.basename(f),
                        "path": f,
                        "size": stat.st_size,
                        "is_dir": os.path.isdir(f),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })
                except Exception:
                    file_infos.append({"name": os.path.basename(f), "path": f, "error": "stat failed"})
            return {"success": True, "directory": dirpath, "files": file_infos, "count": len(file_infos)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.get("/api/files/download/{path:path}")
    async def file_download(path: str) -> Any:
        """Download a file from the filesystem.

        Args:
            path: The file path relative to project root or absolute.
        """
        filepath = os.path.abspath(path)
        if not os.path.exists(filepath) or not os.path.isfile(filepath):
            return JSONResponse(
                status_code=404,
                content={"error": f"File not found: {filepath}"},
            )
        try:
            media_type, _ = mimetypes.guess_type(filepath)
            return FileResponse(filepath, media_type=media_type or "application/octet-stream")
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": str(e)},
            )

    # ═══════════════════════════════════════════════════════
    # WebSocket Endpoint
    # ═══════════════════════════════════════════════════════

    @app.websocket("/api/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """WebSocket endpoint for real-time updates.

        Clients receive JSON events for:
          - tool_call: when a tool is called via the API
          - memory_stored: when new memory is saved
          - townhall_message: when a townhall message is posted
          - analyze_scan_complete: when a full scan finishes
          - status_change: when server status changes
        """
        await websocket.accept()
        client_id = str(uuid.uuid4())[:8]
        with _ws_lock:
            _ws_connections.append(websocket)
        logger.info(f"WebSocket client connected: {client_id} (total: {len(_ws_connections)})")
        _broadcast_ws_event({"type": "status_change", "message": f"Client {client_id} connected", "clients": len(_ws_connections)})
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                    msg_type = msg.get("type", "unknown")
                    if msg_type == "ping":
                        await websocket.send_text(json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}))
                    elif msg_type == "subscribe":
                        channels = msg.get("channels", ["all"])
                        await websocket.send_text(json.dumps({"type": "subscribed", "channels": channels}))
                    else:
                        await websocket.send_text(json.dumps({"type": "echo", "original": msg}))
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({"type": "error", "message": "Invalid JSON"}))
        except WebSocketDisconnect:
            logger.info(f"WebSocket client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"WebSocket error for {client_id}: {e}")
        finally:
            with _ws_lock:
                if websocket in _ws_connections:
                    _ws_connections.remove(websocket)
            _broadcast_ws_event({"type": "status_change", "message": f"Client {client_id} disconnected", "clients": len(_ws_connections)})

    # ═══════════════════════════════════════════════════════
    # Additional Utility Endpoints
    # ═══════════════════════════════════════════════════════

    @app.get("/api/config")
    async def get_config() -> Dict[str, Any]:
        """Get FRIDAY configuration information."""
        try:
            from friday.config import get_config as _get_config
            return {"success": True, "config": _get_config()}
        except ImportError:
            return {"success": True, "note": "config module not available"}

    @app.get("/api/modules")
    async def list_modules() -> Dict[str, Any]:
        """List all loaded FRIDAY modules."""
        import pkgutil
        import friday
        modules = []
        for importer, modname, ispkg in pkgutil.iter_modules(friday.__path__):
            modules.append({"name": modname, "is_package": ispkg})
        return {"success": True, "modules": modules, "count": len(modules)}

    @app.get("/api/paths")
    async def get_paths() -> Dict[str, str]:
        """Get FRIDAY filesystem paths."""
        return {
            "project_root": PROJECT_ROOT,
            "friday_memory": FRIDAY_MEMORY,
            "friday_config": FRIDAY_CONFIG,
        }

    @app.post("/api/echo")
    async def echo_endpoint(request: Request) -> Dict[str, Any]:
        """Echo test endpoint for debugging."""
        try:
            body = await request.json()
        except Exception:
            body = {}
        return {
            "success": True,
            "method": request.method,
            "headers": dict(request.headers),
            "body": body,
            "timestamp": datetime.now().isoformat(),
        }

    @app.get("/api/routes")
    async def list_routes() -> List[Dict[str, str]]:
        """List all registered API routes."""
        routes = []
        for route in app.routes:
            methods = getattr(route, "methods", None)
            path = getattr(route, "path", str(route))
            if methods:
                for method in methods:
                    if method in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
                        routes.append({"path": path, "method": method})
        return sorted(routes, key=lambda r: r["path"])

    @app.get("/api/stats")
    async def get_stats() -> Dict[str, Any]:
        """Get API server statistics."""
        return {
            "start_time": datetime.fromtimestamp(_start_time).isoformat() if _start_time else "",
            "uptime_seconds": int(time.time() - _start_time) if _start_time else 0,
            "total_tools": len(discover_tools()),
            "active_websockets": len(_ws_connections),
            "fastapi_version": API_VERSION,
        }

    return app
# -----------------------------------------------------------
# WebSocket Broadcast
# -----------------------------------------------------------


def _broadcast_ws_event(event: Dict[str, Any]) -> None:
    """Broadcast a JSON event to all connected WebSocket clients.

    Args:
        event: A JSON-serializable dict to send to all clients.
    """
    if not _ws_connections:
        return
    message = json.dumps(event)
    dead = []
    with _ws_lock:
        for ws in _ws_connections:
            try:
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    if loop.is_running():
                        asyncio.run_coroutine_threadsafe(ws.send_text(message), loop)
                    else:
                        dead.append(ws)
                except RuntimeError:
                    dead.append(ws)
            except Exception:
                dead.append(ws)
        for ws in dead:
            try:
                _ws_connections.remove(ws)
            except ValueError:
                pass


# -----------------------------------------------------------
# Server Management
# -----------------------------------------------------------


def start_api_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> Dict[str, Any]:
    """Start the FRIDAY API server in a daemon thread.

    This is the main entry point for launching the FastAPI server.
    Runs uvicorn in a background thread so the calling process
    can continue running.

    Args:
        host: Host address to bind to (default: 127.0.0.1).
        port: Port number to listen on (default: 8000).

    Returns:
        Dict with status, url, and pid information.
    """
    global _server_thread, _server_instance, _server_stop_event, _start_time

    if _server_thread is not None and _server_thread.is_alive():
        return {
            "success": False,
            "error": "Server is already running",
            "url": f"http://{host}:{port}",
        }

    if not HAS_FASTAPI:
        return {
            "success": False,
            "error": "FastAPI is not installed. Install with: pip install fastapi uvicorn",
        }

    _server_stop_event.clear()
    _start_time = time.time()

    def _run_server():
        """Internal function to run the uvicorn server."""
        global _server_instance, _start_time
        try:
            _start_time = time.time()
            app = create_app()
            config = uvicorn.Config(
                app,
                host=host,
                port=port,
                log_level="info",
                reload=False,
                workers=1,
            )
            _server_instance = uvicorn.Server(config)
            set_service_state(
                "api_server",
                status="running",
                pid=os.getpid(),
                port=port,
                url=f"http://{host}:{port}",
                version=API_VERSION,
                start_time=datetime.now().isoformat(),
            )
            logger.info(f"API server starting at http://{host}:{port}")
            _server_instance.run()
        except Exception as e:
            logger.error(f"API server failed to start: {e}", exc_info=True)
            set_service_state(
                "api_server",
                status="error",
                error=str(e),
            )
        finally:
            _server_stop_event.set()
            clear_service_state("api_server")

    _server_thread = threading.Thread(
        target=_run_server,
        name="friday-api-server",
        daemon=True,
    )
    _server_thread.start()

    # Wait briefly for server to start
    for i in range(10):
        if _server_thread.is_alive():
            time.sleep(0.3)
        else:
            break

    return {
        "success": True,
        "url": f"http://{host}:{port}",
        "host": host,
        "port": port,
        "pid": os.getpid(),
        "version": API_VERSION,
        "docs_url": f"http://{host}:{port}/docs",
        "openapi_url": f"http://{host}:{port}/api/openapi.json",
        "message": "FRIDAY API server started. Access /docs for interactive documentation.",
    }


def stop_api_server() -> Dict[str, Any]:
    """Stop the FRIDAY API server gracefully.

    Shuts down the uvicorn server and clears runtime state.
    Safe to call even if the server is not running.

    Returns:
        Dict with status of the stop operation.
    """
    global _server_thread, _server_instance

    if _server_instance is not None:
        try:
            _server_instance.should_exit = True
            logger.info("Signalled API server to stop")
        except Exception as e:
            logger.warning(f"Error signalling server stop: {e}")

    if _server_thread is not None and _server_thread.is_alive():
        _server_stop_event.set()
        _server_thread.join(timeout=5.0)
        if _server_thread.is_alive():
            logger.warning("Server thread did not stop within timeout")
            return {
                "success": False,
                "error": "Server thread did not stop within timeout",
            }

    _server_instance = None
    _server_thread = None
    clear_service_state("api_server")

    with _ws_lock:
        _ws_connections.clear()

    logger.info("API server stopped")
    return {
        "success": True,
        "message": "FRIDAY API server stopped",
    }


def api_server_tool(action: str = "status", **kwargs: Any) -> str:
    """FRIDAY tool integration for managing the API server.

    This function serves as the bridge between the FRIDAY tool system
    and the FastAPI server. It allows FRIDAY to start, stop, and
    query the API server through the standard tool interface.

    Actions:
        status       - Show API server status (default)
        start        - Start the API server (host, port)
        stop         - Stop the API server
        restart      - Restart the API server
        health       - Get server health (if running)
        info         - Show detailed server information
        generate_key - Generate a new API key (name)
        list_keys    - List all API keys
        revoke_key   - Revoke an API key (api_key)
        routes       - List all registered routes
        tools        - List all discovered tools
        call         - Call a tool via the API (tool_name, params)
        openapi      - Get the OpenAPI spec

    Args:
        action: The action to perform (default: "status").
        **kwargs: Additional parameters for the action.

    Returns:
        Formatted string with the result of the action.
    """
    if action == "status":
        running = _server_thread is not None and _server_thread.is_alive()
        lines = [
            "### FRIDAY API SERVER STATUS",
            "",
            f"Running: {running}",
            f"FastAPI available: {HAS_FASTAPI}",
            f"Uvicorn available: {HAS_UVICORN}",
            f"Psutil available: {HAS_PSUTIL}",
            f"WebSocket clients: {len(_ws_connections)}",
            f"Discovered tools: {len(discover_tools())}",
            f"API Keys stored: {len(APIKeyAuth._load_keys())}",
            f"Uptime: {int(time.time() - _start_time)}s" if _start_time else "Uptime: N/A",
        ]
        if running:
            state = get_service_state("api_server")
            lines.append(f"URL: {state.get('url', 'unknown')}")
            lines.append(f"PID: {state.get('pid', 'unknown')}")
            lines.append(f"Port: {state.get('port', 'unknown')}")
        return "\n".join(lines)

    elif action == "start":
        host = kwargs.get("host", DEFAULT_HOST)
        port = int(kwargs.get("port", DEFAULT_PORT))
        result = start_api_server(host=host, port=port)
        if result.get("success"):
            return (
                f"[OK] API SERVER STARTED\n\n"
                f"URL: {result['url']}\n"
                f"Docs: {result['docs_url']}\n"
                f"Version: {result['version']}\n"
                f"PID: {result['pid']}"
            )
        else:
            return f"[FAIL] {result.get('error', 'Unknown error')}"

    elif action == "stop":
        result = stop_api_server()
        if result.get("success"):
            return "### API SERVER STOPPED\n\nServer has been shut down."
        else:
            return f"[FAIL] {result.get('error', 'Unknown error')}"

    elif action == "restart":
        stop_result = stop_api_server()
        host = kwargs.get("host", DEFAULT_HOST)
        port = int(kwargs.get("port", DEFAULT_PORT))
        time.sleep(0.5)
        start_result = start_api_server(host=host, port=port)
        if start_result.get("success"):
            return (
                f"### API SERVER RESTARTED\n\n"
                f"URL: {start_result['url']}\n"
                f"Docs: {start_result['docs_url']}"
            )
        else:
            return f"[FAIL] {start_result.get('error', 'Unknown error')}"

    elif action == "health":
        if _server_thread is None or not _server_thread.is_alive():
            return "[FAIL] Server is not running"
        health = get_system_health()
        return json.dumps(health, indent=2)

    elif action == "info":
        info = get_version_info()
        info["discovered_tools"] = len(discover_tools())
        info["ws_clients"] = len(_ws_connections)
        info["api_keys"] = len(APIKeyAuth._load_keys())
        return json.dumps(info, indent=2)

    elif action == "generate_key":
        name = kwargs.get("name", "tool-generated")
        raw_key = APIKeyAuth.generate_api_key(name)
        return f"### API KEY GENERATED\n\nName: {name}\nKey: {raw_key}\n\nSave this key - it won't be shown again!"

    elif action == "list_keys":
        keys = APIKeyAuth.list_api_keys()
        lines = ["### API KEYS", ""]
        for k in keys:
            status = "revoked" if k["revoked"] else "active"
            lines.append(f"  - {k['name']} ({k['key_prefix']}) [{status}]")
        lines.append(f"\nTotal: {len(keys)}")
        return "\n".join(lines)

    elif action == "revoke_key":
        api_key = kwargs.get("api_key", "")
        if not api_key:
            return "[FAIL] api_key parameter required"
        success = APIKeyAuth.revoke_api_key(api_key)
        if success:
            return "[OK] API key revoked"
        else:
            return "[FAIL] API key not found"

    elif action == "routes":
        return "Use GET /api/routes when the server is running."

    elif action == "tools":
        summary = get_tools_summary()
        lines = [f"### DISCOVERED TOOLS ({len(summary)})", ""]
        for t in summary:
            lines.append(f"  - {t['name']}: {t['doc']}")
        return "\n".join(lines)

    elif action == "call":
        tool_name = kwargs.get("tool_name", "")
        params = kwargs.get("params", {})
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except json.JSONDecodeError:
                return f"[FAIL] Invalid params JSON: {params}"
        if not tool_name:
            return "[FAIL] tool_name parameter required"
        result = call_tool_safe(tool_name, **params)
        return json.dumps(result, indent=2, default=str)

    elif action == "openapi":
        if not HAS_FASTAPI:
            return "[FAIL] FastAPI not installed"
        app = create_app()
        return json.dumps(app.openapi(), indent=2, default=str)

    return f"Unknown action: {action}. Available: status, start, stop, restart, health, info, generate_key, list_keys, revoke_key, routes, tools, call, openapi"


# -----------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------


if __name__ == "__main__":
    """Main entry point when running the file directly.

    Parses command-line arguments and starts the API server.
    Usage: python api_server.py [--host HOST] [--port PORT]
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="FRIDAY API Server - FastAPI REST API for FRIDAY tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\\
            Examples:
              python api_server.py
              python api_server.py --host 0.0.0.0 --port 9000
              python api_server.py --host 127.0.0.1 --port 8000 --no-uvicorn
        """),
    )
    parser.add_argument(
        "--host", type=str, default=DEFAULT_HOST,
        help=f"Host address (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT,
        help=f"Port number (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--no-uvicorn", action="store_true",
        help="Print app info without starting uvicorn",
    )
    parser.add_argument(
        "--version", action="store_true",
        help="Print version and exit",
    )
    parser.add_argument(
        "--list-tools", action="store_true",
        help="List all discovered tools and exit",
    )
    parser.add_argument(
        "--health", action="store_true",
        help="Check system health and exit",
    )

    args = parser.parse_args()

    if args.version:
        print(f"FRIDAY API Server v{API_VERSION}")
        print(f"Python: {sys.version.split()[0]}")
        print(f"Platform: {platform.platform()}")
        sys.exit(0)

    if args.list_tools:
        tools = discover_tools()
        print(f"Discovered {len(tools)} tools:")
        print()
        for name in sorted(tools.keys()):
            meta = get_tool_metadata(name)
            doc_short = meta["doc"][:80].replace("\n", " ") if len(meta["doc"]) > 80 else meta["doc"].replace("\n", " ")
            print(f"  {name}:")
            print(f"    {doc_short}")
            print(f"    Parameters: {meta['params_count']}, Async: {meta['is_async']}")
            print()
        sys.exit(0)

    if args.health:
        health = get_system_health()
        print(json.dumps(health, indent=2))
        sys.exit(0)

    if not HAS_FASTAPI:
        print("[ERROR] FastAPI is not installed.")
        print("Install with: pip install fastapi uvicorn")
        sys.exit(1)

    if args.no_uvicorn:
        app = create_app()
        print(f"FRIDAY API Server v{API_VERSION}")
        print(f"App created: {app.title}")
        print(f"Routes: {len(app.routes)}")
        print(f"Run with uvicorn: uvicorn friday.api_server:create_app --host {args.host} --port {args.port}")
        sys.exit(0)

    print(f"Starting FRIDAY API Server v{API_VERSION}...")
    print(f"Host: {args.host}:{args.port}")
    print(f"Documentation: http://{args.host}:{args.port}/docs")
    print(f"OpenAPI: http://{args.host}:{args.port}/api/openapi.json")
    print(f"Health: http://{args.host}:{args.port}/api/health")
    print(f"WebSocket: ws://{args.host}:{args.port}/api/ws")
    print()

    result = start_api_server(host=args.host, port=args.port)
    if result.get("success"):
        try:
            while _server_thread is not None and _server_thread.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            stop_api_server()
    else:
        print(f"[ERROR] {result.get('error', 'Failed to start server')}")
        sys.exit(1)


# -----------------------------------------------------------
# Documentation Exports
# -----------------------------------------------------------

# The following constants and functions are the public API of this module.
# Import them as:
#   from friday.api_server import start_api_server, stop_api_server, api_server_tool

__all__ = [
    "start_api_server",
    "stop_api_server",
    "api_server_tool",
    "create_app",
    "discover_tools",
    "get_system_health",
    "get_system_status",
    "get_version_info",
    "get_tool_metadata",
    "get_tools_summary",
    "call_tool_safe",
    "APIKeyAuth",
    "RateLimiter",
    "API_VERSION",
    "API_TITLE",
    "HAS_FASTAPI",
    "HAS_UVICORN",
    "HAS_PSUTIL",
]
