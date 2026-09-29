from __future__ import annotations

from pathlib import Path
from typing import Any
import json,time,uuid


class WorkflowRecorder:
    """Record validated desktop/browser actions and compile them into a Skill candidate."""

    ALLOWED_ACTIONS={"click","type","wait","open","hotkey","assert_text","assert_visible","screenshot","navigate"}

    def __init__(self,root,skill_compiler):
        self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True)
        self.compiler=skill_compiler

    def start(self,name,project="KRISHNA"):
        sid=str(uuid.uuid4())
        data={"schema":1,"session_id":sid,"name":str(name),"project":str(project),"started_at":time.time(),"steps":[],"status":"recording"}
        path=self.root/f"{sid}.json";path.write_text(json.dumps(data,indent=2),encoding="utf-8")
        return data

    def append(self,session_id,action,target="",value="",evidence=None):
        path=self.root/f"{session_id}.json"
        if not path.exists():raise KeyError(session_id)
        data=json.loads(path.read_text(encoding="utf-8"))
        if data["status"]!="recording":raise RuntimeError("recording is closed")
        op=str(action).strip().lower()
        if op not in self.ALLOWED_ACTIONS:raise ValueError("unsupported recorded action")
        data["steps"].append({"action":op,"target":str(target)[:500],"value":str(value)[:2000],"evidence":list(evidence or [])[:10]})
        path.write_text(json.dumps(data,indent=2),encoding="utf-8");return data

    def finish(self,session_id):
        path=self.root/f"{session_id}.json";data=json.loads(path.read_text(encoding="utf-8"))
        if not data["steps"]:raise RuntimeError("cannot compile an empty workflow")
        data["status"]="candidate";data["finished_at"]=time.time();path.write_text(json.dumps(data,indent=2),encoding="utf-8")
        candidate=self.compiler.compile_candidate(data["name"],data["steps"],project=data["project"],evidence=[{"recording":str(path)}])
        return {"recording":data,"skill_candidate":candidate}
