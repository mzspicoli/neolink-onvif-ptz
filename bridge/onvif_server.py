"""Small ONVIF PTZ facade for Neolink.NET's Baichuan control API."""

import asyncio
import logging
from xml.etree import ElementTree as ET

from aiohttp import ClientSession, ClientTimeout, web

from . import responses

LOG = logging.getLogger(__name__)
SOAP = "http://www.w3.org/2003/05/soap-envelope"
TT = "http://www.onvif.org/ver10/schema"


class Bridge:
    def __init__(self, neolink_url: str, camera: str, timeout: float = 10):
        self.url = neolink_url.rstrip("/") + f"/api/cameras/{camera}/ptz"
        self.camera = camera
        self.timeout = timeout
        self.session: ClientSession | None = None
        self.stop_task: asyncio.Task | None = None
        self.moving = False
        self.lock = asyncio.Lock()

    async def start(self):
        self.session = ClientSession(timeout=ClientTimeout(total=3))

    async def close(self):
        if self.stop_task:
            self.stop_task.cancel()
        if self.moving:
            await self.command("stop")
        await self.session.close()

    async def command(self, command: str, speed: float = 32):
        async with self.lock:
            async with self.session.post(self.url, json={"command": command, "speed": speed}) as reply:
                data = await reply.json()
                if reply.status != 200 or data.get("ok") is not True:
                    raise RuntimeError(f"Neolink PTZ returned HTTP {reply.status}")
            self.moving = command != "stop"

    async def move(self, pan: float, tilt: float):
        # Frigate sends ContinuousMove on press and Stop on release.
        # The E1 only has one axis at a time; choose the dominant axis.
        if abs(pan) < 0.05 and abs(tilt) < 0.05:
            await self.stop()
            return
        command = ("right" if pan > 0 else "left") if abs(pan) >= abs(tilt) else ("up" if tilt > 0 else "down")
        speed = max(1, min(64, round(max(abs(pan), abs(tilt)) * 64)))
        await self.command(command, speed)
        if self.stop_task:
            self.stop_task.cancel()
        self.stop_task = asyncio.create_task(self._safety_stop())

    async def _safety_stop(self):
        try:
            await asyncio.sleep(self.timeout)
            LOG.warning("PTZ stop timeout for %s", self.camera)
            await self.command("stop")
        except asyncio.CancelledError:
            pass

    async def stop(self):
        if self.stop_task:
            self.stop_task.cancel()
            self.stop_task = None
        await self.command("stop")


def create_app(bridge: Bridge) -> web.Application:
    app = web.Application(client_max_size=64 * 1024)

    async def soap(request: web.Request):
        try:
            root = ET.fromstring(await request.read())
            body = root.find(f"{{{SOAP}}}Body")
            if body is None or len(body) != 1:
                raise ValueError("Invalid SOAP body")
            action = body[0].tag.rsplit("}", 1)[-1]
            base = f"http://{request.host}"
            static = {
                "GetSystemDateAndTime": responses.get_system_date_and_time,
                "GetDeviceInformation": responses.get_device_information,
                "GetProfiles": responses.get_profiles,
                "GetVideoSources": responses.get_video_sources,
                "GetConfigurationOptions": responses.get_configuration_options,
                "GetServiceCapabilities": responses.get_service_capabilities,
                "GetNodes": responses.get_nodes,
            }
            if action == "GetCapabilities":
                result = responses.get_capabilities(base)
            elif action == "GetServices":
                result = responses.get_services(base)
            elif action in static:
                result = static[action]()
            elif action == "GetPresets":
                result = responses.get_presets([])
            elif action == "GetStatus":
                result = responses.get_status(0, 0, 0, 1, "MOVING" if bridge.moving else "IDLE")
            elif action == "ContinuousMove":
                velocity = body[0].find(f".//{{{TT}}}PanTilt")
                if velocity is None:
                    raise ValueError("PanTilt velocity required")
                await bridge.move(float(velocity.get("x", 0)), float(velocity.get("y", 0)))
                result = responses.simple_response("tptz", action)
            elif action == "Stop":
                await bridge.stop()
                result = responses.simple_response("tptz", action)
            else:
                result = responses.fault_action_not_supported(action)
            return web.Response(body=result, content_type="application/soap+xml")
        except Exception as exc:
            LOG.exception("ONVIF request failed")
            return web.Response(body=responses.fault_device_error(str(exc)), status=500, content_type="application/soap+xml")

    for path in ("/", "/onvif/device_service", "/onvif/media_service", "/onvif/ptz_service"):
        app.router.add_post(path, soap)
    app.router.add_get("/health", lambda _: web.json_response({"ok": True}))
    return app
