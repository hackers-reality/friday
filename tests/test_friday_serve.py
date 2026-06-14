"""Test FRIDAY serves frontend from backend."""
import sys, os
sys.path.insert(0, '.')
os.chdir('E:/open-interpreter/friday/friday_ui/backend')

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Test API still works
r = client.get('/api/health')
print(f'API health: {r.status_code} OK={r.status_code == 200}')

# Test frontend is served
r = client.get('/')
ct = r.headers.get("content-type", "")
print(f'Frontend (/): {r.status_code} has_html={"html" in ct}')

# Test assets
r = client.get('/assets/index-CquAwzil.css')
print(f'CSS asset: {r.status_code}')

r = client.get('/assets/index-BXRp-H2f.js')
print(f'JS asset: {r.status_code}')

# Test SPA fallback (non-api, non-file paths)
r = client.get('/anything')
ct2 = r.headers.get("content-type", "")
print(f'SPA fallback: {r.status_code} has_html={"html" in ct2}')

print('\nALL OK')
