from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import os
import urllib.request
from typing import Any


@dataclass(frozen=True)
class Decision:
    choice: str
    confidence: float
    scores: dict[str,float]
    engine: str
    escalated: bool
    reason: str

    def as_dict(self):
        return asdict(self)


class SystemOneDecisionEngine:
    """Low-cost bounded decision layer inspired by Jev/OpenJev.

    It never grants authority. It only ranks caller-provided options. Policy,
    permissions, spend approval, secrets, external actions and safety gates stay
    with deterministic KRISHNA/Sudarshan code.
    """

    HIGH_STAKES={
        "spend","payment","credential","secret","permission","legal_action",
        "medical_action","delete","deploy","promotion","external_write",
    }

    def __init__(self, endpoint: str|None=None, timeout: int=6):
        self.endpoint=(endpoint or os.getenv("KRISHNA_OPENJEV_URL") or "").strip().rstrip("/")
        self.timeout=max(1,min(int(timeout),20))

    def status(self):
        return {
            "component":"KRISHNA System-One",
            "mode":"bounded-option-ranking",
            "openjev_endpoint_configured":bool(self.endpoint),
            "authority":False,
            "high_stakes_escalate":sorted(self.HIGH_STAKES),
            "always_on_model":False,
            "pc_ram_reserved_mb":0,
        }

    @staticmethod
    def _heuristic(options:list[str], signals:dict[str,Any]) -> Decision:
        weights=dict(signals.get("option_scores") or {})
        scores={str(o):float(weights.get(str(o),0.0)) for o in options}
        if not any(scores.values()):
            preferred=str(signals.get("preferred") or "")
            for i,opt in enumerate(options):
                scores[str(opt)]=1.0 if str(opt)==preferred and preferred else max(0.0,1.0-(i*0.1))
        best=max(scores,key=scores.get)
        vals=sorted(scores.values(),reverse=True)
        gap=(vals[0]-vals[1]) if len(vals)>1 else abs(vals[0])
        confidence=max(0.0,min(1.0,0.5+gap/2))
        return Decision(best,confidence,scores,"deterministic-heuristic",False,"bounded local ranking")

    def _remote(self, context:str, options:list[str]) -> Decision:
        body=json.dumps({"context":context,"options":options}).encode()
        req=urllib.request.Request(
            self.endpoint+"/decide",data=body,method="POST",
            headers={"Content-Type":"application/json","Accept":"application/json"},
        )
        with urllib.request.urlopen(req,timeout=self.timeout) as r:
            data=json.loads(r.read().decode())
        scores={str(k):float(v) for k,v in dict(data.get("scores") or {}).items() if str(k) in options}
        if not scores:
            raise RuntimeError("OpenJev endpoint returned no option scores")
        best=max(scores,key=scores.get)
        total=sum(max(0.0,x) for x in scores.values())
        confidence=(max(0.0,scores[best])/total) if total>0 else 0.0
        return Decision(best,confidence,scores,"openjev-compatible",False,"one-pass option score")

    def decide(self, context:str, options:list[str], *, signals=None, decision_class="routing"):
        options=[str(x).strip() for x in options if str(x).strip()]
        if len(options)<2:
            raise ValueError("System-One requires at least two bounded options")
        if len(options)>32:
            raise ValueError("System-One option count exceeds 32")
        klass=str(decision_class or "routing").strip().lower()
        if klass in self.HIGH_STAKES:
            return Decision("",0.0,{},"policy-escalation",True,"high-stakes decisions require deterministic policy/owner authority").as_dict()
        if self.endpoint:
            try:
                return self._remote(str(context or "")[:8000],options).as_dict()
            except Exception:
                pass
        return self._heuristic(options,dict(signals or {})).as_dict()
