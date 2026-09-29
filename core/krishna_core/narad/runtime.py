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

from .contracts import RetryPolicy, required_permissions
from .context import build_node_payload
from .retry import run_with_retry
from .workflow_graph import WorkflowGraph
from .connector_registry import ConnectorRegistry
from .execution_gate import BoundedExecutionGate


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
        self.checkpoints={}
        self.load_error=None
        self.sudarshan=None
        self.connectors=ConnectorRegistry()
        self.execution_gate=BoundedExecutionGate()
        self._register_default_connectors()
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

    def bind_sudarshan(self,control_plane):
        self.sudarshan=control_plane
        return self.status()

    def _register_default_connectors(self):
        for provider,operation,mutating,permission,retry_safe in (
            ("n8n","trigger_workflow",True,"send_external",False),
            ("webhook","post",True,"send_external",False),
            ("telegram","send_message",True,"send_external",False),
            ("discord","send_message",True,"send_external",False),
            ("slack","send_message",True,"send_external",False),
            ("whatsapp","send_message",True,"send_external",False),
            ("gmail","send_email",True,"send_external",False),
            ("gmail","list_messages",False,"provider.read",True),
            ("gmail","get_message",False,"provider.read",True),
            ("gmail","modify_labels",True,"send_external",False),
            ("gmail","trash_message",True,"send_external",False),
            ("gmail","untrash_message",True,"send_external",False),
            ("google_drive","list_files",False,"provider.read",True),
            ("google_drive","create_folder",True,"send_external",False),
            ("google_sheets","append_values",True,"send_external",False),
            ("google_calendar","create_event",True,"send_external",False),
        ):
            self.connectors.register(
                provider,operation,mutating=mutating,permission=permission,
                retry_safe=retry_safe,
            )

    def workflow_plan(self,workflow_id):
        self._healthy()
        with self._lock:
            w=self.workflows[str(workflow_id)]
            graph=WorkflowGraph(list(w.steps))
        external=[]
        for node in graph.nodes:
            if node.action=="narad.provider_send":
                p=node.payload
                provider=str(p.get("provider") or "").strip().lower()
                operation=str(p.get("operation") or "").strip().lower()
                if provider and operation:
                    try:external.append(self.connectors.get(provider,operation).as_dict())
                    except KeyError:external.append({"provider":provider,"operation":operation,"registered":False})
            elif node.action=="narad.adapter_webhook":
                provider=str(node.payload.get("provider") or "webhook").strip().lower()
                external.append({"provider":provider,"operation":"post","registered":provider in self.adapters})
        return {
            "workflow_id":w.id,"name":w.name,"state":w.state,"version":w.version,
            "trigger":dict(w.trigger),"permissions":list(w.permissions),
            "order":list(graph.order),"nodes":graph.normalized_steps(),
            "external_connectors":external,
            "execution_authority":"Sudarshan Control Plane" if self.sudarshan else "legacy-standalone",
            "verification":"IndependentCriticVerifier required" if self.sudarshan else "legacy",
        }
    def _load(self):
        if not self.state_path or not self.state_path.exists():
            return
        try:
            raw=json.loads(self.state_path.read_text(encoding="utf-8-sig"))
            if not isinstance(raw,dict):raise ValueError("Narad state root must be an object")
            schema=raw.get("schema",3)
            if schema!=3:raise ValueError(f"unsupported Narad state schema: {schema!r}")
            self.workflows={x["id"]:Workflow(**x) for x in raw.get("workflows",[]) if x.get("id")}
            self.history=list(raw.get("history",[]))[-500:]
            self.dead_letters=list(raw.get("dead_letters",[]))[-200:]
            self.schedule_state={str(k):float(v) for k,v in (raw.get("schedule_state") or {}).items()}
            self.webhook_hashes={str(k):str(v) for k,v in (raw.get("webhook_hashes") or {}).items()}
            self.checkpoints={str(k):dict(v) for k,v in (raw.get("checkpoints") or {}).items()}
        except Exception as exc:
            self.workflows={};self.history=[];self.dead_letters=[];self.schedule_state={};self.webhook_hashes={};self.checkpoints={}
            self.load_error=f"{type(exc).__name__}: {exc}"
        else:
            self.load_error=None

    def _healthy(self):
        if self.load_error:
            raise RuntimeError("Narad durable state is unreadable; refusing execution or mutation: "+self.load_error)

    def _save(self):
        self._healthy()
        if not self.state_path:
            return
        self.state_path.parent.mkdir(parents=True,exist_ok=True)
        with self._lock:
            payload={
                "schema":3,
                "workflows":[w.as_dict() for w in self.workflows.values()],
                "history":self.history[-500:],
                "dead_letters":self.dead_letters[-200:],
                "schedule_state":dict(self.schedule_state),
                "webhook_hashes":dict(self.webhook_hashes),
                "checkpoints":dict(list(self.checkpoints.items())[-100:]),
            }
        fd,tmp=tempfile.mkstemp(prefix="narad-",suffix=".json",dir=str(self.state_path.parent))
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as h:
                json.dump(payload,h,ensure_ascii=False,indent=2)
            os.replace(tmp,self.state_path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

    def create_workflow(self,name,trigger,steps,permissions=None):
        self._healthy()
        name=str(name or "").strip()
        if not name: raise ValueError("workflow name is required")
        graph=WorkflowGraph(steps)
        clean_trigger=self._validate_trigger(trigger)
        derived=required_permissions(graph.nodes)
        grants=sorted(set(str(x) for x in (permissions or []) if str(x).strip())|set(derived))
        w=Workflow(str(uuid.uuid4()),name,clean_trigger,list(steps),permissions=grants,created_at=self._now_iso())
        with self._lock:self.workflows[w.id]=w
        self._save()
        self.bus.publish("narad.workflow.created",{
            "workflow_id":w.id,"name":name,"nodes":len(graph.nodes),"permissions":grants,
        },source="narad")
        return w.as_dict()

    def promote(self,workflow_id,state,verified=False,approved=False):
        self._healthy()
        with self._lock:
            w=self.workflows[workflow_id]
            target=WorkflowState(state)
            if target in (WorkflowState.VERIFIED,WorkflowState.STABLE) and not approved:
                raise PermissionError("verified/stable workflow promotion requires explicit owner approval")
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

    def _dead_letter(self,w,version,trigger_source,context,exc):
        letter={
            "id":str(uuid.uuid4()),"workflow_id":w.id,"version":version,
            "trigger_source":trigger_source,"context":dict(context or {}),
            "error":f"{type(exc).__name__}: {exc}","status":"pending","at":self._now_iso(),
        }
        with self._lock:
            self.dead_letters.append(letter);self.dead_letters=self.dead_letters[-200:]
        self._save()
        return letter

    def _execute_via_sudarshan(self,w,steps,context,approved,trigger_source,version,resume_run_id=None):
        graph=WorkflowGraph(steps)
        if resume_run_id:
            with self._lock:
                cp=dict(self.checkpoints.get(str(resume_run_id)) or {})
            if not cp:raise KeyError("Narad checkpoint not found")
            if cp.get("workflow_id")!=w.id or int(cp.get("version") or 0)!=int(version):
                raise RuntimeError("Narad checkpoint workflow/version mismatch")
            run_id=str(resume_run_id)
            project=str(cp.get("project") or context.get("project") or "KRISHNA")
            context=dict(cp.get("context") or context or {})
            node_outputs=dict(cp.get("node_outputs") or {})
            completed=set(cp.get("completed") or [])
            # Resume restores only independently verified completed nodes. Prior
            # failed/skipped rows are attempt history, not final verification
            # evidence; those nodes must execute again from a clean failure set.
            node_runs=[
                dict(row) for row in (cp.get("node_runs") or [])
                if row.get("node_id") in completed
                and bool((row.get("verification") or {}).get("passed"))
            ]
            results=list(cp.get("results") or [])
            failed=set()
        else:
            run_id=str(uuid.uuid4())
            project=str(context.get("project") or "KRISHNA")
            node_outputs={}
            node_runs=[]
            results=[]
            failed=set()
            completed=set()
            with self._lock:
                self.checkpoints[run_id]={
                    "run_id":run_id,"workflow_id":w.id,"version":version,"project":project,
                    "context":dict(context),"trigger_source":trigger_source,"completed":[],
                    "failed":[],"node_outputs":{},"node_runs":[],"results":[],
                    "status":"running","updated_at":self._now_iso(),
                }
            self._save()
        external_actions={"narad.adapter_webhook","narad.provider_send"}

        for node_id in graph.order:
            if node_id in completed:continue
            node=graph.by_id[node_id]
            if any(dep in failed for dep in node.depends_on):
                row={
                    "node_id":node.id,"action":node.action,"dispatch":node.dispatch,
                    "status":"skipped","reason":"dependency_failed","verification":{
                        "status":"FAIL","passed":False,"checks":[],"evidence":[],
                        "reason":"dependency failed",
                    },
                }
                node_runs.append(row);failed.add(node.id)
                with self._lock:
                    self.checkpoints[run_id]={
                        "run_id":run_id,"workflow_id":w.id,"version":version,"project":project,
                        "context":dict(context),"trigger_source":trigger_source,
                        "completed":sorted(completed),"failed":sorted(failed),
                        "node_outputs":node_outputs,"node_runs":node_runs,"results":results,
                        "status":"running","updated_at":self._now_iso(),
                    }
                self._save()
                continue

            if node.action in external_actions and w.state!=WorkflowState.STABLE.value:
                raise PermissionError("external Narad side effects require a Stable verified workflow")

            payload=build_node_payload(node.payload,context,node_outputs)
            if node.action in external_actions:
                inner=dict(payload.get("payload") or {})
                payload["payload"]={**inner,**context}

            policy=node.retry
            if node.action in external_actions and policy.max_attempts>1 and not policy.retry_safe:
                policy=RetryPolicy(1,policy.delay_ms,policy.backoff,False)

            def invoke(_attempt):
                key=f"narad:{w.id}:{run_id}:{node.id}"
                if node.dispatch=="job":
                    return self.sudarshan.job(
                        node.action,payload,project=project,actor=f"narad:{w.id}",
                        permissions=w.permissions,approved=approved,idempotency_key=key,
                    )
                return self.sudarshan.action(
                    node.action,payload,project=project,source="job",actor=f"narad:{w.id}",
                    permissions=w.permissions,approved=approved,idempotency_key=key,
                )

            try:
                executed,attempts=run_with_retry(invoke,policy)
                receipt=executed["action"] if node.dispatch=="job" else executed
                actual=receipt.get("result")
                verification=executed.get("verification") or receipt.get("verification") or {}
                row={
                    "node_id":node.id,"action":node.action,"dispatch":node.dispatch,
                    "status":"verified" if verification.get("passed") else "rejected",
                    "action_id":receipt.get("action_id"),"job_id":executed.get("job_id") if node.dispatch=="job" else None,
                    "attempts":attempts,"verification":verification,
                }
                node_runs.append(row)
                node_outputs[node.id]={"result":actual,"receipt":receipt}
                results.append(actual)
                completed.add(node.id)
                with self._lock:
                    self.checkpoints[run_id]={
                        "run_id":run_id,"workflow_id":w.id,"version":version,"project":project,
                        "context":dict(context),"trigger_source":trigger_source,
                        "completed":sorted(completed),"failed":sorted(failed),
                        "node_outputs":node_outputs,"node_runs":node_runs,"results":results,
                        "status":"running","updated_at":self._now_iso(),
                    }
                self._save()
                if not verification.get("passed"):
                    failed.add(node.id)
                    if not node.continue_on_error:
                        raise RuntimeError(f"{node.id}: independent verification failed")
            except Exception as exc:
                failed.add(node.id)
                row={
                    "node_id":node.id,"action":node.action,"dispatch":node.dispatch,
                    "status":"failed","error":f"{type(exc).__name__}: {exc}",
                    "verification":{"status":"FAIL","passed":False,"checks":[],"evidence":[],"reason":str(exc)},
                }
                node_runs.append(row)
                if not node.continue_on_error:
                    if isinstance(exc,KeyError):
                        raise RuntimeError(f"unsupported or unavailable Narad action: {node.action}") from exc
                    raise

        workflow_verification=self.sudarshan.verify_workflow(node_runs)
        if not workflow_verification.get("passed"):
            raise RuntimeError("independent verifier rejected NARAD workflow: "+str(workflow_verification.get("reason")))

        record={
            "id":run_id,"workflow_id":w.id,"version":version,"trigger_source":trigger_source,
            "results":results,"nodes":node_runs,"verification":workflow_verification,
            "execution_authority":"Sudarshan Control Plane","at":self._now_iso(),
        }
        with self._lock:
            self.history.append(record);self.history=self.history[-500:]
            self.checkpoints.pop(run_id,None)
        self._save()
        self.bus.publish("narad.workflow.completed",record,source="narad")
        return record

    def _execute_guarded(self,workflow_id,context=None,approved=False,trigger_source="manual"):
        self._healthy()
        with self._lock:
            w=self.workflows[workflow_id]
            state=w.state
            steps=list(w.steps)
            version=w.version
        if state not in {WorkflowState.SANDBOX.value,WorkflowState.VERIFIED.value,WorkflowState.STABLE.value}:
            raise RuntimeError("workflow is not executable")
        context=dict(context or {})
        if self.sudarshan:
            try:
                return self._execute_via_sudarshan(w,steps,context,approved,trigger_source,version)
            except Exception as exc:
                self._dead_letter(w,version,trigger_source,context,exc)
                raise
        results=[]
        try:
            for step in steps:
                action=str(step.get("action","")).strip()
                external=action in {"adapter_webhook","provider_send"}
                if external and state!=WorkflowState.STABLE.value:
                    raise PermissionError("external Narad side effects require a Stable verified workflow")
                mutating=bool(step.get("mutating",False)) or external
                policy_action="send_external" if external else action
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

    def execute(self,workflow_id,context=None,approved=False,trigger_source="manual"):
        with self.execution_gate.slot():
            return self._execute_guarded(workflow_id,context,approved,trigger_source)
    def handle_event(self,topic,payload=None):
        self._healthy()
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
        self._healthy()
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
        self._healthy()
        with self._lock:
            w=self.workflows[workflow_id]
            if w.trigger.get("type")!="webhook":raise ValueError("workflow is not configured for webhook trigger")
            token=secrets.token_urlsafe(32)
            self.webhook_hashes[w.id]=hashlib.sha256(token.encode()).hexdigest()
        self._save()
        return {"workflow_id":w.id,"token":token,"path":"/api/narad/webhook/"+token,
                "warning":"Token is shown once. KRISHNA stores only its hash."}

    def handle_webhook(self,token,payload=None):
        self._healthy()
        digest=hashlib.sha256(str(token).encode()).hexdigest()
        with self._lock:
            matches=[wid for wid,h in self.webhook_hashes.items() if secrets.compare_digest(h,digest)]
            if not matches: raise PermissionError("invalid Narad webhook token")
            wid=matches[0];w=self.workflows.get(wid)
            if not w or w.state!=WorkflowState.STABLE.value:raise PermissionError("Narad webhook workflow is not Stable")
        return self.execute(wid,{"webhook":payload or {}},approved=False,trigger_source="webhook")

    def resume_checkpoint(self,run_id,approved=False):
        self._healthy()
        if not self.sudarshan:raise RuntimeError("Sudarshan control plane is required for checkpoint resume")
        with self._lock:
            cp=dict(self.checkpoints.get(str(run_id)) or {})
        if not cp:raise KeyError("Narad checkpoint not found")
        w=self.workflows.get(str(cp.get("workflow_id") or ""))
        if not w:raise KeyError("Narad checkpoint workflow not found")
        if w.state not in {WorkflowState.SANDBOX.value,WorkflowState.VERIFIED.value,WorkflowState.STABLE.value}:
            raise RuntimeError("workflow is not executable")
        try:
            with self.execution_gate.slot():
                return self._execute_via_sudarshan(
                    w,list(w.steps),dict(cp.get("context") or {}),approved,
                    str(cp.get("trigger_source") or "resume"),w.version,resume_run_id=str(run_id),
                )
        except Exception as exc:
            self._dead_letter(w,w.version,"resume",cp.get("context") or {},exc)
            raise

    def retry_dead_letter(self,letter_id,approved=False):
        self._healthy()
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
                "history":len(self.history),"dead_letters":len(self.dead_letters),"checkpoints":len(self.checkpoints),"adapters":sorted(self.adapters),
                "states":[x.value for x in WorkflowState],"triggers":triggers,
                "connections":self.credentials.list()["count"] if self.credentials else 0,
                "scheduler_ready":True,"webhook_gateway":True,
                "provider_hub":self.provider_hub.providers() if self.provider_hub else [],
                "workflow_engine":"typed-dag/sudarshan" if self.sudarshan else "legacy-standalone",
                "sudarshan_bound":bool(self.sudarshan),
                "node_contracts":["action","job"],"retry_max_attempts":5,
                "data_mapping":"safe ${input.*} / ${nodes.*}; no eval",
                "execution_gate":self.execution_gate.status(),
                "connector_registry":self.connectors.status(),
                "n8n":self.adapters["n8n"].status() if "n8n" in self.adapters and hasattr(self.adapters["n8n"],"status") else {"available":False},
                "available":not bool(self.load_error),"load_error":self.load_error,
            }
