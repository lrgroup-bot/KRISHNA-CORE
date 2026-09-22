from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse
import ipaddress


@dataclass(frozen=True)
class Endpoint:
    name: str
    url: str
    priority: int


class HawkeyeEndpointPolicy:
    """Choose KRISHNA connectivity without making the cloud the authority.

    Order: direct/private PC -> configured HTTPS cloud relay -> phone-only field mode.
    The relay is transport only; device authentication and Core policy remain authoritative.
    """

    def __init__(self, pc_url: str = "", cloud_url: str = ""):
        self.pc_url = pc_url.strip().rstrip("/")
        self.cloud_url = cloud_url.strip().rstrip("/")

    @staticmethod
    def private_pc_url(value: str) -> bool:
        try:
            u = urlparse(value)
            if u.scheme not in {"http", "https"} or not u.hostname:
                return False
            host = u.hostname.lower()
            if host == "localhost" or host.endswith(".ts.net"):
                return True
            ip = ipaddress.ip_address(host)
            return ip.is_private or ip.is_loopback or ip.is_link_local or ip in ipaddress.ip_network("100.64.0.0/10")
        except ValueError:
            return False

    @staticmethod
    def secure_cloud_url(value: str) -> bool:
        try:
            u = urlparse(value)
            return u.scheme == "https" and bool(u.hostname) and u.username is None and u.password is None
        except ValueError:
            return False

    def candidates(self):
        out = []
        if self.pc_url and self.private_pc_url(self.pc_url):
            out.append(Endpoint("pc-private", self.pc_url, 10))
        if self.cloud_url and self.secure_cloud_url(self.cloud_url):
            out.append(Endpoint("cloud-relay", self.cloud_url, 20))
        return sorted(out, key=lambda x: x.priority)

    def field_fallback(self):
        return {
            "mode": "HAWKEYE_FIELD",
            "network_required": False,
            "authority": "local-phone-capture",
            "sync_when_reachable": True,
        }
