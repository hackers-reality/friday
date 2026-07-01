"""
friday/skills/svg/scripts/check_env.py

Verifies svg skill dependencies (cairosvg for rendering, Pillow for image
post-processing).

Usage:
    python check_env.py
"""
import importlib
import sys

REQUIRED = ["cairosvg", "PIL"]
OPTIONAL = ["svgwrite"]
PIP_NAME = {"PIL": "Pillow"}


def check(pkgs, label):
    print(f"=== {label} ===")
    ok = True
    for pkg in pkgs:
        try:
            importlib.import_module(pkg)
            print(f"  {pkg:<10} OK")
        except ImportError:
            print(f"  {pkg:<10} MISSING -> pip install {PIP_NAME.get(pkg, pkg)}")
            ok = False
    return ok


if __name__ == "__main__":
    req_ok = check(REQUIRED, "Required")
    check(OPTIONAL, "\nOptional")
    print()
    if req_ok:
        print("Environment ready.")
        sys.exit(0)
    else:
        print("Fix missing required packages above.")
        sys.exit(1)
