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

    DEFAULT_LOCAL_MODEL="qwen3.5:4b"
    DEFAULT_LOCAL_FALLBACKS=("gemma3:4b","granite3.3:2b","smollm2:1.7b","llama3.2:1b","deepseek-r1:1.5b","qwen2.5:3b")
    DEFAULT_CODING_MODEL="qwen2.5-coder:7b"
    DEFAULT_CODING_FALLBACKS=("qwen3.5:4b","gemma3:4b","granite3.3:2b")
    DISABLED_LOCAL_MODEL_PREFIXES=()

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
        self.model_scout=None

    def bind_openrouter_free(self,fabric):
        self.openrouter_free=fabric
        return {"provider":"openrouter-free","bound":bool(fabric)}

    def bind_direct_free(self,fabric):
        self.direct_free=fabric
        return {"provider":"direct-free","bound":bool(fabric)}

    def bind_model_scout(self,scout):
        self.model_scout=scout
        return {"provider":"model-scout","bound":bool(scout)}

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

    @classmethod
    def local_model_allowed(cls,model):
        normalized=str(model or "").strip().lower().replace("\\","/")
        if not normalized:return False
        basename=normalized.rsplit("/",1)[-1]
        return not any(
            normalized.startswith(prefix) or basename.startswith(prefix)
            for prefix in cls.DISABLED_LOCAL_MODEL_PREFIXES
        )

    @staticmethod
    def normalize_task(task):
        value=str(task or "general").strip().lower().replace("-","_")
        if value in {"coding","code","implementation","implement","debug","debugging","repair","software_repair","bugfix","bug_fix"}:
            return "coding"
        if value in {"reasoning","analysis","architecture","architecture_review","security_review","review"}:
            return "reasoning"
        return "general"

    @classmethod
    def local_model_candidates(cls,task="general"):
        task=cls.normalize_task(task)
        if task=="coding":
            default_model=cls.DEFAULT_CODING_MODEL
            default_fallbacks=cls.DEFAULT_CODING_FALLBACKS
            primary=str(os.getenv("KRISHNA_CODING_MODEL",default_model) or default_model).strip()
            raw=str(os.getenv("KRISHNA_CODING_FALLBACK_MODELS",",".join(default_fallbacks)) or "")
        else:
            default_model=cls.DEFAULT_LOCAL_MODEL
            default_fallbacks=cls.DEFAULT_LOCAL_FALLBACKS
            primary=str(os.getenv("KRISHNA_LOCAL_MODEL",default_model) or default_model).strip()
            raw=str(os.getenv("KRISHNA_LOCAL_FALLBACK_MODELS",",".join(default_fallbacks)) or "")
        out=[]
        for model in [primary,*raw.split(","),default_model,*default_fallbacks]:
            model=str(model or "").strip()
            if model and cls.local_model_allowed(model) and model not in out:out.append(model)
        return out

    @staticmethod
    def _ollama_model_names(data):
        return {
            str(x.get("name") or x.get("model") or "").strip().lower()
            for x in ((data or {}).get("models") or [])
            if str(x.get("name") or x.get("model") or "").strip()
        }

    def local_model_status(self,task="general"):
        task=self.normalize_task(task)
        ok,data=self._probe_json(settings.ollama_url.rstrip("/")+"/api/tags")
        candidates=self.local_model_candidates(task)
        installed=self._ollama_model_names(data) if ok else set()
        selected=next((m for m in candidates if m.lower() in installed or (m.lower()+":latest") in installed),None)
        default_model=self.DEFAULT_CODING_MODEL if task=="coding" else self.DEFAULT_LOCAL_MODEL
        return {
            "provider":"ollama",
            "task":task,
            "available":bool(ok and selected),
            "service_available":bool(ok),
            "primary_model":candidates[0] if candidates else default_model,
            "fallback_models":candidates[1:],
            "selected_model":selected,
            "installed_candidates":[m for m in candidates if m.lower() in installed or (m.lower()+":latest") in installed],
            "error":None if ok else (data or {}).get("error"),
        }

    def role_status(self):
        return {
            "authority":"KRISHNA_PC",
            "pc":{
                "general":self.local_model_status("general"),
                "coding":self.local_model_status("coding"),
            },
            "cloud":{
                "automatic_paid_fallback":False,
                "general":["openrouter-free:general","direct-free:cloudflare-workers-ai"],
                "coding":["openrouter-free:coding","direct-free:cloudflare-workers-ai"],
                "reasoning":["openrouter-free:reasoning","direct-free:cloudflare-workers-ai"],
                "policy":"cloud only after local failure and only for approved non-sensitive work; automatic paid fallback remains disabled",
            },
            "mobile":{
                "qwen_runtime":False,
                "local_perception":"ML Kit + MediaPipe",
                "heavy_private_inference":"KRISHNA PC",
                "approved_cloud":"HAWKEYE Free Cloud Fabric",
            },
        }

    def _ollama_generate(self,model,prompt):
        body=json.dumps({"model":model,"prompt":prompt,"stream":False}).encode()
        req=urllib.request.Request(settings.ollama_url.rstrip("/")+"/api/generate",data=body,headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=90) as r:return json.loads(r.read().decode()).get("response","")

    def local(self,prompt,model=None,task="general"):
        if model:
            model=str(model).strip()
            if not self.local_model_allowed(model):
                raise RuntimeError("local model disabled by owner policy: "+model)
            return self._ollama_generate(model,prompt)
        status=self.local_model_status(task)
        ordered=[status.get("selected_model"),*self.local_model_candidates(task)]
        candidates=[]
        for candidate in ordered:
            candidate=str(candidate or "").strip()
            if candidate and candidate not in candidates:candidates.append(candidate)
        errors={}
        for candidate in candidates:
            try:
                out=self._ollama_generate(candidate,prompt)
                if str(out).strip():return out
                errors[candidate]="empty response"
            except Exception as exc:
                errors[candidate]=f"{type(exc).__name__}: {exc}"
        raise RuntimeError("no preferred KRISHNA Ollama model succeeded: "+json.dumps({
            **status,"attempted_models":candidates,"attempt_errors":errors,
        }))

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
        candidates=self.local_model_candidates()
        installed=self._ollama_model_names(ollama_data) if ollama_ok else set()
        selected=next((m for m in candidates if m.lower() in installed or (m.lower()+":latest") in installed),None)
        out=[
          {"provider":"ollama","available":bool(ollama_ok and selected),"local":True,
           "model":selected or (candidates[0] if candidates else self.DEFAULT_LOCAL_MODEL),
           "primary_model":candidates[0] if candidates else self.DEFAULT_LOCAL_MODEL,
           "fallback_models":candidates[1:],
           "installed_candidates":[m for m in candidates if m.lower() in installed or (m.lower()+":latest") in installed],
           "credential_source":"none","error":None if ollama_ok else ollama_data.get("error")},
          {"provider":"gpt4all","available":gpt_ok,"local":True,"model":os.getenv("KRISHNA_GPT4ALL_MODEL","auto"),"credential_source":"none","error":None if gpt_ok else gpt_data.get("error")},
        ]
        if self.model_scout and ollama_ok:
            for row in self.model_scout.routing_candidates("general",limit=20):
                model=str(row.get("model_id") or "").strip()
                if not model or not self.local_model_allowed(model):continue
                model_key=model.lower()
                installed_now=model_key in installed or (model_key+":latest") in installed
                row_task=str(row.get("task") or "general").strip().lower()
                out.append({
                    "provider":"ollama-model:"+model,
                    "available":installed_now,
                    "local":True,
                    "model":model,
                    "credential_source":"none",
                    "free_only":True,
                    "scout_routing_enabled":True,
                    "task":row.get("task"),
                    "pc_routing_eligible":row_task!="local_mobile_reasoner",
                    "benchmark_ref":row.get("benchmark_ref"),
                    "error":None if installed_now else "routing-enabled candidate is not installed in Ollama",
                })
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
        if provider=="ollama":return self.local(prompt)
        if provider.startswith("ollama-model:"):
            model=provider.split(":",1)[1].strip()
            if not model:raise ValueError("Ollama candidate model is required")
            return self.local(prompt,model)
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

    def _governed_complete(self,provider,prompt,privacy="approved_cloud",free_only=False,project="KRISHNA",actor="model-router"):
        if not self.control_plane:
            return {"provider":provider,"text":self.ask(provider,prompt)}
        receipt=self.control_plane.action(
            "model.complete",
            {"provider":provider,"prompt":prompt,"privacy":privacy,"free_only":bool(free_only)},
            project=str(project or "KRISHNA"),source="system",actor=str(actor or "model-router"),
            permissions=("model.use",),
        )
        result=receipt.get("result") or {}
        if not isinstance(result,dict):
            raise RuntimeError("governed model completion returned an invalid result")
        return result

    def _governed_ask(self,provider,prompt,privacy="approved_cloud",free_only=False,project="KRISHNA",actor="model-router"):
        result=self._governed_complete(provider,prompt,privacy,free_only,project,actor)
        return str(result.get("text") or "")

    def coding_plan(self,privacy="approved_cloud",free_only=False):
        available=[
            x for x in self.available()
            if x["available"] and x.get("pc_routing_eligible",True)
        ]
        cloud_allowed=privacy not in {"local_only","restricted"}
        if privacy in {"local_only","restricted"}:
            available=[x for x in available if x["local"]]
        elif free_only or not self.paid_cloud_enabled():
            available=[
                x for x in available
                if x["local"] or x["provider"]=="openrouter-free"
                or x["provider"]=="direct-free:cloudflare-workers-ai"
            ]

        def local_role(status,role):
            model=str((status or {}).get("selected_model") or "").strip()
            if not model:return None
            return {
                "role":role,"provider":"ollama-model:"+model,"model":model,
                "local":True,"free_only":True,
            }

        def provider_role(provider,role):
            row=next((x for x in available if x.get("provider")==provider and x.get("available")),None)
            if not row:return None
            return {
                "role":role,"provider":provider,"model":row.get("model"),
                "local":bool(row.get("local",False)),"free_only":bool(row.get("free_only",False)),
            }

        general=local_role(self.local_model_status("general"),"architecture_review")
        coding=local_role(self.local_model_status("coding"),"implementation")
        if coding is None:
            coding=local_role(self.local_model_status("general"),"implementation")
        if general is None:
            first_local=next((x for x in available if x.get("local")),None)
            if first_local:
                general={
                    "role":"architecture_review","provider":first_local["provider"],
                    "model":first_local.get("model"),"local":True,
                    "free_only":bool(first_local.get("free_only",True)),
                }
        if coding is None and general is not None:
            coding={**general,"role":"implementation"}

        openrouter=provider_role("openrouter-free","bug_test_review") if cloud_allowed else None
        cloudflare=provider_role("direct-free:cloudflare-workers-ai","security_review") if cloud_allowed else None
        bug=openrouter or ({**coding,"role":"bug_test_review"} if coding else None)
        security=cloudflare or (
            {**openrouter,"role":"security_review"} if openrouter
            else ({**general,"role":"security_review"} if general else None)
        )
        plan=[x for x in (coding,general,bug,security) if x]
        return plan

    def route(self,prompt,privacy="approved_cloud",free_only=False,project="KRISHNA",actor="model-router",task="general"):
        local_errors={}
        task_name=self.normalize_task(task)
        if self.model_scout:
            for row in self.model_scout.routing_candidates(task,limit=5):
                model=str(row.get("model_id") or "").strip()
                if not model or not self.local_model_allowed(model):continue
                row_task=str(row.get("task") or "general").strip().lower()
                if str(task or "general").strip().lower() in {"","general"} and row_task=="local_mobile_reasoner":
                    continue
                provider="ollama-model:"+model
                try:
                    out=self._governed_ask(provider,prompt,privacy,free_only,project,actor)
                    if str(out).strip():
                        return {
                            "provider":provider,"model":model,"text":out,"model_scout":True,
                            "authority":"worker-model-only","untrusted_output":True,
                        }
                except Exception as exc:
                    local_errors[provider]=f"{type(exc).__name__}: {exc}"
        if task_name=="coding":
            for model in self.local_model_candidates("coding"):
                provider="ollama-model:"+model
                if provider in local_errors:continue
                try:
                    out=self._governed_ask(provider,prompt,privacy,free_only,project,actor)
                    if str(out).strip():
                        return {"provider":provider,"model":model,"text":out,"task":"coding"}
                except Exception as exc:
                    local_errors[provider]=f"{type(exc).__name__}: {exc}"
        for name in ("ollama","gpt4all"):
            try:
                out=self._governed_ask(name,prompt,privacy,free_only,project,actor)
                if str(out).strip():return {"provider":name,"text":out,"task":task_name}
            except Exception as exc:
                local_errors[name]=f"{type(exc).__name__}: {exc}"
        if privacy in {"local_only","restricted"}:
            raise RuntimeError("local model unavailable; cloud fallback blocked by privacy policy: "+json.dumps(local_errors))

        # First cloud fallback is the live-catalog verified zero-cost OpenRouter
        # fabric. It refuses a request if pricing is no longer zero.
        if self.openrouter_free and self.openrouter_free.configured():
            try:
                cloud_role="coding" if task_name=="coding" else ("reasoning" if task_name=="reasoning" else "general")
                provider="openrouter-free:"+cloud_role
                text=self._governed_ask(provider,prompt,privacy,True,project,actor)
                if str(text).strip():return {"provider":provider,"text":text,"free_only":True,"zero_cost_verified":True}
            except Exception:
                pass

        # Next fallback is a native direct provider only when its adapter can prove
        # the configured account is currently non-billable. Cloudflare Workers AI
        # performs a fresh Billing Read subscription preflight before every call.
        if self.direct_free and self.direct_free.configured():
            try:
                provider="direct-free:cloudflare-workers-ai"
                result=self._governed_complete(provider,prompt,privacy,True,project,actor)
                text=str(result.get("text") or "")
                if text.strip():
                    return {"provider":result.get("provider") or provider,
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
