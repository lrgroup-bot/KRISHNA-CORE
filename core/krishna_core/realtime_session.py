"""Durable realtime session/event log used by mobile transports."""
from __future__ import annotations
from pathlib import Path
import hashlib,json,threading,time,uuid


class RealtimeSessionStore:
    def __init__(self,state_dir):
        self.root=Path(state_dir)/"realtime"
        self.root.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock()

    @staticmethod
    def _device_key(device_id):
        raw=str(device_id or "").strip()
        if not raw:
            raise ValueError("device_id is required")
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _path(self,device_id):
        return self.root/(self._device_key(device_id)+".json")

    def _legacy_path(self,device_id):
        raw=str(device_id or "")
        return self.root/(raw.replace("/","_").replace("\\","_")+".json")

    @staticmethod
    def _empty():
        return {"next_seq":1,"events":[],"seen":{}}

    def _load(self,d):
        path=self._path(d)
        legacy=self._legacy_path(d)
        source=path if path.exists() else (legacy if legacy.exists() and legacy!=path else None)
        if source is None:
            return self._empty()
        try:
            data=json.loads(source.read_text("utf-8"))
        except Exception as exc:
            raise RuntimeError(f"realtime session state unreadable: {source.name}: {type(exc).__name__}") from exc
        if not isinstance(data,dict) or not isinstance(data.get("events"),list) or not isinstance(data.get("seen"),dict):
            raise RuntimeError(f"realtime session state invalid: {source.name}")
        try:
            data["next_seq"]=max(1,int(data.get("next_seq") or 1))
        except (TypeError,ValueError) as exc:
            raise RuntimeError(f"realtime session sequence invalid: {source.name}") from exc
        # Non-destructive migration from the old device-id filename scheme.
        if source==legacy and legacy!=path:
            self._save(d,data)
        return data

    def _save(self,d,v):
        p=self._path(d)
        t=p.with_suffix(".tmp")
        t.write_text(json.dumps(v,separators=(",",":")),encoding="utf-8")
        t.replace(p)

    def publish(self,device_id,event_type,payload,idempotency_key=None):
        with self.lock:
            s=self._load(device_id)
            if idempotency_key and idempotency_key in s["seen"]:
                return s["seen"][idempotency_key]
            e={"id":str(uuid.uuid4()),"seq":s["next_seq"],"type":event_type,"payload":payload,"ts":int(time.time())}
            s["next_seq"]+=1
            s["events"].append(e)
            s["events"]=s["events"][-500:]
            if idempotency_key:
                s["seen"][idempotency_key]=e
                s["seen"]=dict(list(s["seen"].items())[-500:])
            self._save(device_id,s)
            return e

    def after(self,device_id,seq=0):
        return [e for e in self._load(device_id)["events"] if e["seq"]>int(seq)]
