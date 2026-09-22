"""Lightweight CheckCle-inspired runtime monitoring for KRISHNA."""
from __future__ import annotations
import socket, ssl, time, urllib.request
from urllib.parse import urlparse

class OpsMonitor:
    def http(self,url,timeout=5):
        started=time.time()
        try:
            with urllib.request.urlopen(url,timeout=timeout) as r:
                return {"ok":200 <= r.status < 400,"status":r.status,"latency_ms":round((time.time()-started)*1000,1)}
        except Exception as e:
            return {"ok":False,"error":type(e).__name__,"latency_ms":round((time.time()-started)*1000,1)}

    def tcp(self,host,port,timeout=3):
        started=time.time()
        try:
            with socket.create_connection((host,int(port)),timeout=timeout): pass
            return {"ok":True,"latency_ms":round((time.time()-started)*1000,1)}
        except OSError as e:
            return {"ok":False,"error":type(e).__name__,"latency_ms":round((time.time()-started)*1000,1)}

    def dns(self,host):
        try:return {"ok":True,"addresses":sorted({x[4][0] for x in socket.getaddrinfo(host,None)})}
        except OSError as e:return {"ok":False,"error":type(e).__name__,"addresses":[]}

    def tls(self,host,port=443,timeout=5):
        try:
            ctx=ssl.create_default_context()
            with socket.create_connection((host,int(port)),timeout=timeout) as raw:
                with ctx.wrap_socket(raw,server_hostname=host) as s:
                    cert=s.getpeercert()
            return {"ok":True,"not_after":cert.get("notAfter"),"issuer":cert.get("issuer")}
        except (OSError,ssl.SSLError) as e:return {"ok":False,"error":type(e).__name__}
