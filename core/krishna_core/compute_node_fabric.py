from __future__ import annotations

from dataclasses import dataclass,asdict
from pathlib import Path
import json,time


@dataclass
class ComputeNode:
    node_id:str
    platform:str
    capabilities:list[str]
    trusted:bool=False
    online:bool=False
    last_seen:float=0.0
    endpoint:str=""
    def as_dict(self):return asdict(self)


class ComputeNodeFabric:
    """Trusted execution-node registry for Windows/Mac/Linux workers.

    Registration never grants source access. A node must be trusted and explicitly
    advertise the capability required by a mission.
    """
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self.nodes={}
        if self.path.exists():
            for row in json.loads(self.path.read_text(encoding="utf-8") or "[]"):
                n=ComputeNode(**row);self.nodes[n.node_id]=n

    def _save(self):self.path.write_text(json.dumps([n.as_dict() for n in self.nodes.values()],indent=2),encoding="utf-8")

    def register(self,node_id,platform,capabilities,endpoint=""):
        key=str(node_id).strip()
        if not key:raise ValueError("node_id is required")
        node=ComputeNode(key,str(platform).lower(),sorted({str(x) for x in capabilities if str(x).strip()}),False,False,0.0,str(endpoint))
        self.nodes[key]=node;self._save();return node.as_dict()

    def trust(self,node_id,approved=False):
        if not approved:raise PermissionError("owner approval required to trust a compute node")
        node=self.nodes[str(node_id)];node.trusted=True;self._save();return node.as_dict()

    def heartbeat(self,node_id,capabilities=None):
        node=self.nodes[str(node_id)];node.online=True;node.last_seen=time.time()
        if capabilities is not None:node.capabilities=sorted({str(x) for x in capabilities})
        self._save();return node.as_dict()

    def select(self,capability,platform=None):
        rows=[n for n in self.nodes.values() if n.trusted and n.online and capability in n.capabilities and (not platform or n.platform==platform)]
        rows.sort(key=lambda n:n.last_seen,reverse=True)
        return rows[0].as_dict() if rows else None

    def status(self):return {"component":"KRISHNA Compute Node Fabric","nodes":[n.as_dict() for n in self.nodes.values()]}
