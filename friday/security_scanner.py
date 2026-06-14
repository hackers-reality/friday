"""FRIDAY Security Scanner — comprehensive vulnerability detection and analysis."""
import os
import re
import ast
import json
import time
import hashlib
import secrets
import fnmatch
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from collections import defaultdict


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Vulnerability:
    id: str
    title: str
    severity: str
    category: str
    file_path: str
    line_number: int
    description: str
    recommendation: str
    cwe_id: str = ""
    codeSnippet: str = ""
    confidence: float = 0.9

    def to_dict(self):
        return asdict(self)


@dataclass
class ScanResult:
    scan_id: str
    timestamp: float
    target: str
    scan_type: str
    vulnerabilities: List[Dict] = field(default_factory=list)
    summary: Dict = field(default_factory=dict)
    duration: float = 0.0
    files_scanned: int = 0
    lines_scanned: int = 0

    def to_dict(self):
        return asdict(self)


SECRET_PATTERNS = [
    (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\'][^"\']{8,}["\']', "API Key", "CWE-798"),
    (r'(?i)(secret[_-]?key|secretkey)\s*[=:]\s*["\'][^"\']{8,}["\']', "Secret Key", "CWE-798"),
    (r'(?i)(password|passwd|pwd)\s*[=:]\s*["\'][^"\']{4,}["\']', "Hardcoded Password", "CWE-798"),
    (r'(?i)(access[_-]?token|accesstoken)\s*[=:]\s*["\'][^"\']{8,}["\']', "Access Token", "CWE-798"),
    (r'(?i)(private[_-]?key|privatekey)\s*[=:]\s*["\'][^"\']{8,}["\']', "Private Key", "CWE-798"),
    (r'sk-[a-zA-Z0-9]{20,}', "OpenAI API Key", "CWE-798"),
    (r'ghp_[a-zA-Z0-9]{36}', "GitHub Personal Access Token", "CWE-798"),
    (r'gho_[a-zA-Z0-9]{36}', "GitHub OAuth Token", "CWE-798"),
    (r'ghs_[a-zA-Z0-9]{36}', "GitHub Server-to-Server Token", "CWE-798"),
    (r'glpat-[a-zA-Z0-9\-]{20,}', "GitLab PAT", "CWE-798"),
    (r'xox[bpsa]-[a-zA-Z0-9\-]+', "Slack Token", "CWE-798"),
    (r'AKIA[0-9A-Z]{16}', "AWS Access Key", "CWE-798"),
    (r'(?i)BEGIN\s+(RSA|DSA|EC|OPENSSH)\s+PRIVATE\s+KEY', "Private Key Block", "CWE-321"),
    (r'(?i)(mysql|postgres|mongodb|redis)://[^\s]+:[^\s]+@[^\s]+', "Database Connection String", "CWE-798"),
]

INJECTION_PATTERNS = [
    (r'eval\s*\([^)]*\)', "eval() Usage", Severity.CRITICAL, "CWE-95", "Use ast.literal_eval() or safe parsing"),
    (r'exec\s*\([^)]*\)', "exec() Usage", Severity.CRITICAL, "CWE-95", "Avoid dynamic code execution"),
    (r'__import__\s*\([^)]*\)', "Dynamic Import", Severity.HIGH, "CWE-95", "Use static imports"),
    (r'compile\s*\([^)]*\)', "Dynamic Compilation", Severity.HIGH, "CWE-95", "Avoid dynamic compilation"),
    (r'os\.system\s*\([^)]*\)', "os.system() Usage", Severity.HIGH, "CWE-78", "Use subprocess with shell=False"),
    (r'subprocess\.call\s*\([^)]*shell\s*=\s*True', "Shell Injection", Severity.CRITICAL, "CWE-78", "Use shell=False"),
    (r'subprocess\.Popen\s*\([^)]*shell\s*=\s*True', "Shell Injection", Severity.CRITICAL, "CWE-78", "Use shell=False"),
    (r'os\.popen\s*\([^)]*\)', "os.popen() Usage", Severity.HIGH, "CWE-78", "Use subprocess"),
    (r'tempfile\.mktemp\s*\(', "Insecure Temp File", Severity.MEDIUM, "CWE-377", "Use tempfile.mkstemp()"),
    (r'pickle\.loads?\s*\([^)]*\)', "Pickle Deserialization", Severity.HIGH, "CWE-502", "Use JSON instead"),
    (r'marshal\.loads?\s*\([^)]*\)', "Marshal Deserialization", Severity.HIGH, "CWE-502", "Use JSON instead"),
    (r'yaml\.load\s*\([^)]*\)', "Unsafe YAML Load", Severity.HIGH, "CWE-502", "Use yaml.safe_load()"),
    (r'shelve\.open\s*\([^)]*\)', "Shelve Usage", Severity.MEDIUM, "CWE-502", "Use JSON for serialization"),
]

CRYPTO_ISSUES = [
    (r'hashlib\.md5\s*\(', "MD5 Usage", Severity.MEDIUM, "CWE-328", "Use SHA-256 or stronger"),
    (r'hashlib\.sha1\s*\(', "SHA-1 Usage", Severity.MEDIUM, "CWE-328", "Use SHA-256 or stronger"),
    (r'(?i)random\.(random|randint|choice|randrange)\s*\(', "Weak PRNG", Severity.MEDIUM, "CWE-330", "Use secrets module for cryptographic randomness"),
    (r'DES\.new\s*\(', "DES Encryption", Severity.HIGH, "CWE-327", "Use AES-256"),
    (r'RC4\s*\(', "RC4 Cipher", Severity.HIGH, "CWE-327", "Use AES-256"),
]

NETWORK_ISSUES = [
    (r'verify\s*=\s*False', "SSL Verification Disabled", Severity.HIGH, "CWE-295", "Enable SSL verification"),
    (r'(?i)http://', "HTTP (not HTTPS)", Severity.LOW, "CWE-319", "Use HTTPS"),
    (r'0\.0\.0\.0', "Binding to All Interfaces", Severity.MEDIUM, "CWE-668", "Bind to specific interface"),
]

PERFORMANCE_ISSUES = [
    (r'for\s+\w+\s+in\s+range\s*\(\s*len\s*\([^)]+\)\s*\)', "Index Iteration", Severity.LOW, "CWE-1176", "Use enumerate() or direct iteration"),
    (r'\.append\s*\(\s*[^)]+\)\s*\n\s*return\s+result', "Loop Append Return", Severity.INFO, "", "Consider list comprehension"),
]

ERROR_PATTERNS = [
    (r'except\s*:', "Bare Except", Severity.MEDIUM, "CWE-396", "Catch specific exceptions"),
    (r'except\s+Exception\s*:', "Broad Exception", Severity.LOW, "CWE-396", "Catch more specific exceptions"),
    (r'pass\s*$', "Silent Pass", Severity.LOW, "CWE-754", "Log or handle the exception"),
    (r'print\s*\(\s*["\'].*password.*["\']', "Password in Logs", Severity.HIGH, "CWE-532", "Never log passwords"),
    (r'logging\.\w+\(.*password', "Password in Logging", Severity.HIGH, "CWE-532", "Never log passwords"),
]

CONFIG_PATTERNS = [
    (r'DEBUG\s*=\s*True', "Debug Mode Enabled", Severity.MEDIUM, "CWE-489", "Disable in production"),
    (r'(?i)DEBUG\s*:\s*true', "Debug Mode Enabled", Severity.MEDIUM, "CWE-489", "Disable in production"),
    (r'(?i)allow[_-]?origin\s*[=:]\s*["\']\*["\']', "CORS Wildcard", Severity.MEDIUM, "CWE-942", "Restrict CORS origins"),
    (r'(?i)allow[_-]?credentials\s*[=:]\s*True', "CORS Credentials", Severity.LOW, "CWE-942", "Review CORS credentials policy"),
]


class SecurityScanner:
    def __init__(self, project_root: str = "."):
        self.project_root = os.path.abspath(project_root)
        self.scan_history: List[ScanResult] = []
        self.vuln_counter = 0
        self._ignored_paths = {
            "node_modules", ".git", "__pycache__", ".venv", "venv",
            "dist", "build", ".next", ".nuxt", "vendor",
        }
        self._ignored_files = {
            "*.pyc", "*.pyo", "*.class", "*.o", "*.so", "*.dll",
            "*.exe", "*.jar", "*.war", "*.ear",
        }

    def _generate_vuln_id(self) -> str:
        self.vuln_counter += 1
        return f"FRIDAY-{self.vuln_counter:04d}"

    def _should_skip_path(self, path: str) -> bool:
        parts = Path(path).parts
        for ignored in self._ignored_paths:
            if ignored in parts:
                return True
        for pattern in self._ignored_files:
            if fnmatch.fnmatch(os.path.basename(path), pattern):
                return True
        return False

    def _read_file(self, file_path: str) -> Optional[str]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return None

    def _check_secrets(self, content: str, file_path: str) -> List[Vulnerability]:
        vulns = []
        for line_num, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//"):
                continue
            for pattern, title, cwe in SECRET_PATTERNS:
                if re.search(pattern, line):
                    vulns.append(Vulnerability(
                        id=self._generate_vuln_id(),
                        title=title,
                        severity=Severity.CRITICAL.value,
                        category="secrets",
                        file_path=file_path,
                        line_number=line_num,
                        description=f"Hardcoded secret found: {title}",
                        recommendation="Move to environment variables or secrets manager",
                        cwe_id=cwe,
                        codeSnippet=stripped[:100],
                    ))
                    break
        return vulns

    def _check_injections(self, content: str, file_path: str) -> List[Vulnerability]:
        vulns = []
        for line_num, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pattern, title, severity, cwe, rec in INJECTION_PATTERNS:
                if re.search(pattern, line):
                    vulns.append(Vulnerability(
                        id=self._generate_vuln_id(),
                        title=title,
                        severity=severity.value,
                        category="injection",
                        file_path=file_path,
                        line_number=line_num,
                        description=f"Potential injection vulnerability: {title}",
                        recommendation=rec,
                        cwe_id=cwe,
                        codeSnippet=stripped[:100],
                    ))
        return vulns

    def _check_crypto(self, content: str, file_path: str) -> List[Vulnerability]:
        vulns = []
        for line_num, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pattern, title, severity, cwe, rec in CRYPTO_ISSUES:
                if re.search(pattern, line):
                    vulns.append(Vulnerability(
                        id=self._generate_vuln_id(),
                        title=title,
                        severity=severity.value,
                        category="cryptography",
                        file_path=file_path,
                        line_number=line_num,
                        description=f"Cryptographic issue: {title}",
                        recommendation=rec,
                        cwe_id=cwe,
                        codeSnippet=stripped[:100],
                    ))
        return vulns

    def _check_network(self, content: str, file_path: str) -> List[Vulnerability]:
        vulns = []
        for line_num, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pattern, title, severity, cwe, rec in NETWORK_ISSUES:
                if re.search(pattern, line):
                    vulns.append(Vulnerability(
                        id=self._generate_vuln_id(),
                        title=title,
                        severity=severity.value,
                        category="network",
                        file_path=file_path,
                        line_number=line_num,
                        description=f"Network security issue: {title}",
                        recommendation=rec,
                        cwe_id=cwe,
                        codeSnippet=stripped[:100],
                    ))
        return vulns

    def _check_errors(self, content: str, file_path: str) -> List[Vulnerability]:
        vulns = []
        for line_num, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            for pattern, title, severity, cwe, rec in ERROR_PATTERNS:
                if re.search(pattern, line):
                    vulns.append(Vulnerability(
                        id=self._generate_vuln_id(),
                        title=title,
                        severity=severity.value,
                        category="error_handling",
                        file_path=file_path,
                        line_number=line_num,
                        description=f"Error handling issue: {title}",
                        recommendation=rec,
                        cwe_id=cwe,
                        codeSnippet=stripped[:100],
                    ))
        return vulns

    def _check_config(self, content: str, file_path: str) -> List[Vulnerability]:
        vulns = []
        for line_num, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            for pattern, title, severity, cwe, rec in CONFIG_PATTERNS:
                if re.search(pattern, line):
                    vulns.append(Vulnerability(
                        id=self._generate_vuln_id(),
                        title=title,
                        severity=severity.value,
                        category="configuration",
                        file_path=file_path,
                        line_number=line_num,
                        description=f"Configuration issue: {title}",
                        recommendation=rec,
                        cwe_id=cwe,
                        codeSnippet=stripped[:100],
                    ))
        return vulns

    def _check_ast_security(self, content: str, file_path: str) -> List[Vulnerability]:
        vulns = []
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return vulns

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                args_with_defaults = [a.arg for a in node.args.args]
                for default in node.args.defaults:
                    if isinstance(default, (ast.Constant, ast.Str)):
                        val = default.s if isinstance(default, ast.Str) else str(default.value)
                        if any(kw in val.lower() for kw in ["password", "secret", "key", "token"]):
                            vulns.append(Vulnerability(
                                id=self._generate_vuln_id(),
                                title="Sensitive Default Parameter",
                                severity=Severity.HIGH.value,
                                category="secrets",
                                file_path=file_path,
                                line_number=node.lineno,
                                description=f"Function '{node.name}' has a sensitive default parameter",
                                recommendation="Remove sensitive defaults, use None and validate at runtime",
                                cwe_id="CWE-798",
                            ))

            if isinstance(node, ast.ExceptHandler) and node.type is None:
                vulns.append(Vulnerability(
                    id=self._generate_vuln_id(),
                    title="Bare Except Clause",
                    severity=Severity.MEDIUM.value,
                    category="error_handling",
                    file_path=file_path,
                    line_number=node.lineno,
                    description="Bare except clause catches all exceptions including SystemExit and KeyboardInterrupt",
                    recommendation="Catch specific exceptions",
                    cwe_id="CWE-396",
                ))

        return vulns

    def scan_file(self, file_path: str) -> List[Vulnerability]:
        if self._should_skip_path(file_path):
            return []

        content = self._read_file(file_path)
        if content is None:
            return []

        vulns = []
        vulns.extend(self._check_secrets(content, file_path))
        vulns.extend(self._check_injections(content, file_path))
        vulns.extend(self._check_crypto(content, file_path))
        vulns.extend(self._check_network(content, file_path))
        vulns.extend(self._check_errors(content, file_path))
        vulns.extend(self._check_config(content, file_path))
        vulns.extend(self._check_ast_security(content, file_path))
        return vulns

    def scan_directory(self, path: str = None, extensions: List[str] = None) -> ScanResult:
        if path is None:
            path = self.project_root
        if extensions is None:
            extensions = [".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css",
                          ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
                          ".env", ".sh", ".bash", ".ps1", ".cmd", ".bat"]

        start_time = time.time()
        scan_id = f"SCAN-{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
        all_vulns = []
        files_scanned = 0
        lines_scanned = 0

        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in self._ignored_paths]
            for fname in files:
                if any(fname.endswith(ext) for ext in extensions):
                    fpath = os.path.join(root, fname)
                    vulns = self.scan_file(fpath)
                    all_vulns.extend(vulns)
                    files_scanned += 1
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            lines_scanned += sum(1 for _ in f)
                    except Exception:
                        pass

        duration = time.time() - start_time

        severity_counts = defaultdict(int)
        category_counts = defaultdict(int)
        for v in all_vulns:
            severity_counts[v.severity] += 1
            category_counts[v.category] += 1

        result = ScanResult(
            scan_id=scan_id,
            timestamp=start_time,
            target=path,
            scan_type="full",
            vulnerabilities=[v.to_dict() for v in all_vulns],
            summary={
                "total": len(all_vulns),
                "by_severity": dict(severity_counts),
                "by_category": dict(category_counts),
                "files_scanned": files_scanned,
                "lines_scanned": lines_scanned,
            },
            duration=round(duration, 3),
            files_scanned=files_scanned,
            lines_scanned=lines_scanned,
        )
        self.scan_history.append(result)
        return result

    def scan_code(self, code: str, language: str = "python") -> List[Vulnerability]:
        vulns = []
        vulns.extend(self._check_secrets(code, "<inline>"))
        vulns.extend(self._check_injections(code, "<inline>"))
        vulns.extend(self._check_crypto(code, "<inline>"))
        vulns.extend(self._check_network(code, "<inline>"))
        vulns.extend(self._check_errors(code, "<inline>"))
        vulns.extend(self._check_config(code, "<inline>"))
        if language == "python":
            vulns.extend(self._check_ast_security(code, "<inline>"))
        return vulns

    def get_history(self) -> List[Dict]:
        return [r.to_dict() for r in self.scan_history]

    def get_stats(self) -> Dict:
        total_vulns = sum(len(r.vulnerabilities) for r in self.scan_history)
        total_scans = len(self.scan_history)
        return {
            "total_scans": total_scans,
            "total_vulnerabilities": total_vulns,
            "history": self.get_history()[-10:],
        }


_scanner = SecurityScanner()


def security_scanner_tool(action: str = "scan_code", **kwargs) -> Any:
    """Security scanner tool dispatcher."""
    try:
        if action == "scan_code":
            code = kwargs.get("code", "")
            language = kwargs.get("language", "python")
            vulns = _scanner.scan_code(code, language)
            return {"vulnerabilities": [v.to_dict() for v in vulns], "count": len(vulns)}

        elif action == "scan_file":
            file_path = kwargs.get("path", "")
            if not file_path:
                return {"error": "No path provided"}
            vulns = _scanner.scan_file(file_path)
            return {"vulnerabilities": [v.to_dict() for v in vulns], "count": len(vulns)}

        elif action == "scan_directory":
            path = kwargs.get("path", _scanner.project_root)
            extensions = kwargs.get("extensions")
            result = _scanner.scan_directory(path, extensions)
            return result.to_dict()

        elif action == "stats":
            return _scanner.get_stats()

        elif action == "history":
            return {"history": _scanner.get_history()}

        elif action == "severity_report":
            if not _scanner.scan_history:
                return {"message": "No scans performed yet"}
            latest = _scanner.scan_history[-1]
            return {
                "scan_id": latest.scan_id,
                "summary": latest.summary,
                "vulnerabilities": latest.vulnerabilities[:50],
            }

        elif action == "fix_suggestions":
            code = kwargs.get("code", "")
            vulns = _scanner.scan_code(code)
            suggestions = []
            for v in vulns:
                suggestions.append({
                    "id": v.id,
                    "title": v.title,
                    "severity": v.severity,
                    "line": v.line_number,
                    "fix": v.recommendation,
                    "cwe": v.cwe_id,
                })
            return {"suggestions": suggestions, "count": len(suggestions)}

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        return {"error": str(e)}
