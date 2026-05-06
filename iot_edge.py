"""
Friday IoT/Edge Computing - Internet of Things and edge processing.
MQTT, sensor networks, edge AI inference.
"""
from __future__ import annotations

import json
import time
import random
import math
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field


# ─── IoT Device ───────────────────────────#

@dataclass
class IoTDevice:
    """Represents an IoT device."""
    device_id: str
    device_type: str  # sensor, actuator, gateway
    location: str
    capabilities: List[str] = field(default_factory=list)
    state: Dict[str, Any] = field(default_factory=dict)
    online: bool = True
    last_seen: float = field(default_factory=lambda: time.time())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "location": self.location,
            "capabilities": self.capabilities,
            "state": self.state,
            "online": self.online,
            "last_seen": self.last_seen,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IoTDevice':
        device = cls(
            data["device_id"],
            data["device_type"],
            data["location"],
            data.get("capabilities", []),
            data.get("state", {}),
        )
        device.online = data.get("online", True)
        device.last_seen = data.get("last_seen", time.time())
        return device


# ─── Sensor ───────────────────────────#

class Sensor(IoTDevice):
    """IoT sensor device."""
    
    def __init__(self, device_id: str, sensor_type: str, location: str):
        capabilities = [f"sense_{sensor_type}", "report"]
        super().__init__(device_id, "sensor", location, capabilities)
        self.sensor_type = sensor_type
        self.unit = self._get_unit()
        self.min_value = 0.0
        self.max_value = 100.0
        self.frequency = 1.0  # Hz
        
    def _get_unit(self) -> str:
        units = {
            "temperature": "°C",
            "humidity": "%",
            "pressure": "hPa",
            "light": "lux",
            "motion": "bool",
            "proximity": "cm",
            "noise": "dB",
        }
        return units.get(self.sensor_type, "units")
    
    def read_value(self) -> float:
        """Simulate sensor reading."""
        if not self.online:
            return None
        
        # Simulate realistic values
        if self.sensor_type == "temperature":
            return 20.0 + random.uniform(-5, 10)
        elif self.sensor_type == "humidity":
            return 50.0 + random.uniform(-20, 30)
        elif self.sensor_type == "motion":
            return 1 if random.random() < 0.1 else 0
        else:
            return random.uniform(self.min_value, self.max_value)
    
    def report(self) -> Dict[str, Any]:
        """Generate sensor report."""
        value = self.read_value()
        self.state["last_value"] = value
        self.state["last_report"] = datetime.now().isoformat()
        self.last_seen = time.time()
        
        return {
            "device_id": self.device_id,
            "sensor_type": self.sensor_type,
            "value": value,
            "unit": self.unit,
            "location": self.location,
            "timestamp": self.last_seen,
        }


# ─── Actuator ───────────────────────────#

class Actuator(IoTDevice):
    """IoT actuator device."""
    
    def __init__(self, device_id: str, actuator_type: str, location: str):
        capabilities = [f"actuate_{actuator_type}", "control"]
        super().__init__(device_id, "actuator", location, capabilities)
        self.actuator_type = actuator_type
        self.state["status"] = "off"
        
    def turn_on(self) -> str:
        if not self.online:
            return f"❌ {self.device_id} is offline"
        self.state["status"] = "on"
        self.last_seen = time.time()
        return f"✅ {self.device_id} turned ON"
    
    def turn_off(self) -> str:
        if not self.online:
            return f"❌ {self.device_id} is offline"
        self.state["status"] = "off"
        self.last_seen = time.time()
        return f"✅ {self.device_id} turned OFF"
    
    def set_value(self, value: float) -> str:
        if not self.online:
            return f"❌ {self.device_id} is offline"
        self.state["value"] = value
        self.last_seen = time.time()
        return f"✅ {self.device_id} set to {value}"


# ─── Edge Gateway ───────────────────────────#

class EdgeGateway(IoTDevice):
    """Edge computing gateway."""
    
    def __init__(self, device_id: str, location: str):
        capabilities = ["compute", "storage", "network", "edge_inference"]
        super().__init__(device_id, "gateway", location, capabilities)
        self.connected_devices: List[str] = []
        self.edge_models: Dict[str, Any] = {}
        
    def connect_device(self, device_id: str) -> str:
        if device_id not in self.connected_devices:
            self.connected_devices.append(device_id)
            return f"✅ Device {device_id} connected to gateway"
        return f"Device {device_id} already connected"
    
    def disconnect_device(self, device_id: str) -> str:
        if device_id in self.connected_devices:
            self.connected_devices.remove(device_id)
            return f"✅ Device {device_id} disconnected"
        return f"❌ Device {device_id} not connected"
    
    def run_edge_inference(self, model_name: str, input_data: Any) -> Any:
        """Run AI inference at the edge."""
        if model_name not in self.edge_models:
            # Simulate loading model
            self.edge_models[model_name] = {"type": "neural_net", "size_mb": 10}
        
        # Simulate inference
        time.sleep(0.1)  # Simulate processing time
        
        if "anomaly" in model_name:
            return {"anomaly_detected": random.random() > 0.8, "confidence": random.uniform(0.7, 0.99)}
        elif "predict" in model_name:
            return {"prediction": random.uniform(0, 100), "confidence": random.uniform(0.8, 0.99)}
        
        return {"result": "ok", "processing_time_ms": random.randint(10, 100)}


# ─── IoT Network ───────────────────────────#

class IoTNetwork:
    """Manages a network of IoT devices."""
    
    def __init__(self, network_id: str = "default"):
        self.network_id = network_id
        self.devices: Dict[str, IoTDevice] = {}
        self.gateways: Dict[str, EdgeGateway] = {}
        self.sensor_data: List[Dict[str, Any]] = []
        
    def add_device(self, device: IoTDevice) -> bool:
        if device.device_id in self.devices:
            return False
        self.devices[device.device_id] = device
        return True
    
    def remove_device(self, device_id: str) -> bool:
        if device_id not in self.devices:
            return False
        del self.devices[device_id]
        return True
    
    def get_device(self, device_id: str) -> Optional[IoTDevice]:
        return self.devices.get(device_id)
    
    def poll_sensors(self) -> List[Dict[str, Any]]:
        """Poll all sensors and collect data."""
        readings = []
        for device in self.devices.values():
            if isinstance(device, Sensor) and device.online:
                report = device.report()
                readings.append(report)
                self.sensor_data.append(report)
                
                # Keep only last 1000 readings
                if len(self.sensor_data) > 1000:
                    self.sensor_data = self.sensor_data[-1000:]
        
        return readings
    
    def get_aggregated_data(self, sensor_type: str = None) -> Dict[str, Any]:
        """Aggregate sensor data."""
        filtered = self.sensor_data
        if sensor_type:
            filtered = [d for d in self.sensor_data if d.get("sensor_type") == sensor_type]
        
        if not filtered:
            return {"count": 0}
        
        values = [d["value"] for d in filtered if isinstance(d.get("value"), (int, float))]
        
        if not values:
            return {"count": len(filtered)}
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1],
        }
    
    def check_anomalies(self, threshold_std: float = 2.0) -> List[Dict[str, Any]]:
        """Detect anomalies in sensor data."""
        anomalies = []
        
        # Group by sensor
        by_sensor: Dict[str, List[float]] = {}
        for reading in self.sensor_data[-100:]:  # Last 100 readings
            sid = reading.get("device_id")
            val = reading.get("value")
            if isinstance(val, (int, float)):
                if sid not in by_sensor:
                    by_sensor[sid] = []
                by_sensor[sid].append(val)
        
        # Check for anomalies
        for sid, values in by_sensor.items():
            if len(values) < 3:
                continue
            
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            std = math.sqrt(variance)
            
            latest = values[-1]
            if abs(latest - mean) > threshold_std * std:
                anomalies.append({
                    "device_id": sid,
                    "value": latest,
                    "mean": mean,
                    "std": std,
                    "deviation": abs(latest - mean) / std if std > 0 else 0,
                })
        
        return anomalies
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "network_id": self.network_id,
            "devices": {k: v.to_dict() for k, v in self.devices.items()},
            "gateways": {k: v.to_dict() for k, v in self.gateways.items()},
            "sensor_data_count": len(self.sensor_data),
        }
    
    def save(self, path: str):
        data = self.to_dict()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load(cls, path: str) -> 'IoTNetwork':
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        network = cls(data["network_id"])
        
        for did, ddata in data.get("devices", {}).items():
            device_type = ddata.get("device_type", "sensor")
            if device_type == "sensor":
                dev = Sensor(did, ddata.get("sensor_type", "generic"), ddata.get("location", ""))
            elif device_type == "actuator":
                dev = Actuator(did, ddata.get("actuator_type", "generic"), ddata.get("location", ""))
            else:
                dev = IoTDevice(did, device_type, ddata.get("location", ""))
            
            dev.__dict__.update(ddata)
            network.devices[did] = dev
        
        return network


# ─── Singleton Network ───────────────────────────#

_networks: Dict[str, IoTNetwork] = {}

def get_iot_network(network_id: str = "default") -> IoTNetwork:
    global _networks
    if network_id not in _networks:
        _networks[network_id] = IoTNetwork(network_id)
    return _networks[network_id]


# ─── Tool Function for Friday ───────────────────────────#

def iot_tool(
    action: str = "status",
    device_id: str = None,
    device_type: str = None,
    location: str = None,
    value: float = None,
) -> str:
    """
    Friday tool for IoT/Edge operations.
    Actions: status, add_device, remove_device, poll, aggregate, anomalies, edge_inference
    """
    network = get_iot_network()
    
    if action == "status":
        lines = [f"### IOT NETWORK: {network.network_id}", ""]
        lines.append(f"**Devices**: {len(network.devices)}")
        lines.append(f"**Gateways**: {len(network.gateways)}")
        lines.append(f"**Data Points**: {len(network.sensor_data)}")
        lines.append("")
        lines.append("**Devices**:")
        for did, dev in network.devices.items():
            status = "🟢" if dev.online else "🔴"
            lines.append(f"  {status} {did} ({dev.device_type})")
        return "\n".join(lines)
    
    if action == "add_device":
        if not device_id or not device_type or not location:
            return "❌ device_id, device_type, and location required."
        
        if device_type == "sensor":
            sensor_type = device_id.split("_")[0] if "_" in device_id else "generic"
            device = Sensor(device_id, sensor_type, location)
        elif device_type == "actuator":
            device = Actuator(device_id, device_id.split("_")[0], location)
        else:
            device = IoTDevice(device_id, device_type, location)
        
        if network.add_device(device):
            return f"✅ Added device: {device_id}"
        return f"❌ Device already exists: {device_id}"
    
    if action == "remove_device":
        if not device_id:
            return "❌ device_id required."
        if network.remove_device(device_id):
            return f"✅ Removed device: {device_id}"
        return f"❌ Device not found: {device_id}"
    
    if action == "poll":
        readings = network.poll_sensors()
        if not readings:
            return "No sensor readings available."
        
        lines = [f"### SENSOR READINGS ({len(readings)})", ""]
        for r in readings[:10]:
            lines.append(f"**{r['device_id']}**: {r['value']:.2f} {r.get('unit', '')}")
        return "\n".join(lines)
    
    if action == "aggregate":
        sensor_type = device_id  # Reuse param
        result = network.get_aggregated_data(sensor_type)
        lines = ["### AGGREGATED DATA", ""]
        lines.append(f"**Count**: {result['count']}")
        if "min" in result:
            lines.append(f"**Min**: {result['min']:.2f}")
            lines.append(f"**Max**: {result['max']:.2f}")
            lines.append(f"**Average**: {result['avg']:.2f}")
            lines.append(f"**Latest**: {result['latest']:.2f}")
        return "\n".join(lines)
    
    if action == "anomalies":
        anomalies = network.check_anomalies()
        if not anomalies:
            return "✅ No anomalies detected."
        
        lines = [f"### ANOMALIES DETECTED ({len(anomalies)})", ""]
        for a in anomalies:
            lines.append(f"**{a['device_id']}**: {a['value']:.2f} (deviation: {a['deviation']:.1f}σ)")
        return "\n".join(lines)
    
    if action == "edge_inference":
        if not device_id or not value:
            return "❌ device_id (model) and value (input) required."
        
        # Find gateway
        gateway = None
        for gw in network.gateways.values():
            if gw.online:
                gateway = gw
                break
        
        if not gateway:
            return "❌ No online gateway found."
        
        result = gateway.run_edge_inference(device_id, value)
        return f"### EDGE INFERENCE\n\n{json.dumps(result, indent=2)}"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing IoT/Edge Computing...\n")
    
    network = get_iot_network()
    
    # Add sensors
    print("--- Adding Devices ---")
    print(iot_tool("add_device", device_id="temp_001", device_type="sensor", location="living_room"))
    print(iot_tool("add_device", device_id="humid_001", device_type="sensor", location="living_room"))
    
    # Poll sensors
    print("\n--- Polling Sensors ---")
    print(iot_tool("poll"))
    
    # Aggregate
    print("\n--- Aggregated Data ---")
    print(iot_tool("aggregate"))
