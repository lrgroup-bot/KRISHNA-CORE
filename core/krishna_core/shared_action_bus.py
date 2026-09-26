from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Callable
import hashlib
import json
import sqlite3
import time
import uuid


_SENSITIVE_KEYS={
    "password","secret","token","api_key","apikey","authorization","credential","credentials",
    "access_token","refresh_token","client_secret","bearer_token","auth_token","session_token",
}
_SENSITIVE_COMPACT_KEYS={
    "password","secret","token","apikey","authorization","credential","credentials",
    "accesstoken","refreshtoken","clientsecret","bearertoken","authtoken","sessiontoken",
}


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


class _DurableIdempotencyStore:
    """Small SQLite journal that prevents mutating/action retries from becoming
    duplicate execution after a KRISHNA process restart."""

    def __init__(self,db_path):
        self.db=sqlite3.connect(str(db_path),check_same_thread=False)
        self.db.row_factory=sqlite3.Row
        self.lock=RLock()
        with self.lock:
            self.db.execute("""CREATE TABLE IF NOT EXISTS action_idempotency(
              key_hash TEXT PRIMARY KEY,
              fingerprint TEXT NOT NULL,
              state TEXT NOT NULL,
              receipt_json TEXT,
              created_at REAL NOT NULL,
              updated_at REAL NOT NULL
            )""")
            self.db.commit()

    @staticmethod
    def _key_hash(key):
        return hashlib.sha256(str(key).encode("utf-8")).hexdigest()

    @staticmethod
    def _decode(row):
        if not row:return None
        out=dict(row)
        raw=out.pop("receipt_json",None)
        if raw:
            try:out["receipt"]=json.loads(raw)
            except Exception as exc:
                raise RuntimeError("idempotency receipt state is unreadable") from exc
        else:
            out["receipt"]=None
        return out

    def get(self,key):
        with self.lock:
            row=self.db.execute("SELECT * FROM action_idempotency WHERE key_hash=?",(self._key_hash(key),)).fetchone()
        return self._decode(row)

    def reserve(self,key,fingerprint,envelope):
        key_hash=self._key_hash(key);now=time.time()
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                row=self.db.execute("SELECT * FROM action_idempotency WHERE key_hash=?",(key_hash,)).fetchone()
                if row:
                    self.db.commit()
                    return False,self._decode(row)
                self.db.execute(
                    "INSERT INTO action_idempotency(key_hash,fingerprint,state,receipt_json,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                    (key_hash,str(fingerprint),"executing",json.dumps(dict(envelope),ensure_ascii=False,default=str),now,now),
                )
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
        return True,self.get(key)

    def finish(self,key,fingerprint,state,receipt):
        if state not in {"completed","failed"}:raise ValueError("invalid idempotency terminal state")
        key_hash=self._key_hash(key);now=time.time()
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                row=self.db.execute("SELECT fingerprint FROM action_idempotency WHERE key_hash=?",(key_hash,)).fetchone()
                if not row:raise RuntimeError("idempotency reservation is missing")
                if row["fingerprint"]!=str(fingerprint):raise ValueError("idempotency fingerprint mismatch")
                self.db.execute(
                    "UPDATE action_idempotency SET state=?,receipt_json=?,updated_at=? WHERE key_hash=?",
                    (state,json.dumps(dict(receipt),ensure_ascii=False,default=str),now,key_hash),
                )
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise

    def close(self):
        with self.lock:
            if self.db is not None:self.db.commit();self.db.close();self.db=None


class SharedActionBus:
    """Canonical action dispatch boundary for KRISHNA.

    UI, mobile, agents, jobs and protocol adapters should dispatch named actions
    here instead of calling runtime internals directly. The bus provides one
    action envelope, source/permission checks, policy approval gates, idempotency,
    audit events and optional rollback hooks. It never accepts raw shell text.
    """

    def __init__(self,event_bus,policy,audit:Callable|None=None,permission_resolver:Callable|None=None,
                 history_limit=500,idempotency_db_path=None):
        self.event_bus=event_bus
        self.policy=policy
        self.audit=audit
        self.permission_resolver=permission_resolver
        self.history_limit=max(50,int(history_limit))
        self._lock=RLock()
        self._handlers:dict[str,tuple[SharedActionSpec,Callable]]={}
        self._history:list[dict]=[]
        self._idempotent:dict[str,dict]={}
        self._idempotency_store=_DurableIdempotencyStore(idempotency_db_path) if idempotency_db_path else None

    @staticmethod
    def _now()->str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _is_sensitive_key(key):
        raw=str(key or "").strip().lower()
        # promotion_token is a bounded in-memory transaction identifier, not an
        # authentication credential. Redacting it from action results breaks the
        # verified candidate -> explicit approval -> promotion workflow.
        if raw=="promotion_token":
            return False
        if raw in _SENSITIVE_KEYS:
            return True
        compact="".join(ch for ch in raw if ch.isalnum())
        if compact in _SENSITIVE_COMPACT_KEYS:
            return True
        normalized=raw.replace("-","_").replace(" ","_")
        return normalized.startswith("authorization_") or normalized.endswith(
            ("_password","_secret","_token","_api_key","_apikey","_credential","_credentials")
        )

    @classmethod
    def _safe_payload(cls,payload):
        def clean(value,key="",depth=0,active=None):
            if cls._is_sensitive_key(key):
                return "[REDACTED]"
            if depth>64:
                return "[MAX_DEPTH]"
            active=set() if active is None else active
            if isinstance(value,(dict,list,tuple)):
                marker=id(value)
                if marker in active:
                    return "[CIRCULAR]"
                active.add(marker)
                try:
                    if isinstance(value,dict):
                        return {str(k):clean(v,str(k),depth+1,active) for k,v in value.items()}
                    return [clean(v,key,depth+1,active) for v in value[:100]]
                finally:
                    active.discard(marker)
            text=str(value) if not isinstance(value,(str,int,float,bool,type(None))) else value
            if isinstance(text,str) and len(text)>4000:
                return text[:4000]+"..."
            return text
        root=payload if isinstance(payload,dict) else dict(payload or {})
        return clean(root)

    @staticmethod
    def _idempotency_fingerprint(action,project,source,actor,payload):
        raw=json.dumps({
            "action":str(action),"project":str(project),"source":str(source),"actor":str(actor),
            "payload":payload or {},
        },sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def register(self,name,handler,*,description="",mutating=False,requires_approval=False,
                 permissions=(),sources=("pc","mobile","system","agent","job","mcp","a2a"),rollback_action=None,
                 replace=False)->dict:
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
            if key in self._handlers and not replace:
                raise ValueError(f"shared action already registered: {key}")
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
        fingerprint=None
        if idempotency_key:
            cache_key=str(idempotency_key)
            fingerprint=self._idempotency_fingerprint(name,project,source,actor,payload)
            with self._lock:
                cached=self._idempotent.get(cache_key)
            if cached is not None:
                if cached.get("_idempotency_fingerprint")!=fingerprint:
                    raise ValueError("idempotency key already used for a different action context or payload")
                replay={k:v for k,v in cached.items() if not str(k).startswith("_idempotency_")}
                replay["idempotent_replay"]=True
                return replay
            if self._idempotency_store is not None:
                existing=self._idempotency_store.get(cache_key)
                if existing is not None:
                    if existing.get("fingerprint")!=fingerprint:
                        raise ValueError("idempotency key already used for a different action context or payload")
                    if existing.get("state")=="completed" and isinstance(existing.get("receipt"),dict):
                        replay=dict(existing["receipt"]);replay["idempotent_replay"]=True
                        with self._lock:
                            cached=dict(existing["receipt"]);cached["_idempotency_fingerprint"]=fingerprint
                            self._idempotent[cache_key]=cached
                        return replay
                    raise RuntimeError(
                        "idempotent action has an indeterminate prior execution; verify state before issuing a new request"
                    )
                reserved,existing=self._idempotency_store.reserve(cache_key,fingerprint,{**envelope,"spec":spec.as_dict()})
                if not reserved:
                    if existing.get("fingerprint")!=fingerprint:
                        raise ValueError("idempotency key already used for a different action context or payload")
                    if existing.get("state")=="completed" and isinstance(existing.get("receipt"),dict):
                        replay=dict(existing["receipt"]);replay["idempotent_replay"]=True
                        return replay
                    raise RuntimeError(
                        "idempotent action is already executing or requires verification before retry"
                    )
        self._publish("action.requested",{**envelope,"spec":spec.as_dict()})
        try:
            result=handler(dict(payload or {}),context)
        except Exception as exc:
            # The original exception still propagates to the live caller for handling,
            # but durable/audit receipts retain only the exception class. Provider,
            # plugin or library errors can contain credentials in their message text.
            row={**envelope,"status":"failed","error":type(exc).__name__,"spec":spec.as_dict()}
            if idempotency_key and self._idempotency_store is not None:
                self._idempotency_store.finish(str(idempotency_key),fingerprint,"failed",row)
            self._record(row);self._publish("action.failed",row)
            raise
        safe_result=self._safe_payload(result) if isinstance(result,dict) else result
        row={
            **envelope,"status":"completed","completed_at":self._now(),
            "spec":spec.as_dict(),"result":safe_result,
        }
        if idempotency_key and self._idempotency_store is not None:
            self._idempotency_store.finish(str(idempotency_key),fingerprint,"completed",row)
        self._record(row);self._publish("action.completed",row)
        if idempotency_key:
            cached=dict(row)
            cached["_idempotency_fingerprint"]=fingerprint or self._idempotency_fingerprint(name,project,source,actor,payload)
            with self._lock:self._idempotent[str(idempotency_key)]=cached
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
            "durable_idempotency":self._idempotency_store is not None,
            "actions":self.list(),
            "policy":"all UI/mobile/agent actions should resolve to a registered shared action; no raw shell dispatch",
        }

    def close(self):
        if self._idempotency_store is not None:
            self._idempotency_store.close()
