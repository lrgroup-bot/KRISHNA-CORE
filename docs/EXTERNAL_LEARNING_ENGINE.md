# External Learning Engine — zero-spend integration contract

## Existing implementation

`krishna_core.external_learning_ledger.ExternalLearningLedger` provides SQLite-backed
source attribution, idempotent capture, quarantine, explicit review gates and
approved-only retrieval. It **does not** fetch websites, execute source code,
verify licenses automatically, train models, or authorize the reviewer.
The host must authenticate the reviewer and enforce owner approval **before**
calling `review`. Never expose `review` directly as a public HTTP endpoint.

## Proposed connections

1. **GARUDA/SURYADEV (collection)**: ingest public/authorized URLs, release notes,
   issues, engineering examples, and research papers; preserve exact source revision.
2. **BRAHMAGYAN (analysis)**: summarize patterns, attach independent evidence,
   note contradictions, and propose a narrowly scoped reproducible test.
3. **GAUTAMA/BRAHMA (verification)**: review provenance, license, and reproduction.
   Store the test artifact externally; do not trust booleans provided by the collector.
4. **SUDARSHAN (implementation)**: create a bounded project proposal for a proven
   technique; owner approves any mutation through the existing Shared Action Bus.
5. **VISHWAKARMA/UI GUARDIAN (verification)**: implement on an isolated branch and
   verify code, browser behavior and performance.
6. **GYAN-BHANDAR (reuse)**: index only approved summaries with citation and revision,
   and revalidate them when source or local code changes.

## Threat model

- Public issue comments, READMEs, and source code may contain prompt injection.
- License identifiers are untrusted until independently checked.
- No automatic repository cloning, script execution, pip install, or secrets access.
- Never ingest passwords, private conversations or proprietary material without rights.
- Review booleans are an **internal API contract**, not independent proof.
- Rejected lessons cannot become approved through repeated capture.
- Host is responsible for authentication, authorization, egress and rate limits.

## Test and release gate

Run `pytest core/tests/test_external_learning_ledger.py` in the repo's existing
Python environment. Then test SQLite persistence, review authorization at the
actual API boundary, prompt-injection handling, and source-license validation.
No live source connector or knowledge-index integration is claimed by this PR.

## Research references

- OpenHands software-agent-sdk: durable state, skills, local-model support.
- Aider: repository map and selective context; run tests after code edits.
- cl-agent: episode capture, replay, inspectable skill distillation, eval gates.
- SWE-CC (2026): repository contribution policies need deterministic checks.

Only adapt license-compatible ideas; avoid copying external code into KRISHNA
without explicit review.
