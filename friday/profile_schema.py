"""
Friday Profile Schema — JSON Schema validation for user_profile.json.
Ensures profile data integrity and catches corruption early.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple
import json
import os

PROFILE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "FRIDAY User Profile",
    "type": "object",
    "properties": {
        "name": {"type": "string", "maxLength": 200},
        "age": {"type": ["string", "integer", "null"], "maxLength": 20},
        "location": {"type": "string", "maxLength": 200},
        "occupation": {"type": "string", "maxLength": 200},
        "interests": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "source": {"type": "string"},
                    "category": {"type": "string"},
                    "timestamp": {"type": ["string", "null"]},
                    "_pinned": {"type": "boolean"},
                    "_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["item"],
            },
        },
        "tech_stack": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "source": {"type": "string"},
                    "category": {"type": "string"},
                    "timestamp": {"type": ["string", "null"]},
                    "_pinned": {"type": "boolean"},
                    "_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["item"],
            },
        },
        "goals": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "source": {"type": "string"},
                    "category": {"type": "string"},
                    "timestamp": {"type": ["string", "null"]},
                    "_pinned": {"type": "boolean"},
                    "_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["item"],
            },
        },
        "personality": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "source": {"type": "string"},
                    "category": {"type": "string"},
                    "timestamp": {"type": ["string", "null"]},
                    "_pinned": {"type": "boolean"},
                    "_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["item"],
            },
        },
        "favorites": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "source": {"type": "string"},
                    "category": {"type": "string"},
                    "timestamp": {"type": ["string", "null"]},
                    "_pinned": {"type": "boolean"},
                    "_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["item"],
            },
        },
        "professional_skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "source": {"type": "string"},
                    "category": {"type": "string"},
                    "timestamp": {"type": ["string", "null"]},
                    "_pinned": {"type": "boolean"},
                    "_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["item"],
            },
        },
        "communication_style": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "source": {"type": "string"},
                    "category": {"type": "string"},
                    "timestamp": {"type": ["string", "null"]},
                    "_pinned": {"type": "boolean"},
                    "_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["item"],
            },
        },
        "life_context": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "source": {"type": "string"},
                    "category": {"type": "string"},
                    "timestamp": {"type": ["string", "null"]},
                    "_pinned": {"type": "boolean"},
                    "_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["item"],
            },
        },
        "preferences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "source": {"type": "string"},
                    "category": {"type": "string"},
                    "timestamp": {"type": ["string", "null"]},
                    "_pinned": {"type": "boolean"},
                    "_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["item"],
            },
        },
        "_version": {"type": "integer", "minimum": 1},
        "_profile_confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "_last_updated": {"type": ["string", "null"]},
        "_audit_history": {
            "type": "array",
            "items": {"type": "object"},
        },
        "_review_queue": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "field": {"type": "string"},
                    "reason": {"type": "string"},
                    "timestamp": {"type": "string"},
                    "resolved": {"type": "boolean"},
                },
            },
        },
    },
    "required": ["name"],
}


def validate_profile(profile: dict) -> Tuple[bool, List[str]]:
    """Validate a profile dict against the JSON Schema.

    Returns (is_valid, list_of_errors).
    """
    errors: List[str] = []

    # Check required top-level fields
    if "name" not in profile:
        errors.append("Missing required field: 'name'")

    # Type checks for scalar fields
    scalar_fields = {
        "name": str,
        "age": (str, int, type(None)),
        "location": str,
        "occupation": str,
    }
    for field, expected in scalar_fields.items():
        val = profile.get(field)
        if val is not None and not isinstance(val, expected):
            errors.append(f"'{field}' should be {expected.__name__}, got {type(val).__name__}")

    # Length checks
    if isinstance(profile.get("name"), str) and len(profile["name"]) > 200:
        errors.append("'name' exceeds 200 characters")

    # Check array fields
    array_fields = [
        "interests", "tech_stack", "goals", "personality",
        "favorites", "professional_skills", "communication_style",
        "life_context", "preferences",
    ]
    for field in array_fields:
        val = profile.get(field)
        if val is not None:
            if not isinstance(val, list):
                errors.append(f"'{field}' should be a list, got {type(val).__name__}")
            else:
                for i, item in enumerate(val):
                    if not isinstance(item, dict):
                        errors.append(f"'{field}[{i}]' should be an object")
                    elif "item" not in item:
                        errors.append(f"'{field}[{i}]' missing required 'item' field")

    # Check version
    version = profile.get("_version")
    if version is not None and not isinstance(version, int):
        errors.append(f"'_version' should be integer, got {type(version).__name__}")

    # Check profile confidence
    confidence = profile.get("_profile_confidence")
    if confidence is not None:
        if not isinstance(confidence, (int, float)):
            errors.append(f"'_profile_confidence' should be a number")
        elif confidence < 0 or confidence > 1:
            errors.append(f"'_profile_confidence' should be between 0 and 1")

    return len(errors) == 0, errors


def validate_profile_file(filepath: str) -> Tuple[bool, List[str]]:
    """Validate a profile file on disk.

    Returns (is_valid, list_of_errors).
    """
    if not os.path.exists(filepath):
        return False, ["File not found"]
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            profile = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]
    except Exception as e:
        return False, [str(e)]

    return validate_profile(profile)
