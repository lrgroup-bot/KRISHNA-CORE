from __future__ import annotations

from dataclasses import dataclass,asdict

@dataclass(frozen=True)
class ProviderCapabilities:
    text:bool=True
    reasoning:bool=False
    streaming:bool=False
    tool_calls:bool=False
    structured_output:bool=False
    vision:bool=False
    files:bool=False

@dataclass(frozen=True)
class NormalizedProvider:
    provider_id:str
    model:str
    local:bool
    available:bool
    context_size:int|None=None
    rate_limited:bool=False
    free_only:bool=False
    capabilities:ProviderCapabilities=ProviderCapabilities()
    metadata:dict|None=None

    def as_dict(self):
        d=asdict(self);d["metadata"]=dict(self.metadata or {});return d

def normalize_provider(row:dict)->dict:
    row=dict(row or {})
    pid=str(row.get("provider") or row.get("provider_id") or "").strip()
    if not pid:raise ValueError("provider id is required")
    local=bool(row.get("local"))
    caps=row.get("capabilities")
    if not isinstance(caps,dict):
        caps={
            "text":True,
            "reasoning":bool(row.get("reasoning",False)),
            "streaming":bool(row.get("streaming",False)),
            "tool_calls":bool(row.get("tool_calls",False)),
            "structured_output":bool(row.get("structured_output",False)),
            "vision":bool(row.get("vision",False)),
            "files":bool(row.get("files",False)),
        }
    known={k:bool(caps.get(k,False)) for k in ProviderCapabilities.__dataclass_fields__}
    known["text"]=bool(caps.get("text",True))
    obj=NormalizedProvider(
        provider_id=pid,model=str(row.get("model") or "unknown"),local=local,
        available=bool(row.get("available")),context_size=(int(row["context_size"]) if row.get("context_size") else None),
        rate_limited=bool(row.get("rate_limited",False)),free_only=bool(row.get("free_only",local)),
        capabilities=ProviderCapabilities(**known),
        metadata={k:v for k,v in row.items() if k not in {
            "provider","provider_id","model","local","available","context_size","rate_limited","free_only","capabilities",
            *ProviderCapabilities.__dataclass_fields__.keys(),
        }},
    )
    return obj.as_dict()

class UnifiedProviderRegistry:
    """Normalized capability view over KRISHNA model providers."""

    def __init__(self,router):
        self.router=router

    def list(self):
        return [normalize_provider(x) for x in self.router.available()]

    def select(self,*,privacy="local_only",vision=False,tool_calls=False,structured_output=False,free_only=False):
        rows=self.list()
        eligible=[]
        for row in rows:
            if not row["available"]:continue
            if privacy in {"local_only","restricted"} and not row["local"]:continue
            if free_only and not (row["local"] or row["free_only"]):continue
            caps=row["capabilities"]
            if vision and not caps["vision"]:continue
            if tool_calls and not caps["tool_calls"]:continue
            if structured_output and not caps["structured_output"]:continue
            eligible.append(row)
        eligible.sort(key=lambda x:(not x["local"],not x["free_only"],x["provider_id"]))
        return eligible

    def status(self):
        return {"owner":"KRISHNA Unified Model Provider Interface","providers":self.list(),
                "normalized_fields":["text","reasoning","streaming","tool_calls","structured_output","vision","files","context_size","rate_limited"],
                "selection":"privacy/capability/hardware policy is applied above provider adapters"}
