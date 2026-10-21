"""Pinned-HTTPS client for BRAHMA inference sidecar on private LAN.

Never sends approved books/evidence to cloud, public IP, unpinned TLS or
unauthenticated Ollama. Model output is unverified research/exam candidate.
"""
from __future__ import annotations

import hashlib
import hmac
import http.client
import ipaddress
import json
from pathlib import Path
import ssl
from urllib.parse import urlsplit

MAX_REPLY_BYTES=131072


class LocalBrahmaInference:
    def __init__(self, *, config_path):
        filename=Path(config_path).expanduser().resolve(strict=True)
        cfg=json.loads(filename.read_text(encoding="utf-8"))
        if not isinstance(cfg,dict) or cfg.get("schema")!="krishna.brahma.local-inference.v1":
            raise ValueError("valid local BRAHMA inference configuration required")
        uri=urlsplit(str(cfg.get("endpoint") or ""))
        if (uri.scheme!="https" or not uri.hostname or uri.path not in ("","/")
                or uri.query or uri.fragment or uri.username or uri.password):
            raise ValueError("inference origin must be private HTTPS only")
        try:
            ip=ipaddress.ip_address(uri.hostname)
        except ValueError as exc:
            raise ValueError("explicit private inference IPv4 required") from exc
        lan=any(ip in n for n in (ipaddress.ip_network("10.0.0.0/8"),
                ipaddress.ip_network("172.16.0.0/12"),
                ipaddress.ip_network("192.168.0.0/16"),
                ipaddress.ip_network("127.0.0.0/8")))
        if ip.version!=4 or not lan:
            raise ValueError("public inference endpoints forbidden")
        digest=str(cfg.get("cert_sha256") or "").replace(":","").lower()
        if len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("inference TLS certificate pin missing or invalid")
        token_file=Path(cfg.get("token_file") or "")
        if not token_file.is_absolute():
            token_file=filename.parent/token_file
        token=token_file.expanduser().resolve(strict=True).read_text(encoding="utf-8").strip()
        if not 48<=len(token)<=256 or not token.isascii() or not token.isprintable():
            raise ValueError("private inference secret must be long printable ASCII")
        self.host=uri.hostname
        self.port=uri.port or 443
        self.pin=digest
        self.token=token
        self.model=str(cfg.get("model") or "")
        if not self.model or len(self.model)>120:
            raise ValueError("explicit local installed model name required")

    def infer(self, *, role, prompt, num_predict=384, num_ctx=4096):
        if role not in ("rishi_research","rishi_exam_author","rishi_exam_reviewer"):
            raise ValueError("invalid Rishi role")
        if not isinstance(prompt,str) or not 40<=len(prompt)<=12000:
            raise ValueError("bounded substantive evidence prompt required")
        body=json.dumps({"model":self.model,"role":role,"prompt":prompt,
                         "num_predict":num_predict,"num_ctx":num_ctx}).encode("utf-8")
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname=False
        ctx.verify_mode=ssl.CERT_NONE
        conn=http.client.HTTPSConnection(self.host,self.port,timeout=110,context=ctx)
        try:
            conn.connect()
            cert=conn.sock.getpeercert(binary_form=True)
            if not hmac.compare_digest(hashlib.sha256(cert).hexdigest(),self.pin):
                raise ssl.SSLError("BRAHMA inference certificate pin mismatch; secret withheld")
            conn.request("POST","/v1/infer",body=body,headers={
                "Content-Type":"application/json","Accept":"application/json",
                "Authorization":"Bearer "+self.token})
            res=conn.getresponse()
            raw=res.read(MAX_REPLY_BYTES+1)
            if len(raw)>MAX_REPLY_BYTES:
                raise RuntimeError("inference response oversized")
            if res.status!=200:
                raise RuntimeError("BRAHMA inference unavailable: HTTP "+str(res.status))
            obj=json.loads(raw)
            if (not isinstance(obj,dict) or obj.get("done") is not True
                    or obj.get("inference_local") is not True
                    or not isinstance(obj.get("response"),str)):
                raise RuntimeError("local inference is incomplete or unverified")
            return obj
        finally:
            conn.close()
