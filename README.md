# Neolink.NET ONVIF PTZ bridge

> **Native support is now available.** Neolink.NET [v1.1.0](https://github.com/borexola/neolink.net/releases/tag/v1.1.0) includes opt-in ONVIF PTZ for Frigate. Enable it under **Cameras → Edit → External connection** in Neolink.NET. New installations should use that built-in feature; this standalone bridge remains available for older Neolink.NET versions and as a reference implementation.

Exposes the manual pan/tilt controls of a Reolink camera served by Neolink.NET
to Frigate as a minimal ONVIF device. Video stays on its existing RTSP route.
Zoom, presets, click-to-move, and autotracking are deliberately not advertised.

The ONVIF response builders in `bridge/responses.py` are adapted from
[reolink-enhanced-onvif-proxy](https://github.com/rgregg/reolink-enhanced-onvif-proxy),
which declares the MIT license. Neolink.NET's HTTP API contract was verified
against its v1.0.9 source.

Requirements: a camera already configured in Neolink.NET, Frigate with its
existing video stream, and a deployment where Frigate and this bridge can reach
each other. The example below assumes Frigate and Neolink.NET use host networking
on the same machine. Change `NEOLINK_URL` and the Frigate `host` value for a
different layout.

Start the bridge:

```sh
CAMERA_NAME=your_camera docker compose up -d --build
```

Then add to the matching Frigate camera in Frigate's configuration and reload
Frigate:

```yaml
onvif:
  host: 127.0.0.1
  port: 8765
  user: ""
  password: ""
```

The server binds to loopback by default and has no authentication. Keep it
loopback-only, or add authentication before listening on a network interface.
The Neolink.NET control API must also be restricted to trusted hosts.

The bridge translates ONVIF `ContinuousMove` to the dominant pan or tilt axis
and `Stop` to Neolink's stop command. A 10-second timeout stops an orphaned
movement if a browser disconnects before sending `Stop`.

To run the no-camera translation check, install the dependencies from the
`Dockerfile` and run `python test_bridge.py`. This project currently targets
Frigate's ONVIF PTZ client; it is not a general ONVIF implementation.

On a first-generation Reolink E1, Neolink.NET v1.0.9 and Frigate's ONVIF
client recognized the bridge as `features: ['pt']`. The four native controls
appeared in Frigate, and a user confirmed physical movement. Video continued
through the existing Neolink.NET RTSP stream.
