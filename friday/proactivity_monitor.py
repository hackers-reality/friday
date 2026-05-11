"""
Friday Proactive Screen Monitor - Phase 2.2 Enhanced
Watches screen continuously, analyzes with AI, makes proactive comments.
"""
from typing import Optional, Callable, Dict, Any__

import os
import sys
import time
import threading
import io
import base64
from typing import Optional, Callable, Dict, Any
from datetime import datetime

from PIL import ImageGrab

# Try to import AI components
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from friday.screen_watcher import get_active_window_info, ScreenWatcher
    SCREEN_WATCHER_AVAILABLE = True
except ImportError:
    SCREEN_WATCHER_AVAILABLE = False

# ─── Configuration ──────────────────────────────────────

CHECK_INTERVAL = 10.0  # Check screen every 10 seconds
COMMENT_INTERVAL = 60.0  # Make AI comment every 60 seconds
SCREENSHOT_SIZE = (800, 450)  # Resize for faster processing
JPEG_QUALITY = 60

# ─── Proactive Screen Monitor ──────────────────────────────

class ProactiveScreenMonitor:
    """
    Continuously monitors the screen, detects what the user is doing,
    and makes proactive comments via AI analysis.
    """
    
    def __init__(
        self,
        comment_callback: Optional[Callable[[str], None]] = None,
        ai_enabled: bool = True,
    ):
        self.comment_callback = comment_callback  # Called with AI comments
        self.ai_enabled = ai_enabled and GEMINI_AVAILABLE
        
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_comment_time = 0.0
        self._last_screenshot_hash = ""
        
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        self.client = None
        
        if self.ai_enabled and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[ProactiveMonitor] Gemini init error: {e}")
                self.ai_enabled = False
        
        # State tracking
        self.current_activity = "Unknown"
        self.activity_start_time = time.time()
        self.screenshot_count = 0
        
    def _calculate_image_hash(self, image_bytes: bytes) -> str:
        """Simple hash to detect if screen changed."""
        return str(hash(image_bytes) % 1000000)
    
    def _capture_and_analyze(self) -> Optional[Dict[str, Any]]:
        """Capture screen and analyze with AI."""
        try:
            # Capture
            screenshot = ImageGrab.grab()
            screenshot = screenshot.resize(SCREENSHOT_SIZE)
            
            buffer = io.BytesIO()
            screenshot.save(buffer, format="JPEG", quality=JPEG_QUALITY)
            image_bytes = buffer.getvalue()
            
            # Check if screen changed
            new_hash = self._calculate_image_hash(image_bytes)
            if new_hash == self._last_screenshot_hash:
                return None  # No change
            self._last_screenshot_hash = new_hash
            self.screenshot_count += 1
            
            # Get active window
            window_info = {}
            if SCREEN_WATCHER_AVAILABLE:
                try:
                    window_info = get_active_window_info()
                except:
                    pass
            
            result = {
                "success": True,
                "image_bytes": image_bytes,
                "window_title": window_info.get("title", "Unknown"),
                "process_name": window_info.get("process_name", "Unknown"),
            }
            
            # AI Analysis
            if self.ai_enabled and self.client:
                try:
                    image_part = types.Part(
                        inline_data=types.Blob(
                            mime_type="image/jpeg",
                            data=image_bytes
                        )
                    )
                    
                    text_part = types.Part(
                        text="""
                        You are Friday's vision system. Analyze this screenshot briefly.
                        1. What is the user doing? (watching anime, coding, browsing, gaming, etc.)
                        2. What app/window are they in?
                        3. One casual, observant comment (1 sentence max).
                        If they're watching anime, mention the show if recognizable.
                        If they're coding, offer help casually.
                        Don't repeat yourself. Be concise. No preamble.
                        """
                    )
                    
                    response = self.client.models.generate_content(
                        model="gemini-3.1-flash-preview",
                        contents=[image_part, text_part]
                    )
                    
                    result["ai_comment"] = response.text
                    
                except Exception as e:
                    result["ai_error"] = str(e)
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _run(self):
        """Main monitoring loop."""
        while not self._stop_event.is_set():
            try:
                now = time.time()
                
                # Capture and analyze
                result = self._capture_and_analyze()
                
                if result and result.get("success"):
                    window_title = result.get("window_title", "")
                    process_name = result.get("process_name", "")
                    ai_comment = result.get("ai_comment", "")
                    
                    # Update activity tracking
                    current_activity = f"{process_name}: {window_title}"
                    if current_activity != self.current_activity:
                        self.current_activity = current_activity
                        self.activity_start_time = now
                        print(f"[ProactiveMonitor] Activity changed: {window_title[:50]}")
                    
                    # Make proactive comment periodically
                    if ai_comment and (now - self._last_comment_time) >= COMMENT_INTERVAL:
                        self._last_comment_time = now
                        
                        comment = f"[Friday Vision] {ai_comment}"
                        print(comment)
                        
                        if self.comment_callback:
                            try:
                                self.comment_callback(ai_comment)
                            except Exception as e:
                                print(f"[ProactiveMonitor] Callback error: {e}")
                
                elif result and not result.get("success") and "error" in result:
                    print(f"[ProactiveMonitor] Error: {result['error']}")
                
            except Exception as e:
                print(f"[ProactiveMonitor] Loop error: {e}")
            
            # Sleep in small increments
            for _ in range(int(CHECK_INTERVAL * 10)):
                if self._stop_event.is_set():
                    return
                time.sleep(0.1)
    
    def start(self):
        """Start the monitor thread."""
        if self._thread and self._thread.is_alive():
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print("[ProactiveMonitor] Started. Friday is now watching your screen.")
    
    def stop(self):
        """Stop the monitor thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        print("[ProactiveMonitor] Stopped.")
    
    def get_status(self) -> str:
        """Get monitor status."""
        lines = ["### PROACTIVE SCREEN MONITOR STATUS", ""]
        lines.append(f"[OK] Running: {self._thread is not None and self._thread.is_alive()}")
        lines.append(f"[OK] AI Enabled: {self.ai_enabled}")
        lines.append(f"📸 Screenshots captured: {self.screenshot_count}")
        lines.append(f"📺 Current activity: {self.current_activity[:50]}")
        lines.append(f"⏱ Active for: {time.time() - self.activity_start_time:.0f}s")
        return "\n".join(lines)


# ─── Singleton ───────────────────────────────────────────

_monitor_instance: Optional[ProactiveScreenMonitor] = None
_monitor_lock = threading.Lock()

def get_proactive_monitor(
    comment_callback: Optional[Callable[[str], None]] = None,
    ai_enabled: bool = True,
) -> ProactiveScreenMonitor:
    """Get or create the singleton monitor."""
    global _monitor_instance
    with _monitor_lock:
        if _monitor_instance is None:
            _monitor_instance = ProactiveScreenMonitor(
                comment_callback=comment_callback,
                ai_enabled=ai_enabled,
            )
        else:
            if comment_callback:
                _monitor_instance.comment_callback = comment_callback
        return _monitor_instance


# ─── Integration with Friday Tools ─────────────────────────

def proactive_monitor_tool(action: str = "status") -> str:
    """Tool for controlling the proactive monitor."""
    monitor = get_proactive_monitor()
    
    if action == "start":
        monitor.start()
        return "[OK] Proactive screen monitor started. Friday is now watching."
    
    elif action == "stop":
        monitor.stop()
        return "🛑 Proactive screen monitor stopped."
    
    elif action == "status":
        return monitor.get_status()
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Proactive Screen Monitor...\n")
    
    def on_comment(comment: str):
        print(f"[Callback] Friday says: {comment}")
    
    monitor = get_proactive_monitor(comment_callback=on_comment)
    monitor.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()
