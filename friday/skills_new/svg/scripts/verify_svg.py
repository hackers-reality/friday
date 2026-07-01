"""
friday/skills/svg/scripts/verify_svg.py

Structural + visual verification for a generated SVG:
  - parses XML to catch malformed markup
  - checks for a viewBox attribute
  - renders to PNG at multiple sizes (800px and, if square, 24px/16px icon
    sizes) so small-size legibility can be checked visually

Usage:
    python verify_svg.py output.svg [--out-dir ./verify_render]
"""
import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import cairosvg


def structural_checks(svg_path: Path):
    issues = []
    raw = svg_path.read_text(encoding="utf-8")

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        issues.append(f"XML parse error — malformed SVG: {e}")
        return issues, None

    if "viewBox" not in root.attrib:
        issues.append("Missing viewBox attribute — SVG will not scale cleanly in containers.")

    if len(list(root)) == 0:
        issues.append("SVG root has no child elements — likely empty output.")

    view_box = root.attrib.get("viewBox")
    is_square = False
    if view_box:
        parts = view_box.split()
        if len(parts) == 4:
            w, h = float(parts[2]), float(parts[3])
            is_square = abs(w - h) < 0.01

    return issues, is_square


def render_previews(svg_path: Path, out_dir: Path, is_square: bool):
    out_dir.mkdir(parents=True, exist_ok=True)
    sizes = [800]
    if is_square:
        sizes += [24, 16]  # icon-scale legibility check

    rendered = []
    for size in sizes:
        out_path = out_dir / f"preview_{size}px.png"
        cairosvg.svg2png(url=str(svg_path), write_to=str(out_path), output_width=size)
        rendered.append(out_path)
    return rendered


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("svg_path")
    ap.add_argument("--out-dir", default="./verify_render")
    args = ap.parse_args()

    svg_path = Path(args.svg_path)
    if not svg_path.exists():
        print(f"File not found: {svg_path}")
        sys.exit(1)

    print(f"Verifying: {svg_path}\n")

    issues, is_square = structural_checks(svg_path)
    if issues and "XML parse error" in issues[0]:
        print("FATAL:", issues[0])
        sys.exit(1)

    images = render_previews(svg_path, Path(args.out_dir), bool(is_square))
    print(f"Rendered {len(images)} preview(s) to {args.out_dir}/ — view these before delivering:")
    for img in images:
        print(f"  {img}")
    if is_square:
        print("  (square viewBox detected — included 24px/16px renders to check icon legibility at small size)")

    print()
    if issues:
        print("ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("Structural checks passed. Still view the rendered previews before delivering.")
        sys.exit(0)


if __name__ == "__main__":
    main()
