"""
Friday System Monitor - Real-time system stats and optimization.
Monitor CPU, RAM, disk, network, and auto-optimize.
"""
from __future__ import annotations

import os
import sys
import time
import threading
from typing import Dict, Any, List
from datetime import datetime


# ─── System Stats ────────────────────────────────────#

def get_cpu_usage() -> float:
    """Get CPU usage percentage."""
    try:
        import psutil
        return psutil.cpu_percent(interval=1)
    except ImportError:
        return -1.0


def get_memory_usage() -> Dict[str, Any]:
    """Get memory usage stats."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "percent": mem.percent,
        }
    except ImportError:
        return {"error": "psutil not installed"}
    except Exception as e:
        return {"error": str(e)}


def get_disk_usage(path: str = "") -> Dict[str, Any]:
    """Get disk usage for a path. Defaults to system drive."""
    try:
        if not path:
            path = os.path.splitdrive(os.getcwd())[0] + "\\"
        import psutil
        disk = psutil.disk_usage(path)
        return {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": round(disk.percent, 1),
        }
    except ImportError:
        return {"error": "psutil not installed"}
    except Exception as e:
        return {"error": str(e)}


def get_network_stats() -> Dict[str, Any]:
    """Get network I/O stats."""
    try:
        import psutil
        net = psutil.net_io_counters()
        return {
            "bytes_sent_mb": round(net.bytes_sent / (1024**2), 2),
            "bytes_recv_mb": round(net.bytes_recv / (1024**2), 2),
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
        }
    except ImportError:
        return {"error": "psutil not installed"}
    except Exception as e:
        return {"error": str(e)}


def get_process_list(sort_by: str = "memory", limit: int = 20) -> List[Dict]:
    """Get running processes sorted by cpu or memory."""
    try:
        import psutil
        processes = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = p.info
                processes.append(info)
            except:
                pass
        
        if sort_by == "cpu":
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
        else:
            processes.sort(key=lambda x: x.get('memory_percent', 0), reverse=True)
        
        return processes[:limit]
    except ImportError:
        return [{"error": "psutil not installed"}]
    except Exception as e:
        return [{"error": str(e)}]


def get_battery_info() -> Dict[str, Any]:
    """Get battery status if available."""
    try:
        import psutil
        battery = psutil.sensors_battery()
        if battery:
            return {
                "percent": battery.percent,
                "seconds_left": battery.secsleft,
                "power_plugged": battery.power_plugged,
            }
        return {"status": "No battery detected"}
    except ImportError:
        return {"error": "psutil not installed"}
    except Exception as e:
        return {"error": str(e)}


def get_uptime() -> str:
    """Get system uptime."""
    try:
        import psutil
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        return f"{days}d {hours}h {minutes}m"
    except:
        return "Unknown"


# ─── System Optimization ────────────────────────────────────#

def _get_system_temp() -> str:
    """Get system temp dir dynamically."""
    return os.environ.get("TEMP") or os.environ.get("TMP") or os.path.join(
        os.environ.get("SystemRoot", os.path.splitdrive(os.getcwd())[0] + "\\Windows"), "Temp"
    )


def clean_temp_files() -> str:
    """Clean temporary files."""
    cleaned = 0
    system_temp = _get_system_temp()
    temp_dirs = [
        system_temp,
        os.path.join(os.environ.get("USERPROFILE", ""), "AppData\\Local\\Temp"),
    ]
    
    for temp_dir in temp_dirs:
        if not os.path.exists(temp_dir):
            continue
        try:
            for root, dirs, files in os.walk(temp_dir):
                for f in files:
                    try:
                        os.remove(os.path.join(root, f))
                        cleaned += 1
                    except:
                        pass
                for d in dirs:
                    try:
                        os.rmdir(os.path.join(root, d))
                    except:
                        pass
        except:
            pass
    
    return f"[OK] Cleaned {cleaned} temporary files."


def kill_process_by_name(name: str) -> str:
    """Kill a process by name."""
    try:
        import psutil
        killed = 0
        for p in psutil.process_iter():
            try:
                if name.lower() in p.name().lower():
                    p.kill()
                    killed += 1
            except:
                pass
        return f"[OK] Killed {killed} process(es) matching '{name}'"
    except ImportError:
        return "[FAIL] psutil not installed."
    except Exception as e:
        return f"[FAIL] Error: {e}"


def get_top_resource_hogs() -> str:
    """Get top resource-consuming processes."""
    try:
        processes = get_process_list(sort_by="memory", limit=10)
        if not processes:
            return "No processes found."
        if "error" in processes[0]:
            return f"[FAIL] {processes[0]['error']}"
        
        lines = ["### TOP RESOURCE HOGS", ""]
        for i, p in enumerate(processes, 1):
            lines.append(
                f"{i}. {p.get('name', 'Unknown')} "
                f"(PID: {p.get('pid')}, "
                f"CPU: {p.get('cpu_percent', 0):.1f}%, "
                f"RAM: {p.get('memory_percent', 0):.1f}%)"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"[FAIL] Error: {e}"


# ─── Full System Report ────────────────────────────────────#

def system_report() -> str:
    """Generate a full system report."""
    lines = ["### FRIDAY SYSTEM MONITOR", ""]
    lines.append(f"**Timestamp**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Uptime**: {get_uptime()}")
    lines.append("")
    
    # CPU
    cpu = get_cpu_usage()
    if cpu >= 0:
        lines.append(f"**CPU Usage**: {cpu:.1f}%")
    
    # Memory
    mem = get_memory_usage()
    if "error" not in mem:
        lines.append(f"**Memory**: {mem['used_gb']}GB / {mem['total_gb']}GB ({mem['percent']}%)")
    
    # Disk
    disk = get_disk_usage("C:\\")
    if "error" not in disk:
        lines.append(f"**Disk C:** {disk['used_gb']}GB / {disk['total_gb']}GB ({disk['percent']}%)")
    
    # Network
    net = get_network_stats()
    if "error" not in net:
        lines.append(f"**Network**: ↓ {net['bytes_recv_mb']}MB | ↑ {net['bytes_sent_mb']}MB")
    
    # Battery
    battery = get_battery_info()
    if "error" not in battery and "percent" in battery:
        lines.append(f"**Battery**: {battery['percent']}% ({'Plugged' if battery['power_plugged'] else 'On Battery'})")
    
    lines.append("")
    lines.append(get_top_resource_hogs())
    
    return "\n".join(lines)


# ─── Tool Function for Friday ────────────────────────────────────#

def system_monitor_tool(
    action: str = "report",
    target: str = None,
    value: float = None,
) -> str:
    """
    Friday tool for system monitoring and optimization.
    Actions: report, cpu, memory, disk, network, processes, battery, cleanup, kill
    """
    if action == "report":
        return system_report()
    
    if action == "cpu":
        cpu = get_cpu_usage()
        return f"CPU Usage: {cpu:.1f}%" if cpu >= 0 else "[FAIL] Could not get CPU usage."
    
    if action == "memory":
        mem = get_memory_usage()
        if "error" in mem:
            return f"[FAIL] {mem['error']}"
        return f"Memory: {mem['used_gb']}GB / {mem['total_gb']}GB ({mem['percent']}%)"
    
    if action == "disk":
        disk = get_disk_usage(target or "C:\\")
        if "error" in disk:
            return f"[FAIL] {disk['error']}"
        return f"Disk: {disk['used_gb']}GB / {disk['total_gb']}GB ({disk['percent']}%)"
    
    if action == "network":
        net = get_network_stats()
        if "error" in net:
            return f"[FAIL] {net['error']}"
        return f"Network: ↓ {net['bytes_recv_mb']}MB | ↑ {net['bytes_sent_mb']}MB"
    
    if action == "processes":
        return get_top_resource_hogs()
    
    if action == "battery":
        battery = get_battery_info()
        if "error" in battery:
            return f"[FAIL] {battery['error']}"
        if "status" in battery:
            return battery["status"]
        return f"Battery: {battery['percent']}%"
    
    if action == "cleanup":
        return clean_temp_files()
    
    if action == "kill":
        if not target:
            return "[FAIL] Process name required for kill action."
        return kill_process_by_name(target)
    
    if action == "uptime":
        return f"System Uptime: {get_uptime()}"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing System Monitor...\n")
    
    print(system_report())
    
    print("\n--- Top Processes ---")
    print(get_top_resource_hogs())
