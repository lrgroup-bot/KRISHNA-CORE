# Replica-inspired implementation and verification plan

This is a development-branch inventory, **not** evidence that features work. Preserve existing agent and business logic; do not duplicate it.

## Evidence gate
Run `python tools/replica_feature_gate.py audits/features.csv` from repository root. Run unit tests with `python -m unittest discover -s tests -p 'test_replica_feature_gate.py' -v`. A passed feature requires actual test evidence, not a claim.

## KRISHNA responsibilities
- BRAHMAGYAN: inventory existing features and reuse learning records.
- VISHWAKARMA: implement missing behavior on isolated branches.
- UI Guardian: browser interactions, keyboard, responsive, accessibility, console, network and screenshots.
- Mrityunjaya: reproduce failure, add regression test, repair and roll back on failure.
- KRISHNA supervisor: enforce human approval for merges, deployments, financial operations and destructive changes.

## LR Group responsibilities
- Inspect existing role and company boundaries before adding routes.
- Authenticate every finance and staff endpoint; verify company ownership server-side.
- Preserve zero autonomous spending and separate company ledgers.
- Test invoice -> settlement -> journal -> reconciliation with fake provider and tamper tests.
- Confirm LR Commerce and LLEO contract compatibility before integration.

## Outstanding verification (all UNVERIFIED)
1. Enumerate actual source tree, agents, routes, screens and test suites; no invented inventory.
2. Establish baseline test results and CI status.
3. Add feature matrix with traceable test case IDs and screenshots/logs.
4. Verify browser click-through for every button and workflow.
5. Verify mobile flows on emulator/device, including permissions, offline and background operation.
6. Resolve existing LR Technology finance prototype gaps and authenticated integration.
7. Review security, concurrency, backup/restore and crash recovery.
8. Rerun full regression and record failures with severity and reproduction.
9. Only after approval: merge, pull, package and deploy.

Replica-skill inspiration: https://github.com/Jakeschincariol/replica-skill (MIT). This repo does not vendor external skill code. No unauthorized cloning of protected assets.
