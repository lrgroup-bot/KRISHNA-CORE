from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class WearableDevice:
    id:str
    name:str
    kind:str
    capabilities:list[str]
    verified:bool=False
    provider:str="generic"
    created_at:float=0.0
    verification_evidence:str=""
    verified_capabilities:list[str]=field(default_factory=list)
    adapter_id:str=""
    last_seen_at:float=0.0


class WearableBridge:
    """Evidence-based KRISHNA wearable capability registry and observation bridge.

    Registration only declares what a device claims. Verification is capability-
    specific and requires real hardware-test evidence. Observation packets are
    accepted only from verified capabilities and remain sensor evidence, not an
    authorization channel for arbitrary device control.
    """

    SAFE_CAPS={
        "bluetooth_audio","microphone","speaker","phone_camera","camera","display",
        "ar_display","imu","head_tracking","gesture","wrist_input","ring_input"
    }

    def __init__(self,path:str|Path):
        self.path=Path(path);self.devices={}
        self._load()

    def _load(self):
        if not self.path.exists():return
        try:
            raw=json.loads(self.path.read_text(encoding="utf-8-sig"))
            rows={}
            for x in raw.get("devices",[]):
                if not x.get("id"):continue
                data=dict(x)
                data.setdefault("verified_capabilities",[])
                data.setdefault("adapter_id","")
                data.setdefault("last_seen_at",0.0)
                # Migration for v1 records: only preserve verified=true as capability
                # verification when there was explicit hardware evidence.
                if data.get("verified") and data.get("verification_evidence") and not data["verified_capabilities"]:
                    data["verified_capabilities"]=list(data.get("capabilities") or [])
                rows[data["id"]]=WearableDevice(**data)
            self.devices=rows
        except Exception:self.devices={}

    def _save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        payload={"schema":2,"devices":[asdict(x) for x in self.devices.values()]}
        fd,tmp=tempfile.mkstemp(prefix="wearables-",suffix=".json",dir=str(self.path.parent))
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as h:json.dump(payload,h,ensure_ascii=False,indent=2)
            os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

    def register(self,name,kind,capabilities,provider="generic",verified=False,adapter_id=""):
        caps=sorted(set(str(x).strip().lower() for x in (capabilities or []) if str(x).strip()))
        unknown=[x for x in caps if x not in self.SAFE_CAPS]
        if unknown:raise ValueError("unsupported wearable capabilities: "+", ".join(unknown))
        name=str(name or "").strip();kind=str(kind or "").strip();provider=str(provider or "generic").strip()
        if not name or not kind:raise ValueError("wearable name and kind are required")
        row=WearableDevice(
            str(uuid.uuid4()),name,kind,caps,False,provider,time.time(),"",[],
            str(adapter_id or "").strip(),0.0
        )
        self.devices[row.id]=row;self._save();return asdict(row)

    def verify(self,device_id,capabilities=None,evidence="",adapter_id=None):
        row=self.devices.get(str(device_id))
        if not row:raise KeyError("wearable device not found")
        requested=(
            sorted(set(str(x).strip().lower() for x in capabilities if str(x).strip()))
            if capabilities is not None else list(row.capabilities)
        )
        if any(x not in self.SAFE_CAPS for x in requested):raise ValueError("unsupported wearable capability")
        undeclared=[x for x in requested if x not in row.capabilities]
        if undeclared:raise ValueError("cannot verify undeclared capabilities: "+", ".join(undeclared))
        evidence=str(evidence or "").strip()
        if not evidence:raise ValueError("wearable verification requires hardware-test evidence")
        row.verified_capabilities=sorted(set(row.verified_capabilities)|set(requested))
        row.verified=bool(row.verified_capabilities)
        row.verification_evidence=evidence[:2000]
        if adapter_id is not None:row.adapter_id=str(adapter_id or "").strip()
        row.last_seen_at=time.time()
        self._save();return asdict(row)

    def observe(self,device_id,capability,payload):
        row=self.devices.get(str(device_id))
        if not row:raise KeyError("wearable device not found")
        cap=str(capability or "").strip().lower()
        if cap not in row.verified_capabilities:
            raise PermissionError("wearable capability is not hardware-verified")
        row.last_seen_at=time.time();self._save()
        return {
            "device_id":row.id,
            "capability":cap,
            "payload":payload,
            "observed_at":row.last_seen_at,
            "evidence_state":"OBSERVED",
            "hardware_verified":True,
            "authority":"sensor evidence only; consequential action still requires KRISHNA/Sudarshan policy",
        }

    def list(self):
        rows=[asdict(x) for x in self.devices.values()]
        rows.sort(key=lambda x:x["created_at"],reverse=True)
        return {"devices":rows,"count":len(rows),"stages":{
            "phase_1":["bluetooth_audio","microphone","speaker","phone_camera"],
            "phase_2":["camera","display","ar_display"],
            "phase_3":["imu","head_tracking","gesture","wrist_input","ring_input"],
        },"policy":"Vendor capability is never claimed until a real adapter/device test verifies that specific capability."}

    def status(self):
        data=self.list()
        caps=sorted(set(c for x in data["devices"] for c in x.get("verified_capabilities") or []))
        verified_devices=[x for x in data["devices"] if x.get("verified_capabilities")]
        return {
            **data,
            "verified_capabilities":caps,
            "bridge_ready":bool(verified_devices),
            "phone_camera_bridge":"mobile attachment -> local vision",
            "bluetooth_audio_bridge":"OS-managed",
            "ar_display_bridge":"adapter-gated",
            "gesture_bridge":"adapter-gated",
        }
