"""KRISHNA Unified Model Mesh: local-first, zero-cost, capability/load aware."""
from __future__ import annotations
from dataclasses import dataclass, field
import time
from .model_scout import ZeroCostPolicy
from .cloud_providers import CloudRequest, QuotaExhausted

@dataclass
class Worker:
    name:str
    provider:object
    model:str
    capabilities:set[str]=field(default_factory=lambda:{"general"})
    local:bool=False
    confirmed_free:bool=False
    priority:float=1.0
    inflight:int=0
    failures:int=0
    latency_ms:float=0.0

class UnifiedModelMesh:
    def __init__(self,zero_cost:ZeroCostPolicy|None=None):
        self.zero_cost=zero_cost or ZeroCostPolicy(); self.workers:dict[str,Worker]={}
    def add(self,w:Worker): self.workers[w.name]=w
    def _eligible(self,task,privacy):
        rows=[]
        for w in self.workers.values():
            if task not in w.capabilities and "general" not in w.capabilities: continue
            if privacy in {"local_only","restricted"} and not w.local: continue
            if not w.local and not self.zero_cost.cloud_allowed(w.name,confirmed_free=w.confirmed_free,estimated_cost_usd=0): continue
            rows.append(w)
        return rows
    @staticmethod
    def _score(w):
        locality=2.0 if w.local else 0.0
        load_penalty=w.inflight*0.75
        failure_penalty=w.failures*0.5
        latency_penalty=min(w.latency_ms/10000.0,1.0)
        return w.priority+locality-load_penalty-failure_penalty-latency_penalty
    def dispatch(self,prompt,task="general",privacy="approved_cloud",system="You are a worker model for KRISHNA.",max_tokens=2048):
        candidates=sorted(self._eligible(task,privacy),key=self._score,reverse=True)
        errors={}
        for w in candidates:
            w.inflight+=1; started=time.perf_counter()
            try:
                req=CloudRequest(prompt=prompt,model=w.model,system=system,max_tokens=max_tokens)
                out=w.provider.complete(req)
                w.latency_ms=(time.perf_counter()-started)*1000
                w.failures=max(0,w.failures-1)
                return {"provider":w.name,"model":w.model,"content":out["text"],"cost_usd":0.0}
            except QuotaExhausted as exc:
                w.failures+=1; self.zero_cost.mark_exhausted(w.name); errors[w.name]=str(exc)
            except Exception as exc:
                w.failures+=1; errors[w.name]=f"{type(exc).__name__}: {exc}"
            finally:w.inflight-=1
        raise RuntimeError("No zero-cost approved model available: "+str(errors))
    def status(self):
        return {"policy":"ZERO_COST_ONLY","max_spend_usd":0.0,"workers":[
            {"name":w.name,"model":w.model,"local":w.local,"confirmed_free":w.confirmed_free,
             "inflight":w.inflight,"failures":w.failures,"latency_ms":round(w.latency_ms,2)}
            for w in self.workers.values()]}
