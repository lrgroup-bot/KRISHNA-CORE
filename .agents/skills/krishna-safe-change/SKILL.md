---
name: krishna-safe-change
description: Safely implement a KRISHNA code change using isolated work, narrow tests, independent evidence, and governed promotion boundaries.
---

# KRISHNA Safe Change

Use this skill for implementation or repair tasks.

1. Read `AGENTS.md` and identify the exact requested scope.
2. Inspect existing implementation before designing a replacement.
3. Work only in an isolated branch/worktree. Never mutate the canonical/live runtime directly.
4. Keep the patch minimal and preserve unrelated behavior.
5. Run narrow checks first. Expand to relevant regression/security/UI checks based on risk.
6. Record changed files, test output, and unresolved validation boundaries.
7. Do not merge or auto-promote. Hand the verified candidate to KRISHNA/Sudarshan/owner policy.

Hard blocks: force push, destructive repository cleanup, secret exposure, paid dependency activation, bypassing permission/security/verification gates, or fabricating runtime evidence.
