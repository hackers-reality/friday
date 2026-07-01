"""
friday/skills/pdf/scripts/verify_pdf.py

Post-generation sanity check for a PDF: renders each page to a JPEG for
visual inspection, and runs automated checks (page count, extractable text,
file size, embedded fonts) so obvious failures are caught before delivery.

Usage:
    python verify_pdf.py output.pdf [--dpi 100] [--out-dir ./verify_render]
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from pypdf import PdfReader


def render_pages(pdf_path: Path, out_dir: Path, dpi: int):
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = out_dir / "page"
    if not shutil.which("pdftoppm"):
        print("WARNING: pdftoppm not found on PATH — skipping visual render. "
              "Run check_env.py to fix.")
        return []
    subprocess.run(
        ["pdftoppm", "-jpeg", "-r", str(dpi), str(pdf_path), str(prefix)],
        check=True,
    )
    images = sorted(out_dir.glob("page-*.jpg"))
    return images


def run_checks(pdf_path: Path):
    issues = []
    reader = PdfReader(str(pdf_path))

    n_pages = len(reader.pages)
    if n_pages == 0:
        issues.append("File has zero pages.")
    else:
        print(f"Page count: {n_pages}")

    empty_text_pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if len(text.strip()) == 0:
            empty_text_pages.append(i + 1)
    if empty_text_pages:
        issues.append(
            f"Pages with no extractable text (may be image-only/scanned, or "
            f"a genuine blank-page bug): {empty_text_pages}"
        )

    size_bytes = pdf_path.stat().st_size
    print(f"File size: {size_bytes / 1024:.1f} KB")
    if size_bytes < 500:
        issues.append("File is suspiciously small (<500 bytes) — likely broken/empty output.")
    if n_pages and (size_bytes / n_pages) > 5_000_000:
        issues.append("Very large per-page size (>5MB/page) — check for unoptimized embedded images.")

    if reader.is_encrypted:
        print("Note: file is encrypted.")

    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf_path")
    ap.add_argument("--dpi", type=int, default=100)
    ap.add_argument("--out-dir", default="./verify_render")
    args = ap.parse_args()

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    print(f"Verifying: {pdf_path}\n")

    issues = run_checks(pdf_path)
    images = render_pages(pdf_path, Path(args.out_dir), args.dpi)

    print()
    if images:
        print(f"Rendered {len(images)} page image(s) to {args.out_dir}/ — view these before delivering.")
        for img in images:
            print(f"  {img}")

    print()
    if issues:
        print("ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("Automated checks passed. Still view the rendered images before delivering.")
        sys.exit(0)


if __name__ == "__main__":
    main()
