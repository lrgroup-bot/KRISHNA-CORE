from __future__ import annotations

import json
import math
import os
import urllib.request
from dataclasses import dataclass, asdict
from typing import Any, Callable


@dataclass(frozen=True)
class ChoiceResult:
    choice: str
    probabilities: dict[str, float]
    engine: str
    calibrated: bool
    authority: str = "advisory-only"

    def as_dict(self):
        return asdict(self)


class SystemOneDecisionEngine:
    """Small advisory choice engine inspired by OpenJev.

    This layer never authorizes spending, protected mutations, credentials, or
    security-sensitive actions. It selects among bounded options and Sudarshan /
    PolicyKernel remain authoritative.
    """

    VERSION = "system-one-v1"

    def __init__(self, scorer: Callable | None = None, endpoint: str | None = None):
        self.scorer = scorer
        self.endpoint = str(endpoint or os.getenv("KRISHNA_OPENJEV_URL") or "").rstrip("/")

    @staticmethod
    def _softmax(values: list[float]) -> list[float]:
        if not values:
            return []
        m = max(values)
        ex = [math.exp(max(-50.0, min(50.0, x - m))) for x in values]
        total = sum(ex) or 1.0
        return [x / total for x in ex]

    @staticmethod
    def _bounded(options):
        out=[]
        for row in options or []:
            value=str(row or "").strip()
            if value and value not in out:
                out.append(value)
        if len(out) < 2:
            raise ValueError("System One requires at least two bounded options")
        if len(out) > 32:
            raise ValueError("System One accepts at most 32 options")
        return out

    @staticmethod
    def _heuristic_scores(context: dict[str, Any], options: list[str]) -> list[float]:
        text=" ".join(str(v or "") for v in (context or {}).values()).lower()
        scores=[]
        for option in options:
            key=option.lower()
            score=0.0
            if key in text:
                score += 2.5
            tokens=[x for x in key.replace("-","_").split("_") if len(x)>2]
            score += sum(0.35 for token in tokens if token in text)
            if any(word in text for word in ("private","credential","secret","protected","local only")):
                if any(word in key for word in ("pc","local","private")): score += 2.0
                if "cloud" in key: score -= 3.0
            if any(word in text for word in ("simple","fast","quick","routine")):
                if any(word in key for word in ("fast","local","mobile","free")): score += 1.0
            if any(word in text for word in ("heavy","complex","deep","render","large")):
                if any(word in key for word in ("pc","heavy","specialist")): score += 1.2
            scores.append(score)
        return scores

    def _remote_scores(self, state: dict, options: list[str]) -> list[float]:
        if not self.endpoint:
            raise RuntimeError("OpenJev endpoint is not configured")
        body=json.dumps({"state":state,"options":options}).encode("utf-8")
        req=urllib.request.Request(
            self.endpoint + "/score",
            data=body,
            headers={"Content-Type":"application/json","Accept":"application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req,timeout=8) as response:
            data=json.loads(response.read().decode("utf-8"))
        if isinstance(data.get("probabilities"),dict):
            probs=[float(data["probabilities"].get(x,0.0)) for x in options]
            return [math.log(max(1e-9,p)) for p in probs]
        scores=data.get("scores")
        if not isinstance(scores,list) or len(scores)!=len(options):
            raise RuntimeError("OpenJev endpoint returned invalid scores")
        return [float(x) for x in scores]

    def choose(self, context: dict[str,Any] | None, options, *, allow_remote=True) -> dict:
        opts=self._bounded(options)
        engine="heuristic"
        calibrated=False
        raw=None
        if self.scorer:
            raw=[float(x) for x in self.scorer(dict(context or {}),opts)]
            engine="injected"
        elif allow_remote and self.endpoint:
            try:
                raw=self._remote_scores(dict(context or {}),opts)
                engine="openjev"
                calibrated=True
            except Exception:
                raw=None
        if raw is None:
            raw=self._heuristic_scores(dict(context or {}),opts)
        probs=self._softmax(raw)
        mapping={k:round(v,6) for k,v in zip(opts,probs)}
        choice=max(mapping,key=mapping.get)
        return ChoiceResult(choice,mapping,engine,calibrated).as_dict()

    def status(self):
        return {
            "component":"KRISHNA System One",
            "version":self.VERSION,
            "remote_openjev_configured":bool(self.endpoint),
            "resident_model":False,
            "authority":"advisory-only",
            "hard_policy_override_allowed":False,
            "use_cases":[
                "provider selection","specialist selection","retry-or-stop",
                "fast-vs-heavy route","tool selection","mobile-cloud-vs-pc escalation",
            ],
        }
