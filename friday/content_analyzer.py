"""Analyze comments and generate content ideas using NIM or simple heuristics."""
from __future__ import annotations

import json
from typing import List, Dict, Any

from friday.analytics_store import save_content_idea, get_top_videos
from friday.nim_client import InferenceClient
from friday.logging_utils import configure_logging

logger = configure_logging(__name__)


async def analyze_comments(comments: List[str]) -> Dict[str, Any]:
    try:
        nim = InferenceClient()
        prompt = (
            "Analyze these YouTube comments and return JSON: {sentiment: positive|mixed|negative, "
            "top_themes: list[str], complaints: list[str], praise: list[str]}. Comments: " + json.dumps(comments[:200])
        )
        result = await nim.chat(
            model="meta/llama-3.3-70b-instruct",
            messages=[{"role": "system", "content": "You are a content analysis assistant. Return JSON only."},
                      {"role": "user", "content": prompt}],
            max_tokens=512,
        )
        return json.loads(result.content)
    except Exception:
        text = " ".join(comments).lower()
        positive = sum(word in text for word in ("good", "great", "love", "awesome", "nice"))
        negative = sum(word in text for word in ("bad", "hate", "terrible", "boring", "dislike"))
        themes = []
        if "tutorial" in text:
            themes.append("tutorial")
        if "review" in text:
            themes.append("review")
        sentiment = "mixed"
        if positive > negative * 2:
            sentiment = "positive"
        elif negative > positive * 2:
            sentiment = "negative"
        return {"sentiment": sentiment, "top_themes": themes, "complaints": [], "praise": []}


def generate_content_ideas(channel_id: str, comments_by_video: Dict[str, List[str]]):
    # Cluster by simple title keywords (use top videos as seed)
    videos = get_top_videos(channel_id, n=10)
    ideas = []
    for v in videos[:3]:
        vid = v.get("video_id")
        comments = comments_by_video.get(vid, [])
        analysis = analyze_comments(comments)
        idea = f"Follow-up on {v.get('title')}: address {', '.join(analysis.get('top_themes',[])[:3])}"
        reasoning = f"Based on top video performance and comments: {analysis.get('sentiment')}"
        save_content_idea(channel_id, idea, reasoning, score=0.5)
        ideas.append({"idea": idea, "reasoning": reasoning})
    return ideas
