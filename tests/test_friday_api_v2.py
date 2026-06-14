"""Test FRIDAY UI API with new endpoints."""
import sys, os
sys.path.insert(0, '.')
os.chdir('E:/open-interpreter/friday/friday_ui/backend')

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

tests = [
    ('GET', '/api/health'),
    ('GET', '/api/system'),
    ('GET', '/api/services'),
    ('GET', '/api/agents'),
    ('GET', '/api/memory'),
    ('GET', '/api/codebase'),
    ('GET', '/api/workflows'),
    ('GET', '/api/plugins'),
    ('GET', '/api/security/stats'),
    ('GET', '/api/config'),
    ('GET', '/api/config/stats'),
    ('GET', '/api/logs'),
    ('GET', '/api/logs/stats'),
    ('GET', '/api/ratelimit/stats'),
]

passed = 0
failed = 0
for method, path in tests:
    r = client.get(path)
    ok = r.status_code == 200
    if ok:
        passed += 1
    else:
        failed += 1
    print(f'  {"OK" if ok else "FAIL"} {path} ({r.status_code})')

r = client.post('/api/chat', json={'message': 'hello'})
ok = r.status_code == 200 and 'response' in r.json()
if ok:
    passed += 1
else:
    failed += 1
print(f'  {"OK" if ok else "FAIL"} POST /api/chat')

r = client.post('/api/tools/call', json={'tool': 'bootstrap', 'action': 'status'})
ok = r.status_code == 200
if ok:
    passed += 1
else:
    failed += 1
print(f'  {"OK" if ok else "FAIL"} POST /api/tools/call')

r = client.post('/api/security/scan', json={'message': 'eval(x)'})
ok = r.status_code == 200
if ok:
    passed += 1
else:
    failed += 1
print(f'  {"OK" if ok else "FAIL"} POST /api/security/scan')

print(f'\nRESULTS: {passed} passed, {failed} failed')
