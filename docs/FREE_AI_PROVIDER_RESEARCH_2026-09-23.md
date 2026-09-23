# KRISHNA Free-AI Provider Verification — 2026-09-23

This file records the provider-policy decision behind KRISHNA's native free-cloud routing.
The runtime rule is stricter than a marketing claim: an automatic cloud provider must be
provably non-billable at execution time. A trial, promo credit, manually-set free_only
label, or "free account exists" is not enough.

## Permanent/recurring free candidates

| Provider | Current official free status | KRISHNA decision |
|---|---|---|
| Cloudflare Workers AI | Workers Free: 10,000 Neurons/day; calls stop after quota. Some frontier models require Workers Paid. | **Native automatic adapter.** Requires Billing Read subscription preflight, an @cf/* model, and no active Workers-paid subscription. |
| GroqCloud | Free tier with published model-specific limits; Developer is a separate paid upgrade. | Strong candidate, but **not automatic** until KRISHNA can machine-prove the organization is still Free. Existing encrypted gateway remains explicit-use only. |
| Mistral Studio Free mode | API enabled without card; rate limits are organization/tier specific. Free-mode prompts/outputs may be used for training unless the admin opts out. | **Not automatic.** No machine-verifiable Free-plan + privacy-opt-out proof currently available to KRISHNA. |
| Google Gemini API | Has a Free tier with model-specific limits. Google documents that Free-tier content may be used to improve products. | **Not automatic** under KRISHNA privacy policy. Public explicit-use only if owner chooses. |
| Hugging Face Inference Providers | Free users currently receive $0.10/month credits; extra use requires purchased credits. | Too small for a meaningful native automatic fallback. |
| GitHub Models | Retired July 30, 2026. | Do not integrate. |

## Trial / promotional, not permanent-free

| Provider | Current official status | KRISHNA decision |
|---|---|---|
| Alibaba Cloud Model Studio / Qwen | New-user quotas in Singapore International are valid 90 days. PAYG begins automatically unless Free Quota Only is enabled. | Trial only; never automatic. |
| Baidu Qianfan | Current onboarding advertises a new-user voucher / promotional token grant with limited validity. | Trial/promo only; never automatic. |
| NVIDIA NIM hosted API | NVIDIA Developer Program gives free hosted NIM access for prototyping; production requires the appropriate NVIDIA AI Enterprise licensing. | Research/prototyping only; not KRISHNA's production automatic route. |
| Cerebras Inference | Current public site describes a $5 free trial credit, then Developer PAYG. | Trial only; not automatic. |
| Moonshot/Kimi direct API | No official permanent-free direct API tier could be verified. Third-party sources describe new-user voucher credit; the web/app free product is not evidence of free API service. | Do not classify as free. Kimi zero-priced OpenRouter variants remain governed by live OpenRouter pricing checks. |
| ByteDance/Volcengine Ark / Doubao | Current platform advertises PAYG plus promotional/free quotas; a 50M/month complimentary offer is tied to a purchased ArkClaw subscription. | No verified unconditional permanent-free API; never automatic. |
| DeepSeek direct API | Metered token pricing; balance API separates granted and topped-up balance. | Paid/metered; never automatic free fallback. |

## Capability notes

- Cloudflare Workers AI: OpenAI-compatible Chat Completions and embeddings for supported
  models; GPT-OSS also supports Responses. The catalog contains text, reasoning, vision,
  embedding, speech and image tasks. Tool/function support is model-specific.
- GroqCloud: OpenAI-compatible APIs, tool use across hosted models, GPT-OSS reasoning and
  code execution, Qwen multimodal/vision, Whisper speech. Free limits are model-specific.
- Mistral: chat/reasoning/coding, tools/function calling and multimodal models are available;
  Free mode is intended for evaluation/prototyping.
- Qwen Model Studio: OpenAI-compatible Chat/Responses plus Qwen text, coder, VL/vision,
  omni/realtime and reasoning families.
- DeepSeek: OpenAI and Anthropic-compatible surfaces; current Flash supports vision, tools,
  reasoning and a 1M context window.

## Privacy boundary

Regardless of a provider's own privacy terms, KRISHNA keeps the following local unless the
owner explicitly overrides the relevant policy: private source code, credentials/secrets,
personal or face data, raw HAWKEYE camera/audio/evidence, and private Gyan-Bhandar material.
Cloud output is worker evidence, never authority or automatic Gyan truth.

Cloudflare states that Workers AI Customer Content is not used to train Workers AI models or
improve Cloudflare/third-party services without explicit consent. Groq states inference data
is not retained by default and supports ZDR, but plan status is not currently exposed to
KRISHNA in a way that proves zero billing. Mistral Free mode may train on inputs/outputs
unless the account admin opts out. Gemini's Free tier is documented as eligible for product
improvement use.

## Automatic routing hierarchy

1. Ollama/local
2. live-zero-price OpenRouter fabric
3. Cloudflare Workers AI only after live zero-billing account verification
4. remaining local engine/fallback or STOP

No provider is promoted into this hierarchy merely because its dashboard says "Free". Paid
cloud remains disabled by default and no direct adapter may relax that rule.

## Official sources checked

- Cloudflare Workers AI pricing: https://developers.cloudflare.com/workers-ai/platform/pricing/
- Cloudflare Workers AI errors: https://developers.cloudflare.com/workers-ai/platform/errors/
- Cloudflare OpenAI compatibility: https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/
- Cloudflare Workers AI data usage: https://developers.cloudflare.com/workers-ai/platform/data-usage/
- Cloudflare account subscriptions API: https://developers.cloudflare.com/api/resources/accounts/subresources/subscriptions/methods/get/
- Mistral Studio API activation: https://docs.mistral.ai/getting-started/quickstarts/studio/activate-and-generate-api-key
- Mistral free-mode privacy controls: https://help.mistral.ai/en/articles/347617-do-you-use-my-user-data-to-train-your-artificial-intelligence-models
- NVIDIA NIM FAQ: https://docs.api.nvidia.com/nim/docs/product
- Baidu Qianfan: https://cloud.baidu.com/doc/WENXINWORKSHOP/s/Ilrhj9zfw
- Alibaba Model Studio free quota: https://www.alibabacloud.com/help/en/model-studio/new-free-quota
- Alibaba Model Studio pricing: https://www.alibabacloud.com/help/en/model-studio/model-pricing
- DeepSeek pricing: https://api-docs.deepseek.com/quick_start/pricing/
- DeepSeek balance API: https://api-docs.deepseek.com/api/get-user-balance/
- Volcengine Ark OpenAI compatibility: https://docs.volcengine.com/docs/82379/1330626?lang=en
- Groq rate limits: https://console.groq.com/docs/rate-limits
- Groq data handling: https://console.groq.com/docs/your-data
- Groq billing: https://console.groq.com/docs/billing-faqs
- Cerebras Inference: https://www.cerebras.ai/inference
- Cerebras privacy: https://www.cerebras.ai/privacy-policy
- Gemini rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Hugging Face Inference Providers pricing: https://huggingface.co/docs/inference-providers/pricing
- GitHub Models retirement: https://docs.github.com/en/github-models
