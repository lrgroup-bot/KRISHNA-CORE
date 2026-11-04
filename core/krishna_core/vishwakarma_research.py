from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib, json

@dataclass(frozen=True)
class ImprovementProposal:
    proposal_id:str; source_name:str; source_url:str; source_version:str
    license:str; what_it_does:str; krishna_benefit:str; expected_efficiency_gain:str
    security_privacy_risk:str; local_resource_cost:str; money_cost:str
    alternatives_checked:list[str]; affected_components:list[str]; test_plan:list[str]
    frontend_impact:str; rollback_plan:str

class VishwakarmaResearchShishya:
    """Evidence collector only. It has no install, mutation, merge or promotion API."""
    def __init__(self, proposal_root):
        from pathlib import Path
        self.root=Path(proposal_root).resolve(); self.root.mkdir(parents=True,exist_ok=True)
    @staticmethod
    def proposal_id(source_url,source_version):
        raw=(str(source_url)+"@"+str(source_version)).encode()
        return "proposal-"+hashlib.sha256(raw).hexdigest()[:16]
    def record(self, **kwargs):
        money=str(kwargs.get("money_cost","")).strip()
        if money not in {"0","₹0","$0","FREE","free"}:
            raise ValueError("research proposals default to zero-spend; paid proposals require a separate owner-controlled process")
        pid=self.proposal_id(kwargs["source_url"],kwargs.get("source_version",""))
        p=ImprovementProposal(proposal_id=pid,**kwargs)
        row={"schema":"krishna.vishwakarma-research-proposal.v1","status":"PROPOSED",
             "created_at":datetime.now(timezone.utc).isoformat(),**asdict(p),
             "owner_decision":None,"implementation_authorized":False}
        path=self.root/(pid+".json"); path.write_text(json.dumps(row,indent=2),encoding="utf-8")
        return row
    def status(self, proposal_id):
        path=self.root/(str(proposal_id)+".json")
        return json.loads(path.read_text(encoding="utf-8"))
