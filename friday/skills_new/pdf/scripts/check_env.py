"""
friday/skills/pdf/scripts/check_env.py

Verifies all binaries/libraries the PDF skill depends on are actually
available on this Windows machine, and prints exact fix instructions for
anything missing. Run this before trusting any PDF task to succeed.

Usage:
    python check_env.py
"""
import shutil
import sys
import importlib

REQUIRED_BINARIES = {
    "pdftoppm": "Poppler — download from https://github.com/oschwartz10612/poppler-windows/releases, extract, add <extracted>\\Library\\bin to PATH",
    "pdftotext": "Poppler (same package as pdftoppm above)",
    "pdfimages": "Poppler (same package as pdftoppm above)",
    "tesseract": "Tesseract-OCR — https://github.com/UB-Mannheim/tesseract/wiki, add install dir to PATH (default C:\\Program Files\\Tesseract-OCR)",
    "qpdf": "qpdf — https://github.com/qpdf/qpdf/releases, extract, add bin\\ folder to PATH",
}

REQUIRED_PACKAGES = [
    "reportlab", "pypdf", "pdfplumber", "matplotlib",
    "pytesseract", "pdf2image", "pikepdf", "fpdf", "fitz", "pandas",
]

PACKAGE_PIP_NAME = {"fitz": "pymupdf", "fpdf": "fpdf2"}


def check_binaries():
    print("=== Binaries (PATH) ===")
    all_ok = True
    for exe, fix in REQUIRED_BINARIES.items():
        found = shutil.which(exe)
        status = f"OK  ({found})" if found else "MISSING"
        print(f"  {exe:<12} {status}")
        if not found:
            print(f"    -> {fix}")
            all_ok = False
    return all_ok


def check_packages():
    print("\n=== Python packages ===")
    all_ok = True
    for pkg in REQUIRED_PACKAGES:
        try:
            importlib.import_module(pkg)
            print(f"  {pkg:<12} OK")
        except ImportError:
            pip_name = PACKAGE_PIP_NAME.get(pkg, pkg)
            print(f"  {pkg:<12} MISSING -> pip install {pip_name}")
            all_ok = False
    return all_ok


if __name__ == "__main__":
    bin_ok = check_binaries()
    pkg_ok = check_packages()
    print()
    if bin_ok and pkg_ok:
        print("All dependencies satisfied. PDF skill is ready.")
        sys.exit(0)
    else:
        print("Some dependencies are missing — fix the items above before running PDF tasks.")
        sys.exit(1)
