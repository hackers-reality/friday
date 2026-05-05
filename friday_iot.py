"""
Friday IoT - Internet of Things integration.
MQTT, CoAP, sensors, actuators, smart home.
"""
from __future__ import annotations

import os
import sys
import json
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from pathlib import Path
import base64
import random


# ─── MQTT Client (Simplified) ────────────────────────────#

class MQTTClient:
    """MQTT client for IoT communication."""
    
    def __init__(self, broker: str = "mqtt.eclipseprojects.io", port: int = 1883):
        self.broker = broker
        self.port = port
        self.client = None
        self.connected = False
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.mqtt_available = self._check_mqtt()
        
    def _check_mqtt(self) -> bool:
        try:
            import paho.mqtt.client as mqtt
            self.mqtt = mqtt
            return True
        except ImportError:
            return False
    
    def connect(self, client_id: str = None) -> Dict[str, Any]:
        """Connect to MQTT broker."""
        if not self.mqtt_available:
            return {"success": False, "error": "paho-mqtt not available. Install: pip install paho-mqtt"}
        
        try:
            client_id = client_id or f"friday_iot_{random.randint(1000, 9999)}"
            self.client = self.mqtt.Client(client_id)
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            
            self.connected = True
            return {"success": True, "client_id": client_id}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for connection."""
        if rc == 0:
            print("✅ Connected to MQTT broker.")
        else:
            print(f"❌ Failed to connect: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Callback for messages."""
        topic = msg.topic
        payload = msg.payload.decode()
        
        if topic in self.subscriptions:
            for callback in self.subscriptions[topic]:
                try:
                    callback(topic, payload)
                except:
                    pass
    
    def publish(self, topic: str, message: str, qos: int = 0) -> Dict[str, Any]:
        """Publish message to topic."""
        if not self.connected or not self.client:
            return {"success": False, "error": "Not connected to broker."}
        
        try:
            result = self.client.publish(topic, message, qos=qos)
            return {"success": True, "mid": result.mid}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def subscribe(self, topic: str, callback: Callable = None) -> Dict[str, Any]:
        """Subscribe to topic."""
        if not self.connected or not self.client:
            return {"success": False, "error": "Not connected to broker."}
        
        try:
            self.client.subscribe(topic)
            
            if callback:
                if topic not in self.subscriptions:
                    self.subscriptions[topic] = []
                self.subscriptions[topic].append(callback)
            
            return {"success": True, "topic": topic}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def disconnect(self):
        """Disconnect from broker."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False


# ─── CoAP Client (Simplified) ────────────────────────────#

class CoAPClient:
    """CoAP client for IoT (simplified)."""
    
    def __init__(self):
        self.coap_available = self._check_coap()
        
    def _check_coap(self) -> bool:
        try:
            import aiocoap
            return True
        except ImportError:
            return False
    
    def get(self, url: str) -> Dict[str, Any]:
        """CoAP GET request (simplified)."""
        if not self.coap_available:
            return {"success": False, "error": "aiocoap not available."}
        
        # Simplified - in reality, use aiocoap
        return {"success": False, "error": "CoAP GET not fully implemented."}
    
    def post(self, url: str, payload: str) -> Dict[str, Any]:
        """CoAP POST request (simplified)."""
        if not self.coap_available:
            return {"success": False, "error": "aiocoap not available."}
        
        return {"success": False, "error": "CoAP POST not fully implemented."}


# ─── Sensor Simulator ────────────────────────────#

class SensorSimulator:
    """Simulate IoT sensors."""
    
    def __init__(self):
        self.sensors: Dict[str, Dict] = {}
        
    def add_sensor(self, name: str, sensor_type: str, unit: str):
        """Add a simulated sensor."""
        self.sensors[name] = {
            "type": sensor_type,
            "unit": unit,
            "value": None,
            "history": [],
            "last_update": None,
        }
        return {"success": True, "sensor": name}
    
    def read_sensor(self, name: str) -> Dict[str, Any]:
        """Read sensor value."""
        if name not in self.sensors:
            return {"success": False, "error": "Sensor not found."}
        
        sensor = self.sensors[name]
        
        # Simulate reading based on type
        if sensor["type"] == "temperature":
            value = random.uniform(20.0, 30.0)
        elif sensor["type"] == "humidity":
            value = random.uniform(40.0, 60.0)
        elif sensor["type"] == "pressure":
            value = random.uniform(1000, 1020)
        elif sensor["type"] == "light":
            value = random.uniform(0, 1000)
        else:
            value = random.uniform(0, 100)
        
        sensor["value"] = value
        sensor["last_update"] = datetime.now().isoformat()
        sensor["history"].append({
            "timestamp": sensor["last_update"],
            "value": value,
        })
        
        # Keep history manageable
        if len(sensor["history"]) > 100:
            sensor["history"] = sensor["history"][-100:]
        
        return {
            "success": True,
            "sensor": name,
            "value": value,
            "unit": sensor["unit"],
        }
    
    def get_history(self, name: str, limit: int = 10) -> Dict[str, Any]:
        """Get sensor history."""
        if name not in self.sensors:
            return {"success": False, "error": "Sensor not found."}
        
        history = self.sensors[name]["history"][-limit:]
        return {
            "success": True,
            "sensor": name,
            "history": history,
            "count": len(history),
        }


# ─── Smart Home (Simplified) ────────────────────────────#

class SmartHome:
    """Smart home device control (simplified)."""
    
    DEVICE_TYPES = ["light", "thermostat", "lock", "camera", "plug"]
    
    def __init__(self):
        self.devices: Dict[str, Dict] = {}
        
    def add_device(self, name: str, device_type: str, location: str = "living_room"):
        """Add a smart home device."""
        if device_type not in self.DEVICE_TYPES:
            return {"success": False, "error": f"Unknown device type: {device_type}"}
        
        self.devices[name] = {
            "type": device_type,
            "location": location,
            "state": "off" if device_type in ("light", "plug") else "unknown",
            "properties": {},
        }
        
        return {"success": True, "device": name}
    
    def control_device(self, name: str, action: str, **kwargs) -> Dict[str, Any]:
        """Control a device."""
        if name not in self.devices:
            return {"success": False, "error": "Device not found."}
        
        device = self.devices[name]
        
        if action == "on":
            device["state"] = "on"
        elif action == "off":
            device["state"] = "off"
        elif action == "toggle":
            device["state"] = "off" if device["state"] == "on" else "on"
        elif action == "set":
            device["properties"].update(kwargs)
        
        return {"success": True, "device": name, "state": device["state"]}
    
    def get_device_status(self, name: str) -> Dict[str, Any]:
        """Get device status."""
        if name not in self.devices:
            return {"success": False, "error": "Device not found."}
        
        device = self.devices[name]
        return {
            "success": True,
            "device": name,
            "type": device["type"],
            "location": device["location"],
            "state": device["state"],
            "properties": device["properties"],
        }
    
    def list_devices(self) -> List[Dict]:
        """List all devices."""
        return [
            {
                "name": name,
                "type": device["type"],
                "location": device["location"],
                "state": device["state"],
            }
            for name, device in self.devices.items()
        ]


# ─── IoT Tool for Friday ────────────────────────────#

def iot_tool(
    action: str = "status",
    target: str = None,
    params: Dict = None,
) -> str:
    """
    Friday tool for IoT operations.
    Actions: status, mqtt_connect, mqtt_publish, mqtt_subscribe,
            sensor_add, sensor_read, smart_add, smart_control, smart_list
    """
    params = params or {}
    
    if action == "status":
        lines = ["### IOT STATUS", ""]
        lines.append("**Available Protocols**:")
        lines.append("  - MQTT (paho-mqtt)")
        lines.append("  - CoAP (aiocoap)")
        lines.append("")
        lines.append("**Simulators**:")
        lines.append("  - Sensor simulator")
        lines.append("  - Smart home devices")
        return "\n".join(lines)
    
    if action == "mqtt_connect":
        broker = params.get("broker", "mqtt.eclipseprojects.io")
        port = params.get("port", 1883)
        mqtt = MQTTClient(broker, port)
        result = mqtt.connect()
        if result["success"]:
            return f"### MQTT CONNECT\n\n✅ Connected to {broker}:{port}\nClient ID: {result['client_id']}"
        else:
            return f"❌ MQTT error: {result.get('error', 'Unknown')}"
    
    if action == "mqtt_publish":
        if not target:
            return "❌ Topic required."
        message = params.get("message", "Hello from Friday!")
        mqtt = MQTTClient()
        mqtt.connect()
        result = mqtt.publish(target, message)
        if result["success"]:
            return f"### MQTT PUBLISH\n\n✅ Published to {target}: {message[:50]}..."
        else:
            return f"❌ MQTT error: {result.get('error', 'Unknown')}"
    
    if action == "mqtt_subscribe":
        if not target:
            return "❌ Topic required."
        mqtt = MQTTClient()
        mqtt.connect()
        result = mqtt.subscribe(target)
        if result["success"]:
            return f"### MQTT SUBSCRIBE\n\n✅ Subscribed to {target}"
        else:
            return f"❌ MQTT error: {result.get('error', 'Unknown')}"
    
    if action == "sensor_add":
        if not target:
            return "❌ Sensor name required."
        sensor_type = params.get("type", "temperature")
        unit = params.get("unit", "°C")
        simulator = SensorSimulator()
        result = simulator.add_sensor(target, sensor_type, unit)
        if result["success"]:
            return f"### SENSOR ADD\n\n✅ Added {sensor_type} sensor: {target}"
        else:
            return f"❌ Sensor error: {result.get('error', 'Unknown')}"
    
    if action == "sensor_read":
        if not target:
            return "❌ Sensor name required."
        simulator = SensorSimulator()
        result = simulator.read_sensor(target)
        if result["success"]:
            return f"### SENSOR READ\n\n**{target}**: {result['value']:.2f} {result['unit']}"
        else:
            return f"❌ Sensor error: {result.get('error', 'Unknown')}"
    
    if action == "smart_add":
        if not target:
            return "❌ Device name required."
        device_type = params.get("type", "light")
        location = params.get("location", "living_room")
        smart = SmartHome()
        result = smart.add_device(target, device_type, location)
        if result["success"]:
            return f"### SMART HOME ADD\n\n✅ Added {device_type}: {target} in {location}"
        else:
            return f"❌ Smart home error: {result.get('error', 'Unknown')}"
    
    if action == "smart_control":
        if not target:
            return "❌ Device name required."
        action_type = params.get("action", "toggle")
        smart = SmartHome()
        result = smart.control_device(target, action_type, **{k: v for k, v in params.items() if k not in ("action",)})
        if result["success"]:
            return f"### SMART HOME CONTROL\n\n✅ {target} -> {result['state']}"
        else:
            return f"❌ Smart home error: {result.get('error', 'Unknown')}"
    
    if action == "smart_list":
        smart = SmartHome()
        devices = smart.list_devices()
        lines = [f"### SMART HOME DEVICES ({len(devices)})", ""]
        for device in devices:
            lines.append(f"  - {device['name']}: {device['type']} ({device['state']}) @ {device['location']}")
        return "\n".join(lines)
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Friday IoT...\n")
    
    # Test MQTT (will fail without broker)
    print("--- MQTT (demo) ---")
    print(iot_tool("mqtt_connect", params={"broker": "test.mosquitto.org"}))
    
    # Test sensor
    print("\n--- Sensor Simulator ---")
    print(iot_tool("sensor_add", target="temp1", params={"type": "temperature", "unit": "°C"}))
    print(iot_tool("sensor_read", target="temp1"))
