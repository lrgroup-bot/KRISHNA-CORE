# KRISHNA Agent Engineering Constitution

This repository is governed by KRISHNA. External coding agents are workers, not authorities.

## Non-negotiable rules

1. Never edit or promote directly into the canonical/live runtime. Work on an isolated branch or KRISHNA-managed Git worktree.
2. Never force-push, bypass required checks, auto-merge, or merge a pull request unless the owner/governed promotion path explicitly authorizes it.
3. Preserve KRISHNA's zero-spend policy. Do not enable paid APIs, trials that consume billable/promotional credits, subscriptions, purchases, or automatic financial actions.
4. Never print, expose, copy, or commit secrets, tokens, credentials, private keys, device identities, or private user data.
5. Do not weaken KABACH, permissions, Shared Action Bus, promotion/rollback, verification, mobile privacy boundaries, or audit controls to make a task pass.
6. Treat repository checks as necessary but not sufficient for hardware/runtime claims. Physical Windows/E-drive/mobile claims require corresponding local evidence.
7. A coding worker must not declare its own work production-ready. Independent verification is required.
8. Prefer additive, narrow changes. Preserve unrelated working behavior.
9. For mutating parallel work, one worker gets one isolated worktree/branch.
10. If required evidence is unavailable, report the exact unverified boundary instead of guessing.

## Standard engineering loop

Requirement -> plan -> isolated worktree -> implementation -> tests/build -> independent review -> security/UI evidence when relevant -> MRITYUNJAY review -> candidate -> governed promotion/PR.

## Evidence expected

For meaningful changes, produce or reference:
- plan/intent;
- changed-file list or diff;
- tests/build results;
- security findings when relevant;
- browser/mobile visual proof when UI is changed;
- independent review verdict;
- remaining unverified local/hardware checks.

## Provider policy

Copilot, Codex, Antigravity, Gemini, Claude, local models, and other model providers are optional workers. None may become KRISHNA's authority or a mandatory paid dependency. Provider-specific convenience must sit behind KRISHNA's existing governance and free-only policy.

See `docs/AGENTIC_ENGINEERING_CONTROL_PLANE.md` and the skills under `.agents/skills/`.
