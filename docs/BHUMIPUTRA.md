# Bhumiputra — KRISHNA Field Geo-Engineering & Live Scene Agent

Bhumiputra is a permanent KRISHNA specialist for live field geospatial, terrain,
visible-structure and access-route inspection. It runs behind KRISHNA and is not a
main-menu item.

## Isolation

- Agent id: `bhumiputra`
- Action namespace: `bhumiputra.*`
- State: `.krishna_state/bhumiputra`
- Heavy compute: isolated workers/processes only
- Mobile camera: paired private KRISHNA network only
- Vision: local-first / local Ollama adapter
- KRISHNA delegates work and receives concise evidence/status.

## Live camera behavior

The user can open Bhumiputra camera mode from KRISHNA Mobile and point the rear
camera at a scene. Sampled frames are analyzed without blocking KRISHNA's primary
conversation loop.

Bhumiputra automatically chooses a scene interpretation such as:

- terrain / quarry / hill / rock face
- structure / building / tower / bridge
- road / haul road / track / culvert
- machinery / truck / excavator / crane
- utility infrastructure / telecom or transmission tower / pole / substation

The live overlay shows the latest analysis and frame count. Every analyzed frame is
associated with a Bhumiputra live-session record.

## Tower / building example

When the camera is pointed at a tower or building, the live analysis should identify
only evidence visible in the frame and supported sensor context:

- visible structural arrangement and geometry
- columns, beams, bracing, slabs, walls, roof, tower members and joints
- apparent material class
- visible dimensions only when scale/depth evidence is available
- access, clearance and approach constraints
- apparent corrosion, cracking, deformation, missing members, surface deterioration
  or other visible condition indicators
- useful next viewpoint or scan direction
- confidence and unknowns

### Evidence boundaries

Camera AI must not present these as verified facts without additional evidence:

- hidden reinforcement
- concealed connections
- foundation depth/condition
- certified structural load capacity
- exact concrete/steel/rock material grade
- subsurface mineral reserves
- original engineering design intent

Drawings, survey control, depth/SLAM, NDT, geotechnical data, drilling or engineering
calculations can be attached to Bhumiputra later and fused with the visual evidence.

## Multi-AI fusion target

Bhumiputra's intended analysis stack is a fusion pipeline, not one monolithic model:

1. Local multimodal vision-language model — semantic scene understanding.
2. Object detector / segmentation — components, vehicles, roads and boundaries.
3. OCR — signs, labels, plate/asset markings when appropriate.
4. Depth / AR / SLAM — geometry and relative measurements.
5. GNSS / RTK / IMU — georeferencing and survey position.
6. Photogrammetry / point cloud — 3D reconstruction.
7. DEM / GIS — terrain, slope, drainage and route cost surfaces.
8. Domain reasoning — geology, civil/structural observations and haul-road constraints.
9. Evidence fusion — observed vs estimated vs inferred vs unknown.
10. Report/overlay generator — live labels plus KML/GeoJSON/3D/report outputs.

Adapters that are not installed must report unavailable rather than being simulated.

## Current implemented foundation

- coordinate polygon validation and preliminary area/perimeter metrics
- persistent survey plans and field observations
- persistent live camera sessions
- local vision prompt/analysis contract
- structure/terrain/road/machinery scene modes
- private mobile camera-frame endpoint
- mobile live camera overlay
- structural/geological truth policies
- Bhumiputra capability-bounded AgentRuntime registration

## Next engineering adapters

- Android sensor/GNSS telemetry into each live frame
- ARCore depth/geospatial anchors
- optional external RTK receiver bridge
- segmentation/object-detection worker
- COLMAP/OpenDroneMap photogrammetry worker
- GDAL/GRASS terrain worker
- truck/haul-road cost-routing worker
- KML/KMZ/GeoJSON and 3D export
- survey recording and final engineering evidence package


## Expanded live perception (v0.2)

The canonical BHOOMIPUTRA live-camera contract now covers terrain/quarry, structures, roads,
machinery and utilities plus people/PPE, vehicles, electronics/devices, ordinary OCR/assets,
hazards and temporal change.

`BhumiputraAgent.ingest_live_frame` uses the local VisionAdapter, applies the field-perception
truth/privacy prompt, redacts authentication secrets before persistence and records the
observation into the live session. The existing bounded encrypted mobile-evidence store is
retained.

### Identity and sensitive-input boundaries

Face presence, person count and visible PPE/activity may be described. Identity matching is
limited to explicitly enrolled and consented local profiles; unknown people remain `UNKNOWN`
and no cloud biometric provider is claimed.

Ordinary text such as signs, labels, serial/model numbers, asset tags and requested registration
plates may be read. Passwords, PINs, OTPs, API keys, bearer/session tokens and equivalent
authentication secrets are never returned, reconstructed, stored, synchronized or learned.
They are replaced with `[SECRET REDACTED]` before live-analysis persistence.

### Diagnostic truth boundary

Vehicle/electronics visual inspection may identify visible condition and candidate functional
blocks. Hidden vehicle faults require OBD/CAN/J1939 or other measurements; hidden electrical
faults require trusted references and instrument/device telemetry. Camera-only observations
must not be reported as verified hidden faults.
