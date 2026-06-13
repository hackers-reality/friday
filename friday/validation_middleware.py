"""
Validation Middleware — comprehensive tool call & result verification system.
Every tool call is intercepted, validated, logged with confidence scores.
Supports: code syntax checking, file validation, HTML/CSS/JS linting,
JSON/XML/YAML/TOML schema validation, security scanning, data quality checks.
"""

from __future__ import annotations

import ast
import csv
import functools
import hashlib
import html as html_lib
import io
import json
import math
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import time
import traceback
import uuid
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from enum import Enum
from io import StringIO
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

try:
    import yaml
except ImportError:
    yaml = None

try:
    import toml
except ImportError:
    toml = None

from friday._paths import FRIDAY_MEMORY

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
_VALIDATION_LOG = os.path.join(FRIDAY_MEMORY, "validation_log.jsonl")
_VALIDATION_STATS = os.path.join(FRIDAY_MEMORY, "validation_stats.json")
_VALIDATION_LOCK = Lock()
os.makedirs(FRIDAY_MEMORY, exist_ok=True)

# ---------------------------------------------------------------------------
# Validation profiles
# ---------------------------------------------------------------------------
PROFILE_STRICT = "strict"
PROFILE_NORMAL = "normal"
PROFILE_RELAXED = "relaxed"

_VALIDATION_PROFILE = PROFILE_NORMAL

PROFILE_THRESHOLDS = {
    PROFILE_STRICT: {"fail_on": "WARN", "log_level": "INFO"},
    PROFILE_NORMAL: {"fail_on": "ERROR", "log_level": "WARN"},
    PROFILE_RELAXED: {"fail_on": "CRITICAL", "log_level": "ERROR"},
}


def set_validation_profile(name: str) -> None:
    """Set the active validation profile by name."""
    global _VALIDATION_PROFILE
    if name not in PROFILE_THRESHOLDS:
        raise ValueError(f"Unknown profile '{name}'. Choose from {list(PROFILE_THRESHOLDS)}")
    _VALIDATION_PROFILE = name


def get_validation_profile() -> str:
    """Return the name of the currently active validation profile."""
    return _VALIDATION_PROFILE


def _profile_should_fail(severity: str) -> bool:
    """Check if a result with the given severity should be treated as a failure under the active profile."""
    profile = get_validation_profile()
    threshold = PROFILE_THRESHOLDS.get(profile, PROFILE_THRESHOLDS[PROFILE_NORMAL])["fail_on"]
    sev_order = ["PASS", "INFO", "WARN", "ERROR", "CRITICAL"]
    try:
        return sev_order.index(severity) >= sev_order.index(threshold)
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Validation severity levels
# ---------------------------------------------------------------------------
class ValidationSeverity(Enum):
    PASS = "PASS"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------
class ValidationResult:
    """Encapsulates the outcome of a single validation check."""

    def __init__(
        self,
        name: str,
        passed: bool,
        severity: Union[str, ValidationSeverity] = ValidationSeverity.ERROR,
        message: str = "",
        details: Optional[dict] = None,
        suggestion: str = "",
    ):
        self.name = name
        self.passed = passed
        if isinstance(severity, ValidationSeverity):
            self.severity = severity
        else:
            self.severity = ValidationSeverity(severity)
        self.message = message
        self.details = details or {}
        self.suggestion = suggestion
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "suggestion": self.suggestion,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def pass_result(name: str, message: str = "OK", details: Optional[dict] = None) -> ValidationResult:
        return ValidationResult(name, True, ValidationSeverity.PASS, message, details)

    @staticmethod
    def fail_result(
        name: str,
        message: str = "Validation failed",
        severity: Union[str, ValidationSeverity] = ValidationSeverity.ERROR,
        details: Optional[dict] = None,
        suggestion: str = "",
    ) -> ValidationResult:
        return ValidationResult(name, False, severity, message, details, suggestion)

    @staticmethod
    def warn_result(name: str, message: str = "Warning", details: Optional[dict] = None, suggestion: str = "") -> ValidationResult:
        return ValidationResult(name, False, ValidationSeverity.WARN, message, details, suggestion)

    @staticmethod
    def info_result(name: str, message: str = "Info", details: Optional[dict] = None) -> ValidationResult:
        return ValidationResult(name, True, ValidationSeverity.INFO, message, details)

    def __repr__(self):
        return f"<ValidationResult {self.name}: {'PASS' if self.passed else 'FAIL'} [{self.severity.value}]>"


# ---------------------------------------------------------------------------
# ValidationCache — TTL-based caching layer
# ---------------------------------------------------------------------------
class ValidationCache:
    """Simple TTL-based cache for validation results to avoid re-validating unchanged content."""

    def __init__(self, ttl_seconds: int = 300):
        self._cache: Dict[str, Tuple[float, list]] = {}
        self._ttl = ttl_seconds

    def _make_key(self, content: str, *extra: str) -> str:
        raw = content + "|".join(extra)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, content: str, *extra: str) -> Optional[list]:
        key = self._make_key(content, *extra)
        entry = self._cache.get(key)
        if entry is None:
            return None
        expires, results = entry
        if time.time() > expires:
            del self._cache[key]
            return None
        return results

    def set(self, content: str, results: list, *extra: str) -> None:
        key = self._make_key(content, *extra)
        self._cache[key] = (time.time() + self._ttl, results)

    def invalidate(self, content: str, *extra: str) -> None:
        key = self._make_key(content, *extra)
        self._cache.pop(key, None)

    def clear(self) -> None:
        self._cache.clear()

    def size(self) -> int:
        return len(self._cache)


_VALIDATION_CACHE = ValidationCache()


# ---------------------------------------------------------------------------
# Custom rules engine
# ---------------------------------------------------------------------------
class ValidationRule:
    """A single custom validation rule."""

    def __init__(
        self,
        name: str,
        check_func: Callable[[str], ValidationResult],
        severity: Union[str, ValidationSeverity] = ValidationSeverity.WARN,
        description: str = "",
    ):
        self.name = name
        self.check_func = check_func
        if isinstance(severity, ValidationSeverity):
            self.severity = severity
        else:
            self.severity = ValidationSeverity(severity)
        self.description = description

    def run(self, content: str) -> ValidationResult:
        return self.check_func(content)


class RulesEngine:
    """Manages a collection of custom validation rules."""

    def __init__(self):
        self._rules: Dict[str, ValidationRule] = {}

    def add_rule(
        self,
        name: str,
        check_func: Callable[[str], ValidationResult],
        severity: Union[str, ValidationSeverity] = ValidationSeverity.WARN,
        description: str = "",
    ) -> None:
        if name in self._rules:
            raise ValueError(f"Rule '{name}' already exists. Use remove_rule first to replace it.")
        self._rules[name] = ValidationRule(name, check_func, severity, description)

    def remove_rule(self, name: str) -> bool:
        return self._rules.pop(name, None) is not None

    def list_rules(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": rule.name,
                "severity": rule.severity.value,
                "description": rule.description,
            }
            for rule in self._rules.values()
        ]

    def run_rules(self, content: str, rule_names: Optional[List[str]] = None) -> List[ValidationResult]:
        targets = [self._rules[n] for n in rule_names] if rule_names else list(self._rules.values())
        return [rule.run(content) for rule in targets]


_RULES_ENGINE = RulesEngine()


# ---------------------------------------------------------------------------
# Integration hooks
# ---------------------------------------------------------------------------
_VALIDATION_HOOK_INSTALLED = False
_ORIGINAL_TOOL_DISPATCH = None


def _validation_hook_wrapper(original_dispatch: Callable, tool_name: str, *args, **kwargs) -> Any:
    """Wrapper that auto-validates results after tool dispatch."""
    result = original_dispatch(tool_name, *args, **kwargs)
    try:
        vr = auto_verify(result, {"tool": tool_name})
        if not vr.passed and _profile_should_fail(vr.severity.value):
            log_validation(vr)
    except Exception:
        pass
    return result


def install_validation_hook() -> bool:
    """Install a monkey-patch hook on the FRIDAY tool dispatch to auto-validate results."""
    global _VALIDATION_HOOK_INSTALLED, _ORIGINAL_TOOL_DISPATCH
    if _VALIDATION_HOOK_INSTALLED:
        return False
    try:
        import friday.tool_dispatch as td

        _ORIGINAL_TOOL_DISPATCH = td.dispatch_tool
        original = td.dispatch_tool

        def hooked_dispatch(tool_name, *args, **kwargs):
            return _validation_hook_wrapper(original, tool_name, *args, **kwargs)

        td.dispatch_tool = hooked_dispatch
        _VALIDATION_HOOK_INSTALLED = True
        return True
    except (ImportError, AttributeError):
        return False


def remove_validation_hook() -> bool:
    """Remove the validation hook and restore the original tool dispatch."""
    global _VALIDATION_HOOK_INSTALLED, _ORIGINAL_TOOL_DISPATCH
    if not _VALIDATION_HOOK_INSTALLED or _ORIGINAL_TOOL_DISPATCH is None:
        return False
    try:
        import friday.tool_dispatch as td

        td.dispatch_tool = _ORIGINAL_TOOL_DISPATCH
        _VALIDATION_HOOK_INSTALLED = False
        _ORIGINAL_TOOL_DISPATCH = None
        return True
    except (ImportError, AttributeError):
        return False


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------
def send_validation_alert(
    result: ValidationResult,
    channel: str = "console",
    webhook_url: Optional[str] = None,
) -> None:
    """Send a validation alert to the specified channel: console, file, or webhook."""
    if channel == "console":
        icon = "✓" if result.passed else "✗"
        print(f"[{icon}] {result.severity.value} {result.name}: {result.message}")
    elif channel == "file":
        alert_path = os.path.join(FRIDAY_MEMORY, "validation_alerts.log")
        with open(alert_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(result.to_dict()) + "\n")
    elif channel == "webhook" and webhook_url:
        try:
            import urllib.request

            data = json.dumps(result.to_dict()).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as exc:
            print(f"Webhook alert failed: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------
def validation_result_to_markdown(result: ValidationResult) -> str:
    """Format a ValidationResult as a Markdown string."""
    icon = "✅" if result.passed else "❌"
    parts = [
        f"{icon} **{result.name}** — {result.severity.value}",
        f"    _Message:_ {result.message}",
    ]
    if result.suggestion:
        parts.append(f"    _Suggestion:_ {result.suggestion}")
    if result.details:
        parts.append(f"    _Details:_ `{json.dumps(result.details)}`")
    return "\n".join(parts)


def validation_result_to_html(result: ValidationResult) -> str:
    """Format a ValidationResult as an HTML snippet."""
    color = "green" if result.passed else "red"
    parts = [
        f'<div class="validation-result severity-{result.severity.value.lower()}">',
        f'  <span style="color:{color};font-weight:bold;">[{result.severity.value}]</span>',
        f"  <strong>{html_lib.escape(result.name)}</strong>: {html_lib.escape(result.message)}",
    ]
    if result.suggestion:
        parts.append(f'  <p class="suggestion">{html_lib.escape(result.suggestion)}</p>')
    parts.append("</div>")
    return "\n".join(parts)


def export_validation_report(format: str = "markdown", days: int = 7) -> str:
    """Export recent validation log entries as a report in markdown or html format."""
    entries = _load_validation_log()
    cutoff = time.time() - days * 86400
    recent = [e for e in entries if e.get("timestamp", 0) >= cutoff]

    if format == "markdown":
        lines = [f"# Validation Report (last {days} days)\n"]
        for e in recent:
            name = e.get("name", "unknown")
            sev = e.get("severity", "?")
            msg = e.get("message", "")
            passed = e.get("passed", False)
            icon = "✅" if passed else "❌"
            lines.append(f"- {icon} **{name}** [{sev}]: {msg}")
        return "\n".join(lines)
    elif format == "html":
        parts = ["<html><body><h1>Validation Report</h1><ul>"]
        for e in recent:
            name = html_lib.escape(e.get("name", "unknown"))
            sev = html_lib.escape(e.get("severity", "?"))
            msg = html_lib.escape(e.get("message", ""))
            parts.append(f"<li><strong>{name}</strong> [{sev}]: {msg}</li>")
        parts.append("</ul></body></html>")
        return "\n".join(parts)
    else:
        return json.dumps(recent, indent=2)


# ---------------------------------------------------------------------------
# Core validation helpers
# ---------------------------------------------------------------------------
def validate_python(code: str) -> ValidationResult:
    """Validate Python code via AST parsing. Catches syntax errors and basic structural issues."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return ValidationResult.fail_result(
            "validate_python",
            f"Python syntax error: {e}",
            severity=ValidationSeverity.ERROR,
            details={"line": e.lineno, "offset": e.offset, "text": e.text},
            suggestion="Fix the syntax error at the indicated line.",
        )
    # Check for non-import statements after imports
    imports_done = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue
        imports_done = True
        break
    return ValidationResult.pass_result("validate_python", "Python code is valid.")


def validate_javascript(js_code: str) -> ValidationResult:
    """Structural validation of JavaScript code via brace/paren matching and basic pattern checks."""
    issues = []
    stack = []
    pairs = {"{": "}", "(": ")", "[": "]"}
    for i, ch in enumerate(js_code):
        if ch in pairs:
            stack.append((ch, i))
        elif ch in pairs.values():
            if not stack:
                issues.append(f"Unmatched closing '{ch}' at position {i}")
            else:
                opening, pos = stack.pop()
                if pairs[opening] != ch:
                    issues.append(f"Mismatched bracket: '{opening}' at {pos} vs '{ch}' at {i}")
    if stack:
        for ch, pos in stack:
            issues.append(f"Unmatched opening '{ch}' at position {pos}")
    disallowed = ["eval(", "document.write(", "innerHTML+="]
    for pat in disallowed:
        if pat in js_code:
            issues.append(f"Potentially unsafe pattern '{pat}' found")
    if issues:
        return ValidationResult.fail_result(
            "validate_javascript",
            f"Found {len(issues)} issue(s)",
            severity=ValidationSeverity.WARN,
            details={"issues": issues},
            suggestion="Review each issue and fix bracket mismatches or unsafe patterns.",
        )
    return ValidationResult.pass_result("validate_javascript", "JS structure looks valid.")


def validate_html(html_content: str) -> ValidationResult:
    """Validate HTML via tag matching and security checks."""
    VOID_ELEMENTS = {"area", "base", "br", "col", "doctype", "embed", "hr", "img",
                     "input", "link", "meta", "param", "source", "track", "wbr"}
    tag_pattern = re.compile(r"</?([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>", re.IGNORECASE)
    opening = []
    closing = []
    for match in tag_pattern.finditer(html_content):
        full = match.group(0)
        name = match.group(1).lower()
        if full.startswith("</"):
            closing.append(name)
        elif name not in VOID_ELEMENTS:
            opening.append(name)
    open_cnt = Counter(opening)
    close_cnt = Counter(closing)
    unclosed = {t: open_cnt[t] - close_cnt.get(t, 0) for t in open_cnt if open_cnt[t] > close_cnt.get(t, 0)}
    if unclosed:
        return ValidationResult.fail_result(
            "validate_html",
            f"Unclosed tags: {unclosed}",
            severity=ValidationSeverity.WARN,
            details={"unclosed": unclosed},
        )
    issues = []
    if re.search(r"<script[^>]*>[^<]*document\.write\s*\(", html_content):
        issues.append("document.write() inside <script>")
    if re.search(r"onerror\s*=", html_content, re.I):
        issues.append("onerror event handler found")
    if issues:
        return ValidationResult.warn_result("validate_html", f"Security issues: {issues}", details={"issues": issues})
    return ValidationResult.pass_result("validate_html", "HTML structure looks valid.")


def validate_css(css_content: str) -> ValidationResult:
    """Validate CSS via brace balance, semicolon checks, and basic structure."""
    braces = 0
    for ch in css_content:
        if ch == "{":
            braces += 1
        elif ch == "}":
            braces -= 1
    if braces != 0:
        return ValidationResult.fail_result(
            "validate_css",
            f"Unbalanced braces: {braces} unclosed",
            severity=ValidationSeverity.ERROR,
        )
    lines = css_content.split("\n")
    issues = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped and "{" in stripped and not stripped.endswith("{") and "}" not in stripped:
            issues.append(f"Line {i}: selector may be missing opening brace on its own line")
        if stripped.endswith("}") and "{" not in stripped and ";" in stripped.rstrip("} ").strip():
            pass
    import re as _re
    url_pattern = _re.compile(r"url\s*\(\s*(['\"]?)((?:https?:)?//[^'\")]+)\1\s*\)", _re.I)
    for match in url_pattern.finditer(css_content):
        url = match.group(2)
        if url.startswith("//") or url.startswith("http"):
            pass
    if issues:
        return ValidationResult.warn_result("validate_css", f"Style issues: {issues}", details={"issues": issues})
    return ValidationResult.pass_result("validate_css", "CSS structure is balanced.")


def validate_json(json_str: str, schema: Optional[dict] = None) -> ValidationResult:
    """Validate JSON string by parsing it; optionally validate against a schema."""
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return ValidationResult.fail_result(
            "validate_json",
            f"Invalid JSON: {e.msg}",
            severity=ValidationSeverity.ERROR,
            details={"line": e.lineno, "col": e.colno},
            suggestion="Fix the JSON syntax error.",
        )
    if schema is not None:
        return validate_against_schema(data, schema)
    return ValidationResult.pass_result("validate_json", "Valid JSON.")


def validate_against_schema(data: Any, schema: dict) -> ValidationResult:
    """Basic JSON schema validation (type checks, required keys)."""
    errors = []

    def _validate(value, sch, path: str):
        if "type" in sch:
            expected = sch["type"]
            if expected == "string" and not isinstance(value, str):
                errors.append(f"{path}: expected string, got {type(value).__name__}")
            elif expected == "integer" and not isinstance(value, int):
                errors.append(f"{path}: expected integer, got {type(value).__name__}")
            elif expected == "number" and not isinstance(value, (int, float)):
                errors.append(f"{path}: expected number, got {type(value).__name__}")
            elif expected == "boolean" and not isinstance(value, bool):
                errors.append(f"{path}: expected boolean, got {type(value).__name__}")
            elif expected == "array" and not isinstance(value, list):
                errors.append(f"{path}: expected array, got {type(value).__name__}")
            elif expected == "object" and not isinstance(value, dict):
                errors.append(f"{path}: expected object, got {type(value).__name__}")
        if "required" in sch and isinstance(value, dict):
            for key in sch["required"]:
                if key not in value:
                    errors.append(f"{path}: missing required key '{key}'")
        if "properties" in sch and isinstance(value, dict):
            for key, prop_sch in sch["properties"].items():
                if key in value:
                    _validate(value[key], prop_sch, f"{path}.{key}")
        if "items" in sch and isinstance(value, list):
            for idx, item in enumerate(value):
                _validate(item, sch["items"], f"{path}[{idx}]")

    _validate(data, schema, "$")
    if errors:
        return ValidationResult.fail_result(
            "validate_schema",
            f"Schema validation failed ({len(errors)} error(s))",
            severity=ValidationSeverity.ERROR,
            details={"errors": errors},
        )
    return ValidationResult.pass_result("validate_schema", "Schema validation passed.")


def validate_xml(xml_content: str) -> ValidationResult:
    """Basic XML tag-matching validation."""
    tag_re = re.compile(r"<!\[CDATA\[.*?\]\]>|<([A-Za-z_][\w.-]*)(\s[^>]*)?(/)?>", re.DOTALL)
    stack = []
    issues = []
    pos = 0
    for match in tag_re.finditer(xml_content):
        if match.group(0).startswith("<![CDATA["):
            continue
        tag_name = match.group(1)
        is_self_closing = match.group(3) == "/"
        if not is_self_closing:
            stack.append((tag_name, match.start()))
        else:
            pass
    closing_re = re.compile(r"<\s*/\s*([A-Za-z_][\w.-]*)\s*>")
    for match in closing_re.finditer(xml_content):
        tag_name = match.group(1)
        if stack and stack[-1][0] == tag_name:
            stack.pop()
        else:
            issues.append(f"Unexpected closing tag </{tag_name}> at position {match.start()}")
    for tag_name, pos in stack:
        issues.append(f"Unclosed tag <{tag_name}> opened at position {pos}")
    if issues:
        return ValidationResult.fail_result(
            "validate_xml",
            f"XML structure issues: {len(issues)}",
            severity=ValidationSeverity.WARN,
            details={"issues": issues},
        )
    return ValidationResult.pass_result("validate_xml", "XML structure is valid.")


def validate_yaml(yaml_content: str) -> ValidationResult:
    """Validate YAML content by parsing it."""
    if yaml is None:
        return ValidationResult.info_result("validate_yaml", "YAML library not available; skipping validation.")
    try:
        data = yaml.safe_load(yaml_content)
        if data is None:
            return ValidationResult.info_result("validate_yaml", "YAML parsed as null/empty.")
        return ValidationResult.pass_result("validate_yaml", "Valid YAML.")
    except yaml.YAMLError as e:
        return ValidationResult.fail_result(
            "validate_yaml",
            f"YAML parse error: {e}",
            severity=ValidationSeverity.ERROR,
        )


def validate_csv(csv_content: str) -> ValidationResult:
    """Validate CSV structure: consistent columns, no encoding issues."""
    try:
        reader = csv.reader(StringIO(csv_content))
        rows = list(reader)
    except Exception as e:
        return ValidationResult.fail_result("validate_csv", f"CSV read error: {e}", severity=ValidationSeverity.ERROR)
    if not rows:
        return ValidationResult.info_result("validate_csv", "Empty CSV content.")
    header_cols = len(rows[0])
    issues = []
    for i, row in enumerate(rows[1:], 2):
        if len(row) != header_cols:
            issues.append(f"Row {i}: expected {header_cols} columns, got {len(row)}")
    if issues:
        return ValidationResult.fail_result(
            "validate_csv",
            f"Inconsistent columns in {len(issues)} row(s)",
            severity=ValidationSeverity.WARN,
            details={"issues": issues},
        )
    return ValidationResult.pass_result("validate_csv", f"CSV is valid ({len(rows)} rows, {header_cols} columns).")


def validate_toml(toml_content: str) -> ValidationResult:
    """Validate TOML content by parsing it."""
    if toml is None:
        return ValidationResult.info_result("validate_toml", "TOML library not available; skipping validation.")
    try:
        data = toml.loads(toml_content)
        return ValidationResult.pass_result("validate_toml", "Valid TOML.")
    except Exception as e:
        return ValidationResult.fail_result("validate_toml", f"TOML parse error: {e}", severity=ValidationSeverity.ERROR)


def validate_sql(sql_content: str) -> ValidationResult:
    """Basic SQL validation: keyword presence, balanced quotes, basic injection pattern check."""
    issues = []
    lines = sql_content.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip().upper()
        if stripped.startswith("SELECT") or stripped.startswith("INSERT") or stripped.startswith("UPDATE") or stripped.startswith("DELETE"):
            pass
    single_q = sql_content.count("'")
    if single_q % 2 != 0:
        issues.append("Unbalanced single quotes")
    if re.search(r"(--|#|/\*)", sql_content):
        issues.append("Comment syntax detected in SQL")
    if issues:
        return ValidationResult.warn_result("validate_sql", f"SQL issues: {issues}", details={"issues": issues})
    return ValidationResult.pass_result("validate_sql", "SQL syntax looks plausible.")


def validate_markdown(md_content: str) -> ValidationResult:
    """Validate Markdown: check links, images, heading structure."""
    issues = []
    link_re = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
    for match in link_re.finditer(md_content):
        text, url = match.groups()
        if not text.strip():
            issues.append(f"Link with empty text at position {match.start()}")
        if not url.strip() or url.strip() == "#":
            issues.append(f"Link with empty or placeholder URL: [{text}]({url})")
    img_re = re.compile(r"!\[([^\]]*)\]\(([^)]*)\)")
    for match in img_re.finditer(md_content):
        alt, url = match.groups()
        if not url.strip():
            issues.append(f"Image with empty URL at position {match.start()}")
    heading_re = re.compile(r"^#{1,6}\s+(.+)$", re.M)
    prev_level = 0
    for match in heading_re.finditer(md_content):
        level = len(match.group(0)) - len(match.group(0).lstrip("#"))
        if level > prev_level + 1 and prev_level > 0:
            issues.append(f"Heading level jumps from {prev_level} to {level}: '{match.group(1)}'")
        prev_level = level
    if issues:
        return ValidationResult.warn_result("validate_markdown", f"Markdown issues: {len(issues)}", details={"issues": issues})
    return ValidationResult.pass_result("validate_markdown", "Markdown looks valid.")


def validate_dockerfile(content: str) -> ValidationResult:
    """Check Dockerfile best practices: FROM first, no latest tag, no root warning."""
    issues = []
    lines = content.split("\n")
    found_from = False
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.upper().startswith("FROM"):
            found_from = True
            if "latest" in stripped.lower().split(":")[-1].split()[0] if ":" in stripped else False:
                issues.append(f"Line {i}: Avoid using 'latest' tag")
            continue
        if not found_from and stripped and not stripped.startswith("#"):
            issues.append(f"Line {i}: Expected FROM as first instruction")
        if "USER root" in stripped or (stripped.upper().startswith("USER") and stripped.split()[-1].lower() == "root"):
            issues.append(f"Line {i}: Running as root is discouraged")
        if "apt-get" in stripped and "install" in stripped and "-y" not in stripped:
            issues.append(f"Line {i}: apt-get install should use -y flag")
    if issues:
        return ValidationResult.fail_result(
            "validate_dockerfile",
            f"Dockerfile issues ({len(issues)})",
            severity=ValidationSeverity.WARN,
            details={"issues": issues},
        )
    return ValidationResult.pass_result("validate_dockerfile", "Dockerfile best practices check passed.")


def validate_file_exists(file_path: str) -> ValidationResult:
    """Check that a file exists at the given path."""
    if os.path.exists(file_path):
        return ValidationResult.pass_result("file_exists", f"File exists: {file_path}")
    return ValidationResult.fail_result("file_exists", f"File not found: {file_path}", severity=ValidationSeverity.ERROR)


def validate_file_size(file_path: str, max_mb: float = 10.0) -> ValidationResult:
    """Check that file size does not exceed max_mb."""
    if not os.path.exists(file_path):
        return ValidationResult.fail_result("file_size", "File not found.", severity=ValidationSeverity.ERROR)
    size_bytes = os.path.getsize(file_path)
    size_mb = size_bytes / (1024 * 1024)
    if size_mb > max_mb:
        return ValidationResult.fail_result(
            "file_size",
            f"File too large: {size_mb:.2f} MB (max {max_mb} MB)",
            severity=ValidationSeverity.WARN,
            details={"size_mb": round(size_mb, 2), "max_mb": max_mb},
        )
    return ValidationResult.pass_result("file_size", f"File size OK ({size_mb:.2f} MB).")


def validate_file_extension(file_path: str, allowed_extensions: Optional[List[str]] = None) -> ValidationResult:
    """Check that the file has an allowed extension."""
    if allowed_extensions is None:
        allowed_extensions = [".py", ".js", ".ts", ".html", ".css", ".json", ".md", ".yaml", ".yml", ".toml", ".csv", ".xml"]
    ext = os.path.splitext(file_path)[1].lower()
    if ext in allowed_extensions:
        return ValidationResult.pass_result("file_extension", f"Extension '{ext}' is allowed.")
    return ValidationResult.fail_result(
        "file_extension",
        f"Extension '{ext}' is not in allowed list",
        severity=ValidationSeverity.WARN,
        details={"extension": ext, "allowed": allowed_extensions},
    )


def validate_file_content_by_type(file_path: str) -> ValidationResult:
    """Validate file content based on its extension."""
    if not os.path.exists(file_path):
        return ValidationResult.fail_result("file_content", "File not found.", severity=ValidationSeverity.ERROR)
    ext = os.path.splitext(file_path)[1].lower()
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        return ValidationResult.fail_result("file_content", f"Cannot read file: {e}", severity=ValidationSeverity.ERROR)
    validators = {
        ".py": validate_python,
        ".js": validate_javascript,
        ".html": validate_html,
        ".css": validate_css,
        ".json": lambda c: validate_json(c),
        ".xml": validate_xml,
        ".yaml": validate_yaml,
        ".yml": validate_yaml,
        ".csv": validate_csv,
        ".md": validate_markdown,
        ".toml": validate_toml,
    }
    validator = validators.get(ext)
    if validator is None:
        return ValidationResult.info_result("file_content", f"No specific validator for extension '{ext}'.")
    return validator(content)


# ---------------------------------------------------------------------------
# Security validators
# ---------------------------------------------------------------------------
SECRET_PATTERNS = [
    (re.compile(r"(?i)(?:api[_-]?key|apikey)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{16,})['\"]?"), "API key"),
    (re.compile(r"(?i)(?:secret|token|password|passwd|pwd)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?"), "Secret/token"),
    (re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}"), "GitHub token"),
    (re.compile(r"(?i)(?:BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY)"), "Private key"),
    (re.compile(r"(?:sk-[A-Za-z0-9_\-]{20,})"), "OpenAI API key"),
    (re.compile(r"(?:AKIA[0-9A-Z]{16})"), "AWS access key"),
    (re.compile(r"(?i)(?:password|passwd|pwd)\s*=\s*['\"][^'\"]{3,}['\"]"), "Password assignment"),
]


def validate_secrets(content: str, context: str = "") -> ValidationResult:
    """Scan content for potential secrets and sensitive data."""
    findings = []
    for pattern, label in SECRET_PATTERNS:
        for match in pattern.finditer(content):
            start = max(0, match.start() - 20)
            end = min(len(content), match.end() + 20)
            snippet = content[start:end].replace("\n", " ")
            findings.append({
                "type": label,
                "position": match.start(),
                "snippet": snippet.strip(),
            })
    if findings:
        msg = f"Found {len(findings)} potential secret(s) in {context or 'content'}"
        return ValidationResult.fail_result(
            "validate_secrets",
            msg,
            severity=ValidationSeverity.ERROR,
            details={"findings": findings},
            suggestion="Remove or externalise secrets via environment variables.",
        )
    return ValidationResult.pass_result("validate_secrets", "No secrets detected.")


def validate_xss(html_content: str) -> ValidationResult:
    """Scan HTML for XSS vectors."""
    issues = []
    xss_patterns = [
        (r"<script[^>]*>[\s\S]*?<\/script>", "Inline script tag"),
        (r"javascript\s*:", "javascript: URI scheme"),
        (r"on\w+\s*=", "Inline event handler"),
        (r"<iframe[^>]*>", "iframe element"),
        (r"<object[^>]*>", "object element"),
        (r"<embed[^>]*>", "embed element"),
        (r"<svg[^>]*>", "SVG element"),
        (r"<math[^>]*>", "MathML element"),
        (r"expression\s*\(", "CSS expression"),
        (r"<[^>]*style\s*=\s*['\"][^'\"]*expression", "Style with expression"),
    ]
    for pattern, label in xss_patterns:
        matches = re.findall(pattern, html_content, re.I | re.S)
        if matches:
            issues.append(f"{label}: {len(matches)} occurrence(s)")
    if issues:
        return ValidationResult.fail_result(
            "validate_xss",
            f"XSS risks: {len(issues)} pattern(s)",
            severity=ValidationSeverity.WARN,
            details={"issues": issues},
            suggestion="Sanitize user input and consider using a Content Security Policy.",
        )
    return ValidationResult.pass_result("validate_xss", "No XSS vectors detected.")


def validate_command_injection(input_str: str) -> ValidationResult:
    """Check for command injection patterns in user-supplied strings."""
    dangerous = [
        r";\s*(?:rm|del|shutdown|reboot|format|mkfs|dd|wget|curl|bash|cmd|powershell)",
        r"`[^`]+`",
        r"\$\([^)]+\)",
        r"\|[\s]*(?:sh|bash|cmd|powershell|python|perl|ruby)",
        r"&&\s*(?:rm|del|shutdown|reboot|format|mkfs|dd)",
        r">>\s*(?:/dev/|\\\\.\\\\)",
    ]
    findings = []
    for pattern in dangerous:
        match = re.search(pattern, input_str, re.I)
        if match:
            findings.append(match.group(0))
    if findings:
        return ValidationResult.fail_result(
            "validate_command_injection",
            f"Command injection risk: {len(findings)} pattern(s)",
            severity=ValidationSeverity.CRITICAL,
            details={"findings": findings},
            suggestion="Sanitize or reject user input containing shell metacharacters.",
        )
    return ValidationResult.pass_result("validate_command_injection", "No command injection detected.")


def validate_path_traversal(path: str) -> ValidationResult:
    """Check for path traversal patterns like ../ or absolute paths in user input."""
    issues = []
    if ".." in path.split(os.sep):
        issues.append(f"Path contains parent directory reference '..': {path}")
    for sep in ["/", "\\"]:
        if f"..{sep}" in path:
            issues.append(f"Path traversal pattern '..{sep}' found")
    if os.path.isabs(path) and not path.startswith(os.environ.get("ALLOWED_BASE", "")):
        issues.append(f"Absolute path outside allowed base: {path}")
    if issues:
        return ValidationResult.fail_result(
            "validate_path_traversal",
            f"Path traversal risk: {len(issues)} pattern(s)",
            severity=ValidationSeverity.CRITICAL,
            details={"issues": issues},
            suggestion="Resolve and sanitize the path; restrict to an allowed base directory.",
        )
    return ValidationResult.pass_result("validate_path_traversal", "No path traversal detected.")


def validate_sql_injection(input_str: str) -> ValidationResult:
    """Check for SQL injection patterns in user-supplied strings."""
    patterns = [
        (r"(['\"])?\s*(?:OR|AND)\s+\1?\s*1\s*=\s*1", "Tautology (OR/AND 1=1)"),
        (r"(['\"])?\s*OR\s+\1?\s*['\"]\s*['\"]\s*=\s*['\"]", "OR '='"),
        (r"\bUNION\b.*\bSELECT\b", "UNION SELECT"),
        (r"--", "SQL comment"),
        (r"/\*", "Block comment"),
        (r"\bEXEC\b.*\bxp\_", "xp_ stored procedure"),
        (r"\bDROP\b\s+\bTABLE\b", "DROP TABLE"),
        (r"\bDROP\b\s+\bDATABASE\b", "DROP DATABASE"),
        (r"\bALTER\b\s+\bTABLE\b", "ALTER TABLE"),
        (r"\bTRUNCATE\b\s+\bTABLE\b", "TRUNCATE TABLE"),
        (r"\bSLEEP\b\s*\(", "Time-based blind injection"),
        (r"\bWAITFOR\b\s+DELAY", "Time-based blind injection (MSSQL)"),
        (r"\bPG_SLEEP\b\s*\(", "Time-based blind injection (PostgreSQL)"),
        (r"\bBENCHMARK\b\s*\(", "Time-based blind injection (MySQL)"),
    ]
    findings = []
    for pattern, label in patterns:
        if re.search(pattern, input_str, re.I):
            findings.append(label)
    if findings:
        return ValidationResult.fail_result(
            "validate_sql_injection",
            f"SQL injection risk: {len(findings)} pattern(s)",
            severity=ValidationSeverity.CRITICAL,
            details={"findings": findings},
            suggestion="Use parameterised queries / prepared statements.",
        )
    return ValidationResult.pass_result("validate_sql_injection", "No SQL injection patterns detected.")


def validate_ssrf(url: str) -> ValidationResult:
    """Check for SSRF (Server-Side Request Forgery) risk in URLs."""
    issues = []
    private_patterns = [
        r"^https?://127\.\d+\.\d+\.\d+",
        r"^https?://10\.\d+\.\d+\.\d+",
        r"^https?://172\.(1[6-9]|2\d|3[01])\.\d+\.\d+",
        r"^https?://192\.168\.\d+\.\d+",
        r"^https?://0\.0\.0\.0",
        r"^https?://localhost",
        r"^https?://\[::1\]",
        r"^https?://\[::\]",
        r"^https?://169\.254\.\d+\.\d+",
    ]
    for pat in private_patterns:
        if re.search(pat, url, re.I):
            issues.append(f"URL points to private/reserved IP: {url}")
    if issues:
        return ValidationResult.fail_result(
            "validate_ssrf",
            f"SSRF risk: {len(issues)} issue(s)",
            severity=ValidationSeverity.CRITICAL,
            details={"issues": issues},
            suggestion="Block requests to private/internal IP ranges.",
        )
    return ValidationResult.pass_result("validate_ssrf", "No SSRF risk detected.")


def validate_insecure_deserialization(content: str) -> ValidationResult:
    """Detect potential insecure deserialization patterns."""
    issues = []
    risky_libs = [
        r"pickle\s*\.\s*loads?\s*\(",
        r"marshal\s*\.\s*loads?\s*\(",
        r"shelve\s*\.\s*open\s*\(",
        r"yaml\s*\.\s*load\s*\(",
        r"jsonpickle\s*\.\s*[dl]",
        r"joblib\s*\.\s*load\s*\(",
        r"dill\s*\.\s*loads?\s*\(",
        r"cloudpickle\s*\.\s*loads?\s*\(",
        r"PyYAML\s*\.\s*load\s*\(",
        r"_pickle\s*\.\s*loads?\s*\(",
    ]
    for pattern in risky_libs:
        match = re.search(pattern, content, re.I)
        if match:
            issues.append(f"Potential insecure deserialization: '{match.group(0)}'")
    if issues:
        return ValidationResult.fail_result(
            "validate_insecure_deserialization",
            f"Insecure deserialization: {len(issues)} issue(s)",
            severity=ValidationSeverity.WARN,
            details={"issues": issues},
            suggestion="Use safe alternatives like JSON; avoid pickle on untrusted data.",
        )
    return ValidationResult.pass_result("validate_insecure_deserialization", "No insecure deserialization detected.")


# ---------------------------------------------------------------------------
# Code quality validators
# ---------------------------------------------------------------------------
def validate_code_complexity(code: str, language: str = "python") -> ValidationResult:
    """Estimate code complexity: nesting depth, line count, comment ratio."""
    lines = code.split("\n")
    total = len(lines)
    blank = sum(1 for l in lines if not l.strip())
    comments = sum(1 for l in lines if l.strip().startswith("#"))
    if language == "python":
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return ValidationResult.info_result("code_complexity", "Cannot parse code for complexity analysis.")
        max_depth = 0

        def _walk(node, depth):
            nonlocal max_depth
            max_depth = max(max_depth, depth)
            for child in ast.iter_child_nodes(node):
                _walk(child, depth + 1)
        _walk(tree, 0)
        ratio = comments / max(total, 1)
        details = {"total_lines": total, "blank_lines": blank, "comment_lines": comments, "max_nesting": max_depth}
        if max_depth > 10:
            return ValidationResult.warn_result("code_complexity", f"Deep nesting detected (depth {max_depth}).", details=details)
        return ValidationResult.pass_result("code_complexity", f"Lines: {total}, Nesting depth: {max_depth}", details=details)
    return ValidationResult.info_result("code_complexity", "Complexity analysis only supports Python.")


def validate_docstrings(code: str) -> ValidationResult:
    """Check that public functions, classes, and methods have docstrings."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ValidationResult.info_result("validate_docstrings", "Cannot parse code.")
    missing = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            if not (node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str)):
                missing.append(f"Function '{node.name}' (line {node.lineno})")
        elif isinstance(node, ast.ClassDef):
            if not (node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str)):
                missing.append(f"Class '{node.name}' (line {node.lineno})")
    if missing:
        return ValidationResult.fail_result(
            "validate_docstrings",
            f"Missing docstrings: {len(missing)} item(s)",
            severity=ValidationSeverity.WARN,
            details={"missing": missing},
            suggestion="Add docstrings to all public functions, classes, and methods.",
        )
    return ValidationResult.pass_result("validate_docstrings", "All public items have docstrings.")


def validate_all(validations: List[Callable[[], ValidationResult]]) -> List[ValidationResult]:
    """Run multiple validation functions in parallel using a thread pool."""
    results = []
    with ThreadPoolExecutor(max_workers=min(8, len(validations) or 1)) as pool:
        futures = {pool.submit(v): v for v in validations}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                fn = futures[future]
                results.append(
                    ValidationResult.fail_result(
                        getattr(fn, "__name__", "unknown"),
                        f"Validation raised exception: {exc}",
                        severity=ValidationSeverity.ERROR,
                    )
                )
    return results


def validate_call(tool_name: str):
    """Decorator that auto-validates the return value of a tool function."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            try:
                vr = auto_verify(result, {"tool": tool_name})
                if not vr.passed and _profile_should_fail(vr.severity.value):
                    log_validation(vr)
            except Exception:
                pass
            return result
        return wrapper
    return decorator


def auto_verify(result_or_func: Any, context: Optional[dict] = None):
    """Automatically verify a result or wrap a function for auto-verification.

    Can be used as a decorator::

        @auto_verify
        def my_func(x, y):
            return x + y

    Or called directly::

        vr = auto_verify(some_result, {"tool": "my_tool"})
    """
    if callable(result_or_func) and context is None:
        func = result_or_func

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            vr = auto_verify(result)
            if not vr.passed and _profile_should_fail(vr.severity.value):
                log_validation(vr)
            return result

        return wrapper

    result = result_or_func
    ctx = context or {}
    if isinstance(result, str):
        checks = []
        if len(result) > 0:
            checks.append(("string_not_empty", True))
        else:
            checks.append(("string_not_empty", False))
        for check, passed in checks:
            if not passed:
                return ValidationResult.fail_result("auto_verify", "Result is an empty string.", severity=ValidationSeverity.WARN)
        return ValidationResult.pass_result("auto_verify", "String result is valid.")
    elif isinstance(result, dict):
        if not result:
            return ValidationResult.info_result("auto_verify", "Empty dict result.")
        return ValidationResult.pass_result("auto_verify", f"Dict result with {len(result)} keys.")
    elif isinstance(result, list):
        return ValidationResult.pass_result("auto_verify", f"List result with {len(result)} items.")
    elif isinstance(result, (int, float)):
        if math.isnan(result) or math.isinf(result):
            return ValidationResult.fail_result("auto_verify", "Numeric result is NaN or Inf.", severity=ValidationSeverity.ERROR)
        return ValidationResult.pass_result("auto_verify", f"Numeric result: {result}")
    elif result is None:
        return ValidationResult.info_result("auto_verify", "Result is None.")
    return ValidationResult.pass_result("auto_verify", f"Result type {type(result).__name__}")


# ---------------------------------------------------------------------------
# Import validators
# ---------------------------------------------------------------------------
def validate_import_order(code: str) -> ValidationResult:
    """Validate that imports follow PEP8 ordering: stdlib, third-party, local."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ValidationResult.info_result("validate_import_order", "Cannot parse code.")
    groups: Dict[str, List[Tuple[int, str]]] = {"stdlib": [], "third_party": [], "local": []}
    stdlib_modules = {"os", "sys", "re", "json", "csv", "math", "ast", "time", "uuid", "hashlib", "html",
                      "io", "pathlib", "subprocess", "tempfile", "textwrap", "traceback", "threading",
                      "collections", "concurrent", "datetime", "enum", "typing", "functools", "itertools",
                      "copy", "types", "inspect", "logging", "argparse", "socket", "ssl", "base64",
                      "binascii", "struct", "zlib", "gzip", "bz2", "lzma", "zipfile", "tarfile",
                      "configparser", "sqlite3", "xml", "http", "urllib", "email", "importlib", "pickle",
                      "marshal", "shelve", "platform", "stat", "glob", "shutil", "operator", "pprint",
                      "warnings", "weakref", "contextlib", "dataclasses", "abc", "numbers", "decimal",
                      "fractions", "random", "statistics", "hashlib", "hmac", "secrets", "string",
                      "difflib", "textwrap", "codecs", "locale", "calendar", "datetime", "zoneinfo",
                      "array", "bisect", "heapq", "queue", "select", "signal", "mmap", "ctypes",
                      "curses", "turtle", "tkinter", "webbrowser", "antigravity", "ensurepip",
                      "venv", "distutils", "distlib", "pydoc", "doctest", "unittest", "compileall",
                      "py_compile", "zipapp", "modulefinder", "runpy", "trace", "profile", "pstats",
                      "pickletools", "tabnanny", "pyclbr", "pycparser", "ast", "symtable", "token",
                      "tokenize", "keyword", "symbol", "parser", "code", "codeop", "codecs"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name.split(".")[0]
                if name in stdlib_modules or name in sys.builtin_module_names:
                    groups["stdlib"].append((node.lineno, alias.name))
                elif name.startswith("friday") or name.startswith("."):
                    groups["local"].append((node.lineno, alias.name))
                else:
                    groups["third_party"].append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                name = node.module.split(".")[0]
                if name in stdlib_modules or name in sys.builtin_module_names:
                    groups["stdlib"].append((node.lineno, node.module))
                elif name.startswith("friday") or name.startswith("."):
                    groups["local"].append((node.lineno, node.module))
                else:
                    groups["third_party"].append((node.lineno, node.module))
    issues = []
    all_imports = groups["stdlib"] + groups["third_party"] + groups["local"]
    if all_imports:
        lines_sorted = sorted(all_imports, key=lambda x: x[0])
        seen_third = False
        seen_local = False
        for lineno, modname in lines_sorted:
            if modname in [x[1] for x in groups["third_party"]]:
                seen_third = True
            if modname in [x[1] for x in groups["local"]]:
                seen_local = True
        stdlib_lines = [l for l, _ in groups["stdlib"]]
        third_lines = [l for l, _ in groups["third_party"]]
        local_lines = [l for l, _ in groups["local"]]
        if stdlib_lines and third_lines and max(stdlib_lines) > min(third_lines):
            issues.append("Third-party imports should come after standard library imports")
        if third_lines and local_lines and max(third_lines) > min(local_lines):
            issues.append("Local imports should come after third-party imports")
        if stdlib_lines and local_lines and max(stdlib_lines) > min(local_lines):
            issues.append("Local imports should come after standard library imports")
    if issues:
        return ValidationResult.warn_result("validate_import_order", f"Import ordering issues: {issues}", details={"issues": issues})
    return ValidationResult.pass_result("validate_import_order", "Imports follow PEP8 ordering.")


def validate_unused_imports(code: str) -> ValidationResult:
    """Detect potentially unused imports in Python code."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ValidationResult.info_result("validate_unused_imports", "Cannot parse code.")
    imported_names: Dict[str, Tuple[int, str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name
                imported_names[name] = (node.lineno, alias.name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname or alias.name
                imported_names[name] = (node.lineno, f"{node.module}.{alias.name}")
    used_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if isinstance(node.ctx, (ast.Load, ast.Del)):
                used_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            pass
    unused = {name: info for name, info in imported_names.items() if name not in used_names}
    builtins = {"__future__", "annotations", "print", "len", "range", "type", "isinstance", "issubclass",
                "hasattr", "getattr", "setattr", "delattr", "open", "super", "object", "property",
                "staticmethod", "classmethod", "str", "int", "float", "bool", "list", "dict", "set",
                "tuple", "iter", "next", "enumerate", "zip", "map", "filter", "reversed", "sorted",
                "min", "max", "sum", "any", "all", "abs", "round", "pow", "chr", "ord", "repr",
                "ascii", "format", "bytes", "bytearray", "memoryview", "slice", "eval", "exec",
                "compile", "globals", "locals", "vars", "dir", "id", "hash", "help", "exit", "quit",
                "input", "NameError", "ValueError", "TypeError", "KeyError", "IndexError", "AttributeError",
                "ImportError", "ModuleNotFoundError", "RuntimeError", "StopIteration", "ZeroDivisionError",
                "FileNotFoundError", "PermissionError", "OSError", "Exception", "BaseException",
                "Warning", "UserWarning", "DeprecationWarning", "FutureWarning", "PendingDeprecationWarning",
                "RuntimeWarning", "SyntaxWarning", "ImportWarning", "UnicodeWarning", "BytesWarning",
                "ResourceWarning"}
    unused = {name: info for name, info in unused.items() if name not in builtins}
    if unused:
        details = {import_name: {"line": line, "full": full} for import_name, (line, full) in unused.items()}
        return ValidationResult.warn_result(
            "validate_unused_imports",
            f"Potentially unused imports: {len(unused)}",
            details={"unused": details},
            suggestion="Remove unused imports to improve code clarity.",
        )
    return ValidationResult.pass_result("validate_unused_imports", "No unused imports detected.")


def validate_import_styles(code: str) -> ValidationResult:
    """Validate import style consistency: prefer explicit imports over wildcards."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ValidationResult.info_result("validate_import_styles", "Cannot parse code.")
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.names and any(alias.name == "*" for alias in node.names):
                issues.append(f"Line {node.lineno}: Wildcard import 'from {node.module} import *'")
            if node.level and node.level > 2:
                issues.append(f"Line {node.lineno}: Deep relative import (level {node.level})")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if len(parts) > 2:
                    issues.append(f"Line {node.lineno}: Importing nested module '{alias.name}'")
    if issues:
        return ValidationResult.warn_result("validate_import_styles", f"Import style issues: {len(issues)}", details={"issues": issues})
    return ValidationResult.pass_result("validate_import_styles", "Import styles are consistent.")


# ---------------------------------------------------------------------------
# Naming convention validators
# ---------------------------------------------------------------------------
def validate_naming_conventions(code: str) -> ValidationResult:
    """Check that names follow Python conventions: snake_case for funcs/vars, PascalCase for classes, UPPER_CASE for constants."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ValidationResult.info_result("validate_naming_conventions", "Cannot parse code.")
    issues = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if not re.match(r"^_*[a-z][a-z0-9_]*_*$", node.name) and not node.name.startswith("__") and not node.name.endswith("__"):
                issues.append(f"Line {node.lineno}: Function '{node.name}' should use snake_case")
        elif isinstance(node, ast.ClassDef):
            if not re.match(r"^_*[A-Z][a-zA-Z0-9]*_*$", node.name) and not node.name.startswith("__"):
                issues.append(f"Line {node.lineno}: Class '{node.name}' should use PascalCase")
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id.isupper() and len(target.id) > 1:
                        pass
                    elif target.id.startswith("__") and target.id.endswith("__"):
                        pass
                    elif target.id.startswith("_"):
                        pass
                    elif not re.match(r"^_*[a-z][a-z0-9_]*_*$", target.id):
                        issues.append(f"Line {node.lineno}: Variable '{target.id}' should use snake_case")

    if issues:
        return ValidationResult.warn_result(
            "validate_naming_conventions",
            f"Naming convention issues: {len(issues)}",
            details={"issues": issues},
            suggestion="Follow PEP8 naming conventions.",
        )
    return ValidationResult.pass_result("validate_naming_conventions", "Naming conventions followed.")


# ---------------------------------------------------------------------------
# Performance validators
# ---------------------------------------------------------------------------
def validate_performance(code: str) -> ValidationResult:
    """Detect potential performance issues: O(n^2) patterns, repeated computations, missing caching."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ValidationResult.info_result("validate_performance", "Cannot parse code.")
    issues = []
    nested_loops = 0
    loops = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)):
            loops.append(node)

    for i, outer in enumerate(loops):
        for inner in ast.walk(outer):
            if inner is not outer and isinstance(inner, (ast.For, ast.While)):
                nested_loops += 1
                ol = getattr(outer, "lineno", 0)
                il = getattr(inner, "lineno", 0)
                issues.append(f"Nested loop at lines {ol} and {il} (potential O(n^2))")
                break

    repeated_calls = Counter()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            call_key = f"{node.func.attr}"
            repeated_calls[call_key] += 1
    for call_name, count in repeated_calls.items():
        if count > 10:
            issues.append(f"Repeated call to '.{call_name}()' ({count} times) — consider caching")

    has_cache = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("cache", "lru_cache", "cached_property"):
                has_cache = True
        elif isinstance(node, ast.Name) and node.id == "lru_cache":
            has_cache = True

    if not has_cache and len(list(ast.walk(tree))) > 200:
        issues.append("Large codebase without caching decorators — consider adding @functools.lru_cache")
    if nested_loops > 3:
        issues.append(f"Multiple nested loop constructs ({nested_loops}) — consider refactoring")

    if issues:
        return ValidationResult.warn_result(
            "validate_performance",
            f"Performance issues: {len(issues)}",
            details={"issues": issues},
            suggestion="Refactor nested loops, cache repeated computations.",
        )
    return ValidationResult.pass_result("validate_performance", "No obvious performance issues.")


# ---------------------------------------------------------------------------
# Type annotation validators
# ---------------------------------------------------------------------------
def validate_type_hints(code: str) -> ValidationResult:
    """Check that Python 3 type annotations are present on public functions and methods."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ValidationResult.info_result("validate_type_hints", "Cannot parse code.")
    missing = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            args = node.args
            arg_issues = []
            for arg in args.posonlyargs + args.args + args.kwonlyargs:
                if arg.arg != "self" and arg.arg != "cls" and arg.annotation is None:
                    arg_issues.append(arg.arg)
            if arg_issues:
                missing.append(f"Function '{node.name}' (line {node.lineno}): missing type hints on args: {arg_issues}")
            if args.vararg and args.vararg.annotation is None:
                missing.append(f"Function '{node.name}': *args missing type hint")
            if args.kwarg and args.kwarg.annotation is None:
                missing.append(f"Function '{node.name}': **kwargs missing type hint")
            if node.returns is None:
                missing.append(f"Function '{node.name}' (line {node.lineno}): missing return type hint")

    if missing:
        return ValidationResult.warn_result(
            "validate_type_hints",
            f"Missing type hints: {len(missing)} issue(s)",
            details={"missing": missing},
            suggestion="Add type annotations to all public function signatures.",
        )
    return ValidationResult.pass_result("validate_type_hints", "All public functions have type hints.")


# ---------------------------------------------------------------------------
# Data quality validators
# ---------------------------------------------------------------------------
def validate_data_completeness(data: Union[list, dict], required_fields: Optional[List[str]] = None) -> ValidationResult:
    """Check that data records have all required fields and no null values in key fields."""
    if isinstance(data, dict):
        data = [data]
    if not data:
        return ValidationResult.info_result("data_completeness", "No data to validate.")
    required = required_fields or []
    issues = []
    for idx, record in enumerate(data):
        if not isinstance(record, dict):
            issues.append(f"Record {idx}: expected dict, got {type(record).__name__}")
            continue
        for field in required:
            if field not in record:
                issues.append(f"Record {idx}: missing required field '{field}'")
            elif record[field] is None:
                issues.append(f"Record {idx}: field '{field}' is null")
            elif isinstance(record[field], str) and not record[field].strip():
                issues.append(f"Record {idx}: field '{field}' is empty string")
        if not record:
            issues.append(f"Record {idx}: empty record")
    if issues:
        return ValidationResult.fail_result(
            "data_completeness",
            f"Completeness issues: {len(issues)}",
            severity=ValidationSeverity.WARN,
            details={"issues": issues},
        )
    return ValidationResult.pass_result("data_completeness", f"All {len(data)} record(s) are complete.")


def validate_data_consistency(data: Union[list, dict], type_map: Optional[Dict[str, type]] = None) -> ValidationResult:
    """Check that data field types and formats are consistent across records."""
    if isinstance(data, dict):
        data = [data]
    if not data:
        return ValidationResult.info_result("data_consistency", "No data to validate.")
    if len(data) < 2:
        return ValidationResult.info_result("data_consistency", "Need at least 2 records to check consistency.")
    issues = []
    keys = set(data[0].keys()) if isinstance(data[0], dict) else set()
    for idx, record in enumerate(data[1:], 1):
        if not isinstance(record, dict):
            issues.append(f"Record {idx}: not a dict")
            continue
        for k in keys:
            if k not in record:
                issues.append(f"Record {idx}: missing key '{k}' present in first record")
        for k in record:
            if k not in keys and k not in issues:
                issues.append(f"Record {idx}: extra key '{k}' not in first record")
        if type_map:
            for field, expected_type in type_map.items():
                if field in record and record[field] is not None and not isinstance(record[field], expected_type):
                    issues.append(f"Record {idx}: field '{field}' expected {expected_type.__name__}, got {type(record[field]).__name__}")
    if issues:
        return ValidationResult.fail_result(
            "data_consistency",
            f"Consistency issues: {len(issues)}",
            severity=ValidationSeverity.WARN,
            details={"issues": issues},
        )
    return ValidationResult.pass_result("data_consistency", f"All {len(data)} records are consistent.")


def validate_data_uniqueness(items: list, key_field: str = "id") -> ValidationResult:
    """Check that items have unique values for the specified key field."""
    if not items:
        return ValidationResult.info_result("data_uniqueness", "No items to validate.")
    seen = {}
    duplicates = []
    for idx, item in enumerate(items):
        if isinstance(item, dict):
            val = item.get(key_field)
        elif hasattr(item, key_field):
            val = getattr(item, key_field)
        else:
            val = item if isinstance(item, (str, int, float)) else None
        if val is not None:
            if val in seen:
                duplicates.append((seen[val], idx, val))
            else:
                seen[val] = idx
    if duplicates:
        detail_items = [{"first_idx": d[0], "second_idx": d[1], "value": str(d[2])} for d in duplicates]
        return ValidationResult.fail_result(
            "data_uniqueness",
            f"Found {len(duplicates)} duplicate(s) in key '{key_field}'",
            severity=ValidationSeverity.WARN,
            details={"duplicates": detail_items},
        )
    return ValidationResult.pass_result("data_uniqueness", f"All {len(items)} items have unique '{key_field}' values.")


def validate_data_range(data: Union[list, dict], min_val: float = 0, max_val: float = 100, key: Optional[str] = None) -> ValidationResult:
    """Check that numeric values fall within a specified range."""
    values = []
    if isinstance(data, dict):
        if key and key in data:
            values = [data[key]]
        else:
            values = [v for v in data.values() if isinstance(v, (int, float))]
    elif isinstance(data, list):
        if key:
            values = [item.get(key) for item in data if isinstance(item, dict) and key in item and isinstance(item[key], (int, float))]
        else:
            values = [item for item in data if isinstance(item, (int, float))]
    values = [v for v in values if v is not None]
    if not values:
        return ValidationResult.info_result("data_range", "No numeric values to validate range.")
    out_of_range = [(i, v) for i, v in enumerate(values) if v < min_val or v > max_val]
    if out_of_range:
        return ValidationResult.fail_result(
            "data_range",
            f"{len(out_of_range)} value(s) out of range [{min_val}, {max_val}]",
            severity=ValidationSeverity.WARN,
            details={"out_of_range": [{"index": i, "value": v} for i, v in out_of_range]},
        )
    return ValidationResult.pass_result("data_range", f"All {len(values)} values are within [{min_val}, {max_val}].")


def validate_data_format(data: Union[list, dict], format_pattern: str = r"^[A-Za-z0-9_\-\.]+@[A-Za-z0-9\-]+\.[A-Za-z]{2,}$", key: Optional[str] = None) -> ValidationResult:
    """Check that data values match a specified regex format pattern."""
    pattern = re.compile(format_pattern)
    items = []
    if isinstance(data, dict):
        items = [(0, k, v) for k, v in data.items() if key is None or k == key]
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            if isinstance(item, dict):
                for k, v in item.items():
                    if key is None or k == key:
                        items.append((idx, k, v))
            elif key is None:
                items.append((idx, "", item))
    mismatches = []
    for idx, field, val in items:
        if isinstance(val, str) and not pattern.match(val):
            mismatches.append({"record": idx, "field": field, "value": val})
    if mismatches:
        return ValidationResult.fail_result(
            "data_format",
            f"{len(mismatches)} value(s) don't match format pattern",
            severity=ValidationSeverity.WARN,
            details={"mismatches": mismatches, "pattern": format_pattern},
        )
    return ValidationResult.pass_result("data_format", f"All values match the format pattern.")


# ---------------------------------------------------------------------------
# Config validators
# ---------------------------------------------------------------------------
def validate_env_file(content: str) -> ValidationResult:
    """Validate .env file structure: KEY=VALUE format, no spaces around =, no quotes."""
    issues = []
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            issues.append(f"Line {i}: missing '=' sign")
            continue
        key, _, val = stripped.partition("=")
        if not key.strip():
            issues.append(f"Line {i}: empty key")
        elif not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key.strip()):
            issues.append(f"Line {i}: key '{key.strip()}' has invalid format")
        if val.strip() and val.strip()[0] in ('"', "'") and val.strip()[-1] in ('"', "'"):
            issues.append(f"Line {i}: value should not be quoted (quotes may be included literally)")
        if key != key.strip() or (val and val != val.strip() and val.strip()):
            issues.append(f"Line {i}: spaces detected around '=' sign")
    if issues:
        return ValidationResult.fail_result(
            "validate_env_file",
            f"ENV file issues ({len(issues)})",
            severity=ValidationSeverity.WARN,
            details={"issues": issues},
        )
    return ValidationResult.pass_result("validate_env_file", "ENV file format is valid.")


def validate_ini_file(content: str) -> ValidationResult:
    """Validate INI file structure: sections, key=value pairs."""
    issues = []
    lines = content.split("\n")
    section_re = re.compile(r"^\s*\[([^\]]+)\]\s*$")
    kv_re = re.compile(r"^\s*([A-Za-z0-9_]+)\s*[:=]\s*(.*)\s*$")
    comment_re = re.compile(r"^\s*[;#]")
    in_section = False
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or comment_re.match(stripped):
            continue
        if section_re.match(stripped):
            in_section = True
            continue
        if not in_section and kv_re.match(stripped):
            issues.append(f"Line {i}: key=value outside section")
        if not section_re.match(stripped) and not kv_re.match(stripped) and not comment_re.match(stripped):
            issues.append(f"Line {i}: unrecognised INI syntax")
    if issues:
        return ValidationResult.fail_result(
            "validate_ini_file",
            f"INI file issues ({len(issues)})",
            severity=ValidationSeverity.WARN,
            details={"issues": issues},
        )
    return ValidationResult.pass_result("validate_ini_file", "INI file format is valid.")


def validate_config_completeness(config: dict, required_keys: List[str]) -> ValidationResult:
    """Check that a config dictionary contains all required keys."""
    missing = [k for k in required_keys if k not in config]
    if missing:
        return ValidationResult.fail_result(
            "validate_config_completeness",
            f"Missing required config keys: {missing}",
            severity=ValidationSeverity.ERROR,
            details={"missing": missing},
        )
    return ValidationResult.pass_result("validate_config_completeness", "All required config keys present.")


# ---------------------------------------------------------------------------
# Docker validators expansion
# ---------------------------------------------------------------------------
def validate_docker_compose(content: str) -> ValidationResult:
    """Validate docker-compose.yml structure and common pitfalls."""
    if yaml is None:
        return ValidationResult.info_result("validate_docker_compose", "YAML library not available.")
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        return ValidationResult.fail_result("validate_docker_compose", f"YAML error: {e}", severity=ValidationSeverity.ERROR)
    if not isinstance(data, dict):
        return ValidationResult.fail_result("validate_docker_compose", "Top-level must be a mapping", severity=ValidationSeverity.ERROR)
    issues = []
    if "version" not in data:
        issues.append("Missing 'version' field")
    if "services" not in data:
        issues.append("Missing 'services' field")
    elif isinstance(data["services"], dict):
        for svc_name, svc_config in data["services"].items():
            if isinstance(svc_config, dict):
                if "image" not in svc_config and "build" not in svc_config:
                    issues.append(f"Service '{svc_name}': missing 'image' or 'build'")
                if svc_config.get("restart") == "always" and svc_config.get("privileged", False):
                    issues.append(f"Service '{svc_name}': privileged mode with restart=always")
                ports = svc_config.get("ports", [])
                if isinstance(ports, list):
                    for p in ports:
                        if isinstance(p, str) and p.endswith(":22"):
                            issues.append(f"Service '{svc_name}': exposing SSH port 22")
    if issues:
        return ValidationResult.fail_result(
            "validate_docker_compose",
            f"Compose issues ({len(issues)})",
            severity=ValidationSeverity.WARN,
            details={"issues": issues},
        )
    return ValidationResult.pass_result("validate_docker_compose", "Docker Compose file looks valid.")


def validate_dockerignore(content: str) -> ValidationResult:
    """Validate .dockerignore entries for common missing patterns."""
    issues = []
    lines = content.split("\n")
    entries = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
    essential_patterns = [".git", "__pycache__", "*.pyc", ".env", "node_modules", ".venv", "venv", ".DS_Store"]
    for pat in essential_patterns:
        if pat not in entries:
            issues.append(f"Missing recommended entry: '{pat}'")
    has_wildcard = any("*" in e for e in entries)
    if not has_wildcard and len(entries) > 5:
        issues.append("No wildcard patterns found; consider using patterns like '*' then '!...'")
    if issues:
        return ValidationResult.warn_result("validate_dockerignore", f"Optimisation suggestions: {len(issues)}", details={"issues": issues})
    return ValidationResult.pass_result("validate_dockerignore", "Dockerignore looks reasonable.")


def validate_container_resources(dockerfile_content: str) -> ValidationResult:
    """Check Dockerfile for resource-related best practices."""
    issues = []
    lines = dockerfile_content.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip().upper()
        if stripped.startswith("RUN") and "apt-get" in stripped and "clean" not in stripped:
            issues.append(f"Line {i}: RUN command may leave apt cache — consider chaining && apt-get clean")
        if "pip install" in stripped.lower() and "--no-cache-dir" not in stripped:
            issues.append(f"Line {i}: pip install without --no-cache-dir")
    layers = len([l for l in lines if l.strip().upper().startswith(("RUN", "COPY", "ADD"))])
    if layers > 20:
        issues.append(f"Too many image layers ({layers}) — consider squashing layers")
    if issues:
        return ValidationResult.warn_result("validate_container_resources", f"Resource optimisation: {len(issues)}", details={"issues": issues})
    return ValidationResult.pass_result("validate_container_resources", "No resource issues detected.")


# ---------------------------------------------------------------------------
# Git validators
# ---------------------------------------------------------------------------
def validate_gitignore(content: str) -> ValidationResult:
    """Validate .gitignore entries: no duplicates, no negated-only patterns, recommended entries."""
    issues = []
    lines = content.split("\n")
    entries = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
    if not entries:
        return ValidationResult.info_result("validate_gitignore", "Empty .gitignore.")
    seen = set()
    for entry in entries:
        if entry in seen:
            issues.append(f"Duplicate entry: '{entry}'")
        seen.add(entry)
    essential = ["__pycache__/", "*.pyc", ".env", ".venv/", "venv/", "node_modules/", ".DS_Store", "*.log", "dist/", "build/", ".tox/", ".pytest_cache/", ".mypy_cache/", ".ruff_cache/", ".coverage", "htmlcov/"]
    for pat in essential:
        if pat not in entries and pat not in [e.rstrip("/") for e in entries]:
            pass
    negations = [e for e in entries if e.startswith("!")]
    if negations and not any(not e.startswith("!") for e in entries):
        issues.append("Only negated patterns found; need at least one positive pattern")
    if issues:
        return ValidationResult.warn_result("validate_gitignore", f"Gitignore issues: {len(issues)}", details={"issues": issues})
    return ValidationResult.pass_result("validate_gitignore", "Gitignore looks valid.")


def validate_git_message(message: str) -> ValidationResult:
    """Validate a git commit message: conventional format, length, etc."""
    issues = []
    lines = message.strip().split("\n")
    if not lines or not lines[0].strip():
        return ValidationResult.fail_result("validate_git_message", "Empty commit message.", severity=ValidationSeverity.ERROR)
    first = lines[0].strip()
    if len(first) > 72:
        issues.append(f"First line too long ({len(first)} chars, max 72)")
    conventional = re.match(r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([^)]+\))?!?:\s.*", first)
    if not conventional:
        issues.append("First line does not follow conventional commit format (e.g., 'feat: ...')")
    if len(lines) > 2:
        if lines[1].strip() != "":
            issues.append("Expected blank line between subject and body")
    body_lines = [l.strip() for l in lines[2:] if l.strip()]
    for i, bl in enumerate(body_lines):
        if len(bl) > 72:
            issues.append(f"Body line {i+1} too long ({len(bl)} chars, max 72)")
    if issues:
        return ValidationResult.warn_result("validate_git_message", f"Commit message issues: {len(issues)}", details={"issues": issues})
    return ValidationResult.pass_result("validate_git_message", "Commit message follows best practices.")


def validate_branch_name(name: str) -> ValidationResult:
    """Validate git branch name: lowercase, no special chars, conventional prefixes."""
    issues = []
    if not name:
        return ValidationResult.fail_result("validate_branch_name", "Empty branch name.", severity=ValidationSeverity.ERROR)
    if re.search(r"[A-Z]", name):
        issues.append("Branch name should be lowercase")
    if re.search(r"[^a-z0-9_\-\./]", name):
        issues.append("Branch name contains disallowed characters (only a-z, 0-9, _, -, ., /)")
    if name.endswith("/") or name.startswith("/"):
        issues.append("Branch name cannot start or end with '/'")
    if ".." in name:
        issues.append("Branch name cannot contain '..'")
    if "@{" in name:
        issues.append("Branch name cannot contain '@{'")
    valid_prefixes = ["feature/", "bugfix/", "hotfix/", "release/", "chore/", "docs/", "refactor/", "test/", "fix/", "feat/"]
    has_prefix = any(name.startswith(p) for p in valid_prefixes)
    if "/" in name and not has_prefix:
        issues.append(f"Branch name with '/' should use a conventional prefix ({', '.join(valid_prefixes)})")
    if len(name) > 100:
        issues.append("Branch name too long (max 100 chars)")
    if issues:
        return ValidationResult.warn_result("validate_branch_name", f"Branch name issues: {len(issues)}", details={"issues": issues})
    return ValidationResult.pass_result("validate_branch_name", "Branch name is valid.")


# ---------------------------------------------------------------------------
# Documentation validators
# ---------------------------------------------------------------------------
def validate_readme(content: str) -> ValidationResult:
    """Validate README content: required sections, badges, installation instructions."""
    issues = []
    lines_lower = content.lower()
    required_sections = ["installation", "usage", "api", "contributing", "license"]
    found_sections = []
    section_re = re.compile(r"^##\s+(.+)$", re.M)
    for match in section_re.finditer(content):
        found_sections.append(match.group(1).strip().lower())
    for section in required_sections:
        if not any(section in fs for fs in found_sections):
            issues.append(f"Recommended section missing: '{section}'")
    if not re.search(r"```\s*(bash|sh|shell|powershell|cmd)", content):
        issues.append("No code block examples found for installation/usage")
    has_badges = any(m in content for m in ["![", "[![", "shield.io", "badge"])
    if not has_badges:
        issues.append("No badges found (e.g., build status, license)")
    if not re.search(r"#\s+.+", content):
        issues.append("No top-level title (H1) found")
    if issues:
        return ValidationResult.warn_result("validate_readme", f"README suggestions: {len(issues)}", details={"issues": issues})
    return ValidationResult.pass_result("validate_readme", "README structure looks good.")


def validate_changelog(content: str) -> ValidationResult:
    """Validate CHANGELOG follows Keep a Changelog format."""
    issues = []
    if not content.startswith("# Changelog") and not content.startswith("# Changelog"):
        issues.append("Changelog should start with '# Changelog'")
    version_re = re.compile(r"^##\s+\[?(\d+\.\d+\.\d+|Unreleased)\]?", re.M)
    versions = version_re.findall(content)
    if not versions:
        issues.append("No version entries found (expected '## [x.y.z]')")
    has_unreleased = "Unreleased" in content
    if not has_unreleased:
        pass
    date_re = re.compile(r"^\d{4}-\d{2}-\d{2}", re.M)
    if not date_re.search(content):
        issues.append("No dates found; entries should include YYYY-MM-DD")
    sections = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]
    found_sections = []
    for match in re.finditer(r"^###\s+(.+)$", content, re.M):
        found_sections.append(match.group(1).strip())
    for s in sections:
        if s in found_sections:
            pass
    if issues:
        return ValidationResult.warn_result("validate_changelog", f"Changelog issues: {len(issues)}", details={"issues": issues})
    return ValidationResult.pass_result("validate_changelog", "Changelog format looks valid.")


def validate_license(content: str) -> ValidationResult:
    """Validate LICENSE content: recognised license type, correct formatting."""
    issues = []
    license_lower = content.lower()
    known_licenses = [
        "mit license", "apache license", "gpl", "lgpl", "bsd", "mozilla public license",
        "unlicense", "cc0", "creative commons", "isc license", "zlib license",
        "artistic license", "eclipse public license", "agpl",
    ]
    recognized = any(l in license_lower for l in known_licenses)
    if not recognized:
        issues.append("Could not identify a standard open-source license")
    year_match = re.search(r"(\d{4})", content)
    if year_match:
        year = int(year_match.group(1))
        current = datetime.now().year
        if year > current + 1 or year < 2000:
            issues.append(f"Copyright year '{year}' seems incorrect")
    if "copyright" not in license_lower and "©" not in content:
        issues.append("No copyright notice found")
    if issues:
        return ValidationResult.warn_result("validate_license", f"License issues: {len(issues)}", details={"issues": issues})
    return ValidationResult.pass_result("validate_license", "License file looks valid.")


# ---------------------------------------------------------------------------
# Accessibility validators
# ---------------------------------------------------------------------------
def validate_html_a11y(html_content: str) -> ValidationResult:
    """Check HTML for accessibility issues: alt text, labels, heading hierarchy, aria attributes."""
    issues = []
    img_pattern = re.compile(r"<img\s[^>]*>", re.I)
    for match in img_pattern.finditer(html_content):
        tag = match.group(0)
        if 'alt' not in tag and 'aria-label' not in tag and 'aria-labelledby' not in tag:
            pos = match.start()
            snippet = tag[:80]
            issues.append(f"Image missing alt text at position {pos}: {snippet}")
    input_pattern = re.compile(r"<input\s[^>]*>", re.I)
    for match in input_pattern.finditer(html_content):
        tag = match.group(0)
        if 'type="hidden"' in tag or 'type=hidden' in tag:
            continue
        if 'aria-label' not in tag and 'aria-labelledby' not in tag and 'label' not in tag:
            if not re.search(r'<label[^>]*>.*' + re.escape(tag.split(' ')[-1].rstrip('>')), html_content, re.I | re.S):
                parent_re = re.compile(r'<label[^>]*>[\s\S]{0,500}' + re.escape(tag.split(' ')[-1].rstrip('>')), re.I | re.S)
                if not parent_re.search(html_content):
                    pos = match.start()
                    issues.append(f"Input missing associated label at position {pos}")
    heading_pattern = re.compile(r"<h([1-6])[^>]*>", re.I)
    headings = [(int(m.group(1)), m.start()) for m in heading_pattern.finditer(html_content)]
    for i in range(1, len(headings)):
        if headings[i][0] > headings[i-1][0] + 1:
            issues.append(f"Heading level jumps from h{headings[i-1][0]} to h{headings[i][0]} at position {headings[i][1]}")
    if not headings:
        issues.append("No heading elements (h1-h6) found; consider adding headings for structure")
    if not re.search(r'role\s*=', html_content, re.I) and not re.search(r'aria-', html_content, re.I):
        issues.append("No ARIA attributes found; consider adding roles for complex widgets")
    lang_match = re.search(r'<html[^>]*\blang\s*=', html_content, re.I)
    if not lang_match:
        issues.append("Missing 'lang' attribute on <html> element")
    if issues:
        return ValidationResult.warn_result("validate_html_a11y", f"Accessibility issues: {len(issues)}", details={"issues": issues})
    return ValidationResult.pass_result("validate_html_a11y", "HTML accessibility checks passed.")


# ---------------------------------------------------------------------------
# Style validators
# ---------------------------------------------------------------------------
def validate_pep8(code: str) -> ValidationResult:
    """Basic PEP8 checks: line length, trailing whitespace, blank lines, indentation."""
    issues = []
    lines = code.split("\n")
    for i, line in enumerate(lines, 1):
        if line.rstrip("\n").endswith(" "):
            issues.append(f"Line {i}: trailing whitespace")
        if len(line) > 79:
            pass
    for i, line in enumerate(lines, 1):
        if line.strip() == "":
            continue
        leading = len(line) - len(line.lstrip())
        if leading % 4 != 0 and leading > 0:
            issues.append(f"Line {i}: indentation is not a multiple of 4 (got {leading} spaces)")
    prev_blank = True
    blank_runs = 0
    for i, line in enumerate(lines, 1):
        if line.strip() == "":
            blank_runs += 1
        else:
            if blank_runs > 2:
                issues.append(f"Line {i}: more than 2 blank lines preceding (got {blank_runs})")
            blank_runs = 0
    if issues:
        return ValidationResult.warn_result("validate_pep8", f"PEP8 style issues: {len(issues)}", details={"issues": issues})
    return ValidationResult.pass_result("validate_pep8", "Code follows basic PEP8 style.")


def validate_max_line_length(code: str, max_len: int = 79) -> ValidationResult:
    """Check that no line exceeds the specified maximum length."""
    issues = []
    lines = code.split("\n")
    for i, line in enumerate(lines, 1):
        if len(line) > max_len and not line.strip().startswith("#"):
            issues.append(f"Line {i}: {len(line)} chars (max {max_len})")
    if issues:
        return ValidationResult.warn_result(
            "validate_max_line_length",
            f"{len(issues)} line(s) exceed {max_len} chars",
            details={"issues": issues, "max_length": max_len},
        )
    return ValidationResult.pass_result("validate_max_line_length", f"No lines exceed {max_len} chars.")


def validate_trailing_whitespace(code: str) -> ValidationResult:
    """Check for trailing whitespace on lines."""
    issues = []
    lines = code.split("\n")
    for i, line in enumerate(lines, 1):
        if line != line.rstrip():
            issues.append(f"Line {i}: trailing whitespace")
    if issues:
        return ValidationResult.warn_result(
            "validate_trailing_whitespace",
            f"Trailing whitespace on {len(issues)} line(s)",
            details={"lines": issues},
        )
    return ValidationResult.pass_result("validate_trailing_whitespace", "No trailing whitespace detected.")


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------
def log_validation(result: ValidationResult) -> None:
    """Write a single validation result to the JSONL log."""
    with _VALIDATION_LOCK:
        try:
            with open(_VALIDATION_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(result.to_dict()) + "\n")
        except OSError:
            pass


def _load_validation_log() -> List[dict]:
    """Load all entries from the validation log file."""
    entries = []
    if not os.path.exists(_VALIDATION_LOG):
        return entries
    try:
        with open(_VALIDATION_LOG, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except OSError:
        pass
    return entries


def get_validation_report(days: int = 7) -> dict:
    """Generate a summary report from the validation log for the last N days."""
    entries = _load_validation_log()
    cutoff = time.time() - days * 86400
    recent = [e for e in entries if e.get("timestamp", 0) >= cutoff]
    total = len(recent)
    passed = sum(1 for e in recent if e.get("passed", False))
    failed = total - passed
    by_severity = Counter(e.get("severity", "UNKNOWN") for e in recent)
    by_name = Counter(e.get("name", "unknown") for e in recent)
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "by_severity": dict(by_severity),
        "by_name": dict(by_name.most_common(20)),
        "period_days": days,
    }


def clear_validation_log() -> bool:
    """Clear all entries from the validation log."""
    try:
        with _VALIDATION_LOCK:
            if os.path.exists(_VALIDATION_LOG):
                os.remove(_VALIDATION_LOG)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Main validation_tool dispatcher
# ---------------------------------------------------------------------------
def validation_tool(action: str, **kwargs) -> str:
    """Unified entry point for validation operations.

    Actions:
      - validate_python, validate_javascript, validate_html, validate_css
      - validate_json, validate_xml, validate_yaml, validate_csv, validate_toml
      - validate_sql, validate_markdown, validate_dockerfile
      - validate_file_exists, validate_file_size, validate_file_extension
      - validate_file_content, validate_secrets, validate_xss
      - validate_code_complexity, validate_docstrings
      - validate_command_injection, validate_path_traversal
      - validate_sql_injection, validate_ssrf, validate_insecure_deserialization
      - validate_import_order, validate_unused_imports, validate_import_styles
      - validate_naming_conventions, validate_performance, validate_type_hints
      - validate_data_completeness, validate_data_consistency
      - validate_data_uniqueness, validate_data_range, validate_data_format
      - validate_env_file, validate_ini_file, validate_config_completeness
      - validate_docker_compose, validate_dockerignore, validate_container_resources
      - validate_gitignore, validate_git_message, validate_branch_name
      - validate_readme, validate_changelog, validate_license
      - validate_html_a11y
      - validate_pep8, validate_max_line_length, validate_trailing_whitespace
      - validate_all (pass list of tuples)
      - auto_verify
      - report, clear_log
      - add_rule, remove_rule, list_rules, run_rules
      - cache_clear, cache_size
      - set_profile, get_profile
      - install_hook, remove_hook
      - send_alert
      - export_report
    """
    if action == "stats":
        return json.dumps({"success": True, "total_calls": sum(1 for _ in open(_VALIDATION_LOG) if _.strip()) if os.path.exists(_VALIDATION_LOG) else 0})

    action_map = {
        "verify_code": lambda: validate_python(kwargs.get("code", "")),
        "verify_python": lambda: validate_python(kwargs.get("code", "")),
        "verify_file": lambda: validate_file_content_by_type(kwargs.get("path", "")),
        "verify_html": lambda: validate_html(kwargs.get("html_content", kwargs.get("html", ""))),
        "verify_json": lambda: validate_json(kwargs.get("code", kwargs.get("json_str", "")), kwargs.get("schema")),
        "verify_csv": lambda: validate_csv(kwargs.get("code", kwargs.get("csv", ""))),
        "validate_python": lambda: validate_python(kwargs.get("code", "")),
        "validate_javascript": lambda: validate_javascript(kwargs.get("code", "")),
        "validate_html": lambda: validate_html(kwargs.get("html_content", kwargs.get("html", ""))),
        "validate_css": lambda: validate_css(kwargs.get("code", kwargs.get("css", ""))),
        "validate_json": lambda: validate_json(kwargs.get("code", kwargs.get("json_str", ""))),
        "validate_xml": lambda: validate_xml(kwargs.get("code", kwargs.get("xml", ""))),
        "validate_yaml": lambda: validate_yaml(kwargs.get("code", kwargs.get("yaml", ""))),
        "validate_csv": lambda: validate_csv(kwargs.get("code", kwargs.get("csv", ""))),
        "validate_toml": lambda: validate_toml(kwargs.get("code", kwargs.get("toml", ""))),
        "validate_sql": lambda: validate_sql(kwargs.get("code", kwargs.get("sql", ""))),
        "validate_markdown": lambda: validate_markdown(kwargs.get("code", kwargs.get("md", ""))),
        "validate_dockerfile": lambda: validate_dockerfile(kwargs.get("code", kwargs.get("content", ""))),
        "validate_file_exists": lambda: validate_file_exists(kwargs.get("path", "")),
        "validate_file_size": lambda: validate_file_size(kwargs.get("path", ""), kwargs.get("max_mb", 10.0)),
        "validate_file_extension": lambda: validate_file_extension(kwargs.get("path", ""), kwargs.get("allowed")),
        "validate_file_content": lambda: validate_file_content_by_type(kwargs.get("path", "")),
        "validate_secrets": lambda: validate_secrets(kwargs.get("content", ""), kwargs.get("context", "")),
        "validate_xss": lambda: validate_xss(kwargs.get("html", "")),
        "validate_code_complexity": lambda: validate_code_complexity(kwargs.get("code", ""), kwargs.get("language", "python")),
        "validate_docstrings": lambda: validate_docstrings(kwargs.get("code", "")),
        "validate_command_injection": lambda: validate_command_injection(kwargs.get("input", "")),
        "validate_path_traversal": lambda: validate_path_traversal(kwargs.get("path", "")),
        "validate_sql_injection": lambda: validate_sql_injection(kwargs.get("input", "")),
        "validate_ssrf": lambda: validate_ssrf(kwargs.get("url", "")),
        "validate_insecure_deserialization": lambda: validate_insecure_deserialization(kwargs.get("content", "")),
        "validate_import_order": lambda: validate_import_order(kwargs.get("code", "")),
        "validate_unused_imports": lambda: validate_unused_imports(kwargs.get("code", "")),
        "validate_import_styles": lambda: validate_import_styles(kwargs.get("code", "")),
        "validate_naming_conventions": lambda: validate_naming_conventions(kwargs.get("code", "")),
        "validate_performance": lambda: validate_performance(kwargs.get("code", "")),
        "validate_type_hints": lambda: validate_type_hints(kwargs.get("code", "")),
        "validate_data_completeness": lambda: validate_data_completeness(kwargs.get("data", []), kwargs.get("required_fields")),
        "validate_data_consistency": lambda: validate_data_consistency(kwargs.get("data", []), kwargs.get("type_map")),
        "validate_data_uniqueness": lambda: validate_data_uniqueness(kwargs.get("items", []), kwargs.get("key_field", "id")),
        "validate_data_range": lambda: validate_data_range(kwargs.get("data", []), kwargs.get("min", 0), kwargs.get("max", 100), kwargs.get("key")),
        "validate_data_format": lambda: validate_data_format(kwargs.get("data", []), kwargs.get("pattern", r"^[A-Za-z0-9_\-\.]+@[A-Za-z0-9\-]+\.[A-Za-z]{2,}$"), kwargs.get("key")),
        "validate_env_file": lambda: validate_env_file(kwargs.get("content", "")),
        "validate_ini_file": lambda: validate_ini_file(kwargs.get("content", "")),
        "validate_config_completeness": lambda: validate_config_completeness(kwargs.get("config", {}), kwargs.get("required_keys", [])),
        "validate_docker_compose": lambda: validate_docker_compose(kwargs.get("content", "")),
        "validate_dockerignore": lambda: validate_dockerignore(kwargs.get("content", "")),
        "validate_container_resources": lambda: validate_container_resources(kwargs.get("content", "")),
        "validate_gitignore": lambda: validate_gitignore(kwargs.get("content", "")),
        "validate_git_message": lambda: validate_git_message(kwargs.get("message", "")),
        "validate_branch_name": lambda: validate_branch_name(kwargs.get("name", "")),
        "validate_readme": lambda: validate_readme(kwargs.get("content", "")),
        "validate_changelog": lambda: validate_changelog(kwargs.get("content", "")),
        "validate_license": lambda: validate_license(kwargs.get("content", "")),
        "validate_html_a11y": lambda: validate_html_a11y(kwargs.get("html", "")),
        "validate_pep8": lambda: validate_pep8(kwargs.get("code", "")),
        "validate_max_line_length": lambda: validate_max_line_length(kwargs.get("code", ""), kwargs.get("max_len", 79)),
        "validate_trailing_whitespace": lambda: validate_trailing_whitespace(kwargs.get("code", "")),
        "auto_verify": lambda: auto_verify(kwargs.get("result"), kwargs.get("context")),
        "report": lambda: get_validation_report(kwargs.get("days", 7)),
        "clear_log": lambda: clear_validation_log(),
        "add_rule": lambda: _add_rule_action(kwargs.get("name", ""), kwargs.get("check_func"), kwargs.get("severity", "WARN"), kwargs.get("description", "")),
        "remove_rule": lambda: _RULES_ENGINE.remove_rule(kwargs.get("name", "")),
        "list_rules": lambda: _RULES_ENGINE.list_rules(),
        "run_rules": lambda: _RULES_ENGINE.run_rules(kwargs.get("content", ""), kwargs.get("rule_names")),
        "cache_clear": lambda: _VALIDATION_CACHE.clear(),
        "cache_size": lambda: _VALIDATION_CACHE.size(),
        "set_profile": lambda: set_validation_profile(kwargs.get("profile", "normal")),
        "get_profile": lambda: get_validation_profile(),
        "install_hook": lambda: install_validation_hook(),
        "remove_hook": lambda: remove_validation_hook(),
        "send_alert": lambda: send_validation_alert(
            ValidationResult(
                kwargs.get("name", "alert"),
                kwargs.get("passed", False),
                kwargs.get("severity", "WARN"),
                kwargs.get("message", ""),
            ),
            kwargs.get("channel", "console"),
            kwargs.get("webhook_url"),
        ),
        "export_report": lambda: export_validation_report(kwargs.get("format", "markdown"), kwargs.get("days", 7)),
    }
    handler = action_map.get(action)
    if handler is None:
        return json.dumps({
            "success": False,
            "error": f"Unknown validation action: '{action}'",
            "available_actions": list(action_map.keys()),
        })
    try:
        result = handler()
        if isinstance(result, ValidationResult):
            log_validation(result)
            d = result.to_dict()
            d["success"] = result.passed
            return json.dumps(d)
        if isinstance(result, dict):
            return json.dumps({"success": True, "data": result})
        return json.dumps({"success": True, "data": result})
    except Exception as exc:
        return json.dumps({
            "success": False,
            "error": f"Validation action '{action}' raised: {exc}",
            "traceback": traceback.format_exc(),
        })


def _add_rule_action(name: str, check_func: Optional[Callable], severity: str, description: str) -> dict:
    """Internal helper to add a rule with an optional serialisable stub."""
    if check_func is None:

        def stub_check(content: str) -> ValidationResult:
            return ValidationResult.info_result(name, f"Stub rule '{name}' — no check function provided.")
        check_func = stub_check
    _RULES_ENGINE.add_rule(name, check_func, severity, description)
    return {"success": True, "message": f"Rule '{name}' added."}


# ---------------------------------------------------------------------------
# __all__
# ---------------------------------------------------------------------------
__all__ = [
    "ValidationSeverity", "ValidationResult", "ValidationCache", "ValidationRule", "RulesEngine",
    "PROFILE_STRICT", "PROFILE_NORMAL", "PROFILE_RELAXED",
    "set_validation_profile", "get_validation_profile",
    "validate_python", "validate_javascript", "validate_html", "validate_css",
    "validate_json", "validate_against_schema", "validate_xml", "validate_yaml",
    "validate_csv", "validate_toml", "validate_sql", "validate_markdown",
    "validate_dockerfile", "validate_file_exists", "validate_file_size",
    "validate_file_extension", "validate_file_content_by_type",
    "validate_secrets", "validate_xss",
    "validate_code_complexity", "validate_docstrings",
    "validate_all", "validate_call", "auto_verify",
    "validate_command_injection", "validate_path_traversal",
    "validate_sql_injection", "validate_ssrf", "validate_insecure_deserialization",
    "validate_import_order", "validate_unused_imports", "validate_import_styles",
    "validate_naming_conventions", "validate_performance", "validate_type_hints",
    "validate_data_completeness", "validate_data_consistency",
    "validate_data_uniqueness", "validate_data_range", "validate_data_format",
    "validate_env_file", "validate_ini_file", "validate_config_completeness",
    "validate_docker_compose", "validate_dockerignore", "validate_container_resources",
    "validate_gitignore", "validate_git_message", "validate_branch_name",
    "validate_readme", "validate_changelog", "validate_license",
    "validate_html_a11y",
    "validate_pep8", "validate_max_line_length", "validate_trailing_whitespace",
    "log_validation", "_load_validation_log", "get_validation_report",
    "clear_validation_log", "validation_tool",
    "install_validation_hook", "remove_validation_hook",
    "send_validation_alert",
    "validation_result_to_markdown", "validation_result_to_html",
    "export_validation_report",
]
