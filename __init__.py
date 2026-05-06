"""
Friday - Advanced AI Assistant.
Complete package initialization.
"""
from __future__ import annotations

__version__ = "2.0.0"
__author__ = "hackers-reality"

# Core imports
try:
    from friday_core import FridayCore, FridayAssistant
except ImportError:
    FridayCore = None
    FridayAssistant = None

try:
    from friday_assistant import FridayAssistant as MainAssistant
except ImportError:
    MainAssistant = None

# Module availability
AVAILABLE_MODULES = []
HIDDEN_MODULES = []

def _check_module(name: str) -> bool:
    """Check if module is available."""
    try:
        __import__(name)
        return True
    except ImportError:
        return False

# Check all modules
ALL_MODULES = [
    "friday_core",
    "friday_assistant",
    "friday_voice",
    "friday_web",
    "friday_automation",
    "friday_database",
    "friday_ai",
    "friday_tools",
    "friday_vision",
    "friday_security",
    "friday_monitor",
    "friday_scheduler",
    "friday_api",
    "friday_cloud",
    "friday_iot",
    "friday_dashboard",
    "friday_analytics",
    "friday_config",
    "friday_backup",
    "friday_nlp",
    "friday_integrations",
    "advanced_networking",
    "advanced_crypto",
]

for module in ALL_MODULES:
    if _check_module(module):
        AVAILABLE_MODULES.append(module)
    else:
        HIDDEN_MODULES.append(module)


def get_info() -> dict:
    """Get Friday package information."""
    return {
        "name": "Friday",
        "version": __version__,
        "author": __author__,
        "available_modules": AVAILABLE_MODULES,
        "missing_modules": HIDDEN_MODULES,
        "module_count": len(AVAILABLE_MODULES),
    }


def print_banner():
    """Print Friday banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   ██████╗ ██████╗ ██╗   ██╗ ██╗   ██╗ ██████╗ ██████╗ ██╗  ██╗   ║
║  ██╔═══╝ ██╔═══╝ ██║   ██║ ██║   ██║ ██╔═══╝ ██╔══██╗███║  ██║   ║
║  ██║     █████╗   ██║   ██║ ██║   ██║ ██║     ██████╔╝╚██║  ██║   ║
║  ██║     ██╔══╝   ╚██╗ ██╔╝ ██║   ██║ ██║     ██╔══██╗ ██║  ██║   ║
║  ╚█████╗  ██║       ╚████╔╝  ╚██████╔╝ ╚█████╗ ██║  ██║   ║
║   ╚════╝  ╚═╝        ╚═══╝    ╚═════╝  ╚═════╝ ╚═╝  ╚═╝   ║
║                                                                  ║
║               Advanced AI Assistant v{}                  ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════════╝
""".format(__version__)
    print(banner)


if __name__ == "__main__":
    print_banner()
    info = get_info()
    print(f"Available Modules: {info['module_count']}")
    print(f"Missing Modules: {len(info['missing_modules'])}")
    print("\nAvailable:")
    for module in info["available_modules"]:
        print(f"  ✅ {module}")
    if info["missing_modules"]:
        print("\nMissing:")
        for module in info["missing_modules"]:
            print(f"  ❌ {module}")
