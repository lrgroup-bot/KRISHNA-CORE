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

Status: GITHUB PASS / LOCAL E-DRIVE BLOCKED

### Source-of-truth findings

- Canonical integration/default branch: `fix/krishna-ui-runtime-verification`.
- PR #37 (`feature/bhumiputra-geovision-agent`) is closed unmerged and superseded by merged PR #42.
- PR #47 (`audit/full-project-hardening-20260922`) is merged. Merge commit: `9457ac7d0389da3bf88dadfd3b42252642923705`.
- PR #48 (`feature/project-perfection-loop-v1`) is closed unmerged. It must not be merged after #47 because its old base diverged from the hardened line.
- PR #49 (`reconcile/project-perfection-after-hardening`) was reconciled directly on PR #47's hardened base and merged successfully.
- PR #49 merge commit: `8bacf126ed738b0dc5b6a5af0e49dc8862ea381f`.
- The merged commit passed post-merge Core, Windows, and Android validation on `fix/krishna-ui-runtime-verification`.
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

6. Android emulator retest command was not actually executed as one shell program.
   - The emulator action dispatched multiline `script:` lines separately, so the Python heredoc body was interpreted by `/bin/sh`.
   - Replaced the fragile heredoc with one explicit Python command so the real APK retest executes inside the booted emulator job.

7. The real APK retest then exposed a launcher/process timing race after force-stop/restart.
   - Install, permissions, first launch, process check, background/foreground and restart launcher command all passed with no fatal exception.
   - The immediate post-restart `pidof` check could run before Android published the restarted PID.
   - Added bounded PID polling for both initial launch and restart, plus a regression test covering delayed PID publication.

8. A later emulator run exposed another slow-runner race: the foreground launcher command could exceed its command timeout even though Android subsequently brought KRISHNA up and restart verification succeeded.
   - Reworked Android launch/foreground/restart verification to gate on observed app PID plus Android top-activity state.
   - Launcher-command timeout is retained as diagnostic evidence instead of being treated as a false runtime failure when the required foreground state is independently verified.
   - Added regression coverage for delayed foreground publication.

### Merge-order rule

The safe order is now fixed:

1. PR #37: do not merge; historical/superseded.
2. PR #47: merged first; hardened base.
3. PR #48: do not merge; superseded old-base Project Perfection line.
4. PR #49: merged after all required latest-head checks were green. Merge commit: `8bacf126ed738b0dc5b6a5af0e49dc8862ea381f`.

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

### GitHub verification result

PR #49 was merged only after its latest head passed the required checks. The resulting merge commit `8bacf126ed738b0dc5b6a5af0e49dc8862ea381f` was then validated again on the integration branch:

- PASS — Test KRISHNA Core.
- PASS — Build KRISHNA Windows App, including bundled-Core/restart retest.
- PASS — Build KRISHNA Mobile Conversation APK.
- PASS — Conversation-only mobile contract.
- PASS — KABACH real APK privacy gate.
- PASS — Clean Android emulator install, launch, foreground, force-stop and restart retest.
- PASS — Project Perfection runtime/browser/integrity tests included by the reconciled branch.

GitHub-side source/merge/CI integrity for Phase 1 is therefore complete.

### External research note

GitHub Actions concurrency is used to prevent obsolete runs from consuming runner capacity while keeping the latest commit authoritative. Supply-chain provenance/attestation remains a later release-hardening candidate; it should be added only after the normal build and runtime acceptance path is stable.

### Phase 1 final status record

- PASS — GitHub source-of-truth and merge order are resolved.
- PASS — PR #47 hardening is preserved.
- PASS — superseded PRs #37 and #48 remain unmerged.
- PASS — PR #49 is merged at `8bacf126ed738b0dc5b6a5af0e49dc8862ea381f`.
- PASS — latest-head and post-merge Core validation.
- PASS — latest-head and post-merge Windows build/restart validation.
- PASS — latest-head and post-merge Android build/privacy/emulator validation.
- FIXED — Android emulator script execution, PID publication race, and slow foreground-launch verification.
- MISSING — repository ruleset/branch protection remains a governance hardening item.
- BLOCKED — direct verification of `E:\KRISHNA-SOURCE`, `E:\Krishna-The GOD`, deployment manifest and live runtime acceptance requires access to the Windows E-drive and cannot be inferred from GitHub.

Do not start Phase 2 until the local E-drive block is either directly verified or explicitly accepted as an environment-only follow-up.
