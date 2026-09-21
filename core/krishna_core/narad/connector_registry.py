from __future__ import annotations
from dataclasses import asdict,dataclass


@dataclass(frozen=True)
class ConnectorOperation:
    provider:str
    operation:str
    mutating:bool
    permission:str
    retry_safe:bool=False
    description:str=""
    def as_dict(self):return asdict(self)


class ConnectorRegistry:
    """Small n8n-inspired connector contract registry.

    This does not execute providers. It describes allowed operations so NARAD can
    derive permissions/retry policy without importing an external workflow engine.
    """
    def __init__(self):
        self._items={}

    def register(self,provider,operation,*,mutating,permission,retry_safe=False,description=""):
        key=(str(provider).strip().lower(),str(operation).strip().lower())
        if not all(key):raise ValueError("provider and operation are required")
        item=ConnectorOperation(key[0],key[1],bool(mutating),str(permission),bool(retry_safe),str(description))
        self._items[key]=item
        return item.as_dict()

    def get(self,provider,operation):
        key=(str(provider).strip().lower(),str(operation).strip().lower())
        item=self._items.get(key)
        if not item:raise KeyError(f"connector operation not registered: {key[0]}.{key[1]}")
        return item

    def list(self):
        return [self._items[k].as_dict() for k in sorted(self._items)]

    def status(self):
        return {"owner":"NARAD Connector Registry","count":len(self._items),"operations":self.list()}
