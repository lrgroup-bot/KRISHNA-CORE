## One SURYADEV Learning Intelligence dashboard — consolidated UI (October 25, 2026)

The detailed Learning Intelligence interface is now **the only served frontend**.
Both `http://127.0.0.1:8772/` and `http://127.0.0.1:8772/advanced`
render the same `dashboard.html`, worker controls, data root and evidence.
For a canary instance on port 8872, the equivalent links are
`http://127.0.0.1:8872/` and `http://127.0.0.1:8872/advanced#video-review`.
Existing deep links and section anchors remain valid. There is no separate
Node Control application, no duplicate worker and no second learning ledger.

Node profile, approved-plan presence, secure pairing state, measured admission,
network link status and Start/Stop are integrated within this single interface.
A configured maximum (3 in legacy mode or 125 in adaptive fleet mode) is not
measured runnable capacity or a guarantee of actual parallel jobs. Evidence
collection is not automatically certified as source comprehension.

### Live KRISHNA pairing (opt-in, never automatic)

The current Core supports **zero-code SHA-256 credential pairing**, not the
legacy pairing-code proposal in `suryadev_enroll.py`. Use the new
`suryadev_pairing_bootstrap.py` only after Core's restricted native HTTPS
listener has been enabled and its certificate fingerprint independently
verified. It creates a local token, submits its SHA-256 to
`/api/mobile/pair/request`, requires approval on the **KRISHNA PC** via
`/api/mobile/pair/approve`, verifies that approval over pinned TLS, and
only then creates `core-mission-connection.json`. No dashboard process,
source plan or evidence is replaced during pairing.

The exact owner-controlled two-machine procedure and rollback boundaries
are in `docs/SURYADEV_FLEET_ROLLOUT.md` at the repository root.
A paired credential does not prove Core job intake, BRAHMAGYAN knowledge
acceptance, Rishi exam grading or deep learning.

**Historical release notes below may still describe the previous split-page
UI and the original mandatory rest policy. Current behavior is controlled
by the profile's continuous-mission policy and the single UI described here.**

---

## Continuous missions: six hours of approved work / ten-minute device rest

**New policy:** the single SURYADEV worker owns a durable
`mission-cycle-runtime.json`. Every six-hour mission window remains active
while approved work is available. At the boundary it stops admitting NEW jobs
and lets existing website, PDF, book and video futures write their actual
receipts. Only after they finish does a **minimum ten-minute rest** start.
During rest the node does not launch new learning, browser, video, book or
examination work and releases an idle Garudanetra Chromium process. Then it
automatically opens the next six-hour mission without requiring another Start
click. Restarting the process cannot skip an already recorded rest.

**The 85% CPU/RAM/disk/GPU admission guard is absolute**, and a rate-limited
source cannot be force-fetched. The schedule cannot guarantee zero idle seconds
without enough approved, legally accessible sources. We must report
`awaiting_assignment`, `no_approved_work`, `rate_limited`,
`hardware_guard_paused`, `draining`, or `rest` accurately instead of
manufacturing tasks, reprocessing completed URLs or overriding provider limits.

Queue replenishment continues to request work before the eligible backlog
falls below three tasks. The request is addressed to **KRISHNA**, asks
**BRAHMAGYAN** to prepare subject-appropriate assignments and choose a RISHI,
and explicitly prefers sources grounded in official expert profiles, vetted
institutions and independently correlated publication identifiers (ORCID /
Crossref DOI). Expert status cannot be inferred from a video title or a random
webpage, and an ORCID/DOI claim without its corresponding official metadata
does **not** establish authenticated identity. No automated KRISHNA/BRAHMAGYAN
delivery or human identity attestation is claimed until separate receipts exist.

The dashboard exposes the actual mission cycle via `/api/operations`.
The new Node Control page shows the rest phase and scheduled resume time;
the full historic evidence dashboard remains at `/advanced`. Per-source
checkpoints survive any rest and belong to the original data folder.

**One laptop first:** this release never creates additional workers, services,
Windows scheduled tasks, firewall rules, network credentials or source
permissions. Continuous operation requires the existing dashboard/worker to
remain launched; a computer sleep/shutdown does not create learning work while
it is off. Longer-term unattended boot/service management must be separately
approved and tested for each device.

---

## SURYADEV adaptive research fleet — source-first mission upgrade (25 October 2026)

### Actual behavior in this release

* Each node samples CPU/RAM/disk and available NVIDIA GPU utilization using `psutil`
  and `nvidia-smi` (when present); Windows GPU names come from WMI, and
  Linux Intel/AMD/NVIDIA GPU vendor inventory comes from DRM sysfs. Other
  GPU utilization is **unverified**, never silently assumed available.
* The worker inspects active network interfaces and their negotiated LINK rate;
  that is **not measured Internet bandwidth**. It records Internet/source
  reachability only for a recent, successfully extracted and SHA-committed,
  authorized PUBLIC HTTPS source; the proof expires after 180 seconds.
* Under separately enrolled, authenticated pinned-TLS KRISHNA pairing and an
  approved learning plan, the existing SURYADEV fleet client sends resource
  telemetry, requests leased tasks periodically, and reconciles evidence SHA
  with KRISHNA. Collector-only RAM capacity and the fresh workspace three-task
  ceiling are reported consistently. Without real pairing, only local
  approved research is possible; an unauthenticated ping is not a mission.
* To **automatically observe** previously owner-approved videos, pass
  `--auto-approved-videos` to the portable `start-node.py` launcher. That
  explicit opt-in activates the existing approved-video queue inside the
  currently running research supervisor; it never invents unapproved URLs,
  bypasses CAPTCHA, forces concurrency beyond admission, or replays jobs
  whose evidence may already exist. Omit the switch for collection-only
  workflows where video automation has not been approved.
* One data-root worker lock controls all local source/video/book lanes. With
  no waiting source jobs, spare measured capacity can launch up to **three
  distinct previously approved browser videos at once** on a fresh workspace.
  Websites, PDFs and books use the SAME per-node capacity and 85% guard;
  a slow node may admit just one or zero jobs. The YouTube caption provider is
  rate-limited to one request; browser observation is an independent lane.
* The canonical Playwright video adapter chooses observed playback speeds
  1x for important/unknown/no-caption sections, 1.5x for explanations,
  2x for ordinary text, and up to 3x for **repeated** clearly low-value chatter.
  It records the actual HTML video playback-rate readback. Playback speed is
  **not proof of whole-video viewing, speech comprehension or frame coverage**.
  Provider sign-in/CAPTCHA/429 conditions are not bypassed.
* Books already have a SHA-pinned SQLite line-by-line ledger, with section,
  PDF page, source line, processed checkpoint and independent model journal.
  PDF URL extraction now additionally retains every page's extracted line
  counts and page-reference format. Images, scanned text, layout ordering and
  equations require separately verified OCR/vision to claim whole-document
  visual coverage. The available deep PDF implementation is optional and
  rejects unsupported documents rather than silently truncating them.
* Webpages retain original/final HTTPS URL, number of extracted text lines and
  at most 25 discovered same-host reference links. **Those links are not
  automatically crawled**; each new page needs an approved mission/source
  scope. Deep viewport scanning is an optional existing operation, not
  a guarantee that dynamic pages or embedded media were understood.

### Evaluated open-source references (not all vendored or installed)

- `psutil`: Python resource counters on Windows/Linux/macOS.
- `microsoft/playwright-python`: browser video observation, DOM, HTML media
  playback-rate readback, source provenance.
- `pymupdf/PyMuPDF` and `pymupdf4llm`: potential structured layout/word and
  OCR upgrades. **Not integrated as the required extractor**; present PDF
  URL pipeline still uses `pypdf`, and book index supports explicit OCR.
- `adbar/trafilatura`: potential article-to-structured-text metadata and
  sitemap discovery, subject to exact approved hosts; **not installed**.
- `SYSTRAN/faster-whisper`: optional local speech transcription fallback;
  its CPU/GPU model memory must be separately admitted. **Not made compulsory**
  for collector nodes.

### Honest remaining gates before "deep learning verified"

KRISHNA must actually pair a node, deliver an approved leased mission and
acknowledge the returned evidence. BRAHMAGYAN must ingest the **complete**
lawfully transferable referenced evidence rather than equate a 500-character
fleet excerpt with understanding. RISHI must independently test conceptual,
practical and source-grounded recall. Long website crawling requires a
multi-page approval policy; full video requires observable complete intervals,
audio/visual coverage and missing-segment audit; OCR ordering and video
provider availability cannot be guaranteed. CI passing unit/browser tests is
not equivalent to these real-device and comprehension gates.

---

## New Node Control frontend — October 25, 2026

**Default:** `http://127.0.0.1:8772/` — a compact, responsive, evidence-first command center
for Windows, Linux and macOS SURYADEV nodes. This is a **functional local
frontend**, not a mockup. It uses existing read-only APIs and performs
Start/Stop through the existing loopback/same-origin/CSRF operator endpoints.

Sections are: worker ownership and actual state, collector-only vs optional
local models, three-task admission, live/queued assignments, website/YouTube/PDF/
book coverage, a searchable paginated evidence ledger, click-through receipt
inspection, 85% hardware guard and explicit KRISHNA pairing status. Task
completions remain distinct from independent comprehension verification.

**Full evidence console:** `http://127.0.0.1:8772/advanced` preserves all
older book journals, video review, detailed time/provenance audit, daily
history and configuration settings; its data is the SAME current node
workspace, not a second database or a copied ledger. Do not delete the old
dashboard files. Prior sessions live in their own previous data root.

On an existing Windows node, stop its old dashboard and worker, pull the
SURYADEV development branch, run `install-windows.ps1` from
`standalone/suryadev` with your chosen install/data folders, and start
`python start-node.py --data <node-data> --model collector --port 8772`
from the installation directory. **Do not launch a second dashboard on
port 8772.** No source is automatically approved because the frontend was
upgraded; a plan or authenticated KRISHNA mission is still required.

The Chromium regression suite covers both the Node Control homepage and
the full `/advanced` evidence view; the installer/runtime verifier asserts
all new HTML/CSS/JS files are present.

---

## Portable SURYADEV fleet nodes — desktops, laptops, CPUs and optional servers

SURYADEV is a **hardware-adaptive collector**, not a dedicated Qwen laptop. Each
machine can be enrolled as its own separately approved evidence collector. A
lightweight node needs Python 3.10+ and `psutil` for safe work admission; approved
website capture needs Playwright + Chromium when that lane is used, and video/PDF
lanes require their own documented dependencies. **Ollama is not required for
collector-only source extraction.** That mode preserves source provenance but
does **not** perform local model analysis, comprehension exams or claim mastery.
Those stages belong with BRAHMAGYAN and RISHI after a real authenticated KRISHNA
handoff; pairing and handoff are not automatically completed at installation.

Use a **full Git checkout**, not just the standalone folder, so the canonical
worker and adapter are available. From `standalone/suryadev` on Windows, Linux,
or macOS, install with Python:

```sh
python -m pip install psutil
python install-node.py --install-dir "/path/to/suryadev-node"
python "/path/to/suryadev-node/start-node.py" --model collector \
  --data "/path/to/suryadev-node-data" --port 8772
```

In Windows PowerShell, replace `/path/to/...` with a chosen Windows directory,
such as `D:\\Work\\SURYADEV-NODE` and `D:\\Work\\SURYADEV-NODE-DATA`. The
portable installer runs the source regression gate before copying code, verifies
the resulting runtime package, and refuses a populated installation directory
unless it belongs to an earlier portable install and `--update` is explicitly
requested **after stopping the node**. No service, Core credential, or model
is installed or inferred.

The `start-node.py` default is `--model collector`, and it creates its own
`fresh-workspace.json` plus independent study database. `--model qwen3.5:2b`
is an optional local Ollama fallback for appropriately provisioned nodes.
`--approved-trial` explicitly opts into the previous fixed textbook/YouTube
trial. Without a paired KRISHNA mission or existing approved learning plan,
the collector has no automatically authorized sources and may remain idle.

The new ledger is isolated; `--previous-data /path/to/old-ledger` validates a
prior directory but never erases or migrates it. Restarting a node reopens the
same ledger; `--new-session` makes another. The fresh-node execution ceiling
is **three jobs total**, not three per source. Admission scales CPU cores and
measured free memory and rejects new work at **85%** CPU/RAM/disk or supported
GPU utilization, on both minimal and high-performance systems. A 4 GiB node
may collect one lightweight assignment when memory headroom permits; it is
not guaranteed to run Chromium or high-resolution video processing.

To reinstall the existing Windows SURYADEV test node from the updated branch,
run `install-windows.ps1` from the source checkout as before; the release now
ships `start-node.py`. Shut down the running dashboard and worker first.
The existing PowerShell `start-fresh-workspace.ps1` retains its earlier 2B
default for backwards compatibility; use `start-node.py --model collector`
for generic new installations. Every node needs its **own authenticated TLS
KRISHNA enrollment**; machine discovery and a successful LAN ping are not
authorization to send research evidence.

---

## Fresh learning workspace — three tasks total (25 October 2026)

**Purpose:** Clear the *active dashboard view* and begin a newly approved trial without destroying prior learning evidence, SQLite history, YouTube cooldown receipts, or book journals. The old data directory stays intact and is not scanned or used by the fresh dashboard.

From a clean checkout of the SURYADEV development branch, run the Windows installer (after stopping the old dashboard and worker gracefully):

```powershell
cd "<GIT-CHECKOUT>\standalone\suryadev"  # replace <GIT-CHECKOUT> with the actual clone location
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-windows.ps1 -InstallDir "D:\Work\SURYADEV-UNIFIED-TEST" -DataDir "D:\Work\SURYADEV-UNIFIED-TEST-DATA"
```

If the installer was already run from that source checkout, launch the new clean dashboard from the installed directory:

```powershell
cd "D:\Work\SURYADEV-UNIFIED-TEST"
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-fresh-workspace.ps1
```

The script requires port **8772** to be free; stop the old dashboard first. Its **separate default data directory** is `D:\Work\SURYADEV-UNIFIED-TEST-DATA-FRESH`. It does not delete or copy earlier databases, credentials, approvals or saved evidence. The first launch creates an isolated SQLite/ledger and can automatically start the already owner-authorized fixed YouTube + textbook trial. Reopening the same fresh directory resumes its checkpoints. Use `-NewSession` to generate another clean workspace rather than wiping the current one.

The dashboard advertises exactly whether its data workspace is fresh. A single SURYADEV owner process admits **at most three active tasks total** shared between websites, captions/PDF work, observed video and model book reading. The 85% CPU/RAM/disk/GPU admission policy may allow fewer or none; large queues are not launched all at once. Ollama model calls remain serialized. The default `qwen3.5:9b` must actually exist on the laptop. Provider 429 limits, full YouTube observation, book progress, provisional recall, and independent BRAHMAGYAN/Rishi checks are reported separately and never considered passed by merely launching the trial. KRISHNA device pairing remains unconfigured in the fresh root until explicitly established.

---

# SURYADEV Standalone — experimental Windows laptop worker

**Scope:** independent local learning; does not connect to KRISHNA, BRAHMA, or other agents.
This is an initial working slice, **not** a certified autonomous video/screen learner.

## Prerequisites
- Python 3.10+ on Windows.
- Optional: Ollama running locally on `127.0.0.1:11434` with `qwen3.5:9b`.
- No paid API keys and no inbound LAN port required.

## First-run commands (PowerShell)

```powershell
cd standalone\suryadev
python suryadev.py --data "$env:USERPROFILE\SURYADEV-DATA" status
python suryadev.py add "https://example.com/"
python suryadev.py run --no-ollama
python suryadev.py search "Example"
python -m unittest discover -s tests -v
```

For Qwen summarization: `python suryadev.py run --model qwen3.5:9b`.
Each `run` processes **one** queued job. Use Task Scheduler only after the tests pass.
Data is stored in `~/SURYADEV-DATA/suryadev.sqlite3`. Back up the SQLite database
while the worker is stopped or via SQLite's online backup API.

## Present capabilities
- Explicitly approved public HTTPS HTML/plain-text fetch (2 MB response cap).
- Local SQLite queue, findings, hashes, duplicate identification, keyword search.
- Optional loopback Qwen summarization with extractive fallback.
- Resumption of interrupted jobs on the next `run` command.
- No dependence on the main PC or other agents.

## Important limitations
- **Not** a full YouTube watcher, video downloader, STT system, screen capture tool,
  GitHub analyzer, autonomous browser or GUI dashboard.
- No continuous scheduling, multi-source verification, semantic retrieval or guaranteed
  factual validation yet. Failed jobs are retained for inspection, not automatically retried.
- Public URL checks and redirect blocking are defense in depth; DNS rebinding and network
  interception need additional controls before accepting untrusted URLs at scale.
- Respect copyright, robots.txt, site policies and authorization. Only add sources
  you have permission to process.
- This experimental module has unit tests but requires Windows hardware acceptance.
- Never claim a source summary is independently verified simply because Qwen generated it.

## Release acceptance checklist
1. Run all unit tests and repository CI.
2. Verify the Windows Python/Ollama setup on the laptop.
3. Study an approved real public page and inspect its stored finding.
4. Restart and verify persistent search and queue recovery.
5. Test offline, bad URLs, large responses and model-unavailable fallback.
6. Only then consider background scheduling and further media capabilities.


## Added standalone extensions

Run these commands from `standalone\\suryadev`:

```powershell
# Import a locally saved transcript (.txt, .srt, or .vtt)
python suryadev_extras.py import-transcript "C:\\Videos\\lesson.vtt" --no-ollama

# Use local Qwen for transcript summaries
python suryadev_extras.py import-transcript "C:\\Videos\\lesson.vtt" --model qwen3.5:9b

# Run queued, explicitly added HTTPS research jobs every 60 seconds
python suryadev_extras.py worker --interval 60

# In a separate terminal, open the local read-only dashboard
python suryadev_extras.py dashboard --port 8769
# Open http://127.0.0.1:8769/
```

The worker does not discover or enqueue sources automatically. The dashboard
is loopback-only, read-only and searches saved findings. The importer does not
download YouTube videos or generate transcripts from audio; provide a lawful
transcript file. A full media capture/transcription pipeline and packaged Windows
installer still require separate development and real-device tests.

## Operational caution
Do not run multiple writer processes against the same database until the
single-writer/locking design is strengthened. Back up the database before
upgrading. Keep local files containing personal/private content out of the
learning queue unless you explicitly authorize processing.

## Optional media-learning modules

These features are opt-in and need additional free Python packages:

```powershell
python -m pip install faster-whisper yt-dlp playwright
python -m playwright install chromium
```

Examples, run from `standalone\\suryadev`:

```powershell
# Transcribe a local audio/video file and save findings
python suryadev_media.py transcribe "C:\\Learning\\lecture.mp3" --device cpu

# Import YouTube captions if publicly available (no video download)
python suryadev_media.py youtube-subtitles "https://www.youtube.com/watch?v=VIDEO_ID"

# Screenshot only a user-approved public website
python suryadev_media.py capture-page "https://example.com/" "captures\\example.png" --allow-host example.com
```

Audio decoding/transcription uses faster-whisper; CPU int8 is the default.
YouTube subtitle retrieval uses yt-dlp and may fail for unavailable captions,
geo restrictions or service changes. Browser capture uses Playwright with
explicit host allowlisting and does not click, submit or authenticate.
Capture is **not** permission to monitor private screens. These tools do not
start automatically or access a microphone.

## Remaining release gates
- Run actual Windows unit and integration tests, including the optional packages.
- Test YouTube subtitle availability and local transcription quality.
- Add a verified single-instance worker lock, source policy/robots review,
  provenance and evidence retention improvements, and browser egress hardening
  before unattended broad-scale crawling.
- Test the dashboard in Chromium and perform restart, outage and backup drills.
- Package a Windows installer only after these gates pass.

## Full evidence and backup

Web and transcript ingestion now store up to 2 MB of normalized full text in
`SURYADEV-DATA/evidence/<first-two-hash-chars>/<sha256>.txt`. Findings
still contain short excerpts and summaries for search. Evidence is
content-addressed; use the integrity command to detect changed files.

```powershell
python suryadev_extras.py verify-evidence
python suryadev_extras.py backup "C:\\Backups\\suryadev.sqlite3"
```

The database backup uses SQLite's online backup API. **The evidence directory
must also be backed up**; the database backup alone does not preserve full text.
Source URLs and hashes are retained in the findings database, but a formal
source-verification and licensing policy remains to be implemented.

## KRISHNA Core LAN discovery (new optional mode)

The laptop can search its local IPv4 /24 networks for an HTTP health endpoint
on port 8766 without entering the server address manually:

```powershell
python suryadev_discovery.py
# Or, if Windows hostname resolution does not expose the correct Wi-Fi interface:
python suryadev_discovery.py --local-ip 192.168.0.105
```

Discovery results are **untrusted candidates**, not authenticated KRISHNA
servers. SURYADEV will **not** transmit learning data, accept remote commands,
or silently join any discovered service. Secure joining needs a confirmed
KRISHNA Core enrollment API and identity verification (for example, a
one-time pairing code or mutual TLS). A successful /health response alone
must never be treated as permission to connect. The standalone research
worker remains functional offline and independently of Core.

## Core connection safety

Run `python suryadev_discovery.py` to find possible Core servers on the local network. The results are untrusted. The optional command `python suryadev_core_identity.py --host 192.168.0.100 --instance-id VERIFIED_ID` compares a manually verified identity with a reported health field. This is not authentication: the current Core health API has not been confirmed to provide this field. No automatic enrollment or exchange of data is enabled. A compatible authenticated enrollment endpoint must be verified before enabling automatic joining.

## Laptop preflight before first pull-and-run acceptance

From Windows PowerShell inside the standalone/suryadev folder, run `powershell -NoProfile -ExecutionPolicy Bypass -File .\laptop-preflight.ps1`. This runs syntax checks, all bundled unit tests, the local database status command, a best-effort local Ollama model check, and LAN discovery. Use `-SkipOllama` for offline checks. Discovery does not imply enrollment. Do not run a background worker or enable Core synchronization until the tests and pairing checks pass.

## Secure enrollment client (integration pending)

The optional `suryadev_enroll.py` command requires a documented HTTPS Core enrollment URL, a SHA-256 fingerprint of its verified TLS certificate, and a one-time code entered interactively. It refuses HTTP and certificate mismatches. Example syntax: `python suryadev_enroll.py --endpoint https://core.example/enroll --cert-sha256 YOUR_VERIFIED_64_HEX_FINGERPRINT`. This is a client-side protocol proposal, not confirmation that KRISHNA Core exposes this endpoint or accepts the proposed JSON. No automatic pairing, credential persistence, or command channel is active. A compatible Core server implementation and hardware integration tests are still required.

## Standalone Windows installation and live acceptance

From a clean Git checkout on the laptop, open PowerShell in `standalone/suryadev` and run `powershell -NoProfile -ExecutionPolicy Bypass -File .\install-windows.ps1`. The script first runs the bundled unit tests and then copies application files to `%LOCALAPPDATA%\SURYADEV`; evidence and SQLite data stay under `%USERPROFILE%\SURYADEV-DATA`. It does not install Python, Ollama or optional media dependencies, and it does not schedule background jobs or pair with KRISHNA Core.

Then run `cd "$env:LOCALAPPDATA\SURYADEV"`, `python suryadev.py status`, and `python suryadev_discovery.py`. For live learning, add a user-approved public HTTPS URL with `python suryadev.py add "https://example.com/"` and process it using `python suryadev.py run --no-ollama` first. Test Ollama only after verifying that `qwen3.5:9b` is installed locally. Confirm evidence integrity with `python suryadev_extras.py verify-evidence`. A production-ready authenticated Core joining workflow is still blocked on the server-side pairing contract and real laptop tests.

### Exact laptop acceptance commands

Run these inside the installed SURYADEV directory:

```powershell
python suryadev.py --data "$env:USERPROFILE\SURYADEV-DATA" status
python suryadev.py --data "$env:USERPROFILE\SURYADEV-DATA" add "https://example.com/"
python suryadev.py --data "$env:USERPROFILE\SURYADEV-DATA" run --no-ollama
python suryadev_extras.py --data "$env:USERPROFILE\SURYADEV-DATA" verify-evidence
python suryadev_extras.py --data "$env:USERPROFILE\SURYADEV-DATA" dashboard --port 8769
```

The `--data` option is a global argument and must appear before the subcommand. The dashboard runs on laptop loopback only; visit `http://127.0.0.1:8769/` on that laptop.

## Live, colorful Learning Mission Control (October 2026)

The laptop-only dashboard at http://127.0.0.1:8769/ uses a responsive
violet/coral/mint/sky theme, a mission overview, CPU/RAM/disk/GPU
telemetry when supported, YouTube/PDF/website counters, and a date-wise diary.
It polls live telemetry every 5 seconds and the assignment ledger every
10 seconds; it is not an automatic worker scheduler.

**All assignments are available**, not only the newest 40. Filter by source
type, worker state, source URL, title, or task number; use Previous/Next to
page through the complete local SQLite history. Clicking any task opens a
read-only inspector showing recorded timestamps, source, summary method,
summary and excerpt, error details, the SHA-256 digest and its evidence file
verification, and a per-stage done/pending/blocked/unverified checklist.
The detail updates every 15 seconds without discarding the reading position.

The local read-only endpoints are:
- `GET /api/live` — high-level status, sources, diary, recent summary and resources.
- `GET /api/tasks?offset=0&limit=25&q=&kind=&status=` — bounded history, max page size 50.
- `GET /api/tasks/{integer_id}` — per-task record and evidence verification.

**Important honesty boundary:** A worker status of `done` means a processing
result was stored, **not** that an entire video was watched, every PDF page
was read, all website text was captured, or BRAHMAGYAN accepted the knowledge.
Those checks remain explicitly unverified or pending. PDF ingestion and
complete YouTube transcript/timeline/visual coverage verification still need
implementation. Legacy findings remain `legacy_unverified` when their original
method was not recorded. The dashboard does not start jobs, send data to
KRISHNA, open any network-facing listener or authenticate an unpaired node.

Run from your actual D-drive checkout:

```powershell
cd "D:\\Work\\SURYADEV-SOURCE"
git pull --ff-only origin feat/suryadev-standalone-laptop-20261019
cd "D:\\Work\\SURYADEV-SOURCE\\standalone\\suryadev"
powershell -NoProfile -ExecutionPolicy Bypass -File .\\install-windows.ps1 -InstallDir "D:\\Work\\SURYADEV" -DataDir "D:\\Work\\SURYADEV-DATA"
cd "D:\\Work\\SURYADEV"
python suryadev_extras.py --data "D:\\Work\\SURYADEV-DATA" dashboard --port 8769
```

The installer runs `python -m unittest discover -s tests -v` in source
before copying. New task-inspection regression tests cover pagination,
filtering, finding evidence integrity and honest completion labels.
The current revisions have not yet been validated by an interactive
Chromium test on the user's Windows laptop.

## Date-wise learning diary and live operations

The colorful laptop dashboard now provides:
- **Date selection:** choose any YYYY-MM-DD day, or click an active-day tile.
  Daily cards distinguish assignments **created**, findings **saved**, jobs
  currently recorded as completed and jobs currently recorded as failed on
  that day. Completing a job later does not move its creation date.
  Completion/failed totals use the job's latest status and updated timestamp;
  this database does not preserve a full transition event log.
- **Date-filtered task history:** the same date applies to the All Assignments
  list and its pagination; click any task to inspect real evidence and errors.
  Use **All dates** to clear the filter. All times follow the laptop's configured
  local timezone.
- **Live Learning:** shows each SQLite `running` job, nearest jobs queued,
  per-source running/queued counts (YouTube, PDFs, websites and other),
  resource-admission pause state, and the next queue check only when the worker
  has recorded that time. Processing percentage and individual start ETAs
  are **not** measured or fabricated.
- **LEDs:** KRISHNA, BRAHMAGYAN and Rishi are red until authenticated and
  verified. A recent successful authorized HTTPS bridge read is **amber** for
  KRISHNA, **not green**, because it does not establish authenticated KRISHNA
  server enrollment. BRAHMAGYAN and Rishi remain red until their authenticated
  acceptance/acknowledgement protocol is implemented.

Read-only localhost endpoints:
`GET /api/operations`, `GET /api/diary`,
`GET /api/diary?date=YYYY-MM-DD`, and
`GET /api/tasks?date=YYYY-MM-DD&limit=25`.
The browser polls operations every 5 seconds and selected-day summaries every
30 seconds. The dashboard itself does not run learning jobs.

The worker is **not** started automatically. To enable queued, user-approved
research in another PowerShell terminal, run:

```powershell
cd "D:\\Work\\SURYADEV"
python suryadev_extras.py --data "D:\\Work\\SURYADEV-DATA" worker --interval 60 --model qwen3.5:9b
```

This requires the local Ollama model and resource-admission conditions;
use `--no-ollama` for extractive mode. The 85% guard is a check before
starting each job; it is **not** a hard OS CPU/RAM cap.

## Optional approved KRISHNA live reader bridge

`suryadev_bridge.py` makes the date diary, operations, hardware and
task APIs available over **explicitly enabled read-only HTTPS** to
an allowlisted Core reader. It is **off by default**: the Windows installer
does not create services, firewall exceptions, certificates or tokens.
Operator must provide a valid TLS PEM certificate and private key,
a private IP bound to SURYADEV, an approved client IP and a separate
strong bearer-token file. Do not run it without manually validating
the Core identity and enforcing your network/firewall policy.

Example with placeholders (do not put tokens directly in shell history):

```powershell
python suryadev_bridge.py --data "D:\\Work\\SURYADEV-DATA" --bind YOUR_LAPTOP_PRIVATE_IP --port 8770 --cert PATH_TO_TLS_CERT.pem --key PATH_TO_PRIVATE_KEY.pem --token-file PATH_TO_PRIVATE_TOKEN_FILE --allow-ip YOUR_CORE_PRIVATE_IP
```

On an approved Core machine, the corresponding command-line client
`suryadev_core_reader.py` pins the exact TLS leaf certificate
SHA-256 **before** sending its token and only permits GETs to approved
read-only paths:

```powershell
python suryadev_core_reader.py --endpoint https://YOUR_LAPTOP_PRIVATE_IP:8770/api/operations --cert-sha256 YOUR_VERIFIED_CERT_SHA256 --token-file PATH_TO_OWNER_SHARED_TOKEN_FILE
```

These two commands are a *manual opt-in secure transport*, not a
verified automatic KRISHNA enrollment or BRAHMAGYAN handoff.
The green KRISHNA/BRAHMAGYAN/Rishi indicators require future Core-side
authenticated pairing and explicit learning-bundle acceptance receipts.
Never expose the bridge on the public internet or change its private-IP
allowlist to a wildcard.


## End-to-end source pipeline and six-hour study mission

### Who provides research data?

Before authenticated KRISHNA enrollment, **the owner** supplies a local JSON
research plan. It lists explicit approved HTTPS sources and/or opt-in RSS/Atom
feeds. The feeder discovers **only** URLs published by these feeds and restricts
RSS/Atom results to `allowed_source_hosts`. There is no general YouTube/web
search engine or autonomous topic generator yet; the queue will eventually
become empty if subscribed sources stop producing new items. Future KRISHNA,
BRAHMAGYAN, or Rishi task delivery must be authenticated, owner-authorized and
acked before it may populate the queue.

Sources travel through this chain:

`learning-plan.json -> suryadev_feeder -> SQLite queued job -> mission worker
-> type-specific source extractor -> full text evidence SHA-256
-> local chunk-by-chunk Ollama preview / extractive preview
-> SQLite finding + job_provenance receipt -> dashboard and optional Core HTTPS reader`

### Run a supervised six-hour study

The installer only copies files; it does **not** start tasks, open firewall
ports, create a Windows service or connect to KRISHNA. Stop any other SURYADEV
worker before starting a mission because the worker lock permits one writer.

```powershell
cd "D:\\Work\\SURYADEV"
python -m pip install pypdf yt-dlp
Copy-Item .\\learning-plan.example.json "D:\\Work\\SURYADEV-DATA\\learning-plan.json" -Force
notepad "D:\\Work\\SURYADEV-DATA\\learning-plan.json"
```

The supplied example includes the already approved Python.org About page and
the public one-page W3C sample PDF. The user must explicitly review/approve
the source plan. To study YouTube, add a user-approved `https://www.youtube.com/watch?v=...`
URL to `approved_urls`. For continuing discovery, add approved RSS/Atom
feed URLs to `approved_feeds`, then explicitly list the allowed destination
hostnames in `allowed_source_hosts`. Only content explicitly available and
permitted for processing should be submitted.

```powershell
python suryadev_mission.py --data "D:\\Work\\SURYADEV-DATA" --plan "D:\\Work\\SURYADEV-DATA\\learning-plan.json" --duration-hours 6 --refill-minutes 30 --check-seconds 60 --model qwen3.5:9b
```

Run the dashboard in a separate PowerShell window:

```powershell
python suryadev_extras.py --data "D:\\Work\\SURYADEV-DATA" dashboard --port 8769
```

For a one-time source discovery dry run (this **does enqueue** approved new
items, but does not start a worker), run:

```powershell
python suryadev_feeder.py --data "D:\\Work\\SURYADEV-DATA" --plan "D:\\Work\\SURYADEV-DATA\\learning-plan.json" --once
```

Use `--no-ollama` in the six-hour mission if no local model is available;
this stores only an explicitly marked extractive preview rather than a
summary of the entire source. A mission is a manually started foreground
process; it ends after approximately six hours (or after the current
processing attempt returns) and can be stopped with Ctrl+C.

### End-to-end validation, evidence and known limitations

- **Website:** approved public HTTPS HTML/plain-text only. Decoded response
  capped at 2 MB and extracted text capped at 220k characters; truncation is
  now a recorded failure, not silent completion. Ordinary extraction does
  **not** render JavaScript or study embedded media/linked pages. Coverage
  claim is `html_text_extracted_not_browser_verified`.
- **PDF:** requires the free `pypdf` dependency. Downloads up to 20 MB,
  extracts selectable text from **every** page (up to 500), fails on scanned
  or missing-text pages or encrypted PDFs, and stores page counts in the
  evidence receipt. OCR, charts, diagrams, formulas and visual interpretation
  are **not** yet covered.
- **YouTube:** requires the free `yt-dlp` dependency and an explicit approved
  single-video URL. Saves caption text with cue start/end timestamps and
  checks timestamps against reported duration, while retaining gap warnings.
  Does **not** download the video for visual review and does not guarantee
  captions cover every spoken or visual second. If captions are missing, fails
  instead of declaring the video learned. The receipt is
  `caption_timeline_only_unverified`.
- **Learning:** with Ollama enabled, sends **each extracted text chunk** to
  the local model and retains per-chunk summaries. All chunks presented does
  not guarantee understanding or fact-checking. Without Ollama, only a preview
  is stored. The transcript/audio/visual and BRAHMAGYAN approval gates remain
  unverified until independent integration and live-device tests.
- **Queue & history:** existing SQLite jobs are not rewritten; new ones gain
  a `job_provenance` receipt. Duplicates reuse existing evidence and do not
  count as new unique understanding. Genuine current, queued, and feeder
  scheduling state is visible at `GET /api/operations`. KRISHNA, BRAHMAGYAN
  and Rishi remain disconnected until secure pairing and acknowledgements.

### Acceptance on the actual laptop

Run the test suite, then process **one real approved source of each type**;
inspect `/api/tasks/{id}` for `coverage`, `evidence_state`, and
`complete_verified` before trusting any higher-level dashboard total.
Regression tests use deterministic/mocked source responses; GitHub CI passing
does **not** prove live YouTube availability, pypdf behavior on arbitrary
third-party PDFs, visual comprehension, or genuine KRISHNA connectivity.


## October 21: visible calendar and sidebar connection lights (UI v4)

The latest colorful dashboard places **Explore learning date-wise** immediately
below the header. A visible native date input, Today, Previous day, Next day,
and All dates buttons filter the local assignment history and populate a
top-level day summary. The full per-task daily report remains available at
the linked Daily Learning Diary. The selected date stays synchronized across
the header, All Assignments, and diary filters.

The three LEDs for KRISHNA Core, BRAHMAGYAN and Rishi Council now sit in a
single sidebar-bottom group, with layout rules for compact-height desktop
windows and a three-column status strip directly below the main navigation
on mobile. Red remains the expected state before authenticated pairing.

After git pull, **stop the running dashboard and reinstall**, because the
live service serves the installed copy at D:\\Work\\SURYADEV rather than the
source checkout. Then start the dashboard again and refresh the browser.
Verify the exact active UI build:

```powershell
Invoke-RestMethod http://127.0.0.1:8769/api/ui-version
```

Expected `version`: `2026-10-21-v4-leds-calendar`. If that endpoint is
404 or reports an older value, the laptop is still serving the older code.
You can also verify the installed HTML has both controls:

```powershell
Select-String -Path "D:\\Work\\SURYADEV\\dashboard.html" -Pattern 'id="date-main"','id="krishna-led"'
```

The LED colors report verified connectivity, not an implied pairing. The UI
contract tests cover presence and event wiring of these visible controls;
an actual Windows browser test at different viewport sizes remains required.


## v5 · KRISHNA Server and Storage & Cleanup popup menus

The dashboard's main sidebar now has two clickable entries:
**KRISHNA Server** and **Storage & Cleanup**. Both open colorful dialogs.
These settings apply only to the local SURYADEV installation and use a
same-origin, per-dashboard-start CSRF token for configuration changes.
No new network listener, Windows service, startup task or firewall exception
is added. The optional remote Core bridge remains read-only.

**KRISHNA Server:** enter the private numeric IPv4 address of KRISHNA Core and
its health port (normally **8766**). Click **Save server IP**, then **Diagnose
connection** to check TCP reachability and the HTTP `/health` JSON response.
This stores only the candidate's IP/port in
`<active-data-root>/operator-settings.json`. A successful diagnosis is **not**
identity proof, authenticated pairing or BRAHMAGYAN/Rishi handoff, so Core
and academy LEDs correctly remain unpaired. There are no tokens or Core
credentials stored by this popup.

**Storage & Cleanup:** displays the *currently active* SURYADEV data folder,
available space and its retained data size. Enter a local absolute data
folder, or click **Browse folders…** to open the optional native Windows
folder picker in the same desktop session as the dashboard server. Click
**Check free disk space**. The migration requires an **empty destination**
and at least 2 GiB free, or the existing data size plus 512 MiB, whichever
is larger. It refuses paths inside the current data folder, network shares,
drive roots and common Windows system directories.

Click **Copy & verify data** and approve the confirmation prompt to copy
durable research data. The migration acquires the worker lock (stop any
running mission/worker first), backs up live SQLite using SQLite's own
backup API, SHA-256 verifies evidence files and copied data, and retains
the entire old data directory. It never automatically deletes the original
folder. The dashboard continues using its original open database until
you stop it and restart both dashboard and any worker with:

```powershell
cd "D:\\Work\\SURYADEV"
python suryadev_extras.py --data "E:\\SURYADEV-DATA" dashboard --port 8769
```

Replace `E:\\SURYADEV-DATA` with the exact verified destination displayed
in your popup and use the same `--data` for `suryadev_mission.py` or the
worker. This is an explicit restart-based cutover, not a risky hot
database move. If a copy fails, do **not** switch; the old location stays
intact. A partial destination may need manual review.

**Automatic cleanup:** enabled by default for newly created *disposable*
SURYADEV working copies only. The worker stages text under
`<data-root>/staging/jobs/<job-id>/source.txt`, then saves permanent
content-addressed evidence and its finding to SQLite. When job status is
`done` and the staged bytes, finding SHA-256 and saved evidence all match,
only `source.txt`, its machine-generated manifest and the empty staging
subdirectory are eligible for deletion. The default retention is **0
hours** (immediately after the verified save); you can choose 1, 24, 72
or 168 hours or disable automatic cleanup. Idle worker cycles revisit
expired work copies. You can preview eligible files without deleting,
or request a manual verified cleanup from the popup.

Important: the software does **not** automatically delete original
videos/PDFs/audio, imported transcripts, durable SHA-256 evidence,
SQLite history, learning plans, unfinished/failed job staging, other
applications' files or arbitrary old laptop files. Full YouTube
audiovisual comprehension and BRAHMAGYAN approval are not inferred
from successful text extraction.

After updating and reinstalling, test the running version:

```powershell
Invoke-RestMethod "http://127.0.0.1:8769/api/ui-version"
```

Expected: `2026-10-21-v5-server-storage`. The loopback diagnostics API is
`GET /api/operator/settings`; state-changing POST requests are limited
to the same-origin UI and require the transient dashboard CSRF header.


## Real YouTube, PDF and website live-source acceptance test

The normal Windows/Ubuntu unit suite mocks external providers. A separate
opt-in real-source smoke test now contacts six clearly identified public
sources via HTTPS using **temporary test data**, not the user's configured
SURYADEV history. It is also run in GitHub Actions by
`.github/workflows/suryadev-live-smoke.yml` on code changes.

After installing the newest branch:

```powershell
cd "D:\\Work\\SURYADEV"
python -m pip install pypdf yt-dlp
python live_smoke.py
```

The script exercises: (1) real Python.org website extraction and hash;
(2) a one-page public text PDF; (3) a CC0 10-page PDF, checking page 1 and
page 10 in the stored evidence; (4) a scanned PDF, which **must fail
without a saved learning record**; (5) a real Harvard CS50 Python YouTube
video via the `yt-dlp` caption path; (6) the **official Harvard publisher
SRT** for the same CS50 video. The publisher SRT path is deliberately
reported `PASS_TRANSCRIPT_ONLY` and is not equivalent to downloading or
watching the YouTube video.

On GitHub-hosted test infrastructure in October 2026, the website,
one-page PDF, and 10-page PDF passed, scanned PDF correctly rejected,
and the Harvard publisher SRT imported 778 timestamped cues with a verified
evidence hash. The actual YouTube fetch was
`BLOCKED_EXTERNAL` by YouTube's bot-verification sign-in response;
no video learning was recorded. The program reports network/provider
blocks distinctly from code failures and does not circumvent authentication.

To test the **real local learner** after ensuring no other worker is running:

```powershell
cd "D:\\Work\\SURYADEV"
python suryadev.py --data "D:\\Work\\SURYADEV-DATA" add "https://www.youtube.com/watch?v=mgBpcQRDtl0"
python suryadev.py --data "D:\\Work\\SURYADEV-DATA" run --no-ollama
```

Adjust `--data` if you have already migrated the live research database.
Check the returned job ID in the dashboard, then
`GET /api/tasks/<job-id>`. A `failed` status due to anti-bot restrictions
is an honest network limitation, not successful learning. Even when
caption extraction succeeds, the full-video visuals and complete audio
coverage remain unverified. No authentication cookies should be pasted
into logs or committed to the repository.


## v6 · Garudanetra lightweight browser + adaptive parallel source lanes

### Existing KRISHNA browser audit

KRISHNA already has `core/krishna_core/browser_fabric.py`,
`garudanetra_session.py` and `garudanetra_research.py`.
They establish a single Garudanetra authority with canonical
**Playwright/Chromium**, private contexts, managed tabs and bounded evidence.
SURYADEV now ships `suryadev_garudanetra.py`: a **small isolated laptop
adapter using that canonical engine**, not an independent full-browser
product. It is not the same authenticated session as the KRISHNA Core host
and does not change the remote Core's Garudanetra or pairing state.

The standalone website worker no longer silently uses ordinary urllib text
fetching as its normal learning route. It launches only **Playwright-managed
Chromium** in a new private, headless context, using browser-rendered visible
text and recording a `garudanetra_rendered_text_unverified` receipt. It
blocks unapproved-host requests plus image, font, media and stylesheet
traffic to limit CPU/RAM/network use. Each webpage tab closes after
extraction; the Chromium process is shared for the duration of the mission.
Scripts, embedded media, inaccessible pages, visual content and linked
pages are **not fully verified**. No personal Chrome/Edge profile,
background desktop browser window or sign-in cookies are used.

### How many jobs at the same time?

`suryadev_parallel.py` now supplies one bounded, monitored scheduler to
both the normal worker and the time-boxed research mission. Hardware
capacity comes from *real* `psutil` CPU/RAM/disk readings and supported
GPU telemetry. The 85% resource ceiling, minimum 2 GiB free storage,
2 GiB RAM reserve and proportional free RAM/CPU-core calculation prevent
unbounded launching. It admits **at most six total concurrent jobs**
and at most four actual Garudanetra website Chromium tabs, with at most
two YouTube caption-extraction jobs and two PDF extraction jobs. Those are
hard upper bounds, **not fixed targets**. A low-resource laptop might
run just one job or pause new work entirely. High-load sampling stops
new work from opening but does not abruptly corrupt already-running
evidence saves. Expensive local Ollama summarization is serialized to
one generation at a time.

The main-menu **Garudanetra browser** screen now reports live values:
website jobs running/allowed/queued and *actual open Chromium tabs*;
YouTube jobs running/allowed/queued; and PDF jobs running/allowed/queued.
Clickable workspaces show currently-running source/job URLs. YouTube/PDF
workspace tabs are truthful job cards, **not Chromium playback tabs**.
The adapter shuts down when the worker stops; stale/unknown telemetry
is shown as offline, not a fabricated green status.

### Install and test on the laptop

Stop existing SURYADEV workers/mission and dashboard before reinstall.
The installer copies source; it does **not** download browser binaries or
run background services. In your SURYADEV Python environment install the
free optional dependencies once:

```powershell
cd "D:\\Work\\SURYADEV"
python -m pip install psutil playwright pypdf yt-dlp
python -m playwright install chromium
```

The browser binary is pinned and private to Playwright. Test with *real
approved public sources* and temporary test data (does not modify your
active SURYADEV SQLite/evidence):

```powershell
python live_smoke.py
python parallel_smoke.py
```

`parallel_smoke.py` uses **controlled hardware readings** to verify the
capacity planner and opens two real Python.org pages in Chromium tabs
while a real public PDF is processed. The production scheduler instead
samples actual laptop hardware via psutil. GitHub Actions has verified a
3-job real run with **2 simultaneously open Chromium tabs**, 3 completed
source extractions and 3 SHA-256-verified findings.

For a live six-hour study using your previously approved research plan,
run the dashboard in one console:

```powershell
python suryadev_extras.py --data "D:\\Work\\SURYADEV-DATA" dashboard --port 8769
```

Then in a separate console, without another worker running, run the
mission (initial extraction-only test; no model required):

```powershell
python suryadev_mission.py --data "D:\\Work\\SURYADEV-DATA" --plan "D:\\Work\\SURYADEV-DATA\\learning-plan.json" --duration-hours 6 --check-seconds 60 --no-ollama
```

Remove `--no-ollama` only after confirming your chosen local Ollama
model is available. Replace both `--data` paths with your actual migrated
storage directory if changed. The six-hour feeder revisits approved
feeds at its configured interval; it does not perform unrestricted
internet/YouTube searches or auto-create unauthorized research topics.
When the queue is empty, capacity can be ready while **0 jobs are running**.

After reinstall, `GET http://127.0.0.1:8769/api/ui-version` reports
`2026-10-21-v6-garudanetra-parallel`. The live worker and browser
telemetry is read-only at `GET /api/operations`, under `capacity`,
`garudanetra`, and `processing`. Counts reflect recorded processing,
not guaranteed full video watching, image understanding or Rishi ACK.

### Verified browser-level frontend contract

The `dashboard_ui_smoke.py` command launches a disposable local SURYADEV
dashboard, seeds synthetic **test-only** running-job and hardware telemetry,
and uses **real Playwright Chromium** to verify the rendered frontend:
two websites running, one YouTube-caption job running, two actual
Garudanetra browser tabs, three clickable workspaces, and the correct
allowed slot totals. It opens assignment details and checks for browser
JavaScript exceptions. The seed data is a UI fixture, not a claim about
the laptop's measured hardware.

```powershell
cd "D:\\Work\\SURYADEV"
python dashboard_ui_smoke.py
```

GitHub Actions verified `GARUDANETRA_DASHBOARD_UI_REPORT` with three
visible cards, two actual browser tabs, and **zero page JavaScript errors**.
All source jobs use a separate SQLite test directory during this check.
The UI script and stylesheet must be served by the local dashboard's
asset routes, and the unit suite enforces those routes to avoid a blank
counter display.


### v6.1: dashboard-only state is not a hardware failure

When you open only `python suryadev_extras.py ... dashboard --port 8769`,
the dashboard has no active research worker. Previous versions displayed
`0 allowed` / `CPU unavailable` / `New tasks paused for laptop safety`
even when the laptop had plenty of resources; default 60-second worker
intervals could also cause the scheduler's last report to expire after
only 45 seconds.

The updated Garudanetra workspaces differentiate:

- **Learning worker offline — dashboard is running:** read-only CPU/RAM
  data from the laptop can still be displayed, but no source tab is
  launched. The potential slots estimate is not an active scheduler.
- **Learning worker ready — approved queue is empty:** worker is
  operational, but there are no new source jobs to start.
- **Worker starting — awaiting fresh capacity readings:** the worker
  heartbeat exists but the scheduler has not yet published new readings.
- **New research paused by live hardware guard:** actual fresh CPU, RAM,
  GPU or storage thresholds prevent launching another job.

A healthy worker polling every 60 seconds now keeps its capacity report
valid across the normal idle interval. `/api/operations` also returns
`worker_running`, `hardware` (read-only snapshot if worker offline),
`research_plan` (whether `learning-plan.json` exists and is valid), and
`capacity_sample_age_seconds` when recent. It does **not** start a
worker or create a research plan on its own.

The installed dashboard identifies this fix via:

```powershell
Invoke-RestMethod "http://127.0.0.1:8769/api/ui-version"
```

Version `2026-10-21-v6.1-worker-status`.

If `learning-plan.json` is missing in the **active data folder**,
manually review and copy `learning-plan.example.json` into it. Before
running a six-hour mission, make sure no other SURYADEV worker or
mission holds that same data root's worker lock. Do not delete the lock
file or terminate unrelated Python processes. Run either the ordinary
worker **or** the mission, not both.


## v6.2 · YouTube subtitle HTTP 429 safety and runtime checks

In the laptop test on October 21, 2026, SURYADEV correctly claimed YouTube
job #6 but the provider refused a Hindi subtitle response with HTTP 429.
This is **not** an offline worker, exhausted RAM, an absent job or verified
learning. The source evidence is not recorded for a failed job.

### What changed

- Requests **one** caption language per job, English (`en`) by default,
  rather than automatically downloading English/Hindi/Odia together. An
  operator can choose one of those supported languages before starting a
  worker by setting `SURYADEV_CAPTION_LANG` in its PowerShell environment.
  Missing captions in that language are a clean failure; no fallback silently
  generates extra requests.
- Disabled automatic yt-dlp HTTP/extractor/fragment retries; added modest
  pacing between requests/subtitle downloads. An HTTP 429 remains a failed
  assignment, not a saved finding.
- Limits the YouTube extractor lane to **one job** at a time, regardless
  of spare CPU. After an observed HTTP 429, the worker records a **one-hour
  cooldown** in `youtube-access-state.json` and will not launch other
  queued YouTube jobs while it is active, including after worker restart.
  This is conservative local load reduction, **not a promise** that the
  provider will allow access when the timer expires.
- Websites and PDFs are not paused by YouTube's separate access restriction.
  The dashboard shows the cooldown and never calls it successful learning.
- Adds a lock-protected, explicitly operator-initiated `retry-failed <id>`
  command, accepted only for a failed YouTube job and only after both the
  job's HTTP 429 age and the persisted cooldown permit an attempt. The prior
  failure is preserved in `job_attempt_history`; no automatic retry or
  duplicate new assignment is created.

### Install a supported free JavaScript runtime

The official yt-dlp EJS guide documents that pip packages need
`yt-dlp[default]` to include `yt-dlp-ejs`; Deno 2.3 or later is
recommended and enabled by default. Missing JavaScript support is a
**compatibility warning**, not a cure for HTTP 429.
See: https://github.com/yt-dlp/yt-dlp/wiki/EJS

Stop the existing worker or mission, then in your SURYADEV Python
environment run:

```powershell
cd "D:\\Work\\SURYADEV"
python -m pip install -U "yt-dlp[default]"
scoop install deno
# Open a new PowerShell session if the deno command is not recognized
deno --version
python suryadev_youtube_preflight.py
```

Do not paste browser cookies or sign-in data into scripts. No special
account authentication or impersonation workarounds are enabled by
SURYADEV. The optional impersonation warning is distinct from the
429 response and is not proof of its cause.

After **at least one hour since the failed job** and only when the
worker or mission is stopped, you can manually try that same job again:

```powershell
cd "D:\\Work\\SURYADEV"
python suryadev.py --data "D:\\Work\\SURYADEV-DATA" retry-failed 6
```

Then start **either** the regular worker or six-hour mission to process
that queued job. If YouTube again responds with HTTP 429, stop requests
and leave the restriction in place. For approved externally obtained
official publisher captions, the separate `import-transcript` path can
save timestamped text evidence without claiming the YouTube video was
watched. The official publisher transcript must be obtained lawfully.

Dashboard UI version: `2026-10-21-v6.2-youtube-cooldown`.


## v6.3 · Learning continuity without bypassing YouTube 429

The earlier 60-minute YouTube cooldown is an **outbound caption
rate-limit guard**, not a ban on learning. SURYADEV can immediately study
other **explicitly approved** HTTPS websites, PDFs and opted-in RSS/Atom
entries. It must never treat alternative documentation as a transcript
of the blocked YouTube video; job #6 remains failed until a successful,
operator-authorized retry after the provider restriction.

### Single-command launch after updating your installed files

Stop any old SURYADEV worker or mission first. In PowerShell from the
installed app folder, **explicitly opt in** to the official source pack and
start exactly one continuously refilling worker:

```powershell
cd "D:\\Work\\SURYADEV"
.\\start-continuous-learning.ps1 -DataDir "D:\\Work\\SURYADEV-DATA" -ActivateOfficialTech
```

The dashboard can stay running in its own terminal. The flag adds only the
published official tech URLs/feeds; it will not download the blocked
YouTube subtitle file during the cooldown. A second invocation without
`-ActivateOfficialTech` uses the existing approved plan without modification.
Use Ctrl+C in the launcher window to stop the learning worker.

### Activate a free official technology research pack

The following action is **opt-in**; it merges a bounded set of public
Python, Playwright, GitHub and Cloudflare documentation URLs and the
official Python and GitHub RSS feeds into the **existing** approved
`learning-plan.json`. It preserves the original URLs, feeds,
host allowlist and per-cycle/queue quotas. A preexisting plan is backed
up before atomic replacement. No app process is started or DB reset.

```powershell
cd "D:\\Work\\SURYADEV"
python suryadev_continuity.py --data "D:\\Work\\SURYADEV-DATA" activate-official-tech
```

Sources are independent public documentation relevant to agents,
automation, secure networks and code. New sources are **not**
unrestricted external search results. RSS only admits entry URLs on
explicitly allowlisted hosts, with HTTPS and public-DNS validation.
These publishers may refuse or change URLs: failed reads remain
failed with evidence excluded, never silently marked learned.

### Start one self-refilling worker

After stopping any old mission or worker (dashboard may remain running):

```powershell
cd "D:\\Work\\SURYADEV"
python suryadev_extras.py --data "D:\\Work\\SURYADEV-DATA" worker --plan "D:\\Work\\SURYADEV-DATA\\learning-plan.json" --refill-minutes 5 --interval 10 --no-ollama
```

The worker immediately queues new approved sources, drives separate
website/PDF/YouTube jobs within measured CPU/RAM/disk headroom, and
reloads the plan every five minutes. An observed YouTube HTTP 429 stops
*new YouTube downloads*, but **not** independent Garudanetra or PDF
processing. One process owns the file lock; do not start a second
worker or six-hour mission simultaneously.

The existing six-hour mission also reloads an approved plan every
refill; it can be run with `--refill-minutes 5`. Neither mode can
guarantee endlessly fresh articles: after all approved sources are
learned and RSS has nothing new, the queue will truthfully become idle.
Add more approved sources, feeds or research categories rather than
fabricating completed work.

### No-wait publisher subtitles for the known CS50 video

An explicit `approved_publisher_transcripts` mapping, activated with
the official pack, pairs YouTube video `mgBpcQRDtl0` with the CS50
publisher's official UTF-8 SRT:

`https://cdn.cs50.net/2017/fall/shorts/python/lang/en/python.srt`

The current real-source smoke checks this official SRT independently
and has recorded 778 timestamped cues covering approximately 38m54s
with a verified evidence SHA-256. On starting the single worker or
six-hour mission, the opt-in continuity feeder can **recover an existing
failed YouTube assignment** from that approved publisher file even
during a YouTube HTTP 429 cooldown, without contacting YouTube again.

The recovery preserves the earlier YouTube error in
`publisher_caption_recoveries`, extracts every readable timestamped
cue, verifies and stores the publisher text, and marks the original job
complete with explicit `publisher_transcript_only=true`,
`youtube_extraction_success=false`, and
`full_video_visuals_verified=false`. The task popup explains that
only publisher-hosted captions were obtained, **not** video playback,
full speech, graphics, or BRAHMAGYAN acceptance.

This mapping applies only to that *specific, explicitly approved*
video. Other YouTube videos will require their own legitimate
publisher-hosted transcript approvals; never assume all publishers
offer transcripts, and never use this as a way to bypass YouTube access
restrictions. Publisher failures are recorded with a separate one-hour
retry backoff, while unrelated website and PDF learning keeps working.

### Read status

Dashboard `http://127.0.0.1:8769/` shows YouTube cooldown separately
from *Approved-source continuity*. The read-only API includes
`/api/operations` → `continuity` with last/next refresh, feed
errors and queued counts. It never says a blocked video was fully
watched, visually understood or accepted by BRAHMAGYAN.

`--no-ollama` saves real source evidence with a **preview-only**
summary. To get chunked, locally generated topic summaries, configure
a working compatible Ollama model first and run the same worker
without `--no-ollama` using the installed `--model` option. This does
not prove correctness or complete comprehension.


## Six-hour task renewal outbox (experimental, request-only)

When the opt-in self-refilling worker or the bounded mission has fewer than
three **executable** website/PDF/YouTube jobs (rate-limited YouTube jobs do
not count), it writes one durable six-hour research renewal request:

`SURYADEV-DATA/krishna-mission-renewal.json`

The request is idempotent while pending. The existing TLS-only, approved-reader
`/api/operations` response includes `mission_renewal`, so a future
KRISHNA task dispatcher can see that SURYADEV wants a fresh six-hour batch.
The request records a stable ID, research duration, queue state and whether
publisher YouTube is unavailable; it intentionally contains no credentials.

**Important:** An outbox request is not a delivered message, a KRISHNA
assignment or an acknowledgment. The new feature does **not** enable an
inbound command endpoint, modify approved host policy, start extra workers,
silently enqueue arbitrary internet sources or connect BRAHMAGYAN/Rishi.
`delivered_to_krishna`, `krishna_assignment_acknowledged` and
`brahmagyan_acknowledged` remain false until independent, authenticated
integration exists. KRISHNA must implement its own persistent task backlog,
verified assignment/ACK protocol and source approval before truly providing
back-to-back six-hour missions.

Operator verification after safe Windows deployment:

```powershell
$ops = Invoke-RestMethod "http://127.0.0.1:8769/api/operations"
$ops.mission_renewal | Format-List *
# Local direct inspection, including if dashboard is stopped:
Get-Content "D:\\Work\\SURYADEV-DATA\\krishna-mission-renewal.json"
```

Retain the existing single-worker lock. Never start `suryadev_mission.py`
beside the continuous worker, and never mistake this request for an active
six-hour task contract or a guarantee of six hours of unique source content.


## 2026-10-21 live laptop acceptance and RSS fix

The operator's installed v6.3 laptop reported: 26 completed source jobs,
no failed source jobs; YouTube job #6 recovered from **778 timestamped
official CS50 publisher caption cues** (not video/audio observation).
One independent feeder diagnostic was observed:
`https://github.blog/feed/` exceeded the previous 1 MiB XML cap.
The parser now accepts a bounded **8 MiB maximum uncompressed RSS/XML body**
and still refuses any larger Content-Length/body and compressed responses.
The official GitHub Engineering RSS is also available as an opt-in source
(`https://github.blog/engineering/feed/`) on reactivation of the
official technology pack. The user's actual response length is not yet known,
so a feed over 8 MiB can still produce a truthful per-feed error.

The observed renewal request showed `awaiting_assignment`,
`eligible_queued_or_running=0`, and all KRISHNA/BRAHMAGYAN delivery
acknowledgment flags false. This is correct: the prior 20-item queue
snapshot was recorded earlier in the five-minute refill cycle.
`requested_hours=6` is a desired assignment window, not a verified
six-hour completion guarantee.

After pulling the new PR head, stop the old worker and dashboard
using Ctrl+C in their own terminals before safe install. Run
`-ActivateOfficialTech` again to append the smaller Engineering feed
without replacing existing approvals or SQLite data. Restart exactly one
continuous worker, refresh `/api/operations` after a refill, then
verify evidence integrity. The Core-side paired dispatcher and explicit
acceptance receipt are still needed.


## v6.4: bounded RSS + opt-in KRISHNA six-hour mission relay

- The former 1 MB RSS feed limit is now **8 MiB maximum** (still bounded);
  official GitHub Engineering RSS may be added by re-running
  `-ActivateOfficialTech`, preserving existing plan and SQLite findings.
- Each active worker records a low-water `mission_renewal` request for a
  new six-hour assignment while it has fewer than 3 executable jobs.
- When *and only when* `-CoreMissionConfig` is explicitly configured,
  that same SINGLE worker contacts the approved paired KRISHNA Core over
  pinned HTTPS to request one prepared Core mission. Source URLs must
  exactly match the laptop's owner-approved plan; unknown URLs are refused.
  It never launches another process or bypasses YouTube cooldown.
- Core `SuryadevAgent` can prepare two six-hour research packets from a
  separate reviewed catalogue and supports paired request/delivery ACK.
  The catalogue is **not auto-installed** and finite curricula may run out.
- A Core delivery ACK is not a completed research session or proof that
  BRAHMAGYAN/Rishis ingested anything. Source evidence still requires
  the existing verified learning-bundle contract/receipt.

Full opt-in pairing, HTTPS, source-plan and Core deployment requirements:
`docs/SURYADEV_SIX_HOUR_MISSION_PROTOCOL.md` at the repository root.
**Do not point the TLS-pinned client at the ordinary HTTP port 8766.**
To continue independent learning without verified Core TLS pairing:

```powershell
.\start-continuous-learning.ps1 -DataDir "D:\Work\SURYADEV-DATA" -ActivateOfficialTech
```

After a guarded reinstall, version-check the dashboard for
`2026-10-21-v6.4-rss-and-mission-relay`; this verifies installed
software assets, not an actual KRISHNA-to-laptop assignment.


## v6.5: truthful timing and source-coverage diagnostics

The default `start-continuous-learning.ps1 -ActivateOfficialTech`
**does not use Ollama**: it runs `--no-ollama` unless the owner explicitly
adds `-UseOllama` and selects an already installed model via `-Model`.
In preview mode it saves the complete *extracted* source evidence when
possible, but the per-source result is only a **2,000-character extractive
preview**, never an all-chunk AI study. The per-source `summary_method`
in the database proves which mode actually ran.

The source-ingest rules are:
- PDF: up to 20 MiB and 500 pages; extract text from EVERY page, fail
  if any page lacks selectable text; cap at 220,000 extracted characters.
  Images/diagrams/scans are not verified.
- Website: Playwright navigates with a 25-second navigation timeout and
  then reads visible `main` or `body` text; max 220,000 characters.
  It does not traverse all links or view multimedia; coverage remains
  unverified.
- YouTube: captions in one requested language via yt-dlp, no video media,
  no audio/visual frame processing. Timed cues may be incomplete; HTTP
  429 never triggers an immediate alternate bypass. The CS50 publisher
  recovery provides timed TEXT cues only.

With Ollama enabled, `suryadev_summary.summarize_all` sends ALL extracted
text in sequential chunks of 9,000 characters, up to 25 chunks. Each local
Ollama HTTP generation request has a 120-second timeout. A successful
summary is a model output, not proof of comprehension.

**New timing telemetry applies only to new v6.5 jobs**, not existing
completed/failed entries. The worker stores, in SQLite `job_timing`,
monotonic processing elapsed seconds, acquisition seconds and the summary
phase seconds. These are exposed in read-only
`http://127.0.0.1:8769/api/operations` as `timing.by_source` and
`timing.recent`. Queue-wait time is excluded, and the summary phase can
include local Ollama-lock waiting. Check:

```powershell
$ops = Invoke-RestMethod "http://127.0.0.1:8769/api/operations"
$ops.timing
$ops.timing.by_source
$ops.timing.recent
```

To distinguish prior preview-only jobs from actual model chunk passes,
query the **existing** SQLite findings summary methods read-only:

```powershell
@'
import sqlite3
db = sqlite3.connect(r"D:\Work\SURYADEV-DATA\suryadev.sqlite3")
for method,n in db.execute("SELECT summary_method, COUNT(*) FROM findings GROUP BY summary_method"):
    print(method, n)
print("FAILED JOBS:")
for i,url,error in db.execute("SELECT id,url,error FROM jobs WHERE status='failed' ORDER BY id DESC LIMIT 15"):
    print(i, url[:100], error[:240])
db.close()
'@ | python -
```

RSS articles that merely quote `<!DOCTYPE html>` or `<!ENTITY>`
inside CDATA/comments are now accepted by the parser. Actual XML DTD
or entity declarations are still rejected using expat structural hooks.
An oversized RSS feed is still rejected by the bounded 8 MiB policy.


## v6.6 opt-in multimodal research lab

Source code now includes:
- `suryadev_deep_web.py`: bounded full-scroll same-host website image/style
  loading, image and link inventory, screenshot-by-screenshot **local** vision
  observations. Off-host assets and linked pages remain excluded.
- `suryadev_deep_pdf.py`: every-page pypdfium2 raster/OCR and local Ollama
  vision observations in addition to the existing PDF text extraction. A
  missing page/modality fails closed instead of silently claiming coverage.
- `suryadev_video_lab.py`: lawful local video files with every decoded
  frame hashed, optional sampled or explicitly each-frame local vision,
  user-provided descriptions/comments/timed captions and optional
  pre-downloaded faster-whisper audio model. This local analyzer does NOT
  download YouTube videos or bypass rate limits.
- `suryadev_ingest.py`: publisher description/chapters plus opt-in capped
  50 YouTube public-comment retrieval from the same approved video
  metadata path; captions-only visual/audio coverage remains unverified.

Continuous worker opt-in flags:
`-DeepWeb -DeepPDF -VisionModel gemma3:4b -UseOllama -Model gemma3:4b`
(use only an installed model and required free OCR/PDF dependencies).
Local video command: `python suryadev_extras.py --data ... analyze-local-video
<local-video.mp4> --vision-model gemma3:4b --every-frame-vision
--max-visual-frames 1800` for a small authorized clip, or use sampled
vision for larger videos. Run the heavy video lab only with the ordinary
worker stopped, so one data-root lock is respected.

Audit, dependencies, per-source limits and evidence-truth rules are
documented in the repository root:
`docs/SURYADEV_MULTIMODAL_RESEARCH.md`.
Do NOT load XTUFE or other unaudited browser extension into Garudanetra.


## v6.7: entire books in original order, line by line

SURYADEV includes the **independent free local** `suryadev_book_reader.py`
book ledger (not SoBrief's ten-minute summary API). It accepts operator-
provided DRM-free EPUB, TXT, Markdown and PDF books, indexes **every line**
of the EPUB spine/PDF pages in source order, and does not mark a partial
import successful. For scanned PDFs, use `book-import --ocr-scanned`
with local Tesseract and pypdfium2. Reading uses a separate persistent
`book-learning.sqlite3` and does not modify the web/video evidence DB.

Use `book-import <local-file>` to get a book ID and then
`book-read <book-id> --model gemma3:4b --lines-per-step 1` to send each
line to a locally installed Ollama model with durable after-each-step
checkpointing; the default is until the last line. On interruption
rerunning the same command resumes at exactly the next unread line.
`book-status <book-id>` shows completion and measured seconds;
`book-verify <book-id>` verifies original line hashes and no gaps in
the sequential journal. `--no-ollama` is text recording only, NOT AI
reading. No complete knowledge or BRAHMAGYAN acceptance is claimed.

This workflow is opt-in and obeys the same single-worker data-root lock:
stop the continuous website worker before a long book reading session.
See the full deployment and use guide in
`docs/SURYADEV_BOOK_LINE_BY_LINE.md` at the repo root.


## v6.8: integrated book learning and BRAHMAGYAN candidate receipts

The earlier v6.7 instructions for a manual `book-read` command still work,
but books may now join the SAME continuous worker using explicitly approved
local file hashes, without starting a duplicate process or abandoning the
web/PDF/YouTube queue.

- `book-approve <local-DRM-free-book>`: import every readable line and add
  its absolute source path and SHA to backed-up `book-plan.json`.
- `start-continuous-learning.ps1 -UseOllama -LearnApprovedBooks`: during
  idle approved-source windows, consume one locally installed Ollama
  line-by-line reading step and atomically update the separate book ledger.
- Add `-BookVisuals -VisionModel gemma3:4b` to opt into one image/page
  local model observation per idle book cycle after the text reaches its end.
  The visual audit includes explicit failure if a required illustration,
  inline SVG/MathML or raster page could not be analyzed; semantic quality
  stays unverified.
- Read-only dashboard `#garudanetra` (Books lane), `/api/books` and
  `/api/book-search?q=...` display per-book text progress, figure counts,
  candidate Core receipts and exact source-line SHA citations; CLI
  `book-search "term"` works without the dashboard.
- `-SyncBookHandoff` is only accepted with an explicitly approved book
  plan and an independently paired, pinned HTTPS
  `-CoreMissionConfig`. It routes full-book candidate knowledge through
  KRISHNA's existing BRAHMA/Rishi intake and verifies Core's canonical
  bundle SHA receipt before recording a locally acknowledged delivery.
  The books and page images stay on the laptop. A receipt is NOT a
  validated scientific or factual understanding certification.

Full owner approval, long-running book OCR/vision and SSL/pairing
requirements: `docs/SURYADEV_BOOK_LINE_BY_LINE.md`.
Never declare the physical laptop rollout or Core connectivity tested
based only on CI success.


## v6.9 — Books inside existing Garudanetra, coverage and hardware panels

Garudanetra now contains a fourth Books workspace lane, integrated
book checkpoints and read-only book citation search; the separate Book
learning sidebar and panel have been removed. Source Coverage reports
indexed, completed, pending and failed book reading separately from normal
website, PDF and YouTube jobs. Laptop Health shows measured local Ollama
book work and visual observations; a stopped worker and empty queue
truthfully show zero live work even when measured hardware utilization is low.

Imported books in SURYADEV-TEST-DATA do not appear in SURYADEV-DATA;
explicitly approve a real book in the production data root.

## 13-source hardware-adaptive learning load check (3 PDF / 2 web / 5 books / 3 YouTube)

The same single Learning Intelligence UI and dashboard-managed worker execute
approved sources under measured 85% CPU/RAM/disk/GPU admission. The configured
125-workload ceiling is NOT a claim of 125 actual runnable laptop tasks.

From the **already verified portable installed app**, use the PowerShell
`START_SURYADEV_13_SOURCE_CHECK.ps1` launcher. It can bring the local canary
dashboard back on `127.0.0.1:8872` without touching the persistent
`data` directory or opening a duplicate service. It does not update app
files while the worker is running. `-DashboardOnly` only opens/reuses the
dashboard and does not require a full 13-source curriculum.

```powershell
$root = 'D:\\Work\\SURYADEV-FLEET-CANARY-20261025'
& "$root\\app\\START_SURYADEV_13_SOURCE_CHECK.ps1" -Root $root -DashboardOnly
# after explicit source approvals, run from another shell:
& "$root\\app\\START_SURYADEV_13_SOURCE_CHECK.ps1" -Root $root -Model auto -Minutes 45
```

The full test **requires exactly 3 fresh, owner-approved PDF URLs, 2 fresh
website URLs, 3 fresh YouTube URLs**, plus **5 SHA-256-approved local books** in
`data/book-plan.json`. Extra historical approved sources may remain;
`suryadev_workload_benchmark.py` selects the first suitable sources unless
an explicit selection manifest (`--manifest`) is provided. A completed or
failed old source URL cannot count as new throughput. The helper will print
what is missing and refuse to fake timings.

Use the existing operator-approved backend sources and CLI
`suryadev_extras.py --data <data> book-approve <bookfile>` to approve each
local supported TXT/MD/PDF/EPUB source while **the worker is stopped**.
No frontend manual source controls are added. If approved books exist, one
dashboard-managed collector will now attach `--book-collect-plan` for
**indexing only**; local-model mode attaches `--book-plan` for checkpointed
reading. The five-book model inference path is serialized on the shared
model lock; five concurrent *source preparations* are not five parallel LLMs.
`auto` chooses a locally installed eligible model or collector without
downloading anything. If it chooses collector, deep book comprehension is
NOT tested or claimed.

Video visual-observation automation is enabled only for exactly approved
YouTube URLs, and can stop with 429/provider restrictions. When the
existing dashboard was started without `--auto-approved-videos`, restart
the single dashboard through its normal controlled lifecycle before claiming
video observation was enabled. Source captions are separately audited from
actual observation; an `AWAITING_SERVER_ACK` status is NOT knowledge mastery.

The read-only benchmark samples hardware, admission slots, queued and active
workloads, website/PDF/caption timing receipts, book lines/model status,
video observation and source SHA verification. It writes timestamped JSON
under the sibling `benchmark-reports` folder and **does not kill, reset,
or automatically restart** the worker on timeout. It distinguishes
`collection_complete_no_book_model` from model-processed work,
`terminal_with_failures`, and `time_limit_reached_jobs_may_still_be_running`.
No elapsed-time target, deep learning certificate, full audiovisual
coverage or independent Rishi examination is inferred.


### Repair missing book-plan.json without touching completed evidence

A healthy worker may report `actual_slots=4` with `WorkerRunning=True`
yet the 13-source preflight will correctly refuse to run because no five-book
owner approval file exists. This is **source authorization**, not a worker error.

The operator can explicitly approve this *fixed*, reviewed test curriculum:
5 Green Tea Press full technical books (Think Python, Think Stats, Think Bayes,
Think Complexity, Think DSP), three short arXiv technical PDFs (Attention, LoRA,
BERT), two Python official docs pages, and three CS50P YouTube lectures. The
script is opt-in, makes a pre-change backup of `learning-plan.json`, stores
full local books with SHA-256 pins, and preserves all prior SQLite evidence.
It does not silently add sources, enable paid services, bypass YouTube 429 or
run a second worker.

With **the current dashboard still open**, use its **Stop learning** control;
verify `/api/learning/control` reports `managed_running=False` and
`external_worker_active=False`. Keep the dashboard process alive. Then:

```powershell
$root='D:\\Work\\SURYADEV-FLEET-CANARY-20261025'
$py="$root\\.venv\\Scripts\\python.exe"
$data="$root\\data"
$app="$root\\app"
& $py "$app\\suryadev_benchmark_prepare.py" --data $data --show
# Review all exact licensed publisher/source URLs, then expressly authorize:
& $py "$app\\suryadev_benchmark_prepare.py" --data $data --approve-curated-trial
& $py "$app\\suryadev_workload_benchmark.py" --data $data `
  --manifest "$data\\benchmark-13-manifest.json" --preflight
```

If the PDF book reader reports `ModuleNotFoundError: pypdf`, install this free
local Python package into the active canary virtual environment before
approving books: `& $py -m pip install pypdf`. A transient publisher failure
must remain a real failed download; no synthetic book content is substituted.

Once preflight succeeds, use the **same existing dashboard** to start a single
`auto` worker; if the selected local model is unsupported/uninstalled, use
`collector` for evidence-only acceptance and separately test model reading.
The explicit manifest is necessary to exclude the historical Python/about
and W3C dummy-PDF runs from a fresh timing test:

```powershell
& "$app\\START_SURYADEV_13_SOURCE_CHECK.ps1" -Root $root -Model auto `
  -Manifest "$data\\benchmark-13-manifest.json" -Minutes 45
```

The benchmark writes read-only 15-second snapshots in the sibling
`benchmark-reports` folder. Full five-book model reading may take longer
than 45 minutes; the report documents partial lines accurately.
The current `complete_verified`, visual-coverage and independent Rishi
acceptance gates remain false without actual supporting evidence.


### Full-book PDF frontmatter: verified blank pages versus scanned material

For the explicit 13-source trial, a real PDF may include an intentionally
blank page (for instance the second page of Think Python 2e). It must not
be incorrectly marked as an OCR error, and a scanned diagram must not be
quietly omitted. Import now distinguishes: (a) no page-content painting or
annotations — structurally verified blank; (b) a **completely white** locally
rendered page — visually verified blank; (c) a page containing visible
content but no selectable text — OCR required; (d) failed/OCR-empty content —
block approval and preserve the original source.

The existing `book_lines` ledger records a verified blank page using its
original page number, a `[verified blank: ...]` section tag and zero-length
source text. No generated page text is substituted; text/image/comprehension
mastery remains unverified until its separate evidence and Rishi stages.
Nonblank figures and scanned text cannot pass as blank.

The free optional renderer `pypdfium2` verifies white page images; it is
required when a page is not provably structurally blank. Only pages with
actual non-white content need the **additional** local `pytesseract` Python
package and installed Tesseract OCR executable. Do not automatically install
an unknown executable or bypass OCR warnings. With the worker stopped:

```powershell
$root='D:\\Work\\SURYADEV-FLEET-CANARY-20261025'
$py="$root\\.venv\\Scripts\\python.exe"
& $py -m pip install pypdf pypdfium2
& $py "$root\\KRISHNA-CORE\\standalone\\suryadev\\suryadev_benchmark_prepare.py" `
    --data "$root\\data" --approve-curated-trial
```

If an actually scanned/illustrated page requires OCR, install
`pytesseract` using pip **and** a verified local Tesseract OCR binary, then
retry. Downloaded PDFs already validated and saved are reused; never wipe
`benchmark-books`, SQLite, or the source plan. Runtime installation from the
feature branch should occur only after the canary regression tests pass.


### YouTube ads, stalls and exclusive worker-lock contention (fleet-adaptive)

The SOURCE of the earlier no-learning failure is not proven to be an ad.
The laptop dashboard's *legacy standalone video auto scheduler* had started
`approved-video-67f8dd17a7b32fd2` before the main learning worker, taking
SURYADEV's **one canonical OS lock** while the site showed no confirmed
captions, transcript chunks, or frames. This prevented 3 PDFs, 2 websites
and five books from being admitted even when CPU/RAM were safe.

**Corrected ownership:** in `fleet_adaptive` profile, the dashboard never
starts a standalone video subprocess. All approved video observations
are admitted ONLY by the main `ParallelVideoReader` under its existing
single-worker supervisor lock and hardware admission. The same supervisor
can schedule website/PDF and verified book model work as separate queues.
A previously active legacy observer is reported as active and must finish or
be explicitly stopped on the owner's Windows PC; this patch does not kill
unrecognized processes or silently replay a partly viewed video.

**Video reliability:** the Playwright adapter measures when YouTube actually
reports an `.html5-video-player.ad-showing` ad. Ad timestamps, captions
and frames are **excluded from the source learning record**. Ads that
persist beyond 120 wall seconds or lectures with no content-clock progress
for 60 seconds exit that video observation with an explicit reason,
not a fake completed lesson. The canonical evidence validator refuses
a bundle with zero real learning chunks AND zero visual observations.
It never clicks or fast-forwards ads, pretends a provider restriction is
comprehension, ignores HTTP 429 or claims that all captions were captured.
`/api/youtube/audit` now exposes the stopped reason, ad event count,
wall seconds, and whether filtering was requested. Live Playwright
backends and YouTube behavior must still be checked on the actual laptop.

**Optional reviewed GitHub content blocker:** The official open-source
[uBO Lite](https://github.com/uBlockOrigin/uBOL-home) from
[gorhill/uBlock (MV3 source)](https://github.com/gorhill/uBlock/tree/master/platform/mv3)
uses declarative Manifest V3 rules. SURYADEV supports it ONLY if the
owner has separately obtained/built/reviewed an **unpacked** uBO Lite
Chromium directory and explicitly opts in by setting
`SURYADEV_UBOL_EXTENSION_DIR` to its absolute local path before starting
the dashboard. This is optional; no extension is downloaded, installed,
auto-updated, or granted access to KRISHNA credentials by the code.

```powershell
# SAMPLE PATH ONLY — review the real official extension directory first
$env:SURYADEV_UBOL_EXTENSION_DIR = 'D:\\Tools\\uBOLite.chromium'
# Then restart the ONE existing dashboard through its controlled
# single-node launch, and use Start Learning there.
```

The adapter verifies a bounded Manifest V3 extension with
`declarativeNetRequest`, denies unexpected privileged native messaging/
debugger grants, and loads it only in an isolated Playwright **Chromium
persistent context**, as documented by Playwright. Its actual filtering
effectiveness and provider availability are NEVER asserted just because an
extension was present. Do not install unrelated unofficial CRX mirrors.

**Canary after updating installed app while dashboard/worker are stopped:**
check `/api/learning/control` for `managed_running` and
`external_worker_active`, then start exactly one approved local worker,
observe the feeder registering fresh PDF/web assignments, separate book
journal `ollama:<model>` lines, and `/api/youtube/audit` for real video
evidence/failures. The original previously attempted video is **not**
silently retried after a failed/partial observation. A new one-time
owner-approved attempt or a different approved video is needed; do not
erase the previous evidence or alter the attempt journal.


### Diagnostic fix: video observer exited but audit stays pending_or_running

An approved YouTube review has THREE independent state sources:
`data/video-review/approved-inbox/approved-video-*.json` (staged jobs),
`data/video-review/runtime/jobs/<job_id>/worker-report.json` (canonical
completion/error/evidence receipt), and
`data/video-observer-attempts.json` (immutable once-only attempt history).
Historically, `/api/youtube/audit` labeled a staged job with no canonical
report `pending_or_running`, **even after** the subprocess failed, the
parent lost its only ephemeral `finished` result on the next tick, or
the child was interrupted. This was a reporting defect, not proof of
continued playback.

The adaptive supervisor now retains bounded per-job outcomes in
`data/video-observer-outcomes.json`, with failure reason and timestamp,
and publishes current `active_job_ids` in the 15-second
`video-concurrent-runtime.json`. The read-only YouTube audit and dashboard
video panel distinguish `worker_failed`,
`attempted_no_final_receipt`, `running_without_final_report` and
`approved_not_started`; the canonical worker report remains authoritative
when present. A corrupt diagnostic-journal file must NOT stop healthy
website/PDF/book lanes; preserve it for inspection.

**Safety boundary:** no new YouTube request is made merely to fix
telemetry, no old attempted job is silently replayed, no captured media or
SQLite evidence is deleted, and the dashboard cannot claim caption
comprehension/Rishi exam without real evidence.

An operator can inspect the three exact IDs by:
```powershell
$root='D:\\Work\\SURYADEV-FLEET-CANARY-20261025\\data'
@('approved-video-bceb228031b31d0b',
  'approved-video-67f8dd17a7b32fd2',
  'approved-video-623e9ad6e4fafd06') | ForEach-Object {
  $id=$_
  $p=Join-Path $root "video-review\\runtime\\jobs\\$id"
  [PSCustomObject]@{
    Video=$id
    WorkerReport=(Test-Path (Join-Path $p 'worker-report.json'))
    LearningBundle=(Test-Path (Join-Path $p 'learning-bundle.json'))
    PlaybackSpeed=(Test-Path (Join-Path $p 'playback-speed.json'))
  }
} | Format-Table -AutoSize
Get-Content (Join-Path $root 'video-concurrent-runtime.json') -ErrorAction SilentlyContinue
```

Deploy only after stopping the dashboard and observer gracefully, updating the
tested portable install and restarting exactly ONE dashboard. The previously
attempted three videos may need additional *new* approved sources or
owner-reviewed one-time retry after diagnoses. Video site restrictions
and missing audio/captions remain possible and must stay visible as failures.


### Verified 26 October canary: 8-second YouTube stall and caption-size failure

The physical canary demonstrated **three distinct conditions**:
- YouTube caption job #8 failed with
  `ValueError: Caption transcript exceeds supported full-processing budget`
  (formerly 220,000 characters). The extraction and bounded summarization
  pipeline now accepts up to 1,000,000 characters of full timed caption text
  without silently deleting later captions. It still requires actual locally
  serialized model calls for every segment, and errors above that honest
  ceiling; 2B-model processing time may be substantial.
- Observers for Conditionals/Loops reported
  `content_playback_stalled` at roughly 8 seconds, with 0 recorded captions,
  1 screenshot and no verified lecture content. Older runtime marked these
  `AWAITING_SERVER_ACK`. **New worker and the KRISHNA Core candidate intake
  both reject stalled/advertisement-wait/no-snapshot bundles**, and they require
  meaningful temporal coverage for a captionless visual-only session.
  Existing canonical worker reports are retained, but the dashboard and
  YouTube audit display `INCOMPLETE_STALLED_OBSERVATION` rather than a
  success-like status.
- A third observer produced a `playback-speed.json` at 7.59 seconds but no
  canonical report/bundle; the durable observer-attempt audit distinguishes
  interrupted/missing-final evidence without inventing a running task.
  The frontend uses per-video canonical reports directly rather than trusting
  the shared `worker-state.json` index, which the physical canary showed
  could omit an otherwise completed concurrent video job.

**Playback investigation:** The canonical adapter now logs HTMLVideoElement
readyState, networkState, MediaError code, paused and advertisement state
along with a bounded stop reason. It does not fake audio/caption data or
bypass a provider block. If the default bundled Chromium lacks the relevant
media codec, Playwright officially supports installed Google Chrome and
Microsoft Edge channels with different codec coverage. The owner can
OPTIONALLY compare the actual local Chrome/Edge browser by setting this
environment variable **before launching the one supervisor/dashboard**:

```powershell
$env:SURYADEV_VIDEO_BROWSER_CHANNEL = 'chrome'  # OR 'msedge'
```

This **does not** install a browser, replay old videos, or guarantee playback.
Chrome/Edge cannot load the optional unpacked uBO Lite Chromium extension
through Playwright's extension-side-loading flags. If
`SURYADEV_UBOL_EXTENSION_DIR` is configured, leave the browser channel
unset or choose `chromium`; combining a branded browser with side-loaded
uBO Lite fails closed instead of silently disabling the extension.
Compare the source's normal YouTube playback in the same browser manually,
then inspect the **new** read-only `/api/youtube/audit` fields:
`stop_reason`, `last_media_diagnostic`,
`browser_channel`, `caption_or_asr_source`,
`learning_candidate_chunks` and `visual_frame_samples`.

**No automatic retry of the original three attempts:** both previous
`AWAITING_SERVER_ACK` and failed/attempted video files are preserved.
A supervised owner-reviewed fresh attempt is required; do not edit/delete
historical worker reports or attempt journals to force replay. Normal
approved source/PDF/book work can continue independently.


### Fresh Chrome/Edge 50-second playback probe, then one new approved video

The fixed original CS50P trio is **historical** and must not be replayed by
clearing worker journals. A separate previously defined SURYADEV test source,
`https://www.youtube.com/watch?v=VZ5LU8vHT0s`
("Playwright Python 1 | Getting Started" from Automation Step by Step), is a
fresh diagnostic candidate. The free tutorial is ~44 minutes, but the first
50 seconds suffice to discriminate an eight-second media-clock stall from
normal browser progress. **A successful probe is not a learned lecture.**

With the original dashboard learning worker gracefully stopped and the
dashboard PowerShell process closed, update the feature checkout and the
marked portable app, preserving the existing data directory. Then, while
both dashboard and worker are **still stopped**, run:

```powershell
$root='D:\\Work\\SURYADEV-FLEET-CANARY-20261025'
$py="$root\\.venv\\Scripts\\python.exe"
$data="$root\\data"
& $py "$root\\app\\suryadev_video_browser_probe.py" `
  --data $data --channel chrome --seconds 50 `
  --video 'https://www.youtube.com/watch?v=VZ5LU8vHT0s' `
  --approve-after-passing
```

The probe uses the **same global worker lock**, requires the 85% hardware
admission guard, opens one **locally installed branded Google Chrome** in a
throwaway fresh profile, records only browser ready/network/error/media-clock
samples and advertisement visibility, and saves a timestamped JSON to
`data/benchmark-reports/video-browser-probe-chrome-*.json`. It never
downloads raw video, skips advertisements, reads an authenticated browser
profile, modifies historical source artifacts, claims full understanding, or
bypasses YouTube access rules. An optional `--channel msedge` comparison
uses a separately installed Edge browser. Its browser channel never loads
the optional uBO Lite extension.

The **explicit** `--approve-after-passing` opt-in stages this exact new
public video in `learning-plan.json`, with the existing plan's automatic
backup, **only if** the actual requested watch page shows 30+ seconds of
non-ad source-video clock advancement and no media error. Failure leaves
the approved curriculum unchanged and writes a diagnostic report.

On success, restart **one** dashboard via the existing
`START_SURYADEV_13_SOURCE_CHECK.ps1 -DashboardOnly` launcher and then use
the UI's **Start learning** control (with model `auto` or an installed
lightweight model). Hardware-admitted lanes will then schedule the newly
approved video observation, caption extraction, and other pending sources,
preserving the previous three attempts. After a real session, examine
`/api/youtube/audit` for stop reasons, caption chunks, true content-clock
coverage and BRAHMAGYAN/Rishi pending status. **An approved video or a
browser probe passing alone never proves full video learning.**
