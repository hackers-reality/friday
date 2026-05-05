"""
Friday API - REST API for Friday.
FastAPI/Flask web API to access Friday capabilities remotely.
"""
from __future__ import annotations

import os
import sys
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import base64


# ─── API Server (Simplified) ────────────────────────────#

class FridayAPI:
    """Simple API server for Friday."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8000):
        self.host = host
        self.port = port
        self.routes: Dict[str, callable] = {}
        self.running = False
        self.fastapi_available = self._check_fastapi()
        
    def _check_fastapi(self) -> bool:
        try:
            import fastapi
            self.fastapi = fastapi
            return True
        except ImportError:
            return False
    
    def add_route(self, path: str, handler: callable, methods: List[str] = None):
        """Add an API route."""
        self.routes[path] = {
            "handler": handler,
            "methods": methods or ["GET"],
        }
    
    def start_fastapi(self):
        """Start FastAPI server."""
        if not self.fastapi_available:
            return {"success": False, "error": "FastAPI not available. Install: pip install fastapi uvicorn"}
        
        try:
            import uvicorn
            from fastapi import FastAPI
            
            app = FastAPI(title="Friday API", version="2.0.0")
            
            # Add routes
            for path, config in self.routes.items():
                # This is simplified - in reality, use proper FastAPI decorators
                pass
            
            # Add default routes
            @app.get("/")
            def root():
                return {"message": "Friday API", "version": "2.0.0"}
            
            @app.get("/status")
            def status():
                return {"status": "running", "host": self.host, "port": self.port}
            
            uvicorn.run(app, host=self.host, port=self.port)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def start_flask(self):
        """Start Flask server (fallback)."""
        try:
            from flask import Flask, request, jsonify
            
            app = Flask("Friday")
            
            @app.route("/")
            def root():
                return jsonify({"message": "Friday API", "version": "2.0.0"})
            
            @app.route("/status")
            def status():
                return jsonify({"status": "running", "host": self.host, "port": self.port})
            
            app.run(host=self.host, port=self.port)
            return {"success": True}
        except ImportError:
            return {"success": False, "error": "Flask not available. Install: pip install flask"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def start(self):
        """Start the API server."""
        if self.fastapi_available:
            return self.start_fastapi()
        else:
            return self.start_flask()


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
            return f"### API START\n\n✅ Server started at http://{host}:{port}"
        else:
            return f"❌ Start error: {result.get('error', 'Unknown')}"
    
    if action == "stop":
        # In a real implementation, would signal the server to stop
        return "### API STOP\n\n✅ Server stop signal sent (not implemented)."
    
    if action == "call":
        if not tool:
            return "❌ Tool name required."
        endpoint = APIEndpoints.get_endpoint(tool)
        if not endpoint:
            return f"❌ Unknown tool: {tool}"
        return f"### API CALL\n\nTool: {tool}\nEndpoint: {endpoint}\nParams: {json.dumps(params, indent=2)}"
    
    if action == "endpoints":
        endpoints = APIEndpoints.list_endpoints()
        lines = ["### API ENDPOINTS", ""]
        for tool, endpoint in endpoints.items():
            lines.append(f"  - **{tool}**: `{endpoint}`")
        return "\n".join(lines)
    
    if action == "client_request":
        if not tool:
            return "❌ Endpoint required."
        client = FridayAPIClient(params.get("base_url", "http://127.0.0.1:8000"))
        method = params.get("method", "GET")
        result = client.request(method, tool, json=params.get("data"))
        if result["success"]:
            return f"### API REQUEST\n\n**Status**: {result['status_code']}\n**Response**: {json.dumps(result['data'], indent=2)[:500]}"
        else:
            return f"❌ Request error: {result.get('error', 'Unknown')}"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Friday API...\n")
    
    # Test status
    print("--- API Status ---")
    print(api_tool("status"))
    
    # Test endpoints
    print("\n--- API Endpoints ---")
    print(api_tool("endpoints"))
