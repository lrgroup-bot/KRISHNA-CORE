---
name: root-cause-investigation
description: Diagnose failures before repair.
triggers:
  - failed
  - not working
  - error
  - broken
project_scope:
  - '*'
permissions:
  - read_context
  - inspect_logs
risk: low
verification_required: true
rollback_required: true
---
# Root Cause Investigation
Reproduce the failure, collect logs and state, isolate the smallest failing layer, form evidence-backed hypotheses, and do not mutate production until the cause is sufficiently supported.
