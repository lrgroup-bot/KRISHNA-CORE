from __future__ import annotations

import json
import os
import urllib.request

from .config import settings
from .model_gateway import ModelGatewayRegistry


class ModelRouter:
    """Privacy-aware local-first model pool.

    Local Ollama/GPT4All are always attempted before approved cloud. A caller may
    request free_only=True, in which case KRISHNA will use only explicitly configured
    free-only encrypted gateway profiles and will never fall through to paid/env cloud
    providers.
    """

    PROVIDERS={
      "openai":{"key":"OPENAI_API_KEY","url":"https://api.openai.com/v1/chat/completions","model":"OPENAI_MODEL","default":"gpt-4o-mini"},
      "anthropic":{"key":"ANTHROPIC_API_KEY","url":"https://api.anthropic.com/v1/messages","model":"ANTHROPIC_MODEL","default":"claude-3-5-sonnet-latest"},
      "gemini":{"key":"GEMINI_API_KEY","url":"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent","model":"GEMINI_MODEL","default":"gemini-2.0-flash"},
      "xai":{"key":"XAI_API_KEY","url":"https://api.x.ai/v1/chat/completions","model":"XAI_MODEL","default":"grok-2-latest"},
      "openrouter":{"key":"OPENROUTER_API_KEY","url":"https://openrouter.ai/api/v1/chat/completions","model":"OPENROUTER_MODEL","default":"openrouter/auto"},
    }

    def __init__(self,gateway:ModelGatewayRegistry|None=None):
        self.gateway=gateway
        self.control_plane=None

    def bind_sudarshan(self,control_plane):
        self.control_plane=control_plane
        return {"authority":"Sudarshan Control Plane","bound":True}

    @staticmethod
    def _openai_local(base_url,model,prompt,timeout=90):
        body=json.dumps({"model":model,"messages":[{"role":"user","content":prompt}],"temperature":0.2}).encode()
        req=urllib.request.Request(base_url.rstrip("/")+"/chat/completions",data=body,headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=timeout) as r:data=json.loads(r.read().decode())
        return data["choices"][0]["message"]["content"]

    def local(self,prompt,model=None):
        model=model or os.getenv("KRISHNA_LOCAL_MODEL","qwen2.5:3b")
        body=json.dumps({"model":model,"prompt":prompt,"stream":False}).encode()
        req=urllib.request.Request(settings.ollama_url.rstrip("/")+"/api/generate",data=body,headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=90) as r:return json.loads(r.read().decode()).get("response","")

    def gpt4all(self,prompt,model=None):
        model=model or os.getenv("KRISHNA_GPT4ALL_MODEL","")
        base=os.getenv("KRISHNA_GPT4ALL_URL","http://127.0.0.1:4891/v1")
        if not model:
            with urllib.request.urlopen(base.rstrip("/")+"/models",timeout=5) as r:
                rows=json.loads(r.read().decode()).get("data",[])
            if not rows:raise RuntimeError("gpt4all has no local models")
            model=rows[0].get("id")
        return self._openai_local(base,model,prompt)

    @staticmethod
    def _probe_json(url,timeout=2):
        try:
            with urllib.request.urlopen(url,timeout=timeout) as r:
                return True,json.loads(r.read().decode())
        except Exception as exc:
            return False,{"error":f"{type(exc).__name__}: {exc}"}

    def available(self):
        ollama_ok,ollama_data=self._probe_json(settings.ollama_url.rstrip("/")+"/api/tags")
        gpt_base=os.getenv("KRISHNA_GPT4ALL_URL","http://127.0.0.1:4891/v1").rstrip("/")
        gpt_ok,gpt_data=self._probe_json(gpt_base+"/models")
        out=[
          {"provider":"ollama","available":ollama_ok,"local":True,"model":os.getenv("KRISHNA_LOCAL_MODEL","qwen2.5:3b"),"credential_source":"none","error":None if ollama_ok else ollama_data.get("error")},
          {"provider":"gpt4all","available":gpt_ok,"local":True,"model":os.getenv("KRISHNA_GPT4ALL_MODEL","auto"),"credential_source":"none","error":None if gpt_ok else gpt_data.get("error")},
        ]
        for name,p in self.PROVIDERS.items():
            out.append({"provider":name,"available":bool(os.getenv(p["key"])),"local":False,
                        "model":os.getenv(p["model"],p["default"]),"credential_source":"environment","free_only":False})
        if self.gateway:
            for row in self.gateway.list()["profiles"]:
                out.append({"provider":"gateway:"+row["id"],"name":row["name"],"available":bool(row["enabled"] and row["credential_available"]),
                            "local":False,"model":row["model"],"credential_source":"windows-dpapi","free_only":row["free_only"]})
        return out

    def _chat_compatible(self,name,prompt):
        p=self.PROVIDERS[name]; key=os.getenv(p["key"]); model=os.getenv(p["model"],p["default"])
        if not key:raise RuntimeError(name+" API not configured")
        if name=="gemini":
            url=p["url"].format(model=model)+"?key="+key
            body={"contents":[{"parts":[{"text":prompt}]}]};headers={"Content-Type":"application/json"}
        elif name=="anthropic":
            url=p["url"];body={"model":model,"max_tokens":4096,"messages":[{"role":"user","content":prompt}]}
            headers={"Content-Type":"application/json","x-api-key":key,"anthropic-version":"2023-06-01"}
        else:
            url=p["url"];body={"model":model,"messages":[{"role":"user","content":prompt}]}
            headers={"Content-Type":"application/json","Authorization":"Bearer "+key}
        req=urllib.request.Request(url,data=json.dumps(body).encode(),headers=headers)
        with urllib.request.urlopen(req,timeout=120) as r:data=json.loads(r.read().decode())
        if name=="gemini":return data["candidates"][0]["content"]["parts"][0]["text"]
        if name=="anthropic":return "".join(x.get("text","") for x in data.get("content",[]) if x.get("type")=="text")
        return data["choices"][0]["message"]["content"]

    def ask(self,provider,prompt):
        if provider=="ollama":return self.local(prompt,os.getenv("KRISHNA_LOCAL_MODEL","qwen2.5:3b"))
        if provider=="gpt4all":return self.gpt4all(prompt,os.getenv("KRISHNA_GPT4ALL_MODEL") or None)
        if provider.startswith("gateway:"):
            if not self.gateway:raise RuntimeError("encrypted model gateway is not configured")
            return self.gateway.complete(provider.split(":",1)[1],prompt)
        if provider in self.PROVIDERS:return self._chat_compatible(provider,prompt)
        raise KeyError(provider)

    def _governed_ask(self,provider,prompt,privacy="approved_cloud",free_only=False):
        if not self.control_plane:
            return self.ask(provider,prompt)
        receipt=self.control_plane.action(
            "model.complete",
            {"provider":provider,"prompt":prompt,"privacy":privacy,"free_only":bool(free_only)},
            project="KRISHNA",source="system",actor="model-router",
            permissions=("model.use",),
        )
        result=receipt.get("result") or {}
        return str(result.get("text") or "")

    def coding_plan(self,privacy="approved_cloud",free_only=False):
        available=[x for x in self.available() if x["available"]]
        if privacy in {"local_only","restricted"}:
            available=[x for x in available if x["local"]]
        elif free_only:
            available=[x for x in available if x["local"] or x.get("free_only")]
        preferred=["gpt4all","ollama"]
        if not free_only:
            preferred=["anthropic","openai","gemini","xai","openrouter","gpt4all","ollama"]
        available.sort(key=lambda x:preferred.index(x["provider"]) if x["provider"] in preferred else (20 if x["provider"].startswith("gateway:") else 99))
        roles=["implementation","architecture_review","bug_test_review","security_review"]
        return [{"role":role,"provider":available[i%len(available)]["provider"],"model":available[i%len(available)]["model"]} for i,role in enumerate(roles)] if available else []

    def route(self,prompt,privacy="approved_cloud",free_only=False):
        local_errors={}
        for name in ("ollama","gpt4all"):
            try:
                out=self._governed_ask(name,prompt,privacy,free_only)
                if str(out).strip():return {"provider":name,"text":out}
            except Exception as exc:
                local_errors[name]=f"{type(exc).__name__}: {exc}"
        if privacy in {"local_only","restricted"}:
            raise RuntimeError("local model unavailable; cloud fallback blocked by privacy policy: "+json.dumps(local_errors))
        if self.gateway:
            profiles=self.gateway.eligible(privacy,free_only=free_only)
            for row in profiles:
                try:return {"provider":"gateway:"+row.id,"text":self._governed_ask("gateway:"+row.id,prompt,privacy,free_only),"free_only":row.free_only}
                except Exception:
                    # Deliberately continue only to another eligible profile of the same policy.
                    continue
        if free_only:
            raise RuntimeError("free-only routing requested; no approved free-only local/gateway provider succeeded")
        for row in self.available():
            if row["available"] and not row["local"] and row["provider"] in self.PROVIDERS:
                try:return {"provider":row["provider"],"text":self._governed_ask(row["provider"],prompt,privacy,free_only)}
                except Exception:continue
        raise RuntimeError("no usable model provider")

    def auto(self,prompt):return self.route(prompt,"approved_cloud")
