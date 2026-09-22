"""Defensive threat-intelligence cache. Feeds are advisory, never auto-block."""
from __future__ import annotations
import ipaddress,time

class ThreatIntel:
    def __init__(self): self._items={}
    def add_ip(self,value,source,confidence=0.5,ttl=7200):
        ip=str(ipaddress.ip_address(value))
        self._items[ip]={"source":str(source),"confidence":max(0,min(1,float(confidence))),
                         "expires":time.time()+max(60,int(ttl))}
        return self._items[ip].copy()
    def lookup(self,value):
        item=self._items.get(str(value))
        if not item or item["expires"]<=time.time(): return None
        return item.copy()
    def decision(self,value):
        item=self.lookup(value)
        return {"indicator":str(value),"known":bool(item),"advisory":item,
                "auto_block":False,"requires_policy_gate":True}
