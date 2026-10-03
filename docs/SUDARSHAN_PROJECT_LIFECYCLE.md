# Sudarshan Project Lifecycle

KRISHNA is the authority boundary; Sudarshan is the project lifecycle owner. Before planning/building, Sudarshan loads the real project context: source/repository, Project Brain, approved requirements, architecture, design, dependencies, tests, deployment, memory and runtime state. It then performs discovery/baseline mapping before team dispatch.

## Project ingress
Owner work may enter as Owner/User -> KRISHNA -> Sudarshan.

Commercial customer work enters as Customer -> LR Technology -> Sudarshan. LR Technology must provide a customer-approved, versioned Project Specification Package. Sudarshan rejects unapproved or unversioned LR Technology project intake. When execution needs a protected capability, Sudarshan requests authority from KRISHNA; it does not self-approve.

## New idea during an active project
An idea is never silently patched into active code.

For owner work, KRISHNA captures intent and hands it to Sudarshan.

For LR Technology customer work, LR Technology records customer intent/approval and submits the versioned project delta directly to Sudarshan.

Sudarshan checks duplicates/conflicts, performs requirement/architecture/design/dependency/security/test/schedule impact analysis, consults the relevant Rishi/specialist (Vishvakarma is mandatory for design work), updates Project Brain and acceptance criteria, then inserts the change at the next safe boundary. Explicit urgent changes may use a controlled-now path only within KRISHNA authority and policy. Affected work is rebuilt/retested and normal Sudarshan acceptance still applies.

Owner flow: User -> KRISHNA -> Sudarshan -> impact analysis -> specialists -> Project Brain delta -> implementation -> regression -> Sudarshan verifier -> learning -> KRISHNA result.

Customer flow: Customer -> LR Technology -> approved Project Delta -> Sudarshan -> KRISHNA authority requests as needed -> specialists -> implementation -> regression -> Sudarshan verifier -> verified release -> LR Technology -> customer.
