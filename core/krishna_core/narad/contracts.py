from __future__ import annotations

from dataclasses import asdict,dataclass,field


LEGACY_ACTION_MAP={
    "publish_event":"narad.publish_event",
    "adapter_webhook":"narad.adapter_webhook",
    "provider_send":"narad.provider_send",
}


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts:int=1
    delay_ms:int=0
    backoff:float=2.0
    retry_safe:bool=False

    @classmethod
    def from_value(cls,value):
        raw=dict(value or {})
        attempts=max(1,min(int(raw.get("max_attempts") or 1),5))
        delay=max(0,min(int(raw.get("delay_ms") or 0),10000))
        backoff=max(1.0,min(float(raw.get("backoff") or 2.0),4.0))
        return cls(attempts,delay,backoff,bool(raw.get("retry_safe",False)))

    def as_dict(self):return asdict(self)


@dataclass(frozen=True)
class WorkflowNode:
    id:str
    action:str
    dispatch:str="action"
    depends_on:tuple[str,...]=()
    payload:dict=field(default_factory=dict)
    retry:RetryPolicy=field(default_factory=RetryPolicy)
    continue_on_error:bool=False

    def as_dict(self):
        row=asdict(self)
        row["depends_on"]=list(self.depends_on)
        row["retry"]=self.retry.as_dict()
        return row


def required_permissions(nodes):
    out={"narad.execute"}
    for node in nodes:
        if node.action in {"narad.adapter_webhook","narad.provider_send"}:
            out.add("send_external")
    return sorted(out)
