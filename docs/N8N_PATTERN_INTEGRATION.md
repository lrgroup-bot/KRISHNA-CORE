# n8n Pattern Integration for KRISHNA

KRISHNA does not embed or fork the n8n runtime. We use selected workflow-engineering patterns only.

## Authority rule

Every model, MCP tool, browser, coding worker, desktop worker and workflow must enter through Sudarshan's permissioned Action/Job architecture and leave through the independent verifier.

n8n is not an authority, scheduler, credential store, UI shell, database or agent core inside KRISHNA.

## What KRISHNA adopts

The useful n8n-style patterns are implemented natively inside NARAD:

- typed workflow nodes;
- explicit graph dependencies;
- deterministic topological execution;
- manual, event, schedule and webhook triggers;
- safe input/output data mapping without eval;
- bounded retry/backoff;
- retry-safety flags for side-effecting operations;
- action/job node dispatch;
- durable execution history;
- dead-letter handling;
- per-run checkpoints;
- restart/resume without replaying already verified nodes;
- credential references rather than embedded secrets;
- provider/connector adapters;
- idempotency keys;
- node-level execution metadata;
- workflow-level independent verification.

## What KRISHNA deliberately does not import

- n8n editor/UI;
- n8n user/account system;
- n8n credential database;
- n8n queue workers;
- n8n database/storage layer;
- n8n licensing/enterprise modules;
- n8n's large node catalog;
- n8n's AI/agent runtime;
- unrestricted code/filesystem nodes.

This keeps KRISHNA small and avoids creating a second control plane.

## Runtime flow

```text
Trigger
  |
  v
NARAD durable workflow
  |
  v
WorkflowGraph
  |
  +--> safe context mapping
  +--> dependency ordering
  +--> bounded retry policy
  +--> checkpoint
  |
  v
Sudarshan Control Plane
  |
  +--> PermissionRuntime
  +--> PolicyKernel / approval
  |
  +--> Shared Action Bus
  |      or
  +--> JobRuntime / TaskLedger
  |
  v
Real capability
  |
  v
IndependentCriticVerifier
  |
  +--> verified -> next node / workflow completion
  +--> rejected -> dead letter / retry / owner review
```

## Compatibility

Legacy NARAD step names are normalized at execution time:

```text
publish_event   -> narad.publish_event
adapter_webhook -> narad.adapter_webhook
provider_send   -> narad.provider_send
```

Existing stored workflows remain readable.

## Permissions

NARAD derives a visible workflow capability manifest.

All workflows receive:

```text
narad.execute
```

External webhook/provider workflows also receive:

```text
send_external
```

The capability alone does not authorize execution. External operations remain behind policy and explicit approval where required.

## Retry policy

Node retries are bounded:

- max attempts: 5;
- delay bounded to 10 seconds per wait;
- exponential backoff bounded to 4x;
- side-effecting external actions default to one attempt;
- an external node may retry only when explicitly marked retry-safe.

This prevents duplicate emails/messages/webhooks from careless automatic retries.

## Data mapping

NARAD supports references such as:

```text
${input.customer}
${nodes.lookup.result.id}
```

The resolver performs dictionary/list lookup only. It does not evaluate Python, JavaScript or arbitrary expressions.

## Checkpoints

NARAD persists incomplete workflow checkpoints in its existing state file.

A checkpoint contains:

- workflow and version;
- run ID;
- project;
- input context;
- completed nodes;
- failed nodes;
- verified node outputs;
- node receipts;
- partial results;
- trigger source.

Resume skips already completed/verified nodes.

No extra database or daemon is added.

## External n8n

If the user runs n8n separately, KRISHNA may call it through the existing bounded webhook adapter.

That flow is:

```text
NARAD -> Sudarshan -> narad.adapter_webhook -> external n8n
```

n8n never receives unrestricted host authority from KRISHNA.

## Resource policy

The native NARAD graph layer uses the existing KRISHNA Python process, TaskLedger, state file, scheduler and provider hub.

It adds no:
- Node.js process;
- Docker container;
- Redis;
- Postgres;
- queue daemon;
- full n8n installation.

That is the deliberate "do not overload KRISHNA" boundary.
