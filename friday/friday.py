#!/usr/bin/env python3
"""F.R.I.D.A.Y. — Single command launcher."""
import subprocess
import sys
import os
import time
import webbrowser
import signal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "friday", "friday_ui", "backend")
FRONTEND = os.path.join(ROOT, "friday", "friday_ui", "frontend")
DIST = os.path.join(FRONTEND, "dist")

backend_proc = None

def shutdown(sig=None, frame=None):
    global backend_proc
    print("\n[FRIDAY] Shutting down...")
    if backend_proc:
        backend_proc.terminate()
        try:
            backend_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend_proc.kill()
    print("[FRIDAY] Goodbye, sir.")
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

def is_port_used(port):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def main():
    global backend_proc

    print("=" * 50)
    print("  F.R.I.D.A.Y.")
    print("  Fully Responsive Intelligent Digital Assistant Youth")
    print("=" * 50)

    if is_port_used(8000):
        print("[OK] Backend already running on :8000")
    else:
        print("[..] Starting backend...")
        backend_proc = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=BACKEND,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for i in range(10):
            time.sleep(1)
            if not is_port_used(8000):
                print("[..] Waiting for backend... %d" % (i+1))
            else:
                break
        if is_port_used(8000):
            print("[OK] Backend running on http://localhost:8000")
        else:
            print("[!!] Backend failed to start")
            return

    if os.path.exists(os.path.join(DIST, "index.html")):
        print("[OK] Frontend built — serving from dist/")
        frontend = subprocess.Popen(
            [sys.executable, "-m", "http.server", "3000", "--directory", DIST],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(1)
        print("[OK] Frontend running on http://localhost:3000")
    else:
        print("[!!] Frontend not built. Run: cd friday/friday_ui/frontend && npx vite build")
        return

    print("\n  Open http://localhost:3000 in your browser\n")
    webbrowser.open("http://localhost:3000")

    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, EOFError):
        shutdown()

if __name__ == "__main__":
    main()
