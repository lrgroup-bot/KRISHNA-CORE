from __future__ import annotations
from dataclasses import dataclass,asdict
@dataclass
class Check: name:str; passed:bool; evidence:str=""
class MachineCertification:
 """Evidence ledger for physical-host acceptance; CI cannot self-certify real hardware."""
 REQUIRED=("cpu","ram","gpu","disk","network","core","guardian","action_bus","mrityunjay","vishwakarma","brahma",
 "restart","network_loss","model_failure","rollback","reboot")
 def __init__(self): self.checks={}
 def record(self,name,passed,evidence=""): self.checks[name]=Check(name,bool(passed),str(evidence)); return asdict(self.checks[name])
 def report(self,burn_in_hours=0):
  missing=[x for x in self.REQUIRED if x not in self.checks]
  failed=[x for x,v in self.checks.items() if not v.passed]
  certified=not missing and not failed and float(burn_in_hours)>=24
  return {"certified":certified,"missing":missing,"failed":failed,"burn_in_hours":float(burn_in_hours),
          "checks":{k:asdict(v) for k,v in self.checks.items()},
          "note":"72h and 7-day runs increase confidence; minimum certification gate is 24h."}
