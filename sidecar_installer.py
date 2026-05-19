"""Installer for Friday sidecar client.

Usage: python sidecar_installer.py --token "eyJ..."
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import jwt


def install(token: str, force: bool = False):
    # decode without verifying to extract brain_url and capabilities
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
    except Exception as e:
        raise RuntimeError(f"Invalid token: {e}")

    cfg_dir = Path.home() / ".friday-sidecar"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg = {
        "brain_url": payload.get("brain_url"),
        "token": token,
        "device_name": payload.get("device_name"),
        "device_id": payload.get("device_id"),
        "capabilities": payload.get("capabilities", []),
    }
    cfg_path = cfg_dir / "config.yaml"
    # use JSON for simplicity
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(f"Wrote config to {cfg_path}")
    print("To run the sidecar: python sidecar_client.py --config {cfg_path}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--token", required=True)
    args = p.parse_args()
    install(args.token)


if __name__ == "__main__":
    main()
