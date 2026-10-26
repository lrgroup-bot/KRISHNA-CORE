# GARUDANETRA Media Lite — SURYADEV worker lane (v1)

## Ownership and runtime topology

```
SURYADEV one local supervisor / one OS worker lock
  ├─ GARUDANETRA Lite: website DOM only (unchanged, denies media)
  ├─ GARUDANETRA Media Lite: allowed YouTube watch URLs
  │    ├─ Playwright Python / installed Chrome (or opt-in Chromium/Edge)
  │    ├─ fresh, job-local browser-profile directory
  │    ├─ real HTML media ready/network/error/clock/element generation
  │    ├─ bounded main-frame navigation / streaming HTTP diagnostics
  │    └─ source captions + selected frame SHA evidence, NOT understanding
  └─ book/PDF/caption extraction queues continue under hardware admission

KRISHNA candidate acceptance → BRAHMAGYAN → Rishi examination (NOT yet paired).
```

The GARUDANETRA Media implementation is in
`standalone/suryadev/suryadev_garudanetra_media.py`. Its session is
instantiated **inside** the already authorized
`scripts/SURYDEV_VIDEO_LEARNING_ADAPTER.py` observer child. The child
retains the parent supervisor's single lock ownership, exact-URL approval,
no-automatic-replay job ledger, and 85% hardware guard. There is no new daemon,
no second scheduler and no new paid provider.

The existing `GarudanetraLite` site-research class **must not** be modified
to permit media. That website class blocks media intentionally to limit
bandwidth and private browsing state. Media Lite has a different network
policy: it permits ordinary public HTTPS streaming hosts, blobs and reviewed
local extension resources, but blocks direct local/RFC1918/link-local URLs,
insecure remote HTTP and local domain names. This is browser navigation
defense-in-depth, not a general DNS-rebinding-proof security sandbox.

## Source and accounts

A media URL must be an exact public HTTPS `youtube.com/watch?v=<11-char-id>`
URL AND already appear in the approved source plan. YouTube advertisements
remain part of ordinary provider playback: never seek, skip or count their
position/captions/frames as lecture evidence.

This v1 does **not** automate YouTube login or copy an owner's normal
Chrome cookies. Profiles are isolated per approved video job. Account
login may sometimes remove consent gates or enable legitimately restricted
views, but is neither required nor a proven remedy for the observed browser
player resets. Dedicated signed-in profile support needs an additional
single-profile lock and explicit owner action and is deliberately deferred.

The browser may still encounter YouTube consent pages, availability blocks,
HTTP 429, provider restrictions or player reloads. None of these outcomes
are silently bypassed or reported as successful learning.

## Player continuity and failure states

After the player has genuinely displayed ready source content, Media Lite
reports:

- `media_unloaded_after_playback`: two consecutive samples of 0 video time,
  0 readyState and 0 networkState following previously playable media.
- `video_element_replaced`: replacement of the HTMLVideoElement after
  previously playable content; no continuity is assumed.
- `unapproved_video_navigation`: unexpected top-level navigation.
- `media_error`: HTMLMediaElement error; no simulated recovery.
- The existing `content_playback_stalled` and `advertisement_wait_limit`
  guards still apply.

All these terminal reasons are rejected by BOTH the SURYADEV worker evidence
gate and KRISHNA Core's intake gate. A stopped session can still retain raw
debugging receipts and legitimate partial timestamped evidence, but it must
not enter the authenticated BRAHMAGYAN/Rishi knowledge path as a completed
lesson.

The reporter records hostname, request type and HTTP status only for network
failures. It never persists media URLs, signed streaming query parameters,
cookies or authorization headers.

## Operator install and canary

The tested feature branch is
`feature/suryadev-universal-fleet-foundation-20261025`, draft PR #232.
The current installed app remains unchanged until explicitly pulled on
the Windows SURYADEV laptop.

First click Stop Learning and wait until the managed worker is stopped;
then close the dashboard PowerShell process with Ctrl+C. Only proceed if
no monitored video child remains and dashboard port 8872 is free.

```powershell
$ErrorActionPreference='Stop'
$root='D:\\Work\\SURYADEV-FLEET-CANARY-20261025'
$repo=Join-Path $root 'KRISHNA-CORE'
$py=Join-Path $root '.venv\\Scripts\\python.exe'
if (Get-NetTCPConnection -LocalPort 8872 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Dashboard is still running'
}
git -C $repo pull --ff-only origin feature/suryadev-universal-fleet-foundation-20261025
if ($LASTEXITCODE -ne 0) { throw 'Git update failed' }
& $py "$repo\\standalone\\suryadev\\install-node.py" --install-dir "$root\\app" --update
if ($LASTEXITCODE -ne 0) { throw 'Installation failed' }
Test-Path "$root\\app\\suryadev_garudanetra_media.py"
```

To use the previously measured **1.5x** ceiling for this laptop,
start the dashboard in the SAME PowerShell process with:

```powershell
$env:SURYADEV_VIDEO_BROWSER_CHANNEL = 'chrome'
if ($env:SURYADEV_UBOL_EXTENSION_DIR) {
    throw 'Chrome channel conflicts with a configured unpacked Chromium uBO Lite extension'
}
& "$root\\app\\START_SURYADEV_13_SOURCE_CHECK.ps1" -Root $root -Model auto -DashboardOnly
```

Use the dashboard Start Learning control once. A **new owner-approved,
unattempted** video is required; the three prior stopped CS50P videos
remain historical and cannot silently replay. The Video Review panel and
`GET /api/youtube/audit` now surface media state (ready/network/clock),
optional failure hostnames/status, unload/replacement event and stop reason.
This diagnostic work is not proof of full AV comprehension.

## Definition of complete

- Source approval and SHA checks, no unauthorized URLs or hosts
- One supervisor, one worker lock, no competing video scheduler
- Normal media permits public HTTPS streaming but denies private-network paths
- Observe actual non-ad media clock and fail on unload/replacement/navigation
- Preserve attempted job history; never replay without new owner approval
- Share concise live media state with a freshness timeout
- Worker and Core reject incomplete video as learning success
- Rishi comprehension remains `NOT VERIFIED` until examined independently

## External references

This implementation reuses upstream Microsoft Playwright Python and the
already installed browser. External agent-browser, browser-use, Browser
Harness, BrowserCode, uBO Lite and other projects remain optional adapters,
not replacement authorities. No additional external GitHub code is copied.
