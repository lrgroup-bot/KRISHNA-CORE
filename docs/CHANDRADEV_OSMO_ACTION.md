# CHANDRADEV — Original DJI Osmo Action on the KRISHNA PC

## Architecture

CHANDRADEV runs on the KRISHNA PC. The DJI Osmo Action is a direct camera source for CHANDRADEV.

There is no Hawkeye dependency in this path.

    DJI Osmo Action (original)
      -> Wi-Fi
    DJI Mimo
      -> RTMP
    MediaMTX on KRISHNA PC
      -> local RTMP
    CHANDRADEV camera adapter
      -> local VisionAdapter
    CHANDRADEV observation ledger
      -> KRISHNA

USB remains a separate file-transfer/presence path.

## Original Osmo Action hardware profile used by CHANDRADEV

- 1/2.3-inch CMOS, 12 MP.
- 145-degree field of view, f/2.8.
- Recorded video up to 4K/60 and 1080p/240.
- Up to 100 Mbps H.264 recorded video.
- 48 kHz AAC audio.
- Two built-in microphones.
- Compatible external microphone through USB-C/3.5 mm adapter.
- Wi-Fi 802.11a/b/g/n/ac on 2.4 GHz and 5.8 GHz.
- BLE 4.2.
- microSD up to 256 GB.
- 1300 mAh battery.
- Waterproof to 11 m without a case and 60 m with the waterproof case.
- DJI documented 1.5 m drop testing and operation down to -10 C.
- DJI Mimo RTMP live streaming on this original model is limited to 480p or 720p at 30 fps; CHANDRADEV therefore uses 720p/30 at 4 Mbps for maximum live quality, with 2 Mbps as the first fallback.
- USB on this camera is file-transfer/storage, not the live camera path.
- Do not rely on USB-C-to-HDMI for this model.

## CHANDRADEV responsibilities

CHANDRADEV owns:

- Osmo USB presence detection on Windows.
- Local RTMP receiver configuration.
- Local RTMP server start/stop.
- Exact Mimo stream URL generation.
- Local JPEG frame capture.
- PC-local vision analysis.
- Local camera observation history.
- Final visual/QC reasoning through the existing ChandradevQC runtime.

CHANDRADEV does not call, create a session in, or store observations in Hawkeye.

## Install

From the KRISHNA repository:

    .\scripts\INSTALL_CHANDRADEV_RTMP.ps1

This installs MediaMTX under:

    E:\Krishna-The GOD\tools\mediamtx

Then:

    .\scripts\INSTALL_CHANDRADEV_VISION.ps1

This installs OpenCV into KRISHNA's existing virtual environment only. The installer refuses a global fallback.

## Start the receiver

Run in PowerShell:

    .\scripts\START_CHANDRADEV_OSMO.ps1

It prints the exact RTMP URL to enter in DJI Mimo.

Keep that PowerShell window open.

## Immediate DJI test

Open a second PowerShell window and run:

    .\scripts\TEST_CHANDRADEV_OSMO.ps1

The test performs five checks:

1. Detects the connected DJI/OSMO USB device.
2. Verifies MediaMTX is installed.
3. Verifies TCP 1935 is listening.
4. Verifies KRISHNA Python + OpenCV.
5. Attempts to capture one real frame from the DJI RTMP stream.

A successful test writes a JPEG under:

    E:\Krishna-The GOD\state\chandradev\test

## Current CHANDRADEV action surface

- chandradev.status
- chandradev.qc
- chandradev.debate.resolve
- chandradev.camera.osmo.profile
- chandradev.camera.osmo.guide
- chandradev.camera.receiver.config
- chandradev.camera.receiver.start
- chandradev.camera.receiver.stop
- chandradev.camera.frame.capture
- chandradev.camera.frame.analyze
- chandradev.camera.observations

There is no chandradev.camera.session.start action because CHANDRADEV is not using Hawkeye sessions.

## Privacy and network boundaries

- Raw sampled frames stay on the PC.
- VisionAdapter is local-only and has no automatic cloud fallback.
- RTMP TCP 1935 is intended for Windows Private profile + LocalSubnet only.
- HLS/WebRTC helper listeners bind to localhost.
- Starting/stopping the LAN listener remains an owner-approved action.
- Camera observations are evidence; they do not establish hidden intent, identity, diagnosis, or fault certainty.
