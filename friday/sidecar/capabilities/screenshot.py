"""Screenshot capability for sidecar client."""
from __future__ import annotations

import base64
from io import BytesIO
from typing import Dict

from PIL import ImageGrab


class ScreenshotHandler:
    async def handle(self, action: str, params: Dict) -> Dict:
        try:
            img = ImageGrab.grab()
            buf = BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            return {"png_base64": b64}
        except Exception as e:
            return {"error": str(e)}
