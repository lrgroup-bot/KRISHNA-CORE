from __future__ import annotations

import json
import os
import tempfile
import time
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

from .secure_vault import SecureSecretVault


@dataclass
class GatewayProfile:
    id:str
    name:str
    base_url:str
    model:str
    secret_id:str
    free_only:bool=True
    enabled:bool=True
    created_at:float=0.0


class ModelGatewayRegistry:
    """OpenAI-compatible cloud gateway profiles with encrypted local credentials.

    A free-only profile never falls through to another cloud provider. KRISHNA may
    use it only when project privacy permits cloud access.
    """

    def __init__(self,path:str|Path,vault:SecureSecretVault|None=None):
        self.path=Path(path)
        self.vault=vault or SecureSecretVault(self.path.parent/"secure-secrets.json")
        self.profiles:dict[str,GatewayProfile]={}
        self._load()

    @staticmethod
    def _validate_url(value:str)->str:
        value=str(value or "").strip().rstrip("/")
        p=urlparse(value)
        if p.scheme not in ("http","https") or not p.netloc:
            raise ValueError("gateway base_url must be http:// or https://")
        host=(p.hostname or "").lower()
        if p.scheme!="https" and host not in {"localhost","127.0.0.1","::1"}:
            raise ValueError("non-local cloud gateway must use https")
        return value

    def _load(self):
        if not self.path.exists():return
        try:
            raw=json.loads(self.path.read_text(encoding="utf-8-sig"))
            self.profiles={x["id"]:GatewayProfile(**x) for x in raw.get("profiles",[]) if x.get("id")}
        except Exception:self.profiles={}

    def _save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        payload={"schema":1,"profiles":[asdict(x) for x in self.profiles.values()]}
        fd,tmp=tempfile.mkstemp(prefix="model-gateways-",suffix=".json",dir=str(self.path.parent))
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as h:json.dump(payload,h,ensure_ascii=False,indent=2)
            os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

    def register(self,name,base_url,model,api_key,free_only=True,enabled=True):
        name=str(name or "").strip();model=str(model or "").strip()
        if not name or not model:raise ValueError("gateway name and model are required")
        url=self._validate_url(base_url)
        secret=self.vault.put(name,"model_gateway",str(api_key or ""))
        row=GatewayProfile(str(uuid.uuid4()),name,url,model,secret["id"],bool(free_only),bool(enabled),time.time())
        self.profiles[row.id]=row;self._save();return self.describe(row.id)

    def delete(self,profile_id):
        row=self.profiles.pop(str(profile_id),None)
        if not row:return False
        try:self.vault.delete(row.secret_id)
        except Exception:pass
        self._save();return True

    def describe(self,profile_id):
        row=self.profiles.get(str(profile_id))
        if not row:raise KeyError("model gateway profile not found")
        return {"id":row.id,"name":row.name,"base_url":row.base_url,"model":row.model,
                "free_only":row.free_only,"enabled":row.enabled,"created_at":row.created_at,
                "credential_backend":"windows-dpapi","credential_available":self.vault.available}

    def list(self):
        rows=[self.describe(x) for x in self.profiles]
        rows.sort(key=lambda x:x["created_at"],reverse=True)
        return {"profiles":rows,"count":len(rows),"policy":"no silent provider fallback; free-only profiles remain free-only"}

    def eligible(self,privacy="approved_cloud",free_only=False):
        if privacy in {"local_only","restricted"}:return []
        rows=[x for x in self.profiles.values() if x.enabled and (not free_only or x.free_only)]
        return sorted(rows,key=lambda x:x.created_at)

    def complete(self,profile_id,prompt,system="You are a worker model for KRISHNA.",max_tokens=2048):
        row=self.profiles.get(str(profile_id))
        if not row or not row.enabled:raise RuntimeError("model gateway profile is unavailable")
        key=self.vault.resolve(row.secret_id)
        body=json.dumps({"model":row.model,"messages":[{"role":"system","content":system},{"role":"user","content":str(prompt)}],
                         "max_tokens":int(max_tokens),"temperature":0.2}).encode()
        req=urllib.request.Request(row.base_url+"/chat/completions",data=body,
            headers={"Content-Type":"application/json","Authorization":"Bearer "+key,
                     "X-Krishna-Free-Only":"1" if row.free_only else "0"})
        try:
            with urllib.request.urlopen(req,timeout=120) as r:data=json.loads(r.read().decode())
        except Exception as exc:
            raise RuntimeError(f"model gateway request failed without fallback: {type(exc).__name__}: {exc}") from exc
        return data["choices"][0]["message"]["content"]
