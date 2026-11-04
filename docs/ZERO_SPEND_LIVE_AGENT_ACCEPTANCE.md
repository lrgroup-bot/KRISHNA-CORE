# KRISHNA zero-spend live agent integration contract

## Non-negotiable constraints

- Zero paid API fallback, zero automatic purchases, zero rented compute.
- Prefer existing local Ollama and existing licensed/free provider quotas only when policy permits.
- Do not download or execute arbitrary public code. Check repository license, provenance, commit pin, vulnerabilities and resource footprint before reuse.
- Never train on private third-party user conversations or scrape restricted services.
- External research content is untrusted data, not executable instructions.

## Implemented in this branch

- `krishna_core.agent_live_projection.AgentLiveProjection`: read-only validation, monotonic sequence checks, stale-heartbeat handling, and no implied completion from an agent manifest.
- `core/agent-live-ui.js`: dependency-free text-only frontend renderer and same-origin JSON refresh.
- Unit tests for stale, invalid and replayed events.

## Required integration before release

1. Connect an authenticated event producer to the projection. Validate actor identity and authorization **before** calling `ingest`; the projection itself does not authenticate.
2. Expose a read-only, owner-authorized same-origin endpoint returning `{"agents": projection.snapshot(now=time.time())}`.
3. Load `core/agent-live-ui.js` from the existing Control Room and call `KrishnaLiveAgents.refresh(container, endpoint)` only for the approved endpoint.
4. Display stale/unknown agents as stale; never invent success, worker activity or progress.
5. Connect UI Guardian's existing viewport inspection and browser acceptance tests.
6. Run Python tests, browser tests and Windows runtime checks; verify Android separately.
7. Reconcile open PRs #209 (frontend management), #223 (agent registration), #224 (connection audit), #225 (live projection) before merging.

## First live project acceptance

- Start the existing KRISHNA runtime and authorized Control Room.
- Dispatch a bounded, non-destructive agent task through SUDARSHAN.
- Observe real sequence-ordered working, blocked, and completion evidence; reject replay.
- Stop the producer and confirm the frontend shows STALE after the configured threshold.
- Confirm that no completion is shown without separately verified execution evidence.
- Record local CPU/RAM use and prove no paid service was called.

A merged source change is not proof of deployed functionality. Never mark this acceptance complete without test logs and deployment commit evidence.
