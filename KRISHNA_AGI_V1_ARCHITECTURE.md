# KRISHNA AGI v1

Single control plane, modular workers. `Krishna_AGI.exe` is the only user-facing entry point. Chromium, inference, creator and avatar workers remain supervised child processes for fault/resource isolation.

## Core contracts
- KRISHNA Neural Action Graph owns orchestration; LangGraph is an optional durable-execution adapter.
- Policy Kernel is mandatory before mutation/external side effects.
- Executors are replaceable adapters (native/OpenHands/Open Interpreter concepts).
- Garudanetra is the browser/computer layer.
- Gyan-Bhandar is the canonical memory API; Graphiti/Letta/Mem0 are optional backends.
- Critic/Verifier is read-only and independent of mutation workers.
- Successful verified procedures may become skill candidates; benchmark pass is required for promotion.
- Native event bus is canonical; n8n/Activepieces are adapters.
- Creator/avatar/revenue systems are capability layers, not owners of the AGI core.

## Packaging
Final Windows release target: `Krishna_AGI.exe`. Heavy models/browser binaries remain managed runtime assets under `E:\Krishna-The GOD` rather than being duplicated into the PE executable.
