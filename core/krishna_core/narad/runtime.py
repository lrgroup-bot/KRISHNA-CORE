from __future__ import annotations
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
import json, os, tempfile, uuid

class WorkflowState(str,Enum):
    DRAFT="draft"; CANDIDATE="candidate"; SANDBOX="sandbox"; VERIFIED="verified"; STABLE="stable"; REJECTED="rejected"

@dataclass
class Workflow:
    id:str; name:str; trigger:dict; steps:list; state:str=WorkflowState.DRAFT.value
    permissions:list=field(default_factory=list); version:int=1; created_at:str=""
    def as_dict(self): return asdict(self)

class NaradRuntime:
    """KRISHNA-native durable automation/messaging control plane."""
    def __init__(self,policy,bus,adapters=None,state_path=None):
        self.policy=policy; self.bus=bus; self.adapters=dict(adapters or {})
        self.state_path=Path(state_path) if state_path else None
        self.workflows={}; self.history=[]; self.dead_letters=[]
        self._load()
    def register_adapter(self,name,adapter): self.adapters[name]=adapter
    def _load(self):
        if not self.state_path or not self.state_path.exists(): return
        try:
            raw=json.loads(self.state_path.read_text(encoding="utf-8"))
            self.workflows={x["id"]:Workflow(**x) for x in raw.get("workflows",[])}
            self.history=list(raw.get("history",[]))[-500:]
            self.dead_letters=list(raw.get("dead_letters",[]))[-200:]
        except Exception:
            self.workflows={}; self.history=[]; self.dead_letters=[]
    def _save(self):
        if not self.state_path:return
        self.state_path.parent.mkdir(parents=True,exist_ok=True)
        payload={"schema":1,"workflows":[w.as_dict() for w in self.workflows.values()],"history":self.history[-500:],"dead_letters":self.dead_letters[-200:]}
        fd,tmp=tempfile.mkstemp(prefix="narad-",suffix=".json",dir=str(self.state_path.parent))
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as h: json.dump(payload,h,ensure_ascii=False,indent=2)
            os.replace(tmp,self.state_path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
    def create_workflow(self,name,trigger,steps,permissions=None):
        w=Workflow(str(uuid.uuid4()),name,dict(trigger),list(steps),permissions=list(permissions or []),created_at=datetime.now(timezone.utc).isoformat())
        self.workflows[w.id]=w; self._save()
        self.bus.publish("narad.workflow.created",{"workflow_id":w.id,"name":name},source="narad"); return w.as_dict()
    def promote(self,workflow_id,state,verified=False):
        w=self.workflows[workflow_id]; target=WorkflowState(state)
        if target in (WorkflowState.VERIFIED,WorkflowState.STABLE) and not verified: raise PermissionError("verified evidence required for promotion")
        allowed={
            WorkflowState.DRAFT:{WorkflowState.CANDIDATE,WorkflowState.SANDBOX,WorkflowState.REJECTED},
            WorkflowState.CANDIDATE:{WorkflowState.SANDBOX,WorkflowState.REJECTED},
            WorkflowState.SANDBOX:{WorkflowState.VERIFIED,WorkflowState.REJECTED},
            WorkflowState.VERIFIED:{WorkflowState.STABLE,WorkflowState.REJECTED},
            WorkflowState.STABLE:{WorkflowState.REJECTED},
            WorkflowState.REJECTED:set(),
        }
        current=WorkflowState(w.state)
        if target not in allowed[current]: raise RuntimeError(f"invalid workflow transition: {current.value} -> {target.value}")
        w.state=target.value; w.version+=1; self._save(); return w.as_dict()
    def execute(self,workflow_id,context=None,approved=False):
        w=self.workflows[workflow_id]
        if w.state not in {WorkflowState.SANDBOX.value,WorkflowState.VERIFIED.value,WorkflowState.STABLE.value}: raise RuntimeError("workflow is not executable")
        results=[]
        try:
            for step in w.steps:
                action=str(step.get("action",""))
                mutating=bool(step.get("mutating",False)) or action=="adapter_webhook"
                policy_action="send_external" if action=="adapter_webhook" else action
                decision=self.policy.action(policy_action,mutating=mutating,approved=approved)
                if not decision.allowed: raise PermissionError(decision.reason)
                if action=="publish_event": results.append(self.bus.publish(step["topic"],step.get("payload",{}),source="narad"))
                elif action=="adapter_webhook":
                    provider=step["provider"]
                    if provider not in self.adapters: raise RuntimeError(f"Narad adapter unavailable: {provider}")
                    results.append(self.adapters[provider].post(step["url"],{**step.get("payload",{}),**(context or {})}))
                else: results.append({"action":action,"status":"delegated"})
        except Exception as exc:
            self.dead_letters.append({"workflow_id":w.id,"version":w.version,"error":f"{type(exc).__name__}: {exc}","at":datetime.now(timezone.utc).isoformat()})
            self._save(); raise
        record={"workflow_id":w.id,"version":w.version,"results":results,"at":datetime.now(timezone.utc).isoformat()}
        self.history.append(record); self.history=self.history[-500:]; self._save()
        self.bus.publish("narad.workflow.completed",record,source="narad"); return record
    def handle_event(self,topic,payload=None):
        matches=[w for w in self.workflows.values() if w.state==WorkflowState.STABLE.value and w.trigger.get("type")=="event" and w.trigger.get("topic")==topic]
        return [self.execute(w.id,{"event":payload or {}},approved=False) for w in matches]
    def status(self):
        return {"name":"NARAD","durable":bool(self.state_path),"workflows":len(self.workflows),"history":len(self.history),"dead_letters":len(self.dead_letters),"adapters":sorted(self.adapters),"states":[x.value for x in WorkflowState]}
