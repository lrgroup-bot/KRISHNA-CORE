# SURYADEV v6.7 — Complete local book reading, in source order

## Purpose and provenance
Use the local-first book approach rather than importing SoBrief's ten-minute
summaries as a substitute for the underlying text. SoBrief is a commercial
summary/reading product, not a verified free whole-book parser. The open-source
projects Morpheis/bookworm (sequential no-lookahead reading/journal, but
Anthropic API dependency) and subev/libratory (OCR and local books) were used
as DESIGN references; this is an independent Python implementation.

**Supported books**: operator-supplied and legally held **DRM-free** TXT, MD,
EPUB and PDF up to 100 MiB. Never scrape copyrighted books, remove DRM,
download unknown files, or transmit text to cloud AI. Existing Ollama is
loopback-only. Reading progress is saved under existing
`D:\Work\SURYADEV-DATA` in a NEW `book-learning.sqlite3` file. Do NOT
delete/change the original `suryadev.sqlite3` job/evidence database.

### Complete start-to-end sequence
1. Operator selects a book file; `book-import` SHA-256 fingerprints it.
2. EPUB parses the book's OPF spine **in defined reading order**. Every
   XHTML spine item is extracted into source-numbered physical/logical lines;
   scripts/styles are omitted as non-reading content. EPUB media not readable
   as text causes a fail, not a skipped chapter.
3. PDF extracts page 1 through final page; every page must contain selectable
   text or, with `--ocr-scanned`, have locally OCR-detected text. The engine
   does not mark a book indexed if any PDF page is unreadable.
   TXT/MD preserve all original text line boundaries, including blanks.
4. An atomic SQLite import creates every numbered line with its SHA-256,
   chapter/page position and overall book fingerprint. Zero partial books
   survive an import error.
5. `book-read` starts at line 1 or the persisted next unread ordinal.
   Default `--lines-per-step 1` gives the local Ollama model one complete,
   numbered source line at a time; never passes any future text. Larger steps
   send every included line in order with explicit ordinal labels. The
   model response, exact evidence digest, time in seconds, and next pointer
   are committed together. Network/model errors leave the cursor unchanged.
6. Resume repeats only the interrupted line/step; never skips a line or
   silently truncates prompt text. `book-verify` rechecks original indexed
   line hashes plus the chronological, contiguous reading journal.
7. `book-status` gives processed/remaining lines, percent, elapsed model
   seconds, average seconds per line, and reached-end state for each model.
   `extractive_record_only` is a separate session and **does not count as
   AI examination**. The `BRAHMAGYAN` ACK flag remains false until a real,
   verified external intake and assessment has occurred.

A model's line-by-line response does not prove deep comprehension. A PDF
text/OCR pass does not guarantee understanding its charts/images/equations;
SURYADEV's separate opt-in deep-PDF vision pathway is required for such
observations, with independent verification still pending. EPUB footnotes,
images, MathML and complex navigation also require an additional multimodal
quality gate before claiming full semantic understanding.

## Laptop commands (after PR tests pass and install updated source)
Stop SURYADEV worker and heavy local video jobs with Ctrl+C (the existing
single-worker lock prevents unsafe competing work). Leave persistent DATA
untouched. Install from the existing feature branch:

```powershell
cd "D:\Work\SURYADEV-SOURCE"
git pull --ff-only origin feat/suryadev-standalone-laptop-20261019
cd "D:\Work\SURYADEV-SOURCE\standalone\suryadev"
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-windows.ps1 -InstallDir "D:\Work\SURYADEV" -DataDir "D:\Work\SURYADEV-DATA"
```

Import any book you already own and are allowed to process:
```powershell
cd "D:\Work\SURYADEV"
python suryadev_extras.py --data "D:\Work\SURYADEV-DATA" book-import "D:\Books\my-book.epub"
# PDF with scanned pages, if local Tesseract and Python OCR prerequisites exist:
python suryadev_extras.py --data "D:\Work\SURYADEV-DATA" book-import "D:\Books\my-book.pdf" --ocr-scanned
```

Copy the `book_id` exactly from import output. Confirm `ollama list`
contains a local model and start processing each line in order:

```powershell
python suryadev_extras.py --data "D:\Work\SURYADEV-DATA" book-read "BOOK_ID_FROM_IMPORT" --model "gemma3:4b" --lines-per-step 1
```

For a long book, one model call per line may require MANY HOURS/DAYS.
To process every line, but group related consecutive lines into one bounded
Ollama call, use `--lines-per-step 20`. There is no hidden first-2000-
characters preview or 220,000-character whole-book cutoff; model prompts
over 12,000 characters are refused without advancing the checkpoint.
`--max-steps 10` processes exactly the next ten steps then exits normally;
omitting it continues to the book's last line. Restart the same command
to resume; model identities have distinct reading cursors.

Read-only status and integrity:
```powershell
python suryadev_extras.py --data "D:\Work\SURYADEV-DATA" book-status "BOOK_ID_FROM_IMPORT"
python suryadev_extras.py --data "D:\Work\SURYADEV-DATA" book-verify "BOOK_ID_FROM_IMPORT"
```

**No Ollama mode** `--no-ollama` is an evidence recording tool only. It
must not be described as AI reading or learning.

## v6.8 — Books join the continuous learner (opt-in)

The book engine is now integrated with SURYADEV's ONE existing worker,
not a second background service. All four components are included in
the guarded Windows installer:
- `suryadev_book_reader.py`: durable complete text index, per-line journal,
  source digest, source-line search and exact reading-time counters.
- `suryadev_book_continuity.py`: only owner-approved absolute local book
  paths with SHA-256 fingerprint. Schedules **one local model step** when
  normal approved web/PDF/YouTube queues are idle. No manual six-hour reset,
  no duplicate new worker, no unapproved book discovery.
- `suryadev_book_visuals.py`: optional every-page local PDF page vision/OCR,
  and original-spine-order EPUB referenced image interpretation. Stores
  independent per-item image hashes and resume markers. Inline SVG/MathML,
  CSS background art and externally hosted assets are not automatically
  supported; the audit rejects problematic markers rather than silently
  claiming all images were understood.
- `suryadev_book_handoff.py`: **explicit owner opt-in** to route locally
  acquired book model observations and selected figure SHA metadata through
  KRISHNA's existing paired `/api/suryadev/learning-bundle` route. It
  rechecks SHA-256 of the book, requires reading to have reached the last
  line, and validates `job_id`, canonical bundle digest, positive chunk
  count and real `SURYA-ACK-` receipt. A candidate routing receipt is NOT a
  Rishi factual-validation/comprehension certificate.

### Operator approves a book in one step

Stop any existing SURYADEV worker with Ctrl+C, preserving
`D:\Work\SURYADEV-DATA` (the lock protects a running worker). After
pulling and passing the guarded installer, copy your DRM-free/authorized
book to the laptop's local `D:\Books` folder and run:

```powershell
cd "D:\Work\SURYADEV"
python suryadev_extras.py --data "D:\Work\SURYADEV-DATA" book-approve "D:\Books\my-book.epub" --lines-per-step 1
```

For a scanned PDF that has pages without selectable text, install local
Tesseract + pypdfium2 + pytesseract, then use `book-approve
"D:\Books\my-book.pdf" --ocr-scanned`.
The command validates the entire text, registers every line, and writes
`D:\Work\SURYADEV-DATA\book-plan.json` with the canonical local
source path and SHA-256. Additional explicit approvals append to that plan
after preserving a timestamped backup. Changed previously approved files
require operator review; they are never silently re-approved.

### Automatic learning alongside normal research

After confirming an **installed local** Ollama model in `ollama list`:

```powershell
.\start-continuous-learning.ps1 -DataDir "D:\Work\SURYADEV-DATA" `
  -ActivateOfficialTech -UseOllama -Model "gemma3:4b" `
  -LearnApprovedBooks
```

This reads approved books sequentially during idle periods and resumes
from exact saved line checkpoints. It does not starve the normal web queue,
does not acquire books from paid/download services, and does not mark
preview-only runs as learning. The model cannot be guaranteed to understand
everything simply because every line was processed.

To additionally audit one image/page per idle book cycle (requires installed
local image-capable model, Pillow, pypdfium2, pytesseract and Tesseract):

```powershell
.\start-continuous-learning.ps1 -DataDir "D:\Work\SURYADEV-DATA" `
  -ActivateOfficialTech -UseOllama -Model "gemma3:4b" `
  -LearnApprovedBooks -BookVisuals -VisionModel "gemma3:4b"
```

Manual deep book-visual pass also exists:
`python suryadev_extras.py --data ... book-visuals <book-id>
--model gemma3:4b --max-items 0`.
The visible dashboard at `http://127.0.0.1:8769/` now contains a
**Book learning** panel, backed by read-only `/api/books`, along with
`/api/book-search?q=<term>` that returns the exact source line, chapter/
page citation and line SHA. The equivalent local CLI is
`book-search "my technical term" --limit 20`.

### Opt-in BRAHMAGYAN handoff, not automatic by default

Only after both machines have been formally paired, and KRISHNA is
really accessible through an owner-verified TLS-pinned HTTPS listener,
may the owner add the following flags to the *same* learner:

```powershell
-CoreMissionConfig "D:\Work\SURYADEV-DATA\paired-core-mission.json" `
-SyncBookHandoff
```

The Core transport uses the existing pair-checked route, not a second
Rishi/knowledge authority. Book data remain local if either flag is
absent. `/api/operations` exposes `book_continuity` and
`book_handoff`; candidate receipt status is not factual acceptance.

### What still needs real-device verification

GitHub's Windows and Ubuntu CI tests exercise fake model/website/media
adapters and expected receipts. They **cannot** prove that:
- the actual laptop has enough CPU/RAM to finish a multi-hundred-page
  PDF's OCR/vision or many thousands of line-by-line Ollama calls;
- the purchased/publisher-controlled YouTube video can lawfully be
  fetched or decoded, or that all 429 constraints can be lifted;
- a vision model understands every equation, diagram, SVG or image;
- the Main Core TLS-pairing config is already running on the laptop;
- BRAHMAGYAN and the Rishis independently verified all model output.

Those remain live acceptance gates for an operator, not fake 'all green'
claims. No source file, user data, database, or old journal is deleted
during a safe install.


## v6.9 — Integrated learning dashboard

The standalone Book learning section and its sidebar link are removed. The
existing Garudanetra area has four lanes: Websites, YouTube, PDF, and Books.
Indexed-book checkpoint cards and source-line search live inside Garudanetra.
Source Coverage adds a separately counted Books card. Laptop Health reports
actual model-processed source lines, book figure observations, Ollama inference
seconds and averaged time per processed line. No completion means verified
semantic comprehension or factual acceptance by BRAHMAGYAN.

An idle browser with zero queued and running jobs is correct even when CPU
and RAM have ample headroom. Without an active learning worker, allowed
processing slots are unavailable; history remains displayed. Historical
successes are not active Chromium tabs.

The three-line test book in D:\\Work\\SURYADEV-TEST-DATA is intentionally
separate from D:\\Work\\SURYADEV-DATA. Approve a lawful local book against
the production data directory before expecting it in the main dashboard.
After pulling, rerun install-windows.ps1 with the worker stopped to deploy
updated local dashboard JS, CSS and Python modules.
