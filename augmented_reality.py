"""
Friday Augmented Reality - AR core and visualization.
Marker detection, 3D rendering, AR scene management.
"""
from __future__ import annotations

import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import time


# ─── 3D Vector ───────────────────────────────────#

@dataclass
class Vector3:
    """A 3D vector."""
    x: float
    y: float
    z: float
    
    def __add__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar: float) -> 'Vector3':
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def dot(self, other: 'Vector3') -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z
    
    def cross(self, other: 'Vector3') -> 'Vector3':
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )
    
    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)
    
    def normalize(self) -> 'Vector3':
        mag = self.magnitude()
        if mag == 0:
            return Vector3(0, 0, 0)
        return Vector3(self.x / mag, self.y / mag, self.z / mag)
    
    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)


# ─── 3D Transform ───────────────────────────────────#

class Transform:
    """Represents position, rotation, scale in 3D."""
    
    def __init__(
        self,
        position: Vector3 = None,
        rotation: Vector3 = None,  # Euler angles (pitch, yaw, roll)
        scale: Vector3 = None,
    ):
        self.position = position or Vector3(0, 0, 0)
        self.rotation = rotation or Vector3(0, 0, 0)
        self.scale = scale or Vector3(1, 1, 1)
    
    def to_matrix(self) -> List[List[float]]:
        """Convert to 4x4 transformation matrix."""
        # Simplified: only position and uniform scale
        return [
            [self.scale.x, 0, 0, self.position.x],
            [0, self.scale.y, 0, self.position.y],
            [0, 0, self.scale.z, self.position.z],
            [0, 0, 0, 1],
        ]


# ─── AR Marker ────────────────────────────────────#

class ARMarker:
    """Represents an AR marker (QR code, ArUco, etc.)."""
    
    def __init__(self, marker_id: str, size: float = 1.0):
        self.id = marker_id
        self.size = size
        self.detected = False
        self.transform = Transform()
        self.last_seen = 0
        
    def detect(self, camera_image) -> bool:
        """
        Detect marker in camera image.
        In reality, would use OpenCV ArUco/QR detection.
        """
        # Simulation: randomly detect
        import random
        if random.random() < 0.1:  # 10% chance per check
            self.detected = True
            self.last_seen = time.time()
            
            # Random position when detected
            self.transform.position = Vector3(
                random.uniform(-1, 1),
                random.uniform(-1, 1),
                random.uniform(0, 2)
            )
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "size": self.size,
            "detected": self.detected,
            "position": self.transform.position.to_tuple(),
            "last_seen": self.last_seen,
        }


# ─── AR Object ────────────────────────────────────#

class ARObject:
    """An object in the AR scene."""
    
    def __init__(
        self,
        name: str,
        geometry: str = "cube",  # cube, sphere, mesh
        transform: Transform = None,
    ):
        self.name = name
        self.geometry = geometry
        self.transform = transform or Transform()
        self.visible = True
        self.color = (255, 255, 255)  # RGB
        self.opacity = 1.0
        
    def render(self, camera_transform) -> Dict[str, Any]:
        """Render object (simplified - return drawing instructions)."""
        if not self.visible:
            return {"visible": False}
        
        # Transform to camera space
        obj_pos = self.transform.position
        cam_pos = camera_transform.position
        
        relative_pos = obj_pos - cam_pos
        
        return {
            "name": self.name,
            "geometry": self.geometry,
            "position": relative_pos.to_tuple(),
            "color": self.color,
            "opacity": self.opacity,
            "scale": self.transform.scale.to_tuple(),
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "geometry": self.geometry,
            "position": self.transform.position.to_tuple(),
            "rotation": self.transform.rotation.to_tuple(),
            "scale": self.transform.scale.to_tuple(),
            "visible": self.visible,
            "color": self.color,
            "opacity": self.opacity,
        }


# ─── AR Scene ────────────────────────────────────#

class ARScene:
    """Manages the AR scene graph."""
    
    def __init__(self, name: str = "default"):
        self.name = name
        self.objects: Dict[str, ARObject] = {}
        self.markers: Dict[str, ARMarker] = {}
        self.camera_transform = Transform()
        self.light_direction = Vector3(0, -1, -1).normalize()
        
    def add_object(self, obj: ARObject) -> bool:
        """Add an object to the scene."""
        if obj.name in self.objects:
            return False
        self.objects[obj.name] = obj
        return True
    
    def remove_object(self, name: str) -> bool:
        """Remove an object."""
        if name not in self.objects:
            return False
        del self.objects[name]
        return True
    
    def add_marker(self, marker: ARMarker) -> bool:
        """Add an AR marker."""
        if marker.id in self.markers:
            return False
        self.markers[marker.id] = marker
        return True
    
    def update(self):
        """Update scene (detect markers, update positions)."""
        for marker in self.markers.values():
            marker.detect(None)  # Would pass camera frame
            
            if marker.detected:
                # Attach objects to marker
                for obj in self.objects.values():
                    if obj.name.startswith(marker.id):
                        obj.transform.position = marker.transform.position
    
    def render_scene(self) -> List[Dict[str, Any]]:
        """Render all visible objects."""
        self.update()
        return [obj.render(self.camera_transform) for obj in self.objects.values()]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "objects": {name: obj.to_dict() for name, obj in self.objects.items()},
            "markers": {mid: m.to_dict() for mid, m in self.markers.items()},
            "camera_position": self.camera_transform.position.to_tuple(),
        }


# ─── AR Renderer (Simplified) ───────────────────────────────────#

class ARRenderer:
    """Renders AR scene to text/ASCII art."""
    
    def __init__(self, width: int = 80, height: int = 24):
        self.width = width
        self.height = height
        
    def render(self, scene: ARScene) -> str:
        """Render scene to ASCII."""
        render_data = scene.render_scene()
        
        lines = [f"=== AR SCENE: {scene.name} ===", ""]
        
        lines.append(f"Camera: {scene.camera_transform.position.to_tuple()}")
        lines.append(f"Objects: {len(render_data)}")
        lines.append(f"Markers: {sum(1 for m in scene.markers.values() if m.detected)} active")
        lines.append("")
        
        for obj_data in render_data:
            if not obj_data.get("visible", True):
                continue
            lines.append(f"  [{obj_data['name']}] {obj_data['geometry']}")
            lines.append(f"    Pos: {obj_data['position']}")
            lines.append(f"    Color: {obj_data['color']}")
        
        return "\n".join(lines)


# ─── Singleton Scene ────────────────────────────────────#

_scene: Optional[ARScene] = None
_renderer: Optional[ARRenderer] = None

def get_ar_scene() -> ARScene:
    """Get or create AR scene."""
    global _scene
    if _scene is None:
        _scene = ARScene()
    return _scene

def get_ar_renderer() -> ARRenderer:
    """Get or create AR renderer."""
    global _renderer
    if _renderer is None:
        _renderer = ARRenderer()
    return _renderer


# ─── Tool Function for Friday ────────────────────────────────────#

def ar_tool(
    action: str = "status",
    object_name: str = None,
    geometry: str = "cube",
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    marker_id: str = None,
) -> str:
    """
    Friday tool for AR operations.
    Actions: status, add_object, remove_object, add_marker, render, update_camera
    """
    scene = get_ar_scene()
    
    if action == "status":
        lines = [f"### AR SCENE: {scene.name}", ""]
        lines.append(f"**Objects**: {len(scene.objects)}")
        lines.append(f"**Markers**: {len(scene.markers)}")
        lines.append(f"**Camera**: {scene.camera_transform.position.to_tuple()}")
        return "\n".join(lines)
    
    if action == "add_object":
        if not object_name:
            return "❌ Object name required."
        
        obj = ARObject(object_name, geometry, Transform(Vector3(x, y, z)))
        if scene.add_object(obj):
            return f"✅ Added object: {object_name}"
        return f"❌ Object '{object_name}' already exists."
    
    if action == "remove_object":
        if not object_name:
            return "❌ Object name required."
        if scene.remove_object(object_name):
            return f"✅ Removed object: {object_name}"
        return f"❌ Object '{object_name}' not found."
    
    if action == "add_marker":
        if not marker_id:
            return "❌ Marker ID required."
        
        marker = ARMarker(marker_id)
        if scene.add_marker(marker):
            return f"✅ Added marker: {marker_id}"
        return f"❌ Marker '{marker_id}' already exists."
    
    if action == "render":
        renderer = get_ar_renderer()
        return renderer.render(scene)
    
    if action == "update_camera":
        scene.camera_transform.position = Vector3(x, y, z)
        return f"✅ Camera moved to ({x}, {y}, {z})"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Augmented Reality...\n")
    
    scene = get_ar_scene()
    
    # Add objects
    print("--- Adding Objects ---")
    print(ar_tool("add_object", object_name="cube1", x=1, y=0, z=0))
    print(ar_tool("add_object", object_name="sphere1", geometry="sphere", x=-1, y=0, z=1))
    
    # Add marker
    print("\n--- Adding Marker ---")
    print(ar_tool("add_marker", marker_id="marker01"))
    
    # Render
    print("\n--- Rendering Scene ---")
    print(ar_tool("render"))
