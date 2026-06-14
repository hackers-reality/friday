#!/usr/bin/env python3
"""F.R.I.D.A.Y. — Single Command Startup."""
import subprocess
import sys
import os
import time
import webbrowser
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(ROOT, "friday", "friday_ui", "backend")
FRONTEND = os.path.join(ROOT, "friday", "friday_ui", "frontend")
DIST = os.path.join(FRONTEND, "dist")


def build_frontend():
    if os.path.isdir(os.path.join(DIST, "assets")):
        return True
    print("[FRIDAY] Building frontend...")
    r = subprocess.run(
        ["npx", "vite", "build"],
        cwd=FRONTEND,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(f"[FRIDAY] Build failed: {r.stderr[:200]}")
        return False
    print("[FRIDAY] Frontend built.")
    return True


def open_browser():
    time.sleep(2)
    webbrowser.open("http://localhost:8000")


def main():
    print("=" * 50)
    print("  F.R.I.D.A.Y.")
    print("  Fully Responsive Intelligent Digital Assistant Youth")
    print("=" * 50)

    if not build_frontend():
        sys.exit(1)

    print("[FRIDAY] Starting server...")
    threading.Thread(target=open_browser, daemon=True).start()

    sys.path.insert(0, BACKEND)
    os.chdir(BACKEND)

    import uvicorn
    from main import app
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
