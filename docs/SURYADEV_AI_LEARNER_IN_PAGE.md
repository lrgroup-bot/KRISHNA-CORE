# SURYADEV AI Learner — one page, four source actions

Owner request (26 October 2026): use a **single in-page AI Learner**
instead of opening an external Chromium or separate YouTube executable.
The four actions are **YouTube, PDF, Websites, Books**. The sidebar
remains the single SURYADEV navigation root.

## Review of the best upstream candidates

| Project | Official source | Why not directly embed its EXE? |
|---|---|---|
| FreeTube (AGPL-3.0) | https://github.com/FreeTubeApp/FreeTube | Electron desktop EXE: renders a **separate OS window**. Claims ad-free local extractor/Invidious support. Copying/repackaging code requires AGPL review and security/maintenance work. Not installed or embedded. |
| Invidious (AGPL-3.0) | https://github.com/iv-org/invidious | Ad-free alternative frontend with embed and API, but it needs a separately hosted service and third-party source availability. Not running on owner's PC. |
| Piped | https://github.com/TeamPiped/Piped | Ad-free privacy frontend and embed support, but separate backend/instances are needed; external availability is not certified. Not installed. |

**Implementation decision:** all four source lanes already have
supervised collectors. Preserve those workers and the 85% admission
guard; add one dedicated *page within the existing dashboard*.

A native FreeTube EXE cannot be placed inside an HTTP page with a
regular iframe; running it externally would violate the no-new-window
requirement. Do not silently download, execute or vendor its code.

The in-page preview uses YouTube's **official privacy-enhanced
`youtube-nocookie.com` player** for explicitly clicked, already
approved watch IDs. The YouTube player MAY DISPLAY ADS; it is
not an ad-free frontend. YouTube API policies do not permit suppressing
ads in its standard embedded player:
https://developers.google.com/youtube/terms/developer-policies-guide

A true ad-free, self-hosted Invidious/Piped backend would be a
separate reviewed installation/integration with provider access,
licensing and independent acceptance. It is not claimed here.

## UX contract

- The main menu includes **AI Learner**, route `#ai-learner`.
- This is a route in the same existing tab/dashboard, not a new OS
  window, duplicate dashboard or browser application.
- Exactly four source action buttons select YouTube / PDF /
  Websites / Books; the active action has `aria-pressed=true`.
- YouTube shows actual approved observation records and a user-click
  optional inline YouTube preview. Only exact approved 11-character
  IDs can load; there is no URL input and no automatic autoplay.
  The preview iframe is destroyed on leave, visibility loss or Close.
- PDFs and Websites read the existing `/api/live` source ledger,
  and Books read `/api/books`. No fabricated learning.
- **Start approved learning** and **Stop** delegate to the pre-existing
  authenticated/CSRF-protected dashboard controls, not new backend
  worker processes. Selecting a lane does not restrict the scheduler
  to only that source type. Do not describe this as four independent
  learning engines.
- Existing Evidence, Assignments, Video review and Books menu entries
  remain accessible and unchanged.
- The browser/video observer is **headless**. This prevents new
  browser windows; it does **not** guarantee video codec support,
  YouTube provider permission or continuous playback.
- No knowledge is committed just because an embedded preview played.
  Canonical worker reports, timestamps, captions, source evidence,
  supervisor ACK and eventual independent Rishi examination remain
  separate gates.
- The backend CSP permits frames **only** from
  `https://www.youtube-nocookie.com`; all other defaults remain
  restricted. Preview deliberately receives no popups permission.

## Installation on the user-owned Windows node

This branch changes GitHub source only; it cannot install on the
owner's external Windows device. Stop the node's worker and dashboard
gracefully, retain the `data` folder and do not force-clear locks.

```powershell
$ErrorActionPreference='Stop'
$root='D:\Work\SURYADEV-FLEET-CANARY-20261025'
$repo="$root\KRISHNA-CORE"
$py="$root\.venv\Scripts\python.exe"
if(Get-NetTCPConnection -LocalPort 8872 -State Listen -ErrorAction SilentlyContinue){
    throw 'Stop the current dashboard safely before installing'
}
git -C $repo pull --ff-only origin feature/suryadev-universal-fleet-foundation-20261025
if($LASTEXITCODE -ne 0){ throw 'Git pull failed' }
& $py "$repo\standalone\suryadev\install-node.py" --install-dir "$root\app" --update
if($LASTEXITCODE -ne 0){ throw 'SURYADEV installer refused' }
```

After restarting the existing dashboard, open
`http://127.0.0.1:8872/#ai-learner`.

## Acceptance boundary

Automated UI/Windows/Linux unit tests verify the same-page route,
four actions, no unsolicited player or OS-window spawn, approved
source/evidence state, installer completeness, and no fabricated
comprehension. They do **not** test FreeTube, Invidious, Piped, a
logged-in YouTube account or live end-to-end decoding on the actual
Windows laptop.
