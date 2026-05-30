"""
Web Scraping & Parsing tools
Libraries: beautifulsoup4, lxml, scrapy, feedparser, newspaper3k,
readability-lxml, trafilatura, html2text, markdownify, cloudscraper, curl-cffi
"""
import asyncio
import json
import os
from typing import Any

HAS_REQUESTS = False
HAS_BS4 = False
HAS_LXML = False
HAS_FEEDPARSER = False
HAS_NEWSPAPER = False
HAS_READABILITY = False
HAS_TRAFILATURA = False
HAS_HTML2TEXT = False
HAS_MARKDOWNIFY = False
HAS_CLOUDSCRAPER = False
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    pass
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    pass
try:
    import lxml
    HAS_LXML = True
except ImportError:
    pass
try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    pass
try:
    from newspaper import Article
    HAS_NEWSPAPER = True
except ImportError:
    pass
try:
    from readability import Document
    HAS_READABILITY = True
except ImportError:
    pass
try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    pass
try:
    import html2text
    HAS_HTML2TEXT = True
except ImportError:
    pass
try:
    import markdownify
    HAS_MARKDOWNIFY = True
except ImportError:
    pass
try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    pass


async def fetch_page(url: str, method: str = "GET", headers: dict[str, str] | None = None,
                     use_cloudscraper: bool = False) -> dict[str, Any]:
    if use_cloudscraper and HAS_CLOUDSCRAPER:
        try:
            scraper = cloudscraper.create_scraper()
            resp = await asyncio.get_event_loop().run_in_executor(None, lambda: scraper.get(url, headers=headers, timeout=30))
            return {"url": url, "status": resp.status_code, "content": resp.text[:50000], "headers": dict(resp.headers)}
        except Exception as e:
            return {"error": str(e)}
    if HAS_REQUESTS:
        try:
            hdrs = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", **(headers or {})}
            resp = await asyncio.get_event_loop().run_in_executor(None, lambda: requests.get(url, headers=hdrs, timeout=30))
            return {"url": url, "status": resp.status_code, "content": resp.text[:50000], "headers": dict(resp.headers)}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "HTTP library not available"}


async def extract_html(html: str, extract_format: str = "text") -> dict[str, Any]:
    if not HAS_BS4:
        return {"error": "beautifulsoup4 not installed"}
    try:
        soup = await asyncio.get_event_loop().run_in_executor(None, lambda: BeautifulSoup(html, "lxml" if HAS_LXML else "html.parser"))
        if extract_format == "text":
            text = soup.get_text(separator="\n", strip=True)
            return {"text": text[:50000], "length": len(text), "title": soup.title.string if soup.title else None}
        elif extract_format == "links":
            links = [{"href": a.get("href"), "text": a.get_text(strip=True)[:100]} for a in soup.find_all("a", href=True)]
            return {"links": links[:100], "count": len(links)}
        elif extract_format == "images":
            images = [{"src": img.get("src"), "alt": img.get("alt")} for img in soup.find_all("img", src=True)]
            return {"images": images[:50], "count": len(images)}
        elif extract_format == "metadata":
            meta = {m.get("name") or m.get("property"): m.get("content") for m in soup.find_all("meta") if m.get("content")}
            return {"metadata": meta}
        elif extract_format == "all":
            text = soup.get_text(separator="\n", strip=True)
            links = [{"href": a.get("href"), "text": a.get_text(strip=True)[:100]} for a in soup.find_all("a", href=True)]
            images = [{"src": img.get("src"), "alt": img.get("alt")} for img in soup.find_all("img", src=True)]
            meta = {m.get("name") or m.get("property"): m.get("content") for m in soup.find_all("meta") if m.get("content")}
            return {"title": soup.title.string if soup.title else None, "text": text[:50000], "links": links[:100],
                    "images": images[:50], "metadata": meta}
        return {"error": f"Unknown format: {extract_format}"}
    except Exception as e:
        return {"error": str(e)}


async def extract_article(url: str) -> dict[str, Any]:
    if HAS_NEWSPAPER:
        try:
            article = Article(url)
            await asyncio.get_event_loop().run_in_executor(None, lambda: article.download())
            await asyncio.get_event_loop().run_in_executor(None, lambda: article.parse())
            text = article.text
            return {"url": url, "title": article.title, "authors": article.authors,
                    "publish_date": str(article.publish_date) if article.publish_date else None,
                    "text": text[:50000], "top_image": article.top_image,
                    "keywords": article.keywords[:20], "summary": article.summary[:1000]}
        except Exception as e:
            return {"error": str(e), "library": "newspaper3k"}
    if HAS_READABILITY:
        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            doc = Document(resp.text)
            return {"url": url, "title": doc.title(), "content": doc.summary()[:50000]}
        except Exception as e:
            return {"error": str(e), "library": "readability"}
    if HAS_TRAFILATURA:
        try:
            downloaded = await asyncio.get_event_loop().run_in_executor(None, lambda: trafilatura.fetch_url(url))
            text = await asyncio.get_event_loop().run_in_executor(None, lambda: trafilatura.extract(downloaded))
            return {"url": url, "text": text[:50000]}
        except Exception as e:
            return {"error": str(e), "library": "trafilatura"}
    return {"error": "No article extraction library available. Install: newspaper3k, readability-lxml, or trafilatura"}


async def html_to_markdown(html: str) -> dict[str, Any]:
    if HAS_MARKDOWNIFY:
        try:
            md = await asyncio.get_event_loop().run_in_executor(None, lambda: markdownify.markdownify(html, heading_style="ATX"))
            return {"markdown": md[:50000], "length": len(md)}
        except Exception as e:
            return {"error": str(e)}
    if HAS_HTML2TEXT:
        try:
            h = html2text.HTML2Text()
            h.ignore_links = False
            md = await asyncio.get_event_loop().run_in_executor(None, lambda: h.handle(html))
            return {"markdown": md[:50000], "length": len(md)}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "html2text or markdownify not installed"}


async def parse_feed(feed_url: str, limit: int = 10) -> dict[str, Any]:
    if not HAS_FEEDPARSER:
        return {"error": "feedparser not installed"}
    try:
        feed = await asyncio.get_event_loop().run_in_executor(None, lambda: feedparser.parse(feed_url))
        entries = []
        for e in feed.entries[:limit]:
            entries.append({"title": e.get("title"), "link": e.get("link"),
                           "published": e.get("published"), "summary": e.get("summary", "")[:500],
                           "author": e.get("author")})
        return {"feed_title": feed.feed.get("title"), "feed_link": feed.feed.get("link"),
                "total_entries": len(feed.entries), "entries": entries}
    except Exception as e:
        return {"error": str(e)}


async def xpath_extract(html: str, expression: str) -> dict[str, Any]:
    if not HAS_LXML:
        return {"error": "lxml not installed"}
    try:
        from lxml import html as lh
        tree = await asyncio.get_event_loop().run_in_executor(None, lambda: lh.fromstring(html))
        results = tree.xpath(expression)
        return {"expression": expression, "results": [str(r) for r in results][:100], "count": len(results)}
    except Exception as e:
        return {"error": str(e)}
