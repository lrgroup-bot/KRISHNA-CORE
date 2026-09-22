from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from ..secure_vault import _dpapi_protect, _dpapi_unprotect, SecretVaultUnavailable
from .models import PrivacyRetentionClass, utc_now


_SENSITIVE_KEYS={
    "password","passwd","secret","token","api_key","apikey","authorization",
    "cookie","cookies","session","credential","credentials","device_id","fingerprint",
    "ip","ipv4","ipv6","resolver","public_ip","local_ip",
}
_SECRETISH=re.compile(
    r"(?i)(?:bearer\s+[A-Za-z0-9._~+\-/]+=*|"
    r"\b(?:api[_-]?key|secret|token|password|passwd)\b\s*[:=]\s*[^\s,;]{6,})"
)
_IPISH=re.compile(r"(?<![0-9A-Fa-f:])(?:\d{1,3}\.){3}\d{1,3}(?![0-9])")


class PrivacyEvidenceStore:
    """Local-first privacy evidence store.

    Normalized summaries are kept as redacted JSONL. Sensitive raw evidence is
    persisted only when Windows DPAPI is available; otherwise KRISHNA stores a
    digest/reference and deliberately discards the raw sensitive value.
    """

    SCHEMA=1

    def __init__(self, root: str|Path):
        self.root=Path(root)
        self.root.mkdir(parents=True,exist_ok=True)
        self.history_path=self.root/"history.jsonl"
        self.baseline_path=self.root/"baselines.json"
        self.evidence_root=self.root/"evidence"
        self.evidence_root.mkdir(parents=True,exist_ok=True)

    @staticmethod
    def _digest(value: Any) -> str:
        raw=json.dumps(value,sort_keys=True,ensure_ascii=False,default=str).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @classmethod
    def sanitize(cls, value: Any, key: str="") -> Any:
        k=str(key or "").lower()
        if k in _SENSITIVE_KEYS:
            return {"redacted":True,"sha256":cls._digest(value)}
        if isinstance(value,dict):
            return {str(a):cls.sanitize(b,str(a)) for a,b in value.items()}
        if isinstance(value,(list,tuple)):
            return [cls.sanitize(x,key) for x in value[:500]]
        if isinstance(value,str):
            text=_SECRETISH.sub("[REDACTED]",value)
            text=_IPISH.sub("[IP-REDACTED]",text)
            return text[:12000]
        if isinstance(value,(int,float,bool,type(None))):
            return value
        return str(value)[:12000]

    @staticmethod
    def _atomic_json(path: Path, payload: dict):
        path.parent.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(prefix=path.stem+"-",suffix=".json",dir=str(path.parent))
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as h:
                json.dump(payload,h,ensure_ascii=False,indent=2)
            os.replace(tmp,path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def append_history(self, report: dict, retention: PrivacyRetentionClass=PrivacyRetentionClass.REGRESSION_HISTORY) -> dict:
        if retention==PrivacyRetentionClass.EPHEMERAL:
            return {"stored":False,"retention":retention.value,"reason":"ephemeral"}
        safe=self.sanitize(report)
        row={
            "schema":self.SCHEMA,
            "stored_at":utc_now(),
            "retention":retention.value,
            "audit":safe,
            "sha256":self._digest(safe),
        }
        with self.history_path.open("a",encoding="utf-8") as h:
            h.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")
        return {"stored":True,"retention":retention.value,"sha256":row["sha256"],"path":str(self.history_path)}

    def history(self, limit: int=50) -> list[dict]:
        if not self.history_path.exists():
            return []
        rows=[]
        for line in self.history_path.read_text(encoding="utf-8-sig").splitlines():
            try: rows.append(json.loads(line))
            except Exception: continue
        return rows[-max(0,min(int(limit),500)):]

    def save_baseline(self, name: str, report: dict) -> dict:
        key=str(name or "").strip()
        if not key:
            raise ValueError("baseline name is required")
        data={"schema":self.SCHEMA,"baselines":{}}
        if self.baseline_path.exists():
            try:
                loaded=json.loads(self.baseline_path.read_text(encoding="utf-8-sig"))
                if isinstance(loaded,dict) and loaded.get("schema")==self.SCHEMA:
                    data=loaded
            except Exception:
                pass
        safe=self.sanitize(report)
        data.setdefault("baselines",{})[key]={
            "saved_at":utc_now(),
            "sha256":self._digest(safe),
            "report":safe,
        }
        self._atomic_json(self.baseline_path,data)
        return {"stored":True,"name":key,"sha256":data["baselines"][key]["sha256"]}

    def baseline(self, name: str) -> dict|None:
        if not self.baseline_path.exists():
            return None
        try:
            raw=json.loads(self.baseline_path.read_text(encoding="utf-8-sig"))
            item=(raw.get("baselines") or {}).get(str(name))
            return dict(item) if isinstance(item,dict) else None
        except Exception:
            return None

    def store_sensitive_evidence(self, audit_id: str, label: str, evidence: Any,
                                 retention: PrivacyRetentionClass=PrivacyRetentionClass.SECURITY_EVIDENCE) -> dict:
        digest=self._digest(evidence)
        if retention==PrivacyRetentionClass.EPHEMERAL:
            return {"stored":False,"retention":retention.value,"sha256":digest,"raw_discarded":True}
        if os.name!="nt":
            return {
                "stored":False,"retention":retention.value,"sha256":digest,
                "raw_discarded":True,"reason":"DPAPI unavailable; sensitive evidence not persisted",
            }
        payload=json.dumps({
            "schema":self.SCHEMA,
            "audit_id":str(audit_id),
            "label":str(label),
            "created_at":utc_now(),
            "evidence":evidence,
        },ensure_ascii=False,default=str).encode("utf-8")
        try:
            cipher=_dpapi_protect(payload,b"KRISHNA-PRIVACY-EVIDENCE-V1")
        except Exception as exc:
            raise SecretVaultUnavailable(f"privacy evidence encryption failed: {exc}") from exc
        target=self.evidence_root/(digest+".dpapi")
        target.write_text(base64.b64encode(cipher).decode("ascii"),encoding="ascii")
        return {
            "stored":True,"retention":retention.value,"sha256":digest,
            "encrypted":True,"backend":"windows-dpapi","path":str(target),
        }

    def read_sensitive_evidence(self, sha256: str) -> dict:
        digest=str(sha256 or "").strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}",digest):
            raise ValueError("invalid evidence digest")
        target=self.evidence_root/(digest+".dpapi")
        if not target.is_file():
            raise FileNotFoundError(digest)
        if os.name!="nt":
            raise SecretVaultUnavailable("privacy evidence decryption requires Windows DPAPI")
        cipher=base64.b64decode(target.read_text(encoding="ascii"),validate=True)
        plain=_dpapi_unprotect(cipher,b"KRISHNA-PRIVACY-EVIDENCE-V1")
        return json.loads(plain.decode("utf-8"))
