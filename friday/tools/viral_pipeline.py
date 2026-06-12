"""
Viral Video Pipeline — auto-generate AI videos and upload to YouTube.
End-to-end: content ideation → text-to-video → upload → thumbnail → analytics
"""
from __future__ import annotations

import base64
import json
import os
import random
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any, Optional

from friday._paths import FRIDAY_MEMORY
from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

_PIPELINE_DIR = os.path.join(FRIDAY_MEMORY, "viral_pipeline")
_VIDEO_DIR = os.path.join(_PIPELINE_DIR, "videos")
_THUMBNAIL_DIR = os.path.join(_PIPELINE_DIR, "thumbnails")
_HISTORY_FILE = os.path.join(_PIPELINE_DIR, "history.jsonl")
_IDEAS_FILE = os.path.join(_PIPELINE_DIR, "content_ideas.json")


def _ensure_dirs():
    for d in (_PIPELINE_DIR, _VIDEO_DIR, _THUMBNAIL_DIR):
        os.makedirs(d, exist_ok=True)


def _load_json(path: str, default=None):
    if default is None:
        default = {}
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return default


def _save_json(path: str, data):
    _ensure_dirs()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _log_history(entry: dict):
    _ensure_dirs()
    with open(_HISTORY_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


CATEGORIES = {
    "22": "People & Blogs", "23": "Comedy", "24": "Entertainment",
    "25": "News & Politics", "26": "Howto & Style", "27": "Education",
    "28": "Science & Technology", "29": "Nonprofits & Activism",
    "10": "Music", "20": "Gaming", "1": "Film & Animation",
}

TRENDING_TOPICS = [
    "future of AI in daily life",
    "top 10 programming languages 2026",
    "how quantum computers work",
    "the history of the internet in 60 seconds",
    "explaining blockchain like I'm 5",
    "why your brain loves shortcuts",
    "the science behind viral videos",
    "how to learn anything faster",
    "what happens when you stop scrolling",
    "the hidden math in nature",
]


# ── Content Ideation ──

def generate_content_ideas(count: int = 5, niche: str = "technology") -> list[dict]:
    """Generate content ideas using LLM."""
    prompt = (
        f"Generate {count} viral video content ideas in the {niche} niche. "
        "For each idea, provide:\n"
        "- title (catchy, under 60 chars)\n"
        "- description (2-3 sentences)\n"
        "- tags (comma-separated, 5-10 tags)\n"
        "- hook (first 5 seconds script)\n"
        "- duration_seconds (30-60)\n\n"
        "Return as JSON array. No markdown."
    )

    try:
        from friday.tools.ai_tools import model_query
        result = model_query(
            prompt=prompt,
            system="You are a viral content strategist. Output only valid JSON arrays.",
            model="opencode/big-pickle",
        )
        text = ""
        if isinstance(result, dict):
            text = result.get("text", "") or result.get("response", "") or result.get("content", "")
        else:
            text = str(result)
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text
            text = text.rsplit("```", 1)[0].strip()

        ideas = json.loads(text) if text else []
        if isinstance(ideas, list):
            for idea in ideas:
                idea["id"] = uuid.uuid4().hex[:8]
                idea["niche"] = niche
                idea["created_at"] = datetime.now().isoformat()
            _save_json(_IDEAS_FILE, {"ideas": ideas, "generated_at": datetime.now().isoformat()})
            return ideas
    except Exception as e:
        logger.warning("Content idea generation failed: %s", e)

    # Fallback
    ideas = []
    for topic in random.sample(TRENDING_TOPICS, min(count, len(TRENDING_TOPICS))):
        ideas.append({
            "id": uuid.uuid4().hex[:8],
            "title": topic.title(),
            "niche": niche,
            "created_at": datetime.now().isoformat(),
        })
    _save_json(_IDEAS_FILE, {"ideas": ideas, "generated_at": datetime.now().isoformat()})
    return ideas


# ── Thumbnail Generation ──

def generate_thumbnail(title: str, output_path: str = "") -> str:
    """Generate a simple thumbnail image with text overlay."""
    if not output_path:
        output_path = os.path.join(_THUMBNAIL_DIR, f"thumb_{uuid.uuid4().hex[:8]}.png")

    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (1280, 720), color=(20, 20, 40))
        draw = ImageDraw.Draw(img)

        # Draw gradient-like background
        for i in range(720):
            r = int(30 + (i / 720) * 60)
            g = int(20 + (i / 720) * 40)
            b = int(50 + (i / 720) * 80)
            draw.line([(0, i), (1280, i)], fill=(r, g, b))

        # Add accent shapes
        for _ in range(5):
            x = random.randint(0, 1280)
            y = random.randint(0, 720)
            s = random.randint(50, 200)
            color = (random.randint(100, 255), random.randint(50, 200), random.randint(50, 200))
            draw.ellipse([x, y, x + s, y + s], fill=(*color, 80), outline=None)

        # Title text
        try:
            font = ImageFont.truetype("arial.ttf", 48)
        except Exception:
            font = ImageFont.load_default()

        words = title.split()
        lines = []
        current = ""
        for w in words:
            test = f"{current} {w}".strip()
            if len(test) > 25:
                lines.append(current)
                current = w
            else:
                current = test
        lines.append(current)

        y_pos = 300
        for line in lines[:3]:
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
            x_pos = (1280 - tw) // 2
            draw.text((x_pos + 2, y_pos + 2), line, fill=(0, 0, 0), font=font)
            draw.text((x_pos, y_pos), line, fill=(255, 255, 255), font=font)
            y_pos += 60

        img.save(output_path, "PNG")
        return output_path
    except Exception as e:
        logger.warning("Thumbnail generation error: %s", e)
        return ""


# ── Video Generation ──

def create_video(idea: dict) -> dict:
    """Generate a video from a content idea using Higgsfield."""
    _ensure_dirs()
    prompt_text = idea.get("hook", idea.get("title", "A video about technology"))

    try:
        from friday.tools.higgsfield_tools import higgsfield_generate_video
        result = higgsfield_generate_video(
            prompt=f"{prompt_text}, cinematic quality, vibrant colors, engaging visuals",
            duration=10,
            resolution="720p",
        )

        if isinstance(result, dict) and result.get("success") and result.get("file_path"):
            video_path = result["file_path"]
            final_path = os.path.join(_VIDEO_DIR, f"video_{idea['id']}.mp4")
            import shutil
            shutil.copy2(video_path, final_path)
            return {"success": True, "video_path": final_path, "prompt": prompt_text}

        return {"error": str(result)}
    except Exception as e:
        return {"error": str(e)}


# ── YouTube Upload ──

def upload_to_youtube(video_path: str, idea: dict, thumbnail_path: str = "") -> dict:
    """Upload video and set thumbnail."""
    try:
        from friday.youtube_client import YouTubeClient
        yt = YouTubeClient()

        upload_result = yt.upload_video(
            file_path=video_path,
            title=idea.get("title", "FRIDAY AI Video"),
            description=idea.get("description", "Generated by FRIDAY AI"),
            tags=idea.get("tags", ["AI", "technology"]),
            category_id="28",
            privacy_status="public",
        )

        if upload_result.get("success") and thumbnail_path and os.path.exists(thumbnail_path):
            yt.set_thumbnail(upload_result["video_id"], thumbnail_path)

        return upload_result
    except Exception as e:
        return {"error": str(e)}


# ── Full Pipeline ──

def run_pipeline(niche: str = "technology", count: int = 1) -> str:
    """Run the full viral video pipeline end-to-end."""
    _ensure_dirs()
    pipeline_id = uuid.uuid4().hex[:8]
    start = time.time()

    log = {
        "pipeline_id": pipeline_id,
        "niche": niche,
        "started_at": datetime.now().isoformat(),
        "steps": [],
    }

    # Step 1: Generate ideas
    ideas = generate_content_ideas(count=count, niche=niche)
    log["steps"].append({"step": "ideation", "ideas": len(ideas)})

    if not ideas:
        log["status"] = "failed_no_ideas"
        _log_history(log)
        return json.dumps({"error": "Failed to generate content ideas", "pipeline_id": pipeline_id}, indent=2)

    results = []
    for idea in ideas[:count]:
        idea_result = {"idea": idea, "status": "pending"}

        # Step 2: Generate thumbnail
        thumb_path = generate_thumbnail(idea.get("title", "Video"))
        idea_result["thumbnail"] = thumb_path or "none"

        # Step 3: Generate video
        video_result = create_video(idea)
        if "error" in video_result:
            idea_result["status"] = "failed_video"
            idea_result["error"] = video_result["error"]
            results.append(idea_result)
            continue

        idea_result["video_path"] = video_result["video_path"]

        # Step 4: Upload
        upload_result = upload_to_youtube(
            video_result["video_path"],
            idea,
            thumb_path,
        )
        idea_result["upload"] = upload_result
        idea_result["status"] = "uploaded" if upload_result.get("success") else "failed_upload"
        results.append(idea_result)

        log["steps"].append({
            "step": "publish",
            "title": idea.get("title", "")[:60],
            "status": idea_result["status"],
        })

    log["results"] = results
    log["status"] = "completed"
    log["elapsed_seconds"] = round(time.time() - start)
    log["completed_at"] = datetime.now().isoformat()
    _log_history(log)

    summary = {
        "pipeline_id": pipeline_id,
        "niche": niche,
        "elapsed_seconds": round(time.time() - start),
        "total_ideas": len(ideas),
        "published": sum(1 for r in results if r.get("status") == "uploaded"),
        "failed": sum(1 for r in results if r.get("status", "").startswith("failed")),
        "results": [
            {
                "title": r["idea"].get("title", "")[:60],
                "status": r["status"],
                "url": r.get("upload", {}).get("url", ""),
                "video_id": r.get("upload", {}).get("video_id", ""),
            }
            for r in results
        ],
        "history_file": _HISTORY_FILE,
    }

    return json.dumps(summary, indent=2)


def get_ideas(niche: str = "technology") -> str:
    ideas = generate_content_ideas(count=5, niche=niche)
    if not ideas:
        return "Failed to generate ideas."

    lines = [f"### Content Ideas ({len(ideas)})"]
    for idea in ideas:
        title = idea.get("title", "?")
        desc = idea.get("description", "")[:100]
        tags = ", ".join((idea.get("tags") or [])[:3])
        lines.append(f"\n  '{title}'")
        lines.append(f"  {desc}")
        if tags:
            lines.append(f"  Tags: {tags}")
    return "\n".join(lines)


def get_history(limit: int = 10) -> str:
    if not os.path.exists(_HISTORY_FILE):
        return "No pipeline history yet."
    entries = []
    with open(_HISTORY_FILE) as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
    if not entries:
        return "No history."

    lines = [f"### Viral Pipeline History ({len(entries)} runs)"]
    for e in entries[-limit:]:
        pid = e.get("pipeline_id", "?")[:8]
        niche = e.get("niche", "?")
        status = e.get("status", "?")
        published = sum(1 for r in e.get("results", []) if r.get("status") == "uploaded")
        elapsed = e.get("elapsed_seconds", 0)
        lines.append(f"  [{pid}] {niche}: {status} ({published} published, {elapsed}s)")
    return "\n".join(lines)


# ── Tool ──

def viral_pipeline_tool(action: str = "status", **kwargs) -> str:
    """Viral Video Pipeline — auto-generate AI videos and upload to YouTube.
    
    Actions:
      status - Show pipeline status
      ideas [niche] - Generate content ideas
      run [niche] [count] - Run full pipeline: ideas → video → upload
      history - Show recent pipeline runs
    """
    if action == "status":
        ideas = _load_json(_IDEAS_FILE, {}).get("ideas", [])
        videos = len([f for f in os.listdir(_VIDEO_DIR) if f.endswith(".mp4")]) if os.path.exists(_VIDEO_DIR) else 0
        return json.dumps({
            "status": "ready",
            "cached_ideas": len(ideas),
            "generated_videos": videos,
            "youtube_oauth": "configure in google_oauth",
            "higgsfield_api": "set HIGGSFIELD_API_KEY",
        }, indent=2)

    elif action == "ideas":
        niche = kwargs.get("niche", "technology")
        return get_ideas(niche=niche)

    elif action == "run":
        niche = kwargs.get("niche", "technology")
        count = int(kwargs.get("count", 1))
        return run_pipeline(niche=niche, count=count)

    elif action == "history":
        return get_history(limit=int(kwargs.get("limit", 10)))

    return f"[FAIL] Unknown action: {action}"
