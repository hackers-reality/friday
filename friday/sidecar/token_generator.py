"""Generate JWT tokens for Friday sidecars.

Usage:
  python -m friday.sidecar.token_generator --device-name "Dell-Laptop" --capabilities terminal,filesystem
"""
from __future__ import annotations

import argparse
import uuid
import time
from datetime import datetime, timedelta

import jwt

from friday.orchestration_config import ensure_config, save_config


def _ensure_secret(cfg: dict) -> str:
    secret = cfg.get("SECRET_KEY") or cfg.get("sidecar", {}).get("secret_key")
    if not secret:
        # generate and persist
        secret = uuid.uuid4().hex + uuid.uuid4().hex
        cfg["SECRET_KEY"] = secret
        cfg.setdefault("sidecar", {})["secret_key"] = secret
        save_config(cfg)
    return secret


def generate_token(device_name: str, capabilities: list[str], brain_url: str, expires_days: int | None = None) -> str:
    cfg = ensure_config()
    secret = _ensure_secret(cfg)

    payload = {
        "device_name": device_name,
        "device_id": str(uuid.uuid4()),
        "capabilities": capabilities,
        "issued_at": int(time.time()),
        "brain_url": brain_url,
    }
    if expires_days:
        payload["exp"] = int((datetime.utcnow() + timedelta(days=expires_days)).timestamp())

    token = jwt.encode(payload, secret, algorithm="HS256")
    # PyJWT may return bytes in older versions
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def main():
    p = argparse.ArgumentParser(description="Generate a JWT token for a Friday sidecar")
    p.add_argument("--device-name", required=True)
    p.add_argument("--capabilities", default="terminal,filesystem,screenshot,system_info")
    cfg = ensure_config()
    default_brain_url = str(cfg.get("sidecar", {}).get("brain_url", "ws://192.168.1.76:3142/sidecar"))
    p.add_argument("--brain-url", default=default_brain_url)
    p.add_argument("--expires-days", type=int, default=None)
    args = p.parse_args()

    caps = [c.strip() for c in args.capabilities.split(",") if c.strip()]
    token = generate_token(args.device_name, caps, args.brain_url, expires_days=args.expires_days)
    print(token)


if __name__ == "__main__":
    main()
