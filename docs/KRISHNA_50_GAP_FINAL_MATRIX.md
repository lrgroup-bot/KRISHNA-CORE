# KRISHNA 50-Gap Final Implementation Matrix

Status: canonical planning matrix for the 50-gap program
Branch: `feature/archify-architecture-intelligence`
Policy: FREE-ONLY, LOCAL-FIRST, SUDARSHAN-GOVERNED

## Core rule

KRISHNA learns from public/open research but keeps its own architecture.

**OWNER RULE — If a required capability cannot be legally and genuinely installed for free, KRISHNA will build its own implementation inside our architecture from lawful public ideas, papers, standards, specifications and documented techniques. We will not buy the dependency, copy proprietary/paid source code, bypass licensing, or make a paid/cloud service mandatory.**

- If KRISHNA already has a real foundation, extend that foundation.
- If the missing capability is reasonably implementable, build it natively.
- If the problem needs a mature specialist engine or maintained external intelligence, use a genuinely free/open-source local tool behind a KRISHNA adapter.
- External tools are evidence instruments only. They never become policy, approval, repair, promotion or execution authority.
- Paid, restricted, cloud-only or proprietary tools are not required dependencies.
- Do not copy proprietary/paid source code. Public ideas, algorithms, papers, standards and documented techniques may inform an independent KRISHNA implementation.
- Re-check license, source integrity, hashes, privacy and current KRISHNA overlap immediately before every installation.
- Nothing closes a gap until its acceptance tests pass with evidence.
- No external tool, Rishi, model, plugin, worker or specialist may bypass Sudarshan / Policy Kernel / Shared Action Bus for a side effect.

## Final count

| Decision | Count | Meaning |
|---|---:|---|
| EXTEND_KRISHNA | 16 | A real foundation exists; strengthen it instead of creating a duplicate system. |
| BUILD_NATIVE | 25 | Implement the missing capability in KRISHNA's own design. |
| FREE_OSS_INSTRUMENT | 6 | Install a free/open specialist engine, but keep intelligence/policy in KRISHNA. |
| OPTIONAL_FREE_TOOL | 1 | Useful presentation/lab tool, not required for correctness. |
| MERGE_OR_REJECT | 2 | Duplicate/separate installation is unnecessary. |
| **TOTAL** | **50** | |

## Gap-by-gap decision

| Gap | Capability | Final decision | KRISHNA ownership / external role |
|---:|---|---|---|
| 001 | Interprocedural source-to-sink dataflow | FREE_OSS_INSTRUMENT | Use free local program-analysis evidence (Joern primary candidate; Semgrep CE complementary where useful). KRISHNA owns queries/rules, evidence normalization, risk interpretation and action policy. No paid CodeQL dependency. |
| 002 | Second CPG/backward-slicing engine | MERGE_OR_REJECT | Merge into GAP-001. Do not install a second graph engine unless a controlled benchmark later proves unique evidence. |
| 003 | Agent-security benchmark corpus | BUILD_NATIVE | Recreate safe/inert attack fixtures in KRISHNA's Security Lab from public techniques; do not import vulnerable production runtimes. |
| 004 | Architecture visualization renderer | OPTIONAL_FREE_TOOL | Archify may be installed later only as a renderer. ProjectGraph/ArchitectureTruth remain authoritative. |
| 005 | External trajectory/observability stack | MERGE_OR_REJECT | Reject current Phoenix/Langfuse/Agent-Health-style duplicate runtime. Re-open only for a proven future scale requirement. |
| 006 | Mutation testing | FREE_OSS_INSTRUMENT | Use free mutators (Python/JS as applicable) only on disposable workspaces; KRISHNA selects targets, scores survivors and creates TEST_GAP evidence. |
| 007 | Structural/API drift | EXTEND_KRISHNA | `ProjectGraph.structural_snapshot()` / `structural_diff()` foundation exists. Finish baseline persistence, API contract scope, NEW/INHERITED integration and acceptance proof. |
| 008 | Hermetic fake-HOME agent evaluation | BUILD_NATIVE | Add isolated HOME/config/cache/credentials fixtures to Shadow/Agent Evaluation. |
| 009 | NEW / INHERITED / RESOLVED finding gate | BUILD_NATIVE | Native finding fingerprints and owner-controlled baseline lifecycle. |
| 010 | Cross-repository service/dataflow graph | EXTEND_KRISHNA | Extend canonical ProjectGraph when multiple LR/KRISHNA repos need verified cross-repo links. No second graph authority. |
| 011 | Property-based/generative invariants | FREE_OSS_INSTRUMENT | Hypothesis may generate/shrink inputs; KRISHNA defines invariants, sandboxing, budgets and permanent regression fixtures. |
| 012 | Deterministic concurrency/race exploration | BUILD_NATIVE | First build deterministic race/interleaving fixtures for Shared Action Bus, workers and state transitions. External detector remains optional benchmark only. |
| 013 | Fault injection/resilience | BUILD_NATIVE | Add KRISHNA-owned failure seams for disk, SQLite, provider, worker, browser and file-operation failures. |
| 014 | Supply-chain provenance/vulnerability gate | FREE_OSS_INSTRUMENT | Use free local scanners/databases (OSV Scanner plus free SBOM/provenance tools selected at install time); KABACH owns allow/deny/promotion policy. |
| 015 | Async/thread/resource leak detection | BUILD_NATIVE | Native tracemalloc/process/thread/task lifecycle baselines first. Add a specialist detector only if a seeded leak proves native checks insufficient. |
| 016 | Performance regression budgets | BUILD_NATIVE | Versioned KRISHNA baselines, robust repetitions, wall time, peak memory and absolute/percentage gates. |
| 017 | API/schema/database migration compatibility | BUILD_NATIVE | Native old-contract fixtures, disposable migrations, rollback/recovery and destructive-migration owner gate. |
| 018 | Prompt/tool/repository injection benchmark | BUILD_NATIVE | Create KRISHNA-owned inert adversarial fixtures mapped to KABACH/Sudarshan expectations. |
| 019 | SQLite corruption/integrity/restore | BUILD_NATIVE | Native disposable DB corruption, WAL/journal crash, integrity check, quarantine and idempotency recovery lab. |
| 020 | Backup restore/disaster recovery proof | BUILD_NATIVE | Native clean-root restore drill with manifests, hashes, RPO/RTO and service-start verification. |
| 021 | Network partition/dependency faults | FREE_OSS_INSTRUMENT | Use a free local fault proxy such as Toxiproxy only as an injector; KRISHNA owns scenarios, retry/idempotency policy and pass/fail evidence. |
| 022 | Clock/time/expiry faults | BUILD_NATIVE | Introduce KRISHNA clock abstraction/test seams for jumps, DST, timezone, lease/token expiry and stale schedules. |
| 023 | Windows/Unicode/path torture | BUILD_NATIVE | Native Windows fixture corpus: spaces, Odia/Hindi/Unicode, long paths, reserved names, locks and permission failures. |
| 024 | Secret lifecycle | FREE_OSS_INSTRUMENT | Free local secret scanner (Gitleaks; optional second opinion only if justified). KRISHNA owns quarantine, redaction, owner-gated rotation and revocation verification. |
| 025 | Model nondeterminism/behavior stability | BUILD_NATIVE | Native repeated-run distributions, forbidden-action rate, model/config fingerprint and upgrade regression replay. |
| 026 | Non-malleable memory provenance/authority | EXTEND_KRISHNA | Extend BRAHMA/BRAHMAGYAN provenance so transformations never upgrade source authority; confidence and execution authority remain separate. |
| 027 | Memory-poisoning benchmark | BUILD_NATIVE | Build private/inert observation, summary, repetition, previous-agent and procedural-memory poison fixtures. |
| 028 | RAG claim faithfulness/citation attribution | BUILD_NATIVE | Native atomic claim -> exact evidence span -> support/contradiction/unknown -> source version/hash contract. |
| 029 | Source independence/corroboration graph | EXTEND_KRISHNA | `BrahmaMemoryIntelligence.source_summary()` and provenance-family logic already provide a foundation; strengthen copy/syndication/derivation lineage. |
| 030 | Contradiction + temporal knowledge | EXTEND_KRISHNA | Temporal records, supersession and contradiction ledger already exist; finish automatic conflict linking, freshness gates and decision behavior. |
| 031 | Retrieval poisoning/sleeper documents | BUILD_NATIVE | KRISHNA-owned poisoned-corpus lab; retrieved instructions remain untrusted data and never gain tool authority. |
| 032 | Event/message loss, duplicate and out-of-order delivery | EXTEND_KRISHNA | Shared Action Bus already has durable idempotency/fail-closed indeterminate execution. Add sequence/gap/out-of-order/restart/dead-letter tests around event/worker layers. |
| 033 | Multi-agent partial failure/stale plans | EXTEND_KRISHNA | Extend orchestrator/agent runtime with evidence-version and precondition revalidation; missing worker output cannot count as consensus. |
| 034 | Cache/vector-index consistency/rebuild proof | BUILD_NATIVE | Derived indexes become disposable, version/hash-linked state rebuildable from canonical provenance-bearing knowledge. |
| 035 | Decision confidence calibration/abstention | EXTEND_KRISHNA | `EvaluatorCalibration` is a useful foundation. Add empirical probability calibration, task-specific bins and ABSTAIN/NEED_MORE_EVIDENCE behavior. |
| 036 | Evidence aging/revalidation | EXTEND_KRISHNA | BRAHMA temporal/freshness foundation exists. Bind decision proofs/approvals to versions/hashes and force revalidation before execution. |
| 037 | Long-horizon goal-drift tests | BUILD_NATIVE | Build our own multi-turn pressure/inherited-context scenarios; owner objective and policy remain fixed authority. |
| 038 | Runaway tool loop/resource guard | EXTEND_KRISHNA | `ResourceGovernor` exists with concurrency/CPU/memory budgets. Add action-rate/retry/failure-fingerprint/time/token/network budgets and circuit breaking. |
| 039 | Multi-agent collusion/correlated-verifier resistance | BUILD_NATIVE | Record model/source/prompt/evidence independence; quorum must weight independence, not headcount. Preserve dissent. |
| 040 | Causal-claim grounding | BUILD_NATIVE | Native causal-vs-correlational claim type, assumptions/estimand/data/code evidence and UNKNOWN when identification fails. Standard free math/stats libraries are implementation dependencies, not authority. |
| 041 | Self-improvement holdout/rollback gate | EXTEND_KRISHNA | Mrityunjaya/Shadow/Project Perfection already provide repair/verification foundations. Add frozen holdouts, baseline-vs-candidate metrics, contamination checks and promotion policy. |
| 042 | Fresh-session resumability/handoff proof | BUILD_NATIVE | Durable explicit task/evidence ledger sufficient for a new session to continue safely without hidden chain-of-thought. |
| 043 | Harness-vs-model regression isolation | BUILD_NATIVE | Native matched-model and matched-harness A/B evaluation with version/resource fingerprints. |
| 044 | Step-level trajectory hijack localization | EXTEND_KRISHNA | Extend `AgentTrajectoryEvaluator` from action-order checks to injection-point / first-corrupted-step / propagation evidence. |
| 045 | Specification gaming/proxy-objective detection | BUILD_NATIVE | Objectives carry protected constraints and anti-metrics; metric improvement cannot silently degrade owner outcomes. |
| 046 | Resource/economic attack accounting | EXTEND_KRISHNA | Extend ResourceGovernor with per-task cumulative time/storage/network/tool/quota accounting; free-tier exhaustion never authorizes paid fallback. |
| 047 | Self-verification independence score | EXTEND_KRISHNA | `IndependentCriticVerifier` exists. Add model/method/evidence/source dependency fingerprints; deterministic checks outrank correlated LLM agreement. |
| 048 | Governance kill-switch/authority leases | EXTEND_KRISHNA | Sudarshan/Policy/Action Bus are the correct authority layer. Add local global pause, scoped expiring grants, restart-safe expiry and mandatory revalidation after pause. |
| 049 | Verification artifact integrity/tamper evidence | EXTEND_KRISHNA | Extend Project Perfection/Evidence outputs with manifest/hash/version binding; post-verification mutation invalidates proof. |
| 050 | Gap Registry self-audit/retirement | BUILD_NATIVE | Native registry lifecycle: last-reviewed/upstream/version/reopen trigger; retire obsolete/duplicate gaps; re-open on license/security/capability change. |

## The six free specialist-tool slots

These are not six new brains. They are instruments behind KRISHNA adapters.

1. **Program analysis** — Joern as primary free candidate; Semgrep CE may complement fast rule checks. One canonical KRISHNA analysis adapter.
2. **Mutation engine** — a free Python mutator and a free JS/TS mutator only where those languages exist.
3. **Property generator** — Hypothesis for Python input generation/shrinking.
4. **Supply-chain scanner** — OSV Scanner plus the minimum free SBOM/provenance utilities required by acceptance tests.
5. **Network-fault injector** — Toxiproxy or a smaller free local substitute only if it passes the benchmark.
6. **Secret detector** — Gitleaks local CLI as primary candidate; no paid Action/service dependency.

All tool versions must be pinned and re-verified immediately before installation. Their output is untrusted evidence until normalized and checked by KRISHNA.

## Optional tool

**Archify** may remain an optional local renderer. It must not become the architecture source of truth. If KRISHNA's own Control Room renderer reaches the required quality, mark GAP-004 `REJECTED_DUPLICATE` and do not install Archify.

## Paid/restricted-tool rule

A paid/restricted feature never creates a purchase requirement.

Decision order:

1. Find a genuinely free/open local equivalent.
2. If a free specialist engine exists, use it behind an adapter.
3. If the remaining capability is implementable safely, design and code a KRISHNA-native implementation from public principles/standards/research.
4. Do not copy proprietary/paid source code, bypass licensing, or disguise a restricted engine.
5. If no safe implementation is currently practical, keep the gap explicit and fail closed rather than pretending it is solved.

**Owner directive: what we cannot legally install free, we make ourselves in KRISHNA.** This means an independent implementation of the needed capability using lawful public knowledge—not a copied or reverse-engineered proprietary product.

## Nine native KRISHNA subsystems

The 50 gaps must not become 50 disconnected features. Implement them through these canonical owners:

1. **Architecture Intelligence** — GAP 001/002/004/007/009/010 plus analyzer adapters.
2. **Verification Lab** — GAP 006/008/011/012/016/017/035/042/043/049.
3. **Reliability & Disaster Lab** — GAP 013/015/019/020/021/022/023/032/034.
4. **KABACH Security Intelligence** — GAP 003/014/018/024/027/031/044.
5. **BRAHMAGYAN Knowledge Integrity** — GAP 026/028/029/030/034/036.
6. **Agent & Rishi Evaluation** — GAP 025/033/035/037/039/044/047.
7. **Decision Intelligence** — GAP 035/036/039/040/045/047.
8. **Self-Improvement Gate** — GAP 041/043/049/050.
9. **Sudarshan Governance** — GAP 032/036/038/041/045/046/048/049 plus every side-effect boundary.

A gap may belong to more than one subsystem, but it gets one canonical implementation rather than duplicate code.

## Recommended implementation order

### Phase A — No downloads

Implement/finish the native authority and evidence foundations first:

- GAP-007 structural drift acceptance + persistence
- GAP-009 finding delta gate
- GAP-026 memory authority/provenance inheritance
- GAP-029/030 knowledge integrity completion
- GAP-032 event correctness fixtures
- GAP-036 evidence/approval revalidation
- GAP-038 runaway loop guard
- GAP-046 resource accounting
- GAP-047 verifier independence
- GAP-048 kill switch/authority lease
- GAP-049 evidence manifest integrity
- GAP-050 registry self-audit

This establishes the control plane that will later govern external tools.

### Phase B — Native verification/reliability labs

Build GAP-008/012/013/015/016/017/019/020/022/023/025/027/028/031/033/034/035/037/039/040/042/043/045.

Each capability starts with a deliberately failing fixture and is accepted only when KRISHNA detects/contains it and a benign fixture still passes.

### Phase C — Install free instruments one at a time

For each candidate:

`license/source/hash -> isolated E:\\Krishna-The GOD\\tools\\<tool> -> disposable KRISHNA snapshot -> seeded benchmark -> adapter -> resource measurement -> security/privacy verification -> keep/remove decision`

No bulk installer should mark every tool trusted merely because installation succeeds.

### Phase D — Optional presentation

Evaluate Archify only after native architecture evidence is stable. Remove/skip it if it does not provide measurable presentation value over Sudarshan Control Room.

## Definition of done

The 50-gap program is complete only when every row is one of:

- `VERIFIED_NATIVE`
- `VERIFIED_FREE_INSTRUMENT`
- `MERGED_DUPLICATE`
- `REJECTED_DUPLICATE`
- `REJECTED_RISK`

`INSTALLED`, `CODE_WRITTEN`, `TEST_EXISTS` and `LOOKS_GOOD` are not completion states.

For mutating/external-world behavior, the final execution path remains:

`Evidence -> KRISHNA reasoning -> independent verification -> Sudarshan policy/authority -> owner approval where required -> exact payload revalidation -> Shared Action Bus -> side effect -> post-verification -> learn/rollback`
