---
name: verification-gate
description: Independently verify claimed completion.
triggers:
  - verify
  - verification
  - completed
  - fixed
project_scope:
  - '*'
permissions:
  - read_context
  - run_tests
risk: low
verification_required: true
rollback_required: false
---
# Verification Gate
Verify expected versus actual behavior with tests and evidence. A change is not complete merely because it was applied.
