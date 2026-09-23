from __future__ import annotations

"""Durable provider-neutral NARAD message inbox/outbox.

This store records message state only. It does not send anything itself: outbound
delivery remains a provider action behind Sudarshan/Policy approval.
"""

from pathlib import Path
import json
import os
import re
import tempfile
import time
import uuid


_SECRET_PATTERNS=(
    re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\b(api[_ -]?key|token|password|otp|pin)\s*[:=]\s*([^\s,;]+)"),
)


def _redact(text):
    value=str(text or "")
    value=_SECRET_PATTERNS[0].sub(r"\1[REDACTED]",value)
    value=_SECRET_PATTERNS[1].sub(lambda m:f"{m.group(1)}=[REDACTED]",value)
    return value[:20000]


class NaradMessageStore:
    VERSION="narad-messages-v1"
    DIRECTIONS={"inbox","outbox"}
    STATES={"received","draft","queued","sent","failed","archived"}

    def __init__(self,path):
        self.path=Path(path).resolve()
        self.rows=self._load()

    def _load(self):
        if not self.path.exists():return []
        try:
            raw=json.loads(self.path.read_text(encoding="utf-8-sig"))
            return list(raw.get("messages") or []) if raw.get("version")==self.VERSION else []
        except Exception:
            return []

    def _save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        payload={"schema":1,"version":self.VERSION,"messages":self.rows[-5000:],"updated_at":time.time()}
        fd,tmp=tempfile.mkstemp(prefix="narad-messages-",suffix=".json",dir=str(self.path.parent))
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as fh:json.dump(payload,fh,ensure_ascii=False,indent=2)
            os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

    def add(self,*,direction,provider,text,state=None,account_ref="",thread_ref="",sender="",recipients=None,metadata=None):
        direction=str(direction or "").strip().lower()
        if direction not in self.DIRECTIONS:raise ValueError("direction must be inbox or outbox")
        state=str(state or ("received" if direction=="inbox" else "draft")).strip().lower()
        if state not in self.STATES:raise ValueError("unsupported message state")
        if direction=="inbox" and state in {"draft","queued","sent"}:
            raise ValueError("inbox messages cannot use outbound states")
        row={
            "id":"MSG-"+uuid.uuid4().hex[:20],
            "direction":direction,
            "provider":str(provider or "").strip().lower()[:80],
            "account_ref":str(account_ref or "").strip()[:160],
            "thread_ref":str(thread_ref or "").strip()[:240],
            "sender":str(sender or "").strip()[:240],
            "recipients":[str(x)[:240] for x in (recipients or [])][:50],
            "text":_redact(text),
            "state":state,
            "metadata":dict(metadata or {}),
            "created_at":time.time(),
            "updated_at":time.time(),
        }
        if not row["provider"]:raise ValueError("provider is required")
        self.rows.append(row);self._save();return dict(row)

    def transition(self,message_id,state,*,provider_receipt=None,error=""):
        state=str(state or "").strip().lower()
        if state not in self.STATES:raise ValueError("unsupported message state")
        for row in self.rows:
            if row.get("id")!=message_id:continue
            if row.get("direction")!="outbox" and state in {"draft","queued","sent"}:
                raise ValueError("only outbox messages can transition to outbound states")
            row["state"]=state;row["updated_at"]=time.time()
            if provider_receipt is not None:row["provider_receipt"]=provider_receipt
            if error:row["error"]=_redact(error)[:1000]
            self._save();return dict(row)
        raise KeyError("message not found")

    def list(self,*,direction=None,state=None,provider=None,limit=200):
        rows=list(reversed(self.rows))
        if direction:rows=[x for x in rows if x.get("direction")==direction]
        if state:rows=[x for x in rows if x.get("state")==state]
        if provider:rows=[x for x in rows if x.get("provider")==provider]
        return rows[:max(1,min(int(limit),1000))]

    def status(self):
        return {
            "version":self.VERSION,
            "count":len(self.rows),
            "inbox":sum(1 for x in self.rows if x.get("direction")=="inbox"),
            "outbox":sum(1 for x in self.rows if x.get("direction")=="outbox"),
            "authority":"record/state only; delivery remains Sudarshan-gated provider action",
            "ready":True,
        }
