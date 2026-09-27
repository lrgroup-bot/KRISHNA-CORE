from __future__ import annotations

"""Private-LAN client used by portable SURYDEV learning nodes.

The high-entropy credential is generated and retained on the learning node.
Only its SHA-256 digest is submitted during pairing, matching KRISHNA's existing
DevicePairingStore contract.
"""

from pathlib import Path
import hashlib
import ipaddress
import json
import os
import secrets
import socket
import time
import urllib.error
import urllib.request
import uuid

from .lan_discovery import DISCOVERY_MAGIC, DISCOVERY_PORT


class SuryadevDeviceClient:
    VERSION="suryadev-device-client-v1"

    def __init__(self,root):
        self.root=Path(root)
        self.root.mkdir(parents=True,exist_ok=True)
        self.identity_file=self.root/"device-identity.json"
        self.core_file=self.root/"core-connection.json"

    @staticmethod
    def _private_host(host):
        try:
            ip=ipaddress.ip_address(str(host))
        except ValueError:
            return str(host).lower().endswith(".ts.net")
        if ip.is_loopback or ip.is_link_local or ip.is_private:return True
        if isinstance(ip,ipaddress.IPv4Address) and ip in ipaddress.ip_network("100.64.0.0/10"):
            return True
        return False

    def _save(self,path,value,secret=False):
        tmp=path.with_suffix(path.suffix+".tmp")
        tmp.write_text(json.dumps(value,indent=2),encoding="utf-8")
        os.replace(tmp,path)
        if secret:
            try:os.chmod(path,0o600)
            except OSError:pass

    def identity(self):
        if self.identity_file.exists():
            try:
                row=json.loads(self.identity_file.read_text(encoding="utf-8"))
                if row.get("device_id") and row.get("credential"):
                    return row
            except Exception:
                # Fail closed rather than silently overwriting a possibly recoverable credential.
                raise RuntimeError("SURYDEV device identity is unreadable; refusing to replace it")
        row={
            "device_id":"suryadev-node-"+str(uuid.uuid4()),
            "credential":secrets.token_urlsafe(64),
            "created_at":time.time(),
        }
        self._save(self.identity_file,row,secret=True)
        return row

    def discover(self,timeout=1.6):
        cached=None
        if self.core_file.exists():
            try:cached=json.loads(self.core_file.read_text(encoding="utf-8"))
            except Exception:cached=None
        if cached and self.health(cached.get("base_url")):
            return cached
        last=None
        for target in ("255.255.255.255","127.0.0.1"):
            s=None
            try:
                s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
                s.settimeout(float(timeout))
                s.sendto(DISCOVERY_MAGIC,(target,DISCOVERY_PORT))
                raw,addr=s.recvfrom(2048)
                data=json.loads(raw.decode("utf-8"))
                if data.get("service")!="KRISHNA_CORE":continue
                if not self._private_host(addr[0]):continue
                port=int(data.get("port") or 8766)
                base=f"http://{addr[0]}:{port}"
                if not self.health(base):continue
                row={"base_url":base,"discovered_at":time.time(),"transport":"private-lan"}
                self._save(self.core_file,row)
                return row
            except Exception as exc:last=exc
            finally:
                if s is not None:s.close()
        return {"base_url":"","error":None if last is None else f"{type(last).__name__}: {last}","transport":"offline"}

    @staticmethod
    def _request(url,*,method="GET",body=None,headers=None,timeout=8):
        data=None
        req_headers={"Accept":"application/json",**dict(headers or {})}
        if body is not None:
            data=json.dumps(body).encode("utf-8")
            req_headers["Content-Type"]="application/json"
        req=urllib.request.Request(url,data=data,headers=req_headers,method=method)
        try:
            with urllib.request.urlopen(req,timeout=timeout) as res:
                raw=res.read(8*1024*1024)
                parsed=json.loads(raw.decode("utf-8") or "{}")
                return int(res.status),parsed
        except urllib.error.HTTPError as exc:
            raw=exc.read(2*1024*1024)
            try:parsed=json.loads(raw.decode("utf-8") or "{}")
            except Exception:parsed={"error":f"HTTP {exc.code}"}
            return int(exc.code),parsed

    def health(self,base_url):
        base=str(base_url or "").rstrip("/")
        if not base:return False
        try:
            host=urllib.request.urlparse(base).hostname  # pragma: no cover - fallback below
        except Exception:
            host=None
        if host is None:
            from urllib.parse import urlparse
            host=urlparse(base).hostname
        if not host or not self._private_host(host):return False
        try:
            code,data=self._request(base+"/health",timeout=2)
            return code==200 and bool(data.get("ok"))
        except Exception:
            return False

    def _auth_headers(self):
        ident=self.identity()
        return {
            "X-Krishna-Device":ident["device_id"],
            "Authorization":"Device "+ident["credential"],
        }

    def request_pairing(self,base_url,name="SURYDEV Learning Node"):
        ident=self.identity()
        digest=hashlib.sha256(ident["credential"].encode("utf-8")).hexdigest()
        code,data=self._request(
            str(base_url).rstrip("/")+"/api/mobile/pair/request",
            method="POST",
            body={
                "device_id":ident["device_id"],
                "name":str(name)[:128],
                "credential_sha256":digest,
            },
            headers={"X-Krishna-Device":ident["device_id"]},
        )
        return {"http_status":code,**data}

    def assignment(self,base_url):
        code,data=self._request(
            str(base_url).rstrip("/")+"/api/suryadev/horse/assignment",
            headers=self._auth_headers(),
        )
        return code,data

    def auto_enroll(self,profile,*,label="SURYDEV learning node"):
        conn=self.discover()
        base=conn.get("base_url") or ""
        if not base:
            return {"connected":False,"paired":False,"assigned":False,"reason":"KRISHNA Core not discovered on private LAN","connection":conn}
        code,current=self.assignment(base)
        if code==200:
            return {
                "connected":True,"paired":True,"assigned":True,
                "device_id":self.identity()["device_id"],
                "assignment":current,
                "core":base,
            }
        if code==401:
            request=self.request_pairing(base,label)
            return {
                "connected":True,"paired":False,"assigned":False,
                "device_id":self.identity()["device_id"],
                "pairing":request,
                "core":base,
                "next_action":"approve this device on KRISHNA PC; the same local credential becomes valid after approval",
            }
        if code not in {403,404}:
            return {"connected":True,"paired":False,"assigned":False,"http_status":code,"response":current,"core":base}
        # 404 means paired but not yet bound; 403 may be an older allowlist/runtime.
        if code==403:
            return {"connected":True,"paired":True,"assigned":False,"http_status":code,"response":current,"core":base}
        pcode,pdata=self._request(
            base+"/api/suryadev/horse/profile",
            method="POST",
            body={"profile":dict(profile or {}),"label":str(label)[:240]},
            headers=self._auth_headers(),
        )
        return {
            "connected":True,
            "paired":pcode!=401,
            "assigned":pcode==200 and bool(pdata.get("binding")),
            "device_id":self.identity()["device_id"],
            "http_status":pcode,
            "assignment":pdata,
            "core":base,
        }

    def heartbeat(self,base_url,status):
        code,data=self._request(
            str(base_url).rstrip("/")+"/api/suryadev/horse/heartbeat",
            method="POST",body={"status":dict(status or {})},headers=self._auth_headers(),
        )
        return {"http_status":code,**data}

    def curriculum(self,base_url):
        code,data=self._request(
            str(base_url).rstrip("/")+"/api/suryadev/horse/curriculum",
            headers=self._auth_headers(),
        )
        return {"http_status":code,**data}

    def upload_learning(self,base_url,batch):
        code,data=self._request(
            str(base_url).rstrip("/")+"/api/suryadev/horse/learning",
            method="POST",body={"batch":dict(batch or {})},headers=self._auth_headers(),timeout=30,
        )
        return {"http_status":code,**data}
