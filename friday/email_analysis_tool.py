"""
FRIDAY Email Intelligence & Forensics Toolkit — "Behind the Email" API

Full email analysis pipeline covering header analysis, SPF/DKIM/DMARC/BIMI/ARC
validation, security scoring, forensic investigation, reputation checks, and
email verification.

All I/O-bound functions are async.  Every public function returns a structured
dict and handles exceptions internally.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import csv
import email
import email.header
import email.message
import email.parser
import email.policy
import email.utils
import hashlib
import io
import ipaddress
import json
import logging
import math
import os
import re
import socket
import ssl
import struct
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict, OrderedDict
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse, urljoin
from zipfile import ZipFile

logger = logging.getLogger(__name__)

HAS_DNSPYTHON = False
try:
    import dns.resolver
    import dns.exception
    import dns.rdatatype
    import dns.asyncresolver
    import dns.name
    import dns.reversename
    HAS_DNSPYTHON = True
except ImportError:
    pass

HAS_HTTPX = False
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    pass

HAS_AIODNS = False
try:
    import aiodns
    HAS_AIODNS = True
except ImportError:
    pass

HAS_WHOIS = False
try:
    import whois
    HAS_WHOIS = True
except ImportError:
    pass

DEFAULT_TIMEOUT = 10.0
MAX_DNS_LOOKUPS = 10

COMMON_DKIM_SELECTORS = [
    "default", "dkim", "google", "selector1", "selector2",
    "mx", "mail", "email", "k1", "s1", "s2", "pk", "protonmail",
    "outlook", "office365", "zoho", "sendgrid", "mandrill",
    "sparkpost", "mailgun", "postmark", "amazonses", "ses",
    "dkim._domainkey", "smtp", "mta", "relay", "edge",
]

DISPOSABLE_DOMAINS = set()

ROLE_PREFIXES = [
    "admin", "administrator", "info", "contact", "support",
    "help", "sales", "marketing", "billing", "accounts",
    "noreply", "no-reply", "donotreply", "do-not-reply",
    "postmaster", "hostmaster", "webmaster", "abuse",
    "security", "privacy", "spam", "mailer-daemon",
    "mailer", "daemon", "null", "root", "sysadmin",
    "service", "services", "team", "office", "hr",
    "jobs", "recruitment", "careers", "press", "media",
    "investor", "investors", "ir", "legal", "compliance",
    "partner", "partners", "feedback", "survey", "newsletter",
    "notifications", "notification", "register", "invite",
]

COMMON_TYPOS = {
    "gmail.com": ["gmial.com", "gmil.com", "gmail.co", "gmail.cm",
                  "gmaill.com", "gmal.com", "gamil.com", "gnail.com",
                  "gmai.com", "gmali.com", "gmaik.com", "gmakl.com",
                  "gmailll.com", "gmail.com.com", "gmaill.co"],
    "yahoo.com": ["yaho.com", "yahooo.com", "yahho.com", "yaoo.com",
                  "yhaoo.com", "yahoo.co", "yahoo.cm", "yahoom.com",
                  "yqhoo.com", "yahu.com"],
    "outlook.com": ["outlok.com", "outloo.com", "outloook.com",
                    "outllook.com", "outlook.co", "outlook.cm"],
    "hotmail.com": ["hotmal.com", "hotmai.com", "hotmaiil.com",
                    "hotmil.com", "hotmail.co", "hotmail.cm",
                    "hhotmail.com", "htomail.com"],
    "icloud.com": ["icloud.co", "iclod.com", "icloud.cm", "icoud.com",
                   "iclloud.com"],
    "live.com": ["live.co", "liv.com", "live.cm", "lve.com"],
    "msn.com": ["msn.co", "msnn.com", "msm.com"],
    "aol.com": ["aol.co", "aoll.com", "aol.cm", "al.com"],
    "protonmail.com": ["protnmail.com", "protonmai.com", "protonmil.com",
                       "protonail.com", "protonmail.co"],
    "zoho.com": ["zohoo.com", "zoho.co", "zohomail.com"],
    "yandex.com": ["yandex.co", "yandx.com", "yandeks.com"],
    "gmx.com": ["gmx.co", "gmx.cm", "gmx.net"],
}

KNOWN_DISPOSABLE_DOMAINS = [
    "10minutemail.com", "trashmail.com", "mailinator.com",
    "guerrillamail.com", "sharklasers.com", "temp-mail.org",
    "throwaway.email", "tempmail.com", "emails.by",
    "yopmail.com", "discard.email", "spambog.com",
    "maildrop.cc", "getairmail.com", "emailondeck.com",
    "fakeinbox.com", "tempinbox.com", "mailnator.com",
    "mintemail.com", "spamgourmet.com", "mailexpire.com",
    "safe-mail.net", "anonymail.net", "anonymousemail.me",
    "jetable.org", "spamdecoy.net", "dispostable.com",
    "mailcatch.com", "tempail.com", "eyepaste.com",
    "mytempemail.com", "pookmail.com", "maileater.com",
    "quickinbox.com", "sneakemail.com", "sofort-mail.de",
    "spam.la", "spamcon.org", "thankyou2010.com",
    "trash2009.com", "trashymail.com", "tyldd.com",
    "uggsrock.com", "wegwerfmail.de", "wh4f.org",
    "wuzup.net", "xagloo.com", "xoxy.net", "z1p.biz",
    "zippymail.info", "zzz.com", "zero-mail.com",
    "fakemailgenerator.com", "mailexperts24.com",
    "mailmetrash.com", "mymogil.com", "nepwk.com",
    "mailsac.com", "mail-temp.com", "temp-mail.net",
    "tempemail.net", "harakirimail.com", "filzmail.com",
    "brefmail.com", "kasmail.com", "mailmetrash.com",
    "rcpt.at", "trash2009.com", "trashymail.net",
    "weg-werf-mail.de", "wegwerfmail.net", "wehshee.com",
    "whyspam.me", "willselfdestruct.com", "winemaven.info",
]

KNOWN_ROLE_ACCOUNTS = [
    "admin", "administrator", "info", "contact", "support",
    "help", "sales", "marketing", "billing", "accounts",
    "noreply", "no-reply", "donotreply", "do-not-reply",
    "postmaster", "hostmaster", "webmaster", "abuse",
    "security", "privacy", "spam", "mailer-daemon",
    "root", "sysadmin", "service", "services", "team",
    "office", "hr", "jobs", "careers", "press", "media",
    "investor", "investors", "ir", "legal", "compliance",
    "partner", "partners", "feedback", "survey",
]


def _extract_domain(email_addr: str) -> str:
    if not email_addr or "@" not in email_addr:
        return ""
    return email_addr.rsplit("@", 1)[-1].strip().lower()


def _parse_email_addr(raw: str) -> dict:
    name, addr = email.utils.parseaddr(raw)
    return {
        "name": name,
        "address": addr,
        "domain": _extract_domain(addr),
        "raw": raw.strip(),
    }


def _decode_mime_header(value: str) -> str:
    if not value:
        return ""
    decoded_parts = []
    for part, encoding in email.header.decode_header(value):
        if isinstance(part, bytes):
            try:
                decoded_parts.append(part.decode(encoding or "utf-8", errors="replace"))
            except (LookupError, UnicodeDecodeError):
                decoded_parts.append(part.decode("utf-8", errors="replace"))
        else:
            decoded_parts.append(part)
    return " ".join(decoded_parts)


def _parse_date_header(value: str) -> dict:
    if not value:
        return {"raw": "", "parsed": None, "utc": None, "valid": False}
    parsed = email.utils.parsedate_to_datetime(value)
    if parsed and parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return {
        "raw": value,
        "parsed": parsed.isoformat() if parsed else None,
        "utc": parsed.isoformat() if parsed else None,
        "valid": parsed is not None,
    }


def _safe_decode_bytes(data: bytes) -> str:
    for enc in ("utf-8", "latin-1", "cp1252", "iso-8859-1", "ascii"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return data.decode("utf-8", errors="replace")


def _is_ip_private(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
        return addr.is_private
    except ValueError:
        return False


def _is_ip_reserved(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
        return addr.is_reserved or addr.is_loopback or addr.is_link_local
    except ValueError:
        return False


def _extract_ip_port(host_str: str) -> tuple:
    host_str = host_str.strip().strip("[]")
    if "]" in host_str:
        parts = host_str.split("]")
        ip = parts[0].strip().lstrip("[")
        port = parts[1].strip().lstrip(":") if len(parts) > 1 else ""
        return ip, port
    if ":" in host_str and host_str.count(":") == 1:
        parts = host_str.split(":")
        return parts[0].strip(), parts[1].strip()
    return host_str, ""


def _parse_received_line(line: str) -> dict:
    entry = {
        "raw": line,
        "from": None, "by": None, "with": None,
        "id": None, "for": None, "timestamp": None,
        "ip": None, "hostname": None, "helo": None,
        "tls": None, "spf": None, "cipher": None,
        "protocol": None,
    }
    line = _decode_mime_header(line)
    m = re.search(r"from\s+(\S+(?:\s+\(.*?\))?)\s*", line, re.I)
    if m:
        from_part = m.group(1)
        entry["from"] = from_part
        ip_m = re.search(r"\[(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:\.\d+)?)\]", from_part)
        if ip_m:
            entry["ip"] = ip_m.group(1)
        ipv6_m = re.search(r"\[IPv6:([^\]]+)\]", from_part)
        if ipv6_m:
            entry["ip"] = ipv6_m.group(1)
        host_m = re.search(r"^(\S+)\s+\[", from_part)
        if host_m:
            entry["hostname"] = host_m.group(1)
    m = re.search(r"by\s+(\S+(?:\s+\(.*?\))?)\s*", line, re.I)
    if m:
        entry["by"] = m.group(1)
    m = re.search(r"with\s+(\S+)", line, re.I)
    if m:
        entry["protocol"] = m.group(1)
        entry["with"] = m.group(1)
    m = re.search(r"id\s+(\S+)", line, re.I)
    if m:
        entry["id"] = m.group(1)
    m = re.search(r"for\s+<([^>]+)>", line, re.I)
    if m:
        entry["for"] = m.group(1)
    m = re.search(r";\s*(.+)$", line, re.I)
    if m:
        ts_str = m.group(1).strip()
        entry["timestamp"] = ts_str
        try:
            parsed = email.utils.parsedate_to_datetime(ts_str)
            if parsed:
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                entry["timestamp_parsed"] = parsed.isoformat()
        except Exception:
            pass
    if re.search(r"TLS\s", line, re.I):
        entry["tls"] = True
        cipher_m = re.search(r"cipher\s*=\s*(\S+)", line, re.I)
        if cipher_m:
            entry["cipher"] = cipher_m.group(1)
    else:
        entry["tls"] = False
    spf_m = re.search(r"spf=(\S+)", line, re.I)
    if spf_m:
        entry["spf"] = spf_m.group(1)
    return entry


def _parse_authentication_results_field(value: str) -> list:
    results = []
    if not value:
        return results
    parts = value.split(";")
    auth_serv_id = None
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if auth_serv_id is None:
            auth_serv_id = part.split()[0] if " " in part else part
            spf_m = re.search(r"spf=(\S+)", part, re.I)
            dkim_m = re.search(r"dkim=(\S+)", part, re.I)
            dmarc_m = re.search(r"dmarc=(\S+)", part, re.I)
            arc_m = re.search(r"arc=(\S+)", part, re.I)
            result_entry = {
                "auth_serv_id": auth_serv_id,
                "spf": spf_m.group(1) if spf_m else None,
                "dkim": dkim_m.group(1) if dkim_m else None,
                "dmarc": dmarc_m.group(1) if dmarc_m else None,
                "arc": arc_m.group(1) if arc_m else None,
            }
            results.append(result_entry)
            continue
        result_set = re.match(r"\s*(\w+)\s*=\s*(.*)", part)
        if result_set:
            method = result_set.group(1).lower()
            rest = result_set.group(2).strip()
            result_entry = {"method": method, "result": rest, "auth_serv_id": auth_serv_id}
            detail_m = re.search(r"(\w+)\s+(\S+)", rest)
            if detail_m:
                result_entry["result"] = detail_m.group(1).lower()
                result_entry["detail"] = detail_m.group(2)
            smtp_m = re.search(r"smtp\.mailfrom[=:](\S+)", rest, re.I)
            if smtp_m:
                result_entry["mailfrom"] = smtp_m.group(1)
            header_m = re.search(r"header\.from[=:](\S+)", rest, re.I)
            if header_m:
                result_entry["header_from"] = header_m.group(1)
            results.append(result_entry)
    return results


def _parse_dmarc_record(record: str) -> dict:
    result = {"raw": record, "tags": {}, "valid": False}
    if not record:
        return result
    tags = [t.strip() for t in record.split(";") if t.strip()]
    for tag in tags:
        if "=" not in tag:
            continue
        k, v = tag.split("=", 1)
        result["tags"][k.strip()] = v.strip()
    if "v" in result["tags"] and result["tags"]["v"] == "DMARC1":
        result["valid"] = True
    return result


async def _resolve_dns_txt(domain: str) -> list:
    results = []
    if HAS_DNSPYTHON:
        try:
            resolver = dns.asyncresolver.Resolver()
            resolver.timeout = DEFAULT_TIMEOUT
            resolver.lifetime = DEFAULT_TIMEOUT
            answers = await resolver.resolve(domain, "TXT")
            for rdata in answers:
                txt_string = b"".join(rdata.strings).decode("utf-8", errors="replace")
                results.append(txt_string)
            return results
        except dns.exception.DNSException as e:
            logger.debug("dns.txt %s: %s", domain, e)
    if HAS_AIODNS:
        try:
            resolver = aiodns.DNSResolver()
            result = await resolver.query(domain, "TXT")
            for entry in result:
                if hasattr(entry, "text") and entry.text:
                    results.append(entry.text)
            return results
        except Exception as e:
            logger.debug("aiodns.txt %s: %s", domain, e)
    if HAS_HTTPX:
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                resp = await client.get(
                    f"https://dns.google/resolve?name={domain}&type=TXT",
                    headers={"Accept": "application/dns-json"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for answer in data.get("Answer", []):
                        if answer.get("type") == 16:
                            txt = answer.get("data", "").strip('"')
                            results.append(txt)
        except Exception as e:
            logger.debug("dns.google %s: %s", domain, e)
    return results


async def _resolve_dns_mx(domain: str) -> list:
    results = []
    if HAS_DNSPYTHON:
        try:
            resolver = dns.asyncresolver.Resolver()
            resolver.timeout = DEFAULT_TIMEOUT
            resolver.lifetime = DEFAULT_TIMEOUT
            answers = await resolver.resolve(domain, "MX")
            for rdata in answers:
                results.append({
                    "preference": rdata.preference,
                    "exchange": str(rdata.exchange).rstrip("."),
                })
            return results
        except dns.exception.DNSException as e:
            logger.debug("dns.mx %s: %s", domain, e)
    if HAS_AIODNS:
        try:
            resolver = aiodns.DNSResolver()
            result = await resolver.query(domain, "MX")
            for entry in result:
                results.append({
                    "preference": getattr(entry, "priority", 0),
                    "exchange": getattr(entry, "host", ""),
                })
            return results
        except Exception as e:
            logger.debug("aiodns.mx %s: %s", domain, e)
    if HAS_HTTPX:
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                resp = await client.get(
                    f"https://dns.google/resolve?name={domain}&type=MX",
                    headers={"Accept": "application/dns-json"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for answer in data.get("Answer", []):
                        if answer.get("type") == 15:
                            data_str = answer.get("data", "")
                            parts = data_str.split()
                            if len(parts) >= 2:
                                results.append({
                                    "preference": int(parts[0]),
                                    "exchange": parts[1].rstrip("."),
                                })
        except Exception as e:
            logger.debug("dns.google mx %s: %s", domain, e)
    return results


async def _resolve_dns_a(hostname: str) -> list:
    results = []
    if HAS_DNSPYTHON:
        try:
            resolver = dns.asyncresolver.Resolver()
            resolver.timeout = DEFAULT_TIMEOUT
            resolver.lifetime = DEFAULT_TIMEOUT
            answers = await resolver.resolve(hostname, "A")
            for rdata in answers:
                results.append(str(rdata))
            return results
        except dns.exception.DNSException as e:
            logger.debug("dns.a %s: %s", hostname, e)
    if HAS_AIODNS:
        try:
            resolver = aiodns.DNSResolver()
            result = await resolver.query(hostname, "A")
            items = result if isinstance(result, list) else [result]
            for entry in items:
                results.append(getattr(entry, "host", str(entry)))
            return results
        except Exception as e:
            logger.debug("aiodns.a %s: %s", hostname, e)
    try:
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            info = await loop.run_in_executor(pool, socket.getaddrinfo, hostname, 80)
            for entry in info:
                ip = entry[4][0]
                if ip not in results:
                    results.append(ip)
    except Exception as e:
        logger.debug("socket.a %s: %s", hostname, e)
    return results


async def _resolve_ptr(ip: str) -> str:
    if HAS_DNSPYTHON:
        try:
            resolver = dns.asyncresolver.Resolver()
            resolver.timeout = DEFAULT_TIMEOUT
            resolver.lifetime = DEFAULT_TIMEOUT
            rev = dns.reversename.from_address(ip)
            answers = await resolver.resolve(rev, "PTR")
            return str(answers[0]).rstrip(".")
        except dns.exception.DNSException:
            pass
    if HAS_AIODNS:
        try:
            resolver = aiodns.DNSResolver()
            result = await resolver.gethostbyaddr(ip)
            return result.name if hasattr(result, "name") else str(result)
        except Exception:
            pass
    try:
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            hostname, _, _ = await loop.run_in_executor(pool, socket.gethostbyaddr, ip)
            return hostname
    except Exception:
        pass
    return ""


async def _http_get(url: str, headers: dict | None = None) -> dict:
    if HAS_HTTPX:
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(DEFAULT_TIMEOUT),
                verify=False,
                follow_redirects=True,
            ) as client:
                resp = await client.get(url, headers=headers or {})
                return {
                    "status": resp.status_code,
                    "body": resp.text,
                    "headers": dict(resp.headers),
                    "success": resp.status_code < 400,
                }
        except Exception as e:
            return {"status": 0, "body": str(e), "headers": {}, "success": False}
    return {"status": 0, "body": "No HTTP client available", "headers": {}, "success": False}


async def _check_breach_api(email_addr: str) -> dict:
    results = {"breaches": [], "pastes": [], "found": False, "count": 0}
    if HAS_HTTPX:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(DEFAULT_TIMEOUT)) as client:
                api_key = os.environ.get("HIBP_API_KEY", "")
                headers = {}
                if api_key:
                    headers["hibp-api-key"] = api_key
                resp = await client.get(
                    f"https://haveibeenpwned.com/api/v3/breachedaccount/{email_addr}",
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results["breaches"] = [
                        {"name": b.get("Name", ""), "domain": b.get("Domain", ""),
                         "date": b.get("BreachDate", ""), "data_classes": b.get("DataClasses", [])}
                        for b in data
                    ]
                    results["found"] = True
                    results["count"] = len(data)
                elif resp.status_code == 404:
                    results["found"] = False
                else:
                    results["error"] = f"API returned {resp.status_code}"
        except Exception as e:
            results["error"] = str(e)
    else:
        results["error"] = "No HTTP client for breach API"
    return results



async def analyze_email_headers(raw_headers: str) -> dict:
    result = {
        "success": True,
        "headers_raw": raw_headers[:500] if raw_headers else "",
        "headers_parsed": {},
        "anomalies": [],
        "field_count": 0,
        "fields": [],
        "message_id": None,
        "date": None,
        "from": None,
        "to": None,
        "cc": None,
        "subject": None,
        "return_path": None,
        "reply_to": None,
        "errors_to": None,
        "content_type": None,
        "mime_version": None,
        "x_headers": [],
        "auth_results": [],
        "received_count": 0,
    }
    try:
        parser = email.parser.HeaderParser(policy=email.policy.default)
        if isinstance(raw_headers, bytes):
            msg = parser.parsestr(_safe_decode_bytes(raw_headers))
        else:
            msg = parser.parsestr(raw_headers)
        parsed = {}
        for key, val in msg.items():
            key_lower = key.lower()
            decoded_val = _decode_mime_header(val)
            if key_lower in parsed:
                if isinstance(parsed[key_lower], list):
                    parsed[key_lower].append(decoded_val)
                else:
                    parsed[key_lower] = [parsed[key_lower], decoded_val]
            else:
                parsed[key_lower] = decoded_val
            if key_lower.startswith("x-"):
                result["x_headers"].append({"name": key, "value": decoded_val})
        result["headers_parsed"] = parsed
        result["field_count"] = len(msg.items())
        result["fields"] = list(msg.keys())
        result["message_id"] = msg.get("Message-ID", "").strip("<>")
        result["date"] = _parse_date_header(msg.get("Date", ""))
        result["from"] = _parse_email_addr(msg.get("From", ""))
        result["to"] = _parse_email_addr(msg.get("To", ""))
        result["cc"] = _parse_email_addr(msg.get("Cc", ""))
        result["subject"] = _decode_mime_header(msg.get("Subject", ""))
        result["return_path"] = msg.get("Return-Path", "").strip("<>")
        result["reply_to"] = _parse_email_addr(msg.get("Reply-To", ""))
        result["errors_to"] = msg.get("Errors-To", "")
        result["content_type"] = msg.get("Content-Type", "")
        result["mime_version"] = msg.get("MIME-Version", "")
        received_headers = msg.get_all("Received", [])
        result["received_count"] = len(received_headers)
        auth_results_headers = msg.get_all("Authentication-Results", [])
        result["auth_results_raw"] = auth_results_headers
        for auth_val in auth_results_headers:
            result["auth_results"].extend(_parse_authentication_results_field(auth_val))
        from_addr = (result.get("from") or {}).get("address", "")
        return_path_val = result.get("return_path", "")
        if from_addr and return_path_val:
            from_domain = _extract_domain(from_addr)
            rp_domain = _extract_domain(return_path_val)
            if from_domain and rp_domain and from_domain != rp_domain:
                result["anomalies"].append({
                    "type": "from_return_path_mismatch",
                    "severity": "high",
                    "detail": f"From domain ({from_domain}) differs from Return-Path ({rp_domain})",
                })
        if "received" not in parsed:
            result["anomalies"].append({
                "type": "missing_received",
                "severity": "high",
                "detail": "No Received headers found; email may be locally generated",
            })
        if "message-id" not in parsed:
            result["anomalies"].append({
                "type": "missing_message_id",
                "severity": "medium",
                "detail": "Missing Message-ID header",
            })
        if "date" not in parsed:
            result["anomalies"].append({
                "type": "missing_date",
                "severity": "low",
                "detail": "Missing Date header",
            })
        if "from" not in parsed:
            result["anomalies"].append({
                "type": "missing_from",
                "severity": "critical",
                "detail": "Missing From header",
            })
        if result.get("mime_version") and result["mime_version"] not in ("1.0", ""):
            result["anomalies"].append({
                "type": "unusual_mime_version",
                "severity": "low",
                "detail": f"Unusual MIME version: {result['mime_version']}",
            })
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
    return result


async def extract_received_chain(raw_headers: str) -> dict:
    result = {
        "success": True,
        "chain": [],
        "hop_count": 0,
        "first_hop": None,
        "last_hop": None,
        "reverse_chain": [],
    }
    try:
        parser = email.parser.HeaderParser(policy=email.policy.default)
        if isinstance(raw_headers, bytes):
            msg = parser.parsestr(_safe_decode_bytes(raw_headers))
        else:
            msg = parser.parsestr(raw_headers)
        received_headers = msg.get_all("Received", [])
        result["hop_count"] = len(received_headers)
        parsed_entries = []
        for raw_line in received_headers:
            entry = _parse_received_line(raw_line)
            entry["header_index"] = len(parsed_entries)
            parsed_entries.append(entry)
        result["chain"] = parsed_entries
        result["reverse_chain"] = list(reversed(parsed_entries))
        if parsed_entries:
            result["first_hop"] = parsed_entries[0]
            result["last_hop"] = parsed_entries[-1]
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
    return result


async def trace_email_path(headers: str) -> dict:
    result = {
        "success": True,
        "hops": [],
        "total_hops": 0,
        "start_time": None,
        "end_time": None,
        "route_summary": [],
        "path_string": "",
        "source_ip": None,
        "source_hostname": None,
        "destination_hostname": None,
        "ip_chain": [],
    }
    try:
        chain_result = await extract_received_chain(headers)
        if not chain_result["success"]:
            return {"success": False, "error": chain_result.get("error", "parse failed")}
        hops = []
        seen_ips = []
        for i, entry in enumerate(chain_result["reverse_chain"]):
            hop = {
                "hop_number": i + 1,
                "from": entry.get("from", ""),
                "by": entry.get("by", ""),
                "ip": entry.get("ip", ""),
                "hostname": entry.get("hostname", ""),
                "protocol": entry.get("protocol", ""),
                "timestamp": entry.get("timestamp", ""),
                "timestamp_parsed": entry.get("timestamp_parsed"),
                "tls": entry.get("tls", False),
                "id": entry.get("id", ""),
                "for": entry.get("for", ""),
            }
            hop_ip = hop["ip"]
            if hop_ip:
                hop["is_private"] = _is_ip_private(hop_ip)
                hop["is_reserved"] = _is_ip_reserved(hop_ip)
                if hop_ip not in seen_ips:
                    seen_ips.append(hop_ip)
                try:
                    hop["ptr"] = await _resolve_ptr(hop_ip)
                except Exception:
                    hop["ptr"] = ""
            hops.append(hop)
        result["hops"] = hops
        result["total_hops"] = len(hops)
        if hops:
            result["start_time"] = hops[0].get("timestamp")
            result["end_time"] = hops[-1].get("timestamp")
            if hops[0].get("ip"):
                result["source_ip"] = hops[0]["ip"]
                result["source_hostname"] = hops[0].get("ptr") or hops[0].get("hostname")
            if hops[-1].get("by"):
                result["destination_hostname"] = hops[-1]["by"]
        result["ip_chain"] = seen_ips
        path_parts = []
        for hop in hops:
            label = hop.get("hostname") or hop.get("ip") or hop.get("from", "unknown")
            path_parts.append(label)
        result["path_string"] = " -> ".join(path_parts)
        for hop in hops:
            result["route_summary"].append({
                "hop": hop["hop_number"],
                "location": hop.get("hostname") or hop.get("ip") or "unknown",
                "protocol": hop.get("protocol"),
                "tls": hop.get("tls"),
            })
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
    return result


async def detect_email_spoofing(headers: str) -> dict:
    result = {
        "success": True,
        "spoofing_detected": False,
        "risk_level": "low",
        "indicators": [],
        "from_domain": None,
        "return_path_domain": None,
        "reply_to_domain": None,
        "auth_results": [],
        "spf_aligned": None,
        "dkim_aligned": None,
        "dmarc_aligned": None,
        "spf_pass": None,
        "dkim_pass": None,
        "dmarc_pass": None,
        "display_name_mismatch": False,
        "domain_similarity": None,
    }
    try:
        parser = email.parser.HeaderParser(policy=email.policy.default)
        if isinstance(headers, bytes):
            msg = parser.parsestr(_safe_decode_bytes(headers))
        else:
            msg = parser.parsestr(headers)
        from_addr = _parse_email_addr(msg.get("From", ""))
        result["from"] = from_addr
        result["from_domain"] = from_addr.get("domain", "")
        return_path_raw = msg.get("Return-Path", "")
        if return_path_raw:
            return_path_addr = return_path_raw.strip("<>")
            result["return_path_domain"] = _extract_domain(return_path_addr)
        reply_to_raw = msg.get("Reply-To", "")
        if reply_to_raw:
            reply_to_addr = _parse_email_addr(reply_to_raw)
            result["reply_to_domain"] = reply_to_addr.get("domain", "")
        auth_headers = msg.get_all("Authentication-Results", [])
        for auth_val in auth_headers:
            parsed = _parse_authentication_results_field(auth_val)
            result["auth_results"].extend(parsed)
            for entry in parsed:
                if isinstance(entry, dict):
                    spf_res = entry.get("spf", "")
                    dkim_res = entry.get("dkim", "")
                    dmarc_res = entry.get("dmarc", "")
                    if spf_res:
                        result["spf_pass"] = spf_res.lower() in ("pass", "softpass")
                    if dkim_res:
                        result["dkim_pass"] = dkim_res.lower() == "pass"
                    if dmarc_res:
                        result["dmarc_pass"] = dmarc_res.lower() == "pass"
        if result.get("from_domain") and result.get("return_path_domain"):
            from_d = result["from_domain"]
            rp_d = result["return_path_domain"]
            if from_d != rp_d:
                result["spoofing_detected"] = True
                result["spf_aligned"] = False
                result["indicators"].append({
                    "type": "domain_mismatch",
                    "severity": "high",
                    "detail": f"From '{from_d}' != Return-Path '{rp_d}'",
                })
            else:
                result["spf_aligned"] = True
        if result.get("from_domain") and result.get("reply_to_domain"):
            from_d = result["from_domain"]
            rt_d = result["reply_to_domain"]
            if from_d != rt_d:
                result["indicators"].append({
                    "type": "reply_to_mismatch",
                    "severity": "medium",
                    "detail": f"From '{from_d}' != Reply-To '{rt_d}'",
                })
        if result.get("spf_pass") is False:
            result["indicators"].append({
                "type": "spf_fail", "severity": "high", "detail": "SPF auth failed",
            })
        if result.get("dkim_pass") is False:
            result["indicators"].append({
                "type": "dkim_fail", "severity": "high", "detail": "DKIM auth failed",
            })
        from_name = from_addr.get("name", "")
        if from_name:
            from_email = from_addr.get("address", "")
            common_providers = ["gmail.com", "yahoo.com", "outlook.com",
                                "hotmail.com", "icloud.com", "aol.com"]
            provider_match = None
            for provider in common_providers:
                if provider in from_email.lower():
                    provider_match = provider
                    break
            if provider_match and provider_match not in from_email.lower():
                result["display_name_mismatch"] = True
                result["indicators"].append({
                    "type": "display_name_spoof",
                    "severity": "medium",
                    "detail": f"Name '{from_name}' may impersonate {provider_match}",
                })
        if result.get("dmarc_pass") is False and result.get("spf_pass") is False and result.get("dkim_pass") is False:
            result["spoofing_detected"] = True
            result["risk_level"] = "critical"
        elif result.get("spoofing_detected"):
            high_count = sum(1 for i in result["indicators"] if i.get("severity") == "high")
            result["risk_level"] = "high" if high_count >= 2 else "medium"
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
    return result


async def extract_authentication_results(headers: str) -> dict:
    result = {
        "success": True,
        "auth_serv_ids": [],
        "results": [],
        "spf_results": [],
        "dkim_results": [],
        "dmarc_results": [],
        "arc_results": [],
        "summary": {},
    }
    try:
        parser = email.parser.HeaderParser(policy=email.policy.default)
        if isinstance(headers, bytes):
            msg = parser.parsestr(_safe_decode_bytes(headers))
        else:
            msg = parser.parsestr(headers)
        auth_headers = msg.get_all("Authentication-Results", [])
        arc_seal = msg.get_all("ARC-Seal", [])
        arc_msgs = msg.get_all("ARC-Message-Signature", [])
        for raw_val in auth_headers:
            parsed = _parse_authentication_results_field(raw_val)
            for entry in parsed:
                result["results"].append(entry)
                if isinstance(entry, dict):
                    serv_id = entry.get("auth_serv_id")
                    if serv_id and serv_id not in result["auth_serv_ids"]:
                        result["auth_serv_ids"].append(serv_id)
                    for m in ("spf", "dkim", "dmarc", "arc"):
                        val = entry.get(m)
                        if val:
                            result[f"{m}_results"].append({
                                "auth_serv_id": serv_id,
                                "result": val,
                            })
        has_spf = any(r.get("result", "").lower() == "pass" for r in result["spf_results"])
        has_dkim = any(r.get("result", "").lower() == "pass" for r in result["dkim_results"])
        has_dmarc = any(r.get("result", "").lower() == "pass" for r in result["dmarc_results"])
        result["summary"] = {
            "spf": "pass" if has_spf else ("fail" if result["spf_results"] else "none"),
            "dkim": "pass" if has_dkim else ("fail" if result["dkim_results"] else "none"),
            "dmarc": "pass" if has_dmarc else ("fail" if result["dmarc_results"] else "none"),
            "auth_servers": result["auth_serv_ids"],
            "arc_seal_count": len(arc_seal),
            "arc_msgs_count": len(arc_msgs),
            "total_results": len(result["results"]),
        }
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
    return result


async def detect_header_forging(headers: str) -> dict:
    result = {
        "success": True,
        "forging_detected": False,
        "risk_level": "low",
        "flags": [],
    }
    try:
        parser = email.parser.HeaderParser(policy=email.policy.default)
        if isinstance(headers, bytes):
            msg = parser.parsestr(_safe_decode_bytes(headers))
        else:
            msg = parser.parsestr(headers)
        received = msg.get_all("Received", [])
        dates = msg.get_all("Date", [])
        msg_ids = msg.get_all("Message-ID", [])
        from_val = msg.get("From", "")
        if received:
            timestamps = []
            for r in received:
                ts_match = re.search(r";\s*(.+)$", r)
                if ts_match:
                    try:
                        ts = email.utils.parsedate_to_datetime(ts_match.group(1).strip())
                        if ts:
                            timestamps.append(ts)
                    except Exception:
                        pass
            if len(timestamps) >= 2:
                sorted_ts = sorted(timestamps)
                for i in range(len(sorted_ts) - 1):
                    diff = (sorted_ts[i + 1] - sorted_ts[i]).total_seconds()
                    if diff < 0:
                        result["flags"].append({
                            "type": "received_out_of_order",
                            "severity": "high",
                            "detail": "Received timestamps out of order",
                        })
                        result["forging_detected"] = True
                        break
                    if diff > 86400:
                        result["flags"].append({
                            "type": "large_timestamp_gap",
                            "severity": "medium",
                            "detail": f"Gap of {diff:.0f}s between hops",
                        })
        if msg_ids:
            for mid in msg_ids:
                mid_clean = mid.strip("<>")
                if not re.match(r".+@.+", mid_clean):
                    result["flags"].append({
                        "type": "invalid_message_id",
                        "severity": "medium",
                        "detail": f"Suspicious Message-ID: {mid}",
                    })
                    result["forging_detected"] = True
        if from_val:
            from_domain = _extract_domain(from_val)
            if from_domain:
                for mid in msg_ids:
                    at_pos = mid.rfind("@")
                    if at_pos > 0:
                        end = mid.rfind(">")
                        if end == -1:
                            end = len(mid)
                        msg_id_domain = mid[at_pos + 1:end].strip().lower()
                        if msg_id_domain and msg_id_domain != from_domain:
                            result["flags"].append({
                                "type": "message_id_domain_mismatch",
                                "severity": "medium",
                                "detail": f"Message-ID domain ({msg_id_domain}) != From ({from_domain})",
                            })
                        break
        if result["flags"]:
            high_count = sum(1 for f in result["flags"] if f.get("severity") == "high")
            med_count = sum(1 for f in result["flags"] if f.get("severity") == "medium")
            if high_count > 0:
                result["risk_level"] = "high"
            elif med_count > 0:
                result["risk_level"] = "medium"
            result["forging_detected"] = high_count > 0
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
    return result


async def calculate_delivery_time(headers: str) -> dict:
    result = {
        "success": True,
        "total_delivery_time_seconds": None,
        "total_delivery_time_human": None,
        "hop_times": [],
        "average_hop_time": None,
        "fastest_hop": None,
        "slowest_hop": None,
        "anomalous_gaps": [],
    }
    try:
        chain_result = await extract_received_chain(headers)
        if not chain_result["success"]:
            return {"success": False, "error": "Failed to extract received chain"}
        hops_with_ts = []
        for entry in chain_result["reverse_chain"]:
            ts_str = entry.get("timestamp_parsed") or entry.get("timestamp")
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str)
                    hops_with_ts.append({"entry": entry, "datetime": ts})
                except (ValueError, TypeError):
                    pass
        if len(hops_with_ts) >= 2:
            hops_with_ts.sort(key=lambda x: x["datetime"])
            for i in range(len(hops_with_ts) - 1):
                diff = (hops_with_ts[i + 1]["datetime"] - hops_with_ts[i]["datetime"]).total_seconds()
                hop_time = {
                    "hop": i + 1,
                    "from": hops_with_ts[i]["entry"].get("from", ""),
                    "by": hops_with_ts[i + 1]["entry"].get("by", ""),
                    "seconds": diff,
                    "human": str(timedelta(seconds=int(diff))),
                }
                result["hop_times"].append(hop_time)
                if diff > 1800:
                    result["anomalous_gaps"].append({
                        "type": "large_delay",
                        "hop": i + 1,
                        "seconds": diff,
                        "detail": f"Delay of {diff:.0f}s between hops",
                    })
            total = sum(ht["seconds"] for ht in result["hop_times"])
            result["total_delivery_time_seconds"] = total
            result["total_delivery_time_human"] = str(timedelta(seconds=int(total)))
            result["average_hop_time"] = total / len(result["hop_times"]) if result["hop_times"] else 0
            if result["hop_times"]:
                result["fastest_hop"] = min(result["hop_times"], key=lambda x: x["seconds"])
                result["slowest_hop"] = max(result["hop_times"], key=lambda x: x["seconds"])
        elif len(hops_with_ts) == 1:
            result["total_delivery_time_seconds"] = 0
            result["total_delivery_time_human"] = "0:00:00"
        else:
            result["note"] = "Insufficient timestamps for delivery time calculation"
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
    return result


# ── Email Header Analysis ─────────────────────────────────────────────────────

async def analyze_email_headers(raw_headers: str) -> dict:
    result = {
        "success": True,
        "headers_raw": (raw_headers[:500] + "...") if raw_headers and len(raw_headers) > 500 else (raw_headers or ""),
        "headers_parsed": {},
        "anomalies": [],
        "field_count": 0,
        "fields": [],
        "message_id": None,
        "date": None,
        "from": None, "to": None, "cc": None,
        "subject": None, "return_path": None, "reply_to": None,
        "errors_to": None, "content_type": None, "mime_version": None,
        "x_headers": [], "auth_results": [], "received_count": 0,
    }
    try:
        parser = email.parser.HeaderParser(policy=email.policy.default)
        if isinstance(raw_headers, bytes):
            msg = parser.parsestr(_safe_decode_bytes(raw_headers))
        else:
            msg = parser.parsestr(raw_headers)
        parsed = {}
        for key, val in msg.items():
            kl = key.lower()
            dv = _decode_mime_header(val)
            if kl in parsed:
                if isinstance(parsed[kl], list):
                    parsed[kl].append(dv)
                else:
                    parsed[kl] = [parsed[kl], dv]
            else:
                parsed[kl] = dv
            if kl.startswith("x-"):
                result["x_headers"].append({"name": key, "value": dv})
        result["headers_parsed"] = parsed
        result["field_count"] = len(msg.items())
        result["fields"] = list(msg.keys())
        result["message_id"] = msg.get("Message-ID", "").strip("<>")
        result["date"] = _parse_date_header(msg.get("Date", ""))
        result["from"] = _parse_email_addr(msg.get("From", ""))
        result["to"] = _parse_email_addr(msg.get("To", ""))
        result["cc"] = _parse_email_addr(msg.get("Cc", ""))
        result["subject"] = _decode_mime_header(msg.get("Subject", ""))
        result["return_path"] = msg.get("Return-Path", "").strip("<>")
        result["reply_to"] = _parse_email_addr(msg.get("Reply-To", ""))
        result["errors_to"] = msg.get("Errors-To", "")
        result["content_type"] = msg.get("Content-Type", "")
        result["mime_version"] = msg.get("MIME-Version", "")
        result["received_count"] = len(msg.get_all("Received", []))
        auth_headers = msg.get_all("Authentication-Results", [])
        result["auth_results_raw"] = auth_headers
        for av in auth_headers:
            result["auth_results"].extend(_parse_authentication_results_field(av))
        from_addr = (result.get("from") or {}).get("address", "")
        rp_val = result.get("return_path", "")
        if from_addr and rp_val:
            fd = _extract_domain(from_addr)
            rd = _extract_domain(rp_val)
            if fd and rd and fd != rd:
                result["anomalies"].append({
                    "type": "from_return_path_mismatch", "severity": "high",
                    "detail": f"From domain ({fd}) != Return-Path ({rd})",
                })
        if "received" not in parsed:
            result["anomalies"].append({
                "type": "missing_received", "severity": "high",
                "detail": "No Received headers; may be locally generated",
            })
        if "message-id" not in parsed:
            result["anomalies"].append({
                "type": "missing_message_id", "severity": "medium",
                "detail": "Missing Message-ID header",
            })
        if "date" not in parsed:
            result["anomalies"].append({
                "type": "missing_date", "severity": "low",
                "detail": "Missing Date header",
            })
        if "from" not in parsed:
            result["anomalies"].append({
                "type": "missing_from", "severity": "critical",
                "detail": "Missing From header",
            })
        mv = result.get("mime_version")
        if mv and mv not in ("1.0", ""):
            result["anomalies"].append({
                "type": "unusual_mime_version", "severity": "low",
                "detail": f"Unusual MIME version: {mv}",
            })
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
    return result


async def extract_received_chain(raw_headers: str) -> dict:
    result = {
        "success": True, "chain": [], "hop_count": 0,
        "first_hop": None, "last_hop": None, "reverse_chain": [],
    }
    try:
        parser = email.parser.HeaderParser(policy=email.policy.default)
        if isinstance(raw_headers, bytes):
            msg = parser.parsestr(_safe_decode_bytes(raw_headers))
        else:
            msg = parser.parsestr(raw_headers)
        received = msg.get_all("Received", [])
        result["hop_count"] = len(received)
        entries = []
        for raw_line in received:
            entry = _parse_received_line(raw_line)
            entry["header_index"] = len(entries)
            entries.append(entry)
        result["chain"] = entries
        result["reverse_chain"] = list(reversed(entries))
        if entries:
            result["first_hop"] = entries[0]
            result["last_hop"] = entries[-1]
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
    return result

async def trace_email_path(headers: str) -> dict:
    result = {
        "success": True, "hops": [], "total_hops": 0,
        "start_time": None, "end_time": None, "route_summary": [],
        "path_string": "", "source_ip": None, "source_hostname": None,
        "destination_hostname": None, "ip_chain": [],
    }
    try:
        chain_result = await extract_received_chain(headers)
        if not chain_result["success"]:
            return {"success": False, "error": chain_result.get("error", "parse failed")}
        hops, seen_ips = [], []
        for i, entry in enumerate(chain_result["reverse_chain"]):
            hop = {
                "hop_number": i + 1, "from": entry.get("from", ""),
                "by": entry.get("by", ""), "ip": entry.get("ip", ""),
                "hostname": entry.get("hostname", ""),
                "protocol": entry.get("protocol", ""),
                "timestamp": entry.get("timestamp", ""),
                "timestamp_parsed": entry.get("timestamp_parsed"),
                "tls": entry.get("tls", False), "id": entry.get("id", ""),
                "for": entry.get("for", ""),
            }
            hip = hop["ip"]
            if hip:
                hop["is_private"] = _is_ip_private(hip)
                hop["is_reserved"] = _is_ip_reserved(hip)
                if hip not in seen_ips:
                    seen_ips.append(hip)
                try:
                    hop["ptr"] = await _resolve_ptr(hip)
                except Exception:
                    hop["ptr"] = ""
            hops.append(hop)
        result["hops"] = hops
        result["total_hops"] = len(hops)
        if hops:
            result["start_time"] = hops[0].get("timestamp")
            result["end_time"] = hops[-1].get("timestamp")
            if hops[0].get("ip"):
                result["source_ip"] = hops[0]["ip"]
                result["source_hostname"] = hops[0].get("ptr") or hops[0].get("hostname")
            if hops[-1].get("by"):
                result["destination_hostname"] = hops[-1]["by"]
        result["ip_chain"] = seen_ips
        path_parts = []
        for hop in hops:
            label = hop.get("hostname") or hop.get("ip") or hop.get("from", "unknown")
            path_parts.append(label)
        result["path_string"] = " -> ".join(path_parts)
        for hop in hops:
            result["route_summary"].append({
                "hop": hop["hop_number"],
                "location": hop.get("hostname") or hop.get("ip") or "unknown",
                "protocol": hop.get("protocol"), "tls": hop.get("tls"),
            })
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
    return result


async def detect_email_spoofing(headers: str) -> dict:
    result = {
        "success": True, "spoofing_detected": False, "risk_level": "low",
        "indicators": [], "from_domain": None, "return_path_domain": None,
        "reply_to_domain": None, "auth_results": [],
        "spf_aligned": None, "dkim_aligned": None, "dmarc_aligned": None,
        "spf_pass": None, "dkim_pass": None, "dmarc_pass": None,
        "display_name_mismatch": False,
    }
    try:
        parser = email.parser.HeaderParser(policy=email.policy.default)
        if isinstance(headers, bytes):
            msg = parser.parsestr(_safe_decode_bytes(headers))
        else:
            msg = parser.parsestr(headers)
        from_addr = _parse_email_addr(msg.get("From", ""))
        result["from"] = from_addr
        result["from_domain"] = from_addr.get("domain", "")
        rp_raw = msg.get("Return-Path", "")
        if rp_raw:
            result["return_path_domain"] = _extract_domain(rp_raw.strip("<>"))
        rt_raw = msg.get("Reply-To", "")
        if rt_raw:
            result["reply_to_domain"] = _parse_email_addr(rt_raw).get("domain", "")
        for av in msg.get_all("Authentication-Results", []):
            parsed = _parse_authentication_results_field(av)
            result["auth_results"].extend(parsed)
            for entry in parsed:
                if isinstance(entry, dict):
                    sr = entry.get("spf", "")
                    dr = entry.get("dkim", "")
                    dmr = entry.get("dmarc", "")
                    if sr: result["spf_pass"] = sr.lower() in ("pass", "softpass")
                    if dr: result["dkim_pass"] = dr.lower() == "pass"
                    if dmr: result["dmarc_pass"] = dmr.lower() == "pass"
        fd = result.get("from_domain")
        rd = result.get("return_path_domain")
        if fd and rd:
            if fd != rd:
                result["spoofing_detected"] = True; result["spf_aligned"] = False
                result["indicators"].append({
                    "type": "domain_mismatch", "severity": "high",
                    "detail": f"From '{fd}' != Return-Path '{rd}'",
                })
            else: result["spf_aligned"] = True
        fd2 = result.get("from_domain")
        rtd = result.get("reply_to_domain")
        if fd2 and rtd and fd2 != rtd:
            result["indicators"].append({
                "type": "reply_to_mismatch", "severity": "medium",
                "detail": f"From '{fd2}' != Reply-To '{rtd}'",
            })
        if result.get("spf_pass") is False:
            result["indicators"].append({"type": "spf_fail", "severity": "high", "detail": "SPF auth failed"})
        if result.get("dkim_pass") is False:
            result["indicators"].append({"type": "dkim_fail", "severity": "high", "detail": "DKIM auth failed"})
        fn = from_addr.get("name", "")
        if fn:
            fe = from_addr.get("address", "")
            for prov in ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "aol.com"]:
                if prov in fe.lower() and prov not in fe.lower():
                    result["display_name_mismatch"] = True
                    result["indicators"].append({
                        "type": "display_name_spoof", "severity": "medium",
                        "detail": f"Name '{fn}' may impersonate {prov}",
                    }); break
        if result.get("dmarc_pass") is False and result.get("spf_pass") is False and result.get("dkim_pass") is False:
            result["spoofing_detected"] = True; result["risk_level"] = "critical"
        elif result.get("spoofing_detected"):
            hc = sum(1 for i in result["indicators"] if i.get("severity") == "high")
            result["risk_level"] = "high" if hc >= 2 else "medium"
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result

async def extract_authentication_results(headers: str) -> dict:
    result = {
        "success": True, "auth_serv_ids": [], "results": [],
        "spf_results": [], "dkim_results": [], "dmarc_results": [],
        "arc_results": [], "summary": {},
    }
    try:
        parser = email.parser.HeaderParser(policy=email.policy.default)
        if isinstance(headers, bytes):
            msg = parser.parsestr(_safe_decode_bytes(headers))
        else:
            msg = parser.parsestr(headers)
        auth_headers = msg.get_all("Authentication-Results", [])
        arc_seal = msg.get_all("ARC-Seal", [])
        arc_msgs = msg.get_all("ARC-Message-Signature", [])
        for raw_val in auth_headers:
            parsed = _parse_authentication_results_field(raw_val)
            for entry in parsed:
                result["results"].append(entry)
                if isinstance(entry, dict):
                    sid = entry.get("auth_serv_id")
                    if sid and sid not in result["auth_serv_ids"]:
                        result["auth_serv_ids"].append(sid)
                    for m in ("spf", "dkim", "dmarc", "arc"):
                        val = entry.get(m)
                        if val:
                            result[f"{m}_results"].append({"auth_serv_id": sid, "result": val})
        has_spf = any(r.get("result","").lower()=="pass" for r in result["spf_results"])
        has_dkim = any(r.get("result","").lower()=="pass" for r in result["dkim_results"])
        has_dmarc = any(r.get("result","").lower()=="pass" for r in result["dmarc_results"])
        result["summary"] = {
            "spf": "pass" if has_spf else ("fail" if result["spf_results"] else "none"),
            "dkim": "pass" if has_dkim else ("fail" if result["dkim_results"] else "none"),
            "dmarc": "pass" if has_dmarc else ("fail" if result["dmarc_results"] else "none"),
            "auth_servers": result["auth_serv_ids"],
            "arc_seal_count": len(arc_seal), "arc_msgs_count": len(arc_msgs),
            "total_results": len(result["results"]),
        }
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def detect_header_forging(headers: str) -> dict:
    result = {
        "success": True, "forging_detected": False,
        "risk_level": "low", "flags": [],
    }
    try:
        parser = email.parser.HeaderParser(policy=email.policy.default)
        if isinstance(headers, bytes):
            msg = parser.parsestr(_safe_decode_bytes(headers))
        else:
            msg = parser.parsestr(headers)
        received = msg.get_all("Received", [])
        msg_ids = msg.get_all("Message-ID", [])
        from_val = msg.get("From", "")
        if received:
            timestamps = []
            for r in received:
                m = re.search(r";\s*(.+)$", r)
                if m:
                    try:
                        ts = email.utils.parsedate_to_datetime(m.group(1).strip())
                        if ts: timestamps.append(ts)
                    except Exception: pass
            if len(timestamps) >= 2:
                sorted_ts = sorted(timestamps)
                for i in range(len(sorted_ts)-1):
                    diff = (sorted_ts[i+1] - sorted_ts[i]).total_seconds()
                    if diff < 0:
                        result["flags"].append({
                            "type": "received_out_of_order", "severity": "high",
                            "detail": "Received timestamps out of order",
                        }); result["forging_detected"] = True; break
                    if diff > 86400:
                        result["flags"].append({
                            "type": "large_timestamp_gap", "severity": "medium",
                            "detail": f"Gap of {diff:.0f}s between hops",
                        })
        if msg_ids:
            for mid in msg_ids:
                mc = mid.strip("<>")
                if not re.match(r".+@.+", mc):
                    result["flags"].append({
                        "type": "invalid_message_id", "severity": "medium",
                        "detail": f"Suspicious Message-ID: {mid}",
                    }); result["forging_detected"] = True
        if from_val:
            fd = _extract_domain(from_val)
            if fd:
                for mid in msg_ids:
                    at = mid.rfind("@")
                    if at > 0:
                        end = mid.rfind(">")
                        if end==-1: end=len(mid)
                        md = mid[at+1:end].strip().lower()
                        if md and md != fd:
                            result["flags"].append({
                                "type": "message_id_domain_mismatch", "severity": "medium",
                                "detail": f"Message-ID domain ({md}) != From ({fd})",
                            }); break
        if result["flags"]:
            hc = sum(1 for f in result["flags"] if f.get("severity")=="high")
            mc = sum(1 for f in result["flags"] if f.get("severity")=="medium")
            result["risk_level"] = "high" if hc>0 else ("medium" if mc>0 else "low")
            result["forging_detected"] = hc>0
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def calculate_delivery_time(headers: str) -> dict:
    result = {
        "success": True, "total_delivery_time_seconds": None,
        "total_delivery_time_human": None, "hop_times": [],
        "average_hop_time": None, "fastest_hop": None, "slowest_hop": None,
        "anomalous_gaps": [],
    }
    try:
        chain_result = await extract_received_chain(headers)
        if not chain_result["success"]:
            return {"success": False, "error": "parse failed"}
        hops_with_ts = []
        for entry in chain_result["reverse_chain"]:
            ts_str = entry.get("timestamp_parsed") or entry.get("timestamp")
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str)
                    hops_with_ts.append({"entry": entry, "datetime": ts})
                except (ValueError, TypeError): pass
        if len(hops_with_ts) >= 2:
            hops_with_ts.sort(key=lambda x: x["datetime"])
            for i in range(len(hops_with_ts)-1):
                diff = (hops_with_ts[i+1]["datetime"] - hops_with_ts[i]["datetime"]).total_seconds()
                ht = {
                    "hop": i+1, "from": hops_with_ts[i]["entry"].get("from",""),
                    "by": hops_with_ts[i+1]["entry"].get("by",""),
                    "seconds": diff, "human": str(timedelta(seconds=int(diff))),
                }
                result["hop_times"].append(ht)
                if diff > 1800:
                    result["anomalous_gaps"].append({
                        "type": "large_delay", "hop": i+1, "seconds": diff,
                        "detail": f"Delay of {diff:.0f}s between hops",
                    })
            total = sum(ht["seconds"] for ht in result["hop_times"])
            result["total_delivery_time_seconds"] = total
            result["total_delivery_time_human"] = str(timedelta(seconds=int(total)))
            result["average_hop_time"] = total/len(result["hop_times"]) if result["hop_times"] else 0
            if result["hop_times"]:
                result["fastest_hop"] = min(result["hop_times"], key=lambda x: x["seconds"])
                result["slowest_hop"] = max(result["hop_times"], key=lambda x: x["seconds"])
        elif len(hops_with_ts) == 1:
            result["total_delivery_time_seconds"] = 0
            result["total_delivery_time_human"] = "0:00:00"
        else:
            result["note"] = "Insufficient timestamps for delivery time calculation"
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result

# ── SPF Analysis ──────────────────────────────────────────────────────────────

async def check_spf_record(domain: str) -> dict:
    result = {
        "success": True, "domain": domain,
        "records": [], "spf_record": None,
        "has_spf": False, "query_time": None,
    }
    t0 = time.monotonic()
    try:
        txt_records = await _resolve_dns_txt(domain)
        spf_records = [t for t in txt_records if t.startswith("v=spf1")]
        for txt in txt_records:
            for part in txt.split(";"):
                if part.strip().startswith("v=spf1"):
                    spf_records.append(txt); break
        result["records"] = txt_records
        if spf_records:
            result["spf_record"] = spf_records[0]
            result["has_spf"] = True
            result["all_records"] = spf_records
        result["query_time"] = time.monotonic() - t0
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
        result["query_time"] = time.monotonic() - t0
    return result


async def analyze_spf_record(spf_record: str) -> dict:
    result = {
        "success": True, "raw": spf_record, "version": None,
        "mechanisms": [], "modifiers": [], "includes": [],
        "ip4_ranges": [], "ip6_ranges": [], "a_mechanisms": [],
        "mx_mechanisms": [], "exists_mechanisms": [],
        "all_mechanism": None, "redirect": None, "exp": None,
        "lookup_count": 0, "parsed": {},
    }
    if not spf_record or not spf_record.startswith("v=spf1"):
        return {"success": False, "error": "Not a valid SPF record", "raw": spf_record}
    try:
        result["version"] = "spf1"
        for part in spf_record.split():
            part = part.strip()
            if part == "v=spf1": continue
            mech = part.split(":")[0].split("/")[0].split("=")[0]
            if mech[0] in "+-~?":
                qualifier, mech = mech[0], mech[1:]
            else:
                qualifier = "+"
            is_mod = mech in ("redirect", "exp")
            entry = {"raw": part, "mechanism": mech, "qualifier": qualifier,
                     "qualifier_name": {"+":"pass","-":"fail","~":"softfail","?":"neutral"}.get(qualifier,"pass")}
            if mech == "include":
                d = part.split(":",1)[1] if ":" in part else ""
                entry["domain"] = d; result["includes"].append(d); result["lookup_count"] += 1
            elif mech == "ip4":
                r = part.split(":",1)[1] if ":" in part else ""
                entry["range"] = r; result["ip4_ranges"].append(r)
            elif mech == "ip6":
                r = part.split(":",1)[1] if ":" in part else ""
                entry["range"] = r; result["ip6_ranges"].append(r)
            elif mech == "a":
                entry["domain"] = part.split(":",1)[1] if ":" in part else ""
                result["a_mechanisms"].append(entry["domain"])
            elif mech == "mx":
                entry["domain"] = part.split(":",1)[1] if ":" in part else ""
                result["mx_mechanisms"].append(entry["domain"])
            elif mech == "exists":
                entry["domain"] = part.split(":",1)[1] if ":" in part else ""
                result["exists_mechanisms"].append(entry["domain"])
            elif mech == "all":
                result["all_mechanism"] = qualifier
                result["all_mechanism_name"] = {"+":"pass","-":"fail","~":"softfail","?":"neutral"}.get(qualifier,"pass")
            elif mech == "redirect":
                d = part.split("=",1)[1] if "=" in part else ""
                entry["domain"] = d; result["redirect"] = d; result["lookup_count"] += 1
            elif mech == "exp":
                entry["domain"] = part.split("=",1)[1] if "=" in part else ""
                result["exp"] = entry["domain"]
            if is_mod: result["modifiers"].append(entry)
            else: result["mechanisms"].append(entry)
        lookups = len(result["includes"])
        if result["a_mechanisms"] or any(m["mechanism"]=="a" for m in result["mechanisms"]): lookups += 1
        if result["mx_mechanisms"] or any(m["mechanism"]=="mx" for m in result["mechanisms"]): lookups += 1
        if result["redirect"]: lookups += 1
        result["estimated_dns_lookups"] = lookups
        result["exceeds_10_limit"] = lookups > 10
        result["parsed"] = {
            "version": "spf1", "all_mechanism": result["all_mechanism"],
            "include_count": len(result["includes"]),
            "ip4_count": len(result["ip4_ranges"]), "ip6_count": len(result["ip6_ranges"]),
            "has_redirect": result["redirect"] is not None,
        }
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result

async def validate_spf(sender_ip: str, sender_domain: str, helo_domain: str = "") -> dict:
    result = {
        "success": True, "sender_ip": sender_ip, "sender_domain": sender_domain,
        "helo_domain": helo_domain or sender_domain, "spf_result": "none",
        "matched_mechanism": None, "matched_rule": None,
        "explanations": [], "validation_steps": [],
    }
    try:
        spf_check = await check_spf_record(sender_domain)
        if not spf_check.get("has_spf"):
            result["spf_result"] = "none"
            result["explanations"].append(f"No SPF record for {sender_domain}")
            return result
        parsed = await analyze_spf_record(spf_check["spf_record"])
        if not parsed["success"]:
            result["spf_result"] = "temperror"
            result["explanations"].append(f"Parse error: {parsed.get('error')}")
            return result
        result["validation_steps"].append({"step": "spf_found", "detail": spf_check["spf_record"]})
        sender_obj = ipaddress.ip_address(sender_ip)
        for r in parsed["ip4_ranges"]:
            try:
                if sender_obj in ipaddress.ip_network(r):
                    q = next((m["qualifier"] for m in parsed["mechanisms"] if m["mechanism"]=="ip4" and m.get("range")==r), "+")
                    result["spf_result"] = {"+":"pass","-":"fail","~":"softfail","?":"neutral"}.get(q,"pass")
                    result["matched_mechanism"] = "ip4"; result["matched_rule"] = r
                    result["explanations"].append(f"IP {sender_ip} matches ip4:{r}"); return result
            except ValueError: continue
        for r in parsed["ip6_ranges"]:
            try:
                if sender_obj in ipaddress.ip_network(r):
                    q = next((m["qualifier"] for m in parsed["mechanisms"] if m["mechanism"]=="ip6" and m.get("range")==r), "+")
                    result["spf_result"] = {"+":"pass","-":"fail","~":"softfail","?":"neutral"}.get(q,"pass")
                    result["matched_mechanism"] = "ip6"; result["matched_rule"] = r
                    result["explanations"].append(f"IP {sender_ip} matches ip6:{r}"); return result
            except ValueError: continue
        a_domains = parsed["a_mechanisms"] if parsed["a_mechanisms"] else [sender_domain]
        for ad in a_domains:
            try:
                a_recs = await _resolve_dns_a(ad or sender_domain)
                if sender_ip in a_recs:
                    q = next((m["qualifier"] for m in parsed["mechanisms"] if m["mechanism"]=="a"), "+")
                    result["spf_result"] = {"+":"pass","-":"fail","~":"softfail","?":"neutral"}.get(q,"pass")
                    result["matched_mechanism"] = "a"; result["matched_rule"] = ad or sender_domain
                    result["explanations"].append(f"IP matches A record of {ad or sender_domain}"); return result
            except Exception: continue
        mx_domains = parsed["mx_mechanisms"] if parsed["mx_mechanisms"] else [sender_domain]
        for md in mx_domains:
            try:
                for mx in await _resolve_dns_mx(md or sender_domain):
                    mx_ips = await _resolve_dns_a(mx.get("exchange",""))
                    if sender_ip in mx_ips:
                        q = next((m["qualifier"] for m in parsed["mechanisms"] if m["mechanism"]=="mx"), "+")
                        result["spf_result"] = {"+":"pass","-":"fail","~":"softfail","?":"neutral"}.get(q,"pass")
                        result["matched_mechanism"] = "mx"; result["matched_rule"] = mx.get("exchange","")
                        result["explanations"].append(f"IP matches MX {mx.get('exchange','')}"); return result
            except Exception: continue
        if parsed.get("all_mechanism"):
            aq = parsed["all_mechanism"]
            result["spf_result"] = {"+":"pass","-":"fail","~":"softfail","?":"neutral"}.get(aq,"neutral")
            result["matched_mechanism"] = "all"; result["matched_rule"] = aq
            result["explanations"].append(f"Fell through to all ({aq})")
        else:
            result["spf_result"] = "neutral"
            result["explanations"].append("No matching mechanism; default neutral")
    except Exception as e:
        result["success"] = False; result["error"] = str(e); result["spf_result"] = "temperror"
    return result


async def spf_include_chain(domain: str) -> dict:
    result = {"success": True, "root_domain": domain, "chain": [], "depth": 0,
              "loop_detected": False, "truncated": False, "total_records": 0}
    visited, chain = set(), [{"domain": domain, "depth": 0}]
    to_process = [(domain, 0)]
    try:
        while to_process and len(chain) <= MAX_DNS_LOOKUPS:
            cur, depth = to_process.pop(0)
            if cur in visited:
                if cur != domain: result["loop_detected"] = True
                continue
            visited.add(cur)
            spf_check = await check_spf_record(cur)
            if not spf_check.get("has_spf"): continue
            parsed = await analyze_spf_record(spf_check["spf_record"])
            if not parsed["success"]: continue
            for inc in parsed.get("includes", []):
                if inc not in visited and len(chain) < MAX_DNS_LOOKUPS:
                    chain.append({"domain": inc, "depth": depth+1, "parent": cur})
                    to_process.append((inc, depth+1))
                    result["total_records"] += 1
        if len(chain) >= MAX_DNS_LOOKUPS and to_process: result["truncated"] = True
        result["chain"] = chain
        result["depth"] = max(e["depth"] for e in chain) if chain else 0
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def spf_recommendations(domain: str) -> dict:
    result = {"success": True, "domain": domain, "has_spf": False,
              "recommendations": [], "issues": [], "strength": "unknown"}
    try:
        spf_check = await check_spf_record(domain)
        if not spf_check.get("has_spf"):
            result["has_spf"] = False
            result["recommendations"].append({"priority":"critical","category":"spf",
                "message":f"No SPF record for {domain}.",
                "action":f"Add TXT: v=spf1 include:_spf.{domain} ~all"})
            result["issues"].append("No SPF record"); result["strength"]="none"; return result
        result["has_spf"] = True
        parsed = await analyze_spf_record(spf_check["spf_record"])
        if not parsed["success"]: return result
        if parsed.get("estimated_dns_lookups",0) > 10:
            result["recommendations"].append({"priority":"high","category":"dns_lookups",
                "message":f"SPF requires {parsed['estimated_dns_lookups']} DNS lookups (max 10).",
                "action":"Consolidate includes."})
            result["issues"].append("Exceeds 10 DNS lookup limit")
        if parsed.get("all_mechanism") != "-":
            an = {"+":"pass","-":"fail","~":"softfail","?":"neutral"}.get(parsed.get("all_mechanism","?"),"neutral")
            result["recommendations"].append({"priority":"high","category":"all_mechanism",
                "message":f"SPF all is '{an}' (should be 'fail').",
                "action":"Change to '-all' for hard fail."})
            result["issues"].append(f"All is '{an}' instead of 'fail'")
        if parsed.get("all_mechanism") == "-":
            result["recommendations"].append({"priority":"info","category":"spf",
                "message":"SPF uses -all (hard fail). Good posture.", "action":"Maintain."})
        result["strength"] = "strong" if not result["issues"] else ("moderate" if len(result["issues"])<=2 else "weak")
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def spf_dns_lookup_count(domain: str) -> dict:
    result = {"success": True, "domain": domain, "direct_lookups": 0,
              "include_lookups": 0, "a_lookups": 0, "mx_lookups": 0,
              "redirect_lookups": 0, "total_lookups": 0, "under_limit": True,
              "remaining": 10, "lookups_breakdown": []}
    try:
        spf_check = await check_spf_record(domain)
        if not spf_check.get("has_spf"):
            result["lookups_breakdown"].append({"type":"none","detail":f"No SPF for {domain}"})
            return result
        parsed = await analyze_spf_record(spf_check["spf_record"])
        if not parsed["success"]: return result
        result["direct_lookups"] = len(parsed.get("includes",[]))
        has_a = bool(parsed["a_mechanisms"] or any(m["mechanism"]=="a" for m in parsed.get("mechanisms",[])))
        has_mx = bool(parsed["mx_mechanisms"] or any(m["mechanism"]=="mx" for m in parsed.get("mechanisms",[])))
        result["a_lookups"] = 1 if has_a else 0
        result["mx_lookups"] = 1 if has_mx else 0
        result["redirect_lookups"] = 1 if parsed.get("redirect") else 0
        total = result["direct_lookups"]+result["a_lookups"]+result["mx_lookups"]+result["redirect_lookups"]
        result["total_lookups"] = total; result["under_limit"] = total <= 10
        result["remaining"] = max(0, 10-total)
        result["lookups_breakdown"] = [
            {"type":"include","count":result["include_lookups"],"max":"unlimited"},
            {"type":"a","count":result["a_lookups"],"max":1},
            {"type":"mx","count":result["mx_lookups"],"max":1},
            {"type":"redirect","count":result["redirect_lookups"],"max":1},
        ]
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result

# ── DKIM Analysis ─────────────────────────────────────────────────────────────

async def check_dkim_record(domain: str, selector: str) -> dict:
    result = {"success": True, "domain": domain, "selector": selector,
              "dkim_domain": f"{selector}._domainkey.{domain}",
              "records": [], "dkim_record": None, "has_dkim": False}
    try:
        dkim_domain = f"{selector}._domainkey.{domain}"
        result["dkim_domain"] = dkim_domain
        txt_records = await _resolve_dns_txt(dkim_domain)
        dkim_records = [t for t in txt_records if "v=DKIM1" in t]
        for txt in txt_records:
            for part in txt.split(";"):
                if part.strip().startswith("v=DKIM1"):
                    dkim_records.append(txt); break
        result["records"] = txt_records
        if dkim_records:
            result["dkim_record"] = dkim_records[0]
            result["has_dkim"] = True
            result["all_records"] = dkim_records
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def analyze_dkim_record(dkim_record: str) -> dict:
    result = {"success": True, "raw": dkim_record, "tags": {}, "version": None,
              "hash_algorithm": None, "key_type": None, "public_key": None,
              "service_type": None, "flags": [], "key_length": 0, "valid": False}
    if not dkim_record:
        return {"success": False, "error": "Empty DKIM record"}
    try:
        for part in dkim_record.split(";"):
            part = part.strip()
            if "=" not in part: continue
            k, v = part.split("=", 1); k = k.strip().lower(); v = v.strip()
            result["tags"][k] = v
            if k == "v": result["version"] = v; result["valid"] = v == "DKIM1"
            elif k == "h": result["hash_algorithm"] = v
            elif k == "k": result["key_type"] = v
            elif k == "p":
                result["public_key"] = v
                try: result["key_length"] = len(base64.b64decode(v)) * 8
                except: result["key_length"] = 0
            elif k == "s": result["service_type"] = v
            elif k == "t":
                flags = [f.strip() for f in v.split(":") if f.strip()]
                result["flags"] = flags
                for flag in flags:
                    if flag == "y": result["testing_mode"] = True
                    elif flag == "s": result["strict_mode"] = True
        if not result.get("version") and dkim_record.strip().startswith("v=DKIM1"):
            result["version"] = "DKIM1"; result["valid"] = True
        kl = result.get("key_length", 0)
        result["key_strength_assessment"] = "strong" if kl>=1024 else "weak"
        if 0 < kl < 1024:
            result["key_warning"] = f"Key length ({kl} bits) below recommended 1024"
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def extract_dkim_signatures(raw_headers: str) -> dict:
    result = {"success": True, "signatures": [], "count": 0, "parsed_tags": []}
    try:
        parser = email.parser.HeaderParser(policy=email.policy.default)
        if isinstance(raw_headers, bytes):
            msg = parser.parsestr(_safe_decode_bytes(raw_headers))
        else:
            msg = parser.parsestr(raw_headers)
        dkim_headers = msg.get_all("DKIM-Signature", [])
        result["count"] = len(dkim_headers)
        for sig_raw in dkim_headers:
            sig = {"raw": sig_raw, "tags": {}}
            for part in sig_raw.split(";"):
                part = part.strip()
                if "=" not in part: continue
                k, v = part.split("=", 1); k = k.strip().lower(); v = v.strip()
                sig["tags"][k] = v
                if k == "bh": sig["body_hash"] = v
                elif k == "d": sig["domain"] = v; result["domain"] = v
                elif k == "s": sig["selector"] = v; result["selector"] = v
                elif k == "b":
                    sig["signature_value"] = v[:30]+"..." if len(v)>30 else v
                    sig["signature_length"] = len(v)
                elif k == "h": sig["signed_headers"] = [h.strip() for h in v.split(":")]
                elif k == "a": sig["algorithm"] = v
                elif k == "c": sig["canonicalization"] = v
                elif k == "i": sig["identity"] = v
                elif k == "l": sig["body_length"] = v
                elif k == "t":
                    try:
                        sig["signature_timestamp"] = int(v)
                        sig["signature_time"] = datetime.fromtimestamp(int(v), tz=timezone.utc).isoformat()
                    except: sig["signature_timestamp"] = v
                elif k == "x":
                    try:
                        sig["expiry_timestamp"] = int(v)
                        sig["expiry_time"] = datetime.fromtimestamp(int(v), tz=timezone.utc).isoformat()
                    except: sig["expiry_timestamp"] = v
            result["signatures"].append(sig)
            result["parsed_tags"].append(sig["tags"])
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


# ── DMARC Functions ─────────────────────────────────────────────────────────────


async def check_dmarc_record(domain: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    result = {"success": True, "domain": domain, "record": None, "tags": {},
              "raw": None, "has_dmarc": False, "query_time": None}
    t0 = time.monotonic()
    try:
        dmarc_domain = f"_dmarc.{domain}"
        txt_records = await _resolve_dns_txt(dmarc_domain)
        dmarc_records = [t for t in txt_records if "v=DMARC1" in t]
        result["raw"] = txt_records
        if dmarc_records:
            result["record"] = dmarc_records[0]
            result["has_dmarc"] = True
            parsed = _parse_dmarc_record(dmarc_records[0])
            result["tags"] = parsed.get("tags", {})
            result["valid_syntax"] = parsed.get("valid", False)
            result["policy"] = result["tags"].get("p")
            result["subdomain_policy"] = result["tags"].get("sp")
            result["pct"] = result["tags"].get("pct", "100")
            result["rua"] = result["tags"].get("rua")
            result["ruf"] = result["tags"].get("ruf")
        result["query_time"] = time.monotonic() - t0
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
        result["query_time"] = time.monotonic() - t0
    return result


async def analyze_dmarc_record(dmarc_record: str) -> dict:
    result = {"success": True, "raw": dmarc_record, "tags": {}, "is_valid": False,
              "policy_summary": {}, "version": None, "policy": None,
              "subdomain_policy": None, "pct": "100", "rua": None, "ruf": None}
    if not dmarc_record:
        return {"success": False, "error": "Empty DMARC record", "raw": dmarc_record}
    try:
        parsed = _parse_dmarc_record(dmarc_record)
        result["tags"] = parsed.get("tags", {})
        result["is_valid"] = parsed.get("valid", False)
        tags = result["tags"]
        result["version"] = tags.get("v")
        result["policy"] = tags.get("p")
        result["subdomain_policy"] = tags.get("sp")
        result["pct"] = tags.get("pct", "100")
        result["rua"] = tags.get("rua")
        result["ruf"] = tags.get("ruf")
        result["report_format"] = tags.get("rf", "afrf")
        result["report_interval"] = tags.get("ri", "86400")
        result["failure_options"] = tags.get("fo", "0")
        result["adkim"] = tags.get("adkim", "r")
        result["aspf"] = tags.get("aspf", "r")
        p = result["policy"]
        sp = result["subdomain_policy"]
        pct_val = int(result["pct"]) if result["pct"].isdigit() else 100
        result["policy_summary"] = {
            "policy": p or "none",
            "subdomain_policy": sp or p or "none",
            "pct": pct_val,
            "reporting_enabled": bool(result["rua"]),
            "has_failure_reporting": bool(result["ruf"]),
            "is_strict_adkim": tags.get("adkim") == "s",
            "is_strict_aspf": tags.get("aspf") == "s",
            "is_strict": tags.get("adkim") == "s" and tags.get("aspf") == "s",
        }
        strength = 0
        if p == "reject": strength = 3
        elif p == "quarantine": strength = 2
        elif p == "none": strength = 1
        result["policy_strength"] = strength
        result["policy_assessment"] = {3: "strict", 2: "moderate", 1: "monitoring", 0: "none"}.get(strength, "unknown")
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def dmarc_policy_analysis(domain: str) -> dict:
    result = {"success": True, "domain": domain, "policy": "none",
              "recommended_actions": [], "compliance_score": 0,
              "findings": [], "strength": "none"}
    try:
        dmarc_check = await check_dmarc_record(domain)
        if not dmarc_check.get("has_dmarc"):
            result["findings"].append(f"No DMARC record for {domain}")
            result["recommended_actions"].append({"priority":"critical","action":"Add DMARC record with p=reject"})
            return result
        parsed = await analyze_dmarc_record(dmarc_check["record"])
        if not parsed["success"]:
            result["findings"].append(f"DMARC parse error: {parsed.get('error')}")
            return result
        result["policy"] = parsed["policy"]
        result["parsed"] = parsed
        score = 0
        p = parsed.get("policy")
        if p == "reject": score += 40
        elif p == "quarantine": score += 25
        elif p == "none": score += 10
        sp = parsed.get("subdomain_policy")
        if sp == "reject": score += 20
        elif sp == "quarantine": score += 15
        elif sp == "none": score += 5
        if parsed.get("rua"): score += 15
        if parsed.get("ruf"): score += 10
        pct = int(parsed.get("pct", "0"))
        score += int(round(pct * 0.15))
        if parsed.get("adkim") == "s": score += 5
        if parsed.get("aspf") == "s": score += 5
        score = min(100, score)
        result["compliance_score"] = score
        if score >= 80: result["strength"] = "strong"
        elif score >= 50: result["strength"] = "moderate"
        elif score >= 25: result["strength"] = "weak"
        else: result["strength"] = "very_weak"
        if p != "reject":
            result["recommended_actions"].append({"priority":"high","action":f"Change DMARC policy from '{p}' to 'reject'"})
        if not sp:
            result["recommended_actions"].append({"priority":"medium","action":"Set subdomain policy (sp=reject)"})
        if not parsed.get("rua"):
            result["recommended_actions"].append({"priority":"medium","action":"Configure rua for aggregate reports"})
        if pct < 100:
            result["recommended_actions"].append({"priority":"medium","action":f"Increase pct from {pct} to 100"})
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def dmarc_recommendations(domain: str) -> dict:
    result = {"success": True, "domain": domain, "has_dmarc": False,
              "recommendations": [], "issues": [], "strength": "unknown"}
    try:
        dmarc_check = await check_dmarc_record(domain)
        if not dmarc_check.get("has_dmarc"):
            result["issues"].append("No DMARC record")
            result["recommendations"].append({"priority":"critical","category":"dmarc",
                "message":f"No DMARC record for {domain}.","action":f"Add TXT _dmarc.{domain}: v=DMARC1; p=reject; sp=reject; pct=100; rua=mailto:dmarc@{domain}"})
            result["strength"] = "none"; return result
        result["has_dmarc"] = True
        parsed = await analyze_dmarc_record(dmarc_check["record"])
        if not parsed["success"]: return result
        p = parsed.get("policy")
        if p != "reject":
            result["issues"].append(f"Policy is '{p}' instead of 'reject'")
            result["recommendations"].append({"priority":"high","category":"policy",
                "message":f"DMARC policy is '{p}'.","action":"Change to p=reject for strictest enforcement."})
        sp = parsed.get("subdomain_policy")
        if not sp:
            result["issues"].append("No subdomain policy (sp) set")
            result["recommendations"].append({"priority":"high","category":"subdomain",
                "message":"No subdomain policy.","action":"Add sp=reject to cover all subdomains."})
        elif sp != "reject":
            result["issues"].append(f"Subdomain policy is '{sp}'")
            result["recommendations"].append({"priority":"high","category":"subdomain",
                "message":f"Subdomain policy is '{sp}'.","action":"Change sp=reject."})
        if not parsed.get("rua"):
            result["recommendations"].append({"priority":"medium","category":"reporting",
                "message":"No aggregate report URI (rua).","action":"Add rua=mailto:dmarc@{domain}"})
        if not parsed.get("ruf"):
            result["recommendations"].append({"priority":"low","category":"reporting",
                "message":"No forensic report URI (ruf).","action":"Add ruf=mailto:dmarc-forensic@{domain}"})
        pct = int(parsed.get("pct", "0"))
        if pct < 100:
            result["issues"].append(f"Policy applies to only {pct}% of email")
            result["recommendations"].append({"priority":"medium","category":"pct",
                "message":f"Policy applies to {pct}%.","action":"Set pct=100 for full coverage."})
        if parsed.get("adkim") != "s":
            result["recommendations"].append({"priority":"low","category":"alignment",
                "message":"DKIM alignment is relaxed (adkim=r).","action":"Set adkim=s for strict DKIM alignment."})
        if parsed.get("aspf") != "s":
            result["recommendations"].append({"priority":"low","category":"alignment",
                "message":"SPF alignment is relaxed (aspf=r).","action":"Set aspf=s for strict SPF alignment."})
        result["strength"] = "strong" if not result["issues"] else ("moderate" if len(result["issues"])<=2 else "weak")
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def validate_dmarc(domain: str) -> dict:
    result = {"success": True, "domain": domain, "valid": False,
              "warnings": [], "errors": [], "checks": {}}
    try:
        dmarc_check = await check_dmarc_record(domain)
        if not dmarc_check.get("has_dmarc"):
            result["errors"].append("No DMARC record found")
            result["checks"]["record_exists"] = False
            return result
        result["checks"]["record_exists"] = True
        parsed = await analyze_dmarc_record(dmarc_check["record"])
        if not parsed["success"]:
            result["errors"].append("DMARC record parse failed")
            result["valid"] = False; return result
        result["checks"]["syntax_valid"] = parsed.get("is_valid", False)
        if not parsed.get("is_valid"):
            result["errors"].append("Invalid DMARC syntax (missing v=DMARC1)")
            return result
        p = parsed.get("policy")
        if p not in ("none", "quarantine", "reject"):
            result["errors"].append(f"Invalid policy: {p}")
        else:
            result["checks"]["policy_set"] = True
            if p == "none":
                result["warnings"].append("Policy is 'none' (monitoring only, no enforcement)")
        sp = parsed.get("subdomain_policy")
        if sp and sp not in ("none", "quarantine", "reject"):
            result["errors"].append(f"Invalid subdomain policy: {sp}")
        else:
            result["checks"]["subdomain_policy_set"] = bool(sp)
        if parsed.get("pct"):
            try:
                pct = int(parsed.get("pct", "0"))
                if pct < 1 or pct > 100:
                    result["errors"].append(f"pct out of range: {pct}")
                elif pct < 100:
                    result["warnings"].append(f"pct={pct} (not full coverage)")
            except ValueError:
                result["errors"].append(f"Invalid pct value: {parsed.get('pct')}")
        rua = parsed.get("rua")
        if rua:
            if "mailto:" not in rua:
                result["warnings"].append(f"rua missing mailto: scheme ({rua})")
            result["checks"]["reporting_configured"] = True
        else:
            result["warnings"].append("No rua configured for aggregate reports")
            result["checks"]["reporting_configured"] = False
        ruf = parsed.get("ruf")
        if ruf and "mailto:" not in ruf:
            result["warnings"].append(f"ruf missing mailto: scheme ({ruf})")
        result["valid"] = len(result["errors"]) == 0
        result["checks"]["policy"] = p
        result["checks"]["subdomain_policy"] = sp
        result["checks"]["pct"] = parsed.get("pct")
        result["checks"]["rua"] = rua
        result["checks"]["ruf"] = ruf
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


# ── DKIM Helper Functions ────────────────────────────────────────────────────────


async def decoded_dkim_public_key(domain: str, selector: str = "default") -> dict:
    result = {"success": True, "domain": domain, "selector": selector,
              "public_key": None, "key_type": None, "key_length": 0,
              "tags": {}, "has_record": False}
    try:
        dkim_check = await check_dkim_record(domain, selector)
        if not dkim_check.get("has_dkim"):
            result["error"] = f"No DKIM record for {selector}._domainkey.{domain}"
            return result
        result["has_record"] = True
        analyzed = await analyze_dkim_record(dkim_check["dkim_record"])
        if not analyzed["success"]:
            result["error"] = f"Parse error: {analyzed.get('error')}"
            return result
        result["tags"] = analyzed.get("tags", {})
        result["key_type"] = analyzed.get("key_type")
        result["key_length"] = analyzed.get("key_length", 0)
        result["hash_algorithm"] = analyzed.get("hash_algorithm")
        result["flags"] = analyzed.get("flags", [])
        result["testing_mode"] = analyzed.get("testing_mode", False)
        result["strict_mode"] = analyzed.get("strict_mode", False)
        raw_pubkey = analyzed.get("public_key")
        if raw_pubkey:
            result["public_key"] = raw_pubkey[:60] + "..." if len(raw_pubkey) > 60 else raw_pubkey
        result["key_strength"] = analyzed.get("key_strength_assessment", "unknown")
        if 0 < result["key_length"] < 1024:
            result["key_warning"] = f"Key length ({result['key_length']} bits) below recommended 1024"
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def dkim_selector_guess(domain: str) -> dict:
    result = {"success": True, "domain": domain, "selectors_tried": [],
              "found_selectors": [], "results": {}, "best_selector": None}
    try:
        for sel in COMMON_DKIM_SELECTORS:
            entry = {"selector": sel, "domain": f"{sel}._domainkey.{domain}", "found": False}
            try:
                pk_info = await decoded_dkim_public_key(domain, sel)
                entry["found"] = pk_info.get("has_record", False)
                if pk_info.get("has_record"):
                    entry["key_length"] = pk_info.get("key_length", 0)
                    entry["key_type"] = pk_info.get("key_type")
                    entry["key_strength"] = pk_info.get("key_strength", "unknown")
                    result["found_selectors"].append(sel)
                    if not result["best_selector"] or pk_info.get("key_length", 0) > result.get("best_key_length", 0):
                        result["best_selector"] = sel
                        result["best_key_length"] = pk_info.get("key_length", 0)
                result["results"][sel] = entry
            except Exception as e:
                entry["error"] = str(e)
            result["selectors_tried"].append(sel)
        result["selectors_found"] = len(result["found_selectors"])
        result["has_dkim"] = len(result["found_selectors"]) > 0
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def dkim_recommendations(domain: str, selector: str = "default") -> dict:
    result = {"success": True, "domain": domain, "selector": selector,
              "has_dkim": False, "recommendations": [], "issues": [],
              "strength": "unknown", "key_length": 0}
    try:
        dkim_check = await check_dkim_record(domain, selector)
        if not dkim_check.get("has_dkim"):
            result["issues"].append("No DKIM record")
            result["recommendations"].append({"priority":"critical","category":"dkim",
                "message":f"No DKIM record for {selector}._domainkey.{domain}.",
                "action":f"Add DKIM record for selector '{selector}'."})
            result["strength"] = "none"; return result
        result["has_dkim"] = True
        analyzed = await analyze_dkim_record(dkim_check["dkim_record"])
        if not analyzed["success"]: return result
        kl = analyzed.get("key_length", 0)
        result["key_length"] = kl
        if kl < 1024:
            result["issues"].append(f"Key length {kl} bits (minimum 1024 recommended)")
            result["recommendations"].append({"priority":"high","category":"key_length",
                "message":f"DKIM key is only {kl} bits.","action":"Generate a 2048-bit RSA key for better security."})
        elif kl < 2048:
            result["recommendations"].append({"priority":"medium","category":"key_length",
                "message":f"DKIM key is {kl} bits.","action":"Consider upgrading to 2048-bit key."})
        hash_algo = analyzed.get("hash_algorithm", "")
        if hash_algo and "sha256" not in hash_algo.lower() and "sha1" in hash_algo.lower():
            result["issues"].append("Using SHA-1 hash algorithm (SHA-256 recommended)")
            result["recommendations"].append({"priority":"high","category":"hash",
                "message":"DKIM uses SHA-1.","action":"Upgrade to SHA-256 (h=sha256)."})
        flags = analyzed.get("flags", [])
        if "y" in flags:
            result["recommendations"].append({"priority":"warning","category":"testing",
                "message":"DKIM is in testing mode (t=y).","action":"Remove t=y flag for production."})
        key_type = analyzed.get("key_type", "")
        if key_type and key_type != "rsa":
            result["recommendations"].append({"priority":"info","category":"key_type",
                "message":f"DKIM uses {key_type} key.","action":"Ensure compatibility across receivers."})
        if kl >= 2048 and "sha256" in (hash_algo or "").lower():
            result["recommendations"].append({"priority":"good","category":"dkim",
                "message":"DKIM configuration looks strong.","action":"Maintain current settings."})
        result["strength"] = "strong" if kl >= 2048 else ("moderate" if kl >= 1024 else "weak")
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


# ── Security Scoring ──────────────────────────────────────────────────────────────


async def email_security_score(domain: str) -> dict:
    result = {"success": True, "domain": domain, "scores": {},
              "total": 0, "grade": "F", "findings": [],
              "spf_score": 0, "dkim_score": 0, "dmarc_score": 0}
    try:
        spf_check = await check_spf_record(domain)
        spf_score = 0
        if spf_check.get("has_spf"):
            parsed = await analyze_spf_record(spf_check["spf_record"])
            if parsed["success"]:
                if parsed.get("all_mechanism") == "-":
                    spf_score = 30
                    result["findings"].append("SPF: -all (hard fail) configured")
                elif parsed.get("all_mechanism") == "~":
                    spf_score = 20
                    result["findings"].append("SPF: ~all (soft fail) configured")
                elif parsed.get("all_mechanism"):
                    spf_score = 10
                    result["findings"].append("SPF: all mechanism present but not hard fail")
                else:
                    spf_score = 5
                    result["findings"].append("SPF: no all mechanism")
                if parsed.get("estimated_dns_lookups", 0) > 10:
                    spf_score = max(0, spf_score - 10)
                    result["findings"].append("SPF: exceeds 10 DNS lookup limit")
            else:
                spf_score = 0
                result["findings"].append("SPF: record exists but unparseable")
        else:
            result["findings"].append("SPF: no record")
        result["spf_score"] = spf_score
        dkim_score = 0
        selector_check = await dkim_selector_guess(domain)
        if selector_check.get("has_dkim"):
            best = selector_check.get("best_selector")
            if best:
                pk_info = await decoded_dkim_public_key(domain, best)
                kl = pk_info.get("key_length", 0)
                if kl >= 2048:
                    dkim_score = 30
                    result["findings"].append(f"DKIM: {best} selector, {kl}-bit key")
                elif kl >= 1024:
                    dkim_score = 20
                    result["findings"].append(f"DKIM: {best} selector, {kl}-bit key (1024+ OK)")
                else:
                    dkim_score = 15
                    result["findings"].append(f"DKIM: {best} selector, {kl}-bit key (weak)")
                if pk_info.get("testing_mode"):
                    dkim_score = max(0, dkim_score - 10)
                    result["findings"].append("DKIM: in testing mode (t=y)")
            else:
                dkim_score = 10
                result["findings"].append("DKIM: record exists but selector unknown")
        else:
            result["findings"].append("DKIM: no record found")
        result["dkim_score"] = dkim_score
        dmarc_check = await check_dmarc_record(domain)
        dmarc_score = 0
        if dmarc_check.get("has_dmarc"):
            parsed = await analyze_dmarc_record(dmarc_check["record"])
            if parsed["success"]:
                p = parsed.get("policy")
                if p == "reject":
                    dmarc_score = 40
                    result["findings"].append(f"DMARC: p={p}")
                elif p == "quarantine":
                    dmarc_score = 30
                    result["findings"].append(f"DMARC: p={p}")
                elif p == "none":
                    dmarc_score = 15
                    result["findings"].append(f"DMARC: p={p} (monitoring only)")
                if parsed.get("rua"): dmarc_score += 5
                if parsed.get("ruf"): dmarc_score += 5
                if parsed.get("adkim") == "s": dmarc_score += 3
                if parsed.get("aspf") == "s": dmarc_score += 2
                pct = int(parsed.get("pct", "0"))
                if pct < 100: dmarc_score = max(0, dmarc_score - 5)
            else:
                dmarc_score = 0
                result["findings"].append("DMARC: record exists but unparseable")
        else:
            result["findings"].append("DMARC: no record")
        dmarc_score = min(55, dmarc_score)
        result["dmarc_score"] = dmarc_score
        total = spf_score + dkim_score + dmarc_score
        result["total"] = total
        result["scores"] = {"spf": spf_score, "dkim": dkim_score, "dmarc": dmarc_score, "total": total}
        if total >= 90: result["grade"] = "A"
        elif total >= 75: result["grade"] = "B"
        elif total >= 55: result["grade"] = "C"
        elif total >= 35: result["grade"] = "D"
        else: result["grade"] = "F"
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def email_security_report(domain: str) -> dict:
    result = {"success": True, "domain": domain, "executive_summary": {},
              "spf": {}, "dkim": {}, "dmarc": {}, "mta_sts": {},
              "tls_rpt": {}, "bimi": {}, "recommendations": [],
              "score": 0, "grade": "F"}
    try:
        scoring = await email_security_score(domain)
        result["score"] = scoring.get("total", 0)
        result["grade"] = scoring.get("grade", "F")
        spf_check = await check_spf_record(domain)
        spf_rec = await spf_recommendations(domain)
        result["spf"] = {"has_spf": spf_check.get("has_spf"), "record": spf_check.get("spf_record"),
                         "strength": spf_rec.get("strength"), "issues": spf_rec.get("issues", [])}
        dkim_guess = await dkim_selector_guess(domain)
        best = dkim_guess.get("best_selector", "default")
        dkim_rec = await dkim_recommendations(domain, best)
        result["dkim"] = {"has_dkim": dkim_guess.get("has_dkim"), "selectors": dkim_guess.get("found_selectors"),
                          "best_selector": best, "key_length": dkim_rec.get("key_length"),
                          "strength": dkim_rec.get("strength"), "issues": dkim_rec.get("issues", [])}
        dmarc_check = await check_dmarc_record(domain)
        dmarc_rec = await dmarc_recommendations(domain)
        result["dmarc"] = {"has_dmarc": dmarc_check.get("has_dmarc"), "record": dmarc_check.get("record"),
                           "policy": dmarc_check.get("policy"),
                           "strength": dmarc_rec.get("strength"), "issues": dmarc_rec.get("issues", [])}
        try:
            mta = await check_mta_sts(domain)
            result["mta_sts"] = {"has_mta_sts": mta.get("has_mta_sts", False), "mode": mta.get("mode"),
                                 "mx": mta.get("mx"), "errors": mta.get("errors", [])}
        except Exception:
            result["mta_sts"] = {"has_mta_sts": False}
        try:
            tls = await check_tls_rpt(domain)
            result["tls_rpt"] = {"has_tls_rpt": tls.get("has_tls_rpt", False), "record": tls.get("record")}
        except Exception:
            result["tls_rpt"] = {"has_tls_rpt": False}
        try:
            bimi = await check_bimi_record(domain)
            result["bimi"] = {"has_bimi": bimi.get("has_bimi", False), "logo_url": bimi.get("logo_url")}
        except Exception:
            result["bimi"] = {"has_bimi": False}
        result["executive_summary"] = {
            "domain": domain, "overall_score": result["score"],
            "grade": result["grade"], "spf": result["spf"].get("strength", "unknown"),
            "dkim": result["dkim"].get("strength", "unknown"),
            "dmarc": result["dmarc"].get("strength", "unknown"),
            "recommendation_count": len(spf_rec.get("recommendations", [])) + len(dkim_rec.get("recommendations", [])) + len(dmarc_rec.get("recommendations", [])),
        }
        result["recommendations"] = (spf_rec.get("recommendations", []) +
                                     dkim_rec.get("recommendations", []) +
                                     dmarc_rec.get("recommendations", []))
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def compare_security_scores(domains: list[str]) -> dict:
    result = {"success": True, "domains": [], "ranked": [],
              "best": None, "worst": None, "average": 0}
    try:
        tasks = [email_security_score(d) for d in domains]
        scores = await asyncio.gather(*tasks, return_exceptions=True)
        domain_scores = []
        total = 0; count = 0
        for i, d in enumerate(domains):
            s = scores[i]
            if isinstance(s, Exception):
                domain_scores.append({"domain": d, "score": 0, "grade": "F", "error": str(s)})
                continue
            domain_scores.append({
                "domain": d, "score": s.get("total", 0), "grade": s.get("grade", "F"),
                "spf_score": s.get("spf_score", 0), "dkim_score": s.get("dkim_score", 0),
                "dmarc_score": s.get("dmarc_score", 0),
            })
            total += s.get("total", 0); count += 1
        domain_scores.sort(key=lambda x: x["score"], reverse=True)
        result["ranked"] = domain_scores
        result["domains"] = [ds["domain"] for ds in domain_scores]
        if domain_scores:
            result["best"] = domain_scores[0]
            result["worst"] = domain_scores[-1]
        result["average"] = round(total / count, 1) if count else 0
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


# ── Email Verification ────────────────────────────────────────────────────────────


async def verify_email_format(email_addr: str) -> dict:
    result = {"success": True, "email": email_addr, "is_valid": False,
              "issues": [], "format_checks": {}}
    try:
        if not email_addr or "@" not in email_addr:
            result["issues"].append("Missing @ symbol")
            result["format_checks"]["has_at"] = False; return result
        result["format_checks"]["has_at"] = True
        local, at, domain = email_addr.partition("@")
        result["format_checks"]["local_part"] = local
        result["format_checks"]["domain"] = domain
        if not local:
            result["issues"].append("Empty local part")
        elif len(local) > 64:
            result["issues"].append(f"Local part too long ({len(local)} chars, max 64)")
        elif local.startswith(".") or local.endswith("."):
            result["issues"].append("Local part starts or ends with dot")
        elif ".." in local:
            result["issues"].append("Consecutive dots in local part")
        else:
            invalid_chars = set(local) - set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.!#$%&'*+/=?^_`{|}~-")
            if invalid_chars:
                result["issues"].append(f"Invalid characters in local part: {''.join(invalid_chars)}")
        if not domain:
            result["issues"].append("Empty domain")
        elif len(domain) > 255:
            result["issues"].append(f"Domain too long ({len(domain)} chars, max 255)")
        elif "." not in domain:
            result["issues"].append("Domain missing dot (no TLD)")
        else:
            tld = domain.rsplit(".", 1)[-1]
            if len(tld) < 2:
                result["issues"].append(f"TLD too short: .{tld}")
            elif not tld.isalpha():
                result["issues"].append(f"TLD has non-alpha characters: .{tld}")
            for label in domain.split("."):
                if label and (label.startswith("-") or label.endswith("-")):
                    result["issues"].append(f"Domain label starts/ends with hyphen: {label}")
                    break
        regex = r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$"
        result["format_checks"]["regex_valid"] = bool(re.match(regex, email_addr))
        if not result["format_checks"]["regex_valid"]:
            result["issues"].append("Failed regex validation")
        rfc_spec = re.match(r'^[^@]+@[^@]+$', email_addr)
        result["format_checks"]["rfc_valid"] = bool(rfc_spec)
        result["is_valid"] = len(result["issues"]) == 0 and result["format_checks"]["regex_valid"]
        result["local_part_length"] = len(local)
        result["domain_length"] = len(domain)
        result["total_length"] = len(email_addr)
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def verify_email_domain(email_addr: str) -> dict:
    result = {"success": True, "email": email_addr, "domain": "",
              "has_mx": False, "mx_records": [], "has_a": False,
              "a_records": [], "resolves": False}
    try:
        domain = _extract_domain(email_addr)
        if not domain:
            result["error"] = "Could not extract domain"; return result
        result["domain"] = domain
        mx_records = await _resolve_dns_mx(domain)
        if mx_records:
            result["has_mx"] = True
            result["mx_records"] = mx_records
            result["resolves"] = True
        a_records = await _resolve_dns_a(domain)
        if a_records:
            result["has_a"] = True
            result["a_records"] = a_records
            result["resolves"] = True
        if not result["resolves"]:
            result["error"] = f"Domain {domain} does not resolve"
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def verify_email_smtp(email_addr: str, timeout: int = 15) -> dict:
    result = {"success": True, "email": email_addr, "is_deliverable": False,
              "smtp_response": "", "server": "", "error": None}
    try:
        domain = _extract_domain(email_addr)
        if not domain:
            result["error"] = "Could not extract domain"; return result
        mx_records = await _resolve_dns_mx(domain)
        if not mx_records:
            result["error"] = f"No MX records for {domain}"
            return result
        mx_records.sort(key=lambda x: x.get("preference", 0))
        target = mx_records[0].get("exchange", "")
        result["server"] = target
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            resp = await loop.run_in_executor(pool, lambda: _smtp_verify_connect(target, email_addr, timeout))
            result.update(resp)
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


def _smtp_verify_connect(server: str, email_addr: str, timeout: int) -> dict:
    r = {"is_deliverable": False, "smtp_response": "", "server": server}
    try:
        s = socket.create_connection((server, 25), timeout=timeout)
        s.settimeout(timeout)
        def recv():
            data = b""
            while True:
                try: chunk = s.recv(4096)
                except: break
                if not chunk: break
                data += chunk
                if b"\r\n" in data: break
            return data.decode("utf-8", errors="replace").strip()
        banner = recv()
        r["banner"] = banner
        s.sendall(f"EHLO verify-check.local\r\n".encode())
        ehlo = recv()
        r["ehlo_response"] = ehlo[:200] if len(ehlo) > 200 else ehlo
        s.sendall(f"MAIL FROM:<verify@check.local>\r\n".encode())
        mfrom = recv()
        r["mail_from_response"] = mfrom
        s.sendall(f"RCPT TO:<{email_addr}>\r\n".encode())
        rcpt = recv()
        r["rcpt_response"] = rcpt
        r["smtp_response"] = rcpt[:200] if len(rcpt) > 200 else rcpt
        if "250" in rcpt or "OK" in rcpt:
            r["is_deliverable"] = True
        elif "550" in rcpt and ("reject" in rcpt.lower() or "not exist" in rcpt.lower() or "invalid" in rcpt.lower()):
            r["is_deliverable"] = False
        elif "450" in rcpt or "451" in rcpt:
            r["is_deliverable"] = None
            r["smtp_response"] = f"Temporary failure: {rcpt[:100]}"
        s.sendall(b"QUIT\r\n")
        s.close()
    except socket.timeout:
        r["smtp_response"] = "Connection timed out"; r["error"] = "timeout"
    except ConnectionRefusedError:
        r["smtp_response"] = "Connection refused"; r["error"] = "refused"
    except Exception as e:
        r["smtp_response"] = str(e)[:100]; r["error"] = str(e)
    return r


async def email_disposable_check(email_addr: str) -> dict:
    result = {"success": True, "email": email_addr, "is_disposable": False,
              "matched_domain": None, "reason": None}
    try:
        domain = _extract_domain(email_addr)
        if not domain:
            result["error"] = "Could not extract domain"; return result
        result["checked_domain"] = domain
        if domain in DISPOSABLE_DOMAINS:
            result["is_disposable"] = True
            result["matched_domain"] = domain
            result["reason"] = "Known disposable domain"
            return result
        for dd in KNOWN_DISPOSABLE_DOMAINS:
            if domain == dd or domain.endswith("." + dd):
                result["is_disposable"] = True
                result["matched_domain"] = dd
                result["reason"] = f"Matched known disposable: {dd}"
                return result
        patterns = [r"^temp", r"^throwaway", r"^dispos", r"10minute", r"guerrilla",
                    r"mailinator", r"trashmail", r"yopmail", r"fakeinbox"]
        for pat in patterns:
            if re.search(pat, domain, re.I):
                result["is_disposable"] = True
                result["matched_domain"] = domain
                result["reason"] = f"Pattern match: {pat}"
                return result
        local, _, _ = email_addr.partition("@")
        if "+" in local:
            plus_domain = local.split("+")[1] if len(local.split("+")) > 1 else ""
            if plus_domain and plus_domain in KNOWN_DISPOSABLE_DOMAINS:
                result["is_disposable"] = True
                result["matched_domain"] = plus_domain
                result["reason"] = "Plus-address matching disposable domain"
                return result
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def email_role_account_check(email_addr: str) -> dict:
    result = {"success": True, "email": email_addr, "is_role": False,
              "matched_pattern": None, "matched_type": None}
    try:
        local, _, _ = email_addr.partition("@")
        local_lower = local.lower()
        result["local_part"] = local_lower
        if local_lower in KNOWN_ROLE_ACCOUNTS:
            result["is_role"] = True
            result["matched_pattern"] = local_lower
            result["matched_type"] = "exact role match"
            return result
        for prefix in ROLE_PREFIXES:
            if local_lower.startswith(prefix):
                result["is_role"] = True
                result["matched_pattern"] = f"{prefix}*"
                result["matched_type"] = f"prefix match: {prefix}"
                return result
        if local_lower.endswith("s") and local_lower[:-1] in ROLE_PREFIXES:
            result["is_role"] = True
            result["matched_pattern"] = f"{local_lower[:-1]}s"
            result["matched_type"] = "pluralized role"
            return result
        role_suffixes = ["-team", "-group", "-dept", "-department", "-help", "-support"]
        for suffix in role_suffixes:
            if local_lower.endswith(suffix):
                result["is_role"] = True
                result["matched_pattern"] = f"*{suffix}"
                result["matched_type"] = f"suffix match: {suffix}"
                return result
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


# ── Reputation ────────────────────────────────────────────────────────────────────


async def check_email_reputation(email_addr: str) -> dict:
    result = {"success": True, "email": email_addr, "reputation_score": 50,
              "breach_count": 0, "risk_level": "medium",
              "breaches": [], "findings": []}
    try:
        domain = _extract_domain(email_addr)
        result["domain"] = domain
        breach_data = await _check_breach_api(email_addr)
        breaches = breach_data.get("breaches", [])
        result["breaches"] = breaches
        result["breach_count"] = breach_data.get("count", 0)
        if breach_data.get("found"):
            result["findings"].append(f"Found in {breach_data['count']} breach(es)")
            bc = breach_data["count"]
            if bc >= 5: result["reputation_score"] = 10
            elif bc >= 3: result["reputation_score"] = 25
            elif bc >= 1: result["reputation_score"] = 40
        else:
            result["reputation_score"] = 70
            result["findings"].append("No known breaches")
        disp_check = await email_disposable_check(email_addr)
        if disp_check.get("is_disposable"):
            result["reputation_score"] = min(result["reputation_score"], 20)
            result["findings"].append("Disposable email domain")
        role_check = await email_role_account_check(email_addr)
        if role_check.get("is_role"):
            result["reputation_score"] = max(0, result["reputation_score"] - 10)
            result["findings"].append("Role-based email address")
        mx_check = await verify_email_domain(email_addr)
        if not mx_check.get("has_mx"):
            result["reputation_score"] = max(0, result["reputation_score"] - 20)
            result["findings"].append("Domain has no MX records")
        if result["reputation_score"] >= 70: result["risk_level"] = "low"
        elif result["reputation_score"] >= 40: result["risk_level"] = "medium"
        else: result["risk_level"] = "high"
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


# ── Forensic Functions ────────────────────────────────────────────────────────────


async def forensic_investigate(raw_headers: str) -> dict:
    result = {"success": True, "verdict": "inconclusive",
              "spoof_detection": {}, "auth_results": {}, "header_forging": {},
              "spoof_score": {}, "indicators": [], "risk_level": "unknown"}
    try:
        spoof_task = detect_email_spoofing(raw_headers)
        auth_task = extract_authentication_results(raw_headers)
        forging_task = detect_header_forging(raw_headers)
        score_task = forensic_spoof_score(raw_headers)
        spoof, auth, forging, score = await asyncio.gather(
            spoof_task, auth_task, forging_task, score_task, return_exceptions=True)
        result["spoof_detection"] = spoof if not isinstance(spoof, Exception) else {"error": str(spoof)}
        result["auth_results"] = auth if not isinstance(auth, Exception) else {"error": str(auth)}
        result["header_forging"] = forging if not isinstance(forging, Exception) else {"error": str(forging)}
        result["spoof_score"] = score if not isinstance(score, Exception) else {"error": str(score)}
        indicators = []
        if isinstance(spoof, dict) and spoof.get("is_spoofed"):
            indicators.append("spoof_detected")
            result["risk_level"] = "high"
        if isinstance(forging, dict) and forging.get("forgery_detected"):
            indicators.append("header_forgery_detected")
            result["risk_level"] = "high"
        if isinstance(score, dict):
            sc = score.get("score", 0)
            if sc >= 70:
                indicators.append("high_spoof_score")
                result["risk_level"] = "high"
            elif sc >= 40:
                indicators.append("moderate_spoof_score")
                if result["risk_level"] != "high": result["risk_level"] = "medium"
        if isinstance(auth, dict):
            auth_pass = all(
                r.get("spf") == "pass" and r.get("dkim") == "pass" and r.get("dmarc") == "pass"
                for r in auth.get("results", []) if isinstance(r, dict)
            )
            if auth_pass:
                indicators.append("authentication_passed")
                if result["risk_level"] == "unknown": result["risk_level"] = "low"
        result["indicators"] = indicators
        if result["risk_level"] == "high":
            result["verdict"] = "suspicious"
        elif result["risk_level"] == "medium":
            result["verdict"] = "needs_review"
        elif result["risk_level"] == "low":
            result["verdict"] = "legitimate"
        else:
            result["verdict"] = "inconclusive"
        result["indicator_count"] = len(indicators)
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def forensic_phishing_detection(email_data: dict) -> dict:
    result = {"success": True, "phish_score": 0, "indicators": [],
              "risk_level": "low", "findings": []}
    try:
        score = 0
        headers_str = email_data.get("headers", "") or email_data.get("raw_headers", "") or ""
        body = email_data.get("body", "") or email_data.get("text", "") or ""
        subject = email_data.get("subject", "") or ""
        urgency_words = ["urgent", "immediate", "action required", "verify", "suspended",
                         "compromised", "unauthorized", "login attempt", "security alert",
                         "account suspended", "payment overdue", "confirm your account",
                         "click here", "update your", "verify your", "reactivate"]
        found_urgency = [w for w in urgency_words if w in subject.lower() or w in body.lower()]
        if found_urgency:
            result["indicators"].append({"type":"urgency_language","matches":found_urgency})
            score += min(len(found_urgency) * 10, 30)
            result["findings"].append(f"Urgency language: {found_urgency}")
        try:
            parser = email.parser.HeaderParser(policy=email.policy.default)
            if isinstance(headers_str, bytes): msg = parser.parsestr(_safe_decode_bytes(headers_str))
            else: msg = parser.parsestr(headers_str)
            display_name = ""
            from_h = msg.get("From", "")
            if from_h:
                parsed = _parse_email_addr(from_h)
                display_name = parsed.get("name", "")
                result["from_address"] = parsed.get("address")
                result["from_display"] = display_name
                result["from_domain"] = parsed.get("domain")
            reply_to = msg.get("Reply-To", "")
            if reply_to:
                rt_parsed = _parse_email_addr(reply_to)
                result["reply_to"] = rt_parsed
                if result.get("from_domain") and rt_parsed.get("domain") != result["from_domain"]:
                    result["indicators"].append({"type":"reply_to_mismatch",
                        "from":result["from_domain"],"reply_to":rt_parsed.get("domain")})
                    score += 25
                    result["findings"].append(f"Reply-To domain {rt_parsed.get('domain')} differs from From domain")
            if display_name:
                suspicious_names = ["support", "security", "admin", "service", "helpdesk",
                                    "mail delivery", "postmaster", "no-reply", "notification"]
                for sn in suspicious_names:
                    if sn in display_name.lower():
                        result["indicators"].append({"type":"suspicious_display_name","name":display_name})
                        score += 10
                        result["findings"].append(f"Suspicious display name: {display_name}")
                        break
        except Exception as e:
            result["parse_error"] = str(e)
        if body:
            url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s"\'<>]*'
            urls = re.findall(url_pattern, body)
            result["urls_found"] = len(urls)
            ip_urls = [u for u in urls if re.search(r'https?://\d+\.\d+\.\d+\.\d+', u)]
            if ip_urls:
                result["indicators"].append({"type":"ip_based_url","urls":ip_urls})
                score += 20
            shorteners = ["bit.ly", "tinyurl", "tiny.cc", "goo.gl", "ow.ly", "is.gd",
                          "buff.ly", "shorturl", "click", "t.co", "tiny.one"]
            shortened = [u for u in urls if any(s in u.lower() for s in shorteners)]
            if shortened:
                result["indicators"].append({"type":"url_shortener","urls":shortened})
                score += 15
            for u in urls:
                if result.get("from_domain"):
                    parsed_u = urlparse(u)
                    domain_from_url = parsed_u.netloc.lower()
                    if domain_from_url and result["from_domain"] not in domain_from_url and domain_from_url not in result.get("from_domain", ""):
                        score += 5
                        break
        result["phish_score"] = min(100, score)
        if result["phish_score"] >= 60: result["risk_level"] = "high"
        elif result["phish_score"] >= 30: result["risk_level"] = "medium"
        else: result["risk_level"] = "low"
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def forensic_url_analysis(urls: list[str]) -> dict:
    result = {"success": True, "urls_analyzed": len(urls),
              "per_url": [], "overall_risk": "low",
              "max_risk_score": 0, "suspicious_count": 0}
    try:
        suspicious_tlds = {"tk", "ml", "ga", "cf", "gq", "xyz", "top", "club",
                           "work", "loan", "download", "review", "date", "racing"}
        shorteners = {"bit.ly", "tinyurl.com", "tiny.cc", "goo.gl", "ow.ly",
                      "is.gd", "buff.ly", "t.co", "tiny.one", "shorturl.at"}
        for url in urls:
            entry = {"url": url, "risk_score": 0, "flags": [], "risk": "low"}
            parsed = urlparse(url)
            hostname = parsed.hostname or ""
            scheme = parsed.scheme or ""
            if not scheme:
                entry["flags"].append("missing_scheme"); entry["risk_score"] += 15
            if scheme and scheme != "https":
                entry["flags"].append("non_https"); entry["risk_score"] += 10
            if re.match(r"^\d+\.\d+\.\d+\.\d+$", hostname):
                entry["flags"].append("ip_based_url"); entry["risk_score"] += 30
            if hostname in shorteners:
                entry["flags"].append("url_shortener"); entry["risk_score"] += 25
            tld = hostname.rsplit(".", 1)[-1].lower() if "." in hostname else ""
            if tld in suspicious_tlds:
                entry["flags"].append(f"suspicious_tld:.{tld}"); entry["risk_score"] += 20
            sub_count = hostname.count(".")
            if sub_count > 3:
                entry["flags"].append(f"excessive_subdomains:{sub_count}"); entry["risk_score"] += 10
            elif sub_count > 5:
                entry["flags"].append(f"excessive_subdomains:{sub_count}"); entry["risk_score"] += 20
            common_domains = ["gmail", "google", "yahoo", "outlook", "hotmail", "icloud",
                              "facebook", "twitter", "linkedin", "amazon", "paypal", "microsoft",
                              "apple", "netflix", "bank", "chase", "wellsfargo"]
            for cd in common_domains:
                if cd in hostname.lower() and cd not in hostname.lower().split(".")[0:1]:
                    continue
                if cd in hostname.lower():
                    actual_domain = hostname.lower().split(".")[-2] if hostname.count(".") >= 1 else hostname.lower()
                    if actual_domain != cd:
                        entry["flags"].append(f"typosquatting:{cd}"); entry["risk_score"] += 25
                        break
            if "@" in url:
                entry["flags"].append("contains_at_symbol"); entry["risk_score"] += 15
            if entry["risk_score"] >= 50: entry["risk"] = "high"
            elif entry["risk_score"] >= 25: entry["risk"] = "medium"
            else: entry["risk"] = "low"
            result["per_url"].append(entry)
            if entry["risk_score"] > result["max_risk_score"]:
                result["max_risk_score"] = entry["risk_score"]
            if entry["risk"] == "high":
                result["suspicious_count"] += 1
        total = result["urls_analyzed"]
        if total:
            avg = sum(e["risk_score"] for e in result["per_url"]) / total
            result["average_risk_score"] = round(avg, 1)
        result["overall_risk"] = "high" if result["max_risk_score"] >= 50 else (
            "medium" if result["max_risk_score"] >= 25 else "low")
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def forensic_sender_verification(headers: str) -> dict:
    result = {"success": True, "alignment_status": "unknown",
              "mismatches": [], "spoof_risk": "unknown",
              "from": {}, "reply_to": {}, "return_path": {},
              "envelope_from": {}}
    try:
        parser = email.parser.HeaderParser(policy=email.policy.default)
        if isinstance(headers, bytes):
            msg = parser.parsestr(_safe_decode_bytes(headers))
        else:
            msg = parser.parsestr(headers)
        from_raw = msg.get("From", "")
        result["from"] = _parse_email_addr(from_raw)
        from_domain = result["from"].get("domain", "")
        reply_to_raw = msg.get("Reply-To", "")
        if reply_to_raw:
            rt = _parse_email_addr(reply_to_raw)
            result["reply_to"] = rt
            if rt.get("domain") and from_domain and rt["domain"] != from_domain:
                result["mismatches"].append({
                    "field": "Reply-To", "expected": from_domain, "actual": rt["domain"],
                    "severity": "high",
                })
        return_path_raw = msg.get("Return-Path", "")
        if return_path_raw:
            rp = _parse_email_addr(return_path_raw)
            result["return_path"] = rp
            rp_domain = rp.get("domain", "")
            if rp_domain and from_domain and rp_domain != from_domain:
                result["mismatches"].append({
                    "field": "Return-Path", "expected": from_domain, "actual": rp_domain,
                    "severity": "high",
                })
        env_from = msg.get("Envelope-From", "")
        if env_from:
            ef = _parse_email_addr(env_from)
            result["envelope_from"] = ef
            ef_domain = ef.get("domain", "")
            if ef_domain and from_domain and ef_domain != from_domain:
                result["mismatches"].append({
                    "field": "Envelope-From", "expected": from_domain, "actual": ef_domain,
                    "severity": "medium",
                })
        display = result["from"].get("name", "")
        addr = result["from"].get("address", "")
        if display and addr:
            name_check = re.sub(r'[<>"\'\\]', "", display).strip()
            addr_local = addr.split("@")[0] if "@" in addr else ""
            if name_check.lower() != addr_local.lower() and name_check.lower() not in addr.lower():
                if any(word in name_check.lower() for word in ["support", "security", "admin", "service", "help"]):
                    result["mismatches"].append({
                        "field": "DisplayName_From", "expected": "consistent name",
                        "actual": f"'{display}' vs '{addr}'", "severity": "medium",
                    })
        if result["mismatches"]:
            high_sev = any(m.get("severity") == "high" for m in result["mismatches"])
            result["alignment_status"] = "mismatch" if high_sev else "partial_mismatch"
            result["spoof_risk"] = "high" if high_sev else "medium"
        else:
            result["alignment_status"] = "aligned"
            result["spoof_risk"] = "low"
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def forensic_ip_analysis(headers: str) -> dict:
    result = {"success": True, "ip_chain": [], "risk_flags": [],
              "total_hops": 0, "suspicious_ips": [], "risk_level": "low"}
    try:
        received_chain = await extract_received_chain(headers)
        hops = received_chain.get("received_chain", [])
        result["total_hops"] = len(hops)
        for hop in hops:
            entry = {"from": None, "by": None, "ip": None, "risk_flags": []}
            from_data = hop.get("from", {})
            by_data = hop.get("by", {})
            entry["from"] = from_data.get("raw", "")
            entry["by"] = by_data.get("raw", "")
            ip = hop.get("ip") or from_data.get("ip") or by_data.get("ip") or ""
            entry["ip"] = ip
            if ip:
                ip_clean = ip.split(":")[0] if ":" in ip else ip
                try:
                    if _is_ip_private(ip_clean):
                        entry["risk_flags"].append("private_ip")
                        result["risk_flags"].append(f"Private IP in chain: {ip}")
                    if _is_ip_reserved(ip_clean):
                        entry["risk_flags"].append("reserved_ip")
                        result["risk_flags"].append(f"Reserved IP in chain: {ip}")
                    ptr = await _resolve_ptr(ip_clean)
                    entry["ptr"] = ptr if ptr else None
                    from_domain = hop.get("from", {}).get("host", "")
                    by_domain = hop.get("by", {}).get("host", "")
                    if ptr and not from_domain and not by_domain:
                        entry["risk_flags"].append("no_hostname_match")
                    elif ptr and from_domain:
                        ptr_base = ".".join(ptr.split(".")[-2:]) if len(ptr.split(".")) >= 2 else ptr
                        from_base = ".".join(from_domain.split(".")[-2:]) if len(from_domain.split(".")) >= 2 else from_domain
                        if ptr_base and from_base and ptr_base != from_base:
                            entry["risk_flags"].append(f"ptr_mismatch:{ptr}")
                            result["risk_flags"].append(f"PTR mismatch: {ip} -> {ptr}")
                except Exception:
                    entry["risk_flags"].append("ptr_lookup_failed")
            entry["risk_count"] = len(entry["risk_flags"])
            result["ip_chain"].append(entry)
            if entry["risk_flags"]:
                result["suspicious_ips"].append({"ip": ip, "flags": entry["risk_flags"]})
        suspicious_count = sum(1 for hop in result["ip_chain"] if hop.get("risk_flags"))
        if suspicious_count >= 2: result["risk_level"] = "high"
        elif suspicious_count == 1: result["risk_level"] = "medium"
        else: result["risk_level"] = "low"
        result["suspicious_count"] = suspicious_count
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def forensic_spoof_score(headers: str) -> dict:
    result = {"success": True, "score": 0, "verdict": "legitimate",
              "contributing_factors": [], "risk_level": "low"}
    try:
        score = 0
        factors = []
        auth = await extract_authentication_results(headers)
        auth_results = auth.get("results", [])
        spf_pass = any(r.get("spf") == "pass" for r in auth_results if isinstance(r, dict))
        dkim_pass = any(r.get("dkim") == "pass" for r in auth_results if isinstance(r, dict))
        dmarc_pass = any(r.get("dmarc") == "pass" for r in auth_results if isinstance(r, dict))
        if not spf_pass:
            score += 20; factors.append("SPF authentication failed/missing")
        if not dkim_pass:
            score += 20; factors.append("DKIM authentication failed/missing")
        if not dmarc_pass:
            score += 20; factors.append("DMARC authentication failed/missing")
        if spf_pass and dkim_pass and dmarc_pass:
            score = max(0, score - 30)
            factors.append("All auth methods passed (-30)")
        forging = await detect_header_forging(headers)
        if forging.get("forgery_detected"):
            score += 25; factors.append("Header forgery detected")
        for key, val in forging.get("forged_headers", {}).items():
            if val: score += 5; factors.append(f"Forged header: {key}")
        sender = await forensic_sender_verification(headers)
        if sender.get("spoof_risk") == "high":
            score += 15; factors.append("Sender verification failed")
        elif sender.get("spoof_risk") == "medium":
            score += 8; factors.append("Partial sender mismatch")
        ip_task = await forensic_ip_analysis(headers)
        if ip_task.get("risk_level") == "high":
            score += 10; factors.append("Suspicious IP chain")
        elif ip_task.get("risk_level") == "medium":
            score += 5; factors.append("Minor IP anomalies")
        spoof_check = await detect_email_spoofing(headers)
        if spoof_check.get("is_spoofed"):
            score += 20; factors.append("Spoofing indicators detected")

        result["score"] = min(100, score)
        result["contributing_factors"] = factors[:10]
        if score >= 70:
            result["verdict"] = "highly_likely_spoofed"; result["risk_level"] = "critical"
        elif score >= 50:
            result["verdict"] = "likely_spoofed"; result["risk_level"] = "high"
        elif score >= 30:
            result["verdict"] = "possibly_spoofed"; result["risk_level"] = "medium"
        elif score >= 10:
            result["verdict"] = "likely_legitimate"; result["risk_level"] = "low"
        else:
            result["verdict"] = "legitimate"; result["risk_level"] = "low"
        result["factor_count"] = len(factors)
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


# ── Full Analysis Pipeline ────────────────────────────────────────────────────────


async def behind_the_email(raw_headers: str) -> dict:
    result = {"success": True, "executive_summary": {}, "technical_details": {},
              "verdict": "inconclusive", "risk_level": "unknown",
              "recommendations": []}
    try:
        trace_task = trace_email_path(raw_headers)
        spoof_task = detect_email_spoofing(raw_headers)
        scoring_task = email_security_score("")  # requires domain extraction
        forensic_task = forensic_investigate(raw_headers)
        route_task = trace_email_path(raw_headers)
        trace, spoof, forensic, route = await asyncio.gather(
            trace_task, spoof_task, forensic_task, route_task, return_exceptions=True)
        trace_data = trace if not isinstance(trace, Exception) else {}
        spoof_data = spoof if not isinstance(spoof, Exception) else {}
        forensic_data = forensic if not isinstance(forensic, Exception) else {}
        route_data = route if not isinstance(route, Exception) else {}
        result["technical_details"] = {
            "email_path": trace_data.get("hops", trace_data.get("chain", [])),
            "hop_count": trace_data.get("hop_count", len(trace_data.get("hops", []))),
            "source": trace_data.get("source_ip", trace_data.get("origin", "unknown")),
            "spoof_indicators": spoof_data.get("indicators", []),
            "auth_results": forensic_data.get("auth_results", {}),
            "spoof_score": forensic_data.get("spoof_score", {}),
            "forging": forensic_data.get("header_forging", {}),
            "route_details": route_data,
        }
        risk_factors = []
        if isinstance(spoof_data, dict) and spoof_data.get("is_spoofed"):
            risk_factors.append("spoofing_detected")
        if isinstance(forensic_data, dict):
            fs = forensic_data.get("spoof_score", {})
            if isinstance(fs, dict) and fs.get("score", 0) >= 50:
                risk_factors.append("high_spoof_score")
            rl = forensic_data.get("risk_level", "")
            if rl == "high": risk_factors.append("forensic_risk_high")
        result["executive_summary"] = {
            "verdict": "Suspicious" if any("spoof" in f for f in risk_factors) else "Legitimate",
            "risk_factors": risk_factors,
            "risk_level": "high" if risk_factors else "low",
            "hops_analyzed": trace_data.get("hop_count", 0),
            "spoof_score": forensic_data.get("spoof_score", {}).get("score", 0) if isinstance(forensic_data.get("spoof_score"), dict) else 0,
        }
        result["risk_level"] = result["executive_summary"]["risk_level"]
        result["verdict"] = result["executive_summary"]["verdict"]
        if risk_factors:
            result["recommendations"].append("Verify sender identity out-of-band")
            result["recommendations"].append("Check with sender via alternative channel")
            result["recommendations"].append("Do not click links or download attachments")
        else:
            result["recommendations"].append("Email appears legitimate but always verify sensitive requests")
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def email_full_analysis(headers_or_email: str) -> dict:
    result = {"success": True, "header_analysis": {}, "route_info": {},
              "security": {}, "forensics": {}, "summary": {},
              "overall_risk": "unknown"}
    try:
        if isinstance(headers_or_email, str) and "@" in headers_or_email and "\n" not in headers_or_email[:100]:
            content = headers_or_email
            is_raw_headers = False
        else:
            content = headers_or_email
            is_raw_headers = True
        if is_raw_headers:
            trace_task = trace_email_path(content)
            spoof_task = detect_email_spoofing(content)
            auth_task = extract_authentication_results(content)
            forging_task = detect_header_forging(content)
            spoof_score_task = forensic_spoof_score(content)
            trace, spoof, auth, forging, spoof_score = await asyncio.gather(
                trace_task, spoof_task, auth_task, forging_task, spoof_score_task,
                return_exceptions=True)
            result["route_info"] = trace if not isinstance(trace, Exception) else {"error": str(trace)}
            result["header_analysis"] = {
                "spoof_detection": spoof if not isinstance(spoof, Exception) else {},
                "auth_results": auth if not isinstance(auth, Exception) else {},
                "header_forging": forging if not isinstance(forging, Exception) else {},
            }
            result["forensics"] = {
                "spoof_score": spoof_score if not isinstance(spoof_score, Exception) else {},
            }
            domain = ""
            if isinstance(auth, dict) and not isinstance(auth, Exception):
                for r in auth.get("results", []):
                    if isinstance(r, dict) and r.get("header_from"):
                        domain = r["header_from"]
                        break
            if domain:
                security_task = email_security_score(domain)
                sec = await security_task
                result["security"] = sec if not isinstance(sec, Exception) else {}
            result["summary"] = {
                "hop_count": result["route_info"].get("hop_count", 0) if isinstance(result["route_info"], dict) else 0,
                "is_spoofed": spoof.get("is_spoofed", False) if isinstance(spoof, dict) else False,
                "forgery_detected": forging.get("forgery_detected", False) if isinstance(forging, dict) else False,
                "spoof_score": spoof_score.get("score", 0) if isinstance(spoof_score, dict) else 0,
            }
        else:
            domain = _extract_domain(content)
            sec = await email_security_score(domain) if domain else {}
            result["security"] = sec if not isinstance(sec, Exception) else {}
            result["summary"] = {"email": content, "domain": domain,
                                 "security_score": sec.get("total", 0) if isinstance(sec, dict) else 0,
                                 "grade": sec.get("grade", "F") if isinstance(sec, dict) else "F"}
        risk_score = 0
        if isinstance(result.get("forensics", {}).get("spoof_score"), dict):
            risk_score = result["forensics"]["spoof_score"].get("score", 0)
        if result["summary"].get("is_spoofed"):
            risk_score += 30
        grades = {"A": 0, "B": 10, "C": 30, "D": 50, "F": 70}
        sec_grade = result.get("security", {}).get("grade", "F")
        risk_score += grades.get(sec_grade, 50)
        risk_score = min(100, risk_score)
        if risk_score >= 60: result["overall_risk"] = "high"
        elif risk_score >= 30: result["overall_risk"] = "medium"
        else: result["overall_risk"] = "low"
        result["overall_risk_score"] = risk_score
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def email_domain_investigation(domain: str) -> dict:
    result = {"success": True, "domain": domain, "spf": {}, "dkim": {},
              "dmarc": {}, "dns": {}, "mx": {}, "security_score": {},
              "intelligence": {}}
    try:
        spf_task = check_spf_record(domain)
        spf_rec_task = spf_recommendations(domain)
        spf, spf_rec = await asyncio.gather(spf_task, spf_rec_task, return_exceptions=True)
        result["spf"] = {
            "has_spf": spf.get("has_spf", False) if not isinstance(spf, Exception) else False,
            "record": spf.get("spf_record") if not isinstance(spf, Exception) else None,
            "recommendations": spf_rec.get("recommendations", []) if not isinstance(spf_rec, Exception) else [],
            "strength": spf_rec.get("strength", "unknown") if not isinstance(spf_rec, Exception) else "unknown",
        }
        dkim_task = dkim_selector_guess(domain)
        dkim_rec_task = dkim_recommendations(domain)
        dkim_guess, dkim_rec = await asyncio.gather(dkim_task, dkim_rec_task, return_exceptions=True)
        result["dkim"] = {
            "has_dkim": dkim_guess.get("has_dkim", False) if not isinstance(dkim_guess, Exception) else False,
            "selectors": dkim_guess.get("found_selectors", []) if not isinstance(dkim_guess, Exception) else [],
            "best_selector": dkim_guess.get("best_selector") if not isinstance(dkim_guess, Exception) else None,
            "recommendations": dkim_rec.get("recommendations", []) if not isinstance(dkim_rec, Exception) else [],
            "strength": dkim_rec.get("strength", "unknown") if not isinstance(dkim_rec, Exception) else "unknown",
        }
        dmarc_task = check_dmarc_record(domain)
        dmarc_rec_task = dmarc_recommendations(domain)
        dmarc, dmarc_rec = await asyncio.gather(dmarc_task, dmarc_rec_task, return_exceptions=True)
        result["dmarc"] = {
            "has_dmarc": dmarc.get("has_dmarc", False) if not isinstance(dmarc, Exception) else False,
            "policy": dmarc.get("policy") if not isinstance(dmarc, Exception) else None,
            "record": dmarc.get("record") if not isinstance(dmarc, Exception) else None,
            "recommendations": dmarc_rec.get("recommendations", []) if not isinstance(dmarc_rec, Exception) else [],
            "strength": dmarc_rec.get("strength", "unknown") if not isinstance(dmarc_rec, Exception) else "unknown",
        }
        mx_task = _resolve_dns_mx(domain)
        a_task = _resolve_dns_a(domain)
        mx, a = await asyncio.gather(mx_task, a_task, return_exceptions=True)
        result["mx"] = mx if not isinstance(mx, Exception) else []
        result["dns"] = {
            "a_records": a if not isinstance(a, Exception) else [],
            "has_mx": len(mx) > 0 if not isinstance(mx, Exception) else False,
        }
        score_task = email_security_score(domain)
        score = await score_task
        result["security_score"] = score if not isinstance(score, Exception) else {}
        result["intelligence"] = {
            "spf_protected": result["spf"].get("has_spf", False),
            "dkim_signed": result["dkim"].get("has_dkim", False),
            "dmarc_enforced": result["dmarc"].get("policy") == "reject",
            "mx_configured": result["dns"].get("has_mx", False),
            "overall_score": result["security_score"].get("total", 0) if isinstance(result["security_score"], dict) else 0,
            "grade": result["security_score"].get("grade", "F") if isinstance(result["security_score"], dict) else "F",
        }
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def email_trace_route(email_addr: str) -> dict:
    result = {"success": True, "email": email_addr, "domain": "",
              "mx_servers": [], "potential_routes": [],
              "hop_estimation": 0, "delivery_path": []}
    try:
        domain = _extract_domain(email_addr)
        if not domain:
            result["error"] = "Could not extract domain"; return result
        result["domain"] = domain
        mx_records = await _resolve_dns_mx(domain)
        a_records = await _resolve_dns_a(domain)
        result["mx_servers"] = mx_records
        if not mx_records:
            result["error"] = f"No MX records for {domain}"
            if a_records:
                result["potential_routes"].append({"type": "a_record_fallback", "targets": a_records})
            return result
        mx_records.sort(key=lambda x: x.get("preference", 0))
        for mx in mx_records:
            exchange = mx.get("exchange", "")
            mx_ips = await _resolve_dns_a(exchange)
            mx["resolved_ips"] = mx_ips
            try:
                ptr = await _resolve_ptr(mx_ips[0]) if mx_ips else ""
                mx["ptr"] = ptr
            except Exception:
                mx["ptr"] = None
        result["mx_servers"] = mx_records
        entry_path = [{"stage": "submission", "description": f"Email sent from MUA to submission server"}]
        entry_path.append({"stage": "mta", "description": f"Relayed via MTA(s)"})
        if mx_records:
            primary = mx_records[0]
            entry_path.append({"stage": "mx", "description": f"Delivered to MX {primary.get('exchange')} (priority {primary.get('preference')})",
                               "server": primary.get("exchange"), "ips": primary.get("resolved_ips", [])})
            for mx in mx_records[1:]:
                entry_path.append({"stage": "mx_alt", "description": f"Alternative MX {mx.get('exchange')} (priority {mx.get('preference')})",
                                   "server": mx.get("exchange"), "ips": mx.get("resolved_ips", [])})
        result["delivery_path"] = entry_path
        result["hop_estimation"] = len(entry_path) + 1
        result["potential_routes"] = [
            {"mx": mx.get("exchange"), "ips": mx.get("resolved_ips", []),
             "preference": mx.get("preference")} for mx in mx_records
        ]
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def email_validate_and_verify(email_addr: str) -> dict:
    result = {"success": True, "email": email_addr, "is_valid": False,
              "confidence_score": 0, "checks": {}, "findings": []}
    try:
        format_task = verify_email_format(email_addr)
        domain_task = verify_email_domain(email_addr)
        disposable_task = email_disposable_check(email_addr)
        role_task = email_role_account_check(email_addr)
        fmt, dom, disp, role = await asyncio.gather(
            format_task, domain_task, disposable_task, role_task, return_exceptions=True)
        fmt_data = fmt if not isinstance(fmt, Exception) else {"is_valid": False, "issues": [str(fmt)]}
        dom_data = dom if not isinstance(dom, Exception) else {"resolves": False, "has_mx": False, "error": str(dom)}
        disp_data = disp if not isinstance(disp, Exception) else {"is_disposable": False}
        role_data = role if not isinstance(role, Exception) else {"is_role": False}
        result["checks"] = {
            "format_valid": fmt_data.get("is_valid", False),
            "domain_resolves": dom_data.get("resolves", False),
            "has_mx": dom_data.get("has_mx", False),
            "is_disposable": disp_data.get("is_disposable", False),
            "is_role_account": role_data.get("is_role", False),
        }
        result["format_details"] = fmt_data
        result["domain_details"] = {"domain": dom_data.get("domain"), "mx_records": dom_data.get("mx_records", []),
                                     "has_a": dom_data.get("has_a", False)}
        result["disposable_details"] = {"is_disposable": disp_data.get("is_disposable", False),
                                         "reason": disp_data.get("reason")}
        result["role_details"] = {"is_role": role_data.get("is_role", False),
                                   "pattern": role_data.get("matched_pattern")}
        if not fmt_data.get("is_valid", False):
            result["findings"].extend([f"Format: {i}" for i in fmt_data.get("issues", [])])
        if not dom_data.get("resolves", False):
            result["findings"].append("Domain does not resolve")
        if disp_data.get("is_disposable", False):
            result["findings"].append(f"Disposable email: {disp_data.get('reason')}")
        if role_data.get("is_role", False):
            result["findings"].append(f"Role account: {role_data.get('matched_pattern')}")
        confidence = 0
        if fmt_data.get("is_valid", False): confidence += 25
        if dom_data.get("resolves", False): confidence += 25
        if dom_data.get("has_mx", False): confidence += 20
        if not disp_data.get("is_disposable", False): confidence += 15
        if not role_data.get("is_role", False): confidence += 15
        result["confidence_score"] = confidence
        result["is_valid"] = bool(fmt_data.get("is_valid") and dom_data.get("resolves") and dom_data.get("has_mx"))
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


# ── Auth Extensions ───────────────────────────────────────────────────────────────


async def check_bimi_record(domain: str) -> dict:
    result = {"success": True, "domain": domain, "bimi_domain": f"default._bimi.{domain}",
              "has_bimi": False, "record": None, "logo_url": None,
              "vmc_url": None, "tags": {}, "is_valid": False}
    try:
        bimi_domain = f"default._bimi.{domain}"
        txt_records = await _resolve_dns_txt(bimi_domain)
        result["raw_records"] = txt_records
        bimi_records = [t for t in txt_records if "v=BIMI1" in t]
        if not bimi_records:
            bimi_records = [t for t in txt_records]
        if bimi_records:
            record = bimi_records[0]
            result["record"] = record
            result["has_bimi"] = True
            tags = {}
            for part in record.split(";"):
                part = part.strip()
                if "=" not in part: continue
                k, v = part.split("=", 1); k = k.strip().lower(); v = v.strip()
                tags[k] = v
            result["tags"] = tags
            if tags.get("v") == "BIMI1":
                result["is_valid"] = True
            result["logo_url"] = tags.get("l")
            result["vmc_url"] = tags.get("a")
            if result["logo_url"]:
                result["logo_parsed"] = result["logo_url"]
            if result["vmc_url"]:
                result["vmc_parsed"] = result["vmc_url"]
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def check_mta_sts(domain: str) -> dict:
    result = {"success": True, "domain": domain, "has_mta_sts": False,
              "policy": None, "mode": None, "mx": [],
              "max_age": None, "errors": []}
    try:
        mta_domain = f"mta-sts.{domain}"
        url = f"https://{mta_domain}/.well-known/mta-sts.txt"
        resp = await _http_get(url)
        if not resp.get("success") or resp.get("status") != 200:
            result["errors"].append(f"MTA-STS fetch failed: HTTP {resp.get('status')}")
            return result
        body = resp.get("body", "")
        result["raw_policy"] = body[:500]
        result["has_mta_sts"] = True
        policy_lines = {}
        for line in body.splitlines():
            line = line.strip()
            if ":" in line:
                k, v = line.split(":", 1)
                policy_lines[k.strip().lower()] = v.strip()
        result["policy"] = policy_lines
        result["version"] = policy_lines.get("version")
        result["mode"] = policy_lines.get("mode", "none")
        mx_raw = policy_lines.get("mx", "")
        result["mx"] = [m.strip() for m in mx_raw.split(",") if m.strip()] if mx_raw else []
        result["max_age"] = policy_lines.get("max_age")
        if result["mode"] == "enforce":
            result["mode_assessment"] = "strict"
        elif result["mode"] == "testing":
            result["mode_assessment"] = "testing"
        else:
            result["mode_assessment"] = "none"
            result["errors"].append("MTA-STS mode is 'none' (no enforcement)")
        if not result["mx"]:
            result["errors"].append("No MX directives in MTA-STS policy")
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result


async def check_tls_rpt(domain: str) -> dict:
    result = {"success": True, "domain": domain, "has_tls_rpt": False,
              "record": None, "rua": None, "tags": {}, "is_valid": False}
    try:
        tls_domain = f"_smtp._tls.{domain}"
        txt_records = await _resolve_dns_txt(tls_domain)
        result["raw_records"] = txt_records
        tls_records = [t for t in txt_records if "v=TLSRPTv1" in t]
        if not tls_records:
            for t in txt_records:
                if "v=TLSRPT" in t or "rua=" in t:
                    tls_records.append(t)
        if tls_records:
            record = tls_records[0]
            result["record"] = record
            result["has_tls_rpt"] = True
            tags = {}
            for part in record.split(";"):
                part = part.strip()
                if "=" not in part: continue
                k, v = part.split("=", 1); k = k.strip().lower(); v = v.strip()
                tags[k] = v
            result["tags"] = tags
            if tags.get("v") == "TLSRPTv1":
                result["is_valid"] = True
            result["rua"] = tags.get("rua")
            if result["rua"]:
                result["report_uris"] = [u.strip() for u in result["rua"].split(",")]
    except Exception as e:
        result["success"] = False; result["error"] = str(e)
    return result
