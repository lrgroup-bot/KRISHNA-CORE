from __future__ import annotations

"""KRISHNA candidate-model scout and admission ledger.

Discovery is separate from installation/activation. This module evaluates supplied
candidate metadata and benchmark evidence; it does not download models or assume a
cloud provider is free merely because a candidate is labelled free.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import os
import tempfile
import time


@dataclass
class ModelCandidate:
    model_id: str
    source: str = "local"
    task: str = "general"
    license: str = ""
    size_bytes: int = 0
    local_capable: bool = True
    cloud_zero_cost_verified: bool = False
    quality: float = 0.0
    latency_ms: float = 0.0
    ram_bytes: int = 0
    vram_bytes: int = 0
    duplicate_of: str = ""
    benchmark_ref: str = ""
    notes: str = ""


class ModelScout:
    VERSION="model-scout-v2"

    def __init__(self,state_path):
        self.path=Path(state_path)
        self.rows={}
        self.load_error=None
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        try:
            raw=json.loads(self.path.read_text(encoding="utf-8-sig"))
            if raw.get("version")!=self.VERSION:
                return
            self.rows=dict(raw.get("models") or {})
        except Exception as exc:
            self.rows={}
            self.load_error=f"{type(exc).__name__}: {exc}"

    def _save(self):
        if self.load_error:
            raise RuntimeError("model scout state is unreadable; refusing overwrite: "+self.load_error)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        payload={"schema":1,"version":self.VERSION,"models":self.rows,"updated_at":time.time()}
        fd,tmp=tempfile.mkstemp(prefix="model-scout-",suffix=".json",dir=str(self.path.parent))
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as handle:
                json.dump(payload,handle,indent=2,ensure_ascii=False)
            os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    @staticmethod
    def score(candidate: ModelCandidate):
        quality=max(0.0,min(float(candidate.quality),1.0))
        latency_penalty=min(max(float(candidate.latency_ms),0.0)/10000.0,1.0)
        ram_penalty=min(max(int(candidate.ram_bytes),0)/(64*1024**3),1.0)
        vram_penalty=min(max(int(candidate.vram_bytes),0)/(24*1024**3),1.0)
        if candidate.duplicate_of:
            return -1.0
        return round(
            quality*0.70
            +(1-latency_penalty)*0.12
            +(1-ram_penalty)*0.10
            +(1-vram_penalty)*0.08,
            6,
        )

    def evaluate(self,candidate: ModelCandidate,*,min_score=0.55):
        if not candidate.model_id.strip():
            raise ValueError("model_id is required")
        score=self.score(candidate)
        benchmarked=bool(str(candidate.benchmark_ref or "").strip())
        accepted=bool(
            candidate.local_capable
            and not candidate.duplicate_of
            and benchmarked
            and score>=float(min_score)
        )
        prior=dict(self.rows.get(candidate.model_id) or {})
        row={
            **asdict(candidate),
            "score":score,
            "benchmarked":benchmarked,
            "accepted":accepted,
            "decision":"PROMOTE_LOCAL_CANDIDATE" if accepted else "REJECT_OR_HOLD",
            "evaluated_at":time.time(),
            "reviewed":bool(prior.get("reviewed",False)) if accepted else False,
            "verified":bool(prior.get("verified",False)) if accepted else False,
            "routing_enabled":bool(prior.get("routing_enabled",False)) if accepted else False,
            "review_ref":str(prior.get("review_ref") or "") if accepted else "",
            "verification_ref":str(prior.get("verification_ref") or "") if accepted else "",
            "cloud_policy":"cloud candidate labels never establish zero-cost; live provider billing verification remains separate",
        }
        self.rows[candidate.model_id]=row
        self._save()
        return dict(row)

    def active(self):
        return [dict(x) for x in self.rows.values() if x.get("accepted")]

    def promote(self,model_id,*,review_ref,verification_ref):
        key=str(model_id or "").strip()
        row=self.rows.get(key)
        if not row:raise KeyError("model candidate not found")
        if not row.get("accepted") or not row.get("benchmarked"):
            raise RuntimeError("model candidate must be benchmarked and accepted before promotion")
        review_ref=str(review_ref or "").strip();verification_ref=str(verification_ref or "").strip()
        if not review_ref or not verification_ref:
            raise ValueError("review_ref and verification_ref are required")
        row=dict(row)
        row.update({
            "reviewed":True,"verified":True,"routing_enabled":True,
            "review_ref":review_ref,"verification_ref":verification_ref,
            "promoted_at":time.time(),"decision":"ROUTING_ENABLED",
        })
        self.rows[key]=row;self._save()
        return dict(row)

    def routing_candidates(self,task="general",*,limit=10):
        task=str(task or "general").strip().lower()
        rows=[]
        for row in self.active():
            if not row.get("routing_enabled"):continue
            row_task=str(row.get("task") or "general").strip().lower()
            if task not in {"","general"} and row_task not in {"general",task}:continue
            rows.append(row)
        rows.sort(key=lambda x:(float(x.get("score") or 0),-float(x.get("latency_ms") or 0)),reverse=True)
        return rows[:max(1,min(int(limit),100))]

    def recommend(self,task="general",*,max_ram_bytes=None,max_vram_bytes=None,limit=10):
        task=str(task or "general").strip().lower()
        rows=[]
        for row in self.active():
            row_task=str(row.get("task") or "general").strip().lower()
            if task not in {"","general"} and row_task not in {"general",task}:
                continue
            if max_ram_bytes is not None and int(row.get("ram_bytes") or 0)>int(max_ram_bytes):
                continue
            if max_vram_bytes is not None and int(row.get("vram_bytes") or 0)>int(max_vram_bytes):
                continue
            rows.append(row)
        rows.sort(key=lambda x:(float(x.get("score") or 0),-float(x.get("latency_ms") or 0)),reverse=True)
        return rows[:max(1,min(int(limit),100))]

    def status(self):
        active=self.active()
        return {
            "version":self.VERSION,
            "source_strategy":"discover-many-benchmark-few-promote-best",
            "download_policy":"no blind bulk downloads",
            "activation_policy":"candidate metadata alone never activates a model",
            "cloud_spend_limit_usd":0.0,
            "cloud_billing_authority":False,
            "routing_authority":False,
            "evaluated":len(self.rows),
            "active":len(active),
            "active_candidates":len(active),
            "routing_enabled":sum(1 for x in active if x.get("routing_enabled")),
            "load_error":self.load_error,
        }
