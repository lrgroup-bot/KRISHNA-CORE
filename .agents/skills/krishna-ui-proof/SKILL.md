---
name: krishna-ui-proof
description: Verify KRISHNA frontend or mobile-facing changes with behavioral checks, API/network evidence, console inspection, and nonblank screenshots.
---

# KRISHNA UI Proof

Use when a task changes visible UI, browser behavior, or mobile rendering.

Evidence should cover, as applicable:
1. the target page/screen loads;
2. expected visible elements exist;
3. important controls can be clicked or invoked;
4. expected API calls return acceptable statuses;
5. console/runtime errors are checked;
6. captured visual output is nonblank and corresponds to the intended screen;
7. device-only assertions remain explicitly unverified until a real device run is supplied.

A successful build alone is not visual proof.
