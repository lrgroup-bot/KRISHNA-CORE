# KRISHNA AI Role Policy

KRISHNA can now assign different AI providers/models to different kinds of work without
weakening the existing local-first, zero-cost-cloud-first safety rules.

## Modes

- **Auto** — KRISHNA chooses under privacy, availability, capability and zero-cost policy.
- **Prefer** — try the selected AI first; if it fails or is blocked, continue through the
  normal safe routing hierarchy.
- **Pin** — use only the selected AI for that role. If it is unavailable or policy-blocked,
  stop instead of silently switching to another AI.

A role selection is a routing preference, not a safety override. It cannot enable paid
cloud, bypass project privacy, relax secret-egress controls, or make a manually-labelled
free gateway eligible for automatic zero-cost routing.

## Built-in roles

| Role | Purpose | OpenRouter specialist family used in Auto |
|---|---|---|
| general | Normal conversation/summaries | general |
| coding | Coding and code changes | coding |
| reasoning | Hard analysis | reasoning |
| vision | Approved non-sensitive image understanding | vision |
| research | Public research synthesis | reasoning |
| medical_research | Public medical-literature synthesis | medical |
| implementation | Software-factory implementation worker | coding |
| architecture_review | Independent architecture review | reasoning |
| bug_test_review | Tests/regression/bug review | coding |
| security_review | Defensive security review | reasoning |

Private HAWKEYE evidence, private Gyan-Bhandar material, credentials, personal/face data,
and project data marked local_only/restricted remain local regardless of role assignment.

## Examples

### Keep everything automatic

```json
{"role":"coding","mode":"auto"}
```

### Prefer a local coding model

```json
{"role":"coding","mode":"prefer","provider":"ollama","model":"qwen2.5-coder:7b"}
```

KRISHNA tries that Ollama model first, then follows the safe local -> verified-free cloud
fallback chain if the local model fails.

### Pin architecture review to OpenRouter's live free reasoning pool

```json
{"role":"architecture_review","mode":"pin","provider":"openrouter-free"}
```

The exact model is still chosen from OpenRouter's live zero-price catalog, so a model is
never pinned past the point where it stops being free.

## Local PC API

Read effective role assignments:

```
GET /api/models/roles?project=KRISHNA
```

Change a role assignment from the KRISHNA PC only:

```
POST /api/models/roles/assign
Content-Type: application/json

{"role":"coding","mode":"prefer","provider":"ollama","model":"qwen2.5-coder:7b"}
```

Reset a role:

```json
{"role":"coding","mode":"auto"}
```

## Recommended initial layout for KRISHNA

- General chat: Auto
- Coding/implementation: Prefer a strong local Ollama coder
- Architecture review: Prefer OpenRouter free reasoning
- Bug/test review: Prefer a different model from implementation when available
- Security review: Auto/verified reasoning, with private code remaining local
- Vision: local by default; OpenRouter vision only for approved public/non-sensitive images
- Medical research: OpenRouter medical/reasoning only for public research; personal medical
  records remain local
- Image generation: keep using the dedicated zero-price media adapter rather than the text
  role router

This gives KRISHNA diversity of reviewers without turning model choice into an uncontrolled
cloud fallback.
