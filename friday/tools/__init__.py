"""FRIDAY tools package — re-exports all flat tools + OSINT sub-modules.

All tool functions (alexa_command, send_instagram_dm, open_url, etc.) are
defined in friday/tools_flat.py (formerly tools.py) and re-exported here.
OSINT sub-modules are available as friday.tools.sherlock_tool, etc.
"""

import sys as _sys
import friday.tools_flat as _tflat

# Re-export ALL public names from tools_flat (not just __all__)
# This ensures names like github_refresh_token that are in live.py's
# TOOL_MAP but accidentally missing from __all__ still resolve.
_mod = _sys.modules[__name__]
for _key in _tflat.__dict__:
    if not _key.startswith("_"):
        _mod.__dict__[_key] = _tflat.__dict__[_key]

# OSINT sub-module imports
from friday.tools.sherlock_tool import SherlockResult, run_sherlock
from friday.tools.exiftool_tool import ExifResult, run_exiftool, strip_metadata
from friday.tools.spiderfoot_tool import SpiderFootResult, SpiderFootEntity, SpiderFootThreat, run_spiderfoot

# Merged __all__ for master.py and introspection
__all__ = _tflat.__all__ + [
    "SherlockResult", "run_sherlock",
    "ExifResult", "run_exiftool", "strip_metadata",
    "SpiderFootResult", "SpiderFootEntity", "SpiderFootThreat", "run_spiderfoot",
]
