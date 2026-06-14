"""Test townhall endpoints."""
import sys, os
sys.path.insert(0, '.')
os.chdir('E:/open-interpreter/friday/friday_ui/backend')

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

for path in ['/api/townhall/status', '/api/townhall/sessions', '/api/townhall/agents', '/api/townhall/agenda']:
    r = client.get(path)
    print(f"{path}: status={r.status_code} keys={list(r.json().keys()) if r.status_code == 200 else 'FAIL'}")
