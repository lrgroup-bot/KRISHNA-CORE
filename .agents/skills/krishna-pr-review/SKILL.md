---
name: krishna-pr-review
description: Review a KRISHNA pull request independently for intent, correctness, CI evidence, security, regressions, and local-runtime truth boundaries.
---

# KRISHNA Pull Request Review

Use this skill when reviewing a PR or candidate.

Check:
- intent matches the requested task;
- diff is scoped and understandable;
- required tests/builds are green;
- no secrets or private data are exposed;
- no new paid/billable dependency violates zero-spend policy;
- permission, Shared Action Bus, KABACH, rollback, and promotion boundaries remain intact;
- UI changes include behavioral/visual proof where applicable;
- physical Windows/E-drive/mobile claims are not inferred from GitHub evidence.

Report only actionable concerns. Distinguish a repository-pass from a production/runtime-pass.
