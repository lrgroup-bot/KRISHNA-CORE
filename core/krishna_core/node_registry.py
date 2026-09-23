"""Durable trusted-node registry without storing credentials."""
from dataclasses import dataclass,asdict
from pathlib import Path
import json,time,uuid
@dataclass
class NodeRecord:
 id:str; name:str; fingerprint:str; role:str="worker"; trusted:bool=False; last_sync:float=0
class NodeRegistry:
 def __init__(self,path): self.path=Path(path)
 def load(self):
  if not self.path.exists(): return {}
  return {x["id"]:NodeRecord(**x) for x in json.loads(self.path.read_text(encoding="utf-8"))}
 def save(self,records): self.path.parent.mkdir(parents=True,exist_ok=True); self.path.write_text(json.dumps([asdict(x) for x in records.values()],indent=2),encoding="utf-8")
 def enroll(self,name,fingerprint,role="worker",approved=False):
  if not approved: raise PermissionError("owner approval required")
  r=NodeRecord(str(uuid.uuid4()),name,fingerprint,role,True); d=self.load(); d[r.id]=r; self.save(d); return r
 def mark_sync(self,node_id):
  d=self.load(); d[node_id].last_sync=time.time(); self.save(d)
