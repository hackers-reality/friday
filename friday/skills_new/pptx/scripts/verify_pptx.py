"""
friday/skills/pptx/scripts/verify_pptx.py

Renders every slide to JPEG for visual inspection and scans text content
for leftover placeholder/lorem-ipsum text before delivery.

Usage:
    python verify_pptx.py output.pptx [--dpi 150] [--out-dir ./verify_render]
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from pptx import Presentation

PLACEHOLDER_PATTERN = re.compile(
    r"\bx{3,}\b|lorem|ipsum|\bTODO\b|\[insert|this.*(page|slide).*layout",
    re.IGNORECASE,
)


def scan_placeholder_text(pptx_path: Path):
    prs = Presentation(str(pptx_path))
    hits = []
    for i, slide in enumerate(prs.slides, start=1):
        for shape in slide.shapes:
            if shape.has_text_frame:
                text = shape.text_frame.text
                if text and PLACEHOLDER_PATTERN.search(text):
                    hits.append(f"Slide {i}: {text!r}")
    return hits


def render_slides(pptx_path: Path, out_dir: Path, dpi: int):
    out_dir.mkdir(parents=True, exist_ok=True)
    if not shutil.which("soffice"):
        print("WARNING: soffice not found — skipping visual render. Run check_env.py.")
        return []
    subprocess.run(
        ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(pptx_path)],
        check=True,
    )
    pdf_path = out_dir / (pptx_path.stem + ".pdf")
    if not pdf_path.exists():
        print("WARNING: PDF conversion did not produce expected output.")
        return []
    prefix = out_dir / "slide"
    for old in out_dir.glob("slide-*.jpg"):
        old.unlink()
    subprocess.run(["pdftoppm", "-jpeg", "-r", str(dpi), str(pdf_path), str(prefix)], check=True)
    return sorted(out_dir.glob("slide-*.jpg"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pptx_path")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--out-dir", default="./verify_render")
    args = ap.parse_args()

    pptx_path = Path(args.pptx_path)
    if not pptx_path.exists():
        print(f"File not found: {pptx_path}")
        sys.exit(1)

    print(f"Verifying: {pptx_path}\n")

    placeholder_hits = scan_placeholder_text(pptx_path)
    images = render_slides(pptx_path, Path(args.out_dir), args.dpi)

    if images:
        print(f"Rendered {len(images)} slide image(s) to {args.out_dir}/ — view these before delivering:")
        for img in images:
            print(f"  {img}")

    print()
    if placeholder_hits:
        print("LEFTOVER PLACEHOLDER TEXT FOUND:")
        for hit in placeholder_hits:
            print(f"  - {hit}")
        sys.exit(1)
    else:
        print("No placeholder text detected. Still view the rendered images for overlap/overflow before delivering.")
        sys.exit(0)


if __name__ == "__main__":
    main()
