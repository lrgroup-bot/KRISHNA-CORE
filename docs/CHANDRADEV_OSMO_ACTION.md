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

## Future dedicated USB webcam — prepared but inactive

The planned permanent monitor camera is **ZEBRONICS ZEB-Pure Plus**.

Target hardware profile:

- 3840x2160 / 4K at 30 FPS.
- Autofocus.
- Built-in microphone.
- USB webcam transport.
- Tripod support.
- Dedicated physical placement in front of the monitor, pointing back toward the display.
- Low-cost manual desk mount target around ₹500; an expensive arm is not required by design.

The runtime deliberately does **not** auto-select the future webcam before physical installation. The current validation source remains:

    DJI Osmo Action -> DJI Mimo -> RTMP -> CHANDRADEV

The future webcam plan is exposed through:

- `chandradev.camera.webcam.profile`
- `chandradev.camera.selection`

This prevents KRISHNA from accidentally binding a laptop camera or another USB camera while the intended webcam is not yet installed.

## Budget mount and owner alignment handoff

CHANDRADEV is designed to tolerate a low-cost manual mount.

During each screen-focus burst it compares detected monitor corners across frames. If the monitor cannot be found, or the camera/mount is moving enough that OCR would be unreliable, CHANDRADEV:

1. stops the unreliable screen read,
2. clears the stale monitor lock,
3. records a structured alignment handoff routed through KRISHNA,
4. asks the owner to stabilize or reposition the camera,
5. re-detects the full monitor on the next focus attempt,
6. perspective-corrects and sharpens the screen,
7. creates a new persistent monitor lock,
8. clears the pending handoff after a stable successful focus.

The owner only needs to make the complete monitor visible, keep all four edges in frame and physically stabilize the camera. CHANDRADEV then handles the software correction and screen reading.

Alignment status is exposed through:

- `chandradev.camera.screen.alignment`

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
- chandradev.camera.webcam.profile
- chandradev.camera.selection
- chandradev.camera.receiver.config
- chandradev.camera.receiver.start
- chandradev.camera.receiver.stop
- chandradev.camera.frame.capture
- chandradev.camera.frame.analyze
- chandradev.camera.screen.focus
- chandradev.camera.screen.analyze
- chandradev.camera.screen.unlock
- chandradev.camera.screen.alignment
- chandradev.camera.observations

There is no chandradev.camera.session.start action because CHANDRADEV is not using Hawkeye sessions.

## Automatic Screen Focus Mode

CHANDRADEV now has software screen auto-focus for a monitor viewed through the Osmo stream. It does not modify DJI firmware or attempt to move the camera lens.

Pipeline:

    live Osmo frame burst
      -> detect monitor quadrilateral
      -> score candidate by size/rectangularity/position/aspect
      -> perspective-correct the four corners
      -> select the sharpest corrected screen from the burst
      -> persist normalized screen-corner lock
      -> upscale toward 1920 px width
      -> local contrast enhancement
      -> unsharp mask
      -> detailed local VisionAdapter screen reading
      -> CHANDRADEV observation ledger

If one later frame has glare or weak edges, the saved normalized four-corner lock can be used as a fallback. If the camera moves, run `chandradev.camera.screen.unlock` to force a fresh monitor detection.

Actions:

- `chandradev.camera.screen.focus` — find/lock/enhance the monitor and save the focused image.
- `chandradev.camera.screen.analyze` — auto-focus first, then read/understand the enhanced screen locally.
- `chandradev.camera.screen.unlock` — clear the remembered monitor corners.

Physical test after the RTMP stream is live:

    .\scripts\TEST_CHANDRADEV_SCREEN.ps1

Successful output includes the focused JPEG path, sharpness score, mount-stability result and the fraction of the camera frame occupied by the monitor. The focused images are stored locally under the CHANDRADEV state tree.

If the monitor is not reliably visible or the camera is moving too much, CHANDRADEV returns an owner handoff through KRISHNA instead of accepting an unreliable OCR frame.

## Privacy and network boundaries

- Raw sampled frames stay on the PC.
- VisionAdapter is local-only and has no automatic cloud fallback.
- RTMP TCP 1935 is intended for Windows Private profile + LocalSubnet only.
- HLS/WebRTC helper listeners bind to localhost.
- Starting/stopping the LAN listener remains an owner-approved action.
- Camera observations are evidence; they do not establish hidden intent, identity, diagnosis, or fault certainty.
