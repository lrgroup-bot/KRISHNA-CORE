# HAWKEYE — Electronics Diagnostic Lab (integration specification)

Status: proposed, not implemented or validated on hardware.

## Purpose
Extend the HAWKEYE mobile field agent to identify, inspect, photograph, and guide professional diagnostics for used electronics collected by LR Resources. GARUDA PRO remains the central diagnostic orchestrator, hardware resource scheduler, and report authority. HAWKEYE is the field interface and camera/sensor companion; do not duplicate GARUDA's scheduler.

## Device classes
- Network switches and routers: port map, negotiated link speed, throughput/packet loss using controlled endpoints, PoE only with rated instruments, management telemetry with authorization.
- TVs and monitors: test patterns, resolution/refresh/EDID when connected, HDMI/input tests, dead/stuck pixel visual review, backlight uniformity; color accuracy/brightness require calibrated colorimeter.
- UPS/inverters/power supplies: model/label recognition, battery/telemetry inspection, instrument-guided voltage/load checks; no unsafe mains switching.
- CCTV, printers, audio, USB peripherals, storage and circuit boards: category-specific inspection and diagnostic checklists.
- Computers and servers: HAWKEYE requests GARUDA diagnostics through an enrolled agent after explicit selection and admin approval.

## Workflow
1. HAWKEYE camera scans device and captures all sides, serial/model/ports and condition.
2. Resolve identity via local registry and optionally verified vendor manuals/web evidence. Never claim unsupported features.
3. Discover attached/enrolled devices via USB/LAN/Wi-Fi/Bluetooth; discovery alone never authorizes remote access.
4. User selects one device. KRISHNA may suggest but must not silently stress-test discovered devices.
5. Display full PRO test plan, estimated duration, instruments needed, risks, and request administrator approval on target machine.
6. GARUDA runs all *supported safe* checks with telemetry, timeouts, thermal thresholds and automatic emergency stop. No destructive writes, factory resets, firmware flashes, or energized mains tests without separate specific authorization.
7. Mark each check PASS/WARN/FAIL/NOT_TESTED with evidence, tool version, timestamps and reason if unsupported.
8. HAWKEYE collects operator photos, video and instrument readings; distinguish manual measurements from automated results.
9. GARUDA produces tamper-evident report and LR Resources intake recommendation: reuse / repair / parts / recycle, including repair estimates and inventory link.

## UI integration
HAWKEYE > Electronics Lab:
- Scan & Identify
- Discovered Devices
- Select & Approve
- PRO Diagnostic Session
- Live Measurements
- Evidence & Test Report
- LR Resources Intake / Grading

## API contracts (design only)
- POST /api/garuda/discovery/scan (authorized discovery scope)
- GET /api/garuda/devices
- POST /api/garuda/diagnostics/plan (device_id, requested_tests)
- POST /api/garuda/diagnostics/approve (plan_id, authorization context)
- POST /api/garuda/diagnostics/start (approved_plan_id)
- GET /api/garuda/diagnostics/{session_id}
- POST /api/garuda/diagnostics/{session_id}/stop
- POST /api/hawkeye/evidence (session_id, image/reading metadata)
- GET /api/garuda/diagnostics/{session_id}/report

All endpoints require authentication, device ownership/authorization, RBAC and audit logs. The API routes above are proposed, not existing endpoints.

## Acceptance criteria
- Only explicitly selected device is tested; no LAN/Bluetooth privilege bypass.
- Hardware class-specific full PRO plan, with unsupported checks clearly marked NOT_TESTED.
- Safe thermal/voltage guardrails and operator emergency stop.
- Read-only first for disks; data-preserving default.
- Report includes raw evidence and can be attached to LR Resources inventory.
- Works offline for capture/checklists and syncs securely when connected.
- Tests on representative hardware before production release.
