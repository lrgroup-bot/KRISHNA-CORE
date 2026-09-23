"""Evidence-oriented UI build/repair pipeline owned by Sudarshan."""
from dataclasses import dataclass,field
@dataclass
class UIEvidence:
 attempts:int=0; findings:list=field(default_factory=list)
class UIPipeline:
 def __init__(self,design_engine,max_repairs=3):
  self.engine=design_engine;self.max_repairs=max_repairs
 def next_action(self,checks,evidence:UIEvidence):
  verdict=self.engine.acceptance.evaluate(checks)
  if verdict["verified"]:return {"action":"accept","verdict":verdict}
  evidence.findings.append(verdict["failed"])
  if evidence.attempts>=self.max_repairs:return {"action":"escalate","verdict":verdict}
  evidence.attempts+=1
  return {"action":"repair-and-retest","failed":verdict["failed"],"attempt":evidence.attempts}
