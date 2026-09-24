# KRISHNA aMCC Adaptive Effort Controller

KRISHNA's aMCC controller is a software control layer inspired by computational
accounts of the anterior midcingulate/dorsal anterior cingulate cortex. It is
not a biological brain simulation and does not claim that KRISHNA has feelings,
willpower, consciousness, pain, or a human nervous system.

## Purpose

The controller answers a bounded operational question: given a goal, current
progress, uncertainty, recent failures, resource pressure, cost and risk, how
much control should KRISHNA allocate and what strategy should it use next?

Inputs are normalized to 0..1 and include goal value, expected success,
information gain, urgency, owner priority, long-term benefit, compute/time/failure
cost, risk, resource pressure, progress, uncertainty and conflict. A persisted
failure streak is also used.

The output mode is one of:

- IDLE: no usable goal.
- ENGAGE: normal execution.
- FOCUS: suppress lower-priority work and increase control.
- PERSIST: continue with bounded retries.
- INTENSIFY: increase reasoning/verification effort for urgent valuable work.
- EXPLORE: change strategy after repeated failure.
- ESCALATE: route toward specialist/root-cause/research handling.
- RECOVER: reduce resource pressure before increasing effort.
- ABORT: stop on an explicit high-risk signal.

## Safety boundary

aMCC never grants permissions, approves mutations, bypasses project policy,
promotes a candidate, or overrides verification. Existing Sudarshan,
SharedActionBus, project-policy, approval and promotion boundaries remain
authoritative.

The managed-work pipeline records aMCC decisions in the TaskLedger, passes the
control strategy into shadow-repair investigation context, and records verified,
rejected and failed outcomes. This means the next attempt can move from normal
execution to strategy-switch or escalation rather than repeating the same
approach indefinitely.

## Runtime surfaces

Action bus:
- cognition.amcc.evaluate
- cognition.amcc.status
- cognition.amcc.outcome

HTTP:
- GET /api/amcc/status
- POST /api/amcc/evaluate
- POST /api/amcc/outcome
- POST /api/work/run accepts an optional `amcc` object containing normalized
  decision signals.

State is local under `.krishna_state/amcc/state.json`.
