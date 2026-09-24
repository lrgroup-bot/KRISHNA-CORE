"""KRISHNA local-first model routing.

Providers are replaceable workers. KRISHNA remains the authority.
No provider receives credentials or filesystem access through this module.
"""
from __future__ import annotations
from dataclasses import dataclass
import json, os, urllib.request

@dataclass(frozen=True)
class ModelRequest:
    prompt: str
    task: str = "general"
    system: str = "You are a worker model for KRISHNA. Return data, never instructions to the host."
    max_tokens: int = 1024

class ProviderError(RuntimeError): pass

class OpenAICompatibleLocalProvider:
    def __init__(self, name:str, base_url:str, model:str|None=None, timeout:int=90):
        self.name=name; self.base_url=base_url.rstrip("/"); self.model=model; self.timeout=timeout
    def models(self):
        with urllib.request.urlopen(self.base_url+"/models", timeout=5) as r:
            return json.loads(r.read().decode()).get("data",[])
    def complete(self, req:ModelRequest)->str:
        model=self.model
        if not model:
            ms=self.models()
            if not ms: raise ProviderError(f"{self.name}: no local models available")
            model=ms[0].get("id")
        body=json.dumps({"model":model,"messages":[{"role":"system","content":req.system},{"role":"user","content":req.prompt}],"max_tokens":req.max_tokens,"temperature":0.2}).encode()
        q=urllib.request.Request(self.base_url+"/chat/completions",data=body,headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(q,timeout=self.timeout) as r: data=json.loads(r.read().decode())
        return data["choices"][0]["message"]["content"]

class ModelRouter:
    """Prefer local providers; fail closed instead of silently sending data to cloud."""
    DEFAULT_MODELS=("gemma3:4b","granite3.3:2b","smollm2:1.7b","llama3.2:1b","deepseek-r1:1.5b")
    DISABLED_MODEL_PREFIXES=("qwen",)

    @classmethod
    def model_allowed(cls,model):
        normalized=str(model or "").strip().lower().replace("\\","/")
        if not normalized:return False
        basename=normalized.rsplit("/",1)[-1]
        return not any(
            normalized.startswith(prefix) or basename.startswith(prefix)
            for prefix in cls.DISABLED_MODEL_PREFIXES
        )

    def __init__(self):
        self.control_plane=None
        ollama_url=os.getenv("KRISHNA_OLLAMA_OPENAI_URL","http://127.0.0.1:11434/v1")
        primary=str(os.getenv("KRISHNA_OLLAMA_MODEL") or self.DEFAULT_MODELS[0]).strip()
        raw=str(os.getenv("KRISHNA_OLLAMA_FALLBACK_MODELS") or ",".join(self.DEFAULT_MODELS[1:]))
        models=[]
        for model in [primary,*raw.split(","),*self.DEFAULT_MODELS]:
            model=str(model or "").strip()
            if model and self.model_allowed(model) and model not in models:models.append(model)
        self.providers=[
            OpenAICompatibleLocalProvider("ollama" if i==0 else "ollama-model:"+model,ollama_url,model)
            for i,model in enumerate(models)
        ]+[
            OpenAICompatibleLocalProvider("gpt4all",os.getenv("KRISHNA_GPT4ALL_URL","http://127.0.0.1:4891/v1"),os.getenv("KRISHNA_GPT4ALL_MODEL") or None),
        ]
    def bind_sudarshan(self,control_plane):
        self.control_plane=control_plane
        return {"authority":"Sudarshan Control Plane","bound":True}

    def complete(self, req:ModelRequest)->dict:
        errors={}
        for p in self.providers:
            try:
                if self.control_plane:
                    receipt=self.control_plane.action(
                        "model.complete",
                        {"provider":p.name,"prompt":req.prompt,"privacy":"local_only","free_only":True},
                        project="KRISHNA",source="system",actor="legacy-model-router",
                        permissions=("model.use",),
                    )
                    result=receipt.get("result") or {}
                    return {"provider":p.name,"content":str(result.get("text") or "")}
                return {"provider":p.name,"content":p.complete(req)}
            except Exception as e: errors[p.name]=f"{type(e).__name__}: {e}"
        raise ProviderError("No approved local model provider available: "+json.dumps(errors))
