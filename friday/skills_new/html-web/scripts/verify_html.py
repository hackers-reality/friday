"""
friday/skills/html-web/scripts/verify_html.py

Screenshots an HTML file at desktop/tablet/mobile breakpoints and captures
any JS console errors during load, for pre-delivery visual + functional QA.

Usage:
    python verify_html.py output.html [--out-dir ./verify_render]
"""
import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BREAKPOINTS = [(1280, 900, "desktop"), (768, 1024, "tablet"), (375, 812, "mobile")]


def verify(html_path: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    file_uri = html_path.resolve().as_uri()

    console_errors = []
    screenshots = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width, height, name in BREAKPOINTS:
            page = browser.new_page(viewport={"width": width, "height": height})
            page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}")
                     if msg.type == "error" else None)
            page.on("pageerror", lambda exc: console_errors.append(f"[pageerror] {exc}"))

            page.goto(file_uri)
            page.wait_for_timeout(500)  # let any async render settle

            out_path = out_dir / f"preview_{name}.png"
            page.screenshot(path=str(out_path), full_page=True)
            screenshots.append(out_path)
            page.close()
        browser.close()

    return screenshots, console_errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html_path")
    ap.add_argument("--out-dir", default="./verify_render")
    args = ap.parse_args()

    html_path = Path(args.html_path)
    if not html_path.exists():
        print(f"File not found: {html_path}")
        sys.exit(1)

    print(f"Verifying: {html_path}\n")
    screenshots, console_errors = verify(html_path, Path(args.out_dir))

    print(f"Rendered {len(screenshots)} breakpoint screenshot(s) — view these before delivering:")
    for s in screenshots:
        print(f"  {s}")

    print()
    if console_errors:
        print(f"CONSOLE ERRORS DURING LOAD ({len(console_errors)}):")
        for e in console_errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("No console errors detected. Still view the screenshots for layout/overlap issues before delivering.")
        sys.exit(0)


if __name__ == "__main__":
    main()
