"""
ExifTool OSINT Tool — extracts metadata from image files.

Runs exiftool as subprocess, parses JSON output, detects GPS,
reverse geocodes, and flags sensitive metadata.

Integrates with vision pipeline: when user drops a photo for
CV analysis, this tool runs FIRST and passes metadata as context.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from friday.logging_utils import configure_logging

logger = configure_logging(__name__)


@dataclass
class ExifResult:
    file_path: str
    success: bool = False
    error: str = ""

    # GPS
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    location_name: Optional[str] = None

    # Camera
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    datetime_original: Optional[str] = None
    software: Optional[str] = None

    # Flags
    is_edited: bool = False
    has_gps: bool = False
    has_sensitive_metadata: bool = False

    # Raw
    raw_metadata: dict = field(default_factory=dict)


def _check_exiftool() -> bool:
    """Check exiftool is in PATH."""
    try:
        proc = subprocess.run(["exiftool", "-ver"], capture_output=True, text=True, timeout=5)
        return proc.returncode == 0
    except Exception:
        return False


def _dms_to_decimal(dms_ref: str, dms_values: list[float]) -> float:
    """Convert DMS (degrees, minutes, seconds) to decimal degrees."""
    if not dms_values or len(dms_values) < 3:
        return 0.0
    deg, mins, secs = dms_values[0], dms_values[1], dms_values[2]
    decimal = deg + mins / 60.0 + secs / 3600.0
    if dms_ref in ("S", "W"):
        decimal = -decimal
    return decimal


async def _reverse_geocode(lat: float, lon: float, cache: dict) -> Optional[str]:
    """Reverse geocode coordinates to location name (geopy Nominatim, cached)."""
    key = f"{round(lat, 4)},{round(lon, 4)}"
    if key in cache:
        return cache[key]

    try:
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent="friday_osint")
        loc = await asyncio.get_event_loop().run_in_executor(
            None, lambda: geolocator.reverse(f"{lat}, {lon}", timeout=5)
        )
        if loc and loc.address:
            cache[key] = loc.address
            return loc.address
    except Exception as exc:
        logger.debug("Geocode failed: %s", exc)
    return None


_EDIT_SIGNATURES = {"photoshop", "gimp", "lightroom", "affinity", "pixelmator", "snapseed", "vsco"}


async def run_exiftool(
    file_path: str | Path,
    reverse_geocode: bool = True,
) -> ExifResult:
    """
    Extract metadata from an image file using ExifTool.

    Args:
        file_path: path to the image file
        reverse_geocode: if True, attempt geopy reverse geocoding for GPS coords

    Returns:
        ExifResult with parsed metadata
    """
    path = Path(file_path)
    if not path.exists():
        return ExifResult(file_path=str(path), error=f"File not found: {path}")

    if not _check_exiftool():
        return ExifResult(file_path=str(path), error="exiftool not in PATH. Install: winget install exiftool")

    try:
        proc = await asyncio.create_subprocess_exec(
            "exiftool", "-json", str(path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)

        if proc.returncode != 0:
            stderr_text = stderr.decode(errors="replace")[:200]
            return ExifResult(file_path=str(path), error=f"exiftool error: {stderr_text}")

        raw_list = json.loads(stdout.decode(errors="replace"))
        if not raw_list:
            return ExifResult(file_path=str(path), error="No metadata returned")

        raw = raw_list[0] if isinstance(raw_list, list) else raw_list
        result = ExifResult(
            file_path=str(path),
            success=True,
            raw_metadata=raw,
            camera_make=raw.get("Make"),
            camera_model=raw.get("Model"),
            datetime_original=raw.get("DateTimeOriginal"),
            software=raw.get("Software"),
        )

        # GPS parsing
        gps_lat_ref = raw.get("GPSLatitudeRef", "N")
        gps_lat = raw.get("GPSLatitude")
        gps_lon_ref = raw.get("GPSLongitudeRef", "E")
        gps_lon = raw.get("GPSLongitude")

        if gps_lat and gps_lon:
            result.gps_latitude = _dms_to_decimal(gps_lat_ref, gps_lat if isinstance(gps_lat, list) else [float(gps_lat)])
            result.gps_longitude = _dms_to_decimal(gps_lon_ref, gps_lon if isinstance(gps_lon, list) else [float(gps_lon)])
            result.has_gps = True
            result.has_sensitive_metadata = True

            if reverse_geocode:
                _cache: dict = {}
                result.location_name = await _reverse_geocode(
                    result.gps_latitude, result.gps_longitude, _cache
                )

        # Detect edits
        if result.software:
            sw_lower = result.software.lower()
            for sig in _EDIT_SIGNATURES:
                if sig in sw_lower:
                    result.is_edited = True
                    break

        return result

    except asyncio.TimeoutError:
        return ExifResult(file_path=str(path), error="exiftool timed out after 15s")
    except json.JSONDecodeError as exc:
        return ExifResult(file_path=str(path), error=f"Failed to parse exiftool JSON: {exc}")
    except Exception as exc:
        logger.exception("exiftool run failed: %s", exc)
        return ExifResult(file_path=str(path), error=str(exc))


async def strip_metadata(file_path: str | Path) -> dict:
    """
    Strip all metadata from an image file using exiftool -all= .

    Returns dict with {success, output_path, error}.
    """
    path = Path(file_path)
    if not path.exists():
        return {"success": False, "error": f"File not found: {path}"}

    if not _check_exiftool():
        return {"success": False, "error": "exiftool not in PATH"}

    backup = path.with_suffix(path.suffix + ".bak")
    try:
        proc = await asyncio.create_subprocess_exec(
            "exiftool", "-all=", "-overwrite_original", str(path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)

        if proc.returncode != 0:
            stderr_text = stderr.decode(errors="replace")[:200]
            return {"success": False, "error": f"Strip failed: {stderr_text}"}

        # Clean up backup if created
        if backup.exists():
            backup.unlink()

        return {"success": True, "output_path": str(path)}

    except asyncio.TimeoutError:
        return {"success": False, "error": "exiftool timed out during strip"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
