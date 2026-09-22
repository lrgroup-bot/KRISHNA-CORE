# KRISHNA Phase 1 — Durable Mission Foundation

This implementation evolves the existing KRISHNA runtime rather than adding parallel apps or a new main-menu surface.

Runtime flow: Desktop/Mobile/CLI/future Glass -> KRISHNA Protocol v1.0 -> Orchestrator -> Mission Engine -> Durable Queue/Checkpoints/Resource Locks -> Shared Action Bus + Durable Event Bus -> Agent/Permission/Budget runtimes -> Sudarshan verification -> Unified Model Provider Contract.

## Mission authority

Mission state is stored in SQLite and survives UI closure, browser/mobile disconnect, Core restart, and process restart. States: QUEUED, PLANNING, RUNNING, WAITING, BLOCKED, ACTION_REQUIRED, VERIFYING, COMPLETED, FAILED, ROLLING_BACK, ROLLED_BACK, CANCELLED.

The mission record includes parent/session/project linkage, goal, priority, timestamps, progress, agents, tools, permission profile, resource budget, checkpoint IDs, artifacts, evidence, errors, retry count, verification state and rollback point.

## Durable queue

The backend queue owns execution state: enqueue -> pending -> processing -> ACK -> completed. A queue is drained only when pending == 0 AND processing == 0. Processing entries carry worker leases. On Core startup, interrupted processing entries are reclaimed and requeued or failed according to retry limits.

JobRuntime.submit() remains synchronous for compatibility, but now performs the durable enqueue/claim/ACK lifecycle before returning.

## Checkpoint/recovery

Mission checkpoints are versioned durable records. Trusted checkpoints update the mission rollback point. Startup recovery moves interrupted mission states to WAITING/recovery_required and records the latest trusted checkpoint instead of pretending interrupted work completed.

## Resource locks

Supported durable lock types: EXACT_LOCK, TREE_LOCK, PROJECT_LOCK, REPOSITORY_LOCK, DATABASE_LOCK, MODEL_LOCK, DEPLOYMENT_LOCK. Read/read locks may coexist. Overlapping writes are rejected. Locks use ownership tokens, leases and stale-lock cleanup.

## Event bus

Important lifecycle events are persisted in SQLite and can also fan out to the existing NARAD-compatible event bus. This gives KRISHNA a restart-safe activity stream without deleting existing automation behavior.

## Permission and tool scope

Existing AgentRuntime capability manifests remain authoritative. PermissionRuntime now also exposes ALLOW, DENY, ASK_OWNER, ALLOW_READ_ONLY and ALLOW_SANDBOXED decisions using source/agent, project, tool, path, operation, risk, mission and FAST/PRO profile context.

## Mission budgets

Per-mission limits support wall time, model calls, tool calls, subagents, agent depth, context tokens, retries, CPU, RAM, GPU memory, network usage and disk growth. Counters are durable and fail closed when configured limits are exceeded.

## Protocol and model boundary

KRISHNA Protocol v1.0 is the stable UI/Core boundary for desktop, mobile, CLI and future Glass surfaces. The Unified Model Provider Interface normalizes text, reasoning, streaming, tool calls, structured output, vision, files, context size and rate-limit capability metadata while preserving existing routing.

## Runtime surfaces

Read/status: /api/missions, /api/missions/status, /api/queue, /api/queue/status, /api/checkpoints?mission_id=..., /api/resource-locks, /api/events, /api/protocol, /api/models/providers.

Governed mutations: /api/missions/create, /api/missions/transition, /api/missions/checkpoint, /api/resource-locks/acquire, /api/resource-locks/release.

Mission and lock mutations are also available through Shared Action Bus actions and pass through Sudarshan verification.

## Compatibility

The historical TaskLedger remains as a compatibility/read surface. New durable jobs link their compatibility task ID to an authoritative Mission. Existing Shared Action Bus, AgentRuntime, PermissionRuntime, NARAD, KABACH, Garudanetra and Sudarshan paths are reused rather than replaced.
