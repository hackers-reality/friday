"""
FRIDAY Unified Ecosystem Controller — single interface for smart home, desktop,
browser, media, calendar, system monitoring, and scheduling.

All ecosystem state is persisted at FRIDAY_MEMORY/ecosystem_state.json.
"""

from __future__ import annotations

import json
import os
import re
import socket
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from friday._paths import FRIDAY_MEMORY
from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

_STATE_PATH = os.path.join(FRIDAY_MEMORY, "ecosystem_state.json")

# ── Optional module detection ──────────────────────────────────────────────

HAS_IOT = False
try:
    from friday.iot import SmartHome, SensorSimulator
    HAS_IOT = True
except ImportError:
    pass

HAS_DESKTOP = False
try:
    from friday.desktop_use_bridge import (
        desktop_use_status,
        desktop_list_windows,
        desktop_get_active_window,
        desktop_launch_app,
        desktop_focus_window,
    )
    HAS_DESKTOP = True
except ImportError:
    pass

HAS_BROWSER = False
try:
    from friday.browser_use_bridge import (
        browser_use_status,
        browser_use_navigate,
        browser_use_available,
        browser_use_get_url,
        browser_use_get_title,
    )
    HAS_BROWSER = True
except ImportError:
    pass

HAS_CALENDAR = False
try:
    from friday.google_clients import calendar_list_events, calendar_list_calendars, calendar_create_event
    HAS_CALENDAR = True
except ImportError:
    pass

HAS_SPOTIFY = False
try:
    from friday.tools_flat import spotify_play, spotify_pause, spotify_next, spotify_prev, spotify_volume, spotify_current
    HAS_SPOTIFY = True
except ImportError:
    pass

HAS_SYSTEM_MONITOR = False
try:
    from friday.system_monitor import (
        get_cpu_usage,
        get_memory_usage,
        get_disk_usage,
        get_network_stats,
        get_battery_info,
        get_uptime,
        clean_temp_files,
    )
    HAS_SYSTEM_MONITOR = True
except ImportError:
    pass

HAS_SCHEDULER = False
try:
    from friday.scheduler import add_schedule, _load as load_schedules, _save as save_schedules
    HAS_SCHEDULER = True
except ImportError:
    pass


# ── State persistence ──────────────────────────────────────────────────────

def _load_state() -> dict:
    if os.path.exists(_STATE_PATH):
        try:
            with open(_STATE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"automations": [], "routines": {}, "scheduled_actions": [], "created": datetime.now(timezone.utc).isoformat()}


def _save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
    state["_updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, default=str)


# ── 1. Ecosystem Status ────────────────────────────────────────────────────

def ecosystem_status() -> dict:
    status: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "smart_home": {"available": HAS_IOT, "devices": [], "error": None},
        "desktop": {"available": HAS_DESKTOP, "active_window": None, "error": None},
        "browser": {"available": HAS_BROWSER, "active": False, "url": None, "error": None},
        "calendar": {"available": HAS_CALENDAR, "events_today": [], "error": None},
        "media": {"available": HAS_SPOTIFY, "now_playing": None, "error": None},
        "system_health": {"cpu": None, "memory": None, "disk": None, "uptime": None, "error": None},
    }

    # Smart home devices
    if HAS_IOT:
        try:
            sh = SmartHome()
            devices = sh.list_devices()
            status["smart_home"]["devices"] = devices
            if not devices:
                status["smart_home"]["devices"] = []
        except Exception as e:
            status["smart_home"]["error"] = str(e)
            logger.exception("ecosystem_status: smart_home error")

    # Desktop status
    if HAS_DESKTOP:
        try:
            raw = desktop_get_active_window()
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            status["desktop"]["active_window"] = parsed.get("active_window", parsed.get("error"))
            if "error" in parsed:
                status["desktop"]["error"] = parsed["error"]
        except Exception as e:
            status["desktop"]["error"] = str(e)
            logger.exception("ecosystem_status: desktop error")

    # Browser status
    if HAS_BROWSER:
        try:
            raw = browser_use_status()
            lines = raw.split("\n") if isinstance(raw, str) else []
            for line in lines:
                if "**Browser active**" in line:
                    status["browser"]["active"] = "Yes" in line
                if "**Playwright**" in line:
                    status["browser"]["available"] = "Yes" in line
            try:
                url_raw = browser_use_get_url()
                url_data = json.loads(url_raw) if isinstance(url_raw, str) else url_raw
                status["browser"]["url"] = url_data.get("url", url_data.get("error")) if isinstance(url_data, dict) else str(url_data)
            except Exception:
                pass
        except Exception as e:
            status["browser"]["error"] = str(e)
            logger.exception("ecosystem_status: browser error")

    # Calendar
    if HAS_CALENDAR:
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z")
            events = calendar_list_events(time_min=today, max_results=10)
            status["calendar"]["events_today"] = events
        except Exception as e:
            status["calendar"]["error"] = str(e)
            logger.exception("ecosystem_status: calendar error")

    # Media / Spotify
    if HAS_SPOTIFY:
        try:
            raw = spotify_current()
            status["media"]["now_playing"] = raw
        except Exception as e:
            status["media"]["error"] = str(e)
            logger.exception("ecosystem_status: spotify error")

    # System health
    if HAS_SYSTEM_MONITOR:
        try:
            status["system_health"]["cpu"] = get_cpu_usage()
            status["system_health"]["memory"] = get_memory_usage()
            status["system_health"]["disk"] = get_disk_usage()
            status["system_health"]["uptime"] = get_uptime()
        except Exception as e:
            status["system_health"]["error"] = str(e)
            logger.exception("ecosystem_status: system_monitor error")
    else:
        try:
            import psutil
            status["system_health"]["cpu"] = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            status["system_health"]["memory"] = {
                "total_gb": round(mem.total / (1024 ** 3), 2),
                "used_gb": round(mem.used / (1024 ** 3), 2),
                "percent": mem.percent,
            }
            disk = psutil.disk_usage(os.path.splitdrive(os.getcwd())[0] + "\\")
            status["system_health"]["disk"] = {
                "total_gb": round(disk.total / (1024 ** 3), 2),
                "free_gb": round(disk.free / (1024 ** 3), 2),
                "percent": round(disk.percent, 1),
            }
            boot = psutil.boot_time()
            uptime_s = time.time() - boot
            days = int(uptime_s // 86400)
            hours = int((uptime_s % 86400) // 3600)
            minutes = int((uptime_s % 3600) // 60)
            status["system_health"]["uptime"] = f"{days}d {hours}h {minutes}m"
        except ImportError:
            status["system_health"]["error"] = "psutil not installed"

    return status


# ── 2. Execute Command ─────────────────────────────────────────────────────

def ecosystem_execute(command: str, context: Optional[dict] = None) -> dict:
    cmd_lower = command.lower().strip()
    result: dict[str, Any] = {
        "command": command,
        "parsed_intent": None,
        "action_taken": None,
        "success": False,
        "details": None,
        "error": None,
    }

    # Smart home: turn on/off lights, set thermostat, etc.
    if any(kw in cmd_lower for kw in ["turn on", "turn off", "lights", "thermostat", "lock", "smart home"]):
        if not HAS_IOT:
            result["error"] = "IoT module not available"
            result["parsed_intent"] = "smart_home_control"
            return result
        try:
            sh = SmartHome()
            devices = sh.list_devices()
            target = None
            for dev in devices:
                if dev["name"].lower() in cmd_lower:
                    target = dev["name"]
                    break
            action = "on" if "turn on" in cmd_lower else "off" if "turn off" in cmd_lower else "toggle"
            if target:
                resp = sh.control_device(target, action)
                result["success"] = resp.get("success", False)
                result["details"] = resp
            else:
                if devices:
                    for dev in devices:
                        sh.control_device(dev["name"], action)
                    result["success"] = True
                    result["details"] = {"action": action, "affected": len(devices)}
                else:
                    result["error"] = "No smart home devices found"
            result["parsed_intent"] = "smart_home_control"
            result["action_taken"] = f"{action} -> {target or 'all devices'}"
        except Exception as e:
            result["error"] = str(e)
            logger.exception("ecosystem_execute: smart_home error")
        return result

    # Desktop: open app, focus window, etc.
    if any(kw in cmd_lower for kw in ["open ", "launch ", "focus ", "desktop"]):
        if not HAS_DESKTOP:
            result["error"] = "Desktop module not available"
            result["parsed_intent"] = "desktop_control"
            return result
        try:
            if "open " in cmd_lower or "launch " in cmd_lower:
                app = re.sub(r"^(open|launch)\s+", "", cmd_lower, flags=re.IGNORECASE).strip()
                raw = desktop_launch_app(app)
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                result["success"] = "error" not in parsed
                result["details"] = parsed
                result["action_taken"] = f"launched {app}"
            elif "focus " in cmd_lower:
                title = re.sub(r"^focus\s+", "", cmd_lower, flags=re.IGNORECASE).strip()
                raw = desktop_focus_window(title)
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                result["success"] = "error" not in parsed
                result["details"] = parsed
                result["action_taken"] = f"focus {title}"
            result["parsed_intent"] = "desktop_control"
        except Exception as e:
            result["error"] = str(e)
            logger.exception("ecosystem_execute: desktop error")
        return result

    # Browser
    if any(kw in cmd_lower for kw in ["browser", "navigate to", "go to ", "open website", "search for "]):
        if not HAS_BROWSER:
            result["error"] = "Browser module not available"
            result["parsed_intent"] = "browser_control"
            return result
        try:
            query = re.sub(r"^(browser|navigate to|go to|open website|search for)\s+", "", cmd_lower, flags=re.IGNORECASE).strip()
            raw = browser_use_navigate(query)
            result["success"] = True
            result["details"] = raw
            result["action_taken"] = f"navigated to {query}"
            result["parsed_intent"] = "browser_control"
        except Exception as e:
            result["error"] = str(e)
            logger.exception("ecosystem_execute: browser error")
        return result

    # Media / Music
    if any(kw in cmd_lower for kw in ["play", "music", "spotify", "pause", "next", "skip", "volume"]):
        if not HAS_SPOTIFY:
            result["error"] = "Media module not available"
            result["parsed_intent"] = "media_control"
            return result
        try:
            if "pause" in cmd_lower:
                raw = spotify_pause()
                result["action_taken"] = "pause"
            elif "next" in cmd_lower or "skip" in cmd_lower:
                raw = spotify_next()
                result["action_taken"] = "next"
            elif "volume" in cmd_lower:
                nums = re.findall(r"\d+", cmd_lower)
                level = int(nums[0]) if nums else 50
                raw = spotify_volume(level)
                result["action_taken"] = f"volume {level}"
            elif "play" in cmd_lower:
                query = re.sub(r"^(play|play )", "", cmd_lower, flags=re.IGNORECASE).strip()
                if query in ("music", "spotify", ""):
                    query = ""
                raw = spotify_play(query)
                result["action_taken"] = f"play {query or 'default'}"
            else:
                raw = "[FAIL] Unknown media command"
            result["success"] = "[OK]" in (raw or "")
            result["details"] = raw
            result["parsed_intent"] = "media_control"
        except Exception as e:
            result["error"] = str(e)
            logger.exception("ecosystem_execute: media error")
        return result

    # Calendar / Schedule
    if any(kw in cmd_lower for kw in ["schedule", "calendar", "events", "what's my", "appointments"]):
        if not HAS_CALENDAR:
            result["error"] = "Calendar module not available"
            result["parsed_intent"] = "calendar"
            return result
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z")
            events = calendar_list_events(time_min=today, max_results=20)
            result["success"] = True
            result["details"] = events
            result["action_taken"] = f"retrieved {len(events)} upcoming events"
            result["parsed_intent"] = "calendar"
        except Exception as e:
            result["error"] = str(e)
            logger.exception("ecosystem_execute: calendar error")
        return result

    # System health check
    if any(kw in cmd_lower for kw in ["system health", "system status", "health check", "status", "system info"]):
        result["parsed_intent"] = "system_health"
        health = ecosystem_status()["system_health"]
        result["success"] = True
        result["details"] = health
        result["action_taken"] = "system_health_check"
        return result

    result["error"] = f"Unrecognized command: {command}"
    return result


# ── 3. Schedule Action ─────────────────────────────────────────────────────

def ecosystem_schedule_action(action: str, time: str, repeat: Optional[str] = None) -> dict:
    entry = {
        "id": f"eco_{uuid.uuid4().hex[:8]}",
        "action": action,
        "time": time,
        "repeat": repeat,
        "created": datetime.now(timezone.utc).isoformat(),
        "enabled": True,
        "last_run": None,
        "run_count": 0,
    }

    state = _load_state()
    state.setdefault("scheduled_actions", [])
    state["scheduled_actions"].append(entry)
    _save_state(state)

    if HAS_SCHEDULER:
        try:
            schedule_expr = f"daily at {time}" if not repeat else f"{repeat} at {time}"
            add_schedule(name=entry["id"], schedule=schedule_expr, action=action)
        except Exception as e:
            logger.warning("ecosystem_schedule_action: scheduler registration failed: %s", e)

    return {"success": True, "scheduled_action": entry}


# ── 4. Automation Rules ────────────────────────────────────────────────────

def ecosystem_automation(trigger: str, action: str) -> dict:
    rule = {
        "id": f"auto_{uuid.uuid4().hex[:8]}",
        "trigger": trigger,
        "action": action,
        "created": datetime.now(timezone.utc).isoformat(),
        "enabled": True,
        "trigger_count": 0,
        "last_triggered": None,
    }

    state = _load_state()
    state.setdefault("automations", [])
    state["automations"].append(rule)
    _save_state(state)

    logger.info("Ecosystem automation rule stored: %s -> %s", trigger, action)

    return {"success": True, "rule": rule}


# ── 5. Routines ────────────────────────────────────────────────────────────

def ecosystem_routines(routine_name: str, steps: list[str]) -> dict:
    state = _load_state()
    state.setdefault("routines", {})

    existing = state["routines"].get(routine_name)
    if existing and not steps:
        existing["run_count"] = existing.get("run_count", 0) + 1
        existing["last_run"] = datetime.now(timezone.utc).isoformat()
        _save_state(state)
        results = []
        for step in existing["steps"]:
            res = ecosystem_execute(step)
            results.append({"step": step, "result": res})
        return {"success": True, "routine": routine_name, "execution": results, "cached": True}

    if not steps:
        return {"success": False, "error": f"Routine '{routine_name}' not found and no steps provided to create it"}

    routine = {
        "name": routine_name,
        "steps": steps,
        "created": datetime.now(timezone.utc).isoformat(),
        "last_run": None,
        "run_count": 0,
    }
    state["routines"][routine_name] = routine
    _save_state(state)

    results = []
    for step in steps:
        res = ecosystem_execute(step)
        results.append({"step": step, "result": res})

    routine["last_run"] = datetime.now(timezone.utc).isoformat()
    routine["run_count"] = 1
    _save_state(state)

    return {"success": True, "routine": routine_name, "execution": results}


# ── 6. Ecosystem Context ───────────────────────────────────────────────────

def ecosystem_context() -> dict:
    now = datetime.now(timezone.utc)
    local_now = datetime.now()

    ctx: dict[str, Any] = {
        "timestamp": now.isoformat(),
        "time": {
            "hour": local_now.hour,
            "minute": local_now.minute,
            "day_of_week": local_now.strftime("%A"),
            "day_of_month": local_now.day,
            "month": local_now.month,
            "year": local_now.year,
            "is_weekend": local_now.weekday() >= 5,
            "is_morning": 5 <= local_now.hour < 12,
            "is_afternoon": 12 <= local_now.hour < 17,
            "is_evening": 17 <= local_now.hour < 21,
            "is_night": local_now.hour >= 21 or local_now.hour < 5,
        },
        "active_window": None,
        "recent_notifications": None,
        "system_load": None,
        "network": {"status": "unknown", "ip": None},
        "weather": None,
        "error": None,
    }

    # Active window
    if HAS_DESKTOP:
        try:
            raw = desktop_get_active_window()
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            ctx["active_window"] = parsed.get("active_window", parsed.get("error"))
        except Exception as e:
            logger.debug("ecosystem_context: active_window error: %s", e)

    # System load
    if HAS_SYSTEM_MONITOR:
        try:
            ctx["system_load"] = {
                "cpu": get_cpu_usage(),
                "memory": get_memory_usage(),
                "uptime": get_uptime(),
            }
        except Exception as e:
            logger.debug("ecosystem_context: system_load error: %s", e)
    else:
        try:
            import psutil
            ctx["system_load"] = {
                "cpu": psutil.cpu_percent(interval=0.3),
                "memory": {
                    "total_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
                    "percent": psutil.virtual_memory().percent,
                },
            }
        except ImportError:
            pass

    # Network status
    try:
        host = socket.gethostname()
        ip = socket.gethostbyname(host)
        ctx["network"] = {"status": "connected", "ip": ip, "hostname": host}
    except Exception:
        ctx["network"] = {"status": "unknown", "ip": None}

    # Weather — best-effort via socket-free approach
    try:
        import urllib.request
        import json as _json
        try:
            resp = urllib.request.urlopen(
                "http://wttr.in/?format=%l:+%t+%C+%w+%h",
                timeout=5,
            )
            ctx["weather"] = resp.read().decode("utf-8").strip()
        except Exception:
            pass
    except Exception:
        pass

    return ctx


# ── 7. Ecosystem Discovery ─────────────────────────────────────────────────

def ecosystem_discover() -> dict:
    discovery: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "modules": {
            "iot": HAS_IOT,
            "desktop": HAS_DESKTOP,
            "browser": HAS_BROWSER,
            "calendar": HAS_CALENDAR,
            "spotify": HAS_SPOTIFY,
            "system_monitor": HAS_SYSTEM_MONITOR,
            "scheduler": HAS_SCHEDULER,
        },
        "hardware": {
            "camera": False,
            "microphone": False,
            "speakers": False,
        },
        "services": {
            "spotify_api": False,
            "google_api": False,
            "smart_home": False,
        },
    }

    # Camera
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            discovery["hardware"]["camera"] = True
            cap.release()
    except Exception:
        pass

    # Microphone & Speakers via sounddevice
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        for dev in devices:
            if dev["max_input_channels"] > 0:
                discovery["hardware"]["microphone"] = True
            if dev["max_output_channels"] > 0:
                discovery["hardware"]["speakers"] = True
    except Exception:
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                if info["maxInputChannels"] > 0:
                    discovery["hardware"]["microphone"] = True
                if info["maxOutputChannels"] > 0:
                    discovery["hardware"]["speakers"] = True
            pa.terminate()
        except Exception:
            pass

    # Services: Spotify API
    if HAS_SPOTIFY:
        try:
            from friday.tools_flat import _get_spotify_client
            sp = _get_spotify_client()
            discovery["services"]["spotify_api"] = sp is not None
        except Exception:
            pass

    # Services: Google API
    if HAS_CALENDAR:
        try:
            from friday.google_oauth import get_access_token
            token = get_access_token()
            discovery["services"]["google_api"] = token is not None
        except Exception:
            pass

    # Services: Smart home
    if HAS_IOT:
        try:
            sh = SmartHome()
            discovery["services"]["smart_home"] = len(sh.list_devices()) > 0
        except Exception:
            pass

    # Check what saved routines/automations exist
    state = _load_state()
    discovery["stored"] = {
        "automations": len(state.get("automations", [])),
        "routines": list(state.get("routines", {}).keys()),
        "scheduled_actions": len(state.get("scheduled_actions", [])),
    }

    return discovery
