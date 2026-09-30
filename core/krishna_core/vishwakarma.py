from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, uuid

def _now(): return datetime.now(timezone.utc).isoformat()
def _slug(v):
    s=re.sub(r"[^a-zA-Z0-9._-]+","-",str(v or "").strip()).strip("-._")
    if not s: raise ValueError("project is required")
    return s[:96]

@dataclass(frozen=True)
class UpdatePolicy:
    frontend_required: bool = True
    exe_before_frontend_approval: bool = False
    live_direct_write: bool = False
    auto_merge: bool = False
    promotion_authority: str = "Sudarshan/owner policy"

class VishwakarmaUpdateManager:
    """Plans stronger KRISHNA updates without writing live runtime.

    VISHWAKARMA is a builder, never promotion authority. It emits durable update
    state and gates packaging behind explicit frontend evidence + approval.
    """
    SCHEMA="krishna.vishwakarma-update.v1"
    ORDER=("PLANNED","IMPLEMENTING","TESTED","FRONTEND_READY","FRONTEND_APPROVED",
           "RELEASE_CANDIDATE","PROMOTION_READY","DEPLOYED","VERIFIED")
    def __init__(self, root):
        self.root=Path(root).resolve(); self.root.mkdir(parents=True,exist_ok=True)
        self.policy=UpdatePolicy()
    def _path(self, update_id): return self.root/(str(update_id)+".json")
    def _save(self,p):
        path=self._path(p["update_id"]); tmp=path.with_suffix(".tmp")
        tmp.write_text(json.dumps(p,indent=2,sort_keys=True),encoding="utf-8"); tmp.replace(path)
        return p
    def plan(self, project, goal, *, source_ref="HEAD", risk="medium"):
        uid=f"{_slug(project)}-{uuid.uuid4().hex[:12]}"
        p={"schema":self.SCHEMA,"update_id":uid,"project":str(project),"goal":str(goal),
           "source_ref":str(source_ref),"risk":str(risk),"state":"PLANNED","created_at":_now(),
           "policy":asdict(self.policy),"evidence":{},"history":[]}
        return self._save(p)
    def load(self, update_id):
        p=self._path(update_id)
        if not p.is_file(): raise FileNotFoundError(update_id)
        v=json.loads(p.read_text(encoding="utf-8"))
        if v.get("schema")!=self.SCHEMA: raise ValueError("invalid update state")
        return v
    def record(self, update_id, state, *, evidence=None, actor="KRISHNA"):
        p=self.load(update_id); state=str(state).upper()
        if state not in self.ORDER: raise ValueError("invalid update state")
        current=self.ORDER.index(p["state"]); target=self.ORDER.index(state)
        if target!=current+1: raise ValueError(f"invalid transition {p['state']} -> {state}")
        ev=dict(evidence or {})
        if state=="TESTED" and not ev.get("tests_passed"): raise ValueError("TESTED requires passing test evidence")
        if state=="FRONTEND_READY" and not ev.get("frontend_proof"): raise ValueError("frontend proof is required")
        if state=="FRONTEND_APPROVED" and not ev.get("approved"): raise ValueError("explicit frontend approval is required")
        if state=="RELEASE_CANDIDATE" and p["state"]!="FRONTEND_APPROVED": raise ValueError("frontend approval must precede packaging")
        if state=="PROMOTION_READY" and not ev.get("independent_verification"): raise ValueError("independent verification is required")
        if state=="DEPLOYED" and not ev.get("promotion_receipt"): raise ValueError("transactional promotion receipt is required")
        if state=="VERIFIED" and not ev.get("post_deploy_health"): raise ValueError("post-deploy health evidence is required")
        p["state"]=state; p["evidence"][state]=ev
        p["history"].append({"state":state,"actor":str(actor),"at":_now()})
        p["updated_at"]=_now(); return self._save(p)
    def packaging_allowed(self, update_id):
        p=self.load(update_id)
        return {"allowed":self.ORDER.index(p["state"])>=self.ORDER.index("FRONTEND_APPROVED"),
                "state":p["state"],"rule":"No Windows EXE/package before explicit frontend approval."}
    def status(self, update_id): return self.load(update_id)
