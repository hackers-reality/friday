"""
friday/skills/pdf/scripts/redact.py

Performs TRUE redaction (removes underlying content, not just a visual
overlay) using pymupdf's redaction annotations. Do not use the black-box
overlay trick from a Canvas/merge_page approach — that leaves the original
text extractable.

Usage:
    python redact.py input.pdf output.pdf "text to redact" "another phrase"
"""
import sys

import fitz  # pymupdf


def redact(input_path: str, output_path: str, search_terms: list[str]):
    doc = fitz.open(input_path)
    total_hits = 0

    for page in doc:
        for term in search_terms:
            areas = page.search_for(term)
            for rect in areas:
                page.add_redact_annot(rect, fill=(0, 0, 0))
                total_hits += 1
        page.apply_redactions()  # actually strips content, not just paints over it

    doc.save(output_path)
    print(f"Redacted {total_hits} occurrence(s) across {len(doc)} page(s) -> {output_path}")

    if total_hits == 0:
        print("WARNING: zero matches found — check spelling/case of search terms, "
              "or the text may be inside an image (needs OCR-based redaction instead).")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    redact(sys.argv[1], sys.argv[2], sys.argv[3:])
