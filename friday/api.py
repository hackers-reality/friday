"""
Friday API - REST API for Friday.
FastAPI web API serving the Vite+React dashboard and REST endpoints.
"""
from __future__ import annotations

import os
import sys
import json
import webbrowser
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import base64

DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "dashboard" / "dist"


# ─── API Server ─────────────────────────────────────────#

class FridayAPI:
    """API server for Friday, serves React dashboard + REST API."""

    def __init__(self, host: str = "0.0.0.0", port: int = 7070):
        self.host = host
        self.port = port

    def start(self) -> dict:
        """Start FastAPI with static file serving and CORS."""
        try:
            import uvicorn
            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware
            from fastapi.staticfiles import StaticFiles
        except ImportError:
            return {"success": False, "error": "fastapi/uvicorn not installed"}

        app = FastAPI(title="FRIDAY", version="2.0.0")

        # CORS for dev server
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Include dashboard API routes
        try:
            from api.dashboard_routes import router as dashboard_router
            app.include_router(dashboard_router)
        except Exception:
            pass

        # Serve Vite build as static files
        if DASHBOARD_DIR.exists():
            app.mount("/", StaticFiles(directory=str(DASHBOARD_DIR), html=True), name="dashboard")
        else:
            @app.get("/")
            def root():
                return {
                    "message": "FRIDAY API",
                    "version": "2.0.0",
                    "dashboard": "Run `cd dashboard && npm run build` to build the frontend",
                }

        print(f"\n  🛸  F·R·I·D·A·Y → http://localhost:{self.port}\n")
        webbrowser.open(f"http://localhost:{self.port}")
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
