from __future__ import annotations
import json,os,urllib.request
from urllib.parse import urlparse


class N8nBridge:
    """Optional external n8n webhook bridge.

    n8n remains outside KRISHNA. This adapter only POSTs to explicitly allowed
    webhook hosts and is intended to be called through NARAD/Sudarshan.
    """

    def __init__(self,allowed_hosts=None,timeout=30):
        configured=allowed_hosts if allowed_hosts is not None else os.getenv("KRISHNA_N8N_ALLOWED_HOSTS","")
        self.allowed_hosts={x.strip().lower() for x in str(configured).split(",") if x.strip()}
        self.timeout=max(3,min(int(timeout),120))

    def _validate(self,url):
        value=str(url or "").strip()
        parsed=urlparse(value)
        if parsed.scheme not in {"https","http"} or not parsed.hostname:
            raise ValueError("n8n webhook URL must be http:// or https://")
        host=parsed.hostname.lower()
        local=host in {"127.0.0.1","localhost","::1"}
        if parsed.scheme!="https" and not local:
            raise ValueError("remote n8n webhook must use https")
        if self.allowed_hosts and host not in self.allowed_hosts:
            raise PermissionError("n8n webhook host is not allowlisted")
        return value

    def trigger(self,url,payload=None,headers=None):
        target=self._validate(url)
        body=json.dumps(payload or {},ensure_ascii=False).encode("utf-8")
        safe_headers={"Content-Type":"application/json","Accept":"application/json"}
        for k,v in dict(headers or {}).items():
            if str(k).lower() in {"authorization","x-api-key","x-n8n-api-key"}:
                safe_headers[str(k)]=str(v)
        req=urllib.request.Request(target,data=body,method="POST",headers=safe_headers)
        with urllib.request.urlopen(req,timeout=self.timeout) as r:
            raw=r.read(20000).decode("utf-8","replace")
            return {
                "status":r.status,"ok":200<=r.status<300,
                "body":raw,"host":urlparse(target).hostname,
            }

    def post(self,url,payload=None,headers=None,timeout=None):
        if timeout is not None:
            previous=self.timeout
            try:
                self.timeout=max(3,min(int(timeout),120))
                return self.trigger(url,payload,headers)
            finally:
                self.timeout=previous
        return self.trigger(url,payload,headers)

    def status(self):
        return {
            "available":True,"mode":"external-webhook-only",
            "allowed_hosts":sorted(self.allowed_hosts),
            "policy":"n8n is a connector, never KRISHNA authority",
        }
