# KRISHNA Historical Branch Reconciliation — 2026-09-23

This record documents the pre-pull audit of divergent historical branches against
the canonical branch. Historical filenames are not source authority; a feature is
restored only when the current tree lacks an equivalent or stronger canonical
implementation.

## Restored because the capability was genuinely absent

- `core/krishna_core/sudarshan_design_engine.py`
  - Restored as Sudarshan Design Engine v2.
  - Provides Design Genome, nested drift detection, selective design skill routing
    and hard acceptance gates.
- `core/krishna_core/sudarshan_ui_pipeline.py`
  - Restored as a bounded repair -> retest -> accept/escalate loop.
- `core/krishna_core/design_adapters.py`
  - Restored as optional/non-authoritative Playwright CLI, Storybook and Stagehand
    adapter contracts.
- `core/krishna_core/vishvakarma_curriculum.py`
- `core/krishna_core/vishvakarma_learning.py`
- `core/krishna_core/vishvakarma_rishi.py`
  - Restored with provenance/evidence requirements and wired into the AGI runtime.
- `core/krishna_core/model_scout.py`
  - Restored as a no-auto-download, benchmark-required candidate admission ledger.
- `scripts/AUDIT_KRISHNA_ARCHITECTURE.py`
  - Restored as an executable fail-closed architecture/product-truth gate and wired
    into CI and verified deployment.

## Superseded; intentionally not restored

- Historical `cloud_providers.py`
  - Superseded by `model_gateway.py`, `router.py`, `openrouter_free.py` and
    `direct_free.py`.
  - The old module trusted provider configuration more broadly. Current KRISHNA is
    stricter: automatic cloud fallback requires live zero-cost or zero-billing
    verification and privacy approval. Providers merely described as "free" remain
    explicit-use/configured adapters rather than automatic fallbacks.
- Historical `unified_model_mesh.py`
  - Superseded by the canonical local-first `router.py` hierarchy:
    local Ollama/GPT4All -> live-zero OpenRouter -> live-zero-billing verified
    direct-free provider -> STOP unless paid cloud is explicitly enabled.
- Historical `diagnostic_engines.py`
  - Superseded by `hawkeye_diagnostic.py`, `diagnostic_adapters.py` and
    `diagnostic_transport.py`, which separate diagnosis/reference logic from
    read-only measured evidence transport and prohibit vehicle transmit/program/
    actuation.

## Already present in canonical source despite divergent commit history

The pre-pull audit confirmed the current tree already contains the intended
HAWKEYE coordinator, BHOOMIPUTRA/field perception, field survey, Android offline
HAWKEYE pipeline, wake service, canonical mobile runtime, shared action routing,
KABACH security operations, project lifecycle, zero-cost OpenRouter/Cloudflare
fabric and the later C6/C7/quantum/nano/project-perfection work.

## Authority after reconciliation

1. `core/requirements/krishna_chat_requirements.json`
2. current canonical source
3. current tests/CI
4. runtime acceptance evidence
5. deployment integrity manifest

Divergent historical branches remain reference evidence only and must never
override the canonical branch automatically.
