from __future__ import annotations
from dataclasses import dataclass,asdict

@dataclass(frozen=True)
class WorkRoute:
 phase:str; primary:str; cloud_allowed:bool; github_allowed:bool
 privacy:str; reason:str; sanitize_before_cloud:bool=True
 def as_dict(self):return asdict(self)

class ProjectWorkPolicy:
 """KRISHNA project law: research externally, build locally, escalate narrowly."""
 RESEARCH={"research","discovery","web_research","github_research","market_scan","docs_research"}
 IMPLEMENT={"architecture","planning","backend","frontend","android","ios","implementation","coding","debug","repair","integration","refactor"}
 VERIFY={"test","testing","qa","security","review","build","release_verify","verification"}

 def route(self,phase,*,sensitive=False,local_failed=False,free_cloud_verified=False,
           github_zero_cost_verified=False):
  p=str(phase or "").strip().lower().replace("-","_")
  if sensitive:
   return WorkRoute(p,"local",False,False,"local_only",
    "sensitive/private project material never escalates to cloud",True).as_dict()
  if p in self.RESEARCH:
   return WorkRoute(p,"web+github-research",True,True,"public_research_only",
    "collect current public findings externally; do not expose private project state",True).as_dict()
  if p in self.IMPLEMENT:
   if local_failed and free_cloud_verified:
    return WorkRoute(p,"verified-free-cloud-escalation",True,False,"approved_cloud_redacted",
     "local implementation failed; cloud may diagnose only with minimal sanitized context",True).as_dict()
   return WorkRoute(p,"local",False,False,"local_only",
    "all project creation/modification is local-first and local-only until a recorded failure",True).as_dict()
  if p in self.VERIFY:
   return WorkRoute(p,"local-tests",False,bool(github_zero_cost_verified),"local_only",
    "run local verification first; GitHub is an independent verifier only when zero-cost is proven",True).as_dict()
  return WorkRoute(p,"local",False,False,"local_only",
   "unknown phases fail closed to local execution",True).as_dict()

 def cloud_escalation_packet(self,*,problem,public_findings=None,redacted_context=None,sensitive=False):
  if sensitive: raise PermissionError("cloud escalation blocked for sensitive/private project context")
  return {
   "problem":str(problem or "")[:4000],
   "public_findings":list(public_findings or [])[:20],
   "redacted_context":dict(redacted_context or {}),
   "forbidden":["credentials","tokens","private files","full repository","personal data","internal secrets"],
   "execution_authority":"NONE; cloud returns advice/patch suggestion only",
   "implementation_location":"local isolated worktree",
   "money_cost":"₹0 only",
  }
