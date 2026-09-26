# CHANDRADEV — Original DJI Osmo Action Live Camera Bridge

## Purpose

CHANDRADEV is KRISHNA's live-camera ingest specialist. For the original DJI Osmo Action, USB is treated as file-transfer/storage, not a webcam input. Live video uses the camera's supported DJI Mimo livestream path:

    DJI Osmo Action
      -> Wi-Fi
    DJI Mimo on phone
      -> RTMP
    MediaMTX on KRISHNA PC
      -> local RTMP/HLS/WebRTC
    CHANDRADEV frame sampler
      -> local fast VisionAdapter
    HAWKEYE evidence coordinator
      -> KRISHNA

No paid streaming service is required.

## Original Osmo Action hardware facts used by KRISHNA

- 1/2.3-inch CMOS, 12 MP; 145-degree FOV, f/2.8.
- Up to 4K/60 recording, 100 Mbps H.264 video and 48 kHz AAC audio.
- Two built-in microphones; external microphone via USB-C with a compatible 3.5 mm adapter.
- Wi-Fi 802.11a/b/g/n/ac on 2.4/5.8 GHz and BLE 4.2.
- microSD up to 256 GB; 1300 mAh battery.
- DJI Mimo RTMP live streaming at 480p or 720p, 30 fps.
- Original Osmo Action is not in DJI's current UVC webcam support list.
- DJI states Osmo series has no HDMI/USB-C-to-HDMI output.

## Install

Run scripts\INSTALL_CHANDRADEV_RTMP.ps1. MediaMTX installs under E:\Krishna-The GOD\tools\mediamtx.
Run scripts\INSTALL_CHANDRADEV_VISION.ps1 for local OpenCV frame extraction in KRISHNA's existing venv.

## First live test

1. Disconnect the Osmo USB file-transfer session.
2. Put the phone and KRISHNA PC on the same trusted Wi-Fi.
3. Connect Osmo Action to DJI Mimo.
4. Run scripts\START_CHANDRADEV_OSMO.ps1.
5. Copy the displayed RTMP URL into DJI Mimo -> Live Stream -> RTMP.
6. Start with 720p / 30fps / 2 Mbps; increase to 4 Mbps only if stable.
7. CHANDRADEV reads sampled local frames and can hand analysis to HAWKEYE.

## Security and privacy

- TCP 1935 should be Private-profile + LocalSubnet only.
- HLS/WebRTC preview bind to localhost.
- Generated non-default stream path; publisher replacement disabled.
- Raw frames stay local; VisionAdapter has no automatic cloud fallback.
- Camera evidence is observation, not proof of hidden intent, identity, diagnosis or fault.

## Hardware roadmap

Useful now: Wi-Fi RTMP, microSD local evidence, USB-C file transfer/charging/external mic, two built-in microphones, wide-angle lens, camera mounts.

Useful later: compatible 3.5 mm adapter plus directional/lavalier mic; continuous power with thermal monitoring; multiple named camera views; a newer UVC-capable Osmo can become a direct USB lane while this original camera remains the wireless field camera.

Not useful for this original model: USB-C-to-HDMI and attempts to force a UVC webcam mode.
