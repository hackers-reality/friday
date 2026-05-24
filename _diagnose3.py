"""Diagnostic v3: simulate exactly what friday.py does."""
import sys, os, traceback
os.environ.setdefault("PYTHONUTF8", "1")

print(f"Python: {sys.version}")
print(f"Executable: {sys.executor}")
print()

# Step 1: Import live module (same as friday.py line 101)
try:
    import asyncio
    from friday.live import friday_live_engine
    print("[OK] from friday.live import friday_live_engine")
except Exception as e:
    print(f"[FAIL] import friday_live_engine: {type(e).__name__}: {e}")
    traceback.print_exc()
    sys.exit(1)

# If we got here, the import succeeded. Now try actually calling it.
# But we can't really run it in a script - it's async and starts hardware.
# Let's at least verify the function object exists.
print(f"[OK] friday_live_engine is a {type(friday_live_engine)}")
print()

# Check if there's a subprocess/importlib trick that could produce "No module named 'fastapi'"
# Search for any code path that mentions fastapi
import ast
with open("friday/live.py") as f:
    source = f.read()
tree = ast.parse(source)
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and "import" in str(node.func.id).lower():
        pass  # skip

# Check the module loading loop target modules
from friday.live import _build_tools
tools = _build_tools()
print(f"[OK] _build_tools() returned {len(tools)} declarations")

print("\n=== Import chain verified ===")
print("The only remaining possibility: the friday.cmd script itself")
Import-Module
