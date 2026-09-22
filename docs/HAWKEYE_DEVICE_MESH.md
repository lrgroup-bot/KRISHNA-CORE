# KRISHNA Device Mesh v1

KRISHNA treats phones, future glasses, PCs and external sensors as capability nodes, not model-specific products.

## Discovery

Android nodes discover camera capabilities through Camera2, enumerate sensors, RAM/storage, battery/power-save/thermal state, GPS, BLE, USB host and UWB when exposed by Android. A capability is enabled only when the runtime reports it.

Profiles are adaptive: `NANO`, `LIGHT`, `BALANCED`, `PERFORMANCE`. Low battery, power-save mode or severe thermal pressure forces a lower-cost profile.

## Hawkeye edge memory

Mobile Hawkeye keeps compact observation records instead of streaming every frame to the PC. Each retained observation contains an object/session id, evidence state, quality score, sensor context, SHA-256 evidence hash and sync state. Local retention is bounded and oldest observations are pruned.

Evidence states: `MEASURED`, `OBSERVED`, `INFERRED`, `PREDICTED`, `UNKNOWN`.

## Execution policy

1. Prefer phone edge compute for frame filtering, quality scoring, tracking and lightweight inference.
2. Send selected evidence to KRISHNA PC for expensive reasoning/reconstruction.
3. Cloud is optional transport/compute and never the authority.
4. Do not fabricate IR, thermal or depth capability. Those modes activate only when supported hardware/driver paths are detected.
5. Future KRISHNA Glass is a Device Mesh node: eyes/ears/display/control. Mobile remains the portable edge computer; PC remains the heavy compute node.

## Next adapters

- CameraX/Camera2 live quality sampler and low-light extension selection.
- NNAPI/QNN/ONNX backend benchmark and model router.
- WorkManager durable encrypted evidence sync.
- USB thermal/NIR/depth device adapters.
- Object embedding index and local semantic observation search.
- Glass/Wearables capability adapter when the target SDK/device is selected.
