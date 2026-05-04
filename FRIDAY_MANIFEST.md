# FRIDAY Architecture Manifest

## Root Directory (`/open-interpreter/`)
* `FRIDAY_MANIFEST.md`: This file. The architectural map. Do not delete.
* `friday.py`: The main entry point and permanent memory wrapper (ChromaDB).
* `interpreter/`: The core Open Interpreter module. 

## Core Configurations
* `interpreter/terminal_interface/profiles/defaults/default.yaml`: The primary configuration file containing Friday's system prompt, execution rules, and API keys.


## Rules for Self-Modification
1. Always read this manifest before making changes to `.py` or `.yaml` files.
2. Do not delete core routing files in `interpreter/core/`.
3. If writing new custom skills (like Spotify or Alexa), create them as separate Python scripts in the root directory and import them into `friday.py`, rather than injecting them directly into the core Open Interpreter files.