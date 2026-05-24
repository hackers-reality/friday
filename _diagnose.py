"""Diagnostic: test all Friday imports including fastapi path."""
import sys, traceback

def test(label, do_import):
    try:
        do_import()
        print(f"[OK] {label}")
        return True
    except Exception as e:
        print(f"[FAIL] {label}: {e}")
        traceback.print_exc()
        return False

print(f"Python: {sys.version}")
print(f"Executable: {sys.executable}")
print()

# 1. Direct fastapi import
test("import fastapi", lambda: __import__("fastapi"))
test("from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query",
     lambda: __import__("fastapi").__import__("fastapi.responses"))

# 2. Try the exact brain_ws_server import chain
test("fastapi.responses", lambda: __import__("fastapi.responses"))
test("jwt", lambda: __import__("jwt"))
test("friday.orchestration_config", lambda: __import__("friday.orchestration_config"))
test("friday.sidecar.device_registry", lambda: __import__("friday.sidecar.device_registry"))

# 3. The full sidecar package
test("friday.sidecar", lambda: __import__("friday.sidecar"))

print("\n=== DIAGNOSTIC COMPLETE ===")
