from __future__ import annotations

from dataclasses import dataclass, asdict
from threading import RLock
from typing import Any


@dataclass(frozen=True)
class CapabilityProvider:
    provider_id: str
    capability: str
    location: str
    free_only: bool
    resident: bool = False
    enabled: bool = True
    sensitive_allowed: bool = False
    heavy: bool = False
    notes: str = ""

    def as_dict(self): return asdict(self)


class CapabilityFabric:
    """Provider/consumer seam for KRISHNA.

    Providers are metadata until invoked by their owning adapter. Registration
    never starts a model or background process, preventing capability discovery
    from increasing KRISHNA's idle memory/CPU load.
    """

    VERSION="capability-fabric-v2"

    def __init__(self, system_one=None):
        self.system_one=system_one
        self._lock=RLock()
        self._providers:dict[str,CapabilityProvider]={}

    def register(self, provider_id, capability, location, *, free_only,
                 resident=False, enabled=True, sensitive_allowed=False,
                 heavy=False, notes=""):
        row=CapabilityProvider(
            str(provider_id),str(capability),str(location),bool(free_only),
            bool(resident),bool(enabled),bool(sensitive_allowed),bool(heavy),str(notes),
        )
        with self._lock:self._providers[row.provider_id]=row
        return row.as_dict()

    def list(self, capability=None):
        with self._lock:rows=list(self._providers.values())
        if capability:
            rows=[x for x in rows if x.capability==str(capability)]
        return [x.as_dict() for x in sorted(rows,key=lambda x:(x.capability,x.provider_id))]

    def route(self, capability, *, sensitive=False, mobile=False, prefer_free=True,
              heavy=False, context=None):
        rows=[
            x for x in self._providers.values()
            if x.enabled and x.capability==str(capability)
            and (not sensitive or x.sensitive_allowed)
            and (not prefer_free or x.free_only)
        ]
        if mobile:
            preferred=[x for x in rows if x.location in {"mobile","cloud"}]
            if preferred: rows=preferred
        if not heavy:
            light=[x for x in rows if not x.heavy]
            if light: rows=light
        if not rows:
            return {"selected":None,"candidates":[],"reason":"no eligible provider"}
        options=[x.provider_id for x in rows]
        if self.system_one and len(options)>1:
            decision=self.system_one.choose({
                **dict(context or {}),"capability":capability,"sensitive":sensitive,
                "mobile":mobile,"heavy":heavy,
            },options)
            selected=decision["choice"]
        else:
            decision=None
            selected=options[0]
        return {
            "selected":selected,
            "provider":next(x.as_dict() for x in rows if x.provider_id==selected),
            "candidates":[x.as_dict() for x in rows],
            "decision":decision,
            "authority":"provider recommendation only; Sudarshan/PolicyKernel governs execution",
        }

    def status(self):
        rows=self.list()
        return {
            "component":"KRISHNA Capability Fabric",
            "version":self.VERSION,
            "providers":rows,
            "provider_count":len(rows),
            "resident_provider_count":sum(bool(x["resident"]) for x in rows),
            "idle_load_policy":"registration never starts provider runtimes",
        }
