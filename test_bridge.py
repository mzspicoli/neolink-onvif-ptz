"""No-camera test of SOAP movement translation and Stop."""

import asyncio

from aiohttp.test_utils import TestClient, TestServer

from bridge.onvif_server import Bridge, create_app

SOAP = """<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
 xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl"
 xmlns:tt="http://www.onvif.org/ver10/schema">
 <s:Body><tptz:{action}><tptz:ProfileToken>000</tptz:ProfileToken>{payload}</tptz:{action}></s:Body>
 </s:Envelope>"""


async def main():
    bridge = Bridge("http://127.0.0.1:1", "fake")
    sent = []

    async def fake_command(command, speed=32):
        sent.append((command, speed))
        bridge.moving = command != "stop"

    bridge.command = fake_command
    async with TestClient(TestServer(create_app(bridge))) as client:
        move = SOAP.format(
            action="ContinuousMove",
            payload='<tptz:Velocity><tt:PanTilt x="0.5" y="0"/></tptz:Velocity>',
        )
        response = await client.post("/onvif/ptz_service", data=move)
        assert response.status == 200, await response.text()
        stop = SOAP.format(action="Stop", payload="")
        response = await client.post("/onvif/ptz_service", data=stop)
        assert response.status == 200, await response.text()
    assert sent == [("right", 32), ("stop", 32)], sent
    print("SOAP ContinuousMove -> Neolink right; SOAP Stop -> Neolink stop")


asyncio.run(main())
