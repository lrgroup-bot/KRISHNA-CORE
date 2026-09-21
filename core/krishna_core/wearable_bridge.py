from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
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


class WearableBridge:
    """Evidence-based KRISHNA wearable capability registry.

    Generic Bluetooth audio and phone-camera handoff may be marked verified after
    runtime checks. Vendor camera/display/gesture APIs remain unavailable until a
    concrete device adapter is registered and verified.
    """

    SAFE_CAPS={"bluetooth_audio","microphone","speaker","phone_camera","camera","display","imu","gesture","wrist_input","ring_input"}

    def __init__(self,path:str|Path):
        self.path=Path(path);self.devices={}
        self._load()

    def _load(self):
        if not self.path.exists():return
        try:
            raw=json.loads(self.path.read_text(encoding="utf-8-sig"))
            self.devices={x["id"]:WearableDevice(**x) for x in raw.get("devices",[]) if x.get("id")}
        except Exception:self.devices={}

    def _save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        payload={"schema":1,"devices":[asdict(x) for x in self.devices.values()]}
        fd,tmp=tempfile.mkstemp(prefix="wearables-",suffix=".json",dir=str(self.path.parent))
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as h:json.dump(payload,h,ensure_ascii=False,indent=2)
            os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

    def register(self,name,kind,capabilities,provider="generic",verified=False):
        caps=sorted(set(str(x).strip().lower() for x in (capabilities or []) if str(x).strip()))
        unknown=[x for x in caps if x not in self.SAFE_CAPS]
        if unknown:raise ValueError("unsupported wearable capabilities: "+", ".join(unknown))
        name=str(name or "").strip();kind=str(kind or "").strip();provider=str(provider or "generic").strip()
        if not name or not kind:raise ValueError("wearable name and kind are required")
        row=WearableDevice(str(uuid.uuid4()),name,kind,caps,False,provider,time.time(),"")
        self.devices[row.id]=row;self._save();return asdict(row)

    def verify(self,device_id,capabilities=None,evidence=""):
        row=self.devices.get(str(device_id))
        if not row:raise KeyError("wearable device not found")
        if capabilities is not None:
            caps=sorted(set(str(x).strip().lower() for x in capabilities if str(x).strip()))
            if any(x not in self.SAFE_CAPS for x in caps):raise ValueError("unsupported wearable capability")
            row.capabilities=caps
        evidence=str(evidence or "").strip()
        if not evidence:raise ValueError("wearable verification requires hardware-test evidence")
        row.verified=True;row.verification_evidence=evidence[:2000];self._save();return asdict(row)

    def list(self):
        rows=[asdict(x) for x in self.devices.values()]
        rows.sort(key=lambda x:x["created_at"],reverse=True)
        return {"devices":rows,"count":len(rows),"stages":{
            "phase_1":["bluetooth_audio","microphone","speaker","phone_camera"],
            "phase_2":["verified_vendor_camera","verified_vendor_display"],
            "phase_3":["imu","gesture","wrist_input","ring_input","ar_display"],
        },"policy":"Vendor camera/display/gesture capability is never claimed until a real adapter/device test is verified."}

    def status(self):
        data=self.list();verified=[x for x in data["devices"] if x["verified"]]
        caps=sorted(set(c for x in verified for c in x["capabilities"]))
        return {**data,"verified_capabilities":caps,"bridge_ready":bool(verified),"phone_camera_bridge":"mobile attachment -> local vision","bluetooth_audio_bridge":"OS-managed"}
