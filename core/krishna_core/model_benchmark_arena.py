from __future__ import annotations
from dataclasses import dataclass,asdict
@dataclass(frozen=True)
class Benchmark:
 provider:str; model:str; task:str; quality:float; latency_ms:float; money_cost:float=0; private_ok:bool=True
class ModelBenchmarkArena:
 """Evidence-based routing. ₹0 is mandatory; private tasks require private_ok."""
 def __init__(self): self.rows=[]
 def record(self,**kw):
  r=Benchmark(**kw)
  if r.money_cost!=0: raise ValueError("paid benchmark candidate blocked")
  self.rows.append(r); return asdict(r)
 def choose(self,task,private=False):
  c=[r for r in self.rows if r.task==task and (not private or r.private_ok) and r.money_cost==0]
  if not c:return None
  # Quality first; latency breaks near-equal quality ties.
  c.sort(key=lambda r:(-r.quality,r.latency_ms,r.provider,r.model))
  return asdict(c[0])
