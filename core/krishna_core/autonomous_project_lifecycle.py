from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone
import json,re

def _now(): return datetime.now(timezone.utc).isoformat()
def _slug(v): return re.sub(r"[^A-Za-z0-9._-]+","-",str(v)).strip(".-")[:96] or "project"

class AutonomousProjectLifecycle:
    """State-only discovery, owner design gate, silent-build and final-QC contract."""
    SCHEMA="krishna.autonomous-project.v1"
    OWNER_ONLY={"financial_approval","legal_approval","private_secret_required","external_commitment"}
    def __init__(self,root):
        self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True)
    def _path(self,p): return self.root/(_slug(p)+".json")
    def _read(self,p): return json.loads(self._path(p).read_text(encoding="utf-8"))
    def _write(self,s):
        s=dict(s);s["updated_at"]=_now();q=self._path(s["project"]);t=q.with_suffix(".tmp")
        t.write_text(json.dumps(s,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8");t.replace(q);return s
    def begin(self,project,idea):
        return self._write({"schema":self.SCHEMA,"project":str(project),"owner_idea":str(idea),"phase":"DISCOVERY",
          "findings":[],"discussion_complete":False,"prototype":{"url":None,"verified":False},
          "frozen_spec":None,"silent_build":False,"chandradev":None,"completion":None})
    def record_discovery(self,project,findings):
        s=self._read(project);s["findings"]=[dict(x) for x in findings];s["phase"]="OWNER_DISCUSSION";return self._write(s)
    def approve_prototype(self,project,prototype_url,verified=True):
        s=self._read(project);s["discussion_complete"]=True;s["prototype"]={"url":str(prototype_url),"verified":bool(verified)}
        s["phase"]="READY_TO_FREEZE" if verified else "PROTOTYPE_REPAIR";return self._write(s)
    def freeze(self,project,spec_version,spec):
        s=self._read(project)
        if not s["discussion_complete"] or not s["prototype"]["verified"]: raise RuntimeError("owner discussion and verified prototype required")
        s["frozen_spec"]={"version":str(spec_version),"spec":dict(spec),"frozen_at":_now()}
        s["silent_build"]=True;s["phase"]="AUTONOMOUS_BUILD";return self._write(s)
    def interruption(self,project,actor,reason,category):
        protected=str(category) in self.OWNER_ONLY; krishna=str(actor).upper()=="KRISHNA"
        return {"project":str(project),"reason":str(reason),"owner_interrupt":bool(protected and krishna),
                "route":"OWNER" if protected and krishna else "SUDARSHAN"}
    def chandradev_result(self,project,report):
        s=self._read(project);s["chandradev"]=dict(report);s["phase"]="FINAL_ACCEPTANCE" if report.get("passed") else "FINAL_REPAIR";return self._write(s)
    def complete(self,project,acceptance_passed,deploy_verified,runtime_verified,live_url=None,replay=None):
        s=self._read(project);ok=bool(acceptance_passed and deploy_verified and runtime_verified and (s.get("chandradev") or {}).get("passed"))
        s["completion"]={"verified":ok,"live_url":live_url,"replay":replay,"completed_at":_now() if ok else None}
        s["phase"]="VERIFIED_COMPLETE" if ok else "FINAL_REPAIR";return self._write(s)
    def status(self,project): return self._read(project)
