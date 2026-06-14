"""Test all FRIDAY UI API endpoints - final version."""
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
    '/api/parser/supported', '/api/database/list', '/api/database/stats',
    '/api/git/status', '/api/git/log', '/api/git/stats',
    '/api/notifications/stats', '/api/notifications/history',
    '/api/gateway/routes', '/api/gateway/stats',
    '/api/backups', '/api/backups/stats',
]

passed = 0
failed = 0
for path in endpoints:
    r = client.get(path)
    ok = r.status_code == 200
    if ok: passed += 1
    else: failed += 1
    print(f'  {"OK" if ok else "FAIL"} {path} ({r.status_code})')

posts = [
    ('/api/chat', {'message': 'hello'}),
    ('/api/tools/call', {'tool': 'bootstrap', 'action': 'status'}),
    ('/api/security/scan', {'message': 'eval(x)'}),
]
for path, body in posts:
    r = client.post(path, json=body)
    ok = r.status_code == 200
    if ok: passed += 1
    else: failed += 1
    print(f'  {"OK" if ok else "FAIL"} POST {path}')

print(f'\nRESULTS: {passed} passed, {failed} failed')
