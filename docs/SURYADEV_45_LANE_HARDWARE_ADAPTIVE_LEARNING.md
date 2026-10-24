# SURYADEV concurrent learning profile — 10 web / 10 videos / 20 PDF / 5 books

**This is a configuration target and a guarded scheduler, not a guarantee
that a 16 GB laptop can run 45 CPU-intensive jobs simultaneously.**

## Ownership

One SURYADEV supervisor and its existing data-root OS lock own all pools.
No second Ollama daemon, scheduler, browser profile outside the approved
workspace, or parallel modification of the same book is created.

- **Web (target 10):** independent lightweight approved HTTPS Garudanetra tabs;
  tab limit scales to at most 10; only measured hardware headroom admits jobs.
- **YouTube video (target 10):** owner must explicitly enable automatic reviewed
  video mode with at least one exact already-approved YouTube URL. The SAME
  supervisor imports durable once-only R39 reviewed jobs and can launch at most
  ten browser video observers. Each uses its own isolated browser profile.
  This is distinct from the **YouTube captions** source lane, which makes at
  most **one provider subtitle request at a time**, pauses on HTTP 429, does not
  retry failed jobs automatically, and cannot claim audio/visual comprehension.
  When the continuous worker owns the OS lock, the dashboard's legacy
  independent video scheduler waits and does not launch another observer.
- **PDF (target 20):** separate approved-source PDF acquisition and parse tasks;
  local model chunk summarization shares one inference lock.
  Scanned pages without required OCR/vision may fail with explicit evidence
  gaps; no false full-coverage mark.
- **Books (target 5):** different source SHA-256s each get their own persisted
  book journal and can import/read in the same worker simultaneously. Five
  concurrent book tasks DO NOT mean five simultaneous Ollama models; expensive
  reading and vision inference share the *same* model lock with the website,
  captions and PDF jobs. Duplicate book bytes are deduplicated by SHA. Strict
  book order and unchanged source verification remain required.

## Hardware admission

Each worker cycle measures psutil CPU, RAM, disk, free space, plus supported
GPU telemetry. Fail closed if CPU/RAM/disk reaches **85%**, if supported
GPU usage/VRAM hits 85%, or if available disk space is <2 GiB. A 2 GiB
operating-system memory reserve is kept in addition to the 15% memory
headroom. The concurrency estimate permits roughly one extra inflight
source task per 1.35 GiB RAM under that reserve, at most half the logical
CPU count. At CPU >=70% or RAM >=75%, newly admitted work is reduced to
one slot. Owner limits reduce this further; never override telemetry.

Pool fairness reserves bounded capacity for books and actual video
observers, leaving a source acquisition slot when at least two slots are
available. The dashboard must show *target 45* separately from *actual
admitted work*, including source, book and browser video tasks. A running
job may complete its bounded work after utilization rises above 85%;
this is an **admission guard**, not a hard OS-enforced per-process CPU/RAM
limit. Runtime protection against thermal spikes, browser crash recovery
and measured per-source memory still requires hardware acceptance.

## Owner setup

1. Pause existing SURYADEV research worker gracefully, backing up the current
   source/data directory; DO NOT delete a worker lock or SQLite WAL files.
2. Pull the development branch and run installer tests before updating the
   installed SURYADEV application directory.
3. Approve sources (exact URLs/hosts) and, for five books, approve five
   legitimately distinct local source files using existing book-approve CLI.
4. Enable reviewed YouTube automatic mode through the local dashboard.
   This is consent to process already approved sources, NOT permission for
   arbitrary new YouTube URLs or bypassing provider authentication.
5. Start ONE worker from the existing dashboard or CLI (with --book-plan to
   enable books). The managed dashboard defaults to target 45 but only runs
   what the 85% guard admits; the explicit legacy profile with max-parallel=1
   remains supported.
6. Inspect /api/operations -> capacity, concurrent_books, concurrent_videos,
   per-source SQLite counts, and the video evidence audit. A running pool
   means work started, not that learning is verified.
7. Verify Core/BRAHMAGYAN acceptance receipts and independent Rishi
   theory/practical exams before marking knowledge learned.

## Acceptance gates before .exe deployment

- Windows 3.11/3.12 and Linux unit checks, Chromium smoke, and real two-PC
  source/video/book trials
- Concurrency measured with 1/2/5/10/20/45 target assignments under
  CPU/RAM pressure, no over-85% new admission and no silent duplicate jobs
- Actual 10 separate approved YouTube browser jobs on *hardware that admits
  them*, with source timestamp, playing versus paused state, frame/caption
  evidence, and no fake mastery
- Safe exit/restart/recovery, SQLite journal order, local provider 429 pause,
  source allowlists, optional pinned-HTTPS KRISHNA ACK
- Never describe candidate summaries as independent BRAHMAGYAN/Rishi exams

**Current real SURYADEV laptop report (2026-10-24): 16 GB RAM,
12 logical CPU threads, 18 website assignments, 0 YouTube/PDF/book jobs,
no authenticated Core or BRAHMAGYAN acceptance.** The code can support the
requested target when released, but this laptop has NOT passed a 45-live-job
benchmark. Do not package a production EXE on the strength of unit tests alone.
