"""
Smart Home & IoT tools
Libraries: paho-mqtt, pychromecast, python-miio, zeroconf, aioice, home-assistant
"""
import asyncio
import json
import os
import socket
from typing import Any

# ── MQTT (paho-mqtt) ──
HAS_MQTT = False
try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ImportError:
    pass


async def mqtt_publish(broker: str, topic: str, message: str, port: int = 1883) -> dict[str, Any]:
    if not HAS_MQTT:
        return {"error": "paho-mqtt not installed"}
    try:
        def _pub():
            client = mqtt.Client()
            client.connect(broker, port, 60)
            client.publish(topic, message)
            client.disconnect()
        await asyncio.get_event_loop().run_in_executor(None, _pub)
        return {"broker": broker, "topic": topic, "message": message}
    except Exception as e:
        return {"error": str(e)}


async def mqtt_subscribe(broker: str, topic: str, timeout: int = 5, port: int = 1883) -> dict[str, Any]:
    if not HAS_MQTT:
        return {"error": "paho-mqtt not installed"}
    messages = []
    def on_message(client, userdata, msg):
        messages.append({"topic": msg.topic, "payload": msg.payload.decode()})
    try:
        def _sub():
            client = mqtt.Client()
            client.on_message = on_message
            client.connect(broker, port, 60)
            client.subscribe(topic)
            for _ in range(timeout):
                client.loop(timeout=1)
                if messages:
                    break
            client.disconnect()
        await asyncio.get_event_loop().run_in_executor(None, _sub)
        return {"broker": broker, "topic": topic, "messages": messages}
    except Exception as e:
        return {"error": str(e)}


# ── mDNS / Zeroconf ──
HAS_ZEROCONF = False
try:
    from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange
    HAS_ZEROCONF = True
except ImportError:
    pass


async def zeroconf_discover(service_type: str = "_http._tcp.local.", timeout: int = 5) -> dict[str, Any]:
    if not HAS_ZEROCONF:
        return {"error": "zeroconf not installed"}
    services = []
    def on_change(zeroconf, service_type, name, state_change):
        if state_change == ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
            if info:
                services.append({"name": name, "host": str(info.server), "address": ".".join(map(str, info.addresses[0])) if info.addresses else None,
                                "port": info.port, "properties": {k.decode(): v.decode() if isinstance(v, bytes) else v for k, v in info.properties.items()}})
    try:
        zeroconf = Zeroconf()
        browser = ServiceBrowser(zeroconf, service_type, handlers=[on_change])
        await asyncio.sleep(timeout)
        zeroconf.close()
        return {"service_type": service_type, "services": services, "count": len(services)}
    except Exception as e:
        return {"error": str(e)}


# ── Chromecast (pychromecast) ──
HAS_CHROMECAST = False
try:
    import pychromecast
    HAS_CHROMECAST = True
except ImportError:
    pass


async def chromecast_discover(timeout: int = 5) -> dict[str, Any]:
    if not HAS_CHROMECAST:
        return {"error": "pychromecast not installed"}
    try:
        casts = await asyncio.get_event_loop().run_in_executor(None, lambda: pychromecast.get_chromecasts(timeout=timeout))
        return {"devices": [{"name": c.name, "host": c.host, "port": c.port, "cast_type": c.cast_type,
                            "status": c.status.display_name if c.status else None} for c in casts],
                "count": len(casts)}
    except Exception as e:
        return {"error": str(e)}


async def chromecast_play(url: str, device_name: str | None = None) -> dict[str, Any]:
    if not HAS_CHROMECAST:
        return {"error": "pychromecast not installed"}
    try:
        casts = await asyncio.get_event_loop().run_in_executor(None, lambda: pychromecast.get_chromecast(timeout=5))
        cast = None
        if device_name:
            cast = next((c for c in casts if c.name.lower() == device_name.lower()), None)
            if not cast:
                return {"error": f"Chromecast '{device_name}' not found"}
        cast = cast or casts[0]
        mc = cast.media_controller
        await asyncio.get_event_loop().run_in_executor(None, lambda: mc.play_media(url, "video/mp4"))
        await asyncio.get_event_loop().run_in_executor(None, lambda: mc.block_until_active())
        return {"device": cast.name, "playing": url}
    except Exception as e:
        return {"error": str(e)}


# ── Xiaomi (python-miio) ──
HAS_MIIO = False
try:
    import miio
    HAS_MIIO = True
except ImportError:
    pass


async def miio_discover(timeout: int = 5) -> dict[str, Any]:
    if not HAS_MIIO:
        return {"error": "python-miio not installed"}
    try:
        devices = await asyncio.get_event_loop().run_in_executor(None, lambda: miio.device.Discovery.discover(timeout=timeout))
        return {"devices": [{"ip": d.ip, "token": d.token, "model": d.model} for d in devices], "count": len(devices)}
    except Exception as e:
        return {"error": str(e)}


# ── Home Assistant ──
async def hass_get_state(entity_id: str) -> dict[str, Any]:
    url = os.environ.get("HASS_URL")
    token = os.environ.get("HASS_TOKEN")
    if not url or not token:
        return {"error": "HASS_URL and HASS_TOKEN env vars required"}
    try:
        import requests
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        r = await asyncio.get_event_loop().run_in_executor(
            None, lambda: requests.get(f"{url}/api/states/{entity_id}", headers=headers, timeout=10))
        data = r.json()
        return {"entity": entity_id, "state": data.get("state"), "attributes": data.get("attributes", {}),
                "last_changed": data.get("last_changed")}
    except Exception as e:
        return {"error": str(e)}


async def hass_call_service(domain: str, service: str, entity_id: str) -> dict[str, Any]:
    url = os.environ.get("HASS_URL")
    token = os.environ.get("HASS_TOKEN")
    if not url or not token:
        return {"error": "HASS_URL and HASS_TOKEN env vars required"}
    try:
        import requests
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        r = await asyncio.get_event_loop().run_in_executor(
            None, lambda: requests.post(f"{url}/api/services/{domain}/{service}",
                                         json={"entity_id": entity_id}, headers=headers, timeout=10))
        return {"domain": domain, "service": service, "entity": entity_id, "status": r.status_code}
    except Exception as e:
        return {"error": str(e)}


# ── WebRTC ICE (aioice) ──
HAS_AIOICE = False
try:
    import aioice
    HAS_AIOICE = True
except ImportError:
    pass


async def ice_gather_candidates(stun_server: str = "stun.l.google.com", stun_port: int = 19302) -> dict[str, Any]:
    if not HAS_AIOICE:
        return {"error": "aioice not installed"}
    try:
        connection = aioice.Connection()
        await connection.gather_candidates(stun_server=(stun_server, stun_port))
        candidates = [str(c) for c in connection.local_candidates]
        await connection.close()
        return {"candidates": candidates, "count": len(candidates)}
    except Exception as e:
        return {"error": str(e)}
