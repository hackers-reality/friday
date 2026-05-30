"""
Web Search tools — DuckDuckGo, Brave Search, Tavily (AI-optimised).

Libraries:
    - duckduckgo_search (optional)
    - httpx / requests    (optional)
    - tavily-python       (optional)
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Optional

from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

# ── Lazy dependency flags ──────────────────────────────────────────────
HAS_DUCKDUCKGO = False
HAS_BRAVE = False  # uses httpx
HAS_TAVILY = False
HAS_HTTPX = False
HAS_REQUESTS = False

try:
    from duckduckgo_search import DDGS
    HAS_DUCKDUCKGO = True
except ImportError:
    pass

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    try:
        import requests
        HAS_REQUESTS = True
    except ImportError:
        pass

try:
    from tavily import TavilyClient
    HAS_TAVILY = True
except ImportError:
    pass


# ── Dataclasses ────────────────────────────────────────────────────────
@dataclass
class SearchItem:
    """A single search result entry."""
    title: str
    url: str
    snippet: str
    source: Optional[str] = None
    published: Optional[str] = None


@dataclass
class SearchResult:
    """Structured result returned by every search tool function."""
    query: str
    engine: str
    results: list[SearchItem] = field(default_factory=list)
    answer: Optional[str] = None
    error: Optional[str] = None


# ── DuckDuckGo ─────────────────────────────────────────────────────────
async def search_duckduckgo(
    query: str,
    max_results: int = 10,
) -> SearchResult:
    """Search the web using DuckDuckGo (free, no API key required).

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (default 10).

    Returns:
        SearchResult with title/url/snippet entries.
    """
    if not HAS_DUCKDUCKGO:
        return SearchResult(
            query=query,
            engine="duckduckgo",
            error="duckduckgo_search package not installed. Run: pip install duckduckgo_search",
        )

    def _sync_search() -> SearchResult:
        try:
            with DDGS() as ddgs:
                raw = list(ddgs.text(query, max_results=max_results))
            items = []
            for r in raw:
                items.append(SearchItem(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                    source="duckduckgo",
                    published=r.get("date", None),
                ))
            return SearchResult(query=query, engine="duckduckgo", results=items)
        except Exception as exc:
            logger.exception("DuckDuckGo search failed")
            return SearchResult(query=query, engine="duckduckgo", error=str(exc))

    return await asyncio.to_thread(_sync_search)


# ── Brave Search ──────────────────────────────────────────────────────
async def search_brave(
    query: str,
    count: int = 10,
) -> SearchResult:
    """Search the web using the Brave Search API.

    Requires the BRAVE_API_KEY environment variable.
    Free tier: 2000 queries/month.

    Args:
        query: The search query string.
        count: Number of results to return (default 10, max 20).

    Returns:
        SearchResult with title/url/snippet/published entries.
    """
    api_key = os.environ.get("BRAVE_API_KEY")
    if not api_key:
        return SearchResult(
            query=query,
            engine="brave",
            error="BRAVE_API_KEY environment variable not set",
        )

    if not HAS_HTTPX and not HAS_REQUESTS:
        return SearchResult(
            query=query,
            engine="brave",
            error="Neither httpx nor requests is installed. Run: pip install httpx",
        )

    async def _async_httpx() -> SearchResult:
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key,
        }
        params = {"q": query, "count": min(count, 20)}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.exception("Brave search failed (httpx)")
            return SearchResult(query=query, engine="brave", error=str(exc))

        items = []
        for r in data.get("web", {}).get("results", []):
            items.append(SearchItem(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("description", ""),
                source="brave",
                published=r.get("age", None),
            ))
        return SearchResult(query=query, engine="brave", results=items)

    def _sync_requests() -> SearchResult:
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key,
        }
        params = {"q": query, "count": min(count, 20)}
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.exception("Brave search failed (requests)")
            return SearchResult(query=query, engine="brave", error=str(exc))

        items = []
        for r in data.get("web", {}).get("results", []):
            items.append(SearchItem(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("description", ""),
                source="brave",
                published=r.get("age", None),
            ))
        return SearchResult(query=query, engine="brave", results=items)

    if HAS_HTTPX:
        return await _async_httpx()
    return await asyncio.to_thread(_sync_requests)


# ── Tavily ─────────────────────────────────────────────────────────────
async def search_tavily(
    query: str,
    max_results: int = 10,
    include_answer: bool = True,
) -> SearchResult:
    """Search the web using the Tavily AI‑optimised search API.

    Requires the TAVILY_API_KEY environment variable.
    Free tier: 1000 calls/month.  Returns an optional AI‑generated answer
    in addition to standard search results.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (default 10).
        include_answer: Whether to request an AI‑generated answer (default True).

    Returns:
        SearchResult with an optional `answer` field plus result items.
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return SearchResult(
            query=query,
            engine="tavily",
            error="TAVILY_API_KEY environment variable not set",
        )

    if not HAS_TAVILY:
        return SearchResult(
            query=query,
            engine="tavily",
            error="tavily-python package not installed. Run: pip install tavily-python",
        )

    def _sync_search() -> SearchResult:
        try:
            client = TavilyClient(api_key=api_key)
            resp = client.search(
                query=query,
                max_results=max_results,
                include_answer=include_answer,
            )
        except Exception as exc:
            logger.exception("Tavily search failed")
            return SearchResult(query=query, engine="tavily", error=str(exc))

        items = []
        for r in resp.get("results", []):
            items.append(SearchItem(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("content", ""),
                source="tavily",
                published=r.get("published_date", None),
            ))
        answer = resp.get("answer", None) if include_answer else None
        return SearchResult(
            query=query,
            engine="tavily",
            results=items,
            answer=answer,
        )

    return await asyncio.to_thread(_sync_search)


# ── Auto-select ───────────────────────────────────────────────────────
async def search_auto(query: str) -> SearchResult:
    """Automatically select the best available search engine.

    Priority:
        1. Tavily (if TAVILY_API_KEY is set)
        2. Brave   (if BRAVE_API_KEY is set)
        3. DuckDuckGo (always available — no key required)

    Args:
        query: The search query string.

    Returns:
        SearchResult from the first available engine.
    """
    if os.environ.get("TAVILY_API_KEY") and HAS_TAVILY:
        result = await search_tavily(query, max_results=10, include_answer=True)
        if not result.error:
            return result

    if os.environ.get("BRAVE_API_KEY") and (HAS_HTTPX or HAS_REQUESTS):
        result = await search_brave(query, count=10)
        if not result.error:
            return result

    result = await search_duckduckgo(query, max_results=10)
    return result
