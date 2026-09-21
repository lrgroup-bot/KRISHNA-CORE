from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
import hashlib
import json
import os
import secrets
import tempfile
import threading
import time
import uuid


class WorkflowState(str, Enum):
    DRAFT="draft"; CANDIDATE="candidate"; SANDBOX="sandbox"; VERIFIED="verified"; STABLE="stable"; REJECTED="rejected"


@dataclass
class Workflow:
    id: str
    name: str
    trigger: dict
    steps: list
    state: str = WorkflowState.DRAFT.value
    permissions: list = field(default_factory=list)
    version: int = 1
    created_at: str = ""
    def as_dict(self): return asdict(self)


class NaradRuntime:
    """KRISHNA-native durable automation/messaging control plane.

    Workflows are data, not authority. Stable promotion needs verification; external
    side effects still pass through PolicyKernel and require explicit approval.
    """

    TRIGGERS={"manual","event","schedule","webhook"}

    def __init__(self, policy, bus, adapters=None, state_path=None, credentials=None, provider_hub=None):
        self.policy=policy
        self.bus=bus
        self.adapters=dict(adapters or {})
        self.state_path=Path(state_path) if state_path else None
        self.credentials=credentials
        self.provider_hub=provider_hub
        self.workflows={}
        self.history=[]
        self.dead_letters=[]
        self.schedule_state={}
        self.webhook_hashes={}
        self._lock=threading.RLock()
        self._load()

    @staticmethod
    def _now_iso():
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def _validate_trigger(cls, trigger):
        trigger=dict(trigger or {"type":"manual"})
        kind=str(trigger.get("type") or "manual").strip().lower()
        if kind not in cls.TRIGGERS:
            raise ValueError(f"unsupported Narad trigger: {kind}")
        trigger["type"]=kind
        if kind=="event":
            topic=str(trigger.get("topic") or "").strip()
            if not topic: raise ValueError("event trigger requires topic")
            trigger["topic"]=topic
        elif kind=="schedule":
            every=int(trigger.get("every_seconds") or 0)
            if every < 60: raise ValueError("schedule every_seconds must be at least 60")
            trigger["every_seconds"]=every
        return trigger

    def register_adapter(self,name,adapter):
        self.adapters[str(name)]=adapter

    def _load(self):
        if not self.state_path or not self.state_path.exists():
            return
        try:
            raw=json.loads(self.state_path.read_text(encoding="utf-8-sig"))
            self.workflows={x["id"]:Workflow(**x) for x in raw.get("workflows",[]) if x.get("id")}
            self.history=list(raw.get("history",[]))[-500:]
            self.dead_letters=list(raw.get("dead_letters",[]))[-200:]
            self.schedule_state={str(k):float(v) for k,v in (raw.get("schedule_state") or {}).items()}
            self.webhook_hashes={str(k):str(v) for k,v in (raw.get("webhook_hashes") or {}).items()}
        except Exception:
            self.workflows={};self.history=[];self.dead_letters=[];self.schedule_state={};self.webhook_hashes={}

    def _save(self):
        if not self.state_path:
            return
        self.state_path.parent.mkdir(parents=True,exist_ok=True)
        with self._lock:
            payload={
                "schema":2,
                "workflows":[w.as_dict() for w in self.workflows.values()],
                "history":self.history[-500:],
                "dead_letters":self.dead_letters[-200:],
                "schedule_state":dict(self.schedule_state),
                "webhook_hashes":dict(self.webhook_hashes),
            }
        fd,tmp=tempfile.mkstemp(prefix="narad-",suffix=".json",dir=str(self.state_path.parent))
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as h:
                json.dump(payload,h,ensure_ascii=False,indent=2)
            os.replace(tmp,self.state_path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

    def create_workflow(self,name,trigger,steps,permissions=None):
        name=str(name or "").strip()
        if not name: raise ValueError("workflow name is required")
        if not isinstance(steps,list) or not steps: raise ValueError("workflow requires at least one step")
        clean_trigger=self._validate_trigger(trigger)
        w=Workflow(str(uuid.uuid4()),name,clean_trigger,list(steps),permissions=list(permissions or []),created_at=self._now_iso())
        with self._lock:self.workflows[w.id]=w
        self._save()
        self.bus.publish("narad.workflow.created",{"workflow_id":w.id,"name":name},source="narad")
        return w.as_dict()

    def promote(self,workflow_id,state,verified=False):
        with self._lock:
            w=self.workflows[workflow_id]
            target=WorkflowState(state)
            if target in (WorkflowState.VERIFIED,WorkflowState.STABLE) and not verified:
                raise PermissionError("verified evidence required for promotion")
            allowed={
                WorkflowState.DRAFT:{WorkflowState.CANDIDATE,WorkflowState.SANDBOX,WorkflowState.REJECTED},
                WorkflowState.CANDIDATE:{WorkflowState.SANDBOX,WorkflowState.REJECTED},
                WorkflowState.SANDBOX:{WorkflowState.VERIFIED,WorkflowState.REJECTED},
                WorkflowState.VERIFIED:{WorkflowState.STABLE,WorkflowState.REJECTED},
                WorkflowState.STABLE:{WorkflowState.REJECTED},
                WorkflowState.REJECTED:set(),
            }
            current=WorkflowState(w.state)
            if target not in allowed[current]:
                raise RuntimeError(f"invalid workflow transition: {current.value} -> {target.value}")
            w.state=target.value
            w.version+=1
            result=w.as_dict()
        self._save()
        return result

    def execute(self,workflow_id,context=None,approved=False,trigger_source="manual"):
        with self._lock:
            w=self.workflows[workflow_id]
            state=w.state
            steps=list(w.steps)
            version=w.version
        if state not in {WorkflowState.SANDBOX.value,WorkflowState.VERIFIED.value,WorkflowState.STABLE.value}:
            raise RuntimeError("workflow is not executable")
        context=dict(context or {})
        results=[]
        try:
            for step in steps:
                action=str(step.get("action","")).strip()
                mutating=bool(step.get("mutating",False)) or action in {"adapter_webhook","provider_send"}
                policy_action="send_external" if action in {"adapter_webhook","provider_send"} else action
                decision=self.policy.action(policy_action,mutating=mutating,approved=approved)
                if not decision.allowed: raise PermissionError(decision.reason)
                if action=="publish_event":
                    results.append(self.bus.publish(str(step.get("topic") or ""),step.get("payload",{}),source="narad"))
                elif action=="adapter_webhook":
                    provider=str(step.get("provider") or "").strip()
                    if provider not in self.adapters: raise RuntimeError(f"Narad adapter unavailable: {provider}")
                    headers={}
                    credential_ref=step.get("credential_ref")
                    if credential_ref:
                        if not self.credentials: raise RuntimeError("Narad credential vault is unavailable")
                        headers=self.credentials.headers(credential_ref)
                    results.append(self.adapters[provider].post(
                        str(step.get("url") or ""),
                        {**(step.get("payload") or {}),**context},
                        headers=headers,
                    ))
                elif action=="provider_send":
                    if not self.provider_hub:raise RuntimeError("Narad provider hub is unavailable")
                    provider=str(step.get("provider") or "").strip().lower()
                    operation=str(step.get("operation") or "").strip().lower()
                    credential_ref=step.get("credential_ref")
                    headers={}
                    if credential_ref:
                        if not self.credentials:raise RuntimeError("Narad credential vault is unavailable")
                        headers=self.credentials.headers(credential_ref)
                    payload={**(step.get("payload") or {}),**context}
                    results.append(self.provider_hub.send(provider,operation,payload,headers=headers))
                else:
                    raise RuntimeError(f"unsupported Narad action: {action}")
        except Exception as exc:
            letter={
                "id":str(uuid.uuid4()),"workflow_id":w.id,"version":version,
                "trigger_source":trigger_source,"context":context,
                "error":f"{type(exc).__name__}: {exc}","status":"pending","at":self._now_iso(),
            }
            with self._lock:
                self.dead_letters.append(letter);self.dead_letters=self.dead_letters[-200:]
            self._save()
            raise
        record={
            "id":str(uuid.uuid4()),"workflow_id":w.id,"version":version,"trigger_source":trigger_source,
            "results":results,"at":self._now_iso(),
        }
        with self._lock:
            self.history.append(record);self.history=self.history[-500:]
        self._save()
        self.bus.publish("narad.workflow.completed",record,source="narad")
        return record

    def handle_event(self,topic,payload=None):
        with self._lock:
            matches=[w.id for w in self.workflows.values()
                     if w.state==WorkflowState.STABLE.value and w.trigger.get("type")=="event"
                     and w.trigger.get("topic")==topic]
        out=[]
        for wid in matches:
            try:out.append(self.execute(wid,{"event":payload or {}},approved=False,trigger_source="event"))
            except Exception as exc:out.append({"workflow_id":wid,"error":f"{type(exc).__name__}: {exc}"})
        return out

    def run_due(self,now=None):
        now=float(now or time.time())
        with self._lock:
            due=[]
            for w in self.workflows.values():
                if w.state!=WorkflowState.STABLE.value or w.trigger.get("type")!="schedule":continue
                every=int(w.trigger.get("every_seconds") or 0)
                last=float(self.schedule_state.get(w.id,0))
                if every>=60 and now-last>=every:
                    self.schedule_state[w.id]=now
                    due.append(w.id)
        if due:self._save()
        results=[]
        for wid in due:
            try:results.append({"workflow_id":wid,"ok":True,"result":self.execute(wid,{"scheduled_at":now},False,"schedule")})
            except Exception as exc:results.append({"workflow_id":wid,"ok":False,"error":f"{type(exc).__name__}: {exc}"})
        return {"checked_at":now,"due":len(due),"results":results}

    def provision_webhook(self,workflow_id):
        with self._lock:
            w=self.workflows[workflow_id]
            if w.trigger.get("type")!="webhook":raise ValueError("workflow is not configured for webhook trigger")
            token=secrets.token_urlsafe(32)
            self.webhook_hashes[w.id]=hashlib.sha256(token.encode()).hexdigest()
        self._save()
        return {"workflow_id":w.id,"token":token,"path":"/api/narad/webhook/"+token,
                "warning":"Token is shown once. KRISHNA stores only its hash."}

    def handle_webhook(self,token,payload=None):
        digest=hashlib.sha256(str(token).encode()).hexdigest()
        with self._lock:
            matches=[wid for wid,h in self.webhook_hashes.items() if secrets.compare_digest(h,digest)]
            if not matches: raise PermissionError("invalid Narad webhook token")
            wid=matches[0];w=self.workflows.get(wid)
            if not w or w.state!=WorkflowState.STABLE.value:raise PermissionError("Narad webhook workflow is not Stable")
        return self.execute(wid,{"webhook":payload or {}},approved=False,trigger_source="webhook")

    def retry_dead_letter(self,letter_id,approved=False):
        with self._lock:
            letter=next((x for x in self.dead_letters if x.get("id")==letter_id),None)
        if not letter:raise KeyError("Narad dead letter not found")
        if letter.get("status")=="retried":raise RuntimeError("Narad dead letter already retried")
        result=self.execute(letter["workflow_id"],letter.get("context") or {},approved,trigger_source="retry")
        with self._lock:
            letter["status"]="retried";letter["retried_at"]=self._now_iso();letter["retry_result_id"]=result["id"]
        self._save()
        return {"dead_letter":dict(letter),"result":result}

    def dead_letter_status(self):
        with self._lock:rows=list(reversed(self.dead_letters[-200:]))
        return {"dead_letters":rows,"count":len(rows)}

    def status(self):
        with self._lock:
            triggers={k:0 for k in self.TRIGGERS}
            for w in self.workflows.values():triggers[w.trigger.get("type","manual")]=triggers.get(w.trigger.get("type","manual"),0)+1
            return {
                "name":"NARAD","durable":bool(self.state_path),"workflows":len(self.workflows),
                "history":len(self.history),"dead_letters":len(self.dead_letters),"adapters":sorted(self.adapters),
                "states":[x.value for x in WorkflowState],"triggers":triggers,
                "connections":self.credentials.list()["count"] if self.credentials else 0,
                "scheduler_ready":True,"webhook_gateway":True,
                "provider_hub":self.provider_hub.providers() if self.provider_hub else [],
            }
