# Agent-Native Reference Integration for KRISHNA

KRISHNA uses Agent-Native as an architectural reference/foundation, never as a replacement product or decision authority.

The design lesson adopted here is simple: keep a small set of trusted runtime primitives and make agents, UI controls, jobs and protocol adapters compose those primitives rather than inventing their own execution paths.

## Priority order

1. **Shared Action Bus**
2. **Projects / Chats**
3. **Agent Runtime**
4. **Jobs**
5. **Permissions**
6. **Audit / Rollback**
7. **MCP / A2A**
8. **Dispatch**
9. **Desktop / Mobile sync**
10. **Garuda / Garudanetra integration**

## Canonical execution spine

```text
Dashboard / Mobile / Agent / Job / MCP / A2A
                    |
                    v
              Shared Action Bus
                    |
       +------------+-------------+
       |            |             |
   Permissions    Policy       Audit/Event
       |            |             |
       +------------+-------------+
                    |
              Registered Action
                    |
          Runtime implementation
                    |
              Result / Evidence
                    |
            Action receipt/id
                    |
       Desktop + Mobile state sync
```

A visible UI control is not considered implemented merely because it renders or has a JavaScript click handler.

For a mutating/operational control to be considered wired, it must either:

- dispatch a registered Shared Action and receive an `action_id`, or
- be a compatibility endpoint whose server implementation dispatches that same registered Shared Action.

Read-only display/inspection controls may use bounded GET endpoints directly.

## Layer status

### 1. Shared Action Bus — IMPLEMENTED / RUNTIME VERIFY

`SharedActionBus` owns:
- named action registration;
- source identity;
- actor identity;
- project scope;
- explicit capability list;
- policy gate;
- approval flag;
- idempotency key;
- action events;
- sanitized audit receipt;
- optional rollback action.

It does not accept raw shell commands.

### 2. Projects / Chats — IMPLEMENTED / RUNTIME VERIFY

The main Project/Chat UI actions dispatch:
- `project.register`
- `project.unregister` (compatibility/runtime action; UI exposure remains guarded)
- `chat.create`
- `chat.move`
- `chat.rename`
- `chat.delete`

Legacy HTTP routes remain for compatibility but call the same bus.

### 3. Agent Runtime — IMPLEMENTED / RUNTIME VERIFY

`AgentRuntime` uses explicit manifests. An agent gets:
- an ID;
- a role;
- explicit permissions;
- explicit allowed action names/prefixes.

It cannot call arbitrary runtime internals.

Built-in manifests currently include Garuda, Garudanetra, UI Guardian, Developer and NARAD.

### 4. Jobs — IMPLEMENTED / RUNTIME VERIFY

`JobRuntime` uses the existing durable `TaskLedger` rather than creating a second job database.

A job stores its job/task ID and the resulting Shared Action `action_id`.

Current execution mode is durable-inline. A future queue/worker implementation may change scheduling without changing the action contract.

### 5. Permissions — IMPLEMENTED / RUNTIME VERIFY

`PermissionRuntime` is the capability boundary for delegated callers.

- local PC/system is the owner/runtime authority;
- mobile remains narrow and conversation-first;
- agent/job/MCP/A2A callers must present the capabilities required by the action spec;
- action source restrictions still apply even when the caller presents a permission.

### 6. Audit / Rollback — IMPLEMENTED BOUNDARY / RUNTIME VERIFY

Every Shared Action produces a sanitized receipt and publishes requested/completed/failed/blocked events. Durable action metadata is also written into KRISHNA's existing MemoryStore audit table.

Shared Action rollback requires:
- a registered rollback action;
- an existing action receipt;
- explicit approval.

For live project file promotion, KRISHNA's `PromotionManager` remains the transactional backup/post-check/automatic-rollback authority. The Shared Action Bus does not replace that stronger project rollback mechanism.

### 7. MCP / A2A — INTERNAL ADAPTER BOUNDARY IMPLEMENTED

`AgentProtocolGateway` exposes:
- an MCP-style tool catalog generated from Shared Actions;
- MCP tool calls mapped to Shared Actions;
- A2A envelopes mapped to AgentRuntime or Shared Actions.

This is **not** an unauthenticated public MCP/A2A network service. Transport/authentication remains a separate boundary.

### 8. Dispatch — IMPLEMENTED / RUNTIME VERIFY

`DispatchRuntime` provides one selector:
- `action`
- `agent`
- `job`

All three ultimately resolve to Shared Action Bus execution.

### 9. Desktop / Mobile sync — IMPLEMENTED FOUNDATION / DEVICE VERIFY

Shared Action events are mirrored into the existing authenticated mobile realtime store as `action.sync` events when a paired mobile device is active.

The mobile product remains conversation-only. This sync is for progress/state continuity, not a mobile dashboard or raw host-control surface.

### 10. Garuda / Garudanetra — IMPLEMENTED / RUNTIME VERIFY

Garuda UI and legacy API use:
- `garuda.scout`

Garudanetra uses:
- `garudanetra.start`
- `garudanetra.control`
- `garudanetra.replay`
- `garudanetra.upload_attachment`

Garuda remains research/evidence. Garudanetra remains browser/computer execution. KRISHNA remains authority over both.

## UI wiring invariant

The target invariant for the Command Center is:

> **No operational button may be styled as active unless its runtime contract is real and testable.**

Repository and Windows acceptance tests enforce the first priority surfaces—Projects, Chats, Garuda and Garudanetra. Remaining legacy direct POST controls are migrated incrementally to named Shared Actions; until migrated, they must remain backed by real server runtime endpoints and may not be represented as action-bus-native.

## Compatibility policy

Compatibility routes may remain during migration to avoid breaking mobile, scripts or saved UI clients. They are allowed only when their server-side implementation delegates to the canonical action/runtime boundary.

No compatibility route may become a second authority.

## Agent-Native relationship

Agent-Native contributes architectural ideas: agent-composable primitives, explicit capability boundaries and a runtime that is more important than ornamental UI.

KRISHNA keeps its own:
- Neural Action Graph;
- Policy Kernel;
- Gyan-Bhandar;
- NARAD;
- KABACH;
- Garuda;
- Garudanetra Browser Fabric;
- verifier/promotion/rollback architecture;
- PC/mobile security model.
