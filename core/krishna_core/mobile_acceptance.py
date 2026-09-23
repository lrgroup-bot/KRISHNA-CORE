from __future__ import annotations

"""Durable real-device acceptance ledger for KRISHNA Mobile.

The ledger does not auto-delete the historical PC companion. It records explicit
pass/fail evidence for each required real-device gate and only reports the old
companion as *eligible for reviewed retirement* after every gate has passed.
"""

from pathlib import Path
import hashlib
import json
import os
import tempfile
import time


REQUIRED_GATES = (
    "clean_install_relaunch",
    "secure_pair_reconnect",
    "shared_conversation_session",
    "camera_permission_capture",
    "audio_permission_capture",
    "offline_encrypted_evidence",
    "selective_private_sync",
    "pc_retained_ack_before_delete",
    "completion_notification_background",
    "wake_microphone_lifecycle",
)


class MobileAcceptanceLedger:
    VERSION="krishna-mobile-acceptance-v1"

    def __init__(self,path):
        self.path=Path(path).resolve()
        self.data=self._load()

    def _empty(self):
        return {
            "schema":1,
            "version":self.VERSION,
            "updated_at":0.0,
            "gates":{name:{"passed":False,"evidence":"","evidence_sha256":"","checked_at":0.0} for name in REQUIRED_GATES},
        }

    def _load(self):
        if not self.path.exists():
            return self._empty()
        try:
            value=json.loads(self.path.read_text(encoding="utf-8-sig"))
        except Exception:
            return self._empty()
        if value.get("schema")!=1 or value.get("version")!=self.VERSION:
            return self._empty()
        gates=value.setdefault("gates",{})
        for name in REQUIRED_GATES:
            gates.setdefault(name,{"passed":False,"evidence":"","evidence_sha256":"","checked_at":0.0})
        return value

    def _save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.data["updated_at"]=time.time()
        fd,tmp=tempfile.mkstemp(prefix="mobile-accept-",suffix=".json",dir=str(self.path.parent))
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as fh:
                json.dump(self.data,fh,indent=2,ensure_ascii=False)
            os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def record(self,gate,passed,*,evidence=""):
        gate=str(gate or "").strip()
        if gate not in REQUIRED_GATES:
            raise ValueError("unknown mobile acceptance gate")
        evidence=str(evidence or "").strip()
        if passed and not evidence:
            raise ValueError("passing a real-device gate requires evidence")
        row={
            "passed":bool(passed),
            "evidence":evidence[:2000],
            "evidence_sha256":hashlib.sha256(evidence.encode("utf-8")).hexdigest() if evidence else "",
            "checked_at":time.time(),
        }
        self.data["gates"][gate]=row
        self._save()
        return {"gate":gate,**row}

    def status(self):
        gates={name:dict(self.data["gates"][name]) for name in REQUIRED_GATES}
        passed=[name for name,row in gates.items() if row.get("passed")]
        pending=[name for name,row in gates.items() if not row.get("passed")]
        ready=not pending
        return {
            "version":self.VERSION,
            "passed":len(passed),
            "required":len(REQUIRED_GATES),
            "pending":pending,
            "gates":gates,
            "real_device_accepted":ready,
            "companion_retirement":"eligible_for_review" if ready else "retain",
            "automatic_delete":False,
        }
