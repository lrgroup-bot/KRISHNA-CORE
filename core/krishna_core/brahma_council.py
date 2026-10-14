from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json

class BrahmaCouncil:
    """Daily council over active + inactive agents. Reports to KRISHNA only."""
    def __init__(self, root, karma):
        self.root=Path(root).resolve(); self.root.mkdir(parents=True,exist_ok=True); self.karma=karma
    def meeting(self, agents, *, improvement_proposals=None):
        rows=[]
        for a in agents:
            name=str(a.get("name") or "").strip()
            if not name: continue
            trust=self.karma.permissions(name)
            rows.append({"name":name,"active":bool(a.get("active")),"role":a.get("role"),
              "health":a.get("health","unknown"),"last_work":a.get("last_work"),
              "karma":trust,"issues":list(a.get("issues") or [])})
        proposals=[]
        for p in improvement_proposals or []:
            cost=str(p.get("money_cost","₹0")).strip().lower()
            free=cost in {"0","₹0","$0","free","none",""}
            proposals.append({**p,"free_priority":free,
              "council_status":"CANDIDATE" if free else "PAID_BLOCKED",
              "rule":"FREE/₹0 solutions have highest priority; paid execution is never automatic."})
        report={"schema":"krishna.brahma-council.v1","meeting_at":datetime.now(timezone.utc).isoformat(),
          "chair":"BRAHMA","reports_to":"KRISHNA","agents":rows,"improvement_proposals":proposals,
          "priority_order":["safety/privacy","FREE/₹0","reliability/self-heal","efficiency/performance","capability","UI/UX"],
          "paid_policy":"Paid proposals are blocked from normal execution and may only be shown to OWNER for explicit decision.",
          "summary":{"total_agents":len(rows),"active":sum(x["active"] for x in rows),
                     "inactive":sum(not x["active"] for x in rows),
                     "restricted":sum(x["karma"]["state"] in {"ORANGE","RED","BLACK"} for x in rows)}}
        path=self.root/("BRAHMA_DAILY_COUNCIL_"+datetime.now(timezone.utc).date().isoformat()+".json")
        path.write_text(json.dumps(report,indent=2),encoding="utf-8")
        return report
