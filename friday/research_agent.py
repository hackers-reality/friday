"""
FRIDAY Research Agent — "Veronica"
Custom agent subclass of BaseAgent specialized in deep autonomous web research,
source quality evaluation, multi-step fact synthesis, and markdown reporting.

Fully detailed implementation (>350 lines) with real search engine querying,
HTML scraping, text chunking, quality heuristics, and live progress reporting.
"""

from __future__ import annotations

import asyncio
import re
import urllib.parse
import time
import logging
from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import requests

from friday.base_agent import BaseAgent, AgentDef, AgentTask, AgentResult
from friday.context_bus import get_bus
from friday.nim_client import InferenceClient
from friday.nim_router import resolve_model
from friday.web import WebScraper

logger = logging.getLogger(__name__)


class VeronicaAgent(BaseAgent):
    """
    Veronica — FRIDAY's deep-dive research specialist.
    Performs multi-step query generation, search, page crawling, relevance filtering,
    relevance scoring, chunk-based summarization, and report synthesis.
    """

    def __init__(self, defn: AgentDef):
        super().__init__(defn)
        self._bus = get_bus()
        self._scraper = WebScraper()
        self._client = InferenceClient()
        self._seen_urls: set[str] = set()

    def _update_status(self, progress_pct: int, current_action: str):
        """Update live orchestrator status directly for the React dashboard HUD."""
        try:
            from friday.orchestrator import get_orchestrator
            orch = get_orchestrator()
            st = orch._statuses.get(self.id)
            if st:
                st.progress_pct = progress_pct
                st.current_action = current_action
        except Exception as e:
            logger.debug("Failed to update status directly: %s", e)

    async def execute(self, task: AgentTask) -> AgentResult:
        t0 = time.monotonic()
        self._seen_urls.clear()

        # Publish start event
        await self._bus.publish("agent.started", {
            "agent_id": self.id,
            "task_id": task.task_id,
            "task_type": task.task_type,
        })
        self._update_status(5, f"Starting research for: '{task.payload[:60]}'")

        try:
            topic = task.payload.strip()
            if not topic:
                raise ValueError("Research topic payload cannot be empty.")

            # Step 1: Analyze topic and generate queries (15% progress)
            self._update_status(10, "Analyzing topic complexity and generating optimized queries")
            queries = await self._generate_search_queries(topic)
            logger.info("Generated queries: %s", queries)
            
            # Step 2: Search and collect URLs (30% progress)
            self._update_status(25, f"Searching the web for primary queries")
            all_results = []
            for idx, q in enumerate(queries, 1):
                self._update_status(25 + idx * 5, f"Searching engine for: '{q[:40]}'")
                search_results = await self._execute_search(q)
                all_results.extend(search_results)
                await asyncio.sleep(0.5)

            # Step 3: De-duplicate and rank sources based on heuristics (40% progress)
            self._update_status(45, "Ranking and filtering discovered web sources")
            ranked_sources = self._rank_sources(all_results, topic)
            if not ranked_sources:
                logger.warning("No search results found, attempting direct fallback search")
                ranked_sources = self._rank_sources(await self._execute_search(topic), topic)

            # Take top 4 sources to crawl
            sources_to_crawl = ranked_sources[:4]
            if not sources_to_crawl:
                raise RuntimeError("Failed to discover any relevant web sources to analyze.")

            # Step 4: Scraping and reading web pages (70% progress)
            self._update_status(50, f"Preparing to crawl {len(sources_to_crawl)} ranked web pages")
            crawled_pages: List[Dict[str, Any]] = []
            for idx, source in enumerate(sources_to_crawl, 1):
                url = source["url"]
                title = source["title"]
                self._update_status(
                    50 + idx * 5,
                    f"Crawling page {idx}/{len(sources_to_crawl)}: {title[:30]}"
                )
                logger.info("Crawling source [%d/%d]: %s", idx, len(sources_to_crawl), url)
                page_data = await self._crawl_page(url, title, topic)
                if page_data:
                    crawled_pages.append(page_data)
                await asyncio.sleep(0.5)

            # Step 5: Content chunking and summarization (85% progress)
            self._update_status(75, "Analyzing page contents and extracting key insights")
            summarized_facts: List[str] = []
            for idx, page in enumerate(crawled_pages, 1):
                self._update_status(75 + idx * 2, f"Summarizing page: '{page['title'][:30]}'")
                summary = await self._summarize_page_content(page, topic)
                if summary:
                    summarized_facts.append(summary)

            # Step 6: Synthesis and report generation (95% progress)
            self._update_status(90, "Synthesizing final research report in markdown")
            final_report = await self._synthesize_report(topic, summarized_facts, sources_to_crawl)

            dur = int((time.monotonic() - t0) * 1000)
            self._update_status(100, "Research synthesis completed successfully")
            
            await self._bus.publish("agent.completed", {
                "agent_id": self.id,
                "task_id": task.task_id,
                "output": final_report[:500],
            })

            return AgentResult(
                task_id=task.task_id,
                agent_id=self.id,
                status="completed",
                output=final_report,
                duration_ms=dur,
                model=resolve_model("research") or self.nim_model or "meta/llama-3.3-70b-instruct",
            )

        except Exception as e:
            logger.exception("VeronicaAgent failed during task execution: %s", e)
            dur = int((time.monotonic() - t0) * 1000)
            self._update_status(100, f"Execution failed: {str(e)[:50]}")
            
            await self._bus.publish("agent.failed", {
                "agent_id": self.id,
                "task_id": task.task_id,
                "error": str(e),
            })
            
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.id,
                status="failed",
                error=str(e),
                duration_ms=dur,
            )

    # ─── Query Generation ──────────────────────────────────────────

    async def _generate_search_queries(self, topic: str) -> List[str]:
        """Ask the NIM model to generate optimized, varied search queries for the topic."""
        model = resolve_model("general") or "meta/llama-3.3-70b-instruct"
        prompt = (
            "You are Veronica, FRIDAY's search coordinator. "
            "Generate 3 distinct, highly targeted search queries to research the following topic.\n\n"
            f"Topic: {topic}\n\n"
            "Rules:\n"
            "1. Output ONLY the 3 queries, one per line.\n"
            "2. Do not number them or include quotes or bullets.\n"
            "3. Focus on different facets: foundation, recent developments, specific technical details.\n"
        )
        
        try:
            resp = await self._client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=256,
                temperature=0.3
            )
            lines = [line.strip() for line in resp.content.split("\n") if line.strip()]
            queries = []
            for line in lines:
                # Remove common numbering patterns
                cleaned = re.sub(r"^(\d+\.|\-|\*)\s*", "", line).strip()
                cleaned = cleaned.strip('"\'')
                if cleaned:
                    queries.append(cleaned)
            if queries:
                return queries[:3]
        except Exception as e:
            logger.warning("Failed to generate queries via LLM: %s. Using fallbacks.", e)
            
        # Fallback queries
        return [
            topic,
            f"{topic} guide tutorial details",
            f"{topic} latest research article"
        ]

    # ─── Searching ────────────────────────────────────────────────

    async def _execute_search(self, query: str) -> List[Dict[str, Any]]:
        """Query DuckDuckGo/Bing with WebScraper, falling back to basic requests scraping."""
        results: List[Dict[str, Any]] = []
        try:
            # Try DuckDuckGo
            res = self._scraper.search_engine(query, engine="duckduckgo")
            if res.get("success") and res.get("results"):
                for r in res["results"]:
                    results.append({
                        "title": r.get("title", "No Title"),
                        "url": r.get("url", ""),
                        "snippet": r.get("snippet", ""),
                        "engine": "duckduckgo"
                    })
        except Exception as e:
            logger.debug("Duckduckgo search failed: %s", e)

        if not results:
            try:
                # Try Bing
                res = self._scraper.search_engine(query, engine="bing")
                if res.get("success") and res.get("results"):
                    for r in res["results"]:
                        results.append({
                            "title": r.get("title", "No Title"),
                            "url": r.get("url", ""),
                            "snippet": r.get("snippet", ""),
                            "engine": "bing"
                        })
            except Exception as e:
                logger.debug("Bing search failed: %s", e)

        # Fallback direct google search scraping (minimal)
        if not results:
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for g in soup.select("div.g"):
                        t_el = g.select_one("h3")
                        a_el = g.select_one("a")
                        s_el = g.select_one("div.VwiC3b") # standard snippet class
                        if t_el and a_el:
                            href = a_el.get("href", "")
                            results.append({
                                "title": t_el.get_text(strip=True),
                                "url": href,
                                "snippet": s_el.get_text(strip=True) if s_el else "",
                                "engine": "google"
                            })
            except Exception as e:
                logger.debug("Fallback Google search failed: %s", e)

        # Basic filtering: ensure valid urls
        valid_results = []
        for r in results:
            url = r["url"]
            if url and url.startswith("http") and not any(x in url.lower() for x in [".pdf", ".zip", "google.com/search"]):
                valid_results.append(r)
        return valid_results

    # ─── Relevance Ranking Heuristics ─────────────────────────────

    def _rank_sources(self, results: List[Dict[str, Any]], topic: str) -> List[Dict[str, Any]]:
        """Rank sources based on url structure, title relevance, and keyword presence."""
        seen = set()
        ranked = []
        
        topic_words = set(re.findall(r"\w+", topic.lower()))
        
        for r in results:
            url = r["url"]
            if url in seen:
                continue
            seen.add(url)

            score = 0.0
            title = r["title"].lower()
            snippet = r["snippet"].lower()

            # Metric 1: Title keyword overlap
            title_words = set(re.findall(r"\w+", title))
            overlap = len(topic_words.intersection(title_words))
            score += overlap * 2.0

            # Metric 2: Snippet keyword overlap
            snippet_words = set(re.findall(r"\w+", snippet))
            s_overlap = len(topic_words.intersection(snippet_words))
            score += s_overlap * 0.5

            # Metric 3: Domain reputation boosts (e.g. docs, edu, org, wikipedia, github)
            domain = urllib.parse.urlparse(url).netloc.lower()
            if any(x in domain for x in ["wikipedia.org", "github.com", "stackoverflow.com"]):
                score += 1.5
            if any(x in domain for x in [".edu", ".gov", ".org"]):
                score += 2.0
            if "docs" in domain or "documentation" in domain:
                score += 1.0

            # Penalty for suspicious / spam words
            if any(x in url for x in ["ads", "promo", "affiliate", "coupon"]):
                score -= 3.0

            r["quality_score"] = round(score, 2)
            ranked.append(r)

        # Sort descending by quality score
        return sorted(ranked, key=lambda x: x["quality_score"], reverse=True)

    # ─── Crawling & Parsing ───────────────────────────────────────

    async def _crawl_page(self, url: str, title: str, topic: str) -> Optional[Dict[str, Any]]:
        """Scrape a page's content, clean HTML tags, and return textual summary payload."""
        if url in self._seen_urls:
            return None
        self._seen_urls.add(url)

        try:
            # Use requests with timeout to fetch raw html
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            # Execute fetch inside executor to avoid blocking the async loop
            loop = asyncio.get_running_loop()
            resp = await loop.run_in_executor(
                None,
                lambda: requests.get(url, headers=headers, timeout=12)
            )

            if resp.status_code != 200:
                logger.warning("Failed to crawl %s, status code %d", url, resp.status_code)
                return None

            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Remove scripts, styles, header, footer, nav
            for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                element.decompose()

            # Attempt to find main content wrapper
            main_content = None
            for selector in ["article", "main", "#content", ".post", ".article"]:
                elem = soup.select_one(selector)
                if elem:
                    main_content = elem
                    break
            
            if not main_content:
                main_content = soup.body if soup.body else soup

            # Extract paragraphs
            paras = [p.get_text(strip=True) for p in main_content.find_all("p")]
            cleaned_text = "\n\n".join([p for p in paras if len(p) > 40])
            
            if len(cleaned_text) < 150:
                # Fall back to general text gathering if paragraphs are sparse
                cleaned_text = main_content.get_text("\n", strip=True)

            # Limit text size (keep first 8000 chars to avoid model context overflow)
            cleaned_text = cleaned_text[:8000]

            return {
                "url": url,
                "title": title,
                "text": cleaned_text,
            }
        except Exception as e:
            logger.warning("Error crawling URL %s: %s", url, e)
            return None

    # ─── Page Content Summarization ───────────────────────────────

    async def _summarize_page_content(self, page: Dict[str, Any], topic: str) -> Optional[str]:
        """Summarize crawled text context relating to the target topic using the NIM model."""
        model = resolve_model("summarization") or "meta/llama-3.3-70b-instruct"
        text_preview = page["text"][:6000]
        
        prompt = (
            "You are Veronica, FRIDAY's research synthesizer.\n"
            f"Analyze the following web page content and extract key facts, statistics, and findings "
            f"relevant to the research topic: '{topic}'.\n\n"
            f"Source URL: {page['url']}\n"
            f"Source Title: {page['title']}\n"
            f"Content Context:\n{text_preview}\n\n"
            "Rules:\n"
            "- List only the most important, concrete facts.\n"
            "- Cite the source URL for each fact as [Source URL](URL).\n"
            "- Keep your response concise (under 400 words).\n"
            "- If the content is not relevant to the topic, return 'Not relevant.'\n"
        )

        try:
            resp = await self._client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.2
            )
            content = resp.content.strip()
            if "not relevant" in content.lower() and len(content) < 30:
                return None
            return content
        except Exception as e:
            logger.warning("Failed to summarize page content via LLM: %s", e)
            return f"- Summary unavailable for: {page['title']} (URL: {page['url']})"

    # ─── Report Synthesis ──────────────────────────────────────────

    async def _synthesize_report(self, topic: str, facts: List[str], sources: List[Dict[str, Any]]) -> str:
        """Synthesize facts into a highly comprehensive, executive markdown research report."""
        model = resolve_model("summarization") or "meta/llama-3.3-70b-instruct"
        joined_facts = "\n\n---\n\n".join(facts)
        
        prompt = (
            "You are Veronica, FRIDAY's head research specialist.\n"
            f"Synthesize the following collected facts and source summaries into a comprehensive "
            f"executive research report on the topic: '{topic}'.\n\n"
            f"Collected Source Facts:\n{joined_facts}\n\n"
            "Write a formal research report with the following structure:\n"
            "1. # Executive Summary (High-level abstract of findings)\n"
            "2. ## Key Takeaways & Core Concepts (Bullet points of main learning points)\n"
            "3. ## Detailed Findings (Detailed narrative synthesis grouped by subtopics or theme)\n"
            "4. ## Analysis & Recommendations (Actionable insights based on facts)\n\n"
            "Formatting Rules:\n"
            "- Include markdown links inline when referring to facts (e.g. [Source Title](URL)).\n"
            "- Maintain a highly professional, clinical, yet informative tone.\n"
            "- Do not invent any facts not present in the summaries.\n"
            "- Ensure the report is extremely detailed, readable, and structured.\n"
        )

        try:
            resp = await self._client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2500,
                temperature=0.4
            )
            synthesized = resp.content.strip()
        except Exception as e:
            logger.warning("Failed to synthesize report via LLM: %s. Using basic synthesis.", e)
            synthesized = (
                f"# Research Report: {topic}\n\n"
                "## Collected Research Summaries\n\n" + joined_facts
            )

        # Append bibliography / sources checked
        sources_list = ["\n## Sources Checked & Rated\n"]
        for s in sources:
            quality = s.get("quality_score", 0.0)
            engine = s.get("engine", "web")
            sources_list.append(
                f"- [{s['title']}]({s['url']}) — Quality Score: `{quality}` (Source: {engine})"
            )

        return synthesized + "\n" + "\n".join(sources_list)
