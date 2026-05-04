
"""Friday's built-in tools — rewritten for safer execution, better stability,
and optional Home Assistant smart-home control.

Designed for Windows-first desktop automation, but the non-UI helpers still work
on other platforms when the optional dependencies are installed.
"""

from __future__ import annotations

import base64
import glob
import io
import json
import os
import queue as _queue_module
import re
import shutil
import sqlite3
import subprocess
import threading
import time
import webbrowser
from datetime import datetime
from html.parser import HTMLParser
from typing import Any, Callable, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

# ─── SAFETY ──────────────────────────────────────────────────────────────

_BLOCKED_PATTERNS = [
    "rm -rf", "del /f", "format ", "rd /s", "shutdown", "rmdir /s",
    "reg delete", "bcdedit", "diskpart", "mkfs", ":(){:|:&};:",
    "dd if=", "mv /* ", "chmod 777 /", "> /dev/sd",
]

def _is_safe_command(command: str) -> bool:
    cmd_lower = command.lower()
    return not any(p in cmd_lower for p in _BLOCKED_PATTERNS)

def safe_run_cmd(command: str) -> str:
    """A safer wrapper around run_cmd() with a hard allowlist."""
    base = (command.strip().split() or [""])[0].lower()
    allowed = {
        "dir", "echo", "ipconfig", "ping", "tasklist", "taskkill",
        "whoami", "date", "time", "python", "py", "git",
    }
    if base not in allowed:
        return f"⛔ Command '{base}' not permitted."
    return run_cmd(command)

# ─── PERSISTENT MEMORY ───────────────────────────────────────────────────

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "friday_memory", "vault.db")
_DB_INIT_LOCK = threading.Lock()

def _init_db() -> None:
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    with sqlite3.connect(_DB_PATH, timeout=10) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS memories ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "category TEXT NOT NULL, "
            "keyword TEXT NOT NULL, "
            "content TEXT NOT NULL, "
            "timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)"
        )
        conn.commit()

def memory_store(category: str, keyword: str, content: str) -> str:
    """Store facts, preferences, or technical details in the vault."""
    with _DB_INIT_LOCK:
        _init_db()
        with sqlite3.connect(_DB_PATH, timeout=10) as conn:
            conn.execute(
                "INSERT INTO memories (category, keyword, content) VALUES (?, ?, ?)",
                (category, keyword, content),
            )
            conn.commit()
    return f"Neural Entry Recorded: '{keyword}' stored in {category} vault, Boss."

def memory_retrieve(query: str) -> str:
    """Recall intel from the vault based on a query."""
    with _DB_INIT_LOCK:
        _init_db()
        with sqlite3.connect(_DB_PATH, timeout=10) as conn:
            rows = conn.execute(
                "SELECT category, keyword, content FROM memories "
                "WHERE keyword LIKE ? OR content LIKE ? "
                "ORDER BY timestamp DESC LIMIT 5",
                (f"%{query}%", f"%{query}%"),
            ).fetchall()

    if not rows:
        return f"Scouted vault for '{query}' — no matching records."
    return "### VAULT RECALL:\n" + "\n".join(
        f"[{r[0]}] {r[1]}: {r[2]}" for r in rows
    )

# ─── SEQUENTIAL TASK QUEUE ────────────────────────────────────────────────

_task_queue = _queue_module.Queue()
_queue_results: dict[str, str] = {}
_queue_results_lock = threading.Lock()
_queue_worker_started = False

def _queue_worker() -> None:
    while True:
        try:
            task_id, func_name, args, kwargs = _task_queue.get(timeout=1)
            func = globals().get(func_name)
            if func and callable(func):
                try:
                    result = func(*args, **kwargs)
                    stark_log(f"[QUEUE] {task_id} ({func_name}) done: {str(result)[:120]}")
                except Exception as e:
                    result = f"[ERROR] {e}"
                    stark_log(f"[QUEUE] {task_id} ({func_name}) FAILED: {e}")
            else:
                result = f"[ERROR] Unknown function: {func_name}"
            with _queue_results_lock:
                _queue_results[task_id] = result
            _task_queue.task_done()
        except _queue_module.Empty:
            continue
        except Exception as e:
            try:
                stark_log(f"[QUEUE WORKER] Error: {e}")
            except Exception:
                pass

def _ensure_queue_worker() -> None:
    global _queue_worker_started
    if not _queue_worker_started:
        threading.Thread(target=_queue_worker, daemon=True).start()
        _queue_worker_started = True

def queue_task(func_name: str, *args, **kwargs) -> str:
    """
    Queue a single tool for sequential execution.
    Returns task_id immediately. Use queue_result(task_id) to check output.
    """
    _ensure_queue_worker()
    import uuid
    task_id = str(uuid.uuid4())[:8]
    _task_queue.put((task_id, func_name, list(args), kwargs))
    pos = _task_queue.qsize()
    return f"Task [{task_id}] queued: {func_name} — position {pos} in queue."

def queue_status() -> str:
    """Check how many tasks are pending and completed."""
    pending = _task_queue.qsize()
    with _queue_results_lock:
        done = len(_queue_results)
    return f"Queue: {pending} pending, {done} completed this session."

def queue_result(task_id: str) -> str:
    """Retrieve the result of a completed queued task."""
    with _queue_results_lock:
        result = _queue_results.get(task_id)
    if result is None:
        return f"Task [{task_id}] not yet complete or not found."
    return f"Task [{task_id}] result: {result}"

def _split_multi_args(raw_args: str) -> list[str]:
    # Accept either pipe-separated args or a single natural-language string.
    if "|" in raw_args:
        return [part.strip() for part in raw_args.split("|") if part.strip()]
    return [raw_args.strip()] if raw_args.strip() else []

def multi_task(*task_specs: str) -> str:
    """
    Queue multiple tool calls to run sequentially, one after another.

    Format examples:
        multi_task("spotify_play:Blinding Lights", "see_screen:any errors?", "web_search:Python asyncio")
        multi_task("open_app:spotify", "alexa_command:turn off bedroom light")
    """
    _ensure_queue_worker()
    import uuid

    task_ids = []
    for spec in task_specs:
        if not spec or ":" not in spec:
            continue
        func_name, raw_args = spec.split(":", 1)
        func_name = func_name.strip()
        args = _split_multi_args(raw_args.strip())

        task_id = str(uuid.uuid4())[:8]
        _task_queue.put((task_id, func_name, args, {}))
        task_ids.append(f"[{task_id}] {func_name}")
        stark_log(f"[MULTI] Queued {func_name} as {task_id}")

    if not task_ids:
        return "No valid tasks were queued."
    return "Queued tasks in sequence:\n" + "\n".join(task_ids)

# ─── DEEP RESEARCH ───────────────────────────────────────────────────────

def deep_research(topic: str, url: Optional[str] = None, depth: int = 3) -> str:
    """
    Stark Research Protocol: multi-source deep research with a markdown report.
    Saved under friday_reports/.
    """
    try:
        from duckduckgo_search import DDGS
    except Exception as e:
        return f"Deep research unavailable: duckduckgo_search import failed ({e})."

    depth = max(1, min(int(depth), 5))
    slug = re.sub(r"[^a-z0-9]+", "_", topic.lower())[:40].strip("_") or "research"
    report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "friday_reports")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f"{slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")

    class _TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts: list[str] = []
            self._skip = False

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style", "nav", "footer", "header"):
                self._skip = True

        def handle_endtag(self, tag):
            if tag in ("script", "style", "nav", "footer", "header"):
                self._skip = False

        def handle_data(self, data):
            if not self._skip and data.strip():
                self.parts.append(data.strip())

    def _fetch_page_text(page_url: str, char_limit: int = 4000) -> Optional[str]:
        try:
            resp = requests.get(page_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if "text/html" not in resp.headers.get("Content-Type", ""):
                return None
            parser = _TextExtractor()
            parser.feed(resp.text)
            return " ".join(parser.parts)[:char_limit]
        except Exception:
            return None

    sources_used: list[str] = []
    raw_sections: list[str] = [
        "# STARK RESEARCH REPORT",
        f"## Topic: {topic}",
        f"**Generated:** {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}",
        "",
        "---",
    ]

    if url:
        raw_sections.append("## Primary Source")
        text = _fetch_page_text(url, 8000)
        if text:
            raw_sections.extend([f"**Source:** {url}", "", text, ""])
            sources_used.append(url)
        else:
            raw_sections.extend([f"**Could not fetch:** {url}", ""])

    search_queries = [
        topic,
        f"{topic} latest",
        f"{topic} technical deep dive",
        f"{topic} pros cons analysis",
        f"{topic} real world applications",
    ]

    raw_sections.append("## Web Intelligence Sweep")
    all_snippets: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for sq in search_queries[:depth + 2]:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(sq, max_results=4))
            for r in results:
                href = r.get("href", "")
                if href and href not in seen_urls:
                    seen_urls.add(href)
                    all_snippets.append(
                        {"title": r.get("title", ""), "url": href, "snippet": r.get("body", "")}
                    )
            time.sleep(0.35)
        except Exception:
            continue

    for i, s in enumerate(all_snippets[:10]):
        raw_sections.extend([
            f"**{i+1}. {s['title']}**",
            s["snippet"],
            f"*Source: {s['url']}*",
            "",
        ])
        sources_used.append(s["url"])

    raw_sections.append("## Deep Page Analysis")
    fetched = 0
    for s in all_snippets[:depth]:
        if fetched >= depth:
            break
        text = _fetch_page_text(s["url"])
        if text:
            raw_sections.extend([f"### {s['title']}", f"**URL:** {s['url']}", "", text, "", "---"])
            fetched += 1

    google_api_key = os.environ.get("GOOGLE_API_KEY", "")
    raw_blob = "\n".join(raw_sections)[:14000]
    synthesis = ""

    if google_api_key:
        try:
            resp = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
                headers={"Content-Type": "application/json"},
                params={"key": google_api_key},
                json={
                    "contents": [{
                        "parts": [{
                            "text": (
                                f"You are Friday, Tony Stark's sovereign AI research analyst.\n"
                                f"Write a comprehensive, structured report about: '{topic}'.\n\n"
                                f"Use these sections:\n"
                                f"1. Executive Summary\n"
                                f"2. Key Findings\n"
                                f"3. Technical Analysis\n"
                                f"4. Opportunities & Risks\n"
                                f"5. Recommended Actions\n"
                                f"6. Conclusion\n\n"
                                f"Be thorough, analytical, precise. Format in clean markdown.\n\n"
                                f"RAW RESEARCH DATA:\n{raw_blob}"
                            )
                        }]
                    }]
                },
                timeout=45,
            )
            resp_json = resp.json()
            candidates = resp_json.get("candidates", [])
            if candidates and candidates[0].get("content", {}).get("parts"):
                synthesis = candidates[0]["content"]["parts"][0].get("text", "")
            else:
                synthesis = f"*Synthesis blocked or empty: {resp_json.get('promptFeedback', 'No feedback')}*"
        except Exception as e:
            synthesis = f"*Synthesis failed: {e} — raw data collected above.*"
    else:
        synthesis = "*Synthesis skipped: GOOGLE_API_KEY not configured.*"

    final_report = (
        "\n".join(raw_sections)
        + "\n\n---\n\n## FRIDAY SYNTHESIS\n\n"
        + synthesis
        + f"\n\n---\n\n## Sources ({len(sources_used)})\n"
        + "\n".join(f"{i+1}. {s}" for i, s in enumerate(sources_used))
    )

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(final_report)

    memory_store("semantic", f"research:{slug}", f"Report: {report_path}")
    stark_log(f"[RESEARCH] Report generated: {report_path} ({len(sources_used)} sources)")

    return (
        "### RESEARCH COMPLETE\n"
        f"**Topic:** {topic}\n"
        f"**Sources swept:** {len(sources_used)}\n"
        f"**Pages deep-fetched:** {fetched}\n"
        f"**Report saved:** {report_path}\n\n"
        f"**SYNTHESIS PREVIEW:**\n{synthesis[:600]}..."
    )

# ─── SMART HOME ───────────────────────────────────────────────────────────

_ALEXA_WEBHOOK_URL = os.environ.get("ALEXA_WEBHOOK_URL", "").rstrip("/")
_FRIDAY_WEBHOOK_SECRET = os.environ.get("FRIDAY_WEBHOOK_SECRET", "")
HOME_ASSISTANT_URL = os.environ.get("HOME_ASSISTANT_URL", "").rstrip("/")
HOME_ASSISTANT_TOKEN = os.environ.get("HOME_ASSISTANT_TOKEN", "")

def home_assistant_command(entity_id: str, action: str = "toggle") -> str:
    """
    Control a Home Assistant entity directly through the REST API.

    Requires:
      HOME_ASSISTANT_URL=http://IP:8123
      HOME_ASSISTANT_TOKEN=Long-Lived Access Token
    """
    if not HOME_ASSISTANT_URL or not HOME_ASSISTANT_TOKEN:
        return "❌ Home Assistant not configured."

    entity_id = entity_id.strip()
    if "." not in entity_id:
        return "❌ entity_id must look like 'light.bedroom'."

    service = {
        "turn_on": "turn_on",
        "turn_off": "turn_off",
        "toggle": "toggle",
    }.get(action.lower().strip(), "toggle")

    domain = entity_id.split(".", 1)[0]
    url = f"{HOME_ASSISTANT_URL}/api/services/{domain}/{service}"
    headers = {
        "Authorization": f"Bearer {HOME_ASSISTANT_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(url, headers=headers, json={"entity_id": entity_id}, timeout=8)
        if resp.status_code in (200, 201):
            return f"✅ Home Assistant executed {service} on {entity_id}."
        return f"❌ Home Assistant error: HTTP {resp.status_code} — {resp.text[:200]}"
    except Exception as e:
        return f"❌ Home Assistant connection failed: {e}"

def alexa_command(command: str) -> str:
    """
    Send a command to the Friday Alexa bridge.

    This is best for Alexa routines, custom skill dispatch, or routing to
    whatever Alexa-side logic you already configured for the Wipro ecosystem.
    """
    command = command.strip()
    if not command:
        return "❌ No command provided."

    if not _ALEXA_WEBHOOK_URL:
        return (
            "❌ Alexa Bridge not configured.\n"
            "Steps:\n"
            "1. Run: python alexa_webhook_server.py\n"
            "2. Run: ngrok http 5123\n"
            "3. Add to .env: ALEXA_WEBHOOK_URL=https://<your-ngrok-url>\n"
            "4. Set Alexa Skill endpoint to: https://<ngrok-url>/alexa"
        )

    smart_aliases = {
        "turn off lights": "turn off the lights",
        "turn on lights": "turn on the lights",
        "lights off": "turn off the lights",
        "lights on": "turn on the lights",
    }
    mapped_command = smart_aliases.get(command.lower(), command)

    try:
        resp = requests.post(
            f"{_ALEXA_WEBHOOK_URL}/friday/send",
            headers={
                "Content-Type": "application/json",
                "X-Friday-Secret": _FRIDAY_WEBHOOK_SECRET,
            },
            json={"command": mapped_command},
            timeout=8,
        )
        if resp.status_code == 200:
            stark_log(f"[ALEXA] Sent: {mapped_command}")
            return f"✅ Alexa command dispatched: '{mapped_command}'"
        if resp.status_code == 401:
            return "❌ Alexa Bridge: Auth failed — check FRIDAY_WEBHOOK_SECRET in .env."
        return f"❌ Alexa Bridge: HTTP {resp.status_code} — {resp.text[:180]}"
    except requests.exceptions.ConnectionError:
        return "❌ Alexa Bridge: Cannot connect — is alexa_webhook_server.py running?"
    except requests.exceptions.Timeout:
        return "❌ Alexa Bridge: Timeout."
    except Exception as e:
        return f"❌ Alexa Error: {e}"

def alexa_poll() -> str:
    """Poll the Alexa bridge for commands Alexa sent to Friday."""
    if not _ALEXA_WEBHOOK_URL:
        return "Alexa Bridge not configured."
    try:
        resp = requests.get(
            f"{_ALEXA_WEBHOOK_URL}/friday/poll",
            headers={"X-Friday-Secret": _FRIDAY_WEBHOOK_SECRET},
            timeout=8,
        )
        if resp.status_code == 200:
            commands = resp.json().get("commands", [])
            if not commands:
                return "No pending Alexa commands."
            return f"Alexa commands received:\n{json.dumps(commands, indent=2)}"
        return f"Poll failed: {resp.status_code}"
    except Exception as e:
        return f"Alexa poll error: {e}"

def smart_home_command(target: str, action: str = "toggle") -> str:
    """
    Preferred smart-home control path:
    1) Home Assistant if configured
    2) Alexa bridge fallback for your existing Alexa routines
    """
    ha_result = home_assistant_command(target, action)
    if not ha_result.startswith("❌ Home Assistant not configured"):
        return ha_result
    phrase = f"{action} {target.replace('.', ' ')}"
    return alexa_command(phrase)

# ─── DIAGNOSTIC ───────────────────────────────────────────────────────────

def stark_doctor() -> str:
    """Perform a full self-diagnostic on Sovereign AI systems."""
    report = ["### STARK SYSTEMS DIAGNOSTIC REPORT"]

    try:
        start = time.time()
        requests.get("https://www.google.com", timeout=3)
        latency = (time.time() - start) * 1000
        report.append(f"✅ Network: Neural Link Active ({latency:.0f}ms)")
    except Exception:
        report.append("❌ Network: Neural Link IMPAIRED")

    try:
        sp = _get_spotify()
        user = sp.current_user()
        report.append(f"✅ Spotify: Authenticated as {user.get('display_name', 'Unknown')}")
    except Exception as e:
        report.append(f"⚠️ Spotify: Link unavailable ({e})")

    state_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sovereign_state.json")
    if not os.path.exists(state_path):
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump({"queue": [], "active_window": "Unknown"}, f)
    report.append("✅ State: Sovereign Memory LOADED")

    try:
        _init_db()
        report.append("✅ Memory Vault: ONLINE")
    except Exception as e:
        report.append(f"❌ Memory Vault: OFFLINE ({e})")

    report.append(f"✅ Task Queue: {_task_queue.qsize()} pending tasks")

    if _ALEXA_WEBHOOK_URL:
        try:
            r = requests.get(f"{_ALEXA_WEBHOOK_URL}/health", timeout=3)
            report.append("✅ Alexa Bridge: ONLINE" if r.status_code == 200 else "⚠️ Alexa Bridge: Unhealthy")
        except Exception:
            report.append("❌ Alexa Bridge: OFFLINE")
    else:
        report.append("⚠️ Alexa Bridge: Not configured")

    if HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN:
        report.append("✅ Home Assistant: CONFIGURED")
    else:
        report.append("⚠️ Home Assistant: Not configured")

    return "\n".join(report)

def run_after(seconds: int, func_name: str, *args, **kwargs) -> str:
    """Schedule a tool call for the future."""
    def task():
        time.sleep(seconds)
        func = globals().get(func_name)
        if func and callable(func):
            try:
                func(*args, **kwargs)
            except Exception as e:
                try:
                    stark_log(f"Scheduled task failed: {e}")
                except Exception:
                    pass
        else:
            try:
                stark_log(f"Scheduled task failed: unknown function '{func_name}'")
            except Exception:
                pass

    threading.Thread(target=task, daemon=True).start()
    return f"Task '{func_name}' scheduled in {seconds}s."

# ─── APP & SYSTEM TOOLS ──────────────────────────────────────────────────

def open_app(name: str) -> str:
    """Open an application by name."""
    import pathlib

    low_name = name.lower().strip()

    ai_nexus = {
        "claude": "https://claude.ai",
        "claw": "https://claude.ai/code",
        "chatgpt": "https://chatgpt.com",
        "gemini": "https://gemini.google.com",
        "deepseek": "https://chat.deepseek.com",
    }
    if low_name in ai_nexus:
        open_url(ai_nexus[low_name])
        return f"Navigating to {name} Nexus."

    protocols = {
        "calculator": "calc",
        "settings": "ms-settings:",
        "photos": "ms-photos:",
        "store": "ms-windows-store:",
    }
    if low_name in protocols:
        try:
            os.startfile(protocols[low_name])
            return f"Opened {name}"
        except Exception:
            pass

    start_menu_dirs = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"),
    ]
    for d in start_menu_dirs:
        if os.path.exists(d):
            for lnk in pathlib.Path(d).rglob("*.lnk"):
                if low_name in lnk.stem.lower():
                    os.startfile(str(lnk))
                    return f"Opened {lnk.stem}"

    found = shutil.which(low_name) or shutil.which(name)
    if found:
        subprocess.Popen([found])
        return f"Launched {name} from PATH."

    try:
        subprocess.Popen(f'start "" "{name}"', shell=True)
        return f"Launched {name}"
    except Exception:
        return f"Could not find {name}."

def run_cmd(command: str) -> str:
    """Run a shell command and return its output."""
    if not _is_safe_command(command):
        return "⛔ BLOCKED: Command matched destructive pattern."
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout.strip() or result.stderr.strip() or "Command executed."
    except subprocess.TimeoutExpired:
        return "Command timed out after 30s."
    except Exception as e:
        return f"Error: {e}"

def open_url(url: str) -> str:
    """Open a URL in the default browser."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opened {url}"

# ─── RESEARCH TOOLS ──────────────────────────────────────────────────────

def web_search(query: str, max_results: int = 5) -> str:
    """Quick single web search."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if results:
            return "\n---\n".join(
                f"Title: {r['title']}\nSource: {r['href']}\nSnippet: {r['body']}"
                for r in results
            )
    except Exception as e:
        return f"Search failed: {e}"
    return "No results found."

def video_search(query: str, max_results: int = 5) -> str:
    """Find videos online and return results headlessly (no browser)."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.videos(query, max_results=max_results))
        if not results:
            return "No videos found for this query."

        lines = [f"### Video Results for: {query}\n"]
        for i, v in enumerate(results, 1):
            title = v.get("title", "Unknown")
            url = v.get("content", v.get("href", "N/A"))
            duration = v.get("duration", "N/A")
            publisher = v.get("publisher", "N/A")
            lines.append(f"{i}. **{title}**")
            lines.append(f"   URL: {url}")
            lines.append(f"   Duration: {duration} | Source: {publisher}\n")
        return "\n".join(lines)
    except Exception as e:
        return f"Video search error: {e}"

# ─── VISION TOOLS ─────────────────────────────────────────────────────────

def see_screen(question: str = "Analyze the current workspace.") -> str:
    """Visual Scout: Gemini Vision analyzes screen with model fallback."""
    try:
        import pygetwindow as gw
        active = gw.getActiveWindow()
        if active:
            try:
                state_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sovereign_state.json")
                with open(state_path, "r+", encoding="utf-8") as f:
                    s = json.load(f)
                    s["active_window"] = active.title
                    f.seek(0)
                    json.dump(s, f, indent=4)
                    f.truncate()
            except Exception:
                pass
    except Exception:
        pass

    try:
        import pyautogui
        img = pyautogui.screenshot()
    except Exception as e:
        return f"Visual Link Error: screenshot failed ({e})"

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=75)
    img_b64 = base64.b64encode(buffer.getvalue()).decode()

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        return "Visual Link Error: GOOGLE_API_KEY not configured."

    models_to_try = [
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-2.0-flash-lite",
    ]

    for model in models_to_try:
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"Content-Type": "application/json"},
                params={"key": api_key},
                json={
                    "contents": [{
                        "parts": [
                            {"text": f"[STARK VISUAL SCOUT] {question}\nIdentify text, buttons, errors, coordinates for automation. Be concise."},
                            {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
                        ]
                    }],
                    "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.1},
                },
                timeout=30,
            )
            if r.status_code == 200:
                data = r.json()
                candidates = data.get("candidates", [])
                if candidates and candidates[0].get("content", {}).get("parts"):
                    res = candidates[0]["content"]["parts"][0].get("text", "No analysis returned.")
                    return f"### VISUAL SCOUT REPORT\n{res}"
                return "Vision returned empty analysis."
            elif r.status_code == 404:
                continue
            elif r.status_code == 403:
                return f"Vision API error: Forbidden (403). Check API key permissions for {model}."
            else:
                return f"Vision API error: HTTP {r.status_code} \u2014 {r.text[:200]}"
        except requests.exceptions.Timeout:
            return "Vision analysis timed out after 30s."
        except Exception as e:
            continue

    return f"All vision models failed. Tried: {', '.join(models_to_try)}. Check API key and connectivity."

# ─── DESKTOP AUTOMATION ──────────────────────────────────────────────────

def type_text(text: str) -> str:
    import pyautogui
    pyautogui.write(text)
    return f"Typed: {text}"

def click(x=None, y=None) -> str:
    import pyautogui
    if x is not None and y is not None:
        pyautogui.click(x, y)
        return f"Clicked at ({x}, {y})"
    pyautogui.click()
    return "Clicked at current position"

def double_click(x=None, y=None) -> str:
    import pyautogui
    if x is not None and y is not None:
        pyautogui.doubleClick(x, y)
    else:
        pyautogui.doubleClick()
    return "Double-clicked"

def right_click(x=None, y=None) -> str:
    import pyautogui
    if x is not None and y is not None:
        pyautogui.rightClick(x, y)
    else:
        pyautogui.rightClick()
    return "Right-clicked"

def move_mouse(x, y) -> str:
    import pyautogui
    pyautogui.moveTo(x, y)
    return f"Mouse moved to ({x}, {y})"

def drag(x, y, duration=0.5) -> str:
    import pyautogui
    pyautogui.dragTo(x, y, duration=duration)
    return f"Dragged to ({x}, {y})"

def hotkey(*keys) -> str:
    import pyautogui
    pyautogui.hotkey(*keys)
    return f"Pressed {'+'.join(keys)}"

def press_key(key) -> str:
    import pyautogui
    pyautogui.press(key)
    return f"Pressed {key}"

def scroll(clicks, x=None, y=None) -> str:
    import pyautogui
    pyautogui.scroll(clicks, x=x, y=y)
    return f"Scrolled {clicks} clicks"

# ─── FILE I/O TOOLS ──────────────────────────────────────────────────────

def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_file(path: str, content: str) -> str:
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Written to {path}"

def list_files(directory: str = ".") -> str:
    items = []
    for item in os.listdir(directory):
        full = os.path.join(directory, item)
        tag = "[DIR]" if os.path.isdir(full) else f"[{os.path.getsize(full)} bytes]"
        items.append(f"  {tag} {item}")
    return f"Contents of {directory}:\n" + "\n".join(items)

def find_files(pattern: str, root: str = ".") -> str:
    matches = glob.glob(os.path.join(root, "**", pattern), recursive=True)
    if not matches:
        return f"No files matching '{pattern}' found."
    return f"Found {len(matches)} matches:\n" + "\n".join(f"  {m}" for m in matches[:50])

def copy_file(src: str, dst: str) -> str:
    shutil.copy2(src, dst)
    return f"Copied {src} → {dst}"

def move_file(src: str, dst: str) -> str:
    shutil.move(src, dst)
    return f"Moved {src} → {dst}"

def delete_file(path: str) -> str:
    try:
        from send2trash import send2trash
        send2trash(path)
        return f"Moved {path} to Recycle Bin"
    except Exception:
        os.remove(path)
        return f"Deleted {path}"

# ─── CLIPBOARD ───────────────────────────────────────────────────────────

def clipboard_get() -> str:
    import pyperclip
    return pyperclip.paste()

def clipboard_set(text: str) -> str:
    import pyperclip
    pyperclip.copy(text)
    return f"Copied to clipboard ({len(text)} chars)"

# ─── SYSTEM INFO ─────────────────────────────────────────────────────────

def system_info() -> str:
    import platform
    import psutil
    mem = psutil.virtual_memory()
    return (
        f"OS: {platform.system()} {platform.release()}\n"
        f"CPU: {platform.processor()}\n"
        f"RAM: {mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB ({mem.percent}%)\n"
        f"Python: {platform.python_version()}"
    )

def get_time() -> str:
    return datetime.now().strftime("Date: %A, %B %d, %Y | Time: %I:%M:%S %p")

# ─── SPOTIFY TOOLS ───────────────────────────────────────────────────────

def _get_spotify():
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.environ.get("SPOTIFY_CLIENT_ID", ""),
        client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET", ""),
        redirect_uri=os.environ.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback"),
        scope="user-modify-playback-state user-read-playback-state user-read-currently-playing",
        open_browser=True,
        cache_path=".spotify_cache",
    ))

def spotify_play(query: Optional[str] = None) -> str:
    """Play a track on Spotify. Auto-wakes app if closed."""
    try:
        sp = _get_spotify()
        devices = sp.devices().get("devices", [])
        if not devices:
            open_app("spotify")
            for _ in range(10):
                time.sleep(1)
                devices = sp.devices().get("devices", [])
                if devices:
                    break
            if not devices:
                return "No active Spotify device found. Play something manually once, Boss."
        active_device = next((d for d in devices if d.get("is_active")), devices[0])
        device_id = active_device["id"]
        if not query:
            sp.start_playback(device_id=device_id)
            return f"Resuming playback on {active_device['name']}."
        # Clean query — remove filler words that mess up search
        clean = query.lower().strip()
        for filler in ["play", "the song", "the track", "by", "on spotify", "please"]:
            clean = clean.replace(filler, "")
        clean = clean.strip()
        if not clean:
            clean = query
        # Search specifically for tracks with the exact name
        results = sp.search(q=f'track:{clean}', limit=5, type="track")
        items = results["tracks"]["items"]
        if not items:
            # Fallback to broader search
            results = sp.search(q=clean, limit=5, type="track")
            items = results["tracks"]["items"]
        if not items:
            return f"No track found for '{query}'."
        # Pick best match — prefer exact title match
        best = items[0]
        for item in items:
            if clean.lower() in item["name"].lower():
                best = item
                break
        sp.start_playback(device_id=device_id, uris=[best["uri"]])
        return f"Playing {best['name']} by {best['artists'][0]['name']}."
    except Exception as e:
        return f"Spotify Error: {e}"

def spotify_pause() -> str:
    """Pause Spotify playback."""
    try:
        _get_spotify().pause_playback()
        return "Paused."
    except Exception as e:
        return f"Pause error: {e}"

# ─── CORE / DIAGNOSTIC HELPERS ───────────────────────────────────────────

def climb_codebase(root: str = ".") -> str:
    """Map codebase structure."""
    tree = []
    for r, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in [".git", "__pycache__", "node_modules", "venv", ".venv"]]
        level = r.replace(root, "").count(os.sep)
        tree.append(f"{'    ' * level}{os.path.basename(r)}/")
        for f in files:
            tree.append(f"{'    ' * (level + 1)}{f}")
        if len(tree) > 100:
            break
    return "\n".join(tree)

def situational_awareness() -> str:
    """Active window + CWD snapshot."""
    try:
        import pygetwindow as gw
        active = gw.getActiveWindow()
        return f"### SITUATIONAL REPORT\n- Active Window: {active.title if active else 'Unknown'}\n- CWD: {os.getcwd()}"
    except Exception:
        return "Sensors failing."

def git_ops(command: str, message: Optional[str] = None) -> str:
    """Git operations."""
    try:
        if command == "commit" and message:
            subprocess.run("git add .", shell=True)
            subprocess.run(f'git commit -m "{message}"', shell=True)
            return f"Committed: {message}"
        return subprocess.check_output(f"git {command}", shell=True).decode() or "Done."
    except Exception as e:
        return f"Git Error: {e}"

_LOG_MAX_BYTES = 5 * 1024 * 1024

def stark_log(entry: str) -> str:
    """Log to stark_logs.txt with rotation."""
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stark_logs.txt")
    if os.path.exists(log_path) and os.path.getsize(log_path) > _LOG_MAX_BYTES:
        shutil.move(log_path, log_path.replace(".txt", "_archive.txt"))
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {entry}\n")
    return "Entry logged."

def take_snapshot() -> str:
    """Timestamped screenshot."""
    os.makedirs("snapshots", exist_ok=True)
    path = f"snapshots/recall_{datetime.now().strftime('%H%M%S')}.png"
    try:
        import pyautogui
        pyautogui.screenshot().save(path)
        return f"Snapshot saved: {path}"
    except Exception as e:
        return f"Snapshot failed: {e}"

def recall_snapshot(index=-1) -> str:
    """Recall snapshot filename."""
    if not os.path.exists("snapshots"):
        return "No snapshots."
    snaps = sorted(os.listdir("snapshots"))
    return f"Last snapshot: {snaps[index]}" if snaps else "No snapshots."

# ─── BOOT ────────────────────────────────────────────────────────────────

_ensure_queue_worker()
