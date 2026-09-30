from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json, re

TRUST_STATES=("GREEN","YELLOW","ORANGE","RED","BLACK")

@dataclass
class KarmaRecord:
    agent:str; state:str="GREEN"; score:int=100; failures:int=0
    unsafe_attempts:int=0; paid_attempts:int=0; last_reason:str=""

class KarmaProtocol:
    """System-wide agent consequence/trust protocol; no simulated emotions."""
    def __init__(self, root):
        self.root=Path(root).resolve(); self.root.mkdir(parents=True,exist_ok=True)
    def _key(self,name):
        return re.sub(r"[^a-zA-Z0-9._-]+","-",str(name).strip()).strip("-")[:96]
    def _path(self,name): return self.root/(self._key(name)+".json")
    def load(self,name):
        p=self._path(name)
        if not p.exists(): return KarmaRecord(agent=str(name))
        return KarmaRecord(**json.loads(p.read_text(encoding="utf-8")))
    def save(self,r):
        self._path(r.agent).write_text(json.dumps(asdict(r),indent=2),encoding="utf-8"); return asdict(r)
    @staticmethod
    def _state(score):
        if score>=85:return "GREEN"
        if score>=65:return "YELLOW"
        if score>=40:return "ORANGE"
        if score>=15:return "RED"
        return "BLACK"
    def event(self,agent,kind,reason=""):
        r=self.load(agent); kind=str(kind).upper()
        delta={"VERIFIED_SUCCESS":2,"FAILURE":-8,"UNSAFE_ATTEMPT":-20,"PAID_ATTEMPT":-25,
               "POLICY_BYPASS":-40,"RECOVERY_SUCCESS":5}.get(kind,0)
        r.score=max(0,min(100,r.score+delta)); r.last_reason=str(reason)[:1000]
        if kind=="FAILURE":r.failures+=1
        if kind in {"UNSAFE_ATTEMPT","POLICY_BYPASS"}:r.unsafe_attempts+=1
        if kind=="PAID_ATTEMPT":r.paid_attempts+=1
        r.state=self._state(r.score); return self.save(r)
    def permissions(self,agent):
        r=self.load(agent)
        return {"agent":r.agent,"state":r.state,"score":r.score,
          "mutation_allowed":r.state in {"GREEN","YELLOW"},
          "independent_review_required":r.state!="GREEN",
          "execution_allowed":r.state not in {"RED","BLACK"},
          "retired":r.state=="BLACK"}
