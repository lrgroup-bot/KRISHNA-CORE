# KRISHNA Phased Audit Memory

This file is the durable audit ledger for the bit-by-bit KRISHNA completion review.  
Rule: inspect one phase completely, record evidence, fix concrete defects, verify, then advance.

## Audit method

For every phase:

1. Inspect current GitHub source and open PRs.
2. Check implementation against KRISHNA requirements and current runtime contracts.
3. Run/inspect relevant tests and CI evidence.
4. Search current public documentation/repos for materially useful improvements.
5. Fix concrete defects without weakening gates.
6. Record what was verified, what was changed, and what remains environment-specific.
7. Do not mark a phase complete while required evidence is failing.

## Phase 1 — Source of truth, merge/deploy integrity, CI

Status: IN PROGRESS

### Source-of-truth findings

- Canonical integration base: `fix/krishna-ui-runtime-verification`.
- PR #48 (`feature/project-perfection-loop-v1`) is the active Project Perfection integration branch and is not yet merged.
- PR #47 (`audit/full-project-hardening-20260922`) is still open and contains additional hardening that must be reconciled before final completion.
- PR #37 was an older Hawkeye line and has been closed as superseded by merged PR #42.
- PR #42 is the current-base Hawkeye integration already merged.

### Phase 1 defects found and corrected

1. Project Perfection browser E2E failed on a synthetic favicon 404.
   - Fixed the test fixture with an inline data favicon.
   - Error detection itself was not weakened.

2. Android emulator retest failed because the emulator action invokes the script through POSIX `sh`, where `set -o pipefail` is unsupported.
   - Replaced the emulator script strict mode with portable `set -eu`.

3. Windows bundled Core startup was falsely reported offline.
   - The in-process Core was running, but `/api/status` raised `FileNotFoundError`.
   - Root cause: `core/requirements/krishna_chat_requirements.json` was not bundled by PyInstaller.
   - Added `core/requirements` to Windows PyInstaller data.
   - Added `core/requirements` to the runtime patch manifest.

4. CI queue was flooded by superseded PR-head runs.
   - Added workflow-level concurrency groups with `cancel-in-progress: true` for Core, Windows, and Android validation.

### Deployment truth rule

GitHub merge state and E-drive runtime state are separate facts.

A GitHub PR being merged does **not** prove that:
- `E:\KRISHNA-SOURCE` has pulled that merge,
- `E:\Krishna-The GOD` has been deployed from that source,
- the runtime manifest matches source,
- runtime acceptance passed.

The E-drive phase will require direct local evidence from the Windows machine or the repository's deployment/audit scripts. Until that evidence exists, E-drive status must be reported as UNVERIFIED rather than guessed.

### External research note

GitHub Actions concurrency is used to prevent obsolete runs from consuming runner capacity while keeping the latest commit authoritative. Supply-chain provenance/attestation remains a later release-hardening candidate; it should be added only after the normal build and runtime acceptance path is stable.

### Exit criteria for Phase 1

- Latest PR #48 Core CI passes.
- Latest PR #48 Windows build/smoke/restart retest passes.
- Latest PR #48 Android build/privacy/emulator retest passes.
- PR #47 is reconciled so no required hardening is lost.
- PR #48 is merged only after required checks are green.
- E-drive source/deployment state is checked separately with local evidence.

