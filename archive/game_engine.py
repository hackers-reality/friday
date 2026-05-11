"""
Friday Game Engine - 2D/3D game development.
Game objects, physics, collision detection, rendering.
"""
from __future__ import annotations

import os
import time
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


# ─── Vector2 ────────────────────────────#

@dataclass
class Vector2:
    """2D vector."""
    x: float
    y: float
    
    def __add__(self, other: 'Vector2') -> 'Vector2':
        return Vector2(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: 'Vector2') -> 'Vector2':
        return Vector2(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar: float) -> 'Vector2':
        return Vector2(self.x * scalar, self.y * scalar)
    
    def dot(self, other: 'Vector2') -> float:
        return self.x * other.x + self.y * other.y
    
    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2)
    
    def normalize(self) -> 'Vector2':
        mag = self.magnitude()
        if mag == 0:
            return Vector2(0, 0)
        return Vector2(self.x / mag, self.y / mag)
    
    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)


# ─── Rectangle ────────────────────────────#

@dataclass
class Rect:
    """Rectangle for collision detection."""
    x: float
    y: float
    width: float
    height: float
    
    def contains(self, point: Vector2) -> bool:
        return (self.x <= point.x <= self.x + self.width and
                self.y <= point.y <= self.y + self.height)
    
    def intersects(self, other: 'Rect') -> bool:
        return not (
            self.x + self.width < other.x or
            other.x + other.width < self.x or
            self.y + self.height < other.y or
            other.y + other.height < self.y
        )
    
    def to_tuple(self) -> Tuple[float, float, float, float]:
        return (self.x, self.y, self.width, self.height)


# ─── GameObject ────────────────────────────#

class GameObject:
    """Base class for game objects."""
    
    def __init__(self, name: str, position: Vector2 = None, size: Vector2 = None):
        self.name = name
        self.position = position or Vector2(0, 0)
        self.size = size or Vector2(1, 1)
        self.velocity = Vector2(0, 0)
        self.acceleration = Vector2(0, 0)
        self.active = True
        self.tags: List[str] = []
        
    def update(self, dt: float):
        """Update object physics."""
        if not self.active:
            return
        
        # Update velocity
        self.velocity = self.velocity + self.acceleration * dt
        
        # Update position
        self.position = self.position + self.velocity * dt
        
    def get_rect(self) -> Rect:
        """Get bounding rectangle."""
        return Rect(
            self.position.x,
            self.position.y,
            self.size.x,
            self.size.y
        )
    
    def on_collision(self, other: 'GameObject'):
        """Handle collision."""
        pass
    
    def render(self) -> str:
        """Render object (ASCII)."""
        return f"[{self.name}: ({self.position.x:.1f}, {self.position.y:.1f})]"


# ─── Physics World ────────────────────────────#

class PhysicsWorld:
    """Manages physics simulation."""
    
    def __init__(self, gravity: Vector2 = None):
        self.gravity = gravity or Vector2(0, -9.8)
        self.objects: List[GameObject] = []
        self.collision_callbacks: Dict[str, callable] = {}
        
    def add_object(self, obj: GameObject) -> bool:
        if any(o.name == obj.name for o in self.objects):
            return False
        self.objects.append(obj)
        return True
    
    def remove_object(self, name: str) -> bool:
        for i, obj in enumerate(self.objects):
            if obj.name == name:
                self.objects.pop(i)
                return True
        return False
    
    def get_object(self, name: str) -> Optional[GameObject]:
        for obj in self.objects:
            if obj.name == name:
                return obj
        return None
    
    def update(self, dt: float):
        """Update all objects."""
        # Apply gravity
        for obj in self.objects:
            if obj.active:
                obj.acceleration = obj.acceleration + self.gravity
                obj.update(dt)
        
        # Check collisions
        self._check_collisions()
        
    def _check_collisions(self):
        """Check for collisions between objects."""
        for i in range(len(self.objects)):
            for j in range(i + 1, len(self.objects)):
                obj1 = self.objects[i]
                obj2 = self.objects[j]
                
                if not obj1.active or not obj2.active:
                    continue
                
                if obj1.get_rect().intersects(obj2.get_rect()):
                    obj1.on_collision(obj2)
                    obj2.on_collision(obj1)
                    
                    # Call registered callbacks
                    key = f"{obj1.name}_{obj2.name}"
                    if key in self.collision_callbacks:
                        self.collision_callbacks[key](obj1, obj2)
    
    def register_collision(self, obj1_name: str, obj2_name: str, callback: callable):
        """Register collision callback."""
        self.collision_callbacks[f"{obj1_name}_{obj2_name}"] = callback


# ─── Game Scene ────────────────────────────#

class GameScene:
    """Manages a game scene."""
    
    def __init__(self, name: str = "default"):
        self.name = name
        self.world = PhysicsWorld()
        self.background = "."
        self.width = 80  # Characters
        self.height = 24  # Lines
        
    def add_object(self, obj: GameObject) -> bool:
        return self.world.add_object(obj)
    
    def update(self, dt: float):
        self.world.update(dt)
        
    def render(self) -> str:
        """Render scene to ASCII."""
        # Create empty grid
        grid = [[self.background for _ in range(self.width)] for _ in range(self.height)]
        
        # Place objects
        for obj in self.world.objects:
            if not obj.active:
                continue
            
            # Simplified: just mark position
            x = int(obj.position.x) % self.width
            y = int(obj.position.y) % self.height
            if 0 <= x < self.width and 0 <= y < self.height:
                grid[y][x] = "O"  # Object marker
        
        # Convert to string
        return "\n".join("".join(row) for row in grid)
    
    def get_stats(self) -> Dict[str, Any]:
        active = sum(1 for o in self.world.objects if o.active)
        return {
            "scene": self.name,
            "objects": len(self.world.objects),
            "active": active,
            "inactive": len(self.world.objects) - active,
        }


# ─── Game Loop ────────────────────────────#

class GameLoop:
    """Main game loop."""
    
    def __init__(self, scene: GameScene, fps: int = 30):
        self.scene = scene
        self.fps = fps
        self.dt = 1.0 / fps
        self.running = False
        self.frame_count = 0
        
    def start(self, max_frames: int = 100):
        """Start the game loop."""
        self.running = True
        print(f"[Game] Starting: {self.scene.name} at {self.fps} FPS")
        
        while self.running and self.frame_count < max_frames:
            start_time = time.time()
            
            # Update
            self.scene.update(self.dt)
            
            # Render
            if self.frame_count % 10 == 0:  # Render every 10 frames
                print("\033[H\033[J")  # Clear screen
                print(self.scene.render())
                print(f"Frame: {self.frame_count}")
            
            self.frame_count += 1
            
            # Sleep to maintain FPS
            elapsed = time.time() - start_time
            sleep_time = max(0, self.dt - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        print(f"[Game] Stopped after {self.frame_count} frames")
    
    def stop(self):
        self.running = False


# ─── Singleton Scene ────────────────────────────#

_scene: Optional[GameScene] = None

def get_game_scene(name: str = "default") -> GameScene:
    global _scene
    if _scene is None:
        _scene = GameScene(name)
    return _scene


# ─── Tool Function for Friday ────────────────────────────#

def game_tool(
    action: str = "status",
    object_name: str = None,
    x: float = 0.0,
    y: float = 0.0,
    vx: float = 0.0,
    vy: float = 0.0,
) -> str:
    """
    Friday tool for game engine operations.
    Actions: status, add_object, update, render, loop
    """
    scene = get_game_scene()
    
    if action == "status":
        stats = scene.get_stats()
        lines = [f"### GAME SCENE: {scene.name}", ""]
        lines.append(f"**Objects**: {stats['objects']}")
        lines.append(f"**Active**: {stats['active']}")
        lines.append(f"**Inactive**: {stats['inactive']}")
        return "\n".join(lines)
    
    if action == "add_object":
        if not object_name:
            return "[FAIL] Object name required."
        
        obj = GameObject(object_name, Vector2(x, y))
        obj.velocity = Vector2(vx, vy)
        
        if scene.add_object(obj):
            return f"[OK] Added object: {object_name}"
        return f"[FAIL] Object '{object_name}' already exists."
    
    if action == "update":
        scene.update(0.016)  # ~60 FPS
        return "[OK] Scene updated."
    
    if action == "render":
        return f"### SCENE RENDER\n\n{scene.render()}"
    
    if action == "loop":
        loop = GameLoop(scene)
        loop.start(max_frames=50)
        return "[OK] Game loop completed."
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Game Engine...\n")
    
    # Create scene
    scene = get_game_scene("test_level")
    
    # Add objects
    print("--- Adding Objects ---")
    print(game_tool("add_object", object_name="player", x=10, y=10))
    print(game_tool("add_object", object_name="enemy", x=50, y=10, vx=-1))
    
    # Status
    print("\n--- Scene Status ---")
    print(game_tool("status"))
    
    # Render
    print("\n--- Render ---")
    print(game_tool("render"))
