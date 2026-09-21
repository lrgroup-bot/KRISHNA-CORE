# KRISHNA AGI v1

Single control plane, modular workers. `Krishna_AGI.exe` is the only user-facing entry point. Chromium, inference, creator and avatar workers remain supervised child processes for fault/resource isolation.

## Core contracts
- KRISHNA Neural Action Graph owns orchestration; LangGraph is an optional durable-execution adapter.
- Agent-Native is an architectural reference only. KRISHNA's canonical execution spine is Shared Action Bus -> Agent/Job/Permission/Protocol/Dispatch adapters; UI controls do not become runtime authorities.
- Priority mutating UI operations must produce auditable Shared Action receipts; compatibility HTTP routes may remain only when they delegate to the same registered action.
- Policy Kernel is mandatory before mutation/external side effects.
- Executors are replaceable adapters (native/OpenHands/Open Interpreter concepts).
- Garuda is the research/evidence scout; Garudanetra is the browser/computer layer.
- Garudanetra has one canonical Browser Fabric: Playwright/Chromium is the verified engine, semantic refs/recovery/stream/record-replay are native capabilities, and external browser projects remain optional adapters.
- Gyan-Bhandar is the canonical memory API; Graphiti/Letta/Mem0 are optional backends.
- Critic/Verifier is read-only and independent of mutation workers.
- Successful verified procedures may become skill candidates; benchmark pass is required for promotion.
- Native event bus is canonical; n8n/Activepieces are adapters.
- Sudarshan is the permissioned Action/Job control plane for delegated capabilities; model, MCP/A2A, agent, browser, coding-worker and NARAD workflow entry points must not bypass it.
- NARAD implements selected n8n workflow patterns natively (typed DAG nodes, triggers, safe mapping, bounded retry, history, dead letters, checkpoints/resume) while rejecting a second embedded n8n runtime.
- IndependentCriticVerifier is the required exit boundary for Sudarshan-dispatched delegated work.
- Creator/avatar/revenue systems are capability layers, not owners of the AGI core.

## Packaging
Final Windows release target: `Krishna_AGI.exe`. Heavy models/browser binaries remain managed runtime assets under `E:\Krishna-The GOD` rather than being duplicated into the PE executable. Garudanetra browser state/assets are isolated under KRISHNA runtime paths and legacy `browser-data` is reconciled non-destructively.
