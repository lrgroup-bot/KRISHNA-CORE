from __future__ import annotations
import time
"""Provider limits plus shared machine pressure. Free/public sources remain provider-compliant."""

DEFAULTS={
 "crossref_public":{"rate_per_second":5,"concurrency":1},
 "crossref_polite":{"rate_per_second":10,"concurrency":3},
}

class ProviderGovernor:
    def __init__(self,limits=None):
        self.limits={**DEFAULTS,**dict(limits or {})};self.state={}
    def permit(self,provider,*,active=0,machine_pressure=0.0,now=None):
        p=str(provider);cfg=self.limits.get(p,{"rate_per_second":1,"concurrency":1})
        if float(machine_pressure)>=.85:
            return {"allowed":False,"reason":"machine_pressure","provider":p}
        if int(active)>=int(cfg["concurrency"]):
            return {"allowed":False,"reason":"provider_concurrency","provider":p,"limit":cfg["concurrency"]}
        now=float(now if now is not None else time.monotonic())
        s=self.state.setdefault(p,{"window":now,"count":0})
        if now-s["window"]>=1.0:s.update(window=now,count=0)
        if s["count"]>=int(cfg["rate_per_second"]):
            return {"allowed":False,"reason":"provider_rate","provider":p,"limit":cfg["rate_per_second"]}
        s["count"]+=1
        return {"allowed":True,"reason":"within_limits","provider":p}

def provider_failure_action(status_code,attempt):
    attempt=max(0,int(attempt))
    if int(status_code)==429:
        return {"retry":True,"backoff_seconds":min(300,2**min(attempt,8)),
                "reduce_concurrency":True,"circuit_breaker":attempt>=5}
    if 500<=int(status_code)<600:
        return {"retry":attempt<5,"backoff_seconds":min(60,2**min(attempt,6)),
                "reduce_concurrency":False,"circuit_breaker":attempt>=5}
    return {"retry":False,"backoff_seconds":0,"reduce_concurrency":False,"circuit_breaker":False}
