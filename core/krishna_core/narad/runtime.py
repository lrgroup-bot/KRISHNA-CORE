from __future__ import annotations
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum
import uuid

class WorkflowState(str,Enum):
    DRAFT="draft"; CANDIDATE="candidate"; SANDBOX="sandbox"; VERIFIED="verified"; STABLE="stable"; REJECTED="rejected"

@dataclass
class Workflow:
    id:str; name:str; trigger:dict; steps:list; state:str=WorkflowState.DRAFT.value
    permissions:list=field(default_factory=list); version:int=1; created_at:str=""
    def as_dict(self): return asdict(self)

class NaradRuntime:
    """KRISHNA-native automation/messaging control plane. Providers are adapters, never owners."""
    def __init__(self,policy,bus,adapters=None):
        self.policy=policy; self.bus=bus; self.adapters=dict(adapters or {}); self.workflows={}; self.history=[]
    def register_adapter(self,name,adapter): self.adapters[name]=adapter
    def create_workflow(self,name,trigger,steps,permissions=None):
        w=Workflow(str(uuid.uuid4()),name,dict(trigger),list(steps),permissions=list(permissions or []),created_at=datetime.now(timezone.utc).isoformat())
        self.workflows[w.id]=w; self.bus.publish("narad.workflow.created",{"workflow_id":w.id,"name":name},source="narad"); return w.as_dict()
    def promote(self,workflow_id,state,verified=False):
        w=self.workflows[workflow_id]; target=WorkflowState(state)
        if target in (WorkflowState.VERIFIED,WorkflowState.STABLE) and not verified: raise PermissionError("verified evidence required for promotion")
        w.state=target.value; w.version+=1; return w.as_dict()
    def execute(self,workflow_id,context=None,approved=False):
        w=self.workflows[workflow_id]
        if w.state not in {WorkflowState.SANDBOX.value,WorkflowState.VERIFIED.value,WorkflowState.STABLE.value}: raise RuntimeError("workflow is not executable")
        results=[]
        for step in w.steps:
            action=str(step.get("action",""))
            mutating=bool(step.get("mutating",False)) or action=="adapter_webhook"
            policy_action="send_external" if action=="adapter_webhook" else action
            decision=self.policy.action(policy_action,mutating=mutating,approved=approved)
            if not decision.allowed: raise PermissionError(decision.reason)
            if action=="publish_event": results.append(self.bus.publish(step["topic"],step.get("payload",{}),source="narad"))
            elif action=="adapter_webhook":
                provider=step["provider"]; adapter=self.adapters[provider]
                results.append(adapter.post(step["url"],{**step.get("payload",{}),**(context or {})}))
            else: results.append({"action":action,"status":"delegated"})
        record={"workflow_id":w.id,"version":w.version,"results":results,"at":datetime.now(timezone.utc).isoformat()}
        self.history.append(record); self.history=self.history[-500:]; self.bus.publish("narad.workflow.completed",record,source="narad"); return record
    def status(self):
        return {"name":"NARAD","workflows":len(self.workflows),"history":len(self.history),"adapters":sorted(self.adapters),"states":[x.value for x in WorkflowState]}
