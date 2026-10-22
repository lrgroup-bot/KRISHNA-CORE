# KRISHNA ↔ LR product lifecycle: no-duplication integration

Date: 2026-10-22
Status: integration specification; not deployed

## Verified KRISHNA modules
- core/krishna_core/brahmagyan.py: research missions, claims, contradiction tracking, maturity levels L0-L8 and QC binding.
- core/krishna_core/rishi_council.py: existing Rishi authority.
- core/krishna_core/suryadev.py: existing source-collection agent.
- core/krishna_core/vishvakarma_learning.py and vishvakarma_rishi.py: repair-learning foundation.
- core/krishna_core/device_pairing.py and mobile_v3/MobileEdgeBot.java: existing device foundation.

## Ownership boundaries
- KRISHNA: orchestrates missions and permissioned learning; does not duplicate LR product inventory or finance.
- BRAHMAGYAN: source provenance, Rishi exam coordination and evidence maturation; does not own customer records.
- VISHVAKARMA: repair recommendations with first-party technician evidence, human safety gates.
- SURYADEV: permitted collection only, deduplicated sources, rate limits and failure reporting.
- LR_Group: authoritative lifecycle events and QAQC orchestration.
- LR_LLEO: original capture and offline queue.
- LR_Commerce: pricing, procurement, supplier risk and owner approval.
- Youtuber-AI: approved marketing creative and media QC.

## Integration contract
Use LR_Group/src/group/product-lifecycle-contract.mjs version 1.
Transfer only validated, minimum-necessary events via authenticated gateway.
Do not silently import external event state into BRAHMAGYAN as mastered knowledge.
Learning promotion requires source check, contradiction review, applied verification and Rishi examination.
Preserve existing audit logs, permissions, and no-autonomous-spend policy.

## Technology placement
- ESP32-S3 inference: isolated experimental edge node, not KRISHNA general LLM.
- AlternativeTo: discovery evidence through LR_Technology; BRAHMAGYAN evaluates licenses.
- iFixit: external reference links only unless license permits further use; technician data is first-party.
- Dupe-style visual similarity: LR_Commerce and LR_Group product images; KRISHNA orchestrates only.
- Photopea-style creative: Youtuber-AI approved assets; do not embed proprietary service without permission.
- RyTuneX-style diagnostics: existing KRISHNA healing and KABACH gates, no security-service disabling.
- CleanYourTV-style ADB: paired device management only with explicit approval and rollback.
- Skiplagged-style travel comparison: procurement research; no hidden-city booking automation.

## Required validation
Confirm current branch is correct, compare existing PRs, implement gateway contract tests, run Python/JS suites, run browser-first UI tests, and only then consider merge. This file is not a claim of implemented features.
