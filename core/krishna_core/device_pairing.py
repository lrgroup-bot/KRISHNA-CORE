"""Local zero-code device-pairing store for KRISHNA PC <-> mobile trust.

Modern clients generate a high-entropy credential locally and send only its SHA-256
with the pairing request. After explicit approval on KRISHNA PC, the already-held
credential becomes valid; no pairing code or plaintext credential crosses the network.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib, json, secrets, threading, time


@dataclass
class PendingPair:
    request_id:str
    device_id:str
    name:str
    created_at:int
    expires_at:int
    credential_sha256:str=""


class DevicePairingStore:
    def __init__(self,state_dir:str|Path,ttl:int=300,max_pending:int=100):
        self.root=Path(state_dir)/"pairing"; self.root.mkdir(parents=True,exist_ok=True)
        self.pending_file=self.root/"pending.json"; self.paired_file=self.root/"paired.json"; self.ttl=ttl
        self.max_pending=max(1,int(max_pending));self._lock=threading.RLock()

    def _load(self,p):
        if not p.exists():return {}
        try:
            data=json.loads(p.read_text("utf-8"))
        except Exception as exc:
            raise RuntimeError(f"pairing state unreadable: {p.name}: {type(exc).__name__}") from exc
        if not isinstance(data,dict):
            raise RuntimeError(f"pairing state unreadable: {p.name}: expected JSON object")
        return data

    def _save(self,p,v):
        tmp=p.with_suffix(".tmp"); tmp.write_text(json.dumps(v,indent=2),"utf-8"); tmp.replace(p)

    @staticmethod
    def _valid_digest(value):
        value=str(value or "").strip().lower()
        return len(value)==64 and all(x in "0123456789abcdef" for x in value)

    def request(self,device_id:str,name:str,credential_sha256:str="")->dict:
        device_id=str(device_id or "").strip();name=str(name or "KRISHNA Mobile").strip()[:128]
        if not device_id:raise ValueError("device_id is required")
        if len(device_id)>160 or any(ch in device_id for ch in "\r\n\0"):raise ValueError("invalid device_id")
        digest=str(credential_sha256 or "").strip().lower()
        if digest and not self._valid_digest(digest):raise ValueError("credential_sha256 must be a SHA-256 hex digest")
        with self._lock:
            now=int(time.time()); pending=self._load(self.pending_file)
            pending={k:v for k,v in pending.items() if v.get("expires_at",0)>now}
            for v in pending.values():
                if v["device_id"]==device_id:
                    if digest:v["credential_sha256"]=digest
                    self._save(self.pending_file,pending)
                    return {k:x for k,x in v.items() if k!="credential_sha256"}
            if len(pending)>=self.max_pending:raise RuntimeError("pairing request queue is full")
            r=asdict(PendingPair(secrets.token_urlsafe(18),device_id,name,now,now+self.ttl,digest))
            pending[r["request_id"]]=r; self._save(self.pending_file,pending)
            return {k:v for k,v in r.items() if k!="credential_sha256"}

    def pending(self)->dict:
        with self._lock:
            now=int(time.time());pending=self._load(self.pending_file)
            pending={k:v for k,v in pending.items() if v.get("expires_at",0)>now}
            self._save(self.pending_file,pending)
            rows=[]
            for row in pending.values():
                clean={k:v for k,v in row.items() if k!="credential_sha256"}
                clean["credential_proposed"]=bool(row.get("credential_sha256"))
                rows.append(clean)
            rows.sort(key=lambda x:x.get("created_at",0),reverse=True)
            return {"pending":rows,"count":len(rows),"policy":"approval occurs on KRISHNA PC; no pairing code is used"}

    def approve(self,request_id:str)->dict:
        with self._lock:
            pending=self._load(self.pending_file); r=pending.pop(request_id,None)
            if not r or r["expires_at"]<=int(time.time()): raise PermissionError("pairing request missing or expired")
            paired=self._load(self.paired_file)
            digest=str(r.get("credential_sha256") or "").strip().lower()
            if digest and self._valid_digest(digest):
                paired[r["device_id"]]={"name":r["name"],"token_sha256":digest,"paired_at":int(time.time()),"mode":"client-hash-zero-code"}
                result={"device_id":r["device_id"],"approved":True,"mode":"client-hash-zero-code"}
            else:
                token=secrets.token_urlsafe(48)
                paired[r["device_id"]]={"name":r["name"],"token_sha256":hashlib.sha256(token.encode()).hexdigest(),"paired_at":int(time.time()),"mode":"legacy-token"}
                result={"device_id":r["device_id"],"token":token,"approved":True,"mode":"legacy-token"}
            self._save(self.pending_file,pending); self._save(self.paired_file,paired)
            return result

    def verify(self,device_id:str,token:str)->bool:
        with self._lock:
            v=self._load(self.paired_file).get(device_id)
            if not v or not token:return False
            return secrets.compare_digest(v["token_sha256"],hashlib.sha256(token.encode()).hexdigest())

    def revoke(self,device_id:str):
        with self._lock:
            paired=self._load(self.paired_file); paired.pop(device_id,None); self._save(self.paired_file,paired)

    def paired(self)->dict:
        with self._lock:
            rows=[]
            for device_id,row in self._load(self.paired_file).items():
                rows.append({"device_id":device_id,"name":row.get("name"),"paired_at":row.get("paired_at"),"mode":row.get("mode","legacy-token")})
            rows.sort(key=lambda x:x.get("paired_at") or 0,reverse=True)
            return {"devices":rows,"count":len(rows)}
