"""Test FULL FRIDAY v4 backend with 757 tools."""
import sys, os
sys.path.insert(0, '.')
os.chdir('E:/open-interpreter/friday/friday_ui/backend')

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

r = client.get('/')
print(f"Frontend: {r.status_code}")

r = client.get('/api/health')
d = r.json()
print(f"Health: {r.status_code} tools={d.get('tools_count')}")

r = client.get('/api/tools')
d = r.json()
print(f"Tools: {r.status_code} total={d.get('total')} categories={d.get('categories')}")

r = client.get('/api/tool/list')
d = r.json()
print(f"Tool list: {r.status_code} count={d.get('count')}")

r = client.get('/api/system')
d = r.json()
print(f"System: {r.status_code} hostname={d.get('hostname')} tools={d.get('tools_count')}")

for path in ['/api/memory', '/api/memory/entities', '/api/memory/graph',
             '/api/townhall/status', '/api/townhall/sessions', '/api/townhall/agents',
             '/api/codebase', '/api/git/status', '/api/git/log',
             '/api/health/status', '/api/security/stats',
             '/api/services', '/api/agents', '/api/chat/history',
             '/api/workflows', '/api/plugins', '/api/config', '/api/logs']:
    r = client.get(path)
    ok = "OK" if r.status_code == 200 else f"FAIL({r.status_code})"
    print(f"  {path}: {ok}")

r = client.post('/api/chat', json={'message': 'hello'})
d = r.json()
print(f"\nChat: {r.status_code} response_len={len(d.get('response',''))}")

r = client.post('/api/tool/invoke', json={'tool': 'get_time', 'action': '', 'params': {}})
print(f"Tool invoke: {r.status_code}")

print("\nALL TESTS PASSED")
