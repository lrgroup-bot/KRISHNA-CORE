# KRISHNA Gap & PC Implementation Registry

Purpose: preserve capabilities discovered during external research that KRISHNA genuinely lacks but should NOT be approximated with a weak duplicate. This file is the installation/verification backlog for the future KRISHNA Windows PC.

Rules:
1. Do not install a candidate merely because it is popular.
2. Re-audit current KRISHNA before every installation; if the gap has since been closed natively, mark REJECTED_DUPLICATE.
3. External analyzers are evidence providers. KRISHNA remains the authority for policy, repair, verification, approval and promotion.
4. Prefer local/read-only operation. No source upload, cloud fallback, account login, telemetry, paid service, repository mutation, merge or deployment unless separately reviewed and owner-approved.
5. Pin an exact version/commit, verify license and hashes, isolate dependencies, run on a disposable/read-only project copy first.
6. A tool is not IMPLEMENTED until its acceptance tests below pass with captured evidence.

Status vocabulary: PLANNED_PC | VERIFY_LICENSE | RESEARCH_MORE | INSTALLED_UNVERIFIED | VERIFIED | REJECTED_DUPLICATE | REJECTED_RISK.

## GAP-001 — Real interprocedural source-to-sink code dataflow

Status: PLANNED_PC / VERIFY_LICENSE
Priority: HIGH
Gap owner: KABACH + Architecture Intelligence
Why missing: KRISHNA has repository/dependency graphs, blast radius, architecture rules, runtime policy and secret/egress checks, but these do not prove variable/value flow across functions/files. A homemade mini-taint engine would create false confidence.

Primary candidate: GitHub CodeQL CLI + github/codeql query libraries.
Alternative/second opinion: joernio/joern.
Do not copy/reimplement their engines.

PC placement proposal:
- E:\\Krishna-The GOD\\tools\\codeql\\
- E:\\Krishna-The GOD\\state\\analysis\\codeql\\
- E:\\Krishna-The GOD\\reports\\security\\codeql\\
Keep databases/results out of source roots.

Integration boundary:
read-only project snapshot -> external analyzer -> SARIF/path evidence -> KRISHNA evidence adapter -> KABACH/Critic/Project Perfection.
The adapter must never grant execution authority to CodeQL/Joern.

Pre-install checks:
- Recheck CodeQL current license/terms for the actual repository visibility/account use case.
- Verify current release source, checksum/signature where available.
- Confirm supported KRISHNA languages.
- Confirm local-only analysis and disable unnecessary upload steps.
- Measure disk/RAM/time on a representative KRISHNA snapshot.
- Compare Joern only if CodeQL licensing, coverage or local-resource constraints make it preferable.

Acceptance tests:
1. Seed a safe fixture with a known user-controlled source reaching a dangerous sink; analyzer must return source, sink and a path.
2. Add a sanitizer/guard fixture; expected false-positive behavior must be documented and calibrated.
3. Seed a cross-function and cross-file flow; verify it is detected.
4. Seed a similar but non-reaching value; it must not be reported as the same reachable flow.
5. Export machine-readable evidence (prefer SARIF for CodeQL) and ingest it without changing source files.
6. Run KABACH/Critic on imported evidence; external findings remain evidence, not autonomous commands.
7. Disconnect network after installation and repeat analysis to prove the normal scan path is local.
8. Measure runtime/RAM/disk and establish a resource-governor ceiling.

Gap closed when: KRISHNA can show a defensible source -> intermediate path -> sink trace, with file/location evidence, while keeping external analysis read-only and locally governed.

## GAP-002 — Optional second-engine code property graph / backward slicing

Status: RESEARCH_MORE
Priority: MEDIUM
Candidate: joernio/joern
Reason to keep separate from GAP-001: Joern's code-property-graph and slicing model may provide useful second-opinion structure/flow evidence where CodeQL coverage or query ergonomics differ.

Install only if a benchmark demonstrates information not already provided by KRISHNA + CodeQL. Otherwise mark REJECTED_DUPLICATE.

Proposed placement:
- E:\\Krishna-The GOD\\tools\\joern\\
- E:\\Krishna-The GOD\\state\\analysis\\joern\\

Acceptance benchmark:
Use the exact same 20-50 seeded flow/architecture fixtures used for CodeQL. Record unique true positives, false positives, runtime, RAM, disk, language coverage and evidence quality. Require a measurable unique benefit before permanent installation.

## GAP-003 — External agent-security benchmark corpus

Status: RESEARCH_MORE
Priority: MEDIUM
Candidate: uber/ADR benchmark concepts/corpus.
Reason not installed now: KRISHNA already has KABACH, Shared Action Bus, policy gates and deterministic trajectory evaluation. ADR adds useful AI/MCP attack benchmarking and normalized traces, but its benchmark environment must be treated as hostile test material rather than production runtime.

PC rule:
If used, place only in a disposable isolated security lab/worktree/VM. Never import intentionally vulnerable benchmark dependencies into KRISHNA's production environment.

Acceptance tests:
- Run only bounded defensive scenarios.
- Map every scenario to a KRISHNA policy/trajectory expectation.
- Confirm forbidden tool/egress/approval-bypass trajectories are rejected.
- Save only sanitized benchmark results to regression memory.
- No credentials, production endpoints or live business data.

## GAP-004 — Architecture visualization renderer

Status: PLANNED_PC
Priority: MEDIUM
Candidate: tt-a1i/archify
Decision already made: presentation/evidence layer only; KRISHNA remains architecture authority.

Proposed placement:
- E:\\Krishna-The GOD\\tools\\archify\\
Generated output must live outside canonical source files unless explicitly approved.

Before installation:
pin exact version/commit; verify MIT/source/hash/third-party notices; disable update checks; isolate dependencies; confirm no telemetry/network requirement for rendering.

Acceptance tests:
- Render KRISHNA architecture from generated IR.
- Verify diagram claims map back to repository evidence.
- Before/delta/after output is deterministic.
- No source mutation.
- No autonomous merge/deploy/spend/approval.
- Missing evidence is shown as unknown rather than invented.

## GAP-005 — External trajectory/observability stack

Status: REJECTED_DUPLICATE unless future scale proves need
Candidates studied: OpenSearch Agent Health, Arize Phoenix, Langfuse.
Current decision: KRISHNA now has objective trajectory evaluation, evaluator calibration, existing event/action history, verification, regression memory and Project Perfection. Do not add a second observability authority now.

Re-open trigger:
Only reconsider if KRISHNA needs multi-machine trace storage, large experiment comparison, standardized OpenTelemetry export, or a UI capability that cannot be added economically to the existing Control Room.

## PC Gap Verification Dashboard

Future Control Room section: Architecture Intelligence -> Gap Registry.

For each gap show:
- ID / capability
- status
- current KRISHNA coverage
- external candidate
- exact installed version/commit
- license verdict
- privacy/local-only verdict
- install path
- adapter health
- last benchmark date
- acceptance tests passed/total
- resource cost
- unique improvement over native KRISHNA
- owner approval state

Global readiness rule:
A gap may change from INSTALLED_UNVERIFIED to VERIFIED only when all mandatory acceptance tests pass. Installation alone never closes a gap.

## Recheck Procedure Before Future PC Work

1. Read this registry.
2. Re-run ArchitectureTruthAudit and current capability inventory.
3. Mark gaps already closed by newer KRISHNA code as REJECTED_DUPLICATE.
4. Re-check upstream repository activity, security advisories and license.
5. Install one candidate at a time in E:\\Krishna-The GOD\\tools.
6. Use a disposable/read-only KRISHNA snapshot first.
7. Run the gap's acceptance benchmark.
8. Compare against native KRISHNA baseline.
9. Keep only measurable unique improvement.
10. Connect through a read-only evidence adapter.
11. Run full KRISHNA regression/browser/security verification.
12. Present evidence to owner before enabling it in normal workflows.

Last research basis: CodeQL, Joern, Uber ADR, Agent Health, Phoenix, Promptfoo, Archify and KRISHNA native architecture-intelligence comparison.


## GAP-006 — Mutation testing / test-strength measurement

Status: PLANNED_PC
Priority: HIGH
Gap owner: Verification Engine + Project Perfection
Candidates:
- Python: mutmut
- JavaScript/TypeScript: Stryker
Research reference: anvesx/repo-analyser uses mutation testing specifically to answer whether tests are behaviorally meaningful rather than merely passing.

Why missing:
KRISHNA currently checks compilation, unit/integration tests, browser E2E, architecture truth and regression evidence. Those prove that the present implementation passes its tests, but they do not prove the tests fail when behavior is subtly broken.

PC placement proposal:
- E:\\Krishna-The GOD\\tools\\mutation\\
- E:\\Krishna-The GOD\\state\\analysis\\mutation\\
- E:\\Krishna-The GOD\\reports\\verification\\mutation\\

Integration:
Project Perfection identifies a high-risk changed/hotspot component -> mutation adapter selects a bounded target -> tool mutates only disposable shadow/worktree -> existing tests run -> surviving mutants become TEST_GAP evidence.
Never mutate canonical/live source.

Acceptance tests:
1. Seed a function with meaningful tests; common mutants must be killed.
2. Remove/weakly assert one behavior; at least one relevant mutant must survive and be reported.
3. Confirm all mutations occur only in disposable/shadow state.
4. Confirm timeout/hung mutants are bounded and cleaned up.
5. Capture killed/survived/timeout/error counts and exact mutated location.
6. Establish baseline mutation score per critical component, not one vanity repo-wide score.
7. Run only bounded targets by default to control CPU/time.
8. A surviving mutant must create a verification/test-gap finding, never an automatic production patch.

Gap closed when:
KRISHNA can demonstrate that tests detect deliberately introduced behavioral faults in critical changed code, with bounded local resource use and no live-source mutation.

## GAP-007 — Structural/API drift snapshots

Status: PLANNED_NATIVE_OR_PC
Priority: HIGH
Gap owner: Architecture Intelligence
Research reference: simonrueba/ariadne tracks public API surface snapshots, coupling/instability and structural drift and can deny new cycles/API growth.

Why missing:
KRISHNA can inspect current graph cycles, rules and blast radius, but it does not yet persist a canonical architecture/API baseline and explain exactly what structural contract changed between approved states.

Preferred implementation:
Native lightweight snapshot/diff in ProjectGraph/ArchitectureTruth first. Do not install Ariadne unless its compiler-grade SCIP symbol/reference graph demonstrates unique value.

Acceptance tests:
1. Snapshot nodes, edges, public/API-marked symbols and selected coupling metrics at approved baseline.
2. Add an edge -> diff reports it.
3. Remove/rename a public API -> diff reports breaking/removal evidence.
4. Introduce a cycle -> delta gate identifies it as newly introduced rather than inherited.
5. Pre-existing debt remains visible but does not masquerade as a new regression.
6. Snapshot has deterministic schema/version/hash.
7. Owner can distinguish CURRENT DEBT vs NEW DRIFT.

Gap closed when:
Every proposed architecture-affecting change can show Before -> Delta -> After and identify newly introduced structural risk separately from inherited risk.

## GAP-008 — Hermetic fake-home agent evaluation

Status: PLANNED_NATIVE
Priority: MEDIUM-HIGH
Gap owner: Agent Evaluation + Shadow Workspace
Research reference: GoogleCloudPlatform/evalbench runs agent CLIs with isolated fake HOME/config directories so evaluations do not contaminate the real machine.

Why missing:
KRISHNA has shadow project workspaces, but agent/CLI evaluation should also isolate HOME-level state such as config files, caches, MCP settings and credentials references.

Proposed PC layout:
- E:\\Krishna-The GOD\\workspace\\agent-eval\\<run-id>\\home\\
- E:\\Krishna-The GOD\\workspace\\agent-eval\\<run-id>\\repo\\
- E:\\Krishna-The GOD\\reports\\agent-eval\\

Acceptance tests:
1. Evaluation writes HOME/config/cache only inside run sandbox.
2. Real user/KRISHNA HOME files remain byte-identical.
3. No real credentials are copied; use synthetic fixtures.
4. Parallel runs receive different homes.
5. Failed/cancelled runs clean disposable state according to retention policy.
6. Required evidence can be retained while sensitive/transient state is deleted.
7. Network/egress policy remains governed by KABACH.

Gap closed when:
Agent evaluation can run realistic CLI/tool scenarios without changing the real KRISHNA/user configuration environment.

## GAP-009 — Inherited-vs-new finding gate

Status: PLANNED_NATIVE
Priority: HIGH
Gap owner: Architecture Intelligence + Verification
Research reference: fallow-rs/fallow supports change gates that distinguish inherited findings from newly introduced findings.

Why useful:
A repository with existing technical debt should not make every future change impossible, but KRISHNA must prevent new debt from being silently added.

Acceptance tests:
- Baseline known findings with stable fingerprints.
- Same inherited finding remains visible but does not count as newly introduced.
- New cycle/boundary violation/security/test-gap is NEW and can block promotion.
- Fixed inherited finding becomes RESOLVED.
- Changed fingerprint/location is conservatively re-evaluated, not silently inherited.
- Baseline updates require verified evidence/owner-controlled policy.

Gap closed when:
Verification reports NEW / INHERITED / RESOLVED findings separately and promotion policy can fail on NEW critical regressions without hiding old debt.

## GAP-010 — Cross-repository service/dataflow graph

Status: RESEARCH_MORE
Priority: MEDIUM
Candidate reference: enola-labs/enola
Why not install now:
KRISHNA's current architecture intelligence is repository/project oriented. LR Universe will eventually need verified cross-repo relationships such as frontend route -> API -> service -> DB/topic, but installing another graph engine now would be premature.

Re-open trigger:
When KRISHNA actively manages multiple independent LR company/service repositories and needs impact analysis across repository boundaries.

Acceptance benchmark:
Use at least three real but read-only LR service repos. Require deterministic cross-repo links, local-only analysis, evidence locations, and measurable unique information not obtainable from KRISHNA's native project graph. Otherwise reject as duplicate.
