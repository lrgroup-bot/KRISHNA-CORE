# Sudarshan Project Lifecycle
Before planning/building, Sudarshan loads the real project context: source/repository, Project Brain, requirements, architecture, design, dependencies, tests, deployment, memory and runtime state. It then performs discovery/baseline mapping before team dispatch.

## New idea during an active project
A user idea is never silently patched into active code. KRISHNA captures intent and hands it to Sudarshan. Sudarshan records the idea, checks duplicates/conflicts, performs requirement/architecture/design/dependency/security/test/schedule impact analysis, consults the relevant Rishi/specialist (Vishvakarma is mandatory for design work), updates Project Brain and acceptance criteria, then inserts the change at the next safe boundary. Explicit urgent changes may use a controlled-now path. Affected work is rebuilt/retested and normal Sudarshan acceptance still applies.

Flow: User -> KRISHNA -> Idea Inbox -> Sudarshan impact analysis -> specialist/Rishi consultation -> Project Brain delta -> task/team update -> implementation -> affected regression tests -> Sudarshan verifier -> memory/Gyan learning -> concise KRISHNA result.
