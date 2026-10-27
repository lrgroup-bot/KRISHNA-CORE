# AI Learner: a single in-page YouTube player and four source lanes

## Recheck: desktop executables versus embedded players

- **FreeTube** https://github.com/FreeTubeApp/FreeTube — free/open-source
  Electron desktop YouTube app; advertisements removed by FreeTube as
  documented by its developers. FreeTube.exe creates its own desktop
  application window, not an embeddable SURYADEV HTML component.
  We did not install, vendor, fork or launch FreeTube.
- **Invidious** https://github.com/iv-org/invidious — AGPL-3.0 alternative
  YouTube frontend with documented `/embed/<video-id>` support and ad-free
  features. Can be configured to render in SURYADEV's existing webpage
  through a local instance. It is a self-hosted web service, **not** a
  Windows .exe that we can invisibly embed. Its availability, playback
  legality and actual ad-free behavior have NOT been verified on the
  owner's machine.
- **Piped** https://github.com/TeamPiped/Piped — alternative web frontend
  with embedded video and no-ads features; also requires a functioning
  backend. Kept as a future alternative, not a second player.
- **Official YouTube IFrame** supports in-page embed but the platform
  developer policy does not allow suppressing ads that YouTube ordinarily
  serves. Removed from the AI Learner preview path at user request.
  We do NOT modify YouTube's official player to hide/skip advertisements.

## Single dashboard and one worker

```
SURYADEV main menu → AI Learner (one page, one URL, no popup)
  ├── YouTube: optional locally operated Invidious /embed/id preview
  ├── PDF: canonical document extraction and evidence (GARUDANETRA tasks)
  ├── Websites: canonical GARUDANETRA website reader and task evidence
  └── Books: indexed documents / serial local AI reading and book-line search
                          ↳ one existing worker lock / 85% hardware guard
```

All four buttons are already present in `dashboard.html` and respond
inside the existing `dashboard-pages.js` router. Real worker controls
are reparented into the AI Learner page; nothing is cloned or scheduled
twice. The existing video-observer and caption-extraction paths are
separate from the **manual preview**. Preview time must NEVER increment
learning progress or obtain KRISHNA/BRAHMAGYAN/Rishi acceptance.

## Owner-controlled local Invidious option

This integration is shipped **disabled**. It neither installs Docker
nor starts an external web service. To enable, the owner must first
operate a trusted Invidious instance bound to a local loopback port,
following official documentation:

- https://docs.invidious.io/installation/
- https://docs.invidious.io/configuration/

Do not copy third-party credentials, GitHub secrets, or video tokens
to source code. Invidious needs a configured database, secret key and
maintenance; official documentation warns it may need frequent restarts.
On a resource-constrained SURYADEV laptop this extra service may reduce
available learning capacity. Consider deploying it only after verifying
CPU/RAM headroom and independent service uptime.

With the dashboard/worker gracefully stopped, on the same computer:

```powershell
$env:SURYADEV_LOCAL_INVIDIOUS_ORIGIN = "http://127.0.0.1:3000"
& "D:\\Work\\SURYADEV-FLEET-CANARY-20261025\\app\\START_SURYADEV_13_SOURCE_CHECK.ps1" `
    -Root "D:\\Work\\SURYADEV-FLEET-CANARY-20261025" -Model auto -DashboardOnly
```

This is only an example. **Do not set the variable until an operator-run
local Invidious service genuinely exists at that origin.** The app
normalizes localhost/IPv6 loopback and refuses arbitrary remote URLs,
embedded credentials, HTTP proxy paths, fragments and non-loopback hosts.
If the local service is absent, the iframe may fail; no claims of playback
success or advertisement elimination are made.

The read-only endpoint `GET /api/ai-learner/player` reports only
configuration status, never credentials or source-derived media URLs.
The YouTube preview controls are disabled unless a valid backend and
previously approved exact YouTube watch job are available. Only a
**direct user click** embeds `/embed/<11-character-id>` within the
existing AI Learner page. It is cleared on tab switching, page
navigation, and backgrounding; autoplay and new-window controls are
not added.

## Remaining acceptance before calling this complete

1. A local Invidious service actually running, reachable and maintained
   without resource saturation (not done here).
2. Operator opens a currently approved video in the AI Learner panel
   and confirms that the player loads **without a second desktop window**.
3. Observe real media progress and buffering in that *preview*; verify
   ad display empirically, not by interpreting FreeTube/Invidious README.
4. Independently exercise canonical SURYADEV video worker, fix observed
   media unload at ~49.5 seconds and Ollama timeout, acquire authorized
   timestamped captions/visual evidence, and validate ingestion.
5. Require actual BRAHMAGYAN and Rishi assessment receipts; preview is
   not a substitute.

For external source or ad policies, see:
https://developers.google.com/youtube/terms/developer-policies-guide

This commits only application integration, documentation and tests. No
software was remotely installed on the owner's Windows system.
