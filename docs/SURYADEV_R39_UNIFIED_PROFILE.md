# SURYADEV unified profile — GitHub frontend + reviewed R39 observer (2026-10-23)

## Single application policy
- **UI authority:** `standalone/suryadev/dashboard.html`, `dashboard.css`, `dashboard.js`, and its GitHub companion assets only.
- **Do not ship/use** R39 ZIP `web/index.html`, `web/app.js`, or `web/ui.css` in the unified version.
- **Single data root:** the operator's existing `D:\Work\SURYADEV-DATA` remains authoritative. Research jobs use existing SQLite and source policies; supervised R39 videos use `video-review/` below that root to avoid overwriting existing evidence.
- **One installation:** `D:\Work\SURYADEV`. The original R39 ZIP remains untouched as source/evidence, not a second daemon.
- **No paid services.** Optional inference requires a locally available Ollama model, never silently switches to a paid provider.

## Responsibility
| Layer | Authoritative component | Readiness |
|---|---|---|
| Dashboard/nav, tasks, Garudanetra, hardware, books, storage settings | GitHub standalone SURYADEV v6.9 | CI successful on Oct 21; real machine acceptance pending |
| Approved website/PDF/RSS/YouTube text and continuity | GitHub adaptive worker + approved learning plan | Existing implementation; provider access not guaranteed |
| Six-hour low-water requests/fleet | GitHub approved catalogue and pinned HTTPS mission relay | Requires actual Core + laptop pairing/TLS acceptance |
| Video/caption/frame observation | Canonical `core/suryadev_worker.py` with `scripts/SURYDEV_VIDEO_LEARNING_ADAPTER.py`, governed by review panel | R39 local test evidence; new GitHub integration separately gated |
| Approved video-job import, exact target display and one-at-a-time run | Repo dashboard video review extension | No automatic recording; explicit per-job checkbox + hash |
| BRAHMA/Rishi acceptance and cleanup | Canonical Core verified receipt and learning-bundle contract | Do not automatically promote; receipt required |
| TLS secure Core authorization | GitHub pinned HTTPS mission relay | Do not reuse the R39 HTTP bearer-token bridge |

## R39 package verification and limits
The 2026-10-23 R39 ZIP contains `Suryadev.exe`, `SuryadevLearning.exe`, `SuryadevLink.exe`, source, SHA-256 manifest and QC report. Its reported browser interactions and synthetic video run passed, but its own QC report states `production_ready: false`. Physical second-machine network pairing, physical microphone/audio/camera, six-hour shifts and cancellation of running observations were not certified. Bundled EXEs remain unsigned and are not deployed by this integration.

## Nonduplication and privacy
Reuse the existing Core worker and video adapter; **do not** copy R39's second worker implementation into a competing daemon. Raw browser media, audio, selected frames and transcripts remain on the observer. Do not auto-upload, cleanup, start capture, grant authorizations or declare learning complete based on UI clicks. The video-job target must match the **exact** approved URL in `learning-plan.json`; approval includes query string, not only the URL path. A new video job cannot run while another worker holds the same root's lock.

## Safe staged deployment
1. **Do not launch or overwrite the present installation during review.** Stop existing worker and dashboard only when choosing a later supervised install.
2. Back up BOTH the SQLite database and full evidence trees and record hashes. Preserve existing `learning-plan.json`, `book-plan.json`, device identity, pairing tokens, receipts and lock-related state.
3. Check this branch's Core/standalone CI, including the video review contracts and manual Chromium operator interactions.
4. Run the guarded standalone installer from GitHub checkout. It validates before copying; it installs the canonical observer worker and video adapter as private source-sidecars to the same GitHub dashboard. Python/playwright/Edge availability are separate preflight checks.
5. Start **dashboard only** at `127.0.0.1:8769`. Review imported job + exact URL; first try a one-minute approved public video. Do not start the continuous worker at the same time.
6. Check actual saved bundle and matching Core receipt; do not represent `AWAITING_SERVER_ACK` as BRAHMAGYAN knowledge.
7. Only after browser, restart, offline, certificate pin, revocation, storage and 6-hour device soak tests consider a continuous scheduled deployment.

## Acceptance gates
- Static/frontend JS/Python syntax and isolated contract tests must pass.
- Browser UI test: import causes no capture; disallowed/mutated target refuses run; consent required; refresh and restart preserve status; error appears honestly.
- Hardware: one real Edge video, captions/frame provenance, crash recovery and explicit stop behavior.
- Core: pin verified TLS and authenticated device ID; bad certificate or unpaired device cannot receive mission/submit evidence; matching receipt only permits authorized cleanup.
- Continuity: dedup, low-water refill, CPU/RAM/disk guards, 429 backoff without bypass, no fabricated source coverage or Rishi learning LED.
- **Production readiness remains false until those physical tests are evidenced.**

## Explicitly excluded from this first integration
R39 local HTTP pairing/sync, its ZIP frontend and binaries, automatic Core knowledge promotion, paid inference, unrelated repo changes, hidden background services, startup installers and unsigned EXE production distribution.
