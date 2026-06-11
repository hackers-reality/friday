"""
FRIDAY Security-Use Bridge — unified security & pen-testing toolkit.
Parallel to desktop_use_bridge.py but for network recon, crypto, WiFi, DNS, OSINT.

Wraps existing tool modules (wifi_tools, security_tools, dns_tool,
osint_advanced_tools) into sync functions returning JSON strings.

Categories:
  - WiFi & Network (sync, no extra deps)
  - Encryption & Hashing (async -> asyncio.run)
  - DNS Reconnaissance (async -> asyncio.run)
  - Port Scanning / Network Scan (async -> asyncio.run)
  - OSINT & Threat Intel (async -> asyncio.run)
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

from friday._paths import FRIDAY_MEMORY
from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

_STATE_PATH = os.path.join(FRIDAY_MEMORY, "security_use_state.json")
_HISTORY_PATH = os.path.join(FRIDAY_MEMORY, "security_use_history.jsonl")


def _load_state() -> dict:
    if os.path.exists(_STATE_PATH):
        try:
            with open(_STATE_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"queries": 0, "last_category": ""}


def _save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
    with open(_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def _log_history(entry: dict) -> None:
    os.makedirs(os.path.dirname(_HISTORY_PATH), exist_ok=True)
    with open(_HISTORY_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _record_action(category: str, action: str, status: str = "ok") -> None:
    state = _load_state()
    state["queries"] += 1
    state["last_category"] = category
    _save_state(state)
    _log_history({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "category": category,
        "action": action,
        "status": status,
    })


def _run_async(coro) -> Any:
    """Run a coroutine synchronously. Works in both sync and async contexts."""
    try:
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=120)
    except RuntimeError:
        return asyncio.run(coro)


# ═══════════════════════════════════════════════════════════════════
# 1. STATUS
# ═══════════════════════════════════════════════════════════════════

def security_use_status() -> str:
    state = _load_state()
    import importlib
    tools = {}
    for mod_name in ("wifi_tools", "dns_tool", "security_tools", "osint_advanced_tools"):
        try:
            mod = importlib.import_module(f"friday.tools.{mod_name}")
            tools[mod_name] = True
        except Exception:
            tools[mod_name] = False
    return json.dumps({
        "available": any(tools.values()),
        "backends": tools,
        "total_queries": state["queries"],
        "shodan_key": bool(os.environ.get("SHODAN_API_KEY")),
        "msfrpc_host": os.environ.get("MSF_HOST", "not configured"),
    }, indent=2)


# ═══════════════════════════════════════════════════════════════════
# 2. WIFI & NETWORK (sync)
# ═══════════════════════════════════════════════════════════════════

def wifi_list_profiles() -> str:
    try:
        from friday.tools.wifi_tools import wifi_list_profiles as _impl
        r = _impl()
        _record_action("wifi", "list_profiles")
        return json.dumps({"profiles": r, "count": len(r)}, indent=2)
    except Exception as e:
        logger.exception("wifi_list_profiles failed")
        return json.dumps({"error": str(e)})


def wifi_show_password(ssid: str) -> str:
    try:
        from friday.tools.wifi_tools import wifi_show_password as _impl
        r = _impl(ssid)
        _record_action("wifi", "show_password", "ok" if r.get("password") else "admin_needed")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def wifi_scan() -> str:
    try:
        from friday.tools.wifi_tools import wifi_scan as _impl
        r = _impl()
        _record_action("wifi", "scan")
        return json.dumps({"networks": r, "count": len(r)}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def wifi_connection_status() -> str:
    try:
        from friday.tools.wifi_tools import wifi_connection_status as _impl
        r = _impl()
        _record_action("wifi", "connection_status")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def wifi_interface_status(interface: str = "Wi-Fi") -> str:
    try:
        from friday.tools.wifi_tools import wifi_interface_status as _impl
        r = _impl(interface)
        _record_action("wifi", "interface_status")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def wifi_all_interfaces_status() -> str:
    try:
        from friday.tools.wifi_tools import wifi_all_interfaces_status as _impl
        r = _impl()
        _record_action("wifi", "all_interfaces")
        return json.dumps({"interfaces": r, "count": len(r)}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def wifi_crack(ssid: str, wordlist: Optional[list[str]] = None, timeout_per_attempt: int = 8) -> str:
    try:
        from friday.tools.wifi_tools import wifi_crack as _impl
        r = _impl(ssid, wordlist, timeout_per_attempt)
        _record_action("wifi", "crack")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def network_connections() -> str:
    try:
        from friday.tools.wifi_tools import network_connections as _impl
        r = _impl()
        _record_action("network", "connections")
        return json.dumps({"connections": r[:50], "count": len(r)}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def arp_table() -> str:
    try:
        from friday.tools.wifi_tools import arp_table as _impl
        r = _impl()
        _record_action("network", "arp_table")
        return json.dumps({"entries": r, "count": len(r)}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def traceroute(target: str, max_hops: int = 30) -> str:
    try:
        from friday.tools.wifi_tools import traceroute as _impl
        r = _impl(target, max_hops)
        _record_action("network", "traceroute")
        return json.dumps({"hops": r, "count": len(r), "target": target}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "target": target})


# ═══════════════════════════════════════════════════════════════════
# 3. ENCRYPTION & HASHING (async -> sync)
# ═══════════════════════════════════════════════════════════════════

def encrypt_text(plaintext: str, key: str) -> str:
    try:
        from friday.tools.security_tools import encrypt_text as _impl
        r = _run_async(_impl(plaintext, key))
        _record_action("crypto", "encrypt")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def decrypt_text(ciphertext: str, key: str) -> str:
    try:
        from friday.tools.security_tools import decrypt_text as _impl
        r = _run_async(_impl(ciphertext, key))
        _record_action("crypto", "decrypt")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def hash_text(text: str, algorithm: str = "sha256") -> str:
    try:
        from friday.tools.security_tools import hash_text as _impl
        r = _run_async(_impl(text, algorithm))
        _record_action("crypto", "hash")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def generate_fernet_key() -> str:
    try:
        from friday.tools.security_tools import generate_fernet_key as _impl
        r = _run_async(_impl())
        _record_action("crypto", "generate_fernet_key")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def generate_rsa_keypair(key_size: int = 2048) -> str:
    try:
        from friday.tools.security_tools import generate_rsa_keypair as _impl
        r = _run_async(_impl(key_size))
        _record_action("crypto", "generate_rsa_keypair")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# 4. DNS RECONNAISSANCE (async -> sync)
# ═══════════════════════════════════════════════════════════════════

def dns_lookup(domain: str, record_types: str = "A,AAAA,MX,NS,TXT") -> str:
    try:
        from friday.tools.dns_tool import dns_lookup as _impl
        types = [t.strip() for t in record_types.split(",")]
        r = _run_async(_impl(domain, types))
        _record_action("dns", "lookup")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "domain": domain})


def dns_reverse_lookup(ip: str) -> str:
    try:
        from friday.tools.dns_tool import dns_reverse_lookup as _impl
        r = _run_async(_impl(ip))
        _record_action("dns", "reverse_lookup")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "ip": ip})


def dns_mx_lookup(domain: str) -> str:
    try:
        from friday.tools.dns_tool import dns_mx_lookup as _impl
        r = _run_async(_impl(domain))
        _record_action("dns", "mx_lookup")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "domain": domain})


def dns_enumeration(domain: str, aggressive: bool = False) -> str:
    try:
        from friday.tools.dns_tool import dns_enumeration as _impl
        r = _run_async(_impl(domain, aggressive))
        _record_action("dns", "enumeration")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "domain": domain})


# ═══════════════════════════════════════════════════════════════════
# 5. PORT SCANNING & NETWORK RECON (async -> sync)
# ═══════════════════════════════════════════════════════════════════

def port_scan(host: str, ports: str | None = None) -> str:
    try:
        from friday.tools.osint_advanced_tools import port_scan as _impl
        port_list: list[int] | None = None
        if ports:
            port_list = [int(p.strip()) for p in ports.split(",") if p.strip().isdigit()]
        r = _run_async(_impl(host, port_list))
        _record_action("scan", "port_scan")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "host": host})


def ping_host(host: str, count: int = 3) -> str:
    try:
        from friday.tools.osint_advanced_tools import ping_host as _impl
        r = _run_async(_impl(host, count))
        _record_action("scan", "ping")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "host": host})


def ssl_certificate_check(hostname: str, port: int = 443) -> str:
    try:
        from friday.tools.osint_advanced_tools import ssl_certificate_check as _impl
        r = _run_async(_impl(hostname, port))
        _record_action("scan", "ssl_cert")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "hostname": hostname})


# ═══════════════════════════════════════════════════════════════════
# 6. OSINT & THREAT INTEL (async -> sync)
# ═══════════════════════════════════════════════════════════════════

def shodan_search(query: str, limit: int = 10) -> str:
    try:
        from friday.tools.osint_advanced_tools import shodan_search as _impl
        r = _run_async(_impl(query, limit))
        _record_action("osint", "shodan_search")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "query": query})


def shodan_host(ip: str) -> str:
    try:
        from friday.tools.osint_advanced_tools import shodan_host as _impl
        r = _run_async(_impl(ip))
        _record_action("osint", "shodan_host")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "ip": ip})


def shodan_search_count(query: str) -> str:
    try:
        from friday.tools.osint_advanced_tools import shodan_search_count as _impl
        r = _run_async(_impl(query))
        _record_action("osint", "shodan_search_count")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def whois_lookup(domain: str) -> str:
    try:
        from friday.tools.osint_advanced_tools import whois_lookup as _impl
        r = _run_async(_impl(domain))
        _record_action("osint", "whois")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "domain": domain})


def geoip_lookup(ip: str) -> str:
    try:
        from friday.tools.osint_advanced_tools import geoip_lookup as _impl
        r = _run_async(_impl(ip))
        _record_action("osint", "geoip")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "ip": ip})


def shodan_ports(ip: str) -> str:
    try:
        from friday.tools.osint_advanced_tools import shodan_ports as _impl
        r = _run_async(_impl(ip))
        _record_action("osint", "shodan_ports")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "ip": ip})


def hibp_breach_check(email: str) -> str:
    try:
        from friday.tools.osint_advanced_tools import hibp_breach_check as _impl
        r = _run_async(_impl(email))
        _record_action("osint", "hibp")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "email": email})


# ═══════════════════════════════════════════════════════════════════
# 7. ADVANCED WIFI TOOLS (smart wordlist, handshake, deauth)
# ═══════════════════════════════════════════════════════════════════

def generate_smart_wordlist(ssid: str, hints: Optional[list[str]] = None, max_words: int = 10000) -> str:
    try:
        from friday.tools.wifi_advanced_tools import generate_smart_wordlist as _impl
        r = _impl(ssid, hints, max_words)
        _record_action("wifi", "smart_wordlist")
        return json.dumps({"ssid": ssid, "wordlist": r, "count": len(r)}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def wifi_smart_crack(ssid: str, wordlist: Optional[list[str]] = None, max_passwords: int = 100000) -> str:
    try:
        from friday.tools.wifi_advanced_tools import wifi_smart_crack as _impl
        r = _impl(ssid, wordlist, max_passwords)
        _record_action("wifi", "smart_crack")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def wifi_capture_handshake(ssid: str, interface: str = "Wi-Fi", timeout: int = 60) -> str:
    try:
        from friday.tools.wifi_advanced_tools import wifi_capture_handshake as _impl
        r = _impl(ssid, interface, timeout)
        _record_action("wifi", "capture_handshake")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def wifi_crack_handshake(cap_file: str, wordlist_file: str = "rockyou.txt") -> str:
    try:
        from friday.tools.wifi_advanced_tools import wifi_crack_handshake as _impl
        r = _impl(cap_file, wordlist_file)
        _record_action("wifi", "crack_handshake")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def download_wordlist(url: Optional[str] = None) -> str:
    try:
        from friday.tools.wifi_advanced_tools import download_wordlist as _impl
        r = _impl(url)
        _record_action("wifi", "download_wordlist")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def wordlist_stats(wordlist_path: str = "rockyou.txt") -> str:
    try:
        from friday.tools.wifi_advanced_tools import wordlist_stats as _impl
        r = _impl(wordlist_path)
        _record_action("wifi", "wordlist_stats")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def wifi_detect_deauth(interface: str = "Wi-Fi", timeout: int = 30) -> str:
    try:
        from friday.tools.wifi_advanced_tools import wifi_detect_deauth as _impl
        r = _impl(interface, timeout)
        _record_action("wifi", "detect_deauth")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# 8. MSF AUTO TOOLS (metasploit auto-install, auto-pwn, etc.)
# ═══════════════════════════════════════════════════════════════════

def msf_auto_install() -> str:
    try:
        from friday.tools.msf_auto_tools import msf_auto_install as _impl
        r = _impl()
        _record_action("metasploit", "auto_install")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def msf_ensure_rpc(host: str = "127.0.0.1", port: int = 55553, password: str = "msf") -> str:
    try:
        from friday.tools.msf_auto_tools import msf_ensure_rpc as _impl
        r = _impl(host, port, password)
        _record_action("metasploit", "ensure_rpc")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def msf_quick_scan(target: str, ports: str = "1-1000") -> str:
    try:
        from friday.tools.msf_auto_tools import msf_quick_scan as _impl
        r = _run_async(_impl(target, ports))
        _record_action("metasploit", "quick_scan")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def msf_find_exploits(target: str, port: int, service: str = "") -> str:
    try:
        from friday.tools.msf_auto_tools import msf_find_exploits as _impl
        r = _run_async(_impl(target, port, service))
        _record_action("metasploit", "find_exploits")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def msf_auto_exploit(target: str, module_path: str, options: dict = None, payload: Optional[str] = None) -> str:
    try:
        from friday.tools.msf_auto_tools import msf_auto_exploit as _impl
        r = _run_async(_impl(target, module_path, options or {}, payload))
        _record_action("metasploit", "auto_exploit")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def msf_auto_pwn(target_ip: str, target_port: Optional[int] = None) -> str:
    try:
        from friday.tools.msf_auto_tools import msf_auto_pwn as _impl
        r = _run_async(_impl(target_ip, target_port))
        _record_action("metasploit", "auto_pwn")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def msf_exploit_eternalblue(target: str, lhost: str = "127.0.0.1", lport: int = 4444) -> str:
    try:
        from friday.tools.msf_auto_tools import msf_exploit_eternalblue as _impl
        r = _run_async(_impl(target, lhost, lport))
        _record_action("metasploit", "exploit_eternalblue")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# 9. PENTESTING AGENT TOOLS
# ═══════════════════════════════════════════════════════════════════

def pentest_scan_target(target: str, ports: Optional[list[int]] = None) -> str:
    try:
        from friday.pentesting_agent import pentest_scan_target as _impl
        r = _impl(target, ports)
        _record_action("pentest", "scan_target")
        return json.dumps(r, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def pentest_enumerate(target: str, service: str, port: int) -> str:
    try:
        from friday.pentesting_agent import pentest_enumerate as _impl
        r = _impl(target, service, port)
        _record_action("pentest", "enumerate")
        return json.dumps(r, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def pentest_exploit(target: str, service: str, port: int) -> str:
    try:
        from friday.pentesting_agent import pentest_exploit as _impl
        r = _impl(target, service, port)
        _record_action("pentest", "exploit")
        return json.dumps(r, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def pentest_full_chain(target: str) -> str:
    try:
        from friday.pentesting_agent import pentest_full_chain as _impl
        r = _impl(target)
        _record_action("pentest", "full_chain")
        return json.dumps(r, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def pentest_generate_report(target: str) -> str:
    try:
        from friday.pentesting_agent import pentest_generate_report as _impl
        r = _impl(target)
        _record_action("pentest", "generate_report")
        return r
    except Exception as e:
        return json.dumps({"error": str(e)})


def pentest_tools_check() -> str:
    try:
        from friday.pentesting_agent import pentest_tools_check as _impl
        r = _impl()
        _record_action("pentest", "tools_check")
        return json.dumps(r, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def pentest_wifi_assessment(ssid: str) -> str:
    try:
        from friday.pentesting_agent import pentest_wifi_assessment as _impl
        r = _impl(ssid)
        _record_action("pentest", "wifi_assessment")
        return json.dumps(r, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def pentest_plan(target: str, assessment_type: str = "full") -> str:
    try:
        from friday.pentesting_agent import pentest_plan as _impl
        r = _impl(target, assessment_type)
        _record_action("pentest", "plan")
        return r
    except Exception as e:
        return json.dumps({"error": str(e)})
