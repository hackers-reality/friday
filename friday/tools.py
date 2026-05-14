def clipboard_get() -> str:
    """Get clipboard content using pyperclip."""
    try:
        import pyperclip
        return pyperclip.paste()
    except Exception as e:
        return f"[FAIL] Clipboard read error: {e}"

def clipboard_set(text: str) -> str:
    """Set clipboard content using pyperclip."""
    try:
        import pyperclip
        pyperclip.copy(text)
        return "Clipboard set"
    except Exception as e:
        return f"[FAIL] Clipboard write error: {e}"