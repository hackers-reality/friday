"""
friday/skills/diagrams/scripts/check_env.py

Verifies mmdc (mermaid-cli) is installed and can actually render — catches
the common Windows failure mode where the Chromium binary mmdc depends on
never downloaded.

Usage:
    python check_env.py
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TEST_DIAGRAM = "flowchart LR\n    A[\"Start\"] --> B[\"End\"]\n"


def check_mmdc_on_path():
    print("=== mmdc binary ===")
    found = shutil.which("mmdc")
    print(f"  mmdc {'OK (' + found + ')' if found else 'MISSING'}")
    if not found:
        print("    -> npm install -g @mermaid-js/mermaid-cli")
    return bool(found)


def check_mmdc_renders():
    print("\n=== mmdc render test ===")
    with tempfile.TemporaryDirectory() as tmp:
        mmd_path = Path(tmp) / "test.mmd"
        png_path = Path(tmp) / "test.png"
        mmd_path.write_text(TEST_DIAGRAM)
        try:
            result = subprocess.run(
                ["mmdc", "-i", str(mmd_path), "-o", str(png_path)],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0 and png_path.exists() and png_path.stat().st_size > 0:
                print("  Render test OK.")
                return True
            print(f"  Render test FAILED (exit {result.returncode}).")
            print(f"  stderr: {result.stderr[:500]}")
            if "chromium" in result.stderr.lower() or "browser" in result.stderr.lower():
                print("  -> Likely missing Chromium — run: npx puppeteer browsers install chrome")
            return False
        except subprocess.TimeoutExpired:
            print("  Render test TIMED OUT (60s) — likely stuck downloading Chromium on first run.")
            return False
        except FileNotFoundError:
            print("  mmdc not found on PATH.")
            return False


if __name__ == "__main__":
    on_path = check_mmdc_on_path()
    render_ok = check_mmdc_renders() if on_path else False

    print()
    if on_path and render_ok:
        print("Environment ready.")
        sys.exit(0)
    else:
        print("Fix items above before running diagram tasks.")
        sys.exit(1)
