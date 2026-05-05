"""Instagram messaging via web automation."""

import time
import webbrowser

def instagram_message(username: str, message: str) -> str:
    """Send Instagram message using web automation.
    
    Strategy (as user described):
    1. Open Instagram chat page (not profile)
    2. Search for similar name
    3. Click whichever comes first
    4. Type message and send
    """
    try:
        # Step 1: Open Instagram direct inbox (not profile)
        inbox_url = "https://www.instagram.com/direct/inbox/"
        webbrowser.open(inbox_url)
        time.sleep(3)
        
        # Step 2: Use vision to find "New Message" or search
        from friday_tools import see_screen, click, type_text, press_key
        
        # Locate new message button
        see_screen("Find the New Message button or search bar on Instagram")
        time.sleep(1)
        
        # Click new message or search
        click(target="New Message button")
        time.sleep(2)
        
        # Step 3: Type username to search
        type_text(username)
        time.sleep(2)
        
        # Click first result
        click(target="first search result")
        time.sleep(2)
        
        # Step 4: Type message and send
        type_text(message)
        time.sleep(1)
        press_key('enter')
        
        return f"Message sent to {username} via Instagram"
        
    except Exception as e:
        return f"Instagram message failed: {e}"


def instagram_search_and_message(username: str, message: str) -> str:
    """Alternative: Open chat URL directly and search."""
    try:
        # Direct approach: open new message URL
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
        return f"Instagram search and message failed: {e}"
