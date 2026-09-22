from __future__ import annotations

import ipaddress
import os


class PrivateRemotePolicy:
    MOBILE_ROUTES=frozenset({
        "/api/status",
        "/api/mobile/connection",
        "/api/mobile/resume",
        "/api/mobile/control",
        "/api/core/event",
        "/api/core/state",
        "/api/core/chat",
        "/api/chats/create",
        "/api/chat/history",
        "/api/attachments",
        "/api/bhumiputra/live/start",
        "/api/bhumiputra/live/frame",
        "/api/bhumiputra/live/state",
        "/api/mobile-log",
    })
    """Network boundary for KRISHNA Mobile/remote clients.

    Loopback and RFC1918/ULA LAN addresses are allowed. Overlay address ranges are
    opt-in through KRISHNA_PRIVATE_REMOTE_CIDRS. Public Internet clients are rejected
    even if they somehow possess a device credential.
    """

    def __init__(self,cidrs=None):
        raw=cidrs if cidrs is not None else os.getenv("KRISHNA_PRIVATE_REMOTE_CIDRS","")
        self.networks=[]
        for item in str(raw or "").split(","):
            item=item.strip()
            if not item:continue
            try:self.networks.append(ipaddress.ip_network(item,strict=False))
            except ValueError:raise ValueError(f"invalid private remote CIDR: {item}")

    @staticmethod
    def _lan(ip):
        return ip.is_loopback or ip.is_private or ip.is_link_local

    def classify(self,address:str)->dict:
        try:ip=ipaddress.ip_address(str(address))
        except ValueError:return {"allowed":False,"kind":"invalid","address":str(address)}
        if self._lan(ip):return {"allowed":True,"kind":"local_or_lan","address":str(ip)}
        for net in self.networks:
            if ip in net:return {"allowed":True,"kind":"private_overlay","address":str(ip),"network":str(net)}
        return {"allowed":False,"kind":"public_rejected","address":str(ip)}

    def allowed(self,address:str)->bool:
        return bool(self.classify(address)["allowed"])

    def mobile_route_allowed(self,path:str)->bool:
        return str(path or "") in self.MOBILE_ROUTES

    def status(self):
        return {"mode":"private-network-only","overlay_cidrs":[str(x) for x in self.networks],
                "mobile_route_count":len(self.MOBILE_ROUTES),
                "policy":"public Internet clients are rejected; paired remote devices are restricted to the conversation/mobile API allowlist"}
