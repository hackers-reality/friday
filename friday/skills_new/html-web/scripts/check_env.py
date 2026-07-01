"""
friday/skills/html-web/scripts/check_env.py

Verifies playwright is installed AND the chromium browser binary is
actually downloaded (a common silent-failure point — pip install alone
does not fetch the browser).

Usage:
    python check_env.py
"""
import importlib
import sys


def check_playwright_package():
    print("=== Playwright package ===")
    try:
        importlib.import_module("playwright")
        print("  playwright  OK")
        return True
    except ImportError:
        print("  playwright  MISSING -> pip install playwright")
        return False


def check_chromium_binary():
    print("\n=== Chromium browser binary ===")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
        print("  chromium binary OK")
        return True
    except Exception as e:
        print(f"  chromium binary MISSING or broken ({e})")
        print("  -> run: python -m playwright install chromium")
        return False


if __name__ == "__main__":
    pkg_ok = check_playwright_package()
    binary_ok = check_chromium_binary() if pkg_ok else False

    print()
    if pkg_ok and binary_ok:
        print("Environment ready.")
        sys.exit(0)
    else:
        print("Fix missing items above before running verify_html.py.")
        sys.exit(1)
