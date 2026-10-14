# KRISHNA Project Research -> Local Build Policy

Hard execution order:

1. Research: GARUDA/web/GitHub gather current PUBLIC findings, docs, patterns and evidence.
2. Local synthesis: KRISHNA/BRAHMA evaluate findings locally.
3. Local build: architecture, backend, frontend, Android/iOS, refactors and repairs occur only in isolated local worktrees.
4. Local verification: tests, browser/UI, security and integration run locally first.
5. Cloud escalation: only after a recorded local failure; only a minimal redacted context packet; only a machine-verified zero-cost provider; cloud has no mutation/promotion authority.
6. GitHub independent verification: use Actions only when zero-cost status is proven for the repository/runner mode. GitHub is verifier/build infrastructure, not primary coding authority.
7. Promotion: independent review -> UI Guardian -> MRITYUNJAY -> SUDARSHAN -> transactional promotion -> post-deploy health -> rollback on regression.

Privacy:
- secrets, credentials, personal/private files, full private repositories and sensitive architecture never leave local execution.
- public web findings may be stored with provenance and then consumed locally.
- cloud failure must never trigger paid fallback.

GitHub zero-spend:
- public repository + standard GitHub-hosted runner: eligible under current GitHub free-use rule.
- private/internal + GitHub-hosted: conditional; block unless zero-cost usage is proven.
- self-hosted: Actions-minute cost is not billed by GitHub, but only an isolated trusted runner is eligible. Do not expose the primary KRISHNA host to untrusted PR execution.
