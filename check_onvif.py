"""Read-only ONVIF discovery using Frigate's own client library."""

import asyncio
from importlib.util import find_spec
from pathlib import Path

from onvif import ONVIFCamera


async def main():
    cam = ONVIFCamera(
        "127.0.0.1",
        8765,
        "",
        "",
        wsdl_dir=str(Path(find_spec("onvif").origin).parent / "wsdl"),
    )
    await cam.update_xaddrs()
    media = await cam.create_media_service()
    profiles = await media.GetProfiles()
    ptz = await cam.create_ptz_service()
    options = await ptz.GetConfigurationOptions(
        {"ConfigurationToken": profiles[0].PTZConfiguration.token}
    )
    print("profiles:", [(p.token, p.PTZConfiguration.token) for p in profiles])
    print(
        "continuous pan/tilt:",
        len(options.Spaces.ContinuousPanTiltVelocitySpace),
    )
    print("relative pan/tilt:", len(options.Spaces.RelativePanTiltTranslationSpace))


asyncio.run(main())
