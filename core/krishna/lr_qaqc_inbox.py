from __future__ import annotations
from dataclasses import dataclass,field
from typing import Any
from .lr_qaqc_contract import validate_lr_qaqc_event
@dataclass
class LRQAQCInbox:
    seen:set[str]=field(default_factory=set)
    artifact_versions:dict[str,int]=field(default_factory=dict)
    events:list[dict[str,Any]]=field(default_factory=list)
    def accept(self,event:dict[str,Any])->dict[str,Any]:
        check=validate_lr_qaqc_event(event)
        if not check["valid"]: return {"accepted":False,"reason":"CONTRACT_INVALID","errors":check["errors"]}
        eid=str(event["eventId"])
        if eid in self.seen:return {"accepted":False,"reason":"DUPLICATE_EVENT"}
        aid=str(event["artifactId"]);version=int(event["artifactVersion"]);prior=self.artifact_versions.get(aid,0)
        if version<prior:return {"accepted":False,"reason":"STALE_ARTIFACT_VERSION","priorVersion":prior}
        if prior and version>prior+1:return {"accepted":False,"reason":"VERSION_GAP","priorVersion":prior,"receivedVersion":version}
        self.seen.add(eid);self.artifact_versions[aid]=max(prior,version);self.events.append(event)
        return {"accepted":True,"reason":"ACCEPTED","route":"KRISHNA","artifactVersion":version}
