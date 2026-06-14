"""Test FRIDAY UI backend endpoints."""
import sys
sys.path.insert(0, '.')
from friday.friday_ui.backend.main import app
from fastapi.testclient import TestClient

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

print(f'\nRESULTS: {passed} passed, {failed} failed')
