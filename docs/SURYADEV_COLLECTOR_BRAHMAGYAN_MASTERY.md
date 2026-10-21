# SURYADEV evidence collection -> BRAHMAGYAN mastery (first guarded increment)

## Responsibility boundary

- **SURYADEV is an evidence collector**, not a trusted knowledge grader. It queues approved websites/YouTube-caption/PDF sources, retains precise source references and SHA-256 evidence, and indexes locally approved books. A source job marked done means collection/extraction completed, NOT learned, verified, watched end-to-end or mastered.
- **BRAHMAGYAN owns knowledge maturity (L0 through L8)**. It receives candidate evidence through the existing permissioned SURYADEV/BRAHMA route. Rishi review, source triangulation, contradiction analysis, practical replication and delayed recall belong here, not in the acquisition worker.
- **BRAHMA/QC is the existing authority** for proposing knowledge to Gyan-Bhandar; no duplicate learning database or new coordinator is introduced.
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

- `create_daily_exam(mission_id, questions, exam_date=...)`: at least 5 evidence-linked, substantial, unambiguous questions, including **3 theoretical** and **2 practical** tasks. Coverage must include **why**, **how**, and **contradiction** reasoning. Challenge rubrics and source references must be recorded.
- `record_daily_exam_attempt(exam_id, results, grader, method)`: requires full candidate answers, independent reviewer name/method, per-answer rationale and evidence references. Every practical item additionally requires an artifact SHA-256 and test evidence. Thresholds: **85% theory**, **90% practical**, and **at least 60% on every question**. Failed attempts are retained with their correction history.
- `daily_exam_status(mission_id)`: read-only history and passing recorded attempts. New-mission L7/L8 advances are blocked without a recorded passing exam; existing L0-L6 source and test gates remain intact.

**Truth boundary:** a named/recorded result is not cryptographically verified grader independence or proof of cognitive understanding. Exam scheduling, automatic question generation, secure independent grading, proof of executable practical work, next-day/weekly retention exams, and certificate/signed reviewer attestation are NOT built in this increment. The dashboard should not claim those milestones were completed. For a true end-of-day process, connect this record/grade API to the future BRAHMA scheduler only after a trusted evaluator and job authorization path exist.

## Exact-source retrieval requirements

BRAHMAGYAN's evidence rows now keep URL, source_id, publication, retrieval date and content hash, plus precise locator fields where supplied: `url_fragment`, `page`, `chapter`, `section`, `line_start`, `line_end`, `start_seconds`, `end_seconds`. Future SURYADEV source bundle adapters must supply real, measured locators and verified citation spans; never fabricate precise timestamps or source-page claims.

## Remaining integration gates

1. Feed source-specific candidate bundles from **website/PDF/video/book collector** into BRAHMAGYAN using existing authenticated transport, while keeping L0 evidence separate from L2/L7 achievements.
2. Add a BRAHMA task supplier and exam scheduler that generates unseen theory/practical questions at day end without disclosing keys to the learner.
3. Require independently executable practical tests plus attributed Gautama/Bharadvaja reviews; preserve failures and counterexamples.
4. Add next-day, seven-day and monthly spaced-retention/transfer assessments with real checks. Gate stronger `mastered` claims until these are verified.
5. Run Core and standalone tests, Playwright UI regression and owner-approved laptop tests before any .exe; do not merge this draft branch automatically.
