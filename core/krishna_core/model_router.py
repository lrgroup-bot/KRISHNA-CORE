"""KRISHNA local-first model routing.

Providers are replaceable workers. KRISHNA remains the authority.
No provider receives credentials or filesystem access through this module.
"""
from __future__ import annotations
from dataclasses import dataclass
import json, os, urllib.request\nfrom .unified_model_mesh import UnifiedModelMesh, Worker\nfrom .cloud_providers import GroqProvider, CerebrasProvider, GeminiProvider, OpenRouterProvider, HuggingFaceProvider

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
    def __init__(self):
        self.control_plane=None
        self.mesh=UnifiedModelMesh()\n        self.providers=[
            OpenAICompatibleLocalProvider("ollama",os.getenv("KRISHNA_OLLAMA_OPENAI_URL","http://127.0.0.1:11434/v1"),os.getenv("KRISHNA_OLLAMA_MODEL") or None),
            OpenAICompatibleLocalProvider("gpt4all",os.getenv("KRISHNA_GPT4ALL_URL","http://127.0.0.1:4891/v1"),os.getenv("KRISHNA_GPT4ALL_MODEL") or None),
        ]
    def configure_free_cloud(self, secret_resolver, models=None):
        """Register cloud workers only when a trusted secret resolver supplies keys.

        The caller should resolve secrets from SecureSecretVault/DPAPI. Keys are
        never written to router state. confirmed_free is an explicit admission
        assertion and the mesh still blocks providers after quota exhaustion.
        """
        models=models or {}
        specs=[
            ("groq",GroqProvider,"GROQ_API_KEY",models.get("groq","openai/gpt-oss-120b")),
            ("cerebras",CerebrasProvider,"CEREBRAS_API_KEY",models.get("cerebras","gpt-oss-120b")),
            ("gemini",GeminiProvider,"GEMINI_API_KEY",models.get("gemini","gemini-3.5-flash")),
            ("openrouter",OpenRouterProvider,"OPENROUTER_API_KEY",models.get("openrouter","openrouter/free")),
            ("huggingface",HuggingFaceProvider,"HF_TOKEN",models.get("huggingface","openai/gpt-oss-120b")),
        ]
        added=[]
        for name,cls,secret_name,model in specs:
            key=secret_resolver(secret_name)
            if not key: continue
            self.mesh.add(Worker(name,cls(key),model,{"general","reasoning","coding"},local=False,confirmed_free=True))
            added.append(name)
        return {"added":added,"policy":"ZERO_COST_ONLY","spend_limit_usd":0.0}

    def cloud_complete(self,req:ModelRequest,privacy="approved_cloud"):
        return self.mesh.dispatch(req.prompt,task=req.task,privacy=privacy,system=req.system,max_tokens=req.max_tokens)

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
