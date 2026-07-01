"""
friday/skills/docx/scripts/verify_docx.py

Post-generation sanity check for a .docx: renders to images for visual
inspection, and runs structural checks (empty doc, broken image refs,
paragraph count) before delivery.

Usage:
    python verify_docx.py output.docx [--dpi 100] [--out-dir ./verify_render]
"""
import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from docx import Document


def structural_checks(docx_path: Path):
    issues = []
    doc = Document(str(docx_path))

    n_paragraphs = len(doc.paragraphs)
    non_empty = sum(1 for p in doc.paragraphs if p.text.strip())
    print(f"Paragraphs: {n_paragraphs} total, {non_empty} non-empty")
    if non_empty == 0:
        issues.append("Document appears to have no visible text content.")

    n_tables = len(doc.tables)
    print(f"Tables: {n_tables}")
    for i, table in enumerate(doc.tables):
        widths = set()
        for row in table.rows:
            for cell in row.cells:
                if cell.width:
                    widths.add(cell.width)
        if len(widths) == 0:
            issues.append(f"Table {i+1}: no explicit cell widths set — likely misaligned columns.")

    # check image relationships resolve to actual embedded parts
    with zipfile.ZipFile(str(docx_path)) as z:
        names = set(z.namelist())
        media_files = [n for n in names if n.startswith("word/media/")]
        print(f"Embedded media files: {len(media_files)}")
        if "word/_rels/document.xml.rels" in names:
            rels_xml = z.read("word/_rels/document.xml.rels").decode("utf-8", errors="ignore")
            referenced_media = [m for m in media_files if Path(m).name in rels_xml]
            orphaned = set(media_files) - set(referenced_media)
            if orphaned:
                issues.append(f"Embedded media not referenced by any relationship (orphaned): {orphaned}")

    size_kb = docx_path.stat().st_size / 1024
    print(f"File size: {size_kb:.1f} KB")
    if size_kb < 5:
        issues.append("File is suspiciously small (<5KB) — likely near-empty output.")

    return issues


def render_pages(docx_path: Path, out_dir: Path, dpi: int):
    out_dir.mkdir(parents=True, exist_ok=True)
    if not shutil.which("soffice"):
        print("WARNING: soffice not found — skipping visual render. Run check_env.py.")
        return []
    subprocess.run(
        ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(docx_path)],
        check=True,
    )
    pdf_path = out_dir / (docx_path.stem + ".pdf")
    if not pdf_path.exists():
        print("WARNING: PDF conversion did not produce expected output file.")
        return []
    prefix = out_dir / "page"
    subprocess.run(["pdftoppm", "-jpeg", "-r", str(dpi), str(pdf_path), str(prefix)], check=True)
    return sorted(out_dir.glob("page-*.jpg"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("docx_path")
    ap.add_argument("--dpi", type=int, default=100)
    ap.add_argument("--out-dir", default="./verify_render")
    args = ap.parse_args()

    docx_path = Path(args.docx_path)
    if not docx_path.exists():
        print(f"File not found: {docx_path}")
        sys.exit(1)

    print(f"Verifying: {docx_path}\n")
    issues = structural_checks(docx_path)
    print()
    images = render_pages(docx_path, Path(args.out_dir), args.dpi)
    if images:
        print(f"Rendered {len(images)} page image(s) to {args.out_dir}/ — view before delivering.")
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
