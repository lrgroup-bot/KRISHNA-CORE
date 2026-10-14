from __future__ import annotations
from dataclasses import dataclass,asdict
from collections import deque
import time
@dataclass
class Observation:
 source:str; kind:str; data:dict; confidence:float; ts:float
class PerceptionFusion:
 """Fuse structured UI/OCR/VLM/tracking evidence and verify changes over time."""
 PRIORITY={"api":0,"accessibility":1,"ui_tree":2,"ocr":3,"vlm":4,"coordinates":5}
 def __init__(self,history=32): self.history=deque(maxlen=max(4,int(history)))
 def observe(self,source,kind,data,confidence=1.0,ts=None):
  o=Observation(str(source),str(kind),dict(data or {}),max(0,min(1,float(confidence))),float(ts or time.time()))
  self.history.append(o); return asdict(o)
 def scene(self):
  rows=sorted(self.history,key=lambda o:(self.PRIORITY.get(o.kind,9),-o.confidence,-o.ts))
  return {"observations":[asdict(x) for x in rows],"best":asdict(rows[0]) if rows else None}
 def verify_change(self,before:dict,after:dict):
  changed=before!=after
  return {"changed":changed,"verified":changed,"before":before,"after":after,
          "rule":"observe again after every consequential GUI/physical action"}
