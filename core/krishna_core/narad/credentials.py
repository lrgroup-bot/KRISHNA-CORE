from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class CredentialRef:
    id: str
    name: str
    provider: str
    env_var: str
    header: str = "Authorization"
    scheme: str = "Bearer"
    created_at: float = 0.0


class NaradCredentialVault:
    """Secret-reference vault.

    KRISHNA persists only metadata and an environment-variable reference. Raw secret
    values are never written to Narad state or returned by status APIs.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.refs: dict[str, CredentialRef] = {}
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        try:
            raw=json.loads(self.path.read_text(encoding="utf-8-sig"))
            self.refs={x["id"]:CredentialRef(**x) for x in raw.get("credentials",[]) if x.get("id")}
        except Exception:
            self.refs={}

    def _save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        payload={"schema":1,"credentials":[asdict(x) for x in self.refs.values()]}
        fd,tmp=tempfile.mkstemp(prefix="narad-credentials-",suffix=".json",dir=str(self.path.parent))
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as h:json.dump(payload,h,ensure_ascii=False,indent=2)
            os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

    def register(self,name,provider,env_var,header="Authorization",scheme="Bearer"):
        name=str(name or "").strip();provider=str(provider or "").strip();env_var=str(env_var or "").strip()
        header=str(header or "Authorization").strip();scheme=str(scheme or "").strip()
        if not name or not provider or not env_var:raise ValueError("name, provider and env_var are required")
        if any(x in env_var for x in ("="," ","\n","\r","\t")):raise ValueError("env_var must be a variable name, not a secret value")
        if not env_var.replace("_","").isalnum():raise ValueError("invalid env_var")
        ref=CredentialRef(str(uuid.uuid4()),name,provider,env_var,header,scheme,time.time())
        self.refs[ref.id]=ref;self._save();return self.describe(ref.id)

    def describe(self,credential_id):
        ref=self.refs.get(str(credential_id))
        if not ref:raise KeyError("Narad credential reference not found")
        return {**asdict(ref),"available":bool(os.getenv(ref.env_var))}

    def list(self):
        rows=[self.describe(x) for x in self.refs]
        rows.sort(key=lambda x:x["created_at"],reverse=True)
        return {"connections":rows,"count":len(rows),"policy":"secret references only; raw secret values are never persisted"}

    def headers(self,credential_id):
        ref=self.refs.get(str(credential_id))
        if not ref:raise KeyError("Narad credential reference not found")
        secret=os.getenv(ref.env_var)
        if not secret:raise RuntimeError(f"credential environment variable is unavailable: {ref.env_var}")
        value=f"{ref.scheme} {secret}".strip() if ref.scheme else secret
        return {ref.header:value}
