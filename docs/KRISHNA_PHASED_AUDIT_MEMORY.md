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

- Canonical integration/default branch: `fix/krishna-ui-runtime-verification`.
- PR #37 (`feature/bhumiputra-geovision-agent`) is closed unmerged and superseded by merged PR #42.
- PR #47 (`audit/full-project-hardening-20260922`) is merged. Merge commit: `9457ac7d0389da3bf88dadfd3b42252642923705`.
- PR #48 (`feature/project-perfection-loop-v1`) is closed unmerged. It must not be merged after #47 because its old base diverged from the hardened line.
- PR #49 (`reconcile/project-perfection-after-hardening`) is the active Project Perfection reconciliation PR. It is built directly on PR #47's merged head, is mergeable, and at the Phase 1 audit point was 4 commits ahead / 0 behind that hardened base.
- The repository's current default branch head is the PR #47 merge until PR #49 is verified and merged.
- No repository ruleset is currently configured. Branch-list evidence also reports the integration branch as unprotected. This is recorded as a release-governance gap; do not weaken CI/verification to compensate for it.

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

5. Phase 1 audit memory became stale after the hardening/reconciliation merge-order change.
   - Corrected the source-of-truth ledger: #47 is merged, #48 is closed unmerged, and #49 is the active reconciliation PR.

### Merge-order rule

The safe order is now fixed:

1. PR #37: do not merge; historical/superseded.
2. PR #47: merged first; hardened base.
3. PR #48: do not merge; superseded old-base Project Perfection line.
4. PR #49: validate on top of #47, then merge only when all required checks are green.

### Deployment truth rule

GitHub merge state and E-drive runtime state are separate facts.

A GitHub PR being merged does **not** prove that:
- `E:\KRISHNA-SOURCE` has pulled that merge,
- `E:\Krishna-The GOD` has been deployed from that source,
- the runtime manifest matches source,
- runtime acceptance passed.

`scripts/DEPLOY_KRISHNA_ONCE.ps1` is the canonical deploy path. It:
- refuses deployment from a dirty source checkout,
- fetches/prunes and fast-forwards the selected branch,
- tests authoritative source before mutating runtime,
- deploys to `E:\Krishna-The GOD`,
- retests deployed code,
- writes `state\deployment\DEPLOYED_COMMIT.json` with commit/branch/file hashes,
- runs `ACCEPT_KRISHNA_RUNTIME.ps1` by default,
- rolls back the provisional manifest if acceptance fails.

The E-drive phase still requires direct local Windows evidence. Until that evidence exists in the audit session, local source/runtime synchronization is **UNVERIFIED**, never assumed from GitHub state.

### Current CI gate

For the active PR #49 head, required validation is:

- Test KRISHNA Core.
- Build KRISHNA Windows App, including bundled-Core/restart retest.
- Build KRISHNA Mobile Conversation APK, including privacy/emulator retest.
- Project Perfection browser E2E and integrity checks included by the reconciliation branch.

Any new commit to PR #49 invalidates earlier head results; only checks attached to the latest PR head are authoritative.

### External research note

GitHub Actions concurrency is used to prevent obsolete runs from consuming runner capacity while keeping the latest commit authoritative. Supply-chain provenance/attestation remains a later release-hardening candidate; it should be added only after the normal build and runtime acceptance path is stable.

### Exit criteria for Phase 1

- Latest PR #49 Core CI passes.
- Latest PR #49 Windows build/smoke/restart retest passes.
- Latest PR #49 Android build/privacy/emulator retest passes.
- PR #49 retains PR #47 hardening and the intended Project Perfection delta without old-base regression.
- PR #49 is merged only after all required latest-head checks are green.
- E-drive source/deployment state is checked separately with direct local evidence.
- Phase 1 receives a final PASS/FIXED/MISSING/BLOCKED status record before Phase 2 begins.
