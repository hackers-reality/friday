"""FRIDAY OSINT tool implementations for the Ghost agent."""

from friday.tools.sherlock_tool import SherlockResult, run_sherlock
from friday.tools.exiftool_tool import ExifResult, run_exiftool, strip_metadata
from friday.tools.spiderfoot_tool import SpiderFootResult, SpiderFootEntity, SpiderFootThreat, run_spiderfoot

__all__ = [
    "SherlockResult", "run_sherlock",
    "ExifResult", "run_exiftool", "strip_metadata",
    "SpiderFootResult", "SpiderFootEntity", "SpiderFootThreat", "run_spiderfoot",
]
