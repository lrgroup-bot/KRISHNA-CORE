# SURYADEV v7 — single GitHub frontend consolidation

**Canonical UI:** `standalone/suryadev/dashboard.html` in KRISHNA-CORE. 
**Branch/PR:** `feature/suryadev-r39-unified-repo-ui-20261023`, draft PR #231 (stacked on PR #229). This is an isolated test branch, **not yet merged** into the default branch.

## What was actually removed
- Duplicate date inputs in the assignment filter and daily diary. One **Learning history** date input controls assignment filtering and the selected-day report. Day tiles remain as shortcuts, not additional calendar inputs.
- Duplicated detailed book counts in Source Coverage and Laptop Health. The **Books** link now opens the single Garudanetra book-ledger area, including indexed progress, original-line search, visuals and candidate receipts.
- Runtime JavaScript insertion of another Video Review section and duplicate sidebar link. `dashboard.html` is the only panel/layout definition; the video JavaScript binds to that existing section.
- Stale hardcoded UI v6.9 footer and test-vs-production-folder messages. The footer reads its actual build version from `/api/ui-version`.
- Stale API capability claims that book detail cards still appear in other panels.

## Navigating the only dashboard
- **Overview** — count of assignments, completed workers, queued jobs, source findings. Counts are not proof of mastery.
- **Live learning** — Garudanetra browser, worker state, YouTube/PDF lanes and book activity. An offline worker is not a disconnected dashboard.
- **Assignments** — one searchable, pageable task ledger with evidence inspection.
- **Video review** — enter a URL, observe length, important terms and adaptive playback. The advanced JSON entry remains optional for existing KRISHNA jobs. Importing does **not** run a job; the exact URL and one-time approval remain mandatory.
- **Evidence** — source type and counts.
- **Books** — one detailed book record and exact original-line search.
- **History** — one date filter and related diary records.
- **Configuration** — secure KRISHNA and storage popups; neither creates pairing or silently changes a worker.

## Backend/API reliability
- Read-only dashboard GET requests use a bounded same-origin 2-attempt retry helper; operator POSTs **are never retried** automatically.
- SQLite dashboard readers open query-only connections instead of performing migrations and journal-mode writes on every poll.
- Both API and network failures remain visible rather than being hidden; previously saved counters are last-known values.
- No paid frontend libraries, external telemetry, Core pairing, startup services, scheduled tasks, app builds or data migrations added.

## Windows test upgrade (DO NOT TOUCH original D:\Work\SURYADEV)
1. Stop the test dashboard on port 8771, without stopping Ollama unless you choose to.
2. `cd D:\Work\SURYADEV-UNIFIED-R39-SOURCE` then `git pull --ff-only origin feature/suryadev-r39-unified-repo-ui-20261023`.
3. `cd .\standalone\suryadev` and run `python -m unittest discover -s tests -v`; installer independently reruns its gate.
4. Run `install-windows.ps1` with `-InstallDir D:\Work\SURYADEV-UNIFIED-TEST` and `-DataDir D:\Work\SURYADEV-UNIFIED-TEST-DATA`.
5. Run `python dashboard_ui_smoke.py` from the source to inspect a browser with disposable test data.
6. Start the installed `suryadev_extras.py --data D:\Work\SURYADEV-UNIFIED-TEST-DATA dashboard --port 8771`, hard-refresh `http://127.0.0.1:8771/`.
7. Verify `GET /api/live`, `/api/tasks`, `/api/diary?date=YYYY-MM-DD`, `/api/books`, `/api/video/review` return HTTP 200 with no repeated "Failed to fetch".
8. Keep learning and live worker testing separate until the dashboard and operator approval are verified.

## Acceptance criteria
Browser: no duplicate IDs, one date input, one Video Review, one book detail, book search working, no uncaught JS errors, no unexpected 4× claims. Windows installer: all unit tests pass and isolated runtime imports pass. A short public approved video is required to validate real playback speeds and evidence. No unverified claim of comprehensive source learning or BRAHMAGYAN/Rishi promotion.
