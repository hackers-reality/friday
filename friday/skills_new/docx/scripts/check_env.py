"""
friday/skills/docx/scripts/check_env.py

Verifies docx skill dependencies: Python packages, pandoc, LibreOffice, and
(optionally) MS Word COM availability for higher-fidelity PDF conversion.

Usage:
    python check_env.py
"""
import importlib
import shutil
import sys

REQUIRED_PACKAGES = ["docx", "docxtpl", "docx2pdf", "pandas", "PIL"]
PIP_NAME = {"docx": "python-docx", "PIL": "Pillow"}

REQUIRED_BINARIES = {
    "pandoc": "https://pandoc.org/installing.html (Windows installer available)",
    "soffice": "LibreOffice — https://www.libreoffice.org/download/download/, add "
               "'C:\\Program Files\\LibreOffice\\program' to PATH",
}


def check_packages():
    print("=== Python packages ===")
    ok = True
    for pkg in REQUIRED_PACKAGES:
        try:
            importlib.import_module(pkg)
            print(f"  {pkg:<12} OK")
        except ImportError:
            print(f"  {pkg:<12} MISSING -> pip install {PIP_NAME.get(pkg, pkg)}")
            ok = False
    return ok


def check_binaries():
    print("\n=== Binaries ===")
    ok = True
    for exe, fix in REQUIRED_BINARIES.items():
        found = shutil.which(exe)
        print(f"  {exe:<10} {'OK (' + found + ')' if found else 'MISSING'}")
        if not found:
            print(f"    -> {fix}")
            ok = False
    return ok


def check_word_com():
    print("\n=== MS Word COM (optional, higher-fidelity PDF conversion) ===")
    try:
        import winreg
        winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application")
        print("  Word.Application registered — docx2pdf COM conversion available.")
        return True
    except Exception:
        print("  Word not detected — docx2pdf will fall back to LibreOffice, or fail. "
              "Not required, but improves render fidelity if present.")
        return False


if __name__ == "__main__":
    pkg_ok = check_packages()
    bin_ok = check_binaries()
    check_word_com()
    print()
    if pkg_ok and bin_ok:
        print("Core dependencies satisfied.")
        sys.exit(0)
    else:
        print("Fix missing items above before running docx tasks.")
        sys.exit(1)
