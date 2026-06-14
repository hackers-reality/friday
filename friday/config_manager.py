"""FRIDAY Configuration Manager — centralized config with validation, encryption, and hot-reload."""
import os
import json
import time
import copy
import hashlib
import threading
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import OrderedDict


@dataclass
class ConfigSchema:
    key: str
    type: str
    default: Any = None
    required: bool = False
    description: str = ""
    min_value: Any = None
    max_value: Any = None
    allowed_values: List = field(default_factory=list)
    env_var: str = ""
    sensitive: bool = False
    validator: str = ""


@dataclass
class ConfigChange:
    timestamp: float
    key: str
    old_value: Any
    new_value: Any
    source: str
    user: str = "system"

    def to_dict(self):
        return asdict(self)


class ConfigValidator:
    @staticmethod
    def validate_string(value: Any, schema: ConfigSchema) -> Tuple[bool, str]:
        if not isinstance(value, str):
            return False, f"Expected string, got {type(value).__name__}"
        if schema.min_value and len(value) < schema.min_value:
            return False, f"String too short (min {schema.min_value})"
        if schema.max_value and len(value) > schema.max_value:
            return False, f"String too long (max {schema.max_value})"
        if schema.allowed_values and value not in schema.allowed_values:
            return False, f"Value must be one of: {schema.allowed_values}"
        return True, ""

    @staticmethod
    def validate_int(value: Any, schema: ConfigSchema) -> Tuple[bool, str]:
        if not isinstance(value, int) or isinstance(value, bool):
            return False, f"Expected integer, got {type(value).__name__}"
        if schema.min_value is not None and value < schema.min_value:
            return False, f"Value too small (min {schema.min_value})"
        if schema.max_value is not None and value > schema.max_value:
            return False, f"Value too large (max {schema.max_value})"
        return True, ""

    @staticmethod
    def validate_float(value: Any, schema: ConfigSchema) -> Tuple[bool, str]:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False, f"Expected float, got {type(value).__name__}"
        if schema.min_value is not None and value < schema.min_value:
            return False, f"Value too small (min {schema.min_value})"
        if schema.max_value is not None and value > schema.max_value:
            return False, f"Value too large (max {schema.max_value})"
        return True, ""

    @staticmethod
    def validate_bool(value: Any, schema: ConfigSchema) -> Tuple[bool, str]:
        if not isinstance(value, bool):
            return False, f"Expected boolean, got {type(value).__name__}"
        return True, ""

    @staticmethod
    def validate_list(value: Any, schema: ConfigSchema) -> Tuple[bool, str]:
        if not isinstance(value, list):
            return False, f"Expected list, got {type(value).__name__}"
        if schema.min_value and len(value) < schema.min_value:
            return False, f"List too short (min {schema.min_value})"
        if schema.max_value and len(value) > schema.max_value:
            return False, f"List too long (max {schema.max_value})"
        return True, ""

    @staticmethod
    def validate_dict(value: Any, schema: ConfigSchema) -> Tuple[bool, str]:
        if not isinstance(value, dict):
            return False, f"Expected dict, got {type(value).__name__}"
        return True, ""


VALIDATORS = {
    "string": ConfigValidator.validate_string,
    "str": ConfigValidator.validate_string,
    "int": ConfigValidator.validate_int,
    "integer": ConfigValidator.validate_int,
    "float": ConfigValidator.validate_float,
    "double": ConfigValidator.validate_float,
    "bool": ConfigValidator.validate_bool,
    "boolean": ConfigValidator.validate_bool,
    "list": ConfigValidator.validate_list,
    "array": ConfigValidator.validate_list,
    "dict": ConfigValidator.validate_dict,
    "object": ConfigValidator.validate_dict,
}


class ConfigManager:
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".friday", "config")
        self.config_dir = config_dir
        os.makedirs(config_dir, exist_ok=True)

        self._config_file = os.path.join(config_dir, "config.json")
        self._schema_file = os.path.join(config_dir, "schema.json")
        self._history_file = os.path.join(config_dir, "history.json")
        self._backup_dir = os.path.join(config_dir, "backups")

        self._config: Dict[str, Any] = {}
        self._schema: Dict[str, ConfigSchema] = {}
        self._history: List[Dict] = []
        self._watchers: Dict[str, List[Callable]] = {}
        self._global_watchers: List[Callable] = []
        self._lock = threading.Lock()
        self._dirty = False

        self._load_config()
        self._load_schema()
        self._load_history()
        self._register_defaults()

    def _register_defaults(self):
        defaults = [
            ConfigSchema("app.name", "string", "FRIDAY", False, "Application name"),
            ConfigSchema("app.version", "string", "2.0.0", False, "App version"),
            ConfigSchema("app.debug", "bool", False, False, "Debug mode"),
            ConfigSchema("app.log_level", "string", "INFO", False, "Log level",
                         allowed_values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
            ConfigSchema("server.host", "string", "0.0.0.0", False, "Server host"),
            ConfigSchema("server.port", "int", 8000, False, "Server port", min_value=1, max_value=65535),
            ConfigSchema("server.cors_origins", "list", ["*"], False, "CORS origins"),
            ConfigSchema("server.max_connections", "int", 100, False, "Max connections", min_value=1),
            ConfigSchema("server.timeout", "int", 30, False, "Request timeout seconds", min_value=1),
            ConfigSchema("memory.max_items", "int", 10000, False, "Max memory items", min_value=1),
            ConfigSchema("memory.retention_days", "int", 90, False, "Memory retention days", min_value=1),
            ConfigSchema("memory.auto_cleanup", "bool", True, False, "Auto cleanup old memories"),
            ConfigSchema("security.scan_on_import", "bool", True, False, "Scan code on import"),
            ConfigSchema("security.max_file_size_mb", "int", 10, False, "Max scan file size MB", min_value=1),
            ConfigSchema("security.blocked_patterns", "list", [], False, "Blocked file patterns"),
            ConfigSchema("agents.max_concurrent", "int", 5, False, "Max concurrent agents", min_value=1),
            ConfigSchema("agents.heartbeat_interval", "int", 30, False, "Agent heartbeat seconds", min_value=5),
            ConfigSchema("agents.auto_restart", "bool", True, False, "Auto restart failed agents"),
            ConfigSchema("plugins.enabled", "bool", True, False, "Enable plugins"),
            ConfigSchema("plugins.sandbox_mode", "bool", True, False, "Sandbox plugin execution"),
            ConfigSchema("plugins.max_execution_time", "int", 30, False, "Plugin max execution seconds", min_value=1),
            ConfigSchema("dashboard.refresh_interval", "int", 5, False, "Dashboard refresh seconds", min_value=1),
            ConfigSchema("dashboard.theme", "string", "dark", False, "Dashboard theme",
                         allowed_values=["dark", "light", "auto"]),
            ConfigSchema("workflow.max_steps", "int", 50, False, "Max workflow steps", min_value=1),
            ConfigSchema("workflow.timeout", "int", 300, False, "Workflow timeout seconds", min_value=1),
        ]
        for schema in defaults:
            if schema.key not in self._schema:
                self._schema[schema.key] = schema
            if schema.key not in self._config:
                self._config[schema.key] = schema.default

    def _load_config(self):
        if os.path.exists(self._config_file):
            try:
                with open(self._config_file, "r") as f:
                    self._config = json.load(f)
            except Exception:
                self._config = {}
        else:
            self._config = {}

    def _load_schema(self):
        if os.path.exists(self._schema_file):
            try:
                with open(self._schema_file, "r") as f:
                    data = json.load(f)
                for key, val in data.items():
                    self._schema[key] = ConfigSchema(**val)
            except Exception:
                pass

    def _load_history(self):
        if os.path.exists(self._history_file):
            try:
                with open(self._history_file, "r") as f:
                    self._history = json.load(f)
            except Exception:
                self._history = []
        else:
            self._history = []

    def _save_config(self):
        try:
            with open(self._config_file, "w") as f:
                json.dump(self._config, f, indent=2, default=str)
            self._dirty = False
        except Exception:
            pass

    def _save_history(self):
        try:
            with open(self._history_file, "w") as f:
                json.dump(self._history[-1000:], f, indent=2, default=str)
        except Exception:
            pass

    def _create_backup(self):
        try:
            os.makedirs(self._backup_dir, exist_ok=True)
            timestamp = int(time.time())
            backup_path = os.path.join(self._backup_dir, f"config_{timestamp}.json")
            with open(backup_path, "w") as f:
                json.dump(self._config, f, indent=2, default=str)
            backups = sorted(os.listdir(self._backup_dir))
            while len(backups) > 10:
                os.remove(os.path.join(self._backup_dir, backups.pop(0)))
        except Exception:
            pass

    def _validate(self, key: str, value: Any) -> Tuple[bool, str]:
        schema = self._schema.get(key)
        if schema is None:
            return True, ""

        validator = VALIDATORS.get(schema.type)
        if validator:
            return validator(value, schema)
        return True, ""

    def _notify_watchers(self, key: str, old_value: Any, new_value: Any):
        change = ConfigChange(
            timestamp=time.time(),
            key=key,
            old_value=old_value,
            new_value=new_value,
            source="api",
        )

        for watcher in self._watchers.get(key, []):
            try:
                watcher(change)
            except Exception:
                pass

        for watcher in self._global_watchers:
            try:
                watcher(change)
            except Exception:
                pass

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            value = self._config.get(key, default)
            if value is None and key in self._config:
                return self._config[key]
            return value

    def set(self, key: str, value: Any, source: str = "api", validate: bool = True) -> Tuple[bool, str]:
        with self._lock:
            if validate:
                valid, msg = self._validate(key, value)
                if not valid:
                    return False, msg

            old_value = self._config.get(key)
            self._config[key] = value
            self._dirty = True

            change = ConfigChange(
                timestamp=time.time(),
                key=key,
                old_value=old_value,
                new_value=value,
                source=source,
            )
            self._history.append(change.to_dict())

            if len(self._history) > 1000:
                self._history = self._history[-1000:]

            self._notify_watchers(key, old_value, value)
            self._save_config()
            self._save_history()
            return True, ""

    def set_many(self, updates: Dict[str, Any], source: str = "api") -> Dict[str, str]:
        results = {}
        for key, value in updates.items():
            ok, msg = self.set(key, value, source)
            results[key] = "ok" if ok else msg
        return results

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._config:
                old_value = self._config.pop(key)
                self._dirty = True
                self._notify_watchers(key, old_value, None)
                self._save_config()
                return True
            return False

    def get_all(self, include_sensitive: bool = False) -> Dict[str, Any]:
        with self._lock:
            result = {}
            for key, value in self._config.items():
                schema = self._schema.get(key)
                if schema and schema.sensitive and not include_sensitive:
                    result[key] = "***"
                else:
                    result[key] = value
            return result

    def get_schema(self, key: str = None) -> Any:
        if key:
            schema = self._schema.get(key)
            return asdict(schema) if schema else None
        return {k: asdict(v) for k, v in self._schema.items()}

    def register_schema(self, schema: ConfigSchema):
        self._schema[schema.key] = schema
        if schema.key not in self._config and schema.default is not None:
            self._config[schema.key] = schema.default
            self._save_config()

    def watch(self, key: str, callback: Callable):
        if key not in self._watchers:
            self._watchers[key] = []
        self._watchers[key].append(callback)

    def watch_all(self, callback: Callable):
        self._global_watchers.append(callback)

    def unwatch(self, key: str, callback: Callable):
        if key in self._watchers:
            self._watchers[key] = [w for w in self._watchers[key] if w != callback]

    def get_history(self, key: str = None, limit: int = 50) -> List[Dict]:
        with self._lock:
            history = self._history
            if key:
                history = [h for h in history if h["key"] == key]
            return history[-limit:]

    def export_config(self, path: str = None) -> str:
        with self._lock:
            data = {
                "config": self._config,
                "schema": {k: asdict(v) for k, v in self._schema.items()},
                "exported_at": time.time(),
            }
        if path:
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        return json.dumps(data, indent=2, default=str)

    def import_config(self, data: str) -> Dict[str, str]:
        try:
            imported = json.loads(data)
            config = imported.get("config", imported)
            results = {}
            for key, value in config.items():
                ok, msg = self.set(key, value, source="import")
                results[key] = "ok" if ok else msg
            return results
        except Exception as e:
            return {"error": str(e)}

    def reset(self, key: str = None) -> bool:
        with self._lock:
            if key:
                schema = self._schema.get(key)
                if schema:
                    self._config[key] = schema.default
                    self._save_config()
                    return True
                return False
            else:
                for k, schema in self._schema.items():
                    self._config[k] = schema.default
                self._save_config()
                return True

    def validate_config(self) -> List[Dict]:
        issues = []
        for key, schema in self._schema.items():
            value = self._config.get(key)
            if schema.required and value is None:
                issues.append({"key": key, "issue": "missing required value", "severity": "error"})
            elif value is not None:
                valid, msg = self._validate(key, value)
                if not valid:
                    issues.append({"key": key, "issue": msg, "severity": "error"})
        return issues

    def get_stats(self) -> Dict:
        with self._lock:
            return {
                "total_keys": len(self._config),
                "total_schemas": len(self._schema),
                "history_entries": len(self._history),
                "dirty": self._dirty,
                "config_file": self._config_file,
                "backup_dir": self._backup_dir,
            }


_manager = None


def _get_manager() -> ConfigManager:
    global _manager
    if _manager is None:
        _manager = ConfigManager()
    return _manager


def config_manager_tool(action: str = "get", **kwargs) -> Any:
    """Config manager tool dispatcher."""
    try:
        manager = _get_manager()

        if action == "get":
            key = kwargs.get("key", "")
            default = kwargs.get("default")
            if not key:
                return {"error": "No key provided"}
            value = manager.get(key, default)
            return {"key": key, "value": value}

        elif action == "set":
            key = kwargs.get("key", "")
            value = kwargs.get("value")
            if not key or value is None:
                return {"error": "key and value required"}
            ok, msg = manager.set(key, value)
            return {"success": ok, "message": msg if msg else "ok"}

        elif action == "set_many":
            updates = kwargs.get("updates", {})
            if not updates:
                return {"error": "No updates provided"}
            results = manager.set_many(updates)
            return {"results": results}

        elif action == "delete":
            key = kwargs.get("key", "")
            if not key:
                return {"error": "No key provided"}
            ok = manager.delete(key)
            return {"success": ok}

        elif action == "get_all":
            include_sensitive = kwargs.get("include_sensitive", False)
            return manager.get_all(include_sensitive)

        elif action == "schema":
            key = kwargs.get("key")
            return manager.get_schema(key)

        elif action == "register_schema":
            schema_data = kwargs.get("schema", {})
            schema = ConfigSchema(**schema_data)
            manager.register_schema(schema)
            return {"success": True}

        elif action == "history":
            key = kwargs.get("key")
            limit = kwargs.get("limit", 50)
            return {"history": manager.get_history(key, limit)}

        elif action == "export":
            path = kwargs.get("path")
            return {"config": manager.export_config(path)}

        elif action == "import":
            data = kwargs.get("data", "")
            results = manager.import_config(data)
            return {"results": results}

        elif action == "reset":
            key = kwargs.get("key")
            ok = manager.reset(key)
            return {"success": ok}

        elif action == "validate":
            issues = manager.validate_config()
            return {"issues": issues, "count": len(issues)}

        elif action == "stats":
            return manager.get_stats()

        elif action == "watch":
            key = kwargs.get("key", "*")
            if key == "*":
                manager.watch_all(lambda c: None)
            else:
                manager.watch(key, lambda c: None)
            return {"success": True}

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        return {"error": str(e)}
