# KUIF experimental foundation

This is an opt-in library. No application imports or production services are changed.

- `policy.py`: read-only project action allowlist. This is **not** a substitute for authentication or tenant authorization.
- `gateway.py`: validation of the default local Ollama endpoint; no requests are sent.
- `tests/test_kuif_*.py`: pytest tests (execution required before merging).

Next: map actual KRISHNA entry points, integrate authenticated principals, add per-project scopes and audit logging, and run CI. Do not merge or deploy until reviewed.
