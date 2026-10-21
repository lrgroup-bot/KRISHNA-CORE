# SURYADEV fleet rollout — opt-in, no automatic production deployment

## Current authority and scope

BRAHMAGYAN owns the knowledge ledger. Council Rishis/Acharyas own
domain research and independent theory/practical examinations. BRAHMA owns
scheduling policy; this draft's fleet service currently executes within
the paired KRISHNA Core API (a lightweight relay) until a standalone BRAHMA
scheduler is deployed. SURYADEV nodes acquire owner-approved source evidence
only. CHANDRADEV hardware-wide fleet supervision is not yet installed.

**Do not merge, install, sign or build an EXE until CI and isolated two-PC
and rollback tests pass.**

## Core-side preparation

Core's existing validated, manually approved source inventory remains:
`<Core SURYADEV state>/mission-authority/approved-curriculum.json`,
schema `krishna.suryadev.approved-curriculum.v1`. Entries must contain
an allowed HTTPS source host, a six-hour topic mission, and explicitly
approved URLs. Removing a source from this inventory prevents new dispatch.
No search agent may silently expand the inventory.

The new `SuryadevFleetService` derives stable task IDs from approved
mission IDs and URLs; each task is attributed to a registered subject
specialist. State is persisted atomically in `fleet-authority/fleet-leases.json`.
The agent status returns fleet counters, but no knowledge masteries.

## Owner-approved laptop activation after verified deployment

The device must first be explicitly paired with Core over the existing
pinned-HTTPS scheme; keep the token in a private file, never commit it.
The local `learning-plan.json` must independently approve each candidate
URL exactly, not merely its hostname. Existing source and book databases
are not cleared or replaced.

The following is the planned command **after the new branch is tested and
copied/installed into `D:\Work\SURYADEV`**, with a real owner-created
Core pairing file at the example path. It is not an instruction to run
before deployment:

```powershell
cd "D:\Work\SURYADEV"
.\start-continuous-learning.ps1 `
  -DataDir "D:\Work\SURYADEV-DATA" `
  -CoreMissionConfig "D:\Work\SURYADEV-DATA\core-mission-connection.json" `
  -FleetMode `
  -CollectApprovedBooks
```

`-FleetMode` activates pinned-TLS node heartbeats, bounded multi-lease
claims, renewals and collection receipts. No local Ollama model is required.
`-CollectApprovedBooks` only indexes already approved local books, not remote
unapproved media. Do not combine it with `-UseOllama`. All source-specific
network access remains subject to the existing permissions and provider limits.
There is only one active worker per data directory.

## Lease semantics and hard truths

- Every incoming assignment is revalidated against the device's own exact
  approved URL list and source kind.
- A lease is bound to one paired node, with expiry and ownership verification.
  Persisted local task IDs allow safe lease replay and several concurrent jobs.
  Renewals are required for long-running jobs.
- A recorded source SHA-256 is a **candidate collection receipt**, not an
  independent proof that source bytes were uploaded or factually verified.
- Previously collected source evidence remains local when Core is offline;
  completion is not claimed without Core acknowledgment. Expired leases are
  orphaned for recovery rather than rewritten as a success.
- Server-side YouTube 429 results impose a one-hour fleet-wide no-new-
  YouTube-admission period. Do not circumvent provider controls using extra PCs.
- Hardware safety: 85% admission guard, reduction from 75% pressure, current
  measured CPU/RAM/disk headroom. These do not enforce hard OS-wide limits.
  GPU telemetry and real temperatures remain hardware/driver-dependent.
- Queue exhaustion is truthfully reported when the approved curriculum
  contains no more work. Infinite *unique* research is not guaranteed.

## Acceptance gates before rollout

1. GitHub Core and SURYADEV unit tests pass on Windows and Linux.
2. Paired TLS device authentication, token replay and source allowlist
   rejection are tested on two isolated real machines.
3. Execute 1/5/10-node planner simulations, then 2-PC lease acceptance and
   task completion with actual persisted evidence.
4. Power off one node during a job; verify expired lease returns to queue,
   no duplicate globally accepted result, and original evidence preserved.
5. Confirm average and peak CPU/RAM stay within operational thresholds, and
   external-source rate limits remain honored across nodes.
6. Have a second Rishi independently examine a genuine practical artifact
   through BRAHMAGYAN. Never award a learning level based on a job receipt.
7. Run browser UI regressions, package only after tests, install only with
   owner authorization, and preserve rollback.

## Unimplemented requirements

BRAHMA self-hosted standalone scheduler service, direct dispatch from
arbitrary BRAHMAGYAN Rishi research subquestions, automatic six-hour refill
after the finite operator-approved catalogue is exhausted, true Rishi exam
generation and signed independent grading, spaced-retention tests, central
local Ollama gateway routing, CHANDRADEV real hardware fleet guardian,
fully benchmarked adaptive 20+ tab scheduling, physical two-PC proof and
universal signed EXE packaging are still unfinished.
