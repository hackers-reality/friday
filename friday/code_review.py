"""
FRIDAY Code Review Agent Module

A comprehensive code review tool that analyzes Python files for bugs,
security issues, performance problems, and style violations, generating
detailed reports with fix suggestions.
"""

import ast
import os
import re
import json
import math
import hashlib
import tokenize
import io
import sys
import types
import warnings
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple, Set
from pathlib import Path
from collections import defaultdict
from enum import Enum


class Severity(Enum):
    """Enumeration of issue severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Category(Enum):
    """Enumeration of issue categories."""
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    BUG = "bug"
    COMPLEXITY = "complexity"


SECURITY_PATTERNS = {
    "hardcoded_secret": [
        r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']',
        r'(?i)(secret|secret_key|api_key|apikey)\s*=\s*["\'][^"\']+["\']',
        r'(?i)(access_token|auth_token)\s*=\s*["\'][^"\']+["\']',
        r'(?i)(private_key)\s*=\s*["\'][^"\']+["\']',
    ],
    "sql_injection": [
        r'(?i)(execute|cursor\.execute)\s*\(\s*["\'].*%s',
        r'(?i)(execute|cursor\.execute)\s*\(\s*["\'].*\+',
        r'(?i)(execute|cursor\.execute)\s*\(\s*f["\']',
        r'(?i)(execute|cursor\.execute)\s*\(\s*["\'].*\.format\(',
    ],
    "command_injection": [
        r'os\.system\s*\(',
        r'os\.popen\s*\(',
        r'subprocess\.call\s*\(\s*["\']',
        r'subprocess\.Popen\s*\(\s*["\']',
        r'commands\.getoutput\s*\(',
    ],
    "path_traversal": [
        r'open\s*\([^)]*\+',
        r'open\s*\([^)]*format\(',
        r'open\s*\([^)]*\%',
        r'os\.path\.join\s*\([^)]*\.\.',
    ],
    "eval_exec": [
        r'\beval\s*\(',
        r'\bexec\s*\(',
        r'compile\s*\(.*["\']exec["\']',
    ],
    "pickle_deserialization": [
        r'pickle\.load\s*\(',
        r'pickle\.loads\s*\(',
        r'cPickle\.load\s*\(',
    ],
    "unsafe_yaml": [
        r'yaml\.load\s*\([^)]*\)',
        r'yaml\.unsafe_load\s*\(',
    ],
    "insecure_random": [
        r'\brandom\.\b(?![^(]*seed)',
        r'\brandom\.randint\s*\(',
        r'\brandom\.choice\s*\(',
    ],
    "ssl_disabled": [
        r'verify\s*=\s*False',
        r'check_hostname\s*=\s*False',
        r'PROTOCOL_TLS',
        r'SSLContext.*PROTOCOL_TLSv',
    ],
    "debug_mode": [
        r'DEBUG\s*=\s*True',
        r'debug\s*=\s*True',
        r'app\.run\(.*debug\s*=\s*True',
    ],
}
RULES = {
    "SEC001": {
        "description": "Hardcoded secret or API key detected",
        "severity": "error",
        "category": "security",
        "suggestion": "Use environment variables or a secrets manager instead of hardcoding credentials"
    },
    "SEC002": {
        "description": "Potential SQL injection vulnerability",
        "severity": "error",
        "category": "security",
        "suggestion": "Use parameterized queries or ORM to prevent SQL injection"
    },
    "SEC003": {
        "description": "Command injection vulnerability",
        "severity": "error",
        "category": "security",
        "suggestion": "Use subprocess with shell=False and pass arguments as a list"
    },
    "SEC004": {
        "description": "Potential path traversal vulnerability",
        "severity": "warning",
        "category": "security",
        "suggestion": "Validate and sanitize file paths, use os.path.realpath to resolve symlinks"
    },
    "SEC005": {
        "description": "Use of eval() or exec() detected",
        "severity": "error",
        "category": "security",
        "suggestion": "Avoid eval/exec, use ast.literal_eval for safe evaluation or alternative approaches"
    },
    "SEC006": {
        "description": "Unsafe pickle deserialization",
        "severity": "error",
        "category": "security",
        "suggestion": "Avoid unpickling untrusted data, use JSON or other safe serialization formats"
    },
    "SEC007": {
        "description": "Unsafe YAML loading",
        "severity": "warning",
        "category": "security",
        "suggestion": "Use yaml.safe_load() instead of yaml.load() to prevent arbitrary code execution"
    },
    "SEC008": {
        "description": "Insecure random number generation",
        "severity": "warning",
        "category": "security",
        "suggestion": "Use secrets module or os.urandom() for cryptographic operations"
    },
    "SEC009": {
        "description": "SSL certificate verification disabled",
        "severity": "error",
        "category": "security",
        "suggestion": "Enable SSL certificate verification in production environments"
    },
    "SEC010": {
        "description": "Debug mode enabled in production code",
        "severity": "warning",
        "category": "security",
        "suggestion": "Disable debug mode in production to prevent information leakage"
    },
    "PERF001": {
        "description": "O(n^2) complexity: nested loops over same collection",
        "severity": "warning",
        "category": "performance",
        "suggestion": "Consider using set operations or dictionary lookups to reduce complexity"
    },
    "PERF002": {
        "description": "Repeated computation in loop",
        "severity": "warning",
        "category": "performance",
        "suggestion": "Cache the computation result before the loop"
    },
    "PERF003": {
        "description": "Unnecessary list comprehension",
        "severity": "info",
        "category": "performance",
        "suggestion": "Use a generator expression for memory efficiency when iterating"
    },
    "PERF004": {
        "description": "Global variable mutation inside loop",
        "severity": "warning",
        "category": "performance",
        "suggestion": "Local variable lookup is faster than global, consider passing as parameter"
    },
    "PERF005": {
        "description": "String concatenation in loop",
        "severity": "warning",
        "category": "performance",
        "suggestion": "Use str.join() or io.StringIO for efficient string building"
    },
    "PERF006": {
        "description": "Unused import detected",
        "severity": "info",
        "category": "performance",
        "suggestion": "Remove unused imports to improve startup time and clarity"
    },
    "PERF007": {
        "description": "Missing generator for iteration",
        "severity": "info",
        "category": "performance",
        "suggestion": "Use yield instead of building a list for large datasets"
    },
    "STYLE001": {
        "description": "Line exceeds maximum length",
        "severity": "info",
        "category": "style",
        "suggestion": "Break line into multiple lines or use intermediate variables"
    },
    "STYLE002": {
        "description": "Function/method missing docstring",
        "severity": "info",
        "category": "style",
        "suggestion": "Add a docstring describing the function purpose and parameters"
    },
    "STYLE003": {
        "description": "Function/method missing type hints",
        "severity": "info",
        "category": "style",
        "suggestion": "Add type hints for parameters and return value"
    },
    "STYLE004": {
        "description": "Magic number detected",
        "severity": "info",
        "category": "style",
        "suggestion": "Extract magic numbers into named constants"
    },
    "STYLE005": {
        "description": "Bare except clause",
        "severity": "warning",
        "category": "style",
        "suggestion": "Specify the exception type or use except Exception for better error handling"
    },
    "STYLE006": {
        "description": "Mutable default argument",
        "severity": "warning",
        "category": "style",
        "suggestion": "Use None as default and create mutable object inside function"
    },
    "STYLE007": {
        "description": "Class missing docstring",
        "severity": "info",
        "category": "style",
        "suggestion": "Add a docstring describing the class purpose"
    },
    "STYLE008": {
        "description": "Variable name not following snake_case convention",
        "severity": "info",
        "category": "style",
        "suggestion": "Use snake_case for variable and function names per PEP8"
    },
    "STYLE009": {
        "description": "Class name not using CamelCase",
        "severity": "info",
        "category": "style",
        "suggestion": "Use CamelCase for class names per PEP8"
    },
    "STYLE010": {
        "description": "Multiple statements on one line",
        "severity": "info",
        "category": "style",
        "suggestion": "Put each statement on its own line for readability"
    },
    "BUG001": {
        "description": "Missing return statement in function with return type",
        "severity": "error",
        "category": "bug",
        "suggestion": "Add explicit return statement to ensure consistent behavior"
    },
    "BUG002": {
        "description": "Variable used before assignment",
        "severity": "error",
        "category": "bug",
        "suggestion": "Initialize variable before conditional assignment or restructure logic"
    },
    "BUG003": {
        "description": "Potential None dereference",
        "severity": "warning",
        "category": "bug",
        "suggestion": "Add None check before accessing attributes or calling methods"
    },
    "BUG004": {
        "description": "Unreachable code detected",
        "severity": "warning",
        "category": "bug",
        "suggestion": "Remove dead code or fix control flow logic"
    },
    "BUG005": {
        "description": "Incorrect comparison operator",
        "severity": "error",
        "category": "bug",
        "suggestion": "Review comparison logic, did you mean == or !=?"
    },
    "BUG006": {
        "description": "Shadowed builtin name",
        "severity": "warning",
        "category": "bug",
        "suggestion": "Rename variable to avoid shadowing builtin functions"
    },
    "BUG007": {
        "description": "Potential infinite loop",
        "severity": "warning",
        "category": "bug",
        "suggestion": "Ensure loop has a definite termination condition"
    },
    "BUG008": {
        "description": "Exception silently caught and ignored",
        "severity": "warning",
        "category": "bug",
        "suggestion": "Log the exception or handle it appropriately"
    },
    "COMP001": {
        "description": "Function has too many branches",
        "severity": "warning",
        "category": "complexity",
        "suggestion": "Refactor into smaller functions to improve readability"
    },
    "COMP002": {
        "description": "Function is too long",
        "severity": "warning",
        "category": "complexity",
        "suggestion": "Break into smaller functions with clear responsibilities"
    },
    "COMP003": {
        "description": "Too many function parameters",
        "severity": "warning",
        "category": "complexity",
        "suggestion": "Use a configuration object or reduce parameter count"
    },
    "COMP004": {
        "description": "Excessive nesting depth",
        "severity": "warning",
        "category": "complexity",
        "suggestion": "Reduce nesting by using early returns or extracting logic"
    },
    "COMP005": {
        "description": "High cyclomatic complexity",
        "severity": "warning",
        "category": "complexity",
        "suggestion": "Simplify logic and break into smaller functions"
    },
    "COMP006": {
        "description": "Function has too many local variables",
        "severity": "warning",
        "category": "complexity",
        "suggestion": "Reduce local variables or extract into helper functions"
    },
    "COMP007": {
        "description": "Too many nested blocks",
        "severity": "warning",
        "category": "complexity",
        "suggestion": "Flatten logic or use guard clauses"
    },
}
VARIABLE_NAME_REGEX = re.compile(r'^[a-z_][a-z0-9_]*$')
CLASS_NAME_REGEX = re.compile(r'^[A-Z][a-zA-Z0-9_]*$')
FUNCTION_NAME_REGEX = re.compile(r'^[a-z_][a-z0-9_]*$')

BUILTIN_NAMES = {
    'abs', 'all', 'any', 'bin', 'bool', 'bytearray', 'bytes', 'callable',
    'chr', 'classmethod', 'compile', 'complex', 'delattr', 'dict', 'dir',
    'divmod', 'enumerate', 'eval', 'exec', 'filter', 'float', 'format',
    'frozenset', 'getattr', 'globals', 'hasattr', 'hash', 'help', 'hex',
    'id', 'input', 'int', 'isinstance', 'issubclass', 'iter', 'len',
    'list', 'locals', 'map', 'max', 'memoryview', 'min', 'next',
    'object', 'oct', 'open', 'ord', 'pow', 'print', 'property',
    'range', 'repr', 'reversed', 'round', 'set', 'setattr', 'slice',
    'sorted', 'staticmethod', 'str', 'sum', 'super', 'tuple', 'type',
    'vars', 'zip', '__import__',
}

MAX_LINE_LENGTH = 79
MAX_FUNCTION_LINES = 50
MAX_PARAMETERS = 5
MAX_NESTING_DEPTH = 4
MAX_COMPLEXITY = 10
MAX_LOCAL_VARS = 15


SECURITY_BAD = '''
import os
import pickle
import yaml

DB_PASSWORD = "super_secret_password_123"
API_KEY = "sk-1234567890abcdef1234567890abcdef"
SECRET_TOKEN = "ghp_abc123def456ghi789jkl012mno345pqr"

def get_user(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    return cursor.fetchone()

def run_command(cmd):
    result = os.system(cmd)
    return result

def load_data(data_bytes):
    return pickle.loads(data_bytes)

def parse_config(yaml_string):
    return yaml.load(yaml_string)

def process_file(filename):
    path = "/data/" + filename
    with open(path) as f:
        return f.read()

def dangerous_eval(expr):
    return eval(expr)

def dangerous_exec(code):
    exec(code)

def make_request():
    import requests
    return requests.get("https://api.example.com", verify=False)

import random
def generate_token():
    return str(random.randint(100000, 999999))

DEBUG = True

app.run(debug=True)
'''

PERFORMANCE_BAD = '''
import os

global_counter = 0

def find_duplicates_slow(items):
    duplicates = []
    for i in items:
        for j in items:
            if i == j and items.count(i) > 1:
                duplicates.append(i)
    return duplicates

def build_string_slow(words):
    result = ""
    for word in words:
        result = result + " " + word
    return result

def process_items(items):
    global global_counter
    results = []
    for item in items:
        global_counter += 1
        result = expensive_computation(item)
        result = expensive_computation(item)
        results.append(result)
    return [x for x in results if x is not None]

def read_large_file(filepath):
    with open(filepath) as f:
        lines = f.readlines()
    return [line.strip() for line in lines]

def transform_data(data):
    return [item * 2 for item in data if item > 0]

def merge_lists(list_a, list_b):
    merged = []
    for a in list_a:
        for b in list_b:
            if a == b:
                merged.append(a)
    return merged
'''

STYLE_BAD = '''
import os
import sys
import json
import re
from typing import List, Dict

MAX_SIZE = 1000
timeout_val = 30

class my_class:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def do_something(self, a, b, c, d, e, f, g):
        if a: pass
        try:
            result = a / b
        except:
            result = 0
        return result

def bad_defaults(items=[]):
    items.append(1)
    return items

def complicated(x=5, y=10, z=15):
    return x + y + z

def myFunction(myVar):
    result = myVar + 1
    return result

def add(a,b):
    return a+b

class my_object:
    pass

def no_hints(data):
    return data

def with_hints(data: List[int]) -> Dict[str, int]:
    return {"sum": sum(data)}

result = complicated(1,2,3)
data = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30]
'''

BUG_BAD = '''
def divide_numbers(a, b):
    result = a / b
    return result

def get_value(key, data):
    if key in data:
        value = data[key]
    return value

class User:
    def __init__(self, name=None):
        self.name = name
        self.age = None

    def get_info(self):
        return self.name.lower()

def process_list(items):
    for i in range(len(items)):
        if items[i] > 10:
            pass
        else:
            pass
    return

def risky_operation():
    try:
        return 1 / 0
    except ValueError:
        return None

def calculate(x):
    if x > 0:
        return x * 2
    elif x < 0:
        return x * -1

def check_type(value):
    if value == True:
        return "yes"
    if value == False:
        return "no"

list = [1, 2, 3]
dict = {"key": "value"}
print(list)
print(dict)

def infinite_check(n):
    x = 0
    while x < n:
        if x % 2 == 0:
            x += 1

def shadow_test():
    input = "test"
    return input

def maybe_none(data):
    result = data.get("key")
    length = len(result)
    return length

def compare_values(a, b):
    if a = b:
        return True
    return False
'''
@dataclass
class CodeIssue:
    """Represents a single code review issue found during analysis."""
    file_path: str
    line: int
    col: int
    severity: str
    category: str
    rule_id: str
    message: str
    suggestion: str
    code_snippet: str = ""
    fix_available: bool = False
    fix_code: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert issue to dictionary representation."""
        return asdict(self)


class SecurityScanner:
    """Scans Python code for security vulnerabilities and unsafe patterns."""

    def __init__(self):
        self.patterns = SECURITY_PATTERNS
        self.issues: List[CodeIssue] = []

    def scan_code(self, source: str, filename: str) -> List[CodeIssue]:
        """Scan source code for security issues and return list of CodeIssue."""
        self.issues = []
        self._scan_patterns(source, filename)
        self._scan_ast_security(source, filename)
        self._scan_ssl_verification(source, filename)
        self._scan_debug_flags(source, filename)
        return self.issues

    def _scan_patterns(self, source: str, filename: str) -> None:
        """Scan using regex patterns for common security issues."""
        lines = source.split('\n')
        rule_map = {
            "hardcoded_secret": "SEC001",
            "sql_injection": "SEC002",
            "command_injection": "SEC003",
            "path_traversal": "SEC004",
            "eval_exec": "SEC005",
            "pickle_deserialization": "SEC006",
            "unsafe_yaml": "SEC007",
            "insecure_random": "SEC008",
            "ssl_disabled": "SEC009",
            "debug_mode": "SEC010",
        }
        for category, pattern_list in self.patterns.items():
            rule_id = rule_map.get(category, "SEC001")
            for pattern in pattern_list:
                regex = re.compile(pattern)
                for line_num, line in enumerate(lines, start=1):
                    match = regex.search(line)
                    if match:
                        issue = self._create_pattern_issue(
                            filename, line_num, match.start(),
                            rule_id, line.strip(), category, pattern
                        )
                        self.issues.append(issue)

    def _create_pattern_issue(self, filename: str, line_num: int,
                              col: int, rule_id: str, line_text: str,
                              category: str, pattern: str) -> CodeIssue:
        """Create a CodeIssue from a pattern match."""
        rule_info = RULES.get(rule_id, {})
        suggestion = rule_info.get(
            "suggestion",
            f"Review line for {category} security issue"
        )
        return CodeIssue(
            file_path=filename,
            line=line_num,
            col=col,
            severity=rule_info.get("severity", "warning"),
            category="security",
            rule_id=rule_id,
            message=rule_info.get("description", f"Security issue: {category}"),
            suggestion=suggestion,
            code_snippet=line_text,
            fix_available=False,
            fix_code=""
        )

    def _scan_ast_security(self, source: str, filename: str) -> None:
        """Scan AST for security issues not caught by regex."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                self._check_dangerous_functions(node, filename)
            elif isinstance(node, ast.FunctionDef):
                self._check_function_security(node, filename)

    def _check_dangerous_functions(self, node: ast.Call, filename: str) -> None:
        """Check for dangerous function calls."""
        func_name = self._get_call_name(node)
        danger_map = {
            "eval": ("SEC005", "Use of eval() can execute arbitrary code"),
            "exec": ("SEC005", "Use of exec() can execute arbitrary code"),
            "__import__": ("SEC005", "Dynamic import can load malicious modules"),
            "compile": ("SEC005", "Dynamic compilation can be dangerous"),
            "globals": ("SEC005", "globals() access can lead to code injection"),
            "locals": ("SEC005", "locals() access can leak sensitive data"),
            "getattr": ("SEC005", "Dynamic attribute access can be exploited"),
            "setattr": ("SEC005", "Dynamic attribute setting can be dangerous"),
            "breakpoint": ("SEC010", "Breakpoint left in production code"),
        }
        if func_name in danger_map:
            rule_id, msg = danger_map[func_name]
            rule_info = RULES.get(rule_id, {})
            self.issues.append(CodeIssue(
                file_path=filename,
                line=getattr(node, 'lineno', 0),
                col=getattr(node, 'col_offset', 0),
                severity=rule_info.get("severity", "warning"),
                category="security",
                rule_id=rule_id,
                message=msg,
                suggestion=rule_info.get("suggestion", ""),
                code_snippet=f"{func_name}() call detected",
                fix_available=False
            ))

    def _get_call_name(self, node: ast.Call) -> str:
        """Extract function name from call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""

    def _check_function_security(self, node: ast.FunctionDef, filename: str) -> None:
        """Check function definitions for security patterns."""
        for default in node.args.defaults:
            if isinstance(default, ast.Constant) and isinstance(default.value, str):
                lower_val = default.value.lower()
                if any(kw in lower_val for kw in ['password', 'secret', 'key', 'token']):
                    self.issues.append(CodeIssue(
                        file_path=filename,
                        line=getattr(default, 'lineno', node.lineno),
                        col=getattr(default, 'col_offset', 0),
                        severity="error",
                        category="security",
                        rule_id="SEC001",
                        message="Potential secret in default parameter",
                        suggestion="Do not use secrets as default parameter values",
                        code_snippet=f"def {node.name}(..., secret='{default.value[:10]}...')",
                        fix_available=False
                    ))

    def _scan_ssl_verification(self, source: str, filename: str) -> None:
        """Scan for disabled SSL verification."""
        lines = source.split('\n')
        ssl_pattern = re.compile(r'verify\s*=\s*False|check_hostname\s*=\s*False')
        for line_num, line in enumerate(lines, start=1):
            match = ssl_pattern.search(line)
            if match:
                rule_info = RULES.get("SEC009", {})
                self.issues.append(CodeIssue(
                    file_path=filename,
                    line=line_num,
                    col=match.start(),
                    severity=rule_info.get("severity", "warning"),
                    category="security",
                    rule_id="SEC009",
                    message="SSL certificate verification disabled",
                    suggestion=rule_info.get("suggestion", "Enable SSL verification"),
                    code_snippet=line.strip(),
                    fix_available=True,
                    fix_code="verify=True"
                ))

    def _scan_debug_flags(self, source: str, filename: str) -> None:
        """Scan for debug flags enabled in production."""
        lines = source.split('\n')
        debug_pattern = re.compile(r'\bDEBUG\s*=\s*True|debug\s*=\s*True\b')
        for line_num, line in enumerate(lines, start=1):
            match = debug_pattern.search(line)
            if match:
                rule_info = RULES.get("SEC010", {})
                self.issues.append(CodeIssue(
                    file_path=filename,
                    line=line_num,
                    col=match.start(),
                    severity=rule_info.get("severity", "warning"),
                    category="security",
                    rule_id="SEC010",
                    message="Debug mode appears to be enabled",
                    suggestion=rule_info.get("suggestion", "Disable debug mode"),
                    code_snippet=line.strip(),
                    fix_available=True,
                    fix_code="DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'"
                ))
class PerformanceAnalyzer:
    """Analyzes code for performance issues and inefficiencies."""

    def __init__(self):
        self.issues: List[CodeIssue] = []

    def analyze(self, source: str, filename: str) -> List[CodeIssue]:
        """Analyze source code for performance issues."""
        self.issues = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return self.issues
        self._check_nested_loops(tree, filename)
        self._check_string_concatenation(tree, filename)
        self._check_global_mutations(tree, filename)
        self._check_repeated_computations(tree, filename)
        self._check_unused_imports(tree, source, filename)
        self._check_list_comprehension_patterns(tree, filename)
        self._check_generator_patterns(tree, filename)
        self._check_membership_testing(tree, filename)
        self._check_loop_variable_lookup(tree, filename)
        return self.issues

    def _check_nested_loops(self, tree: ast.AST, filename: str) -> None:
        """Detect nested loops over the same collection (O(n^2))."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                self._find_nested_loops_recursive(node, filename, depth=0)

    def _find_nested_loops_recursive(self, node: ast.AST, filename: str,
                                      depth: int) -> None:
        """Recursively find nested loops and report O(n^2) patterns."""
        if depth > 0 and isinstance(node, (ast.For, ast.While)):
            rule_info = RULES.get("PERF001", {})
            loop_type = "for" if isinstance(node, ast.For) else "while"
            self.issues.append(CodeIssue(
                file_path=filename,
                line=getattr(node, 'lineno', 0),
                col=getattr(node, 'col_offset', 0),
                severity=rule_info.get("severity", "warning"),
                category="performance",
                rule_id="PERF001",
                message=f"Nested {loop_type} loop creates O(n^2) complexity",
                suggestion=rule_info.get("suggestion", "Reduce nesting complexity"),
                code_snippet=self._get_node_source(node),
                fix_available=False
            ))
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.For, ast.While)):
                self._find_nested_loops_recursive(child, filename, depth + 1)
            else:
                self._find_nested_loops_recursive(child, filename, depth)

    def _get_node_source(self, node: ast.AST) -> str:
        """Get a simple string representation of an AST node."""
        if isinstance(node, ast.For):
            target = "i"
            if isinstance(node.target, ast.Name):
                target = node.target.id
            return f"for {target} in ..."
        elif isinstance(node, ast.While):
            return "while condition:"
        return "nested loop detected"

    def _check_string_concatenation(self, tree: ast.AST, filename: str) -> None:
        """Detect string concatenation in loops."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                self._check_loop_body_string_concat(node, filename)

    def _check_loop_body_string_concat(self, loop_node: ast.AST,
                                        filename: str) -> None:
        """Check loop body for string concatenation patterns."""
        body = getattr(loop_node, 'body', [])
        for stmt in body:
            if isinstance(stmt, ast.Assign):
                self._check_string_concat_in_assign(stmt, filename)
            elif isinstance(stmt, ast.AugAssign):
                if isinstance(stmt.op, ast.Add):
                    rule_info = RULES.get("PERF005", {})
                    self.issues.append(CodeIssue(
                        file_path=filename,
                        line=getattr(stmt, 'lineno', 0),
                        col=getattr(stmt, 'col_offset', 0),
                        severity=rule_info.get("severity", "warning"),
                        category="performance",
                        rule_id="PERF005",
                        message="String concatenation using += in loop",
                        suggestion=rule_info.get("suggestion", "Use str.join()"),
                        code_snippet="result += value",
                        fix_available=False
                    ))

    def _check_string_concat_in_assign(self, stmt: ast.Assign,
                                        filename: str) -> None:
        """Check assignment statement for string concatenation."""
        if isinstance(stmt.value, ast.BinOp) and isinstance(stmt.value.op, ast.Add):
            rule_info = RULES.get("PERF005", {})
            target_name = "unknown"
            if isinstance(stmt.targets[0], ast.Name):
                target_name = stmt.targets[0].id
            self.issues.append(CodeIssue(
                file_path=filename,
                line=getattr(stmt, 'lineno', 0),
                col=getattr(stmt, 'col_offset', 0),
                severity=rule_info.get("severity", "warning"),
                category="performance",
                rule_id="PERF005",
                message="String concatenation with + operator in loop",
                suggestion=rule_info.get("suggestion", "Use str.join() for efficiency"),
                code_snippet=f"{target_name} = {target_name} + value",
                fix_available=False
            ))

    def _check_global_mutations(self, tree: ast.AST, filename: str) -> None:
        """Detect global variable mutations inside loops."""
        global_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Global):
                for name in node.names:
                    global_names.add(name)
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                self._check_globals_in_loop(node, global_names, filename)

    def _check_globals_in_loop(self, loop_node: ast.AST,
                                global_names: set, filename: str) -> None:
        """Check if global variables are mutated inside a loop."""
        for stmt in ast.walk(loop_node):
            if isinstance(stmt, ast.Global):
                for name in stmt.names:
                    if name in global_names:
                        rule_info = RULES.get("PERF004", {})
                        self.issues.append(CodeIssue(
                            file_path=filename,
                            line=getattr(stmt, 'lineno', 0),
                            col=getattr(stmt, 'col_offset', 0),
                            severity=rule_info.get("severity", "warning"),
                            category="performance",
                            rule_id="PERF004",
                            message=f"Global variable '{name}' mutated in loop",
                            suggestion=rule_info.get("suggestion", "Use local variables"),
                            code_snippet=f"global {name}",
                            fix_available=False
                        ))

    def _check_repeated_computations(self, tree: ast.AST, filename: str) -> None:
        """Detect repeated function calls with same arguments in loops."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                self._find_repeated_calls(node, filename)

    def _find_repeated_calls(self, node: ast.AST, filename: str) -> None:
        """Find repeated function calls in loop body."""
        call_counts: Dict[str, int] = {}
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_key = self._get_call_signature(child)
                if call_key in call_counts:
                    call_counts[call_key] += 1
                else:
                    call_counts[call_key] = 1
        for call_key, count in call_counts.items():
            if count > 1:
                rule_info = RULES.get("PERF002", {})
                self.issues.append(CodeIssue(
                    file_path=filename,
                    line=getattr(node, 'lineno', 0),
                    col=getattr(node, 'col_offset', 0),
                    severity=rule_info.get("severity", "warning"),
                    category="performance",
                    rule_id="PERF002",
                    message=f"Function called {count} times with same arguments in loop",
                    suggestion=rule_info.get("suggestion", "Cache result before loop"),
                    code_snippet=call_key,
                    fix_available=False
                ))

    def _get_call_signature(self, node: ast.Call) -> str:
        """Generate a signature string for a function call."""
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
        args_len = len(node.args) + len(node.keywords)
        return f"{func_name}({args_len} args)"

    def _check_unused_imports(self, tree: ast.AST, source: str,
                               filename: str) -> None:
        """Detect unused imports."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports.append((name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name != '*':
                        name = alias.asname if alias.asname else alias.name
                        imports.append((name, node.lineno))
        for name, line_num in imports:
            usage_count = source.count(name)
            if usage_count <= 1:
                rule_info = RULES.get("PERF006", {})
                self.issues.append(CodeIssue(
                    file_path=filename,
                    line=line_num,
                    col=0,
                    severity=rule_info.get("severity", "info"),
                    category="performance",
                    rule_id="PERF006",
                    message=f"Import '{name}' appears unused",
                    suggestion=rule_info.get("suggestion", "Remove unused imports"),
                    code_snippet=f"import {name}",
                    fix_available=True,
                    fix_code=f"# Removed unused import: {name}"
                ))

    def _check_list_comprehension_patterns(self, tree: ast.AST,
                                            filename: str) -> None:
        """Check for unnecessary list comprehensions."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ListComp):
                self._check_if_generator_sufficient(node, filename)

    def _check_if_generator_sufficient(self, node: ast.ListComp,
                                        filename: str) -> None:
        """Check if a list comprehension could be a generator."""
        parent = getattr(node, '_parent', None)
        if parent and isinstance(parent, (ast.For, ast.While)):
            rule_info = RULES.get("PERF003", {})
            self.issues.append(CodeIssue(
                file_path=filename,
                line=getattr(node, 'lineno', 0),
                col=getattr(node, 'col_offset', 0),
                severity=rule_info.get("severity", "info"),
                category="performance",
                rule_id="PERF003",
                message="List comprehension could be a generator expression",
                suggestion=rule_info.get("suggestion", "Use generator for memory efficiency"),
                code_snippet="[expr for x in iterable]",
                fix_available=False
            ))

    def _check_generator_patterns(self, tree: ast.AST, filename: str) -> None:
        """Check for functions that could use yield."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._check_yield_opportunity(node, filename)

    def _check_yield_opportunity(self, node: ast.FunctionDef,
                                  filename: str) -> None:
        """Check if function building list could use yield."""
        has_append = False
        has_return_list = False
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func_name = ""
                if isinstance(child.func, ast.Attribute):
                    func_name = child.func.attr
                if func_name == "append":
                    has_append = True
            if isinstance(child, ast.Return) and isinstance(child.value, ast.Name):
                has_return_list = True
        if has_append and has_return_list:
            rule_info = RULES.get("PERF007", {})
            self.issues.append(CodeIssue(
                file_path=filename,
                line=node.lineno,
                col=node.col_offset,
                severity=rule_info.get("severity", "info"),
                category="performance",
                rule_id="PERF007",
                message=f"Function '{node.name}' builds list with append, could use yield",
                suggestion=rule_info.get("suggestion", "Consider using yield for lazy evaluation"),
                code_snippet=f"def {node.name}(): ...",
                fix_available=False
            ))

    def _check_membership_testing(self, tree: ast.AST, filename: str) -> None:
        """Check for membership testing on lists vs sets."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                for comparator in node.comparators:
                    if isinstance(comparator, ast.List) and len(comparator.elts) > 5:
                        for op in node.ops:
                            if isinstance(op, (ast.In, ast.NotIn)):
                                rule_info = RULES.get("PERF001", {})
                                self.issues.append(CodeIssue(
                                    file_path=filename,
                                    line=getattr(node, 'lineno', 0),
                                    col=getattr(node, 'col_offset', 0),
                                    severity=rule_info.get("severity", "info"),
                                    category="performance",
                                    rule_id="PERF001",
                                    message="Membership test on large list literal, use set instead",
                                    suggestion="Convert list to set for O(1) lookup",
                                    code_snippet="x in [large list]",
                                    fix_available=False
                                ))

    def _check_loop_variable_lookup(self, tree: ast.AST, filename: str) -> None:
        """Check for attribute lookups in tight loops."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                self._scan_loop_body_for_lookup(node, filename)

    def _scan_loop_body_for_lookup(self, loop_node: ast.AST, filename: str) -> None:
        """Scan loop body for repeated attribute lookups."""
        attr_lookups: Dict[str, int] = {}
        for child in ast.walk(loop_node):
            if isinstance(child, ast.Attribute):
                if isinstance(child.value, ast.Name):
                    key = f"{child.value.id}.{child.attr}"
                    attr_lookups[key] = attr_lookups.get(key, 0) + 1
        for key, count in attr_lookups.items():
            if count > 3:
                rule_info = RULES.get("PERF002", {})
                self.issues.append(CodeIssue(
                    file_path=filename,
                    line=getattr(loop_node, 'lineno', 0),
                    col=getattr(loop_node, 'col_offset', 0),
                    severity=rule_info.get("severity", "info"),
                    category="performance",
                    rule_id="PERF002",
                    message=f"Attribute '{key}' accessed {count} times in loop",
                    suggestion="Cache attribute lookup in local variable",
                    code_snippet=key,
                    fix_available=False
                ))
class StyleChecker:
    """Checks Python code against PEP8 and style conventions."""

    def __init__(self):
        self.issues: List[CodeIssue] = []

    def check(self, source: str, filename: str) -> List[CodeIssue]:
        """Check source code for style violations."""
        self.issues = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return self.issues
        lines = source.split('\n')
        self._check_line_length(lines, filename)
        self._check_naming_conventions(tree, filename)
        self._check_docstrings(tree, filename)
        self._check_type_hints(tree, filename)
        self._check_magic_numbers(tree, filename)
        self._check_bare_excepts(tree, filename)
        self._check_mutable_defaults(tree, filename)
        self._check_multiple_statements(lines, filename)
        self._check_import_ordering(tree, source, filename)
        return self.issues

    def _check_line_length(self, lines: List[str], filename: str) -> None:
        """Check for lines exceeding maximum length."""
        rule_info = RULES.get("STYLE001", {})
        for line_num, line in enumerate(lines, start=1):
            if len(line) > MAX_LINE_LENGTH:
                self.issues.append(CodeIssue(
                    file_path=filename,
                    line=line_num,
                    col=MAX_LINE_LENGTH,
                    severity=rule_info.get("severity", "info"),
                    category="style",
                    rule_id="STYLE001",
                    message=f"Line length {len(line)} exceeds {MAX_LINE_LENGTH}",
                    suggestion=rule_info.get("suggestion", "Break line into multiple lines"),
                    code_snippet=line[:80] + "..." if len(line) > 80 else line,
                    fix_available=False
                ))

    def _check_naming_conventions(self, tree: ast.AST, filename: str) -> None:
        """Check naming conventions for variables, functions, and classes."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._check_function_naming(node, filename)
            elif isinstance(node, ast.ClassDef):
                self._check_class_naming(node, filename)
            elif isinstance(node, ast.Assign):
                self._check_variable_naming(node, filename)

    def _check_function_naming(self, node: ast.FunctionDef, filename: str) -> None:
        """Check function name follows snake_case."""
        rule_info = RULES.get("STYLE008", {})
        if not FUNCTION_NAME_REGEX.match(node.name) and not node.name.startswith('_'):
            self.issues.append(CodeIssue(
                file_path=filename,
                line=node.lineno,
                col=node.col_offset,
                severity=rule_info.get("severity", "info"),
                category="style",
                rule_id="STYLE008",
                message=f"Function name '{node.name}' does not follow snake_case",
                suggestion=rule_info.get("suggestion", "Use snake_case for function names"),
                code_snippet=f"def {node.name}(...)",
                fix_available=False
            ))

    def _check_class_naming(self, node: ast.ClassDef, filename: str) -> None:
        """Check class name follows CamelCase."""
        rule_info = RULES.get("STYLE009", {})
        if not CLASS_NAME_REGEX.match(node.name):
            self.issues.append(CodeIssue(
                file_path=filename,
                line=node.lineno,
                col=node.col_offset,
                severity=rule_info.get("severity", "info"),
                category="style",
                rule_id="STYLE009",
                message=f"Class name '{node.name}' does not follow CamelCase",
                suggestion=rule_info.get("suggestion", "Use CamelCase for class names"),
                code_snippet=f"class {node.name}:",
                fix_available=False
            ))

    def _check_variable_naming(self, node: ast.Assign, filename: str) -> None:
        """Check variable names follow snake_case."""
        rule_info = RULES.get("STYLE008", {})
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id
                if not name.startswith('_') and name.islower():
                    if not VARIABLE_NAME_REGEX.match(name) and name not in BUILTIN_NAMES:
                        self.issues.append(CodeIssue(
                            file_path=filename,
                            line=getattr(target, 'lineno', 0),
                            col=getattr(target, 'col_offset', 0),
                            severity=rule_info.get("severity", "info"),
                            category="style",
                            rule_id="STYLE008",
                            message=f"Variable name '{name}' does not follow snake_case",
                            suggestion=rule_info.get("suggestion", "Use snake_case for variables"),
                            code_snippet=f"{name} = ...",
                            fix_available=False
                        ))

    def _check_docstrings(self, tree: ast.AST, filename: str) -> None:
        """Check for missing docstrings in functions, classes, and modules."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._check_function_docstring(node, filename)
            elif isinstance(node, ast.ClassDef):
                self._check_class_docstring(node, filename)

    def _check_function_docstring(self, node: ast.FunctionDef, filename: str) -> None:
        """Check if function has a docstring."""
        rule_info = RULES.get("STYLE002", {})
        if not self._has_docstring(node):
            self.issues.append(CodeIssue(
                file_path=filename,
                line=node.lineno,
                col=node.col_offset,
                severity=rule_info.get("severity", "info"),
                category="style",
                rule_id="STYLE002",
                message=f"Function '{node.name}' is missing a docstring",
                suggestion=rule_info.get("suggestion", "Add docstring describing purpose"),
                code_snippet=f"def {node.name}(...):",
                fix_available=True,
                fix_code=f'def {node.name}(...):\n    """TODO: Add docstring."""\n'
            ))

    def _check_class_docstring(self, node: ast.ClassDef, filename: str) -> None:
        """Check if class has a docstring."""
        rule_info = RULES.get("STYLE007", {})
        if not self._has_docstring(node):
            self.issues.append(CodeIssue(
                file_path=filename,
                line=node.lineno,
                col=node.col_offset,
                severity=rule_info.get("severity", "info"),
                category="style",
                rule_id="STYLE007",
                message=f"Class '{node.name}' is missing a docstring",
                suggestion=rule_info.get("suggestion", "Add docstring describing class purpose"),
                code_snippet=f"class {node.name}:",
                fix_available=True,
                fix_code=f'class {node.name}:\n    """TODO: Add docstring."""\n'
            ))

    def _has_docstring(self, node: ast.AST) -> bool:
        """Check if a function or class node has a docstring."""
        body = getattr(node, 'body', [])
        if not body:
            return False
        first_stmt = body[0]
        if isinstance(first_stmt, ast.Expr) and isinstance(first_stmt.value, ast.Constant):
            if isinstance(first_stmt.value.value, str):
                return True
        if isinstance(first_stmt, ast.Expr) and isinstance(first_stmt.value, ast.Str):
            return True
        return False

    def _check_type_hints(self, tree: ast.AST, filename: str) -> None:
        """Check for missing type hints in function signatures."""
        rule_info = RULES.get("STYLE003", {})
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                missing_hints = []
                for arg in node.args.args:
                    if arg.arg != 'self' and arg.arg != 'cls':
                        if arg.annotation is None:
                            missing_hints.append(arg.arg)
                if node.returns is None and node.name != '__init__':
                    missing_hints.append('return')
                if missing_hints:
                    self.issues.append(CodeIssue(
                        file_path=filename,
                        line=node.lineno,
                        col=node.col_offset,
                        severity=rule_info.get("severity", "info"),
                        category="style",
                        rule_id="STYLE003",
                        message=f"Function '{node.name}' missing type hints for: {', '.join(missing_hints[:3])}",
                        suggestion=rule_info.get("suggestion", "Add type hints"),
                        code_snippet=f"def {node.name}(...):",
                        fix_available=True,
                        fix_code=self._generate_type_hint_stub(node)
                    ))

    def _generate_type_hint_stub(self, node: ast.FunctionDef) -> str:
        """Generate a type hint stub for a function."""
        args = []
        for arg in node.args.args:
            if arg.arg == 'self' or arg.arg == 'cls':
                args.append(arg.arg)
            else:
                args.append(f"{arg.arg}: Any")
        args_str = ", ".join(args)
        return f"def {node.name}({args_str}) -> Any: ..."

    def _check_magic_numbers(self, tree: ast.AST, filename: str) -> None:
        """Check for magic numbers in code."""
        rule_info = RULES.get("STYLE004", {})
        skip_contexts = {ast.Constant, ast.Name, ast.Attribute}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._find_magic_numbers_in_function(node, filename, rule_info)

    def _find_magic_numbers_in_function(self, node: ast.FunctionDef,
                                         filename: str, rule_info: dict) -> None:
        """Find magic numbers in a function body."""
        for child in ast.walk(node):
            if isinstance(child, ast.Constant) and isinstance(child.value, (int, float)):
                if child.value not in (0, 1, -1, 0.0, 1.0, 0.5, 100, 1000, -1):
                    parent = getattr(child, '_parent', None)
                    if not isinstance(parent, ast.keyword):
                        self.issues.append(CodeIssue(
                            file_path=filename,
                            line=getattr(child, 'lineno', 0),
                            col=getattr(child, 'col_offset', 0),
                            severity=rule_info.get("severity", "info"),
                            category="style",
                            rule_id="STYLE004",
                            message=f"Magic number {child.value} should be a named constant",
                            suggestion=rule_info.get("suggestion", "Extract to named constant"),
                            code_snippet=str(child.value),
                            fix_available=False
                        ))

    def _check_bare_excepts(self, tree: ast.AST, filename: str) -> None:
        """Check for bare except clauses."""
        rule_info = RULES.get("STYLE005", {})
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    self.issues.append(CodeIssue(
                        file_path=filename,
                        line=node.lineno,
                        col=node.col_offset,
                        severity=rule_info.get("severity", "warning"),
                        category="style",
                        rule_id="STYLE005",
                        message="Bare except clause catches all exceptions",
                        suggestion=rule_info.get("suggestion", "Specify exception type"),
                        code_snippet="except:",
                        fix_available=True,
                        fix_code="except Exception:"
                    ))

    def _check_mutable_defaults(self, tree: ast.AST, filename: str) -> None:
        """Check for mutable default arguments."""
        rule_info = RULES.get("STYLE006", {})
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        self.issues.append(CodeIssue(
                            file_path=filename,
                            line=getattr(default, 'lineno', node.lineno),
                            col=getattr(default, 'col_offset', 0),
                            severity=rule_info.get("severity", "warning"),
                            category="style",
                            rule_id="STYLE006",
                            message=f"Mutable default argument in '{node.name}'",
                            suggestion=rule_info.get("suggestion", "Use None as default"),
                            code_snippet=f"def {node.name}(..., default=[])",
                            fix_available=True,
                            fix_code=f"def {node.name}(..., default=None):"
                        ))
                for default in node.args.kw_defaults:
                    if default is not None and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        self.issues.append(CodeIssue(
                            file_path=filename,
                            line=getattr(default, 'lineno', node.lineno),
                            col=getattr(default, 'col_offset', 0),
                            severity=rule_info.get("severity", "warning"),
                            category="style",
                            rule_id="STYLE006",
                            message=f"Mutable default keyword argument in '{node.name}'",
                            suggestion=rule_info.get("suggestion", "Use None as default"),
                            code_snippet=f"def {node.name}(..., default={{}})",
                            fix_available=True,
                            fix_code=f"def {node.name}(..., default=None):"
                        ))

    def _check_multiple_statements(self, lines: List[str], filename: str) -> None:
        """Check for multiple statements on one line."""
        rule_info = RULES.get("STYLE010", {})
        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                if stripped.startswith(('if ', 'for ', 'while ', 'with ', 'try:', 'except')):
                    if ';' in stripped:
                        self.issues.append(CodeIssue(
                            file_path=filename,
                            line=line_num,
                            col=stripped.find(';'),
                            severity=rule_info.get("severity", "info"),
                            category="style",
                            rule_id="STYLE010",
                            message="Multiple statements on one line",
                            suggestion=rule_info.get("suggestion", "Put each statement on its own line"),
                            code_snippet=stripped[:60],
                            fix_available=False
                        ))

    def _check_import_ordering(self, tree: ast.AST, source: str,
                                filename: str) -> None:
        """Check import ordering (stdlib before third-party)."""
        stdlib_modules = {
            'os', 'sys', 'json', 're', 'math', 'hashlib', 'ast',
            'tokenize', 'io', 'types', 'warnings', 'pathlib',
            'collections', 'enum', 'dataclasses', 'typing',
            'functools', 'itertools', 'operator', 'string',
            'textwrap', 'unicodedata', 'difflib', 'traceback',
            'unittest', 'logging', 'getpass', 'platform',
        }
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name.split('.')[0]
                    imports.append((mod, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    mod = node.module.split('.')[0]
                    imports.append((mod, node.lineno))
        seen_third_party = False
        for mod, line_num in imports:
            if mod not in stdlib_modules:
                seen_third_party = True
            elif seen_third_party:
                rule_info = RULES.get("STYLE001", {})
                self.issues.append(CodeIssue(
                    file_path=filename,
                    line=line_num,
                    col=0,
                    severity="info",
                    category="style",
                    rule_id="STYLE001",
                    message=f"Standard library import '{mod}' should come before third-party imports",
                    suggestion="Reorder imports per PEP8 (stdlib, third-party, local)",
                    code_snippet=f"import {mod}",
                    fix_available=False
                ))
class BugDetector:
    """Detects potential bugs and logical errors in Python code."""

    def __init__(self):
        self.issues: List[CodeIssue] = []

    def detect(self, source: str, filename: str) -> List[CodeIssue]:
        """Detect potential bugs in source code."""
        self.issues = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            self._report_syntax_error(source, filename)
            return self.issues
        self._check_missing_returns(tree, filename)
        self._check_uninitialized_variables(tree, filename)
        self._check_none_dereference(tree, filename)
        self._check_unreachable_code(tree, filename)
        self._check_comparison_operators(tree, filename)
        self._check_shadowed_builtins(tree, filename)
        self._check_bare_except_patterns(tree, filename)
        self._check_infinite_loop_patterns(tree, filename)
        self._check_boolean_comparisons(tree, filename)
        self._check_exception_handling(tree, filename)
        self._check_return_consistency(tree, filename)
        return self.issues

    def _report_syntax_error(self, source: str, filename: str) -> None:
        """Report syntax errors in the source code."""
        try:
            ast.parse(source)
        except SyntaxError as e:
            self.issues.append(CodeIssue(
                file_path=filename,
                line=e.lineno or 0,
                col=e.offset or 0,
                severity="error",
                category="bug",
                rule_id="BUG001",
                message=f"Syntax error: {e.msg}",
                suggestion="Fix the syntax error before further analysis",
                code_snippet=str(e.text)[:80] if e.text else "",
                fix_available=False
            ))

    def _check_missing_returns(self, tree: ast.AST, filename: str) -> None:
        """Check for functions with missing return statements."""
        rule_info = RULES.get("BUG001", {})
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._analyze_return_paths(node, filename, rule_info)

    def _analyze_return_paths(self, node: ast.FunctionDef, filename: str,
                               rule_info: dict) -> None:
        """Analyze return paths in a function."""
        has_return = False
        all_paths_return = True
        for child in ast.walk(node):
            if isinstance(child, ast.Return):
                has_return = True
            if isinstance(child, ast.If):
                has_if_return = self._check_if_all_paths_return(child)
                if not has_if_return:
                    all_paths_return = False
        if node.returns is not None and not has_return:
            self.issues.append(CodeIssue(
                file_path=filename,
                line=node.lineno,
                col=node.col_offset,
                severity=rule_info.get("severity", "error"),
                category="bug",
                rule_id="BUG001",
                message=f"Function '{node.name}' has return annotation but no return statement",
                suggestion=rule_info.get("suggestion", "Add return statement"),
                code_snippet=f"def {node.name}(...) -> {ast.dump(node.returns)}:",
                fix_available=False
            ))

    def _check_if_all_paths_return(self, node: ast.If) -> bool:
        """Check if all branches of an if statement return."""
        if_returns = self._block_has_return(node.body)
        else_returns = False
        if node.orelse:
            else_returns = self._block_has_return(node.orelse)
        return if_returns and else_returns

    def _block_has_return(self, body: list) -> bool:
        """Check if a block of statements contains a return."""
        for stmt in body:
            if isinstance(stmt, ast.Return):
                return True
            if isinstance(stmt, ast.If):
                if self._check_if_all_paths_return(stmt):
                    return True
        return False

    def _check_uninitialized_variables(self, tree: ast.AST, filename: str) -> None:
        """Check for variables that may be used before assignment."""
        rule_info = RULES.get("BUG002", {})
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._check_func_var_init(node, filename, rule_info)

    def _check_func_var_init(self, node: ast.FunctionDef, filename: str,
                              rule_info: dict) -> None:
        """Check variable initialization in a function."""
        assigned_names = set()
        used_names = []
        for arg in node.args.args:
            assigned_names.add(arg.arg)
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                if isinstance(child.ctx, ast.Store):
                    assigned_names.add(child.id)
                elif isinstance(child.ctx, ast.Load):
                    used_names.append((child.id, getattr(child, 'lineno', 0)))
        for name, line_num in used_names:
            if name not in assigned_names and not name.startswith('_'):
                if name not in BUILTIN_NAMES and name not in ('self', 'cls'):
                    self.issues.append(CodeIssue(
                        file_path=filename,
                        line=line_num,
                        col=0,
                        severity=rule_info.get("severity", "error"),
                        category="bug",
                        rule_id="BUG002",
                        message=f"Variable '{name}' may be used before assignment",
                        suggestion=rule_info.get("suggestion", "Initialize variable"),
                        code_snippet=name,
                        fix_available=False
                    ))

    def _check_none_dereference(self, tree: ast.AST, filename: str) -> None:
        """Check for potential None dereference."""
        rule_info = RULES.get("BUG003", {})
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._check_func_none_deref(node, filename, rule_info)

    def _check_func_none_deref(self, node: ast.FunctionDef, filename: str,
                                rule_info: dict) -> None:
        """Check for None dereference in a function."""
        nullable_names = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func_name = ""
                if isinstance(child.func, ast.Name):
                    func_name = child.func.id
                nullable_funcs = {'dict', 'list', 'get', 'pop', 'getattr', 'os.getenv'}
                if func_name in nullable_funcs:
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                        if child.func.attr in ('get', 'pop'):
                            if isinstance(child.func.value, ast.Name):
                                nullable_names.add(child.func.value.id)
            if isinstance(child, ast.Attribute):
                if isinstance(child.value, ast.Name):
                    if child.value.id in nullable_names:
                        self.issues.append(CodeIssue(
                            file_path=filename,
                            line=getattr(child, 'lineno', 0),
                            col=getattr(child, 'col_offset', 0),
                            severity=rule_info.get("severity", "warning"),
                            category="bug",
                            rule_id="BUG003",
                            message=f"Potential None dereference on '{child.value.id}'",
                            suggestion=rule_info.get("suggestion", "Add None check"),
                            code_snippet=f"{child.value.id}.{child.attr}",
                            fix_available=False
                        ))

    def _check_unreachable_code(self, tree: ast.AST, filename: str) -> None:
        """Check for unreachable code after return/break/continue."""
        rule_info = RULES.get("BUG004", {})
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.For, ast.While, ast.If, ast.With)):
                self._find_unreachable_in_block(node.body, filename, rule_info)
                if isinstance(node, ast.If):
                    self._find_unreachable_in_block(node.orelse, filename, rule_info)

    def _find_unreachable_in_block(self, body: list, filename: str,
                                    rule_info: dict) -> None:
        """Find unreachable code in a block."""
        found_terminator = False
        terminator_line = 0
        for stmt in body:
            if found_terminator:
                self.issues.append(CodeIssue(
                    file_path=filename,
                    line=getattr(stmt, 'lineno', 0),
                    col=getattr(stmt, 'col_offset', 0),
                    severity=rule_info.get("severity", "warning"),
                    category="bug",
                    rule_id="BUG004",
                    message="Unreachable code after return/break/continue/raise",
                    suggestion=rule_info.get("suggestion", "Remove dead code"),
                    code_snippet=f"line {getattr(stmt, 'lineno', '?')}",
                    fix_available=False
                ))
                break
            if isinstance(stmt, (ast.Return, ast.Break, ast.Continue, ast.Raise)):
                found_terminator = True
                terminator_line = getattr(stmt, 'lineno', 0)

    def _check_comparison_operators(self, tree: ast.AST, filename: str) -> None:
        """Check for incorrect comparison operators."""
        rule_info = RULES.get("BUG005", {})
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                for op in node.ops:
                    if isinstance(op, ast.Assign):
                        self.issues.append(CodeIssue(
                            file_path=filename,
                            line=getattr(node, 'lineno', 0),
                            col=getattr(node, 'col_offset', 0),
                            severity=rule_info.get("severity", "error"),
                            category="bug",
                            rule_id="BUG005",
                            message="Assignment (=) used instead of comparison (==)",
                            suggestion=rule_info.get("suggestion", "Use == for comparison"),
                            code_snippet="if a = b:",
                            fix_available=True,
                            fix_code="if a == b:"
                        ))

    def _check_shadowed_builtins(self, tree: ast.AST, filename: str) -> None:
        """Check for variables shadowing builtins."""
        rule_info = RULES.get("BUG006", {})
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._find_shadowed_names(node, filename, rule_info)

    def _find_shadowed_names(self, node: ast.FunctionDef, filename: str,
                              rule_info: dict) -> None:
        """Find variables that shadow builtin names."""
        for arg in node.args.args:
            if arg.arg in BUILTIN_NAMES:
                self.issues.append(CodeIssue(
                    file_path=filename,
                    line=node.lineno,
                    col=node.col_offset,
                    severity=rule_info.get("severity", "warning"),
                    category="bug",
                    rule_id="BUG006",
                    message=f"Parameter '{arg.arg}' shadows builtin '{arg.arg}'",
                    suggestion=rule_info.get("suggestion", "Rename to avoid shadowing"),
                    code_snippet=f"def {node.name}({arg.arg}=...)",
                    fix_available=False
                ))
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                if child.id in BUILTIN_NAMES:
                    self.issues.append(CodeIssue(
                        file_path=filename,
                        line=getattr(child, 'lineno', 0),
                        col=getattr(child, 'col_offset', 0),
                        severity=rule_info.get("severity", "warning"),
                        category="bug",
                        rule_id="BUG006",
                        message=f"Variable '{child.id}' shadows builtin '{child.id}'",
                        suggestion=rule_info.get("suggestion", "Rename variable"),
                        code_snippet=f"{child.id} = ...",
                        fix_available=False
                    ))

    def _check_bare_except_patterns(self, tree: ast.AST, filename: str) -> None:
        """Check for except blocks that silently swallow exceptions."""
        rule_info = RULES.get("BUG008", {})
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.name:
                    has_reraise = False
                    for child in ast.walk(node):
                        if isinstance(child, ast.Raise):
                            has_reraise = True
                        if isinstance(child, (ast.Return, ast.Continue, ast.Break)):
                            has_reraise = True
                    if not has_reraise and len(node.body) == 1:
                        if isinstance(node.body[0], ast.Pass):
                            self.issues.append(CodeIssue(
                                file_path=filename,
                                line=node.lineno,
                                col=node.col_offset,
                                severity=rule_info.get("severity", "warning"),
                                category="bug",
                                rule_id="BUG008",
                                message=f"Exception '{node.name}' caught and silently ignored",
                                suggestion=rule_info.get("suggestion", "Log or handle the exception"),
                                code_snippet=f"except {node.name}: pass",
                                fix_available=False
                            ))

    def _check_infinite_loop_patterns(self, tree: ast.AST, filename: str) -> None:
        """Check for potential infinite loops."""
        rule_info = RULES.get("BUG007", {})
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                self._analyze_while_loop(node, filename, rule_info)

    def _analyze_while_loop(self, node: ast.While, filename: str,
                             rule_info: dict) -> None:
        """Analyze while loop for infinite loop patterns."""
        if isinstance(node.test, ast.Constant) and node.test.value is True:
            self.issues.append(CodeIssue(
                file_path=filename,
                line=node.lineno,
                col=node.col_offset,
                severity=rule_info.get("severity", "warning"),
                category="bug",
                rule_id="BUG007",
                message="Infinite loop: while True without break",
                suggestion=rule_info.get("suggestion", "Ensure loop has exit condition"),
                code_snippet="while True:",
                fix_available=False
            ))
        has_break = False
        has_increment = False
        for child in ast.walk(node):
            if isinstance(child, ast.Break):
                has_break = True
            if isinstance(child, ast.AugAssign):
                has_increment = True
            if isinstance(child, ast.Assign):
                if isinstance(child.targets[0], ast.Name):
                    if child.targets[0].id in ('x', 'i', 'j', 'k', 'n', 'count', 'idx'):
                        has_increment = True
        if not has_break and not has_increment and isinstance(node.test, ast.Name):
            self.issues.append(CodeIssue(
                file_path=filename,
                line=node.lineno,
                col=node.col_offset,
                severity=rule_info.get("severity", "warning"),
                category="bug",
                rule_id="BUG007",
                message="Potential infinite loop: no break or variable increment found",
                suggestion=rule_info.get("suggestion", "Verify loop termination"),
                code_snippet=f"while {ast.dump(node.test)}:",
                fix_available=False
            ))

    def _check_boolean_comparisons(self, tree: ast.AST, filename: str) -> None:
        """Check for comparisons to True/False using == instead of is."""
        rule_info = RULES.get("BUG005", {})
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                for i, (op, comparator) in enumerate(zip(node.ops, node.comparators)):
                    if isinstance(comparator, ast.Constant):
                        if comparator.value is True or comparator.value is False:
                            if isinstance(op, (ast.Eq, ast.NotEq)):
                                bool_val = "True" if comparator.value else "False"
                                self.issues.append(CodeIssue(
                                    file_path=filename,
                                    line=getattr(node, 'lineno', 0),
                                    col=getattr(node, 'col_offset', 0),
                                    severity=rule_info.get("severity", "warning"),
                                    category="bug",
                                    rule_id="BUG005",
                                    message=f"Comparison to {bool_val} should use 'is' not '=='",
                                    suggestion=f"Use 'is {bool_val}' instead of '== {bool_val}'",
                                    code_snippet=f"x == {bool_val}",
                                    fix_available=True,
                                    fix_code=f"x is {bool_val}"
                                ))

    def _check_exception_handling(self, tree: ast.AST, filename: str) -> None:
        """Check for overly broad exception handling."""
        rule_info = RULES.get("BUG008", {})
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for handler in node.handlers:
                    if handler.type is None:
                        self.issues.append(CodeIssue(
                            file_path=filename,
                            line=handler.lineno,
                            col=handler.col_offset,
                            severity="warning",
                            category="bug",
                            rule_id="BUG008",
                            message="Bare except catches all exceptions including SystemExit",
                            suggestion="Catch specific exceptions or use except Exception",
                            code_snippet="except:",
                            fix_available=True,
                            fix_code="except Exception:"
                        ))

    def _check_return_consistency(self, tree: ast.AST, filename: str) -> None:
        """Check for inconsistent return values in function."""
        rule_info = RULES.get("BUG001", {})
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._check_func_return_consistency(node, filename, rule_info)

    def _check_func_return_consistency(self, node: ast.FunctionDef,
                                        filename: str, rule_info: dict) -> None:
        """Check if a function returns consistently."""
        return_types = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Return):
                if child.value is None:
                    return_types.add("None")
                elif isinstance(child.value, ast.Constant):
                    return_types.add(type(child.value.value).__name__)
                elif isinstance(child.value, ast.Name):
                    return_types.add("variable")
                elif isinstance(child.value, ast.Call):
                    return_types.add("call")
                else:
                    return_types.add("expression")
        if len(return_types) > 2:
            self.issues.append(CodeIssue(
                file_path=filename,
                line=node.lineno,
                col=node.col_offset,
                severity="info",
                category="bug",
                rule_id="BUG001",
                message=f"Function '{node.name}' has inconsistent return types: {', '.join(return_types)}",
                suggestion="Ensure function returns consistent types",
                code_snippet=f"def {node.name}():",
                fix_available=False
            ))
class ComplexityAnalyzer:
    """Analyzes code complexity using McCabe cyclomatic complexity and other metrics."""

    def __init__(self):
        self.issues: List[CodeIssue] = []

    def analyze(self, source: str, filename: str) -> List[CodeIssue]:
        """Analyze source code complexity."""
        self.issues = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return self.issues
        self._check_cyclomatic_complexity(tree, filename)
        self._check_nesting_depth(tree, filename)
        self._check_function_length(tree, filename)
        self._check_parameter_count(tree, filename)
        self._check_local_variable_count(tree, filename)
        self._check_class_methods_count(tree, filename)
        self._check_nested_classes(tree, filename)
        self._check_function_count(tree, filename)
        self._check_module_length(tree, source, filename)
        return self.issues

    def _check_cyclomatic_complexity(self, tree: ast.AST, filename: str) -> None:
        """Calculate cyclomatic complexity for each function."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = self._calculate_complexity(node)
                rule_info = RULES.get("COMP005", {})
                if complexity > MAX_COMPLEXITY:
                    self.issues.append(CodeIssue(
                        file_path=filename,
                        line=node.lineno,
                        col=node.col_offset,
                        severity=rule_info.get("severity", "warning"),
                        category="complexity",
                        rule_id="COMP005",
                        message=f"Function '{node.name}' has cyclomatic complexity of {complexity} (max {MAX_COMPLEXITY})",
                        suggestion=rule_info.get("suggestion", "Simplify logic"),
                        code_snippet=f"def {node.name}()  # complexity: {complexity}",
                        fix_available=False
                    ))
                elif complexity > MAX_COMPLEXITY // 2:
                    self.issues.append(CodeIssue(
                        file_path=filename,
                        line=node.lineno,
                        col=node.col_offset,
                        severity="info",
                        category="complexity",
                        rule_id="COMP005",
                        message=f"Function '{node.name}' has moderate complexity of {complexity}",
                        suggestion="Consider simplifying if possible",
                        code_snippet=f"def {node.name}()  # complexity: {complexity}",
                        fix_available=False
                    ))

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate McCabe cyclomatic complexity for a function."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
                if child.ifs:
                    complexity += len(child.ifs)
        return complexity

    def _check_nesting_depth(self, tree: ast.AST, filename: str) -> None:
        """Check for excessive nesting depth."""
        rule_info = RULES.get("COMP004", {})
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                max_depth = self._find_max_nesting(node)
                if max_depth > MAX_NESTING_DEPTH:
                    self.issues.append(CodeIssue(
                        file_path=filename,
                        line=node.lineno,
                        col=node.col_offset,
                        severity=rule_info.get("severity", "warning"),
                        category="complexity",
                        rule_id="COMP004",
                        message=f"Function '{node.name}' has nesting depth of {max_depth} (max {MAX_NESTING_DEPTH})",
                        suggestion=rule_info.get("suggestion", "Reduce nesting"),
                        code_snippet=f"def {node.name}()  # depth: {max_depth}",
                        fix_available=False
                    ))

    def _find_max_nesting(self, node: ast.AST, current_depth: int = 0) -> int:
        """Find maximum nesting depth in an AST node."""
        max_depth = current_depth
        nesting_nodes = (ast.If, ast.For, ast.While, ast.With, ast.Try)
        for child in ast.iter_child_nodes(node):
            if isinstance(child, nesting_nodes):
                child_depth = self._find_max_nesting(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = self._find_max_nesting(child, current_depth)
                max_depth = max(max_depth, child_depth)
        return max_depth

    def _check_function_length(self, tree: ast.AST, filename: str) -> None:
        """Check for functions that are too long."""
        rule_info = RULES.get("COMP002", {})
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                length = self._get_function_length(node)
                if length > MAX_FUNCTION_LINES:
                    self.issues.append(CodeIssue(
                        file_path=filename,
                        line=node.lineno,
                        col=node.col_offset,
                        severity=rule_info.get("severity", "warning"),
                        category="complexity",
                        rule_id="COMP002",
                        message=f"Function '{node.name}' is {length} lines long (max {MAX_FUNCTION_LINES})",
                        suggestion=rule_info.get("suggestion", "Break into smaller functions"),
                        code_snippet=f"def {node.name}()  # {length} lines",
                        fix_available=False
                    ))

    def _get_function_length(self, node: ast.FunctionDef) -> int:
        """Calculate function length in lines."""
        if not node.body:
            return 0
        first_line = node.lineno
        last_line = first_line
        for child in ast.walk(node):
            line = getattr(child, 'lineno', 0)
            end_line = getattr(child, 'end_lineno', line)
            if line > last_line:
                last_line = line
            if end_line > last_line:
                last_line = end_line
        return last_line - first_line + 1

    def _check_parameter_count(self, tree: ast.AST, filename: str) -> None:
        """Check for functions with too many parameters."""
        rule_info = RULES.get("COMP003", {})
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                param_count = len(node.args.args) + len(node.args.kwonlyargs)
                if node.args.vararg:
                    param_count += 1
                if node.args.kwarg:
                    param_count += 1
                if param_count > MAX_PARAMETERS:
                    self.issues.append(CodeIssue(
                        file_path=filename,
                        line=node.lineno,
                        col=node.col_offset,
                        severity=rule_info.get("severity", "warning"),
                        category="complexity",
                        rule_id="COMP003",
                        message=f"Function '{node.name}' has {param_count} parameters (max {MAX_PARAMETERS})",
                        suggestion=rule_info.get("suggestion", "Reduce parameter count"),
                        code_snippet=f"def {node.name}({param_count} params)",
                        fix_available=False
                    ))

    def _check_local_variable_count(self, tree: ast.AST, filename: str) -> None:
        """Check for functions with too many local variables."""
        rule_info = RULES.get("COMP006", {})
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                local_vars = self._count_local_variables(node)
                if local_vars > MAX_LOCAL_VARS:
                    self.issues.append(CodeIssue(
                        file_path=filename,
                        line=node.lineno,
                        col=node.col_offset,
                        severity=rule_info.get("severity", "warning"),
                        category="complexity",
                        rule_id="COMP006",
                        message=f"Function '{node.name}' has {local_vars} local variables (max {MAX_LOCAL_VARS})",
                        suggestion=rule_info.get("suggestion", "Reduce local variables"),
                        code_snippet=f"def {node.name}()  # {local_vars} locals",
                        fix_available=False
                    ))

    def _count_local_variables(self, node: ast.FunctionDef) -> int:
        """Count local variables in a function."""
        local_vars = set()
        for arg in node.args.args:
            local_vars.add(arg.arg)
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                local_vars.add(child.id)
        return len(local_vars)

    def _check_class_methods_count(self, tree: ast.AST, filename: str) -> None:
        """Check for classes with too many methods."""
        rule_info = RULES.get("COMP001", {})
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                if len(methods) > 15:
                    self.issues.append(CodeIssue(
                        file_path=filename,
                        line=node.lineno,
                        col=node.col_offset,
                        severity=rule_info.get("severity", "warning"),
                        category="complexity",
                        rule_id="COMP001",
                        message=f"Class '{node.name}' has {len(methods)} methods",
                        suggestion="Consider splitting class into smaller classes",
                        code_snippet=f"class {node.name}:  # {len(methods)} methods",
                        fix_available=False
                    ))

    def _check_nested_classes(self, tree: ast.AST, filename: str) -> None:
        """Check for deeply nested class definitions."""
        rule_info = RULES.get("COMP004", {})
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._find_nested_classes(node, filename, depth=0, rule_info=rule_info)

    def _find_nested_classes(self, node: ast.ClassDef, filename: str,
                              depth: int, rule_info: dict) -> None:
        """Find nested class definitions."""
        if depth > 0:
            self.issues.append(CodeIssue(
                file_path=filename,
                line=node.lineno,
                col=node.col_offset,
                severity=rule_info.get("severity", "warning"),
                category="complexity",
                rule_id="COMP004",
                message=f"Nested class '{node.name}' at depth {depth}",
                suggestion="Consider flattening class hierarchy",
                code_snippet=f"class {node.name}:  # depth {depth}",
                fix_available=False
            ))
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                self._find_nested_classes(child, filename, depth + 1, rule_info)

    def _check_function_count(self, tree: ast.AST, filename: str) -> None:
        """Check for modules with too many functions."""
        rule_info = RULES.get("COMP002", {})
        functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        if len(functions) > 30:
            self.issues.append(CodeIssue(
                file_path=filename,
                line=1,
                col=0,
                severity=rule_info.get("severity", "warning"),
                category="complexity",
                rule_id="COMP002",
                message=f"Module has {len(functions)} functions (consider splitting)",
                suggestion="Split module into smaller, focused modules",
                code_snippet=f"# {len(functions)} functions in module",
                fix_available=False
            ))

    def _check_module_length(self, tree: ast.AST, source: str,
                              filename: str) -> None:
        """Check if module is too long."""
        rule_info = RULES.get("COMP002", {})
        line_count = len(source.split('\n'))
        if line_count > 500:
            self.issues.append(CodeIssue(
                file_path=filename,
                line=1,
                col=0,
                severity="info",
                category="complexity",
                rule_id="COMP002",
                message=f"Module is {line_count} lines long (consider splitting at 500+)",
                suggestion="Break module into smaller files",
                code_snippet=f"# {line_count} lines",
                fix_available=False
            ))
class AutoFixer:
    """Automatically fixes certain categories of code issues."""

    def __init__(self):
        self.fixers = {
            "PERF006": self._fix_unused_import,
            "STYLE003": self._fix_missing_type_hints,
            "STYLE005": self._fix_bare_except,
            "STYLE006": self._fix_mutable_default,
            "BUG005": self._fix_comparison_operator,
            "BUG008": self._fix_bare_except_bug,
        }

    def fix_code(self, source: str, issues: List[CodeIssue]) -> Tuple[str, int]:
        """Apply automatic fixes to source code based on issues."""
        fixed_source = source
        fixes_applied = 0
        fixable_issues = [i for i in issues if i.fix_available and i.rule_id in self.fixers]
        fixable_issues.sort(key=lambda x: x.line, reverse=True)
        for issue in fixable_issues:
            fixer = self.fixers.get(issue.rule_id)
            if fixer:
                new_source = fixer(fixed_source, issue)
                if new_source != fixed_source:
                    fixed_source = new_source
                    fixes_applied += 1
        return fixed_source, fixes_applied

    def _fix_unused_import(self, source: str, issue: CodeIssue) -> str:
        """Remove unused import lines."""
        lines = source.split('\n')
        target_line = issue.line - 1
        if 0 <= target_line < len(lines):
            import_line = lines[target_line].strip()
            if import_line.startswith('import ') or import_line.startswith('from '):
                lines[target_line] = '# removed unused import'
                return '\n'.join(lines)
        return source

    def _fix_missing_docstring(self, source: str, issue: CodeIssue) -> str:
        """Add a docstring stub to functions."""
        lines = source.split('\n')
        target_line = issue.line - 1
        if 0 <= target_line < len(lines):
            func_line = lines[target_line]
            indent = len(func_line) - len(func_line.lstrip())
            body_indent = ' ' * (indent + 4)
            docstring_line = f'{body_indent}"""TODO: Add docstring."""'
            insert_line = target_line + 1
            if insert_line < len(lines):
                next_line = lines[insert_line].strip()
                if not next_line.startswith('"""') and not next_line.startswith("'''"):
                    lines.insert(insert_line, docstring_line)
                    return '\n'.join(lines)
        return source

    def _fix_missing_type_hints(self, source: str, issue: CodeIssue) -> str:
        """Add basic type hint stubs to functions."""
        lines = source.split('\n')
        target_line = issue.line - 1
        if 0 <= target_line < len(lines):
            func_line = lines[target_line]
            if '->' not in func_line and ':' in func_line:
                new_line = func_line.rstrip()
                if new_line.endswith(':'):
                    new_line = new_line[:-1] + ' -> Any:'
                else:
                    new_line = new_line + ' -> Any'
                lines[target_line] = new_line
                return '\n'.join(lines)
        return source

    def _fix_bare_except(self, source: str, issue: CodeIssue) -> str:
        """Replace bare except with except Exception."""
        lines = source.split('\n')
        target_line = issue.line - 1
        if 0 <= target_line < len(lines):
            line = lines[target_line]
            if 'except:' in line:
                lines[target_line] = line.replace('except:', 'except Exception:')
                return '\n'.join(lines)
        return source

    def _fix_mutable_default(self, source: str, issue: CodeIssue) -> str:
        """Replace mutable defaults with None."""
        lines = source.split('\n')
        target_line = issue.line - 1
        if 0 <= target_line < len(lines):
            line = lines[target_line]
            new_line = re.sub(r'=\s*\[\]', '= None', line)
            new_line = re.sub(r'=\s*\{\}', '= None', new_line)
            new_line = re.sub(r'=\s*set\(\)', '= None', new_line)
            if new_line != line:
                lines[target_line] = new_line
                return '\n'.join(lines)
        return source

    def _fix_missing_class_docstring(self, source: str, issue: CodeIssue) -> str:
        """Add a docstring stub to classes."""
        lines = source.split('\n')
        target_line = issue.line - 1
        if 0 <= target_line < len(lines):
            class_line = lines[target_line]
            indent = len(class_line) - len(class_line.lstrip())
            body_indent = ' ' * (indent + 4)
            docstring_line = f'{body_indent}"""TODO: Add class docstring."""'
            insert_line = target_line + 1
            if insert_line < len(lines):
                next_line = lines[insert_line].strip()
                if not next_line.startswith('"""') and not next_line.startswith("'''"):
                    lines.insert(insert_line, docstring_line)
                    return '\n'.join(lines)
        return source

    def _fix_comparison_operator(self, source: str, issue: CodeIssue) -> str:
        """Fix = to == in comparisons."""
        lines = source.split('\n')
        target_line = issue.line - 1
        if 0 <= target_line < len(lines):
            line = lines[target_line]
            new_line = re.sub(r'if\s+(\w+)\s*=\s*(\w+)', r'if \1 == \2', line)
            if new_line != line:
                lines[target_line] = new_line
                return '\n'.join(lines)
        return source

    def _fix_bare_except_bug(self, source: str, issue: CodeIssue) -> str:
        """Replace bare except with except Exception for bug category."""
        return self._fix_bare_except(source, issue)

    def get_fixable_rules(self) -> List[str]:
        """Return list of rule IDs that can be auto-fixed."""
        return list(self.fixers.keys())
class ReviewReport:
    """Aggregates code review issues and generates formatted reports."""

    def __init__(self, filename: str = "", source: str = ""):
        self.filename = filename
        self.source = source
        self.issues: List[CodeIssue] = []
        self.start_time = 0.0
        self.end_time = 0.0
        self._analyzers_run: List[str] = []

    def add_issues(self, issues: List[CodeIssue], analyzer_name: str = "") -> None:
        """Add issues from an analyzer to the report."""
        self.issues.extend(issues)
        if analyzer_name:
            self._analyzers_run.append(analyzer_name)

    def get_summary(self) -> Dict[str, Any]:
        """Generate a summary of all issues found."""
        severity_counts = {"error": 0, "warning": 0, "info": 0}
        category_counts = defaultdict(int)
        rules_triggered = defaultdict(int)
        fixable_count = 0
        for issue in self.issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
            category_counts[issue.category] += 1
            rules_triggered[issue.rule_id] += 1
            if issue.fix_available:
                fixable_count += 1
        return {
            "filename": self.filename,
            "total_issues": len(self.issues),
            "severity_counts": dict(severity_counts),
            "category_counts": dict(category_counts),
            "rules_triggered": dict(rules_triggered),
            "fixable_issues": fixable_count,
            "analyzers_run": self._analyzers_run,
        }

    def to_text(self) -> str:
        """Generate a formatted text report."""
        summary = self.get_summary()
        lines = []
        lines.append("=" * 70)
        lines.append("CODE REVIEW REPORT")
        lines.append("=" * 70)
        lines.append(f"File: {self.filename}")
        lines.append(f"Total Issues: {summary['total_issues']}")
        lines.append("-" * 70)
        lines.append("SEVERITY BREAKDOWN:")
        for sev, count in summary['severity_counts'].items():
            lines.append(f"  {sev.upper()}: {count}")
        lines.append("-" * 70)
        lines.append("CATEGORY BREAKDOWN:")
        for cat, count in summary['category_counts'].items():
            lines.append(f"  {cat.upper()}: {count}")
        lines.append("-" * 70)
        lines.append(f"Fixable Issues: {summary['fixable_issues']}")
        lines.append("-" * 70)
        lines.append("DETAILED ISSUES:")
        lines.append("-" * 70)
        sorted_issues = sorted(self.issues, key=lambda x: (x.severity != 'error', x.severity != 'warning', x.line))
        for i, issue in enumerate(sorted_issues, 1):
            lines.append(f"\n[{issue.severity.upper()}] {issue.rule_id} (line {issue.line})")
            lines.append(f"  Category: {issue.category}")
            lines.append(f"  Message: {issue.message}")
            lines.append(f"  Suggestion: {issue.suggestion}")
            if issue.code_snippet:
                lines.append(f"  Code: {issue.code_snippet[:60]}")
            if issue.fix_available:
                lines.append(f"  Fix Available: Yes")
        lines.append("\n" + "=" * 70)
        lines.append("END OF REPORT")
        lines.append("=" * 70)
        return '\n'.join(lines)

    def to_json(self) -> Dict[str, Any]:
        """Generate structured JSON report."""
        summary = self.get_summary()
        issues_data = []
        for issue in self.issues:
            issues_data.append({
                "file_path": issue.file_path,
                "line": issue.line,
                "col": issue.col,
                "severity": issue.severity,
                "category": issue.category,
                "rule_id": issue.rule_id,
                "message": issue.message,
                "suggestion": issue.suggestion,
                "code_snippet": issue.code_snippet,
                "fix_available": issue.fix_available,
                "fix_code": issue.fix_code,
            })
        return {
            "report": summary,
            "issues": issues_data,
            "rules_database": {
                rule_id: {
                    "description": info["description"],
                    "severity": info["severity"],
                    "category": info["category"],
                    "suggestion": info["suggestion"],
                }
                for rule_id, info in RULES.items()
                if rule_id in summary["rules_triggered"]
            },
        }

    def to_html(self) -> str:
        """Generate an HTML report."""
        summary = self.get_summary()
        html_parts = []
        html_parts.append('<!DOCTYPE html>')
        html_parts.append('<html lang="en">')
        html_parts.append('<head>')
        html_parts.append('<meta charset="UTF-8">')
        html_parts.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
        html_parts.append(f'<title>Code Review Report - {self.filename}</title>')
        html_parts.append('<style>')
        html_parts.append('body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 20px; background: #f5f5f5; }')
        html_parts.append('.container { max-width: 1000px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }')
        html_parts.append('h1 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }')
        html_parts.append('.summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }')
        html_parts.append('.summary-card { padding: 15px; border-radius: 6px; text-align: center; }')
        html_parts.append('.summary-card h3 { margin: 0 0 10px 0; font-size: 14px; text-transform: uppercase; }')
        html_parts.append('.summary-card .count { font-size: 28px; font-weight: bold; }')
        html_parts.append('.error { background: #fee; color: #c00; }')
        html_parts.append('.warning { background: #fff3cd; color: #856404; }')
        html_parts.append('.info { background: #d1ecf1; color: #0c5460; }')
        html_parts.append('.issues { margin-top: 20px; }')
        html_parts.append('.issue { padding: 15px; margin: 10px 0; border-left: 4px solid #ccc; background: #fafafa; border-radius: 4px; }')
        html_parts.append('.issue.error { border-left-color: #dc3545; }')
        html_parts.append('.issue.warning { border-left-color: #ffc107; }')
        html_parts.append('.issue.info { border-left-color: #17a2b8; }')
        html_parts.append('.issue-header { display: flex; justify-content: space-between; margin-bottom: 8px; }')
        html_parts.append('.issue-rule { font-weight: bold; color: #555; }')
        html_parts.append('.issue-line { color: #888; }')
        html_parts.append('.issue-message { margin: 5px 0; }')
        html_parts.append('.issue-suggestion { color: #28a745; font-style: italic; }')
        html_parts.append('.issue-code { background: #f0f0f0; padding: 8px; border-radius: 4px; font-family: monospace; margin-top: 8px; font-size: 13px; }')
        html_parts.append('.fix-badge { display: inline-block; background: #28a745; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px; }')
        html_parts.append('</style>')
        html_parts.append('</head>')
        html_parts.append('<body>')
        html_parts.append('<div class="container">')
        html_parts.append(f'<h1>Code Review Report</h1>')
        html_parts.append(f'<p><strong>File:</strong> {self.filename}</p>')
        html_parts.append(f'<p><strong>Total Issues:</strong> {summary["total_issues"]}</p>')
        html_parts.append('<div class="summary">')
        for sev, count in summary['severity_counts'].items():
            html_parts.append(f'<div class="summary-card {sev}"><h3>{sev}</h3><div class="count">{count}</div></div>')
        html_parts.append('</div>')
        html_parts.append('<div class="issues">')
        sorted_issues = sorted(self.issues, key=lambda x: (x.severity != 'error', x.severity != 'warning', x.line))
        for issue in sorted_issues:
            fix_badge = '<span class="fix-badge">Fix Available</span>' if issue.fix_available else ''
            html_parts.append(f'<div class="issue {issue.severity}">')
            html_parts.append(f'<div class="issue-header"><span class="issue-rule">{issue.rule_id}</span><span class="issue-line">Line {issue.line}</span></div>')
            html_parts.append(f'<div class="issue-message">{issue.message}</div>')
            html_parts.append(f'<div class="issue-suggestion">{issue.suggestion}</div>')
            if issue.code_snippet:
                html_parts.append(f'<div class="issue-code">{self._escape_html(issue.code_snippet[:80])}</div>')
            html_parts.append(f'{fix_badge}')
            html_parts.append('</div>')
        html_parts.append('</div>')
        html_parts.append('</div>')
        html_parts.append('</body>')
        html_parts.append('</html>')
        return '\n'.join(html_parts)

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

    def get_top_issues(self, count: int = 10) -> List[CodeIssue]:
        """Get the top N most severe issues."""
        severity_order = {"error": 0, "warning": 1, "info": 2}
        sorted_issues = sorted(
            self.issues,
            key=lambda x: (severity_order.get(x.severity, 3), x.line)
        )
        return sorted_issues[:count]

    def get_issues_by_category(self, category: str) -> List[CodeIssue]:
        """Get all issues in a specific category."""
        return [i for i in self.issues if i.category == category]

    def get_issues_by_severity(self, severity: str) -> List[CodeIssue]:
        """Get all issues with a specific severity."""
        return [i for i in self.issues if i.severity == severity]

    def get_fixable_issues(self) -> List[CodeIssue]:
        """Get all issues that have automatic fixes available."""
        return [i for i in self.issues if i.fix_available]

    def has_errors(self) -> bool:
        """Check if report contains any error-level issues."""
        return any(i.severity == 'error' for i in self.issues)

    def has_warnings(self) -> bool:
        """Check if report contains any warning-level issues."""
        return any(i.severity == 'warning' for i in self.issues)
def review_code(code: str, filename: str = "<string>",
                categories: Optional[List[str]] = None) -> ReviewReport:
    """Review source code and return a ReviewReport with all issues found.

    Args:
        code: Python source code to review.
        filename: Name of the file being reviewed.
        categories: List of categories to check. None means all categories.

    Returns:
        ReviewReport containing all issues found.
    """
    report = ReviewReport(filename=filename, source=code)
    all_categories = ["security", "performance", "style", "bug", "complexity"]
    if categories is None:
        categories = all_categories
    if "security" in categories:
        scanner = SecurityScanner()
        issues = scanner.scan_code(code, filename)
        report.add_issues(issues, "SecurityScanner")
    if "performance" in categories:
        analyzer = PerformanceAnalyzer()
        issues = analyzer.analyze(code, filename)
        report.add_issues(issues, "PerformanceAnalyzer")
    if "style" in categories:
        checker = StyleChecker()
        issues = checker.check(code, filename)
        report.add_issues(issues, "StyleChecker")
    if "bug" in categories:
        detector = BugDetector()
        issues = detector.detect(code, filename)
        report.add_issues(issues, "BugDetector")
    if "complexity" in categories:
        complexity = ComplexityAnalyzer()
        issues = complexity.analyze(code, filename)
        report.add_issues(issues, "ComplexityAnalyzer")
    return report


def review_file(file_path: str,
                categories: Optional[List[str]] = None) -> ReviewReport:
    """Review a Python file and return a ReviewReport.

    Args:
        file_path: Path to the Python file to review.
        categories: List of categories to check. None means all categories.

    Returns:
        ReviewReport containing all issues found.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not a Python file.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if not path.suffix == '.py':
        raise ValueError(f"Not a Python file: {file_path}")
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        source = f.read()
    return review_code(source, str(path), categories)


def review_directory(dir_path: str, pattern: str = "*.py",
                     categories: Optional[List[str]] = None) -> Dict[str, Any]:
    """Review all matching Python files in a directory.

    Args:
        dir_path: Path to the directory to review.
        pattern: Glob pattern for files to review.
        categories: List of categories to check. None means all categories.

    Returns:
        Dictionary with aggregated results from all files reviewed.
    """
    path = Path(dir_path)
    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {dir_path}")
    if not path.is_dir():
        raise ValueError(f"Not a directory: {dir_path}")
    results = {
        "directory": str(path),
        "pattern": pattern,
        "files": {},
        "files_reviewed": [],
        "total_issues": 0,
        "total_files": 0,
        "severity_counts": {"error": 0, "warning": 0, "info": 0},
        "category_counts": defaultdict(int),
        "reports": {},
    }
    files = list(path.glob(pattern))
    for file_path in sorted(files):
        try:
            report = review_file(str(file_path), categories)
            results["files_reviewed"].append(str(file_path))
            results["total_issues"] += len(report.issues)
            results["total_files"] += 1
            summary = report.get_summary()
            for sev, count in summary["severity_counts"].items():
                results["severity_counts"][sev] += count
            for cat, count in summary["category_counts"].items():
                results["category_counts"][cat] += count
            results["reports"][str(file_path)] = {
                "issues": len(report.issues),
                "errors": summary["severity_counts"].get("error", 0),
                "warnings": summary["severity_counts"].get("warning", 0),
                "info": summary["severity_counts"].get("info", 0),
            }
            results["files"][str(file_path)] = {
                "issues": len(report.issues),
                "errors": summary["severity_counts"].get("error", 0),
                "warnings": summary["severity_counts"].get("warning", 0),
                "info": summary["severity_counts"].get("info", 0),
            }
        except Exception as e:
            results["reports"][str(file_path)] = {"error": str(e)}
    results["category_counts"] = dict(results["category_counts"])
    return results


_last_review_report: Optional[ReviewReport] = None


def code_review_tool(action: str = "review", **kwargs) -> str:
    """Dispatcher for FRIDAY tool system.

    Actions:
        review: Review code snippet (requires 'code' and 'filename')
        review_file: Review a file (requires 'path')
        review_dir: Review a directory (requires 'path', optional 'pattern')
        stats: Get stats from last review
        fix: Auto-fix code (requires 'code' and 'filename')
        security_scan: Quick security scan (requires 'code')
        analyze_complexity: Analyze code complexity (requires 'code')

    Returns:
        JSON string with results.
    """
    global _last_review_report
    try:
        if action == "review":
            code = kwargs.get("code", "")
            filename = kwargs.get("filename", "<string>")
            categories = kwargs.get("categories", None)
            if not code:
                return json.dumps({"error": "No code provided"})
            report = review_code(code, filename, categories)
            _last_review_report = report
            return json.dumps(report.to_json(), indent=2)

        elif action == "review_file":
            path = kwargs.get("path", "")
            categories = kwargs.get("categories", None)
            if not path:
                return json.dumps({"error": "No file path provided"})
            report = review_file(path, categories)
            _last_review_report = report
            return json.dumps(report.to_json(), indent=2)

        elif action == "review_dir":
            path = kwargs.get("path", "")
            pattern = kwargs.get("pattern", "*.py")
            categories = kwargs.get("categories", None)
            if not path:
                return json.dumps({"error": "No directory path provided"})
            results = review_directory(path, pattern, categories)
            return json.dumps(results, indent=2)

        elif action == "stats":
            if _last_review_report is None:
                return json.dumps({"error": "No review has been performed yet"})
            return json.dumps(_last_review_report.get_summary(), indent=2)

        elif action == "fix":
            code = kwargs.get("code", "")
            filename = kwargs.get("filename", "<string>")
            if not code:
                return json.dumps({"error": "No code provided"})
            report = review_code(code, filename)
            fixer = AutoFixer()
            fixed_code, fixes_applied = fixer.fix_code(code, report.issues)
            return json.dumps({
                "original_code": code,
                "fixed_code": fixed_code,
                "fixes_applied": fixes_applied,
                "total_issues": len(report.issues),
                "fixable_issues": len(report.get_fixable_issues()),
            }, indent=2)

        elif action == "security_scan":
            code = kwargs.get("code", "")
            filename = kwargs.get("filename", "<string>")
            if not code:
                return json.dumps({"error": "No code provided"})
            scanner = SecurityScanner()
            issues = scanner.scan_code(code, filename)
            report = ReviewReport(filename=filename, source=code)
            report.add_issues(issues, "SecurityScanner")
            _last_review_report = report
            return json.dumps(report.to_json(), indent=2)

        elif action == "analyze_complexity":
            code = kwargs.get("code", "")
            filename = kwargs.get("filename", "<string>")
            if not code:
                return json.dumps({"error": "No code provided"})
            analyzer = ComplexityAnalyzer()
            issues = analyzer.analyze(code, filename)
            report = ReviewReport(filename=filename, source=code)
            report.add_issues(issues, "ComplexityAnalyzer")
            _last_review_report = report
            return json.dumps(report.to_json(), indent=2)

        else:
            return json.dumps({
                "error": f"Unknown action: {action}",
                "valid_actions": [
                    "review", "review_file", "review_dir",
                    "stats", "fix", "security_scan", "analyze_complexity"
                ]
            })

    except Exception as e:
        return json.dumps({"error": str(e), "type": type(e).__name__})
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        target = sys.argv[1]
        if os.path.isfile(target):
            report = review_file(target)
            print(report.to_text())
        elif os.path.isdir(target):
            results = review_directory(target)
            print(f"Reviewed {results['total_files']} files, found {results['total_issues']} issues")
            for f, r in results["reports"].items():
                if "error" not in r:
                    print(f"  {f}: {r['issues']} issues ({r['errors']} errors, {r['warnings']} warnings)")
        else:
            print(f"Error: {target} is not a valid file or directory")
            sys.exit(1)
    else:
        print("FRIDAY Code Review Agent")
        print("Usage: python code_review.py <file_or_directory>")
        print()
        print("Running demo scan on example bad code...")
        report = review_code(SECURITY_BAD, "security_example.py", ["security"])
        print(report.to_text())