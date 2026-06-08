"""
Central path resolution module for FRIDAY.
Auto-discovers all project file locations — no hardcoded absolute paths.
Call get_*() functions to get any path in the project.
"""
import os
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Return the absolute path to the project root (where friday/ lives)."""
    this_file = Path(__file__).resolve()
    # paths.py is at friday/paths.py — project root is parent of the friday directory
    for parent in this_file.parents:
        # Check: does parent/friday/live.py exist?
        if (parent / "friday" / "live.py").is_file():
            return parent
    # Fallback
    return Path.cwd().resolve()


def get_friday_dir() -> Path:
    """Return the friday package directory."""
    return get_project_root() / "friday"


def get_tools_dir() -> Path:
    """Return the friday/tools directory."""
    return get_friday_dir() / "tools"


def get_osint_extra_path() -> Path:
    """Return path to tools_osint_extra.py."""
    return get_friday_dir() / "tools_osint_extra.py"


def get_env_path() -> Path:
    """Return path to .env file."""
    return get_project_root() / ".env"


def get_downloads_dir() -> Path:
    """Return user's Downloads directory, falling back to project root."""
    try:
        import platformdirs
        return Path.home() / "Downloads"
    except ImportError:
        pass
    # Windows
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        try:
            buf = ctypes.create_unicode_buffer(260)
            ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf)
            return Path(buf.value)
        except Exception:
            pass
    # Fallback
    dl = Path.home() / "Downloads"
    if dl.is_dir():
        return dl
    return get_project_root()


def get_skills_path() -> Path:
    """Return path to skills.md (FRIDAY's system skill file)."""
    p = get_friday_dir() / "skills.md"
    if p.exists():
        return p
    # Also check .opencode/skills/ directory
    alt = get_project_root() / ".opencode" / "skills" / "friday.md"
    if alt.exists():
        return alt
    return p


def get_knowledge_dir() -> Path:
    """Return the knowledge store directory."""
    return get_friday_dir() / "friday_memory" / "knowledge"


def get_sidecar_dir() -> Path:
    """Return the sidecar directory."""
    return get_friday_dir() / "sidecar"


def get_scripts_dir() -> Path:
    """Return the scripts directory."""
    return get_project_root() / "scripts"


def get_temp_dir() -> Path:
    """Return a FRIDAY-specific temp directory."""
    tmp = Path(os.environ.get("FRIDAY_TEMP", "")) if os.environ.get("FRIDAY_TEMP") else None
    if tmp and tmp.is_dir():
        return tmp
    system_temp = Path(os.environ.get("TEMP", "/tmp"))
    friday_temp = system_temp / "friday"
    friday_temp.mkdir(parents=True, exist_ok=True)
    return friday_temp


def get_reports_dir() -> Path:
    """Return directory for generated reports."""
    reports = get_friday_dir() / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    return reports


def ensure_dir(path: Path) -> Path:
    """Ensure a directory exists and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def add_project_to_path():
    """Ensure project root is in sys.path for imports."""
    root = str(get_project_root())
    if root not in sys.path:
        sys.path.insert(0, root)
