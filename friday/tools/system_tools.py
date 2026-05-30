"""
System Control tools — Windows
Libraries: pycaw, pyautogui, pynput, pywinauto, keyboard, mouse, psutil,
winsound, win32api/pywin32, winreg, ctypes, comtypes, pygetwindow,
pyscreenshot/mss, pillow, screen-brightness-control
"""
import asyncio
import os
import subprocess
import tempfile
from typing import Any

# ── System Info ──

HAS_PSUTIL = False
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    pass


async def system_info() -> dict[str, Any]:
    if not HAS_PSUTIL:
        return {"error": "psutil not installed"}
    try:
        cpu = await asyncio.get_event_loop().run_in_executor(None, lambda: {
            "percent": psutil.cpu_percent(interval=1),
            "count": psutil.cpu_count(),
            "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
        })
        mem = await asyncio.get_event_loop().run_in_executor(None, lambda: {
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "percent": psutil.virtual_memory().percent
        })
        disk = await asyncio.get_event_loop().run_in_executor(None, lambda: {
            p.mountpoint: {"total": p.total, "used": p.used, "free": p.free, "percent": p.percent}
            for p in psutil.disk_partitions() if os.name == "nt" or p.mountpoint.startswith("/")
        })
        net = await asyncio.get_event_loop().run_in_executor(None, lambda: dict(psutil.net_if_addrs()))
        return {"cpu": cpu, "memory": mem, "disk": disk, "network_interfaces": {k: [{"address": a.address, "family": str(a.family)} for a in v] for k, v in net.items()}}
    except Exception as e:
        return {"error": str(e)}


async def get_processes(sort_by: str = "cpu") -> list[dict[str, Any]]:
    if not HAS_PSUTIL:
        return [{"error": "psutil not installed"}]
    try:
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
            try:
                procs.append(p.info)
            except Exception:
                pass
        procs = sorted(procs, key=lambda x: x.get(sort_by, 0) or 0, reverse=True)[:50]
        return procs
    except Exception as e:
        return [{"error": str(e)}]


async def kill_process(pid: int) -> dict[str, Any]:
    if not HAS_PSUTIL:
        return {"error": "psutil not installed"}
    try:
        p = psutil.Process(pid)
        name = p.name()
        p.terminate()
        return {"status": "terminated", "pid": pid, "name": name}
    except Exception as e:
        return {"error": str(e)}


# ── Windows Registry ──

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False


async def read_registry(key_path: str, value_name: str = "") -> dict[str, Any]:
    if not HAS_WINREG:
        return {"error": "winreg not available (Windows only)"}
    try:
        hive_map = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER,
                    "HKCR": winreg.HKEY_CLASSES_ROOT, "HKU": winreg.HKEY_USERS}
        parts = key_path.split("\\", 1)
        hive = hive_map.get(parts[0], winreg.HKEY_CURRENT_USER)
        subkey = parts[1] if len(parts) > 1 else ""
        key = await asyncio.get_event_loop().run_in_executor(None, lambda: winreg.OpenKey(hive, subkey))
        if value_name:
            val, typ = winreg.QueryValueEx(key, value_name)
            return {"key": key_path, "value": str(val), "type": str(typ)}
        else:
            vals = []
            i = 0
            while True:
                try:
                    n, v, t = winreg.EnumValue(key, i)
                    vals.append({"name": n, "value": str(v)})
                    i += 1
                except OSError:
                    break
            return {"key": key_path, "values": vals}
    except Exception as e:
        return {"error": str(e)}


# ── Windows Sound (winsound) ──

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False


async def play_system_sound(sound: str = "default") -> dict[str, Any]:
    if not HAS_WINSOUND:
        return {"error": "winsound not available (Windows only)"}
    sounds = {"default": winsound.SND_ALIAS, "beep": 0, "asterisk": winsound.MB_ICONASTERISK,
              "exclamation": winsound.MB_ICONEXCLAMATION, "hand": winsound.MB_ICONHAND, "question": winsound.MB_ICONQUESTION}
    flags = sounds.get(sound, winsound.SND_ALIAS)
    try:
        if sound == "beep":
            winsound.Beep(440, 500)
        else:
            winsound.PlaySound(sound, flags)
        return {"played": sound}
    except Exception as e:
        return {"error": str(e)}


# ── Volume Control (pycaw) ──

HAS_PYCAW = False
try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    HAS_PYCAW = True
except ImportError:
    pass


async def get_volume() -> dict[str, Any]:
    if not HAS_PYCAW:
        return {"error": "pycaw not installed"}
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        current = volume.GetMasterVolumeLevelScalar()
        muted = volume.GetMute()
        return {"volume": round(current * 100, 1), "muted": bool(muted)}
    except Exception as e:
        return {"error": str(e)}


async def set_volume(percent: int) -> dict[str, Any]:
    if not HAS_PYCAW:
        return {"error": "pycaw not installed"}
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(max(0.0, min(1.0, percent / 100.0)), None)
        return {"volume": percent}
    except Exception as e:
        return {"error": str(e)}


async def mute_audio(muted: bool = True) -> dict[str, Any]:
    if not HAS_PYCAW:
        return {"error": "pycaw not installed"}
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMute(1 if muted else 0, None)
        return {"muted": muted}
    except Exception as e:
        return {"error": str(e)}


# ── Screen Brightness ──

HAS_BRIGHTNESS = False
try:
    import screen_brightness_control as sbc
    HAS_BRIGHTNESS = True
except ImportError:
    pass


async def get_brightness() -> dict[str, Any]:
    if not HAS_BRIGHTNESS:
        return {"error": "screen-brightness-control not installed"}
    try:
        current = sbc.get_brightness()
        return {"brightness": current}
    except Exception as e:
        return {"error": str(e)}


async def set_brightness(percent: int) -> dict[str, Any]:
    if not HAS_BRIGHTNESS:
        return {"error": "screen-brightness-control not installed"}
    try:
        sbc.set_brightness(max(0, min(100, percent)))
        return {"brightness": percent}
    except Exception as e:
        return {"error": str(e)}


# ── Window Management (pygetwindow) ──

HAS_PYGETWINDOW = False
try:
    import pygetwindow as gw
    HAS_PYGETWINDOW = True
except ImportError:
    pass


async def list_windows() -> dict[str, Any]:
    if not HAS_PYGETWINDOW:
        return {"error": "pygetwindow not installed"}
    try:
        wins = gw.getAllWindows()
        return {"windows": [{"title": w.title, "left": w.left, "top": w.top, "width": w.width, "height": w.height, "active": w.isActive} for w in wins if w.title.strip()]}
    except Exception as e:
        return {"error": str(e)}


async def focus_window(title: str) -> dict[str, Any]:
    if not HAS_PYGETWINDOW:
        return {"error": "pygetwindow not installed"}
    try:
        wins = gw.getWindowsWithText(title)
        if not wins:
            return {"error": f"No window found matching '{title}'"}
        wins[0].activate()
        return {"focused": title}
    except Exception as e:
        return {"error": str(e)}


# ── Screenshot (mss/pyscreenshot/pillow) ──

HAS_MSS = False
try:
    import mss
    HAS_MSS = True
except ImportError:
    pass

HAS_PIL = False
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    pass


async def take_screenshot(monitor: int = 0) -> dict[str, Any]:
    if HAS_MSS:
        try:
            with mss.mss() as sct:
                mon = sct.monitors[monitor] if monitor < len(sct.monitors) else sct.monitors[0]
                sct_img = sct.grab(mon)
                path = os.path.join(tempfile.gettempdir(), "friday_screenshot.png")
                from PIL import Image as PILImage
                img = PILImage.frombytes("RGB", sct_img.size, sct_img.rgb)
                img.save(path)
                return {"path": path, "width": sct_img.size[0], "height": sct_img.size[1], "monitor": monitor}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "mss not installed"}


# ── AutoGUI / Mouse / Keyboard ──

HAS_PYAUTOGUI = False
try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    pass

HAS_KEYBOARD = False
try:
    import keyboard as kb
    HAS_KEYBOARD = True
except ImportError:
    pass

HAS_MOUSE = False
try:
    import mouse as ms
    HAS_MOUSE = True
except ImportError:
    pass


async def mouse_click(x: int | None = None, y: int | None = None, button: str = "left") -> dict[str, Any]:
    if HAS_PYAUTOGUI:
        try:
            if x is not None and y is not None:
                pyautogui.click(x, y, button=button)
            else:
                pyautogui.click(button=button)
            return {"action": "click", "x": x, "y": y, "button": button}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "pyautogui not installed"}


async def mouse_move(x: int, y: int, duration: float = 0.3) -> dict[str, Any]:
    if HAS_PYAUTOGUI:
        try:
            pyautogui.moveTo(x, y, duration=duration)
            return {"action": "move", "x": x, "y": y}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "pyautogui not installed"}


async def type_text_auto(text: str, interval: float = 0.05) -> dict[str, Any]:
    if HAS_PYAUTOGUI:
        try:
            pyautogui.write(text, interval=interval)
            return {"typed": text[:100], "length": len(text)}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "pyautogui not installed"}


async def press_key(key: str) -> dict[str, Any]:
    if HAS_PYAUTOGUI:
        try:
            pyautogui.press(key)
            return {"pressed": key}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "pyautogui not installed"}


async def hotkey(*keys: str) -> dict[str, Any]:
    if HAS_PYAUTOGUI:
        try:
            pyautogui.hotkey(*keys)
            return {"hotkey": "+".join(keys)}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "pyautogui not installed"}


async def get_mouse_position() -> dict[str, Any]:
    if HAS_PYAUTOGUI:
        try:
            x, y = pyautogui.position()
            return {"x": x, "y": y}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "pyautogui not installed"}


async def scroll(clicks: int = 1) -> dict[str, Any]:
    if HAS_PYAUTOGUI:
        try:
            pyautogui.scroll(clicks)
            return {"scrolled": clicks}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "pyautogui not installed"}


async def drag(x: int, y: int, duration: float = 0.3, button: str = "left") -> dict[str, Any]:
    if HAS_PYAUTOGUI:
        try:
            pyautogui.drag(x, y, duration=duration, button=button)
            return {"action": "drag", "x": x, "y": y, "duration": duration}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "pyautogui not installed"}


# ── PyWinAuto ──

HAS_PYWINAUTO = False
try:
    from pywinauto import Application
    HAS_PYWINAUTO = True
except ImportError:
    pass


async def launch_application(app_path: str, params: str = "") -> dict[str, Any]:
    if not HAS_PYWINAUTO:
        return {"error": "pywinauto not installed"}
    try:
        app = Application().start(f"{app_path} {params}".strip())
        return {"launched": app_path, "params": params, "pid": app.process}
    except Exception as e:
        return {"error": str(e)}


async def find_window(title: str) -> dict[str, Any]:
    if not HAS_PYWINAUTO:
        return {"error": "pywinauto not installed"}
    try:
        app = Application().connect(title=title)
        win = app.top_window()
        return {"title": win.window_text(), "visible": win.visible, "enabled": win.enabled}
    except Exception as e:
        return {"error": str(e)}
