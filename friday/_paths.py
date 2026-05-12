"""Centralized path resolution for the friday/ package.
All files should import from here instead of computing paths from __file__ directly.
"""
import os

_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_PACKAGE_DIR)

FRIDAY_MEMORY = os.path.join(PROJECT_ROOT, "friday_memory")
CREDENTIALS_JSON = os.path.join(PROJECT_ROOT, "credentials.json")
GMAIL_TOKEN = os.path.join(PROJECT_ROOT, ".gmail_token.json")
STARK_LOGS = os.path.join(PROJECT_ROOT, "stark_logs.txt")
SPOTIFY_CACHE = os.path.join(PROJECT_ROOT, ".spotify_cache")
PICOVOICE_MODEL = os.path.join(PROJECT_ROOT, "picovoice_model", "Friday_en_windows_v4_0_0.ppn")
SOVEREIGN_STATE = os.path.join(PROJECT_ROOT, "sovereign_state.json")
FRIDAY_ICO = os.path.join(PROJECT_ROOT, "friday.ico")
