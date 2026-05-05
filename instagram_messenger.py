"""Instagram messaging via OpenCLI-style browser automation."""

import os
import json
import time
import re

def instagram_message(username: str, message: str) -> str:
    """Send Instagram message via web automation.
    
    Strategy (as user described):
    1. Open Instagram chat page (not profile)
    2. Search for similar name
    3. Click first result
    4. Type message and send
    """
    try:
        import webbrowser
        # Step 1: Open Instagram chat/direct page
        chat_url = "https://www.instagram.com/direct/inbox/"
        webbrowser.open(chat_url)
        time.sleep(3)
        
        # Step 2: Search for user (using see_screen to locate search)
        from friday_tools import see_screen, click, type_text
        
        # Wait for page to load
        see_screen("Is Instagram inbox loaded? Wait for search bar.")
        time.sleep(2)
        
        # Click search or new message button
        click(target="search bar")
        time.sleep(1)
        
        # Type username to search
        type_text(username)
        time.sleep(2)
        
        # Click first result
        click(target="first search result")
        time.sleep(2)
        
        # Type message
        type_text(message)
        time.sleep(1)
        
        # Press enter to send
        from friday_tools import press_key
        press_key('enter')
        
        return f"Message sent to {username} via Instagram"
        
    except Exception as e:
        return f"Instagram message failed: {e}"

def opencli_instagram(username: str, message: str) -> str:
    """Use OpenCLI approach: deterministic browser automation for Instagram.
    
    OpenCLI concept: Use logged-in browser session, no tokens needed.
    Since we can't install OpenCLI here, we replicate the approach:
    - Use see_screen() to find elements
    - Use click() and type_text() for interaction
    - All via logged-in Chrome session (if using Chrome)
    """
    try:
        # Approach: Direct to Instagram's web interface
        import webbrowser
        url = f"https://www.instagram.com/direct/new/?text={username}"
        webbrowser.open(url)
        time.sleep(3)
        
        from friday_tools import see_screen, click, type_text, press_key
        
        # Verify page loaded
        see_screen("Is Instagram message composer loaded?")
        
        # Type message
        type_text(message)
        time.sleep(1)
        
        # Send
        press_key('enter')
        
        return f"Message sent to {username}"
        
    except Exception as e:
        return f"OpenCLI-style Instagram failed: {e}"

# Note: OpenCLI itself would be installed separately:
# npm install -g opencli
# Then: opencli browser navigate "https://instagram.com"
# opencli browser type "message text"
# opencli browser click "Send button"
