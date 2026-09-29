from __future__ import annotations

import json
from typing import Any


class ManibhadraCloudAdvisor:
    """Dedicated zero-cost cloud reasoning lane for MANIBHADRA.

    It is intentionally separate from KRISHNA's conversational path. Only sanitized,
    non-sensitive CRM summaries may be sent. OpenRouter verified-free is primary;
    verified-free Cloudflare is the fallback. Paid providers are never used.
    """

    def __init__(self,openrouter_free,direct_free):
        self.openrouter_free=openrouter_free
        self.direct_free=direct_free

    def status(self)->dict[str,Any]:
        return {
            "component":"MANIBHADRA Cloud Advisor",
            "openrouter_free":bool(self.openrouter_free and self.openrouter_free.configured()),
            "direct_free":bool(self.direct_free and self.direct_free.configured()),
            "paid_fallback":False,
            "privacy":"approved public/non-sensitive business summaries only",
            "krishna_chat_path_used":False,
        }

    @staticmethod
    def _prompt(question:str,dashboard:dict[str,Any])->str:
        safe={
            "kpis":dashboard.get("kpis") or {},
            "attention":(dashboard.get("attention") or [])[:12],
            "pipeline":[
                {"stage":x.get("stage"),"count":x.get("count"),"value":x.get("value")}
                for x in (dashboard.get("pipeline") or [])
            ],
            "connections":dashboard.get("connections") or [],
            "counts":dashboard.get("counts") or {},
            "zero_spend":True,
        }
        return (
            "You are MANIBHADRA's bounded commerce advisor. The owner's hard rule is ZERO SPEND: "
            "receive money, never initiate payment, ads, subscriptions, inventory purchase, seller fee, "
            "paid API or paid lead. Recommend concrete next actions to increase revenue through organic, "
            "affiliate, referral, supplier-funded fulfillment, free marketplaces and free SEO. Never promise "
            "returns. Never claim an action was executed. Return concise JSON with keys summary, priorities, "
            "risks, opportunities, suggested_owner_decision.\nQuestion: "
            +str(question or "What should I do next?")[:2000]
            +"\nCRM summary: "+json.dumps(safe,ensure_ascii=False)
        )

    def advise(self,question:str,dashboard:dict[str,Any])->dict[str,Any]:
        prompt=self._prompt(question,dashboard)
        errors=[]
        if self.openrouter_free and self.openrouter_free.configured():
            try:
                result=self.openrouter_free.complete("reasoning",prompt,privacy="approved_cloud",sensitive=False,max_tokens=1800)
                return {
                    "provider":"openrouter-free",
                    "model":result.get("model"),
                    "text":result.get("text"),
                    "zero_cost_verified":bool(result.get("zero_cost_verified",True)),
                    "paid_fallback":False,
                }
            except Exception as exc:
                errors.append("openrouter-free: "+type(exc).__name__+": "+str(exc)[:500])
        if self.direct_free and self.direct_free.configured():
            try:
                result=self.direct_free.complete(prompt,privacy="approved_cloud",sensitive=False,max_tokens=1800)
                return {
                    "provider":result.get("provider") or "direct-free:cloudflare-workers-ai",
                    "model":result.get("model"),
                    "text":result.get("text"),
                    "zero_cost_verified":bool(result.get("zero_cost_verified")),
                    "paid_fallback":False,
                }
            except Exception as exc:
                errors.append("direct-free: "+type(exc).__name__+": "+str(exc)[:500])
        raise RuntimeError("MANIBHADRA free-cloud advisor unavailable: "+" | ".join(errors or ["no configured verified-free provider"]))
