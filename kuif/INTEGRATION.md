# KUIF integration and release gate

This is an opt-in Python library, not a production service. The Runtime composes
project-scoped permissions, SQLite text lookup, JSONL audit events and a local
Ollama generation call. Principal objects must come from a verified identity
provider: never trust user-supplied project/action lists. KnowledgeStore.put is
an internal administrative method and must not be exposed as an API without
authorization. Audit files must be protected against modification and rotation
must be configured by the host. The task state machine is in-memory only.

Run from repository root using the standard library test runner used by CI:

```bash
python -m unittest discover -s tests -p 'test_kuif_*.py' -v
```

All KUIF tests must be compatible with `unittest` discovery without pytest or
pytest fixtures. A cancelled CI run is not a pass; start a fresh run on the
current feature branch and inspect both Linux and Windows jobs.

Release gates:
1. Inspect existing KRISHNA startup paths and dependencies before wiring imports.
2. Configure trusted authentication, credential storage and tenant isolation.
3. Add durable queues, retries, cancellations and idempotency.
4. Add structured metrics, secure audit persistence and failure handling.
5. Run complete repository regression and end-to-end Ollama tests.
6. Review company-specific APIs before enabling any cross-project writes.
7. Keep feature branch isolated until checks pass; do not deploy automatically.
