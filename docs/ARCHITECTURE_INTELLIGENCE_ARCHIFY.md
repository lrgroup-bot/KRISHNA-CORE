# KRISHNA Architecture Intelligence — Archify Integration

Status: isolated integration candidate; not merged or deployed.

## Purpose

Use Archify as a read-only visualization and validation engine beneath KRISHNA. It does not become an autonomous agent and it does not receive authority to edit code, merge, deploy, spend, or approve architecture changes.

Upstream: tt-a1i/archify
License: MIT. Preserve upstream copyright/license notices for copied or vendored code.

## Security / local-first policy

- Pin an explicitly reviewed Archify version or commit before installation.
- Set `ARCHIFY_UPDATE_CHECK_DISABLED=1`.
- Do not send repository source, prompts, device identifiers, credentials, secrets, or private data to external services.
- Run repository analysis locally against a checkout.
- Start read-only: source repository input + generated architecture artifacts output.
- Do not grant write access to the repository under analysis.
- Do not treat a diagram or architecture delta as proof that a change is safe.
- Do not merge/deploy from this subsystem.
- Avoid redistributing bundled third-party brand marks unless their individual terms have been reviewed; prefer KRISHNA/LR-owned icons.

## Architecture

Repository checkout
  -> KRISHNA Architecture Scanner
  -> evidence-backed Architecture IR
  -> Archify validate/finalize
  -> architecture/workflow/sequence/dataflow/lifecycle artifact
  -> Architecture Guardian
  -> Control Room read-only Architecture View

For code changes:

Before IR + After IR
  -> Archify compare
  -> deterministic delta
  -> KRISHNA impact/risk assessment
  -> Mrityunjaya regression evidence
  -> Vishwakarma implementation review
  -> Brahma QC
  -> Owner approval
  -> merge/deploy remains a separate gated action

## Trust boundary

Archify provides rendering, validation, source evidence, and deterministic diagram comparison.
KRISHNA owns interpretation, risk assessment, policy, permissions, and owner-facing explanation.

Never infer:
- runtime health from a static diagram;
- causal impact from an authored edge alone;
- safety from a passing Archify validation;
- approval from a visual diff.

## Rollout gates

1. Verify pinned upstream source, MIT license, dependencies, and tests.
2. Disable Archify update checks.
3. Run upstream doctor/tests/demo in an isolated local workspace.
4. Generate one repository-grounded KRISHNA architecture artifact.
5. Verify sampled source links against the pinned Git revision.
6. Generate all five views for one subsystem.
7. Browser/perceptual test the standalone artifact.
8. Add read-only Control Room integration.
9. Test Before/After comparison on a known harmless change.
10. Only after evidence is green, consider LR Group/LR Commerce/LR Technology integration.

## Acceptance criteria

- No external network request during normal rendering/validation.
- No source-repository mutation.
- Generated evidence is tied to a known repository revision.
- Invalid/stale evidence fails closed.
- Architecture output is understandable in Owner View and traceable in Evidence View.
- Existing KRISHNA tests remain green.
- Runtime/browser verification is recorded before merge.
- Owner explicitly approves merge/deployment.

## Multi-repository rule

Do not pretend one artifact can strongly verify every LR repository at once. Keep repository-grounded maps per repository and create a higher-level LR Universe contract map for cross-repository boundaries.
