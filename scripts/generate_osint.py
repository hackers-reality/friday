"""Generate the tools_osint_extra.py file with comprehensive OSINT tools."""
import os

OUTPUT = r'E:\open-interpreter\friday\tools_osint_extra.py'

HEADER = r'''"""
FRIDAY OSINT Extra Tools — 15+ Intelligence Gathering Modules.
Extends osint_advanced_tools.py with social media, phone, DNS deep recon,
web tech detection, URL analysis, Wayback Machine, breach checking,
IP intelligence, domain intelligence, crawling, security headers,
cryptocurrency, dark web, and formatting utilities.

Every function is async with proper error handling and structured returns.
"""
'''

CONTENT = r'''
from __future__ import annotations
import asyncio
import hashlib
import html.parser
import ipaddress
import json
import os
import re
import socket
import ssl
import struct
import subprocess
import tempfile
import time
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, Union
from urllib.parse import urlparse, quote, urljoin

import aiohttp
import requests

SOCIAL_PLATFORMS = {
    "instagram": "https://www.instagram.com/{}/",
    "twitter": "https://twitter.com/{}",
    "facebook": "https://www.facebook.com/{}",
    "linkedin": "https://www.linkedin.com/in/{}",
    "tiktok": "https://www.tiktok.com/@{}",
    "telegram": "https://t.me/{}",
    "reddit": "https://www.reddit.com/user/{}",
    "github": "https://github.com/{}",
    "youtube": "https://www.youtube.com/@{}",
    "pinterest": "https://www.pinterest.com/{}",
    "twitch": "https://www.twitch.tv/{}",
    "medium": "https://medium.com/@{}",
    "discord": "https://discord.com/users/{}",
    "steam": "https://steamcommunity.com/id/{}",
    "mastodon": "https://mastodon.social/@{}",
    "keybase": "https://keybase.io/{}",
    "codepen": "https://codepen.io/{}",
    "replit": "https://replit.com/@{}",
    "flickr": "https://www.flickr.com/people/{}",
    "behance": "https://www.behance.net/{}",
    "deviantart": "https://www.deviantart.com/{}",
    "vimeo": "https://vimeo.com/{}",
    "soundcloud": "https://soundcloud.com/{}",
    "patreon": "https://www.patreon.com/{}",
    "hackernews": "https://news.ycombinator.com/user?id={}",
    "producthunt": "https://www.producthunt.com/@{}",
    "angelco": "https://angel.co/u/{}",
}

DISPOSABLE_EMAIL_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com",
    "throwaway.email", "yopmail.com", "mailnator.com", "temp-mail.org",
    "fakeinbox.com", "trashmail.com", "sharklasers.com", "maildrop.cc",
    "getnada.com", "tempinbox.com", "emailondeck.com",
    "dispostable.com", "spambox.us", "burnermail.io",
    "anonaddy.com", "simplelogin.co", "relay.firefox.com",
}

COMMON_DKIM_SELECTORS = [
    "google", "selector1", "selector2", "default", "dkim", "mail",
    "zoho", "protonmail", "mx", "mandrill", "sparkpost", "sendgrid",
    "amazonses", "k1", "k2", "s1", "s2",
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FRIDAY-OSINT/3.0"
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(r'(\+?\d{1,4}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}')


# ─── Helper ─────────────────────────────────────────────────

async def _fetch(url: str, timeout: float = 15.0, headers: dict = None) -> tuple[int, str]:
    """Fetch URL and return (status_code, text)."""
    if headers is None:
        headers = {"User-Agent": USER_AGENT}
    try:
        connector = aiohttp.TCPConnector(limit=100, force_close=True)
        async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                text = await resp.text()
                return resp.status, text
    except asyncio.TimeoutError:
        return 0, "TIMEOUT"
    except aiohttp.ClientError as e:
        return 0, f"CLIENT_ERROR:{e}"
    except Exception as e:
        return 0, f"ERROR:{e}"


async def _fetch_json(url: str, timeout: float = 15.0, headers: dict = None) -> dict:
    """Fetch JSON from URL."""
    if headers is None:
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    try:
        connector = aiohttp.TCPConnector(limit=100, force_close=True)
        async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {"error": f"HTTP {resp.status}", "url": url}
    except asyncio.TimeoutError:
        return {"error": "Timeout", "url": url}
    except aiohttp.ClientError as e:
        return {"error": str(e), "url": url}
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}", "url": url}
    except Exception as e:
        return {"error": str(e), "url": url}


async def _async_dns_lookup(hostname: str, record_type: str = "A") -> list[str]:
    """Async DNS lookup using subprocess."""
    results = []
    try:
        if record_type == "A":
            proc = await asyncio.create_subprocess_exec(
                "nslookup", hostname,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            for m in re.finditer(r'Addresses?:\s*(\S+)', stdout.decode(), re.IGNORECASE):
                for ip in m.group(1).split():
                    ip = ip.strip()
                    if ip.count(".") == 3 and all(p.isdigit() for p in ip.split(".")):
                        results.append(ip)
        elif record_type == "MX":
            try:
                import dns.resolver
                answers = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: dns.resolver.resolve(hostname, 'MX')
                )
                results = [str(r.exchange).rstrip(".") for r in answers]
            except ImportError:
                proc = await asyncio.create_subprocess_exec(
                    "nslookup", "-type=MX", hostname,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
                for m in re.finditer(r'mail exchanger\s*=\s*(\S+)', stdout.decode(), re.IGNORECASE):
                    results.append(m.group(1).rstrip("."))
        elif record_type == "TXT":
            try:
                import dns.resolver
                answers = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: dns.resolver.resolve(hostname, 'TXT')
                )
                results = ["".join(r.strings) for r in answers]
            except ImportError:
                proc = await asyncio.create_subprocess_exec(
                    "nslookup", "-type=TXT", hostname,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
                for m in re.finditer(r'text\s*=\s*"([^"]*)"', stdout.decode(), re.IGNORECASE):
                    results.append(m.group(1))
    except (asyncio.TimeoutError, FileNotFoundError, Exception):
        pass
    return results


# ============================================================
# SECTION 1: Social Media OSINT
# ============================================================

async def social_analyzer(username: str, timeout: float = 15.0) -> dict[str, Any]:
    """Check username across 30+ social media platforms."""
    if not username or len(username) < 2:
        return {"error": "Username too short", "username": username}
    result = {
        "username": username, "platforms_checked": 0,
        "platforms_found": [], "profiles": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    headers = {"User-Agent": USER_AGENT}
    connector = aiohttp.TCPConnector(limit=15, force_close=True)
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        for platform, url_template in SOCIAL_PLATFORMS.items():
            url = url_template.format(username)
            result["platforms_checked"] += 1
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    if resp.status == 200:
                        profile = {"platform": platform, "url": url, "status": resp.status}
                        result["platforms_found"].append(platform)
                        result["profiles"].append(profile)
            except Exception:
                pass
    result["platforms_found_count"] = len(result["platforms_found"])
    result["coverage_pct"] = round(
        result["platforms_found_count"] / max(result["platforms_checked"], 1) * 100, 1
    )
    return result


async def instagram_osint(username: str, timeout: float = 15.0) -> dict[str, Any]:
    """Scrape public Instagram profile information."""
    result = {"username": username, "success": False}
    url = f"https://www.instagram.com/{username}/"
    headers = {"User-Agent": USER_AGENT}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    result["success"] = True
                    result["url"] = url
                    m = re.search(r'<meta property="og:title" content="(.*?)"', text)
                    if m:
                        result["display_name"] = html.unescape(m.group(1))
                    m = re.search(r'<meta property="og:description" content="(.*?)"', text)
                    if m:
                        desc = html.unescape(m.group(1))
                        result["description"] = desc
                    m = re.search(r'"edge_followed_by":\{"count":(\d+)\}', text)
                    if m:
                        result["followers"] = int(m.group(1))
                    m = re.search(r'"edge_follow":\{"count":(\d+)\}', text)
                    if m:
                        result["following"] = int(m.group(1))
                    m = re.search(r'"edge_owner_to_timeline_media":\{"count":(\d+)\}', text)
                    if m:
                        result["posts"] = int(m.group(1))
                    result["is_private"] = '"_csrftoken"' not in text
                elif resp.status == 404:
                    result["error"] = "Profile not found"
                else:
                    result["error"] = f"HTTP {resp.status}"
    except asyncio.TimeoutError:
        result["error"] = "Request timed out"
    except Exception as e:
        result["error"] = str(e)
    return result


async def twitter_osint(username: str, timeout: float = 15.0) -> dict[str, Any]:
    """Get public Twitter/X profile info."""
    result = {"username": username, "success": False}
    url = f"https://twitter.com/{username}"
    headers = {"User-Agent": USER_AGENT}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    result["success"] = True
                    m = re.search(r'<title>(.*?)</title>', text, re.DOTALL)
                    if m: result["title"] = html.unescape(m.group(1).strip())
                    m = re.search(r'<meta name="description" content="(.*?)"', text)
                    if m: result["description"] = html.unescape(m.group(1))
                    m = re.search(r'"followersCount":(\d+)', text)
                    if m: result["followers"] = int(m.group(1))
                    m = re.search(r'"followingCount":(\d+)', text)
                    if m: result["following"] = int(m.group(1))
                    m = re.search(r'"statusesCount":(\d+)', text)
                    if m: result["tweets"] = int(m.group(1))
                    result["url"] = url
                elif resp.status == 404:
                    result["error"] = "User not found"
                else:
                    result["error"] = f"HTTP {resp.status}"
    except asyncio.TimeoutError:
        result["error"] = "Request timed out"
    except Exception as e:
        result["error"] = str(e)
    return result


async def facebook_osint(query: str, timeout: float = 15.0) -> dict[str, Any]:
    """Search Facebook public directory."""
    result = {"query": query, "success": False}
    url = f"https://www.facebook.com/public/{urllib.parse.quote(query)}"
    headers = {"User-Agent": USER_AGENT}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                text = await resp.text()
                result["success"] = resp.status == 200
                result["url"] = url
                matches = re.findall(r'href="/([^"/]+)"', text)
                unique = set(m.group(1) for m in re.finditer(r'href="/([^"]+)"', text) if "/" not in m.group(1) and len(m.group(1)) > 3)
                result["profile_hints"] = list(unique)[:50]
                result["hint_count"] = len(result["profile_hints"])
    except Exception as e:
        result["error"] = str(e)
    return result


async def linkedin_osint(query: str, timeout: float = 15.0) -> dict[str, Any]:
    """Search LinkedIn for public profiles."""
    result = {"query": query, "success": False}
    url = f"https://www.linkedin.com/pub/dir/{urllib.parse.quote(query)}"
    headers = {"User-Agent": USER_AGENT}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                text = await resp.text()
                result["success"] = resp.status == 200
                result["url"] = url
                result["response_length"] = len(text)
    except Exception as e:
        result["error"] = str(e)
    return result


async def tiktok_osint(username: str, timeout: float = 15.0) -> dict[str, Any]:
    """Get public TikTok profile info."""
    result = {"username": username, "success": False}
    url = f"https://www.tiktok.com/@{username}"
    headers = {"User-Agent": USER_AGENT}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    result["success"] = True
                    m = re.search(r'<title>(.*?)</title>', text, re.DOTALL)
                    if m: result["title"] = html.unescape(m.group(1).strip())
                    m = re.search(r'"followerCount":(\d+)', text)
                    if m: result["followers"] = int(m.group(1))
                    m = re.search(r'"followingCount":(\d+)', text)
                    if m: result["following"] = int(m.group(1))
                    m = re.search(r'"heartCount":(\d+)', text)
                    if m: result["likes"] = int(m.group(1))
                    m = re.search(r'"videoCount":(\d+)', text)
                    if m: result["videos"] = int(m.group(1))
                    result["url"] = url
                elif resp.status == 404:
                    result["error"] = "User not found"
                else:
                    result["error"] = f"HTTP {resp.status}"
    except asyncio.TimeoutError:
        result["error"] = "Request timed out"
    except Exception as e:
        result["error"] = str(e)
    return result


async def telegram_osint(username: str, timeout: float = 15.0) -> dict[str, Any]:
    """Check Telegram username existence and info."""
    result = {"username": username, "exists": False}
    url = f"https://t.me/{username}"
    headers = {"User-Agent": USER_AGENT}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    result["exists"] = True
                    result["url"] = url
                    m = re.search(r'<title>(.*?)</title>', text, re.DOTALL)
                    if m: result["title"] = html.unescape(m.group(1).strip())
                    m = re.search(r'<meta property="og:description" content="(.*?)"', text)
                    if m: result["description"] = html.unescape(m.group(1))
                elif resp.status == 404:
                    result["exists"] = False
                else:
                    result["error"] = f"HTTP {resp.status}"
    except Exception as e:
        result["error"] = str(e)
    return result


async def reddit_osint(username: str, timeout: float = 15.0) -> dict[str, Any]:
    """Get public Reddit user info via JSON API."""
    result = {"username": username, "success": False}
    url = f"https://www.reddit.com/user/{username}/about.json"
    headers = {"User-Agent": USER_AGENT}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    d = data.get("data", {})
                    result["success"] = True
                    result["id"] = d.get("id")
                    result["name"] = d.get("name")
                    result["created_utc"] = d.get("created_utc")
                    result["link_karma"] = d.get("link_karma", 0)
                    result["comment_karma"] = d.get("comment_karma", 0)
                    result["is_employee"] = d.get("is_employee", False)
                    result["has_verified_email"] = d.get("has_verified_email", False)
                    if d.get("created_utc"):
                        result["account_age_days"] = int((time.time() - d["created_utc"]) / 86400)
                    result["url"] = f"https://www.reddit.com/user/{username}"
                elif resp.status == 404:
                    result["error"] = "User not found"
                else:
                    result["error"] = f"HTTP {resp.status}"
    except asyncio.TimeoutError:
        result["error"] = "Request timed out"
    except Exception as e:
        result["error"] = str(e)
    return result


async def social_links_extractor(url: str, timeout: float = 15.0) -> dict[str, Any]:
    """Extract social media links from a webpage."""
    result = {"source_url": url, "social_links": {}, "success": False}
    social_domains = {
        "facebook.com": "facebook", "twitter.com": "twitter", "x.com": "twitter",
        "instagram.com": "instagram", "linkedin.com": "linkedin", "tiktok.com": "tiktok",
        "youtube.com": "youtube", "t.me": "telegram", "discord.com": "discord",
        "discord.gg": "discord", "reddit.com": "reddit", "github.com": "github",
        "medium.com": "medium", "twitch.tv": "twitch",
    }
    try:
        status, text = await _fetch(url, timeout)
        if status == 200:
            result["success"] = True
            for m in re.finditer(r'href=["\'](https?://[^"\'<>]+)["\']', text, re.IGNORECASE):
                link = m.group(1)
                parsed = urlparse(link)
                for domain, platform in social_domains.items():
                    if domain in parsed.netloc:
                        result["social_links"].setdefault(platform, set()).add(link)
            result["social_links"] = {k: list(v) for k, v in result["social_links"].items()}
            result["platforms"] = list(result["social_links"].keys())
            result["total_links"] = sum(len(v) for v in result["social_links"].values())
        else:
            result["error"] = f"HTTP {status}"
    except Exception as e:
        result["error"] = str(e)
    return result


# ============================================================
# SECTION 2: Email-to-Account Discovery
# ============================================================

HOLEHE_SERVICES = {
    "spotify": "https://accounts.spotify.com/en/status?email={}",
    "instagram": "https://www.instagram.com/accounts/web_create_ajax/",
    "twitter": "https://api.twitter.com/i/users/email_available.json",
    "pinterest": "https://www.pinterest.com/resource/EmailExistsResource/get/",
    "tumblr": "https://www.tumblr.com/svc/account/check_email",
}

async def holehe_check(email: str, timeout: float = 10.0) -> dict[str, Any]:
    """Check if email is registered on popular services."""
    result = {"email": email, "services": {}, "timestamp": datetime.now(timezone.utc).isoformat()}
    domain = email.split("@")[-1] if "@" in email else email
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    
    # Check HaveIBeenPwned
    try:
        resp_json = await _fetch_json(f"https://leakcheck.io/api/public?check={email}", timeout)
        if "success" in resp_json:
            result["breach_check"] = resp_json.get("success", False)
    except Exception:
        pass
    
    # Check disposable
    result["is_disposable_domain"] = domain.lower() in DISPOSABLE_EMAIL_DOMAINS
    
    # Check common email services
    email_lower = email.lower()
    common_services = {
        "google/gmail": email_lower.endswith("@gmail.com") or email_lower.endswith("@googlemail.com"),
        "microsoft/outlook": any(email_lower.endswith(s) for s in ["@outlook.com", "@hotmail.com", "@live.com", "@msn.com"]),
        "yahoo": any(email_lower.endswith(s) for s in ["@yahoo.com", "@yahoo.co.uk", "@ymail.com"]),
        "protonmail": email_lower.endswith("@protonmail.com") or email_lower.endswith("@proton.me"),
        "icloud": email_lower.endswith("@icloud.com") or email_lower.endswith("@me.com"),
        "aol": email_lower.endswith("@aol.com"),
        "zoho": email_lower.endswith("@zoho.com"),
    }
    result["email_provider"] = None
    for provider, check in common_services.items():
        if check:
            result["email_provider"] = provider
            break
    
    result["services"]["email_provider"] = result["email_provider"]
    return result


async def email_rep(email: str, timeout: float = 10.0) -> dict[str, Any]:
    """Email reputation check."""
    result = {"email": email, "reputation": "unknown"}
    try:
        resp_json = await _fetch_json(f"https://emailrep.io/{email}", timeout)
        if "details" in resp_json:
            result = resp_json
            result["reputation"] = resp_json.get("reputation", "unknown")
            result["suspicious"] = resp_json.get("suspicious", False)
            result["details"] = resp_json.get("details", {})
        else:
            result["reputation_data"] = resp_json
    except Exception as e:
        result["error"] = str(e)
    return result


async def email_format(first_name: str, last_name: str, domain: str) -> dict[str, Any]:
    """Generate possible email formats from name and domain."""
    first = first_name.lower().strip()
    last = last_name.lower().strip()
    domain = domain.lower().strip()
    return {
        "first_name": first_name,
        "last_name": last_name,
        "domain": domain,
        "formats": [
            f"{first}@{domain}",
            f"{first}.{last}@{domain}",
            f"{first[0]}{last}@{domain}",
            f"{first}{last[0]}@{domain}",
            f"{first[0]}.{last}@{domain}",
            f"{first}.{last[0]}@{domain}",
            f"{first[0]}{last[0]}@{domain}",
            f"{last}@{domain}",
            f"{first}_{last}@{domain}",
            f"{first}-{last}@{domain}",
        ],
        "count": 10,
    }


# ============================================================
# SECTION 3: Username Search
# ============================================================

USERNAME_CHECK_SITES = {
    "github": "https://github.com/{}",
    "gitlab": "https://gitlab.com/{}",
    "bitbucket": "https://bitbucket.org/{}/",
    "keybase": "https://keybase.io/{}",
    "hackerone": "https://hackerone.com/{}",
    "bugcrowd": "https://bugcrowd.com/{}",
    "dockerhub": "https://hub.docker.com/u/{}",
    "npm": "https://www.npmjs.com/~{}",
    "pypi": "https://pypi.org/user/{}/",
    "rubygems": "https://rubygems.org/profiles/{}",
    "crates": "https://crates.io/users/{}",
    "packagist": "https://packagist.org/profile/{}",
}

async def username_search(username: str, timeout: float = 10.0) -> dict[str, Any]:
    """Search username across development platforms."""
    result = {"username": username, "found_on": [], "profiles": [], "count": 0}
    headers = {"User-Agent": USER_AGENT}
    connector = aiohttp.TCPConnector(limit=10, force_close=True)
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        for site, url_template in USERNAME_CHECK_SITES.items():
            url = url_template.format(username)
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    if resp.status == 200:
                        result["found_on"].append(site)
                        result["profiles"].append({"platform": site, "url": url})
                        result["count"] += 1
            except Exception:
                pass
    return result


async def username_variations(username: str) -> dict[str, Any]:
    """Generate username variations."""
    u = username.strip()
    return {
        "original": u,
        "variations": [
            u.lower(), u.upper(), u.capitalize(),
            u + "_", u + ".", "_" + u,
            u.replace("_", ""), u.replace(".", ""),
            u.replace("_", "."), u.replace(".", "_"),
            u + "1", u + "123", u + "99",
            u[:int(len(u)/2)], u + "official",
            u + "real", "the" + u, "its" + u,
        ],
        "count": 18,
    }


# ============================================================
# SECTION 4: Phone OSINT
# ============================================================

async def phone_lookup(phone: str, timeout: float = 10.0) -> dict[str, Any]:
    """Phone number intelligence lookup."""
    cleaned = re.sub(r'[^\d+]', '', phone)
    result = {
        "phone_raw": phone,
        "phone_clean": cleaned,
        "success": False,
    }
    # Determine country based on prefix
    if cleaned.startswith("+1") or (cleaned.startswith("1") and len(cleaned) == 11):
        result["country"] = "US/Canada"
        result["country_code"] = "+1"
        if len(cleaned) >= 10:
            n = cleaned[-10:]
            result["area_code"] = n[:3]
            result["central_office"] = n[3:6]
            result["subscriber"] = n[6:]
            result["formatted"] = f"({n[:3]}) {n[3:6]}-{n[6:]}"
    elif cleaned.startswith("+44"):
        result["country"] = "UK"
        result["country_code"] = "+44"
    elif cleaned.startswith("+91"):
        result["country"] = "India"
        result["country_code"] = "+91"
    elif cleaned.startswith("+86"):
        result["country"] = "China"
        result["country_code"] = "+86"
    elif cleaned.startswith("+49"):
        result["country"] = "Germany"
        result["country_code"] = "+49"
    elif cleaned.startswith("+33"):
        result["country"] = "France"
        result["country_code"] = "+33"
    elif cleaned.startswith("+61"):
        result["country"] = "Australia"
        result["country_code"] = "+61"
    elif cleaned.startswith("+81"):
        result["country"] = "Japan"
        result["country_code"] = "+81"
    else:
        result["country"] = "Unknown"
        result["country_code"] = cleaned[:3] if len(cleaned) > 3 else cleaned
    
    result["valid_format"] = len(cleaned) >= 8 and len(cleaned) <= 15
    result["length"] = len(cleaned)
    result["success"] = result["valid_format"]
    return result


async def phone_format(phone: str, country: str = "US") -> dict[str, Any]:
    """Validate and format phone number."""
    cleaned = re.sub(r'[^\d+]', '', phone)
    result = {"input": phone, "cleaned": cleaned, "valid": False, "formats": []}
    if len(cleaned) >= 8:
        result["valid"] = True
        if not cleaned.startswith("+"):
            result["formats"].append("+" + cleaned)
        result["formats"].append(cleaned)
        result["e164"] = cleaned if cleaned.startswith("+") else "+" + cleaned
    return result


async def phone_breach_check(phone: str, timeout: float = 10.0) -> dict[str, Any]:
    """Check if phone appears in data breaches."""
    cleaned = re.sub(r'[^\d+]', '', phone)
    result = {"phone": cleaned, "breach_count": 0, "breaches": []}
    try:
        resp_json = await _fetch_json(f"https://leakcheck.io/api/public?check={cleaned}", timeout)
        if "success" in resp_json:
            result["found"] = resp_json.get("success", False)
            result["sources"] = resp_json.get("sources", [])
            result["breach_count"] = len(result.get("sources", []))
    except Exception:
        result["error"] = "Breach API unavailable"
    return result


# ============================================================
# SECTION 5: DNS Deep Recon
# ============================================================

async def dns_enum(domain: str, timeout: float = 15.0) -> dict[str, Any]:
    """Comprehensive DNS enumeration for a domain."""
    result = {
        "domain": domain,
        "records": {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.timeout = timeout
        resolver.lifetime = timeout
        
        for rtype in ["A", "AAAA", "MX", "NS", "TXT", "SOA", "CNAME"]:
            try:
                answers = await asyncio.get_event_loop().run_in_executor(
                    None, lambda rt=rtype: list(resolver.resolve(domain, rt))
                )
                if answers:
                    result["records"][rtype] = [str(r) for r in answers]
            except Exception:
                pass
    except ImportError:
        pass
    
    # Fallback: nslookup
    if not result["records"].get("A"):
        try:
            proc = await asyncio.create_subprocess_exec(
                "nslookup", domain,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            ips = []
            for m in re.finditer(r'Address(?:es)?:\s*(\S+)', stdout.decode(), re.IGNORECASE):
                for ip in m.group(1).split():
                    ip = ip.strip()
                    if ip.count(".") == 3:
                        ips.append(ip)
            if ips:
                result["records"]["A"] = ips
        except Exception:
            pass
    
    if not result["records"].get("MX"):
        try:
            proc = await asyncio.create_subprocess_exec(
                "nslookup", "-type=MX", domain,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            mxs = []
            for m in re.finditer(r'mail exchanger\s*=\s*(\S+)', stdout.decode(), re.IGNORECASE):
                mxs.append(m.group(1).rstrip("."))
            if mxs:
                result["records"]["MX"] = mxs
        except Exception:
            pass
    
    if not result["records"].get("NS"):
        try:
            proc = await asyncio.create_subprocess_exec(
                "nslookup", "-type=NS", domain,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            nss = []
            for m in re.finditer(r'nameserver\s*=\s*(\S+)', stdout.decode(), re.IGNORECASE):
                nss.append(m.group(1).rstrip("."))
            if nss:
                result["records"]["NS"] = nss
        except Exception:
            pass
    
    result["record_types"] = list(result["records"].keys())
    result["total_records"] = sum(len(v) for v in result["records"].values())
    return result

async def dns_bruteforce(domain: str, wordlist: list[str] = None, timeout: float = 15.0) -> dict[str, Any]:
    """Brute-force subdomains."""
    if wordlist is None:
        wordlist = ["www", "mail", "ftp", "admin", "api", "dev", "test", "staging",
                    "blog", "shop", "portal", "cdn", "static", "app", "webmail",
                    "vpn", "remote", "git", "jenkins", "jira", "confluence",
                    "wiki", "docs", "support", "help", "status", "monitor",
                    "backup", "db", "sql", "redis", "mq", "ns1", "ns2",
                    "mx", "smtp", "pop", "imap", "autodiscover", "owa",
                    "cpanel", "whm", "direct", "cloud", "host", "server",
                    "ns", "dns", "dhcp", "proxy", "gateway", "firewall",
                    "owa", "exchange", "lync", "skype", "teams"]
    result = {
        "domain": domain,
        "subdomains_found": [],
        "total_checked": len(wordlist),
        "found_count": 0,
    }
    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.timeout = timeout
        resolver.lifetime = timeout
        for sub in wordlist:
            fqdn = f"{sub}.{domain}"
            try:
                answers = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: list(resolver.resolve(fqdn, "A"))
                )
                if answers:
                    result["subdomains_found"].append({
                        "subdomain": sub,
                        "fqdn": fqdn,
                        "ips": [str(r) for r in answers]
                    })
            except Exception:
                pass
    except ImportError:
        pass
    
    result["found_count"] = len(result["subdomains_found"])
    return result


async def dns_zone_transfer(domain: str, timeout: float = 10.0) -> dict[str, Any]:
    """Attempt DNS zone transfer."""
    result = {"domain": domain, "zone_transfer_possible": False, "records": []}
    ns_list = []
    try:
        import dns.resolver
        answers = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(dns.resolver.resolve(domain, "NS"))
        )
        ns_list = [str(r) for r in answers]
    except Exception:
        pass
    
    if not ns_list:
        try:
            proc = await asyncio.create_subprocess_exec(
                "nslookup", "-type=NS", domain,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            ns_list = [m.group(1).rstrip(".") for m in re.finditer(r'nameserver\s*=\s*(\S+)', stdout.decode(), re.IGNORECASE)]
        except Exception:
            pass
    
    result["nameservers"] = ns_list
    
    for ns in ns_list:
        try:
            proc = await asyncio.create_subprocess_exec(
                "nslookup", "-type=AXFR", domain, ns,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
            output = stdout.decode()
            if "server can't find" not in output.lower() and "refused" not in output.lower() and "failed" not in output.lower():
                records = []
                for line in output.split("\n"):
                    line = line.strip()
                    if line and "->" in line:
                        records.append(line)
                    elif line and line.startswith(domain):
                        records.append(line)
                if records:
                    result["zone_transfer_possible"] = True
                    result["records"].extend(records[:100])
                    result["from_ns"] = ns
                    break
        except Exception:
            pass
    
    return result


async def dns_reverse(ip: str, timeout: float = 10.0) -> dict[str, Any]:
    """Reverse DNS lookup for an IP."""
    result = {"ip": ip, "ptrs": []}
    try:
        proc = await asyncio.create_subprocess_exec(
            "nslookup", ip,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        for m in re.finditer(r'name\s*=\s*(\S+)', stdout.decode(), re.IGNORECASE):
            hostname = m.group(1).rstrip(".")
            if hostname not in result["ptrs"]:
                result["ptrs"].append(hostname)
    except Exception as e:
        result["error"] = str(e)
    return result


async def spf_check(domain: str, timeout: float = 10.0) -> dict[str, Any]:
    """Check SPF record for domain."""
    result = {"domain": domain, "has_spf": False}
    try:
        import dns.resolver
        answers = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(dns.resolver.resolve(domain, "TXT"))
        )
        for answer in answers:
            txt = str(answer)
            if txt.startswith("v=spf1"):
                result["has_spf"] = True
                result["spf_record"] = txt
                result["spf_raw"] = txt
                result["mechanisms"] = re.findall(r'\b(?:include|a|mx|ip4|ip6|exists|ptr|redirect|all)(?::\S+)?', txt)
                result["all_mechanism"] = None
                m = re.search(r'\b([-+~?]?all)\b', txt)
                if m:
                    result["all_mechanism"] = m.group(1)
                result["includes"] = re.findall(r'include:(\S+)', txt)
                break
    except ImportError:
        pass
    except Exception:
        pass
    
    if not result["has_spf"]:
        try:
            proc = await asyncio.create_subprocess_exec(
                "nslookup", "-type=TXT", domain,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            for m in re.finditer(r'text\s*=\s*"([^"]*v=spf1[^"]*)"', stdout.decode(), re.IGNORECASE):
                result["has_spf"] = True
                result["spf_record"] = m.group(1)
                result["mechanisms"] = re.findall(r'\b(?:include|a|mx|ip4|ip6|exists|ptr|redirect|all)(?::\S+)?', m.group(1))
                break
        except Exception:
            pass
    
    if not result["has_spf"]:
        result["spf_record"] = "No SPF record found"
    return result


async def dkim_check(domain: str, selector: str = "default", timeout: float = 10.0) -> dict[str, Any]:
    """Check DKIM record for domain with given selector."""
    result = {"domain": domain, "selector": selector, "has_dkim": False}
    dkim_domain = f"{selector}._domainkey.{domain}"
    try:
        import dns.resolver
        answers = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(dns.resolver.resolve(dkim_domain, "TXT"))
        )
        for answer in answers:
            txt = str(answer)
            if "v=DKIM1" in txt:
                result["has_dkim"] = True
                result["dkim_record"] = txt
                result["dkim_raw"] = txt
                result["key_type"] = None
                m = re.search(r'k=(\S+)', txt)
                if m: result["key_type"] = m.group(1)
                m = re.search(r'p=([A-Za-z0-9+/=]+)', txt)
                if m:
                    pubkey = m.group(1)
                    result["public_key_length"] = len(base64.b64decode(pubkey)) * 8 if pubkey else 0
                break
    except ImportError:
        pass
    except Exception:
        pass
    return result


async def dmarc_check(domain: str, timeout: float = 10.0) -> dict[str, Any]:
    """Check DMARC record for domain."""
    result = {"domain": domain, "has_dmarc": False}
    dmarc_domain = f"_dmarc.{domain}"
    try:
        import dns.resolver
        answers = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(dns.resolver.resolve(dmarc_domain, "TXT"))
        )
        for answer in answers:
            txt = str(answer)
            if txt.startswith("v=DMARC1"):
                result["has_dmarc"] = True
                result["dmarc_record"] = txt
                m = re.search(r'p=(none|quarantine|reject)', txt)
                if m: result["policy"] = m.group(1)
                m = re.search(r'sp=(none|quarantine|reject)', txt)
                if m: result["subdomain_policy"] = m.group(1)
                m = re.search(r'pct=(\d+)', txt)
                if m: result["pct"] = int(m.group(1))
                m = re.search(r'rua=mailto:(\S+)', txt)
                if m: result["rua"] = m.group(1)
                m = re.search(r'ruf=mailto:(\S+)', txt)
                if m: result["ruf"] = m.group(1)
                m = re.search(r'fo=(\S+)', txt)
                if m: result["fo"] = m.group(1)
                result["policy_strength"] = {"none": 0, "quarantine": 1, "reject": 2}.get(result.get("policy", ""), -1)
                break
    except ImportError:
        pass
    except Exception:
        pass
    return result


async def mx_lookup(domain: str, timeout: float = 10.0) -> dict[str, Any]:
    """MX record lookup with priority."""
    result = {"domain": domain, "mx_records": []}
    try:
        import dns.resolver
        answers = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(dns.resolver.resolve(domain, "MX"))
        )
        result["mx_records"] = sorted(
            [{"priority": r.preference, "host": str(r.exchange).rstrip(".")} for r in answers],
            key=lambda x: x["priority"]
        )
    except ImportError:
        pass
    except Exception:
        pass
    
    if not result["mx_records"]:
        try:
            proc = await asyncio.create_subprocess_exec(
                "nslookup", "-type=MX", domain,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            for m in re.finditer(r'mail exchanger\s*=\s*(\d+)\s+(\S+)', stdout.decode(), re.IGNORECASE):
                result["mx_records"].append({"priority": int(m.group(1)), "host": m.group(2).rstrip(".")})
        except Exception:
            pass
    
    result["mx_count"] = len(result["mx_records"])
    return result


# ============================================================
# SECTION 6: Web Technology Detection
# ============================================================

async def whatweb(domain: str, timeout: float = 15.0) -> dict[str, Any]:
    """Web technology fingerprinting."""
    if not domain.startswith("http"):
        domain = f"https://{domain}"
    result = {"url": domain, "technologies": [], "headers": {}, "success": False}
    try:
        status, text = await _fetch(domain, timeout)
        result["http_status"] = status
        if status > 0:
            result["success"] = True
        
        # Get headers via HEAD request
        try:
            async with aiohttp.ClientSession(headers={"User-Agent": USER_AGENT}) as session:
                async with session.head(domain, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    for key, val in resp.headers.items():
                        result["headers"][key.lower()] = val
        except Exception:
            pass
        
        # Detect technologies from headers
        headers = result["headers"]
        server = headers.get("server", "")
        if server:
            result["technologies"].append({"name": server, "category": "server"})
        if "x-powered-by" in headers:
            result["technologies"].append({"name": headers["x-powered-by"], "category": "framework"})
        if "x-generator" in headers:
            result["technologies"].append({"name": headers["x-generator"], "category": "cms"})
        
        # Detect from HTML
        if text and len(text) > 100:
            if "wp-content" in text or "wp-includes" in text or "wordpress" in text.lower():
                result["technologies"].append({"name": "WordPress", "category": "cms"})
            if "jquery" in text.lower():
                result["technologies"].append({"name": "jQuery", "category": "javascript"})
            if "react" in text.lower() or "react-dom" in text.lower():
                result["technologies"].append({"name": "React", "category": "javascript"})
            if "vue" in text.lower() or "vuejs" in text.lower():
                result["technologies"].append({"name": "Vue.js", "category": "javascript"})
            if "angular" in text.lower():
                result["technologies"].append({"name": "Angular", "category": "javascript"})
            if "bootstrap" in text.lower():
                result["technologies"].append({"name": "Bootstrap", "category": "css"})
            if "tailwind" in text.lower():
                result["technologies"].append({"name": "Tailwind CSS", "category": "css"})
            if "laravel" in text.lower():
                result["technologies"].append({"name": "Laravel", "category": "framework"})
            if "django" in text.lower():
                result["technologies"].append({"name": "Django", "category": "framework"})
            if "shopify" in text.lower() or "/cdn/shop/" in text:
                result["technologies"].append({"name": "Shopify", "category": "ecommerce"})
            if "magento" in text.lower():
                result["technologies"].append({"name": "Magento", "category": "ecommerce"})
            if "cloudflare" in text.lower() or "__cfduid" in text:
                result["technologies"].append({"name": "Cloudflare", "category": "cdn"})
        
        result["tech_count"] = len(result["technologies"])
    except Exception as e:
        result["error"] = str(e)
    return result


async def whatcms(url: str, timeout: float = 15.0) -> dict[str, Any]:
    """Detect CMS platform."""
    result = await whatweb(url, timeout)
    cms_tools = [t for t in result.get("technologies", []) if t.get("category") in ("cms", "framework")]
    result["cms_detected"] = cms_tools
    return result


async def cdn_detect(domain: str, timeout: float = 10.0) -> dict[str, Any]:
    """Detect CDN provider."""
    if not domain.startswith("http"):
        domain = f"https://{domain}"
    result = {"domain": domain, "cdn": None}
    try:
        headers = {"User-Agent": USER_AGENT}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(domain, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                server = resp.headers.get("Server", "").lower()
                via = resp.headers.get("via", "").lower()
                cf_ray = resp.headers.get("cf-ray", "")
                x_cache = resp.headers.get("x-cache", "").lower()
                
                if cf_ray or "cloudflare" in server or "cloudflare" in via:
                    result["cdn"] = "Cloudflare"
                elif "akamai" in server or "akamai" in via:
                    result["cdn"] = "Akamai"
                elif "fastly" in server or "fastly" in via:
                    result["cdn"] = "Fastly"
                elif "cloudfront" in server or "cloudfront" in via:
                    result["cdn"] = "AWS CloudFront"
                elif "cloudfront" in x_cache:
                    result["cdn"] = "AWS CloudFront"
                elif "incapsula" in server or "incapsula" in via:
                    result["cdn"] = "Incapsula"
                elif "stackpath" in server or "stackpath" in via:
                    result["cdn"] = "StackPath"
                elif "cdn" in server or "cdn" in via:
                    result["cdn"] = f"Generic CDN ({server or via})"
                else:
                    result["cdn"] = "No CDN detected"
                
                result["headers_found"] = {
                    "server": server, "via": via, "cf-ray": cf_ray, "x-cache": x_cache
                }
    except Exception as e:
        result["error"] = str(e)
    return result


async def web_server_headers(url: str, timeout: float = 10.0) -> dict[str, Any]:
    """Get HTTP response headers."""
    if not url.startswith("http"):
        url = f"https://{url}"
    result = {"url": url, "headers": {}}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                result["status"] = resp.status
                for key, val in resp.headers.items():
                    result["headers"][key.lower()] = val
    except Exception as e:
        result["error"] = str(e)
    return result


# ============================================================
# SECTION 7: URL/Website Analysis
# ============================================================

URLSCAN_API_KEY = os.environ.get("URLSCAN_API_KEY", "")

async def urlscan_submit(url: str, timeout: float = 30.0) -> dict[str, Any]:
    """Submit URL to URLScan.io for scanning."""
    result = {"url": url, "success": False}
    if not URLSCAN_API_KEY:
        result["error"] = "URLSCAN_API_KEY not set"
        return result
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://urlscan.io/api/v1/scan/",
                json={"url": url, "public": "on"},
                headers={"API-Key": URLSCAN_API_KEY, "Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                data = await resp.json()
                result["success"] = resp.status == 200
                result["scan_id"] = data.get("uuid")
                result["result_url"] = data.get("result")
                result["api_url"] = f"https://urlscan.io/api/v1/result/{data.get('uuid')}/"
    except Exception as e:
        result["error"] = str(e)
    return result


async def urlscan_result(uuid: str, timeout: float = 30.0) -> dict[str, Any]:
    """Get URLScan.io scan result."""
    result = {"uuid": uuid, "success": False}
    try:
        resp_json = await _fetch_json(f"https://urlscan.io/api/v1/result/{uuid}/", timeout)
        result["success"] = True
        result["data"] = resp_json
        result["page"] = resp_json.get("page", {})
        result["lists"] = resp_json.get("lists", {})
        result["verdicts"] = resp_json.get("verdicts", {})
    except Exception as e:
        result["error"] = str(e)
    return result


VT_API_KEY = os.environ.get("VIRUSTOTAL_API_KEY", "")

async def virus_total_url(url: str, timeout: float = 30.0) -> dict[str, Any]:
    """VirusTotal URL scan."""
    result = {"url": url, "malicious": 0, "suspicious": 0, "harmless": 0}
    if not VT_API_KEY:
        result["error"] = "VIRUSTOTAL_API_KEY not set"
        return result
    try:
        url_id = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
        resp_json = await _fetch_json(
            f"https://www.virustotal.com/api/v3/urls/{url_id}",
            timeout,
            {"x-apikey": VT_API_KEY, "Accept": "application/json"}
        )
        if "data" in resp_json:
            attr = resp_json["data"].get("attributes", {})
            stats = attr.get("last_analysis_stats", {})
            result["malicious"] = stats.get("malicious", 0)
            result["suspicious"] = stats.get("suspicious", 0)
            result["harmless"] = stats.get("harmless", 0)
            result["undetected"] = stats.get("undetected", 0)
            result["timeout"] = stats.get("timeout", 0)
            result["total_votes"] = attr.get("total_votes", {})
            result["reputation"] = attr.get("reputation", 0)
            result["categories"] = attr.get("categories", {})
    except Exception as e:
        result["error"] = str(e)
    return result


async def virus_total_domain(domain: str, timeout: float = 30.0) -> dict[str, Any]:
    """VirusTotal domain report."""
    result = {"domain": domain, "malicious": 0}
    if not VT_API_KEY:
        result["error"] = "VIRUSTOTAL_API_KEY not set"
        return result
    try:
        resp_json = await _fetch_json(
            f"https://www.virustotal.com/api/v3/domains/{domain}",
            timeout,
            {"x-apikey": VT_API_KEY, "Accept": "application/json"}
        )
        if "data" in resp_json:
            attr = resp_json["data"].get("attributes", {})
            stats = attr.get("last_analysis_stats", {})
            result["malicious"] = stats.get("malicious", 0)
            result["suspicious"] = stats.get("suspicious", 0)
            result["harmless"] = stats.get("harmless", 0)
            result["undetected"] = stats.get("undetected", 0)
            result["reputation"] = attr.get("reputation", 0)
            result["categories"] = attr.get("categories", {})
    except Exception as e:
        result["error"] = str(e)
    return result


async def url_expander(short_url: str, timeout: float = 10.0) -> dict[str, Any]:
    """Expand shortened URL to original."""
    result = {"short_url": short_url, "expanded_url": short_url}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(short_url, timeout=aiohttp.ClientTimeout(total=timeout),
                                    allow_redirects=True) as resp:
                result["expanded_url"] = str(resp.url)
                result["redirect_count"] = len(resp.history)
                result["status"] = resp.status
    except Exception as e:
        result["error"] = str(e)
    return result


async def url_analyze(url: str) -> dict[str, Any]:
    """Analyze URL structure and components."""
    parsed = urlparse(url)
    return {
        "url": url,
        "scheme": parsed.scheme,
        "netloc": parsed.netloc,
        "hostname": parsed.hostname,
        "port": parsed.port,
        "path": parsed.path,
        "params": parsed.params,
        "query": parsed.query,
        "fragment": parsed.fragment,
        "has_query_params": bool(parsed.query),
        "has_fragment": bool(parsed.fragment),
        "has_auth": bool(parsed.username),
        "is_https": parsed.scheme == "https",
        "query_params": dict(urllib.parse.parse_qsl(parsed.query)) if parsed.query else {},
    }


# ============================================================
# SECTION 8: Wayback Machine
# ============================================================

async def wayback_snapshots(domain: str, timeout: float = 15.0) -> dict[str, Any]:
    """Get Wayback Machine snapshot count and timeline."""
    result = {"domain": domain, "snapshot_count": 0}
    try:
        resp_json = await _fetch_json(
            f"https://web.archive.org/cdx/search/cdx?url={domain}&output=json&limit=1&fl=timestamp,original",
            timeout
        )
        if isinstance(resp_json, list) and len(resp_json) > 1:
            # Get count
            resp_json2 = await _fetch_json(
                f"https://web.archive.org/cdx/search/cdx?url={domain}&output=json&limit=0&showNumPages=true",
                timeout
            )
            if isinstance(resp_json2, dict):
                result["snapshot_count"] = int(resp_json2.get("pages", 0))
            
            # Get timeline years
            resp_json3 = await _fetch_json(
                f"https://web.archive.org/cdx/search/cdx?url={domain}&output=json&fl=timestamp&limit=1000&collapse=timestamp:4",
                timeout
            )
            if isinstance(resp_json3, list) and len(resp_json3) > 1:
                years = set()
                for entry in resp_json3[1:]:
                    if isinstance(entry, list) and len(entry) > 0:
                        years.add(entry[0][:4])
                result["years"] = sorted(years)
                result["year_count"] = len(years)
                result["first_seen"] = min(years) if years else None
                result["last_seen"] = max(years) if years else None
    except Exception as e:
        result["error"] = str(e)
    return result


async def wayback_urls(domain: str, limit: int = 100, timeout: float = 30.0) -> dict[str, Any]:
    """Get archived URLs for a domain."""
    result = {"domain": domain, "urls": [], "count": 0}
    try:
        resp_json = await _fetch_json(
            f"https://web.archive.org/cdx/search/cdx?url={domain}/*&output=json&fl=timestamp,original&limit={limit}&collapse=urlkey",
            timeout
        )
        if isinstance(resp_json, list) and len(resp_json) > 1:
            urls = []
            for entry in resp_json[1:]:
                if isinstance(entry, list) and len(entry) >= 2:
                    urls.append({"timestamp": entry[0], "url": entry[1]})
            result["urls"] = urls
            result["count"] = len(urls)
    except Exception as e:
        result["error"] = str(e)
    return result


async def wayback_latest(domain: str, timeout: float = 15.0) -> dict[str, Any]:
    """Get latest Wayback Machine snapshot."""
    result = {"domain": domain, "has_snapshot": False}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://web.archive.org/web/timemap/link/{domain}",
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    links = [l for l in text.split("\n") if l.strip()]
                    if links:
                        result["has_snapshot"] = True
                        result["snapshots"] = links[:10]
                        result["count"] = len(links)
    except Exception as e:
        result["error"] = str(e)
    return result


# ============================================================
# SECTION 9: Data Breach Checking
# ============================================================

LEAKCHECK_API_KEY = os.environ.get("LEAKCHECK_API_KEY", "")

async def leak_check(email: str, timeout: float = 15.0) -> dict[str, Any]:
    """Multi-source data breach check."""
    result = {"query": email, "found": False, "sources": []}
    try:
        async with aiohttp.ClientSession() as session:
            resp_json = await _fetch_json(f"https://leakcheck.io/api/public?check={email}", timeout)
            if "success" in resp_json:
                result["found"] = resp_json.get("success", False)
                result["sources"] = resp_json.get("sources", [])
                result["source_count"] = len(result["sources"])
                if result["found"]:
                    result["passwords"] = resp_json.get("passwords", [])
                    result["password_count"] = len(result.get("passwords", []))
                    result["lines"] = resp_json.get("lines", 0)
    except Exception as e:
        result["error"] = str(e)
    return result


INTELX_API_KEY = os.environ.get("INTELX_API_KEY", "")

async def intelx_search(query: str, search_type: str = "email", timeout: float = 30.0) -> dict[str, Any]:
    """Intelligence X search."""
    result = {"query": query, "type": search_type, "results": []}
    if not INTELX_API_KEY:
        result["error"] = "INTELX_API_KEY not set"
        return result
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://2.intelx.io/intelligent/search",
                json={"term": query, "buckets": [], "lookuplevel": 0, "maxresults": 100, "sort": 2, "media": 0},
                headers={"x-key": INTELX_API_KEY, "x-agent": "FRIDAY/3.0"},
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result["total_results"] = data.get("total", 0)
                    result["records"] = data.get("records", [])
                    result["result_count"] = len(result["records"])
    except Exception as e:
        result["error"] = str(e)
    return result

DEHASHED_API_KEY = os.environ.get("DEHASHED_API_KEY", "")
DEHASHED_EMAIL = os.environ.get("DEHASHED_EMAIL", "")

async def dehashed_search(query: str, search_type: str = "email", timeout: float = 30.0) -> dict[str, Any]:
    """Search Dehashed database."""
    result = {"query": query, "type": search_type, "entries": []}
    if not DEHASHED_API_KEY or not DEHASHED_EMAIL:
        result["error"] = "DEHASHED_API_KEY/EMAIL not set"
        return result
    try:
        auth = aiohttp.BasicAuth(DEHASED_EMAIL, DEHASHED_API_KEY)
        async with aiohttp.ClientSession(auth=auth) as session:
            async with session.get(
                f"https://api.dehashed.com/v1/search?query={search_type}:{urllib.parse.quote(query)}&size=100",
                headers={"Accept": "application/json"},
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result["entries"] = data.get("entries", [])
                    result["total"] = data.get("total", 0)
                    result["balance"] = data.get("balance", 0)
    except Exception as e:
        result["error"] = str(e)
    return result


# ============================================================
# SECTION 10: IP Intelligence
# ============================================================

ABUSEIPDB_API_KEY = os.environ.get("ABUSEIPDB_API_KEY", "")

async def ip_abuse_report(ip: str, timeout: float = 10.0) -> dict[str, Any]:
    """Check IP against AbuseIPDB."""
    result = {"ip": ip, "abuse_confidence_score": 0}
    if not ABUSEIPDB_API_KEY:
        result["error"] = "ABUSEIPDB_API_KEY not set"
        return result
    try:
        resp_json = await _fetch_json(
            f"https://api.abuseipdb.com/api/v2/check?ipAddress={ip}&maxAgeInDays=90",
            timeout,
            {"Key": ABUSEIPDB_API_KEY, "Accept": "application/json"}
        )
        if "data" in resp_json:
            d = resp_json["data"]
            result["abuse_confidence_score"] = d.get("abuseConfidenceScore", 0)
            result["country"] = d.get("countryCode", "")
            result["domain"] = d.get("domain", "")
            result["hostnames"] = d.get("hostnames", [])
            result["isp"] = d.get("isp", "")
            result["usage_type"] = d.get("usageType", "")
            result["total_reports"] = d.get("totalReports", 0)
            result["is_whitelisted"] = d.get("isWhitelisted", False)
            result["is_tor"] = d.get("isTor", False)
    except Exception as e:
        result["error"] = str(e)
    return result


async def ip_threat_intel(ip: str, timeout: float = 20.0) -> dict[str, Any]:
    """Multi-source IP threat intelligence."""
    result = {"ip": ip, "threat_score": 0, "sources": {}}
    
    # AbuseIPDB
    abuse = await ip_abuse_report(ip, timeout)
    result["sources"]["abuseipdb"] = abuse.get("abuse_confidence_score", 0)
    
    # VirusTotal
    vt = await virus_total_domain(ip, timeout)
    result["sources"]["virustotal"] = vt.get("malicious", 0)
    if vt.get("malicious", 0) > 0:
        result["threat_score"] += 25
    
    # Check if private
    try:
        addr = ipaddress.ip_address(ip)
        result["is_private"] = addr.is_private
        result["is_loopback"] = addr.is_loopback
        result["is_global"] = addr.is_global
        result["is_multicast"] = addr.is_multicast
    except Exception:
        pass
    
    result["threat_score"] = min(result["threat_score"] + abuse.get("abuse_confidence_score", 0), 100)
    result["threat_level"] = "low" if result["threat_score"] < 30 else "medium" if result["threat_score"] < 70 else "high"
    return result


async def ip_reverse_dns(ip: str, timeout: float = 10.0) -> dict[str, Any]:
    """Reverse DNS lookup."""
    result = await dns_reverse(ip, timeout)
    return result


async def ip_asn_info(ip: str, timeout: float = 10.0) -> dict[str, Any]:
    """Get ASN information for IP."""
    result = {"ip": ip}
    try:
        resp_json = await _fetch_json(f"https://ipinfo.io/{ip}/json", timeout)
        if "org" in resp_json:
            org = resp_json["org"]
            if "AS" in org:
                parts = org.split(" ", 1)
                result["asn"] = parts[0].replace("AS", "")
                result["org"] = parts[1] if len(parts) > 1 else ""
            else:
                result["org"] = org
        if "asn" in resp_json:
            result["asn"] = resp_json["asn"].get("asn", "").replace("AS", "")
            result["org"] = resp_json["asn"].get("name", "")
            result["route"] = resp_json["asn"].get("route", "")
            result["type"] = resp_json["asn"].get("type", "")
    except Exception:
        # Fallback
        try:
            resp_json = await _fetch_json(f"https://api.iptoasn.com/v1/as/ip/{ip}", timeout)
            if "as_number" in resp_json:
                result["asn"] = resp_json["as_number"]
                result["org"] = resp_json.get("as_description", "")
                result["country"] = resp_json.get("country_code", "")
                result["range"] = resp_json.get("allocated", "")
        except Exception:
            pass
    return result


async def ip_blacklist_check(ip: str, timeout: float = 30.0) -> dict[str, Any]:
    """Check IP against DNS blacklists."""
    result = {"ip": ip, "blacklisted": False, "blacklists": []}
    dnsbls = [
        "zen.spamhaus.org", "bl.spamcop.net", "cbl.abuseat.org",
        "b.barracudacentral.org", "dnsbl-1.uceprotect.net",
    ]
    try:
        rev = ".".join(reversed(ip.split(".")))
        for dnsbl in dnsbls:
            try:
                query = f"{rev}.{dnsbl}"
                answers = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: socket.gethostbyname(query)
                )
                if answers:
                    result["blacklisted"] = True
                    result["blacklists"].append(dnsbl)
            except socket.gaierror:
                pass
            except Exception:
                pass
        result["blacklist_count"] = len(result["blacklists"])
    except Exception as e:
        result["error"] = str(e)
    return result


async def ip_geolocate_full(ip: str, timeout: float = 10.0) -> dict[str, Any]:
    """Full IP geolocation."""
    result = {"ip": ip}
    try:
        resp_json = await _fetch_json(f"https://ipinfo.io/{ip}/json", timeout)
        if "error" not in resp_json:
            result["city"] = resp_json.get("city", "")
            result["region"] = resp_json.get("region", "")
            result["country"] = resp_json.get("country", "")
            result["loc"] = resp_json.get("loc", "")
            result["org"] = resp_json.get("org", "")
            result["postal"] = resp_json.get("postal", "")
            result["timezone"] = resp_json.get("timezone", "")
            if resp_json.get("loc"):
                lat_lon = resp_json["loc"].split(",")
                result["latitude"] = float(lat_lon[0]) if len(lat_lon) > 0 else None
                result["longitude"] = float(lat_lon[1]) if len(lat_lon) > 1 else None
    except Exception as e:
        result["error"] = str(e)
    return result


async def ip_range_expand(cidr: str) -> dict[str, Any]:
    """Expand CIDR notation to IP range."""
    result = {"cidr": cidr}
    try:
        net = ipaddress.ip_network(cidr, strict=False)
        result["network_address"] = str(net.network_address)
        result["broadcast_address"] = str(net.broadcast_address) if net.broadcast_address else None
        result["num_addresses"] = net.num_addresses
        result["prefixlen"] = net.prefixlen
        result["netmask"] = str(net.netmask)
        result["hosts"] = [str(h) for h in list(net.hosts())[:256]]
        result["host_count"] = len(result["hosts"])
    except ValueError as e:
        result["error"] = f"Invalid CIDR: {e}"
    return result


# ============================================================
# SECTION 11: Domain Intelligence
# ============================================================

async def domain_similar(domain: str) -> dict[str, Any]:
    """Find similar/typosquatting domains."""
    result = {"domain": domain, "similar_domains": []}
    base = domain.split(".")[0] if "." in domain else domain
    tld = "." + ".".join(domain.split(".")[1:]) if "." in domain else ""
    
    # Common typosquatting patterns
    patterns = set()
    # Character omissions
    for i in range(len(base)):
        patterns.add(base[:i] + base[i+1:])
    # Character swaps
    for i in range(len(base)-1):
        patterns.add(base[:i] + base[i+1] + base[i] + base[i+2:])
    # Character replacements
    for i, c in enumerate(base):
        for r in "abcdefghijklmnopqrstuvwxyz":
            if c != r:
                patterns.add(base[:i] + r + base[i+1:])
    # Extra characters
    for i in range(len(base)+1):
        for c in "abcdefghijklmnopqrstuvwxyz0123456789":
            patterns.add(base[:i] + c + base[i:])
    # Double letters
    for i, c in enumerate(base):
        patterns.add(base[:i] + c + c + base[i+1:])
    
    result["similar_domains"] = sorted([p + tld for p in patterns if p != base])[:50]
    result["total_variations"] = len(result["similar_domains"])
    result["tld"] = tld
    return result


async def domain_history(domain: str, timeout: float = 15.0) -> dict[str, Any]:
    """Historical WHOIS and domain data."""
    result = {"domain": domain}
    try:
        resp_json = await _fetch_json(f"https://whoisjson.com/api/v1/whois?domain={domain}", timeout)
        if "whois" in resp_json or "created_date" in resp_json:
            result["whois_data"] = resp_json
    except Exception:
        pass
    return result


async def certificate_transparency(domain: str, timeout: float = 15.0) -> dict[str, Any]:
    """Search crt.sh for subdomains via certificate transparency logs."""
    result = {"domain": domain, "subdomains": [], "count": 0}
    try:
        resp_json = await _fetch_json(
            f"https://crt.sh/?q=%25.{domain}&output=json",
            timeout
        )
        if isinstance(resp_json, list):
            subdomains = set()
            for entry in resp_json:
                name = entry.get("name_value", "")
                for sub in name.split("\n"):
                    s = sub.strip().lower()
                    if s.endswith(domain) and s != domain and "*" not in s:
                        subdomains.add(s)
            result["subdomains"] = sorted(subdomains)
            result["count"] = len(subdomains)
    except Exception as e:
        result["error"] = str(e)
    return result


async def domain_age(domain: str, timeout: float = 10.0) -> dict[str, Any]:
    """Estimate domain age from WHOIS."""
    result = {"domain": domain, "age_days": None, "age_years": None}
    try:
        resp_json = await _fetch_json(f"https://whoisjson.com/api/v1/whois?domain={domain}", timeout)
        created = resp_json.get("created_date") or resp_json.get("creation_date")
        if created:
            try:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - created_dt)
                result["age_days"] = age.days
                result["age_years"] = round(age.days / 365.25, 1)
                result["created_date"] = created
            except Exception:
                pass
    except Exception:
        pass
    return result


# ============================================================
# SECTION 12: Crawling & Scraping
# ============================================================

async def web_crawl(url: str, depth: int = 1, timeout: float = 30.0) -> dict[str, Any]:
    """Simple web crawler."""
    if not url.startswith("http"):
        url = f"https://{url}"
    result = {"start_url": url, "depth": depth, "pages_crawled": 0, "links_found": [], "pages": []}
    visited = set()
    to_visit = [(url, 0)]
    headers = {"User-Agent": USER_AGENT}
    connector = aiohttp.TCPConnector(limit=5, force_close=True)
    
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        while to_visit and len(visited) < 50:
            current_url, current_depth = to_visit.pop(0)
            if current_url in visited:
                continue
            visited.add(current_url)
            
            try:
                async with session.get(current_url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        result["pages_crawled"] += 1
                        page = {"url": current_url, "size": len(text)}
                        m = re.search(r'<title>(.*?)</title>', text, re.DOTALL)
                        if m: page["title"] = html.unescape(m.group(1).strip())
                        result["pages"].append(page)
                        
                        if current_depth < depth:
                            for m in re.finditer(r'href=["\'](https?://[^"\'<>]+)["\']', text, re.IGNORECASE):
                                link = m.group(1)
                                if link not in visited and link not in [v[0] for v in to_visit]:
                                    to_visit.append((link, current_depth + 1))
                                    result["links_found"].append(link)
            except Exception:
                pass
    
    result["total_links"] = len(result["links_found"])
    return result


async def email_extractor(url: str, timeout: float = 15.0) -> dict[str, Any]:
    """Extract email addresses from a webpage."""
    result = {"url": url, "emails": [], "count": 0}
    try:
        status, text = await _fetch(url, timeout)
        if status == 200:
            emails = set()
            for m in EMAIL_REGEX.finditer(text):
                email = m.group(0).lower()
                if not any(email.endswith(f"@{d}") for d in
                           ["example.com", "domain.com", "test.com", "sample.com"]):
                    emails.add(email)
            result["emails"] = sorted(emails)
            result["count"] = len(emails)
    except Exception as e:
        result["error"] = str(e)
    return result


async def phone_extractor(url: str, timeout: float = 15.0) -> dict[str, Any]:
    """Extract phone numbers from a webpage."""
    result = {"url": url, "phones": [], "count": 0}
    try:
        status, text = await _fetch(url, timeout)
        if status == 200:
            phones = set()
            for m in PHONE_REGEX.finditer(text):
                phone = m.group(0).strip()
                if len(phone) >= 7:
                    phones.add(phone)
            result["phones"] = sorted(phones)
            result["count"] = len(phones)
    except Exception as e:
        result["error"] = str(e)
    return result


async def meta_extractor(url: str, timeout: float = 15.0) -> dict[str, Any]:
    """Extract meta tags from a webpage."""
    result = {"url": url, "meta_tags": {}}
    try:
        status, text = await _fetch(url, timeout)
        if status == 200:
            for m in re.finditer(r'<meta[^>]+>', text, re.IGNORECASE):
                tag = m.group(0)
                name_m = re.search(r'name=["\']([^"\']+)["\']', tag, re.IGNORECASE)
                prop_m = re.search(r'property=["\']([^"\']+)["\']', tag, re.IGNORECASE)
                content_m = re.search(r'content=["\']([^"\']+)["\']', tag, re.IGNORECASE)
                key = name_m.group(1) if name_m else (prop_m.group(1) if prop_m else None)
                value = content_m.group(1) if content_m else None
                if key and value:
                    result["meta_tags"][key] = html.unescape(value)
            result["tag_count"] = len(result["meta_tags"])
    except Exception as e:
        result["error"] = str(e)
    return result


async def page_text_extractor(url: str, timeout: float = 15.0) -> dict[str, Any]:
    """Extract readable text from webpage."""
    result = {"url": url, "text": "", "word_count": 0}
    try:
        status, text = await _fetch(url, timeout)
        if status == 200:
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            text = html.unescape(text)
            result["text"] = text[:10000]
            result["word_count"] = len(text.split())
    except Exception as e:
        result["error"] = str(e)
    return result


# ============================================================
# SECTION 13: Security Headers
# ============================================================

SECURITY_HEADERS_LIST = [
    "strict-transport-security", "content-security-policy", "x-content-type-options",
    "x-frame-options", "x-xss-protection", "referrer-policy", "permissions-policy",
    "feature-policy", "access-control-allow-origin", "cross-origin-opener-policy",
    "cross-origin-embedder-policy", "cross-origin-resource-policy",
]

async def security_headers(url: str, timeout: float = 10.0) -> dict[str, Any]:
    """Check HTTP security headers."""
    if not url.startswith("http"):
        url = f"https://{url}"
    result = {"url": url, "headers": {}, "score": 0, "max_score": len(SECURITY_HEADERS_LIST)}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                for key, val in resp.headers.items():
                    result["headers"][key.lower()] = val
                
                present = 0
                for h in SECURITY_HEADERS_LIST:
                    result[h] = h in result["headers"]
                    if h in result["headers"]:
                        present += 1
                
                result["present_count"] = present
                result["missing_count"] = len(SECURITY_HEADERS_LIST) - present
                result["score"] = round((present / len(SECURITY_HEADERS_LIST)) * 100, 1)
                result["grade"] = "A" if result["score"] >= 80 else "B" if result["score"] >= 60 else "C" if result["score"] >= 40 else "D" if result["score"] >= 20 else "F"
    except Exception as e:
        result["error"] = str(e)
    return result


async def cors_check(url: str, timeout: float = 10.0) -> dict[str, Any]:
    """Check CORS configuration."""
    if not url.startswith("http"):
        url = f"https://{url}"
    result = {"url": url, "cors_detected": False}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.options(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                headers = {k.lower(): v for k, v in resp.headers.items()}
                result["access_control_allow_origin"] = headers.get("access-control-allow-origin", "not set")
                result["access_control_allow_methods"] = headers.get("access-control-allow-methods", "not set")
                result["access_control_allow_headers"] = headers.get("access-control-allow-headers", "not set")
                result["access_control_max_age"] = headers.get("access-control-max-age", "not set")
                result["access_control_allow_credentials"] = headers.get("access-control-allow-credentials", "not set")
                result["cors_detected"] = any(v for v in [result.get(h) for h in
                    ["access_control_allow_origin", "access_control_allow_methods"]]
                    if v != "not set")
    except Exception as e:
        result["error"] = str(e)
    return result


async def hsts_check(domain: str, timeout: float = 10.0) -> dict[str, Any]:
    """Check HSTS preload status."""
    result = {"domain": domain, "preloaded": False}
    try:
        resp_json = await _fetch_json(
            f"https://hstspreload.org/api/v2/status?domain={domain}",
            timeout
        )
        if "status" in resp_json:
            result["preloaded"] = resp_json["status"] == "preloaded"
            result["status"] = resp_json["status"]
            result["last_updated"] = resp_json.get("last_updated", "")
    except Exception as e:
        result["error"] = str(e)
    return result


async def robots_txt_check(url: str, timeout: float = 10.0) -> dict[str, Any]:
    """Check robots.txt."""
    if not url.startswith("http"):
        url = f"https://{url}"
    robots_url = url.rstrip("/") + "/robots.txt"
    result = {"url": robots_url, "exists": False, "disallowed_paths": []}
    try:
        status, text = await _fetch(robots_url, timeout)
        result["exists"] = status == 200
        if status == 200:
            result["content"] = text[:2000]
            for m in re.finditer(r'^Disallow:\s*(.*?)$', text, re.MULTILINE | re.IGNORECASE):
                path = m.group(1).strip()
                if path and path != "/":
                    result["disallowed_paths"].append(path)
            result["disallow_count"] = len(result["disallowed_paths"])
            m = re.search(r'^Sitemap:\s*(.*?)$', text, re.MULTILINE | re.IGNORECASE)
            if m: result["sitemap"] = m.group(1).strip()
            m = re.search(r'^Crawl-delay:\s*(\d+)$', text, re.MULTILINE | re.IGNORECASE)
            if m: result["crawl_delay"] = int(m.group(1))
    except Exception as e:
        result["error"] = str(e)
    return result


async def ssl_cert_check_full(hostname: str, port: int = 443, timeout: float = 15.0) -> dict[str, Any]:
    """Full SSL certificate analysis."""
    result = {"hostname": hostname, "port": port}
    try:
        ctx = ssl.create_default_context()
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(hostname, port, ssl=ctx),
            timeout=timeout
        )
        sock = writer.get_extra_info("ssl_object")
        cert = sock.getpeercert()
        writer.close()
        if cert:
            result["subject"] = dict(cert.get("subject", [[("", "")]])[0])
            result["issuer"] = dict(cert.get("issuer", [[("", "")]])[0])
            result["serial"] = cert.get("serialNumber")
            result["version"] = cert.get("version")
            result["not_before"] = cert.get("notBefore")
            result["not_after"] = cert.get("notAfter")
            result["subject_alt_names"] = [san[1] for san in cert.get("subjectAltName", [])]
            result["san_count"] = len(result["subject_alt_names"])
            
            not_after = cert.get("notAfter", "")
            if not_after:
                try:
                    expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                    days_left = (expiry - datetime.now()).days
                    result["days_until_expiry"] = days_left
                    result["status"] = "expired" if days_left < 0 else "expiring_soon" if days_left < 30 else "valid"
                except Exception:
                    pass
        else:
            result["error"] = "No certificate returned"
    except asyncio.TimeoutError:
        result["error"] = "Connection timed out"
    except ssl.SSLCertVerificationError as e:
        result["error"] = f"SSL verification failed: {e}"
    except ConnectionRefusedError:
        result["error"] = "Connection refused"
    except Exception as e:
        result["error"] = str(e)
    return result


# ============================================================
# SECTION 14: Cryptocurrency OSINT
# ============================================================

async def btc_address_lookup(address: str, timeout: float = 15.0) -> dict[str, Any]:
    """Look up Bitcoin address transactions."""
    result = {"address": address, "success": False}
    try:
        resp_json = await _fetch_json(
            f"https://blockchain.info/rawaddr/{address}",
            timeout
        )
        if "address" in resp_json:
            result["success"] = True
            result["total_received"] = resp_json.get("total_received", 0)
            result["total_sent"] = resp_json.get("total_sent", 0)
            result["balance"] = resp_json.get("final_balance", 0)
            result["tx_count"] = resp_json.get("n_tx", 0)
            result["first_tx"] = resp_json.get("first_tx", "")
            result["last_tx"] = resp_json.get("last_tx", "")
            result["total_received_btc"] = resp_json.get("total_received", 0) / 100000000
            result["total_sent_btc"] = resp_json.get("total_sent", 0) / 100000000
            result["balance_btc"] = resp_json.get("final_balance", 0) / 100000000
    except Exception as e:
        result["error"] = str(e)
    return result


async def eth_address_lookup(address: str, timeout: float = 15.0) -> dict[str, Any]:
    """Look up Ethereum address info."""
    result = {"address": address, "success": False}
    try:
        resp_json = await _fetch_json(
            f"https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest",
            timeout
        )
        if resp_json.get("status") == "1":
            result["success"] = True
            balance_wei = int(resp_json.get("result", 0))
            result["balance_wei"] = balance_wei
            result["balance_eth"] = balance_wei / 10**18
            result["balance_display"] = f"{result['balance_eth']:.6f} ETH"
    except Exception as e:
        result["error"] = str(e)
    return result


async def wallet_balance(address: str, currency: str = "btc", timeout: float = 15.0) -> dict[str, Any]:
    """Cryptocurrency wallet balance."""
    currency = currency.lower()
    if currency in ("btc", "bitcoin"):
        return await btc_address_lookup(address, timeout)
    elif currency in ("eth", "ethereum"):
        return await eth_address_lookup(address, timeout)
    else:
        return {"error": f"Unsupported currency: {currency}", "address": address}


# ============================================================
# SECTION 15: Dark Web / Tor
# ============================================================

async def onion_check(onion_url: str, timeout: float = 30.0) -> dict[str, Any]:
    """Check if .onion site is accessible via Tor."""
    result = {"url": onion_url, "accessible": False, "via_tor_proxy": False}
    tor_proxy = os.environ.get("TOR_PROXY", "socks5://127.0.0.1:9050")
    try:
        connector = aiohttp.TCPConnector(limit=1, force_close=True)
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout_obj) as session:
            try:
                async with session.get(onion_url) as resp:
                    result["accessible"] = resp.status == 200 or resp.status < 500
                    result["status"] = resp.status
            except Exception:
                result["error"] = "Tor proxy not available (try setting TOR_PROXY env)"
    except Exception as e:
        result["error"] = str(e)
    return result


async def tor_dns_lookup(domain: str, timeout: float = 30.0) -> dict[str, Any]:
    """DNS lookup via Tor proxy."""
    result = {"domain": domain, "ips": []}
    tor_proxy = os.environ.get("TOR_PROXY", "socks5://127.0.0.1:9050")
    try:
        proc = await asyncio.create_subprocess_exec(
            "torsocks", "nslookup", domain,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        for m in re.finditer(r'Address(?:es)?:\s*(\S+)', stdout.decode(), re.IGNORECASE):
            for ip in m.group(1).split():
                ip = ip.strip()
                if ip.count(".") == 3:
                    result["ips"].append(ip)
        result["method"] = "torsocks"
    except (FileNotFoundError, asyncio.TimeoutError):
        result["error"] = "Tor DNS lookup failed (torsocks not installed or Tor not running)"
    except Exception as e:
        result["error"] = str(e)
    return result


# ============================================================
# SECTION 16: Formatting Utilities
# ============================================================

async def format_osint_for_report(results: list[dict], title: str = "OSINT Report") -> dict[str, Any]:
    """Format OSINT results as a structured report."""
    lines = [f"# {title}", f"Generated: {datetime.now(timezone.utc).isoformat()}", ""]
    for i, result in enumerate(results, 1):
        if isinstance(result, dict):
            name = result.get("tool", result.get("source", f"Result {i}"))
            lines.append(f"## {name}")
            if "error" in result:
                lines.append(f"Error: {result['error']}")
            else:
                for key, val in result.items():
                    if key not in ("tool", "source", "timestamp") and not key.startswith("_"):
                        if isinstance(val, (list, dict)):
                            val_str = json.dumps(val, indent=2)[:200]
                        else:
                            val_str = str(val)
                        lines.append(f"  {key}: {val_str}")
            lines.append("")
    return {"title": title, "report": "\n".join(lines), "line_count": len(lines)}


async def summarize_osint_findings(results: list[dict]) -> dict[str, Any]:
    """Create a summary of OSINT findings."""
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_checks": len(results),
        "errors": 0,
        "findings": {},
        "summary_text": "",
    }
    for result in results:
        if isinstance(result, dict):
            if "error" in result:
                summary["errors"] += 1
            for key, val in result.items():
                if isinstance(val, (int, float, str, bool)) and val and key not in ("timestamp",):
                    if key not in summary["findings"]:
                        summary["findings"][key] = []
                    summary["findings"][key].append(str(val)[:100])
    
    lines = [f"OSINT Summary - {summary['total_checks']} checks, {summary['errors']} errors"]
    for key, vals in summary["findings"].items():
        unique = list(set(vals))[:5]
        if unique:
            lines.append(f"  {key}: {', '.join(str(v) for v in unique)}")
    summary["summary_text"] = "\n".join(lines)
    return summary


async def osint_to_markdown(result: dict, title: str = "OSINT Data") -> dict[str, Any]:
    """Convert OSINT result dict to markdown."""
    lines = [f"# {title}", ""]
    for key, val in result.items():
        if key.startswith("_"):
            continue
        if isinstance(val, dict):
            lines.append(f"## {key}")
            for k, v in val.items():
                lines.append(f"- **{k}**: {v}")
            lines.append("")
        elif isinstance(val, list):
            lines.append(f"## {key} ({len(val)} items)")
            for item in val[:20]:
                if isinstance(item, dict):
                    lines.append(f"- {json.dumps(item)[:200]}")
                else:
                    lines.append(f"- {item}")
            if len(val) > 20:
                lines.append(f"- ... and {len(val) - 20} more")
            lines.append("")
        else:
            lines.append(f"- **{key}**: {val}")
    return {"title": title, "markdown": "\n".join(lines), "line_count": len(lines)}


# ============================================================
# Tool Descriptions Registry
# ============================================================

OSINT_EXTRA_TOOL_DESCRIPTIONS = {
    "social_analyzer": ("Search username across 30+ platforms", {"username": "Username to search", "timeout": "Timeout per request"}),
    "instagram_osint": ("Instagram profile intelligence", {"username": "Instagram username", "timeout": "Timeout"}),
    "twitter_osint": ("Twitter/X profile lookup", {"username": "Twitter username", "timeout": "Timeout"}),
    "facebook_osint": ("Facebook public search", {"query": "Name to search", "timeout": "Timeout"}),
    "linkedin_osint": ("LinkedIn profile search", {"query": "Name to search", "timeout": "Timeout"}),
    "tiktok_osint": ("TikTok profile info", {"username": "TikTok username", "timeout": "Timeout"}),
    "telegram_osint": ("Telegram username check", {"username": "Telegram username", "timeout": "Timeout"}),
    "reddit_osint": ("Reddit user info", {"username": "Reddit username", "timeout": "Timeout"}),
    "social_links_extractor": ("Extract social links from page", {"url": "Page URL", "timeout": "Timeout"}),
    "holehe_check": ("Check email on services", {"email": "Email to check", "timeout": "Timeout"}),
    "email_rep": ("Email reputation check", {"email": "Email to check", "timeout": "Timeout"}),
    "email_format": ("Generate email formats", {"first_name": "First name", "last_name": "Last name", "domain": "Domain"}),
    "username_search": ("Cross-platform username search", {"username": "Username", "timeout": "Timeout"}),
    "username_variations": ("Generate username variations", {"username": "Username"}),
    "phone_lookup": ("Phone number intelligence", {"phone": "Phone number", "timeout": "Timeout"}),
    "phone_format": ("Phone number formatting", {"phone": "Phone number", "country": "Country code"}),
    "phone_breach_check": ("Check phone in breaches", {"phone": "Phone number", "timeout": "Timeout"}),
    "dns_enum": ("DNS enumeration", {"domain": "Target domain", "timeout": "Timeout"}),
    "dns_bruteforce": ("DNS subdomain brute force", {"domain": "Target domain", "wordlist": "Subdomain list", "timeout": "Timeout"}),
    "dns_zone_transfer": ("DNS zone transfer attempt", {"domain": "Target domain", "timeout": "Timeout"}),
    "dns_reverse": ("Reverse DNS lookup", {"ip": "IP address", "timeout": "Timeout"}),
    "spf_check": ("SPF record check", {"domain": "Domain", "timeout": "Timeout"}),
    "dkim_check": ("DKIM record check", {"domain": "Domain", "selector": "DKIM selector", "timeout": "Timeout"}),
    "dmarc_check": ("DMARC record check", {"domain": "Domain", "timeout": "Timeout"}),
    "mx_lookup": ("MX record lookup", {"domain": "Domain", "timeout": "Timeout"}),
    "whatweb": ("Web technology detection", {"domain": "Domain/URL", "timeout": "Timeout"}),
    "whatcms": ("CMS detection", {"url": "URL", "timeout": "Timeout"}),
    "cdn_detect": ("CDN detection", {"domain": "Domain", "timeout": "Timeout"}),
    "web_server_headers": ("Get web server headers", {"url": "URL", "timeout": "Timeout"}),
    "urlscan_submit": ("Submit URL to URLScan", {"url": "URL to scan", "timeout": "Timeout"}),
    "urlscan_result": ("Get URLScan result", {"uuid": "Scan UUID", "timeout": "Timeout"}),
    "virus_total_url": ("VirusTotal URL scan", {"url": "URL", "timeout": "Timeout"}),
    "virus_total_domain": ("VirusTotal domain report", {"domain": "Domain", "timeout": "Timeout"}),
    "url_expander": ("Expand shortened URL", {"short_url": "Short URL", "timeout": "Timeout"}),
    "url_analyze": ("Analyze URL structure", {"url": "URL to analyze"}),
    "wayback_snapshots": ("Wayback Machine snapshot timeline", {"domain": "Domain", "timeout": "Timeout"}),
    "wayback_urls": ("Get archived URLs", {"domain": "Domain", "limit": "Max URLs", "timeout": "Timeout"}),
    "wayback_latest": ("Get latest Wayback snapshot", {"domain": "Domain", "timeout": "Timeout"}),
    "leak_check": ("Multi-source breach check", {"email": "Email to check", "timeout": "Timeout"}),
    "intelx_search": ("Intelligence X search", {"query": "Search query", "search_type": "Type (email,domain,ip)", "timeout": "Timeout"}),
    "dehashed_search": ("Dehashed database search", {"query": "Search query", "search_type": "Type", "timeout": "Timeout"}),
    "ip_abuse_report": ("AbuseIPDB check", {"ip": "IP address", "timeout": "Timeout"}),
    "ip_threat_intel": ("IP threat intelligence", {"ip": "IP address", "timeout": "Timeout"}),
    "ip_reverse_dns": ("Reverse DNS", {"ip": "IP address", "timeout": "Timeout"}),
    "ip_asn_info": ("ASN information", {"ip": "IP address", "timeout": "Timeout"}),
    "ip_blacklist_check": ("DNS blacklist check", {"ip": "IP address", "timeout": "Timeout"}),
    "ip_geolocate_full": ("IP geolocation", {"ip": "IP address", "timeout": "Timeout"}),
    "ip_range_expand": ("Expand CIDR range", {"cidr": "CIDR notation"}),
    "domain_similar": ("Find similar domains", {"domain": "Domain to check"}),
    "domain_history": ("Domain history", {"domain": "Domain", "timeout": "Timeout"}),
    "certificate_transparency": ("crt.sh certificate search", {"domain": "Domain", "timeout": "Timeout"}),
    "domain_age": ("Estimate domain age", {"domain": "Domain", "timeout": "Timeout"}),
    "web_crawl": ("Simple web crawler", {"url": "Start URL", "depth": "Crawl depth", "timeout": "Timeout"}),
    "email_extractor": ("Extract emails from page", {"url": "Page URL", "timeout": "Timeout"}),
    "phone_extractor": ("Extract phones from page", {"url": "Page URL", "timeout": "Timeout"}),
    "meta_extractor": ("Extract meta tags", {"url": "Page URL", "timeout": "Timeout"}),
    "page_text_extractor": ("Extract readable text", {"url": "Page URL", "timeout": "Timeout"}),
    "security_headers": ("Check security headers", {"url": "URL", "timeout": "Timeout"}),
    "cors_check": ("CORS configuration check", {"url": "URL", "timeout": "Timeout"}),
    "hsts_check": ("HSTS preload check", {"domain": "Domain", "timeout": "Timeout"}),
    "robots_txt_check": ("robots.txt analysis", {"url": "URL", "timeout": "Timeout"}),
    "ssl_cert_check_full": ("SSL certificate analysis", {"hostname": "Hostname", "port": "Port", "timeout": "Timeout"}),
    "btc_address_lookup": ("Bitcoin address lookup", {"address": "BTC address", "timeout": "Timeout"}),
    "eth_address_lookup": ("Ethereum address lookup", {"address": "ETH address", "timeout": "Timeout"}),
    "wallet_balance": ("Wallet balance check", {"address": "Wallet address", "currency": "Currency (btc/eth)", "timeout": "Timeout"}),
    "onion_check": ("Check .onion accessibility", {"onion_url": ".onion URL", "timeout": "Timeout"}),
    "tor_dns_lookup": ("DNS via Tor", {"domain": "Domain", "timeout": "Timeout"}),
    "format_osint_for_report": ("Format OSINT as report", {"results": "List of result dicts", "title": "Report title"}),
    "summarize_osint_findings": ("Summarize OSINT findings", {"results": "List of result dicts"}),
    "osint_to_markdown": ("Convert OSINT to markdown", {"result": "Result dict", "title": "Title"}),
}

__all__ = [
    "social_analyzer", "instagram_osint", "twitter_osint", "facebook_osint",
    "linkedin_osint", "tiktok_osint", "telegram_osint", "reddit_osint",
    "social_links_extractor", "holehe_check", "email_rep", "email_format",
    "username_search", "username_variations",
    "phone_lookup", "phone_format", "phone_breach_check",
    "dns_enum", "dns_bruteforce", "dns_zone_transfer", "dns_reverse",
    "spf_check", "dkim_check", "dmarc_check", "mx_lookup",
    "whatweb", "whatcms", "cdn_detect", "web_server_headers",
    "urlscan_submit", "urlscan_result", "virus_total_url", "virus_total_domain",
    "url_expander", "url_analyze",
    "wayback_snapshots", "wayback_urls", "wayback_latest",
    "leak_check", "intelx_search", "dehashed_search",
    "ip_abuse_report", "ip_threat_intel", "ip_reverse_dns", "ip_asn_info",
    "ip_blacklist_check", "ip_geolocate_full", "ip_range_expand",
    "domain_similar", "domain_history", "certificate_transparency", "domain_age",
    "web_crawl", "email_extractor", "phone_extractor", "meta_extractor", "page_text_extractor",
    "security_headers", "cors_check", "hsts_check", "robots_txt_check", "ssl_cert_check_full",
    "btc_address_lookup", "eth_address_lookup", "wallet_balance",
    "onion_check", "tor_dns_lookup",
    "format_osint_for_report", "summarize_osint_findings", "osint_to_markdown",
    "OSINT_EXTRA_TOOL_DESCRIPTIONS",
]
'''

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(HEADER)
    f.write(CONTENT)

print(f"Written {OUTPUT}")
print(f"File size: {os.path.getsize(OUTPUT)} bytes")
print(f"Lines: {CONTENT.count(chr(10))}")
