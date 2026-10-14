# Rishi Śukrācārya — KRISHNA Growth Research Advisor

## Boundary

Śukrācārya lives inside KRISHNA as a permanent research Rishi. He is **not** LR Group management and has no operating authority over LR Group companies.

His job is to continuously study business growth, markets, competitors, pricing, unit economics, customer behavior, retention, distribution, partnerships, adjacencies, geographic expansion and portfolio strategy, then send sourced advisory packets to LR Group.

KRISHNA remains the research/intelligence system. LR Group remains the business operating system.

## Research loop

1. Rotate through a bounded portfolio of growth questions.
2. Use BRAHMAGYAN live research for current web evidence.
3. Search for counter-evidence and contradictions.
4. Use SURYDEV for timestamped YouTube/video learning.
5. Treat video claims as candidate evidence, not automatic truth.
6. Debate important findings with Gautama, Chanakya, Jamadagni, Narada and Veda Vyasa.
7. Export a provenance-preserving advisory packet to LR Group.
8. LR Group independently debates commercial, financial, legal, compliance and risk implications before action.

## LR Group bridge

Default local endpoint:

`http://127.0.0.1:8788/api/advisory/sukracharya`

Override with:

`KRISHNA_LR_GROUP_ADVISORY_URL`

Optional shared token:

`KRISHNA_LR_GROUP_ADVISORY_TOKEN`

Failed deliveries are written to a durable JSONL outbox under the Sukracharya runtime state.

## Continuous research

`SukracharyaScheduler` runs at low frequency and waits one full interval before its first cycle. The server integration uses a six-hour default interval. The interval and enable flag are environment-controlled.

## Evidence model

Every exported finding distinguishes:
- claims and evidence maturity
- sources and source families
- supporting vs qualifying/contradicting evidence
- confidence and limitations
- unresolved questions
- proposed tests
- observation time

No finding can authorize spending, outreach, contracting, trading, legal action or LR Group execution.

## Initial video seeds

The bootstrap watchlist includes public business-learning material from Y Combinator / Startup School and Strategyzer. These are starting points only; dynamic discovery searches for additional and newer videos.

## Design rationale

The implementation uses hypotheses and measurable tests instead of treating business ideas as plans. It preserves dissent and requires independent validation because structured evidence-backed critique is more useful than unconstrained agent agreement.
