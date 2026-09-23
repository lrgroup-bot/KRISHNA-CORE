# HAWKEYE Learning Observer

## Purpose

HAWKEYE Learning Observer is a bounded learning/curation layer for KRISHNA Mobile and PC.
It lets the owner deliberately show HAWKEYE a camera scene, video, book/page, document,
screen, object or audio sample and ask KRISHNA to learn from it.

The observer does not treat raw media as truth. It extracts a distilled finding, preserves
source provenance/hash, routes the candidate through Universal Learning and BRAHMA, then
assigns the relevant Rishi team for research, cross-checking and later Gyan-Bhandar
promotion under the normal evidence gates.

## Learning flow

1. Owner starts HAWKEYE camera or supplies media.
2. Phone performs bounded local perception/object tracking and keeps raw evidence local.
3. Selected/curated evidence may be analyzed by the approved local PC vision stack.
4. HAWKEYE Learning Observer records a distilled observation plus source hash/provenance.
5. Universal Learning classifies learning intent and unresolved gaps.
6. BRAHMA checks existing Rishi knowledge and learning value.
7. Rishi Council assigns a lead Rishi and supporting/reviewer Rishis.
8. Candidate knowledge remains unverified until the normal Rishi/BRAHMA/Gautama/Veda
   Vyasa/Gyan verification path is satisfied.

## Mobile camera controls

HAWKEYE camera mode exposes four explicit controls while retaining the conversation-first UI:

- **LEARN** — enable periodic observer routing of changed analysis.
- **SEARCH** — open a public search in an Android Custom Tab backed by the user's browser.
- **PHOTO+DATA** — save the current image with visible overlay/caption plus a JSON sidecar.
- **REC+DATA** — save a bounded short video plus a JSON sidecar.

The local object layer uses ML Kit object detection/tracking for bounding boxes and tracking
IDs. It may request camera zoom only when the Android/WebView camera track reports a real
zoom capability. Unsupported cameras continue without claiming zoom control.

## Browser policy

Research pages open through Android Custom Tabs / the user's default browser session.
KRISHNA's WebView JavaScript bridge is not injected into arbitrary third-party pages.

HAWKEYE may build normal public research queries from:
- a name explicitly supplied by the owner;
- an enrolled and consented local identity match; or
- ordinary public textual clues such as a visible name, username, organization or asset mark.

An unknown face or face embedding is **not** an identity-search key and is not used to hunt
for a person's social-media accounts.

## Capture policy

User-requested images/videos are saved locally on the phone:
- MediaStore Pictures or Movies under KRISHNA/HAWKEYE on modern Android;
- JSON metadata sidecars under Downloads KRISHNA/HAWKEYE;
- app external-file fallback for older supported Android versions.

Capture metadata may include session, goal, timestamp, observed object boxes, tracking IDs,
zoom setting and the current HAWKEYE analysis. Passwords, PINs, OTPs, tokens and API keys
are excluded/redacted. Saving locally does not authorize cloud upload.

## Truth boundary

Every important HAWKEYE result keeps an evidence state such as OBSERVED, MEASURED,
INFERRED, PREDICTED or UNKNOWN. Coarse mobile object labels are geometry/tracking hints,
not exact object identity. Raw media is evidence, not semantic truth.

## Verification still required

Software/CI can prove the implementation and Android package contracts. Production readiness
still requires a real-device acceptance pass for:
- live camera tracking IDs/bounding boxes;
- device-supported automatic zoom;
- Custom Tab opening in the owner's installed browser;
- gallery PHOTO+DATA and REC+DATA persistence;
- sidecar metadata content;
- battery/thermal/load behavior;
- offline/PC-sync behavior; and
- observer-to-Rishi routing using real captured material.
