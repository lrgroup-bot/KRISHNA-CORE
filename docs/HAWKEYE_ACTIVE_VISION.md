# HAWKEYE Active Vision

## Purpose

HAWKEYE Active Vision turns the KRISHNA Mobile camera into an automatic reading
instrument. The owner should normally only show an item or point at one. HAWKEYE
selects the target, follows it, tries camera/read recovery automatically, and
shows a full green border only after a stable read.

The live fast path is deterministic and local. Heavy AI is not allowed to block
camera target acquisition or OCR/barcode scanning.

## Hard target priority

1. POINTED — continuous MediaPipe index-finger ray intersects a tracked object.
2. LOCKED — explicit tracking-id lock, used only when no pointed target wins.
3. AUTO — best visible object by centrality, readable size, stability and local
   object confidence.

Canned gesture commands remain opt-in. Pointing selection does not wait for the
old gesture debounce.

## Hard state machine

SEARCH -> TARGET -> READING -> RECOVER -> COMPLETE -> NEXT

- SEARCH: no stable target yet.
- TARGET: object/subject target selected.
- READING: cropped local OCR + barcode read in progress.
- RECOVER: automatic camera/read correction. No left/right/closer instruction
  loop is shown to the owner.
- COMPLETE: multi-frame text consensus or decoded barcode evidence is stable.
  The full camera border becomes green and the extracted details panel is shown.
- NEXT: when the completed target leaves or a new pointed/best target wins, the
  state resets automatically.

## Mobile fast path

### Detection and pointing

- ML Kit stream-mode object detector supplies bounding boxes and tracking IDs.
- MediaPipe supplies 21 normalized landmarks per detected hand.
- Index-finger PIP/DIP/TIP geometry forms a forward pointing ray.
- Subject segmentation bounding boxes are a fallback when the object detector has
  no usable target.

### Camera recovery

The WebView camera track is capability-gated. HAWKEYE attempts only controls the
device/browser exposes:

- continuous focus mode;
- zoom;
- exposure compensation;
- torch for low light, with automatic ownership/hysteresis;
- high-detail 1920x1080 / 30 fps preferred capture request.

HawkeyeCameraProfiler.java also reads native rear-camera capabilities without
opening the camera: focal lengths, minimum focus distance, AF/AE/OIS modes, flash,
digital/zoom-ratio ranges, and logical/physical multi-camera relationships.

### Reading

The selected target is cropped with padding and locally enhanced before reading.
HawkeyeMobileVision.analyzeReadTarget() runs only:

- Latin OCR;
- Devanagari OCR;
- barcode scanning with enableAllPotentialBarcodes().

Potential but undecoded barcodes increase automatic zoom pressure.

### Multi-frame consensus

hawkeye-active-vision.js retains a bounded per-target history. Completion
requires repeated text agreement or decoded barcode evidence after a minimum
stability interval. Repeated completion vibration is suppressed.

The deterministic extractor currently recognizes common fields such as model,
serial, input, output, power, voltage, current and barcode. If no structured
field is found, the stable OCR text is still displayed.

## Automatic unreadable recovery

Unreadable does not immediately become a user instruction. HAWKEYE first tries:

1. refocus/continuous-focus mode;
2. target zoom;
3. exposure compensation;
4. low-light torch when supported;
5. target-crop OCR;
6. potential-barcode rescan;
7. multi-frame retry/consensus.

Physical impossibility remains a truth boundary: hidden, completely occluded or
non-visible information is not invented.

## PC escalation

HawkeyeActiveVisionRuntime keeps heavy reasoning outside the camera loop.
After bounded mobile recovery it can select a capability-gated escalation:

- PP-OCRv6 for difficult labels;
- MobileSAM-style point/box segmentation;
- device depth for 3D pointing disambiguation;
- Florence-2 region-grounded semantic reading on the PC;
- Grounding DINO open-set grounding on the PC;
- existing HAWKEYE local/free-only vision when optional engines are absent.

These specialist engines are optional adapters, not automatic paid
dependencies and not required for the mobile fast path.

## Privacy and safety

- Raw camera frames remain local by default.
- Existing credential redaction remains in force.
- Unknown-face identity search stays disabled.
- Active Vision does not claim unreadable/hidden product data.
- Electronics hidden faults still require measurement/reference evidence.
- Heavy/cloud escalation must preserve the existing HAWKEYE privacy and free-only
  routing policies.

## Acceptance gates

A release is not accepted unless CI proves:

- the Active Vision asset is packaged and JavaScript syntax-valid;
- pointed target selection is evaluated before explicit lock;
- object, hand and active-read timers are sub-second;
- the target-only native OCR/barcode bridge exists;
- potential barcode detection is enabled;
- automatic recovery replaces move-left/right/closer guidance;
- READ COMPLETE drives the full green border;
- the canonical runtime declares Active Vision and the native camera profiler;
- mobile fast recovery precedes optional heavyweight escalation.

Real-device acceptance on the Samsung phone must additionally verify focus/zoom
capabilities, torch behavior, pointing accuracy, thermal/battery load, fast target
switching, multi-lens behavior exposed by WebView/Android, and continuous scanning
of several real products and electronic parts.
