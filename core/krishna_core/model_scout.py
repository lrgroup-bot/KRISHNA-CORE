from __future__ import annotations

"""Persistent local model candidate evaluation.

Discovery is separate from download/installation. This module never downloads a
model and never decides cloud billing eligibility; current router/openrouter/direct-
free policies remain the only cloud-routing authorities.
"""

from dataclasses import asdict,dataclass
from pathlib import Path
import json
import os
import tempfile
import time


@dataclass(frozen=True)
class ModelCandidate:
    model_id:str
    source:str="local"
    task:str="general"
    license:str=""
    size_bytes:int=0
    local_capable:bool=True
    quality:float=0.0
    latency_ms:float=0.0
    ram_bytes:int=0
    vram_bytes:int=0
    duplicate_of:str=""
    notes:str=""


class ModelScout:
    VERSION="model-scout-v2"

    def __init__(self,state_path:str|Path):
        self.path=Path(state_path).resolve()
        self.rows={}
        self.load_error=None
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        try:
            raw=json.loads(self.path.read_text(encoding="utf-8-sig"))
            self.rows=dict(raw.get("models") or {})
        except Exception as exc:
            self.rows={}
            self.load_error=f"{type(exc).__name__}: {exc}"

    def _save(self):
        if self.load_error:
            raise RuntimeError("model scout state is unreadable; refusing overwrite")
        self.path.parent.mkdir(parents=True,exist_ok=True)
        payload={"schema":1,"version":self.VERSION,"models":self.rows}
        fd,tmp=tempfile.mkstemp(prefix="model-scout-",suffix=".json",dir=str(self.path.parent))
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as h:
                json.dump(payload,h,indent=2,ensure_ascii=False)
            os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

    @staticmethod
    def score(c:ModelCandidate):
        if c.duplicate_of:
            return -1.0
        quality=max(0.0,min(float(c.quality),1.0))
        latency_penalty=min(max(float(c.latency_ms),0.0)/10000.0,1.0)
        ram_penalty=min(max(int(c.ram_bytes),0)/(64*1024**3),1.0)
        vram_penalty=min(max(int(c.vram_bytes),0)/(24*1024**3),1.0)
        return round(
            quality*0.70+(1-latency_penalty)*0.12+
            (1-ram_penalty)*0.10+(1-vram_penalty)*0.08,6
        )

    def evaluate(self,candidate:ModelCandidate,*,min_score=.55):
        if not str(candidate.model_id or "").strip():
            raise ValueError("model_id is required")
        score=self.score(candidate)
        accepted=bool(candidate.local_capable and not candidate.duplicate_of and score>=float(min_score))
        row={
            **asdict(candidate),
            "score":score,
            "accepted":accepted,
            "decision":"PROMOTE_LOCAL_CANDIDATE" if accepted else "REJECT_OR_HOLD",
            "evaluated_at":time.time(),
            "authority":"candidate evaluation only; installation and routing remain separate governed actions",
        }
        self.rows[candidate.model_id]=row
        self._save()
        return row

    def recommend(self,task="general",*,max_ram_bytes=None,max_vram_bytes=None,limit=10):
        rows=[dict(x) for x in self.rows.values() if x.get("accepted")]
        task=str(task or "general").strip().lower()
        rows=[x for x in rows if str(x.get("task") or "general").lower() in {task,"general"}]
        if max_ram_bytes is not None:
            rows=[x for x in rows if int(x.get("ram_bytes") or 0)<=int(max_ram_bytes)]
        if max_vram_bytes is not None:
            rows=[x for x in rows if int(x.get("vram_bytes") or 0)<=int(max_vram_bytes)]
        rows.sort(key=lambda x:(float(x.get("score") or 0),-float(x.get("latency_ms") or 0)),reverse=True)
        return rows[:max(1,min(int(limit),100))]

    def status(self):
        active=[x for x in self.rows.values() if x.get("accepted")]
        return {
            "version":self.VERSION,
            "source_strategy":"discover-many-benchmark-few-promote-best",
            "download_policy":"no automatic downloads",
            "cloud_billing_authority":False,
            "evaluated":len(self.rows),
            "active_candidates":len(active),
            "load_error":self.load_error,
        }
