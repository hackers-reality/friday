"""Create proper deep_search_streaming.py."""

content = '''"""Deep Research Streaming module for Friday."""

def deep_research_streaming(topic: str, url: str = None, depth: int = 3, progress_callback=None) -> str:
    """Deep research with real-time progress streaming via callback.

    progress_callback(stage, message) where stage is:
    'started', 'searching', 'fetching', 'analyzing', 'synthesizing', 'saving', 'complete'
    """
    try:
        from ddgs import DDGS
    except Exception as e:
        return f"Deep research unavailable: {e}"

    if progress_callback:
        progress_callback('started', f"Research started: {topic}")

    depth = max(1, min(int(depth), 5))
    import re
    from datetime import datetime
    slug = re.sub(r"[^a-z0-9]+", "_", topic.lower())[:40].strip("_") or "research"

    import os
    report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "friday_reports")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f"{slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")

    raw_sections = [
        "# STARK RESEARCH REPORT",
        f"## Topic: {topic}",
        f"**Generated:** {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}",
        "",
        "---",
    ]

    sources_used = []

    if url:
        if progress_callback:
            progress_callback('fetching', f"Fetching primary source: {url}")
        from html.parser import HTMLParser
        import requests

        class _TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.parts = []
                self._skip = False
            def handle_starttag(self, tag, attrs):
                if tag in ("script", "style", "nav", "footer", "header"):
                    self._skip = True
            def handle_endtag(self, tag):
                if tag in ("script", "style", "nav", "footer", "header"):
                    self._skip = False
            def handle_data(self, data):
                if not self._skip:
                    txt = data.strip()
                    if txt:
                        self.parts.append(txt)

        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            parser = _TextExtractor()
            parser.feed(resp.text)
            content = " ".join(parser.parts)[:3000]
            raw_sections.append(f"## Primary Source: {url}")
            raw_sections.append(content)
            raw_sections.append("")
            sources_used.append(url)
            if progress_callback:
                progress_callback('analyzing', f"Primary source fetched: {len(content)} chars")
        except Exception as e:
            raw_sections.append(f"*Failed to fetch {url}: {e}*")
            if progress_callback:
                progress_callback('analyzing', f"Failed to fetch primary source: {e}")

    if progress_callback:
        progress_callback('searching', f"DuckDuckGo search: {topic}")

    queries = [topic]
    if depth >= 2:
        queries.append(f"{topic} how to")
    if depth >= 3:
        queries.append(f"{topic} examples")
    if depth >= 4:
        queries.append(f"{topic} vs")
    if depth >= 5:
        queries.append(f"{topic} alternatives")

    all_results = []
    try:
        with DDGS() as ddgs:
            for q in queries:
                try:
                    results = list(ddgs.text(q, max_results=5))
                    all_results.extend(results)
                    if progress_callback:
                        progress_callback('searching', f"Found {len(results)} results for: {q}")
                except Exception as e:
                    if progress_callback:
                        progress_callback('searching', f"Search failed for {q}: {e}")
    except Exception as e:
        raw_sections.append(f"*Search error: {e}*")

    fetched = 0
    for r in all_results[:depth * 5]:
        link = r.get("href") or r.get("url")
        if not link or link in sources_used:
            continue
        if progress_callback:
            progress_callback('fetching', f"Fetching: {link[:80]}")
        try:
            resp = requests.get(link, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            parser = _TextExtractor()
            parser.feed(resp.text)
            content = " ".join(parser.parts)[:2000]
            raw_sections.append(f"## Source: {r.get('title', 'Untitled')}")
            raw_sections.append(f"URL: {link}")
            raw_sections.append(content)
            raw_sections.append("")
            sources_used.append(link)
            fetched += 1
            if progress_callback:
                progress_callback('fetching', f"Fetched {fetched}/{depth*5}: {r.get('title', '')[:50]}")
        except Exception as e:
            if progress_callback:
                progress_callback('fetching', f"Failed to fetch: {e}")

    if progress_callback:
        progress_callback('synthesizing', f"Synthesizing {fetched} sources...")

    synthesis = " ".join(raw_sections[6:])
    summary = synthesis[:800] + "..." if len(synthesis) > 800 else synthesis

    final_report = (
        "\n".join(raw_sections)
        + "\n\n---\n\n## Synthesis\n\n"
        + summary
        + "\n\n---\n\n## Sources ({})\n".format(len(sources_used))
        + "\n".join(f"{i+1}. {s}" for i, s in enumerate(sources_used))
    )

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(final_report)

    if progress_callback:
        progress_callback('saving', f"Report saved: {report_path}")
        progress_callback('complete', f"Research complete: {len(sources_used)} sources")

    return (
        "### RESEARCH COMPLETE\n"
        f"**Topic:** {topic}\n"
        f"**Sources swept:** {len(sources_used)}\n"
        f"**Pages deep-fetched:** {fetched}\n"
        f"**Report saved:** {report_path}\n\n"
        f"**SYNTHESIS PREVIEW:**\n{synthesis[:600]}..."
    )
'''

with open('deep_search_streaming.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('deep_search_streaming.py created with proper indentation')
print('Verifying...')

import sys
sys.path.insert(0, '.')
try:
    from deep_search_streaming import deep_research_streaming
    print('Import OK!')
except Exception as e:
    print(f'Import failed: {e}')
