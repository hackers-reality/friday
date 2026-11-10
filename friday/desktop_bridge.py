"""FRIDAY Desktop Bridge — thin wrapper around the ``agent-desktop`` CLI.

agent-desktop (Apache-2.0, https://github.com/vercel-labs/agent-desktop) reads the
OS accessibility tree instead of OCR/pixel-matching:
  - Windows: UI Automation
  - macOS:   AX API
  - Linux:   AT-SPI

Every element carries a snapshot-scoped ref (``@<snapshot_id>:e<N>``). Refs are only
valid for the snapshot that produced them — if the UI changes, ref actions return
``STALE_REF`` / ``AMBIGUOUS_TARGET`` and you must take a new snapshot.

This module enforces that contract locally: ``desktop_get`` / ``desktop_click`` /
``desktop_type`` reject refs that were not produced by the most recent
``desktop_snapshot`` call, and typed text is piped via ``--stdin`` so secrets stay
out of process arguments.

NOTE on PowerShell: refs contain ``@`` and ``:`` — always quote them
(``'@s8f3k2p9:e8'``) when invoking the CLI by hand. This module calls the CLI with
an argv list (no shell), so refs never need quoting here.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from typing import Any, Optional

_REF_RE = re.compile(r"^@[A-Za-z0-9_-]+:e\d+$")

# Module-level record of refs produced by the LATEST snapshot (per process).
_latest_refs: set[str] = set()
_latest_snapshot_id: Optional[str] = None
_bin_cache: Optional[str] = None


def _bin() -> str:
    """Resolve the agent-desktop executable (cached). Returns '' if not found."""
    global _bin_cache
    if _bin_cache is None:
        _bin_cache = shutil.which("agent-desktop") or shutil.which("agent-desktop-win32-x64.exe") or ""
    return _bin_cache


def _unavailable() -> dict[str, Any]:
    return {
        "ok": False,
        "error": "agent-desktop CLI not found on PATH. Install with: npm install -g agent-desktop",
        "hint": "https://github.com/vercel-labs/agent-desktop",
    }


def _parse_envelope(raw: str) -> dict[str, Any]:
    """Parse the single-line JSON envelope printed by every agent-desktop command."""
    try:
        env = json.loads(raw)
    except json.JSONDecodeError:
        return {"ok": False, "error": f"agent-desktop returned non-JSON output: {raw[:300]}"}
    if not isinstance(env, dict):
        return {"ok": False, "error": "agent-desktop returned an unexpected payload"}
    if env.get("ok"):
        return {"ok": True, "command": env.get("command"), "data": env.get("data", {})}
    err = env.get("error") or {}
    return {
        "ok": False,
        "command": env.get("command"),
        "error": err.get("message") or "unknown agent-desktop error",
        "code": err.get("code"),
        "disposition": (err.get("disposition") or {}).get("retry"),
        "details": err.get("details"),
    }


def _run(args: list[str], stdin_text: Optional[str] = None, timeout: float = 60.0) -> dict[str, Any]:
    exe = _bin()
    if not exe:
        return _unavailable()
    try:
        proc = subprocess.run(
            [exe, *args],
            input=stdin_text.encode("utf-8") if stdin_text is not None else None,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"agent-desktop timed out after {timeout}s ({args[0] if args else '?'})"}
    except OSError as e:
        return {"ok": False, "error": f"failed to execute agent-desktop: {e}"}
    out = proc.stdout.decode("utf-8", errors="replace").strip()
    parsed = _parse_envelope(out)
    if proc.returncode != 0 and parsed.get("ok"):
        # Non-zero exit but parseable ok envelope — surface as failure honestly.
        parsed["ok"] = False
        parsed["error"] = f"exit code {proc.returncode}: {parsed.get('error', 'unknown error')}"
    return parsed


def _collect_refs(node: Any, refs: set[str]) -> None:
    """Walk the snapshot tree collecting every ref_id."""
    if isinstance(node, dict):
        ref = node.get("ref_id") or node.get("ref")
        if isinstance(ref, str) and _REF_RE.match(ref):
            refs.add(ref)
        for value in node.values():
            _collect_refs(value, refs)
    elif isinstance(node, list):
        for item in node:
            _collect_refs(item, refs)


def _remember_snapshot(result: dict[str, Any]) -> None:
    global _latest_refs, _latest_snapshot_id
    refs: set[str] = set()
    data = result.get("data") or {}
    _collect_refs(data.get("tree"), refs)
    # Some envelopes also ship a flat ref list.
    for key in ("refs", "elements"):
        _collect_refs(data.get(key), refs)
    _latest_refs = refs
    sid = data.get("snapshot_id")
    _latest_snapshot_id = sid if isinstance(sid, str) else None


def _require_ref(ref: str) -> Optional[str]:
    """Return an error string if the ref is unusable, else None."""
    if not isinstance(ref, str):
        return "ref must be a string like '@s8f3k2p9:e8'"
    ref = ref.strip()
    if not _REF_RE.match(ref):
        return f"invalid ref format '{ref}' — expected '@<snapshot_id>:e<N>' (e.g. '@s8f3k2p9:e8')"
    if ref not in _latest_refs:
        scope = f" (current snapshot: @{_latest_snapshot_id})" if _latest_snapshot_id else " (no snapshot taken yet)"
        return (
            f"ref '{ref}' was not produced by the latest snapshot{scope}. "
            f"Take a new desktop_snapshot(app=...) and use its refs."
        )
    return None


# ─── Tool functions ───────────────────────────────────────────────────────────

def desktop_status() -> dict[str, Any]:
    """agent-desktop availability, permissions and supported surfaces (read-only)."""
    return _run(["status"], timeout=30.0)


def desktop_list_apps() -> dict[str, Any]:
    """List running applications with pids and presentation state (read-only)."""
    return _run(["list-apps"], timeout=30.0)


def desktop_list_windows() -> dict[str, Any]:
    """List open application windows with ids, bounds, titles (read-only)."""
    return _run(["list-windows"], timeout=30.0)


def desktop_snapshot(app: str = "", window_id: str = "", interactive_only: bool = True,
                     compact: bool = True, max_depth: int = 10) -> dict[str, Any]:
    """Capture the accessibility tree of an app (or focused window) as JSON with refs.

    Interactive elements only by default. Every actionable element carries a
    snapshot-scoped ref ('@<snapshot_id>:e<N>') for desktop_get/click/type.
    """
    args = ["snapshot"]
    if app:
        args += ["--app", app]
    if window_id:
        args += ["--window-id", window_id]
    if interactive_only:
        args.append("-i")
    if compact:
        args.append("--compact")
    if max_depth and max_depth != 10:
        args += ["--max-depth", str(int(max_depth))]
    result = _run(args, timeout=60.0)
    if result.get("ok"):
        _remember_snapshot(result)
        data = result.get("data") or {}
        result["ref_count"] = len(_latest_refs)
        result["snapshot_id"] = _latest_snapshot_id
        result["note"] = "Refs are valid only for this snapshot. Re-snapshot after any UI change."
    return result


def desktop_get(ref: str, property: str = "text") -> dict[str, Any]:
    """Read an element property: text, value, title, bounds, role, states."""
    err = _require_ref(ref)
    if err:
        return {"ok": False, "error": err}
    prop = property if property in {"text", "value", "title", "bounds", "role", "states"} else "text"
    return _run(["get", ref.strip(), "--property", prop], timeout=30.0)


def desktop_click(ref: str) -> dict[str, Any]:
    """Click an element via its accessibility ref (headless by default)."""
    err = _require_ref(ref)
    if err:
        return {"ok": False, "error": err}
    return _run(["click", ref.strip()], timeout=30.0)


def desktop_type(ref: str, text: str = "") -> dict[str, Any]:
    """Type text into the element identified by ref. Text is piped via --stdin
    so it never appears in process arguments."""
    err = _require_ref(ref)
    if err:
        return {"ok": False, "error": err}
    if not isinstance(text, str) or not text:
        return {"ok": False, "error": "text must be a non-empty string"}
    if len(text.encode("utf-8")) > 10_000:
        return {"ok": False, "error": "text exceeds 10,000 bytes (agent-desktop --stdin limit)"}
    return _run(["type", ref.strip(), "--stdin"], stdin_text=text, timeout=60.0)


def desktop_press(key: str, app: str = "") -> dict[str, Any]:
    """Send a key combo (e.g. 'return', 'escape', 'ctrl+c', 'shift+tab').

    Headless: targets the app's process without focusing it when ``app`` is given.
    Dangerous shortcuts are refused by agent-desktop unless run with --force
    (which this bridge never passes)."""
    if not isinstance(key, str) or not key.strip():
        return {"ok": False, "error": "key must be a non-empty combo like 'return' or 'ctrl+c'"}
    combo = key.strip().lower()
    if not re.match(r"^[a-z0-9_]+(\+[a-z0-9_]+)*$", combo):
        return {"ok": False, "error": f"invalid key combo '{key}' — expected like 'return', 'ctrl+c', 'shift+tab'"}
    args = ["press", combo]
    if app:
        args += ["--app", app]
    return _run(args, timeout=30.0)
