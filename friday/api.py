"""
Friday API - REST API for Friday.
FastAPI web API providing REST endpoints (CLI-only mode).
"""
from __future__ import annotations

import os
import sys
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import base64


# ─── API Server ─────────────────────────────────────────#

class FridayAPI:
    """API server for Friday, serves REST endpoints only."""

    def __init__(self, host: str = "127.0.0.1", port: int = 7070):
        self.host = host
        self.port = port

    def start(self) -> dict:
        """Start FastAPI with REST endpoints only."""
        try:
            import uvicorn
            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware
        except ImportError as e:
            print(f"[FRIDAY] [ERROR] Dependencies for server missing: {e}", flush=True)
            raise e

        app = FastAPI(title="FRIDAY API", version="2.0.0")

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @app.get("/api/health")
        def health():
            return {"status": "ok", "version": "2.0.0"}

        @app.get("/")
        def root():
            return {"message": "FRIDAY API", "version": "2.0.0"}

        # Include REST API routes
        try:
            from api.dashboard_routes import router as api_router
            app.include_router(api_router)
        except Exception as e:
            print(f"[FRIDAY] [ERROR] Failed to load API routes: {e}", flush=True)
            import traceback
            traceback.print_exc()

        from friday._singletons import set_service_state
        set_service_state(
            "api_server",
            status="running",
            pid=os.getpid(),
            port=self.port,
            url=f"http://127.0.0.1:{self.port}",
        )

        print(f"\n  [FRIDAY] API server listening at http://localhost:{self.port}", flush=True)
        uvicorn.run(app, host=self.host, port=self.port)
        return {"success": True}


# ─── API Client ────────────────────────────#

class FridayAPIClient:
    """Client for Friday API."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session = __import__("requests", fromlist=["Session"]).Session()
        
    def request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an API request."""
        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.request(method, url, **kwargs)
            
            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "data": response.json() if response.content else {},
                "text": response.text,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """GET request."""
        return self.request("GET", endpoint, params=params)
    
    def post(self, endpoint: str, data: Dict = None, json_data: Dict = None) -> Dict[str, Any]:
        """POST request."""
        return self.request("POST", endpoint, data=data, json=json_data)
    
    def put(self, endpoint: str, data: Dict = None, json_data: Dict = None) -> Dict[str, Any]:
        """PUT request."""
        return self.request("PUT", endpoint, data=data, json=json_data)
    
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """DELETE request."""
        return self.request("DELETE", endpoint)
    
    def tool_call(self, tool: str, action: str, **params) -> Dict[str, Any]:
        """Call a Friday tool via API."""
        payload = {
            "tool": tool,
            "action": action,
            "params": params,
        }
        return self.post("/tool", json_data=payload)


# ─── API Endpoints ────────────────────────────#

class APIEndpoints:
    """Define API endpoints for Friday tools."""
    
    ENDPOINTS = {
        "network": "/api/network",
        "crypto": "/api/crypto",
        "web": "/api/web",
        "automation": "/api/automation",
        "database": "/api/database",
        "ai": "/api/ai",
        "tools": "/api/tools",
        "vision": "/api/vision",
        "security": "/api/security",
        "monitor": "/api/monitor",
        "scheduler": "/api/scheduler",
    }
    
    @staticmethod
    def get_endpoint(tool: str) -> Optional[str]:
        """Get endpoint for a tool."""
        return APIEndpoints.ENDPOINTS.get(tool)
    
    @staticmethod
    def list_endpoints() -> Dict[str, str]:
        """List all endpoints."""
        return APIEndpoints.ENDPOINTS.copy()


# ─── API Tool for Friday ────────────────────────────#

def api_tool(
    action: str = "status",
    tool: str = None,
    params: Dict = None,
) -> str:
    """
    Friday tool for API operations.
    Actions: status, start, stop, call, endpoints, client_request
    """
    params = params or {}
    
    if action == "status":
        lines = ["### API STATUS", ""]
        lines.append("**Available Servers**:")
        lines.append("  - FastAPI (recommended)")
        lines.append("  - Flask (fallback)")
        lines.append("")
        lines.append("**Default Endpoint**: http://127.0.0.1:8000")
        lines.append("")
        lines.append("**Available Routes**:")
        for tool, endpoint in APIEndpoints.ENDPOINTS.items():
            lines.append(f"  - {tool}: {endpoint}")
        return "\n".join(lines)
    
    if action == "start":
        host = params.get("host", "127.0.0.1")
        port = params.get("port", 8000)
        api = FridayAPI(host, port)
        result = api.start()
        if result.get("success"):
            return f"### API START\n\n[OK] Server started at http://{host}:{port}"
        else:
            return f"[FAIL] Start error: {result.get('error', 'Unknown')}"
    
    if action == "stop":
        # In a real implementation, would signal the server to stop
        return "### API STOP\n\n[OK] Server stop signal sent (not implemented)."
    
    if action == "call":
        if not tool:
            return "[FAIL] Tool name required."
        endpoint = APIEndpoints.get_endpoint(tool)
        if not endpoint:
            return f"[FAIL] Unknown tool: {tool}"
        return f"### API CALL\n\nTool: {tool}\nEndpoint: {endpoint}\nParams: {json.dumps(params, indent=2)}"
    
    if action == "endpoints":
        endpoints = APIEndpoints.list_endpoints()
        lines = ["### API ENDPOINTS", ""]
        for tool, endpoint in endpoints.items():
            lines.append(f"  - **{tool}**: `{endpoint}`")
        return "\n".join(lines)
    
    if action == "client_request":
        if not tool:
            return "[FAIL] Endpoint required."
        client = FridayAPIClient(params.get("base_url", "http://127.0.0.1:8000"))
        method = params.get("method", "GET")
        result = client.request(method, tool, json=params.get("data"))
        if result["success"]:
            return f"### API REQUEST\n\n**Status**: {result['status_code']}\n**Response**: {json.dumps(result['data'], indent=2)[:500]}"
        else:
            return f"[FAIL] Request error: {result.get('error', 'Unknown')}"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Friday API...\n")
    
    # Test status
    print("--- API Status ---")
    print(api_tool("status"))
    
    # Test endpoints
    print("\n--- API Endpoints ---")
    print(api_tool("endpoints"))
