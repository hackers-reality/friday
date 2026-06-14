"""Test FRIDAY UI API with all new endpoints."""
import sys, os
sys.path.insert(0, '.')
os.chdir('E:/open-interpreter/friday/friday_ui/backend')

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

endpoints = [
    '/api/health', '/api/system', '/api/services', '/api/agents',
    '/api/memory', '/api/codebase', '/api/workflows', '/api/plugins',
    '/api/security/stats', '/api/config', '/api/config/stats',
    '/api/logs', '/api/logs/stats', '/api/ratelimit/stats',
    '/api/scheduler/tasks', '/api/scheduler/stats',
    '/api/health/status', '/api/health/alerts',
    '/api/cache/stats', '/api/metrics/dashboard',
]

passed = 0
failed = 0
for path in endpoints:
    r = client.get(path)
    ok = r.status_code == 200
    if ok:
        passed += 1
    else:
        failed += 1
    print(f'  {"OK" if ok else "FAIL"} {path} ({r.status_code})')

r = client.post('/api/chat', json={'message': 'hello'})
ok = r.status_code == 200
if ok: passed += 1
else: failed += 1
print(f'  {"OK" if ok else "FAIL"} POST /api/chat')

r = client.post('/api/tools/call', json={'tool': 'bootstrap', 'action': 'status'})
ok = r.status_code == 200
if ok: passed += 1
else: failed += 1
print(f'  {"OK" if ok else "FAIL"} POST /api/tools/call')

r = client.post('/api/security/scan', json={'message': 'eval(x)'})
ok = r.status_code == 200
if ok: passed += 1
else: failed += 1
print(f'  {"OK" if ok else "FAIL"} POST /api/security/scan')

print(f'\nRESULTS: {passed} passed, {failed} failed')
