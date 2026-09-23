"""First-class cloud workers for the KRISHNA Unified Model Mesh.

Hard rule: these adapters do not decide whether spending is allowed. Dispatch must
pass ZeroCostPolicy before any cloud request. API keys are supplied at runtime
from KRISHNA's encrypted vault/environment and are never persisted here.
"""
from __future__ import annotations
from dataclasses import dataclass
import json, urllib.error, urllib.request

class CloudProviderError(RuntimeError): pass
class QuotaExhausted(CloudProviderError): pass

@dataclass(frozen=True)
class CloudRequest:
    prompt: str
    model: str
    system: str = "You are a worker model for KRISHNA."
    max_tokens: int = 2048

class OpenAICloudProvider:
    def __init__(self,name,base_url,api_key,timeout=120,extra_headers=None):
        self.name=name; self.base_url=base_url.rstrip("/"); self.api_key=api_key
        self.timeout=timeout; self.extra_headers=extra_headers or {}
    def complete(self,req:CloudRequest):
        body=json.dumps({"model":req.model,"messages":[{"role":"system","content":req.system},{"role":"user","content":req.prompt}],
                         "max_tokens":req.max_tokens,"temperature":0.2}).encode()
        headers={"Content-Type":"application/json","Authorization":"Bearer "+self.api_key}|self.extra_headers
        q=urllib.request.Request(self.base_url+"/chat/completions",data=body,headers=headers)
        try:
            with urllib.request.urlopen(q,timeout=self.timeout) as r:
                data=json.loads(r.read().decode()); meta=dict(r.headers.items())
        except urllib.error.HTTPError as exc:
            if exc.code==429: raise QuotaExhausted(f"{self.name}: free quota/rate limit exhausted") from exc
            raise CloudProviderError(f"{self.name}: HTTP {exc.code}") from exc
        return {"text":data["choices"][0]["message"]["content"],"headers":meta}

class GroqProvider(OpenAICloudProvider):
    def __init__(self,api_key,timeout=120):
        super().__init__("groq","https://api.groq.com/openai/v1",api_key,timeout)

class CerebrasProvider(OpenAICloudProvider):
    def __init__(self,api_key,timeout=120):
        super().__init__("cerebras","https://api.cerebras.ai/v1",api_key,timeout,
                         {"X-Cerebras-3rd-Party-Integration":"krishna"})

class OpenRouterProvider(OpenAICloudProvider):
    def __init__(self,api_key,timeout=120):
        super().__init__("openrouter","https://openrouter.ai/api/v1",api_key,timeout)

class HuggingFaceProvider(OpenAICloudProvider):
    def __init__(self,api_key,timeout=120):
        super().__init__("huggingface","https://router.huggingface.co/v1",api_key,timeout)

class GeminiProvider:
    def __init__(self,api_key,timeout=120):
        self.name="gemini"; self.api_key=api_key; self.timeout=timeout
    def complete(self,req:CloudRequest):
        model=req.model.strip()
        url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        body=json.dumps({"system_instruction":{"parts":[{"text":req.system}]},
                         "contents":[{"role":"user","parts":[{"text":req.prompt}]}],
                         "generationConfig":{"maxOutputTokens":req.max_tokens,"temperature":0.2}}).encode()
        q=urllib.request.Request(url,data=body,headers={"Content-Type":"application/json","x-goog-api-key":self.api_key})
        try:
            with urllib.request.urlopen(q,timeout=self.timeout) as r:data=json.loads(r.read().decode())
        except urllib.error.HTTPError as exc:
            if exc.code==429: raise QuotaExhausted("gemini: free quota/rate limit exhausted") from exc
            raise CloudProviderError(f"gemini: HTTP {exc.code}") from exc
        parts=((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
        return {"text":"".join(str(x.get("text") or "") for x in parts),"headers":{}}
