"""KRISHNA zero-spend cloud storage policy and provider-neutral router.

Cloud is an asynchronous replica/archive tier, never authority for live cognitive state.
Accounts are owner-created and owner-authorized; this module never creates provider accounts.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

ZERO_SPEND_POLICY={
 "paid_storage":False,"auto_upgrade":False,"paid_egress":False,
 "auto_account_creation":False,"owner_authorization_required":True,
 "local_first":True,"delete_local_only_after_verified_replica":True,
}

@dataclass(frozen=True)
class StorageProvider:
    provider_id:str
    kind:str
    free_bytes:int
    healthy:bool=True
    free_tier:bool=True
    authorized:bool=True
    priority:int=100
    supports_resumable:bool=True

class NoFreeCapacity(RuntimeError):pass

def eligible(p:StorageProvider,size_bytes:int)->bool:
    return bool(p.healthy and p.free_tier and p.authorized and p.free_bytes>=max(0,int(size_bytes)))

def route(providers:Iterable[StorageProvider],size_bytes:int)->StorageProvider:
    choices=[p for p in providers if eligible(p,size_bytes)]
    if not choices:raise NoFreeCapacity("no authorized healthy free-tier provider has sufficient capacity")
    return max(choices,key=lambda p:(p.free_bytes,-p.priority,p.provider_id))

def replication_plan(providers:Iterable[StorageProvider],size_bytes:int,replicas:int=1):
    choices=sorted((p for p in providers if eligible(p,size_bytes)),key=lambda p:(-p.free_bytes,p.priority,p.provider_id))
    n=max(1,int(replicas))
    if len(choices)<n:raise NoFreeCapacity("insufficient independent free-tier capacity for requested replicas")
    return choices[:n]

def upload_policy(*,privacy:str,network:str,battery_percent:int,size_bytes:int,mobile:bool):
    privacy=privacy.lower()
    if privacy=="never_upload":return {"upload":False,"reason":"device_local_policy"}
    if mobile and size_bytes>=100*1024*1024 and network.lower()!="wifi":
        return {"upload":False,"reason":"large_mobile_upload_waits_for_wifi"}
    if mobile and int(battery_percent)<20:
        return {"upload":False,"reason":"battery_guard"}
    return {"upload":True,"encrypt":privacy in {"private","sensitive"},"checksum":"sha256","resumable":True}
