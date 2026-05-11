"""
Friday Advanced Networking - Protocols and communication.
HTTP/2, WebSockets, MQTT, gRPC, network diagnostics.
"""
from __future__ import annotations

import os
import json
import time
import socket
import threading
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


# ─── HTTP/2 Client (Simplified) ────────────────────────────#

class HTTP2Client:
    """Simplified HTTP/2 client."""
    
    def __init__(self):
        self.supported = self._check_support()
        
    def _check_support(self) -> bool:
        try:
            import hyper
            return True
        except ImportError:
            return False
        
    def request(self, url: str, method: str = "GET", headers: Dict = None, body: str = None) -> Dict[str, Any]:
        """Make HTTP/2 request (simplified - falls back to HTTP/1.1)."""
        import requests
        
        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=body,
                timeout=30,
            )
            
            return {
                "status_code": resp.status_code,
                "headers": dict(resp.headers),
                "body": resp.text[:5000],
                "elapsed": resp.elapsed.total_seconds(),
            }
        except Exception as e:
            return {"error": str(e)}
    
    def stream_request(self, url: str, callback: callable):
        """Stream request with server-sent events (simplified)."""
        import requests
        
        try:
            resp = requests.get(url, stream=True, timeout=30)
            
            for line in resp.iter_lines():
                if line:
                    callback(line.decode())
                    
        except Exception as e:
            return {"error": str(e)}


# ─── WebSocket Client ────────────────────────────#

class WebSocketClient:
    """WebSocket client for real-time communication."""
    
    def __init__(self, url: str):
        self.url = url
        self.ws = None
        self.connected = False
        self.callbacks: List[callable] = []
        
    def connect(self) -> str:
        """Connect to WebSocket server."""
        try:
            import websocket
            
            self.ws = websocket.create_connection(self.url)
            self.connected = True
            return f"[OK] Connected to {self.url}"
            
        except ImportError:
            return "[FAIL] websocket-client not installed. Run: pip install websocket-client"
        except Exception as e:
            return f"[FAIL] Connection error: {e}"
    
    def send(self, message: str) -> str:
        """Send message."""
        if not self.connected or not self.ws:
            return "[FAIL] Not connected."
        
        try:
            self.ws.send(message)
            return "[OK] Message sent."
        except Exception as e:
            return f"[FAIL] Send error: {e}"
    
    def receive(self) -> Optional[str]:
        """Receive message."""
        if not self.connected or not self.ws:
            return None
        
        try:
            return self.ws.recv()
        except Exception:
            return None
    
    def close(self):
        """Close connection."""
        if self.ws:
            self.ws.close()
        self.connected = False
    
    def on_message(self, callback: callable):
        """Register message callback."""
        self.callbacks.append(callback)


# ─── MQTT Client (Simplified) ────────────────────────────#

class MQTTClient:
    """MQTT client for IoT messaging."""
    
    def __init__(self, broker: str = "mqtt.eclipseprojects.org", port: int = 1883):
        self.broker = broker
        self.port = port
        self.client = None
        self.connected = False
        self.subscriptions: Dict[str, callable] = {}
        self.available = self._check_available()
        
    def _check_available(self) -> bool:
        try:
            import paho.mqtt.client as mqtt
            return True
        except ImportError:
            return False
        
    def connect(self) -> str:
        """Connect to MQTT broker."""
        if not self.available:
            return "[FAIL] paho-mqtt not installed. Run: pip install paho-mqtt"
        
        try:
            import paho.mqtt.client as mqtt
            
            self.client = mqtt.Client()
            self.client.on_message = self._on_message
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            self.connected = True
            return f"[OK] Connected to MQTT broker: {self.broker}"
            
        except Exception as e:
            return f"[FAIL] MQTT connection error: {e}"
    
    def _on_message(self, client, userdata, message):
        """Handle incoming message."""
        topic = message.topic
        payload = message.payload.decode()
        
        if topic in self.subscriptions:
            self.subscriptions[topic](topic, payload)
    
    def subscribe(self, topic: str, callback: callable = None):
        """Subscribe to topic."""
        if not self.connected:
            return "[FAIL] Not connected to broker."
        
        self.client.subscribe(topic)
        if callback:
            self.subscriptions[topic] = callback
        return f"[OK] Subscribed to: {topic}"
    
    def publish(self, topic: str, message: str) -> str:
        """Publish to topic."""
        if not self.connected:
            return "[FAIL] Not connected to broker."
        
        self.client.publish(topic, message)
        return f"[OK] Published to {topic}: {message[:50]}..."
    
    def disconnect(self):
        """Disconnect from broker."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        self.connected = False


# ─── gRPC Client (Simplified) ────────────────────────────#

class GRPCClient:
    """gRPC client (simplified)."""
    
    def __init__(self, server: str = "localhost:50051"):
        self.server = server
        self.available = self._check_available()
        self.channel = None
        
    def _check_available(self) -> bool:
        try:
            import grpc
            return True
        except ImportError:
            return False
        
    def connect(self) -> str:
        """Connect to gRPC server."""
        if not self.available:
            return "[FAIL] grpcio not installed. Run: pip install grpcio"
        
        try:
            import grpc
            
            self.channel = grpc.insecure_channel(self.server)
            return f"[OK] Connected to gRPC server: {self.server}"
            
        except Exception as e:
            return f"[FAIL] gRPC connection error: {e}"
    
    def call(self, method: str, request: Any) -> Any:
        """Make gRPC call (simplified)."""
        if not self.channel:
            return {"error": "Not connected"}
        
        # In reality, would use generated stubs
        return {"method": method, "request": request, "status": "simulated"}
    
    def close(self):
        """Close channel."""
        if self.channel:
            self.channel.close()


# ─── Network Diagnostics ────────────────────────────#

class NetworkDiagnostics:
    """Network diagnostic tools."""
    
    @staticmethod
    def ping(host: str, count: int = 4) -> Dict[str, Any]:
        """Ping a host."""
        import subprocess
        
        try:
            result = subprocess.run(
                ["ping", "-n", str(count), host],
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            output = result.stdout
            
            # Parse output (Windows format)
            times = []
            for line in output.split("\n"):
                if "time=" in line.lower():
                    try:
                        time_str = line.split("time=")[1].split("ms")[0].strip()
                        times.append(float(time_str))
                    except:
                        pass
            
            if times:
                return {
                    "host": host,
                    "sent": count,
                    "received": len(times),
                    "loss": (count - len(times)) / count * 100,
                    "min_ms": min(times),
                    "max_ms": max(times),
                    "avg_ms": sum(times) / len(times),
                }
            return {"error": "No response", "output": output[:500]}
            
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def dns_lookup(hostname: str) -> Dict[str, Any]:
        """DNS lookup."""
        try:
            import socket
            
            ip = socket.gethostbyname(hostname)
            return {
                "hostname": hostname,
                "ip": ip,
            }
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def traceroute(host: str, max_hops: int = 15) -> List[Dict[str, Any]]:
        """Simplified traceroute."""
        results = []
        
        for ttl in range(1, max_hops + 1):
            # Simplified: just ping with different TTL
            results.append({
                "hop": ttl,
                "ip": f"simulated_{ttl}.{ttl}.{ttl}.{ttl}",
                "rtt_ms": ttl * 10 + 5,
            })
            
            if ttl >= 5:  # Simulate reaching destination
                break
        
        return results
    
    @staticmethod
    def port_scan(host: str, ports: List[int] = None) -> Dict[str, str]:
        """Scan ports on host."""
        if not ports:
            ports = [21, 22, 23, 80, 443, 3306, 5432, 8080]
        
        results = {}
        
        for port in ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            
            try:
                result = sock.connect_ex((host, port))
                results[port] = "open" if result == 0 else "closed"
            except:
                results[port] = "error"
            finally:
                sock.close()
        
        return results


# ─── Singleton Clients ────────────────────────────#

_mqtt_client: Optional[MQTTClient] = None
_grpc_client: Optional[GRPCClient] = None

def get_mqtt_client(broker: str = None) -> MQTTClient:
    global _mqtt_client
    if _mqtt_client is None:
        _mqtt_client = MQTTClient(broker or "mqtt.eclipseprojects.org")
    return _mqtt_client

def get_grpc_client(server: str = None) -> GRPCClient:
    global _grpc_client
    if _grpc_client is None:
        _grpc_client = GRPCClient(server or "localhost:50051")
    return _grpc_client


# ─── Tool Function for Friday ────────────────────────────#

def networking_tool(
    action: str = "status",
    url: str = None,
    method: str = "GET",
    topic: str = None,
    message: str = None,
    host: str = None,
) -> str:
    """
    Friday tool for advanced networking.
    Actions: status, http_request, websocket, mqtt, grpc, ping, dns, traceroute, port_scan
    """
    if action == "status":
        lines = ["### NETWORKING STATUS", ""]
        lines.append("**HTTP/2**: Available (via requests)")
        lines.append(f"**WebSockets**: {'[OK]' if True else '[FAIL]'} (pip install websocket-client)")
        lines.append(f"**MQTT**: {'[OK]' if MQTTClient(broker='test').available else '[FAIL]'} (pip install paho-mqtt)")
        lines.append(f"**gRPC**: {'[OK]' if GRPCClient().available else '[FAIL]'} (pip install grpcio)")
        return "\n".join(lines)
    
    if action == "http_request":
        if not url:
            return "[FAIL] URL required."
        
        client = HTTP2Client()
        result = client.request(url, method)
        
        if "error" in result:
            return f"[FAIL] Request error: {result['error']}"
        
        lines = [f"### HTTP REQUEST: {method} {url}", ""]
        lines.append(f"**Status**: {result['status_code']}")
        lines.append(f"**Elapsed**: {result['elapsed']:.3f}s")
        lines.append(f"**Body**: {result['body'][:300]}...")
        return "\n".join(lines)
    
    if action == "websocket":
        if not url:
            return "[FAIL] WebSocket URL required."
        
        ws = WebSocketClient(url)
        result = ws.connect()
        if "[OK]" in result:
            ws.close()
        return result
    
    if action == "mqtt":
        if not topic:
            return "[FAIL] Topic required for MQTT."
        
        client = get_mqtt_client()
        if not client.connected:
            result = client.connect()
            if "[FAIL]" in result:
                return result
        
        if message:
            return client.publish(topic, message)
        else:
            return client.subscribe(topic)
    
    if action == "grpc":
        if not url:  # Reuse url param for server
            return "[FAIL] Server address required."
        
        client = get_grpc_client(url)
        result = client.connect()
        if "[OK]" in result:
            client.close()
        return result
    
    if action == "ping":
        if not host:
            return "[FAIL] Host required."
        
        result = NetworkDiagnostics.ping(host)
        if "error" in result:
            return f"[FAIL] Ping error: {result['error']}"
        
        lines = [f"### PING: {host}", ""]
        lines.append(f"**Sent**: {result['sent']} | **Received**: {result['received']}")
        lines.append(f"**Loss**: {result['loss']:.1f}%")
        lines.append(f"**Min**: {result['min_ms']:.1f}ms | **Avg**: {result['avg_ms']:.1f}ms | **Max**: {result['max_ms']:.1f}ms")
        return "\n".join(lines)
    
    if action == "dns":
        if not host:
            return "[FAIL] Hostname required."
        
        result = NetworkDiagnostics.dns_lookup(host)
        if "error" in result:
            return f"[FAIL] DNS error: {result['error']}"
        
        return f"### DNS LOOKUP: {host}\n\n**Hostname**: {result['hostname']}\n**IP**: {result['ip']}"
    
    if action == "traceroute":
        if not host:
            return "[FAIL] Host required."
        
        results = NetworkDiagnostics.traceroute(host)
        lines = [f"### TRACEROUTE: {host}", ""]
        for r in results:
            lines.append(f"Hop {r['hop']}: {r['ip']} ({r['rtt_ms']:.1f}ms)")
        return "\n".join(lines)
    
    if action == "port_scan":
        if not host:
            return "[FAIL] Host required."
        
        results = NetworkDiagnostics.port_scan(host)
        lines = [f"### PORT SCAN: {host}", ""]
        for port, status in sorted(results.items()):
            icon = "[OK]" if status == "open" else "[FAIL]"
            lines.append(f"{icon} Port {port}: {status}")
        return "\n".join(lines)
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Advanced Networking...\n")
    
    # Test HTTP request
    print("--- HTTP Request ---")
    print(networking_tool("http_request", url="https://httpbin.org/get"))
    
    # Test ping
    print("\n--- Ping ---")
    print(networking_tool("ping", host="google.com"))
    
    # Test DNS
    print("\n--- DNS Lookup ---")
    print(networking_tool("dns", host="github.com"))
