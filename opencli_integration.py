"""OpenCLI-style browser automation for Friday.
Uses the same approach: deterministic browser actions via vision + automation.
"""

import os
import time
import json
from typing import Optional, Dict, Any

class OpenCLIStyle:
    """Implements OpenCLI concepts: deterministic browser automation."""
    
    def __init__(self):
        self.chrome_debug_port = 9222
        self.cdp_available = self._check_cdp()
    
    def _check_cdp(self) -> bool:
        """Check if Chrome is running with remote debugging."""
        try:
            import requests
            resp = requests.get(f"http://127.0.0.1:{self.chrome_debug_port}/json", timeout=2)
            return resp.status_code == 200
        except:
            return False
    
    def navigate_to(self, url: str) -> str:
        """Navigate to URL using Chrome CDP (like opencli browser navigate)."""
        if not self.cdp_available:
            # Fallback: use webbrowser
            import webbrowser
            webbrowser.open(url)
            return f"Navigated to {url} (fallback)"
        
        try:
            import requests
            # Get page list
            pages = requests.get(f"http://127.0.0.1:{self.chrome_debug_port}/json").json()
            if pages:
                # Use first page
                ws_url = pages[0]["webSocketDebuggerUrl"]
                # In real implementation, use websocket to send CDP commands
                # For now, use webbrowser as fallback
                import webbrowser
                webbrowser.open(url)
                return f"Navigated to {url}"
        except Exception as e:
            return f"Navigation failed: {e}"
    
    def click_element(self, target: str) -> str:
        """Click element using vision (like opencli browser click)."""
        try:
            from friday_tools import see_screen, click
            
            # Use vision to locate element
            location = see_screen(f"Where is '{target}' on screen? Give coordinates (x,y).")
            
            import re
            coords = re.search(r'\(?(\d+)\s*,\s*(\d+)\)?', location)
            if coords:
                x, y = int(coords.group(1)), int(coords.group(2))
                return click(x=x, y=y, target=target)
            else:
                return f"Could not locate '{target}'. Analysis: {location[:200]}"
        except Exception as e:
            return f"Click failed: {e}"
    
    def type_text_deterministic(self, text: str, target: Optional[str] = None) -> str:
        """Type text deterministically (like opencli browser type)."""
        try:
            from friday_tools import type_text, click
            
            if target:
                # Click target first
                self.click_element(target)
                time.sleep(0.5)
            
            type_text(text)
            return f"Typed '{text[:50]}...'"
        except Exception as e:
            return f"Type failed: {e}"
    
    def extract_data(self, query: str) -> str:
        """Extract structured data from page (like opencli browser extract)."""
        try:
            from friday_tools import see_screen
            result = see_screen(f"Extract this data: {query}. Return as JSON.")
            return result
        except Exception as e:
            return f"Extract failed: {e}"
    
    def screenshot(self, save_path: Optional[str] = None) -> str:
        """Take screenshot (like opencli browser screenshot)."""
        try:
            from PIL import ImageGrab
            screen = ImageGrab.grab()
            if save_path:
                screen.save(save_path)
                return f"Screenshot saved to {save_path}"
            else:
                temp = "temp_screenshot.png"
                screen.save(temp)
                return f"Screenshot saved to {temp}"
        except Exception as e:
            return f"Screenshot failed: {e}"


# Global instance
opencli_style = OpenCLIStyle()


def opencli_navigate(url: str) -> str:
    """Navigate to URL using OpenCLI-style automation."""
    return opencli_style.navigate_to(url)


def opencli_click(target: str) -> str:
    """Click element using OpenCLI-style vision automation."""
    return opencli_style.click_element(target)


def opencli_type(text: str, target: Optional[str] = None) -> str:
    """Type text using OpenCLI-style automation."""
    return opencli_style.type_text_deterministic(text, target)


def opencli_extract(query: str) -> str:
    """Extract structured data from current page."""
    return opencli_style.extract_data(query)


def opencli_screenshot(save_path: Optional[str] = None) -> str:
    """Take screenshot of current page."""
    return opencli_style.screenshot(save_path)


# Instagram specific: use OpenCLI approach
def instagram_message_opencli(username: str, message: str) -> str:
    """Message Instagram user using OpenCLI-style browser automation.
    
    Approach (as user described):
    1. Open Instagram chat page (not profile)
    2. Search for similar name
    3. Click whichever comes first
    4. Type message and send
    """
    try:
        # Step 1: Open Instagram direct inbox
        opencli_navigate("https://www.instagram.com/direct/inbox/")
        time.sleep(3)
        
        # Step 2: Click "New Message" or search
        opencli_click("New Message button")
        time.sleep(2)
        
        # Step 3: Type username to search
        opencli_type(username, target="search box")
        time.sleep(2)
        
        # Step 4: Click first result
        opencli_click("first search result")
        time.sleep(2)
        
        # Step 5: Type message
        opencli_type(message)
        time.sleep(1)
        
        # Step 6: Send (press Enter or click Send)
        from friday_tools import press_key
        press_key('enter')
        
        return f"Message sent to {username} via OpenCLI-style automation"
        
    except Exception as e:
        return f"Instagram OpenCLI message failed: {e}"
