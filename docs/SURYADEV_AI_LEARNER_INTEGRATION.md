# SURYADEV AI Learner — integrated four-lane decision (26 Oct 2026)

## Decision and repository review

Keep **one existing SURYADEV dashboard** and **one existing learning scheduler/worker lock**. The menu route `#ai-learner` selects four workspace panels: YouTube, PDF, Websites, Book. Do not install a second YouTube executable, start a second dashboard server, introduce another unapproved source queue, or open a visible Chromium/Chrome/Edge window.

The existing GARUDANETRA controlled browser is an **unbranded Playwright Chromium engine**, not a separately embedded browser executable. The approved YouTube frontend preview uses the provider's `youtube-nocookie.com/embed/<video-id>` iframe inside the local dashboard, **only on an explicit user click**. The browser-based GARUDANETRA media observer remains the existing independent job runtime. A preview has no authority to generate an evidence receipt, mark comprehension or promote a knowledge candidate. Ads may still appear.

Repository candidates and reasons **not** to vendor at this stage:
- [FreeTube](https://github.com/FreeTubeApp/FreeTube): Windows-compatible Electron desktop application, AGPL-3.0; its own desktop window, extractor updates and license integration would add an app/runtime, contrary to the required single SURYADEV interface. Privacy and ad-free features are not guaranteed for SURYADEV.
- [Invidious](https://github.com/iv-org/invidious): AGPL-3.0 alternative frontend with embed/API, but requires separately operated service instances or externally trusted providers. This creates an availability/security dependency and does not demonstrate validated learning evidence.
- [Piped](https://github.com/TeamPiped/Piped): frontend/API with embedded video support but a separately deployed backend/proxy, redundant with GARUDANETRA and its approval controls.
- [Official YouTube iframe API](https://developers.google.com/youtube/iframe_api_reference): supports in-page playback and player state reporting, but such state is **only a playback observation**. Any future telemetry wiring must keep preview events separate from the independently recorded observer receipts.

No third-party repos have been installed, downloaded into the laptop or forked in this change. Do not circumvent provider restrictions or claim advertisement-free playback.

## Source and evidence boundaries

The AI Learner client uses existing read-only APIs, never manual URL submission:
- YouTube: `/api/video/review`, `/api/youtube/audit`. Reports media observer health, time-indexed observations and explicit **Rishi examination not verified**.
- PDF and Websites: `/api/live`, `/api/tasks?kind=pdf|website&limit=12` and `/api/tasks/{id}`. Task identity and kind must match before rendering evidence integrity and available extraction coverage. Source strings render as text, not HTML; this does not embed arbitrary third-party websites.
- Book: `/api/books`. Reuses recorded `sessions[ollama:...]` with line counts, journal steps, visual audit and BRAHMAGYAN candidate counts. Indexing, line-level processing and learning are distinct.
- Worker: `/api/learning/control` and the **existing** CSRF-protected Start/Stop UI controls. No competing worker, new source approval, hidden background replay, or source-data reset.

The current workspaces expose recorded facts only. Full PDF visual navigation, website visual frame inspection and audiovisual coverage cannot be certified by the local API fields alone. Hardware capacity and the 85% admission policy are enforced by the existing worker, not by UI cards.

## Acceptance and release guard

1. Run all SURYADEV unit tests, including `test_garudanetra_owned_browser.py`, on Windows and Linux.
2. Run existing Playwright dashboard smoke for the four buttons and no popups. Confirm source and book APIs return data from disposable fixtures, with no live source injection.
3. On **the actual paired Windows laptop**, install from the feature branch in a separate safe test environment without overwriting the existing `data` directory.
4. Verify real GARUDANETRA-only video progress, media events, caption provenance, provider errors, PDF/book resume, CPU/RAM guard, worker lock and OS window visibility. Video observation != completed learning != Rishi verification.
5. Verify authenticated KRISHNA/BRAHMAGYAN receipts and independent Rishi examination separately.
6. Keep PR #232 **draft** and do not merge or label production accepted until physical acceptance passes.

The prior Chrome-only 44.14-second video probe does not satisfy the GARUDANETRA acceptance gate.

## Windows laptop canary — pull and acceptance runbook

The known test root is `D:\Work\SURYADEV-FLEET-CANARY-20261025`, with a checked-out
`KRISHNA-CORE` repository, an installed `app` folder, existing `data` and
a local `.venv\Scripts\python.exe`. Confirm these paths exist first.
**Do not run git reset --hard, git clean, reinstall to a new data directory,
or start a second dashboard while an earlier process is running.**

In PowerShell, check for uncommitted work before updating; do not discard it:

```powershell
$Root = 'D:\Work\SURYADEV-FLEET-CANARY-20261025'
cd "$Root\KRISHNA-CORE"
git status --short
git fetch origin feature/suryadev-universal-fleet-foundation-20261025
git switch feature/suryadev-universal-fleet-foundation-20261025
git pull --ff-only origin feature/suryadev-universal-fleet-foundation-20261025
git rev-parse HEAD
```

Preserve the current `data` root. If an existing learner or dashboard is running,
gracefully stop it **using its own controls** before installing; check that the
worker lock is free. Do not terminate unrelated processes. Install using the
repository's existing test-gated Windows installer **only after** that stop:

```powershell
& "$Root\KRISHNA-CORE\standalone\suryadev\install-windows.ps1" `
    -InstallDir "$Root\app" -DataDir "$Root\data" `
    -Python "$Root\.venv\Scripts\python.exe"
```

Start the **single** local dashboard using the existing launch method and port
8872 after installation. To launch explicitly when no dashboard is running and
the existing canary `fresh-workspace.json` has been reviewed:

```powershell
cd "$Root\app"
& "$Root\.venv\Scripts\python.exe" .\start-node.py --data "$Root\data" `
    --model auto --adaptive-fleet --continuous --port 8872
```

That launcher updates only its existing workspace marker before starting the
dashboard; do not mistake it for a strictly read-only command. It does **not**
automatically start an approved-video observer without the separate
`--auto-approved-videos` opt-in. Start the worker only after confirming
approved sources, current hardware admission and the single-worker lock.

Then run the **read-only** acceptance preflight from the checkout:

```powershell
& "$Root\KRISHNA-CORE\standalone\suryadev\VERIFY_AI_LEARNER_WINDOWS.ps1" `
    -Root $Root -RequireDashboard
```

Open `http://127.0.0.1:8872/#ai-learner` in the existing SURYADEV
application/dashboard. Confirm menu isolation, all four lanes, approved
YouTube-only preview (explicit click), no external popup, PDF/web task
provenance, book line checkpoints and status from existing data. Read the
real video observer and YouTube audits separately. A UI preview **is not** a
GARUDANETRA playback acceptance or a Rishi exam.

The PowerShell preflight performs only Git/file hashing, local-file presence
tests and loopback **GET** requests. It does not fetch external media, write
learning data, launch a second process, start jobs, install software, pair Core
or certify video comprehension. **Physical GARUDANETRA video and BRAHMAGYAN /
Rishi validation remain manual gates**, even if the preflight returns PASS.
