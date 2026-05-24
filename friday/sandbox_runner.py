"""
FRIDAY Autonomous Sandbox Runner & Self-Healing Debugger.

This module provides the `AutonomousSandboxRunner` class, which manages isolated
runtime environments (Python virtual environments) to execute user scripts safely,
captures stdout/stderr, handles execution timeouts, resolves missing imports automatically,
and runs a recursive self-healing debugging loop using NVIDIA NIM (or fallback models) via
FRIDAY's `InferenceClient`.

Events emitted on ContextBus:
  - sandbox.started:   Published when process execution begins.
  - sandbox.progress:  Published for step status updates (e.g. installing dependencies, model repair attempts).
  - sandbox.repaired:  Published when a script has been modified with LLM repair details (explanation and diff).
  - sandbox.completed: Published when execution finishes successfully (exit code 0).
  - sandbox.failed:    Published when execution fails and cannot be repaired.
"""

from __future__ import annotations

import ast
import asyncio
import difflib
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import venv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Friday System Imports
from friday.context_bus import get_bus
from friday.nim_client import InferenceClient
from friday.nim_router import resolve_model

# Logger Configuration
logger = logging.getLogger(__name__)

# Comprehensive mapping from Python import names to pip-installable package names
IMPORT_TO_PIP: dict[str, str] = {
    "yaml": "pyyaml",
    "bs4": "beautifulsoup4",
    "dotenv": "python-dotenv",
    "PIL": "Pillow",
    "fitz": "PyMuPDF",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "skimage": "scikit-image",
    "google.genai": "google-genai",
    "googleapiclient": "google-api-python-client",
    "github": "PyGithub",
    "jose": "python-jose",
    "jwt": "PyJWT",
    "mysql": "mysql-connector-python",
    "psycopg2": "psycopg2-binary",
    "sqlalchemy": "SQLAlchemy",
    "dateutil": "python-dateutil",
    "win32api": "pywin32",
    "win32con": "pywin32",
    "win32gui": "pywin32",
    "docx": "python-docx",
    "pptx": "python-pptx",
    "openpyxl": "openpyxl",
    "pdfplumber": "pdfplumber",
    "pypdf": "pypdf",
    "numpy": "numpy",
    "pandas": "pandas",
    "matplotlib": "matplotlib",
    "requests": "requests",
    "httpx": "httpx",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "jinja2": "Jinja2",
    "lxml": "lxml",
    "aiohttp": "aiohttp",
    "pytest": "pytest",
    "redis": "redis",
    "pydantic": "pydantic",
    "toml": "toml",
    "cryptography": "cryptography",
    "bcrypt": "bcrypt",
    "scipy": "scipy",
    "sympy": "sympy",
    "flask": "Flask",
    "django": "Django",
    "gunicorn": "gunicorn",
    "click": "click",
    "rich": "rich",
    "tqdm": "tqdm",
    "colorama": "colorama",
    "dns": "dnspython",
    "docker": "docker",
    "elasticsearch": "elasticsearch",
    "grpc": "grpcio",
    "kafka": "kafka-python",
    "openopt": "openopt",
    "paramiko": "paramiko",
    "peewee": "peewee",
    "pika": "pika",
    "pymongo": "pymongo",
    "pytest_mock": "pytest-mock",
    "simplejson": "simplejson",
    "tornado": "tornado",
    "websocket": "websocket-client",
    "werkzeug": "Werkzeug",
}


def is_standard_library(module_name: str) -> bool:
    """
    Check if the module is part of the Python standard library.
    Checks sys.stdlib_module_names (Python 3.10+) with a hardcoded fallback.
    """
    top_level = module_name.split(".")[0]
    
    # 1. Use sys.stdlib_module_names if available
    if hasattr(sys, "stdlib_module_names"):
        if top_level in sys.stdlib_module_names:
            return True

    # 2. Hardcoded fallback list of standard library modules
    stdlib_fallback = {
        "abc", "argparse", "array", "ast", "asynchat", "asyncore", "asyncio",
        "base64", "bdb", "binascii", "bisect", "builtins", "bz2",
        "calendar", "cgi", "cgitb", "chunk", "cmath", "cmd", "code", "codecs",
        "collections", "colorsys", "compileall", "concurrent", "configparser",
        "contextlib", "contextvars", "copy", "copyreg", "crypt", "csv", "ctypes",
        "curses", "dataclasses", "datetime", "dbm", "decimal", "difflib",
        "dis", "distutils", "doctest", "email", "encodings", "ensurepip",
        "enum", "errno", "faulthandler", "filecmp", "fileinput", "fnmatch",
        "formatter", "fractions", "ftplib", "functools", "gc", "getopt",
        "getpass", "gettext", "glob", "graphlib", "grp", "gzip", "hashlib",
        "heapq", "hmac", "html", "http", "imaplib", "imghdr", "imp", "importlib",
        "inspect", "io", "ipaddress", "itertools", "json", "keyword", "lib2to3",
        "linecache", "locale", "logging", "lzma", "mailbox", "mailcap", "marshal",
        "math", "mimetypes", "mmap", "modulefinder", "msilib", "msvcrt",
        "multiprocessing", "netrc", "nis", "nntplib", "nt", "ntpath", "numbers",
        "operator", "optparse", "os", "ossaudiodev", "pathlib", "pdb", "pickle",
        "pickletools", "pipes", "pkgutil", "platform", "plistlib", "poplib",
        "posix", "posixpath", "pprint", "profile", "pstats", "pty", "pwd",
        "py_compile", "pyclbr", "pydoc", "queue", "quopri", "random", "re",
        "readline", "reprlib", "resource", "rlcompleter", "runpy", "sched",
        "secrets", "select", "selectors", "shelve", "shutil", "signal",
        "site", "smtpd", "smtplib", "sndhdr", "socket", "socketserver", "spwd",
        "sqlite3", "ssl", "stat", "statistics", "string", "stringprep",
        "struct", "subprocess", "sunau", "symtable", "sys", "sysconfig",
        "syslog", "tabnanny", "tarfile", "telnetlib", "tempfile", "termios",
        "test", "textwrap", "threading", "time", "timeit", "tkinter", "token",
        "tokenize", "tomllib", "trace", "traceback", "tracemalloc", "tty", "types",
        "typing", "unicodedata", "unittest", "urllib", "uu", "uuid", "venv",
        "warnings", "wave", "weakref", "webbrowser", "winreg", "winsound",
        "wsgiref", "xdg", "xml", "xmlrpc", "zipapp", "zipfile", "zipimport",
        "zlib"
    }
    if top_level in stdlib_fallback:
        return True

    # 3. Check builtin names
    if top_level in sys.builtin_module_names:
        return True

    return False


def resolve_pip_package(module_name: str) -> str:
    """Resolve Python module import name to pip installable package name."""
    top_level = module_name.strip().split(".")[0]
    
    # Check manual overrides
    pip_name = IMPORT_TO_PIP.get(top_level)
    if pip_name:
        return pip_name

    # Check case-insensitive override mapping
    for import_name, pkg in IMPORT_TO_PIP.items():
        if import_name.lower() == top_level.lower():
            return pkg

    # Fallback heuristics (lowercase and snake to kebab)
    return top_level.lower().replace("_", "-")


def extract_imports(script_path: str) -> set[str]:
    """Parse python file with AST and extract all top-level and nested imported module names."""
    imports: set[str] = set()
    if not os.path.exists(script_path):
        return imports
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, filename=script_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.add(name.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
    except Exception as e:
        logger.warning(f"AST parsing failed for {script_path}: {e}. Proactive dependency scan may be partial.")
    return imports


def calculate_unified_diff(original_code: str, corrected_code: str, filename: str) -> str:
    """Calculate and return unified diff string between original and corrected code."""
    original_lines = original_code.splitlines(keepends=True)
    corrected_lines = corrected_code.splitlines(keepends=True)
    diff = difflib.unified_diff(
        original_lines,
        corrected_lines,
        fromfile=f"original/{filename}",
        tofile=f"repaired/{filename}"
    )
    return "".join(diff)


def _execute_subprocess_sync(
    cmd: list[str],
    cwd: str,
    env: dict[str, str],
    timeout: float
) -> tuple[int, str, str, bool]:
    """
    Synchronously execute a process using subprocess.Popen.
    Captures stdout/stderr, manages timeouts, handles process tree termination, and returns outcomes.
    """
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        exit_code = proc.returncode if proc.returncode is not None else 0
        return exit_code, stdout, stderr, False
    except subprocess.TimeoutExpired:
        # Gracefully terminate then force-kill process tree
        logger.warning(f"Process exceeded timeout of {timeout}s. Terminating pid={proc.pid}...")
        if sys.platform == "win32":
            try:
                # Force kill target and all child processes
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5.0
                )
            except Exception as e:
                logger.error(f"Failed taskkill for pid={proc.pid}: {e}. Falling back to Popen.kill()")
                proc.kill()
        else:
            try:
                import signal
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                proc.kill()

        stdout, stderr = proc.communicate()
        exit_code = proc.returncode if proc.returncode is not None else -1
        return exit_code, stdout, stderr, True
    except Exception as e:
        logger.error(f"Subprocess communication exception: {e}")
        proc.kill()
        stdout, stderr = proc.communicate()
        return -1, stdout, stderr + f"\n[Runner Exception: {e}]", False


async def _run_command_async(
    cmd: list[str],
    cwd: Optional[str] = None,
    timeout: Optional[float] = None
) -> tuple[int, str, str]:
    """
    Run command asynchronously using asyncio subprocess, with timeout support.
    Returns (exit_code, stdout, stderr).
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
    except FileNotFoundError:
        return -1, "", f"Executable not found: {cmd[0]}"
    except Exception as e:
        return -1, "", f"Failed to start command: {e}"

    try:
        if timeout:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout
            )
        else:
            stdout_bytes, stderr_bytes = await proc.communicate()

        exit_code = proc.returncode if proc.returncode is not None else 0
        return (
            exit_code,
            stdout_bytes.decode("utf-8", errors="replace"),
            stderr_bytes.decode("utf-8", errors="replace")
        )
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except OSError:
            pass
        stdout_bytes, stderr_bytes = await proc.communicate()
        return (
            -1,
            stdout_bytes.decode("utf-8", errors="replace") + "\n[Timeout]",
            stderr_bytes.decode("utf-8", errors="replace") + "\n[Timeout]"
        )
    except Exception as e:
        return -1, "", f"Subprocess exception: {e}"


@dataclass
class SandboxRunResult:
    """Details the result of executing a script inside the isolated environment."""
    script_path: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    success: bool
    timeout_occurred: bool


class IsolatedEnvironment:
    """
    Creates and manages Python Virtual Environments (venv) dynamically.
    Enables workspace management, package installations, and dependency resolution.
    """

    def __init__(
        self,
        workspace_dir: Optional[str] = None,
        venv_dir: Optional[str] = None
    ):
        self.workspace_dir = workspace_dir
        self.venv_dir = venv_dir
        self.python_path: Optional[str] = None
        self.pip_path: Optional[str] = None
        self.is_temp = False

    async def setup(self) -> None:
        """Create workspace, build virtualenv, and locate python/pip paths."""
        if not self.workspace_dir:
            self.workspace_dir = tempfile.mkdtemp(prefix="friday_sandbox_ws_")
            self.is_temp = True
            logger.info(f"Generated temporary workspace folder: {self.workspace_dir}")
        else:
            os.makedirs(self.workspace_dir, exist_ok=True)
            logger.info(f"Using workspace folder: {self.workspace_dir}")

        if not self.venv_dir:
            self.venv_dir = os.path.join(self.workspace_dir, ".venv")
            logger.info(f"Venv directory set to: {self.venv_dir}")

        # Setup virtual environment asynchronously (venv.create is blocking, run in executor)
        logger.info(f"Creating virtual environment in: {self.venv_dir}")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: venv.create(self.venv_dir, system_site_packages=True, with_pip=False)
        )

        # Handle platform-specific bin/Script paths
        if sys.platform == "win32":
            self.python_path = os.path.abspath(os.path.join(self.venv_dir, "Scripts", "python.exe"))
        else:
            self.python_path = os.path.abspath(os.path.join(self.venv_dir, "bin", "python"))
        self.pip_path = None

        if not os.path.exists(self.python_path):
            raise RuntimeError(
                f"Virtual environment creation failed. Python: {self.python_path}"
            )
        logger.info(f"Virtual environment setup complete. Python path: {self.python_path}")

    def is_module_installed(self, module_name: str) -> bool:
        """Check if a module is importable in the virtual environment."""
        top_level = module_name.split(".")[0]
        if is_standard_library(top_level):
            return True

        if not self.python_path or not os.path.exists(self.python_path):
            return False

        try:
            # Execute quick test command
            res = subprocess.run(
                [self.python_path, "-c", f"import {top_level}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5.0
            )
            return res.returncode == 0
        except Exception:
            return False

    async def install_package(self, package_name: str) -> bool:
        """Install a package into the environment using the virtual environment's pip."""
        if not self.python_path or not os.path.exists(self.python_path):
            logger.error("Venv python executable not available. Cannot install package.")
            return False

        cmd = [
            self.python_path,
            "-m",
            "pip",
            "install",
            package_name,
            "--disable-pip-version-check",
            "--no-cache-dir",
            "--timeout",
            "20"
        ]
        logger.info(f"Installing package: {package_name} -> {' '.join(cmd)}")

        exit_code, stdout, stderr = await _run_command_async(
            cmd, cwd=self.workspace_dir, timeout=120.0
        )
        if exit_code == 0:
            logger.info(f"Successfully installed package: {package_name}")
            return True
        else:
            logger.error(
                f"Failed to install package '{package_name}'. Exit Code: {exit_code}\n"
                f"Stdout: {stdout}\nStderr: {stderr}"
            )
            return False

    async def scan_and_install_dependencies(self, script_path: str) -> None:
        """Proactively scan the target script for third-party dependencies and install them."""
        if not os.path.exists(script_path):
            return

        imports = extract_imports(script_path)
        logger.info(f"Proactive dependency scanner identified imports in {script_path}: {imports}")

        for imp in imports:
            top_level = imp.split(".")[0]
            if is_standard_library(top_level):
                continue

            if not self.is_module_installed(top_level):
                pip_pkg = resolve_pip_package(top_level)
                logger.info(f"Dependency '{top_level}' is missing in venv. Installing package '{pip_pkg}'...")
                await self.install_package(pip_pkg)

    def cleanup(self) -> None:
        """Clean up the workspace and venv if they were dynamically created."""
        if not self.is_temp:
            logger.debug("Sandbox workspace is persistent. Skipping cleanup.")
            return

        if self.workspace_dir and os.path.exists(self.workspace_dir):
            logger.info(f"Deleting sandbox workspace folder: {self.workspace_dir}")

            def remove_readonly(func, path, excinfo):
                """Force delete read-only files (common on Windows)."""
                import stat
                try:
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                except Exception as e:
                    logger.debug(f"Unable to change permissions for {path}: {e}")

            try:
                shutil.rmtree(self.workspace_dir, onerror=remove_readonly)
                logger.info("Sandbox workspace cleaned up successfully.")
            except Exception as e:
                logger.warning(f"Error occurred during sandbox workspace cleanup: {e}")


class AutonomousSandboxRunner:
    """
    Executes Python scripts inside virtual environments, monitors processes, handles timeouts,
    reactively installs missing imports, and repairs logic errors via a self-healing LLM loop.
    """

    def __init__(
        self,
        env: Optional[IsolatedEnvironment] = None,
        model_name: Optional[str] = None
    ):
        self.env = env or IsolatedEnvironment()
        self.client = InferenceClient()
        self.model_name = model_name

    async def _safe_publish(self, topic: str, data: dict[str, Any]) -> None:
        """Publish events to Friday's ContextBus safely."""
        try:
            bus = get_bus()
            if bus:
                await bus.publish(topic, data)
        except Exception as e:
            logger.error(f"Failed to publish to context bus on {topic}: {e}")

    async def run_script(
        self,
        script_path: str,
        args: Optional[list[str]] = None,
        timeout: float = 30.0
    ) -> SandboxRunResult:
        """
        Execute python script using subprocess.Popen in the virtual environment.
        Measures duration, handles timeouts, and publishes events.
        """
        args = args or []
        python_exe = self.env.python_path
        if not python_exe or not os.path.exists(python_exe):
            raise RuntimeError(
                f"Virtual environment python executable not set or not found: {python_exe}"
            )

        cmd = [python_exe, script_path] + args
        logger.info(f"Executing script command: {' '.join(cmd)}")

        # Configure environment variables
        env_vars = os.environ.copy()
        venv_bin = os.path.dirname(python_exe)
        env_vars["PATH"] = os.pathsep.join([venv_bin, env_vars.get("PATH", "")])
        script_dir = os.path.dirname(os.path.abspath(script_path))
        env_vars["PYTHONPATH"] = os.pathsep.join([script_dir, env_vars.get("PYTHONPATH", "")])
        env_vars["PYTHONUNBUFFERED"] = "1"

        t0 = time.perf_counter()

        await self._safe_publish("sandbox.started", {
            "script_path": script_path,
            "args": args,
            "venv_path": self.env.venv_dir
        })

        # Run process in an executor to keep event loop free
        loop = asyncio.get_running_loop()
        exit_code, stdout, stderr, timeout_occurred = await loop.run_in_executor(
            None,
            lambda: _execute_subprocess_sync(cmd, self.env.workspace_dir or ".", env_vars, timeout)
        )

        duration_ms = int((time.perf_counter() - t0) * 1000)
        success = (exit_code == 0) and not timeout_occurred

        result = SandboxRunResult(
            script_path=script_path,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            success=success,
            timeout_occurred=timeout_occurred
        )

        status_str = "succeeded" if success else ("timed out" if timeout_occurred else "failed")
        await self._safe_publish("sandbox.progress", {
            "script_path": script_path,
            "message": f"Execution {status_str} in {duration_ms}ms with exit code {exit_code}",
            "exit_code": exit_code,
            "duration_ms": duration_ms,
            "success": success
        })

        return result

    async def auto_install_missing_imports(self, traceback_text: str) -> bool:
        """
        Scan traceback error messages for ModuleNotFoundError or ImportError,
        resolve missing packages to pip installable names, and run pip install.
        """
        if not traceback_text:
            return False

        logger.debug("Scanning traceback for missing modules...")

        # Pattern 1: ModuleNotFoundError: No module named 'some_module'
        no_mod_pattern = re.compile(
            r"(?:ModuleNotFoundError|ImportError):\s*No\s*module\s*named\s*'([^']+)'",
            re.IGNORECASE
        )
        # Pattern 2: ImportError: cannot import name 'sub_module' from 'module'
        import_from_pattern = re.compile(
            r"ImportError:\s*cannot\s*import\s*name\s*'([^']+)'\s*from\s*'([^']+)'",
            re.IGNORECASE
        )

        match_no_mod = no_mod_pattern.search(traceback_text)
        match_import_from = import_from_pattern.search(traceback_text)

        missing_module = None
        if match_no_mod:
            missing_module = match_no_mod.group(1)
        elif match_import_from:
            # The top-level module is from where imports are fetched
            missing_module = match_import_from.group(2)

        # Fallback trace line scan backwards
        if not missing_module:
            lines = traceback_text.splitlines()
            for line in reversed(lines):
                if "ModuleNotFoundError:" in line or "ImportError:" in line:
                    m = re.search(r"No module named\s*'([^']+)'", line, re.IGNORECASE)
                    if m:
                        missing_module = m.group(1)
                        break
                    m2 = re.search(r"cannot import name\s*'([^']+)'\s*from\s*'([^']+)'", line, re.IGNORECASE)
                    if m2:
                        missing_module = m2.group(2)
                        break

        if not missing_module:
            return False

        top_level = missing_module.split(".")[0]
        if is_standard_library(top_level):
            logger.warning(f"Failed to resolve: module '{top_level}' is a Python stdlib module.")
            return False

        pip_pkg = resolve_pip_package(top_level)
        logger.info(f"Traceback indicates missing import '{missing_module}'. Installing package '{pip_pkg}'...")

        await self._safe_publish("sandbox.progress", {
            "message": f"Reactively installing missing package '{pip_pkg}'...",
            "status": "installing_dependency"
        })

        success = await self.env.install_package(pip_pkg)
        if success:
            await self._safe_publish("sandbox.progress", {
                "message": f"Successfully installed '{pip_pkg}'",
                "status": "dependency_installed"
            })
            return True
        else:
            await self._safe_publish("sandbox.progress", {
                "message": f"Failed to install package '{pip_pkg}'",
                "status": "dependency_installation_failed"
            })
            return False

    def _parse_llm_response(self, text: str) -> tuple[str, str]:
        """Extract explanation and corrected python code block from LLM tags."""
        explanation = ""
        corrected_code = ""

        # 1. Extract explanation
        exp_match = re.search(r"<explanation>(.*?)</explanation>", text, re.DOTALL | re.IGNORECASE)
        if exp_match:
            explanation = exp_match.group(1).strip()
        else:
            # Fallback to lines before the code block
            parts = text.split("<code_patch>")
            if parts:
                explanation = parts[0].strip()
            else:
                parts_py = text.split("```python")
                if parts_py:
                    explanation = parts_py[0].strip()

        # Clean tags from explanation
        explanation = re.sub(r"<[^>]+>", "", explanation).strip()

        # 2. Extract code block
        code_match = re.search(r"<code_patch>(.*?)</code_patch>", text, re.DOTALL | re.IGNORECASE)
        if code_match:
            code_content = code_match.group(1).strip()
            if "```python" in code_content:
                code_content = code_content.split("```python")[1].split("```")[0].strip()
            elif "```" in code_content:
                code_content = code_content.split("```")[1].split("```")[0].strip()
            corrected_code = code_content
        else:
            # Fallback direct markdown block search
            blocks = re.findall(r"```python\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
            if blocks:
                corrected_code = blocks[0].strip()
            else:
                blocks_generic = re.findall(r"```\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
                if blocks_generic:
                    corrected_code = blocks_generic[0].strip()

        return explanation, corrected_code

    async def _query_llm_for_repair(
        self,
        script_path: str,
        code: str,
        traceback_text: str,
        attempt: int
    ) -> tuple[str, str]:
        """Query InferenceClient to analyze traceback error and return corrected python script."""
        model = self.model_name or resolve_model("code_gen") or "nvidia/llama-3.1-nemotron-70b-instruct"
        
        system_prompt = (
            "You are Friday's Autonomous Self-Healing Debugger. You analyze python crash logs and "
            "repair code. You do not use mocks or stub code. You return clean, complete, working python "
            "code that replaces the original file entirely. You output your bug explanation inside "
            "<explanation> tags and the full corrected code inside <code_patch> tags containing a single "
            "```python code block."
        )

        user_prompt = f"""
Failing Script Path: {script_path}
Debugging Attempt: {attempt}

Original Code Contents:
```python
{code}
```

Crash Traceback / Error Log:
```
{traceback_text}
```

Please:
1. Explain the root cause of this error.
2. Provide the complete corrected Python code. Write the entire script with the fix, retaining all standard imports, classes, and logic.

Response format:
<explanation>
Your explanation goes here.
</explanation>

<code_patch>
```python
# The complete corrected python file contents here.
```
</code_patch>
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        logger.info(f"Querying model '{model}' for code repair (attempt {attempt})...")
        try:
            res = await self.client.chat(
                model=model,
                messages=messages,
                temperature=0.1
            )
            return self._parse_llm_response(res.content)
        except Exception as e:
            logger.error(f"Error during primary LLM query: {e}. Trying fallback model...")
            # Fallback model query
            fallback_model = "meta/llama-3.3-70b-instruct"
            try:
                res = await self.client.chat(
                    model=fallback_model,
                    messages=messages,
                    temperature=0.1
                )
                return self._parse_llm_response(res.content)
            except Exception as e_fallback:
                logger.error(f"Fallback LLM query failed: {e_fallback}")
                return "", ""

    async def repair_and_retry(
        self,
        script_path: str,
        traceback_text: str,
        max_attempts: int = 5,
        attempt: int = 1
    ) -> SandboxRunResult:
        """
        Recursive debugging loop.
        Explains bugs, applies corrected patches, calculates unified diffs, and executes retries.
        """
        logger.info(f"Autonomous repair loop: attempt {attempt}/{max_attempts} for {script_path}")

        if attempt > max_attempts:
            logger.warning(f"Exceeded max repair attempts ({max_attempts}) for {script_path}.")
            await self._safe_publish("sandbox.failed", {
                "script_path": script_path,
                "error": "Max repair attempts reached",
                "traceback": traceback_text,
                "attempts": attempt - 1
            })
            # Run final retry to get definitive failure result
            return await self.run_script(script_path)

        # 1. Reactive check: is it a missing import error?
        is_import_error = "ModuleNotFoundError" in traceback_text or "ImportError" in traceback_text
        if is_import_error:
            installed = await self.auto_install_missing_imports(traceback_text)
            if installed:
                result = await self.run_script(script_path)
                if result.success:
                    await self._safe_publish("sandbox.completed", {
                        "script_path": script_path,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "duration_ms": result.duration_ms,
                        "repaired_by": "dependency_auto_install",
                        "attempts": attempt
                    })
                    return result
                else:
                    return await self.repair_and_retry(
                        script_path,
                        result.stderr,
                        max_attempts=max_attempts,
                        attempt=attempt + 1
                    )

        # 2. Programmatic logic repair via NIM LLM
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Script to repair does not exist: {script_path}")

        try:
            with open(script_path, "r", encoding="utf-8") as f:
                original_code = f.read()
        except Exception as e:
            logger.error(f"Failed to read original file {script_path}: {e}")
            return SandboxRunResult(
                script_path=script_path,
                exit_code=-1,
                stdout="",
                stderr=f"Error reading file for repair: {e}",
                duration_ms=0,
                success=False,
                timeout_occurred=False
            )

        explanation, corrected_code = await self._query_llm_for_repair(
            script_path, original_code, traceback_text, attempt
        )

        if not corrected_code:
            logger.error("No valid patch generated by model. Recursing repair retry...")
            return await self.repair_and_retry(
                script_path,
                traceback_text + "\n[Debugger: Repair attempt failed to generate code patch]",
                max_attempts=max_attempts,
                attempt=attempt + 1
            )

        # Compute and output unified diff of patch
        diff_text = calculate_unified_diff(original_code, corrected_code, os.path.basename(script_path))
        logger.info(f"Proposed Repair Diff (Attempt {attempt}):\n{diff_text}")

        # Write corrected code to script path
        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(corrected_code)
        except Exception as e:
            logger.error(f"Failed to write repaired code to {script_path}: {e}")
            return SandboxRunResult(
                script_path=script_path,
                exit_code=-1,
                stdout="",
                stderr=f"Failed to write repaired file: {e}",
                duration_ms=0,
                success=False,
                timeout_occurred=False
            )

        # Publish sandbox.repaired event
        await self._safe_publish("sandbox.repaired", {
            "script_path": script_path,
            "attempt": attempt,
            "explanation": explanation,
            "diff": diff_text
        })

        # Re-run execution
        result = await self.run_script(script_path)
        if result.success:
            logger.info(f"Self-healing debugger resolved crash successfully in attempt {attempt}!")
            await self._safe_publish("sandbox.completed", {
                "script_path": script_path,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration_ms": result.duration_ms,
                "repaired_by": "llm_code_patch",
                "attempts": attempt
            })
            return result
        else:
            logger.warning(f"Repair code failed with exit code {result.exit_code}. Retrying...")
            return await self.repair_and_retry(
                script_path,
                result.stderr or "[Execution crashed without traceback output]",
                max_attempts=max_attempts,
                attempt=attempt + 1
            )

    async def run_and_heal(
        self,
        script_path: str,
        args: Optional[list[str]] = None,
        timeout: float = 30.0,
        max_attempts: int = 5
    ) -> SandboxRunResult:
        """
        Setup virtual environment, check and install dependencies,
        run the script, and handle logic crashes through self-healing loops.
        """
        logger.info(f"Starting Sandbox Run & Heal pipeline for: {script_path}")

        # Ensure environment is initialized
        if not self.env.python_path:
            await self._safe_publish("sandbox.progress", {
                "script_path": script_path,
                "message": "Initializing isolated virtualenv...",
                "status": "init_env"
            })
            await self.env.setup()

        # Proactive dependency scan and install
        await self._safe_publish("sandbox.progress", {
            "script_path": script_path,
            "message": "Scanning script dependencies...",
            "status": "scanning_imports"
        })
        await self.env.scan_and_install_dependencies(script_path)

        # First run
        result = await self.run_script(script_path, args=args, timeout=timeout)
        if result.success:
            logger.info("Script executed successfully on the first run.")
            await self._safe_publish("sandbox.completed", {
                "script_path": script_path,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration_ms": result.duration_ms,
                "repaired_by": "none"
            })
            return result

        # Dynamic debug loop on failure
        logger.warning(f"Initial run failed (exit_code={result.exit_code}). Running self-healing debugger...")
        traceback_str = result.stderr if result.stderr.strip() else "[Standard error stream was empty]"
        if result.timeout_occurred:
            traceback_str = f"TimeoutExpired: Script execution timed out after {timeout} seconds."

        final_result = await self.repair_and_retry(
            script_path,
            traceback_str,
            max_attempts=max_attempts,
            attempt=1
        )

        return final_result


if __name__ == "__main__":
    # Command Line Interface / Development Diagnostic Mode
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    async def main():
        print("=== Sandbox Runner Diagnostic Test ===")
        if len(sys.argv) < 2:
            print("Usage: python sandbox_runner.py <script_to_run_path>")
            # Create a simple test file that fails
            temp_dir = tempfile.mkdtemp()
            test_script = os.path.join(temp_dir, "test_buggy_script.py")
            
            # This script imports colorama, prints, and division by zero to test both dependency and repair loops
            test_code = (
                "import colorama\n"
                "print('Colorama package successfully loaded in venv!')\n"
                "def calculate():\n"
                "    # Introduce error\n"
                "    res = 10 / 0\n"
                "    print(f'Result: {res}')\n\n"
                "calculate()\n"
            )
            with open(test_script, "w", encoding="utf-8") as f:
                f.write(test_code)
                
            print(f"Created buggy test script: {test_script}")
            script_to_run = test_script
            is_test = True
        else:
            script_to_run = sys.argv[1]
            is_test = False

        runner = AutonomousSandboxRunner()
        try:
            result = await runner.run_and_heal(script_to_run, timeout=20.0)
            print("\n=== Sandbox Runner Execution Summary ===")
            print(f"Script Path:  {result.script_path}")
            print(f"Exit Code:    {result.exit_code}")
            print(f"Success:      {result.success}")
            print(f"Duration:     {result.duration_ms}ms")
            print(f"Stdout:\n{result.stdout}")
            print(f"Stderr:\n{result.stderr}")
        except Exception as e:
            traceback.print_exc()
            logger.error(f"Sandbox runner diagnostic failed: {e}")
        finally:
            if is_test:
                runner.env.cleanup()
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass

    asyncio.run(main())
