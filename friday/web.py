"""
Friday Web - Web scraping, search engines, and API interactions.
Advanced web automation, content extraction, search, and API clients.
"""
from __future__ import annotations

import os
import sys
import json
import time
import re
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs
import base64


# ─── Web Scraping ────────────────────────────#

class WebScraper:
    """Advanced web scraping with multiple backends."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
    def fetch(
        self,
        url: str,
        method: str = "GET",
        headers: Dict = None,
        params: Dict = None,
        data: Dict = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Fetch a URL and return content."""
        try:
            req_headers = self.session.headers.copy()
            if headers:
                req_headers.update(headers)
            
            response = self.session.request(
                method=method,
                url=url,
                headers=req_headers,
                params=params,
                data=data,
                timeout=timeout,
            )
            
            return {
                "success": True,
                "status_code": response.status_code,
                "url": response.url,
                "content": response.text,
                "headers": dict(response.headers),
                "encoding": response.encoding,
                "elapsed": response.elapsed.total_seconds(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    def extract_links(self, url: str, selector: str = "a") -> Dict[str, Any]:
        """Extract links from a page."""
        try:
            from bs4 import BeautifulSoup
            
            result = self.fetch(url)
            if not result["success"]:
                return result
            
            soup = BeautifulSoup(result["content"], "html.parser")
            links = []
            
            for element in soup.select(selector):
                href = element.get("href")
                if href:
                    full_url = urljoin(url, href)
                    links.append({
                        "text": element.get_text(strip=True),
                        "href": full_url,
                    })
            
            return {
                "success": True,
                "url": url,
                "links": links,
                "count": len(links),
            }
        except ImportError:
            return {
                "success": False,
                "error": "BeautifulSoup not available. Install: pip install beautifulsoup4 lxml",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    def extract_text(self, url: str, selector: str = "body") -> Dict[str, Any]:
        """Extract text content from a page."""
        try:
            from bs4 import BeautifulSoup
            
            result = self.fetch(url)
            if not result["success"]:
                return result
            
            soup = BeautifulSoup(result["content"], "html.parser")
            
            elements = soup.select(selector)
            texts = [elem.get_text(strip=True) for elem in elements]
            
            return {
                "success": True,
                "url": url,
                "texts": texts,
                "combined": "\n".join(texts),
            }
        except ImportError:
            return {
                "success": False,
                "error": "BeautifulSoup not available.",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    def extract_images(self, url: str) -> Dict[str, Any]:
        """Extract images from a page."""
        try:
            from bs4 import BeautifulSoup
            
            result = self.fetch(url)
            if not result["success"]:
                return result
            
            soup = BeautifulSoup(result["content"], "html.parser")
            images = []
            
            for img in soup.find_all("img"):
                src = img.get("src") or img.get("data-src")
                if src:
                    full_url = urljoin(url, src)
                    images.append({
                        "src": full_url,
                        "alt": img.get("alt", ""),
                        "title": img.get("title", ""),
                    })
            
            return {
                "success": True,
                "url": url,
                "images": images,
                "count": len(images),
            }
        except ImportError:
            return {
                "success": False,
                "error": "BeautifulSoup not available.",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    def search_engine(self, query: str, engine: str = "duckduckgo") -> Dict[str, Any]:
        """Search the web using various engines."""
        if engine == "duckduckgo":
            return self._search_duckduckgo(query)
        elif engine == "bing":
            return self._search_bing(query)
        elif engine == "google":
            return self._search_google(query)
        else:
            return {
                "success": False,
                "error": f"Unknown engine: {engine}",
            }

    def _search_google(self, query: str) -> Dict[str, Any]:
        """Search Google via HTML scraping with multiple selector fallbacks."""
        try:
            from bs4 import BeautifulSoup

            url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=10"
            result = self.fetch(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            })

            if not result["success"]:
                return result

            soup = BeautifulSoup(result["content"], "html.parser")
            results = []

            # Strategy 1: Modern Google (div.g with h3)
            for g in soup.select("div.g"):
                title_el = g.select_one("h3")
                link_el = g.select_one("a")
                snippet_el = g.select_one(".VwiC3b") or g.select_one(".st") or g.select_one("[data-sncf]")
                if title_el and link_el:
                    href = link_el.get("href", "")
                    if href.startswith("/url?q="):
                        href = href.split("?q=")[1].split("&")[0]
                    results.append({
                        "title": title_el.get_text(strip=True),
                        "url": href,
                        "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                    })

            # Strategy 2: Alternative selectors if no results
            if not results:
                for block in soup.select("[data-hveid]"):
                    title_el = block.select_one("h3, .DKV0Md, .LC20lb")
                    link_el = block.select_one("a")
                    snippet_el = block.select_one(".st, .VwiC3b, .lEBKkf")
                    if title_el and link_el:
                        href = link_el.get("href", "")
                        if href.startswith("/url?q="):
                            href = href.split("?q=")[1].split("&")[0]
                        results.append({
                            "title": title_el.get_text(strip=True),
                            "url": href,
                            "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                        })

            return {
                "success": len(results) > 0,
                "query": query,
                "engine": "google",
                "results": results,
                "count": len(results),
            } if results else {
                "success": False,
                "query": query,
                "engine": "google",
                "error": "No results parsed. Google may have changed their markup.",
            }
        except ImportError:
            return {"success": False, "error": "BeautifulSoup not available."}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _search_duckduckgo(self, query: str) -> Dict[str, Any]:
        """Search DuckDuckGo using ddgs library."""
        try:
            from ddgs import DDGS
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=10):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    })
            return {
                "success": bool(results),
                "query": query,
                "engine": "duckduckgo",
                "results": results,
                "count": len(results),
            }
        except ImportError:
            # Fallback to old HTML parsing
            try:
                from bs4 import BeautifulSoup
                url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
                result = self.fetch(url)
                if not result["success"]:
                    return result
                soup = BeautifulSoup(result["content"], "html.parser")
                results = []
                for result_div in soup.select(".result"):
                    title_elem = result_div.select_one(".result__title")
                    link_elem = result_div.select_one(".result__url")
                    snippet_elem = result_div.select_one(".result__snippet")
                    if title_elem:
                        results.append({
                            "title": title_elem.get_text(strip=True),
                            "url": link_elem.get_text(strip=True) if link_elem else "",
                            "snippet": snippet_elem.get_text(strip=True) if snippet_elem else "",
                        })
                return {
                    "success": True,
                    "query": query,
                    "engine": "duckduckgo",
                    "results": results,
                    "count": len(results),
                }
            except Exception as e2:
                return {"success": False, "error": str(e2)}
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    def _search_bing(self, query: str) -> Dict[str, Any]:
        """Search Bing."""
        try:
            from bs4 import BeautifulSoup
            
            url = f"https://www.bing.com/search?q={requests.utils.quote(query)}"
            result = self.fetch(url)
            
            if not result["success"]:
                return result
            
            soup = BeautifulSoup(result["content"], "html.parser")
            results = []
            
            for result_div in soup.select(".b_algo"):
                title_elem = result_div.select_one("h2")
                link_elem = title_elem.select_one("a") if title_elem else None
                snippet_elem = result_div.select_one(".b_caption p")
                
                if title_elem and link_elem:
                    results.append({
                        "title": title_elem.get_text(strip=True),
                        "url": link_elem.get("href", ""),
                        "snippet": snippet_elem.get_text(strip=True) if snippet_elem else "",
                    })
            
            return {
                "success": True,
                "query": query,
                "engine": "bing",
                "results": results,
                "count": len(results),
            }
        except ImportError:
            return {
                "success": False,
                "error": "BeautifulSoup not available.",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


# ─── API Client ────────────────────────────#

class APIClient:
    """Generic API client for REST APIs."""
    
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "Friday/2.0",
        })
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
    
    def request(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        data: Dict = None,
        json_data: Dict = None,
        headers: Dict = None,
    ) -> Dict[str, Any]:
        """Make an API request."""
        url = self.base_url + endpoint if self.base_url else endpoint
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json_data,
                headers=headers,
                timeout=30,
            )
            
            # Try to parse JSON
            try:
                response_json = response.json()
            except:
                response_json = None
            
            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "url": response.url,
                "data": response_json,
                "text": response.text,
                "headers": dict(response.headers),
                "elapsed": response.elapsed.total_seconds(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    def get(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        return self.request("GET", endpoint, params=params)
    
    def post(self, endpoint: str, data: Dict = None, json_data: Dict = None) -> Dict[str, Any]:
        return self.request("POST", endpoint, data=data, json_data=json_data)
    
    def put(self, endpoint: str, data: Dict = None, json_data: Dict = None) -> Dict[str, Any]:
        return self.request("PUT", endpoint, data=data, json_data=json_data)
    
    def delete(self, endpoint: str) -> Dict[str, Any]:
        return self.request("DELETE", endpoint)
    
    def graphql(self, endpoint: str, query: str, variables: Dict = None) -> Dict[str, Any]:
        """Make a GraphQL request."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        return self.request("POST", endpoint, json_data=payload)


# ─── Content Extraction ────────────────────────────#

class ContentExtractor:
    """Extract structured content from web pages."""
    
    @staticmethod
    def extract_article(url: str) -> Dict[str, Any]:
        """Extract article content (title, text, author, date)."""
        try:
            import requests
            from bs4 import BeautifulSoup
            import dateutil.parser
            
            response = requests.get(url, timeout=30)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Title
            title = None
            for selector in ["h1", ".title", "#title", "title"]:
                elem = soup.select_one(selector)
                if elem:
                    title = elem.get_text(strip=True)
                    break
            
            # Text - get paragraphs
            paragraphs = []
            for p in soup.select("p"):
                text = p.get_text(strip=True)
                if len(text) > 50:  # Filter short paragraphs
                    paragraphs.append(text)
            
            # Author
            author = None
            for selector in ["[rel=author]", ".author", "#author", "[itemprop=author]"]:
                elem = soup.select_one(selector)
                if elem:
                    author = elem.get_text(strip=True)
                    break
            
            # Date
            date = None
            for selector in ["[itemprop=datePublished]", ".date", ".published", "time"]:
                elem = soup.select_one(selector)
                if elem:
                    date_str = elem.get("datetime") or elem.get_text(strip=True)
                    try:
                        date = dateutil.parser.parse(date_str).isoformat()
                        break
                    except:
                        pass
            
            return {
                "success": True,
                "url": url,
                "title": title,
                "text": "\n\n".join(paragraphs),
                "author": author,
                "date": date,
                "word_count": sum(len(p.split()) for p in paragraphs),
            }
        except ImportError:
            return {
                "success": False,
                "error": "Required libraries not available. Install: pip install beautifulsoup4 lxml python-dateutil",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    @staticmethod
    def extract_table(url: str, selector: str = "table") -> Dict[str, Any]:
        """Extract table data from a page."""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            response = requests.get(url, timeout=30)
            soup = BeautifulSoup(response.text, "html.parser")
            
            tables = []
            for table in soup.select(selector):
                rows = []
                for tr in table.select("tr"):
                    cells = []
                    for td in tr.select("td, th"):
                        cells.append(td.get_text(strip=True))
                    if cells:
                        rows.append(cells)
                tables.append(rows)
            
            return {
                "success": True,
                "url": url,
                "tables": tables,
                "table_count": len(tables),
            }
        except ImportError:
            return {
                "success": False,
                "error": "BeautifulSoup not available.",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


# ─── Web Tool for Friday ────────────────────────────#

def web_tool(
    action: str = "status",
    url: str = None,
    query: str = None,
    selector: str = None,
    params: Dict = None,
) -> str:
    """
    Friday tool for web operations.
    Actions: status, fetch, links, text, images, search, api_get, api_post,
            extract_article, extract_table
    """
    if action == "status":
        lines = ["### WEB STATUS", ""]
        lines.append("**Available Features**:")
        lines.append("  - Web scraping (BeautifulSoup)")
        lines.append("  - Search engines (DuckDuckGo, Bing)")
        lines.append("  - REST API client")
        lines.append("  - GraphQL support")
        lines.append("  - Content extraction (articles, tables)")
        return "\n".join(lines)
    
    if action == "fetch":
        if not url:
            return "[FAIL] URL required."
        scraper = WebScraper()
        result = scraper.fetch(url)
        if result["success"]:
            return f"### FETCH\n\n**Status**: {result['status_code']}\n**Content Length**: {len(result['content'])} chars"
        else:
            return f"[FAIL] Fetch error: {result.get('error', 'Unknown')}"
    
    if action == "links":
        if not url:
            return "[FAIL] URL required."
        scraper = WebScraper()
        result = scraper.extract_links(url, selector or "a")
        if result["success"]:
            links_preview = "\n".join([f"  - {l['text'][:50]}: {l['href'][:60]}" for l in result["links"][:10]])
            return f"### LINKS\n\nFound {result['count']} links:\n{links_preview}"
        else:
            return f"[FAIL] Links error: {result.get('error', 'Unknown')}"
    
    if action == "text":
        if not url:
            return "[FAIL] URL required."
        scraper = WebScraper()
        result = scraper.extract_text(url, selector or "body")
        if result["success"]:
            preview = result["combined"][:500]
            return f"### TEXT EXTRACTION\n\n{preview}..."
        else:
            return f"[FAIL] Text extraction error: {result.get('error', 'Unknown')}"
    
    if action == "images":
        if not url:
            return "[FAIL] URL required."
        scraper = WebScraper()
        result = scraper.extract_images(url)
        if result["success"]:
            return f"### IMAGES\n\nFound {result['count']} images."
        else:
            return f"[FAIL] Images error: {result.get('error', 'Unknown')}"
    
    if action == "search":
        if not query:
            return "[FAIL] Query required."
        scraper = WebScraper()
        result = scraper.search_engine(query)
        if result["success"]:
            results_preview = "\n".join([f"  {i+1}. {r['title'][:60]}" for i, r in enumerate(result["results"][:5])])
            return f"### SEARCH RESULTS\n\nQuery: {query}\nFound {result['count']} results:\n{results_preview}"
        else:
            return f"[FAIL] Search error: {result.get('error', 'Unknown')}"
    
    if action == "api_get":
        if not url:
            return "[FAIL] URL required."
        client = APIClient()
        result = client.get(url, params=params)
        if result["success"]:
            return f"### API GET\n\n**Status**: {result['status_code']}\n**Data**: {json.dumps(result['data'], indent=2)[:500]}"
        else:
            return f"[FAIL] API error: {result.get('error', 'Unknown')}"
    
    if action == "api_post":
        if not url:
            return "[FAIL] URL required."
        client = APIClient()
        result = client.post(url, json_data=params)
        if result["success"]:
            return f"### API POST\n\n**Status**: {result['status_code']}\n**Response**: {json.dumps(result['data'], indent=2)[:500]}"
        else:
            return f"[FAIL] API error: {result.get('error', 'Unknown')}"
    
    if action == "extract_article":
        if not url:
            return "[FAIL] URL required."
        result = ContentExtractor.extract_article(url)
        if result["success"]:
            return f"### ARTICLE EXTRACTION\n\n**Title**: {result['title']}\n**Author**: {result.get('author', 'Unknown')}\n**Date**: {result.get('date', 'Unknown')}\n**Word Count**: {result['word_count']}"
        else:
            return f"[FAIL] Extraction error: {result.get('error', 'Unknown')}"
    
    if action == "extract_table":
        if not url:
            return "[FAIL] URL required."
        result = ContentExtractor.extract_table(url, selector or "table")
        if result["success"]:
            return f"### TABLE EXTRACTION\n\nFound {result['table_count']} tables."
        else:
            return f"[FAIL] Extraction error: {result.get('error', 'Unknown')}"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Friday Web...\n")
    
    # Test fetch
    print("--- Fetch ---")
    print(web_tool("fetch", url="https://example.com"))
    
    # Test search
    print("\n--- Search ---")
    print(web_tool("search", query="Python programming"))
