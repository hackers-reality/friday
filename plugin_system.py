"""
Friday Plugin System - Extensible architecture for adding new capabilities.
Plugins can be loaded dynamically and expose new tools to Friday.
"""
from __future__ import annotations

import os
import sys
import importlib
import inspect
from typing import Dict, Any, List, Callable, Type
from pathlib import Path
import json


# ─── Plugin Base Class ────────────────────────────────────#

class FridayPlugin:
    """Base class for all Friday plugins."""
    
    name: str = "base_plugin"
    description: str = "Base plugin class"
    version: str = "1.0.0"
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self._register_tools()
    
    def _register_tools(self):
        """Override this to register tools."""
        pass
    
    def register_tool(self, name: str, func: Callable, description: str = ""):
        """Register a tool with Friday."""
        self.tools[name] = {
            "function": func,
            "description": description or func.__doc__ or "No description",
        }
    
    def get_tools(self) -> Dict[str, Callable]:
        """Get all registered tools."""
        return self.tools
    
    def initialize(self):
        """Called when plugin is loaded. Override for setup."""
        pass
    
    def shutdown(self):
        """Called when plugin is unloaded. Override for cleanup."""
        pass


# ─── Plugin Manager ────────────────────────────────────#

class PluginManager:
    """Manages Friday plugins."""
    
    def __init__(self, plugin_dir: str = "friday_plugins"):
        self.plugin_dir = Path(plugin_dir)
        self.plugins: Dict[str, FridayPlugin] = {}
        self._ensure_plugin_dir()
    
    def _ensure_plugin_dir(self):
        """Create plugin directory if needed."""
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        # Create __init__.py
        init_file = self.plugin_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# Friday Plugins\n")
    
    def discover_plugins(self) -> List[str]:
        """Discover available plugins."""
        plugins = []
        if not self.plugin_dir.exists():
            return plugins
        
        for py_file in self.plugin_dir.glob("*.py"):
            if py_file.name != "__init__.py":
                plugins.append(py_file.stem)
        
        return plugins
    
    def load_plugin(self, plugin_name: str) -> bool:
        """Load a plugin by name."""
        try:
            module = importlib.import_module(f"friday_plugins.{plugin_name}")
            
            # Find plugin classes
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, FridayPlugin) and obj != FridayPlugin:
                    plugin_instance = obj()
                    plugin_instance.initialize()
                    self.plugins[plugin_name] = plugin_instance
                    print(f"[Plugin] Loaded: {plugin_name} v{plugin_instance.version}")
                    return True
            
            print(f"[Plugin] No plugin class found in {plugin_name}")
            return False
            
        except Exception as e:
            print(f"[Plugin] Error loading {plugin_name}: {e}")
            return False
    
    def load_all_plugins(self):
        """Load all discovered plugins."""
        plugins = self.discover_plugins()
        print(f"[Plugin] Discovering {len(plugins)} plugins...")
        for plugin_name in plugins:
            self.load_plugin(plugin_name)
    
    def unload_plugin(self, plugin_name: str):
        """Unload a plugin."""
        if plugin_name in self.plugins:
            self.plugins[plugin_name].shutdown()
            del self.plugins[plugin_name]
            print(f"[Plugin] Unloaded: {plugin_name}")
    
    def get_all_tools(self) -> Dict[str, Callable]:
        """Get all tools from all plugins."""
        all_tools = {}
        for plugin_name, plugin in self.plugins.items():
            tools = plugin.get_tools()
            for tool_name, tool_info in tools.items():
                all_tools[f"{plugin_name}.{tool_name}"] = tool_info
        return all_tools
    
    def get_plugin(self, plugin_name: str) -> FridayPlugin:
        """Get a specific plugin instance."""
        return self.plugins.get(plugin_name)
    
    def list_plugins(self) -> str:
        """List all loaded plugins."""
        if not self.plugins:
            return "No plugins loaded."
        
        lines = ["### LOADED PLUGINS", ""]
        for name, plugin in self.plugins.items():
            lines.append(f"**{name}** v{plugin.version}")
            lines.append(f"  {plugin.description}")
            lines.append(f"  Tools: {len(plugin.tools)}")
            lines.append("")
        
        return "\n".join(lines)


# ─── Example Plugin ────────────────────────────────────#

class ExamplePlugin(FridayPlugin):
    """Example plugin demonstrating the plugin system."""
    
    name = "example"
    description = "Example plugin for demonstration"
    version = "1.0.0"
    
    def _register_tools(self):
        self.register_tool("hello", self.hello, "Say hello from plugin")
        self.register_tool("calculate", self.calculate, "Perform calculation")
    
    def hello(self, name: str = "World") -> str:
        """Say hello."""
        return f"Hello, {name}! From Friday Plugin System!"
    
    def calculate(self, expression: str) -> str:
        """Calculate a math expression."""
        try:
            result = eval(expression, {"__builtins__": {}}, {})
            return f"Result: {result}"
        except Exception as e:
            return f"Error: {e}"


# ─── Global Plugin Manager ────────────────────────────────────#

_manager: Optional[PluginManager] = None

def get_plugin_manager() -> PluginManager:
    """Get or create the global plugin manager."""
    global _manager
    if _manager is None:
        _manager = PluginManager()
    return _manager


# ─── Tool Function for Friday ────────────────────────────────────#

def plugin_tool(
    action: str = "list",
    plugin_name: str = None,
    tool_name: str = None,
    **kwargs
) -> str:
    """
    Friday tool for managing plugins.
    Actions: list, load, unload, call, discover
    """
    manager = get_plugin_manager()
    
    if action == "list":
        return manager.list_plugins()
    
    if action == "discover":
        plugins = manager.discover_plugins()
        return f"Discovered plugins: {', '.join(plugins) if plugins else 'None'}"
    
    if action == "load":
        if not plugin_name:
            return "[FAIL] Plugin name required."
        success = manager.load_plugin(plugin_name)
        return f"{'[OK]' if success else '[FAIL]'} Load plugin '{plugin_name}'"
    
    if action == "load_all":
        manager.load_all_plugins()
        return "[OK] Loaded all plugins."
    
    if action == "unload":
        if not plugin_name:
            return "[FAIL] Plugin name required."
        manager.unload_plugin(plugin_name)
        return f"[OK] Unloaded '{plugin_name}'"
    
    if action == "call":
        if not plugin_name or not tool_name:
            return "[FAIL] Plugin and tool name required."
        plugin = manager.get_plugin(plugin_name)
        if not plugin:
            return f"[FAIL] Plugin '{plugin_name}' not loaded."
        if tool_name not in plugin.tools:
            return f"[FAIL] Tool '{tool_name}' not found in plugin '{plugin_name}'."
        func = plugin.tools[tool_name]["function"]
        return func(**kwargs)
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Plugin System...")
    
    # Create plugin manager
    manager = PluginManager()
    
    # Discover plugins
    print("\nDiscovering plugins...")
    plugins = manager.discover_plugins()
    print(f"Found: {plugins}")
    
    # Load all plugins
    print("\nLoading plugins...")
    manager.load_all_plugins()
    
    # List plugins
    print("\n" + manager.list_plugins())
    
    # Test calling a tool
    print("\nTesting tool call...")
    result = plugin_tool("call", plugin_name="example", tool_name="hello", name="Friday")
    print(result)
