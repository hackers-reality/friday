"""
Friday Browser History - Phase 3.1-3.4
Search across all browsers: Chrome, Brave, Edge, Opera, Firefox, Vivaldi.
Natural language query + time-ordered results.
"""
from __future__ import annotations__

import os
import sys
import webbrowser
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

try:
    from browser_history import get_history, browsers
    BROWSER_HISTORY_AVAILABLE = True
except Exception as e:
    print(f"[BrowserHistory] browser-history not available: {e}")
    BROWSER_HISTORY_AVAILABLE = False


# ─── Search History ────────────────────────────────────────────

def search_browser_history(
    query: str,
    max_results: int = 10,
    browser_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search browser history across all browsers or a specific one.
    Returns time-ordered results (most recent first).
    """
    if not BROWSER_HISTORY_AVAILABLE:
        return [{"error": "browser-history package not installed"}]
    
    results = []
    query_lower = query.lower()
    
    try:
        if browser_name:
            # Search specific browser
            browser_class = getattr(browsers, browser_name, None)
            if not browser_class:
                return [{"error": f"Browser '{browser_name}' not supported"}]
            browser = browser_class()
            histories = browser.fetch_history().histories
        else:
            # Search all browsers
            all_histories = get_history()
            histories = all_histories.histories if all_histories else []
        
        # Filter by query and format results
        for timestamp, url, title in histories:
            if not url or not url.startswith(("http://", "https://")):
                continue
            
            title_str = str(title) if title else ""
            url_str = str(url)
            
            # Match query against title and URL
            if (query_lower in title_str.lower() or 
                query_lower in url_str.lower()):
                
                results.append({
                    "timestamp": timestamp.isoformat() if timestamp else "",
                    "url": url_str,
                    "title": title_str,
                    "datetime": timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "",
                })
        
        # Sort by timestamp (most recent first)
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return results[:max_results]
    
    except Exception as e:
        return [{"error": str(e)}]


def find_and_open_url(
    query: str,
    browser_name: Optional[str] = None,
    open_in_browser: bool = True,
) -> str:
    """
    Search history for a URL, find the most recent match, and optionally open it.
    Returns a formatted report.
    """
    results = search_browser_history(query, max_results=5, browser_name=browser_name)
    
    if not results:
        return f"No results found for '{query}' in browser history."
    
    if "error" in results[0]:
        return f"Search error: {results[0]['error']}"
    
    if not results:
        return f"No history entries found matching '{query}'."
    
    # Get the most recent result
    best = results[0]
    url = best["url"]
    title = best.get("title", "Unknown")
    dt = best.get("datetime", "Unknown time")
    
    report_lines = [
        f"### Browser History Search: '{query}'",
        f"**Found:** {len(results)} result(s)",
        f"**Most Recent:**",
        f"- Title: {title}",
        f"- URL: {url}",
        f"- Time: {dt}",
        "",
    ]
    
    # Add more results
    if len(results) > 1:
        report_lines.append("**Other Results:**")
        for i, r in enumerate(results[1:5], 2):
            report_lines.append(
                f"{i}. {r.get('title', 'Unknown')} - {r.get('datetime', '')}\n   {r['url']}"
            )
    
    # Open in browser if requested
    if open_in_browser and url:
        try:
            webbrowser.open(url)
            report_lines.append(f"\n✅ Opened in browser: {url}")
        except Exception as e:
            report_lines.append(f"\n❌ Failed to open browser: {e}")
    
    return "\n".join(report_lines)


def get_history_for_date(
    date: str,
    browser_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get all history entries for a specific date (format: YYYY-MM-DD).
    """
    if not BROWSER_HISTORY_AVAILABLE:
        return []
    
    try:
        if browser_name:
            browser_class = getattr(browsers, browser_name, None)
            if not browser_class:
                return []
            browser = browser_class()
            histories = browser.fetch_history().histories
        else:
            histories = get_history().histories
        
        results = []
        for timestamp, url, title in histories:
            if timestamp and timestamp.strftime("%Y-%m-%d") == date:
                results.append({
                    "timestamp": timestamp.isoformat(),
                    "url": str(url),
                    "title": str(title) if title else "",
                    "datetime": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                })
        
        results.sort(key=lambda x: x.get("timestamp", ""))
        return results
    
    except Exception as e:
        print(f"[BrowserHistory] Date filter error: {e}")
        return []


def check_visited_today(url_pattern: str) -> bool:
    """
    Check if a URL pattern was visited today.
    Used by goal enforcement system.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    entries = get_history_for_date(today)
    
    for entry in entries:
        if url_pattern.lower() in entry.get("url", "").lower():
            return True
    return False


def format_history_report(results: List[Dict[str, Any]]) -> str:
    """Format history results into a readable report."""
    if not results:
        return "No history entries found."
    
    if "error" in results[0]:
        return f"Error: {results[0]['error']}"
    
    lines = ["### Browser History Results", ""]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **{r.get('title', 'Unknown')}**")
        lines.append(f"   URL: {r['url']}")
        lines.append(f"   Time: {r.get('datetime', 'Unknown')}")
        lines.append("")
    
    return "\n".join(lines)


# ─── Integration with Friday Tools ────────────────────────────────

def browser_history_search(query: str, max_results: int = 5) -> str:
    """
    Search browser history by natural language query.
    This function is exposed as a Friday tool.
    """
    if not BROWSER_HISTORY_AVAILABLE:
        return "Browser history package not installed. Install with: pip install browser-history"
    
    results = search_browser_history(query, max_results=max_results)
    
    if not results:
        return f"No browser history found matching '{query}'."
    
    if "error" in results[0]:
        return f"Search error: {results[0]['error']}"
    
    return format_history_report(results)


def browser_history_open(query: str) -> str:
    """
    Search for a URL in history and open the most recent match.
    Example: "open the repo I was seeing about jarvis by vierisid"
    """
    return find_and_open_url(query, open_in_browser=True)


def browser_history_check_today(url_pattern: str) -> str:
    """
    Check if a URL pattern was visited today.
    Returns a simple yes/no + details.
    """
    visited = check_visited_today(url_pattern)
    
    if visited:
        # Get today's entries that match
        today = datetime.now().strftime("%Y-%m-%d")
        entries = get_history_for_date(today)
        matching = [e for e in entries if url_pattern.lower() in e.get("url", "").lower()]
        
        lines = [f"✅ Visited {len(matching)} time(s) today matching '{url_pattern}':"]
        for e in matching[:5]:
            lines.append(f"  - {e.get('title', 'Unknown')} at {e.get('datetime', '')}")
        return "\n".join(lines)
    
    return f"❌ No visits today matching '{url_pattern}'."


if __name__ == "__main__":
    # Test
    print("Testing Browser History...")
    
    # Search test
    print("\n--- Search Test ---")
    results = search_browser_history("github", max_results=3)
    print(format_history_report(results))
    
    # Check today test
    print("\n--- Today Check Test ---")
    print(browser_history_check_today("github"))
