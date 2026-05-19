"""Friday Sidecar package — JWT-authenticated WebSocket network + legacy sidecar_tool."""

from friday.sidecar.brain_ws_server import router, send_command
from friday.sidecar.device_registry import DeviceRegistry, DeviceRecord, SidecarCommand, get_registry
from friday.sidecar.token_generator import generate_token

# Legacy sidecar_tool API re-exports (from friday/sidecar_legacy.py)
from friday.sidecar_legacy import (
    register_sidecar,
    heartbeat_sidecar,
    list_sidecars,
    sidecar_status,
    dispatch_sidecar_command,
    sidecar_tool,
    SIDECAR_TYPES,
)

__all__ = [
    "router", "send_command",
    "DeviceRegistry", "DeviceRecord", "SidecarCommand", "get_registry",
    "generate_token",
    "register_sidecar", "heartbeat_sidecar", "list_sidecars",
    "sidecar_status", "dispatch_sidecar_command", "sidecar_tool",
    "SIDECAR_TYPES",
]
