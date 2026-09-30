from __future__ import annotations
from dataclasses import dataclass,asdict
from datetime import datetime,timezone

@dataclass
class ProcessExpectation:
 name:str; expected:bool=True; max_idle_seconds:int=900; last_progress_at:str|None=None
 state:str="UNKNOWN"; reason:str=""; failures:int=0
 def as_dict(self):return asdict(self)

class Prahari:
 """Always-on observer. Observes/explains/escalates; never patches production."""
 def __init__(self):self._items={}
 def expect(self,name,**kw):
  row=ProcessExpectation(str(name),**kw);self._items[row.name]=row;return row.as_dict()
 def observe(self,name,*,state,last_progress_at=None,reason="",failures=0):
  row=self._items.get(str(name)) or ProcessExpectation(str(name));row.state=str(state).upper()
  row.last_progress_at=last_progress_at;row.reason=str(reason);row.failures=int(failures);self._items[row.name]=row
  return self.assess(row.name)
 def assess(self,name,now=None):
  row=self._items[str(name)];now=now or datetime.now(timezone.utc);idle=None
  if row.last_progress_at:
   try: idle=max(0,(now-datetime.fromisoformat(row.last_progress_at.replace("Z","+00:00"))).total_seconds())
   except Exception: idle=None
  bad=row.expected and (row.state in {"FAILED","CRASHED","BLOCKED","DEGRADED"} or row.failures>0 or (idle is not None and idle>row.max_idle_seconds))
  route="MRITYUNJAY" if bad else "NONE"
  if bad and row.reason.lower().find("change")>=0:route="VISHWAKARMA"
  return {**row.as_dict(),"idle_seconds":idle,"needs_attention":bad,"route":route,
   "authority":"observe-and-escalate-only"}
 def sweep(self):return [self.assess(x) for x in sorted(self._items)]
