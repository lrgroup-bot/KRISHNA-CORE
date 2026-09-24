# KRISHNA AGI v1 — verification report

## Canonical repository state
- Repository: `lrgroup-bot/KRISHNA-CORE`
- Default branch: `fix/krishna-ui-runtime-verification`
- Audited canonical head: `b41c2b25adffbebeea6cdf5c13bec941d3c4d6b8`
- Open pull requests at audit time: none

## Current automated verification
The latest audited integration head feeding the canonical merge passed the active CI gates:

- Python source compilation: PASS
- PowerShell parse validation: PASS
- Core unit and isolated HTTP integration tests on Ubuntu: PASS
- Core unit and isolated HTTP integration tests on Windows: PASS
- Repository contracts: PASS
- Canonical architecture-truth audit: PASS
- Project Perfection Chromium E2E: PASS
- KABACH/privacy browser E2E: PASS
- Windows desktop application build: PASS
- Windows console fallback build: PASS
- Protected-data safe-patch verification: PASS
- Bundled-Core live smoke test: PASS
- Clean Windows EXE launch/restart retest: PASS

The current owner-facing navigation contract is also aligned with the canonical requirements: MAIN MENU exposes KRISHNA, Sudarshan and Plugins only; internal systems remain hidden from the main menu.

## Historical defects closed by current canonical work
- Windows `/api/architecture/truth` timeout caused by repeated deep source-tree scans: repaired with generated-directory pruning, same-size duplicate hashing and bounded caching.
- Source-tree audit drift after Gita/Sanskrit additions: repaired.
- Stale/superseded Gita and voice implementation branches: closed; canonical replacements merged.
- Windows Indic voice worker command quoting: repaired.
- Voice configuration overwrite risk: repaired with merge-safe configuration updates.
- Verified orphan Core listener handoff on port 8766: recovery path added without weakening fail-closed ownership checks.
- Sidebar requirements drift that re-exposed Working Gods: repaired and regression-tested.

## Truth boundary / machine acceptance
Repository CI being green does not prove that the user's physical Windows machine and E: drive are currently synchronized with this exact commit.

The Windows host remains accepted only when the local deployment/acceptance scripts confirm all of the following on the actual machine:
- source and deployed runtime are synchronized to the intended canonical commit;
- runtime integrity reports SYNCED;
- canonical Guardian/Core process chain owns the expected runtime;
- port 8766 is owned by the verified KRISHNA Core listener;
- no stale duplicate runtime roots/processes have reappeared;
- mobile pairing, local microphones/cameras and optional hardware-backed capabilities pass their own live checks;
- avatar skeletal/morph rendering is reported VERIFIED only when the private GLB inspector and renderer confirm the required rig/morph channels;
- gated or optional voice/model assets are reported ready only when actually installed and accessible.

## Release gate
Repository-side release/build gates are currently green for the audited integration head. Packaging is no longer blocked by the obsolete browser-test warning that previously appeared in this file. Final production deployment remains contingent on the real Windows/E:-drive acceptance gate above.
