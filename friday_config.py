"""
Friday Config - Configuration management.
Configuration files, environment variables, settings management.
"""
from __future__ import annotations

import os
import sys
import json
import configparser
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime


# ─── Config File Formats ────────────────────────────#

class ConfigManager:
    """Manage configuration in various formats."""
    
    def __init__(self, config_dir: str = None):
        self.config_dir = Path(config_dir) if config_dir else Path.home() / ".friday"
        self.config_dir.mkdir(exist_ok=True)
        self.configs: Dict[str, Dict] = {}
        
    def load_json(self, name: str, file_path: str = None) -> Dict[str, Any]:
        """Load JSON config file."""
        file_path = file_path or str(self.config_dir / f"{name}.json")
        
        try:
            with open(file_path, "r") as f:
                config = json.load(f)
            
            self.configs[name] = config
            return {"success": True, "config": config, "source": file_path}
        except FileNotFoundError:
            return {"success": False, "error": f"Config file not found: {file_path}"}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def save_json(self, name: str, config: Dict, file_path: str = None) -> Dict[str, Any]:
        """Save config as JSON."""
        file_path = file_path or str(self.config_dir / f"{name}.json")
        
        try:
            with open(file_path, "w") as f:
                json.dump(config, f, indent=2)
            
            self.configs[name] = config
            return {"success": True, "path": file_path}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def load_ini(self, name: str, file_path: str = None) -> Dict[str, Any]:
        """Load INI config file."""
        file_path = file_path or str(self.config_dir / f"{name}.ini")
        
        try:
            parser = configparser.ConfigParser()
            parser.read(file_path)
            
            config = {}
            for section in parser.sections():
                config[section] = dict(parser.items(section))
            
            self.configs[name] = config
            return {"success": True, "config": config, "source": file_path}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def save_ini(self, name: str, config: Dict, file_path: str = None) -> Dict[str, Any]:
        """Save config as INI."""
        file_path = file_path or str(self.config_dir / f"{name}.ini")
        
        try:
            parser = configparser.ConfigParser()
            
            for section, values in config.items():
                parser[section] = values
            
            with open(file_path, "w") as f:
                parser.write(f)
            
            self.configs[name] = config
            return {"success": True, "path": file_path}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get(self, config_name: str, key: str = None, default: Any = None) -> Any:
        """Get config value."""
        if config_name not in self.configs:
            # Try to load
            result = self.load_json(config_name)
            if not result.get("success"):
                result = self.load_ini(config_name)
                if not result.get("success"):
                    return default
        
        config = self.configs.get(config_name)
        if not config:
            return default
        
        if key:
            # Support dot notation: section.key
            parts = key.split(".")
            value = config
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return default
            return value
        return config
    
    def set(self, config_name: str, key: str, value: Any) -> Dict[str, Any]:
        """Set config value."""
        if config_name not in self.configs:
            self.configs[config_name] = {}
        
        config = self.configs[config_name]
        
        # Support dot notation
        parts = key.split(".")
        current = config
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
        
        # Auto-save
        file_path = self.config_dir / f"{config_name}.json"
        if file_path.exists():
            return self.save_json(config_name, config)
        
        file_path = self.config_dir / f"{config_name}.ini"
        if file_path.exists():
            return self.save_ini(config_name, config)
        
        return {"success": True}


# ─── Environment Variables ────────────────────────────#

class EnvManager:
    """Manage environment variables."""
    
    @staticmethod
    def get(var_name: str, default: Any = None) -> Any:
        """Get environment variable."""
        return os.environ.get(var_name, default)
    
    @staticmethod
    def set(var_name: str, value: str, permanent: bool = False) -> Dict[str, Any]:
        """Set environment variable."""
        try:
            os.environ[var_name] = value
            
            if permanent and os.name == "nt":  # Windows
                import subprocess
                subprocess.run(f"setx {var_name} \"{value}\"", shell=True)
            
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def load_env_file(file_path: str = ".env") -> Dict[str, Any]:
        """Load .env file."""
        if not os.path.exists(file_path):
            return {"success": False, "error": f"File not found: {file_path}"}
        
        loaded = {}
        try:
            with open(file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip("'\"")
                        os.environ[key] = value
                        loaded[key] = value
            
            return {"success": True, "loaded": loaded, "count": len(loaded)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def list_all() -> Dict[str, str]:
        """List all environment variables."""
        return dict(os.environ)


# ─── Settings Manager ────────────────────────────#

class SettingsManager:
    """Manage application settings."""
    
    def __init__(self, config_manager: ConfigManager = None):
        self.config = config_manager or ConfigManager()
        self.settings: Dict[str, Any] = {}
        self.defaults: Dict[str, Any] = {}
        
    def register_defaults(self, defaults: Dict[str, Any]):
        """Register default settings."""
        self.defaults.update(defaults)
        # Apply defaults to settings
        for key, value in defaults.items():
            if key not in self.settings:
                self.settings[key] = value
    
    def load_settings(self, config_name: str = "settings"):
        """Load settings from config."""
        config = self.config.get(config_name)
        if config:
            self.settings.update(config)
        
        # Apply defaults for missing
        for key, value in self.defaults.items():
            if key not in self.settings:
                self.settings[key] = value
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting."""
        return self.settings.get(key, self.defaults.get(key, default))
    
    def set_setting(self, key: str, value: Any, save: bool = True):
        """Set a setting."""
        self.settings[key] = value
        
        if save:
            self.config.set("settings", key, value)
    
    def save_settings(self, config_name: str = "settings"):
        """Save settings to config."""
        return self.config.save_json(config_name, self.settings)
    
    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        self.settings = self.defaults.copy()


# ─── Profile Manager ────────────────────────────#

class ProfileManager:
    """Manage user profiles."""
    
    def __init__(self, config_dir: str = None):
        self.config_manager = ConfigManager(config_dir)
        self.current_profile: Optional[str] = None
        self.profiles: Dict[str, Dict] = {}
        
    def create_profile(self, name: str, settings: Dict = None) -> Dict[str, Any]:
        """Create a new profile."""
        if name in self.profiles:
            return {"success": False, "error": f"Profile '{name}' already exists."}
        
        self.profiles[name] = settings or {}
        self.config.save_json(f"profile_{name}", self.profiles[name])
        
        return {"success": True, "profile": name}
    
    def load_profile(self, name: str) -> Dict[str, Any]:
        """Load a profile."""
        result = self.config_manager.load_json(f"profile_{name}")
        
        if result["success"]:
            self.current_profile = name
            self.profiles[name] = result["config"]
            return {"success": True, "profile": name, "settings": result["config"]}
        else:
            return result
    
    def switch_profile(self, name: str) -> Dict[str, Any]:
        """Switch to a profile."""
        if name not in self.profiles:
            # Try to load
            result = self.load_profile(name)
            if not result["success"]:
                return result
        
        self.current_profile = name
        return {"success": True, "profile": name}
    
    def delete_profile(self, name: str) -> Dict[str, Any]:
        """Delete a profile."""
        if name in self.profiles:
            del self.profiles[name]
            
        file_path = self.config_manager.config_dir / f"profile_{name}.json"
        if file_path.exists():
            file_path.unlink()
        
        if self.current_profile == name:
            self.current_profile = None
        
        return {"success": True}
    
    def list_profiles(self) -> List[str]:
        """List all profiles."""
        return list(self.profiles.keys())


# ─── Config Tool for Friday ────────────────────────────#

def config_tool(
    action: str = "status",
    name: str = None,
    params: Dict = None,
) -> str:
    """
    Friday tool for configuration management.
    Actions: status, load, save, get, set, env_get, env_set,
            settings_load, settings_save, profile_create, profile_switch
    """
    params = params or {}
    
    if action == "status":
        config_mgr = ConfigManager()
        env_mgr = EnvManager()
        
        lines = ["### CONFIG STATUS", ""]
        lines.append(f"**Config Directory**: {config_mgr.config_dir}")
        lines.append(f"**Loaded Configs**: {len(config_mgr.configs)}")
        lines.append(f"**Environment Variables**: {len(env_mgr.list_all())}")
        return "\n".join(lines)
    
    if action == "load":
        if not name:
            return "❌ Config name required."
        config_mgr = ConfigManager()
        result = config_mgr.load_json(name)
        if result["success"]:
            return f"### CONFIG LOAD\n\n✅ Loaded from {result['source']}\n{json.dumps(result['config'], indent=2)[:500]}"
        else:
            # Try INI
            result = config_mgr.load_ini(name)
            if result["success"]:
                return f"### CONFIG LOAD\n\n✅ Loaded from {result['source']}\n{json.dumps(result['config'], indent=2)[:500]}"
            else:
                return f"❌ Load error: {result.get('error', 'Unknown')}"
    
    if action == "save":
        if not name or "config" not in params:
            return "❌ Name and config required."
        config_mgr = ConfigManager()
        result = config_mgr.save_json(name, params["config"])
        if result["success"]:
            return f"### CONFIG SAVE\n\n✅ Saved to {result['path']}"
        else:
            return f"❌ Save error: {result.get('error', 'Unknown')}"
    
    if action == "get":
        if not name:
            return "❌ Config name required."
        config_mgr = ConfigManager()
        key = params.get("key")
        value = config_mgr.get(name, key)
        return f"### CONFIG GET\n\n**{name}.{key or ''}**: {json.dumps(value, indent=2)[:500]}"
    
    if action == "set":
        if not name or "key" not in params or "value" not in params:
            return "❌ Name, key, and value required."
        config_mgr = ConfigManager()
        result = config_mgr.set(name, params["key"], params["value"])
        if result["success"]:
            return f"### CONFIG SET\n\n✅ Set {name}.{params['key']} = {json.dumps(params['value'])[:100]}"
        else:
            return f"❌ Set error: {result.get('error', 'Unknown')}"
    
    if action == "env_get":
        if not name:
            return "❌ Variable name required."
        env_mgr = EnvManager()
        value = env_mgr.get(name)
        return f"### ENV GET\n\n**{name}**: {value or '(not set)'}"
    
    if action == "env_set":
        if not name or "value" not in params:
            return "❌ Variable name and value required."
        env_mgr = EnvManager()
        result = env_mgr.set(name, params["value"], permanent=params.get("permanent", False))
        if result["success"]:
            return f"### ENV SET\n\n✅ Set {name} = {params['value'][:50]}..."
        else:
            return f"❌ Set error: {result.get('error', 'Unknown')}"
    
    if action == "settings_load":
        config_mgr = ConfigManager()
        settings_mgr = SettingsManager(config_mgr)
        settings_mgr.load_settings(name or "settings")
        return f"### SETTINGS LOAD\n\n✅ Loaded settings ({len(settings_mgr.settings)} settings)"
    
    if action == "settings_save":
        config_mgr = ConfigManager()
        settings_mgr = SettingsManager(config_mgr)
        result = settings_mgr.save_settings(name or "settings")
        if result["success"]:
            return f"### SETTINGS SAVE\n\n✅ Saved settings"
        else:
            return f"❌ Save error: {result.get('error', 'Unknown')}"
    
    if action == "profile_create":
        if not name:
            return "❌ Profile name required."
        profile_mgr = ProfileManager()
        settings = params.get("settings", {})
        result = profile_mgr.create_profile(name, settings)
        if result["success"]:
            return f"### PROFILE CREATE\n\n✅ Created profile: {name}"
        else:
            return f"❌ Create error: {result.get('error', 'Unknown')}"
    
    if action == "profile_switch":
        if not name:
            return "❌ Profile name required."
        profile_mgr = ProfileManager()
        result = profile_mgr.switch_profile(name)
        if result["success"]:
            return f"### PROFILE SWITCH\n\n✅ Switched to profile: {name}"
        else:
            return f"❌ Switch error: {result.get('error', 'Unknown')}"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Friday Config...\n")
    
    # Test config
    print("--- Config Manager ---")
    print(config_tool("status"))
    
    # Test env
    print("\n--- Environment ---")
    print(config_tool("env_get", name="HOME"))
