from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass


_SENSITIVE_KEYS={
    "password","secret","token","authorization","credential","credentials",
    "access_token","refresh_token","client_secret","api_key","apikey",
}


def _is_sensitive(key):
    raw=str(key or "").strip().lower().replace("-","_")
    return raw in _SENSITIVE_KEYS or raw.endswith(("_password","_secret","_token","_credential","_credentials","_api_key"))


def _safe(value,depth=0):
    if depth>24:return "[MAX_DEPTH]"
    if isinstance(value,dict):
        return {str(k):("[REDACTED]" if _is_sensitive(k) else _safe(v,depth+1)) for k,v in value.items()}
    if isinstance(value,list):return [_safe(x,depth+1) for x in value[:200]]
    if isinstance(value,str):return value[:50000]+("…" if len(value)>50000 else "")
    if isinstance(value,(int,float,bool,type(None))):return value
    return str(value)[:4000]


def _allowed_endpoint(value):
    parsed=urllib.parse.urlparse(str(value or ""))
    if parsed.scheme=="https" and parsed.hostname:return True
    if parsed.scheme=="http" and parsed.hostname in {"localhost","127.0.0.1","::1"}:return True
    return False


@dataclass(frozen=True)
class LRMailGatewayStatus:
    configured: bool
    read_only: bool = True
    mutations_allowed: bool = False
    provider: str = "LR Group Owner Mail Gateway"

    def as_dict(self):
        return {
            "configured":self.configured,
            "read_only":self.read_only,
            "mutations_allowed":self.mutations_allowed,
            "provider":self.provider,
            "operations":["status","summary","list","get"],
        }


class LRMailGateway:
    """KRISHNA's bounded read-only bridge into the LR Group mail surface.

    KRISHNA never receives Stalwart administrator credentials or mailbox-user
    credentials.  It receives one LR-issued read token which can call only
    LR Group's owner-mail summary/list/get endpoints.
    """

    def __init__(self,base_url=None,read_token=None,timeout=8,opener=None):
        self.base_url=str(base_url or os.getenv("KRISHNA_LR_MAIL_URL") or "").strip().rstrip("/")
        self.read_token=str(read_token or os.getenv("KRISHNA_LR_MAIL_READ_TOKEN") or "").strip()
        self.timeout=max(2,min(int(timeout or 8),30))
        self.opener=opener or urllib.request.urlopen

    def status(self):
        configured=bool(self.base_url and self.read_token and _allowed_endpoint(self.base_url))
        result=LRMailGatewayStatus(configured=configured).as_dict()
        result.update({
            "endpoint":"configured" if self.base_url else "missing",
            "credential":"configured" if self.read_token else "missing",
            "transport_policy":"HTTPS or localhost HTTP only",
            "boundary":"KRISHNA can inspect LR mail but cannot create, send, delete or modify it",
        })
        return result

    def _request(self,path,query=None):
        if not self.base_url or not self.read_token:raise RuntimeError("LR mail gateway is not configured")
        if not _allowed_endpoint(self.base_url):raise PermissionError("LR mail gateway requires HTTPS or localhost HTTP")
        suffix=str(path or "")
        if not suffix.startswith("/"):suffix="/"+suffix
        url=self.base_url+suffix
        if query:
            encoded=urllib.parse.urlencode({k:v for k,v in query.items() if v not in (None,"")})
            if encoded:url+="?"+encoded
        request=urllib.request.Request(
            url,
            headers={"Authorization":"Bearer "+self.read_token,"Accept":"application/json","User-Agent":"KRISHNA-LR-Mail-Read/1"},
            method="GET",
        )
        try:
            with self.opener(request,timeout=self.timeout) as response:
                raw=response.read(4*1024*1024+1)
                if len(raw)>4*1024*1024:raise RuntimeError("LR mail response exceeded 4 MB")
                data=json.loads(raw.decode("utf-8") or "{}")
        except Exception as exc:
            # Do not propagate provider/network messages: they may contain URLs or credentials.
            raise RuntimeError("LR mail read request failed: "+type(exc).__name__) from exc
        if not isinstance(data,dict):raise RuntimeError("LR mail gateway returned invalid JSON object")
        return _safe(data)

    def summary(self,limit=100):
        value=max(1,min(int(limit or 100),100))
        return self._request("/api/owner-mail/summary",{"limit":value})

    def list(self,limit=50,position=0,text=""):
        value=max(1,min(int(limit or 50),100))
        pos=max(0,int(position or 0))
        query=str(text or "").strip()[:500]
        return self._request("/api/owner-mail/messages",{"limit":value,"position":pos,"text":query})

    def get(self,message_id):
        mid=str(message_id or "").strip()
        if not mid or len(mid)>512:raise ValueError("message_id is required")
        return self._request("/api/owner-mail/message",{"id":mid})
