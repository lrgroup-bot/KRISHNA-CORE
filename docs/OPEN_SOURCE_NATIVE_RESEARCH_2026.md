# Free-only engineering research and implementation backlog (2026-10)

These are **external reference projects**, not dependencies installed or capabilities already delivered. Review their license, source provenance, resource requirements and maintenance before importing code. No paid API fallback.

| Reference | Engineering lesson | KRISHNA owner | Validation |
| --- | --- | --- | --- |
| [enkiTS](https://github.com/dougbinks/enkiTS) | Bounded multicore task scheduling, dependency execution, pinned work | SUDARSHAN native scheduler | CPU saturation and fairness benchmark |
| [Kairos](https://github.com/araray/kairos) | Deterministic DAG scheduling, missed-trigger recovery, explainable plans | SUDARSHAN / AI-HR | Restart/replay and dependency tests |
| [AgentOS](https://github.com/KAAZamapiloT/agent-os) | C++ native scheduler with Python fallback | SUDARSHAN | Cross-language parity; no silent fallback errors |
| [Agenhood](https://github.com/appssemble/agenhood) | Persistent workspaces, streamed task events, sandbox and egress policy | SUDARSHAN / KABACH | Local security and task persistence tests |
| [OpenWOP](https://github.com/openwop/openwop) | Replayable workflow events, handoffs and durable suspension | Agent Runtime | Event schema and deterministic replay |
| [Syngrisi](https://github.com/syngrisi/syngrisi) | Local visual regression and baseline approval | UI GUARDIAN | Pixel/DOM diff, manual baseline approval |
| [TestivAI OSS](https://github.com/testivai/testivai-oss) | Offline screenshot+DOM evidence with machine-readable results | VISHWAKARMA | No external service, reproducible browser run |
| [Bug0 QA Agent](https://github.com/bug0inc/qa-agent) | Browser regression strategies | UI GUARDIAN | Review model-provider and network requirements before reuse |

## Native migration rules

1. Preserve the existing Python Shared Action Bus permission and idempotency guarantees.
2. Start with read-only C++ modules and native parity tests; do not replace authoritative Python state on a feature branch.
3. Run `cmake -S core/native -B core/native/build`, `cmake --build core/native/build`, and `ctest --test-dir core/native/build --output-on-failure` locally.
4. Introduce a versioned C ABI or a well-maintained Python binding only after tests pass on Windows.
5. Use bounded worker queues, explicit CPU/RAM/VRAM budgets, deterministic task IDs, and cancellation.
6. Record verified events only; do not animate fabricated status or infer completion from model text.
7. Keep experimental research data quarantined from promoted BRAHMAGYAN knowledge.

## Cost policy

No purchased API calls, SaaS subscriptions, rented GPU instances or automatic spending. Existing internet, hardware and electricity are not literally free.
