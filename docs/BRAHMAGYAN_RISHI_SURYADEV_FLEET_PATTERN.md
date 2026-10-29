# BRAHMAGYAN + Rishi Council + SURYADEV: scalable many-to-many research pattern

## Decision (one authoritative learning system)

**Do not divide Rishis by the number of SURYADEV computers.** Specialist identities are logical skill profiles; computers are a shared resource pool. The observed feature branch has **31 registered Council profiles (Rishi and Acharya)**, not yet the proposed 35. Never hardcode 31 or 35 into resource allocation. Use `RishiCouncil.list()` at runtime. A new approved Council member becomes eligible without reassignment of PC ownership.

### Division of authority

1. **KRISHNA** — ultimate policy, scope, private-source approval and security supervision; avoid per-tab operations.
2. **BRAHMAGYAN** — one durable knowledge/missions/evidence/uncertainty/exam record, L0–L8. Does NOT invent evidence, perform source acquisition, set questions, grade answers, or run unapproved external commands.
3. **Rishi Council** — each topic's relevant Rishi(s) decompose *why/what/how/when/where* into specific investigative questions. Different specialists seek supporting evidence, contradiction, falsification, transfer, practical proof; Council members (including registered Acharyas) are academic profiles, not necessarily separate live LLM processes.
4. **BRAHMA execution scheduler** — central backlog ownership, device authentication, task leasing, priorities and capacity. A *separate/new coordinator* is unnecessary. Runtime cross-machine leases are **not yet wired**.
5. **SURYADEV 1..N** — owner-paired, measured machines collecting and indexing permitted website, video captions, PDF, book and other approved sources. They return source-aligned evidence and actual errors. Nodes never award mastery scores or widen URL permissions.
6. **Central local Ollama** — shared private network inference where genuinely required (Rishi evidence reasoning/analysis and exam preparation), never a mandatory 9B model on each laptop; inference capacity independently scheduled.
7. **CHANDRADEV** — existing visual QC peer; independent fleet-machine monitoring is an expansion to build separately.

### Information and control flow

```text
KRISHNA approved objective
          |
          v
BRAHMAGYAN: canonical mission, history, source/claim/exam ledger
          |
          v
RISHI Council: subject owner + counterexample + method specialists
          |
          v
BRAHMA: authenticated task queue / priorities / idempotent leases
          |
          v
SURYADEV node pool [1] [2] [3] ... [N] (no permanent Rishi affinity)
          |
          v
EVIDENCE: original URL / video timestamp / PDF page / book line
          | + content hash + observed conditions + limitations
          v
BRAHMAGYAN L0 candidate evidence
          |
          v
RISHI independence checks, challenges and lab applications
          |
          v
BRAHMAGYAN verified claims / disputed claims / exact-source retrieval
          |
          v
END OF DAY BRAHMA selects exam time
 -> Subject RISHI creates theory/practical exam THROUGH BRAHMAGYAN
 -> Learner/Rishi-team submits unseen answers and practical test artifacts
 -> DIFFERENT RISHI assesses answers and tests
 -> BRAHMAGYAN records both, does not self-grade
 -> failed/uncertain topics become a new research task; later retest
```

### 1 PC, 5 PCs and 10 PCs

- **1 node:** It may sequentially serve requests from *all* registered Council profiles, but only with its measured available parallel slots. 35 logical Rishis does **not** mean 35 concurrent browser tabs.
- **5 nodes:** Any Rishi may use any of the 5 nodes, possibly multiple simultaneously. The mean 35/5=7 is a display statistic only, **not** a binding assignment.
- **10 nodes:** Again no fixed 35/10 allocation. Urgent research may use several nodes while other Rishis wait. An exhausted or failed node's leases return safely to the backlog.
- **0 healthy nodes:** No new dispatch. Preserve queue, checkpoint, retry/dead-letter. Models are not assumed healthy just because their processes exist.

### Resource scheduler contract

- The new `core/krishna_core/suryadev_fleet_policy.py` implements a **read-only planning function**, `plan_rishi_collection`, and BRAHMAGYAN exposes `draft_suryadev_fleet_plan` for a real existing mission.
- It requires Council attribution, owner approval, queued state, authenticated `suryadev-` device identity, online worker, recent heartbeat (150s), current CPU/RAM/disk telemetry (45s), known remaining slots and compatible capabilities; otherwise it **fails closed**.
- Hard admission ceiling 85%; at 75% any measured node is limited to a single remaining admission slot. These are **new-job admission** rules, not hard OS CPU/RAM throttles or a guarantee against sudden resource spikes.
- Equal-priority tasks balance logical Rishi requests, while higher priority goes first. No Rishi or PC has permanent hardware ownership. Video provider 429 and media compliance restrictions remain separately enforced by the existing collectors.
- Planner output is `proposed_not_leased`. It **does not** establish a network connection, send a command, allocate a lease, mark learning complete or certify an exam. **Authenticated registry telemetry extension, BRAHMA durable leases, heartbeat renewal, crash recovery and two-PC tests are not yet implemented.**

### Six-hour / 24x7 continuity

- Six hours means a requested **work session horizon**, not six hours of asserted learning. BRAHMA maintains approved future work and triggers refill before queue exhaustion. Prior six-hour low-water exchange on KRISHNA and SURYADEV already exists, but cannot guarantee endless original material from an exhausted owner-approved catalogue.
- Rishi tasks must preserve exactly what/why/where/when/how was sought, original source link, exact passage/page/timestamp, hash, observation date, unresolved questions, contradictions, and tests. Do not infer deep understanding from a source job marked "done".
- External URLs may change or disappear. Preserve user-authorized short excerpts, content hashes and provenance when permitted; retain source links and retrieval state. Don't promise a remote source can always be retrieved again.

### Exam protocol through BRAHMAGYAN, authority from Rishis

- `BrahmagyanRuntime.create_daily_exam(..., issued_by=<Council member ID>)` records Rishi-authored questions; no BRAHMAGYAN question generator exists.
- `record_daily_exam_attempt(..., grader=<different Council member ID>, method='independent_rishi_review')` records grading. Same Rishi cannot issue and grade their own test; SURYADEV cannot grade.
- The recorded thresholds are 85% theory, 90% practical, minimum 60% per question. Practical evidence requires artifact hashes/test descriptions. This remains **reported test evidence** until signed provenance and reproducible execution are validated.
- BRAHMAGYAN maintains candidate knowledge/claim maturity and written exam history. Daily automatic test generation, secure evaluator execution, next-day/7-day/30-day transfer retests and independently verified identities **remain to be built**; avoid claiming a recorded grade is actual mastery.

## Implementation/acceptance sequence

1. Run read-only Council-to-machine scheduling policy unit tests against 1/5/10 synthetic PCs.
2. Extend owner-paired SURYADEV heartbeat data to include *measured, fresh* normalized hardware/capacity data, independently authenticated at the CORE API boundary.
3. Add BRAHMA durable queue + atomic task leases, lease expiry, idempotent evidence receipts, priority/fairness policy, rollback and privacy/source-allowlist checks.
4. Build end-to-end 2-PC research test with real checkpoints, loss/recovery and central local Ollama offloading; record actual throughput under the 85% guard.
5. Connect Rishi evidence review and exam issuance through authorized BRAHMAGYAN interfaces with genuine separate examiner contexts, auditable practical evaluation and spaced retesting.
6. Run Windows/backend/browser/APK gates before considering a universal EXE or production merge.

**Current status:** Policy + recording gates in draft PR only. It is not a deployed multi-machine autonomous fleet.
