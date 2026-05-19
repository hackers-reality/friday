"""Generate SEO-optimized metadata using NIM for a given video title/description."""
from __future__ import annotations

import json
from typing import Dict, Any, List

from friday.nim_client import InferenceClient
from friday.logging_utils import configure_logging

logger = configure_logging(__name__)


async def generate_metadata(title: str, description_draft: str = "", topic: str = "") -> Dict[str, Any]:
    nim = InferenceClient()
    prompt = (
        f"Generate YouTube metadata for a video titled '{title}'. Return JSON only:"
        "{tags: list[str] (max 15), description: str (200-300 words), chapters: list[{time: str, title: str}]}"
        f"\n\nDescription draft: {description_draft}\nTopic: {topic}"
    )
    result = await nim.chat(
        model="meta/llama-3.3-70b-instruct",
        messages=[{"role": "system", "content": "You are a YouTube SEO assistant. Return JSON only."},
                  {"role": "user", "content": prompt}],
        max_tokens=800,
    )
    text = result.content
    try:
        data = json.loads(text)
    except Exception:
        # Try to extract JSON substring
        try:
            start = text.find("{")
            end = text.rfind("}")
            data = json.loads(text[start:end+1]) if start != -1 and end != -1 else {"error": "invalid_response"}
        except Exception:
            data = {"error": "invalid_response"}

    # Validate
    tags = data.get("tags", []) if isinstance(data.get("tags", []), list) else []
    if len(tags) > 15:
        tags = tags[:15]
    desc = data.get("description", "")
    words = len(desc.split())
    if words < 150:
        data["description"] = (desc + " " + (description_draft or ""))[:1800]
    return {"tags": tags, "description": data.get("description", ""), "chapters": data.get("chapters", [])}
