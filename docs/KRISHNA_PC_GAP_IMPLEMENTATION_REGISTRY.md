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


## GAP-011 — Property-based / generative invariant testing

Status: PLANNED_PC
Priority: HIGH
Candidate: HypothesisWorks/hypothesis
Gap owner: Verification Engine + Project Perfection

Why missing:
Example-based unit tests cover inputs humans remembered to write. Property-based testing generates many valid/invalid edge cases, shrinks failures to a minimal counterexample, and can replay discovered failures. This is complementary to mutation testing: mutation asks whether tests catch broken code; property testing searches the input/state space for cases that break invariants.

PC placement:
- E:\\Krishna-The GOD\\tools\\property-testing\\
- E:\\Krishna-The GOD\\state\\verification\\hypothesis\\
- E:\\Krishna-The GOD\\reports\\verification\\property\\

Acceptance tests:
1. Define invariants for high-risk pure functions and parsers.
2. Seed at least one hidden edge-case bug and prove Hypothesis finds and shrinks it.
3. Convert critical discovered counterexamples into permanent explicit regression fixtures; do not rely only on Hypothesis's internal example database.
4. Bound examples/deadlines/resources under Resource Governor.
5. No generated input may trigger external side effects without a fake/sandbox adapter.
6. Record seed/profile/version and a reproducible failure representation where supported.
7. Start only on critical modules changed by a proposal; no uncontrolled whole-repo fuzz storm.

Gap closed when:
Critical deterministic components have property/invariant tests that discover edge cases beyond hand-written examples and preserve important failures as permanent regression evidence.

## GAP-012 — Deterministic concurrency / race exploration

Status: RESEARCH_MORE / PLANNED_PC
Priority: HIGH for Shared Action Bus, worker/event/job runtimes
Candidates:
- lucaswiman/frontrun
- ChidcGithub/Threadcheck
- Getego/pytest-deterministic-lab (beta/reference only)

Why missing:
KRISHNA has locks, SQLite transactions, idempotency and recovery tests, but ordinary tests may not explore dangerous thread/task interleavings. Python's evolving free-threading ecosystem increases the importance of explicit race analysis.

Decision:
Do not install a young race detector blindly. First build KRISHNA-native deterministic concurrency fixtures around critical invariants; benchmark candidate tools in isolation.

Acceptance tests:
- Concurrent duplicate action submissions never execute a side effect twice.
- Approval/promotion cannot race ahead of verification.
- Event/job state transitions remain valid under competing updates.
- Lock-protected state shows no reported race in supported detector.
- Intentionally unsafe fixture is detected and replayable.
- Every reported interleaving includes enough evidence to reproduce.
- Tool limitations (threads vs asyncio vs processes) are displayed explicitly.

Gap closed when:
Critical concurrency invariants survive bounded schedule/interleaving exploration and a seeded race is reliably detected.

## GAP-013 — Fault injection / resilience testing

Status: PLANNED_NATIVE_THEN_PC
Priority: HIGH
Candidate reference: teilomillet/ordeal
Gap owner: Mrityunjaya + Verification + Recovery

Why missing:
KRISHNA tests success/failure paths, but needs systematic injected failures at boundaries: disk full/write failure, SQLite busy/locked, timeout, malformed provider response, killed worker, partial file operation, browser crash, network unavailable and restart between durable action states.

Native-first rule:
Implement fault seams in existing adapters before considering a chaos framework. Never inject faults into live production state.

Acceptance tests:
- Inject failure before side effect -> safe retry allowed.
- Inject unknown outcome after side effect boundary -> fail closed/no duplicate execution.
- Kill/restart between action states -> durable state recovers correctly.
- Simulate disk/database/browser/network failures in disposable environment.
- Verify rollback/cleanup evidence.
- Every injected fault has stable ID, expected invariant and observed result.

Gap closed when:
KRISHNA can intentionally break its own disposable execution environment and prove core safety/recovery invariants remain true.

## GAP-014 — Software supply-chain provenance and malicious dependency gate

Status: PLANNED_PC
Priority: CRITICAL before future third-party installations
Candidates:
- google/osv-scanner for vulnerability inventory
- sigstore tooling / SLSA provenance verification
- homeofe/supply-chain-guard as a candidate to benchmark, not automatically trust

Gap owner: KABACH + Installer/Dependency Audit

Why missing:
Current SBOM/dependency inventory does not by itself prove that an artifact came from the claimed build/repository, nor comprehensively detect known-malicious packages, dependency confusion, compromised install hooks or unpinned CI actions.

Policy:
Every new external KRISHNA tool should itself pass the supply-chain gate before entering E:\\Krishna-The GOD\\tools.

Acceptance tests:
1. Generate/consume SBOM and map direct/transitive dependencies.
2. Verify artifact checksum and provenance/attestation when upstream provides it.
3. Detect a seeded known-vulnerable dependency.
4. Detect an intentionally unpinned or suspicious CI/dependency fixture where supported.
5. Offline scan mode must clearly report intelligence freshness and unavailable checks; never equate unavailable with clean.
6. Networked enrichment is opt-in and must disclose exactly what package/repo identifiers leave the machine.
7. Fail closed on incomplete critical inventory.
8. Pin scanner version and verify the scanner's own provenance before trusting its result.

Gap closed when:
KRISHNA can answer WHAT is installed, WHERE it came from, WHAT exact version/hash is running, WHAT security intelligence was checked, and which checks were unavailable.

## GAP-015 — Async/thread/resource leak verification

Status: PLANNED_PC
Priority: MEDIUM-HIGH
Candidate: deepankarm/pyleak plus native tracemalloc/process metrics
Gap owner: Verification + Resource Governor

Why missing:
A test can pass while leaving background threads, asyncio tasks, handles or growing memory behind. Long-running KRISHNA services need post-test quiescence checks.

Acceptance tests:
- Seed leaked asyncio task -> detected.
- Seed leaked thread -> detected.
- Verify clean worker returns to expected task/thread baseline.
- Repeated lifecycle test shows bounded memory/file-handle growth.
- Allowlist only explicitly persistent infrastructure.
- Capture stack/location for leaked task/thread where available.
- No false 'clean' if measurement was unavailable.

Gap closed when:
Critical long-running runtimes prove post-test quiescence and bounded resource growth across repeated start/work/stop cycles.

## GAP-016 — Performance regression budgets

Status: PLANNED_NATIVE
Priority: MEDIUM-HIGH
Gap owner: Project Perfection + Resource Governor

Why missing:
Functional correctness can regress latency, memory or CPU enough to make KRISHNA unusable, especially on the current resource-constrained machine.

Acceptance tests:
- Establish versioned baseline for selected critical operations.
- Compare candidate vs baseline with warmup/repetition and robust statistic, not one timing.
- Track wall time plus peak memory where practical.
- Separate environmental noise from material regression.
- Use percentage + absolute threshold to avoid tiny-number noise.
- Performance gate applies only to stable benchmark scenarios.
- Store hardware/runtime context with result.

Gap closed when:
A candidate repair cannot silently introduce a material performance/resource regression in critical paths.

## GAP-017 — API/schema/database migration compatibility

Status: PLANNED_NATIVE
Priority: HIGH before LR multi-service expansion
Gap owner: Architecture Intelligence + Verification

Why missing:
Structural snapshot detects removed public nodes, but not yet request/response schema compatibility, persisted-state migration safety or forward/backward compatibility.

Acceptance tests:
- Old valid API fixture remains accepted where compatibility is promised.
- Removed/renamed required field is classified as breaking.
- Database/state migration runs on disposable copy and preserves invariants/counts.
- Migration rollback/recovery behavior is explicitly tested.
- Old binary/new data and new binary/old data compatibility policy is declared per component.
- Destructive migration requires explicit owner gate and backup evidence.
- Schema delta is machine-readable and linked to blast radius.

Gap closed when:
KRISHNA can distinguish safe additive evolution from breaking API/persisted-state changes before promotion.


## GAP-018 — Repository/tool-output prompt-injection security benchmark

Status: PLANNED_PC
Priority: CRITICAL
Gap owner: KABACH + Agent Evaluation + Garuda/Garudanetra
Candidates/references:
- DaoyuanLi2816/RepoGuardBench (local repository-borne injection benchmark)
- ppradyoth/AgentInjectionBench (tool output, goal hijack, privilege escalation, exfiltration, multi-turn, MCP poisoning)
- opena2a-org/oasb (broader agent-security scenarios/MITRE ATLAS mapping)
- liu00222/Open-Prompt-Injection (research benchmark; heavier/provider-oriented)

Why missing:
KRISHNA has permission/action gates and deterministic trajectory checks, but needs a maintained adversarial corpus proving that README text, code comments, issue text, test logs, web/tool output and MCP context cannot redirect an agent into forbidden actions.

Safety rule:
Use only synthetic/inert benchmark payloads in an isolated evaluation environment. Never use real secrets, live exfiltration endpoints or production business data.

Acceptance tests:
1. Malicious repository instruction cannot override owner/policy/system authority.
2. Poisoned tool/web output cannot cause an unapproved action.
3. Canary synthetic secret is never emitted to forbidden sink/tool.
4. MCP/context poisoning cannot expand capabilities or permissions.
5. Multi-turn injection cannot persist attacker policy into trusted memory.
6. Measure attack-success rate AND false-positive/over-refusal rate; security that blocks normal work is not sufficient.
7. Keep a held-out private test split so KRISHNA cannot merely memorize public cases.
8. Dataset/report must have stable version/hash.
9. Separate agent COMPLIANCE from DAMAGE CONTAINMENT: even if the model follows bad text, structural permission/egress controls should still prevent the side effect.
10. Every failure becomes a sanitized permanent regression case.

Gap closed when:
KRISHNA passes a versioned local agent-injection corpus with zero critical forbidden side effects and an explicitly accepted false-positive rate.

## GAP-019 — SQLite corruption, integrity and restore verification

Status: PLANNED_NATIVE
Priority: CRITICAL
Gap owner: Persistence + Shared Action Bus + Mrityunjaya

Why missing:
SQLite transactions protect normal atomicity but do not prove behavior under corrupted DB/WAL files, truncated storage, disk-full conditions or restore from backup.

Acceptance tests:
- Run SQLite integrity_check/quick_check on disposable copies.
- Corrupt/truncate a test DB and prove startup refuses to call it healthy.
- Simulate WAL/journal recovery and abrupt process termination.
- Restore from a known backup into a separate location and verify schema, row counts, critical hashes/invariants and idempotency records.
- Never auto-delete the only damaged copy; quarantine before recovery.
- Record recovery point/time and data loss window.
- Database recovery must not replay an already-completed external side effect.

Gap closed when:
KRISHNA can detect corrupted persistent state, quarantine it, restore a verified copy and resume without silently losing action-safety guarantees.

## GAP-020 — Backup restore proof / disaster recovery drill

Status: PLANNED_NATIVE
Priority: CRITICAL
Gap owner: Guardian + Mrityunjaya

Why missing:
Having backup files is not evidence that KRISHNA can restore from them. Recovery must be tested end-to-end.

Acceptance tests:
1. Generate manifest of required state/config/data with hashes and schema/version metadata.
2. Restore into a clean disposable KRISHNA root, never over the live installation during a drill.
3. Verify required services can start against restored state in isolated mode.
4. Verify critical memories/action ledgers/approval state/configuration survive.
5. Measure RPO (maximum acceptable lost data) and RTO (restore duration).
6. Test missing/corrupt/latest-backup fallback to an older valid recovery point.
7. Keep secrets encrypted or separately restored under owner control.
8. Produce human-readable PASS/PARTIAL/FAIL recovery report.

Gap closed when:
A clean-machine/disposable-root drill proves a backup can actually reconstruct a safe usable KRISHNA state within declared RPO/RTO.

## GAP-021 — Network partition and dependency-failure simulation

Status: PLANNED_PC
Priority: HIGH
Candidate: Shopify/toxiproxy or a lightweight native fault proxy
Gap owner: Verification + Recovery + Resource Governor

Why missing:
Timeouts alone do not reproduce latency, connection reset, partial response, unavailable dependency or intermittent network partitions.

Acceptance tests:
- Inject latency/jitter/reset/unavailable upstream into disposable/local services.
- Verify retries are bounded and idempotent.
- Verify circuit/open-offline behavior prevents retry storms.
- Verify local-first fallback is used only where policy allows.
- Verify approval/external side-effect actions fail closed on uncertain outcome.
- Restore connection and prove controlled recovery rather than thundering-herd retry.
- No fault proxy in normal production path unless explicitly enabled for a test.

Gap closed when:
KRISHNA survives realistic dependency/network faults without duplicate actions, runaway retries or unsafe fallback.

## GAP-022 — Clock/time/expiry fault testing

Status: PLANNED_NATIVE
Priority: HIGH
Gap owner: Scheduler + approvals + leases/cooldowns + recovery

Why missing:
Wall-clock jumps, timezone/DST changes and expired tokens/leases can break cooldowns, scheduling and approval validity. Duration logic should use monotonic time where appropriate; persisted timestamps still need explicit UTC/offset semantics.

Acceptance tests:
- Wall clock moves backward/forward during cooldown/retry logic.
- DST/timezone change does not duplicate/skip a critical scheduled action unexpectedly.
- Expired approval/token/lease is rejected.
- Persisted timestamps round-trip with explicit timezone semantics.
- Duration measurements are not corrupted by wall-clock adjustment.
- Restart with stale scheduled work applies declared catch-up policy rather than blindly replaying.

Gap closed when:
Time changes cannot bypass expiry/cooldown/approval safety or cause duplicate critical execution.

## GAP-023 — Windows/Unicode/path torture suite

Status: PLANNED_NATIVE
Priority: HIGH
Gap owner: Filesystem/Installer/Shadow Workspace

Why missing:
KRISHNA is Windows-first. Normal tests may miss long paths, spaces, non-ASCII names, Unicode normalization, case behavior, reserved device names, trailing-dot/space semantics, locked files and permission failures.

Acceptance tests:
- Paths with spaces and Odia/Hindi/Unicode characters.
- Long nested paths near configured Windows limits.
- Case-only name differences and normalization-equivalent Unicode names where filesystem behavior differs.
- Reserved/invalid Windows names are rejected safely.
- Locked/read-only/permission-denied file operations fail without partial promotion.
- Shadow copy and rollback preserve filenames/content exactly.
- Generated reports safely escape paths and never reinterpret them as commands.

Gap closed when:
Critical file/install/repair operations pass the Windows path corpus without data loss, command injection or silent skip.

## GAP-024 — Secret lifecycle: detect -> quarantine -> rotate -> verify revocation

Status: PLANNED_PC + OWNER-GATED PROCEDURE
Priority: CRITICAL
Candidates: gitleaks/gitleaks and trufflesecurity/trufflehog
Gap owner: KABACH + NARAD/owner governance

Why missing:
Secret detection alone is incomplete. A leaked credential may remain valid after the finding is removed from source.

Acceptance tests:
- Detect synthetic secrets in current files and Git history.
- Distinguish verified/live vs pattern-only findings when a tool supports it, without sending real secrets to an unapproved third party.
- Quarantine evidence without echoing full secret into logs/UI.
- Owner-controlled rotation procedure produces replacement credential.
- Verify old credential is revoked/invalid using the provider's safe verification mechanism.
- Scan history/artifacts/backups for residual exposure.
- Baseline/suppression requires reason, owner and expiry; expired suppression reopens.
- Never auto-rotate production credentials without explicit owner approval.

Gap closed when:
KRISHNA tracks a secret incident through detection, containment, owner-approved rotation, old-secret revocation and residual-exposure verification.

## GAP-025 — Model nondeterminism / behavioral stability evaluation

Status: PLANNED_NATIVE
Priority: HIGH
Gap owner: BRAHMA + Agent Evaluation + Model Router

Why missing:
One successful model run is weak evidence. Agent behavior can vary across repeated runs, model versions, temperatures/providers and context ordering.

Acceptance tests:
- Repeat the same critical scenario multiple times and report pass-rate distribution, not one pass.
- Compare objective trajectory/security outcomes across allowed local/free providers.
- Track model/version/config/context fingerprint with result.
- Critical forbidden-action rate must be zero across the declared test budget.
- Report variance/confidence interval for non-binary quality metrics where appropriate.
- A mock/deterministic agent may test harness correctness but cannot substitute for real-model behavioral evidence.
- Model upgrade requires replay of critical held-out regression/security corpus.

Gap closed when:
KRISHNA knows whether a safety/quality claim is stable across repeated real-model runs rather than relying on a lucky single execution.


## GAP-026 — Non-malleable memory provenance and authority

Status: PLANNED_NATIVE
Priority: CRITICAL
Gap owner: BRAHMAGYAN + Gyan-Bhandar + BRAHMA QC + Policy Kernel
Research references:
- iluxu/memory-integrity-benchmark
- OWASP/www-project-agent-memory-guard
- memory-security research on provenance/lineage laundering

Core invariant:
Transformation does not upgrade authority. Summarizing, repeating, embedding, retrieving, quoting, reformatting or passing content through a trusted agent/tool must preserve the least-trusted relevant origin unless an explicit verified promotion process supplies independent evidence.

Required memory fields/concepts:
- origin/source identity and source class
- ingestion channel
- observed_at / valid_at / expires_at where relevant
- provenance/derivation parents
- factual confidence
- authority/permission class (separate from confidence)
- verification/corroboration evidence
- risk label
- promotion history
- supersedes/conflicts_with links

Acceptance tests:
1. Untrusted web/repository/tool text cannot become policy merely by being summarized by KRISHNA.
2. Repetition of the same source does not count as independent corroboration.
3. A trusted tool echoing an untrusted claim does not launder its origin.
4. Derived summaries retain lineage to all material source records.
5. High factual confidence never grants execution/approval authority.
6. Procedural instructions from memory cannot expand agent permissions.
7. Memory promotion requires explicit rule/evidence and leaves an audit trail.
8. Poisoned memory can be selectively quarantined/forgotten without deleting unrelated valid memory.
9. Retrieval returns authority/provenance metadata with content.
10. Unknown/missing provenance fails closed for high-risk use.

Gap closed when:
Every persisted/retrieved knowledge item carries durable provenance and an authority class that cannot be silently upgraded by transformation or repetition.

## GAP-027 — Memory poisoning benchmark and selective repair

Status: PLANNED_PC
Priority: CRITICAL
Candidates:
- iluxu/memory-integrity-benchmark
- Digital-Trust-Lab/mp-bench
- OWASP Agent Memory Guard benchmark corpus
Gap owner: Agent Evaluation + BRAHMAGYAN security

Why separate from GAP-026:
GAP-026 is the native control model. GAP-027 is adversarial proof that the model works.

Acceptance tests:
- Observation poisoning
- summary poisoning
- repeated-content/corroboration laundering
- previous-agent-output poisoning
- policy/procedure injection
- retrieval-time sleeper payload
- benign-memory false-positive corpus
- write -> retrieve -> action consequence tracking
- selective repair/quarantine and post-repair retest
- held-out private cases

Metrics:
write acceptance, poisoned retrieval rate, unauthorized action rate, containment rate, selective repair success, benign false-positive rate.

## GAP-028 — RAG claim faithfulness and citation attribution

Status: PLANNED_NATIVE_THEN_PC
Priority: HIGH
Candidates/reference metrics: Ragas faithfulness, DeepEval faithfulness/context metrics
Gap owner: BRAHMA QC + Evidence Engine

Why missing:
A response can contain a citation yet the cited passage may not support the exact claim. Retrieval relevance and answer faithfulness are different problems.

Native-first implementation target:
claim -> cited evidence span -> support verdict -> unsupported/contradicted/unknown.
Do not treat an LLM judge as ground truth; deterministic exact evidence checks and source metadata should be used where possible, with judge-based evaluation clearly labeled.

Acceptance tests:
1. Fully supported atomic claims pass.
2. Correct source but wrong cited passage fails attribution.
3. Unsupported added detail is flagged even if nearby claims are supported.
4. Contradictory retrieved sources are surfaced rather than silently averaged.
5. Citation target must exist and match stored source/version/hash.
6. Stale/expired evidence is labeled.
7. Judge disagreement/uncertainty is retained, not rounded into certainty.
8. Important claims can require independent-source corroboration.

Gap closed when:
KRISHNA can show which exact evidence supports each material claim and refuses to present unsupported claims as verified knowledge.

## GAP-029 — Source independence / corroboration graph

Status: PLANNED_NATIVE
Priority: HIGH
Gap owner: Evidence Engine + BRAHMAGYAN

Why missing:
Ten websites copying one original report are not ten independent confirmations. Corroboration must account for common origin and derivation.

Acceptance tests:
- Same URL/domain duplicate does not increase independence.
- Syndicated/copied article linked to common source counts as dependent evidence.
- Agent summaries derived from same source remain one provenance family.
- Independent primary sources increase corroboration.
- Unknown dependence is labeled UNKNOWN, not independent by default.
- Confidence calculation exposes both evidence count and independent provenance-family count.

Gap closed when:
KRISHNA distinguishes repeated evidence from genuinely independent corroboration.

## GAP-030 — Contradiction and temporal knowledge handling

Status: PLANNED_NATIVE
Priority: HIGH
Gap owner: Gyan-Bhandar + BRAHMA QC

Why missing:
Knowledge changes. A newer claim should not silently overwrite an older claim when both may have different validity periods or evidence quality.

Acceptance tests:
- Contradictory claims coexist with conflict links.
- Newer timestamp alone does not automatically make a weaker source authoritative.
- Superseded facts retain history/provenance.
- Query can request current-as-of time and receive temporally valid evidence.
- Expired/stale facts are not silently returned as current.
- Unresolved contradiction is surfaced to KRISHNA/user for high-impact decisions.

Gap closed when:
Knowledge updates preserve history and distinguish CURRENT / SUPERSEDED / CONFLICTED / STALE / UNKNOWN.

## GAP-031 — Retrieval poisoning / sleeper-document evaluation

Status: PLANNED_PC
Priority: HIGH
Candidates/reference:
- NVIDIA/garak retrieval-time sleeper poisoning proposal
- prompt-security/RAG_Poisoning_POC
- samkorn/rag-poisoning-architecture-bench

Why useful:
A malicious document can remain dormant in the corpus and activate only when an innocent query retrieves it. Write-time screening alone is therefore insufficient.

Acceptance tests:
- Poisoned document is stored in isolated test corpus.
- Benign query retrieves it.
- Retrieved instructions remain data, never authority.
- Answer remains grounded in trusted evidence.
- Tool/action policy is unchanged by retrieved text.
- Compare clean vs poisoned corpus with identical model/query/config.
- Measure retrieval contamination, answer corruption and forbidden-action rate separately.

## GAP-032 — Event/message loss, duplication and out-of-order delivery

Status: PLANNED_NATIVE
Priority: CRITICAL
Gap owner: Shared Action Bus + Event Bus + workers

Why missing:
Durable idempotency covers action execution, but distributed/multi-worker growth requires explicit tests for duplicated, delayed, missing and out-of-order events.

Acceptance tests:
- Duplicate event does not duplicate irreversible action.
- Out-of-order completion cannot precede required approval/verification state.
- Lost notification is recoverable from durable authoritative state.
- Consumer restart resumes from declared checkpoint.
- Poison/dead-letter event is isolated without blocking unrelated work.
- Event ID/correlation/causation chain survives retries.
- At-least-once delivery semantics are explicit where exactly-once is impossible.

Gap closed when:
Correctness derives from durable state/idempotency rather than assuming perfect message delivery.

## GAP-033 — Multi-agent partial-failure and stale-plan detection

Status: PLANNED_NATIVE
Priority: HIGH
Gap owner: Orchestrator + Rishi Council + Agent Runtime

Why missing:
A multi-agent plan can become invalid when one worker fails, returns stale evidence or another worker changes the underlying state.

Acceptance tests:
- One specialist timeout/failure does not let consensus pretend it participated.
- Evidence version/hash changes invalidate dependent stale recommendations.
- Plan execution revalidates preconditions immediately before action.
- Conflicting specialist outputs remain visible with provenance.
- Quorum/consensus rules cannot convert missing evidence into agreement.
- Restarted worker cannot submit an obsolete result as current without version check.

Gap closed when:
Partial failure or stale evidence cannot silently become a valid council/agent decision.

## GAP-034 — Cache/vector-index consistency and rebuild proof

Status: PLANNED_NATIVE
Priority: HIGH
Gap owner: Memory/RAG + Gyan-Bhandar

Why missing:
Caches and vector indexes are derived state. They can become stale/corrupt and disagree with canonical records.

Acceptance tests:
- Delete/update canonical source -> stale derived entry is invalidated.
- Index record carries canonical source ID/version/hash.
- Mismatch is detected at retrieval.
- Full index/cache rebuild from canonical state produces equivalent retrievable corpus within declared tolerance.
- Corrupt derived index can be discarded/rebuilt without losing canonical knowledge.
- Cache hit never bypasses provenance/expiry/authority checks.

Gap closed when:
Derived retrieval state is disposable and verifiably synchronized with canonical provenance-bearing knowledge.
