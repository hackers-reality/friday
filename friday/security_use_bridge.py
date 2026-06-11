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
from typing import Any

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
    """Run a coroutine synchronously from a sync context (safe from within an async context too)."""
    try:
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=120)
    except RuntimeError:
        return _run_async(coro)


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
