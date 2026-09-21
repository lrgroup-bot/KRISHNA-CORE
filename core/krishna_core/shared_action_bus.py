from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Callable
import json
import uuid


_SENSITIVE_KEYS={"password","secret","token","api_key","apikey","authorization","credential","credentials"}


@dataclass(frozen=True)
class SharedActionSpec:
    name: str
    description: str = ""
    mutating: bool = False
    requires_approval: bool = False
    permissions: tuple[str, ...] = ()
    sources: tuple[str, ...] = ("pc","mobile","system","agent","job","mcp","a2a")
    rollback_action: str | None = None

    def as_dict(self) -> dict:
        row=asdict(self)
        row["permissions"]=list(self.permissions)
        row["sources"]=list(self.sources)
        return row


class SharedActionBus:
    """Canonical action dispatch boundary for KRISHNA.

    UI, mobile, agents, jobs and protocol adapters should dispatch named actions
    here instead of calling runtime internals directly. The bus provides one
    action envelope, source/permission checks, policy approval gates, idempotency,
    audit events and optional rollback hooks. It never accepts raw shell text.
    """

    def __init__(self,event_bus,policy,audit:Callable|None=None,permission_resolver:Callable|None=None,history_limit=500):
        self.event_bus=event_bus
        self.policy=policy
        self.audit=audit
        self.permission_resolver=permission_resolver
        self.history_limit=max(50,int(history_limit))
        self._lock=RLock()
        self._handlers:dict[str,tuple[SharedActionSpec,Callable]]={}
        self._history:list[dict]=[]
        self._idempotent:dict[str,dict]={}

    @staticmethod
    def _now()->str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _safe_payload(payload):
        def clean(value,key=""):
            if key.lower() in _SENSITIVE_KEYS:
                return "[REDACTED]"
            if isinstance(value,dict):
                return {str(k):clean(v,str(k)) for k,v in value.items()}
            if isinstance(value,list):
                return [clean(v,key) for v in value[:100]]
            if isinstance(value,tuple):
                return [clean(v,key) for v in value[:100]]
            text=str(value) if not isinstance(value,(str,int,float,bool,type(None))) else value
            if isinstance(text,str) and len(text)>4000:
                return text[:4000]+"..."
            return text
        return clean(dict(payload or {}))

    def register(self,name,handler,*,description="",mutating=False,requires_approval=False,
                 permissions=(),sources=("pc","mobile","system","agent","job","mcp","a2a"),rollback_action=None)->dict:
        key=str(name or "").strip()
        if not key or any(ch.isspace() for ch in key):
            raise ValueError("shared action name must be a non-empty token")
        if not callable(handler):
            raise TypeError("shared action handler must be callable")
        spec=SharedActionSpec(
            name=key,description=str(description or ""),mutating=bool(mutating),
            requires_approval=bool(requires_approval),
            permissions=tuple(str(x) for x in permissions if str(x).strip()),
            sources=tuple(str(x) for x in sources if str(x).strip()),
            rollback_action=str(rollback_action) if rollback_action else None,
        )
        with self._lock:
            self._handlers[key]=(spec,handler)
        return spec.as_dict()

    def list(self)->list[dict]:
        with self._lock:
            rows=[spec.as_dict() for spec,_ in self._handlers.values()]
        return sorted(rows,key=lambda x:x["name"])

    def _record(self,row):
        with self._lock:
            self._history.append(dict(row))
            self._history=self._history[-self.history_limit:]
        if self.audit:
            try:
                detail={
                    "action_id":row.get("action_id"),"action":row.get("action"),"project":row.get("project"),
                    "source":row.get("source"),"actor":row.get("actor"),"status":row.get("status"),
                    "reason":row.get("reason"),"error":row.get("error"),"spec":row.get("spec"),
                    "created_at":row.get("created_at"),"completed_at":row.get("completed_at"),
                }
                self.audit(row["action_id"],row["status"],json.dumps(detail,ensure_ascii=False)[:12000])
            except Exception:
                pass

    def _publish(self,topic,payload):
        try:
            return self.event_bus.publish(topic,payload,source="shared-action-bus")
        except Exception:
            return None

    def dispatch(self,action,payload=None,*,project="KRISHNA",source="pc",actor="owner",
                 approved=False,permissions=(),idempotency_key=None)->dict:
        name=str(action or "").strip()
        source=str(source or "pc").strip().lower()
        project=str(project or "KRISHNA").strip() or "KRISHNA"
        actor=str(actor or "owner").strip() or "owner"
        with self._lock:
            pair=self._handlers.get(name)
            if idempotency_key and str(idempotency_key) in self._idempotent:
                cached=dict(self._idempotent[str(idempotency_key)])
                cached["idempotent_replay"]=True
                return cached
        if not pair:
            raise KeyError(f"shared action not registered: {name}")
        spec,handler=pair
        action_id=str(uuid.uuid4())
        envelope={
            "action_id":action_id,"action":name,"project":project,"source":source,"actor":actor,
            "approved":bool(approved),"permissions":list(permissions or []),
            "payload":self._safe_payload(payload),"created_at":self._now(),
        }
        if source not in spec.sources:
            row={**envelope,"status":"blocked","reason":"source_not_allowed","spec":spec.as_dict()}
            self._record(row);self._publish("action.blocked",row)
            raise PermissionError(f"action source not allowed: {source}")
        context={**envelope,"spec":spec.as_dict()}
        if self.permission_resolver:
            allowed,reason=self.permission_resolver(spec,context)
            if not allowed:
                row={**envelope,"status":"blocked","reason":str(reason or "permission_denied"),"spec":spec.as_dict()}
                self._record(row);self._publish("action.blocked",row)
                raise PermissionError(str(reason or "action permission denied"))
        # Low-risk state mutations can be marked mutating for audit without forcing
        # an approval dialog. PolicyKernel approval is invoked when this action's
        # contract explicitly requires approval.
        decision=self.policy.action(name,mutating=bool(spec.requires_approval),approved=bool(approved))
        if not decision.allowed:
            row={**envelope,"status":"blocked","reason":decision.reason,"policy":decision.as_dict(),"spec":spec.as_dict()}
            self._record(row);self._publish("action.blocked",row)
            raise PermissionError(decision.reason)
        self._publish("action.requested",{**envelope,"spec":spec.as_dict()})
        try:
            result=handler(dict(payload or {}),context)
        except Exception as exc:
            row={**envelope,"status":"failed","error":f"{type(exc).__name__}: {exc}","spec":spec.as_dict()}
            self._record(row);self._publish("action.failed",row)
            raise
        safe_result=self._safe_payload(result) if isinstance(result,dict) else result
        row={
            **envelope,"status":"completed","completed_at":self._now(),
            "spec":spec.as_dict(),"result":safe_result,
        }
        self._record(row);self._publish("action.completed",row)
        if idempotency_key:
            with self._lock:self._idempotent[str(idempotency_key)]=dict(row)
        return row

    def rollback(self,action_id,*,source="pc",actor="owner",approved=False)->dict:
        with self._lock:
            original=next((dict(x) for x in reversed(self._history) if x.get("action_id")==action_id),None)
        if not original:
            raise KeyError(f"action not found: {action_id}")
        spec_name=(original.get("spec") or {}).get("rollback_action")
        if not spec_name:
            raise ValueError("action has no registered rollback")
        if not approved:
            raise PermissionError("rollback requires explicit approval")
        return self.dispatch(
            spec_name,{"original_action":original},project=original.get("project") or "KRISHNA",
            source=source,actor=actor,approved=True,
            idempotency_key=f"rollback:{action_id}",
        )

    def recent(self,limit=50)->list[dict]:
        with self._lock:return [dict(x) for x in self._history[-max(0,int(limit)):]]

    def status(self)->dict:
        return {
            "owner":"KRISHNA Shared Action Bus",
            "registered_actions":len(self.list()),
            "recent_actions":len(self.recent(self.history_limit)),
            "actions":self.list(),
            "policy":"all UI/mobile/agent actions should resolve to a registered shared action; no raw shell dispatch",
        }
