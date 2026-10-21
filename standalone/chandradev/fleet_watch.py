"""CHANDRADEV 24/7 private fleet observer on its own PC.

Read-only, outbound HTTPS, pinned server certificate and owner-paired
chandradev-* identity. It never restarts machines, takes screenshots, runs
shell commands, collects raw media, downloads source data or invokes Ollama.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import http.client
import ipaddress
import json
import os
from pathlib import Path
import ssl
import time
from urllib.parse import urlsplit

SCHEMA="chandradev.fleet-observer.v1"


def load_config(path):
    filename=Path(path).expanduser().resolve(strict=True)
    data=json.loads(filename.read_text(encoding="utf-8"))
    if not isinstance(data,dict) or data.get("schema")!=SCHEMA:
        raise ValueError("invalid owner-paired CHANDRADEV observer config")
    address=urlsplit(data.get("endpoint",""))
    if (address.scheme!="https" or not address.hostname
            or address.username or address.password or address.query
            or address.fragment or address.path not in ("","/")):
        raise ValueError("observer needs private pinned HTTPS origin")
    try:ip=ipaddress.ip_address(address.hostname)
    except ValueError as exc:raise ValueError("explicit private IPv4 required") from exc
    lans=(ipaddress.ip_network("10.0.0.0/8"),
          ipaddress.ip_network("172.16.0.0/12"),
          ipaddress.ip_network("192.168.0.0/16"),
          ipaddress.ip_network("127.0.0.0/8"))
    if ip.version!=4 or not any(ip in net for net in lans):
        raise ValueError("observer cannot send credentials to public networks")
    pin=str(data.get("cert_sha256") or "").lower().replace(":","")
    if len(pin)!=64 or any(ch not in "0123456789abcdef" for ch in pin):
        raise ValueError("valid TLS leaf certificate SHA256 required")
    device=str(data.get("device_id") or "")
    if not device.startswith("chandradev-") or len(device)>200:
        raise ValueError("owner-paired CHANDRADEV identity required")
    token_file=Path(data.get("token_file") or "")
    if not token_file.is_absolute():
        token_file=filename.parent/token_file
    token=token_file.expanduser().resolve(strict=True).read_text(encoding="ascii").strip()
    if not 48<=len(token)<=256 or not token.isascii() or not token.isprintable():
        raise ValueError("long private device token required")
    return {"host":address.hostname,"port":address.port or 443,
            "device_id":device,"pin":pin,"token":token}


def fetch_status(config):
    tls=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    tls.check_hostname=False
    tls.verify_mode=ssl.CERT_NONE
    conn=http.client.HTTPSConnection(config["host"],config["port"],timeout=12,context=tls)
    try:
        conn.connect()
        leaf=hashlib.sha256(conn.sock.getpeercert(binary_form=True)).hexdigest()
        if not hmac.compare_digest(leaf,config["pin"]):
            raise ssl.SSLError("CHANDRADEV peer certificate mismatch; secret withheld")
        conn.request("GET","/api/chandradev/fleet/health",headers={
            "Authorization":"Device "+config["token"],
            "X-Krishna-Device":config["device_id"],
            "Accept":"application/json"})
        res=conn.getresponse()
        body=res.read(131073)
        if len(body)>131072:raise RuntimeError("oversized fleet report")
        if res.status!=200:raise RuntimeError("Core fleet read refused: HTTP "+str(res.status))
        result=json.loads(body)
        if not isinstance(result,dict) or not isinstance(result.get("nodes"),list):
            raise ValueError("invalid CHANDRADEV fleet health response")
        return result
    finally:
        conn.close()


class ChandradevFleetWatch:
    def __init__(self, root, config, *, transport=fetch_status, clock=time.time):
        self.root=Path(root).expanduser().resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.file=self.root/"fleet-health-history.json"
        self.config=config
        self.transport=transport
        self.clock=clock

    def _state(self):
        if not self.file.exists():
            return {"schema":SCHEMA,"last":{},"events":[]}
        value=json.loads(self.file.read_text(encoding="utf-8"))
        if (not isinstance(value,dict) or value.get("schema")!=SCHEMA
                or not isinstance(value.get("last"),dict)
                or not isinstance(value.get("events"),list)):
            raise RuntimeError("CHANDRADEV fleet journal unreadable; refuse overwrite")
        return value

    def tick(self):
        result=self.transport(self.config)
        rows=result["nodes"]
        if any(not isinstance(n,dict) or not isinstance(n.get("device_id"),str)
               or not isinstance(n.get("state"),str) for n in rows):
            raise ValueError("invalid fleet health node")
        state=self._state()
        when=float(self.clock())
        latest={str(n["device_id"]):str(n["state"]) for n in rows}
        changes=[{"device_id":device,"previous":state["last"].get(device),
                  "state":status,"observed_at":when}
                 for device,status in latest.items()
                 if state["last"].get(device)!=status]
        changes += [{"device_id":dev,"previous":old,"state":"missing_from_snapshot",
                     "observed_at":when} for dev,old in state["last"].items() if dev not in latest]
        state["last"]=latest
        state["events"]=(state["events"]+changes)[-1000:]
        state["last_success"]=when
        temp=self.file.with_suffix(".tmp")
        with temp.open("w",encoding="utf-8") as f:
            json.dump(state,f,indent=2,ensure_ascii=False)
            f.flush();os.fsync(f.fileno())
        os.replace(temp,self.file)
        return {"nodes":len(rows),"changes":changes,
                "alerts":result.get("alerts"),"observed_at":when,
                "action":"read_only_no_remote_control"}

def main(argv=None):
    p=argparse.ArgumentParser(description="CHANDRADEV independent fleet observation")
    p.add_argument("--config",required=True)
    p.add_argument("--data",required=True)
    p.add_argument("--interval",type=int,default=60)
    a=p.parse_args(argv)
    if not 60<=a.interval<=3600:
        p.error("interval must be 60..3600 seconds")
    watcher=ChandradevFleetWatch(a.data,load_config(a.config))
    while True:
        try:
            print(json.dumps(watcher.tick(),ensure_ascii=False),flush=True)
        except (OSError,ValueError,RuntimeError,ssl.SSLError) as exc:
            print(json.dumps({"state":"temporarily_unavailable",
                              "error_type":type(exc).__name__,
                              "knowledge_verified":False}),flush=True)
        try:time.sleep(a.interval)
        except KeyboardInterrupt:break

if __name__=="__main__":
    main()
