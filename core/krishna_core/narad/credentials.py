from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from ..secure_vault import SecureSecretVault


@dataclass
class CredentialRef:
    id: str
    name: str
    provider: str
    env_var: str = ""
    header: str = "Authorization"
    scheme: str = "Bearer"
    created_at: float = 0.0
    source: str = "env"
    secret_id: str = ""


class NaradCredentialVault:
    """Credential-reference registry.

    References may resolve from environment variables or KRISHNA's Windows DPAPI
    vault. Raw secret values are never written into Narad state or returned by APIs.
    """

    def __init__(self, path: str | Path, secure_vault: SecureSecretVault | None = None):
        self.path = Path(path)
        self.secure_vault = secure_vault or SecureSecretVault(self.path.parent/"secure-secrets.json")
        self.refs: dict[str, CredentialRef] = {}
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        try:
            raw=json.loads(self.path.read_text(encoding="utf-8-sig"))
            refs={}
            for x in raw.get("credentials",[]):
                if not x.get("id"):
                    continue
                row=dict(x)
                row.setdefault("source","env")
                row.setdefault("secret_id","")
                row.setdefault("env_var","")
                refs[row["id"]]=CredentialRef(**row)
            self.refs=refs
        except Exception:
            self.refs={}

    def _save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        payload={"schema":2,"credentials":[asdict(x) for x in self.refs.values()]}
        fd,tmp=tempfile.mkstemp(prefix="narad-credentials-",suffix=".json",dir=str(self.path.parent))
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as h:json.dump(payload,h,ensure_ascii=False,indent=2)
            os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

    @staticmethod
    def _validate_common(name,provider,header,scheme):
        name=str(name or "").strip();provider=str(provider or "").strip()
        header=str(header or "Authorization").strip();scheme=str(scheme or "").strip()
        if not name or not provider:raise ValueError("name and provider are required")
        if any(x in header for x in ("
","")):raise ValueError("invalid credential header")
        return name,provider,header,scheme

    def register(self,name,provider,env_var,header="Authorization",scheme="Bearer"):
        name,provider,header,scheme=self._validate_common(name,provider,header,scheme)
        env_var=str(env_var or "").strip()
        if not env_var:raise ValueError("env_var is required")
        if any(x in env_var for x in ("="," ","
","","	")):raise ValueError("env_var must be a variable name, not a secret value")
        if not env_var.replace("_","").isalnum():raise ValueError("invalid env_var")
        ref=CredentialRef(str(uuid.uuid4()),name,provider,env_var,header,scheme,time.time(),"env","")
        self.refs[ref.id]=ref;self._save();return self.describe(ref.id)

    def register_secret(self,name,provider,secret,header="Authorization",scheme="Bearer"):
        name,provider,header,scheme=self._validate_common(name,provider,header,scheme)
        meta=self.secure_vault.put(name,provider,str(secret or ""))
        ref=CredentialRef(str(uuid.uuid4()),name,provider,"",header,scheme,time.time(),"vault",meta["id"])
        self.refs[ref.id]=ref;self._save();return self.describe(ref.id)

    def delete(self,credential_id):
        ref=self.refs.pop(str(credential_id),None)
        if not ref:return False
        if ref.source=="vault" and ref.secret_id:
            try:self.secure_vault.delete(ref.secret_id)
            except Exception:pass
        self._save();return True

    def _available(self,ref:CredentialRef):
        if ref.source=="env":return bool(ref.env_var and os.getenv(ref.env_var))
        if ref.source=="vault":
            try:
                self.secure_vault.describe(ref.secret_id)
                return bool(self.secure_vault.available)
            except Exception:return False
        return False

    def describe(self,credential_id):
        ref=self.refs.get(str(credential_id))
        if not ref:raise KeyError("Narad credential reference not found")
        row=asdict(ref)
        row["available"]=self._available(ref)
        row["backend"]="environment" if ref.source=="env" else "windows-dpapi"
        return row

    def list(self):
        rows=[self.describe(x) for x in self.refs]
        rows.sort(key=lambda x:x["created_at"],reverse=True)
        return {"connections":rows,"count":len(rows),"secure_vault":self.secure_vault.list(),
                "policy":"environment references or Windows DPAPI; plaintext secrets are never returned"}

    def resolve(self,credential_id):
        ref=self.refs.get(str(credential_id))
        if not ref:raise KeyError("Narad credential reference not found")
        if ref.source=="env":
            secret=os.getenv(ref.env_var)
            if not secret:raise RuntimeError(f"credential environment variable is unavailable: {ref.env_var}")
            return secret
        if ref.source=="vault":
            return self.secure_vault.resolve(ref.secret_id)
        raise RuntimeError("unsupported credential reference source")

    def headers(self,credential_id):
        ref=self.refs.get(str(credential_id))
        if not ref:raise KeyError("Narad credential reference not found")
        secret=self.resolve(credential_id)
        value=f"{ref.scheme} {secret}".strip() if ref.scheme else secret
        return {ref.header:value}
