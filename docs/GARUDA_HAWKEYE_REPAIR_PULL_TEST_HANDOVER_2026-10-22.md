# GARUDA Repair Studio / HAWKEYE integration handover
Date: 2026-10-22
Branch: feat/lr-lifecycle-integration-20261022
PR: https://github.com/lrgroup-bot/KRISHNA-CORE/pull/230

## Committed source
- core/krishna_core/garuda_diagnostics.py: read-only diagnostic plan, paired flag, approval classification; not an executor.
- core/krishna_core/garuda_repair_studio.py: deterministic repair cases and safe generic step plans.
- core/krishna_core/garuda_repair_guides.py: original, immutable structured guide library.
- core/krishna_core/hawkeye_repair_reference.py: opt-in iFixit API v2 suggest, attributed reference links only; no training or bulk ingestion.
- core/krishna_core/garuda_repair_workflow.py: coordinates above modules and produces offline-safe case envelopes.
- Matching unittest files: test_garuda_diagnostics.py, test_garuda_repair_studio.py, test_garuda_repair_guides.py, test_hawkeye_repair_reference.py, test_garuda_repair_workflow.py.

## Pull and test commands (Windows PowerShell)
git fetch origin
git switch feat/lr-lifecycle-integration-20261022
git pull --ff-only
$env:PYTHONPATH = (Resolve-Path .\\core).Path
python -m unittest discover -s core/tests -p 'test_garuda*.py' -v
python -m unittest discover -s core/tests -p 'test_hawkeye_repair_reference.py' -v
python -m unittest discover -s core/tests -p 'test_hawkeye*.py' -v
# Run full project regression and UI/browser tests according to repo instructions before any merge or APK.

## Important honest limits
- Commits and test files exist. No tests were executed by this GitHub-only session.
- HAWKEYE live camera/AR overlay is NOT wired to the new reference client.
- Device pairing store is NOT bound to the new workflow; caller-supplied paired=True is insufficient for production authorization.
- GARUDA read-only diagnostic planner does NOT execute system commands or collect telemetry.
- No mobile APK, browser UI, REST endpoint, technician repair workflow state machine, guide media viewer, Q&A, catalog, parts compatibility, inventory or Rishi examination integration yet.
- External iFixit API has NOT been live-smoke-tested; suggest response contract may differ. Provider must remain opt-in and no automatic retries on 429.
- Do not merge until integration, auth, security, unit tests, real device smoke tests and rollback gates pass.

## Next implementation order
1. Bind authenticated pairing/authorization server-side; never trust caller-provided paired flags.
2. Add read-only diagnostic executors with per-device permissions, audit and redaction.
3. Add REST endpoint and HAWKEYE camera UI module card with real provider toggle and source attribution.
4. Add guide/part/tool/catalog storage, versioned review and corrections, photo/video references, safe troubleshooting trees.
5. Wire VISHVAKARMA repair outcomes and BRAHMAGYAN Rishi examination, no automatic promotion.
6. Run unit, security, UI and real Android/Windows hardware tests; fix all failures, then review merge.

## Scope
Personal noncommercial project; first-party content only for stored guides; external iFixit references remain attributed and subject to terms. No destructive repair without explicit approval.
