from __future__ import annotations

import base64
from io import BytesIO
from typing import Any, Dict


async def handle(action: str, params: Dict[str, Any]) -> dict:
    if action not in {"capture", "capture_screen"}:
        return {"error": f"unsupported screenshot action: {action}"}
    try:
        from PIL import ImageGrab
        image = ImageGrab.grab()
        buf = BytesIO()
        image.save(buf, format="PNG")
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        return {"png_base64": encoded}
    except Exception as exc:
        return {"error": str(exc)}
