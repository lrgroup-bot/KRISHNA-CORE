"""Durable trusted-node registry without storing credentials.

Node trust is canonical here. Engineering execution capabilities are metadata on
an already owner-approved node; a second trust registry is intentionally avoided.
"""
from dataclasses import dataclass,asdict,field
from pathlib import Path
import json,time,uuid

ROLES={"worker","controller","research","media","field","observer","qc"}

@dataclass
class NodeRecord:
 id:str
 name:str
 fingerprint:str
 role:str="worker"
 trusted:bool=False
 last_sync:float=0
 platform:str=""
 capabilities:list[str]=field(default_factory=list)
 endpoint:str=""
 workspace_root:str=""
 online:bool=False
 last_seen:float=0

class NodeRegistry:
 def __init__(self,path): self.path=Path(path)
 def load(self):
  if not self.path.exists(): return {}
  rows=json.loads(self.path.read_text(encoding="utf-8"))
  return {x["id"]:NodeRecord(**x) for x in rows}
 def save(self,records):
  self.path.parent.mkdir(parents=True,exist_ok=True)
  self.path.write_text(json.dumps([asdict(x) for x in records.values()],indent=2),encoding="utf-8")
 def enroll(self,name,fingerprint,role="worker",approved=False):
  name=str(name or "").strip(); fingerprint=str(fingerprint or "").strip().lower(); role=str(role or "worker").strip().lower()
  if not approved: raise PermissionError("owner approval required")
  if not name: raise ValueError("node name is required")
  if len(fingerprint)<16: raise ValueError("node fingerprint is missing or too short")
  if role not in ROLES: raise ValueError("unsupported node role")
  d=self.load()
  if any(x.fingerprint==fingerprint for x in d.values()): raise ValueError("node fingerprint already enrolled")
  r=NodeRecord(str(uuid.uuid4()),name,fingerprint,role,True); d[r.id]=r; self.save(d); return r
 def mark_sync(self,node_id):
  d=self.load()
  if node_id not in d: raise KeyError(node_id)
  d[node_id].last_sync=time.time(); self.save(d)
  return asdict(d[node_id])
 def configure_execution(self,node_id,*,platform,capabilities,endpoint="",workspace_root="",approved=False):
  if not approved: raise PermissionError("owner approval required to configure a compute node")
  d=self.load()
  if node_id not in d: raise KeyError(node_id)
  node=d[node_id]
  if not node.trusted: raise PermissionError("node must already be trusted")
  node.platform=str(platform or "").strip().lower()
  node.capabilities=sorted({str(x).strip() for x in capabilities or [] if str(x).strip()})
  node.endpoint=str(endpoint or "").strip()
  node.workspace_root=str(workspace_root or "").strip()
  self.save(d);return asdict(node)
 def heartbeat(self,node_id,capabilities=None):
  d=self.load()
  if node_id not in d: raise KeyError(node_id)
  node=d[node_id]
  if not node.trusted: raise PermissionError("untrusted node heartbeat is not execution authority")
  node.online=True;node.last_seen=time.time()
  if capabilities is not None:
   node.capabilities=sorted({str(x).strip() for x in capabilities if str(x).strip()})
  self.save(d);return asdict(node)
 def select(self,capability,platform=None,max_age_seconds=120):
  now=time.time();rows=[]
  for node in self.load().values():
   if not node.trusted or not node.online:continue
   if now-float(node.last_seen or 0)>max(5,int(max_age_seconds)):continue
   if str(capability) not in node.capabilities:continue
   if platform and node.platform!=str(platform).lower():continue
   rows.append(node)
  rows.sort(key=lambda x:x.last_seen,reverse=True)
  return asdict(rows[0]) if rows else None
 def status(self):
  return {"component":"KRISHNA Trusted Node Registry","nodes":[asdict(x) for x in self.load().values()],
          "trust_authority":"owner-approved fingerprint enrollment",
          "execution_metadata_does_not_grant_trust":True}
