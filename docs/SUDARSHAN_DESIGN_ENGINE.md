# Sudarshan Design Engine
Sudarshan owns UI/design governance so KRISHNA receives summary-only results.

## Project Brain extension
Projects use PROJECT.md, ARCHITECTURE.md, RULES.md, PHASES.md, DESIGN.md, AGENTS.md, MEMORY.md and PROJECT_STATE.json.

## Selective skill routing
Load only task-relevant design skills. Frontend uses web-design + Taste; screenshot/reference work adds image-to-code; deterministic browser QA uses Playwright CLI; Stagehand is optional only for agentic/self-healing browser cases. Storybook-style component-state testing is an adapter target.

## Verification loop
spec -> design genome -> implementation -> render -> functional/visual/responsive/accessibility/security checks -> repair/retest -> Sudarshan acceptance -> memory update.

Third-party repositories are references/adapters, not blindly vendored. Pin versions and preserve licenses before importing code.
