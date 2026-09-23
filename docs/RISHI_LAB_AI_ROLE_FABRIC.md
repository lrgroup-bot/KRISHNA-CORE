# Rishi + LAB AI Role Fabric

## Purpose

KRISHNA separates **evidence acquisition**, **model reasoning**, **experimentation**, and
**knowledge promotion**. No model is treated as an authority merely because it produced
a confident answer.

The runtime uses dedicated AI roles for different BRAHMAGYAN/Rishi/LAB phases so the
same model does not silently perform every step.

## Research authority split

- **Garuda / Garudanetra**: discover and retrieve source material.
- **Rishi AI roles**: interpret supplied evidence, challenge claims and structure debate.
- **LAB BOT**: formulate bounded testable hypotheses, validate protocols, simulate or
  coordinate approved adapters, and record evidence.
- **Gautama**: independent evidential/citation sufficiency review.
- **Bharadvaja**: falsifiable test-plan design.
- **Veda Vyasa**: final source-grounded synthesis.
- **BRAHMA**: learning/QC governor.
- **Gyan-Bhandar**: approved knowledge storage only after normal gates.

Model prose is never source evidence.

## AI roles

| Role | Purpose | Auto strategy |
|---|---|---|
| rishi_research | source-grounded claim extraction and analysis | local first |
| rishi_counter_evidence | challenge candidate claims with counter-evidence | verified cloud first |
| rishi_debate | council debate | verified cloud first |
| gautama_review | citation/evidence sufficiency review | verified cloud first |
| bharadvaja_test_plan | falsifiable test/experiment planning | verified cloud first |
| lab_hypothesis | unverified hypothesis assistance | local first |
| lab_result_analysis | independent result interpretation | verified cloud first |
| vyasa_synthesis | final source-grounded synthesis | verified cloud first |

Existing general/coding/reasoning/vision/medical/coding-review roles remain available.

## Auto / Prefer / Pin

- **Auto**: KRISHNA follows the role's strategy under privacy/cost policy.
- **Prefer**: try the owner-selected AI first, then safe fallback.
- **Pin**: use only the owner-selected AI for that role; otherwise STOP.

These modes never override privacy or billing protections.

## Zero-cost policy

Automatic cloud routing accepts only providers that prove zero-cost eligibility at
execution time:

1. Local Ollama/GPT4All.
2. OpenRouter zero-cost fabric after a live price preflight.
3. Native direct-free adapters that independently prove non-billable account state,
   currently including the Cloudflare Workers AI guard.
4. STOP when paid cloud is disabled.

A generic gateway profile merely labelled `free_only=true` is **not** sufficient for
automatic Rishi/LAB learning. Groq, Mistral, Gemini, Hugging Face, Cerebras and similar
profiles remain explicit/manual until a provider-specific live billing guard exists.

## Privacy

For `local_only` or `restricted` projects, every Rishi/LAB role stays local. Private
source code, credentials, personal/face information, HAWKEYE raw evidence and private
Gyan-Bhandar content are not sent to cloud models through these roles.

## Rishi live research mapping

The live research executor maps its phases as follows:

- atomic and classical extraction -> `rishi_research`
- counter-evidence classification -> `rishi_counter_evidence`
- Rishi debate turns -> `rishi_debate`
- Gautama claim/debate review -> `gautama_review`
- Bharadvaja test plan -> `bharadvaja_test_plan`
- Veda Vyasa debate/final synthesis -> `vyasa_synthesis`

The modern-science and Vedic/classical evidence tracks remain explicitly separate.
Classical texts may supply textual, historical or philosophical evidence; they are not
reclassified as experimental science.

## LAB hypothesis assistance

`lab.hypothesis.assist` / `POST /api/lab/hypothesis` produces one falsifiable
candidate with variables, controls, measurements, falsification criteria and limitations.
Its status is always `UNVERIFIED_HYPOTHESIS`.

It does not execute an experiment and does not bypass the existing LAB request/protocol
workflow.

## LAB result analysis

`lab.result.analyze` / `POST /api/lab/result/analyze` reviews an existing experiment
record only after result evidence exists.

When privacy permits, KRISHNA requests:

1. one **local** review; and
2. one **independent live-verified zero-cost cloud** review.

The returned status remains `UNVERIFIED_INTERPRETATION`. Agreement between the two
models does not make a claim true. Independent replication, measurements, controls,
Rishi review and BRAHMA/Gyan gates remain required.

For local-only work, the cloud review is omitted.

## Owner API

Read roles and effective routing:

```
GET /api/models/roles?project=KRISHNA
```

Assign a role from the KRISHNA PC:

```
POST /api/models/roles/assign
Content-Type: application/json

{"role":"gautama_review","mode":"prefer","provider":"openrouter-free"}
```

Pin a local model:

```json
{"role":"lab_hypothesis","mode":"pin","provider":"ollama","model":"qwen2.5:3b"}
```

Reset to automatic:

```json
{"role":"lab_hypothesis","mode":"auto"}
```

The role policy is persisted under KRISHNA runtime state and does not expose stored
credentials.
