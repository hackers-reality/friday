"""FRIDAY Settings Dashboard — API key management, Google OAuth, service status, and system configuration.

This module provides a full-featured web settings panel for FRIDAY with:
- API key management (31+ keys with real brand logos, verify, save, mask)
- Google OAuth integration (16+ Google services with scopes)
- Real-time .env updates without restarting FRIDAY
- Search, filter (All/Connected/Not Configured)
- Side panel navigation with responsive layout
- Toast notifications, modal dialogs, animated glassmorphic UI
- Auto-polling for live status updates every 15 seconds

All API keys, pricing tiers, service categories, OAuth scopes, and brand
logos are documented inline with comprehensive metadata for tooltip display.
"""

from __future__ import annotations

import json
import os
import re
import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
CONFIG_CHANGE_FILE = Path(__file__).resolve().parent.parent / ".config_updated"


def _notify_friday(event_type: str, details: str = ""):
    """Write a change event so Friday can pick it up and react."""
    try:
        data = {"event": event_type, "details": details, "ts": time.time(), "iso": datetime.now(timezone.utc).isoformat()}
        CONFIG_CHANGE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass

# ── Inline SVG Data URIs for brands not available on SimpleIcons CDN ───────
# These are 40x40 rounded-square icons with the brand letter on brand color.
# Used as fallback when the simpleicons.org CDN is unreachable or the brand
# is not available on simpleicons.

BRAND_SVG = {
    "shodan": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='8' fill='%2300e5ff'/%3E%3Ctext x='20' y='28' font-size='22' font-family='Arial,sans-serif' font-weight='bold' fill='%23080c14' text-anchor='middle'%3ES%3C/text%3E%3C/svg%3E",
    "censys": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='8' fill='%2300a8ff'/%3E%3Ctext x='20' y='28' font-size='22' font-family='Arial,sans-serif' font-weight='bold' fill='%23080c14' text-anchor='middle'%3EC%3C/text%3E%3C/svg%3E",
    "hunter": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='8' fill='%23ff6b35'/%3E%3Ctext x='20' y='28' font-size='22' font-family='Arial,sans-serif' font-weight='bold' fill='%23080c14' text-anchor='middle'%3EH%3C/text%3E%3C/svg%3E",
    "clearbit": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='8' fill='%234a90d9'/%3E%3Ctext x='20' y='28' font-size='18' font-family='Arial,sans-serif' font-weight='bold' fill='%23ffffff' text-anchor='middle'%3ECb%3C/text%3E%3C/svg%3E",
    "dehashed": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='8' fill='%23ff0000'/%3E%3Ctext x='20' y='28' font-size='22' font-family='Arial,sans-serif' font-weight='bold' fill='%23ffffff' text-anchor='middle'%3ED%3C/text%3E%3C/svg%3E",
    "intelx": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='8' fill='%23ff6600'/%3E%3Ctext x='20' y='28' font-size='22' font-family='Arial,sans-serif' font-weight='bold' fill='%23080c14' text-anchor='middle'%3EX%3C/text%3E%3C/svg%3E",
    "abuseipdb": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='8' fill='%23ff4444'/%3E%3Ctext x='20' y='28' font-size='22' font-family='Arial,sans-serif' font-weight='bold' fill='%23ffffff' text-anchor='middle'%3EA%3C/text%3E%3C/svg%3E",
    "ipinfo": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='8' fill='%2300cca8'/%3E%3Ctext x='20' y='28' font-size='22' font-family='Arial,sans-serif' font-weight='bold' fill='%23080c14' text-anchor='middle'%3Ei%3C/text%3E%3C/svg%3E",
    "urlscan": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='8' fill='%2300aaff'/%3E%3Ctext x='20' y='28' font-size='22' font-family='Arial,sans-serif' font-weight='bold' fill='%23080c14' text-anchor='middle'%3EU%3C/text%3E%3C/svg%3E",
    "groq": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='8' fill='%23f97316'/%3E%3Ctext x='20' y='28' font-size='22' font-family='Arial,sans-serif' font-weight='bold' fill='%23080c14' text-anchor='middle'%3EG%3C/text%3E%3C/svg%3E",
    "picovoice": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='8' fill='%236c5ce7'/%3E%3Ctext x='20' y='28' font-size='22' font-family='Arial,sans-serif' font-weight='bold' fill='%23ffffff' text-anchor='middle'%3EP%3C/text%3E%3C/svg%3E",
    "sarvam": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='8' fill='%23ff6b9d'/%3E%3Ctext x='20' y='28' font-size='22' font-family='Arial,sans-serif' font-weight='bold' fill='%23080c14' text-anchor='middle'%3ES%3C/text%3E%3C/svg%3E",
    "builtwith": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='8' fill='%232c3e50'/%3E%3Ctext x='20' y='28' font-size='18' font-family='Arial,sans-serif' font-weight='bold' fill='%23ffffff' text-anchor='middle'%3EBw%3C/text%3E%3C/svg%3E",
    "securitytrails": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='8' fill='%2300b4d8'/%3E%3Ctext x='20' y='28' font-size='18' font-family='Arial,sans-serif' font-weight='bold' fill='%23080c14' text-anchor='middle'%3ESt%3C/text%3E%3C/svg%3E",
    "whatcms": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='8' fill='%2316a085'/%3E%3Ctext x='20' y='28' font-size='18' font-family='Arial,sans-serif' font-weight='bold' fill='%23ffffff' text-anchor='middle'%3EWc%3C/text%3E%3C/svg%3E",
    "fullcontact": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='8' fill='%23e91e63'/%3E%3Ctext x='20' y='28' font-size='18' font-family='Arial,sans-serif' font-weight='bold' fill='%23ffffff' text-anchor='middle'%3EFc%3C/text%3E%3C/svg%3E",
    "alexa": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='8' fill='%2300caff'/%3E%3Ctext x='20' y='28' font-size='22' font-family='Arial,sans-serif' font-weight='bold' fill='%23080c14' text-anchor='middle'%3EA%3C/text%3E%3C/svg%3E",
    "contacts": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='8' fill='%2334a853'/%3E%3Ctext x='20' y='28' font-size='22' font-family='Arial,sans-serif' font-weight='bold' fill='%23ffffff' text-anchor='middle'%3E%3C/text%3E%3C/svg%3E",
    "people": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='8' fill='%234285f4'/%3E%3Ctext x='20' y='28' font-size='18' font-family='Arial,sans-serif' font-weight='bold' fill='%23ffffff' text-anchor='middle'%3EPp%3C/text%3E%3C/svg%3E",
}

SIMPLEICONS = "https://cdn.simpleicons.org"
FAVICON = "https://www.google.com/s2/favicons?domain={domain}&sz=40&scale_factor=1"

API_LOGO = {
    "GOOGLE_API_KEY": {"src": f"{SIMPLEICONS}/google/4285F4", "type": "simpleicons", "fallback": "google", "domain": "google.com"},
    "GOOGLE_CLIENT_ID": {"src": f"{SIMPLEICONS}/google/4285F4", "type": "simpleicons", "fallback": "google", "domain": "google.com"},
    "GOOGLE_CLIENT_SECRET": {"src": f"{SIMPLEICONS}/google/4285F4", "type": "simpleicons", "fallback": "google", "domain": "google.com"},
    "NVIDIA_VISION_API_KEY": {"src": f"{SIMPLEICONS}/nvidia/76B900", "type": "simpleicons", "fallback": "nvidia", "domain": "nvidia.com"},
    "NVIDIA_NIM_API_KEY": {"src": f"{SIMPLEICONS}/nvidia/76B900", "type": "simpleicons", "fallback": "nvidia", "domain": "nvidia.com"},
    "OPENCODE_ZEN_API_KEY": {"src": f"{SIMPLEICONS}/opencode/00e5ff", "type": "simpleicons", "fallback": "opencode", "domain": "opencode.ai"},
    "GROQ_API_KEY": {"src": f"{FAVICON.format(domain='groq.com')}", "type": "favicon", "fallback": "groq", "domain": "groq.com"},
    "SARVAM_API_KEY": {"src": f"{FAVICON.format(domain='sarvam.ai')}", "type": "favicon", "fallback": "sarvam", "domain": "sarvam.ai"},
    "PICOVOICE_ACCESS_KEY": {"src": f"{FAVICON.format(domain='picovoice.ai')}", "type": "favicon", "fallback": "picovoice", "domain": "picovoice.ai"},
    "SHODAN_API_KEY": {"src": f"{FAVICON.format(domain='shodan.io')}", "type": "favicon", "fallback": "shodan", "domain": "shodan.io"},
    "CENSYS_API_ID": {"src": f"{FAVICON.format(domain='censys.io')}", "type": "favicon", "fallback": "censys", "domain": "censys.io"},
    "CENSYS_API_SECRET": {"src": f"{FAVICON.format(domain='censys.io')}", "type": "favicon", "fallback": "censys", "domain": "censys.io"},
    "VIRUSTOTAL_API_KEY": {"src": f"{SIMPLEICONS}/virustotal/394EFF", "type": "simpleicons", "fallback": "virustotal", "domain": "virustotal.com"},
    "HUNTER_API_KEY": {"src": f"{FAVICON.format(domain='hunter.io')}", "type": "favicon", "fallback": "hunter", "domain": "hunter.io"},
    "CLEARBIT_API_KEY": {"src": f"{FAVICON.format(domain='clearbit.com')}", "type": "favicon", "fallback": "clearbit", "domain": "clearbit.com"},
    "HIBP_API_KEY": {"src": f"{SIMPLEICONS}/haveibeenpwned/00e5ff", "type": "simpleicons", "fallback": "haveibeenpwned", "domain": "haveibeenpwned.com"},
    "DEHASHED_API_KEY": {"src": f"{FAVICON.format(domain='dehashed.com')}", "type": "favicon", "fallback": "dehashed", "domain": "dehashed.com"},
    "INTELX_API_KEY": {"src": f"{FAVICON.format(domain='intelx.io')}", "type": "favicon", "fallback": "intelx", "domain": "intelx.io"},
    "ABUSEIPDB_API_KEY": {"src": f"{FAVICON.format(domain='abuseipdb.com')}", "type": "favicon", "fallback": "abuseipdb", "domain": "abuseipdb.com"},
    "IPINFO_API_KEY": {"src": f"{FAVICON.format(domain='ipinfo.io')}", "type": "favicon", "fallback": "ipinfo", "domain": "ipinfo.io"},
    "URLSCAN_API_KEY": {"src": f"{FAVICON.format(domain='urlscan.io')}", "type": "favicon", "fallback": "urlscan", "domain": "urlscan.io"},
    "BUILTWITH_API_KEY": {"src": f"{FAVICON.format(domain='builtwith.com')}", "type": "favicon", "fallback": "builtwith", "domain": "builtwith.com"},
    "SECURITYTRAILS_API_KEY": {"src": f"{FAVICON.format(domain='securitytrails.com')}", "type": "favicon", "fallback": "securitytrails", "domain": "securitytrails.com"},
    "WHATCMS_API_KEY": {"src": f"{FAVICON.format(domain='whatcms.org')}", "type": "favicon", "fallback": "whatcms", "domain": "whatcms.org"},
    "FULLCONTACT_API_KEY": {"src": f"{FAVICON.format(domain='fullcontact.com')}", "type": "favicon", "fallback": "fullcontact", "domain": "fullcontact.com"},
    "GITHUB_CLIENT_ID": {"src": f"{SIMPLEICONS}/github/FFFFFF", "type": "simpleicons", "fallback": "github", "domain": "github.com"},
    "GITHUB_CLIENT_SECRET": {"src": f"{SIMPLEICONS}/github/FFFFFF", "type": "simpleicons", "fallback": "github", "domain": "github.com"},
    "OPENCAGE_API_KEY": {"src": f"{SIMPLEICONS}/opencage/00e5ff", "type": "simpleicons", "fallback": "opencage", "domain": "opencagedata.com"},
    "SPOTIFY_CLIENT_ID": {"src": f"{SIMPLEICONS}/spotify/1DB954", "type": "simpleicons", "fallback": "spotify", "domain": "spotify.com"},
    "SPOTIFY_CLIENT_SECRET": {"src": f"{SIMPLEICONS}/spotify/1DB954", "type": "simpleicons", "fallback": "spotify", "domain": "spotify.com"},
    "GITLAB_TOKEN": {"src": f"{SIMPLEICONS}/gitlab/E24329", "type": "simpleicons", "fallback": "gitlab", "domain": "gitlab.com"},
    "TELEGRAM_API_HASH": {"src": f"{FAVICON.format(domain='telegram.org')}", "type": "favicon", "fallback": "telegram", "domain": "telegram.org"},
    "REDDIT_CLIENT_ID": {"src": f"{SIMPLEICONS}/reddit/FF4500", "type": "simpleicons", "fallback": "reddit", "domain": "reddit.com"},
    "REDDIT_CLIENT_SECRET": {"src": f"{SIMPLEICONS}/reddit/FF4500", "type": "simpleicons", "fallback": "reddit", "domain": "reddit.com"},
    "TWITTER_BEARER_TOKEN": {"src": f"{SIMPLEICONS}/x/FFFFFF", "type": "simpleicons", "fallback": "x", "domain": "twitter.com"},
    "TWITTER_API_KEY": {"src": f"{SIMPLEICONS}/x/FFFFFF", "type": "simpleicons", "fallback": "x", "domain": "twitter.com"},
    "TWITTER_API_SECRET": {"src": f"{SIMPLEICONS}/x/FFFFFF", "type": "simpleicons", "fallback": "x", "domain": "twitter.com"},
    "INSTAGRAM_PASS": {"src": f"{SIMPLEICONS}/instagram/E4405F", "type": "simpleicons", "fallback": "instagram", "domain": "instagram.com"},
    "OTX_API_KEY": {"src": f"{FAVICON.format(domain='alienvault.com')}", "type": "favicon", "fallback": "alienvault", "domain": "alienvault.com"},
    "LEAKCHECK_API_KEY": {"src": f"{FAVICON.format(domain='leakcheck.io')}", "type": "favicon", "fallback": "leakcheck", "domain": "leakcheck.io"},
    "FLICKR_API_KEY": {"src": f"{FAVICON.format(domain='flickr.com')}", "type": "favicon", "fallback": "flickr", "domain": "flickr.com"},
    "DISCOGS_TOKEN": {"src": f"{FAVICON.format(domain='discogs.com')}", "type": "favicon", "fallback": "discogs", "domain": "discogs.com"},
    "DISCORD_BOT_TOKEN": {"src": f"{SIMPLEICONS}/discord/5865F2", "type": "simpleicons", "fallback": "discord", "domain": "discord.com"},
    "TELEGRAM_API_ID": {"src": f"{FAVICON.format(domain='telegram.org')}", "type": "favicon", "fallback": "telegram", "domain": "telegram.org"},
    "INSTAGRAM_USER": {"src": f"{SIMPLEICONS}/instagram/E4405F", "type": "simpleicons", "fallback": "instagram", "domain": "instagram.com"},
}

GOOGLE_LOGO = {
    "gmail": f"{SIMPLEICONS}/gmail/EA4335",
    "calendar": f"{SIMPLEICONS}/googlecalendar/4285F4",
    "drive": f"{SIMPLEICONS}/googledrive/FBBC04",
    "youtube": f"{SIMPLEICONS}/youtube/FF0000",
    "photos": f"{SIMPLEICONS}/googlephotos/FF6F00",
    "docs": f"{SIMPLEICONS}/googledocs/4285F4",
    "sheets": f"{SIMPLEICONS}/googlesheets/0F9D58",
    "slides": f"{SIMPLEICONS}/googleslides/FBBC04",
    "tasks": f"{SIMPLEICONS}/googletasks/4285F4",
    "contacts": f"{SIMPLEICONS}/googlecontacts/34A853",
    "people": f"{SIMPLEICONS}/people/4285F4",
    "cloud": f"{SIMPLEICONS}/googlecloud/4285F4",
    "maps": f"{SIMPLEICONS}/googlemaps/34A853",
    "classroom": f"{SIMPLEICONS}/googleclassroom/1A73E8",
    "analytics": f"{SIMPLEICONS}/googleanalytics/E37400",
    "ads": f"{SIMPLEICONS}/googleads/4285F4",
    "forms": f"{SIMPLEICONS}/googleforms/7248B9",
    "firebase": f"{SIMPLEICONS}/firebase/FFCA28",
    "books": f"{SIMPLEICONS}/googlebooks/4285F4",
    "searchconsole": f"{SIMPLEICONS}/googlesearchconsole/4285F4",
    "translation": f"{SIMPLEICONS}/googletranslate/4285F4",
    "naturallanguage": f"{SIMPLEICONS}/googlenatural language/4285F4",
    "bigquery": f"{SIMPLEICONS}/googlebigquery/4285F4",
    "cloudstorage": f"{SIMPLEICONS}/googlecloudstorage/4285F4",
}

CATEGORY_ICON_MAP = {
    "Gmail": "gmail",
    "Calendar": "calendar",
    "Drive": "drive",
    "Sheets": "sheets",
    "Docs": "docs",
    "Slides": "slides",
    "YouTube": "youtube",
    "People": "people",
    "Tasks": "tasks",
    "Forms": "forms",
    "Photos": "photos",
    "Firebase": "firebase",
    "Books": "books",
    "Analytics": "analytics",
    "Search Console": "searchconsole",
    "Translation": "translation",
    "Natural Language": "naturallanguage",
    "BigQuery": "bigquery",
    "Cloud Storage": "cloudstorage",
    "Cloud Platform": "cloud",
    "Classroom": "classroom",
    "Gmail Readonly": "gmail",
    "Drive Readonly": "drive",
}

# ── API Key Metadata ──────────────────────────────────────────────────────
# Each entry contains: name, description (detailed), pricing (all tiers),
# url (to signup/get key), docs (API documentation), category,
# test_url (endpoint to verify the key), test_headers (request headers for test).

API_KEY_META = {
    "GOOGLE_API_KEY": {
        "name": "Gemini API Key",
        "category": "AI",
        "description": "Google's Gemini foundation model API key. This is the primary brain of FRIDAY — it powers all core intelligence including multimodal reasoning (text + image + audio), vision understanding (screen analysis, object detection), thinking capabilities (deep reasoning before responses), and live audio streaming (voice conversations). Without this key, FRIDAY cannot operate in its primary mode and must fall back to NVIDIA NIM or OpenCode models. The key is obtained from Google AI Studio and is associated with your Google Cloud project for billing and quota management.",
        "pricing": "Free Tier: 60 requests per minute with rate limiting, 1,500 requests per day for Gemini 1.5 models. Gemini 2.0 Flash free tier includes 1,000 requests per day. Paid: Pay-as-you-go at $0.15 per 1 million input tokens for Gemini 2.0 Flash, $0.50 per 1M output tokens. Gemini 2.5 Pro at $1.25 per 1M input tokens. The free tier is sufficient for personal daily use.",
        "url": "https://aistudio.google.com/app/apikey",
        "docs": "https://ai.google.dev/gemini-api/docs",
        "test_url": "https://generativelanguage.googleapis.com/v1beta/models?key={key}",
        "test_headers": None,
        "howto": "1. Go to aistudio.google.com 2. Click 'Get API Key' 3. Create or select a Google Cloud project 4. Enable the Generative Language API 5. Copy the generated key and paste it into FRIDAY settings. No credit card required for free tier.",
        "ratelimit": "60 requests/minute (free tier), unlimited with paid tier",
        "related": "GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GEMINI_MODEL, GEMINI_LIVE_MODEL",
    },
    "GOOGLE_CLIENT_ID": {
        "name": "Google OAuth Client ID",
        "category": "Google",
        "description": "OAuth 2.0 client identifier registered in Google Cloud Console. This is required alongside GOOGLE_CLIENT_SECRET to authorize FRIDAY to access your personal Google services including Gmail (read emails), Calendar (manage events), Drive (access files), YouTube (search videos), Photos (view albums), Docs/Sheets/Slides (edit documents), and many more. The OAuth flow gives FRIDAY delegated access to your Google data without sharing your password.",
        "pricing": "Free — requires a Google Cloud Project with OAuth consent screen configured. The consent screen needs at least an 'External' user type which is free to set up. No credit card required for OAuth credentials. You only need to configure the consent screen with your app name and support email.",
        "url": "https://console.cloud.google.com/apis/credentials",
        "docs": "https://developers.google.com/identity/protocols/oauth2",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Go to console.cloud.google.com 2. Create a new project or select existing 3. Navigate to APIs & Services > Credentials 4. Click 'Create Credentials' > 'OAuth client ID' 5. Configure consent screen (External, fill required fields) 6. Select 'Desktop app' as application type 7. Copy the Client ID and Client Secret 8. Add http://127.0.0.1:7071/settings/google/callback as an authorized redirect URI",
        "ratelimit": "No rate limit for OAuth itself. API rate limits apply per-service.",
        "related": "GOOGLE_CLIENT_SECRET, GOOGLE_API_KEY",
    },
    "GOOGLE_CLIENT_SECRET": {
        "name": "Google OAuth Client Secret",
        "category": "Google",
        "description": "Confidential secret paired with GOOGLE_CLIENT_ID for OAuth 2.0 authentication. This secret must be kept private — never expose it in client-side code, never commit it to version control, and never share it with third parties. If you suspect the secret has been compromised, immediately rotate it from the Google Cloud Console.",
        "pricing": "Free — generated from Google Cloud Console alongside the Client ID. You can create multiple client IDs and secrets for different applications. Rotate this secret periodically for security (recommended: every 90 days).",
        "url": "https://console.cloud.google.com/apis/credentials",
        "docs": "https://developers.google.com/identity/protocols/oauth2",
        "test_url": None,
        "test_headers": None,
        "howto": "Generated automatically when you create an OAuth client ID in Google Cloud Console. You can view it anytime from APIs & Services > Credentials. Click the pencil icon on your OAuth 2.0 Client ID to see the secret.",
        "ratelimit": "No rate limit.",
        "related": "GOOGLE_CLIENT_ID",
    },
    "NVIDIA_VISION_API_KEY": {
        "name": "NVIDIA NIM Vision Key",
        "category": "AI",
        "description": "NVIDIA NIM API key for vision AI models. FRIDAY uses this key to access NVIDIA's cloud-hosted vision models including Microsoft Florence-2 Large (general vision), and other computer vision models for real-time screen analysis, object detection, scene understanding, OCR, and camera feed interpretation. When you ask FRIDAY 'what do you see on my screen', this key handles the vision inference. The key is the same as your NVIDIA NIM API key — both vision and LLM use the same NVIDIA API key.",
        "pricing": "Free Tier: NVIDIA offers 1,000+ free API calls across all NIM models as part of their 'Free NIM API' program. Rate limited to 10 requests per minute on free tier. Paid: Pay-per-token pricing for production workloads — approximately $0.10 per 1K tokens for vision models. No credit card required to start.",
        "url": "https://build.nvidia.com",
        "docs": "https://build.nvidia.com/docs",
        "test_url": "https://integrate.api.nvidia.com/v1/models",
        "test_headers": {"Authorization": "Bearer {key}"},
        "howto": "1. Go to build.nvidia.com 2. Sign up for a free account 3. Click on any NIM model (e.g., 'Florence-2 Large') 4. Click 'Get API Key' 5. Copy the generated key. The same API key works for all NVIDIA NIM models — vision, LLM, and embedding.",
        "ratelimit": "10 requests/minute (free tier). Higher limits available with NVIDIA Enterprise account.",
        "related": "NVIDIA_NIM_API_KEY, NVIDIA_NIM_VISION_MODEL",
    },
    "NVIDIA_NIM_API_KEY": {
        "name": "NVIDIA NIM LLM Key",
        "category": "AI",
        "description": "NVIDIA NIM API key for large language models hosted on NVIDIA's cloud infrastructure. FRIDAY uses this key to access models like DeepSeek V4 Flash/Pro, Meta Llama 3.3 70B, Kimi K2.5, MiniMax M2.7, and more. These models are used for deep research tasks (Veronica agent), web browsing analysis, code generation, and as fallback when Gemini is unavailable or rate-limited. The NIM API provides OpenAI-compatible endpoints.",
        "pricing": "Free Tier: 1,000+ free API calls included. Rate limited to 10 requests per minute. Paid: Pay-as-you-go pricing varies by model — approximately $0.50-$2.00 per 1M tokens for most models. DeepSeek V4 Flash is the most cost-effective at ~$0.25 per 1M tokens.",
        "url": "https://build.nvidia.com",
        "docs": "https://build.nvidia.com/docs",
        "test_url": "https://integrate.api.nvidia.com/v1/models",
        "test_headers": {"Authorization": "Bearer {key}"},
        "howto": "1. Go to build.nvidia.com 2. Create a free account 3. Navigate to 'API' section 4. Generate an API key 5. Copy the key. The NVIDIA NIM API key is the same for all NIM services — vision, language, and embeddings.",
        "ratelimit": "10 requests/minute (free tier). 2,000 requests/minute (Enterprise).",
        "related": "NVIDIA_VISION_API_KEY, NVIDIA_NIM_MODEL, NIM_API_BASE",
    },
    "OPENCODE_ZEN_API_KEY": {
        "name": "OpenCode Zen API Key",
        "category": "AI",
        "description": "API key for OpenCode's Zen multi-agent orchestration platform. This enables FRIDAY to spawn and coordinate multiple AI sub-agents including Veronica (deep research), Forge (software engineering), Atlas (navigation and planning), Ghost (OSINT operations), and JARVIS (system administration). Each sub-agent can work on complex tasks in parallel, sharing context and results through the Zen orchestration layer.",
        "pricing": "Free credits included with every OpenCode account (typically 10,000 credits). Usage-based pricing after free credits: approximately $0.50 per 1K agent calls. The Zen API provides access to multiple LLM models (big-pickle, mimo-v2.5, etc.) through a single unified endpoint.",
        "url": "https://opencode.ai",
        "docs": "https://opencode.ai/docs",
        "test_url": "https://opencode.ai/zen/v1/models",
        "test_headers": {"Authorization": "Bearer {key}"},
        "howto": "1. Go to opencode.ai 2. Create an account 3. Navigate to Settings > API Keys 4. Generate a new Zen API key 5. Copy the key. You can also set OPENCODE_ZEN_MODEL to choose which model to use (default: big-pickle).",
        "ratelimit": "60 requests/minute on free tier. Higher limits with paid plans.",
        "related": "OPENCODE_ZEN_MODEL, ZEN_API_BASE",
    },
    "GROQ_API_KEY": {
        "name": "Groq API Key",
        "category": "Voice",
        "description": "Groq LPU (Language Processing Unit) API key for ultra-fast inference. FRIDAY primarily uses Groq for Speech-to-Text transcription via Whisper large-v3 running on Groq's custom hardware. Groq's LPU architecture delivers sub-500ms transcription times for real-time voice commands. Groq also supports LLM inference (Llama 3, Mixtral) which FRIDAY can use for rapid text processing tasks.",
        "pricing": "Free Tier: 1,440 requests per day, 7 requests/second rate limit, with Whisper (STT) and LLM inference included. Paid: $0.10 per 1K requests for Whisper transcription. Groq is currently one of the most generous free tiers available.",
        "url": "https://console.groq.com/keys",
        "docs": "https://console.groq.com/docs",
        "test_url": "https://api.groq.com/openai/v1/models",
        "test_headers": {"Authorization": "Bearer {key}"},
        "howto": "1. Go to console.groq.com 2. Sign up with Google or GitHub 3. Navigate to API Keys 4. Click 'Create API Key' 5. Copy the key starting with 'gsk_' 6. Paste it into FRIDAY settings.",
        "ratelimit": "1,440 requests/day (free), 7 requests/second. Paid: 14,400 requests/day.",
        "related": "None",
    },
    "SARVAM_API_KEY": {
        "name": "Sarvam AI TTS Key",
        "category": "Voice",
        "description": "Sarvam AI Text-to-Speech API key for multilingual voice synthesis with a focus on Indian languages. FRIDAY uses Sarvam for high-quality Hindi, Tamil, Telugu, Bengali, Marathi, and other Indian language voice output. Supports multiple voices (male, female) and speaking styles with natural rhythm and intonation. Essential for serving users who prefer voice interaction in Indian regional languages.",
        "pricing": "Free Tier: 1,000 API calls per month, up to 100 characters per call. Paid: Starter at $10/month for 10,000 calls. Growth at $50/month for 100,000 calls. Enterprise: Custom pricing for unlimited calls and custom voice models.",
        "url": "https://dashboard.sarvam.ai",
        "docs": "https://docs.sarvam.ai",
        "test_url": "https://api.sarvam.ai/v1/tts",
        "test_headers": {"api-key": "{key}"},
        "howto": "1. Go to dashboard.sarvam.ai 2. Sign up for an account 3. Navigate to API Keys section 4. Generate a new API key 5. Copy the key (starts with 'sk_')",
        "ratelimit": "10 requests/minute (free tier). 100 requests/minute (paid).",
        "related": "None",
    },
    "PICOVOICE_ACCESS_KEY": {
        "name": "Picovoice Access Key",
        "category": "Voice",
        "description": "Picovoice access key for the Porcupine wake word engine. Enables hands-free 'Hey FRIDAY' activation without continuously recording audio to the cloud. The wake word detection runs entirely on-device using Picovoice's embedded AI engine, ensuring privacy and low latency. Porcupine supports multiple wake words and custom wake word training.",
        "pricing": "Free Tier: Porcupine wake word engine is free for unlimited use on-device. Picovoice Console access is free for 1,000 requests per month (for speech-to-intent features). Paid: Standard plan at $50/month for 10,000 requests. Enterprise: Custom pricing.",
        "url": "https://console.picovoice.ai",
        "docs": "https://picovoice.ai/docs/",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Go to console.picovoice.ai 2. Create an account 3. Navigate to Access Keys 4. Create a new AccessKey 5. Copy the key (starts with 'OeDA...'). The Porcupine library uses this key to validate your license.",
        "ratelimit": "On-device wake word detection has no rate limit. Cloud features limited to 1,000 requests/month.",
        "related": "PORCUPINE_MODEL_PATH (config in live.py)",
    },
    "SHODAN_API_KEY": {
        "name": "Shodan API Key",
        "category": "OSINT",
        "description": "Shodan search engine API key for internet-connected device intelligence. Shodan scans the entire IPv4 address space and indexes service banners from devices including webcams, routers, servers, SCADA systems, and IoT devices. FRIDAY uses Shodan for IP geolocation (find where a server is located), port scanning (discover open ports and services), service banner grabbing (identify software versions), vulnerability lookup (CVEs associated with services), and discovering exposed industrial control systems.",
        "pricing": "Free Tier: 1 million query credits per month, limited to 100 results per page, 1 page per query (max 100 results per search). Paid: Developer at $49/month (unlimited results, no rate limiting, 1,000 results per search). Professional at $89/month (2,000 results/search). Enterprise at $999/month (custom limits, API access, historical data).",
        "url": "https://account.shodan.io/register",
        "docs": "https://developer.shodan.io",
        "test_url": "https://api.shodan.io/api-info?key={key}",
        "test_headers": None,
        "howto": "1. Go to account.shodan.io/register 2. Create an account 3. Verify email 4. Navigate to 'API Key' in your account settings 5. Copy the key. The free tier gives you 1M credits/month — enough for several hundred IP lookups.",
        "ratelimit": "Free: 1 query/second. Paid: Unlimited queries.",
        "related": "None",
    },
    "CENSYS_API_ID": {
        "name": "Censys API ID",
        "category": "OSINT",
        "description": "Censys API identifier for internet-wide scanning data and certificate transparency intelligence. Censys continuously scans the entire internet (all IPv4 addresses) and indexes SSL/TLS certificates, open ports, HTTP responses, and other service data. FRIDAY uses Censys for SSL/TLS certificate analysis (identify certificate issuers, expiration dates, and cipher suites), subdomain enumeration (discover subdomains from certificate transparency logs), host discovery (find all services running on an IP), and attack surface management.",
        "pricing": "Free Tier: 250 queries per month with basic search filters and limited results. Paid: Community at $74/month for 10,000 queries, advanced search, and full API access. Professional at $199/month for 50,000 queries. Research: Free for academic researchers with .edu email.",
        "url": "https://search.censys.io/register",
        "docs": "https://docs.censys.io",
        "test_url": "https://search.censys.io/api/v1/account",
        "test_headers": None,
        "howto": "1. Go to search.censys.io/register 2. Create an account 3. Navigate to Account > API 4. Generate API credentials (API ID + Secret) 5. Copy both into FRIDAY settings.",
        "ratelimit": "Free: 1 query/second. Paid: 10 queries/second.",
        "related": "CENSYS_API_SECRET",
    },
    "CENSYS_API_SECRET": {
        "name": "Censys API Secret",
        "category": "OSINT",
        "description": "Secret key paired with CENSYS_API_ID for authenticating with the Censys API. Both the API ID and Secret are required together. The secret acts as the password to your Censys account and should be kept confidential. Never commit this to version control or expose it in client-side code.",
        "pricing": "Free with Censys account — generated from the Account > API settings page after signup. You can regenerate the secret at any time, which will invalidate the previous secret.",
        "url": "https://search.censys.io/account/api",
        "docs": "https://docs.censys.io",
        "test_url": None,
        "test_headers": None,
        "howto": "Generated alongside CENSYS_API_ID from search.censys.io/account/api. Copy both values immediately as the secret is only shown once.",
        "ratelimit": "Same as CENSYS_API_ID.",
        "related": "CENSYS_API_ID",
    },
    "VIRUSTOTAL_API_KEY": {
        "name": "VirusTotal API Key",
        "category": "OSINT",
        "description": "VirusTotal API key for comprehensive file and URL threat intelligence. VirusTotal aggregates detection results from 70+ antivirus engines (including Kaspersky, McAfee, Symantec, Microsoft Defender) and sandbox detonation services. FRIDAY uses VirusTotal to scan suspicious files (upload or hash lookup), analyze URLs (check if a website is malicious), investigate IP addresses (find associated malware domains), and perform domain reputation checks. Each scan provides detailed reports including detection ratios, community comments, and behavior analysis.",
        "pricing": "Free Tier: 500 requests per day, 4 requests per minute, 1 community API request per minute. Search is limited to 2,500 matches. Paid: VirusTotal Intelligence at $100/month for 100,000 requests per day, advanced search filters, file downloads, and behavioral sandbox reports. Enterprise at $1,200/month for 1M+ requests.",
        "url": "https://www.virustotal.com/gui/join-us",
        "docs": "https://developers.virustotal.com",
        "test_url": "https://www.virustotal.com/api/v3/ip_addresses/8.8.8.8",
        "test_headers": {"x-apikey": "{key}"},
        "howto": "1. Go to virustotal.com 2. Sign up for a free account 3. Navigate to your account settings 4. Find the API Key section 5. Copy the key. The free tier is sufficient for casual threat intelligence work.",
        "ratelimit": "Free: 4 requests/minute, 500/day. Paid: 100 requests/minute.",
        "related": "None",
    },
    "HUNTER_API_KEY": {
        "name": "Hunter.io API Key",
        "category": "OSINT",
        "description": "Hunter.io API key for email address discovery and verification. Given a domain name, Hunter finds publicly associated email addresses from web sources. FRIDAY uses Hunter for social engineering assessments (find employees of a company), contact discovery (get email patterns for a domain), email verification (check if an email is deliverable), and lead generation. Each search returns email addresses with confidence scores, sources, and position titles.",
        "pricing": "Free Tier: 25 searches per month, 50 verifications per month, 25 automatic enrichments. Paid: Starter at $49/month (500 searches, 1,000 verifications), Growth at $149/month (5,000 searches, 10,000 verifications), Pro at $499/month (50,000 searches, 100,000 verifications).",
        "url": "https://hunter.io/users/sign_up",
        "docs": "https://hunter.io/api-documentation",
        "test_url": "https://api.hunter.io/v2/account?api_key={key}",
        "test_headers": None,
        "howto": "1. Go to hunter.io 2. Sign up for a free account 3. Verify your email 4. Go to Dashboard > API 5. Copy your API key. The free tier gives 25 searches — use them wisely for targeted investigations.",
        "ratelimit": "Free: 10 requests/minute. Paid: 100 requests/minute.",
        "related": "None",
    },
    "CLEARBIT_API_KEY": {
        "name": "Clearbit API Key",
        "category": "OSINT",
        "description": "Clearbit API key for company and person data enrichment. Given a domain name, Clearbit returns detailed company profiles including name, description, logo, industry, employee count, funding history, technologies used, and key people. Given an email, it returns person details including name, bio, social media profiles, job title, and company. FRIDAY uses Clearbit for OSINT investigations (profile target companies), competitive analysis (analyze competitor tech stacks), and social engineering prep.",
        "pricing": "Free Tier: 50 lookups per month across all APIs. Paid: Prospector at $99/month (1,000 lookups), Pro at $349/month (10,000 lookups), Enterprise at custom pricing. The free tier is very limited but useful for testing and occasional lookups.",
        "url": "https://dashboard.clearbit.com/signup",
        "docs": "https://clearbit.com/docs",
        "test_url": "https://person.clearbit.com/v1/people/email/test@example.com",
        "test_headers": None,
        "howto": "1. Go to dashboard.clearbit.com 2. Sign up 3. Navigate to API section 4. Generate an API key 5. Copy the key.",
        "ratelimit": "Free: 1 lookup/second. Paid: 10 lookups/second.",
        "related": "None",
    },
    "HIBP_API_KEY": {
        "name": "Have I Been Pwned Key",
        "category": "OSINT",
        "description": "Have I Been Pwned (HIBP) API key for searching data breaches. HIBP maintains a database of over 12 billion compromised records from thousands of data breaches. FRIDAY uses HIBP to check if email addresses or usernames appear in known breaches, search for specific breach names and details, verify if passwords have been compromised (via k-anonymity), and get breach metadata including breach date, data classes compromised (emails, passwords, credit cards, etc.), and breach description.",
        "pricing": "Free — completely free to use with a verified API key. The API was created and is maintained by Troy Hunt as a public service. Rate limit of 10 requests per second with a verified API key. Without a key, rate is 1 request per 1.5 seconds. No paid tiers exist.",
        "url": "https://haveibeenpwned.com/API/Key",
        "docs": "https://haveibeenpwned.com/API/v3",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Go to haveibeenpwned.com/API/Key 2. Enter your email and request a key 3. Check your email for the API key 4. Copy the key into FRIDAY settings. The process takes about 2 minutes.",
        "ratelimit": "10 requests/second with API key. No daily limit.",
        "related": "None",
    },
    "DEHASHED_API_KEY": {
        "name": "Dehashed API Key",
        "category": "OSINT",
        "description": "Dehashed API key for dark web breach data searching. Dehashed indexes leaked credentials, emails, and personal information from dark web marketplaces, underground forums, and data dumps. FRIDAY uses Dehashed for advanced password breach analysis (get actual plaintext passwords), credential stuffing research, dark web threat intelligence, and comprehensive identity exposure checks.",
        "pricing": "Paid Only: Basic plan at $19.99/month for 10,000 search credits. Pro plan at $39.99/month for 50,000 search credits with API access. Enterprise at $99.99/month for unlimited credits. Each search query costs approximately 1-5 credits. There is NO free tier available — this is a paid-only service.",
        "url": "https://dehashed.com/pricing",
        "docs": "https://dehashed.com/docs",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Go to dehashed.com 2. Subscribe to a paid plan 3. Navigate to API settings 4. Generate an API key 5. Copy the key. Note: Dehashed is the only paid-only API key in the FRIDAY stack.",
        "ratelimit": "Basic: 1 query/5 seconds. Pro: 1 query/second.",
        "related": "None",
    },
    "INTELX_API_KEY": {
        "name": "Intelligence X API Key",
        "category": "OSINT",
        "description": "Intelligence X (IntelX) API key for dark web and deep web archival search. IntelX maintains a massive archive of data from dark web marketplaces, forums, paste sites, and leaked document repositories dating back years. FRIDAY uses IntelX to search for archived web pages (historical content that's been deleted), dark web market listings (products, vendors, prices), leaked documents (PDFs, spreadsheets, databases), email dumps, and credential leaks that are not indexed by Google.",
        "pricing": "Free Tier: Limited searches with basic results, 1 concurrent request. Paid: Basic at 10 EUR/month for 100 queries with full result access, Pro at 100 EUR/month for 1,000 queries, Enterprise at custom pricing with unlimited queries and dedicated infrastructure.",
        "url": "https://intelx.io/account",
        "docs": "https://intelx.io/docs",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Go to intelx.io 2. Create an account 3. Navigate to Account settings 4. Generate an API key 5. Copy the key. The free tier is very limited — consider the Basic plan for meaningful OSINT work.",
        "ratelimit": "Free: 1 request/10 seconds. Paid: 1 request/second.",
        "related": "None",
    },
    "ABUSEIPDB_API_KEY": {
        "name": "AbuseIPDB API Key",
        "category": "OSINT",
        "description": "AbuseIPDB API key for IP address reputation checking. AbuseIPDB is a community-maintained database of IP addresses reported for abusive behavior. FRIDAY uses AbuseIPDB to check if an IP address is associated with malicious activity including SSH brute-forcing (most common), web application scanning, spam sending, DDoS participation, port scanning, malware hosting, and phishing. Each check returns a confidence score (0-100), categories of abuse, and a list of recent reports with timestamps.",
        "pricing": "Free Tier: 1,000 checks per day with full result details (100 results per check). Paid: Community at $20/month for 10,000 checks/day, Professional at $100/month for 50,000 checks/day, Enterprise at custom pricing. All plans include WHOIS data and category classifications.",
        "url": "https://www.abuseipdb.com/register",
        "docs": "https://docs.abuseipdb.com",
        "test_url": "https://api.abuseipdb.com/api/v2/check?ipAddress=8.8.8.8",
        "test_headers": {"Key": "{key}", "Accept": "application/json"},
        "howto": "1. Go to abuseipdb.com/register 2. Create an account 3. Verify email 4. Navigate to API section 5. Generate an API key 6. Copy the key.",
        "ratelimit": "Free: 1 request/2 seconds. Paid: 30 requests/second.",
        "related": "None",
    },
    "IPINFO_API_KEY": {
        "name": "IPinfo API Key",
        "category": "OSINT",
        "description": "IPinfo API key for IP address geolocation and network intelligence. IPinfo provides comprehensive IP data including geographic location (city, region, country, latitude/longitude), ASN details (autonomous system number, organization, network range), ISP identification (internet service provider name), carrier detection for mobile IPs, VPN/proxy/anonymizer detection (identify traffic from privacy services), and domain name associated with the IP.",
        "pricing": "Free Tier: 50,000 requests per month with standard fields (IP, location, ASN, carrier). No credit card required. Paid: Growth at $25/month for 500,000 requests with additional fields like company details, privacy detection (VPN/proxy/tor flags), and abuse contact data. Pro at $250/month for 5M requests.",
        "url": "https://ipinfo.io/signup",
        "docs": "https://ipinfo.io/developers",
        "test_url": "https://ipinfo.io/json?token={key}",
        "test_headers": None,
        "howto": "1. Go to ipinfo.io/signup 2. Create a free account 3. Verify email 4. Navigate to Dashboard > Token 5. Copy your API token. 50,000 requests/month is very generous for personal use.",
        "ratelimit": "Free: 10 requests/second. Paid: 100 requests/second.",
        "related": "None",
    },
    "URLSCAN_API_KEY": {
        "name": "URLScan.io API Key",
        "category": "OSINT",
        "description": "URLScan.io API key for automated website analysis and screenshot service. URLScan.io takes full-page screenshots of websites and records detailed information about page resources, network connections, and security indicators. FRIDAY uses URLScan for phishing detection (analyze suspicious URLs), website profiling (identify technologies, third-party scripts), screenshot capture for evidence gathering, redirect chain analysis (trace where a URL ultimately leads), and extracting JavaScript, CSS, and resource URLs from scanned pages.",
        "pricing": "Free Tier: 50 scans per month with 1 concurrent scan, public results only. Paid: Micro at $29/month for 500 scans with 5 concurrent scans, Private plan at $99/month for 2,500 scans with private results, Team at $299/month for 10,000 scans. Each scan captures a full DOM snapshot, network HAR file, and security indicators.",
        "url": "https://urlscan.io/user/signup",
        "docs": "https://urlscan.io/docs/api",
        "test_url": "https://urlscan.io/user/quotas/",
        "test_headers": {"API-Key": "{key}"},
        "howto": "1. Go to urlscan.io 2. Sign up for a free account 3. Verify email 4. Navigate to User > API 5. Copy your API key. The free tier gives 50 scans/month.",
        "ratelimit": "Free: 1 request/10 seconds. Paid: 10 requests/second.",
        "related": "None",
    },
    "BUILTWITH_API_KEY": {
        "name": "BuiltWith API Key",
        "category": "OSINT",
        "description": "BuiltWith API key for website technology stack profiling. BuiltWith identifies all technologies used by a website including web frameworks (React, Angular, Vue), CMS platforms (WordPress, Shopify, Magento), analytics tools (Google Analytics, Mixpanel), CDN providers (Cloudflare, Akamai), advertising networks, JavaScript libraries, server software, and payment processors. FRIDAY uses BuiltWith for competitive analysis and website reconnaissance.",
        "pricing": "Free Tier: 50 lookups per month with basic technology data. Paid: Pro at $295/month for 5,000 lookups with historical data and trend analysis. Team at $595/month for unlimited lookups with API access and CSV exports.",
        "url": "https://builtwith.com/signup",
        "docs": "https://api.builtwith.com",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Go to builtwith.com 2. Sign up for an account 3. Navigate to API section 4. Generate an API key 5. Copy the key.",
        "ratelimit": "Pro: 500 lookups/day. Team: Unlimited.",
        "related": "None",
    },
    "SECURITYTRAILS_API_KEY": {
        "name": "SecurityTrails API Key",
        "category": "OSINT",
        "description": "SecurityTrails API key for DNS and domain intelligence. SecurityTrails provides comprehensive DNS data including subdomain discovery (complete list of subdomains for any domain), reverse DNS (find all domains hosted on an IP address), WHOIS history (historical WHOIS records for domain ownership tracking), SSL certificate correlation (find all certificates associated with a domain), and DNS record enumeration across all record types (A, AAAA, MX, NS, TXT, CNAME, SOA).",
        "pricing": "Free Tier: 50 queries per month with basic DNS data. Paid: Professional at $49/month for 5,000 queries with full DNS history and WHOIS data. Enterprise at $149/month for 25,000 queries with API access and priority support.",
        "url": "https://securitytrails.com/signup",
        "docs": "https://docs.securitytrails.com",
        "test_url": "https://api.securitytrails.com/v1/ping",
        "test_headers": {"APIKEY": "{key}"},
        "howto": "1. Go to securitytrails.com 2. Sign up for an account 3. Navigate to API section 4. Generate an API key 5. Copy the key.",
        "ratelimit": "Free: 1 query/10 seconds. Paid: 10 queries/second.",
        "related": "None",
    },
    "WHATCMS_API_KEY": {
        "name": "WhatCMS API Key",
        "category": "OSINT",
        "description": "WhatCMS API key for Content Management System detection. Given a URL, WhatCMS identifies the CMS powering the website including version detection where available. Supports 500+ CMS platforms including WordPress, Joomla, Drupal, Shopify, Magento, Wix, Squarespace, Weebly, Ghost, Blogger, and many more obscure systems. FRIDAY uses WhatCMS for website reconnaissance and vulnerability assessment.",
        "pricing": "Free Tier: 500 checks per day with CMS name and version detection. Paid: Developer at $10/month for 5,000 checks with extended reporting. Business at $50/month for 50,000 checks with priority support and API access.",
        "url": "https://whatcms.org/API",
        "docs": "https://whatcms.org/API",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Go to whatcms.org 2. Create an account 3. Navigate to API section 4. Generate an API key 5. Copy the key. The free tier of 500 checks/day is very generous.",
        "ratelimit": "Free: 1 request/2 seconds. Paid: 10 requests/second.",
        "related": "None",
    },
    "FULLCONTACT_API_KEY": {
        "name": "FullContact API Key",
        "category": "OSINT",
        "description": "FullContact API key for person identity resolution and data enrichment. Given an email address or phone number, FullContact returns comprehensive identity data including full name, location, social media profiles (Twitter, LinkedIn, Facebook), employment history, company information, interests, and demographic data. FRIDAY uses FullContact for social engineering preparation, identity verification, and contact enrichment.",
        "pricing": "Free Tier: 50 lookups per month with basic identity data (name, location). Paid: Lite at $99/month for 500 lookups with full social profile data. Pro at $349/month for 5,000 lookups with company enrichment and employment history. Enterprise at custom pricing.",
        "url": "https://dashboard.fullcontact.com/signup",
        "docs": "https://www.fullcontact.com/developer/docs/",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Go to dashboard.fullcontact.com 2. Sign up for an account 3. Navigate to API section 4. Generate an API key 5. Copy the key.",
        "ratelimit": "Free: 1 lookup/second. Paid: 5 lookups/second.",
        "related": "None",
    },
    "GITHUB_CLIENT_ID": {
        "name": "GitHub OAuth Client ID",
        "category": "Development",
        "description": "GitHub OAuth App client identifier for authenticating FRIDAY with the GitHub API via OAuth flow. FRIDAY uses GitHub for code repository analysis (read file contents, commit history, contributors), issue and PR management (create, update, close issues and pull requests), code search across public repositories, user profile lookup, repository statistics and health metrics, GitHub Actions monitoring (workflow runs, job status), and software composition analysis. OAuth provides scoped, revocable access without sharing a long-lived token.",
        "pricing": "Free — unlimited API calls with a rate limit of 5,000 requests per hour for authenticated users (versus 60/hour unauthenticated). GitHub Actions minutes included: free tier gives 2,000 minutes/month for public repositories and self-hosted runners.",
        "url": "https://github.com/settings/developers",
        "docs": "https://docs.github.com/en/apps/oauth-apps",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Go to github.com/settings/developers 2. Click 'New OAuth App' 3. Set Application name: FRIDAY 4. Set Homepage URL: http://127.0.0.1:7071 5. Set Authorization callback URL: http://127.0.0.1:7071/settings/github/callback 6. Register and copy the Client ID and Client Secret 7. Paste both into FRIDAY settings.",
        "ratelimit": "5,000 requests/hour. 2,000 GitHub Actions minutes/month (free).",
        "related": "GITHUB_CLIENT_SECRET",
    },
    "GITHUB_CLIENT_SECRET": {
        "name": "GitHub OAuth Client Secret",
        "category": "Development",
        "description": "GitHub OAuth App client secret — the confidential counterpart to GITHUB_CLIENT_ID. Used together in the OAuth authorization code flow to exchange temporary codes for access tokens. FRIDAY stores this locally and uses it to authenticate GitHub API requests on your behalf. Never share this secret — it grants API access to all repos your OAuth app has scoped access to.",
        "pricing": "Free — no cost for OAuth App registration or usage. GitHub does not charge for API calls made through OAuth tokens.",
        "url": "https://github.com/settings/developers",
        "docs": "https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps",
        "test_url": None,
        "test_headers": None,
        "howto": "1. In the same GitHub OAuth App where you got the Client ID 2. Click 'Generate a new client secret' 3. Copy the secret immediately (it's shown only once) 4. Paste into FRIDAY settings. Keep this value secure — it's equivalent to a password for your GitHub integration.",
        "ratelimit": "Same as Client ID: 5,000 requests/hour.",
        "related": "GITHUB_CLIENT_ID",
    },
    "OPENCAGE_API_KEY": {
        "name": "OpenCage Geocoding Key",
        "category": "OSINT",
        "description": "OpenCage Geocoding API key for forward and reverse geocoding. Forward geocoding converts street addresses and place names into GPS coordinates (latitude/longitude). Reverse geocoding converts coordinates into human-readable addresses. OpenCage supports 300+ countries with comprehensive address formatting, timezone data, and elevation information. FRIDAY uses OpenCage for location analysis in OSINT investigations, map plotting, and address validation.",
        "pricing": "Free Tier: 2,500 requests per day with standard geocoding (forward and reverse). No credit card required. Paid: Starting at 50 EUR for 100,000 additional requests through top-ups. OpenCage credits never expire — you buy once and use until depleted. Enterprise: Custom pricing for high-volume users.",
        "url": "https://opencagedata.com/users/sign_up",
        "docs": "https://opencagedata.com/api",
        "test_url": "https://api.opencagedata.com/geocode/v1/json?q=51.5,-0.09&key={key}",
        "test_headers": None,
        "howto": "1. Go to opencagedata.com/users/sign_up 2. Create an account 3. Verify email 4. Navigate to Dashboard > API Keys 5. Copy your API key. The free tier of 2,500 requests/day is one of the most generous geocoding free tiers available.",
        "ratelimit": "Free: 1 request/second. Paid: 10 requests/second.",
        "related": "None",
    },
    "SPOTIFY_CLIENT_ID": {
        "name": "Spotify Client ID",
        "category": "Media",
        "description": "Spotify API client identifier for music playback control integration. FRIDAY uses the Spotify API to play, pause, skip, and control music playback on your Spotify-connected devices (phone, computer, speaker). Additional capabilities include searching for tracks/albums/artists, managing and creating playlists, displaying currently playing information with album art, and controlling playback volume. Requires Spotify Premium for active device playback control.",
        "pricing": "Free — requires a Spotify Developer account which is free to create with any Spotify account (including free tier). No usage limits on API calls for music search and playlist management. Device playback control requires Spotify Premium.",
        "url": "https://developer.spotify.com/dashboard",
        "docs": "https://developer.spotify.com/documentation/web-api",
        "test_url": "https://api.spotify.com/v1/me",
        "test_headers": {},
        "howto": "1. Go to developer.spotify.com/dashboard 2. Log in with your Spotify account 3. Click 'Create App' 4. Name your app and add a description 5. Check 'Web API' and click create 6. Copy the Client ID and Client Secret from the app dashboard 7. Click 'Edit Settings' and add http://127.0.0.1:8888/callback to Redirect URIs",
        "ratelimit": "No official rate limit for most endpoints. Practical limit: ~100 requests/minute.",
        "related": "SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI",
    },
    "SPOTIFY_CLIENT_SECRET": {
        "name": "Spotify Client Secret",
        "category": "Media",
        "description": "Spotify API client secret paired with SPOTIFY_CLIENT_ID for OAuth 2.0 authentication. Required to obtain access and refresh tokens for Spotify API requests. Keep this secret confidential — never expose it in client-side code or share it with third parties.",
        "pricing": "Free — generated from Spotify Developer Dashboard alongside the Client ID. You can rotate the secret from the dashboard at any time.",
        "url": "https://developer.spotify.com/dashboard",
        "docs": "https://developer.spotify.com/documentation/web-api",
        "test_url": None,
        "test_headers": None,
        "howto": "Generated automatically when you create a Spotify App in the Developer Dashboard. Click 'View Client Secret' in your app settings to see it.",
        "ratelimit": "Same as SPOTIFY_CLIENT_ID.",
        "related": "SPOTIFY_CLIENT_ID",
    },
    "ALEXA_WEBHOOK_URL": {
        "name": "Alexa Webhook URL",
        "category": "Integration",
        "description": "Public ngrok URL that receives Alexa skill requests from Amazon Echo devices. This URL is registered with your Alexa Skill as the endpoint that Alexa calls when a user speaks a command. The ngrok tunnel routes traffic from the public internet to your local FRIDAY instance. Without an active ngrok tunnel, Alexa integration will not work.",
        "pricing": "Requires ngrok account (free tier: 2 simultaneous tunnels, 4 connections per minute, random subdomains, 40 connections/minute total). Paid: Basic at $8/month for custom subdomains, 3 tunnels, 120 connections/minute. Pro at $25/month for 10 tunnels, 300 connections/minute.",
        "url": "https://ngrok.com",
        "docs": "https://ngrok.com/docs",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Go to ngrok.com 2. Create a free account 3. Download and install ngrok 4. Authenticate with 'ngrok config add-authtoken YOUR_TOKEN' 5. Run 'ngrok http 7071' to create a tunnel 6. Copy the generated https URL 7. Register this URL in your Alexa Skill configuration",
        "ratelimit": "Free: 4 connections/minute, 40 connections/minute total.",
        "related": "FRIDAY_WEBHOOK_SECRET",
    },
    "FRIDAY_WEBHOOK_SECRET": {
        "name": "FRIDAY Webhook Secret",
        "category": "Integration",
        "description": "HMAC signing secret for verifying that incoming webhook requests genuinely come from Amazon Alexa. When Alexa sends a request to your webhook URL, it signs the request with this secret. FRIDAY verifies the signature before processing the request, preventing unauthorized actors from sending fake requests.",
        "pricing": "Config value set by the user. No cost. Must be a random string of at least 32 characters. Use a password manager to generate and store this value.",
        "url": None,
        "docs": None,
        "test_url": None,
        "test_headers": None,
        "howto": "1. Generate a random string of 32+ characters (use a password manager or 'openssl rand -hex 32') 2. Set it as FRIDAY_WEBHOOK_SECRET in .env 3. Configure the same secret in your Alexa Skill's endpoint configuration.",
        "ratelimit": "No rate limit.",
        "related": "ALEXA_WEBHOOK_URL",
    },
    "GCP_PROJECT": {
        "name": "Google Cloud Project ID",
        "category": "Google",
        "description": "Your Google Cloud Project ID is the unique identifier used to associate resources, billing, and quotas with your GCP account. FRIDAY uses this to route API calls to the correct project and track usage against project-level quotas for Gemini, Vision, and other Google Cloud services.",
        "pricing": "Free tier includes $300 credits for new users. Pay-as-you-go pricing varies by service (compute, storage, AI/ML APIs). Most Google APIs have a free monthly quota before billing applies. Projects can be configured with budget alerts to prevent unexpected charges.",
        "url": "https://console.cloud.google.com",
        "docs": "https://cloud.google.com/docs/overview",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Go to console.cloud.google.com 2. Select or create a project from the top navigation bar 3. The Project ID is shown in the project info card 4. Copy the Project ID (not the Name or Number) 5. Set it as GCP_PROJECT in FRIDAY settings",
        "ratelimit": "Varies by API; typically 60-600 requests per minute per project",
        "related": "GCP_LOCATION, GOOGLE_API_KEY, GEMINI_MODEL",
    },
    "GCP_LOCATION": {
        "name": "Google Cloud Location/Region",
        "category": "Google",
        "description": "The GCP region or location (e.g., us-central1, europe-west4) determines where your API requests are processed and where data resides. FRIDAY uses this to target the correct regional endpoint for services like Vertex AI, Speech-to-Text, Translation, and other regional GCP services. Choosing a region close to you reduces latency.",
        "pricing": "Free to configure. Some services have region-specific pricing tiers, but the location parameter itself incurs no cost. Data egress between regions may incur charges. Most Google services are available in multiple regions for redundancy.",
        "url": "https://cloud.google.com/compute/docs/regions-zones",
        "docs": "https://cloud.google.com/compute/docs/regions-zones#available",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Visit cloud.google.com/compute/docs/regions-zones 2. Choose a region close to you (e.g., us-central1, europe-west4, asia-southeast1) 3. Set this value to the region string (e.g., 'us-central1') 4. Ensure the region supports the GCP services you plan to use 5. Common choices: us-central1 (low cost, broad support), europe-west4 (Netherlands, good for EU users)",
        "ratelimit": "N/A — configuration value only",
        "related": "GCP_PROJECT, GOOGLE_API_KEY, GEMINI_MODEL, GEMINI_LIVE_MODEL",
    },
    "SPOTIFY_REDIRECT_URI": {
        "name": "Spotify OAuth Redirect URI",
        "category": "Media",
        "description": "The registered redirect URI for Spotify OAuth authentication, typically pointing to a local or hosted callback endpoint on port 8888. FRIDAY uses this during the OAuth flow to receive the authorization code after the user approves access to their Spotify account for music playback control.",
        "pricing": "Free to register in the Spotify Developer Dashboard. No cost associated with the redirect URI itself. Must match exactly what is configured in your Spotify App settings, including the protocol (http://) and port.",
        "url": "https://developer.spotify.com/dashboard",
        "docs": "https://developer.spotify.com/documentation/web-api/concepts/apps",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Go to developer.spotify.com/dashboard 2. Create or select your app 3. Click 'Edit Settings' 4. Add your redirect URI to the 'Redirect URIs' field (e.g., http://localhost:8888/callback) 5. Click 'Save' and copy the exact URI into this field 6. Default value: http://127.0.0.1:8888/callback",
        "ratelimit": "N/A — configuration value only",
        "related": "SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET",
    },
    "OPENCODE_ZEN_MODEL": {
        "name": "OpenCode Zen Model Name",
        "category": "AI",
        "description": "The model identifier string for the OpenCode Zen API, specifying which language model to use for multi-agent orchestration and code generation. FRIDAY passes this to the OpenCode Zen endpoint to select the appropriate model variant. The default 'big-pickle' model provides the best balance of speed and capability for agentic workflows.",
        "pricing": "Free credits included with every OpenCode account (typically 10,000 credits). Usage-based pricing after free credits: approximately $0.50 per 1K agent calls. Different models have different pricing tiers — larger models cost more per token.",
        "url": "https://opencode.ai/zen",
        "docs": "https://opencode.ai/docs/zen-models",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Visit opencode.ai/zen to view available models 2. Choose a model (e.g., 'big-pickle' for best quality, 'mimo-v2.5' for faster responses) 3. Copy the model name string exactly as shown on the OpenCode dashboard 4. Set this value in your FRIDAY settings",
        "ratelimit": "Free: 20 req/min. Paid: 500 req/min for standard tier",
        "related": "OPENCODE_ZEN_API_KEY, ZEN_API_BASE",
    },
    "NVIDIA_NIM_VISION_MODEL": {
        "name": "NVIDIA NIM Vision Model",
        "category": "AI",
        "description": "The model name for NVIDIA NIM's vision-language inference API, enabling image understanding and multimodal reasoning on NVIDIA's cloud infrastructure. FRIDAY uses this to identify objects in camera feeds, read text from screenshots, describe visual scenes, and perform OCR. The default model is microsoft/Florence-2-large.",
        "pricing": "Free Tier: NVIDIA offers 1,000+ free API calls across all NIM models. Rate limited to 10 requests per minute on free tier. Paid: Pay-per-token pricing approximately $0.10 per 1K tokens for vision models. No credit card required to start.",
        "url": "https://build.nvidia.com/explore/discover",
        "docs": "https://docs.nvidia.com/nim/large-language-models/latest/introduction.html",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Sign in at build.nvidia.com 2. Browse available NIM vision models 3. Use the dropdown in the playground to find model names 4. Common models: microsoft/Florence-2-large, nvidia/vision-language-model 5. Copy the exact model name string into this field",
        "ratelimit": "Free: 10 req/min. Paid: 100 req/min per API key",
        "related": "NVIDIA_VISION_API_KEY, NVIDIA_NIM_API_KEY, NVIDIA_NIM_MODEL",
    },
    "GITLAB_TOKEN": {
        "name": "GitLab Personal Access Token",
        "category": "Development",
        "description": "A GitLab personal access token used to authenticate API requests for repository management, CI/CD pipelines, and code search on GitLab instances. FRIDAY uses this token to clone private repositories, read project files, create merge requests, manage issues, trigger pipelines, and interact with the GitLab API on your behalf for software engineering tasks.",
        "pricing": "Free tier includes unlimited private repositories and 400 CI/CD minutes per month. Premium at $29/user/month for 10,000 CI minutes and advanced features. Ultimate at $99/user/month for 50,000 CI minutes with compliance and security features.",
        "url": "https://gitlab.com/-/user_settings/personal_access_tokens",
        "docs": "https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html",
        "test_url": "https://gitlab.com/api/v4/user",
        "test_headers": {"Authorization": "Bearer {key}"},
        "howto": "1. Go to gitlab.com/-/user_settings/personal_access_tokens 2. Enter a token name and set an expiration date 3. Select scopes: 'api', 'read_repository', 'write_repository' 4. Click 'Create personal access token' 5. Copy the token immediately (it won't be shown again after you leave the page)",
        "ratelimit": "Free: 2,000 requests/hour. Premium/Ultimate: 6,000 requests/hour",
        "related": "None",
    },
    "TELEGRAM_API_ID": {
        "name": "Telegram API ID",
        "category": "OSINT",
        "description": "Your Telegram API ID is a numeric identifier for your application, required alongside the API Hash to authenticate with Telegram's MTProto API. FRIDAY uses this combination to access Telegram channels for OSINT data collection, scrape message data from public groups, monitor channels for keywords, and interact with the Telegram network for social intelligence gathering.",
        "pricing": "Free. Telegram provides API credentials at no cost to any registered developer. No usage limits beyond the standard API rate limiting of approximately 30 messages per second. A phone number is required to register for API access.",
        "url": "https://my.telegram.org/apps",
        "docs": "https://core.telegram.org/api/obtaining_api_id",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Log in to my.telegram.org with your phone number 2. Go to 'API Development Tools' 3. Create a new application if none exists 4. Copy the 'api_id' field (a numeric value, typically 6-8 digits) 5. Keep this value private — it identifies your app to Telegram's servers",
        "ratelimit": "Approximately 30 messages per second per connection; flood wait limits apply on excessive use",
        "related": "TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN",
    },
    "TELEGRAM_API_HASH": {
        "name": "Telegram API Hash",
        "category": "OSINT",
        "description": "The Telegram API Hash is a secret key paired with your API ID to authenticate your application with Telegram's MTProto protocol. FRIDAY uses the hash alongside the API ID to establish encrypted sessions for reading channel messages, monitoring public groups, scraping user profile information, and collecting media metadata for OSINT investigations.",
        "pricing": "Free. No cost for API credentials. Telegram does not charge for API access regardless of usage volume. The API hash is generated once per application and remains valid indefinitely unless regenerated.",
        "url": "https://my.telegram.org/apps",
        "docs": "https://core.telegram.org/api/obtaining_api_id",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Log in to my.telegram.org with your phone number 2. Go to 'API Development Tools' 3. Locate the 'api_hash' field for your application (a 32-character hex string) 4. Copy the full hash string 5. Store it securely — this is a secret credential that grants API access",
        "ratelimit": "Same as API ID: ~30 messages/second per connection",
        "related": "TELEGRAM_API_ID, TELEGRAM_BOT_TOKEN",
    },
    "REDDIT_CLIENT_ID": {
        "name": "Reddit API Client ID",
        "category": "OSINT",
        "description": "The Reddit API Client ID is a public identifier for your registered Reddit application, used in OAuth authentication flows to access Reddit's content API. FRIDAY uses this with the Client Secret to obtain access tokens for reading subreddit content, searching posts and comments, tracking trending topics, collecting user profile data, and analyzing community discussions for OSINT.",
        "pricing": "Free. Reddit's API is free for non-commercial use with rate limits of 60 requests per minute per OAuth client. Paid tiers for enterprise/commercial usage via Reddit Data API pricing starting at $0.24 per 1K API calls. A Reddit account is required to register an application.",
        "url": "https://www.reddit.com/prefs/apps",
        "docs": "https://github.com/reddit-archive/reddit/wiki/OAuth2",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Go to reddit.com/prefs/apps 2. Click 'Create App' or 'Create Another App' at the bottom 3. Select 'script' type (for personal use) 4. Enter a name and description 5. Set redirect URI to http://127.0.0.1:8080 6. The Client ID is the 14-character string under the app name 7. Copy this ID for configuration",
        "ratelimit": "60 requests per minute per OAuth client ID. Higher limits available on request for approved use cases.",
        "related": "REDDIT_CLIENT_SECRET",
    },
    "REDDIT_CLIENT_SECRET": {
        "name": "Reddit API Client Secret",
        "category": "OSINT",
        "description": "The Reddit API Client Secret is a confidential key used with the Client ID for OAuth2 authentication to Reddit's API. FRIDAY uses this secret to obtain authorized access tokens, enabling programmatic read access to subreddit content, user data, and comment streams for social media intelligence gathering and online discourse analysis.",
        "pricing": "Free for non-commercial use. Commercial access requires a Data Licensing agreement with Reddit. The secret can be regenerated from the app settings page at any time, which will invalidate the previous secret immediately.",
        "url": "https://www.reddit.com/prefs/apps",
        "docs": "https://github.com/reddit-archive/reddit/wiki/OAuth2",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Visit reddit.com/prefs/apps 2. Find your created app under 'Developer Applications' 3. The 'secret' field is shown as a long alphanumeric string 4. Click 'edit' to reveal the secret if masked 5. Copy the full secret string 6. Store this securely — it grants API access to Reddit's content",
        "ratelimit": "Same as Client ID: 60 requests/minute",
        "related": "REDDIT_CLIENT_ID",
    },
    "TWITTER_BEARER_TOKEN": {
        "name": "Twitter/X API Bearer Token",
        "category": "OSINT",
        "description": "A Twitter/X API v2 Bearer Token used for server-to-server OAuth 2.0 authentication, allowing read-only access to public Twitter data without user context. FRIDAY uses this token to search tweets by keyword/hashtag, retrieve user timelines and mentions, track conversation threads, collect engagement metrics, and perform social media intelligence gathering at scale.",
        "pricing": "Free tier: Very limited (only 1,500 tweets/month with Essential access). Basic at $100/month for 10K tweets/month. Pro at $5,000/month for 1M tweets/month. Enterprise pricing available for higher volumes. Read-only access with Bearer Token does not require user authentication.",
        "url": "https://developer.twitter.com/en/portal/dashboard",
        "docs": "https://developer.twitter.com/en/docs/authentication/oauth-2-0/bearer-tokens",
        "test_url": "https://api.twitter.com/2/tweets/search/recent?query=test&max_results=5",
        "test_headers": {"Authorization": "Bearer {key}"},
        "howto": "1. Go to developer.twitter.com/en/portal/dashboard 2. Create a Project and a new App (requires approved Developer Account) 3. Navigate to 'Keys and Tokens' tab 4. Under 'Bearer Token', click 'Regenerate' or copy the existing token 5. The token starts with 'AAAAAAAAAAAAAAAAAAAA...' and is ~100 characters long",
        "ratelimit": "Free: 450 requests/15min (app-only). Basic: 1,500 requests/15min. Pro: 15,000 requests/15min.",
        "related": "TWITTER_API_KEY, TWITTER_API_SECRET",
    },
    "TWITTER_API_KEY": {
        "name": "Twitter/X API Key (Consumer Key)",
        "category": "OSINT",
        "description": "The Twitter/X API Key (also called Consumer Key) is the public identifier for your Twitter developer application used in OAuth 1.0a authentication. FRIDAY uses this alongside the API Secret for user-context operations like posting tweets, reading direct messages, and accessing account-specific data that requires user-level authentication.",
        "pricing": "Included with Twitter API subscription: Basic ($100/month), Pro ($5,000/month), or Enterprise (custom pricing). No free tier for write access. The API Key is generated when you create a Twitter App in the Developer Portal.",
        "url": "https://developer.twitter.com/en/portal/dashboard",
        "docs": "https://developer.twitter.com/en/docs/authentication/oauth-1-0a/api-key-and-secret",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Open developer.twitter.com/en/portal/dashboard 2. Select your Project and App 3. Go to 'Keys and Tokens' tab 4. Under 'Consumer Keys', copy the 'API Key' string 5. Note: this is different from the Bearer Token — both serve different authentication methods",
        "ratelimit": "Varies by endpoint; typically 75-300 requests per 15-minute window per user context",
        "related": "TWITTER_API_SECRET, TWITTER_BEARER_TOKEN",
    },
    "TWITTER_API_SECRET": {
        "name": "Twitter/X API Secret (Consumer Secret)",
        "category": "OSINT",
        "description": "The Twitter/X API Secret (Consumer Secret) is the confidential counterpart to the API Key, used in OAuth 1.0a HMAC-SHA1 signing of requests for user-level API access. FRIDAY uses this secret to cryptographically sign authenticated requests for Twitter operations that require user context, such as posting tweets and reading timelines.",
        "pricing": "Same as API Key: requires a paid subscription tier starting at $100/month. The secret can be regenerated from the Developer Portal at any time, which invalidates the previous secret and all tokens created with it.",
        "url": "https://developer.twitter.com/en/portal/dashboard",
        "docs": "https://developer.twitter.com/en/docs/authentication/oauth-1-0a/api-key-and-secret",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Go to developer.twitter.com/en/portal/dashboard 2. Select your app under the Project 3. Navigate to 'Keys and Tokens' 4. Under 'Consumer Keys', click 'Regenerate' or copy 'API Secret' 5. Store this value securely — never expose it in client-side code or commit it to version control",
        "ratelimit": "Same rate limits as API Key; tied to the same project and app",
        "related": "TWITTER_API_KEY, TWITTER_BEARER_TOKEN",
    },
    "INSTAGRAM_USER": {
        "name": "Instagram Username",
        "category": "OSINT",
        "description": "The Instagram account username used for authenticated scraping and data collection via Instagram's private API (using the instagrapi library). FRIDAY uses this credential with the corresponding password to log into Instagram for extracting follower data, post metadata, story content, profile information, and hashtag analytics for social media intelligence.",
        "pricing": "Free — uses a standard Instagram account. No API subscription required. Instagram does not officially support automated access; use at your own risk respecting terms of service. Consider using a dedicated account for scraping to protect your primary account from rate limiting or blocks.",
        "url": "https://www.instagram.com",
        "docs": "https://developers.facebook.com/docs/instagram-basic-display-api/",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Create or use an existing Instagram account 2. Note the exact username (case-sensitive) 3. Enable two-factor authentication for account security 4. Enter the username in this field 5. Enter the corresponding password in the INSTAGRAM_PASS field 6. Consider using a dedicated OSINT account to avoid risking your personal account",
        "ratelimit": "No official rate limit; aggressive scraping may trigger temporary blocks or phone verification challenges",
        "related": "INSTAGRAM_PASS",
    },
    "INSTAGRAM_PASS": {
        "name": "Instagram Password",
        "category": "OSINT",
        "description": "The password for the Instagram account used by FRIDAY for authenticated data collection via the instagrapi library. This credential allows FRIDAY to establish a session with Instagram's internal API for accessing profile data, follower lists, post metadata, story archives, and hashtag-based content discovery that is not available through public endpoints.",
        "pricing": "Free. No additional cost beyond a standard Instagram account. The password is stored encrypted in FRIDAY's configuration and is only used for establishing API sessions. It is never transmitted to third parties beyond Instagram's servers.",
        "url": "https://www.instagram.com",
        "docs": "https://developers.facebook.com/docs/instagram-basic-display-api/",
        "test_url": None,
        "test_headers": None,
        "howto": "1. Ensure your Instagram account uses a strong, unique password 2. Avoid using your personal primary account — create a dedicated account for OSINT work 3. Enable two-factor authentication on the account 4. Enter the password in this field 5. FRIDAY will use instagrapi to authenticate and create a session",
        "ratelimit": "Same as Instagram username — no official SLA; use responsibly to avoid account restrictions",
        "related": "INSTAGRAM_USER",
    },
    "OTX_API_KEY": {
        "name": "AlienVault OTX API Key",
        "category": "OSINT",
        "description": "The API key for AlienVault Open Threat Exchange (OTX), a collaborative threat intelligence platform where security researchers share indicators of compromise (IOCs). FRIDAY uses this key to query OTX for IP reputation data, malware hash lookups, domain threat intelligence, threat actor profiles, and pulse intelligence feeds for cybersecurity analysis and threat hunting.",
        "pricing": "Free tier includes full access to community pulses, threat intelligence feeds, and up to 1,000 API calls per day. OTX Pro subscription at $1,200/year includes premium pulses, dedicated support, and higher rate limits. No credit card required for free tier.",
        "url": "https://otx.alienvault.com",
        "docs": "https://otx.alienvault.com/api",
        "test_url": "https://otx.alienvault.com/api/v1/user/me",
        "test_headers": {"X-OTX-API-KEY": "{key}"},
        "howto": "1. Register at otx.alienvault.com (free) 2. Log in and go to your profile settings 3. Click 'API Keys' in the sidebar 4. Generate a new API key or copy your existing one 5. Paste the key into this configuration field in FRIDAY settings",
        "ratelimit": "Free: 1,000 requests/day, 10 requests/second. Pro: higher limits available",
        "related": "VIRUSTOTAL_API_KEY, SHODAN_API_KEY, ABUSEIPDB_API_KEY",
    },
    "LEAKCHECK_API_KEY": {
        "name": "LeakCheck.io API Key",
        "category": "OSINT",
        "description": "The API key for LeakCheck.io, a breach database search service that indexes compromised credentials from thousands of data breaches. FRIDAY uses this key to query email addresses, usernames, and domains against known breach datasets for security investigations, password reuse analysis, and credential exposure assessments during OSINT operations.",
        "pricing": "Pay-per-search pricing starting at approximately $0.10/query. Monthly subscription plans available from $29/month for 1,000 queries. Pro plan at $99/month for 10,000 queries. Enterprise plans for high-volume searching with custom rate limits and dedicated support.",
        "url": "https://leakcheck.io",
        "docs": "https://leakcheck.io/docs/api",
        "test_url": "https://leakcheck.io/api/v1/account",
        "test_headers": {"Authorization": "Bearer {key}"},
        "howto": "1. Create an account at leakcheck.io 2. Purchase a subscription or credits 3. Go to your account dashboard 4. Locate your API key in the 'API' section 5. Copy the key and enter it here 6. Note: LeakCheck.io is a paid service with no free tier",
        "ratelimit": "Varies by plan: 10-100 requests/minute depending on subscription tier",
        "related": "DEHASHED_API_KEY, HIBP_API_KEY",
    },
    "FLICKR_API_KEY": {
        "name": "Flickr API Key",
        "category": "Media",
        "description": "The Flickr API Key grants access to Flickr's photo-sharing platform for searching and retrieving images, albums, user profiles, geotagged photos, and metadata. FRIDAY uses this to search for Creative Commons images by keyword, download photo metadata including EXIF data and geolocation, retrieve album contents, and collect geotagged photos for location-based analysis.",
        "pricing": "Free for non-commercial use with 3,600 API calls per hour per key. Commercial licenses available through Flickr. A free Flickr account (1,000 photo limit) is sufficient for API access. Pro account at $8.99/month for unlimited storage and advanced stats.",
        "url": "https://www.flickr.com/services/apps/create/",
        "docs": "https://www.flickr.com/services/api/",
        "test_url": "https://api.flickr.com/services/rest/?method=flickr.test.echo&api_key={key}&format=json",
        "test_headers": None,
        "howto": "1. Log in to Flickr at flickr.com 2. Go to flickr.com/services/apps/create/ 3. Click 'Request an API Key' 4. Select 'Apply for a non-commercial key' 5. Fill in the required information 6. Copy the generated API Key (a 32-character hex string)",
        "ratelimit": "3,600 requests/hour per API key. Applies to all Flickr API endpoints.",
        "related": "FLICKR_API_SECRET",
    },
    "DISCOGS_TOKEN": {
        "name": "Discogs API Token",
        "category": "Media",
        "description": "The Discogs API Token (personal access token) authenticates requests to the Discogs music database API for querying artists, releases, labels, and market pricing data. FRIDAY uses this to search the Discogs catalog for album information, retrieve track listings and credits, look up vinyl and cassette pricing, and collect music metadata for cataloging and analysis.",
        "pricing": "Free tier allows up to 25 requests per minute from a single IP address for authenticated users. No paid tiers required for personal use. Commercial usage requires approval from Discogs. A Discogs account is free and required to generate a token.",
        "url": "https://www.discogs.com/settings/developers",
        "docs": "https://www.discogs.com/developers",
        "test_url": "https://api.discogs.com/oauth/identity",
        "test_headers": {"Authorization": "Discogs token={key}", "User-Agent": "FRIDAY/1.0"},
        "howto": "1. Log in to discogs.com 2. Go to Settings > Developers 3. Click 'Generate New Token' under 'Personal Access Tokens' 4. Give the token a description (e.g., 'FRIDAY') 5. Copy the generated token string and paste it here",
        "ratelimit": "25 requests/minute per IP. Database endpoints: 60 requests/minute for authenticated users.",
        "related": "DISCOGS_CONSUMER_KEY, DISCOGS_CONSUMER_SECRET",
    },
    "DISCORD_BOT_TOKEN": {
        "name": "Discord Bot Token",
        "category": "Social",
        "description": "Discord bot token for authenticating your bot with Discord's API. FRIDAY uses this to read messages, manage servers, and interact with users on Discord servers where the bot is invited. The token is generated from the Discord Developer Portal and grants full access to all capabilities your bot has been assigned.",
        "pricing": "Free. Discord bots are free to create and use. No paid tier required. However, Discord has rate limits: 50 API calls per second per bot, with specific endpoint limits (e.g., 10,000 webhook updates per day).",
        "url": "https://discord.com/developers/applications",
        "docs": "https://discord.com/developers/docs/topics/oauth2#bot-tokens",
        "test_url": "https://discord.com/api/v10/users/@me",
        "test_headers": {"Authorization": "Bot {key}"},
        "howto": "1. Go to discord.com/developers/applications 2. Click 'New Application' and name it FRIDAY 3. Go to Bot settings 4. Click 'Reset Token' 5. Copy the token (starts with 'MTE...') 6. Under Privileged Gateway Intents, enable all three intents 7. Paste the token into FRIDAY settings",
        "ratelimit": "50 requests/second per bot. Global rate limit: ~100 requests/second.",
        "related": "None",
    },
    "DEHASHED_EMAIL": {
        "name": "Dehashed API Email",
        "category": "OSINT",
        "description": "The email address used to authenticate with the Dehashed API, a breach intelligence service that aggregates compromised credentials from thousands of data breaches across the surface web, deep web, and dark web. FRIDAY uses this email alongside the DEHASHED_API_KEY for HTTP Basic Authentication to query email addresses, usernames, passwords, and IPs in breach databases.",
        "pricing": "Dehashed offers paid plans starting at $3.99/day for basic access (100 queries). Monthly subscriptions from $15.99/month (1,000 queries) to $39.99/month (5,000 queries). No free tier available. Enterprise plans available for high-volume breach data access.",
        "url": "https://dehashed.com",
        "docs": "https://dehashed.com/docs/api",
        "test_url": "https://api.dehashed.com/account",
        "test_headers": None,
        "howto": "1. Register an account at dehashed.com 2. Purchase a subscription plan 3. Go to your account dashboard 4. Your registered email is used as the credential username 5. Enter your Dehashed account email in this field 6. Enter your Dehashed API key in the DEHASHED_API_KEY field",
        "ratelimit": "Varies by plan: daily query limits from 100 to unlimited queries depending on subscription tier",
        "related": "DEHASHED_API_KEY, LEAKCHECK_API_KEY, HIBP_API_KEY",
    },
}

SERVICE_CATEGORIES = ["AI", "Google", "Voice", "Media", "OSINT", "Development", "Integration"]

API_KEYS_ORDER = [
    "GOOGLE_API_KEY",
    "NVIDIA_VISION_API_KEY", "NVIDIA_NIM_API_KEY",
    "OPENCODE_ZEN_API_KEY",
    "GROQ_API_KEY", "SARVAM_API_KEY", "PICOVOICE_ACCESS_KEY",
    "SHODAN_API_KEY", "CENSYS_API_ID", "CENSYS_API_SECRET",
    "VIRUSTOTAL_API_KEY", "HUNTER_API_KEY", "CLEARBIT_API_KEY",
    "HIBP_API_KEY", "DEHASHED_API_KEY", "INTELX_API_KEY",
    "OTX_API_KEY", "LEAKCHECK_API_KEY",
    "ABUSEIPDB_API_KEY", "IPINFO_API_KEY", "URLSCAN_API_KEY",
    "BUILTWITH_API_KEY", "SECURITYTRAILS_API_KEY", "WHATCMS_API_KEY",
    "FULLCONTACT_API_KEY",
    "GITLAB_TOKEN", "OPENCAGE_API_KEY", "FLICKR_API_KEY", "DISCOGS_TOKEN",
]

# ── Service Credential Cards (multi-input, OAuth-capable) ────────────────
# Each service has: id, name, logo, fields (inputs), redirect_uri (shown to user),
# oauth (bool), connected_check (how to detect connected state)

SERVICES = [
    {
        "id": "google",
        "name": "Google",
        "logo": f"{SIMPLEICONS}/google/4285F4",
        "color": "#4285F4",
        "desc": "OAuth credentials for Google services (Gmail, Calendar, Drive, Docs, Sheets, Slides, YouTube, etc.). Get these from Google Cloud Console > APIs & Services > Credentials.",
        "fields": [
            {"key": "GOOGLE_CLIENT_ID", "label": "Client ID", "type": "text"},
            {"key": "GOOGLE_CLIENT_SECRET", "label": "Client Secret", "type": "password"},
        ],
        "redirect_uri": "http://127.0.0.1:7071/settings/google/callback",
        "oauth": True,
        "oauth_url": "/settings/google/auth",
        "revoke_url": "/settings/google/revoke",
        "status_url": "/settings/google/status",
        "connected_check": "has_creds",
    },
    {
        "id": "github",
        "name": "GitHub",
        "logo": f"{SIMPLEICONS}/github/FFFFFF",
        "color": "#FFFFFF",
        "desc": "OAuth credentials for GitHub API access (repos, issues, PRs, workflows, orgs). Register an OAuth App at GitHub Settings > Developer Settings > OAuth Apps.",
        "fields": [
            {"key": "GITHUB_CLIENT_ID", "label": "Client ID", "type": "text"},
            {"key": "GITHUB_CLIENT_SECRET", "label": "Client Secret", "type": "password"},
        ],
        "redirect_uri": "http://127.0.0.1:7071/settings/github/callback",
        "oauth": True,
        "oauth_url": "/settings/github/auth",
        "revoke_url": "/settings/github/revoke",
        "status_url": "/settings/github/status",
        "connected_check": "has_token",
    },
    {
        "id": "spotify",
        "name": "Spotify",
        "logo": f"{SIMPLEICONS}/spotify/1DB954",
        "color": "#1DB954",
        "desc": "Spotify API credentials for music playback control. Register at Spotify Developer Dashboard, then add the redirect URI below to your app settings.",
        "fields": [
            {"key": "SPOTIFY_CLIENT_ID", "label": "Client ID", "type": "text"},
            {"key": "SPOTIFY_CLIENT_SECRET", "label": "Client Secret", "type": "password"},
        ],
        "redirect_uri": "http://127.0.0.1:8888/callback",
        "oauth": False,
        "connected_check": "both",
    },
    {
        "id": "reddit",
        "name": "Reddit",
        "logo": f"{SIMPLEICONS}/reddit/FF4500",
        "color": "#FF4500",
        "desc": "Reddit API credentials for reading posts, comments, and subreddit data. Create an app at Reddit App Preferences > Apps > Create App.",
        "fields": [
            {"key": "REDDIT_CLIENT_ID", "label": "Client ID", "type": "text"},
            {"key": "REDDIT_CLIENT_SECRET", "label": "Client Secret", "type": "password"},
        ],
        "redirect_uri": "http://127.0.0.1:8000/reddit_callback",
        "oauth": False,
        "connected_check": "both",
    },
    {
        "id": "twitter",
        "name": "Twitter / X",
        "logo": f"{SIMPLEICONS}/x/FFFFFF",
        "color": "#FFFFFF",
        "desc": "Twitter API credentials for posting tweets, reading timelines, and searching content. Get these from the Twitter Developer Portal > Projects & Apps.",
        "fields": [
            {"key": "TWITTER_BEARER_TOKEN", "label": "Bearer Token", "type": "password"},
            {"key": "TWITTER_API_KEY", "label": "API Key", "type": "text"},
            {"key": "TWITTER_API_SECRET", "label": "API Secret", "type": "password"},
        ],
        "redirect_uri": None,
        "oauth": False,
        "connected_check": "any",
    },
    {
        "id": "telegram",
        "name": "Telegram",
        "logo": f"{FAVICON.format(domain='telegram.org')}",
        "color": "#0088CC",
        "desc": "Telegram API credentials for reading channels and messages. Get API ID and Hash at my.telegram.org > API Development Tools.",
        "fields": [
            {"key": "TELEGRAM_API_ID", "label": "API ID", "type": "text"},
            {"key": "TELEGRAM_API_HASH", "label": "API Hash", "type": "password"},
        ],
        "redirect_uri": None,
        "oauth": False,
        "connected_check": "both",
    },
    {
        "id": "instagram",
        "name": "Instagram",
        "logo": f"{SIMPLEICONS}/instagram/E4405F",
        "color": "#E4405F",
        "desc": "Instagram credentials for profile access and content monitoring. Used for OSINT data collection. Note: Basic Display API requires Facebook Login setup.",
        "fields": [
            {"key": "INSTAGRAM_USER", "label": "Username", "type": "text"},
            {"key": "INSTAGRAM_PASS", "label": "Password", "type": "password"},
        ],
        "redirect_uri": None,
        "oauth": False,
        "connected_check": "both",
    },
    {
        "id": "discord",
        "name": "Discord",
        "logo": f"{SIMPLEICONS}/discord/5865F2",
        "color": "#5865F2",
        "desc": "Discord bot token for server management, message reading, and community interaction. Create a bot at Discord Developer Portal, then copy the token. Optionally set guild/channel IDs for auto-join or announcements.",
        "fields": [
            {"key": "DISCORD_BOT_TOKEN", "label": "Bot Token", "type": "password"},
            {"key": "DISCORD_GUILD_ID", "label": "Guild ID (optional)", "type": "text"},
            {"key": "DISCORD_CHANNEL_ID", "label": "Default Channel ID (optional)", "type": "text"},
            {"key": "DISCORD_ANNOUNCE_CHANNEL", "label": "Announcement Channel ID (optional)", "type": "text"},
            {"key": "DISCORD_LOG_CHANNEL", "label": "Log Channel ID (optional)", "type": "text"},
        ],
        "redirect_uri": None,
        "oauth": False,
        "connected_check": "present",
    },
]

# ── Google Services with ALL OAuth scopes and detailed features ───────────

GOOGLE_SERVICES = [
    {"id": "gmail", "name": "Gmail", "color": "#EA4335",
     "desc": "Read, manage, and compose emails. Search inboxes, apply labels, organize conversations, and analyze email content with AI. FRIDAY can read your emails, draft responses, search for specific messages, manage labels and filters, and extract information from email threads for analysis.",
     "features": "Read emails and threads, search inbox with Gmail search syntax, manage labels (create/apply/remove), draft and send emails, manage filters, automatic email classification, attachment analysis, extract contacts from emails",
     "scopes": [
         "https://www.googleapis.com/auth/gmail.readonly",
         "https://www.googleapis.com/auth/gmail.modify",
         "https://www.googleapis.com/auth/gmail.compose",
         "https://www.googleapis.com/auth/gmail.send",
         "https://www.googleapis.com/auth/gmail.labels",
         "https://www.googleapis.com/auth/gmail.metadata",
     ]},
    {"id": "calendar", "name": "Google Calendar", "color": "#4285F4",
     "desc": "Read, create, and manage calendar events and schedules. Check availability, set reminders, and organize your time. FRIDAY can create events, check your schedule, find free time slots, manage reminders and notifications, and share event details with you.",
     "features": "List and query events by date range, create events with attendees, update and cancel events, check free/busy schedules, manage reminders (email, popup), manage calendars, set event colors and visibility",
     "scopes": [
         "https://www.googleapis.com/auth/calendar",
         "https://www.googleapis.com/auth/calendar.events",
         "https://www.googleapis.com/auth/calendar.readonly",
         "https://www.googleapis.com/auth/calendar.settings.readonly",
     ]},
    {"id": "drive", "name": "Google Drive", "color": "#FBBC04",
     "desc": "Access, search, and manage files and folders in Google Drive. Read documents, spreadsheets, presentations, and other file types. FRIDAY can search your Drive, read file contents, manage folders, download files for analysis, and organize your cloud storage.",
     "features": "Search files by name/content/type, read file contents (text, PDF, images), manage folders (create/move/rename), upload files, download files, view file metadata (size, owner, dates), manage sharing permissions, full-text search within documents",
     "scopes": [
         "https://www.googleapis.com/auth/drive.readonly",
         "https://www.googleapis.com/auth/drive.file",
         "https://www.googleapis.com/auth/drive.metadata.readonly",
         "https://www.googleapis.com/auth/drive.appdata",
         "https://www.googleapis.com/auth/drive",
     ]},
    {"id": "youtube", "name": "YouTube", "color": "#FF0000",
     "desc": "Search videos, retrieve channel information, manage playlists, and analyze video content. FRIDAY can find videos by keyword, get channel statistics, manage your playlists, fetch video captions and transcripts, and analyze video metadata.",
     "features": "Search videos with filters (duration, quality, date), get video details and statistics, retrieve captions and transcripts, manage playlists (create/add/remove), get channel information and analytics, search channels, get trending videos, manage video comments",
     "scopes": [
         "https://www.googleapis.com/auth/youtube.readonly",
         "https://www.googleapis.com/auth/youtube.upload",
         "https://www.googleapis.com/auth/youtube",
         "https://www.googleapis.com/auth/youtube.force-ssl",
         "https://www.googleapis.com/auth/youtubepartner",
     ]},
    {"id": "photos", "name": "Google Photos", "color": "#FF6F00",
     "desc": "Access your Google Photos library including photos, albums, and media metadata. FRIDAY can search for photos by content, create albums, retrieve image metadata (date taken, location, camera info), and download media files for analysis.",
     "features": "Browse albums and media items, search photos by content (AI-powered), retrieve image metadata (EXIF, location, dates), create and manage albums, upload photos, share media, face grouping information",
     "scopes": [
         "https://www.googleapis.com/auth/photoslibrary.readonly",
         "https://www.googleapis.com/auth/photoslibrary",
         "https://www.googleapis.com/auth/photoslibrary.sharing",
     ]},
    {"id": "docs", "name": "Google Docs", "color": "#4285F4",
     "desc": "Read and edit Google Docs documents. Access document content, formatting, comments, and revision history. FRIDAY can open documents, extract text content, read and add comments, and export documents in various formats.",
     "features": "Read document content and formatting, extract text with formatting, read and add comments, access revision history, suggest edits, export to PDF/HTML/TXT, manage document metadata",
     "scopes": [
         "https://www.googleapis.com/auth/documents.readonly",
         "https://www.googleapis.com/auth/documents",
     ]},
    {"id": "sheets", "name": "Google Sheets", "color": "#0F9D58",
     "desc": "Read and edit Google Sheets spreadsheets. Query cell data, analyze formulas, and manipulate rows and columns. FRIDAY can read spreadsheet data, write values to cells, apply formatting, create charts, and perform data analysis on sheet contents.",
     "features": "Read cell values and ranges, write data to cells, apply formatting (colors, fonts, borders), manage sheets and rows, sort and filter data, create charts, apply formulas, import/export CSV",
     "scopes": [
         "https://www.googleapis.com/auth/spreadsheets.readonly",
         "https://www.googleapis.com/auth/spreadsheets",
     ]},
    {"id": "slides", "name": "Google Slides", "color": "#FBBC04",
     "desc": "Read and edit Google Slides presentations. Access slide content, speaker notes, and visual elements. FRIDAY can extract text and images from slides, create presentations, edit existing slides, and add speaker notes.",
     "features": "Read slide content and layout, extract text and images from slides, access speaker notes, create presentations, add/edit/delete slides, manage slide elements (text boxes, images, shapes), export to PDF",
     "scopes": [
         "https://www.googleapis.com/auth/presentations.readonly",
         "https://www.googleapis.com/auth/presentations",
     ]},
    {"id": "tasks", "name": "Google Tasks", "color": "#4285F4",
     "desc": "Read and manage Google Tasks lists and individual tasks. Create reminders, set due dates, and organize tasks by list. FRIDAY can help you manage your to-do list, create new tasks from conversations, set deadlines, and track completion.",
     "features": "List all task lists, create/update/delete tasks, set due dates and reminders, mark tasks complete, reorder tasks, manage subtasks",
     "scopes": [
         "https://www.googleapis.com/auth/tasks",
         "https://www.googleapis.com/auth/tasks.readonly",
     ]},
    {"id": "contacts", "name": "Google Contacts", "color": "#34A853",
     "desc": "Read and manage Google Contacts. Access contact information including phone numbers, emails, addresses, and groups. FRIDAY can search contacts, retrieve contact details, manage contact groups, and create new contacts.",
     "features": "Search contacts by name/email/phone, retrieve contact details (phones, emails, addresses), manage contact groups, create and update contacts, merge duplicate contacts, export contacts",
     "scopes": [
         "https://www.googleapis.com/auth/contacts.readonly",
         "https://www.googleapis.com/auth/contacts",
     ]},
    {"id": "people", "name": "Google People API", "color": "#4285F4",
     "desc": "Access Google People API for user profiles, contacts, and connection management. Provides unified access to profile data and connections across Google services. FRIDAY can retrieve user profiles, manage circles, and access aggregated contact data.",
     "features": "Get user profile (name, photo, emails, phone numbers), list connections, manage circles and groups, search people, access profile fields across services",
     "scopes": [
         "https://www.googleapis.com/auth/contacts.readonly",
         "https://www.googleapis.com/auth/contacts",
         "https://www.googleapis.com/auth/user.phonenumbers.readonly",
         "https://www.googleapis.com/auth/userinfo.email",
         "https://www.googleapis.com/auth/userinfo.profile",
     ]},
    {"id": "cloud", "name": "Google Cloud Console", "color": "#4285F4",
     "desc": "Access Google Cloud Platform resources and services. Manage compute instances, storage buckets, databases, IAM policies, and more. FRIDAY can manage cloud infrastructure, deploy resources, monitor costs, and analyze logs.",
     "features": "List and manage Compute Engine instances, access Cloud Storage buckets and objects, query Cloud SQL databases, manage IAM roles and permissions, view billing and cost data, access Cloud Logging and Monitoring, manage Kubernetes clusters",
     "scopes": [
         "https://www.googleapis.com/auth/cloud-platform",
         "https://www.googleapis.com/auth/cloud-platform.read-only",
         "https://www.googleapis.com/auth/cloud-platform.userinfo.email",
         "https://www.googleapis.com/auth/devstorage.read_only",
         "https://www.googleapis.com/auth/bigquery",
     ]},
    {"id": "maps", "name": "Google Maps", "color": "#34A853",
     "desc": "Access Google Maps APIs for location-based services. Perform geocoding, reverse geocoding, directions, place searches, and distance calculations. FRIDAY can convert addresses to coordinates, find nearby places, calculate routes, and get travel times.",
     "features": "Forward geocoding (address to coordinates), reverse geocoding (coordinates to address), place search and details, directions with multiple modes (driving, walking, transit), distance matrix calculations, elevation data, timezone lookups",
     "scopes": [
         "https://www.googleapis.com/auth/maps",
         "https://www.googleapis.com/auth/places",
     ]},
    {"id": "classroom", "name": "Google Classroom", "color": "#1A73E8",
     "desc": "Access Google Classroom courses, assignments, and student work. FRIDAY can list courses, view assignments and submissions, access course materials, and track student progress.",
     "features": "List and manage courses, view assignments and due dates, access student submissions, read course materials and resources, view announcements, track grades and feedback",
     "scopes": [
         "https://www.googleapis.com/auth/classroom.courses.readonly",
         "https://www.googleapis.com/auth/classroom.courses",
         "https://www.googleapis.com/auth/classroom.coursework.readonly",
         "https://www.googleapis.com/auth/classroom.coursework.me",
     ]},
    {"id": "analytics", "name": "Google Analytics", "color": "#E37400",
     "desc": "Access Google Analytics data for website and app analytics. Retrieve traffic statistics, user behavior metrics, conversion data, and custom reports. FRIDAY can analyze website performance, track user engagement, and generate analytics reports.",
     "features": "Retrieve analytics reports (visitors, pageviews, bounce rate), analyze user behavior (sessions, time on page), track conversions and goals, access real-time analytics data, generate custom reports, export data to spreadsheets",
     "scopes": [
         "https://www.googleapis.com/auth/analytics.readonly",
         "https://www.googleapis.com/auth/analytics",
         "https://www.googleapis.com/auth/analytics.manage.users.readonly",
     ]},
    {"id": "ads", "name": "Google Ads", "color": "#4285F4",
     "desc": "Access Google Ads data for advertising campaign management. View campaign performance, manage ad groups and keywords, analyze metrics. FRIDAY can help optimize advertising campaigns, analyze performance data, and suggest improvements.",
     "features": "View campaign performance and metrics, manage ad groups and creatives, analyze keyword performance, track conversions and ROI, manage budgets and bids, generate performance reports",
     "scopes": [
         "https://www.googleapis.com/auth/adwords",
     ]},
]

# ── Service Categories ────────────────────────────────────────────────────

GOOGLE_SERVICE_CATEGORIES = [
    {
        "id": "workspace",
        "name": "Google Workspace",
        "color": "#4285F4",
        "icon": "googleworkspace",
        "desc": "Full access to Google's core productivity suite — email, calendar, documents, spreadsheets, presentations, tasks, and cloud storage.",
        "features": "FRIDAY can manage your entire workflow across Gmail, Calendar, Drive, Docs, Sheets, Slides, and Tasks. Draft and send emails, schedule events and check availability, search and organize files, create and edit documents, analyze spreadsheet data, build presentations, and manage to-do lists — all through natural conversation.",
        "service_ids": ["gmail", "calendar", "drive", "docs", "sheets", "slides", "tasks"],
    },
    {
        "id": "people_identity",
        "name": "People & Identity",
        "color": "#34A853",
        "icon": "googlecontacts",
        "desc": "Manage contacts, user profiles, and people connections across Google services.",
        "features": "FRIDAY can search and manage your contacts, retrieve detailed user profile information, organize contact groups and circles, create new contacts from conversations, merge duplicates, and access aggregated people data across all Google services.",
        "service_ids": ["contacts", "people"],
    },
    {
        "id": "media_content",
        "name": "Media & Content",
        "color": "#FF0000",
        "icon": "googlephotos",
        "desc": "Access and manage your media library across YouTube and Google Photos.",
        "features": "FRIDAY can search YouTube videos with advanced filters, retrieve captions and transcripts, manage playlists and channel subscriptions, browse Google Photos albums, search photos by content using AI, retrieve EXIF metadata, create albums, and download media for analysis.",
        "service_ids": ["youtube", "photos"],
    },
    {
        "id": "cloud_platform",
        "name": "Cloud Platform",
        "color": "#4285F4",
        "icon": "googlecloud",
        "desc": "Manage Google Cloud Platform resources including compute, storage, databases, and IAM.",
        "features": "FRIDAY can manage Compute Engine instances, access Cloud Storage buckets and objects, query BigQuery and Cloud SQL databases, configure IAM roles and permissions, monitor cloud costs and billing, view logs and metrics, and administer Kubernetes clusters — all from natural language commands.",
        "service_ids": ["cloud"],
    },
    {
        "id": "maps_places",
        "name": "Maps & Places",
        "color": "#34A853",
        "icon": "googlemaps",
        "desc": "Location-based services including geocoding, directions, place search, and distance calculations.",
        "features": "FRIDAY can convert addresses to coordinates and vice versa, search for places and get detailed information, calculate routes with multiple travel modes, compute travel distances and times, look up elevation data and timezones, and find nearby points of interest.",
        "service_ids": ["maps"],
    },
    {
        "id": "education",
        "name": "Education",
        "color": "#1A73E8",
        "icon": "googleclassroom",
        "desc": "Access Google Classroom courses, assignments, submissions, and student progress tracking.",
        "features": "FRIDAY can list and navigate your courses, view assignments and upcoming due dates, access student submissions and provide feedback, retrieve course materials and announcements, track grades and performance metrics, and help manage the full classroom workflow.",
        "service_ids": ["classroom"],
    },
    {
        "id": "marketing_ads",
        "name": "Marketing & Ads",
        "color": "#E37400",
        "icon": "googleanalytics",
        "desc": "Analytics and advertising tools for measuring and optimizing business performance.",
        "features": "FRIDAY can analyze website traffic and user behavior from Google Analytics, track conversions and goal completions, generate custom performance reports, manage Google Ads campaigns, optimize keywords and ad groups, monitor budgets and bids, and provide actionable recommendations to improve ROI.",
        "service_ids": ["analytics", "ads"],
    },
]

CATEGORY_SERVICE_IDS = {
    "workspace": ["gmail", "calendar", "drive", "docs", "sheets", "slides", "tasks"],
    "people_identity": ["contacts", "people"],
    "media_content": ["youtube", "photos"],
    "cloud_platform": ["cloud"],
    "maps_places": ["maps"],
    "education": ["classroom"],
    "marketing_ads": ["analytics", "ads"],
}

SERVICE_CATEGORY_MAP = {}
for _cat_id, _svc_ids in CATEGORY_SERVICE_IDS.items():
    for _svc_id in _svc_ids:
        SERVICE_CATEGORY_MAP[_svc_id] = _cat_id

# ── Category-to-SCOPE_CATEGORIES mapping (bridges dashboard groups to google_oauth.py) ──
# Each dashboard GOOGLE_SERVICE_CATEGORY maps to one or more SCOPE_CATEGORY names
# from friday/google_oauth.py. This lets the "Connect" button on a dashboard
# category card call google_authorize_category() for the relevant scopes.

CATEGORY_TO_SCOPE_CATEGORIES = {
    "workspace": [
        "Gmail", "Calendar", "Drive", "Sheets", "Docs", "Slides", "Tasks", "Forms",
    ],
    "people_identity": [
        "People",
    ],
    "media_content": [
        "YouTube", "Photos", "Books",
    ],
    "cloud_platform": [
        "Cloud Platform", "BigQuery", "Cloud Storage",
        "Translation", "Natural Language", "Firebase",
    ],
    "maps_places": [],
    "education": [
        "Classroom",
    ],
    "marketing_ads": [
        "Analytics", "Search Console",
    ],
}

ALL_SCOPE_CATEGORIES_FLAT = []
for _scope_cats in CATEGORY_TO_SCOPE_CATEGORIES.values():
    ALL_SCOPE_CATEGORIES_FLAT.extend(_scope_cats)
ALL_SCOPE_CATEGORIES_FLAT = list(dict.fromkeys(ALL_SCOPE_CATEGORIES_FLAT))

# ── Helper Functions ──────────────────────────────────────────────────────

def _load_env() -> dict:
    """Load current .env file contents as a dictionary."""
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def _save_env(updates: dict) -> bool:
    """Update .env file with new key-value pairs, preserving existing content."""
    try:
        lines = []
        found = set()
        if ENV_PATH.exists():
            for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    k = stripped.split("=", 1)[0].strip()
                    if k in updates:
                        lines.append(f"{k}={updates[k]}")
                        found.add(k)
                    else:
                        lines.append(line)
                else:
                    lines.append(line)
        for k, v in updates.items():
            if k not in found:
                lines.append(f"{k}={v}")
        ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        for k, v in updates.items():
            os.environ[k] = v
        return True
    except Exception:
        return False


def _mask_key(val: str) -> str:
    """Mask API key showing only first and last 4 characters."""
    if not val or len(val) < 8:
        return val if val else ""
    return val[:4] + chr(42) * (len(val) - 8) + val[-4:]


router = APIRouter()


@router.get("/settings", response_class=HTMLResponse)
async def settings_page():
    return HTMLResponse(DASHBOARD_HTML)


@router.get("/settings/api/keys")
async def get_api_keys():
    env = _load_env()
    keys = []
    for ek in API_KEYS_ORDER:
        meta = API_KEY_META.get(ek, {})
        raw_val = env.get(ek, "")
        logo_info = API_LOGO.get(ek, {"src": "", "type": "favicon", "fallback": None, "domain": None})
        svg_fallback = BRAND_SVG.get(logo_info.get("fallback", ""), "") if logo_info.get("fallback") else ""
        keys.append({
            "key": ek, "name": meta.get("name", ek),
            "value": _mask_key(raw_val) if raw_val else "",
            "present": bool(raw_val), "category": meta.get("category", "Other"),
            "pricing": meta.get("pricing", ""), "description": meta.get("description", ""),
            "url": meta.get("url", ""), "docs": meta.get("docs", ""),
            "howto": meta.get("howto", ""), "ratelimit": meta.get("ratelimit", ""),
            "related": meta.get("related", ""),
            "logoSrc": logo_info.get("src", ""),
            "logoType": logo_info.get("type", "favicon"),
            "svgFallback": svg_fallback or "",
        })
    total = len(keys)
    connected = sum(1 for k in keys if k["present"])
    return JSONResponse({
        "keys": keys, "categories": SERVICE_CATEGORIES,
        "total": total, "connected": connected, "disconnected": total - connected,
    })


@router.post("/settings/api/keys")
async def update_api_key(req: Request):
    data = await req.json()
    key = data.get("key", "").strip()
    value = data.get("value", "").strip()
    if not key:
        return JSONResponse({"success": False, "error": "Key name is required"}, status_code=400)
    if not value:
        return JSONResponse({"success": False, "error": "Key value is required"}, status_code=400)
    ok = _save_env({key: value})
    if ok:
        _notify_friday("api_key_saved", key)
        meta = API_KEY_META.get(key, {})
        return JSONResponse({"success": True, "key": key, "name": meta.get("name", key),
            "value": _mask_key(value) if value else "", "present": bool(value)})
    return JSONResponse({"success": False, "error": "Failed to write .env file."}, status_code=500)


@router.post("/settings/api/keys/test")
async def test_api_key(req: Request):
    import httpx
    data = await req.json()
    key = data.get("key", "").strip()
    value = data.get("value", "").strip()
    if not key or not value:
        return JSONResponse({"success": False, "error": "Key and value required"}, status_code=400)
    meta = API_KEY_META.get(key)
    if not meta:
        return JSONResponse({"success": False, "error": "Unknown API key type."})
    test_url = meta.get("test_url")
    test_headers = meta.get("test_headers")
    if not test_url:
        name = meta.get("name", key)
        if key.endswith("_SECRET") or key.endswith("_CLIENT_SECRET"):
            return JSONResponse({"success": True, "message": f"{name} is a credential pair \u2014 verify via its client ID."})
        return JSONResponse({"success": True, "message": "No automated test available. Verify manually."})
    try:
        headers = {}
        if test_headers:
            for hk, hv in test_headers.items():
                headers[hk] = hv.replace("{key}", value)
        url = test_url.replace("{key}", value) if "{key}" in test_url else test_url
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers or None)
            if resp.status_code < 500:
                return JSONResponse({"success": True, "status": resp.status_code, "message": f"HTTP {resp.status_code}"})
            return JSONResponse({"success": False, "status": resp.status_code, "message": f"Error {resp.status_code}"})
    except httpx.ConnectError:
        return JSONResponse({"success": False, "message": "Connection failed."})
    except httpx.TimeoutException:
        return JSONResponse({"success": False, "message": "Request timed out."})
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)[:200]})


@router.get("/settings/services/status")
async def services_status():
    env = _load_env()
    from friday.google_oauth import credentials_exist as google_creds_exist
    result = []
    for sv in SERVICES:
        present = 0
        for f in sv["fields"]:
            if env.get(f["key"], ""):
                present += 1
        total = len(sv["fields"])
        d = {"id": sv["id"], "name": sv["name"], "logo": sv["logo"], "color": sv["color"],
             "desc": sv["desc"], "fields": sv["fields"],
             "redirect_uri": sv.get("redirect_uri"), "oauth": sv.get("oauth", False),
             "field_count": total, "filled": present}
        cc = sv.get("connected_check", "")
        if cc == "both":
            d["connected"] = present == total
        elif cc == "any":
            d["connected"] = present > 0
        elif cc == "present":
            d["connected"] = present == total
        elif cc == "has_creds":
            d["connected"] = google_creds_exist()
        elif cc == "has_token":
            d["connected"] = GITHUB_TOKEN_PATH.exists() and GITHUB_TOKEN_PATH.stat().st_size > 10
        else:
            d["connected"] = False
        result.append(d)
    total = len(result)
    connected = sum(1 for r in result if r["connected"])
    return JSONResponse({"services": result, "total": total, "connected": connected})


@router.get("/settings/google/status")
async def google_status():
    try:
        from friday.google_oauth import SCOPE_CATEGORIES, get_authorized_categories, list_categories, credentials_exist
        env = _load_env()
        cid = env.get("GOOGLE_CLIENT_ID", "")
        csecret = env.get("GOOGLE_CLIENT_SECRET", "")
        configured = bool(cid and csecret)
        has_creds = credentials_exist() if configured else False
        authd_cats = get_authorized_categories() if configured else []
        scope_cats_raw = list_categories()
        all_flat_categories = list(scope_cats_raw.keys())
        services = []
        for s in GOOGLE_SERVICES:
            svc_on = s["name"] in authd_cats
            services.append({
                "id": s["id"], "name": s["name"], "icon": GOOGLE_LOGO.get(s["id"], ""),
                "color": s["color"], "desc": s["desc"], "features": s.get("features", ""),
                "scopes": s["scopes"], "connected": svc_on,
            })
        categories = []
        for cat in GOOGLE_SERVICE_CATEGORIES:
            scope_names = CATEGORY_TO_SCOPE_CATEGORIES.get(cat["id"], [])
            connected_scopes = [s for s in scope_names if s in authd_cats]
            all_connected = len(connected_scopes) == len(scope_names) if scope_names else False
            cat_services = []
            for svc_id in cat["service_ids"]:
                svc_data = next((s for s in GOOGLE_SERVICES if s["id"] == svc_id), None)
                if svc_data:
                    cat_services.append({
                        "id": svc_data["id"], "name": svc_data["name"],
                        "icon": GOOGLE_LOGO.get(svc_data["id"], ""),
                        "color": svc_data["color"],
                    })
            categories.append({
                "id": cat["id"], "name": cat["name"], "color": cat["color"],
                "icon": cat.get("icon", ""), "desc": cat["desc"], "features": cat["features"],
                "service_ids": cat["service_ids"], "services": cat_services,
                "scope_categories": scope_names,
                "connected_scopes": connected_scopes,
                "scope_count": len(scope_names),
                "connected_scope_count": len(connected_scopes),
                "all_connected": all_connected,
                "partial": len(connected_scopes) > 0 and not all_connected,
            })
        scope_cats = []
        for name, scopes in SCOPE_CATEGORIES.items():
            scope_cats.append({
                "name": name, "scopes": scopes, "scope_count": len(scopes),
                "connected": name in authd_cats,
            })
        return JSONResponse({
            "configured": configured, "has_creds": has_creds,
            "client_id": _mask_key(cid) if cid else "",
            "authorized_categories": authd_cats,
            "services": services,
            "categories": categories,
            "scope_categories": scope_cats,
            "connected_count": sum(1 for s in services if s["connected"]),
            "total_services": len(services),
            "total_categories": len(categories),
            "total_scope_cats": len(scope_cats),
        })
    except ImportError:
        return JSONResponse({"error": "google_oauth module not available"}, status_code=500)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/settings/google/auth/{category}")
async def google_auth_category(category: str):
    try:
        from friday.google_oauth import get_scope_string, get_auth_url, SCOPE_CATEGORIES
    except ImportError:
        return HTMLResponse("<html><body style='background:#080c14;color:#e0e6f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h2>google_oauth module not available</h2><a href='/settings' style='color:#00e5ff'>\u2190 Back</a></div></body></html>")
    env = _load_env()
    cid = env.get("GOOGLE_CLIENT_ID", "")
    if not cid:
        return HTMLResponse("<html><body style='background:#080c14;color:#e0e6f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h2>Google Client ID not configured</h2><p>Set GOOGLE_CLIENT_ID in .env first.</p><a href='/settings' style='color:#00e5ff'>\u2190 Back</a></div></body></html>")
    if category not in SCOPE_CATEGORIES:
        return HTMLResponse(f"<html><body style='background:#080c14;color:#e0e6f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h2>Unknown category: {category}</h2><a href='/settings' style='color:#00e5ff'>\u2190 Back</a></div></body></html>")
    redirect_uri = "http://127.0.0.1:7071/settings/google/callback"
    scope_str = get_scope_string(category)
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={cid}&redirect_uri={redirect_uri}"
        "&response_type=code"
        f"&scope={scope_str}"
        "&access_type=offline&prompt=consent"
        "&include_granted_scopes=true"
        f"&state={category}"
    )
    return RedirectResponse(auth_url)


@router.get("/settings/google/auth")
async def google_auth_all():
    try:
        from friday.google_oauth import get_scope_string
    except ImportError:
        return HTMLResponse("<html><body style='background:#080c14;color:#e0e6f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h2>google_oauth module not available</h2><a href='/settings' style='color:#00e5ff'>\u2190 Back</a></div></body></html>")
    env = _load_env()
    cid = env.get("GOOGLE_CLIENT_ID", "")
    if not cid:
        return HTMLResponse("<html><body style='background:#080c14;color:#e0e6f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h2>Google Client ID not configured</h2><p>Set GOOGLE_CLIENT_ID in .env first.</p><a href='/settings' style='color:#00e5ff'>\u2190 Back</a></div></body></html>")
    redirect_uri = "http://127.0.0.1:7071/settings/google/callback"
    scope_str = get_scope_string(None)
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={cid}&redirect_uri={redirect_uri}"
        "&response_type=code"
        f"&scope={scope_str}"
        "&access_type=offline&prompt=consent"
        "&include_granted_scopes=true"
    )
    return RedirectResponse(auth_url)


@router.get("/settings/google/callback")
async def google_callback(code: str = "", error: str = "", state: str = ""):
    if error:
        return HTMLResponse(f"<html><body style='background:#080c14;color:#e0e6f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h2>Auth Error</h2><p>{error}</p><a href='/settings' style='color:#00e5ff'>\u2190 Back</a></div></body></html>")
    if not code:
        return HTMLResponse("<html><body style='background:#080c14;color:#e0e6f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h2>No auth code</h2><a href='/settings' style='color:#00e5ff'>\u2190 Back</a></div></body></html>")
    try:
        from friday.google_oauth import save_token_data
        env = _load_env()
        cid = env.get("GOOGLE_CLIENT_ID", "")
        csecret = env.get("GOOGLE_CLIENT_SECRET", "")
        redirect_uri = "http://127.0.0.1:7071/settings/google/callback"
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post("https://oauth2.googleapis.com/token", data={
                "code": code, "client_id": cid, "client_secret": csecret,
                "redirect_uri": redirect_uri, "grant_type": "authorization_code",
            }, headers={"Content-Type": "application/x-www-form-urlencoded"})
            if resp.status_code != 200:
                return HTMLResponse(f"<html><body style='background:#080c14;color:#e0e6f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h2>Token exchange failed</h2><p>{resp.text[:200]}</p><a href='/settings' style='color:#00e5ff'>\u2190 Back</a></div></body></html>")
            td = resp.json()
            category = state or None
            success = save_token_data(td, category=category)
        _notify_friday("oauth_connected", "google")
        return HTMLResponse("""<html><head><style>
body{background:#080c14;color:#e0e6f0;font-family:system-ui,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
.c{background:rgba(255,255,255,0.04);border:1px solid rgba(0,229,255,0.2);border-radius:16px;padding:48px;text-align:center;max-width:440px}
h1{font-size:28px;margin:0 0 12px;background:linear-gradient(135deg,#00e5ff,#76ff03);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
p{color:#6b7a99;font-size:14px;margin:0 0 24px}
a{display:inline-block;padding:12px 32px;background:#00e5ff;color:#080c14;text-decoration:none;border-radius:8px;font-weight:600}
.check{font-size:48px;margin-bottom:16px}
</style></head><body><div class="c"><div class="check">\\u2705</div><h1>Google Connected!</h1><p>Your Google account is linked.</p><a href="/settings">\\u2190 Back to Dashboard</a></div></body></html>""")
    except ImportError:
        return HTMLResponse("<html><body style='background:#080c14;color:#e0e6f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h2>google_oauth module not available</h2><a href='/settings' style='color:#00e5ff'>\u2190 Back</a></div></body></html>")
    except Exception as e:
        return HTMLResponse(f"<html><body style='background:#080c14;color:#e0e6f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h2>OAuth Error</h2><p>{str(e)}</p><a href='/settings' style='color:#00e5ff'>\\u2190 Back</a></div></body></html>")


@router.post("/settings/google/revoke")
async def google_revoke():
    try:
        from friday.google_oauth import _CREDENTIALS_PATH as creds_path
    except ImportError:
        creds_path = Path(__file__).resolve().parent.parent / ".google_credentials.json"
    if creds_path.exists():
        try:
            creds_path.unlink()
            _notify_friday("oauth_revoked", "google")
            return JSONResponse({"success": True, "message": "Credentials revoked."})
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)
    return JSONResponse({"success": True, "message": "No credentials found."})


# ── GitHub OAuth ──

GITHUB_TOKEN_PATH = Path(__file__).resolve().parent.parent / ".github_token.json"


@router.get("/settings/github/status")
async def github_status():
    env = _load_env()
    from friday.github import _GITHUB_CLIENT_ID as GH_DEFAULT_CID
    cid = env.get("GITHUB_CLIENT_ID", GH_DEFAULT_CID)
    csecret = env.get("GITHUB_CLIENT_SECRET", "")
    configured = bool(cid)
    token = ""
    if GITHUB_TOKEN_PATH.exists():
        try:
            token = json.loads(GITHUB_TOKEN_PATH.read_text()).get("access_token", "")
        except Exception:
            pass
    return JSONResponse({
        "configured": configured,
        "client_id": _mask_key(cid) if cid != GH_DEFAULT_CID else "(default public app)",
        "has_token": bool(token),
        "user": "",
    })


@router.get("/settings/github/auth")
async def github_auth():
    env = _load_env()
    from friday.github import _GITHUB_CLIENT_ID as GH_DEFAULT_CID
    cid = env.get("GITHUB_CLIENT_ID", GH_DEFAULT_CID)
    if not cid:
        return HTMLResponse("<html><body style='background:#080c14;color:#e0e6f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h2>GitHub Client ID not configured</h2><p>No default or configured client ID found.</p><a href='/settings' style='color:#00e5ff'>&#x2190; Back</a></div></body></html>")
    # Device flow — no client secret needed
    import httpx, time
    async with httpx.AsyncClient(timeout=15) as client:
        payload = {"client_id": cid, "scope": "repo workflow admin:org"}
        resp = await client.post("https://github.com/login/device/code", data=payload, headers={"Accept": "application/json"})
        data = resp.json()
    if "device_code" not in data:
        return HTMLResponse(f"<html><body style='background:#080c14;color:#e0e6f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h2>Device Flow Error</h2><p>{data.get('error_description','Could not get device code')}</p><a href='/settings' style='color:#00e5ff'>&#x2190; Back</a></div></body></html>")
    device_code = data["device_code"]
    user_code = data["user_code"]
    interval = data.get("interval", 5)
    page = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>GitHub Device Auth — FRIDAY</title>
<style>
*{box-sizing:border-box}
body{background:#080c14;color:#e0e6f0;font-family:system-ui,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;padding:20px}
.card{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:40px;text-align:center;max-width:480px;width:100%}
h1{font-size:24px;margin:0 0 8px}
p{color:#6b7a99;font-size:14px;margin:0 0 24px;line-height:1.6}
.code{display:inline-block;font-size:32px;font-weight:700;letter-spacing:8px;padding:16px 32px;background:rgba(255,255,255,0.06);border:2px dashed rgba(0,229,255,0.3);border-radius:12px;color:#00e5ff;font-family:monospace;margin:16px 0;cursor:pointer;transition:background 0.2s;user-select:all}
.code:hover{background:rgba(0,229,255,0.08)}
.btn{display:inline-block;padding:12px 32px;background:#00e5ff;color:#080c14;text-decoration:none;border-radius:8px;font-weight:600;border:none;cursor:pointer;font-size:14px}
.btn:hover{background:#00c4dd}
.btn:disabled{opacity:0.5;cursor:not-allowed}
#status{margin-top:20px;font-size:13px;color:#6b7a99}
.spinner{display:inline-block;width:14px;height:14px;border:2px solid rgba(0,229,255,0.3);border-top-color:#00e5ff;border-radius:50%;animation:spin .8s linear infinite;vertical-align:middle;margin-right:6px}
@keyframes spin{to{transform:rotate(360deg)}}
#toast{position:fixed;bottom:30px;left:50%;transform:translateX(-50%);background:#1a2332;color:#e0e6f0;padding:12px 24px;border-radius:10px;border:1px solid rgba(0,229,255,0.2);font-size:13px;opacity:0;transition:opacity 0.3s;pointer-events:none;z-index:999}
#toast.show{opacity:1}
a{color:#00e5ff}
</style></head><body>
<div id="toast"></div>
<div class="card">
<h1>&#x1f454; GitHub Device Auth</h1>
<p>Using the <strong>default public app</strong>.<br>Your code has been copied &mdash; paste it at the GitHub page that just opened.</p>
<div class="code" id="codeEl">__USER_CODE__</div>
<p style="margin:4px 0 16px;font-size:12px;color:#4a5a7a">Click the code above to copy again</p>
<div id="status"><span class="spinner"></span>Waiting for authorization... (auto-checks every __INTERVAL__s)</div>
<p style="margin-top:20px;font-size:12px;color:#4a5a7a">After authorizing, this page will auto-redirect to your dashboard.</p>
</div>
<script>
var dc="__DEVICE_CODE__",iv=__INTERVAL__;
function toast(m){var t=document.getElementById('toast');t.textContent=m;t.className='show';setTimeout(function(){t.className=''},2500)}
function copyCode(){var el=document.getElementById('codeEl'),t=el.textContent.trim();navigator.clipboard.writeText(t).then(function(){toast('\\u2705 PIN copied to clipboard')}).catch(function(){var r=document.createRange();r.selectNode(el);window.getSelection().removeAllRanges();window.getSelection().addRange(r);document.execCommand('copy');window.getSelection().removeAllRanges();toast('\\u2705 PIN copied to clipboard')})}
copyCode();var w=window.open('https://github.com/login/device');if(!w){document.getElementById('status').innerHTML='\\u26a0 Popup blocked. <a href="https://github.com/login/device" target="_blank" style="color:#00e5ff">Click here</a>'}
function poll(){var x=new XMLHttpRequest();x.open('POST','/settings/github/device/poll',true);x.setRequestHeader('Content-Type','application/json');x.onload=function(){if(x.status===200){try{var d=JSON.parse(x.responseText);if(d.success){document.getElementById('status').innerHTML='\\u2705 Authorized! Redirecting...';setTimeout(function(){window.location.href='/settings'},1500)}else if(d.error==='authorization_pending'){var s=document.getElementById('status');s.innerHTML='<span class=\"spinner\"></span>Still waiting...';setTimeout(poll,iv*1000)}else if(d.error==='access_denied'){document.getElementById('status').innerHTML='\\u274c Authorization denied. <a href=\"/settings/github/auth\" style=\"color:#00e5ff\">Try again</a>'}else{document.getElementById('status').innerHTML='\\u23f3 '+d.error;setTimeout(poll,iv*1000)}}}catch(e){setTimeout(poll,5000)}};x.onerror=function(){setTimeout(poll,5000)};x.send(JSON.stringify({device_code:dc}))}
setTimeout(poll,iv*1000);
document.getElementById('codeEl').onclick=copyCode;
</script></body></html>"""
    page = page.replace("__USER_CODE__", user_code).replace("__DEVICE_CODE__", device_code).replace("__INTERVAL__", str(interval))
    return HTMLResponse(page)


@router.post("/settings/github/device/poll")
async def github_device_poll(data: dict):
    from friday.github import _GITHUB_CLIENT_ID as GH_DEFAULT_CID
    dc = data.get("device_code", "")
    if not dc:
        return JSONResponse({"error": "no device_code"}, status_code=400)
    env = _load_env()
    cid = env.get("GITHUB_CLIENT_ID", GH_DEFAULT_CID)
    import httpx
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post("https://github.com/login/oauth/access_token", data={
            "client_id": cid, "device_code": dc,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }, headers={"Accept": "application/json"})
        result = resp.json()
    if "access_token" in result:
        GITHUB_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        import time
        saved = {"access_token": result["access_token"], "token_type": result.get("token_type", "bearer"),
                 "scope": result.get("scope", ""), "created_at": time.time()}
        GITHUB_TOKEN_PATH.write_text(json.dumps(saved, indent=2), encoding="utf-8")
        _notify_friday("oauth_connected", "github")
        return JSONResponse({"success": True})
    error = result.get("error", "unknown")
    return JSONResponse({"error": error})


@router.get("/settings/github/callback")
async def github_callback(code: str = "", error: str = ""):
    from friday.github import _GITHUB_CLIENT_ID as GH_DEFAULT_CID
    if error:
        return HTMLResponse(f"<html><body style='background:#080c14;color:#e0e6f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h2>GitHub Auth Error</h2><p>{error}</p><a href='/settings' style='color:#00e5ff'>&#x2190; Back</a></div></body></html>")
    if not code:
        return HTMLResponse("<html><body style='background:#080c14;color:#e0e6f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h2>No auth code</h2><a href='/settings' style='color:#00e5ff'>&#x2190; Back</a></div></body></html>")
    try:
        env = _load_env()
        cid = env.get("GITHUB_CLIENT_ID", GH_DEFAULT_CID)
        csecret = env.get("GITHUB_CLIENT_SECRET", "")
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post("https://github.com/login/oauth/access_token", data={
                "client_id": cid, "client_secret": csecret, "code": code,
                "redirect_uri": "http://127.0.0.1:7071/settings/github/callback",
            }, headers={"Accept": "application/json"})
            if resp.status_code != 200:
                return HTMLResponse(f"<html><body style='background:#080c14;color:#e0e6f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h2>GitHub token exchange failed</h2><p>{resp.text[:200]}</p><a href='/settings' style='color:#00e5ff'>&#x2190; Back</a></div></body></html>")
            td = resp.json()
            GITHUB_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
            GITHUB_TOKEN_PATH.write_text(json.dumps(td, indent=2), encoding="utf-8")
        return HTMLResponse("""<html><head><style>
body{background:#080c14;color:#e0e6f0;font-family:system-ui,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
.c{background:rgba(255,255,255,0.04);border:1px solid rgba(0,229,255,0.2);border-radius:16px;padding:48px;text-align:center;max-width:440px}
h1{font-size:28px;margin:0 0 12px;background:linear-gradient(135deg,#00e5ff,#76ff03);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
p{color:#6b7a99;font-size:14px;margin:0 0 24px}
a{display:inline-block;padding:12px 32px;background:#00e5ff;color:#080c14;text-decoration:none;border-radius:8px;font-weight:600}
.check{font-size:48px;margin-bottom:16px}
</style></head><body><div class="c"><div class="check">&#x2705;</div><h1>GitHub Connected!</h1><p>Your GitHub account is linked. FRIDAY can now access your repos.</p><a href="/settings">&#x2190; Back to Dashboard</a></div></body></html>""")
    except ImportError:
        return HTMLResponse("<html><body style='background:#080c14;color:#e0e6f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h2>httpx library required</h2><a href='/settings' style='color:#00e5ff'>&#x2190; Back</a></div></body></html>")
    except Exception as e:
        return HTMLResponse(f"<html><body style='background:#080c14;color:#e0e6f0;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h2>GitHub OAuth Error</h2><p>{str(e)}</p><a href='/settings' style='color:#00e5ff'>&#x2190; Back</a></div></body></html>")


@router.post("/settings/github/revoke")
async def github_revoke():
    if GITHUB_TOKEN_PATH.exists():
        try:
            GITHUB_TOKEN_PATH.unlink()
            _notify_friday("oauth_revoked", "github")
            return JSONResponse({"success": True, "message": "GitHub token revoked."})
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=500)
    return JSONResponse({"success": True, "message": "No GitHub token found."})


DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>FRIDAY Settings Dashboard</title>
<style>
:root{--bg:#080c14;--bg2:#0b1120;--surface:rgba(255,255,255,0.035);--surface-hover:rgba(255,255,255,0.06);--border:rgba(0,229,255,0.12);--border-active:rgba(0,229,255,0.4);--primary:#00e5ff;--primary-dim:rgba(0,229,255,0.1);--green:#00e676;--red:#ff1744;--yellow:#ffd600;--text:#e0e6f0;--text-dim:#6b7a99;--text-muted:#4a5568;--radius:12px;--radius-sm:8px;--shadow:0 8px 32px rgba(0,0,0,0.5);--panel-w:240px;--font:'Segoe UI',system-ui,-apple-system,sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--font);background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden}
::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--border-active);border-radius:3px}
::selection{background:var(--primary-dim);color:var(--primary)}
a{color:var(--primary);text-decoration:none}
a:hover{text-decoration:underline}
img{-webkit-user-drag:none;user-select:none}
.app-layout{display:flex;min-height:100vh}
.side-panel{width:var(--panel-w);background:rgba(8,12,20,0.96);border-right:1px solid var(--border);display:flex;flex-direction:column;position:fixed;top:0;left:0;height:100vh;z-index:200;transition:transform 0.3s cubic-bezier(0.4,0,0.2,1);backdrop-filter:blur(20px);overflow-y:auto}
.side-panel.closed{transform:translateX(-100%)}
.panel-header{display:flex;align-items:center;justify-content:space-between;padding:18px 16px 14px;border-bottom:1px solid var(--border)}
.panel-header h2{font-size:16px;font-weight:700;letter-spacing:-0.3px;background:linear-gradient(135deg,#00e5ff,#00b8d4);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.panel-toggle{background:none;border:none;color:var(--text-dim);font-size:18px;cursor:pointer;padding:4px 8px;border-radius:var(--radius-sm);transition:all 0.2s}
.panel-toggle:hover{background:var(--surface);color:var(--text)}
.panel-nav{flex:1;padding:12px 8px;display:flex;flex-direction:column;gap:3px}
.nav-item{display:flex;align-items:center;gap:10px;padding:10px 14px;border-radius:var(--radius-sm);text-decoration:none;color:var(--text-dim);font-size:13px;font-weight:500;transition:all 0.2s;cursor:pointer;position:relative;border:1px solid transparent}
.nav-item:hover{background:var(--surface);color:var(--text)}
.nav-item.active{background:var(--primary-dim);color:var(--primary);border-color:rgba(0,229,255,0.15)}
.nav-icon{font-size:18px;width:26px;text-align:center;display:flex;align-items:center;justify-content:center}
.nav-icon img{width:20px;height:20px;border-radius:4px}
.nav-label{flex:1}
.nav-badge{font-size:10px;padding:1px 8px;border-radius:10px;background:rgba(255,255,255,0.06);color:var(--text-muted);font-weight:600}
.nav-item.active .nav-badge{background:rgba(0,229,255,0.15);color:var(--primary)}
.main-content{flex:1;margin-left:var(--panel-w);transition:margin-left 0.3s ease;min-width:0}
.main-content.expanded{margin-left:0}
.top-bar{display:flex;align-items:center;gap:12px;padding:12px 24px;background:rgba(8,12,20,0.88);border-bottom:1px solid var(--border);backdrop-filter:blur(16px);position:sticky;top:0;z-index:50}
.hamburger{background:none;border:none;color:var(--text-dim);font-size:20px;cursor:pointer;padding:4px 8px;border-radius:var(--radius-sm);transition:all 0.2s;display:none}
.hamburger:hover{background:var(--surface);color:var(--text)}
.top-bar h1{font-size:17px;font-weight:600;flex:1}
.top-bar-right{display:flex;align-items:center;gap:16px;font-size:12px;color:var(--text-muted)}
.page{display:none;padding:20px 24px 60px}
.page.active{display:block}
.page-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:20px;flex-wrap:wrap}
.search-input{padding:9px 16px;font-size:13px;min-width:220px;flex:1;max-width:360px;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:20px;color:var(--text);outline:none;transition:border-color 0.2s;font-family:var(--font)}
.search-input:focus{border-color:var(--primary)}
.search-input::placeholder{color:var(--text-muted)}
.filter-group{display:flex;gap:4px;flex-wrap:wrap}
.filter-chip{padding:5px 14px;font-size:12px;border-radius:20px;cursor:pointer;transition:all 0.2s;border:1px solid var(--border);background:transparent;color:var(--text-dim);font-family:var(--font);white-space:nowrap;display:flex;align-items:center;gap:4px}
.filter-chip:hover{border-color:var(--border-active);color:var(--text)}
.filter-chip.active{background:var(--primary-dim);border-color:var(--primary);color:var(--primary)}
.filter-chip span{font-size:11px;opacity:0.6}
.filter-chip.active span{opacity:1}
.toolbar-stats{font-size:12px;color:var(--text-muted);display:flex;gap:14px;align-items:center}
.toolbar-stats span{display:flex;align-items:center;gap:4px}
.card-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:16px;transition:all 0.25s cubic-bezier(0.4,0,0.2,1);display:flex;flex-direction:column;position:relative;overflow:hidden}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--border-active),transparent);opacity:0;transition:opacity 0.3s}
.card:hover{background:var(--surface-hover);border-color:var(--border-active);transform:translateY(-2px);box-shadow:var(--shadow)}
.card:hover::before{opacity:1}
.card-top{display:flex;align-items:flex-start;gap:12px;margin-bottom:8px}
.card-logo{width:40px;height:40px;border-radius:10px;flex-shrink:0;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);overflow:hidden}
.card-logo img{width:24px;height:24px;object-fit:contain}
.card-logo .fb{font-size:18px;font-weight:700;color:var(--text-muted)}
.card-info{flex:1;min-width:0}
.card-name{font-size:14px;font-weight:600;display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.card-name .badge{font-size:10px;font-weight:600;padding:1px 8px;border-radius:10px;background:rgba(0,229,255,0.1);color:var(--primary)}
.card-desc{font-size:12px;color:var(--text-dim);margin-top:3px;line-height:1.45;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.card-links{display:flex;gap:8px;margin-top:4px;flex-wrap:wrap}
.card-links a{font-size:11px;color:var(--primary);text-decoration:none;opacity:0.7;transition:opacity 0.2s}
.card-links a:hover{opacity:1;text-decoration:underline}
.card-actions{display:flex;gap:6px;align-items:center;flex-shrink:0;margin-left:auto}
.card-input-row{display:flex;gap:6px;margin-top:10px}
.card-input-row input{flex:1;padding:7px 10px;font-size:12px;font-family:monospace;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:6px;color:var(--text);outline:none;transition:border-color 0.2s;min-width:0}
.card-input-row input:focus{border-color:var(--primary)}
.card-status-row{display:flex;align-items:center;gap:8px;margin-top:8px;font-size:11px}
.card-status-row .ph{color:var(--text-muted);font-size:10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:200px}
.status-badge{display:inline-flex;align-items:center;gap:5px;padding:3px 10px;border-radius:10px;font-size:11px;font-weight:600;white-space:nowrap}
.status-badge.on{background:rgba(0,230,118,0.12);color:var(--green)}
.status-badge.off{background:rgba(255,255,255,0.04);color:var(--text-muted)}
.status-badge .dot{width:7px;height:7px;border-radius:50%;display:inline-block}
.status-badge.on .dot{background:var(--green);box-shadow:0 0 6px rgba(0,230,118,0.5)}
.status-badge.off .dot{background:var(--text-muted)}
.btn{padding:6px 14px;font-size:12px;font-weight:600;border:none;border-radius:6px;cursor:pointer;transition:all 0.2s;font-family:var(--font);white-space:nowrap}
.btn-primary{background:var(--primary);color:#0b0e17}
.btn-primary:hover{background:#00b8d4;transform:translateY(-1px);box-shadow:0 2px 8px rgba(0,229,255,0.3)}
.btn-outline{background:transparent;color:var(--primary);border:1px solid var(--border-active)}
.btn-outline:hover{background:var(--primary-dim)}
.btn-danger{background:rgba(255,23,68,0.12);color:var(--red);border:1px solid rgba(255,23,68,0.25)}
.btn-danger:hover{background:rgba(255,23,68,0.2)}
.btn-ghost{background:transparent;color:var(--text-dim);border:1px solid var(--border)}
.btn-ghost:hover{background:var(--surface);color:var(--text)}
.btn:disabled{opacity:0.35;cursor:not-allowed;transform:none!important;box-shadow:none!important}
.btn-sm{padding:4px 10px;font-size:11px}
.verify-result{font-size:12px;margin-top:6px;display:none;padding:5px 10px;border-radius:6px;word-break:break-word;line-height:1.4}
.verify-result.ok{display:block;background:rgba(0,230,118,0.08);color:var(--green)}
.verify-result.err{display:block;background:rgba(255,23,68,0.08);color:var(--red)}
.verify-result.wait{display:block;background:rgba(255,214,0,0.08);color:var(--yellow)}
.gauth-card{display:flex;align-items:center;justify-content:space-between;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:20px 24px;margin-bottom:20px;gap:16px;flex-wrap:wrap}
.gauth-info{display:flex;align-items:center;gap:14px}
.gdot{width:14px;height:14px;border-radius:50%;flex-shrink:0}
.gdot.on{background:var(--green);box-shadow:0 0 14px rgba(0,230,118,0.5)}
.gdot.off{background:var(--text-muted)}
.gauth-text h3{font-size:15px;font-weight:600;margin-bottom:2px}
.gauth-text p{font-size:12px;color:var(--text-dim)}
.service-card{cursor:pointer}
.modal-overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);backdrop-filter:blur(8px);z-index:1000;justify-content:center;align-items:flex-start;padding:40px 20px;overflow-y:auto}
.modal-overlay.open{display:flex}
.modal-panel{background:#0f1528;border:1px solid var(--border-active);border-radius:16px;width:100%;max-width:680px;box-shadow:0 20px 60px rgba(0,0,0,0.6);animation:modalIn 0.25s cubic-bezier(0.4,0,0.2,1);margin-top:20px}
@keyframes modalIn{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:translateY(0)}}
.modal-header{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid var(--border)}
.modal-header h2{font-size:16px;font-weight:600;display:flex;align-items:center;gap:10px}
.modal-header h2 img{width:24px;height:24px;border-radius:6px}
.modal-close{background:none;border:none;color:var(--text-dim);font-size:20px;cursor:pointer;padding:4px 8px;border-radius:6px;transition:all 0.2s}
.modal-close:hover{background:var(--surface);color:var(--text)}
.modal-body{padding:16px 20px 20px;max-height:58vh;overflow-y:auto}
.gmi-item{display:flex;align-items:center;gap:12px;padding:10px 12px;border-radius:var(--radius-sm);transition:background 0.2s;margin-bottom:4px}
.gmi-item:hover{background:var(--surface)}
.gmi-item .gmi-ico{width:36px;height:36px;border-radius:8px;display:flex;align-items:center;justify-content:center;overflow:hidden;background:rgba(255,255,255,0.03);flex-shrink:0}
.gmi-item .gmi-ico img{width:22px;height:22px;object-fit:contain}
.gmi-item .gmi-info{flex:1}
.gmi-item .gmi-name{font-size:13px;font-weight:500}
.gmi-item .gmi-desc{font-size:11px;color:var(--text-dim);margin-top:1px}
.gmi-item .gmi-st{font-size:11px;font-weight:600;padding:2px 10px;border-radius:10px}
.gmi-item .gmi-st.on{background:rgba(0,230,118,0.12);color:var(--green)}
.gmi-item .gmi-st.off{background:rgba(255,255,255,0.04);color:var(--text-muted)}
.toast-container{position:fixed;top:16px;right:16px;z-index:9999;display:flex;flex-direction:column;gap:8px;pointer-events:none}
.toast{padding:10px 18px;border-radius:var(--radius-sm);font-size:13px;font-weight:500;backdrop-filter:blur(16px);animation:toastIn 0.3s cubic-bezier(0.4,0,0.2,1);max-width:400px;word-break:break-word;pointer-events:auto;border:1px solid rgba(255,255,255,0.08)}
.toast.success{background:rgba(0,230,118,0.15);border-color:rgba(0,230,118,0.3);color:var(--green)}
.toast.error{background:rgba(255,23,68,0.15);border-color:rgba(255,23,68,0.3);color:var(--red)}
.toast.info{background:rgba(0,229,255,0.12);border-color:rgba(0,229,255,0.25);color:var(--primary)}
@keyframes toastIn{from{opacity:0;transform:translateX(24px)}to{opacity:1;transform:translateX(0)}}
.toast.removing{animation:toastOut 0.25s ease forwards}
@keyframes toastOut{to{opacity:0;transform:translateX(24px)}}
.empty-state{text-align:center;padding:60px 20px;color:var(--text-dim);font-size:14px;grid-column:1/-1}
@media(max-width:768px){
.side-panel{transform:translateX(-100%)}.side-panel.open{transform:translateX(0)}.main-content{margin-left:0}.hamburger{display:block}.card-grid{grid-template-columns:1fr}.page-toolbar{flex-direction:column;align-items:stretch}.search-input{max-width:none}.toolbar-stats{justify-content:center}.top-bar{padding:10px 16px}.page{padding:16px}
}
@media(min-width:1400px){.card-grid{grid-template-columns:repeat(3,1fr)}}
</style>
</head>
<body>
<div class="app-layout">
<aside class="side-panel" id="sidePanel"><div class="panel-header"><h2>&#x26a1; FRIDAY</h2><button class="panel-toggle" id="panelToggle">&#x2630;</button></div>
<nav class="panel-nav">
<a class="nav-item active" data-page="keys"><span class="nav-icon"><img src="https://cdn.simpleicons.org/key/00e5ff" alt="" onerror="this.style.display='none'"><span class="fb" style="display:none">&#x1f511;</span></span><span class="nav-label">API Keys</span><span class="nav-badge" id="navKB">0</span></a>
<a class="nav-item" data-page="google"><span class="nav-icon"><img src="https://cdn.simpleicons.org/google/4285F4" alt="" onerror="this.style.display='none'"><span class="fb" style="display:none">&#x1f310;</span></span><span class="nav-label">Google Services</span><span class="nav-badge" id="navGB">0</span></a>
<a class="nav-item" data-page="services"><span class="nav-icon"><img src="https://cdn.simpleicons.org/apps/00e5ff" alt="" onerror="this.style.display='none'"><span class="fb" style="display:none">&#x2699;</span></span><span class="nav-label">Services</span><span class="nav-badge" id="navSvB">0</span></a>
</nav></aside>
<main class="main-content" id="mainContent">
<header class="top-bar"><button class="hamburger" id="hamburger">&#x2630;</button><h1 id="pageTitle">API Keys</h1><div class="top-bar-right"><span id="sLive" style="display:flex;align-items:center;gap:4px"><span style="color:var(--green)">&#x25cf;</span> Live</span><span id="sClock"></span></div></header>
<div class="page active" id="page-keys">
<div class="page-toolbar">
<input class="search-input" id="kSearch" placeholder="Search API keys by name or category..." autocomplete="off" spellcheck="false">
<div class="filter-group">
<button class="filter-chip active" data-f="all">All <span id="kAll">0</span></button>
<button class="filter-chip" data-f="connected">Connected <span id="kOn">0</span></button>
<button class="filter-chip" data-f="disconnected">Not Configured <span id="kOff">0</span></button>
</div>
<div class="toolbar-stats">
<span>&#x1f511; <b id="kT">0</b></span><span style="color:var(--green)">&#x25cf; <b id="kTON">0</b></span><span style="color:var(--text-muted)">&#x25cf; <b id="kTOFF">0</b></span>
</div>
</div>
<div class="card-grid" id="kGrid"></div>
</div>
<div class="page" id="page-google">
<div class="gauth-card" id="gauthC">
<div class="gauth-info"><div class="gdot off" id="gDot"></div><div class="gauth-text"><h3>Google Account</h3><p id="gStat">Not connected</p></div></div>
<div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-primary" id="gConn">&#x1f517; Connect</button><button class="btn btn-danger" id="gRev" style="display:none">&#x274c; Revoke</button></div>
</div>
<div class="page-toolbar">
<input class="search-input" id="gSearch" placeholder="Search scope categories..." autocomplete="off" spellcheck="false">
<div class="filter-group">
<button class="filter-chip active" data-f="all">All <span id="gAll">0</span></button>
<button class="filter-chip" data-f="connected">Connected <span id="gOn">0</span></button>
<button class="filter-chip" data-f="disconnected">Not Connected <span id="gOff">0</span></button>
</div>
<div class="toolbar-stats"><span>&#x1f310; <b id="gT">0</b></span><span style="color:var(--green)">&#x25cf; <b id="gTON">0</b></span></div>
</div>
<div class="card-grid" id="gGrid"></div>
</div>
<div class="page" id="page-github">
<div class="gauth-card" id="ghAuthC">
<div class="gauth-info"><div class="gdot off" id="ghDot"></div><div class="gauth-text"><h3>GitHub Account</h3><p id="ghStat">Not connected</p></div></div>
<div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-primary" id="ghConn">&#x1f517; Connect with GitHub</button><button class="btn btn-danger" id="ghRev" style="display:none">&#x274c; Revoke</button></div>
</div>
<div style="margin-top:16px;padding:20px 24px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius)">
<p style="font-size:13px;color:var(--text-dim);line-height:1.6">Once connected, FRIDAY can access your repositories, issues, pull requests, workflows, and organization data via the GitHub API with the following scopes:</p>
<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px;margin-top:14px">
<div style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-dim);padding:6px 10px;background:rgba(255,255,255,0.02);border-radius:6px"><span style="color:var(--primary)">&#x25cf;</span> repo (full control)</div>
<div style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-dim);padding:6px 10px;background:rgba(255,255,255,0.02);border-radius:6px"><span style="color:var(--primary)">&#x25cf;</span> user (profile, email)</div>
<div style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-dim);padding:6px 10px;background:rgba(255,255,255,0.02);border-radius:6px"><span style="color:var(--primary)">&#x25cf;</span> workflow (Actions)</div>
<div style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-dim);padding:6px 10px;background:rgba(255,255,255,0.02);border-radius:6px"><span style="color:var(--primary)">&#x25cf;</span> admin:org (org management)</div>
<div style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-dim);padding:6px 10px;background:rgba(255,255,255,0.02);border-radius:6px"><span style="color:var(--primary)">&#x25cf;</span> delete_repo</div>
</div>
</div>
</div>
<div class="page" id="page-services">
<div class="page-toolbar">
<div class="toolbar-stats"><span>&#x2699; <b id="svT">0</b></span><span style="color:var(--green)">&#x25cf; <b id="svTON">0</b></span></div>
</div>
<div id="svGrid" style="display:flex;flex-direction:column;gap:14px"></div>
</div>
</main>
</div>
<div class="modal-overlay" id="mOverlay"><div class="modal-panel"><div class="modal-header"><h2 id="mTitle"></h2><button class="modal-close" id="mClose">&#x2715;</button></div><div class="modal-body" id="mBody"></div></div></div>
<div class="toast-container" id="tC"></div>
<script>
var kData=[],gCat=[],gAuth={},kF='all',kS='',gF='all',gS='';
function t(m,ty){ty=ty||'info';var c=document.getElementById('tC'),e=document.createElement('div');e.className='toast '+ty;e.textContent=m;c.appendChild(e);setTimeout(function(){e.classList.add('removing');setTimeout(function(){if(e.parentNode)e.parentNode.removeChild(e)},300)},3500)}
document.getElementById('hamburger').onclick=function(){document.getElementById('sidePanel').classList.toggle('open');document.getElementById('mainContent').classList.toggle('expanded')};
document.getElementById('panelToggle').onclick=function(){var s=document.getElementById('sidePanel');s.classList.toggle('closed');setTimeout(function(){document.getElementById('mainContent').classList.toggle('expanded')},50)};
document.querySelectorAll('.nav-item').forEach(function(n){n.onclick=function(){document.querySelectorAll('.nav-item').forEach(function(x){x.classList.remove('active')});document.querySelectorAll('.page').forEach(function(x){x.classList.remove('active')});n.classList.add('active');document.getElementById('page-'+n.dataset.page).classList.add('active');document.getElementById('pageTitle').textContent=n.querySelector('.nav-label').textContent;if(n.dataset.page==='google')loadG();if(n.dataset.page==='github')loadGH();if(n.dataset.page==='services')loadSV();if(window.innerWidth<=768){document.getElementById('sidePanel').classList.remove('open');document.getElementById('mainContent').classList.remove('expanded')}}});
function loadK(){var x=new XMLHttpRequest();x.open('GET','/settings/api/keys',true);x.onload=function(){if(x.status===200){try{var d=JSON.parse(x.responseText);kData=d.keys||[];document.getElementById('kT').textContent=d.total;document.getElementById('kTON').textContent=d.connected;document.getElementById('kTOFF').textContent=d.disconnected;document.getElementById('navKB').textContent=d.total;rK()}catch(e){}}};x.send()}
function rK(){var g=document.getElementById('kGrid'),q=kS.toLowerCase(),f=[];for(var i=0;i<kData.length;i++){var k=kData[i];if(kF==='connected'&&!k.present)continue;if(kF==='disconnected'&&k.present)continue;if(q&&k.name.toLowerCase().indexOf(q)===-1&&k.key.toLowerCase().indexOf(q)===-1&&k.category.toLowerCase().indexOf(q)===-1)continue;f.push(k)}
document.getElementById('kAll').textContent=kData.length;var nOn=0,nOff=0;for(i=0;i<kData.length;i++){if(kData[i].present)nOn++;else nOff++}
document.getElementById('kOn').textContent=nOn;document.getElementById('kOff').textContent=nOff;if(f.length===0){g.innerHTML='<div class="empty-state">No keys match your filter.</div>';return}
var h='';for(i=0;i<f.length;i++){k=f[i];var cls=k.present?'on':'off',ls=k.logoSrc||'',lh='';if(ls){lh='<img src="'+ls+'" alt="'+k.name+'" loading="lazy" onerror="this.style.display=\'none\';this.parentNode.querySelector(\'.fb\').style.display=\'flex\'"><div class="fb" style="display:none">'+(k.name?k.name.charAt(0).toUpperCase():'?')+'</div>'}else{lh='<div class="fb">'+(k.name?k.name.charAt(0).toUpperCase():'?')+'</div>'}
h+='<div class="card" data-key="'+k.key+'"><div class="card-top"><div class="card-logo">'+lh+'</div><div class="card-info"><div class="card-name">'+k.name+' <span class="badge">'+k.category+'</span></div><div class="card-desc">'+(k.description||'')+'</div><div class="card-links">'+(k.url?'<a href="'+k.url+'" target="_blank">&#x1f4c4; Get Key</a>':'')+(k.docs?'<a href="'+k.docs+'" target="_blank">&#x1f4d6; Docs</a>':'')+'</div></div><div class="card-actions"><button class="btn btn-outline btn-sm tBtn" data-key="'+k.key+'"'+(k.present?'':' disabled')+'>Verify</button></div></div><div class="card-status-row"><span class="status-badge '+cls+'"><span class="dot"></span> '+(k.present?'Connected':'Not Configured')+'</span><span class="ph">'+(k.pricing||'')+'</span></div><div class="card-input-row"><input type="password" class="kIn" data-key="'+k.key+'" placeholder="Enter '+k.name+' key..." value="'+k.value+'" autocomplete="off"><button class="btn btn-primary btn-sm sBtn" data-key="'+k.key+'">Save</button><button class="btn btn-ghost btn-sm tVis" data-key="'+k.key+'" title="Show/Hide">&#x1f441;</button></div><div class="verify-result" data-key="'+k.key+'"></div></div>'}
g.innerHTML=h;bE()}
function bE(){document.querySelectorAll('.sBtn').forEach(function(b){b.onclick=function(){var s=this,k=s.dataset.key,i=document.querySelector('.kIn[data-key="'+k+'"]'),v=i.value.replace(/\*+/g,'').trim();if(!v){t('Enter a key value','error');return}var o=null;for(var x=0;x<kData.length;x++){if(kData[x].key===k){o=kData[x];break}}if(o&&o.present&&v.length<8){t('Enter the full key','error');return}s.disabled=true;s.textContent='...';var r=new XMLHttpRequest();r.open('POST','/settings/api/keys',true);r.setRequestHeader('Content-Type','application/json');r.onload=function(){if(r.status===200){try{var d=JSON.parse(r.responseText);if(d.success){t(d.name+' saved!','success');loadK()}else t(d.error||'Save failed','error')}catch(e){t('Save failed','error')}}else t('Server error','error');s.disabled=false;s.textContent='Save'};r.onerror=function(){t('Network error','error');s.disabled=false;s.textContent='Save'};r.send(JSON.stringify({key:k,value:v}))}})
document.querySelectorAll('.tBtn').forEach(function(b){b.onclick=function(){var s=this,k=s.dataset.key,c=s.closest('.card'),re=c.querySelector('.verify-result'),o=null;for(var x=0;x<kData.length;x++){if(kData[x].key===k){o=kData[x];break}}s.disabled=true;s.textContent='&#x23f3;';re.className='verify-result wait';re.textContent='Verifying...';var tv=o?o.value.replace(/\*/g,'x'):'',r=new XMLHttpRequest();r.open('POST','/settings/api/keys/test',true);r.setRequestHeader('Content-Type','application/json');r.onload=function(){if(r.status===200){try{var d=JSON.parse(r.responseText);if(d.success){re.className='verify-result ok';re.textContent='&#x2705; '+(d.message||'OK');t(o.name+': Verified','success')}else{re.className='verify-result err';re.textContent='&#x274c; '+(d.message||d.error||'Failed');t(o.name+': '+(d.message||'Failed'),'error')}}catch(e){re.className='verify-result err';re.textContent='&#x274c; Invalid'}}else{re.className='verify-result err';re.textContent='&#x274c; Server error'}s.disabled=false;s.textContent='Verify'};r.onerror=function(){re.className='verify-result err';re.textContent='&#x274c; Network error';s.disabled=false;s.textContent='Verify'};r.send(JSON.stringify({key:k,value:tv}))}})
document.querySelectorAll('.tVis').forEach(function(b){b.onclick=function(){var k=this.dataset.key,i=document.querySelector('.kIn[data-key="'+k+'"]');if(i)i.type=i.type==='password'?'text':'password'}})}
function loadG(){var x=new XMLHttpRequest();x.open('GET','/settings/google/status',true);x.onload=function(){if(x.status===200){try{var d=JSON.parse(x.responseText);if(d.error){document.getElementById('gGrid').innerHTML='<div class="empty-state">'+d.error+'</div>';return}gCat=d.scope_categories||[];gAuth=d;var dot=document.getElementById('gDot'),st=document.getElementById('gStat'),cn=document.getElementById('gConn'),rv=document.getElementById('gRev');if(d.configured&&d.has_creds){dot.className='gdot on';st.textContent='Connected ('+d.connected_count+'/'+d.total_services+' services)';cn.textContent='&#x1f504; Reconnect All';rv.style.display='inline-block'}else if(d.configured){dot.className='gdot off';st.textContent='OAuth not completed';cn.textContent='&#x1f517; Connect All';rv.style.display='none'}else{dot.className='gdot off';st.textContent='GOOGLE_CLIENT_ID not configured';cn.disabled=true;cn.textContent='&#x26a0; Not Configured';rv.style.display='none'}
document.getElementById('gT').textContent=d.total_scope_cats||0;document.getElementById('gTON').textContent=gCat.filter(function(c){return c.connected}).length;document.getElementById('navGB').textContent=d.total_scope_cats||0;rG()}catch(e){}}};x.send()}
function rG(){var g=document.getElementById('gGrid'),q=gS.toLowerCase(),f=[];for(var i=0;i<gCat.length;i++){var c=gCat[i];if(gF==='connected'&&!c.connected)continue;if(gF==='disconnected'&&c.connected)continue;if(q&&c.name.toLowerCase().indexOf(q)===-1)continue;f.push(c)}
document.getElementById('gAll').textContent=gCat.length;var nOn=0;for(i=0;i<gCat.length;i++){if(gCat[i].connected)nOn++}document.getElementById('gOn').textContent=nOn;document.getElementById('gOff').textContent=gCat.length-nOn
if(f.length===0){g.innerHTML='<div class="empty-state">No scope categories match your filter.</div>';return}
var h='';for(i=0;i<f.length;i++){c=f[i];var cls=c.connected?'on':'off';var nm=c.name;var svgKey=nm.toLowerCase().replace(/ /g,'').replace(/readonly/g,'readonly').replace(/gmail/g,'gmail').replace(/drive/g,'drive');var iconURL='https://cdn.simpleicons.org/google'+nm.replace(/ /g,'')+'/4285F4';if(nm==='Gmail'||nm==='Gmail Readonly')iconURL='https://cdn.simpleicons.org/gmail/EA4335';if(nm==='Calendar')iconURL='https://cdn.simpleicons.org/googlecalendar/4285F4';if(nm==='Drive'||nm==='Drive Readonly')iconURL='https://cdn.simpleicons.org/googledrive/FBBC04';if(nm==='YouTube')iconURL='https://cdn.simpleicons.org/youtube/FF0000';if(nm==='Photos')iconURL='https://cdn.simpleicons.org/googlephotos/FF6F00';if(nm==='Docs')iconURL='https://cdn.simpleicons.org/googledocs/4285F4';if(nm==='Sheets')iconURL='https://cdn.simpleicons.org/googlesheets/0F9D58';if(nm==='Slides')iconURL='https://cdn.simpleicons.org/googleslides/FBBC04';if(nm==='Tasks')iconURL='https://cdn.simpleicons.org/googletasks/4285F4';if(nm==='People')iconURL='https://cdn.simpleicons.org/googlepeople/4285F4';if(nm==='Cloud Platform')iconURL='https://cdn.simpleicons.org/googlecloud/4285F4';if(nm==='Classroom')iconURL='https://cdn.simpleicons.org/googleclassroom/1A73E8';if(nm==='Analytics')iconURL='https://cdn.simpleicons.org/googleanalytics/E37400';if(nm==='Firebase')iconURL='https://cdn.simpleicons.org/firebase/FFCA28';if(nm==='Forms')iconURL='https://cdn.simpleicons.org/googleforms/7248B9';if(nm==='Books')iconURL='https://cdn.simpleicons.org/googlebooks/4285F4';if(nm==='Translation')iconURL='https://cdn.simpleicons.org/googletranslate/4285F4';if(nm==='BigQuery')iconURL='https://cdn.simpleicons.org/googlebigquery/4285F4';if(nm==='Cloud Storage')iconURL='https://cdn.simpleicons.org/googlecloudstorage/4285F4';if(nm==='Search Console')iconURL='https://cdn.simpleicons.org/googlesearchconsole/4285F4';if(nm==='Natural Language')iconURL='https://cdn.simpleicons.org/googlenaturallanguage/4285F4'
var scopesHTML='';for(var s=0;s<c.scopes.length;s++){scopesHTML+='<div style="font-size:11px;color:var(--text-muted);padding:2px 0;font-family:monospace;word-break:break-all">'+c.scopes[s]+'</div>'}
h+='<div class="card" data-cat="'+c.name+'"><div class="card-top"><div class="card-logo"><img src="'+iconURL+'" alt="" loading="lazy" onerror="this.style.display=\'none\';this.parentNode.querySelector(\'.fb\').style.display=\'flex\'"><div class="fb" style="display:none">'+nm.charAt(0)+'</div></div><div class="card-info"><div class="card-name">'+nm+' <span class="badge">'+c.scope_count+' scope'+(c.scope_count!==1?'s':'')+'</span></div><div class="card-desc">Click Connect to authorize '+nm+' with '+c.scope_count+' OAuth scopes. Includes openid+userinfo+profile automatically.</div></div><div class="card-actions"><span class="status-badge '+cls+'"><span class="dot"></span> '+(c.connected?'Connected':'Not Connected')+'</span></div></div><div class="card-input-row">'+(c.connected?'<button class="btn btn-outline btn-sm gDiscBtn" data-cat="'+c.name+'" style="width:100%">Connected &#x2705; — Click to review scopes</button>':'<button class="btn btn-primary btn-sm gConnBtn" data-cat="'+c.name+'" style="width:100%">&#x1f517; Connect '+nm+'</button>')+'</div>'+'<div class="verify-result" data-cat="'+c.name+'" style="display:none">'+scopesHTML+'</div></div>'}
g.innerHTML=h;g.querySelectorAll('.gConnBtn').forEach(function(b){b.onclick=function(){var cat=this.dataset.cat;window.location.href='/settings/google/auth/'+encodeURIComponent(cat)}});g.querySelectorAll('.gDiscBtn').forEach(function(b){b.onclick=function(){var cat=this.dataset.cat;for(var j=0;j<gCat.length;j++){if(gCat[j].name===cat){var d=gCat[j];var r=this.closest('.card').querySelector('.verify-result');if(r.style.display==='none'){r.style.display='block';this.textContent='Hide scopes'}else{r.style.display='none';this.textContent='Connected &#x2705; — Click to review scopes'}break}}}})}
document.getElementById('mClose').onclick=function(){document.getElementById('mOverlay').classList.remove('open')}
document.getElementById('mOverlay').onclick=function(e){if(e.target===e.currentTarget)this.classList.remove('open')}
document.getElementById('gConn').onclick=function(){window.location.href='/settings/google/auth'}
document.getElementById('gRev').onclick=function(){if(!confirm('Revoke all Google OAuth tokens?'))return;var x=new XMLHttpRequest();x.open('POST','/settings/google/revoke',true);x.onload=function(){t('Tokens revoked','info');loadG()};x.onerror=function(){t('Failed to revoke','error')};x.send()}
function loadGH(){var x=new XMLHttpRequest();x.open('GET','/settings/github/status',true);x.onload=function(){if(x.status===200){try{var d=JSON.parse(x.responseText);var dot=document.getElementById('ghDot'),st=document.getElementById('ghStat'),cn=document.getElementById('ghConn'),rv=document.getElementById('ghRev');if(d.configured&&d.has_token){dot.className='gdot on';st.textContent='Connected';cn.textContent='&#x1f504; Reconnect';rv.style.display='inline-block';document.getElementById('navHubB').textContent='&#x2705;'}else if(d.configured){dot.className='gdot off';st.textContent='OAuth not completed';cn.textContent='&#x1f517; Connect with GitHub';rv.style.display='none';document.getElementById('navHubB').textContent=''}else{dot.className='gdot off';st.textContent='GITHUB_CLIENT_ID not configured';cn.disabled=true;cn.textContent='&#x26a0; Not Configured';rv.style.display='none';document.getElementById('navHubB').textContent=''}}catch(e){}}};x.send()}
document.getElementById('ghConn').onclick=function(){window.location.href='/settings/github/auth'}
document.getElementById('ghRev').onclick=function(){if(!confirm('Revoke GitHub OAuth token?'))return;var x=new XMLHttpRequest();x.open('POST','/settings/github/revoke',true);x.onload=function(){t('GitHub token revoked','info');loadGH()};x.onerror=function(){t('Failed to revoke','error')};x.send()}
var svCfg=[];function loadSV(){var x=new XMLHttpRequest();x.open('GET','/settings/services/status',true);x.onload=function(){if(x.status===200){try{var d=JSON.parse(x.responseText);svCfg=d.services||[];document.getElementById('svT').textContent=d.total;document.getElementById('svTON').textContent=d.connected;document.getElementById('navSvB').textContent=d.total;rSV()}catch(e){}}};x.send()}
function rSV(){var g=document.getElementById('svGrid'),h='';for(var i=0;i<svCfg.length;i++){var sv=svCfg[i],cls=sv.connected?'on':'off';var ru=sv.redirect_uri?'<div style="font-size:11px;color:var(--text-dim);margin-top:6px;padding:6px 10px;background:rgba(0,0,0,0.2);border-radius:6px;font-family:monospace;word-break:break-all">Redirect URI: <span style="color:var(--primary)">'+sv.redirect_uri+'</span></div>':''
var flds='';for(var j=0;j<sv.fields.length;j++){var f=sv.fields[j],v='',eK=f.key;for(var e=0;e<svCfg.length;e++){if(svCfg[e].id===sv.id&&svCfg[e].fields&&svCfg[e].fields[j])v=svCfg[e].fields[j].value||''}flds+='<div style="flex:1;min-width:120px"><label style="font-size:11px;color:var(--text-dim);margin-bottom:3px;display:block">'+f.label+'</label><input type="'+(f.type||'text')+'" class="svIn" data-svc="'+sv.id+'" data-idx="'+j+'" data-key="'+f.key+'" placeholder="Enter '+f.label+'..." value="'+v+'" autocomplete="off" style="width:100%;padding:8px 10px;font-size:12px;font-family:monospace;background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:6px;color:var(--text);outline:none;transition:border-color 0.2s"></div>'}
var oa=sv.oauth?'<button class="btn btn-primary btn-sm svOAuthBtn" data-svc="'+sv.id+'" style="margin-top:8px">&#x1f517; Connect via OAuth</button>':''
h+='<div class="card" style="width:100%" data-svc="'+sv.id+'"><div class="card-top" style="margin-bottom:0"><div class="card-logo" style="background:'+sv.color+'15;border-color:'+sv.color+'30"><img src="'+sv.logo+'" alt="" loading="lazy" onerror="this.style.display=\'none\';this.parentNode.querySelector(\'.fb\').style.display=\'flex\'"><div class="fb" style="display:none">'+sv.name.charAt(0)+'</div></div><div class="card-info"><div class="card-name">'+sv.name+'</div><div class="card-desc">'+(sv.desc||'')+'</div>'+ru+'</div><div class="card-actions" style="align-self:flex-start"><span class="status-badge '+cls+'"><span class="dot"></span> '+(sv.connected?'Connected':'Not Connected')+'</span></div></div><div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:10px">'+flds+'</div><div style="display:flex;gap:8px;margin-top:10px"><button class="btn btn-primary btn-sm svSaveBtn" data-svc="'+sv.id+'">Save Credentials</button>'+oa+'</div></div>'}
g.innerHTML=h;g.querySelectorAll('.svSaveBtn').forEach(function(b){b.onclick=function(){var id=this.dataset.svc,up={};g.querySelectorAll('.svIn[data-svc="'+id+'"]').forEach(function(inp){var k=inp.dataset.key,v=inp.value.trim();if(v)up[k]=v});if(Object.keys(up).length===0){t('No values to save','error');return}var r=new XMLHttpRequest();r.open('POST','/settings/api/keys',true);r.setRequestHeader('Content-Type','application/json');r.onload=function(){if(r.status===200){try{var d=JSON.parse(r.responseText);if(d.success){t(id+' saved!','success');loadSV()}else t(d.error||'Save failed','error')}catch(e){t('Save failed','error')}}else t('Server error','error')};r.onerror=function(){t('Network error','error')};var keys=Object.keys(up);r.send(JSON.stringify({key:keys[0],value:up[keys[0]]}))}})
g.querySelectorAll('.svOAuthBtn').forEach(function(b){b.onclick=function(){var id=this.dataset.svc;window.location.href='/settings/'+id+'/auth'}})}
document.querySelectorAll('.filter-chip').forEach(function(c){c.onclick=function(){var g=this.parentElement;g.querySelectorAll('.filter-chip').forEach(function(x){x.classList.remove('active')});this.classList.add('active');var p=this.closest('.page');if(p&&p.id==='page-keys'){kF=this.dataset.f;rK()}else if(p&&p.id==='page-google'){gF=this.dataset.f;rG()}}})
document.getElementById('kSearch').oninput=function(){kS=this.value;rK()}
document.getElementById('gSearch').oninput=function(){gS=this.value;rG()}
function uC(){var d=new Date();document.getElementById('sClock').textContent=String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0')+':'+String(d.getSeconds()).padStart(2,'0')}
setInterval(uC,1000);uC();loadK();loadG();loadGH();loadSV();setInterval(function(){loadK();loadG();loadGH();loadSV()},60000);
document.addEventListener('keydown',function(e){if(e.key==='Escape'&&document.getElementById('mOverlay').classList.contains('open')){document.getElementById('mOverlay').classList.remove('open')}});
</script>
</body>
</html>"""


def register_settings_routes(app):
    """Register all settings dashboard routes on the provided FastAPI application instance."""
    app.include_router(router)
