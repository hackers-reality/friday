"""
friday/skills/xlsx/scripts/check_env.py

Verifies xlsx skill dependencies and checks whether MS Excel COM is
available (enables the more accurate xlwings recalculation path).

Usage:
    python check_env.py
"""
import importlib
import shutil
import sys

REQUIRED_PACKAGES = ["openpyxl", "pandas", "xlsxwriter"]
OPTIONAL_PACKAGES = ["xlwings", "win32com"]
PIP_NAME = {"win32com": "pywin32"}


def check(pkgs, label):
    print(f"=== {label} ===")
    ok = True
    for pkg in pkgs:
        try:
            importlib.import_module(pkg)
            print(f"  {pkg:<12} OK")
        except ImportError:
            print(f"  {pkg:<12} MISSING -> pip install {PIP_NAME.get(pkg, pkg)}")
            ok = False
    return ok


def check_excel_com():
    print("\n=== MS Excel COM (optional, enables accurate recalc + PivotTables) ===")
    try:
        import win32com.client
        excel = win32com.client.DispatchEx("Excel.Application")
        excel.Quit()
        print("  Excel COM available.")
        return True
    except Exception as e:
        print(f"  Excel COM not available ({e}). Will fall back to LibreOffice for recalculation.")
        return False


def check_soffice():
    print("\n=== LibreOffice (fallback recalc) ===")
    found = shutil.which("soffice")
    print(f"  soffice {'OK (' + found + ')' if found else 'MISSING'}")
    if not found:
        print("    -> https://www.libreoffice.org/download/download/, add program dir to PATH")
    return bool(found)


if __name__ == "__main__":
    req_ok = check(REQUIRED_PACKAGES, "Required packages")
    check(OPTIONAL_PACKAGES, "\nOptional packages (Excel COM path)")
    excel_ok = check_excel_com()
    soffice_ok = check_soffice()

    print()
    if req_ok and (excel_ok or soffice_ok):
        print("Environment ready — recalculation path available:", "Excel COM" if excel_ok else "LibreOffice")
        sys.exit(0)
    else:
        print("Missing required pieces — fix items above. At least one recalc path (Excel or LibreOffice) is needed.")
        sys.exit(1)
