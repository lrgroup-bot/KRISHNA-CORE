# R19 bounded hybrid engineering

This increment connects the existing callback contract to production components. It is not a claim that all future autonomous KRISHNA features are complete.

`hybrid.implementation.plan` returns policy only. `hybrid.implementation.run` is a local-PC/authorized-job action requiring approval, an active registered project, enabled actions and explicit capabilities. The existing job API can run it and retains its task/mission/action receipts. It never merges, promotes, installs dependencies, changes accounts or starts financial actions.

The production stages reuse:

1. GARUDA's existing public discovery adapters. Only a separately approved `public_query` is sent externally, never the private task or source files. No approved query, missing evidence or unavailable free cloud leaves the workflow local. OpenRouter cross-check is optional, restricted to cloud-approved projects, independently zero-price checked and limited to one completion attempt.
2. BRAHMAGYAN mission and the existing Rishi Council perspective planner through the registered Gautama actor. Perspective planning is real execution but is not independent source or license verification. Discovered claims remain untrusted.
3. The existing developer actor and local Ollama model action. Source context and replacement files are bounded; model output must be strict JSON. Instructions in retrieved material are not executable authority.
4. SUDARSHAN's existing staging and independent verification operator. Only registered allowlisted checks run. Optional approved loopback frontend/browser checks use existing browser adapters. Models cannot modify acceptance tests, manifests, credentials or CI. Candidates are file-copy workspaces, not an OS security sandbox.
5. One MRITYUNJAY repair attempt using the existing repair prompt/guard, local model and existing staging/verifier. The failed candidate supplies context; restaging starts from the registered project to avoid recursive candidate copies. A repaired candidate is retested, never treated as successful merely because a model said so.
6. BRAHMA/Gyan's existing proposal path. Test evidence is retained as a candidate lesson. Trusted learning still requires its existing review/approval; passing software tests does not validate research claims.

Each stage returns actual action IDs/actors. `/api/agents/runtime` includes the latest observed action for each registered agent, explicitly limited to the last 200 receipts. No receipt means `not_observed`; returned actions do not certify complete agent workflows. Model prompt text is hashed in action receipts; secrets and raw provider bodies/reasoning are not copied into error reports.

## Provider boundaries

OpenRouter preserves only numeric HTTP status and bounded Retry-After metadata. 429/503 stop the call immediately, with persistent bounded exponential cooldown; 401/402 stop account attempts; 403/404 cool down the affected model. Generic failures never print provider body/prompt details. Calls attempt at most two catalog-eligible text models, or exactly one explicitly selected model. Known unavailable endpoints are removed from rankings. Empty/reasoning-only output is diagnostic failure, never a final answer.

Authenticated OpenRouter inference also requires the canonical endpoint and a fresh per-key `$0` spending cap. Missing/unknown/nonzero caps block POST without changing account configuration. No paid fallback is enabled. See [OpenRouter's error documentation](https://openrouter.ai/docs/api/reference/errors-and-debugging) for HTTP/backoff behavior. Live inference requires an approved public prompt and respected cooldown; mock results are not live provider acceptance.

Ollama requests use loopback URLs, ignore environment proxies, reject redirects, bound input/output/context/generation and permit one concurrent transport request with a short queue deadline. Existing local routing tries at most two installed candidates. Unattended readiness requires measured local-model and real Core chat acceptance, not installed-model metadata alone.

## Verification and deployment

Run focused provider/privacy/hybrid integration tests, then all Core/repository tests, architecture audit, real Chromium privacy/desktop/project checks, frontend build and relevant mobile contracts. The hybrid integration tests use real registered agents, action receipts, staging, subprocess tests and learning proposals; only model/network responses are controlled fixtures. Live Ollama tests and live cloud tests must be reported separately.

The Windows workflow builds and bundles the actual spatial frontend and orchestration page; the frozen server prefers bundled spatial assets while retaining the legacy external fallback. Test browser/UI behavior before packaging, then verify frozen Core, local inference and bundled assets. Accepted existing R8/R13/R16/R19 packages and dirty user worktrees remain unchanged. Native capture/physical mobile/remote-hardware limitations must remain explicit.

PR #228 may merge only into `fix/krishna-ui-runtime-verification` after current-head required CI and local acceptance pass. Merging to main, signing or promoting a release needs separate authorization. Production self-modification, complete fleet diagnostics, trusted worker attestation and a general repository-to-plugin installer remain future gated work.
