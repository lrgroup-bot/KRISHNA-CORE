from __future__ import annotations

import ipaddress
import json
import os
import socket
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
        self.load_error=None
        self._load()

    @staticmethod
    def _validate_url(value:str)->str:
        value=str(value or "").strip().rstrip("/")
        p=urlparse(value)
        if p.scheme not in ("http","https") or not p.netloc or not p.hostname:
            raise ValueError("gateway base_url must be http:// or https://")
        if p.username or p.password or p.fragment:
            raise ValueError("gateway base_url must not embed credentials or fragments")
        host=(p.hostname or "").strip().lower()
        if host in {"metadata.google.internal","metadata","instance-data","instance-data.ec2.internal"}:
            raise PermissionError("cloud metadata gateway target is blocked")
        addresses=[]
        try:addresses=[ipaddress.ip_address(host.strip("[]"))]
        except ValueError:
            try:
                addresses=list({ipaddress.ip_address(row[4][0].split("%",1)[0])
                    for row in socket.getaddrinfo(host,p.port or (443 if p.scheme=="https" else 80),type=socket.SOCK_STREAM)})
            except OSError as exc:raise ValueError("gateway hostname could not be resolved") from exc
        for addr in addresses:
            if addr.is_link_local or addr.is_unspecified or addr.is_multicast or addr.is_reserved:
                raise PermissionError("link-local/reserved gateway target is blocked")
        local=host=="localhost" or bool(addresses and all(x.is_loopback for x in addresses))
        if p.scheme!="https" and not local:
            raise ValueError("non-local cloud gateway must use https")
        return value

    @staticmethod
    def _validate_stored_url(value:str)->str:
        """Validate persisted gateway structure without requiring DNS at startup."""
        value=str(value or "").strip().rstrip("/")
        p=urlparse(value)
        if p.scheme not in ("http","https") or not p.netloc or not p.hostname:
            raise ValueError("gateway base_url must be http:// or https://")
        if p.username or p.password or p.fragment:
            raise ValueError("gateway base_url must not embed credentials or fragments")
        host=(p.hostname or "").strip().lower()
        if host in {"metadata.google.internal","metadata","instance-data","instance-data.ec2.internal"}:
            raise PermissionError("cloud metadata gateway target is blocked")
        literal=None
        try:literal=ipaddress.ip_address(host.strip("[]"))
        except ValueError:pass
        if literal is not None and (literal.is_link_local or literal.is_unspecified or literal.is_multicast or literal.is_reserved):
            raise PermissionError("link-local/reserved gateway target is blocked")
        local=host=="localhost" or bool(literal and literal.is_loopback)
        if p.scheme!="https" and not local:
            raise ValueError("non-local cloud gateway must use https")
        return value

    def _healthy(self):
        if self.load_error:
            raise RuntimeError("model gateway registry is unreadable; refusing to overwrite it: "+self.load_error)

    def _load(self):
        if not self.path.exists():return
        try:
            raw=json.loads(self.path.read_text(encoding="utf-8-sig"))
            if not isinstance(raw,dict):raise ValueError("model gateway registry root must be an object")
            schema=raw.get("schema",1)
            if schema!=1:raise ValueError(f"unsupported model gateway schema: {schema!r}")
            profiles=raw.get("profiles",[])
            if not isinstance(profiles,list):raise ValueError("model gateway profiles must be a list")
            loaded={}
            for item in profiles:
                if not isinstance(item,dict) or not item.get("id"):
                    raise ValueError("model gateway profile entry is invalid")
                row=GatewayProfile(**item)
                row.base_url=self._validate_stored_url(row.base_url)
                loaded[row.id]=row
            self.profiles=loaded
            self.load_error=None
        except Exception as exc:
            self.profiles={}
            self.load_error=f"{type(exc).__name__}: {exc}"

    def _save(self):
        self._healthy()
        self.path.parent.mkdir(parents=True,exist_ok=True)
        payload={"schema":1,"profiles":[asdict(x) for x in self.profiles.values()]}
        fd,tmp=tempfile.mkstemp(prefix="model-gateways-",suffix=".json",dir=str(self.path.parent))
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as h:json.dump(payload,h,ensure_ascii=False,indent=2)
            os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

    def register(self,name,base_url,model,api_key,free_only=True,enabled=True):
        self._healthy()
        name=str(name or "").strip();model=str(model or "").strip()
        if not name or not model:raise ValueError("gateway name and model are required")
        url=self._validate_url(base_url)
        secret=self.vault.put(name,"model_gateway",str(api_key or ""))
        row=GatewayProfile(str(uuid.uuid4()),name,url,model,secret["id"],bool(free_only),bool(enabled),time.time())
        self.profiles[row.id]=row;self._save();return self.describe(row.id)

    def delete(self,profile_id):
        self._healthy()
        key=str(profile_id)
        row=self.profiles.get(key)
        if not row:return False
        # Do not orphan encrypted credentials by forgetting the profile first.
        self.vault.delete(row.secret_id)
        self.profiles.pop(key,None)
        self._save();return True

    def describe(self,profile_id):
        row=self.profiles.get(str(profile_id))
        if not row:raise KeyError("model gateway profile not found")
        credential_available=False
        credential_backend="windows-dpapi"
        credential_error=None
        try:
            meta=self.vault.describe(row.secret_id)
            credential_available=bool(meta.get("available"))
            credential_backend=str(meta.get("backend") or credential_backend)
        except Exception as exc:
            credential_error=f"{type(exc).__name__}: {exc}"
        return {"id":row.id,"name":row.name,"base_url":row.base_url,"model":row.model,
                "free_only":row.free_only,"enabled":row.enabled,"created_at":row.created_at,
                "credential_backend":credential_backend,"credential_available":credential_available,
                "credential_reference_valid":credential_error is None,
                "credential_error":credential_error}

    def list(self):
        rows=[self.describe(x) for x in self.profiles]
        rows.sort(key=lambda x:x["created_at"],reverse=True)
        return {"profiles":rows,"count":len(rows),"load_error":self.load_error,"policy":"no silent provider fallback; free-only profiles remain free-only"}

    def eligible(self,privacy="approved_cloud",free_only=False):
        if privacy in {"local_only","restricted"}:return []
        rows=[x for x in self.profiles.values() if x.enabled and (not free_only or x.free_only)]
        return sorted(rows,key=lambda x:x.created_at)

    def request_json(self,profile_id,path,payload=None,method=None,timeout=120):
        """Make an authenticated JSON request without exposing the stored secret.

        Internal provider adapters may use only relative paths under the registered,
        already-validated gateway base URL. This intentionally does not accept an
        arbitrary URL or return the credential.
        """
        self._healthy()
        row=self.profiles.get(str(profile_id))
        if not row or not row.enabled:raise RuntimeError("model gateway profile is unavailable")
        row.base_url=self._validate_url(row.base_url)
        relative=str(path or "").strip()
        if not relative.startswith("/") or "://" in relative or "\\" in relative or ".." in relative:
            raise ValueError("gateway request path must be a safe relative API path")
        verb=str(method or ("POST" if payload is not None else "GET")).strip().upper()
        if verb not in {"GET","POST"}:raise ValueError("gateway JSON request supports GET/POST only")
        key=self.vault.resolve(row.secret_id)
        body=None if payload is None else json.dumps(payload).encode()
        headers={
            "Accept":"application/json",
            "Authorization":"Bearer "+key,
            "X-Krishna-Free-Only":"1" if row.free_only else "0",
        }
        if body is not None:headers["Content-Type"]="application/json"
        req=urllib.request.Request(row.base_url+relative,data=body,headers=headers,method=verb)
        try:
            with urllib.request.urlopen(req,timeout=max(1,int(timeout))) as response:
                raw=response.read()
        except Exception as exc:
            raise RuntimeError(f"model gateway request failed without fallback: {type(exc).__name__}: {exc}") from exc
        try:return json.loads(raw.decode())
        except Exception as exc:raise RuntimeError("model gateway returned invalid JSON") from exc

    def complete(self,profile_id,prompt,system="You are a worker model for KRISHNA.",max_tokens=2048):
        # Generic OpenAI-compatible profiles do not provide KRISHNA with a
        # provider-independent proof that a completion will consume zero money
        # and zero credits. Inference therefore requires a specialized adapter
        # such as OpenRouterFreeFabric or VerifiedDirectFreeFabric.
        self._healthy()
        row=self.profiles.get(str(profile_id))
        if not row or not row.enabled:raise RuntimeError("model gateway profile is unavailable")
        raise PermissionError(
            "generic model-gateway inference is blocked by KRISHNA hard zero-credit policy; "
            "credential remains stored for metadata/status and future verified-zero-cost adapters"
        )
