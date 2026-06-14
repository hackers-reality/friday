"""Test FRIDAY UI backend serves frontend correctly."""
import sys, os
sys.path.insert(0, '.')
os.chdir('E:/open-interpreter/friday/friday_ui/backend')

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Test frontend is served
r = client.get('/')
ct = r.headers.get("content-type", "")
print(f"GET /: status={r.status_code} content-type={ct}")
if r.status_code == 200 and "html" in ct:
    print("  -> Frontend HTML served OK")
    if "FRIDAY" in r.text or "root" in r.text:
        print("  -> Contains React root div")
else:
    print("  -> FAILED to serve frontend")

# Test static assets
r = client.get("/assets/index-CquAwzil.css")
print(f"GET CSS: status={r.status_code}")

r = client.get("/assets/index-BXRp-H2f.js")
print(f"GET JS: status={r.status_code}")

# Test SPA fallback
r = client.get("/dashboard")
ct2 = r.headers.get("content-type", "")
print(f"GET /dashboard: status={r.status_code} content-type={ct2}")

# Test API endpoints
api_tests = [
    '/api/health', '/api/system', '/api/services', '/api/agents',
    '/api/memory', '/api/codebase', '/api/tools', '/api/workflows',
    '/api/plugins', '/api/security/stats', '/api/config',
    '/api/logs', '/api/ratelimit/stats', '/api/scheduler/tasks',
    '/api/health/status', '/api/cache/stats', '/api/metrics/dashboard',
    '/api/notifications/stats', '/api/gateway/routes', '/api/backups',
]
passed = 0
failed = 0
for path in api_tests:
    r = client.get(path)
    ok = r.status_code == 200
    if ok: passed += 1
    else: failed += 1

print(f"\nAPI: {passed}/{passed+failed} endpoints OK")

# Test chat
r = client.post('/api/chat', json={'message': 'hello'})
print(f"POST /api/chat: status={r.status_code} has_response={'response' in r.json()}")

print("\nDONE")
