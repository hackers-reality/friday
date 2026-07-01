"""
friday/skills/pptx/scripts/check_env.py

Verifies pptx skill dependencies and checks for PowerPoint COM availability
(higher-fidelity verify render + animation support) vs LibreOffice fallback.

Usage:
    python check_env.py
"""
import importlib
import shutil
import sys

REQUIRED_PACKAGES = ["pptx", "matplotlib", "PIL"]
PIP_NAME = {"pptx": "python-pptx", "PIL": "Pillow"}


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


def check_powerpoint_com():
    print("\n=== MS PowerPoint COM (optional) ===")
    try:
        import win32com.client
        ppt = win32com.client.DispatchEx("PowerPoint.Application")
        ppt.Quit()
        print("  PowerPoint COM available — enables accurate render + animations.")
        return True
    except Exception as e:
        print(f"  PowerPoint COM not available ({e}). Falling back to LibreOffice for verify render.")
        return False


def check_soffice():
    print("\n=== LibreOffice (fallback verify render) ===")
    found = shutil.which("soffice")
    print(f"  soffice {'OK (' + found + ')' if found else 'MISSING'}")
    poppler = shutil.which("pdftoppm")
    print(f"  pdftoppm {'OK (' + poppler + ')' if poppler else 'MISSING (Poppler not on PATH)'}")
    return bool(found) and bool(poppler)


if __name__ == "__main__":
    pkg_ok = check_packages()
    ppt_ok = check_powerpoint_com()
    soffice_ok = check_soffice()

    print()
    if pkg_ok and (ppt_ok or soffice_ok):
        print("Environment ready.")
        sys.exit(0)
    else:
        print("Fix missing items above. At least one render path (PowerPoint or LibreOffice) is required.")
        sys.exit(1)
