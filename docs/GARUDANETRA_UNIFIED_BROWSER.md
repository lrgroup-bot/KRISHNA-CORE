# GARUDANETRA — one owned browser policy for KRISHNA and SURYADEV

**Operator decision, 26 October 2026: No Google Chrome / Edge for our browser tasks.**

GARUDANETRA is our own browser *application layer* for network source
rendering, source-approval boundaries, session isolation, browser
instrumentation and observable evidence. The actual HTML/JS engine
remains the open-source Chromium build supplied by Playwright. This is
**not** a newly written browser engine or a standalone consumer
Windows browser executable. Do not make either claim.

## Browser authority

| Surface | Owner | Rendering engine |
| --- | --- | --- |
| KRISHNA GARUDANETRA live session | KRISHNA Core Browser Fabric | Playwright channel `chromium` only |
| KRISHNA browser inspector / UI Guardian / privacy probe | KRISHNA Core Browser Operator | Playwright channel `chromium` only |
| SURYADEV approved website research | `GarudanetraLite` | Playwright channel `chromium` only |
| SURYADEV approved video observation | `GarudanetraMediaSession` | Playwright channel `chromium` only |
| SURYADEV video/browser speed probes | Worker-lock-safe diagnostics | Playwright channel `chromium` only |
| SURYADEV approved PDFs/books | Existing PDF/book/vision pipelines | No external web browser required to parse a local file |

**Do not install or launch Google Chrome or Microsoft Edge as a
fallback.** Missing Playwright Chromium should produce an honest
prerequisite failure; website queues and book/PDF jobs must not report
browser success in that condition. Older
`SURYADEV_VIDEO_BROWSER_CHANNEL=chrome` settings are ignored.

No additional remote AI browser agent is required. Browser Use and
agent-browser can remain optional capability research, not alternate
authorities.

## Windows fleet node: test the owned engine offline

After stopping the learning worker (not necessarily the dashboard) and
updating the feature branch's portable app, run:

```powershell
$root='D:\\Work\\SURYADEV-FLEET-CANARY-20261025'
$py="$root\\.venv\\Scripts\\python.exe"
$data="$root\\data"

& $py "$root\\app\\suryadev_browser_preflight.py" --data $data
Write-Host "GARUDANETRA PREFLIGHT EXIT: $LASTEXITCODE"
```

This checks only locally available open-source Chromium in a temporary
in-memory page and reports browser version and HTMLMediaElement
`canPlayType` codec declarations; it opens no YouTube URL, changes no
source approval, and downloads no browser or media.

If the *only* blocker is missing Chromium binaries, the owner can
explicitly install the Playwright-managed open-source browser:

```powershell
& $py -m playwright install chromium
```

This can download hundreds of megabytes from Playwright's configured
browser distribution source. It does not install branded Google Chrome.
For portable fleet deployments, set `PLAYWRIGHT_BROWSERS_PATH` to a
controlled persistent directory consistently at installation AND
runtime, or use the default per-user Playwright browser cache.

## Test YouTube separately

Only after the offline test passes and no learning worker holds the lock:

```powershell
& $py "$root\\app\\suryadev_video_browser_probe.py" `
    --data $data --channel chromium --seconds 50 `
    --video "https://www.youtube.com/watch?v=VZ5LU8vHT0s"
```

Without `--approve-after-passing`, this is a bounded playback
diagnostic, not a new assignment. The VZ5LU8vHT0s video already has an
attempted learning record and must not be replayed as a fresh learning
job. Do **not** delete `.worker.lock` or bypass the prior-attempt journal.

**Codec and transfer limits:** Playwright states its Chromium build
may not ship some proprietary codecs present in Chrome/Edge. The
successful earlier **Chrome** report (44.14 seconds real progress)
and Chrome speed sweep **do not transfer** to GARUDANETRA.
Until GARUDANETRA's own full Chromium speed sweep passes, the video
learning ceiling falls back to 1x. If official YouTube playback is not
supported by our chosen engine, report `media_unavailable` rather
than launching Chrome, bypassing provider restrictions or claiming
video learning.

## Live security and evidence

- One node-local SURYADEV supervisor / OS worker lock.
- Approved sources only. No arbitrary browsing of private networks.
- Isolated per-job video profile; no reuse of the owner's personal
  Chrome/Edge profile or extraction of account credentials.
- Website-only GARUDANETRA remains low-bandwidth and denies media.
  Media session selectively permits normal public HTTPS streaming;
  it never skips ads, fakes video time, or downloads the source.
- Book/PDF pipeline unchanged. KRISHNA remains approval authority
  for its own browsing actions and for eventual verified knowledge.
- An unloaded/replaced media element, unexpected navigation or
  incomplete captions is not successful video learning.

## Official upstream evidence

- https://playwright.dev/python/docs/browsers
- https://playwright.dev/python/docs/api/class-browsertype
