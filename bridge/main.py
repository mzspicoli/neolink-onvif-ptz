"""Run the loopback-only ONVIF facade."""

import asyncio
import logging
import os
import signal

from aiohttp import web

from .onvif_server import Bridge, create_app


async def main():
    logging.basicConfig(level=logging.INFO)
    bridge = Bridge(
        os.getenv("NEOLINK_URL", "http://127.0.0.1:8655"),
        os.environ["CAMERA_NAME"],
        float(os.getenv("SAFETY_STOP_SECONDS", "10")),
    )
    await bridge.start()
    app = create_app(bridge)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, os.getenv("LISTEN_HOST", "127.0.0.1"), int(os.getenv("LISTEN_PORT", "8765")))
    await site.start()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    try:
        await stop.wait()
    finally:
        await bridge.close()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
