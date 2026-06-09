"""
FRIDAY Research Agent — "Veronica"
Deep-dive research specialist using browser-based scraping, PDF extraction,
recursive link following, adaptive LLM-driven search, and comprehensive PDF reports.

Workflow:
  1. LLM generates search queries based on the topic
  2. Browser scrapes: search → collect links (max 5 search pages) → visit each → scroll to bottom → extract ALL content
  3. LLM identifies relevant links inside each page → click → scrape recursively (depth 2)
  4. LLM identifies PDF/download links → download PDFs → extract text
  5. LLM evaluates: "Do I have enough on this subtopic? What should I search next?"
  6. Repeat until LLM decides research is comprehensive
  7. Save ALL raw data to .md file
  8. Read skill files (pdf, svg, chart SKILL.md)
  9. LLM reads raw .md, generates comprehensive PDF report via create_pdf() with 24 chart types (including timeline)
  10. Report back to FRIDAY with summary
"""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import re
import time
import urllib.parse
from pathlib import Path
from typing import Any, Optional

from friday.base_agent import BaseAgent, AgentDef, AgentTask, AgentResult
from friday.context_bus import get_bus
from friday.nim_client import InferenceClient
from friday.nim_router import resolve_model

logger = logging.getLogger(__name__)

SKILL_DIR = Path(__file__).resolve().parent / "skills"
MEMORY_DIR = Path(__file__).resolve().parent / "memory"
MAX_RECURSION_DEPTH = 2
MAX_ITERATIONS = 5
MAX_SECONDS_PER_ITERATION = 7200
MAX_PAGES_PER_QUERY = 10


class VeronicaAgent(BaseAgent):
    """
    Veronica — FRIDAY's deep-dive research specialist.
    Uses adaptive LLM-driven research: decides what to search, what to drill into,
    when to move on, and when the research is comprehensive enough.
    """

    def __init__(self, defn: AgentDef):
        super().__init__(defn)
        self._bus = get_bus()
        self._client = InferenceClient()
        self._seen_urls: set[str] = set()

    def _update_status(self, progress_pct: int, current_action: str):
        logger.info("[%d%%] %s", progress_pct, current_action)
        try:
            from friday.agent_terminal import get_terminal_manager
            tm = get_terminal_manager()
            tm.update_agent_terminal(
                agent_name="veronica",
                status="running",
                action=current_action,
                progress=progress_pct,
            )
        except Exception:
            pass

    # ─── Main Execution ──────────────────────────────────────────

    async def execute(self, task: AgentTask) -> AgentResult:
        t0 = time.monotonic()
        overall_timeout = getattr(task, "metadata", {}).get("timeout", 36000) if hasattr(task, "metadata") else 36000
        self._seen_urls.clear()
        topic = task.payload.strip()
        safe_name = re.sub(r"[^\w\s-]", "", topic).strip().replace(" ", "_")[:60]

        await self._bus.publish("agent.started", {
            "agent_id": self.id, "task_id": task.task_id, "task_type": task.task_type,
        })
        self._update_status(5, f"Starting research: '{topic[:60]}'")
        timings = {"query_gen": 0, "scraping": [], "decisions": [], "report_gen": 0}

        try:
            # Step 1: Generate initial search queries via NIM
            self._update_status(8, "LLM generating initial search queries")
            t_q = time.monotonic()
            try:
                queries = await asyncio.wait_for(self._generate_queries(topic), timeout=60)
            except (asyncio.TimeoutError, Exception):
                queries = [topic, f"{topic} detailed guide", f"{topic} problems and solutions"]
            timings["query_gen"] = time.monotonic() - t_q

            all_data = {"pages": [], "links": set(), "search_queries": queries}

            # Step 2: Adaptive iterative research loop
            iteration = 0
            current_queries = queries
            accumulated_findings = []

            while iteration < MAX_ITERATIONS:
                iteration += 1
                elapsed = time.monotonic() - t0
                if elapsed > overall_timeout:
                    logger.warning("Overall time budget exceeded (%.0fs > %ds)", elapsed, overall_timeout)
                    break

                self._update_status(
                    10 + iteration * 8,
                    f"Iteration {iteration}/{MAX_ITERATIONS}: researching with {len(current_queries)} queries",
                )

                # Browser scrape these queries (with per-iteration timeout)
                partial = None
                t_s = time.monotonic()
                try:
                    partial = {"pages": [], "links": set()}
                    batch_data = await asyncio.wait_for(
                        self._browser_scrape_batch(topic, current_queries, iteration, partial),
                        timeout=MAX_SECONDS_PER_ITERATION,
                    )
                except (asyncio.TimeoutError, Exception) as e:
                    logger.warning("Iteration %d scraping timed out or failed: %s", iteration, e)
                    batch_data = partial or {"pages": [], "links": set()}
                timings["scraping"].append(time.monotonic() - t_s)

                all_data["pages"].extend(batch_data.get("pages", []))
                all_data["links"].update(batch_data.get("links", []))

                # Ask LLM: have we gathered enough? What to search next?
                self._update_status(
                    10 + iteration * 8 + 4,
                    f"Iteration {iteration}: LLM evaluating findings & deciding next steps",
                )
                t_d = time.monotonic()
                try:
                    decision = await asyncio.wait_for(
                        self._decide_next_steps(topic, batch_data, accumulated_findings, iteration),
                        timeout=120,
                    )
                except (asyncio.TimeoutError, Exception):
                    decision = {
                        "summary": "Decision unavailable",
                        "next_queries": [],
                        "stop": iteration >= MAX_ITERATIONS,
                        "subtopics_covered": [],
                        "subtopics_needed": [topic],
                    }
                timings["decisions"].append(time.monotonic() - t_d)

                accumulated_findings.append({
                    "iteration": iteration,
                    "queries": current_queries,
                    "pages_count": len(batch_data.get("pages", [])),
                    "summary": decision.get("summary", ""),
                })

                if decision.get("stop", False):
                    self._update_status(50, f"LLM decided research is comprehensive after {iteration} iterations")
                    break

                current_queries = decision.get("next_queries", [])
                if not current_queries:
                    break

            all_data["links"] = list(all_data["links"])

            # Step 3: Save raw data to .md
            self._update_status(55, "Saving all raw scraped data to markdown file")
            md_path = MEMORY_DIR / f"raw_research_{safe_name}.md"
            raw_md_body = self._build_raw_md(topic, all_data, accumulated_findings)
            dur_sofar = int(time.monotonic() - t0)
            timing_footer = (
                f"\n\n---\n## Research Timing\n"
                f"- **Total research duration**: {dur_sofar // 3600}h {(dur_sofar % 3600) // 60}m {dur_sofar % 60}s\n"
                f"- **Query generation**: {timings['query_gen']:.0f}s\n" +
                "\n".join(
                    [f"- **Iteration {i+1} scraping**: {t:.0f}s" for i, t in enumerate(timings['scraping'])] +
                    [f"- **Iteration {i+1} decision**: {t:.0f}s" for i, t in enumerate(timings['decisions'])]
                ) +
                f"\n- **Report generation**: {timings['report_gen']:.0f}s\n"
            )
            md_content = raw_md_body + timing_footer
            MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            md_path.write_text(md_content, encoding="utf-8")

            # Step 4: Read skill files
            self._update_status(60, "Reading skill files for report patterns")
            skill_contents = self._read_skills()

            # Step 5: Generate PDF via LLM
            self._update_status(65, "LLM generating comprehensive PDF report from all raw data")
            t_r = time.monotonic()
            pdf_path = MEMORY_DIR / f"{safe_name}_Report.pdf"
            report_result = await self._generate_report(topic, md_content, skill_contents, str(pdf_path))
            timings["report_gen"] = time.monotonic() - t_r

            dur = int((time.monotonic() - t0) * 1000)
            self._update_status(100, "Research complete")

            timing_lines = "\n".join(
                [f"- **Query generation**: {timings['query_gen']:.0f}s"] +
                [f"- **Iteration {i+1} scraping**: {t:.0f}s" for i, t in enumerate(timings['scraping'])] +
                [f"- **Iteration {i+1} decision**: {t:.0f}s" for i, t in enumerate(timings['decisions'])] +
                [f"- **Report generation**: {timings['report_gen']:.0f}s"]
            )

            summary = (
                f"## Research Complete: {topic}\n"
                f"- **Iterations**: {iteration}\n"
                f"- **Raw data**: {md_path}\n"
                f"- **PDF report**: {pdf_path}\n"
                f"- **Pages/sources scraped**: {len(all_data.get('pages', []))}\n"
                f"- **Links collected**: {len(all_data.get('links', []))}\n"
                f"- **Report sections**: {report_result.get('sections', 'N/A')}\n"
                f"- **NIM model**: {report_result.get('model', 'unknown')}\n"
                f"- **Total Duration**: {dur / 1000:.0f}s ({dur / 60000:.1f} min)\n"
                f"### Timing Breakdown\n{timing_lines}\n"
            )

            await self._bus.publish("agent.completed", {
                "agent_id": self.id, "task_id": task.task_id, "output": summary,
            })
            return AgentResult(
                task_id=task.task_id, agent_id=self.id, status="completed",
                output=summary, duration_ms=dur,
                model=resolve_model("research") or self.nim_model,
            )

        except Exception as e:
            logger.exception("VeronicaAgent failed: %s", e)
            dur = int((time.monotonic() - t0) * 1000)
            self._update_status(100, f"Failed: {str(e)[:60]}")
            await self._bus.publish("agent.failed", {
                "agent_id": self.id, "task_id": task.task_id, "error": str(e),
            })
            return AgentResult(
                task_id=task.task_id, agent_id=self.id, status="failed",
                error=str(e), duration_ms=dur,
            )

    # ─── LLM Query Generation ────────────────────────────────────

    async def _generate_queries(self, topic: str) -> list[str]:
        model = resolve_model("research") or self.nim_model or "qwen/qwen3-coder-480b-a35b-instruct"
        prompt = (
            "You are Veronica, FRIDAY's research strategist.\n"
            f"Generate 3-4 highly targeted search queries to thoroughly research: '{topic}'.\n"
            "Each query should cover a DIFFERENT facet of the topic (e.g., syllabus, problems, books, tutorials).\n"
            "Output ONLY the queries, one per line, no numbering or quotes."
        )
        try:
            resp = await self._client.chat(
                model=model, messages=[{"role": "user", "content": prompt}],
                max_tokens=512, temperature=0.3,
            )
            lines = [l.strip().strip("\"'") for l in resp.content.split("\n") if l.strip()]
            queries = [re.sub(r"^(\d+\.|\-|\*)\s*", "", l).strip() for l in lines]
            return [q for q in queries[:5] if q and len(q) > 5] or [topic]
        except Exception:
            return [
                topic,
                f"{topic} complete guide",
                f"{topic} problems and solutions",
                f"{topic} books and resources",
            ]

    # ─── LLM Decide Next Steps ───────────────────────────────────

    async def _decide_next_steps(
        self, topic: str, batch_data: dict, history: list, iteration: int,
    ) -> dict:
        """
        Ask the LLM to evaluate the current batch of scraped data and decide:
        - What subtopics have been sufficiently covered?
        - What still needs more research?
        - What should the next search queries be?
        - Should we stop (comprehensive enough)?
        """
        model = resolve_model("research") or self.nim_model or "qwen/qwen3-coder-480b-a35b-instruct"

        pages_summary = []
        for p in batch_data.get("pages", [])[:10]:
            pages_summary.append(f"- {p.get('title', 'Untitled')} ({p.get('url', '')[:80]})")

        history_summary = "\n".join(
            f"Iteration {h['iteration']}: {h['pages_count']} pages, queries={h['queries']}"
            for h in history[-3:]
        )

        prompt = (
            f"You are Veronica evaluating research progress on: '{topic}'.\n\n"
            f"=== Current batch results (iteration {iteration}) ===\n"
            f"Pages scraped: {len(batch_data.get('pages', []))}\n"
            f"Links found: {len(batch_data.get('links', []))}\n"
            f"Titles/URLs:\n{chr(10).join(pages_summary)}\n\n"
            f"=== Previous iterations ===\n{history_summary}\n\n"
            "Analyze whether the research is comprehensive enough or still needs more depth.\n\n"
            "Return a JSON object in this exact format (no ProseMirror/doc wrapper):\n"
            '{\n'
            '  "summary": "one paragraph summary of what was found",\n'
            '  "next_queries": ["query 1", "query 2", "query 3"],\n'
            '  "stop": false,\n'
            '  "subtopics_covered": ["subtopic A", "subtopic B"],\n'
            '  "subtopics_needed": ["subtopic C", "subtopic D"]\n'
            '}\n\n'
            "IMPORTANT: Be ambitious. Only stop when you have covered ALL major facets of the topic.\n"
            "If there are still untapped subtopics, generate specific queries for them.\n"
            "Return ONLY valid JSON. No markdown fences."
        )

        try:
            resp = await self._client.chat(
                model=model, messages=[{"role": "user", "content": prompt}],
                max_tokens=4096, temperature=0.3,
            )
            text = resp.content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(text)
        except Exception as e:
            logger.warning("LLM decision failed (%s), defaulting to continue with fallback queries", e)
            return {
                "summary": "LLM decision unavailable, continuing with fallback queries",
                "next_queries": [f"{topic} additional resources", f"{topic} in-depth analysis"],
                "stop": iteration >= 5,
                "subtopics_covered": [],
                "subtopics_needed": [topic],
            }

    # ─── Browser Scraping Batch ──────────────────────────────────

    async def _browser_scrape_batch(self, topic: str, queries: list[str], iteration: int, partial: dict | None = None) -> dict[str, Any]:
        """Search, collect links from 3 search pages, visit relevant ones."""
        from friday.browser_use_bridge import (
            browser_use_navigate, browser_use_extract_links,
            browser_use_scroll, browser_use_get_url, browser_use_get_title,
            browser_use_get_dom_state, browser_use_click, browser_use_extract_text,
        )

        collected = {"pages": [], "links": set()}

        def _checkpoint():
            if partial is not None:
                partial["pages"] = list(collected["pages"])
                partial["links"] = set(collected["links"])

        for qi, query in enumerate(queries):
            self._update_status(
                10 + iteration * 8 + qi * 2,
                f"Iter {iteration} search {qi + 1}/{len(queries)}: '{query[:45]}'",
            )

            # Navigate directly to search (page is replaced automatically)
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            try:
                nav_result = browser_use_navigate(search_url)
                logger.info("SCRAPE: Navigate result for %s: %s", query[:40], nav_result[:100])
                if "[FAIL]" in nav_result:
                    logger.warning("Navigate failed for query: %s", query)
                    continue
            except Exception as e:
                logger.warning("Navigate error for query %s: %s", query, e)
                continue
            await asyncio.sleep(2)

            # Collect links from first 2 search pages (faster)
            search_page_links = set()
            for page_num in range(3):
                try:
                    links_raw = browser_use_extract_links()
                    logger.info("SCRAPE: Links raw len=%d, page=%d", len(links_raw), page_num)
                    links = self._parse_links(links_raw)
                    logger.info("SCRAPE: Parsed %d links from page %d", len(links), page_num)
                except Exception as e:
                    logger.warning("Link extraction error: %s", e)
                    links = []
                passing = [l for l in links if not any(
                    x in l for x in ["google.com/search", "google.com/preferences",
                                     "accounts.google", "policies.google", "support.google"]
                )]
                logger.info("SCRAPE: Parsed %d links, passing filter: %d, sample: %s",
                           len(links), len(passing), [l[:80] for l in passing[:5]])
                for link in passing:
                    search_page_links.add(link)
                    collected["links"].add(link)
                if page_num < 2:
                    clicked = False
                    for next_text in ["Next", "›", "Next page"]:
                        try:
                            result = browser_use_click(text=next_text)
                            parsed = json.loads(result) if isinstance(result, str) else {}
                            if isinstance(parsed, dict) and parsed.get("success"):
                                clicked = True
                                await asyncio.sleep(1.5)
                                break
                        except Exception:
                            pass
                    if not clicked:
                        break
            _checkpoint()
            logger.debug("Total links collected after pagination: %d", len(search_page_links))

            # Skip LLM filtering if few links — just visit all non-Google ones
            non_google = [l for l in search_page_links
                          if not any(x in l for x in ["google.com", "youtube.com", "facebook.com"])]
            if len(non_google) <= 10:
                relevant_urls = list(non_google)[:20]
            else:
                relevant_urls = await self._filter_relevant(list(non_google)[:50], query)
            self._update_status(
                10 + iteration * 8 + qi * 2 + 1,
                f"Iter {iteration}: visiting {len(relevant_urls)} pages",
            )

            limit = getattr(self, '_max_pages_per_query', MAX_PAGES_PER_QUERY)
            for ui, url in enumerate(relevant_urls[:limit]):
                self._update_status(
                    10 + iteration * 8 + qi * 2 + 1 + int(ui / max(len(relevant_urls), 1) * 5),
                    f"Iter {iteration} page {ui + 1}/{min(len(relevant_urls),5)}",
                )
                await self._recursive_scrape(url, topic, collected, depth=0)
                _checkpoint()

        collected["links"] = list(collected["links"])
        return collected

    # ─── Recursive Deep Scrape ───────────────────────────────────

    async def _recursive_scrape(self, url: str, topic: str, collected: dict, depth: int):
        """
        Scrape a page and its relevant child links recursively (up to MAX_RECURSION_DEPTH).
        If the page links to a PDF, download and extract text from it.
        """
        if url in self._seen_urls or depth > MAX_RECURSION_DEPTH:
            return
        self._seen_urls.add(url)

        from friday.browser_use_bridge import (
            browser_use_navigate, browser_use_extract_text, browser_use_extract_links,
            browser_use_extract_html, browser_use_scroll, browser_use_get_url,
            browser_use_get_title, browser_use_get_dom_state, browser_use_click,
        )

        # Handle PDFs directly
        if url.lower().endswith(".pdf"):
            pdf_data = await self._download_and_extract_pdf(url)
            if pdf_data:
                collected["pages"].append(pdf_data)
            return

        try:
            nav_result = browser_use_navigate(url)
            if "[FAIL]" in nav_result:
                logger.warning("Recursive scrape navigate failed: %s", url[:80])
                return
            await asyncio.sleep(2)

            page_url = url
            try:
                raw = browser_use_get_url()
                parsed = json.loads(raw)
                page_url = parsed.get("url", url) if isinstance(parsed, dict) else url
            except Exception:
                pass

            page_title = ""
            try:
                raw = browser_use_get_title()
                parsed = json.loads(raw)
                page_title = parsed.get("title", "") if isinstance(parsed, dict) else ""
            except Exception:
                pass

            # Progressive scrolling (30 chunks × 3000px for deep content extraction)
            prev_height = 0
            for _ in range(30):
                try:
                    browser_use_scroll(direction="down", amount=3000)
                    dom_raw = browser_use_get_dom_state()
                    dom = json.loads(dom_raw)
                    sh = dom.get("scrollHeight", 0) if isinstance(dom, dict) else 0
                    if sh == prev_height:
                        break
                    prev_height = sh
                except Exception:
                    break
                await asyncio.sleep(0.5)

            # Extract all content
            text_content = ""
            try:
                raw = browser_use_extract_text(selector="body")
                parsed = json.loads(raw)
                text_content = parsed.get("text", "") if isinstance(parsed, dict) else raw
            except Exception:
                pass

            html_content = ""
            try:
                html_content = browser_use_extract_html()
            except Exception:
                pass

            links_raw = ""
            try:
                links_raw = browser_use_extract_links()
            except Exception:
                pass
            page_links = self._parse_links(links_raw)
            for link in page_links:
                collected["links"].add(link)

            # Handle content pagination (Next page on articles, etc.)
            pagination_texts = ["Next", "Next page", "›", "Load more"]
            for next_text in pagination_texts:
                try:
                    result = browser_use_click(text=next_text)
                    parsed = json.loads(result) if isinstance(result, str) else {}
                    if isinstance(parsed, dict) and parsed.get("success"):
                        await asyncio.sleep(1.5)
                        more_raw = browser_use_extract_text(selector="body")
                        more_parsed = json.loads(more_raw) if isinstance(more_raw, str) else {}
                        more_text = more_parsed.get("text", "") if isinstance(more_parsed, dict) else ""
                        if more_text:
                            text_content += "\n\n[PAGE 2+]\n\n" + more_text
                except Exception:
                    pass

            text_content = text_content[:50000]

            page_record = {
                "url": page_url,
                "title": page_title,
                "text": text_content,
                "html": html_content[:20000] if html_content else "",
                "links": page_links,
                "scraped_at": datetime.datetime.now().isoformat(),
            }

            collected["pages"].append(page_record)

            # If depth < max, drill into child links (max 8)
            if depth < MAX_RECURSION_DEPTH:
                child_links = self._get_child_links(page_links, url)
                pdf_links = [l for l in child_links if l.lower().endswith(".pdf")]
                html_child_links = [l for l in child_links if not l.lower().endswith(".pdf") and not any(
                    x in l for x in ["#", "javascript:", "mailto:", "tel:", "logout", "login"])]

                for pdf_link in pdf_links[:5]:
                    self._update_status(0, f"Downloading PDF: {pdf_link.split('/')[-1][:40]}")
                    pdf_data = await self._download_and_extract_pdf(pdf_link)
                    if pdf_data:
                        collected["pages"].append(pdf_data)

                if html_child_links:
                    drill_urls = await self._filter_drill_links(html_child_links[:15], topic, page_title)
                    for child_url in drill_urls[:3]:
                        try:
                            await asyncio.wait_for(
                                self._recursive_scrape(child_url, topic, collected, depth + 1),
                                timeout=90,
                            )
                        except (asyncio.TimeoutError, Exception) as e:
                            logger.warning("Child scrape timeout/error: %s - %s", child_url[:60], e)

        except Exception as e:
            logger.warning("Failed to scrape %s: %s", url, e)

    def _get_child_links(self, links: list[str], parent_url: str) -> list[str]:
        """Get relevant child links from the same domain."""
        from urllib.parse import urlparse
        parent_netloc = urlparse(parent_url).netloc
        childs = []
        for link in links:
            try:
                parsed = urlparse(link)
                # Same domain or meaningful subdomain, not external ads/social
                if parsed.netloc and parent_netloc in parsed.netloc:
                    if not any(x in link for x in ["#", "javascript:", "mailto:", "tel:", "logout", "login"]):
                        childs.append(link)
            except Exception:
                pass
        return childs[:20]

    async def _filter_drill_links(self, urls: list[str], topic: str, context: str) -> list[str]:
        """Use LLM to choose which links to drill into for deeper content."""
        if not urls:
            return []
        model = resolve_model("research") or self.nim_model or "qwen/qwen3-coder-480b-a35b-instruct"
        url_list = "\n".join(f"{i + 1}. {u}" for i, u in enumerate(urls))
        prompt = (
            f"Current page context: '{context[:80]}'\n"
            f"Research topic: '{topic}'\n\n"
            f"From the URLs below (all same-domain), select up to 5 that are MOST likely to contain\n"
            f"in-depth educational content, lesson pages, problem sets, PDFs, or detailed explanations\n"
            f"relevant to the topic. Skip navigation, About, Contact, Privacy pages.\n\n"
            f"{url_list}\n\n"
            "Return ONLY the numbers, comma-separated. No explanations."
        )
        try:
            resp = await self._client.chat(
                model=model, messages=[{"role": "user", "content": prompt}],
                max_tokens=256, temperature=0.1,
            )
            nums = [int(n.strip()) for n in re.findall(r"\d+", resp.content)]
            return [urls[i - 1] for i in nums if 0 < i <= len(urls)][:5]
        except Exception:
            return urls[:3]

    # ─── PDF Extraction ──────────────────────────────────────────

    async def _download_and_extract_pdf(self, url: str) -> Optional[dict]:
        """Download a PDF and extract its text content."""
        if url in self._seen_urls:
            return None
        self._seen_urls.add(url)

        try:
            import requests
            resp = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.get(url, timeout=15, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                }),
            )
            if resp.status_code != 200:
                return None

            pdf_path = MEMORY_DIR / f"_temp_{abs(hash(url))}.pdf"
            pdf_path.write_bytes(resp.content)

            text_content = ""
            try:
                import pdfplumber
                with pdfplumber.open(str(pdf_path)) as pdf:
                    pages_text = []
                    for page in pdf.pages[:200]:
                        t = page.extract_text()
                        if t:
                            pages_text.append(t)
                    text_content = "\n\n".join(pages_text)
            except Exception:
                pass

            try:
                pdf_path.unlink()
            except Exception:
                pass

            if text_content:
                return {
                    "url": url,
                    "title": f"PDF: {url.split('/')[-1][:60]}",
                    "text": text_content[:100000],
                    "html": "",
                    "links": [],
                    "scraped_at": datetime.datetime.now().isoformat(),
                }
        except Exception as e:
            logger.debug("PDF extraction failed for %s: %s", url, e)
        return None

    # ─── Link Parsing ────────────────────────────────────────────

    def _parse_links(self, raw: str) -> list[str]:
        links = []
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(parsed, dict):
                items = parsed.get("links", [])
                for item in items:
                    if isinstance(item, dict):
                        href = item.get("href", "")
                        if href:
                            url = self._extract_real_url(href)
                            if url.startswith("http"):
                                links.append(url)
                    elif isinstance(item, str):
                        url = self._extract_real_url(item)
                        if url.startswith("http"):
                            links.append(url)
            elif isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "url" in item:
                        links.append(item["url"])
                    elif isinstance(item, str):
                        links.append(item)
        except (json.JSONDecodeError, TypeError):
            urls = re.findall(r"https?://[^\s\"'>)]+", raw)
            links = urls
        return links

    def _extract_real_url(self, href: str) -> str:
        """Extract the real URL from Google's /url?q=... redirect format."""
        try:
            if "/url?" in href and "q=" in href:
                from urllib.parse import parse_qs, urlparse
                parsed = urlparse(href if href.startswith("http") else "https://www.google.com" + href)
                qs = parse_qs(parsed.query)
                if "q" in qs:
                    return qs["q"][0]
        except Exception:
            pass
        return href

    async def _filter_relevant(self, urls: list[str], query: str) -> list[str]:
        if len(urls) <= 10:
            return urls
        model = resolve_model("research") or self.nim_model or "qwen/qwen3-coder-480b-a35b-instruct"
        url_list = "\n".join(f"{i + 1}. {u}" for i, u in enumerate(urls))
        prompt = (
            f"Select the {min(len(urls), 50)} URLs most relevant to: '{query}'.\n"
            "Prioritize educational content, detailed guides, problem sets, official resources.\n"
            "Skip ads, social media, forums, video pages (unless directly relevant).\n"
            "Return ONLY the numbers, comma-separated.\n\n" + url_list
        )
        try:
            resp = await self._client.chat(
                model=model, messages=[{"role": "user", "content": prompt}],
                max_tokens=512, temperature=0.1,
            )
            nums = [int(n.strip()) for n in re.findall(r"\d+", resp.content)]
            return [urls[i - 1] for i in nums if 0 < i <= len(urls)][:50]
        except Exception:
            return urls[:50]

    # ─── Raw Data to .md ─────────────────────────────────────────

    def _build_raw_md(self, topic: str, data: dict, iterations: list) -> str:
        lines = [
            f"# Raw Research Data: {topic}",
            f"**Generated:** {datetime.datetime.now().isoformat()}",
            f"**Search Queries:** {', '.join(data.get('search_queries', []))}",
            f"**Iterations:** {len(iterations)}",
            f"**Total Pages Scraped:** {len(data.get('pages', []))}",
            f"**Total Links Collected:** {len(data.get('links', []))}",
            "",
            "---",
            "## Research Iterations",
            "",
        ]
        for it in iterations:
            lines.extend([
                f"### Iteration {it['iteration']}",
                f"- Queries: {', '.join(it.get('queries', []))}",
                f"- Pages scraped: {it['pages_count']}",
                f"- Summary: {it.get('summary', 'N/A')}",
                "",
            ])

        lines.extend(["---", "## ALL Collected Links", ""])
        for link in data.get("links", []):
            lines.append(f"- {link}")

        lines.extend(["", "---", "## Page Contents", ""])
        for idx, page in enumerate(data.get("pages", []), 1):
            lines.extend([
                f"### Page {idx}: {page.get('title', 'Untitled')}",
                f"**URL:** {page.get('url', 'N/A')}",
                f"**Scraped At:** {page.get('scraped_at', 'N/A')}",
                "",
                page.get("text", "No text extracted")[:50000],
                "",
            ])

        return "\n".join(lines)

    # ─── Skill Reading ───────────────────────────────────────────

    def _read_skills(self) -> dict[str, str]:
        contents = {}
        for name in ["pdf", "svg", "chart"]:
            skill_file = SKILL_DIR / name / "SKILL.md"
            if skill_file.exists():
                try:
                    contents[name] = skill_file.read_text(encoding="utf-8")
                except Exception as e:
                    logger.warning("Failed to read skill %s: %s", name, e)
                    contents[name] = ""
            else:
                contents[name] = ""
        return contents

    # ─── PDF Report Generation via LLM ───────────────────────────

    async def _generate_report(self, topic: str, raw_md: str, skill_contents: dict, output_path: str) -> dict:
        model = resolve_model("research") or self.nim_model or "qwen/qwen3-coder-480b-a35b-instruct"
        raw_preview = raw_md[:80000]
        pdf_skill = skill_contents.get("pdf", "")[:4000]
        svg_skill = skill_contents.get("svg", "")[:4000]
        chart_skill = skill_contents.get("chart", "")[:4000]

        prompt = (
            "You are Veronica, FRIDAY's research report architect. You write exhaustive textbook-quality research reports.\n\n"
            f"Generate a create_pdf() sections JSON array for a comprehensive research report on: '{topic}'.\n"
            "The report should be thorough — cover every subtopic with detailed paragraphs, tables, "
            "charts, and structured data from the raw research.\n\n"
            "Return a JSON array in this EXACT flat format — no markdown fences, no explanations, no wrapper:\n"
            '[\n'
            '  {"type": "heading", "text": "Section Title", "level": 1},\n'
            '  {"type": "paragraph", "text": "Detailed body text here."},\n'
            '  {"type": "table", "headers": ["Col1","Col2"], "rows": [["a","b"]], "caption": "Caption"},\n'
            '  {"type": "chart", "chart_type": "bar", "data": [10,20,30], '
            '"labels": ["X","Y","Z"], "title": "Chart", "xlabel": "x", "ylabel": "y"},\n'
            '  {"type": "bullets", "items": ["Key point 1", "Key point 2"]},\n'
            '  {"type": "numbered", "items": ["Step 1", "Step 2"]},\n'
            '  {"type": "divider"},\n'
            '  {"type": "code", "text": "code here"}\n'
            ']\n\n'
            "Use ALL element types: heading(1-3), paragraph, table, chart(bar,line,pie,timeline), bullets, numbered, divider, code.\n"
            "Write at least 80 sections. Cover every topic from the raw research with detailed paragraphs.\n"
            "Include a References section at the end with all source URLs.\n\n"
            f"RAW RESEARCH DATA:\n{raw_preview}\n\n"
            f"PDF SKILL GUIDE:\n{pdf_skill}\n\n"
            f"SVG SKILL GUIDE:\n{svg_skill}\n\n"
            f"CHART SKILL GUIDE:\n{chart_skill}\n\n"
            "REPORT STRUCTURE:\n"
            "1. Executive Summary\n"
            "2. Methodology\n"
            "3-13. Detailed topic analysis (one section per subtopic from the raw data)\n"
            "14. Comparative Analysis (tables)\n"
            "15. Visualizations (charts)\n"
            "16. References (ALL source URLs)\n\n"
            "RULES:\n"
            "- Return ONLY valid JSON array. No markdown fences, no wrapper text.\n"
            "- Each element is a dict with 'type' and required fields.\n"
            "- Write at least 80 sections. Be thorough but concise in each paragraph (3-6 sentences).\n"
            "- Every source URL from the raw data must appear in the References section table.\n"
            "- Use tables and charts wherever structured data exists in the research.\n"
            "- Write in formal, professional English."
        )

        try:
            resp = await self._client.chat(
                model=model, messages=[{"role": "user", "content": prompt}],
                max_tokens=32000, temperature=0.3,
            )
            sections_raw = resp.content.strip()
            if sections_raw.startswith("```"):
                sections_raw = sections_raw.split("\n", 1)[1]
                if sections_raw.endswith("```"):
                    sections_raw = sections_raw.rsplit("```", 1)[0]
            sections_raw = sections_raw.strip()

            sections = json.loads(sections_raw)
            if not isinstance(sections, list):
                sections = [{"type": "paragraph", "text": str(sections)}]

            from friday.tools.doc_tools import create_pdf
            pdf_result = await create_pdf(
                sections=sections, title=f"Research Report: {topic}", output_path=output_path,
            )
            pdf_result["model"] = model
            return pdf_result

        except (json.JSONDecodeError, Exception) as e:
            logger.warning("LLM report failed (%s), building fallback report", e)
            try:
                fallback_resp = await self._client.chat(
                    model=model,
                    messages=[{
                        "role": "user",
                        "content": (
                            "Write a structured report outline and key findings as a JSON array for create_pdf(). "
                            f"Topic: {topic}\n\n"
                            f"Raw data:\n{raw_md[:60000]}\n\n"
                            "Return JSON array with heading(1-3), paragraph, table, bullets, divider elements. "
                            "At least 30 sections covering the main topics. No markdown fences, just raw JSON."
                        )
                    }],
                    max_tokens=16000, temperature=0.3,
                )
                raw = fallback_resp.content.strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                sections = json.loads(raw)
                if not isinstance(sections, list):
                    raise ValueError("not a list")
            except Exception:
                lines = raw_md[:80000].split("\n")
                sections = [
                    {"type": "heading", "text": f"Research Report: {topic}", "level": 1},
                    {"type": "paragraph", "text": f"Auto-generated by Veronica on {datetime.datetime.now().isoformat()}"},
                    {"type": "divider"},
                ]
                chunk = []
                for line in lines:
                    if line.startswith("#") and chunk:
                        sections.append({"type": "paragraph", "text": "\n".join(chunk).strip()})
                        chunk = []
                        sections.append({"type": "heading", "text": line.lstrip("#").strip(), "level": min(line.count("#"), 3)})
                    elif line.strip():
                        chunk.append(line)
                if chunk:
                    sections.append({"type": "paragraph", "text": "\n".join(chunk).strip()})
            from friday.tools.doc_tools import create_pdf
            result = await create_pdf(
                sections=sections, title=f"Research Report: {topic}", output_path=output_path,
            )
            result["model"] = model
            return result
