# KRISHNA Agentic Engineering Control Plane

## Purpose

This is an additive compatibility/control layer for coding agents such as GitHub Copilot, Codex, Antigravity, local models, and future providers.

It does **not** replace KRISHNA's existing runtime, Software Factory, Engineering Scheduler, Engineering Swarm, Shared Action Bus, KABACH, MRITYUNJAY, Git worktree manager, verifier, promotion manager, browser fabric, or UI Guardian.

## Added surfaces

- `AGENTS.md`: provider-neutral repository engineering constitution.
- `.github/copilot-instructions.md`: GitHub Copilot always-on repository guidance.
- `.github/agents/`: specialist Copilot agents for development, review, UI proof, and MRITYUNJAY-style final review.
- `.agents/skills/`: portable skills usable by compatible agent systems.
- `.github/hooks/krishna-safety.json` + `scripts/AGENTIC_PRE_TOOL_GATE.py`: deterministic pre-tool guard.
- `core/krishna_core/agentic_control_plane.py`: provider-neutral mission/evidence adapter over existing KRISHNA primitives.
- `tests/test_agentic_control_plane.py`: isolated validation.
- `.github/workflows/agentic-control-plane.yml`: CI validation for only this additive layer.

## Authority model

```text
Owner / KRISHNA
      |
      v
Existing KRISHNA governance
      |
      +--> Engineering Scheduler
      +--> Engineering Swarm
      +--> Git worktrees
      +--> Verification / Critic
      +--> MRITYUNJAY
      +--> Promotion / rollback
      |
      v
Agentic Control Plane
      |
  optional workers
  Copilot / Codex / Antigravity / local models
```

External agents remain optional workers. They have no merge authority, no production-promotion authority, and may not become a required billable runtime dependency.

## Artifact contract

A mission can record:
- `PLAN.json`
- `STAFFING.json`
- `CHANGES.json`
- `TEST_RESULTS.json`
- `SECURITY.json`
- `UI_PROOF.json`
- `REVIEW.json`
- `MRITYUNJAY.json`
- `FINAL_RECEIPT.json`

The final receipt never auto-merges. By default it requires at least test results and an independent review before it can say that a candidate is ready for the existing governed promotion path.

## Safety hook

The pre-tool hook is deliberately narrow and fail-closed on hook execution errors under supported Copilot environments. It blocks:
- force pushes;
- destructive Git cleanup/reset patterns;
- direct pushes to configured protected branches;
- `gh pr merge` from coding-agent sessions;
- direct edits to obvious secret/credential targets;
- obvious billable-dependency purchase operations.

This hook supplements existing KRISHNA policy. It is not a replacement for KABACH or the Shared Action Bus.

## GitHub issue -> agent -> PR

Once the branch is merged to the repository default branch and GitHub Copilot coding agent is enabled for the repository, the custom agents become selectable for Copilot coding-agent work, including issue assignment. GitHub then owns the cloud-agent issue/branch/PR lifecycle while KRISHNA's repository instructions, skills, and hooks constrain the worker.

This repository intentionally does not add an auto-merge path.

## Local integration

No existing runtime file is edited by this change. When KRISHNA is ready to activate the control plane locally, existing code can import:

```python
from krishna_core.agentic_control_plane import build_default_agentic_control_plane

plane = build_default_agentic_control_plane(state_root)
```

That binds the additive layer to the existing EngineeringScheduler, EngineeringSwarmManager, and IndependentCriticVerifier classes. Worktree and MissionEngine instances remain supplied by the existing runtime that already owns them.

## Truth boundary

GitHub CI can validate repository syntax, contracts, and tests. It cannot prove the user's physical E-drive state, Windows services, attached cameras, mobile hardware, or the active local KRISHNA runtime. Those remain separate local acceptance checks.
