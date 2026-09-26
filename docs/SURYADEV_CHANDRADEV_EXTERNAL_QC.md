# SURYDEV + CHANDRADEV External Observation/QC Architecture

## Purpose

SURYDEV and CHANDRADEV are independent external-node agents for KRISHNA.

- **SURYDEV** is the overall external Eye + Ear + Reader + UI/research observer.
- **CHANDRADEV** is the independent final live-camera QC peer.
- **BRAHMA** remains the knowledge/QC governor for BRAHMAGYAN/Gyan-Bhandar.
- **KRISHNA** remains decision authority.
- **SUDARSHAN/deterministic gates** remain authoritative for verified implementation/release checks.

Neither external agent replaces HAWKEYE. HAWKEYE remains KRISHNA's field/perception specialist. SURYDEV exists specifically as an isolated external research/test observer with its own workstation.

## SURYDEV responsibilities

SURYDEV runs on a separate Windows PC/laptop and can be assigned jobs by KRISHNA/Rishis:

1. Read the screen during frontend/backend testing.
2. Capture/listen to system audio and optionally microphone audio.
3. Watch videos in an isolated browser and keep a synchronized video/audio timeline.
4. Convert speech to timestamped text.
5. Detect scene changes and extract representative frames.
6. Read visible screen/UI text and, where configured, use OCR/VLM analysis.
7. Observe live tester behavior of the rendered product.
8. Audit KRISHNA and every registered project for visible UI defects:
   - poor buttons/inputs/text boxes
   - typography/hierarchy
   - spacing/alignment
   - clipping/overlap
   - contrast/readability
   - responsive breakage
   - asset/loading/error/empty-state quality
   - inconsistent interaction patterns
9. Research public UI/UX patterns and accessibility/platform guidance.
10. Produce evidence-backed change requests rather than subjective redesign commands.
11. Send **only distilled findings** into KRISHNA/BRAHMA/BRAHMAGYAN.

Raw recordings, full screenshots, full audio/video, browser caches and temporary frames remain on the external SURYDEV workspace unless an explicit separate evidence-transfer workflow is approved.

## CHANDRADEV responsibilities

CHANDRADEV runs on a separate PC/laptop and is the final independent visual QC peer.

Primary input is a live camera aimed at the actual display/device under test. Direct screen corroboration may also be used, but CHANDRADEV's value is independent observation of what a human physically sees.

CHANDRADEV evaluates:

- deterministic test result
- SURYDEV review/findings
- BRAHMA QC
- independent camera-visible defects
- test summary/evidence

Decision rules:

- deterministic test failure -> **BLOCKED**
- high-confidence live-camera error/critical defect -> **BLOCKED**
- SURYDEV + BRAHMA agree pass -> **PASSED** (assuming deterministic/camera pass)
- SURYDEV + BRAHMA agree fail -> **BLOCKED**
- SURYDEV and BRAHMA disagree -> **DEBATE_REQUIRED**

A disagreement cannot silently pass. A recorded CHANDRADEV/BRAHMA debate must preserve both positions and end in one of:

- PASSED
- BLOCKED
- RETEST_REQUIRED

## Knowledge path

External media is working evidence, not knowledge.

SURYDEV finding flow:

Rishi/KRISHNA request
-> external SURYDEV job
-> screen/audio/video/browser observation
-> local transcription/frame/OCR/VLM analysis
-> distilled finding + timestamp + source hash + contradiction notes
-> KRISHNA
-> BRAHMA intake
-> BRAHMAGYAN / Rishi routing
-> research/cross-check
-> Gautama evidence review where required
-> BRAHMA QC
-> Gyan-Bhandar normal proposal/approval gate

## External workstation layout

Recommended:

E:\KRISHNA-EXTERNAL-OBSERVERS\
  .venv\
  cache\
  models\
  playwright-browsers\
  workspace\
    suryadev\
      jobs\
      browser-profile\
      video-cache\
      audio-cache\
      frames\
      transcripts\
      evidence\
    chandradev\
      camera-cache\
      qc\
      evidence\

Use:

scripts/INSTALL_SURYADEV_CHANDRADEV_WORKER.ps1

The installer is free-only and configures local caches/models/browser storage under the selected root.

## Portable EXEs

Build:

scripts/BUILD_SURYADEV_CHANDRADEV_EXE.ps1

Outputs:

- Suryadev.exe
- Chandradev.exe
- Suryadev-probe.json
- Chandradev-probe.json
- SHA256.json

The EXEs are deliberately small control-plane binaries. Heavy components are free sidecar tools/models so the external machine can select them based on hardware and upgrade them independently.

Current sidecar capability targets:

- mss: screen capture
- OpenAdapt Capture patterns/library: synchronized desktop capture/auth handoff
- PyAudioWPatch: Windows system-audio loopback
- faster-whisper: speech-to-text
- PySceneDetect: scene/keyframe detection
- OpenCV: camera/frame processing
- Playwright/Chromium: isolated browser research
- FFmpeg/ffprobe: media extraction/inspection
- optional local/free VLM/OCR adapters

No paid API is configured by the installer.

## Trusted LAN + USB

Both agents are normal KRISHNA trusted nodes.

New node roles:

- observer
- qc

Recommended capabilities:

SURYDEV node:
- suryadev.worker
- suryadev.screen_read
- suryadev.system_audio
- suryadev.video_research
- suryadev.ui_review
- suryadev.web_research

CHANDRADEV node:
- chandradev.worker
- chandradev.live_camera_qc
- chandradev.final_qc

LAN:
- endpoint comes only from an already owner-approved NodeRegistry entry
- discovery does not grant trust

USB:
- JSON envelope
- SHA-256 file manifest
- node fingerprint must still match NodeRegistry
- packet payload hash is verified before ingestion

## Internal actions

- suryadev.status
- suryadev.job.create
- suryadev.ui.audit-projects
- suryadev.ui.research-plan
- suryadev.finding.route
- chandradev.status
- chandradev.qc
- chandradev.debate.resolve
- external.observer.lan-target

Internal HTTP status:

- /api/suryadev/status
- /api/chandradev/status

## Authentication and web verification

Authentication is a handoff boundary. Credential entry, MFA, CAPTCHA, liveness and anti-bot human-verification challenges are not learned or bypassed by SURYDEV/CHANDRADEV.

During authentication/verification:
- raw credential capture is disabled
- secrets are not learned
- the worker pauses/hands control to the authorized human when required
- normal observation can resume after authentication completes

This keeps the observer useful for legitimate browsing/testing without turning it into a human-impersonation or anti-bot-bypass system.

## UI authority rule

SURYDEV should behave like a careful human reviewer, but it is not allowed to request changes based only on taste.

Every requested UI change should have at least one of:
- visible defect evidence
- failed deterministic/accessibility evidence
- reproducible interaction problem
- documented accessibility/platform guidance
- clearly identified public benchmark pattern relevant to the same surface

Final acceptance still requires the existing KRISHNA verification chain plus CHANDRADEV/BRAHMA QC where configured.
