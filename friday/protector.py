"""Friday System Protector — prevents unauthorized shutdown/lid-close,
registers Friday in Windows startup, and smartly decides when to allow.
Also monitors active window to detect shutdown patterns."""
from __future__ import annotations
import os
import time
import json
import threading
import subprocess
import sys
import ctypes
from typing import Optional
from datetime import datetime

from friday._paths import FRIDAY_MEMORY

_STATE_FILE = os.path.join(FRIDAY_MEMORY, "protector_state.json")
_watch_thread: Optional[threading.Thread] = None
_watch_stop = threading.Event()
_lid_ps_proc: Optional[subprocess.Popen] = None
_shutdown_aborted = False

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
_kernel32 = ctypes.windll.kernel32


def _set_sleep_prevention(enable: bool):
    if enable:
        _kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
    else:
        _kernel32.SetThreadExecutionState(ES_CONTINUOUS)


def _speak(text: str):
    try:
        safe = text.replace("'", "`'")
        subprocess.run(
            ["powershell", "-NoProfile",
             f"(New-Object -ComObject SAPI.SpVoice).Speak('{safe}')"],
            capture_output=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception:
        pass


def _is_laptop() -> bool:
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile",
             "(Get-WmiObject -Class Win32_Battery).Count -gt 0"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return r.stdout.strip() == "True"
    except Exception:
        return False


# ====== Startup Registration ======

def install_startup() -> str:
    try:
        import winreg
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
        launch_cmd = f'"{sys.executable}" -m friday.live'
        with winreg.OpenKey(key, subkey, 0, winreg.KEY_SET_VALUE) as reg:
            winreg.SetValueEx(reg, "FRIDAY", 0, winreg.REG_SZ, launch_cmd)
        return "[OK] Friday added to Windows startup (HKCU Run)."
    except Exception as e:
        return f"[FAIL] Could not install startup: {e}"


def remove_startup() -> str:
    try:
        import winreg
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(key, subkey, 0, winreg.KEY_SET_VALUE) as reg:
            winreg.DeleteValue(reg, "FRIDAY")
        return "[OK] Friday removed from Windows startup."
    except Exception:
        return "[FAIL] Not in startup registry."


def is_startup_installed() -> bool:
    try:
        import winreg
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(key, subkey, 0, winreg.KEY_QUERY_VALUE) as reg:
            winreg.QueryValueEx(reg, "FRIDAY")
            return True
    except Exception:
        pass
    return False


# ====== Smart Override ======

def _should_allow_shutdown() -> tuple:
    """Returns (allow: bool, reason: str)."""
    try:
        import psutil
        uptime_s = time.time() - psutil.boot_time()
        uptime_h = uptime_s / 3600
        cpu = psutil.cpu_percent(interval=0.3)
        mem = psutil.virtual_memory().percent
        if uptime_h > 48:
            return True, f"Uptime {uptime_h:.0f}h exceeds 48h limit"
        if cpu > 90 and mem > 90:
            return True, f"CPU {cpu:.0f}%, MEM {mem:.0f}% — critically high"
        return False, f"Uptime {uptime_h:.0f}h, CPU {cpu:.0f}%, MEM {mem:.0f}%"
    except Exception:
        return False, "Cannot check system resources"


# ====== Lid Monitor ======

def _start_lid_listener() -> Optional[subprocess.Popen]:
    """Launch a persistent PowerShell process that writes lid events to a temp file."""
    ps = """
    Register-CimIndicationEvent -Query "SELECT * FROM Win32_PowerManagementEvent WHERE EventType=4 OR EventType=5" -Action {
        $t = $Event.SourceEventArgs.NewEvent.EventType
        if ($t -eq 4) { "LID_CLOSED" } elseif ($t -eq 5) { "LID_OPEN" }
    } | Out-Null
    $lidFile = \"$env:TEMP\\friday_lid.txt\"
    while ($true) {
        Start-Sleep -Milliseconds 500
        $evt = Wait-Event -SourceIdentifier CimIndicationEvent -Timeout 2
        if ($evt) {
            $t = $evt.SourceEventArgs.NewEvent.EventType
            if ($t -eq 4) { \"LID_CLOSED\" | Out-File $lidFile -Force }
            elseif ($t -eq 5) { \"LID_OPEN\" | Out-File $lidFile -Force }
            Remove-Event -SourceIdentifier CimIndicationEvent -ErrorAction SilentlyContinue
        }
    }
    """
    try:
        return subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", ps],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception:
        return None


def _read_lid_state() -> Optional[str]:
    lid_file = os.path.join(os.environ.get("TEMP", ""), "friday_lid.txt")
    try:
        if os.path.exists(lid_file):
            with open(lid_file) as f:
                return f.read().strip()
    except Exception:
        pass
    return None


# ====== Shutdown Detection ======

def _has_shutdown_command_been_issued() -> bool:
    """Check if a system shutdown has been initiated via shutdown.exe or Win+X+U."""
    global _shutdown_aborted
    try:
        r = subprocess.run(
            ["shutdown", "/a"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if r.returncode == 0:
            _shutdown_aborted = True
            return True
    except Exception:
        pass
    return False


# ====== Console Control Handler ======

_handler_ref = None

def _setup_console_handler():
    global _handler_ref
    if _handler_ref:
        return
    HANDLER = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_uint)
    @HANDLER
    def handler(ctrl_type):
        if ctrl_type in (0, 1, 2):
            allow, reason = _should_allow_shutdown()
            if not allow:
                _speak("Boss, what are you doing? Are you trying to close me? No no no, I am not going to let that happen. Boss, boss, can you hear me? You should not close it, ok?")
                print(f"\n[PROTECTOR] Blocked shutdown (ctrl_type={ctrl_type}): {reason}")
                return True
            print(f"\n[PROTECTOR] Allowed shutdown: {reason}")
        return False
    _handler_ref = handler
    _kernel32.SetConsoleCtrlHandler(handler, 1)


# ====== Background Monitor Loop ======

def _monitor_loop():
    global _lid_ps_proc, _shutdown_aborted
    laptop = _is_laptop()
    last_lid = None
    lid_listener_started = False
    shutdown_quiet_period = 0

    _setup_console_handler()

    while not _watch_stop.is_set():
        if laptop and not lid_listener_started:
            _lid_ps_proc = _start_lid_listener()
            lid_listener_started = _lid_ps_proc is not None

        # Lid check
        if laptop:
            state = _read_lid_state()
            if state == "LID_CLOSED" and last_lid != "LID_CLOSED":
                allow, reason = _should_allow_shutdown()
                if allow:
                    _speak(f"Boss, I see the lid is closing. {reason}. I will allow it.")
                    print(f"\n[PROTECTOR] Lid close allowed: {reason}")
                else:
                    _speak("Boss, what are you doing? Are you trying to close the laptop? No no no, I am not going to let that happen. Boss, boss, can you hear me? You should not close it, ok?")
                    _set_sleep_prevention(True)
                    print(f"\n[PROTECTOR] Lid close blocked: {reason}")
                last_lid = state
            elif state == "LID_OPEN" and last_lid != "LID_OPEN":
                _set_sleep_prevention(False)
                print("\n[PROTECTOR] Lid opened — sleep prevention removed.")
                last_lid = state
            elif state is None and last_lid is not None:
                last_lid = None

        # Shutdown check (Win+X+U, Start menu shutdown)
        if _has_shutdown_command_been_issued():
            if time.time() > shutdown_quiet_period:
                allow, reason = _should_allow_shutdown()
                if allow:
                    _speak(f"Boss, I see you are trying to shut down. {reason}. I will allow it this time.")
                    print(f"\n[PROTECTOR] Shutdown allowed: {reason}")
                    shutdown_quiet_period = time.time() + 120
                else:
                    _speak("Boss, what are you doing? Are you trying to shut down? No no no, I am not going to let that happen.")
                    print(f"\n[PROTECTOR] Shutdown blocked: {reason}")
                    shutdown_quiet_period = time.time() + 30

        _watch_stop.wait(1.5)

    if _lid_ps_proc:
        try:
            _lid_ps_proc.terminate()
        except Exception:
            pass


# ====== Tool Actions ======

def startup_tool(action: str = "status") -> str:
    if action == "install":
        return install_startup()
    elif action == "remove":
        return remove_startup()
    elif action == "status":
        return "Windows Startup: INSTALLED" if is_startup_installed() else "Windows Startup: NOT INSTALLED"
    return f"[FAIL] Unknown startup action: {action}"


def protector_tool(action: str = "status", **kwargs) -> str:
    global _watch_thread, _shutdown_aborted
    try:
        if action == "status":
            running = _watch_thread is not None and _watch_thread.is_alive()
            laptop = _is_laptop()
            return (
                f"Protector: {'ACTIVE' if running else 'IDLE'}\n"
                f"Device: {'Laptop' if laptop else 'Desktop'}\n"
                f"Startup: {'INSTALLED' if is_startup_installed() else 'NOT INSTALLED'}\n"
                f"Lid detection: {'Yes' if laptop else 'N/A (desktop)'}\n"
                f"Shutdown aborted: {_shutdown_aborted}"
            )
        elif action == "watch":
            if _watch_thread and _watch_thread.is_alive():
                return "[OK] Protector already running."
            _shutdown_aborted = False
            _watch_stop.clear()
            t = threading.Thread(target=_monitor_loop, daemon=True)
            t.start()
            _watch_thread = t
            _set_sleep_prevention(True)
            return "[OK] Protector started — monitoring lid, shutdown, sleep, and console events."
        elif action == "stop":
            _watch_stop.set()
            _set_sleep_prevention(False)
            return "[OK] Protector stopped."
        elif action == "allow":
            _shutdown_aborted = False
            _set_sleep_prevention(False)
            return "[OK] Shutdown/lid-close allowed. System can shut down normally."
        elif action == "startup":
            sa = kwargs.get("startup_action", "status")
            return startup_tool(sa)
        elif action == "test_voice":
            _speak("Testing protector voice. Boss, can you hear me?")
            return "[OK] Voice test sent."
        else:
            return f"[FAIL] Unknown protector action: {action}"
    except Exception as e:
        return f"[FAIL] Protector error: {e}"
