# SURYADEV evidence collection -> BRAHMAGYAN mastery (first guarded increment)

## Responsibility boundary

- **SURYADEV is an evidence collector**, not a trusted knowledge grader. It queues approved websites/YouTube-caption/PDF sources, retains precise source references and SHA-256 evidence, and indexes locally approved books. A source job marked done means collection/extraction completed, NOT learned, verified, watched end-to-end or mastered.
- **BRAHMAGYAN owns the evidence and maturity ledger (L0 through L8)**. It never writes examination questions or grades its own learning. It records what authorized Rishis submit, flags unverified attribution, and enforces evidence/maturity gates. Rishi review, source triangulation, contradiction analysis, practical replication and delayed recall remain Rishi duties, not SURYADEV collector duties.
- **BRAHMA coordinates the examination schedule and mission assignments**. Subject Rishis author and conduct the theory/practical exam; a *different* Rishi must review the results. BRAHMA/QC remains the existing authority for proposing knowledge to Gyan-Bhandar; no duplicate learning database or new coordinator is introduced.
- **KRISHNA** stays final supervisor and owner permission gate. **CHANDRADEV** is currently a camera/visual QC peer; hardware-fleet supervision is a separately unimplemented future extension.

## Collector-only Windows worker (opt-in, no Ollama)

After the approved research plan and approved local book plan exist, STOP any prior worker before starting another:

```powershell
cd "D:\Work\SURYADEV"
.\start-continuous-learning.ps1 -DataDir "D:\Work\SURYADEV-DATA" -CollectApprovedBooks
```

This uses the already existing approved `learning-plan.json` and `book-plan.json`, without deleting or changing them. **No `-UseOllama` flag**. Do not combine `-LearnApprovedBooks` (LLM interpretation mode) with `-CollectApprovedBooks`. The collector revalidates each book's original bytes against its owner-approved SHA-256, indexes existing local TXT/Markdown/PDF/EPUB material, verifies indexed lines, and marks `indexed_evidence_only`. It never asserts comprehension and never calls Ollama. Research source ingestion still transfers approved network content; no media/video download is initiated by this option.

`book-approve` remains the explicit owner approval and does an initial source index immediately. The new worker collector is an idempotent continuation/re-verification path, not a new downloader or source discovery mechanism.

## Strengthened theory/practical mastery gate

The existing `BrahmagyanRuntime` persists daily examination plans and graded attempts under its existing guarded `state.json` alongside missions/claims/debates. New missions have `daily_exam_gate_required=True`; historical persisted missions without that key retain backward-compatible legacy behavior.

- `create_daily_exam(mission_id, questions, exam_date=..., issued_by=<rishi-id>)` is a **BRAHMAGYAN recording interface for a Rishi-issued exam**, not a BRAHMAGYAN question generator. `issued_by` is mandatory and validated against the Rishi Council. At least 5 evidence-linked, substantial questions are required: **3 theoretical** and **2 practical**, including **why**, **how**, and **contradiction** reasoning. Rubrics and source references are retained.
- `record_daily_exam_attempt(exam_id, results, grader, method)` requires a **different, Council-registered Rishi** as grader, using `independent_rishi_review`; SURYADEV, BRAHMAGYAN, the issuing Rishi, or a made-up examiner ID cannot grade the exam. It records full candidate answers, rationale and evidence references. Practical items additionally need an artifact SHA-256 and test evidence. Thresholds: **85% theory**, **90% practical**, and **at least 60% on every question**. Failed attempts remain in the history.
- `daily_exam_status(mission_id)`: read-only history and passing recorded attempts. New-mission L7/L8 advances are blocked without a recorded passing exam; existing L0-L6 source and test gates remain intact.

**Truth boundary:** a named/recorded result is not cryptographically verified grader independence or proof of cognitive understanding. BRAHMA exam scheduling, automatic Rishi question generation and administration, cryptographically verified issuer/grader identity, proof of executable practical work, next-day/weekly retention exams, and certificate/signed reviewer attestation are NOT built in this increment. The dashboard should not claim those milestones were completed. For a true end-of-day process, connect this record/grade API to the future BRAHMA scheduler only after a trusted evaluator and job authorization path exist.

## Exact-source retrieval requirements

BRAHMAGYAN's evidence rows now keep URL, source_id, publication, retrieval date and content hash, plus precise locator fields where supplied: `url_fragment`, `page`, `chapter`, `section`, `line_start`, `line_end`, `start_seconds`, `end_seconds`. Future SURYADEV source bundle adapters must supply real, measured locators and verified citation spans; never fabricate precise timestamps or source-page claims.

## Remaining integration gates

1. Feed source-specific candidate bundles from **website/PDF/video/book collector** into BRAHMAGYAN using existing authenticated transport, while keeping L0 evidence separate from L2/L7 achievements.
2. Add a BRAHMA task supplier and exam scheduler that assigns a subject Rishi to generate unseen theory/practical questions at day end, and a different Rishi to independently grade answers without disclosing exam keys to the learner.
3. Require independently executable practical tests plus attributed Gautama/Bharadvaja reviews; preserve failures and counterexamples.
4. Add next-day, seven-day and monthly spaced-retention/transfer assessments with real checks. Gate stronger `mastered` claims until these are verified.
5. Run Core and standalone tests, Playwright UI regression and owner-approved laptop tests before any .exe; do not merge this draft branch automatically.

## Fleet delivery hardening and local verification — 25 October 2026

The already implemented KRISHNA HTTP route `/api/suryadev/fleet/complete`
requires an authenticated, owner-paired device and live lease. On collection,
Core stores an untrusted-source receipt and calls
`BrahmagyanRuntime.intake_suryadev_collection` to record a persistent L0
candidate. A heartbeat, a lease, and a successful local extraction are three
different events, and none means comprehension.

The portable SURYADEV fleet client now adds two fail-closed requirements:
1. **Before uploading a collected completion**, the local evidence file
   `evidence/<digest-prefix>/<sha256>.txt` must exist and its bytes must
   reproduce the finding's SHA-256 digest. A corrupt, missing or forged digest
   keeps the lease locally pending, records an integrity error and attempts
   lease renewal if expiry approaches. It never fabricates an ACK or deletes
   the evidence.
2. **Before retiring the local leased assignment**, the paired Core completion
   reply must contain `acknowledged=true`, `candidate_recorded=true` and
   a receipt matching the task ID, device ID, lease ID and local evidence
   digest. A partial acknowledgment stays retryable; Core's completion
   is idempotent for the same task/lease/hash, including after a process
   restart and candidate-inbox retry.

The node UI distinguishes `candidate_inbox_acknowledged` from mastery.
The BRAHMAGYAN connection indicator requires both a **recent authenticated
Core heartbeat** and at least one locally retained Core-acknowledged L0
candidate receipt. Rishi remains disconnected and the knowledge acceptance
flag remains false without an independently reviewed examination.

Read-only acceptance on a paired canary:
```powershell
$base = "http://127.0.0.1:8872"
$o = Invoke-RestMethod "$base/api/operations"
$o.connections | Format-List
$o.mission_cycle | Select-Object phase,mission_rest_policy,admission_allowed
$o.research_plan | Format-List
1,2 | ForEach-Object {
    $t = Invoke-RestMethod "$base/api/tasks/$_"
    [PSCustomObject]@{
        Job=$t.id; Status=$t.status; Integrity=$t.evidence_state
        PDFTextComplete=$t.text_extraction_verified
        VisualComplete=$t.visual_coverage_verified
        Comprehension=$t.comprehension_verified
        RishiExam=$t.rishi_exam_verified
    }
}
```

**Important:** A node currently running in collector mode with a *local-only*
source plan still will **not** report a Core/BRAHMAGYAN ACK. These new
checks apply to assignments actually leased through the authenticated Core
fleet. The owner must provision a genuine HTTPS endpoint, verified pinned
certificate fingerprint, paired device token and approved curriculum using
the existing pairing workflow before enabling fleet mode. The ordinary
HTTP port 8766 is not a TLS endpoint and must not receive that token.
There is no anonymous LAN auto-pairing.

**Still pending, not mislabeled as done:** Rishi-authored challenging theory
and practical exams, distinct Rishi grading, actual practical artifact review,
retention/re-examination and hardware canary evidence of end-to-end TLS
delivery. The BRAHMAGYAN exam ledger already validates manually submitted
independent exams; this change does not invent answers, graders, exam
certificates or verified understanding.
