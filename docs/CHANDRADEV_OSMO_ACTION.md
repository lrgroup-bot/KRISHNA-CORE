# CHANDRADEV — Original DJI Osmo Action Camera Adapter

## Canonical role

CHANDRADEV already exists in KRISHNA as the independent external live-camera final-QC peer. This module does **not** create another Chandradev. It adds an Osmo Action camera transport/input adapter beneath the existing CHANDRADEV/Hawkeye pipeline.

Architecture:

    DJI Osmo Action (original)
      -> Wi-Fi
    DJI Mimo on phone
      -> RTMP
    Local MediaMTX receiver
      -> local RTMP/HLS/WebRTC
    chandradev_camera adapter
      -> local fast VisionAdapter
    HAWKEYE live evidence
      -> existing CHANDRADEV QC / KRISHNA

No paid streaming service is required.

## Original Osmo Action hardware facts used by KRISHNA

- 1/2.3-inch CMOS, 12 MP.
- 145-degree field of view, f/2.8.
- Up to 4K/60 recorded video and 1080p/240 slow motion.
- Up to 100 Mbps H.264 recorded video; 48 kHz AAC audio.
- Two built-in microphones.
- External microphone support through USB-C with a compatible 3.5 mm adapter.
- Wi-Fi 802.11a/b/g/n/ac on 2.4 GHz and 5.8 GHz.
- BLE 4.2.
- microSD up to 256 GB.
- 1300 mAh battery.
- Waterproof to 11 m without a case and 60 m with the waterproof case.
- DJI documented 1.5 m drop testing and operation down to -10 C.
- DJI Mimo RTMP live streaming at 480p or 720p, 30 fps.
- The original Osmo Action is not on DJI's current UVC webcam support list.
- DJI states Osmo series does not provide HDMI/USB-C-to-HDMI output.

## How KRISHNA uses each hardware path

### Wi-Fi — primary live lane

DJI Mimo originates the supported RTMP stream. Start at 720p/30fps/2 Mbps. Increase to 4 Mbps only if the local Wi-Fi is stable. If unstable, fall back to 480p/1 Mbps.

### USB-C — presence, charging, file/evidence lane

On this original camera the Windows connection presents as USB mass storage/file transfer, not live UVC video. The adapter includes a read-only Windows PnP probe so KRISHNA can recognize the connected DJI/OSMO storage device. USB can also support the compatible 3.5 mm microphone adapter.

### microSD — high-quality evidence lane

The RTMP feed is optimized for live observation. microSD recordings can preserve the higher-quality source for later local HAWKEYE review.

### Audio

The two built-in microphones can provide environmental audio in the stream/recording. A compatible external microphone can later improve speech or machine/acoustic evidence. Audio transcription/diagnostic extraction is a separate bounded pipeline; the first adapter implementation samples video frames.

### Rugged field use

The camera's 145-degree FOV, waterproofing, impact resistance and small mounting footprint make it suitable for fixed workshop views, vehicle/field observation, mobile inspection and outdoor Chandradev/Hawkeye work.

## Installation

Run:

    .\scripts\INSTALL_CHANDRADEV_RTMP.ps1

MediaMTX is downloaded from the official bluenviron/mediamtx GitHub release and placed under:

    E:\Krishna-The GOD\tools\mediamtx

The script attempts to create a Windows firewall rule for TCP 1935 limited to the Private profile and LocalSubnet.

For local frame sampling:

    .\scripts\INSTALL_CHANDRADEV_VISION.ps1

OpenCV is installed only into KRISHNA's existing virtual environment and pip cache stays on E:. The installer refuses a global fallback.

## First live test

1. Disconnect the Osmo USB file-transfer session for live use.
2. Put the phone and KRISHNA PC on the same trusted Wi-Fi.
3. Connect the Osmo Action to DJI Mimo.
4. Run:

    .\scripts\START_CHANDRADEV_OSMO.ps1

5. Copy the displayed RTMP URL.
6. DJI Mimo -> Live Stream -> RTMP.
7. Paste the URL.
8. Select 720p / 30 fps / 2 Mbps.
9. Start livestreaming.
10. Use the CHANDRADEV camera actions to create a Hawkeye session, capture a frame or run fast local visual analysis.

## Action surface

- chandradev.status — existing canonical CHANDRADEV status, now also includes camera adapter status.
- chandradev.qc — unchanged canonical final-QC action.
- chandradev.debate.resolve — unchanged canonical CHANDRADEV/BRAHMA debate action.
- chandradev.camera.osmo.profile
- chandradev.camera.osmo.guide
- chandradev.camera.receiver.config
- chandradev.camera.receiver.start
- chandradev.camera.receiver.stop
- chandradev.camera.session.start
- chandradev.camera.frame.capture
- chandradev.camera.frame.analyze

## Security and privacy

- RTMP port 1935 is intended only for the trusted Private LAN/local subnet.
- Local HLS and WebRTC preview endpoints bind to 127.0.0.1.
- A non-default generated stream path is persisted locally.
- Publisher replacement is disabled.
- Raw sampled frames remain local.
- Fast VisionAdapter analysis is local-only and has no automatic cloud fallback.
- Camera evidence is observable evidence only; it does not prove identity, hidden intent, mental state, diagnosis or hardware-fault certainty.
- Starting/stopping the LAN receiver is an owner-approved action.

## Hardware roadmap

Useful immediately: Wi-Fi RTMP, wide-angle live video, microSD high-quality evidence, built-in microphones, USB storage transfer, rugged mounts and field use.

Useful later: compatible external microphone; multi-camera named views; optional audio extraction; recorded-video sync from USB/microSD; a newer UVC-capable Osmo as a direct USB live lane while this original camera remains a wireless RTMP field camera.

Do not buy a USB-C-to-HDMI adapter for this camera path. DJI states Osmo series does not support HDMI output.
