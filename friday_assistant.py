"""
Friday Assistant - Main assistant integrating all modules.
High-level interface for all Friday capabilities.
"""
from __future__ import annotations

import os
import sys
import json
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from pathlib import Path
import importlib.util
import traceback


# ─── Module Registry ────────────────────────────#

class ModuleRegistry:
    """Registry of all Friday modules."""
    
    def __init__(self):
        self.modules: Dict[str, Any] = {}
        self.module_paths: Dict[str, str] = {}
        self.loaded = False
        
    def discover_modules(self, base_path: str = None):
        """Discover and register available modules."""
        base_path = base_path or os.path.dirname(os.path.abspath(__file__))
        
        # Module definitions
        module_defs = [
            ("friday_core", "FridayCore", "friday_core.py"),
            ("friday_voice", "voice_tool", "friday_voice.py"),
            ("friday_web", "web_tool", "friday_web.py"),
            ("friday_automation", "automation_tool", "friday_automation.py"),
            ("friday_database", "database_tool", "friday_database.py"),
            ("friday_ai", "ai_tool", "friday_ai.py"),
            ("friday_tools", "tools_tool", "friday_tools.py"),
            ("friday_vision", "vision_tool", "friday_vision.py"),
            ("friday_security", "security_tool", "friday_security.py"),
            ("advanced_networking", "network_tool", "advanced_networking.py"),
            ("advanced_crypto", "crypto_tool", "advanced_crypto.py"),
        ]
        
        for module_name, tool_name, file_name in module_defs:
            file_path = os.path.join(base_path, file_name)
            if os.path.exists(file_path):
                self.module_paths[module_name] = file_path
                
        self.loaded = True
        return self.module_paths
    
    def load_module(self, module_name: str) -> Optional[Any]:
        """Load a module by name."""
        if module_name in self.modules:
            return self.modules[module_name]
        
        if module_name not in self.module_paths:
            return None
        
        try:
            spec = importlib.util.spec_from_file_location(module_name, self.module_paths[module_name])
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.modules[module_name] = module
            return module
        except Exception as e:
            print(f"❌ Error loading {module_name}: {e}")
            return None
    
    def get_tool(self, module_name: str, tool_name: str = None) -> Optional[Callable]:
        """Get a tool function from a module."""
        module = self.load_module(module_name)
        if not module:
            return None
        
        # If tool_name is provided, look for it
        if tool_name:
            if hasattr(module, tool_name):
                return getattr(module, tool_name)
            return None
        
        # Otherwise, try to find a tool function
        for attr_name in dir(module):
            if "tool" in attr_name.lower():
                attr = getattr(module, attr_name)
                if callable(attr):
                    return attr
        
        return None
    
    def list_modules(self) -> List[str]:
        """List all available modules."""
        return list(self.module_paths.keys())


# ─── Friday Assistant ────────────────────────────#

class FridayAssistant:
    """Main Friday Assistant class."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.registry = ModuleRegistry()
        self.registry.discover_modules()
        
        self.config = config or {
            "name": "Friday",
            "version": "2.0.0",
            "voice_enabled": False,
            "auto_execute": True,
            "debug": False,
        }
        
        self.history: List[Dict] = []
        self.context: Dict[str, Any] = {}
        self.start_time = datetime.now()
        
    def initialize(self) -> str:
        """Initialize Friday and all modules."""
        lines = [
            f"### {self.config['name']} v{self.config['version']} - INITIALIZED",
            "",
            "**Available Modules**:",
        ]
        
        for module_name in self.registry.list_modules():
            module = self.registry.load_module(module_name)
            status = "✅ Loaded" if module else "❌ Not loaded"
            lines.append(f"  - {module_name}: {status}")
        
        lines.append("")
        lines.append("**Ready for commands.**")
        lines.append(f"**Uptime**: {self._get_uptime()}")
        
        return "\n".join(lines)
    
    def process(self, command: str) -> str:
        """Process a user command."""
        if not command or not command.strip():
            return "❌ Empty command."
        
        command = command.strip()
        self._log_command(command)
        
        # Parse command
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # Help
        if cmd in ("help", "?", "h"):
            return self._show_help()
        
        # Status
        if cmd in ("status", "info"):
            return self._show_status()
        
        # List modules
        if cmd in ("modules", "list"):
            return self._list_modules()
        
        # Clear history
        if cmd == "clear":
            self.history = []
            return "✅ History cleared."
        
        # Exit
        if cmd in ("exit", "quit", "bye"):
            return "Goodbye!"
        
        # Route to appropriate module
        try:
            return self._route_command(cmd, args)
        except Exception as e:
            error_msg = f"❌ Error processing command: {e}"
            if self.config.get("debug"):
                error_msg += f"\n\nTraceback:\n{traceback.format_exc()}"
            return error_msg
    
    def _route_command(self, cmd: str, args: str) -> str:
        """Route command to appropriate module."""
        
        # Networking commands
        if cmd in ("network", "http", "ping", "dns", "scan"):
            tool = self.registry.get_tool("advanced_networking", "network_tool")
            if tool:
                return tool(cmd, args)
            return "❌ Networking module not available."
        
        # Crypto commands
        if cmd in ("crypto", "encrypt", "decrypt", "hash", "aes", "rsa", "ecc"):
            tool = self.registry.get_tool("advanced_crypto", "crypto_tool")
            if tool:
                return tool(cmd, args)
            return "❌ Crypto module not available."
        
        # Web commands
        if cmd in ("web", "fetch", "scrape", "search"):
            tool = self.registry.get_tool("friday_web", "web_tool")
            if tool:
                return tool(cmd, args)
            return "❌ Web module not available."
        
        # Automation commands
        if cmd in ("automate", "browser", "rpa"):
            tool = self.registry.get_tool("friday_automation", "automation_tool")
            if tool:
                return tool(cmd, args)
            return "❌ Automation module not available."
        
        # Database commands
        if cmd in ("db", "database", "sql", "query"):
            tool = self.registry.get_tool("friday_database", "database_tool")
            if tool:
                return tool(cmd, args)
            return "❌ Database module not available."
        
        # AI commands
        if cmd in ("ai", "chat", "ask"):
            tool = self.registry.get_tool("friday_ai", "ai_tool")
            if tool:
                return tool(cmd, args)
            return "❌ AI module not available."
        
        # Tools commands
        if cmd in ("tools", "convert", "calc", "calculate"):
            tool = self.registry.get_tool("friday_tools", "tools_tool")
            if tool:
                return tool(cmd, args)
            return "❌ Tools module not available."
        
        # Vision commands
        if cmd in ("vision", "image", "ocr", "qr"):
            tool = self.registry.get_tool("friday_vision", "vision_tool")
            if tool:
                return tool(cmd, args)
            return "❌ Vision module not available."
        
        # Security commands
        if cmd in ("security", "scan", "ssl", "password"):
            tool = self.registry.get_tool("friday_security", "security_tool")
            if tool:
                return tool(cmd, args)
            return "❌ Security module not available."
        
        # Voice commands
        if cmd in ("voice", "speak", "listen"):
            tool = self.registry.get_tool("friday_voice", "voice_tool")
            if tool:
                return tool(cmd, args)
            return "❌ Voice module not available."
        
        # Unknown command
        return f"""### UNKNOWN COMMAND
        
I don't understand: "{cmd}"

Try `help` to see available commands."""
    
    def _show_help(self) -> str:
        """Show help."""
        lines = [
            "### FRIDAY HELP",
            "",
            "**Available Commands**:",
            "",
            "**Core**:",
            "  - `help` - Show this help",
            "  - `status` - Show system status",
            "  - `modules` - List all modules",
            "  - `clear` - Clear command history",
            "  - `exit` - Exit Friday",
            "",
            "**Modules**:",
            "  - `network <action>` - Networking operations",
            "  - `crypto <action>` - Cryptography operations",
            "  - `web <action>` - Web operations",
            "  - `automate <action>` - Automation operations",
            "  - `db <action>` - Database operations",
            "  - `ai <action>` - AI operations",
            "  - `tools <action>` - Utility tools",
            "  - `vision <action>` - Vision operations",
            "  - `security <action>` - Security operations",
            "  - `voice <action>` - Voice operations",
            "",
            "**Examples**:",
            "  - `network status`",
            "  - `crypto hash Hello`",
            "  - `web search Python`",
            "  - `vision qr_generate data=https://friday.ai`",
            "  - `security port_scan localhost`",
        ]
        return "\n".join(lines)
    
    def _show_status(self) -> str:
        """Show system status."""
        lines = [
            "### FRIDAY STATUS",
            "",
            f"**Name**: {self.config['name']}",
            f"**Version**: {self.config['version']}",
            f"**Uptime**: {self._get_uptime()}",
            f"**Commands Processed**: {len(self.history)}",
            "",
            "**Modules**:",
        ]
        
        for module_name in self.registry.list_modules():
            module = self.registry.load_module(module_name)
            status = "✅" if module else "❌"
            lines.append(f"  {status} {module_name}")
        
        return "\n".join(lines)
    
    def _list_modules(self) -> str:
        """List all modules."""
        lines = [
            "### AVAILABLE MODULES",
            "",
        ]
        
        for i, module_name in enumerate(self.registry.list_modules(), 1):
            module = self.registry.load_module(module_name)
            status = "✅ Loaded" if module else "❌ Not loaded"
            lines.append(f"{i}. **{module_name}** - {status}")
        
        return "\n".join(lines)
    
    def _log_command(self, command: str):
        """Log a command to history."""
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "command": command,
        })
        
        # Keep history manageable
        if len(self.history) > 100:
            self.history = self.history[-100:]
    
    def _get_uptime(self) -> str:
        """Get uptime as string."""
        delta = datetime.now() - self.start_time
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h {minutes}m {seconds}s"


# ─── Interactive CLI ────────────────────────────#

def main():
    """Main entry point for Friday Assistant."""
    friday = FridayAssistant()
    
    print(friday.initialize())
    print()
    
    while True:
        try:
            user_input = input("Friday> ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ("exit", "quit", "bye"):
                print("Friday: Goodbye!")
                break
            
            response = friday.process(user_input)
            print(response)
            print()
            
        except KeyboardInterrupt:
            print("\nFriday: Interrupted. Use 'exit' to quit.")
        except EOFError:
            print("\nFriday: Goodbye!")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            if friday.config.get("debug"):
                traceback.print_exc()


if __name__ == "__main__":
    main()
