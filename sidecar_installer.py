"""Installer for Friday sidecar client.

Usage: python sidecar_installer.py --token "eyJ..."
"""
from __future__ import annotations

import argparse
import subprocess
import sys
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
    yaml_lines = [
        f"brain_url: {cfg['brain_url']}",
        f"token: {cfg['token']}",
        f"device_name: {cfg['device_name']}",
        f"device_id: {cfg['device_id']}",
        "capabilities:",
    ]
    for item in cfg["capabilities"]:
        yaml_lines.append(f"  - {item}")
    cfg_path.write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

    deps = ["websockets", "pyjwt", "psutil", "Pillow"]
    subprocess.run([sys.executable, "-m", "pip", "install", *deps], check=False)

    print(f"Wrote config to {cfg_path}")
    print(f"To run the sidecar: python sidecar_client.py --config {cfg_path}")


def install_service_windows(config_path: Path):
    task_name = "FridaySidecar"
    cmd = f'{sys.executable} "{Path.cwd() / "sidecar_client.py"}" --config "{config_path}"'
    subprocess.run(
        [
            "schtasks",
            "/Create",
            "/SC",
            "ONLOGON",
            "/TN",
            task_name,
            "/TR",
            cmd,
            "/F",
        ],
        check=False,
    )


def install_service_linux(config_path: Path):
    unit_path = Path.home() / ".config" / "systemd" / "user" / "friday-sidecar.service"
    unit_path.parent.mkdir(parents=True, exist_ok=True)
    content = """[Unit]
Description=Friday Sidecar

[Service]
ExecStart={python} {script} --config {config}
Restart=always

[Install]
WantedBy=default.target
""".format(
        python=sys.executable,
        script=str(Path.cwd() / "sidecar_client.py"),
        config=str(config_path),
    )
    unit_path.write_text(content, encoding="utf-8")
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    subprocess.run(["systemctl", "--user", "enable", "--now", "friday-sidecar"], check=False)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--token", required=True)
    p.add_argument("--install-service", action="store_true")
    args = p.parse_args()
    install(args.token)
    cfg_path = Path.home() / ".friday-sidecar" / "config.yaml"
    if args.install_service:
        if sys.platform.startswith("win"):
            install_service_windows(cfg_path)
        elif sys.platform.startswith("linux"):
            install_service_linux(cfg_path)


if __name__ == "__main__":
    main()
