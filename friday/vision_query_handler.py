"""Reactive vision query handler with fast-path CV answers and NIM fallback."""
from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from io import BytesIO
from typing import Optional

try:
    from PIL import Image
except ImportError:
    Image = None

from friday.frame_buffer import CVLabels, FrameBuffer
from friday.logging_utils import configure_logging
from friday.nim_client import InferenceClient
from friday.nim_router import resolve_model, classify_task_type
from friday.orchestration_config import ensure_config


logger = configure_logging(__name__)


_VISION_KEYWORDS = {
    "holding": "objects in hands, hand regions",
    "hold": "objects in hands, hand regions",
    "desk": "objects on desk, workspace surfaces",
    "room": "people and objects in room",
    "who": "faces and people",
    "there": "presence of people",
}


def _classify_intent_fast(query: str) -> str:
    q = query.lower()
    if any(k in q for k in ("holding", "hold", "hand")):
        return "holding"
    if any(k in q for k in ("desk", "table", "on my")):
        return "scene_objects"
    if any(k in q for k in ("who", "anyone", "person", "room")):
        return "presence"
    return "ambiguous"


def _focus_areas_from_query(query: str) -> str:
    q = query.lower()
    matches = [focus for key, focus in _VISION_KEYWORDS.items() if key in q]
    if matches:
        return ", ".join(dict.fromkeys(matches))
    return "salient objects, people, and scene context"


def _quick_answer_from_labels(query: str, labels: Optional[CVLabels]) -> Optional[str]:
    if labels is None:
        return None

    q = query.lower()
    if "anyone" in q or "who" in q or "in the room" in q:
        if labels.faces:
            return f"I can see {len(labels.faces)} person{'s' if len(labels.faces) != 1 else ''} in view."
        return "I do not currently see anyone in view."

    if "holding" in q or "hold" in q:
        if labels.hands and labels.objects:
            names = [obj.class_name for obj in labels.objects[:3]]
            return f"I can see a hand near: {', '.join(names)}."
        if labels.hands:
            return "I can see a hand, but I cannot clearly identify the object yet."
        return "I cannot currently see a hand holding an object."

    if "desk" in q or "what's on" in q or "what is on" in q:
        if labels.objects:
            names = [obj.class_name for obj in labels.objects[:5]]
            return f"I can currently see: {', '.join(names)}."
        return "I do not detect clear objects right now."

    return None


def _encode_frame_jpeg_base64(frame) -> Optional[str]:
    if Image is None:
        return None
    try:
        import cv2

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return None


@dataclass
class VisionQueryHandler:
    frame_buffer: FrameBuffer
    nim_client: Optional[InferenceClient] = None

    def __post_init__(self) -> None:
        cfg = ensure_config().get("camera", {})
        self.enabled = bool(cfg.get("vision_query", True))
        if self.nim_client is None:
            try:
                self.nim_client = InferenceClient()
            except Exception as exc:
                logger.warning("VisionQueryHandler NIM unavailable: %s", exc)
                self.nim_client = None

    async def handle_vision_query(self, query: str) -> str:
        if not self.enabled:
            return "Vision query handling is currently disabled."

        snapshot = self.frame_buffer.get_snapshot()
        if snapshot is None:
            return "I do not have camera context yet."

        intent = _classify_intent_fast(query)
        if intent == "ambiguous" and self.nim_client is not None:
            intent = await self._classify_intent_via_nim(query)

        quick = _quick_answer_from_labels(query, snapshot.cv_labels)
        if quick and intent != "holding":
            return quick

        if self.nim_client is None:
            return quick or "I can see the scene, but advanced vision reasoning is unavailable right now."

        encoded = _encode_frame_jpeg_base64(snapshot.raw_frame)
        if not encoded:
            return quick or "I could not encode the latest camera frame in time."

        focus = _focus_areas_from_query(query)
        prompt = (
            f"You are Friday, a personal AI assistant. The user asked: '{query}'. "
            "Analyze this image and answer concisely in 1-2 sentences. "
            f"Focus on: {focus}"
        )

        model = resolve_model("image_analysis") or "microsoft/phi-3-vision-128k-instruct"

        async def _nim_call() -> str:
            messages = [
                {"role": "system", "content": "You are Friday, a personal AI assistant."},
                {"role": "user", "content": f"[IMG]{encoded}[/IMG]\n\n{prompt}"},
            ]
            result = await self.nim_client.chat(
                model=model,
                messages=messages,
                max_tokens=300,
                temperature=0.1,
            )
            return result.content.strip() or "I could not derive a confident visual answer."

        try:
            return await asyncio.wait_for(_nim_call(), timeout=4.0)
        except asyncio.TimeoutError:
            return quick or "I can see a hand holding an object, but I need more time to identify it specifically."
        except Exception as exc:
            logger.warning("Vision NIM query failed: %s", exc)
            return quick or "I can see the scene, but I could not complete deep image analysis right now."

    async def _classify_intent_via_nim(self, query: str) -> str:
        if self.nim_client is None:
            return "ambiguous"
        try:
            messages = [
                {"role": "system", "content": "Classify the user query into one word only: holding, scene_objects, presence, ambiguous."},
                {"role": "user", "content": query},
            ]
            result = await asyncio.wait_for(
                self.nim_client.chat(
                    model=resolve_model("reasoning") or "meta/llama-3.3-70b-instruct",
                    messages=messages,
                    max_tokens=8,
                    temperature=0.0,
                ),
                timeout=0.8,
            )
            text = (result.content or "").strip().lower()
            for label in ("holding", "scene_objects", "presence", "ambiguous"):
                if label in text:
                    return label
        except Exception:
            pass
        return "ambiguous"
