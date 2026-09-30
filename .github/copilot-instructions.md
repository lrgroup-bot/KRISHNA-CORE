# KRISHNA repository instructions for GitHub Copilot

Follow the root `AGENTS.md` as the repository engineering constitution.

KRISHNA already owns orchestration, permissions, worktree isolation, verification, rollback, browser/UI inspection, PR review, and self-heal primitives. Reuse them; do not create competing authorities.

For implementation work:
- use a feature/fix branch or isolated worktree;
- keep unrelated files untouched;
- do not force-push or auto-merge;
- do not bypass tests, security gates, zero-spend policy, KABACH, or Shared Action Bus;
- never claim physical Windows/E-drive/mobile validation from GitHub-only evidence;
- provide test/build/review evidence before calling work complete.

When a task is primarily review, testing, UI verification, or recovery, prefer the matching custom agent under `.github/agents/`.
