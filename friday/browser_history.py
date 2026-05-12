"""
Friday Browser History Tools - Phase 3
Read and search browser history from Chrome, Edge, Brave, Opera.
"""
from __future__ import annotations

import os
import sys
import json
import sqlite3
import shutil
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

# ─── Browser Paths (Windows) ────────────────────────────────────

BROWSER_PATHS = {
    "chrome": {
        "path": os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default"),
        "history_file": "History",
        "name": "Chrome",
    },
    "edge": {
        "path": os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default"),
        "history_file": "History",
        "name": "Microsoft Edge",
    },
    "brave": {
        "path": os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default"),
        "history_file": "History",
        "name": "Brave",
    },
    "opera": {
        "path": os.path.expandvars(r"%APPDATA%\Opera Software\Opera Stable"),
        "history_file": "History",
        "name": "Opera",
    },
}

# ─── History Reading ────────────────────────────────────────────────

def _get_history_db_path(browser: str) -> Optional[str]:
    """Get the path to the history database for a browser."""
    if browser not in BROWSER_PATHS:
        return None
    info = BROWSER_PATHS[browser]
    db_path = os.path.join(info["path"], info["history_file"])
    return db_path if os.path.exists(db_path) else None

def _copy_history_db(src: str) -> str:
    """Copy the history DB to a temp file (since Chrome locks it)."""
    from friday._paths import FRIDAY_MEMORY; temp_dir = FRIDAY_MEMORY
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"history_temp_{int(time.time())}.db")
    try:
        shutil.copy2(src, temp_path)
        return temp_path
    except Exception as e:
        # If copy fails (very fresh Chrome), try direct
        return src

def _read_history(db_path: str, days_back: int = 3650, limit: int = 10000) -> List[Dict[str, Any]]:
    """Read history entries from a Chrome-format history DB.
    Uses days_back=3650 (10 years) to effectively search ALL history by default."""
    temp_path = None
    try:
        # Copy to avoid lock
        temp_path = _copy_history_db(db_path)
        
        conn = sqlite3.connect(temp_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Calculate cutoff — use full history (3650 days = ~10 years covers everything)
        cutoff = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1_000_000)
        
        query = """
            SELECT url, title, last_visit_time, visit_count
            FROM urls
            WHERE last_visit_time > ?
            ORDER BY last_visit_time DESC
            LIMIT ?
        """
        cursor.execute(query, (cutoff, limit))
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            # Chrome time: microseconds since Jan 1, 1601
            chrome_time = row["last_visit_time"]
            if chrome_time:
                # Convert to Unix timestamp
                unix_time = (chrome_time / 1_000_000) - 11644473600
                dt = datetime.fromtimestamp(unix_time)
            else:
                dt = None
            
            results.append({
                "url": row["url"],
                "title": row["title"] or "",
                "visited_at": dt.isoformat() if dt else "",
                "visit_count": row["visit_count"] or 1,
            })
        
        return results
    
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        # Cleanup temp
        if temp_path and temp_path != db_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass


def search_all_history(query: str, days_back: int = 3650, limit_per_browser: int = 500) -> str:
    """
    Search ALL installed browsers for a query in URL or title (no time limit).
    Returns the most relevant matching entries across all browsers.
    """
    all_results = []
    
    for browser_key, info in BROWSER_PATHS.items():
        db_path = _get_history_db_path(browser_key)
        if not db_path:
            continue
        
        entries = _read_history(db_path, days_back=days_back, limit=limit_per_browser)
        
        for entry in entries:
            if "error" in entry:
                continue
            url_lower = entry["url"].lower()
            title_lower = entry["title"].lower()
            query_lower = query.lower()
            
            if query_lower in url_lower or query_lower in title_lower:
                all_results.append({
                    "browser": info["name"],
                    "url": entry["url"],
                    "title": entry["title"],
                    "visited_at": entry["visited_at"],
                    "visit_count": entry["visit_count"],
                })
    
    if not all_results:
        return f"[FAIL] No history entries found matching '{query}' in any browser."
    
    # Sort by visit time (most recent first)
    all_results.sort(key=lambda x: x["visited_at"], reverse=True)
    
    # Format output
    lines = [f"### BROWSER HISTORY SEARCH: '{query}'", ""]
    lines.append(f"Found {len(all_results)} matching entries (showing top 10):\n")
    
    for i, entry in enumerate(all_results[:10]):
        lines.append(f"**{i+1}. {entry['title'] or '(No title)'}**")
        lines.append(f"   URL: {entry['url']}")
        lines.append(f"   Browser: {entry['browser']}")
        lines.append(f"   Visited: {entry['visited_at']} (count: {entry['visit_count']})")
        lines.append("")
    
    return "\n".join(lines)

def find_latest_by_keyword(keyword: str, days_back: int = 3650) -> Optional[Dict[str, Any]]:
    """
    Find the most recent history entry matching a keyword.
    Returns the entry dict or None.
    """
    all_results = []
    
    for browser_key, info in BROWSER_PATHS.items():
        db_path = _get_history_db_path(browser_key)
        if not db_path:
            continue
        
        entries = _read_history(db_path, days_back=days_back, limit=5000)
        
        for entry in entries:
            if "error" in entry:
                continue
            url_lower = entry["url"].lower()
            title_lower = entry["title"].lower()
            
            if keyword.lower() in url_lower or keyword.lower() in title_lower:
                all_results.append(entry)
    
    if not all_results:
        return None
    
    # Sort by visit time
    all_results.sort(key=lambda x: x["visited_at"], reverse=True)
    return all_results[0]

def open_latest_in_browser(query: str) -> str:
    """
    Find the most recent history entry matching query and open it in the default browser.
    General-purpose: works for ANYTHING - anime, repos, chats, blogs, courses, etc.
    """
    entry = find_latest_by_keyword(query, days_back=3650)
    
    if not entry:
        return f"[FAIL] No recent history found for '{query}'.\n\nTrying web search instead..."
    
    url = entry["url"]
    title = entry["title"] or url
    
    try:
        import webbrowser
        webbrowser.open(url)
        return f"[OK] Opened in browser:\n\n**{title}**\nURL: {url}\n\n(From {entry['visited_at']})"
    except Exception as e:
        return f"[FAIL] Failed to open browser: {e}\n\nURL was: {url}"


# ─── URL Categorization ────────────────────────────────────

def categorize_url(url: str, title: str = "") -> str:
    """
    Categorize a URL/title into a content type.
    Returns: anime, chat, repo, blog, social, video, music, education, shopping, news, email, other
    """
    url_lower = url.lower()
    title_lower = title.lower()
    
    # Anime / Streaming
    anime_domains = ["hianime", "animekai", "animepahe", "9anime", "gogoanime",
                     "crunchyroll", "funimation", "hidive", "anime", "aniwatch",
                     "zoro.to", "kaido.to", "anix"]
    if any(d in url_lower for d in anime_domains):
        return "anime"
    
    # Chat / Messaging
    chat_domains = ["discord.com/channels", "discord.com/app", "instagram.com/direct",
                    "web.whatsapp.com", "wa.me", "telegram.org", "t.me",
                    "messenger.com", "slack.com", "chat.openai.com", "claude.ai"]
    if any(d in url_lower for d in chat_domains):
        return "chat"
    
    # Video / Movies (check BEFORE social to catch Netflix, YouTube, etc)
    video_domains = ["youtube.com", "youtu.be", "netflix.com", "primevideo.com",
                     "hotstar.com", "hulu.com", "disneyplus.com", "hbomax.com",
                     "sonyliv.com", "vimeo.com", "dailymotion.com", "twitch.tv"]
    if any(d in url_lower for d in video_domains):
        return "video"
    
    # Social Media
    social_domains = ["instagram.com", "facebook.com", "x.com", "twitter.com",
                      "reddit.com", "tiktok.com", "snapchat.com", "linkedin.com",
                      "pinterest.com", "tumblr.com"]
    if any(d in url_lower for d in social_domains):
        return "social"
    
    # Music
    music_domains = ["spotify.com", "soundcloud.com", "music.youtube.com",
                     "apple.music.com", "deezer.com", "bandcamp.com"]
    if any(d in url_lower for d in music_domains):
        return "music"
    
    # Repository / Code
    repo_keywords = ["github.com", "gitlab.com", "bitbucket.org", "sourceforge.net",
                     "coder.com", "replit.com", "codesandbox.io", "colab.research.google.com"]
    if any(d in url_lower for d in repo_keywords):
        return "repo"
    
    # Educational
    edu_domains = ["coursera.org", "udemy.com", "edx.org", "khanacademy.org",
                   "brilliant.org", "iitm", "byjus.com", "unacademy.com",
                   "vedantu.com", "physicswallah", "pw.live",
                   "classroom.google.com", "meet.google.com"]
    if any(d in url_lower for d in edu_domains):
        return "education"
    
    # Blog / Reading
    blog_keywords = ["medium.com", "blog.", "substack.com", "wordpress.com",
                     "blogger.com", "ghost.org", "dev.to", "hashnode.com",
                     "notion.so", "evernote.com", "obsidian"]
    if any(d in url_lower for d in blog_keywords):
        return "blog"
    
    # News
    news_domains = ["cnn.com", "bbc.com", "bbc.co.uk", "nytimes.com", "reuters.com",
                    "theguardian.com", "wsj.com", "bloomberg.com", "forbes.com",
                    "timesofindia.com", "hindustantimes.com", "ndtv.com"]
    if any(d in url_lower for d in news_domains):
        return "news"
    
    # Shopping
    shop_domains = ["amazon", "flipkart", "myntra", "ajio", "ebay", "walmart",
                    "aliexpress", "etsy.com", "bestbuy.com", "shopify.com"]
    if any(d in url_lower for d in shop_domains):
        return "shopping"
    
    # Email
    email_domains = ["mail.google.com", "outlook.live.com", "outlook.office.com",
                     "mail.yahoo.com", "protonmail.com"]
    if any(d in url_lower for d in email_domains):
        return "email"
    
    return "other"


def search_and_open(query: str, category_hint: str = None) -> str:
    """
    Ultimate general-purpose function: search browser history for ANYTHING
    and open the most relevant result.
    
    Handles: anime, repos, chats, blogs, courses, social media, videos, etc.
    
    Args:
        query: What to search for (e.g. "onepiece", "my chat with arnav", "openclaw repo")
        category_hint: Optional category filter (anime, repo, chat, blog, etc.)
    
    Returns:
        Status string with what was opened or error
    """
    all_results = []
    
    for browser_key, info in BROWSER_PATHS.items():
        db_path = _get_history_db_path(browser_key)
        if not db_path:
            continue
        
        entries = _read_history(db_path, days_back=3650, limit=10000)
        
        for entry in entries:
            if "error" in entry:
                continue
            url_lower = entry["url"].lower()
            title_lower = entry["title"].lower()
            query_lower = query.lower()
            
            # Tokenize query for better matching
            query_tokens = query_lower.split()
            
            # Check if ALL significant tokens appear somewhere
            matches = 0
            for token in query_tokens:
                if len(token) > 2:  # Skip very short tokens
                    if token in url_lower or token in title_lower:
                        matches += 1
            
            if matches > 0:
                entry["browser"] = info["name"]
                entry["match_score"] = matches  # More matches = better
            else:
                continue
            
            # Apply category filter if provided
            if category_hint:
                entry_category = categorize_url(entry["url"], entry["title"])
                if entry_category != category_hint:
                    continue
            
            all_results.append(entry)
    
    if not all_results:
        msg = f"[FAIL] No history entries found matching '{query}'"
        if category_hint:
            msg += f" in category '{category_hint}'"
        msg += ".\n\nTrying web search instead..."
        return msg
    
    # Sort by match score (descending) then by visit time (descending)
    all_results.sort(key=lambda x: (x.get("match_score", 0), x.get("visited_at", "")), reverse=True)
    
    best = all_results[0]
    url = best["url"]
    title = best["title"] or url
    category = categorize_url(url, title)
    
    try:
        import webbrowser
        webbrowser.open(url)
        
        result = f"[OK] Found and opened:\n\n"
        result += f"**{title}**\n"
        result += f"URL: {url}\n"
        result += f"Category: {category}\n"
        result += f"Browser: {best['browser']}\n"
        result += f"Visited: {best['visited_at']}\n"
        
        # Show total matches found
        if len(all_results) > 1:
            result += f"\n[i] Also found {len(all_results) - 1} other matching entries."
        
        return result
    except Exception as e:
        return f"[FAIL] Failed to open browser: {e}\n\nURL was: {url}"


def search_by_category(query: str, category: str) -> str:
    """
    Search history for a query within a specific category.
    """
    all_results = []
    
    for browser_key, info in BROWSER_PATHS.items():
        db_path = _get_history_db_path(browser_key)
        if not db_path:
            continue
        
        entries = _read_history(db_path, days_back=3650, limit=10000)
        
        for entry in entries:
            if "error" in entry:
                continue
            url_lower = entry["url"].lower()
            title_lower = entry["title"].lower()
            query_lower = query.lower()
            
            if query_lower not in url_lower and query_lower not in title_lower:
                continue
            
            entry_category = categorize_url(entry["url"], entry["title"])
            if entry_category == category:
                entry["browser"] = info["name"]
                all_results.append(entry)
    
    if not all_results:
        return f"[FAIL] No {category} entries found matching '{query}'."
    
    all_results.sort(key=lambda x: x["visited_at"], reverse=True)
    
    lines = [f"### {category.upper()} SEARCH: '{query}'", ""]
    lines.append(f"Found {len(all_results)} matching entries (showing top 10):\n")
    
    for i, entry in enumerate(all_results[:10]):
        lines.append(f"**{i+1}. {entry['title'] or '(No title)'}**")
        lines.append(f"   URL: {entry['url']}")
        lines.append(f"   Browser: {entry['browser']}")
        lines.append(f"   Visited: {entry['visited_at']}")
        lines.append("")
    
    return "\n".join(lines)

def list_browser_histories(days_back: int = 7, limit: int = 20) -> str:
    """List recent history from all browsers."""
    all_entries = []
    
    for browser_key, info in BROWSER_PATHS.items():
        db_path = _get_history_db_path(browser_key)
        if not db_path:
            continue
        
        entries = _read_history(db_path, days_back=days_back, limit=limit)
        for entry in entries:
            if "error" not in entry:
                entry["browser"] = info["name"]
                all_entries.append(entry)
    
    if not all_entries:
        return "[FAIL] No recent history found in any browser."
    
    # Sort all by time
    all_entries.sort(key=lambda x: x["visited_at"], reverse=True)
    
    lines = [f"### RECENT BROWSER HISTORY (Last {days_back} days)", ""]
    
    for i, entry in enumerate(all_entries[:limit]):
        lines.append(f"**{i+1}. {entry['title'] or '(No title)'}**")
        lines.append(f"   {entry['url'][:80]}")
        lines.append(f"   {entry['browser']} | {entry['visited_at']}")
        lines.append("")
    
    return "\n".join(lines)

def check_visited_today(url_pattern: str) -> bool:
    """Check if a URL pattern was visited today."""
    today = datetime.now().date()
    
    for browser_key in BROWSER_PATHS:
        db_path = _get_history_db_path(browser_key)
        if not db_path:
            continue
        
        entries = _read_history(db_path, days_back=1, limit=500)
        
        for entry in entries:
            if "error" in entry:
                continue
            
            # Check if visited today
            try:
                visit_date = datetime.fromisoformat(entry["visited_at"]).date()
                if visit_date == today and url_pattern.lower() in entry["url"].lower():
                    return True
            except:
                pass
    
    return False

def get_browser_status() -> str:
    """Check which browsers are installed and their history availability."""
    lines = ["### BROWSER HISTORY STATUS", ""]
    
    for browser_key, info in BROWSER_PATHS.items():
        db_path = _get_history_db_path(browser_key)
        if db_path:
            lines.append(f"[OK] {info['name']}: History available at {db_path}")
        else:
            lines.append(f"[FAIL] {info['name']}: Not installed or history not found")
    
    return "\n".join(lines)

# ─── Integration with Friday Tools ────────────────────────────────

def browser_history_tool(action: str = "status", query: str = "", **kwargs) -> str:
    """
    Friday tool for browser history operations.
    Actions: status, search, open_latest, list_recent, find_and_open, search_category, categorize
    """
    if action == "status":
        return get_browser_status()
    
    if action == "search":
        if not query:
            return "[FAIL] Query required for search."
        return search_all_history(query, days_back=kwargs.get("days_back", 3650))
    
    if action == "open_latest":
        if not query:
            return "[FAIL] Query required. Example: 'open_latest' with query='jarvis'"
        return open_latest_in_browser(query)
    
    if action == "list_recent":
        return list_browser_histories(
            days_back=kwargs.get("days_back", 30),
            limit=kwargs.get("limit", 50)
        )
    
    if action == "find_and_open":
        """General-purpose: search history for ANYTHING and open the best match."""
        if not query:
            return "[FAIL] Query required. Example: 'find_and_open' with query='onepiece episode 1100'"
        category = kwargs.get("category") or kwargs.get("category_hint")
        return search_and_open(query, category_hint=category)
    
    if action == "search_category":
        """Search within a specific category (anime, repo, chat, blog, etc)."""
        if not query or not kwargs.get("category"):
            return "[FAIL] Query and category required. Example: 'search_category' with query='naruto' and category='anime'"
        return search_by_category(query, kwargs["category"])
    
    if action == "categorize":
        """Categorize a URL to understand what type of content it is."""
        url = kwargs.get("url", query)
        title = kwargs.get("title", "")
        cat = categorize_url(url, title)
        return f"Category: {cat}\nURL: {url}\nTitle: {title}"
    
    return f"Unknown action: {action}"

if __name__ == "__main__":
    print("Testing Browser History Tools...\n")
    
    # Test status
    print("--- Browser Status ---")
    print(browser_history_tool("status"))
    
    # Test listing recent
    print("\n--- Recent History (if any) ---")
    print(browser_history_tool("list_recent", days_back=1, limit=5))
    
    # Test search (if you have something in history)
    # print(browser_history_tool("search", query="github"))
