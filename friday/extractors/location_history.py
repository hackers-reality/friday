"""
Extract location patterns from Google Takeout Location History.
Parses Records.json and Semantic Location History JSON files.
Reverse geocodes coordinates → city names via geopy/Nominatim (rate-limited).
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from friday.logging_utils import configure_logging

logger = configure_logging(__name__)

try:
    from geopy.geocoders import Nominatim
    _geolocator = Nominatim(user_agent="friday-takeout")
except ImportError:
    _geolocator = None

_GEO_CACHE: dict[tuple, str] = {}


def _reverse_geocode(lat: float, lon: float) -> Optional[str]:
    if _geolocator is None or (lat == 0.0 and lon == 0.0):
        return None
    key = (round(lat, 3), round(lon, 3))
    if key in _GEO_CACHE:
        return _GEO_CACHE[key]
    try:
        location = _geolocator.reverse(f"{lat}, {lon}", timeout=3)
        if location and location.address:
            parts = location.address.split(",")
            city = parts[0].strip() if parts else None
            _GEO_CACHE[key] = city or "Unknown"
            return _GEO_CACHE[key]
    except Exception:
        pass
    return None


def _parse_timestamp_ms(ms: int) -> Optional[datetime]:
    try:
        return datetime.fromtimestamp(ms / 1000)
    except Exception:
        return None


def extract_location_history(zip_file) -> list[dict]:
    """Parse location records from Takeout Location History."""
    chunks: list[dict] = []

    records: list[dict] = []

    # Primary: Records.json
    for path in ["Takeout/Location History/Records.json",
                 "Takeout/Location History/Location History/Records.json"]:
        try:
            data = json.loads(zip_file.read(path))
            items = data.get("locations", [])
            records.extend(items)
            logger.info("Loaded %d records from %s", len(items), path)
        except KeyError:
            continue
        except Exception as exc:
            logger.warning("Failed %s: %s", path, exc)

    # Secondary: Semantic Location History (monthly JSONs)
    try:
        prefix = "Takeout/Location History/Semantic Location History/"
        for name in zip_file.namelist():
            if name.startswith(prefix) and name.endswith(".json"):
                try:
                    sem_data = json.loads(zip_file.read(name))
                    for timeline in sem_data.get("timelineObjects", []):
                        if "placeVisit" in timeline:
                            loc = timeline["placeVisit"].get("location", {})
                            records.append({
                                "latitudeE7": loc.get("latitudeE7", 0),
                                "longitudeE7": loc.get("longitudeE7", 0),
                                "timestampMs": timeline["placeVisit"].get("duration", {}).get("startTimestampMs", 0),
                                "placeName": loc.get("name", ""),
                                "address": loc.get("address", ""),
                            })
                except Exception:
                    continue
    except Exception:
        pass

    if not records:
        return chunks

    # Convert to usable list
    parsed: list[dict] = []
    for rec in records:
        lat_e7 = rec.get("latitudeE7", rec.get("latitude", 0))
        lon_e7 = rec.get("longitudeE7", rec.get("longitude", 0))
        lat = lat_e7 / 1e7 if abs(lat_e7) > 1e6 else lat_e7
        lon = lon_e7 / 1e7 if abs(lon_e7) > 1e6 else lon_e7

        ts_ms = rec.get("timestampMs", rec.get("timestamp", 0))
        dt = _parse_timestamp_ms(int(ts_ms)) if ts_ms else None

        if lat and lon:
            parsed.append({"lat": lat, "lon": lon, "dt": dt,
                           "place": rec.get("placeName", ""),
                           "address": rec.get("address", "")})

    if not parsed:
        return chunks

    # --- Home location (most frequent night-time, 10pm-6am) ---
    night_coords: Counter = Counter()
    day_coords: Counter = Counter()
    for p in parsed:
        if p["dt"]:
            hour = p["dt"].hour
            key = (round(p["lat"], 2), round(p["lon"], 2))
            if hour < 6 or hour >= 22:
                night_coords[key] += 1
            else:
                day_coords[key] += 1

    if night_coords:
        home_key = night_coords.most_common(1)[0][0]
        home_city = _reverse_geocode(home_key[0], home_key[1])
        if home_city:
            chunks.append({
                "content": f"User's home location is likely in or near {home_city} "
                           f"based on frequent night-time GPS coordinates.",
                "source": "google_takeout/location_history",
                "category": "locations",
                "confidence": 0.75,
            })

    if day_coords:
        work_key = day_coords.most_common(1)[0][0]
        work_city = _reverse_geocode(work_key[0], work_key[1])
        if work_city and work_key != home_key:
            chunks.append({
                "content": f"User's daytime / work location is likely in or near {work_city}.",
                "source": "google_takeout/location_history",
                "category": "locations",
                "confidence": 0.70,
            })

    # --- Frequent places ---
    place_counter: Counter = Counter()
    for p in parsed:
        if p["place"]:
            place_counter[p["place"]] += 1

    if place_counter:
        top_places = place_counter.most_common(10)
        lines = [f"  - {name} ({cnt} visits)" for name, cnt in top_places[:5]]
        chunks.append({
            "content": "User's most frequently visited places:\n" + "\n".join(lines),
            "source": "google_takeout/location_history",
            "category": "locations",
            "confidence": 0.80,
        })

    # --- City/country counts ---
    if not _geolocator:
        return chunks

    city_counter: Counter = Counter()
    for p in parsed[:500]:  # limit for performance
        city = _reverse_geocode(p["lat"], p["lon"])
        if city:
            city_counter[city] += 1

    if city_counter:
        top_cities = city_counter.most_common(5)
        lines = [f"  - {city} ({cnt} pings)" for city, cnt in top_cities]
        chunks.append({
            "content": "Cities where user has most location activity:\n" + "\n".join(lines),
            "source": "google_takeout/location_history",
            "category": "schedule",
            "confidence": 0.70,
        })

    return chunks
