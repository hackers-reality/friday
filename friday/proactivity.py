"""
Friday Proactive Commentary - Phase 2.3 & 2.4
Vision + LLM pipeline for proactive screen watching and commentary.
"""
from __future__ import annotations

import os
import sys`
import time`
import threading`
import json`
import io`
import base64`
from typing import Optional, Callable, Dict, Any`

from PIL import ImageGrab`

try:`
    from friday.screen_watcher import get_active_window_info, ScreenWatcher`
    SCREEN_WATCHER_AVAILABLE = True`
except Exception as e:`
    print(f"[ProactiveCommentary] screen_watcher not available: {e}")`
    SCREEN_WATCHER_AVAILABLE = False`

try:`
    from dotenv import load_dotenv`
    load_dotenv()`
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")`
    if GOOGLE_API_KEY:`
        GEMINI_AVAILABLE = True`
    else:`
        GEMINI_AVAILABLE = False`
except Exception:`
    GEMINI_AVAILABLE = False`


# ─── Vision Analysis ────────────────────────────────────────────`

def analyze_screenshot_with_vision(`
    screenshot_bytes: bytes,`
    question: str = "What do you see on this screen? Be concise and conversational.",`
) -> str:`
    """`
    Send screenshot to Gemini Vision model and get analysis.`
    """`
    if not GEMINI_AVAILABLE:`
        return "Vision analysis unavailable: GOOGLE_API_KEY not set."`

    try:`
        import requests`

        # Convert to base64`
        img_b64 = base64.b64encode(screenshot_bytes).decode()`

        # Try models in order`
        models_to_try = [`
            "gemini-2.0-flash",`
            "gemini-1.5-flash",`
            "gemini-2.0-flash-lite",`
        ]`

        for model in models_to_try:`
            try:`
                r = requests.post(`
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",`
                    headers={"Content-Type": "application/json"},`
                    params={"key": GOOGLE_API_KEY},`
                    json={`
                        "contents": [{`
                            "parts": [`
                                {"text": question},`
                                {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},`
                            ]`
                        }],`
                        "generationConfig": {"maxOutputTokens": 300, "temperature": 0.7},`
                    },`
                    timeout=30,`
                )`

                if r.status_code == 200:`
                    data = r.json()`
                    candidates = data.get("candidates", [])`
                    if candidates and candidates[0].get("content", {}).get("parts"):`
                        return candidates[0]["content"]["parts"][0].get("text", "No analysis.")`
                elif r.status_code == 404:`
                    continue`
            except Exception:`
                continue`

        return "All vision models failed."`

    except Exception as e:`
        return f"Vision error: {str(e)}"`


# ─── Proactive Commentary System (Phase 2.3) ────────────────────`

class ProactiveCommentary:`
    """`
    Watches screen and makes contextual comments like:`
    "I see you're watching My Hero Academia" or`
    "Working on Friday again? Want some help?"`
    """`

    def __init__(`
        self,`
        on_comment: Optional[Callable[[str], None]] = None,`
        check_interval: float = 10.0,  # Check every 10 seconds`
        enable_vision: bool = True,`
    ):`
        self.on_comment = on_comment`
        self.check_interval = check_interval`
        self.enable_vision = enable_vision`
        self._stop_event = threading.Event()`
        self._thread: Optional[threading.Thread] = None`
        self._last_comment_time = 0.0`
        self._last_window_title = ""`
        self._comment_cooldown = 30.0  # Don't comment more than every 30s`
        self._current_context = {`
            "window_title": "Unknown",`
            "process_name": "Unknown",`
            "last_analysis": "",`
        }`

    def _generate_commentary(self) -> Optional[str]:`
        """Generate a contextual comment based on current screen."""`
        if not GEMINI_AVAILABLE and not SCREEN_WATCHER_AVAILABLE:`
            return None`

        try:`
            # Get window info`
            if SCREEN_WATCHER_AVAILABLE:`
                info = get_active_window_info()`
            else:`
                info = {"title": "Unknown", "process_name": "Unknown"}`

            window_title = info.get("title", "Unknown")`
            process_name = info.get("process_name", "Unknown")`

            # Skip if window hasn't changed`
            if window_title == self._last_window_title:`
                return None`

            self._last_window_title = window_title`
            self._current_context["window_title"] = window_title`
            self._current_context["process_name"] = process_name`

            # Generate comment using LLM`
            comment = self._generate_contextual_comment(window_title, process_name)`

            if comment:`
                self._last_comment_time = time.time()`
                return comment`

        except Exception as e:`
            print(f"[ProactiveCommentary] Error: {e}")`

        return None`

    def _generate_contextual_comment(self, window_title: str, process_name: str) -> str:`
        """Use LLM to generate a natural comment about current activity."""`
        if not GEMINI_AVAILABLE:`
            # Simple rule-based comments`
            title_lower = window_title.lower()`
            if "youtube" in title_lower:`
                if "anime" in title_lower or "my hero" in title_lower:`
                    return "I see you're watching anime. Nice choice!"`
                return "Watching YouTube, I see."`
            if "vs code" in title_lower or "code" in title_lower:`
                return "Coding again? Need any help?"`
            if "chrome" in process_name.lower() or "brave" in process_name.lower():`
                return "Browsing the web? Let me know if you need a search."`
            return ""`

        try:`
            import requests`

            prompt = f"""You are Friday, a witty AI assistant watching the user's screen.`
The user's active window is: "{window_title}"`
Process: {process_name}`

Generate a SHORT (1 sentence max) conversational comment like:`
- "I see you're watching My Hero Academia. Enjoying it?"`
- "Working on Friday again? Want some help?"`
- "Browsing GitHub? Need me to search anything?"`
- "I see you're playing a game. Should I close it and open your course?"`

Be witty, brief, and contextual. Don't be annoying. 1 sentence only.`
"""`

            r = requests.post(`
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",`
                headers={"Content-Type": "application/json"},`
                params={"key": GOOGLE_API_KEY},`
                json={`
                    "contents": [{"parts": [{"text": prompt}]}],`
                    "generationConfig": {"maxOutputTokens": 100, "temperature": 0.8},`
                },`
                timeout=10,`
            )`

            if r.status_code == 200:`
                data = r.json()`
                candidates = data.get("candidates", [])`
                if candidates and candidates[0].get("content", {}).get("parts"):`
                    comment = candidates[0]["content"]["parts"][0].get("text", "").strip()`
                    # Remove quotes if present`
                    if comment.startswith('"') and comment.endswith('"'):`
                        comment = comment[1:-1]`
                    return comment`

        except Exception as e:`
            print(f"[ProactiveCommentary] LLM error: {e}")`

        return ""`

    def _vision_analysis(self) -> Optional[str]:`
        """Capture screenshot and analyze with vision model."""`
        if not self.enable_vision or not GEMINI_AVAILABLE:`
            return None`

        try:`
            screenshot = ImageGrab.grab()`
            buffer = io.BytesIO()`
            screenshot.save(buffer, format="JPEG", quality=60)`
            screenshot_bytes = buffer.getvalue()`

            question = """Analyze this screen briefly. What is the user doing?`
Be concise (1-2 sentences max). If they're working, say so.`
If they're watching something, mention it. If they're gaming, note it."""`


            analysis = analyze_screenshot_with_vision(screenshot_bytes, question)`
            self._current_context["last_analysis"] = analysis`
            return analysis`

        except Exception as e:`
            print(f"[ProactiveCommentary] Vision error: {e}")`
            return None`

    def _run(self):`
        """Main commentary loop."""`
        while not self._stop_event.is_set():`
            try:`
                # Check if enough time has passed since last comment`
                if time.time() - self._last_comment_time < self._comment_cooldown:`
                    time.sleep(self.check_interval)`
                    continue`

                # Generate commentary`
                comment = self._generate_commentary()`

                if comment and self.on_comment:`
                    try:`
                        self.on_comment(comment)`
                    except Exception as e:`
                        print(f"[ProactiveCommentary] Callback error: {e}")`

                # Optional vision analysis (less frequent)`
                if self.enable_vision and time.time() % 60 < self.check_interval:`
                    analysis = self._vision_analysis()`
                    if analysis and "error" not in analysis.lower():`
                        # Vision analysis could trigger additional comments`
                        pass`

            except Exception as e:`
                print(f"[ProactiveCommentary] Loop error: {e}")`

            # Sleep in small increments`
            for _ in range(int(self.check_interval * 10)):`
                if self._stop_event.is_set():`
                    return`
                time.sleep(0.1)`

    def start(self):`
        """Start the commentary thread."""`
        if self._thread and self._thread.is_alive():`
            return`
        self._stop_event.clear()`
        self._thread = threading.Thread(target=self._run, daemon=True)`
        self._thread.start()`
        print("[ProactiveCommentary] Started.")`

    def stop(self):`
        """Stop the commentary thread."""`
        self._stop_event.set()`
        if self._thread:`
            self._thread.join(timeout=5)`
        print("[ProactiveCommentary] Stopped.")`


# ─── Integration with Friday Tools ────────────────────────────────`

_proactive_instance: Optional[ProactiveCommentary] = None`
_proactive_lock = threading.Lock()`

def get_proactive_commentary(`
    on_comment: Optional[Callable[[str], None]] = None,`
    enable_vision: bool = True,`) -> ProactiveCommentary:`
    """Get or create the singleton commentary instance."""`
    global _proactive_instance`
    with _proactive_lock:`
        if _proactive_instance is None:`
            _proactive_instance = ProactiveCommentary(`
                on_comment=on_comment,`
                enable_vision=enable_vision,`
            )`
        else:`
            if on_comment:`
                _proactive_instance.on_comment = on_comment`
            _proactive_instance.enable_vision = enable_vision`
        return _proactive_instance`


def proactive_commentary_tool(action: str = "status", enable: bool = True) -> str:`
    """`
    Friday tool to control proactive commentary.`
    Actions: start, stop, status`
    """`
    commentary = get_proactive_commentary()`

    if action == "start" or enable:`
        commentary.start()`
        return "[OK] Proactive commentary started. I'll watch your screen and comment."`

    if action == "stop":`
        commentary.stop()`
        return "⏸ Proactive commentary stopped."`

    if action == "status":`
        return f"Proactive Commentary: {'Running' if commentary._thread and commentary._thread.is_alive() else 'Stopped'}"`

    if action == "analyze_now":`
        analysis = commentary._vision_analysis()`
        return analysis or "Vision analysis unavailable."`

    return f"Unknown action: {action}"`


# ─── Vision + LLM Pipeline (Phase 2.4) ──────────────────────`

def vision_llm_pipeline(`
    user_query: str,`
    screenshot_bytes: Optional[bytes] = None,`) -> str:`
    """`
    Complete pipeline: screenshot -> vision analysis -> LLM response.`
    """`
    if not screenshot_bytes:`
        try:`
            screenshot = ImageGrab.grab()`
            buffer = io.BytesIO()`
            screenshot.save(buffer, format="JPEG", quality=70)`
            screenshot_bytes = buffer.getvalue()`
        except Exception as e:`
            return f"Screenshot capture failed: {e}"`

    # Analyze with vision`
    analysis = analyze_screenshot_with_vision(`
        screenshot_bytes,`
        f"{user_query}\n\nBe concise and helpful."`
    )`

    return analysis`


if __name__ == "__main__":`
    # Test`
    print("Testing Proactive Commentary...")`

    def on_comment(comment: str):`
        print(f"[Friday] {comment}")`

    commentary = get_proactive_commentary(on_comment=on_comment, enable_vision=True)`
    commentary.check_interval = 5.0`
    commentary.start()`

    try:`
        while True:`
            time.sleep(1)`
    except KeyboardInterrupt:`
        commentary.stop()`
