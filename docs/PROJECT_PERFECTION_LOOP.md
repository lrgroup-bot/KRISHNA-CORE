# KRISHNA Project Perfection Loop v1

This subsystem turns project completion into evidence, not a percentage.

## Operating loop

1. Architect decomposes the goal into a dependency-aware work graph.
2. Deadline HR estimates serial/parallel effort and sizes bounded ephemeral teams.
3. Existing DevelopmentOperator and worker runtime implement in isolated candidates.
4. BrowserOperator explores every applicable route, control and important state.
5. Hawkeye-style UI inspection consumes measured DOM geometry, screenshots and accessibility evidence; it does not replace deterministic assertions.
6. API testing may use an OpenAPI/GraphQL property-testing adapter (for example Schemathesis) when a schema exists.
7. Every objectively testable repaired defect gets a regression detector in Immune Memory.
8. Adversarial/chaos checks exercise invalid input, timeouts, offline states, denied permissions and restarts in test environments.
9. Packaging is followed by clean installed-artifact testing. A successful build alone is not completion.
10. Critic/KABACH independently verify evidence.
11. CompletionProof emits RELEASE_GATES_PASSED only when every required gate has evidence and passes.

## UI design research

KRISHNA should research current public design references appropriate to the project, render multiple original candidate pages, and show the user visual previews labelled A/B/C/D. Labels are selection handles, not abstract style names. The selected candidate is applied only after Submit.

## Visual editor contract

A future BrowserOperator adapter should support element picking and drag/voice intent. The browser supplies selector, bounding box, computed style, accessibility node, screenshot context and source mapping. DevelopmentOperator creates a candidate patch, hot reloads it, and affected deterministic tests run before promotion.

## Browser coverage

The discovery contract includes route/control discovery, console and network failures, DOM geometry, accessibility tree, screenshots, deterministic regression generation, a viewport matrix, UI state matrix and adversarial scenarios.

Do not claim pixel-perfect or error-free merely because a screenshot looks acceptable. Rendering varies by environment, so golden visual baselines must be generated and compared in controlled environments.

## External adapters

Keep optional external tools behind adapters rather than making KRISHNA depend on all of them:
- Playwright: deterministic browser E2E, traces, locator picking, screenshots/visual regression.
- Schemathesis: schema-derived API property/stateful testing.
- Maestro/Appium-class adapter: packaged mobile E2E when installed in the environment.
- Mutation adapter: deliberately modifies isolated candidates to verify tests detect defects.
- Accessibility adapter: automated checks plus explicit unresolved/manual findings.

## Release gates

requirements, unit, integration, backend_api, browser_e2e, ui_geometry, visual_regression, responsive, accessibility, security, adversarial, restart_recovery, package_build, installed_artifact.

A missing gate means NOT_COMPLETE.


## One-command finish

On the KRISHNA PC, the operator entrypoint is:

```powershell
powershell -ExecutionPolicy Bypass -File "E:\Krishna-The GOD\scripts\FINISH_KRISHNA_PROJECT.ps1" -Project "<registered-project>" -Url "<project-url>"
```

This sends one governed `project.perfection.finish` action with auto-repair, bounded QA workers, mutation testing, strict accessibility/performance gates and `apply_verified=true`.

The command can apply a release only after the completion certificate and independent review pass. Promotion is transactional. After promotion KRISHNA re-runs deterministic checks, route regressions, multi-viewport browser inspection, accessibility, performance and browser-chaos checks against the live project. A failed post-apply verification restores the promotion backup and reports `ROLLED_BACK_POST_APPLY`.

## Design Studio Submit

The normal Submit button is the owner's explicit design-selection instruction:

```text
Web/GitHub design research
→ original rendered A/B/C/D candidates
→ owner selects one
→ Submit
→ bounded source implementation in isolated candidate
→ browser/geometry/accessibility/performance/chaos verification
→ transactional live promotion
→ live post-apply verification
→ VERIFIED, or automatic rollback
```

The preview itself is never executable authority. Generated preview HTML is stripped of scripts/event handlers and receives an offline CSP.
