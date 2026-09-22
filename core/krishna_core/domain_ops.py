"""Read-only-first domain/DNS/SSL operations for KRISHNA infrastructure."""
from __future__ import annotations
import socket
from .ops_monitor import OpsMonitor

class DomainOps:
    def __init__(self): self.monitor=OpsMonitor()
    def inspect(self,domain):
        domain=str(domain).strip().lower().rstrip(".")
        if not domain or "/" in domain: raise ValueError("plain domain required")
        return {"domain":domain,"dns":self.monitor.dns(domain),"tls":self.monitor.tls(domain),
                "mode":"read_only","dns_mutation":False}
    def plan_change(self,domain,record_type,name,value):
        return {"domain":str(domain),"record":{"type":str(record_type).upper(),"name":str(name),"value":str(value)},
                "executed":False,"requires_owner_approval":True,"requires_provider_adapter":True}
