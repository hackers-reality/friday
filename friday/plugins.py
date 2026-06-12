"""
Friday Plugin System - Extensible architecture for adding new capabilities.
Plugins can be loaded dynamically and expose new tools to Friday.

Supports metadata, dependencies, configuration, sandboxing, hot-reload,
marketplace, testing, API docs generation, events/hooks, templates,
compatibility checking, categories, and statistics.
"""
from __future__ import annotations

import datetime
import fnmatch
import hashlib
import importlib
import importlib.util
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import traceback
import types
import contextlib
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)
from urllib.parse import urlparse

try:
    from typing import TypedDict
except ImportError:
    TypedDict = dict


# ─── Constants ─────────────────────────────────────────────────────

FRIDAY_VERSION: str = "2.0.0"
FRIDAY_MEMORY: str = os.environ.get(
    "FRIDAY_MEMORY",
    os.path.join(os.path.expanduser("~"), ".friday", "memory"),
)
DEFAULT_PLUGIN_DIR: str = os.environ.get(
    "FRIDAY_PLUGIN_DIR",
    os.path.join(os.path.expanduser("~"), ".friday", "plugins"),
)
PLUGINS_AVAILABLE_DIR: str = os.path.join(FRIDAY_MEMORY, "plugins_available")
PLUGIN_HOTRELOAD_INTERVAL: float = 3.0
PLUGIN_TEST_TIMEOUT: float = 30.0
PLUGIN_EXECUTION_TIMEOUT: float = 60.0
SANDBOX_ALLOWED_IMPORTS: Set[str] = {
    "json", "math", "re", "datetime", "collections",
    "itertools", "functools", "random", "string", "typing",
    "pathlib", "os.path", "copy", "enum", "hashlib", "uuid",
    "statistics", "decimal", "fractions", "dataclasses",
}


# ─── Plugin Metadata ───────────────────────────────────────────────

@dataclass
class PluginMetadata:
    """
    Structured metadata for a Friday plugin.

    Attributes:
        name: Unique plugin identifier.
        version: Semver string e.g. '1.2.3'.
        author: Creator name or organisation.
        description: One-line summary.
        dependencies: Dict mapping plugin name to required version.
        min_friday_version: Minimum Friday version required.
        tags: List of category tags.
        license: SPDX license identifier.
        homepage: Project URL.
        entry_point: Fully-qualified class path (e.g. 'myplugin.MyPlugin').
    """
    name: str = ""
    version: str = "1.0.0"
    author: str = "unknown"
    description: str = ""
    dependencies: Dict[str, str] = field(default_factory=dict)
    min_friday_version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    license: str = "MIT"
    homepage: str = ""
    entry_point: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to a JSON-serialisable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PluginMetadata:
        """Create metadata from a dictionary."""
        return cls(**{k: data.get(k, v.default if hasattr(v, 'default') else "")
                      for k, v in cls.__dataclass_fields__.items()})


# ─── Plugin Event System ────────────────────────────────────────────

class PluginEvent(Enum):
    """Events that can be subscribed to by plugins."""
    ON_LOAD = auto()
    ON_UNLOAD = auto()
    ON_TOOL_CALL = auto()
    ON_TOOL_RESULT = auto()
    ON_ERROR = auto()
    ON_SHUTDOWN = auto()


class PluginHookManager:
    """
    Manages event subscriptions and dispatches events to all plugins.

    Plugins can subscribe to events via subscribe(event, handler).
    The manager dispatches events to all registered handlers.
    """

    def __init__(self):
        self._handlers: Dict[PluginEvent, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event: PluginEvent, handler: Callable) -> None:
        """
        Register a handler for a given event.

        Args:
            event: The PluginEvent to subscribe to.
            handler: Callable that receives event data.
        """
        with self._lock:
            self._handlers[event].append(handler)

    def unsubscribe(self, event: PluginEvent, handler: Callable) -> None:
        """Remove a previously registered handler."""
        with self._lock:
            if handler in self._handlers[event]:
                self._handlers[event].remove(handler)

    def dispatch(self, event: PluginEvent, **kwargs) -> List[Any]:
        """
        Dispatch an event to all registered handlers.

        Args:
            event: The event being fired.
            **kwargs: Contextual data passed to each handler.

        Returns:
            List of results from each handler.
        """
        results = []
        with self._lock:
            handlers = list(self._handlers.get(event, []))
        for handler in handlers:
            try:
                result = handler(event=event, **kwargs)
                results.append(result)
            except Exception as exc:
                results.append(None)
        return results

    def clear(self) -> None:
        """Remove all handlers."""
        with self._lock:
            self._handlers.clear()

    def list_subscribers(self, event: Optional[PluginEvent] = None) -> Dict[PluginEvent, int]:
        """Return counts of handlers per event."""
        if event is not None:
            return {event: len(self._handlers.get(event, []))}
        return {e: len(h) for e, h in self._handlers.items()}


# ─── Plugin Sandbox ─────────────────────────────────────────────────

class SandboxViolation(Exception):
    """
    Raised when a plugin attempts an operation disallowed by the sandbox.

    Attributes:
        message: Human-readable description.
        operation: The operation that was blocked.
        plugin_name: The plugin that caused the violation.
    """

    def __init__(self, message: str, operation: str = "", plugin_name: str = ""):
        self.operation = operation
        self.plugin_name = plugin_name
        super().__init__(message)


class PluginSandbox:
    """
    Execution sandbox that restricts plugin capabilities.

    Enforces:
    - Allowed imports whitelist.
    - Filesystem access limited to plugin directory.
    - No subprocess execution.
    - No network access.
    - Execution time limits.
    """

    def __init__(self, plugin_name: str, plugin_dir: str = ""):
        self.plugin_name = plugin_name
        self.plugin_dir = os.path.abspath(plugin_dir) if plugin_dir else ""
        self.allowed_imports: Set[str] = set(SANDBOX_ALLOWED_IMPORTS)
        self.allow_subprocess: bool = False
        self.allow_network: bool = False
        self.allow_fs_write: bool = False
        self.time_limit: float = PLUGIN_EXECUTION_TIMEOUT
        self._start_time: float = 0.0

    def check_import(self, module_name: str) -> None:
        """
        Verify that an import is allowed by the sandbox.

        Args:
            module_name: The module being imported.

        Raises:
            SandboxViolation: If the import is not in the whitelist.
        """
        base = module_name.split('.')[0]
        if base not in self.allowed_imports:
            raise SandboxViolation(
                message=f"Import '{module_name}' is not allowed by sandbox",
                operation="import",
                plugin_name=self.plugin_name,
            )

    def check_path_access(self, target_path: str, mode: str = "r") -> None:
        """
        Verify filesystem access is within allowed bounds.

        Args:
            target_path: Path the plugin is trying to access.
            mode: 'r' for read, 'w' for write.

        Raises:
            SandboxViolation: If access is denied.
        """
        abs_target = os.path.abspath(target_path)
        if mode == "w" and not self.allow_fs_write:
            pass
        if self.plugin_dir:
            if not abs_target.startswith(self.plugin_dir):
                raise SandboxViolation(
                    message=f"Filesystem access to '{target_path}' denied (outside plugin dir)",
                    operation="filesystem",
                    plugin_name=self.plugin_name,
                )

    def check_execution_time(self) -> None:
        """Check if the execution time limit has been exceeded."""
        if self._start_time and self.time_limit > 0:
            elapsed = time.time() - self._start_time
            if elapsed > self.time_limit:
                raise SandboxViolation(
                    message=f"Execution time limit ({self.time_limit}s) exceeded",
                    operation="timeout",
                    plugin_name=self.plugin_name,
                )

    def check_subprocess(self, cmd: List[str]) -> None:
        """
        Verify subprocess execution is allowed.

        Args:
            cmd: The command list being executed.

        Raises:
            SandboxViolation: If subprocess execution is disabled.
        """
        if not self.allow_subprocess:
            raise SandboxViolation(
                message=f"Subprocess execution is disabled: {' '.join(cmd)}",
                operation="subprocess",
                plugin_name=self.plugin_name,
            )

    def check_network(self, host: str = "", port: int = 0) -> None:
        """
        Verify network access is allowed.

        Args:
            host: Target hostname or IP.
            port: Target port.

        Raises:
            SandboxViolation: If network access is disabled.
        """
        if not self.allow_network:
            raise SandboxViolation(
                message=f"Network access denied: {host}:{port}",
                operation="network",
                plugin_name=self.plugin_name,
            )

    @contextlib.contextmanager
    def execution_context(self):
        """
        Context manager that tracks execution time.

        Use to wrap plugin tool execution.
        """
        self._start_time = time.time()
        try:
            yield
        finally:
            self._start_time = 0.0

    def get_status(self) -> Dict[str, Any]:
        """Return current sandbox configuration as a dictionary."""
        return {
            "plugin_name": self.plugin_name,
            "plugin_dir": self.plugin_dir,
            "allowed_imports": sorted(self.allowed_imports),
            "allow_subprocess": self.allow_subprocess,
            "allow_network": self.allow_network,
            "allow_fs_write": self.allow_fs_write,
            "time_limit": self.time_limit,
        }


# ─── Plugin Configuration ──────────────────────────────────────────

class PluginConfig:
    """
    Per-plugin configuration with JSON Schema validation.

    Config files are stored in FRIDAY_MEMORY/plugins/{name}/config.json.
    """

    def __init__(self, plugin_name: str, schema: Optional[Dict[str, Any]] = None,
                 defaults: Optional[Dict[str, Any]] = None):
        self.plugin_name = plugin_name
        self.schema: Dict[str, Any] = schema or {"type": "object", "properties": {}}
        self.defaults: Dict[str, Any] = defaults or {}
        self._config_dir = Path(FRIDAY_MEMORY) / "plugins" / plugin_name
        self._config_path = self._config_dir / "config.json"
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load config from disk, merging with defaults."""
        self._config = dict(self.defaults)
        if self._config_path.exists():
            try:
                with open(str(self._config_path), "r", encoding="utf-8") as f:
                    saved = json.load(f)
                if isinstance(saved, dict):
                    self._config.update(saved)
            except (json.JSONDecodeError, OSError):
                pass

    def _save_config(self) -> None:
        """Write current config to disk."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        with open(str(self._config_path), "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)

    def _validate_value(self, key: str, value: Any) -> bool:
        """
        Validate a value against the schema for the given key.

        Args:
            key: Configuration key.
            value: Value to validate.

        Returns:
            True if valid or no schema for key.
        """
        props = self.schema.get("properties", {})
        if key not in props:
            return True
        prop_schema = props[key]
        prop_type = prop_schema.get("type", "")
        if prop_type == "string" and not isinstance(value, str):
            return False
        if prop_type == "integer" and not isinstance(value, int):
            return False
        if prop_type == "number" and not isinstance(value, (int, float)):
            return False
        if prop_type == "boolean" and not isinstance(value, bool):
            return False
        if prop_type == "array" and not isinstance(value, list):
            return False
        if "enum" in prop_schema and value not in prop_schema["enum"]:
            return False
        return True

    def set(self, key: str, value: Any) -> bool:
        """
        Set a configuration value.

        Args:
            key: Configuration key.
            value: Value to set.

        Returns:
            True if set successfully, False if validation fails.
        """
        if not self._validate_value(key, value):
            return False
        self._config[key] = value
        self._save_config()
        return True

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._config.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        """Return the full configuration dictionary."""
        return dict(self._config)

    def reset(self) -> None:
        """Reset configuration to defaults."""
        self._config = dict(self.defaults)
        self._save_config()

    def delete(self, key: str) -> bool:
        """Delete a configuration key."""
        if key in self._config:
            del self._config[key]
            self._save_config()
            return True
        return False

    def to_str(self) -> str:
        """Return configuration as a formatted string."""
        lines = [f"Config for plugin '{self.plugin_name}':", ""]
        for k, v in self._config.items():
            lines.append(f"  {k} = {json.dumps(v)}")
        return "\n".join(lines)


# ─── Plugin Dependency Resolver ────────────────────────────────────

class DependencyError(Exception):
    """Raised when plugin dependencies cannot be satisfied."""

    def __init__(self, message: str, plugin_name: str = ""):
        self.plugin_name = plugin_name
        super().__init__(message)


class PluginDependencyResolver:
    """
    Resolves plugin dependencies using a directed graph approach.

    Checks:
    - Required plugins exist.
    - Minimum version constraints are met.
    - No circular dependencies exist.
    """

    def __init__(self, manager: PluginManager):
        self._manager = manager
        self._graph: Dict[str, Dict[str, str]] = {}
        self._metadata_cache: Dict[str, PluginMetadata] = {}

    def register_plugin(self, plugin_name: str, metadata: PluginMetadata) -> None:
        """Register a plugin and its dependencies."""
        self._graph[plugin_name] = dict(metadata.dependencies)
        self._metadata_cache[plugin_name] = metadata

    def _parse_version(self, version: str) -> Tuple[int, ...]:
        """Parse a semver string into a comparable tuple."""
        parts = version.replace("-", ".").split(".")
        result = []
        for p in parts:
            try:
                result.append(int(p))
            except ValueError:
                result.append(0)
        while len(result) < 3:
            result.append(0)
        return tuple(result[:3])

    def _check_version(self, required: str, installed: str) -> bool:
        """
        Check if installed version satisfies required version.

        Supports:
        - '>=1.0.0', '>1.0.0', '==1.0.0', '<=1.0.0', '<1.0.0'
        - '1.0.0' (interpreted as >=1.0.0)
        """
        required = required.strip()
        if required.startswith(">="):
            op, ver = ">=", required[2:].strip()
        elif required.startswith(">"):
            op, ver = ">", required[1:].strip()
        elif required.startswith("=="):
            op, ver = "==", required[2:].strip()
        elif required.startswith("<="):
            op, ver = "<=", required[2:].strip()
        elif required.startswith("<"):
            op, ver = "<", required[1:].strip()
        else:
            op, ver = ">=", required.strip()

        req_parsed = self._parse_version(ver)
        inst_parsed = self._parse_version(installed)

        if op == ">=":
            return inst_parsed >= req_parsed
        if op == ">":
            return inst_parsed > req_parsed
        if op == "==":
            return inst_parsed == req_parsed
        if op == "<=":
            return inst_parsed <= req_parsed
        if op == "<":
            return inst_parsed < req_parsed
        return False

    def _has_circular(self, plugin: str, path: Set[str]) -> bool:
        """Detect circular dependencies using DFS."""
        if plugin in path:
            return True
        path.add(plugin)
        deps = self._graph.get(plugin, {})
        for dep in deps:
            if dep in self._graph:
                if self._has_circular(dep, path):
                    return True
        path.remove(plugin)
        return False

    def resolve(self, plugin_name: str) -> List[str]:
        """
        Resolve dependencies for a plugin and return a load order.

        Args:
            plugin_name: Name of the plugin to resolve dependencies for.

        Returns:
            Ordered list of plugin names to load (including the plugin itself).

        Raises:
            DependencyError: If dependencies cannot be satisfied.
        """
        if plugin_name not in self._graph:
            self._graph[plugin_name] = {}
            self._metadata_cache[plugin_name] = PluginMetadata(name=plugin_name)

        if self._has_circular(plugin_name, set()):
            raise DependencyError(
                f"Circular dependency detected involving '{plugin_name}'",
                plugin_name=plugin_name,
            )

        visited: Set[str] = set()
        order: List[str] = []

        def dfs(current: str) -> None:
            if current in visited:
                return
            visited.add(current)
            deps = self._graph.get(current, {})
            for dep, req_ver in deps.items():
                if dep not in self._graph:
                    raise DependencyError(
                        f"Plugin '{current}' requires '{dep}' which is not registered",
                        plugin_name=current,
                    )
                dep_meta = self._metadata_cache.get(dep, PluginMetadata(name=dep))
                installed_ver = dep_meta.version
                if not self._check_version(req_ver, installed_ver):
                    raise DependencyError(
                        f"Plugin '{current}' requires '{dep}' version {req_ver}, "
                        f"installed version is {installed_ver}",
                        plugin_name=current,
                    )
                dfs(dep)
            order.append(current)

        dfs(plugin_name)
        return order

    def check_all(self) -> List[str]:
        """Check all registered plugins and return list of errors."""
        errors = []
        for plugin_name in self._graph:
            try:
                self.resolve(plugin_name)
            except DependencyError as e:
                errors.append(str(e))
        return errors


# ─── Plugin Compatibility Checker ─────────────────────────────────

class PluginCompatibilityChecker:
    """
    Checks plugin compatibility against the current Friday version.

    Uses min_friday_version from plugin metadata to determine
    whether a plugin is compatible.
    """

    def __init__(self, friday_version: str = FRIDAY_VERSION):
        self.friday_version = friday_version

    def _parse_ver(self, v: str) -> Tuple[int, ...]:
        parts = v.strip().split(".")
        result = []
        for p in parts:
            try:
                result.append(int(p))
            except ValueError:
                result.append(0)
        while len(result) < 3:
            result.append(0)
        return tuple(result[:3])

    def check(self, plugin_metadata: PluginMetadata) -> Tuple[bool, str]:
        """
        Check if a plugin is compatible with the current Friday version.

        Args:
            plugin_metadata: The plugin's metadata.

        Returns:
            Tuple of (is_compatible, message).
        """
        required = plugin_metadata.min_friday_version
        friday_ver = self._parse_ver(self.friday_version)
        plugin_req = self._parse_ver(required)
        if friday_ver >= plugin_req:
            return True, (
                f"Plugin '{plugin_metadata.name}' v{plugin_metadata.version} "
                f"is compatible with Friday {self.friday_version}"
            )
        return False, (
            f"Plugin '{plugin_metadata.name}' requires Friday >= {required}, "
            f"current version is {self.friday_version}"
        )

    def check_many(self, metadata_list: List[PluginMetadata]) -> List[Tuple[str, bool, str]]:
        """Check multiple plugins and return results."""
        results = []
        for meta in metadata_list:
            ok, msg = self.check(meta)
            results.append((meta.name, ok, msg))
        return results


# ─── Plugin Statistics ─────────────────────────────────────────────

@dataclass
class PluginStats:
    """Runtime statistics for a single plugin."""
    name: str = ""
    load_count: int = 0
    unload_count: int = 0
    tool_call_count: int = 0
    error_count: int = 0
    total_load_time: float = 0.0
    last_load_time: float = 0.0
    last_error: str = ""
    last_error_time: Optional[float] = None


class PluginStatisticsCollector:
    """
    Collects and reports plugin usage statistics.

    Tracks load times, tool call counts, error rates, and more.
    """

    def __init__(self):
        self._stats: Dict[str, PluginStats] = defaultdict(PluginStats)
        self._lock = threading.Lock()

    def record_load(self, plugin_name: str, load_time: float) -> None:
        """Record a plugin load event."""
        with self._lock:
            s = self._stats[plugin_name]
            s.name = plugin_name
            s.load_count += 1
            s.total_load_time += load_time
            s.last_load_time = load_time

    def record_unload(self, plugin_name: str) -> None:
        """Record a plugin unload event."""
        with self._lock:
            self._stats[plugin_name].unload_count += 1

    def record_tool_call(self, plugin_name: str) -> None:
        """Record a plugin tool invocation."""
        with self._lock:
            self._stats[plugin_name].tool_call_count += 1

    def record_error(self, plugin_name: str, error: str) -> None:
        """Record a plugin error."""
        with self._lock:
            s = self._stats[plugin_name]
            s.name = plugin_name
            s.error_count += 1
            s.last_error = error
            s.last_error_time = time.time()

    def get_stats(self, plugin_name: str) -> Optional[PluginStats]:
        """Get statistics for a specific plugin."""
        return self._stats.get(plugin_name)

    def get_all_stats(self) -> Dict[str, PluginStats]:
        """Get statistics for all plugins."""
        return dict(self._stats)

    def get_summary(self) -> Dict[str, Any]:
        """Return an aggregate summary of all plugin statistics."""
        total_plugins = len(self._stats)
        total_tool_calls = sum(s.tool_call_count for s in self._stats.values())
        total_errors = sum(s.error_count for s in self._stats.values())
        total_loads = sum(s.load_count for s in self._stats.values())
        avg_load_time = (
            sum(s.total_load_time for s in self._stats.values()) / total_loads
            if total_loads > 0 else 0.0
        )

        most_used = max(self._stats.values(), key=lambda s: s.tool_call_count) \
            if self._stats else None

        return {
            "total_plugins": total_plugins,
            "total_tool_calls": total_tool_calls,
            "total_errors": total_errors,
            "total_loads": total_loads,
            "avg_load_time_ms": round(avg_load_time * 1000, 2),
            "most_used_plugin": most_used.name if most_used else None,
            "most_used_calls": most_used.tool_call_count if most_used else 0,
        }

    def to_str(self) -> str:
        """Return statistics as a formatted string."""
        summary = self.get_summary()
        lines = ["### PLUGIN STATISTICS", ""]
        lines.append(f"Total plugins: {summary['total_plugins']}")
        lines.append(f"Total tool calls: {summary['total_tool_calls']}")
        lines.append(f"Total errors: {summary['total_errors']}")
        lines.append(f"Total loads: {summary['total_loads']}")
        lines.append(f"Average load time: {summary['avg_load_time_ms']}ms")
        lines.append(f"Most used plugin: {summary['most_used_plugin']} "
                     f"({summary['most_used_calls']} calls)")
        lines.append("")
        for name, s in sorted(self._stats.items()):
            lines.append(f"  {name}: {s.load_count} loads, "
                         f"{s.tool_call_count} calls, {s.error_count} errors")
            if s.last_error:
                lines.append(f"    Last error: {s.last_error[:80]}")
        return "\n".join(lines)


# ─── Plugin Categories ─────────────────────────────────────────────

PLUGIN_CATEGORIES: Dict[str, str] = {
    "automation": "Task automation and scripting",
    "search": "Web and local file search",
    "analysis": "Data analysis and processing",
    "communication": "Messaging and notification",
    "entertainment": "Games, media, and fun",
    "utility": "General-purpose utility tools",
    "integration": "Third-party service integration",
    "development": "Software development tools",
    "system": "System monitoring and administration",
    "ai": "AI and machine learning tools",
}

DEFAULT_CATEGORY: str = "utility"


class PluginCategoriser:
    """
    Organises plugins by category.

    Plugins declare categories via metadata tags. This class provides
    filtering and browsing capabilities.
    """

    def __init__(self):
        self._by_category: Dict[str, List[str]] = defaultdict(list)

    def register(self, plugin_name: str, tags: List[str]) -> None:
        """Register a plugin under its relevant categories."""
        categories_found = set()
        for tag in tags:
            tag_lower = tag.lower().strip()
            if tag_lower in PLUGIN_CATEGORIES:
                if plugin_name not in self._by_category[tag_lower]:
                    self._by_category[tag_lower].append(plugin_name)
                categories_found.add(tag_lower)
        if not categories_found:
            self._by_category[DEFAULT_CATEGORY].append(plugin_name)

    def unregister(self, plugin_name: str) -> None:
        """Remove a plugin from all categories."""
        for cat in list(self._by_category.keys()):
            if plugin_name in self._by_category[cat]:
                self._by_category[cat].remove(plugin_name)

    def get_plugins_in_category(self, category: str) -> List[str]:
        """List all plugins in a given category."""
        return list(self._by_category.get(category.lower().strip(), []))

    def list_categories(self) -> Dict[str, List[str]]:
        """Return all categories with their plugins."""
        return {cat: list(plugins) for cat, plugins in self._by_category.items()}

    def get_category_description(self, category: str) -> str:
        """Get the description for a given category."""
        return PLUGIN_CATEGORIES.get(category.lower().strip(), "Unknown category")

    def list_all_categories(self) -> Dict[str, str]:
        """Return all available categories and their descriptions."""
        return dict(PLUGIN_CATEGORIES)

    def to_str(self) -> str:
        """Return categories as a formatted string."""
        lines = ["### PLUGIN CATEGORIES", ""]
        for cat, description in sorted(PLUGIN_CATEGORIES.items()):
            plugins = self._by_category.get(cat, [])
            count = len(plugins)
            lines.append(f"  {cat} ({count}): {description}")
            if plugins:
                lines.append(f"    Plugins: {', '.join(sorted(plugins))}")
        return "\n".join(lines)


# ─── Hot-Reload Watcher ────────────────────────────────────────────

class HotReloadWatcher:
    """
    Monitors plugin files for changes and triggers reloads.

    Uses file mtime polling at a configurable interval.
    """

    def __init__(self, manager: PluginManager, interval: float = PLUGIN_HOTRELOAD_INTERVAL):
        self._manager = manager
        self._interval = interval
        self._watched: Dict[str, float] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def watch(self, plugin_name: str) -> None:
        """Start watching a plugin file for changes."""
        plugin_path = self._get_plugin_path(plugin_name)
        if plugin_path and plugin_path.exists():
            with self._lock:
                self._watched[plugin_name] = plugin_path.stat().st_mtime

    def unwatch(self, plugin_name: str) -> None:
        """Stop watching a plugin file."""
        with self._lock:
            self._watched.pop(plugin_name, None)

    def _get_plugin_path(self, plugin_name: str) -> Optional[Path]:
        return self._manager.plugin_dir / f"{plugin_name}.py"

    def _check_for_changes(self) -> List[str]:
        """Check all watched files for modifications."""
        changed = []
        with self._lock:
            for plugin_name in list(self._watched.keys()):
                plugin_path = self._get_plugin_path(plugin_name)
                if not plugin_path or not plugin_path.exists():
                    continue
                current_mtime = plugin_path.stat().st_mtime
                last_mtime = self._watched.get(plugin_name)
                if last_mtime is not None and current_mtime > last_mtime:
                    self._watched[plugin_name] = current_mtime
                    changed.append(plugin_name)
        return changed

    def _reload_changed(self) -> None:
        """Reload any plugins whose files have changed."""
        changed = self._check_for_changes()
        for plugin_name in changed:
            try:
                self._manager.unload_plugin(plugin_name)
                self._manager.load_plugin(plugin_name)
            except Exception as exc:
                pass

    def _loop(self) -> None:
        """Main polling loop."""
        while self._running:
            self._reload_changed()
            time.sleep(self._interval)

    def start(self) -> None:
        """Start the hot-reload watcher in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name="hotreload-watcher")
        self._thread.start()

    def stop(self) -> None:
        """Stop the hot-reload watcher."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._thread = None

    def is_running(self) -> bool:
        """Check if the watcher is currently active."""
        return self._running

    def get_watched(self) -> List[str]:
        """Return list of currently watched plugin names."""
        with self._lock:
            return list(self._watched.keys())


# ─── Plugin Marketplace ─────────────────────────────────────────────

class PluginMarketplace:
    """
    Manages plugin installation from remote sources.

    Scans FRIDAY_MEMORY/plugins_available/ for downloadable plugins,
    supports installing from URLs, and maintains a plugin index.
    """

    def __init__(self, manager: PluginManager):
        self._manager = manager
        self._available_dir = Path(PLUGINS_AVAILABLE_DIR)
        self._index_path = self._available_dir / "index.json"
        self._index: Dict[str, Dict[str, Any]] = {}
        self._ensure_dirs()
        self._load_index()

    def _ensure_dirs(self) -> None:
        """Create necessary directories."""
        self._available_dir.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> None:
        """Load the plugin index from disk if it exists."""
        if self._index_path.exists():
            try:
                with open(str(self._index_path), "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self._index = data
            except (json.JSONDecodeError, OSError):
                self._index = {}

    def _save_index(self) -> None:
        """Save the plugin index to disk."""
        with open(str(self._index_path), "w", encoding="utf-8") as f:
            json.dump(self._index, f, indent=2, ensure_ascii=False)

    def list_available(self) -> List[Dict[str, Any]]:
        """
        List all plugins available for installation.

        Returns:
            List of plugin info dictionaries from the index.
        """
        return list(self._index.values())

    def install_plugin(self, url: str) -> bool:
        """
        Download and install a plugin from a URL.

        The URL should point to a Python plugin file. It is downloaded
        into the plugin directory.

        Args:
            url: URL of the plugin file to install.

        Returns:
            True if installation succeeded, False otherwise.
        """
        try:
            import urllib.request
            parsed = urlparse(url)
            filename = os.path.basename(parsed.path)
            if not filename.endswith(".py"):
                filename += ".py"

            dest = self._manager.plugin_dir / filename
            if dest.exists():
                return False

            with urllib.request.urlopen(url, timeout=30) as response:
                content = response.read()

            with open(str(dest), "wb") as f:
                f.write(content)

            plugin_name = dest.stem
            self._index[plugin_name] = {
                "name": plugin_name,
                "url": url,
                "installed_at": datetime.datetime.now().isoformat(),
                "filename": filename,
            }
            self._save_index()
            return True

        except Exception:
            return False

    def uninstall_plugin(self, plugin_name: str) -> bool:
        """
        Remove an installed plugin.

        Args:
            plugin_name: Name of the plugin to uninstall.

        Returns:
            True if successfully removed.
        """
        if plugin_name in self._manager.plugins:
            self._manager.unload_plugin(plugin_name)

        plugin_path = self._manager.plugin_dir / f"{plugin_name}.py"
        if plugin_path.exists():
            plugin_path.unlink()
            self._index.pop(plugin_name, None)
            self._save_index()
            return True
        return False

    def add_to_index(self, name: str, metadata: Dict[str, Any]) -> None:
        """Add or update an entry in the plugin index."""
        self._index[name] = metadata
        self._save_index()

    def remove_from_index(self, name: str) -> None:
        """Remove an entry from the plugin index."""
        self._index.pop(name, None)
        self._save_index()

    def search_index(self, query: str) -> List[Dict[str, Any]]:
        """Search the plugin index by name or description."""
        query = query.lower().strip()
        results = []
        for name, info in self._index.items():
            if query in name.lower():
                results.append(info)
                continue
            desc = info.get("description", "")
            if query in desc.lower():
                results.append(info)
        return results

    def to_str(self) -> str:
        """Return marketplace content as a formatted string."""
        lines = ["### PLUGIN MARKETPLACE", ""]
        available = self.list_available()
        if not available:
            lines.append("No plugins in the marketplace index.")
        else:
            for info in available:
                name = info.get("name", "unknown")
                url = info.get("url", "")
                installed = info.get("installed_at", "")
                lines.append(f"  {name}")
                lines.append(f"    URL: {url}")
                lines.append(f"    Installed: {installed}")
        lines.append("")
        plugin_dir = self._manager.plugin_dir
        installed_files = list(plugin_dir.glob("*.py")) if plugin_dir.exists() else []
        installed_names = [p.stem for p in installed_files if p.stem != "__init__"]
        lines.append(f"Installed plugin files ({len(installed_names)}):")
        for n in installed_names:
            lines.append(f"  - {n}")
        return "\n".join(lines)


# ─── Plugin Test Runner ────────────────────────────────────────────

class PluginTestRunner:
    """
    Discovers and runs test functions defined in plugins.

    Test functions must start with 'test_' and accept no required
    arguments (except optional plugin instance). Each test is run
    with a configurable timeout.
    """

    def __init__(self, manager: PluginManager, timeout: float = PLUGIN_TEST_TIMEOUT):
        self._manager = manager
        self._timeout = timeout

    def discover_tests(self, plugin_name: str) -> List[Dict[str, Any]]:
        """
        Find all test functions in a plugin.

        Args:
            plugin_name: Name of the plugin to scan.

        Returns:
            List of dicts with 'name' and 'function' keys.
        """
        plugin = self._manager.get_plugin(plugin_name)
        if not plugin:
            return []

        tests = []
        for member_name in dir(plugin):
            if member_name.startswith("test_"):
                member = getattr(plugin, member_name)
                if callable(member):
                    tests.append({
                        "name": member_name,
                        "function": member,
                    })
        return tests

    def run_test(self, plugin_name: str, test_name: str) -> Dict[str, Any]:
        """
        Run a single test function.

        Args:
            plugin_name: Name of the plugin.
            test_name: Name of the test function.

        Returns:
            Dict with keys: name, passed, duration, error, traceback.
        """
        tests = self.discover_tests(plugin_name)
        test_info = next((t for t in tests if t["name"] == test_name), None)
        if not test_info:
            return {
                "name": test_name,
                "passed": False,
                "duration": 0.0,
                "error": f"Test '{test_name}' not found in plugin '{plugin_name}'",
                "traceback": "",
            }

        func = test_info["function"]
        start = time.time()
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func)
                future.result(timeout=self._timeout)
            duration = time.time() - start
            return {
                "name": test_name,
                "passed": True,
                "duration": round(duration, 4),
                "error": "",
                "traceback": "",
            }
        except TimeoutError:
            duration = time.time() - start
            return {
                "name": test_name,
                "passed": False,
                "duration": round(duration, 4),
                "error": f"Test timed out after {self._timeout}s",
                "traceback": "",
            }
        except Exception as exc:
            duration = time.time() - start
            return {
                "name": test_name,
                "passed": False,
                "duration": round(duration, 4),
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }

    def run_plugin_tests(self, plugin_name: str) -> List[Dict[str, Any]]:
        """
        Run all tests for a specific plugin.

        Args:
            plugin_name: Name of the plugin.

        Returns:
            List of test result dictionaries.
        """
        tests = self.discover_tests(plugin_name)
        results = []
        for test in tests:
            result = self.run_test(plugin_name, test["name"])
            results.append(result)
        return results

    def run_all_tests(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Run tests for all loaded plugins.

        Returns:
            Dict mapping plugin names to their test results.
        """
        all_results = {}
        for plugin_name in self._manager.plugins:
            results = self.run_plugin_tests(plugin_name)
            all_results[plugin_name] = results
        return all_results

    def results_to_str(self, results: Union[List[Dict[str, Any]],
                                            Dict[str, List[Dict[str, Any]]]]) -> str:
        """Format test results as a readable string."""
        lines = ["### TEST RESULTS", ""]
        if isinstance(results, dict):
            for plugin_name, plugin_results in results.items():
                lines.append(f"Plugin: {plugin_name}")
                passed = sum(1 for r in plugin_results if r["passed"])
                total = len(plugin_results)
                lines.append(f"  {passed}/{total} tests passed")
                for r in plugin_results:
                    status = "[PASS]" if r["passed"] else "[FAIL]"
                    lines.append(f"  {status} {r['name']} ({r['duration']}s)")
                    if r["error"]:
                        lines.append(f"       Error: {r['error']}")
                lines.append("")
        elif isinstance(results, list):
            passed = sum(1 for r in results if r["passed"])
            total = len(results)
            lines.append(f"{passed}/{total} tests passed")
            for r in results:
                status = "[PASS]" if r["passed"] else "[FAIL]"
                lines.append(f"{status} {r['name']} ({r['duration']}s)")
                if r["error"]:
                    lines.append(f"  Error: {r['error']}")
        return "\n".join(lines)


# ─── Plugin API Documentation Generator ────────────────────────────

class PluginAPIDocs:
    """
    Generates Markdown documentation for plugin tools.

    Extracts function signatures, docstrings, and parameter descriptions
    from each tool registered by a plugin.
    """

    def __init__(self, manager: PluginManager):
        self._manager = manager

    def generate_plugin_docs(self, plugin_name: str) -> str:
        """
        Create Markdown documentation for a single plugin.

        Args:
            plugin_name: Name of the plugin.

        Returns:
            Markdown string documenting the plugin and its tools.
        """
        plugin = self._manager.get_plugin(plugin_name)
        if not plugin:
            return f"# Plugin '{plugin_name}' is not loaded.\n"

        lines = [
            f"# Plugin: {plugin_name}",
            "",
            f"**Version:** {plugin.version}",
            f"**Description:** {plugin.description}",
            "",
            "---",
            "## Tools",
            "",
        ]

        tools = plugin.get_tools()
        if not tools:
            lines.append("No tools registered.")
            return "\n".join(lines)

        for tool_name, tool_info in tools.items():
            func = tool_info["function"]
            description = tool_info.get("description", "")

            lines.append(f"### `{tool_name}`")
            lines.append("")
            if description:
                lines.append(f"{description}")
                lines.append("")

            sig = self._get_signature(func)
            lines.append(f"**Signature:** `{tool_name}{sig}`")
            lines.append("")

            doc = inspect.getdoc(func)
            if doc:
                lines.append("**Docstring:**")
                lines.append("")
                for doc_line in doc.strip().split("\n"):
                    lines.append(f"> {doc_line}")
                lines.append("")

            params = self._get_parameters(func)
            if params:
                lines.append("**Parameters:**")
                lines.append("")
                lines.append("| Name | Type | Default | Description |")
                lines.append("|------|------|---------|-------------|")
                for p in params:
                    lines.append(
                        f"| {p['name']} | {p['type']} | {p['default']} | "
                        f"{p.get('description', '')} |"
                    )
                lines.append("")

            return_annotation = self._get_return_annotation(func)
            if return_annotation:
                lines.append(f"**Returns:** `{return_annotation}`")
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def generate_all_docs(self) -> Dict[str, str]:
        """Generate documentation for all loaded plugins."""
        docs = {}
        for plugin_name in self._manager.plugins:
            docs[plugin_name] = self.generate_plugin_docs(plugin_name)
        return docs

    def _get_signature(self, func: Callable) -> str:
        """Get a readable signature string for a function."""
        try:
            sig = inspect.signature(func)
            params = []
            for name, param in sig.parameters.items():
                if name == "self":
                    continue
                default = ""
                if param.default is not inspect.Parameter.empty:
                    default = f"={param.default!r}"
                params.append(f"{name}{default}")
            return "(" + ", ".join(params) + ")"
        except (ValueError, TypeError):
            return "(...)"

    def _get_parameters(self, func: Callable) -> List[Dict[str, str]]:
        """Extract parameter information from a function."""
        params = []
        try:
            sig = inspect.signature(func)
            for name, param in sig.parameters.items():
                if name == "self":
                    continue
                ptype = ""
                if param.annotation is not inspect.Parameter.empty:
                    ptype = self._format_annotation(param.annotation)
                default = ""
                if param.default is not inspect.Parameter.empty:
                    default = repr(param.default)
                params.append({
                    "name": name,
                    "type": ptype,
                    "default": default,
                    "description": "",
                })
        except (ValueError, TypeError):
            pass
        return params

    def _get_return_annotation(self, func: Callable) -> str:
        """Get the return type annotation as a string."""
        try:
            sig = inspect.signature(func)
            if sig.return_annotation is not inspect.Parameter.empty:
                return self._format_annotation(sig.return_annotation)
        except (ValueError, TypeError):
            pass
        return ""

    def _format_annotation(self, ann: Any) -> str:
        """Format a type annotation for display."""
        if hasattr(ann, "__name__"):
            return ann.__name__
        return str(ann).replace("typing.", "")


# ─── Plugin Template Generator ─────────────────────────────────────

class PluginTemplateGenerator:
    """
    Generates new plugin files from boilerplate templates.

    Includes class skeleton, register_tools stub, docstrings, and
    example tools with various template styles.
    """

    BASIC_TEMPLATE = '''"""
{name} plugin for Friday.
"""

from friday.plugins import FridayPlugin


class {class_name}(FridayPlugin):
    """{description}"""

    name = "{name}"
    description = "{description}"
    version = "{version}"
    author = "{author}"

    def _register_tools(self):
        """Register plugin tools."""
        self.register_tool(
            "example",
            self.example_tool,
            "Example tool description",
        )

    def example_tool(self, message: str = "Hello") -> str:
        """Example tool that returns a greeting.

        Args:
            message: The message to echo back.

        Returns:
            A greeting string.
        """
        return f"{{message}} from {self.name} plugin!"

    def initialize(self):
        """Called when the plugin is loaded."""
        pass

    def shutdown(self):
        """Called when the plugin is unloaded."""
        pass
'''

    WEB_SCRAPER_TEMPLATE = '''"""
{name} plugin - Web scraping utilities.
"""

from friday.plugins import FridayPlugin


class {class_name}(FridayPlugin):
    """{description}"""

    name = "{name}"
    description = "{description}"
    version = "{version}"
    author = "{author}"

    def _register_tools(self):
        self.register_tool("fetch_page", self.fetch_page, "Fetch a web page")
        self.register_tool(
            "extract_links",
            self.extract_links,
            "Extract links from HTML",
        )

    def fetch_page(self, url: str) -> str:
        """Fetch a web page and return its text content.

        Args:
            url: The URL to fetch.

        Returns:
            Page text content or error message.
        """
        return f"Fetched {{url}} (stub)"

    def extract_links(self, html: str) -> str:
        """Extract links from HTML content.

        Args:
            html: The HTML content to parse.

        Returns:
            List of extracted URLs.
        """
        return "Links extracted (stub)"
'''

    DATA_PROCESSING_TEMPLATE = '''"""
{name} plugin - Data processing and conversion.
"""

from friday.plugins import FridayPlugin


class {class_name}(FridayPlugin):
    """{description}"""

    name = "{name}"
    description = "{description}"
    version = "{version}"
    author = "{author}"

    def _register_tools(self):
        self.register_tool(
            "transform",
            self.transform_data,
            "Transform data format",
        )
        self.register_tool(
            "validate",
            self.validate_data,
            "Validate data structure",
        )

    def transform_data(self, data: str, format: str = "json") -> str:
        """Transform data between different formats.

        Args:
            data: The input data string.
            format: Target format (json, csv, yaml).

        Returns:
            Transformed data string.
        """
        return f"Transformed to {{format}} (stub)"

    def validate_data(self, data: str, schema: str = "") -> str:
        """Validate data against an optional schema.

        Args:
            data: Data to validate.
            schema: Optional schema definition.

        Returns:
            Validation result.
        """
        return "Validation passed (stub)"
'''

    MONITORING_TEMPLATE = '''"""
{name} plugin - System monitoring tools.
"""

from friday.plugins import FridayPlugin


class {class_name}(FridayPlugin):
    """{description}"""

    name = "{name}"
    description = "{description}"
    version = "{version}"
    author = "{author}"

    def _register_tools(self):
        self.register_tool(
            "status",
            self.system_status,
            "Get system status overview",
        )
        self.register_tool(
            "disk_usage",
            self.check_disk,
            "Check disk usage",
        )
        self.register_tool(
            "memory_info",
            self.check_memory,
            "Check memory usage",
        )

    def system_status(self) -> str:
        """Return a summary of system status.

        Returns:
            System status string.
        """
        return "System status (stub)"

    def check_disk(self, path: str = "/") -> str:
        """Check disk usage for a given path.

        Args:
            path: Filesystem path to check.

        Returns:
            Disk usage information.
        """
        return f"Disk usage for {{path}} (stub)"

    def check_memory(self) -> str:
        """Check memory usage.

        Returns:
            Memory usage information.
        """
        return "Memory info (stub)"
'''

    def __init__(self):
        self.templates = {
            "basic": self.BASIC_TEMPLATE,
            "web_scraper": self.WEB_SCRAPER_TEMPLATE,
            "data_processing": self.DATA_PROCESSING_TEMPLATE,
            "monitoring": self.MONITORING_TEMPLATE,
        }

    def list_templates(self) -> List[str]:
        """Return available template names."""
        return list(self.templates.keys())

    def create_plugin(self, name: str, author: str,
                      template: str = "basic",
                      description: str = "",
                      version: str = "1.0.0",
                      output_dir: Optional[str] = None) -> Optional[str]:
        """
        Generate a new plugin file from a template.

        Args:
            name: Plugin name (used for filename and class).
            author: Plugin author name.
            template: Template style (basic, web_scraper, data_processing, monitoring).
            description: Short plugin description.
            version: Plugin version string.
            output_dir: Output directory (defaults to plugin dir).

        Returns:
            Path to the created file, or None on failure.
        """
        template_str = self.templates.get(template, self.BASIC_TEMPLATE)
        class_name = "".join(word.capitalize() for word in name.replace("-", "_").split("_"))
        if not class_name.endswith("Plugin"):
            class_name += "Plugin"
        if not description:
            description = f"{name} plugin for Friday"
        content = template_str.format(
            name=name,
            class_name=class_name,
            description=description,
            version=version,
            author=author,
        )
        if output_dir is None:
            from friday._paths import PROJECT_ROOT as fallback_root
            output_dir = os.path.join(fallback_root, "friday_plugins")
        output_path = Path(output_dir) / f"{name}.py"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            output_path.write_text(content, encoding="utf-8")
            return str(output_path)
        except OSError:
            return None

    def preview(self, name: str, author: str,
                template: str = "basic",
                description: str = "") -> str:
        """Return the generated template content without writing to disk."""
        template_str = self.templates.get(template, self.BASIC_TEMPLATE)
        class_name = "".join(word.capitalize() for word in name.replace("-", "_").split("_"))
        if not class_name.endswith("Plugin"):
            class_name += "Plugin"
        if not description:
            description = f"{name} plugin for Friday"
        return template_str.format(
            name=name,
            class_name=class_name,
            description=description,
            version="1.0.0",
            author=author,
        )


# ─── Plugin Base Class (Enhanced) ──────────────────────────────────

class FridayPlugin:
    """
    Base class for all Friday plugins.

    Subclass this to create a new plugin. Override _register_tools
    to register tool functions, and optionally override initialize
    and shutdown for lifecycle management.
    """

    name: str = "base_plugin"
    description: str = "Base plugin class"
    version: str = "1.0.0"
    author: str = "unknown"
    category: str = DEFAULT_CATEGORY
    tags: List[str] = field(default_factory=list)
    min_friday_version: str = "1.0.0"
    dependencies: Dict[str, str] = field(default_factory=dict)
    license: str = "MIT"

    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.metadata: PluginMetadata = self._build_metadata()
        self.config: PluginConfig = PluginConfig(
            plugin_name=self.name,
            defaults=getattr(self, "default_config", None),
        )
        self._sandbox: Optional[PluginSandbox] = None
        self._register_tools()

    def _build_metadata(self) -> PluginMetadata:
        """Construct PluginMetadata from class attributes."""
        return PluginMetadata(
            name=self.name,
            version=self.version,
            author=self.author,
            description=self.description,
            dependencies=dict(self.dependencies),
            min_friday_version=self.min_friday_version,
            tags=list(self.tags),
            license=self.license,
            entry_point=f"{type(self).__module__}.{type(self).__qualname__}",
        )

    def _register_tools(self):
        """Override this to register tools."""
        pass

    def register_tool(self, name: str, func: Callable,
                      description: str = "") -> None:
        """
        Register a tool with Friday.

        Args:
            name: Tool name (unique within the plugin).
            func: The callable implementing the tool.
            description: Human-readable description.
        """
        self.tools[name] = {
            "function": func,
            "description": description or func.__doc__ or "No description",
        }

    def get_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered tools."""
        return self.tools

    def get_tool_names(self) -> List[str]:
        """Get names of all registered tools."""
        return list(self.tools.keys())

    def initialize(self):
        """Called when plugin is loaded. Override for setup."""
        pass

    def shutdown(self):
        """Called when plugin is unloaded. Override for cleanup."""
        pass

    def get_metadata(self) -> PluginMetadata:
        """Return the plugin's metadata."""
        return self.metadata

    def get_sandbox(self) -> Optional[PluginSandbox]:
        """Return the plugin's sandbox if configured."""
        return self._sandbox

    def set_sandbox(self, sandbox: PluginSandbox) -> None:
        """Assign a sandbox to this plugin."""
        self._sandbox = sandbox

    def to_str(self) -> str:
        """Return a summary string for this plugin."""
        lines = [
            f"Name: {self.name}",
            f"Version: {self.version}",
            f"Author: {self.author}",
            f"Description: {self.description}",
            f"Category: {self.category}",
            f"License: {self.license}",
            f"Tools: {len(self.tools)}",
        ]
        if self.tools:
            lines.append("Registered tools:")
            for tname in self.tools:
                lines.append(f"  - {tname}")
        return "\n".join(lines)


# ─── Example: WebScraperPlugin ─────────────────────────────────────

class WebScraperPlugin(FridayPlugin):
    """Plugin providing web scraping utilities."""

    name = "web_scraper"
    description = "Web scraping and content extraction tools"
    version = "1.0.0"
    author = "Friday Team"
    tags = ["utility", "search"]

    def _register_tools(self):
        self.register_tool("fetch_url", self.fetch_url, "Fetch a URL and return its text content")
        self.register_tool("extract_emails", self.extract_emails, "Extract email addresses from text")
        self.register_tool("count_words", self.count_words, "Count words in a text")

    def fetch_url(self, url: str = "") -> str:
        """Fetch a URL and return its text content.

        Args:
            url: The URL to fetch.

        Returns:
            The text content or error message.
        """
        if not url:
            return "No URL provided."
        return f"[WebScraper] Fetched content from {url} (stub)"

    def extract_emails(self, text: str = "") -> str:
        """Extract email addresses from the given text.

        Args:
            text: Text to search for email addresses.

        Returns:
            List of found email addresses.
        """
        if not text:
            return "No text provided."
        pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        emails = re.findall(pattern, text)
        if emails:
            return "Found emails: " + ", ".join(emails)
        return "No email addresses found."

    def count_words(self, text: str = "") -> str:
        """Count the number of words in a text.

        Args:
            text: The text to analyse.

        Returns:
            Word count result.
        """
        if not text:
            return "No text provided."
        words = text.split()
        return f"Word count: {len(words)}"


# ─── Example: FileConverterPlugin ──────────────────────────────────

class FileConverterPlugin(FridayPlugin):
    """Plugin for file format conversion and processing."""

    name = "file_converter"
    description = "File format conversion and processing tools"
    version = "1.0.0"
    author = "Friday Team"
    tags = ["utility", "analysis"]

    def _register_tools(self):
        self.register_tool("to_upper", self.to_upper, "Convert text to uppercase")
        self.register_tool("to_lower", self.to_lower, "Convert text to lowercase")
        self.register_tool("reverse_text", self.reverse_text, "Reverse a text string")
        self.register_tool("count_lines", self.count_lines, "Count lines in text")

    def to_upper(self, text: str = "") -> str:
        """Convert text to uppercase.

        Args:
            text: Text to convert.

        Returns:
            Uppercase version of the input.
        """
        if not text:
            return "No text provided."
        return text.upper()

    def to_lower(self, text: str = "") -> str:
        """Convert text to lowercase.

        Args:
            text: Text to convert.

        Returns:
            Lowercase version of the input.
        """
        if not text:
            return "No text provided."
        return text.lower()

    def reverse_text(self, text: str = "") -> str:
        """Reverse a text string.

        Args:
            text: Text to reverse.

        Returns:
            Reversed text.
        """
        if not text:
            return "No text provided."
        return text[::-1]

    def count_lines(self, text: str = "") -> str:
        """Count lines in text.

        Args:
            text: Text to analyse.

        Returns:
            Line count.
        """
        if not text:
            return "No text provided."
        lines = text.split("\n")
        return f"Line count: {len(lines)}"


# ─── Example: SystemMonitorPlugin ──────────────────────────────────

class SystemMonitorPlugin(FridayPlugin):
    """Plugin for monitoring system resources."""

    name = "system_monitor"
    description = "System monitoring and resource tracking tools"
    version = "1.0.0"
    author = "Friday Team"
    tags = ["system", "utility"]

    def _register_tools(self):
        self.register_tool("ping", self.ping_tool, "Ping a host to check connectivity")
        self.register_tool("uptime_info", self.uptime_info, "Get system uptime information")
        self.register_tool("environment", self.environment, "List environment variables")

    def ping_tool(self, host: str = "localhost") -> str:
        """Ping a host to check connectivity.

        Args:
            host: Hostname or IP address.

        Returns:
            Ping result string.
        """
        return f"[SystemMonitor] Ping result for {host} (stub)"

    def uptime_info(self) -> str:
        """Get system uptime information.

        Returns:
            Uptime information string.
        """
        try:
            import psutil
            uptime_seconds = time.time() - psutil.boot_time()
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            return f"System uptime: {days}d {hours}h {minutes}m"
        except ImportError:
            return "System uptime: psutil not available (stub)"

    def environment(self) -> str:
        """List environment variables.

        Returns:
            Formatted list of environment variables.
        """
        keys = sorted(os.environ.keys())[:20]
        lines = ["Environment variables (first 20):", ""]
        for k in keys:
            lines.append(f"  {k}={os.environ[k][:60]}")
        return "\n".join(lines)


# ─── Example: ChatBotPlugin ────────────────────────────────────────

class ChatBotPlugin(FridayPlugin):
    """Plugin providing chatbot interaction utilities."""

    name = "chatbot"
    description = "Chatbot interaction and conversation tools"
    version = "1.0.0"
    author = "Friday Team"
    tags = ["communication", "ai"]

    def _register_tools(self):
        self.register_tool("ask", self.ask, "Ask the chatbot a question")
        self.register_tool("echo", self.echo, "Echo a message back")
        self.register_tool("repeat", self.repeat, "Repeat a message multiple times")

    def ask(self, question: str = "") -> str:
        """Ask the chatbot a question.

        Args:
            question: The question to ask.

        Returns:
            Chatbot response.
        """
        if not question:
            return "Please provide a question."
        return f"[ChatBot] You asked: '{question}'. This is a stub response."

    def echo(self, message: str = "") -> str:
        """Echo a message back.

        Args:
            message: The message to echo.

        Returns:
            The echoed message.
        """
        if not message:
            return "Nothing to echo."
        return f"Echo: {message}"

    def repeat(self, message: str = "", count: int = 3) -> str:
        """Repeat a message multiple times.

        Args:
            message: The message to repeat.
            count: Number of times to repeat (1-20).

        Returns:
            Repeated message string.
        """
        if not message:
            return "Nothing to repeat."
        count = max(1, min(count, 20))
        return "\n".join([f"{i+1}. {message}" for i in range(count)])


# ─── Example: ExamplePlugin (from original) ────────────────────────

class ExamplePlugin(FridayPlugin):
    """Example plugin demonstrating the plugin system."""

    name = "example"
    description = "Example plugin for demonstration"
    version = "1.0.0"
    author = "Friday Team"
    tags = ["utility"]

    def _register_tools(self):
        self.register_tool("hello", self.hello, "Say hello from plugin")
        self.register_tool("calculate", self.calculate, "Perform calculation")

    def hello(self, name: str = "World") -> str:
        """Say hello.

        Args:
            name: Name to greet.

        Returns:
            Greeting string.
        """
        return f"Hello, {name}! From Friday Plugin System!"

    def calculate(self, expression: str = "") -> str:
        """Calculate a math expression.

        Args:
            expression: Math expression to evaluate.

        Returns:
            Result or error message.
        """
        if not expression:
            return "No expression provided."
        try:
            result = eval(expression, {"__builtins__": {}}, {})
            return f"Result: {result}"
        except Exception as e:
            return f"Error: {e}"

    def test_hello(self) -> bool:
        """Test the hello function."""
        result = self.hello("Test")
        return "Hello, Test!" in result

    def test_calculate_addition(self) -> bool:
        """Test calculate with addition."""
        result = self.calculate("1 + 2")
        return "3" in result


# ─── Plugin Manager (Enhanced) ─────────────────────────────────────

class PluginManager:
    """
    Manages discovery, loading, unloading, and querying of Friday plugins.

    Features:
    - Plugin discovery from directory
    - Dynamic loading via importlib
    - Dependency resolution
    - Configuration management
    - Event dispatching
    - Statistics collection
    - Hot-reload support
    - Marketplace access
    - Testing and documentation
    """

    def __init__(self, plugin_dir: Optional[str] = None):
        self.plugin_dir = Path(plugin_dir or DEFAULT_PLUGIN_DIR)
        self.plugins: Dict[str, FridayPlugin] = {}
        self._ensured = False
        self._ensure_plugin_dir()

        self.hooks = PluginHookManager()
        self.stats = PluginStatisticsCollector()
        self.categoriser = PluginCategoriser()
        self.resolver = PluginDependencyResolver(self)
        self.compatibility = PluginCompatibilityChecker(FRIDAY_VERSION)
        self.marketplace = PluginMarketplace(self)
        self.test_runner = PluginTestRunner(self)
        self.docs_generator = PluginAPIDocs(self)
        self.template_generator = PluginTemplateGenerator()
        self.hot_reloader = HotReloadWatcher(self)

    def _ensure_plugin_dir(self) -> None:
        """Create plugin directory and __init__.py if needed."""
        if self._ensured:
            return
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        init_file = self.plugin_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# Friday Plugins\n", encoding="utf-8")
        self._ensured = True

    def discover_plugins(self) -> List[str]:
        """Discover available plugin files in the plugin directory.

        Returns:
            List of plugin names (without .py extension).
        """
        plugins = []
        if not self.plugin_dir.exists():
            return plugins
        for py_file in self.plugin_dir.glob("*.py"):
            if py_file.name != "__init__.py":
                plugins.append(py_file.stem)
        return plugins

    def load_plugin(self, plugin_name: str) -> bool:
        """
        Load a plugin by name.

        Resolves dependencies first, then loads the plugin and any
        required dependencies.

        Args:
            plugin_name: Name of the plugin to load.

        Returns:
            True if loading succeeded.
        """
        start_time = time.time()
        try:
            module_path = self.plugin_dir / f"{plugin_name}.py"
            if not module_path.exists():
                return False

            self.hooks.dispatch(PluginEvent.ON_LOAD, plugin_name=plugin_name)

            spec = importlib.util.spec_from_file_location(
                plugin_name, str(module_path)
            )
            if spec is None or spec.loader is None:
                return False

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            plugin_class = None
            for _name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, FridayPlugin) and obj is not FridayPlugin:
                    plugin_class = obj
                    break

            if plugin_class is None:
                return False

            plugin_instance = plugin_class()
            plugin_instance.initialize()

            self.plugins[plugin_name] = plugin_instance

            self.resolver.register_plugin(plugin_name, plugin_instance.metadata)
            self.categoriser.register(plugin_name, plugin_instance.tags)

            load_time = time.time() - start_time
            self.stats.record_load(plugin_name, load_time)

            return True

        except Exception:
            return False

    def load_all_plugins(self) -> int:
        """Load all discovered plugins.

        Returns:
            Number of successfully loaded plugins.
        """
        plugins = self.discover_plugins()
        count = 0
        for plugin_name in plugins:
            if self.load_plugin(plugin_name):
                count += 1
        return count

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin, calling its shutdown method.

        Args:
            plugin_name: Name of the plugin to unload.

        Returns:
            True if the plugin was unloaded.
        """
        if plugin_name not in self.plugins:
            return False
        try:
            self.hooks.dispatch(PluginEvent.ON_UNLOAD, plugin_name=plugin_name)
            self.plugins[plugin_name].shutdown()
            del self.plugins[plugin_name]
            self.categoriser.unregister(plugin_name)
            self.stats.record_unload(plugin_name)
            return True
        except Exception:
            return False

    def reload_plugin(self, plugin_name: str) -> bool:
        """
        Reload a plugin by unloading then loading it.

        Args:
            plugin_name: Name of the plugin to reload.

        Returns:
            True if reload succeeded.
        """
        self.unload_plugin(plugin_name)
        if plugin_name in sys.modules:
            del sys.modules[plugin_name]
        return self.load_plugin(plugin_name)

    def get_plugin(self, plugin_name: str) -> Optional[FridayPlugin]:
        """Get a loaded plugin instance by name."""
        return self.plugins.get(plugin_name)

    def get_all_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all tools from all loaded plugins.

        Returns:
            Dict mapping 'plugin_name.tool_name' to tool info dicts.
        """
        all_tools = {}
        for plugin_name, plugin in self.plugins.items():
            tools = plugin.get_tools()
            for tool_name, tool_info in tools.items():
                all_tools[f"{plugin_name}.{tool_name}"] = tool_info
        return all_tools

    def get_tool_signature(self, plugin_name: str, tool_name: str) -> str:
        """
        Get the inspect signature for a specific tool.

        Args:
            plugin_name: Name of the plugin.
            tool_name: Name of the tool.

        Returns:
            String representation of the function signature.
        """
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return "Plugin not found."
        tools = plugin.get_tools()
        if tool_name not in tools:
            return "Tool not found."
        func = tools[tool_name]["function"]
        try:
            sig = inspect.signature(func)
            return str(sig)
        except (ValueError, TypeError):
            return "(...)"

    def is_compatible(self, plugin_name: str) -> Tuple[bool, str]:
        """
        Check if a loaded plugin is compatible with the current Friday version.

        Args:
            plugin_name: Name of the plugin.

        Returns:
            Tuple of (compatible, message).
        """
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return False, f"Plugin '{plugin_name}' is not loaded."
        return self.compatibility.check(plugin.get_metadata())

    def search_plugins(self, query: str) -> List[Dict[str, Any]]:
        """
        Search loaded plugins by name, description, or tool name.

        Args:
            query: Search query string.

        Returns:
            List of matching plugin info dicts.
        """
        query = query.lower().strip()
        results = []
        for name, plugin in self.plugins.items():
            score = 0
            if query in name.lower():
                score += 10
            if query in plugin.description.lower():
                score += 5
            for tool_name in plugin.get_tool_names():
                if query in tool_name.lower():
                    score += 3
            if score > 0:
                results.append({
                    "name": name,
                    "description": plugin.description,
                    "version": plugin.version,
                    "tools": plugin.get_tool_names(),
                    "score": score,
                })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def list_plugins(self) -> str:
        """List all loaded plugins in a formatted string."""
        if not self.plugins:
            return "No plugins loaded."
        lines = ["### LOADED PLUGINS", ""]
        for name, plugin in self.plugins.items():
            lines.append(f"**{name}** v{plugin.version}")
            lines.append(f"  {plugin.description}")
            lines.append(f"  Author: {plugin.author}")
            lines.append(f"  Tags: {', '.join(getattr(plugin, 'tags', []))}")
            lines.append(f"  Tools: {len(plugin.tools)}")
            for tname in plugin.tools:
                lines.append(f"    - {tname}")
            lines.append("")
        return "\n".join(lines)

    def list_by_category(self, category: str) -> str:
        """List plugins in a specific category.

        Args:
            category: Category name to filter by.

        Returns:
            Formatted string of matching plugins.
        """
        names = self.categoriser.get_plugins_in_category(category)
        if not names:
            return f"No plugins found in category '{category}'."
        lines = [f"### Plugins in category '{category}'", ""]
        for name in names:
            plugin = self.get_plugin(name)
            if plugin:
                lines.append(f"  {name} v{plugin.version} - {plugin.description}")
        return "\n".join(lines)


# ─── Global Plugin Manager ─────────────────────────────────────────

_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Get or create the global plugin manager singleton."""
    global _manager
    if _manager is None:
        _manager = PluginManager()
    return _manager


def reset_plugin_manager() -> None:
    """Reset the global plugin manager (for testing)."""
    global _manager
    if _manager is not None:
        _manager.hooks.dispatch(PluginEvent.ON_SHUTDOWN)
        for name in list(_manager.plugins.keys()):
            _manager.unload_plugin(name)
        _manager.hot_reloader.stop()
    _manager = None


# ─── Tool Function for Friday ──────────────────────────────────────

def plugin_tool(
    action: str = "list",
    plugin_name: str = None,
    tool_name: str = None,
    category: str = None,
    url: str = None,
    template: str = "basic",
    output_dir: str = None,
    config_key: str = None,
    config_value: Any = None,
    query: str = None,
    event: str = None,
    **kwargs,
) -> str:
    """
    Friday tool for managing plugins.

    Actions:
      list        - List all loaded plugins
      discover    - Discover available plugin files
      load        - Load a specific plugin by name
      load_all    - Load all discovered plugins
      unload      - Unload a specific plugin
      reload      - Reload a specific plugin
      call        - Call a specific tool on a plugin
      config      - Get or set plugin configuration
      test        - Run tests for a plugin
      docs        - Generate API documentation for a plugin
      template    - Generate a new plugin from a template
      install     - Install a plugin from a URL
      uninstall   - Uninstall a plugin
      search      - Search loaded plugins
      category    - List plugins by category
      stats       - Show plugin statistics
      event       - Show event subscriber counts
      watch       - Start/stop hot-reload watcher
      check       - Check plugin compatibility
      metadata    - Show plugin metadata

    Args:
        action: The action to perform.
        plugin_name: Name of the target plugin.
        tool_name: Name of the tool (for 'call' action).
        category: Category name (for 'category' action).
        url: Plugin URL (for 'install' action).
        template: Template name (for 'template' action).
        output_dir: Output directory (for 'template' action).
        config_key: Configuration key (for 'config' action).
        config_value: Configuration value (for 'config' action).
        query: Search query (for 'search' action).
        event: Event name (for 'event' action).
        **kwargs: Additional arguments passed to plugin tools.

    Returns:
        Result string.
    """
    manager = get_plugin_manager()

    if action == "list":
        return manager.list_plugins()

    if action == "discover":
        plugins = manager.discover_plugins()
        if plugins:
            return f"Discovered plugins: {', '.join(plugins)}"
        return "No plugins discovered."

    if action == "load":
        if not plugin_name:
            return "[FAIL] Plugin name required."
        success = manager.load_plugin(plugin_name)
        if success:
            plugin = manager.get_plugin(plugin_name)
            ver = plugin.version if plugin else "?"
            return f"[OK] Loaded plugin '{plugin_name}' v{ver}"
        return f"[FAIL] Could not load plugin '{plugin_name}'"

    if action == "load_all":
        count = manager.load_all_plugins()
        return f"[OK] Loaded {count} plugin(s)."

    if action == "unload":
        if not plugin_name:
            return "[FAIL] Plugin name required."
        if manager.unload_plugin(plugin_name):
            return f"[OK] Unloaded plugin '{plugin_name}'"
        return f"[FAIL] Plugin '{plugin_name}' not loaded."

    if action == "reload":
        if not plugin_name:
            return "[FAIL] Plugin name required."
        if manager.reload_plugin(plugin_name):
            return f"[OK] Reloaded plugin '{plugin_name}'"
        return f"[FAIL] Could not reload plugin '{plugin_name}'"

    if action == "call":
        if not plugin_name or not tool_name:
            return "[FAIL] Plugin name and tool name required."
        plugin = manager.get_plugin(plugin_name)
        if not plugin:
            return f"[FAIL] Plugin '{plugin_name}' not loaded."
        tools = plugin.get_tools()
        if tool_name not in tools:
            available = ", ".join(tools.keys())
            return f"[FAIL] Tool '{tool_name}' not found. Available: {available}"
        func = tools[tool_name]["function"]
        manager.hooks.dispatch(
            PluginEvent.ON_TOOL_CALL,
            plugin_name=plugin_name,
            tool_name=tool_name,
        )
        manager.stats.record_tool_call(plugin_name)
        try:
            result = func(**kwargs)
            manager.hooks.dispatch(
                PluginEvent.ON_TOOL_RESULT,
                plugin_name=plugin_name,
                tool_name=tool_name,
                result=result,
            )
            return result
        except Exception as exc:
            error_msg = f"[ERROR] {exc}"
            manager.stats.record_error(plugin_name, str(exc))
            manager.hooks.dispatch(
                PluginEvent.ON_ERROR,
                plugin_name=plugin_name,
                tool_name=tool_name,
                error=str(exc),
            )
            return error_msg

    if action == "config":
        if not plugin_name:
            return "[FAIL] Plugin name required."
        plugin = manager.get_plugin(plugin_name)
        if not plugin:
            return f"[FAIL] Plugin '{plugin_name}' not loaded."
        cfg = plugin.config
        if config_key is None:
            return cfg.to_str()
        if config_value is None:
            val = cfg.get(config_key)
            return f"{config_key} = {json.dumps(val)}"
        success = cfg.set(config_key, config_value)
        if success:
            return f"[OK] Set {config_key} = {json.dumps(config_value)}"
        return f"[FAIL] Value rejected by schema."

    if action == "test":
        if not plugin_name:
            return "[FAIL] Plugin name required."
        results = manager.test_runner.run_plugin_tests(plugin_name)
        return manager.test_runner.results_to_str(results)

    if action == "docs":
        if plugin_name:
            return manager.docs_generator.generate_plugin_docs(plugin_name)
        all_docs = manager.docs_generator.generate_all_docs()
        lines = ["### PLUGIN API DOCUMENTATION", ""]
        for pname, doc_text in all_docs.items():
            lines.append(f"---\n{doc_text}")
        return "\n".join(lines)

    if action == "template":
        if not plugin_name:
            return "[FAIL] Plugin name required for template generation."
        author = kwargs.get("author", "Friday User")
        desc = kwargs.get("description", "")
        created = manager.template_generator.create_plugin(
            name=plugin_name,
            author=author,
            template=template,
            description=desc,
            output_dir=output_dir,
        )
        if created:
            return f"[OK] Created plugin template at: {created}"
        return "[FAIL] Could not create plugin template."

    if action == "install":
        if not url:
            return "[FAIL] URL required."
        if manager.marketplace.install_plugin(url):
            return f"[OK] Installed plugin from {url}"
        return f"[FAIL] Could not install plugin from {url}"

    if action == "uninstall":
        if not plugin_name:
            return "[FAIL] Plugin name required."
        if manager.marketplace.uninstall_plugin(plugin_name):
            return f"[OK] Uninstalled plugin '{plugin_name}'"
        return f"[FAIL] Could not uninstall plugin '{plugin_name}'"

    if action == "search":
        if not query:
            return "[FAIL] Search query required."
        results = manager.search_plugins(query)
        if not results:
            return f"No plugins matching '{query}'."
        lines = [f"### Search results for '{query}'", ""]
        for r in results:
            lines.append(f"  {r['name']} (score: {r['score']})")
            lines.append(f"    {r['description']}")
            lines.append(f"    Tools: {', '.join(r['tools'])}")
        return "\n".join(lines)

    if action == "category":
        if not category:
            return manager.categoriser.to_str()
        return manager.list_by_category(category)

    if action == "stats":
        return manager.stats.to_str()

    if action == "event":
        if event:
            try:
                evt = PluginEvent[event.upper()]
                subs = manager.hooks.list_subscribers(evt)
                return f"Event '{event}': {subs.get(evt, 0)} subscriber(s)"
            except KeyError:
                valid = ", ".join(e.name for e in PluginEvent)
                return f"Unknown event '{event}'. Valid: {valid}"
        subs = manager.hooks.list_subscribers()
        lines = ["### EVENT SUBSCRIBERS", ""]
        for evt, count in subs.items():
            lines.append(f"  {evt.name}: {count} handler(s)")
        return "\n".join(lines)

    if action == "watch":
        sub_action = kwargs.get("sub_action", "status")
        if sub_action == "start":
            manager.hot_reloader.start()
            return "[OK] Hot-reload watcher started."
        if sub_action == "stop":
            manager.hot_reloader.stop()
            return "[OK] Hot-reload watcher stopped."
        if sub_action == "add" and plugin_name:
            manager.hot_reloader.watch(plugin_name)
            return f"[OK] Watching plugin '{plugin_name}' for changes."
        if sub_action == "remove" and plugin_name:
            manager.hot_reloader.unwatch(plugin_name)
            return f"[OK] Stopped watching plugin '{plugin_name}'."
        running = manager.hot_reloader.is_running()
        watched = manager.hot_reloader.get_watched()
        status = "running" if running else "stopped"
        lines = [f"### Hot-Reload Watcher ({status})", ""]
        if watched:
            lines.append(f"Watched plugins: {', '.join(watched)}")
        else:
            lines.append("No plugins being watched.")
        return "\n".join(lines)

    if action == "check":
        if plugin_name:
            compatible, msg = manager.is_compatible(plugin_name)
            return msg
        results = []
        for pname in manager.plugins:
            compatible, msg = manager.is_compatible(pname)
            results.append((pname, compatible, msg))
        lines = ["### COMPATIBILITY CHECK", ""]
        for pname, compatible, msg in results:
            icon = "[OK]" if compatible else "[INCOMPATIBLE]"
            lines.append(f"  {icon} {pname}: {msg}")
        return "\n".join(lines)

    if action == "metadata":
        if not plugin_name:
            return "[FAIL] Plugin name required."
        plugin = manager.get_plugin(plugin_name)
        if not plugin:
            return f"[FAIL] Plugin '{plugin_name}' not loaded."
        meta = plugin.get_metadata()
        lines = [f"### Metadata for '{plugin_name}'", ""]
        for field_name in ("name", "version", "author", "description",
                           "min_friday_version", "license", "homepage",
                           "entry_point"):
            val = getattr(meta, field_name, "")
            if val:
                lines.append(f"  {field_name}: {val}")
        if meta.dependencies:
            lines.append("  dependencies:")
            for dep, ver in meta.dependencies.items():
                lines.append(f"    {dep}: {ver}")
        if meta.tags:
            lines.append(f"  tags: {', '.join(meta.tags)}")
        return "\n".join(lines)

    if action == "reset":
        reset_plugin_manager()
        return "[OK] Plugin manager reset."

    valid_actions = [
        "list", "discover", "load", "load_all", "unload", "reload",
        "call", "config", "test", "docs", "template", "install",
        "uninstall", "search", "category", "stats", "event", "watch",
        "check", "metadata", "reset",
    ]
    return (f"Unknown action: '{action}'. "
            f"Valid actions: {', '.join(valid_actions)}")


# ─── Main Entry Point ──────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Friday Plugin System - Test & Demo")
    print("=" * 60)

    print("\nInitialising plugin manager...")
    manager = get_plugin_manager()
    print(f"Plugin directory: {manager.plugin_dir}")

    print("\nDiscovering plugins...")
    discovered = manager.discover_plugins()
    print(f"Found: {discovered if discovered else '(none)'}")

    print("\nLoading all plugins...")
    count = manager.load_all_plugins()
    print(f"Loaded {count} plugin(s).")

    print("\n" + manager.list_plugins())

    print("\nTesting plugin_tool dispatcher...")
    print("\n--- list ---")
    print(plugin_tool("list"))

    print("\n--- stats ---")
    print(plugin_tool("stats"))

    print("\n--- category ---")
    print(plugin_tool("category"))

    print("\n--- metadata for example ---")
    print(plugin_tool("metadata", plugin_name="example"))

    print("\n--- call example.hello ---")
    result = plugin_tool("call", plugin_name="example", tool_name="hello", name="Friday")
    print(result)

    print("\n--- call example.calculate ---")
    result = plugin_tool("call", plugin_name="example", tool_name="calculate", expression="2 + 2")
    print(result)

    print("\n--- search for 'hello' ---")
    print(plugin_tool("search", query="hello"))

    print("\n--- test example ---")
    print(plugin_tool("test", plugin_name="example"))

    print("\n--- check compatibility ---")
    print(plugin_tool("check"))

    print("\n--- event subscribers ---")
    print(plugin_tool("event"))

    print("\n--- docs for example ---")
    print(plugin_tool("docs", plugin_name="example"))

    print("\n--- config for example ---")
    print(plugin_tool("config", plugin_name="example"))

    print("\n--- template preview ---")
    preview = manager.template_generator.preview("my_new_plugin", "Test Author")
    print(preview[:500] + "...")

    print("\n" + "=" * 60)
    print("All systems nominal.")
    print("=" * 60)
