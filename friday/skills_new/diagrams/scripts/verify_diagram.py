"""
friday/skills/diagrams/scripts/verify_diagram.py

Renders a .mmd Mermaid file to PNG and runs basic sanity checks. Mermaid
syntax errors sometimes fail silently or produce a garbled partial render
rather than a hard error, so this always reports the rendered file path for
manual visual review — don't trust a zero exit code alone.

Usage:
    python verify_diagram.py diagram.mmd [--width 1200] [--out preview.png]
"""
import argparse
import subprocess
import sys
from pathlib import Path


def verify(mmd_path: Path, out_path: Path, width: int):
    result = subprocess.run(
        ["mmdc", "-i", str(mmd_path), "-o", str(out_path), "-w", str(width)],
        capture_output=True, text=True,
    )

    if result.returncode != 0:
        print(f"mmdc exited with error (code {result.returncode}):")
        print(result.stderr)
        return False

    if not out_path.exists():
        print("mmdc reported success but no output file was created — treat as failure.")
        return False

    size = out_path.stat().st_size
    print(f"Rendered: {out_path} ({size / 1024:.1f} KB)")

    if size < 1000:
        print("WARNING: output file is suspiciously small — likely a near-empty/broken render. "
              "View the image to confirm.")
        return False

    print(f"\nView {out_path} before delivering — check for overlapping labels, "
          "correct arrow connections, and no clipped text inside node boxes.")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mmd_path")
    ap.add_argument("--width", type=int, default=1200)
    ap.add_argument("--out", default="preview.png")
    args = ap.parse_args()

    mmd_path = Path(args.mmd_path)
    if not mmd_path.exists():
        print(f"File not found: {mmd_path}")
        sys.exit(1)

    ok = verify(mmd_path, Path(args.out), args.width)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
