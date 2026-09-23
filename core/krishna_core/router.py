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
        self.openrouter_free=None
        self.direct_free=None

    def bind_openrouter_free(self,fabric):
        self.openrouter_free=fabric
        return {"provider":"openrouter-free","bound":bool(fabric)}

    def bind_direct_free(self,fabric):
        self.direct_free=fabric
        return {"provider":"direct-free","bound":bool(fabric)}

    @staticmethod
    def paid_cloud_enabled():
        return str(os.getenv("KRISHNA_ALLOW_PAID_CLOUD","0")).strip().lower() in {"1","true","yes","on"}

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
        if self.openrouter_free:
            try:
                status=self.openrouter_free.status(refresh=False)
                out.append({
                    "provider":"openrouter-free","name":"OpenRouter Zero-Cost Fabric",
                    "available":bool(status.get("configured")),"local":False,
                    "model":"dynamic-live-zero-cost","credential_source":"windows-dpapi",
                    "free_only":True,"zero_cost_verified":"live-catalog-preflight",
                })
            except Exception as exc:
                out.append({"provider":"openrouter-free","name":"OpenRouter Zero-Cost Fabric","available":False,
                            "local":False,"model":"dynamic-live-zero-cost","credential_source":"windows-dpapi",
                            "free_only":True,"error":f"{type(exc).__name__}: {exc}"})
        if self.direct_free:
            try:
                status=self.direct_free.status(refresh=False)
                out.append({
                    "provider":status.get("provider_id") or "direct-free",
                    "name":"Verified Direct Free Cloud",
                    "available":bool(status.get("configured")),"local":False,
                    "model":"configured-live-zero-billing","credential_source":"windows-dpapi",
                    "free_only":True,"zero_cost_verified":"live-billing-preflight",
                    "automatic_zero_cost_eligible":bool(status.get("automatic_zero_cost_eligible")),
                })
            except Exception as exc:
                out.append({"provider":"direct-free:cloudflare-workers-ai","name":"Verified Direct Free Cloud",
                            "available":False,"local":False,"model":"configured-live-zero-billing",
                            "credential_source":"windows-dpapi","free_only":True,
                            "error":f"{type(exc).__name__}: {exc}"})
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
        if provider=="openrouter-free" or provider.startswith("openrouter-free:"):
            if not self.openrouter_free:raise RuntimeError("OpenRouter zero-cost fabric is not configured")
            role=provider.split(":",1)[1] if ":" in provider else "general"
            return self.openrouter_free.complete(role,prompt,privacy="approved_cloud")["text"]
        if provider=="direct-free" or provider=="direct-free:cloudflare-workers-ai":
            if not self.direct_free:raise RuntimeError("verified direct-free fabric is not configured")
            return self.direct_free.complete(prompt,privacy="approved_cloud")["text"]
        if provider.startswith("gateway:"):
            if not self.gateway:raise RuntimeError("encrypted model gateway is not configured")
            return self.gateway.complete(provider.split(":",1)[1],prompt)
        if provider in self.PROVIDERS:return self._chat_compatible(provider,prompt)
        raise KeyError(provider)

    def _governed_ask(self,provider,prompt,privacy="approved_cloud",free_only=False,project="KRISHNA",actor="model-router"):
        if not self.control_plane:
            return self.ask(provider,prompt)
        receipt=self.control_plane.action(
            "model.complete",
            {"provider":provider,"prompt":prompt,"privacy":privacy,"free_only":bool(free_only)},
            project=str(project or "KRISHNA"),source="system",actor=str(actor or "model-router"),
            permissions=("model.use",),
        )
        result=receipt.get("result") or {}
        return str(result.get("text") or "")

    def coding_plan(self,privacy="approved_cloud",free_only=False):
        available=[x for x in self.available() if x["available"]]
        if privacy in {"local_only","restricted"}:
            available=[x for x in available if x["local"]]
        else:
            if free_only or not self.paid_cloud_enabled():
                # Automatic zero-cost planning trusts only local inference, the
                # live-catalog verified OpenRouter fabric, and native direct adapters
                # that perform their own live zero-billing preflight. A profile merely
                # labelled free_only (Gemini/Groq/etc.) is not a billing guarantee.
                available=[x for x in available if x["local"] or x["provider"]=="openrouter-free"
                           or x["provider"]=="direct-free:cloudflare-workers-ai"]
        # Local models remain first. Free cloud can provide an independent reviewer
        # when available, while paid providers are opt-in only.
        def rank(row):
            if row.get("local"):
                return 0 if row["provider"]=="ollama" else 1
            if row["provider"]=="openrouter-free":
                return 2
            if row["provider"]=="direct-free:cloudflare-workers-ai":
                return 3
            if row.get("free_only"):
                return 4
            return 20
        available.sort(key=rank)
        roles=["implementation","architecture_review","bug_test_review","security_review"]
        return [{"role":role,"provider":available[i%len(available)]["provider"],"model":available[i%len(available)]["model"]} for i,role in enumerate(roles)] if available else []

    def route(self,prompt,privacy="approved_cloud",free_only=False,project="KRISHNA",actor="model-router"):
        local_errors={}
        for name in ("ollama","gpt4all"):
            try:
                out=self._governed_ask(name,prompt,privacy,free_only,project,actor)
                if str(out).strip():return {"provider":name,"text":out}
            except Exception as exc:
                local_errors[name]=f"{type(exc).__name__}: {exc}"
        if privacy in {"local_only","restricted"}:
            raise RuntimeError("local model unavailable; cloud fallback blocked by privacy policy: "+json.dumps(local_errors))

        # First cloud fallback is the live-catalog verified zero-cost OpenRouter
        # fabric. It refuses a request if pricing is no longer zero.
        if self.openrouter_free and self.openrouter_free.configured():
            try:
                provider="openrouter-free:general"
                text=self._governed_ask(provider,prompt,privacy,True,project,actor)
                if str(text).strip():return {"provider":provider,"text":text,"free_only":True,"zero_cost_verified":True}
            except Exception:
                pass

        # Next fallback is a native direct provider only when its adapter can prove
        # the configured account is currently non-billable. Cloudflare Workers AI
        # performs a fresh Billing Read subscription preflight before every call.
        if self.direct_free and self.direct_free.configured():
            try:
                result=self.direct_free.complete(prompt,privacy=privacy)
                text=str(result.get("text") or "")
                if text.strip():
                    return {"provider":result.get("provider_id") or "direct-free:cloudflare-workers-ai",
                            "text":text,"free_only":True,"zero_cost_verified":True,
                            "zero_cost_proof":result.get("zero_cost_proof")}
            except Exception:
                pass

        # Other direct gateway profiles labelled free_only may still be invoked
        # explicitly by the owner, but they are not automatic fallbacks because
        # KRISHNA cannot independently prove their account billing state.
        if free_only or not self.paid_cloud_enabled():
            raise RuntimeError("no live-verified zero-cost provider succeeded; declared-free/paid cloud auto-fallback is disabled")

        # Paid cloud is never a silent fallback. It must be explicitly enabled by
        # KRISHNA_ALLOW_PAID_CLOUD=1.
        if self.gateway:
            for row in self.gateway.eligible(privacy,free_only=False):
                if row.free_only:continue
                try:return {"provider":"gateway:"+row.id,"text":self._governed_ask("gateway:"+row.id,prompt,privacy,False,project,actor),"free_only":False}
                except Exception:continue
        for row in self.available():
            if row["available"] and not row["local"] and row["provider"] in self.PROVIDERS:
                try:return {"provider":row["provider"],"text":self._governed_ask(row["provider"],prompt,privacy,False,project,actor)}
                except Exception:continue
        raise RuntimeError("no usable model provider")

    def auto(self,prompt,project="KRISHNA"):return self.route(prompt,"approved_cloud",project=project)
