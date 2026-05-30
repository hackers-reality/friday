"""
Web Intelligence Tools — Crawl4AI, curl_cffi, Trafilatura, Docling

Provides LLM-friendly async functions for crawling, fingerprint HTTP requests,
text extraction, and document parsing with lazy imports and structured results.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

HAS_CRAWL4AI = False
HAS_CURL_CFFI = False
HAS_TRAFILATURA = False
HAS_DOCLING = False

try:
    import crawl4ai  # noqa: F401
    HAS_CRAWL4AI = True
except ImportError:
    pass

try:
    import curl_cffi  # noqa: F401
    HAS_CURL_CFFI = True
except ImportError:
    pass

try:
    import trafilatura  # noqa: F401
    HAS_TRAFILATURA = True
except ImportError:
    pass

try:
    import docling  # noqa: F401
    HAS_DOCLING = True
except ImportError:
    pass


# ── Data Models ──

@dataclass
class CrawlResult:
    url: str
    title: str
    content: str
    links: list[str] = None
    images: list[str] = None
    error: Optional[str] = None

    def __post_init__(self):
        self.links = self.links or []
        self.images = self.images or []


@dataclass
class FingerprintResult:
    url: str
    status_code: int
    headers: dict
    content: str
    error: Optional[str] = None


@dataclass
class ExtractResult:
    url: str
    title: str
    content: str
    author: Optional[str] = None
    date: Optional[str] = None
    format: str = "markdown"
    error: Optional[str] = None


@dataclass
class DocumentResult:
    file: str
    pages: int
    content: str
    tables: list[list[list[str]]] = None
    error: Optional[str] = None

    def __post_init__(self):
        self.tables = self.tables or []


# ── Crawl4AI ──

async def crawl_page(
    url: str,
    extract_links: bool = True,
    max_pages: int = 1,
) -> CrawlResult:
    """Crawl a web page with Crawl4AI and return clean markdown content.

    Uses Crawl4AI's async web crawler to fetch a URL, extract the main
    article / body content, and convert it to markdown.  Optionally
    extracts all hyperlinks and image sources found on the page.

    Parameters
    ----------
    url : str
        The fully-qualified URL to crawl (including scheme).
    extract_links : bool, optional
        Whether to collect all href links and img src attributes from the
        page (default True).
    max_pages : int, optional
        Maximum number of pages to crawl (default 1).  When >1, Crawl4AI
        follows same-domain links up to the limit.

    Returns
    -------
    CrawlResult
        Structured result with title, markdown content, extracted links,
        and image URLs.  ``error`` is set on failure.
    """
    if not HAS_CRAWL4AI:
        return CrawlResult(url=url, title="", content="",
                           error="crawl4ai is not installed.  pip install crawl4ai")

    try:
        from crawl4ai import AsyncWebCrawler
        from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig

        browser_cfg = BrowserConfig(headless=True, verbose=False)

        run_cfg = CrawlerRunConfig(
            word_count_threshold=10,
            extraction_strategy="NoExtractionStrategy",
            markdown=True,
            excluded_tags=["nav", "footer", "aside", "script", "style"],
            verbose=False,
        )

        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=url, config=run_cfg)

        if not result.success:
            return CrawlResult(url=url, title="", content="",
                               error=result.error_message or "Unknown crawl error")

        title = getattr(result, "title", "") or ""
        md_content = ""

        if hasattr(result, "markdown") and result.markdown:
            if isinstance(result.markdown, str):
                md_content = result.markdown
            elif isinstance(result.markdown, dict):
                md_content = (result.markdown.get("raw") or
                              result.markdown.get("markdown") or
                              "")

        md_content = md_content[:50000]

        links: list[str] = []
        images: list[str] = []

        if extract_links:
            if hasattr(result, "links") and result.links:
                for link in result.links:
                    href = link.get("href") or link.get("url") or ""
                    if href and href.startswith("http"):
                        links.append(href)

            if hasattr(result, "media") and result.media:
                for item in result.media:
                    src = item.get("src") or item.get("url") or ""
                    if src:
                        images.append(src)

            if not links and hasattr(result, "raw_html") and result.raw_html:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(result.raw_html, "html.parser")
                links = [a.get("href") for a in soup.find_all("a", href=True)
                         if a.get("href", "").startswith("http")]
                images = [img.get("src") for img in soup.find_all("img", src=True)
                          if img.get("src")]

        return CrawlResult(url=url, title=title, content=md_content,
                           links=links[:200], images=images[:100])

    except Exception as exc:
        logger.exception("crawl_page failed for %s", url)
        return CrawlResult(url=url, title="", content="",
                           error=str(exc))


# ── curl_cffi (fingerprint HTTP) ──

async def fetch_with_fingerprint(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
) -> FingerprintResult:
    """Make an HTTP request with browser TLS fingerprinting via curl_cffi.

    curl_cffi impersonates real browser TLS handshakes (Chrome, Safari,
    Firefox) to bypass bot detection on services like Cloudflare.

    Parameters
    ----------
    url : str
        Target URL.
    method : str, optional
        HTTP method — ``"GET"`` or ``"POST"`` (default ``"GET"``).
    headers : dict, optional
        Additional request headers.  A realistic User-Agent is set
        automatically.

    Returns
    -------
    FingerprintResult
        Status code, response headers, and body content (truncated to
        100 KB).  ``error`` is set on failure.
    """
    if not HAS_CURL_CFFI:
        return FingerprintResult(url=url, status_code=0, headers={}, content="",
                                 error="curl_cffi is not installed.  pip install curl_cffi")

    try:
        from curl_cffi import requests as curl_requests

        default_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        if headers:
            default_headers.update(headers)

        resp = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: curl_requests.request(
                method=method.upper(),
                url=url,
                headers=default_headers,
                timeout=30,
                impersonate="chrome120",
            ),
        )

        return FingerprintResult(
            url=url,
            status_code=resp.status_code,
            headers=dict(resp.headers),
            content=resp.text[:100_000],
        )

    except Exception as exc:
        logger.exception("fetch_with_fingerprint failed for %s", url)
        return FingerprintResult(url=url, status_code=0, headers={}, content="",
                                 error=str(exc))


# ── Trafilatura ──

async def extract_text(
    url: str,
    output_format: str = "markdown",
) -> ExtractResult:
    """Extract clean, readable text from a web page using Trafilatura.

    Trafilatura is the current state-of-the-art for web text extraction
    (F1 0.958 on Clean-Eval).  It strips navigation, ads, and other
    boilerplate, returning the main article content.

    Parameters
    ----------
    url : str
        The URL of the page to extract.
    output_format : str, optional
        ``"markdown"`` (default) or ``"txt"`` for plain text.

    Returns
    -------
    ExtractResult
        Title, content, author, and publication date if available.
        ``error`` is set on failure.
    """
    if not HAS_TRAFILATURA:
        return ExtractResult(url=url, title="", content="",
                             error="trafilatura is not installed.  pip install trafilatura")

    try:
        import trafilatura

        downloaded = await asyncio.get_event_loop().run_in_executor(
            None, lambda: trafilatura.fetch_url(url),
        )
        if not downloaded:
            return ExtractResult(url=url, title="", content="",
                                 error="trafilatura could not download the page")

        extract_kwargs: dict[str, Any] = {
            "include_links": True,
            "include_images": False,
            "include_tables": True,
            "include_formatting": True,
            "no_fallback": False,
        }

        if output_format == "markdown":
            content = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: trafilatura.extract(downloaded, output_format="markdown",
                                            **extract_kwargs),
            )
        else:
            content = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: trafilatura.extract(downloaded, output_format="txt",
                                            **extract_kwargs),
            )

        if not content:
            return ExtractResult(url=url, title="", content="",
                                 error="trafilatura could not extract content")

        title = await asyncio.get_event_loop().run_in_executor(
            None, lambda: trafilatura.extract(downloaded, output_format="txt",
                                              include_links=False, include_images=False,
                                              include_tables=False, include_formatting=False,
                                              favor_precision=True),
        )
        metadata = await asyncio.get_event_loop().run_in_executor(
            None, lambda: trafilatura.extract_metadata(downloaded),
        )

        extracted_title = ""
        author: str | None = None
        date: str | None = None

        if metadata:
            extracted_title = metadata.title or ""
            author = metadata.author or None
            if metadata.date:
                date = str(metadata.date)

        if not extracted_title and title:
            extracted_title = title.split("\n")[0][:200]

        return ExtractResult(
            url=url,
            title=extracted_title,
            content=content[:50000],
            author=author,
            date=date,
            format=output_format,
        )

    except Exception as exc:
        logger.exception("extract_text failed for %s", url)
        return ExtractResult(url=url, title="", content="", error=str(exc))


# ── Docling (IBM AI document parser) ──

async def parse_document(
    file_path: str,
    output_format: str = "markdown",
) -> DocumentResult:
    """Parse a document (PDF, DOCX, PPTX, XLSX, HTML) with Docling.

    Docling is IBM's AI-powered document understanding library that
    preserves layout structure, tables, and images.  It uses deep
    learning models for layout analysis (DocLayNet) and table extraction.

    Parameters
    ----------
    file_path : str
        Absolute or relative path to the document file.
    output_format : str, optional
        ``"markdown"`` (default) or ``"text"`` for plain text output.

    Returns
    -------
    DocumentResult
        Number of pages, full document content, and extracted tables
        (as 2-D string arrays).  ``error`` is set on failure.
    """
    if not HAS_DOCLING:
        return DocumentResult(file=file_path, pages=0, content="",
                              error="docling is not installed.  pip install docling")

    import os as _os
    if not _os.path.exists(file_path):
        return DocumentResult(file=file_path, pages=0, content="",
                              error=f"File not found: {file_path}")

    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: converter.convert(file_path),
        )

        doc = result.document

        pages = len(doc.pages) if doc.pages else 0

        if output_format == "markdown":
            content = await asyncio.get_event_loop().run_in_executor(
                None, lambda: doc.export_to_markdown(),
            )
        else:
            content = await asyncio.get_event_loop().run_in_executor(
                None, lambda: doc.export_to_text(),
            )

        content = (content or "")[:100_000]

        tables: list[list[list[str]]] = []
        if doc.tables:
            for table in doc.tables:
                table_data: list[list[str]] = []
                if table.data and table.data.row_headers and table.data.cells:
                    rows: dict[int, dict[int, str]] = {}
                    for cell in table.data.cells:
                        r = cell.row_idx
                        c = cell.col_idx
                        rows.setdefault(r, {})[c] = cell.text or ""
                    for r in sorted(rows):
                        row_data = [rows[r].get(c, "") for c in sorted(rows[r])]
                        table_data.append(row_data)
                tables.append(table_data)

        return DocumentResult(
            file=file_path,
            pages=pages,
            content=content,
            tables=tables,
        )

    except Exception as exc:
        logger.exception("parse_document failed for %s", file_path)
        return DocumentResult(file=file_path, pages=0, content="",
                              error=str(exc))
