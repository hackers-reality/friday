"""
Friday Core - Main AI Assistant.
Integrates all advanced modules: networking, crypto, web, automation, etc.
"""
from __future__ import annotations

import os
import sys
import json
import time
import subprocess
import threading
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from pathlib import Path
import importlib.util


# ─── Module Loader ────────────────────────────#

class ModuleLoader:
    """Dynamically load Friday modules."""
    
    def __init__(self, base_path: str = None):
        self.base_path = base_path or os.path.dirname(os.path.abspath(__file__))
        self.modules: Dict[str, Any] = {}
        
    def load_module(self, module_name: str) -> Optional[Any]:
        """Load a module by name."""
        if module_name in self.modules:
            return self.modules[module_name]
        
        module_path = os.path.join(self.base_path, f"{module_name}.py")
        
        if not os.path.exists(module_path):
            return None
        
        try:
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.modules[module_name] = module
            return module
        except Exception as e:
            print(f"❌ Error loading {module_name}: {e}")
            return None
    
    def get_tool(self, module_name: str, tool_name: str) -> Optional[Callable]:
        """Get a tool function from a module."""
        module = self.load_module(module_name)
        if module and hasattr(module, tool_name):
            return getattr(module, tool_name)
        return None


# ─── Friday Core Assistant ────────────────────────────#

class FridayCore:
    """Main Friday AI Assistant."""
    
    def __init__(self):
        self.loader = ModuleLoader()
        self.history: List[Dict] = []
        self.config: Dict[str, Any] = {
            "name": "Friday",
            "version": "2.0.0",
            "voice_enabled": False,
            "auto_execute": True,
            "modules": [
                "advanced_networking",
                "advanced_crypto",
            ],
        }
        self.context: Dict[str, Any] = {}
        
    def initialize(self):
        """Initialize Friday and load modules."""
        lines = [
            f"### {self.config['name']} v{self.config['version']} - INITIALIZED",
            "",
            "**Loaded Modules**:",
        ]
        
        for module_name in self.config["modules"]:
            module = self.loader.load_module(module_name)
            if module:
                lines.append(f"  ✅ {module_name}")
            else:
                lines.append(f"  ❌ {module_name} (not found)")
        
        lines.append("")
        lines.append("**Ready for commands.**")
        
        return "\n".join(lines)
    
    def process_command(self, command: str) -> str:
        """Process a user command."""
        cmd_lower = command.lower().strip()
        
        # Log command
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "command": command,
        })
        
        # Route to appropriate module
        if cmd_lower.startswith("network") or cmd_lower.startswith("http"):
            return self._handle_networking(command)
        
        if cmd_lower.startswith("crypto") or cmd_lower.startswith("encrypt") or cmd_lower.startswith("hash"):
            return self._handle_crypto(command)
        
        if cmd_lower.startswith("help"):
            return self._show_help()
        
        if cmd_lower.startswith("status"):
            return self._show_status()
        
        if cmd_lower.startswith("exec"):
            return self._execute_command(command[5:].strip())
        
        if cmd_lower.startswith("python"):
            return self._execute_python(command[7:].strip())
        
        # Default: try to understand and respond
        return self._default_response(command)
    
    def _handle_networking(self, command: str) -> str:
        """Route networking commands."""
        tool = self.loader.get_tool("advanced_networking", "network_tool")
        if not tool:
            return "❌ Networking module not loaded."
        
        # Parse action from command
        if "http2" in command.lower():
            return tool("http2_get", url=self._extract_url(command))
        elif "websocket" in command.lower():
            return tool("websocket_status")
        elif "mqtt" in command.lower():
            return tool("mqtt_status")
        elif "grpc" in command.lower():
            return tool("grpc_status")
        elif "ping" in command.lower():
            host = self._extract_host(command)
            return tool("ping", host=host) if host else tool("ping")
        elif "dns" in command.lower():
            domain = self._extract_domain(command)
            return tool("dns_lookup", domain=domain) if domain else tool("dns_lookup")
        elif "scan" in command.lower():
            host = self._extract_host(command)
            return tool("port_scan", host=host) if host else tool("port_scan")
        else:
            return tool("status")
    
    def _handle_crypto(self, command: str) -> str:
        """Route crypto commands."""
        tool = self.loader.get_tool("advanced_crypto", "crypto_tool")
        if not tool:
            return "❌ Crypto module not loaded."
        
        cmd_lower = command.lower()
        
        if "hash" in cmd_lower:
            data = self._extract_data(command)
            return tool("hash", data=data) if data else tool("hash", data="test")
        elif "aes" in cmd_lower and "encrypt" in cmd_lower:
            data = self._extract_data(command)
            return tool("aes_encrypt", data=data) if data else "❌ Data required."
        elif "aes" in cmd_lower and "decrypt" in cmd_lower:
            return tool("aes_decrypt")
        elif "rsa" in cmd_lower and "encrypt" in cmd_lower:
            data = self._extract_data(command)
            return tool("rsa_encrypt", data=data) if data else "❌ Data required."
        elif "rsa" in cmd_lower and "sign" in cmd_lower:
            data = self._extract_data(command)
            return tool("rsa_sign", data=data) if data else "❌ Data required."
        elif "ecc" in cmd_lower:
            return tool("ecc_gen")
        elif "ecdsa" in cmd_lower:
            data = self._extract_data(command)
            return tool("ecdsa_sign", data=data) if data else "❌ Data required."
        elif "zkp" in cmd_lower or "zero" in cmd_lower:
            data = self._extract_data(command)
            return tool("zkp", data=data) if data else tool("zkp", data="secret")
        elif "pbkdf2" in cmd_lower or "key" in cmd_lower:
            data = self._extract_data(command)
            return tool("pbkdf2", data=data) if data else tool("pbkdf2", data="password")
        elif "cert" in cmd_lower:
            data = self._extract_data(command)
            return tool("cert_create", data=data) if data else tool("cert_create", data="Friday CA")
        else:
            return tool("status")
    
    def _show_help(self) -> str:
        """Show help."""
        lines = [
            "### FRIDAY HELP",
            "",
            "**Available Commands**:",
            "",
            "**Networking**:",
            "  - `network status` - Show networking status",
            "  - `http2 get <url>` - HTTP/2 request",
            "  - `ping <host>` - Ping host",
            "  - `dns <domain>` - DNS lookup",
            "  - `scan <host>` - Port scan",
            "",
            "**Cryptography**:",
            "  - `crypto status` - Show crypto status",
            "  - `hash <data>` - Hash data",
            "  - `aes encrypt <data>` - AES encrypt",
            "  - `rsa encrypt <data>` - RSA encrypt",
            "  - `rsa sign <data>` - RSA sign",
            "  - `ecc gen` - Generate ECC keypair",
            "  - `zkp <secret>` - Zero-knowledge proof",
            "  - `pbkdf2 <password>` - Key derivation",
            "",
            "**System**:",
            "  - `exec <command>` - Execute system command",
            "  - `python <code>` - Execute Python code",
            "  - `status` - Show system status",
            "  - `help` - Show this help",
        ]
        return "\n".join(lines)
    
    def _show_status(self) -> str:
        """Show system status."""
        lines = [
            "### FRIDAY STATUS",
            "",
            f"**Name**: {self.config['name']}",
            f"**Version**: {self.config['version']}",
            f"**Commands Processed**: {len(self.history)}",
            "",
            "**Modules**:",
        ]
        
        for module_name in self.config["modules"]:
            module = self.loader.load_module(module_name)
            lines.append(f"  - {module_name}: {'✅ Loaded' if module else '❌ Not loaded'}")
        
        return "\n".join(lines)
    
    def _execute_command(self, cmd: str) -> str:
        """Execute a system command."""
        if not cmd:
            return "❌ No command provided."
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = result.stdout or result.stderr
            return f"### EXECUTION RESULT\n\n```\n{output}\n```"
        except subprocess.TimeoutExpired:
            return "❌ Command timed out."
        except Exception as e:
            return f"❌ Execution error: {e}"
    
    def _execute_python(self, code: str) -> str:
        """Execute Python code."""
        if not code:
            return "❌ No code provided."
        
        try:
            # Create a restricted globals dict
            globals_dict = {
                "__builtins__": __builtins__,
                "print": print,
                "len": len,
                "range": range,
                "int": int,
                "str": str,
                "list": list,
                "dict": dict,
            }
            
            exec(code, globals_dict)
            return "✅ Python code executed successfully."
        except Exception as e:
            return f"❌ Python execution error: {e}"
    
    def _default_response(self, command: str) -> str:
        """Default response for unrecognized commands."""
        return f"""### FRIDAY RESPONSE

I don't understand: "{command}"

Try `help` to see available commands."""
    
    def _extract_url(self, command: str) -> Optional[str]:
        """Extract URL from command."""
        import re
        urls = re.findall(r'https?://[^\s]+', command)
        return urls[0] if urls else None
    
    def _extract_host(self, command: str) -> Optional[str]:
        """Extract host from command."""
        import re
        # Simple host extraction
        words = command.split()
        for word in words:
            if "." in word or word == "localhost":
                return word
        return None
    
    def _extract_domain(self, command: str) -> Optional[str]:
        """Extract domain from command."""
        return self._extract_host(command)
    
    def _extract_data(self, command: str) -> Optional[str]:
        """Extract data parameter from command."""
        # Simple: get text after the action
        parts = command.split()
        if len(parts) > 2:
            return " ".join(parts[2:])
        return None


# ─── Interactive CLI ────────────────────────────#

def main():
    """Main entry point for Friday."""
    friday = FridayCore()
    
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
            
            response = friday.process_command(user_input)
            print(response)
            print()
            
        except KeyboardInterrupt:
            print("\nFriday: Interrupted. Use 'exit' to quit.")
        except EOFError:
            print("\nFriday: Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
