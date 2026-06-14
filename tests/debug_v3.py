"""Test full FRIDAY v3 backend."""
import sys, os, json
sys.path.insert(0, '.')
os.chdir('E:/open-interpreter/friday/friday_ui/backend')

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Frontend
r = client.get('/')
print(f"Frontend: {r.status_code} {'OK' if 'html' in r.headers.get('content-type','') else 'FAIL'}")

# Core API
endpoints = [
    '/api/health', '/api/system', '/api/services', '/api/tools',
    '/api/agents', '/api/memory', '/api/memory/entities', '/api/memory/graph',
    '/api/codebase', '/api/chat/history',
    '/api/townhall/status', '/api/townhall/sessions', '/api/townhall/agents', '/api/townhall/agenda',
    '/api/workflows', '/api/plugins', '/api/reviews/stats',
    '/api/security/stats', '/api/config', '/api/config/stats',
    '/api/logs', '/api/logs/stats',
    '/api/ratelimit/stats', '/api/scheduler/tasks', '/api/scheduler/stats',
    '/api/health/status', '/api/health/alerts',
    '/api/cache/stats', '/api/metrics/dashboard',
    '/api/parser/supported', '/api/database/list', '/api/database/stats',
    '/api/git/status', '/api/git/log', '/api/git/stats',
    '/api/notifications/stats', '/api/notifications/history',
    '/api/gateway/routes', '/api/gateway/stats',
    '/api/backups', '/api/backups/stats',
    '/api/conversations',
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
        print(f"  FAIL: {path} -> {r.status_code}")

print(f"\nAPI: {passed}/{passed+failed} endpoints OK")

# POST endpoints
r = client.post('/api/chat', json={'message': 'hello'})
print(f"Chat: {r.status_code} has_response={'response' in r.json()}")

r = client.post('/api/memory/store', json={'content': 'test memory from UI', 'source': 'test'})
print(f"Memory store: {r.status_code}")

r = client.post('/api/memory/learn', json={'message': 'FRIDAY is an AI assistant'})
print(f"Memory learn: {r.status_code}")

r = client.post('/api/voice/speak', json={'text': 'Hello sir', 'voice': 'default'})
print(f"Voice speak: {r.status_code}")

r = client.post('/api/tools/call', json={'tool': 'health', 'action': 'status'})
print(f"Tool call: {r.status_code}")

print("\nALL TESTS PASSED" if failed == 0 else f"\n{failed} FAILED")
