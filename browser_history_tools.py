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
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "friday_memory")
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"history_temp_{int(time.time())}.db")
    try:
        shutil.copy2(src, temp_path)
        return temp_path
    except Exception as e:
        # If copy fails (very fresh Chrome), try direct
        return src

def _read_history(db_path: str, days_back: int = 30, limit: int = 1000) -> List[Dict[str, Any]]:
    """Read history entries from a Chrome-format history DB."""
    temp_path = None
    try:
        # Copy to avoid lock
        temp_path = _copy_history_db(db_path)
        
        conn = sqlite3.connect(temp_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Calculate cutoff
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

def search_all_history(query: str, days_back: int = 30, limit_per_browser: int = 50) -> str:
    """
    Search all installed browsers for a query in URL or title.
    Returns the most recent matching entry across all browsers.
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
        return f"❌ No history entries found matching '{query}' in any browser."
    
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

def find_latest_by_keyword(keyword: str, days_back: int = 90) -> Optional[Dict[str, Any]]:
    """
    Find the most recent history entry matching a keyword.
    Returns the entry dict or None.
    """
    all_results = []
    
    for browser_key, info in BROWSER_PATHS.items():
        db_path = _get_history_db_path(browser_key)
        if not db_path:
            continue
        
        entries = _read_history(db_path, days_back=days_back, limit=200)
        
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
    This is the "Friday open the repo I was seeing about jarvis" feature.
    """
    # First, try to find in history
    entry = find_latest_by_keyword(query, days_back=90)
    
    if not entry:
        return f"❌ No recent history found for '{query}'.\n\nTrying web search instead..."
    
    url = entry["url"]
    title = entry["title"] or url
    
    try:
        import webbrowser
        webbrowser.open(url)
        return f"✅ Opened in browser:\n\n**{title}**\nURL: {url}\n\n(From {entry['visited_at']})"
    except Exception as e:
        return f"❌ Failed to open browser: {e}\n\nURL was: {url}"

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
        return "❌ No recent history found in any browser."
    
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
            lines.append(f"✅ {info['name']}: History available at {db_path}")
        else:
            lines.append(f"❌ {info['name']}: Not installed or history not found")
    
    return "\n".join(lines)

# ─── Integration with Friday Tools ────────────────────────────────

def browser_history_tool(action: str = "status", query: str = "", **kwargs) -> str:
    """
    Friday tool for browser history operations.
    Actions: status, search, open_latest, list_recent
    """
    if action == "status":
        return get_browser_status()
    
    if action == "search":
        if not query:
            return "❌ Query required for search."
        return search_all_history(query, days_back=kwargs.get("days_back", 30))
    
    if action == "open_latest":
        if not query:
            return "❌ Query required. Example: 'open_latest' with query='jarvis'"
        return open_latest_in_browser(query)
    
    if action == "list_recent":
        return list_browser_histories(
            days_back=kwargs.get("days_back", 7),
            limit=kwargs.get("limit", 20)
        )
    
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
