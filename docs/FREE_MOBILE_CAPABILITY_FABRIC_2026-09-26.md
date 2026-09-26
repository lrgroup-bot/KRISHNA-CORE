# KRISHNA Free Mobile + Lazy Capability Fabric

Date: 2026-09-26

## Owner rules

1. Automatic spend is zero. No paid fallback.
2. Permanent cloud credentials remain on KRISHNA PC.
3. Mobile general non-sensitive conversation should avoid KRISHNA PC inference when a configured free-only direct session is available.
4. Private, personalized, stateful, attachment, project/action, financial, credential, medical-personal and fresh/live-data requests escalate to KRISHNA PC.
5. Heavy optional models and security/science workers are lazy. Registration must not imply download, startup, model residency, or background daemon execution.

## Mobile routing

Eligible general conversation:

Mobile -> paired KRISHNA token broker (once per ephemeral session) -> short-lived Gemini Live token -> Mobile <-> Gemini Live directly.

The phone never receives the permanent Gemini API key. The short-lived token and session-resumption handle remain memory-only. Gemini Live native audio is played on-device and output-audio transcription is rendered in the chat. If the direct route is unavailable, not explicitly marked free-only, or the request is not eligible, the request falls back to KRISHNA PC.

PC polling is intentionally reduced:
- UI status: 30 s while visible.
- realtime resume: 15 s while visible, 60 s while hidden.
- PCObserver project scan: 30 s default, max 2,500 files/project per pass.

## Capability seams

CapabilityFabric is metadata-only and lazy. It does not instantiate model runtimes.

Registered provider ideas:
- mobile-mlkit: on-device lightweight vision.
- gemini-live-ephemeral: direct mobile free-only session when configured.
- krishna-pc: private/action/heavy fallback.
- dots3-note-prev: dormant heavyweight multimodal provider; never auto-downloaded.
- dots.mocr: dormant document/OCR provider pending model-license/commercial review.
- dots.tts: dormant voice provider pending quality/language benchmark.
- stemkit-core: deterministic science-compute adapter; on-demand subprocess only.
- strix-local-sandbox: disabled by default; local candidate/localhost authorization only.
- system-one: bounded option ranking with no action authority.

## System-One / OpenJev boundary

System-One may rank caller-supplied bounded options for low-risk routing. It never decides spending, permissions, secrets, legal/medical actions, deployment, deletion, promotion, or external writes. High-stakes classes always escalate to deterministic policy/owner authority.

## DeepSeek Harness ideas adopted

KRISHNA adopts the provider/capability seam concept, not the DSH runtime itself. KRISHNA keeps Sudarshan, Shared Action Bus, Agent Runtime, audit, idempotency, approval and promotion gates as the authority.

## STEMKit

Only allowlisted deterministic functions can be invoked through the adapter. No Node daemon remains resident. Package installation is optional and should happen only when the owner wants the scientific compute capability locally.

## Strix

Strix is not automatically installed or executed. The adapter only accepts:
- a path inside an explicitly supplied candidate root, or
- localhost/loopback URLs.

External target scanning is not part of the KRISHNA integration.

## Dots family

No Dots model is automatically downloaded. dots3-note-prev is intentionally not a current-PC local target due its server-class size. Dots OCR/TTS remain optional benchmark candidates.

## KUBER and other projects

Patterns learned from Daily Stock Analysis belong in KUBER's own market-data/backtest runtime rather than loading KRISHNA Core with another market stack. Eromify remains a workflow-design reference rather than a paid dependency. Google Maps bulk scraping remains excluded from VANIK-NETRA production ingestion; open-data sources remain canonical.
