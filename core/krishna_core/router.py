from __future__ import annotations

import json
import os
import urllib.request

from .config import settings
from .model_gateway import ModelGatewayRegistry


class ModelRouter:
    """Privacy-aware, role-aware model pool.

    Automatic routing trusts only local inference plus cloud adapters that can
    independently prove zero-cost eligibility at execution time. Generic gateway
    profiles marked free_only remain explicit/manual because that label alone does
    not prove the external account is non-billable.
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
        self.role_policy=None

    def bind_openrouter_free(self,fabric):
        self.openrouter_free=fabric
        return {"provider":"openrouter-free","bound":bool(fabric)}

    def bind_direct_free(self,fabric):
        self.direct_free=fabric
        return {"provider":"direct-free","bound":bool(fabric)}

    def bind_role_policy(self,policy):
        self.role_policy=policy
        return {"policy":"ai-role-policy","bound":bool(policy)}

    @staticmethod
    def paid_cloud_enabled():
        return str(os.getenv("KRISHNA_ALLOW_PAID_CLOUD","0")).strip().lower() in {"1","true","yes","on"}

    def bind_sudarshan(self,control_plane):
        self.control_plane=control_plane
        return {"authority":"Sudarshan Control Plane","bound":True}

    def role_assignment(self,role="general"):
        if self.role_policy:
            return self.role_policy.get(role)
        role=str(role or "general").strip().lower()
        openrouter_role={
            "coding":"coding","implementation":"coding","bug_test_review":"coding",
            "reasoning":"reasoning","research":"reasoning","architecture_review":"reasoning",
            "security_review":"reasoning","vision":"vision","medical_research":"medical",
            "rishi_research":"reasoning","rishi_counter_evidence":"reasoning",
            "rishi_debate":"reasoning","gautama_review":"reasoning",
            "bharadvaja_test_plan":"reasoning","lab_hypothesis":"reasoning",
            "lab_result_analysis":"reasoning","vyasa_synthesis":"reasoning",
        }.get(role,"general")
        strategy="verified_cloud_first" if role in {
            "architecture_review","bug_test_review","security_review",
            "rishi_counter_evidence","rishi_debate","gautama_review",
            "bharadvaja_test_plan","lab_result_analysis","vyasa_synthesis",
        } else "local_first"
        return {"role":role,"mode":"auto","provider":None,"model":None,
                "openrouter_role":openrouter_role,"auto_strategy":strategy}

    def _role_target_provider(self,role,provider):
        provider=str(provider or "").strip()
        if provider=="openrouter-free":
            return "openrouter-free:"+str(self.role_assignment(role).get("openrouter_role") or "general")
        if provider=="direct-free":
            return "direct-free:cloudflare-workers-ai"
        return provider

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
          {"provider":"ollama","available":ollama_ok,"local":True,"model":os.getenv("KRISHNA_LOCAL_MODEL","qwen2.5:3b"),"credential_source":"none","error":None if ollama_ok else ollama_data.get("error"),"free_only":True},
          {"provider":"gpt4all","available":gpt_ok,"local":True,"model":os.getenv("KRISHNA_GPT4ALL_MODEL","auto"),"credential_source":"none","error":None if gpt_ok else gpt_data.get("error"),"free_only":True},
        ]
        for name,p in self.PROVIDERS.items():
            out.append({"provider":name,"available":bool(os.getenv(p["key"])),"local":False,
                        "model":os.getenv(p["model"],p["default"]),"credential_source":"environment","free_only":False})
        if self.gateway:
            for row in self.gateway.list()["profiles"]:
                out.append({"provider":"gateway:"+row["id"],"name":row["name"],"available":bool(row["enabled"] and row["credential_available"]),
                            "local":False,"model":row["model"],"credential_source":"windows-dpapi","free_only":row["free_only"],
                            "automatic_zero_cost_eligible":False,
                            "automatic_policy":"manual profile label is not live billing proof"})
        if self.openrouter_free:
            try:
                status=self.openrouter_free.status(refresh=False)
                out.append({
                    "provider":"openrouter-free","name":"OpenRouter Zero-Cost Fabric",
                    "available":bool(status.get("configured")),"local":False,
                    "model":"dynamic-live-zero-cost","credential_source":"windows-dpapi",
                    "free_only":True,"zero_cost_verified":"live-catalog-preflight",
                    "automatic_zero_cost_eligible":True,
                })
            except Exception as exc:
                out.append({"provider":"openrouter-free","name":"OpenRouter Zero-Cost Fabric","available":False,
                            "local":False,"model":"dynamic-live-zero-cost","credential_source":"windows-dpapi",
                            "free_only":True,"automatic_zero_cost_eligible":True,
                            "error":f"{type(exc).__name__}: {exc}"})
        if self.direct_free:
            try:
                status=self.direct_free.status(refresh=False)
                out.append({
                    "provider":status.get("provider_id") or "direct-free",
                    "name":"Verified Direct Free Cloud",
                    "available":bool(status.get("configured")),"local":False,
                    "model":"configured-live-zero-billing","credential_source":"windows-dpapi",
                    "free_only":True,"zero_cost_verified":"live-billing-preflight",
                    # Native direct-free adapters are eligible to be attempted when
                    # configured because complete() performs the live billing preflight
                    # immediately before inference. This is eligibility-to-verify, not
                    # a claim that the account was already verified in this status call.
                    "automatic_zero_cost_eligible":bool(status.get("configured")),
                    "zero_cost_verification_state":(
                        "recently-verified" if status.get("automatic_zero_cost_eligible")
                        else "verify-before-call"
                    ),
                })
            except Exception as exc:
                out.append({"provider":"direct-free:cloudflare-workers-ai","name":"Verified Direct Free Cloud",
                            "available":False,"local":False,"model":"configured-live-zero-billing",
                            "credential_source":"windows-dpapi","free_only":True,
                            "automatic_zero_cost_eligible":False,
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

    def ask(self,provider,prompt,model=None,privacy="approved_cloud"):
        if provider=="ollama":return self.local(prompt,model or os.getenv("KRISHNA_LOCAL_MODEL","qwen2.5:3b"))
        if provider=="gpt4all":return self.gpt4all(prompt,model or os.getenv("KRISHNA_GPT4ALL_MODEL") or None)
        if provider=="openrouter-free" or provider.startswith("openrouter-free:"):
            if not self.openrouter_free:raise RuntimeError("OpenRouter zero-cost fabric is not configured")
            role=provider.split(":",1)[1] if ":" in provider else "general"
            return self.openrouter_free.complete(role,prompt,privacy=privacy)["text"]
        if provider=="direct-free" or provider=="direct-free:cloudflare-workers-ai":
            if not self.direct_free:raise RuntimeError("verified direct-free fabric is not configured")
            return self.direct_free.complete(prompt,privacy=privacy)["text"]
        if provider.startswith("gateway:"):
            if not self.gateway:raise RuntimeError("encrypted model gateway is not configured")
            return self.gateway.complete(provider.split(":",1)[1],prompt)
        if provider in self.PROVIDERS:return self._chat_compatible(provider,prompt)
        raise KeyError(provider)

    def _governed_ask(self,provider,prompt,privacy="approved_cloud",free_only=False,project="KRISHNA",actor="model-router",model=None):
        if not self.control_plane:
            return self.ask(provider,prompt,model=model,privacy=privacy)
        receipt=self.control_plane.action(
            "model.complete",
            {"provider":provider,"prompt":prompt,"privacy":privacy,"free_only":bool(free_only),"model":model},
            project=str(project or "KRISHNA"),source="system",actor=str(actor or "model-router"),
            permissions=("model.use",),
        )
        result=receipt.get("result") or {}
        return str(result.get("text") or "")

    def _automatic_candidates(self,privacy="approved_cloud",free_only=False,role="general",available_rows=None):
        source=self.available() if available_rows is None else available_rows
        rows=[x for x in source if x.get("available")]
        locals_=[dict(x) for x in rows if x.get("local")]
        if privacy in {"local_only","restricted"}:
            return locals_
        cloud=[]
        assignment=self.role_assignment(role)
        openrouter_role=str(assignment.get("openrouter_role") or "general")
        for row in rows:
            provider=row.get("provider")
            if provider=="openrouter-free":
                item=dict(row);item["provider"]="openrouter-free:"+openrouter_role
                cloud.append(item)
            elif provider=="direct-free:cloudflare-workers-ai" and row.get("automatic_zero_cost_eligible",True):
                cloud.append(dict(row))
        strategy=str(assignment.get("auto_strategy") or "local_first")
        if strategy=="verified_cloud_first":
            return cloud+locals_
        return locals_+cloud

    def _role_selected_row(self,role,privacy="approved_cloud",free_only=False,available_rows=None):
        assignment=self.role_assignment(role)
        provider=self._role_target_provider(role,assignment.get("provider"))
        if assignment.get("mode")=="auto" or not provider:
            return None
        base_provider="openrouter-free" if provider.startswith("openrouter-free:") else provider
        source=self.available() if available_rows is None else available_rows
        rows={x.get("provider"):x for x in source}
        row=rows.get(base_provider)
        if not row or not row.get("available"):
            raise RuntimeError(f"AI role {role} selected provider is unavailable: {provider}")
        if privacy in {"local_only","restricted"} and not row.get("local"):
            raise PermissionError(f"AI role {role} cloud provider is blocked by project privacy")
        verified=bool(row.get("local") or base_provider=="openrouter-free"
                      or (base_provider=="direct-free:cloudflare-workers-ai" and row.get("automatic_zero_cost_eligible")))
        if not verified and not self.paid_cloud_enabled():
            raise PermissionError(
                f"AI role {role} selected provider lacks live zero-billing proof; "
                "generic free_only profiles remain manual-only while paid cloud is disabled"
            )
        if free_only and not verified:
            raise PermissionError(f"AI role {role} provider is outside verified zero-cost routing")
        selected=dict(row)
        selected["provider"]=provider
        if assignment.get("model"):
            selected["model"]=assignment["model"]
        selected["role_mode"]=assignment.get("mode")
        selected["zero_cost_verified"]=verified
        return selected

    def role_plan(self,role,privacy="approved_cloud",free_only=False,available_rows=None):
        assignment=self.role_assignment(role)
        selected=None
        try:
            selected=self._role_selected_row(role,privacy,free_only,available_rows)
        except Exception:
            if assignment.get("mode")=="pin":
                raise
        if selected and assignment.get("mode")=="pin":
            return [selected]
        candidates=self._automatic_candidates(privacy,free_only,role,available_rows)
        if selected:
            key=(selected.get("provider"),selected.get("model"))
            candidates=[x for x in candidates if (x.get("provider"),x.get("model"))!=key]
            candidates.insert(0,selected)
        return candidates

    def coding_plan(self,privacy="approved_cloud",free_only=False,available_rows=None):
        roles=["implementation","architecture_review","bug_test_review","security_review"]
        snapshot=self.available() if available_rows is None else available_rows
        plan=[]
        for index,role in enumerate(roles):
            rows=self.role_plan(role,privacy,free_only,snapshot)
            if not rows:continue
            assignment=self.role_assignment(role)
            row=rows[index % len(rows)] if assignment.get("mode")=="auto" else rows[0]
            route_provider=row["provider"]
            public_provider="openrouter-free" if route_provider.startswith("openrouter-free:") else route_provider
            plan.append({"role":role,"provider":public_provider,"route_provider":route_provider,
                         "model":row.get("model"),"mode":assignment.get("mode","auto")})
        return plan

    def research_plan(self,privacy="approved_cloud",free_only=True,available_rows=None):
        roles=[
            "rishi_research","rishi_counter_evidence","rishi_debate","gautama_review",
            "bharadvaja_test_plan","lab_hypothesis","lab_result_analysis","vyasa_synthesis",
        ]
        snapshot=self.available() if available_rows is None else available_rows
        out=[]
        for role in roles:
            rows=self.role_plan(role,privacy,free_only,snapshot)
            first=rows[0] if rows else None
            out.append({
                "role":role,
                "mode":self.role_assignment(role).get("mode","auto"),
                "strategy":self.role_assignment(role).get("auto_strategy","local_first"),
                "provider":None if not first else first.get("provider"),
                "model":None if not first else first.get("model"),
                "available":bool(first),
            })
        return out

    def _run_candidate(self,row,prompt,privacy,free_only,project,actor):
        provider=row["provider"]
        verified=bool(row.get("local") or provider.startswith("openrouter-free:")
                      or provider=="direct-free:cloudflare-workers-ai")
        text=self._governed_ask(
            provider,prompt,privacy,bool(free_only or verified),project,actor,
            model=row.get("model") if row.get("local") else None,
        )
        if not str(text).strip():
            raise RuntimeError("model returned an empty response")
        result={"provider":provider,"text":str(text)}
        if row.get("model"):result["model"]=row.get("model")
        if verified and not row.get("local"):
            result.update({"free_only":True,"zero_cost_verified":True})
        return result

    def route(self,prompt,privacy="approved_cloud",free_only=False,project="KRISHNA",actor="model-router",role="general"):
        role=str(role or "general").strip().lower()
        assignment=self.role_assignment(role)
        errors={}

        if assignment.get("mode") in {"prefer","pin"}:
            try:
                row=self._role_selected_row(role,privacy,free_only)
                result=self._run_candidate(row,prompt,privacy,free_only,project,actor)
                if not (role=="general" and assignment.get("mode")=="auto"):
                    result.update({"role":role,"role_mode":assignment.get("mode")})
                return result
            except Exception as exc:
                errors["selected"]=f"{type(exc).__name__}: {exc}"
                if assignment.get("mode")=="pin":
                    raise RuntimeError(
                        f"AI role {role} is pinned and the selected provider could not run: {errors['selected']}"
                    ) from exc

        candidates=self._automatic_candidates(privacy,free_only,role)
        for row in candidates:
            try:
                result=self._run_candidate(row,prompt,privacy,free_only,project,actor)
                if role=="general" and assignment.get("mode","auto")=="auto":
                    return {k:v for k,v in result.items() if k not in {"model"} or row.get("local") is False}
                result.update({"role":role,"role_mode":assignment.get("mode","auto")})
                return result
            except Exception as exc:
                errors[row.get("provider") or "unknown"]=f"{type(exc).__name__}: {exc}"

        if privacy in {"local_only","restricted"}:
            raise RuntimeError("local model unavailable; cloud fallback blocked by privacy policy: "+json.dumps(errors))

        if free_only or not self.paid_cloud_enabled():
            raise RuntimeError("no live-verified zero-cost provider succeeded; declared-free/paid cloud auto-fallback is disabled")

        # Paid/manual cloud can only be reached after the global owner opt-in.
        if self.gateway:
            for row in self.gateway.eligible(privacy,free_only=False):
                if row.free_only:continue
                try:
                    provider="gateway:"+row.id
                    text=self._governed_ask(provider,prompt,privacy,False,project,actor)
                    if str(text).strip():
                        return {"provider":provider,"role":role,"text":text,"free_only":False}
                except Exception:continue
        for row in self.available():
            if row["available"] and not row["local"] and row["provider"] in self.PROVIDERS:
                try:
                    text=self._governed_ask(row["provider"],prompt,privacy,False,project,actor)
                    if str(text).strip():
                        return {"provider":row["provider"],"role":role,"text":text,"free_only":False}
                except Exception:continue
        raise RuntimeError("no usable model provider")

    def independent_review_pair(self,prompt,privacy="approved_cloud",project="KRISHNA",
                                actor="independent-review",role="lab_result_analysis"):
        """Return independent local + verified-free-cloud reviews when policy allows.

        This never treats agreement as proof. It exists to reduce single-model
        dependence before evidence is interpreted or promoted.
        """
        errors={}
        local_result=None
        cloud_result=None
        snapshot=self.available()
        local_rows=[x for x in snapshot if x.get("available") and x.get("local")]
        for row in local_rows:
            try:
                local_result=self._run_candidate(row,prompt,"local_only",True,project,actor+"-local")
                break
            except Exception as exc:
                errors["local:"+str(row.get("provider"))]=f"{type(exc).__name__}: {exc}"

        if privacy not in {"local_only","restricted"}:
            assignment=self.role_assignment(role)
            openrouter_role=str(assignment.get("openrouter_role") or "reasoning")
            cloud_candidates=[]
            rows={x.get("provider"):x for x in snapshot if x.get("available")}
            if "openrouter-free" in rows:
                item=dict(rows["openrouter-free"]);item["provider"]="openrouter-free:"+openrouter_role
                cloud_candidates.append(item)
            direct=rows.get("direct-free:cloudflare-workers-ai")
            if direct and direct.get("automatic_zero_cost_eligible",True):
                cloud_candidates.append(dict(direct))
            for row in cloud_candidates:
                try:
                    cloud_result=self._run_candidate(row,prompt,privacy,True,project,actor+"-cloud")
                    break
                except Exception as exc:
                    errors["cloud:"+str(row.get("provider"))]=f"{type(exc).__name__}: {exc}"

        if not local_result and not cloud_result:
            raise RuntimeError("no independent review model succeeded: "+json.dumps(errors))
        return {
            "role":role,
            "local_review":local_result,
            "independent_cloud_review":cloud_result,
            "independent_pair":bool(local_result and cloud_result),
            "privacy":privacy,
            "errors":errors,
            "policy":"model agreement is not evidence; experiment/source evidence remains authoritative",
        }

    def auto(self,prompt,project="KRISHNA",role="general"):
        return self.route(prompt,"approved_cloud",project=project,role=role)
