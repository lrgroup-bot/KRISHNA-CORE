from __future__ import annotations
from collections import Counter,deque
import time

class ProviderTelemetry:
    def __init__(self,limit=1000):self.events=deque(maxlen=max(100,int(limit)))
    def record(self,provider,*,local=False,status="ok",latency_ms=0,rate_limited=False,fallback=False,blocked_paid=False):
        self.events.append({"provider":str(provider),"local":bool(local),"status":str(status),"latency_ms":int(latency_ms or 0),
            "rate_limited":bool(rate_limited),"fallback":bool(fallback),"blocked_paid":bool(blocked_paid),"at":time.time()})
    def status(self):
        rows=list(self.events);n=len(rows);providers=Counter(x["provider"] for x in rows)
        return {"calls":n,"providers":dict(providers),"local_percent":round(100*sum(x["local"] for x in rows)/n,1) if n else 0.0,
            "rate_limits":sum(x["rate_limited"] for x in rows),"fallbacks":sum(x["fallback"] for x in rows),
            "blocked_paid_attempts":sum(x["blocked_paid"] for x in rows),"spend_inr":0,
            "average_latency_ms":round(sum(x["latency_ms"] for x in rows)/n,1) if n else 0.0,"policy":"hard zero-spend"}
