from __future__ import annotations

from dataclasses import dataclass, asdict
from threading import RLock


@dataclass(frozen=True)
class CapabilityProvider:
    capability: str
    provider_id: str
    priority: int=100
    free_only: bool=True
    lazy: bool=True
    local: bool=False
    mobile_direct: bool=False
    enabled: bool=True
    notes: str=""

    def as_dict(self):
        return asdict(self)


class CapabilityFabric:
    """Provider/consumer seam. Registration is metadata-only and reserves no model RAM."""

    def __init__(self):
        self._lock=RLock()
        self._providers={}

    def register(self, capability, provider_id, **kwargs):
        row=CapabilityProvider(str(capability),str(provider_id),**kwargs)
        with self._lock:
            self._providers[(row.capability,row.provider_id)]=row
        return row.as_dict()

    def list(self, capability=None):
        with self._lock:
            rows=list(self._providers.values())
        if capability is not None:
            rows=[x for x in rows if x.capability==str(capability)]
        return [x.as_dict() for x in sorted(rows,key=lambda x:(x.capability,x.priority,x.provider_id))]

    def choose(self, capability, *, require_free=True, prefer_mobile=False, prefer_local=False):
        rows=[x for x in self.list(capability) if x["enabled"]]
        if require_free:
            rows=[x for x in rows if x["free_only"]]
        if not rows:
            return None
        def score(x):
            return (
                0 if (prefer_mobile and x["mobile_direct"]) else 1,
                0 if (prefer_local and x["local"]) else 1,
                int(x["priority"]),
            )
        return sorted(rows,key=score)[0]

    def status(self):
        rows=self.list()
        return {
            "component":"KRISHNA Capability Fabric",
            "provider_count":len(rows),
            "capabilities":sorted(set(x["capability"] for x in rows)),
            "lazy_by_default":True,
            "always_on_heavy_runtime":False,
            "providers":rows,
        }


def build_default_capability_fabric():
    f=CapabilityFabric()
    # Mobile: phone-local and direct short-lived free cloud before PC escalation.
    f.register("vision","mobile-mlkit",priority=10,local=True,mobile_direct=True,notes="on-device lightweight perception")
    f.register("vision","gemini-live-ephemeral",priority=20,mobile_direct=True,notes="short-lived token; non-sensitive owner-approved session only")
    f.register("vision","krishna-pc-vision",priority=80,local=True,notes="private/heavy escalation")
    f.register("conversation","gemini-live-ephemeral",priority=10,mobile_direct=True,notes="general non-sensitive mobile conversation")
    f.register("conversation","krishna-pc",priority=80,local=True,notes="actions/private/project context")
    # Dots family is lazy metadata only: no model download/startup.
    f.register("multimodal-large","dots3-note-prev",priority=90,local=False,enabled=False,notes="280B/16B-active; future verified-free endpoint only")
    f.register("ocr-document","dots.mocr",priority=70,local=False,enabled=False,notes="enable after model-license/commercial review")
    f.register("voice","dots.tts",priority=60,local=True,enabled=False,notes="experimental provider; benchmark before activation")
    # Deterministic and defensive optional workers.
    f.register("science-compute","stemkit-core",priority=20,local=True,notes="lazy Node adapter; no daemon")
    f.register("dynamic-security","strix-local-sandbox",priority=70,local=True,enabled=False,notes="authorized local candidate targets only")
    f.register("decision","system-one",priority=10,local=True,notes="bounded option ranking; no authority")
    return f
