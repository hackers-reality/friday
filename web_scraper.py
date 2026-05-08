"""
Friday Advanced Web Scraper - Research-grade web scraping.
Uses multiple methods: requests, BeautifulSoup, Playwright for JS-heavy sites.
"""
from __future__ import annotations

import os
import re
import json
from typing import Optional, Dict, List, Any
from urllib.parse import urlparse


# ─── Simple Scraper (requests + BeautifulSoup) ────────────────────────────#

def simple_scrape(url: str, extract: str = "text") -> str:
    """
    Simple web scraper using requests + BeautifulSoup.
    extract: text, links, images, tables, all
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        if extract == "text":
            # Remove script/style
            for s in soup(["script", "style"]):
                s.decompose()
            return soup.get_text(separator="\n", strip=True)[:5000]
        
        elif extract == "links":
            links = [a.get("href") for a in soup.find_all("a", href=True)]
            return "\n".join(links[:50])
        
        elif extract == "images":
            imgs = [img.get("src") for img in soup.find_all("img", src=True)]
            return "\n".join(imgs[:50])
        
        elif extract == "tables":
            tables = []
            for table in soup.find_all("table"):
                rows = []
                for tr in table.find_all("tr"):
                    cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                    rows.append(" | ".join(cells))
                tables.append("\n".join(rows))
            return "\n\n".join(tables)[:5000]
        
        elif extract == "all":
            return {
                "title": soup.title.string if soup.title else "No title",
                "text": soup.get_text()[:3000],
                "links_count": len(soup.find_all("a")),
                "images_count": len(soup.find_all("img")),
            }
        
        return soup.get_text()[:3000]
        
    except ImportError:
        return "[FAIL] BeautifulSoup not installed. Run: pip install beautifulsoup4"
    except Exception as e:
        return f"[FAIL] Scraping error: {e}"


# ─── Advanced Scraper (Playwright for JS sites) ────────────────────────────#

def advanced_scrape(url: str, wait_for: str = "body", timeout: int = 30000) -> str:
    """
    Advanced scraper using Playwright for JavaScript-heavy sites.
    wait_for: CSS selector to wait for, or "load", "domcontentloaded", "networkidle"
    """
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            
            if wait_for not in ("load", "domcontentloaded", "networkidle"):
                try:
                    page.wait_for_selector(wait_for, timeout=5000)
                except:
                    pass  # Continue anyway
            
            content = page.content()
            text = page.inner_text("body")
            
            browser.close()
            
            return f"URL: {url}\n\n{text[:5000]}"
            
    except ImportError:
        return "[FAIL] Playwright not installed. Run: pip install playwright && playwright install chromium"
    except Exception as e:
        return f"[FAIL] Advanced scraping error: {e}"


# ─── Web Research Tool ────────────────────────────────────#

def web_research_tool(
    url: str = None,
    query: str = None,
    search_first: bool = False,
    extract: str = "text",
    use_advanced: bool = False,
) -> str:
    """
    Friday tool for web research.
    If search_first=True, will search for query and scrape top result.
    """
    if not url and not query:
        return "[FAIL] URL or query required."
    
    # Search first if needed
    if search_first and query:
        try:
            from friday_tools import web_search
            results = web_search(query, count=1)
            # Extract URL from search results
            urls = re.findall(r'https?://[^\s<>"\']+', results)
            if urls:
                url = urls[0]
            else:
                return f"[FAIL] No URLs found for query: {query}"
        except Exception as e:
            return f"[FAIL] Search error: {e}"
    
    if not url:
        return "[FAIL] No URL to scrape."
    
    # Validate URL
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return f"[FAIL] Invalid URL: {url}"
    
    # Choose scraper
    if use_advanced:
        return advanced_scrape(url)
    else:
        return simple_scrape(url, extract)


# ─── Batch Scrape Tool ────────────────────────────────────#

def batch_scrape(urls: List[str], extract: str = "text") -> str:
    """Scrape multiple URLs and return combined results."""
    results = []
    for i, url in enumerate(urls[:10], 1):  # Limit to 10
        results.append(f"=== Result {i}: {url} ===")
        results.append(simple_scrape(url, extract))
        results.append("")
    return "\n".join(results)


if __name__ == "__main__":
    print("Testing Web Scraper...")
    
    # Test simple scrape
    print("\n--- Simple Scrape Test ---")
    result = simple_scrape("https://example.com")
    print(result[:500])
    
    # Test with extract options
    print("\n--- Extract Links ---")
    result = simple_scrape("https://example.com", extract="links")
    print(result[:300])
