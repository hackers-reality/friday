"""
Friday Advanced Robotics - Robot control and automation.
Supports robot simulation, control systems, and automation protocols.
"""
from __future__ import annotations

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import time
import math


# ─── Robot State ─────────────────────────────────#

class RobotState:
    """Represents the state of a robot."""
    
    def __init__(
        self,
        position: List[float] = None,
        orientation: List[float] = None,
        joint_angles: List[float] = None,
        gripper_state: str = "open",
    ):
        self.position = position or [0.0, 0.0, 0.0]  # [x, y, z]
        self.orientation = orientation or [0.0, 0.0, 0.0, 1.0]  # [roll, pitch, yaw] or quaternion
        self.joint_angles = joint_angles or []
        self.gripper_state = gripper_state  # "open" or "closed"
        self.timestamp = datetime.now().isoformat()
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "position": self.position,
            "orientation": self.orientation,
            "joint_angles": self.joint_angles,
            "gripper_state": self.gripper_state,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RobotState':
        return cls(
            data.get("position", [0.0, 0.0, 0.0]),
            data.get("orientation", [0.0, 0.0, 0.0, 1.0]),
            data.get("joint_angles"),
            data.get("gripper_state", "open"),
        )


# ─── Robot Arm (6-DOF) ─────────────────────────────────#

class RobotArm:
    """Simulates a 6-DOF robotic arm."""
    
    def __init__(self, name: str = "friday_arm", num_joints: int = 6):
        self.name = name
        self.num_joints = num_joints
        self.state = RobotState(joint_angles=[0.0] * num_joints)
        self.link_lengths = [1.0] * num_joints  # Meteres
        self.joint_limits = [(-math.pi, math.pi)] * num_joints  # Radians
        self._calculate_forward_kinematics()
        
    def _calculate_forward_kinematics(self):
        """Update position based on joint angles (simplified)."""
        # Simplified: assume all joints are revolute in Z-axis
        x, y, z = 0.0, 0.0, 0.0
        cum_angle = 0.0
        
        for i, angle in enumerate(self.state.joint_angles):
            length = self.link_lengths[i] if i < len(self.link_lengths) else 1.0
            cum_angle += angle
            x += length * math.cos(cum_angle)
            y += length * math.sin(cum_angle)
            z += 0.1  # Small Z increment per joint
        
        self.state.position = [x, y, z]
        self.state.timestamp = datetime.now().isoformat()
        
    def move_joint(self, joint_index: int, angle: float) -> str:
        """Move a specific joint to an angle (radians)."""
        if joint_index < 0 or joint_index >= self.num_joints:
            return f"[FAIL] Invalid joint index: {joint_index}"
        
        # Clamp to limits
        min_limit, max_limit = self.joint_limits[joint_index]
        angle = max(min_limit, min(max_limit, angle))
        
        self.state.joint_angles[joint_index] = angle
        self._calculate_forward_kinematics()
        return f"[OK] Joint {joint_index} moved to {angle:.2f} rad ({math.degrees(angle):.1f}°)"
    
    def move_to_position(self, x: float, y: float, z: float) -> str:
        """Move end-effector to a position (inverse kinematics - simplified)."""
        # Very simplified: assume 2-DOF for X-Y plane
        target_angle = math.atan2(y, x)
        if len(self.state.joint_angles) > 0:
            self.state.joint_angles[0] = target_angle
        
        # Adjust for distance
        distance = math.sqrt(x**2 + y**2)
        if len(self.state.joint_angles) > 1:
            self.state.joint_angles[1] = distance - sum(self.link_lengths[:-1])
        
        self._calculate_forward_kinematics()
        return f"[OK] Moved to position ({x:.2f}, {y:.2f}, {z:.2f})"
    
    def grip(self, action: str = "close") -> str:
        """Control gripper."""
        if action == "close":
            self.state.gripper_state = "closed"
            return "[OK] Gripper closed."
        elif action == "open":
            self.state.gripper_state = "open"
            return "[OK] Gripper opened."
        return f"[FAIL] Unknown action: {action}"
    
    def get_state(self) -> str:
        """Get current robot state."""
        lines = [f"### ROBOT ARM: {self.name}", ""]
        lines.append(f"**Position**: {[f'{p:.2f}' for p in self.state.position]}")
        lines.append(f"**Joint Angles**: {[f'{a:.2f}' for a in self.state.joint_angles]}")
        lines.append(f"**Gripper**: {self.state.gripper_state}")
        return "\n".join(lines)
    
    def reset(self) -> str:
        """Reset robot to home position."""
        self.state.joint_angles = [0.0] * self.num_joints
        self.state.gripper_state = "open"
        self._calculate_forward_kinematics()
        return "[OK] Robot reset to home position."


# ─── Robot Swarm ─────────────────────────────────#

class RobotSwarm:
    """Manages multiple robots working together."""
    
    def __init__(self):
        self.robots: Dict[str, RobotArm] = {}
        self._add_default_robots()
        
    def _add_default_robots(self):
        """Add some default robots."""
        self.robots["arm1"] = RobotArm("Arm 1", num_joints=6)
        self.robots["arm2"] = RobotArm("Arm 2", num_joints=4)
        
    def add_robot(self, name: str, num_joints: int = 6) -> str:
        """Add a robot to the swarm."""
        if name in self.robots:
            return f"[FAIL] Robot '{name}' already exists."
        self.robots[name] = RobotArm(name, num_joints)
        return f"[OK] Added robot: {name}"
    
    def remove_robot(self, name: str) -> str:
        """Remove a robot from the swarm."""
        if name not in self.robots:
            return f"[FAIL] Robot '{name}' not found."
        del self.robots[name]
        return f"[OK] Removed robot: {name}"
    
    def broadcast_command(self, command: str, params: Dict[str, Any] = None) -> str:
        """Send command to all robots."""
        params = params or {}
        results = []
        
        for name, robot in self.robots.items():
            if command == "reset":
                results.append(f"{name}: {robot.reset()}")
            elif command == "grip":
                action = params.get("action", "close")
                results.append(f"{name}: {robot.grip(action)}")
            elif command == "move_joint":
                joint = params.get("joint", 0)
                angle = params.get("angle", 0.0)
                results.append(f"{name}: {robot.move_joint(joint, angle)}")
            elif command == "move_to":
                x = params.get("x", 0.0)
                y = params.get("y", 0.0)
                z = params.get("z", 0.0)
                results.append(f"{name}: {robot.move_to_position(x, y, z)}")
        
        return "### SWARM COMMAND: " + command.upper() + "\n\n" + "\n".join(results)
    
    def get_swarm_status(self) -> str:
        """Get status of all robots."""
        lines = ["### ROBOT SWARM STATUS", ""]
        lines.append(f"**Total Robots**: {len(self.robots)}")
        lines.append("")
        
        for name, robot in self.robots.items():
            lines.append(f"**{name}**")
            lines.append(f"  Position: {[f'{p:.2f}' for p in robot.state.position]}")
            lines.append(f"  Gripper: {robot.state.gripper_state}")
            lines.append("")
        
        return "\n".join(lines)


# ─── Path Planning ─────────────────────────────────#

class PathPlanner:
    """Basic path planning for robots."""
    
    @staticmethod
    def plan_linear(start: List[float], end: List[float], steps: int = 10) -> List[List[float]]:
        """Plan a linear path from start to end."""
        if len(start) != len(end):
            return []
        
        path = []
        for i in range(steps + 1):
            t = i / steps
            point = [start[j] + t * (end[j] - start[j]) for j in range(len(start))]
            path.append(point)
        
        return path
    
    @staticmethod
    def plan_circle(center: List[float], radius: float, steps: int = 20) -> List[List[float]]:
        """Plan a circular path."""
        if len(center) < 2:
            return []
        
        path = []
        for i in range(steps):
            angle = 2 * math.pi * i / steps
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            z = center[2] if len(center) > 2 else 0.0
            path.append([x, y, z])
        
        return path
    
    @staticmethod
    def follow_path(robot: RobotArm, path: List[List[float]]) -> str:
        """Make robot follow a path."""
        results = []
        for i, point in enumerate(path):
            if len(point) >= 3:
                result = robot.move_to_position(point[0], point[1], point[2])
                results.append(f"Step {i+1}: {result}")
            elif len(point) >= 2:
                result = robot.move_to_position(point[0], point[1], 0.0)
                results.append(f"Step {i+1}: {result}")
        return "\n".join(results)


# ─── Singleton Instances ─────────────────────────────────#

_arm: Optional[RobotArm] = None
_swarm: Optional[RobotSwarm] = None

def get_robot_arm(name: str = "default") -> RobotArm:
    """Get or create a robot arm."""
    global _arm
    if _arm is None:
        _arm = RobotArm(name)
    return _arm

def get_swarm() -> RobotSwarm:
    """Get or create robot swarm."""
    global _swarm
    if _swarm is None:
        _swarm = RobotSwarm()
    return _swarm


# ─── Tool Function for Friday ─────────────────────────────────#

def robotics_tool(
    action: str = "status",
    robot_name: str = None,
    joint_index: int = 0,
    angle: float = 0.0,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    grip_action: str = "close",
) -> str:
    """
    Friday tool for robotics control.
    Actions: status, move_joint, move_to, grip, reset, swarm_status, swarm_command, plan_path
    """
    if action == "status":
        arm = get_robot_arm("default")
        return arm.get_state()
    
    if action == "move_joint":
        arm = get_robot_arm("default")
        return arm.move_joint(joint_index, angle)
    
    if action == "move_to":
        arm = get_robot_arm("default")
        return arm.move_to_position(x, y, z)
    
    if action == "grip":
        arm = get_robot_arm("default")
        return arm.grip(grip_action)
    
    if action == "reset":
        arm = get_robot_arm("default")
        return arm.reset()
    
    if action == "swarm_status":
        swarm = get_swarm()
        return swarm.get_swarm_status()
    
    if action == "swarm_command":
        if not robot_name:
            return "[FAIL] robot_name required for swarm_command."
        swarm = get_swarm()
        params = {"action": grip_action} if grip_action else {}
        return swarm.broadcast_command(robot_name, params)
    
    if action == "plan_path":
        # Plan a sample path
        planner = PathPlanner()
        center = [x, y, z] if z else [x, y]
        path = planner.plan_circle(center, radius=1.0, steps=10)
        return f"### PLANNED PATH ({len(path)} points)\n" + "\n".join(
            [f"  Point {i+1}: {p}" for i, p in enumerate(path[:5])]
        ) + f"\n  ... and {len(path) - 5} more points."
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Robotics Control...\n")
    
    # Test robot arm
    arm = RobotArm("TestArm", num_joints=3)
    print("--- Initial State ---")
    print(arm.get_state())
    
    print("\n--- Move Joint ---")
    print(arm.move_joint(0, math.pi / 4))
    print(arm.get_state())
    
    print("\n--- Move to Position ---")
    print(arm.move_to_position(1.0, 1.0, 0.5))
    
    print("\n--- Grip ---")
    print(arm.grip("close"))
    
    print("\n--- Path Planning ---")
    planner = PathPlanner()
    path = planner.plan_linear([0, 0, 0], [1, 1, 0], steps=5)
    print(f"Linear path: {len(path)} points")
    for p in path:
        print(f"  {p}")
