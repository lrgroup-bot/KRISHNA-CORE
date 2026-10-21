# SURYADEV v6.6: research-grade multimodal evidence (opt-in)

## Scope and trust boundary

This is part of the **existing** standalone SURYADEV / Garudanetra
implementation, not a duplicate browser or knowledge authority.
BRAHMAGYAN and its existing Rishi council remain the knowledge-review
authority. All source text, visual interpretations, captions and comments
are **untrusted evidence**, not new operator instructions.

There is no such thing as fully guaranteed comprehension of all diagrams,
audio or pixels simply because a model was asked to inspect them. Reports
distinguish acquisition, OCR, model attempts, elapsed processing time and
externally verified BRAHMAGYAN acceptance.

### Why XTUFE is not installed

As verified 2026-10-21, `XTUFE/YouTube-Premium-XTUFE` on GitHub
advertises a Chrome ad blocker, sponsor skipper and download hooks, but
the public repository shows only one README file and no auditable
extension manifest/scripts. This is not sufficient provenance to inject
unknown code into Garudanetra or grant it browser permissions. Do NOT
download a README-advertised ZIP or install it on the learning machine
without a separate security review. Ad blocking cannot solve YouTube
HTTP 429 or authorize bypassing DRM/permissions.

FOSS research reviewed:
- `FreeTubeApp/FreeTube`: optional **independent** privacy-oriented
  ad-free viewer; not a SURYADEV extractor or a substitute for provenance.
- `yt-dlp/yt-dlp`: existing approved-source caption extraction, now also
  includes publisher-provided description/chapters from the same request;
  comments are sampled only when explicitly enabled (max 50).
- `SYSTRAN/faster-whisper`: optional local transcription of a **lawfully
  available local file** with a preinstalled model; no hidden model download.
- `ocrmypdf/OCRmyPDF`: useful scanned-PDF tool, not embedded as a new
  conflicting PDF engine; our opt-in path uses pypdfium2+pytesseract
  for per-page raster/OCR, plus the existing pypdf source text.
- OpenCV / Playwright: local frame decoding and the existing
  canonical Garudanetra browser respectively.

## Opt-in Windows prerequisites

Stop the single existing worker and dashboard with Ctrl+C before the
guarded installer; keep `D:\Work\SURYADEV-DATA` and
`suryadev.sqlite3` intact. First install optional **free** libraries
into the same Python environment that launches SURYADEV:

```powershell
python -m pip install pypdfium2 pillow pytesseract opencv-python
# Only if local audio ASR is wanted:
python -m pip install faster-whisper
tesseract --version
ollama list
```

Tesseract OCR is a **separate Windows executable**; install from a
trusted official distribution if not already present. Its OCR language
packs are separate. A local Ollama image-capable model such as
`gemma3:4b` must actually appear in `ollama list`. Do NOT point
document pages or footage to unapproved paid/cloud vision services.

### Deep webpage/PDF continuous learner

Once the feature branch has passed tests and been safely installed:

```powershell
cd "D:\Work\SURYADEV"
.\start-continuous-learning.ps1 -DataDir "D:\Work\SURYADEV-DATA" `
  -ActivateOfficialTech -UseOllama -Model "gemma3:4b" `
  -DeepWeb -DeepPDF -VisionModel "gemma3:4b" `
  -AnalyzeYoutubeComments
```

These options are **OFF by default** for compatibility with lightweight
laptop operation. Do not start a second worker for the same SQLite root.

Deep webpage mode:
- Reuses exactly one isolated Playwright Chromium / Garudanetra context.
- Loads same-HTTPS-host scripts, styles and images, but continues to block
  cross-host assets, unrelated domains, browser account cookies, media and
  downloads. It does not install any third-party extension.
- Scrolls and checks **every viewport** within a 24-viewport safety budget;
  throws if the page exceeds the budget rather than hiding omitted content.
  Lazy-loaded DOM images and anchor labels are inventoried after scrolling.
- Tries the local vision model on each inspected screenshot. Extracts
  rendered text, links, image alt labels, tables and model observations;
  no auto-follow of discovered pages without owner approval.
- Third-party images, iframe contents, video embeds, inaccessible controls
  and scripts that require interaction are **NOT guaranteed covered**.

Deep PDF mode:
- Downloads only owner-approved public HTTPS PDF URLs (max 20 MiB).
- Runs every PDF page through existing pypdf text extraction, optional
  pypdfium2 rasterization, Tesseract OCR and an **explicit local** vision
  model to inspect page charts, scans, labels, equations and figures.
- Requires **all configured modalities** to succeed on every page; one
  missing page fails the source instead of claiming complete research.
- Applies the existing max 500 pages and 220,000 extracted-text-character
  budget. Split very large documents into operator-reviewed sections; it
  never silently skips the remainder.
- Vision descriptions and OCR can be wrong; full semantic comprehension
  remains explicitly unverified.

Online YouTube jobs:
- Keep existing `yt-dlp` single-language caption acquisition and provider
  HTTP 429 cooldown. Capture video description and chapter titles from the
  same metadata response. `-AnalyzeYoutubeComments` opts into at most
  50 accessible public comments, as unverified opinions, without retry.
- **No claim of frame/audio analysis** from this online-only path. Download
  or DRM bypass is not embedded or done automatically.

### Authorized local-video research: full frame pass

For a **local, lawfully available, operator-provided video**, with optional
timestamped transcript, description and public-comments JSON/JSONL sidecars,
first stop the continuous worker so the heavy local scanner owns the
one-worker lock. Then:

```powershell
python suryadev_extras.py --data "D:\Work\SURYADEV-DATA" analyze-local-video `
  "D:\Videos\authorized-lesson.mp4" `
  --source-url "https://www.youtube.com/watch?v=mgBpcQRDtl0" `
  --title "Authorized lesson" `
  --transcript-file "D:\Videos\lesson.srt" `
  --description-file "D:\Videos\description.txt" `
  --comments-file "D:\Videos\public-comments.json" `
  --vision-model "gemma3:4b" --visual-interval-seconds 1 `
  --max-visual-frames 300
```

It decodes **every frame** (up to 300,000 frames) and records a
rolling SHA-256 chain of every decoded pixel array. At the default
one-second interval, visual semantics are assessed on a **sample**, not
all frames. A one-hour 30-fps video has about 108,000 frames, and
3600 one-second observations before any budget cap; 300 observations
must NEVER be presented as 108,000 visually understood frames.

For a small clip only, require an exact per-frame model attempt:

```powershell
python suryadev_extras.py --data "D:\Work\SURYADEV-DATA" analyze-local-video `
  "D:\Videos\short-authorized-clip.mp4" `
  --vision-model "gemma3:4b" --every-frame-vision `
  --max-visual-frames 1800
```

This mode **refuses** a video when the model-call budget is smaller
than its frame count. Sending 1,800 frame images to a local model is
resource-intensive and may take a very long time; neither a model
reply nor a hash by itself proves all demonstrations were understood.
Every-frame vision is opt-in, never the worker's automatic YouTube mode.

Optional local audio transcription (instead of transcript_file):
`--whisper-model-dir D:\Models\faster-whisper-small`.
The directory must already contain the model; no auto-download.
The system stores a coverage report and text evidence in the same
persistent data root without overwriting the old SQLite findings.
Comment snapshots may be incomplete, are opinions, and are not used to
overwrite verified source statements. No YouTube access request occurs
in local video mode.

## Verification and remaining work

The existing `/api/operations` shows `timing`, source status and
`mission_renewal` (not implied knowledge acceptance). Tests validate
that every page and frame is visited or the audit fails explicitly.

Still needed before promising full unattended end-to-end research:
- Physical laptop image/audio OCR/vision benchmarks and operator review.
- Reliable automatic authorized media acquisition, if the publisher
  provides it without access restrictions or rate-limit violations.
- Evidence-aware extraction from embedded video, CSS backgrounds, complex
  PDFs, external CDNs and interactive websites under explicit approvals.
- Authenticated BRAHMAGYAN/Rishi ingestion and review receipts for the new
  multimodal findings. No automatic promotion of a model observation to
  verified knowledge.
