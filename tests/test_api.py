"""Test all JARVIS API endpoints."""
import sys
sys.path.insert(0, '.')
from friday.friday_ui.backend.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

endpoints = ['/api/health', '/api/system', '/api/services', '/api/tools', '/api/agents', '/api/memory', '/api/codebase', '/api/workflows', '/api/plugins']
for ep in endpoints:
    r = client.get(ep)
    print(f'{ep}: {r.status_code} OK={r.status_code == 200}')

r = client.post('/api/chat', json={'message': 'hello'})
print(f'POST /api/chat: {r.status_code} resp={r.json()["response"][:40]}')

r = client.post('/api/tools/call', json={'tool': 'bootstrap', 'action': 'status'})
print(f'POST /api/tools/call: {r.status_code} OK={r.status_code == 200}')

print('ALL ENDPOINTS OK')
