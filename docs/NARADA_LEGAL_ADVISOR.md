# Rishi Narada Legal Advisor

## Purpose

Rishi Narada is KRISHNA's permanent legal, judicial-reasoning and compliance advisor for Indian-law research. The subsystem is designed to help KRISHNA choose lawful paths, identify prohibited conduct, find relevant Indian precedent and keep a provenance-backed cache of official legal sources.

It is not a substitute for a licensed advocate. Materially consequential, disputed, criminal, regulatory or litigation-facing conclusions must be escalated for qualified legal review.

## Permanent legal Shishyas

1. **Constitution** — Constitution, Acts, amendments, rules, regulations, notifications, orders, circulars, commencement/effective dates and official-source freshness.
2. **Legal** — lawful implementation paths, permissions, licences, consent, contracts and compliance-by-design.
3. **Illegal** — prohibited/restricted conduct, legal-risk boundaries and explicit do-not-do analysis.
4. **Vakeel** — lawful alternatives, exemptions, licences, appeals, review, legitimate defences, settlement and remediation. It is forbidden from providing evasion, concealment, bribery, obstruction, evidence destruction or bypass instructions.
5. **Judge** — fact-and-law matching against Indian judgments; extracts issues, provisions, precedent, ratio, holding, result, binding status and later history.
6. **Police** — lawful immediate-situation analysis, de-escalation, evidence preservation, reporting and police/criminal-procedure research. It never advises evasion of arrest or investigation.

These six names are permanent role profiles. Ordinary research Shishyas created for missions remain temporary and are destroyed under the existing KRISHNA Shishya lifecycle after findings/provenance handover.

## Authority model

Current-law conclusions prefer official sources:

- Legislative Department official Constitution
- India Code
- eGazette of India
- Supreme Court of India / Verdict Finder
- eCourts Judgment Search
- Ministry of Home Affairs current criminal-law material
- Bureau of Police Research & Development material
- Odisha Law Department Acts, Rules/Regulations and Notifications
- SEBI legal material
- RBI Master Directions
- TRAI Directions

Every legal conclusion should state jurisdiction, effective/commencement date when material, amendment/repeal status, and precedent status where relevant.

GitHub/NLP repositories may help parse, index, search or summarize judgments, but they are never legal authority. Initial engineering references include OpenNyAI, Legal-NLP-EkStep legal NER/summarization and the public Indian Supreme Court judgments dataset.

## Source freshness

`narada.legal.update_check` fingerprints allowlisted official source pages/documents and stores retrieval metadata. The first observation creates a baseline. A later fingerprint difference creates a **research trigger**, not an automatic claim that the law changed.

KRISHNA has an opt-in durable autonomy commitment, created from the owner's explicit requirement, that periodically refreshes selected official-source fingerprints. The operation is evidence-only and cannot amend policy or legal conclusions on its own.

`narada.legal.sync` stores versioned official-source snapshots in:

`.krishna_state/narada-legal/corpus/`

The local cache must never be described as a complete copy of every Indian law unless measured source/category coverage proves that statement.

## Safety boundary

Narada is specifically designed to help KRISHNA stay legal.

The deterministic risk gate blocks requests involving evidence destruction/concealment, bribery, law-enforcement evasion, compliance/KYC/legal bypass, money laundering, forged records, witness interference, detection evasion or obstruction.

When a requested path is illegal or risky, Vakeel redirects to genuine lawful alternatives such as permission/licensing, consent, compliant restructuring, appeal/review, representation, settlement, remediation or qualified counsel.

## Runtime actions

- `narada.legal.status`
- `narada.legal.sources`
- `narada.legal.plan`
- `narada.legal.risk_gate`
- `narada.legal.case_plan`
- `narada.legal.update_check`
- `narada.legal.sync`

The existing NARAD connector/runtime and Rishi Narada are separate concepts: NARAD handles communications/connectors; Rishi Narada owns legal reasoning and compliance research.
