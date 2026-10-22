# CODEX LOCAL HANDOVER — KRISHNA SUDARSHAN + GARUDA / HAWKEYE
Date: 2026-10-22
Repository: lrgroup-bot/KRISHNA-CORE
Remote feature branch: feat/lr-lifecycle-integration-20261022
PR: https://github.com/lrgroup-bot/KRISHNA-CORE/pull/230
Baseline commit for handover: 5995785f0b5a283f932cb5e20c6516a19abdeea7
IMPORTANT: Do not merge or build .exe before complete browser and regression verification.

## Evidence verified remotely
- SUDARSHAN Lean Review Tests GitHub Actions run 39704268419: success at baseline commit.
- GARUDA Repair Studio Tests GitHub Actions run 39704268388: success at baseline commit.
- Test KRISHNA Core run 39704268380: in_progress at last check. Check final result.
- CI focused tests do not prove Windows runtime, browser UI, Android APK or external iFixit integration.

## Local preparation (PowerShell)
Set-Location 'E:\Krishna-The GOD'
git status --short
git remote -v
git fetch origin
git branch -a
# NEVER overwrite uncommitted user changes.
# Use a separate worktree when the existing working tree is dirty:
git worktree add 'E:\Krishna-The GOD\engineering-worktrees\sudarshan-handover' origin/feat/lr-lifecycle-integration-20261022
Set-Location 'E:\Krishna-The GOD\engineering-worktrees\sudarshan-handover'
git rev-parse HEAD
$env:PYTHONPATH = (Resolve-Path '.\core').Path
python -m unittest discover -s core/tests -p 'test_sudarshan_*review.py' -v
python -m unittest discover -s core/tests -p 'test_garuda_*.py' -v
python -m unittest discover -s core/tests -p 'test_hawkeye_repair_reference.py' -v
# Then run the repo's full regression instructions; do not assume command coverage.

## SUDARSHAN code delivered
- core/krishna_core/sudarshan_lean_review.py: scoped read-only impact/symbol scan, dependency justification, debt comments, lite/full/ultra.
- core/krishna_core/sudarshan_duplicate_review.py: Python AST structural duplicate candidates; review-only, no deletions.
- core/krishna_core/sudarshan_project_orchestrator.py: lean_review, lean_debt, duplicate_review methods.
- core/tests/test_sudarshan_lean_review.py and test_sudarshan_duplicate_review.py.
- .github/workflows/sudarshan-lean-tests.yml.

## GARUDA / HAWKEYE code delivered
- core/krishna_core/garuda_repair_studio.py, garuda_repair_guides.py, garuda_diagnostics.py.
- core/krishna_core/garuda_repair_workflow.py, garuda_repair_knowledge.py.
- core/krishna_core/hawkeye_repair_reference.py: optional iFixit metadata link client; verify real API shape/terms.
- mobile_v3/garuda-repair-studio.html: standalone draft UI, not yet integrated into live camera.
- Matching test_garuda_*.py, test_hawkeye_repair_reference.py.
- .github/workflows/garuda-repair-tests.yml.

## Codex execution mandate (no duplicate architecture)
1. Inventory canonical source and tests, all changed/untracked files, active services and existing SUDARSHAN, HAWKEYE, BRAHMAGYAN, VISHVAKARMA contracts.
2. Check GitHub CI and run full Python, frontend, security and regression suite locally; capture exact failing tests, stack traces, environment and evidence. Do not suppress tests or mark unexecuted tests PASS.
3. Fix root causes with minimal diffs. Existing SUDARSHAN control plane, independent critic and shared action bus remain the authority; no new orchestrator.
4. Strengthen duplicate analysis where necessary; don't automatically delete similar functions. No extra third-party packages unless justified.
5. Bind GARUDA Repair Studio into existing HAWKEYE authenticated endpoint, camera UI and source reference system. The new standalone HTML must not be described as complete live UI.
6. Enforce actual DevicePairingStore credential verification server-side; NEVER trust a client-provided paired=True. Keep diagnostics read-only by default, approval for risky actions, and audit receipts.
7. Bind original repair guides, catalog, parts fitment, safe fault trees, correction reviews, media references, technician outcomes to existing VISHVAKARMA and BRAHMAGYAN Rishi exam workflow. No external content auto-promotion.
8. Verify iFixit public API endpoint, response schema, opt-in, rate limits, attribution, license and fallback. No scraping or copying proprietary guide content.
9. Browser-first: click EVERY affected UI button, exercise errors, empty states, auth, mobile viewport and navigation. Then real Android/Hawkeye and paired Windows device smoke tests. APK only after browser passes; .exe only after full gates.
10. Produce a reproducible evidence bundle: git SHA, environment, commands, test counts, failures fixed, browser screenshots, logs, security findings, unresolved risks, rollback instructions.
11. Merge only after explicit user approval; no destructive cleanup of unrelated work.

## Definition of done
- All focused + full repo tests PASS (no cancelled or skipped critical suites), browser/UI tests PASS, pairing security PASS, device checks PASS, and no known blocker.
- If hardware/network or tools unavailable, record BLOCKED with reproducible reason; never claim error-free.
- Keep all changes on feature branch; no merge, pull into production, APK/.exe build before gates.
