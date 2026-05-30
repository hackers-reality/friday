import asyncio
import json
import re
from typing import Any

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


TECH_PATTERNS: dict[str, list[dict]] = {
    "Cloudflare": [{"search": "text", "pattern": r"cloudflare", "location": "headers.server"}, {"search": "text", "pattern": r"__cfduid", "location": "headers.set-cookie"}],
    "nginx": [{"search": "text", "pattern": r"nginx", "location": "headers.server"}],
    "Apache": [{"search": "text", "pattern": r"Apache", "location": "headers.server"}],
    "Node.js": [{"search": "text", "pattern": r"Node\.?[Jj]s", "location": "headers.x-powered-by"}],
    "Express": [{"search": "text", "pattern": r"Express", "location": "headers.x-powered-by"}],
    "React": [{"search": "text", "pattern": r"react", "location": "body"}, {"search": "attr", "pattern": r"_react", "location": "body"}],
    "Next.js": [{"search": "text", "pattern": r"next\.js|__NEXT_DATA__", "location": "body"}],
    "Vue.js": [{"search": "text", "pattern": r"vue\.js|__VUE__", "location": "body"}],
    "Angular": [{"search": "text", "pattern": r"angular|ng-version", "location": "body"}],
    "Django": [{"search": "text", "pattern": r"django", "location": "headers.x-powered-by"}, {"search": "text", "pattern": r"csrftoken", "location": "headers.set-cookie"}],
    "Flask": [{"search": "text", "pattern": r"flask", "location": "headers"}],
    "WordPress": [{"search": "text", "pattern": r"wp-content|wp-json", "location": "body"}],
    "Laravel": [{"search": "text", "pattern": r"laravel", "location": "headers.x-powered-by"}],
    "Ruby on Rails": [{"search": "text", "pattern": r"rails|Rails", "location": "headers.x-powered-by"}, {"search": "text", "pattern": r"_rails", "location": "headers"}],
    "jQuery": [{"search": "text", "pattern": r"jquery", "location": "body"}],
    "Bootstrap": [{"search": "text", "pattern": r"bootstrap", "location": "body"}],
    "Tailwind CSS": [{"search": "text", "pattern": r"tailwindcss|tailwind ", "location": "body"}],
    "Google Analytics": [{"search": "text", "pattern": r"gtag|ga\.js|analytics\.js", "location": "body"}],
    "Hotjar": [{"search": "text", "pattern": r"hotjar", "location": "body"}],
    "Cloudflare": [{"search": "text", "pattern": r"cloudflare", "location": "headers.server"}, {"search": "text", "pattern": r"__cf", "location": "headers"}],
    "Amazon AWS": [{"search": "text", "pattern": r"aws|amazonaws\.com", "location": "body"}],
    "Google Cloud": [{"search": "text", "pattern": r"google\.com/cloud|gstatic\.com", "location": "body"}],
    "Microsoft IIS": [{"search": "text", "pattern": r"IIS", "location": "headers.server"}],
    "PHP": [{"search": "text", "pattern": r"PHP", "location": "headers.x-powered-by"}, {"search": "text", "pattern": r"PHPSESSID", "location": "headers.set-cookie"}],
    "Python": [{"search": "text", "pattern": r"Python", "location": "headers.server"}],
}


async def fingerprint_url(url: str) -> dict[str, Any]:
    if not HAS_REQUESTS:
        return {"error": "requests not installed. Run: pip install requests", "url": url, "technologies": []}
    result: dict[str, Any] = {"url": url, "technologies": [], "headers": {}}
    try:
        resp = await asyncio.get_event_loop().run_in_executor(
            None, lambda: requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
        )
        headers = {k.lower(): v for k, v in resp.headers.items()}
        result["headers"] = headers
        result["status"] = resp.status_code
        result["final_url"] = resp.url
        body_lower = resp.text.lower()
        detected = set()
        for tech, patterns in TECH_PATTERNS.items():
            for p in patterns:
                try:
                    location = p.get("location", "body")
                    if location.startswith("headers."):
                        header_key = location.split(".", 1)[1]
                        header_val = headers.get(header_key, "")
                        if re.search(p["pattern"], str(header_val), re.IGNORECASE):
                            detected.add(tech)
                            break
                    else:
                        if re.search(p["pattern"], body_lower, re.IGNORECASE):
                            detected.add(tech)
                            break
                except Exception:
                    pass
        result["technologies"] = sorted(detected)
    except Exception as e:
        result["error"] = str(e)
    return result
