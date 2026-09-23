"""Safe mid-project idea intake: capture -> impact -> plan -> approve -> implement."""
from dataclasses import dataclass,asdict
@dataclass
class Idea:
 text:str;source:str="user";priority:str="normal"
class IdeaIntake:
 def capture(self,idea,project_state):
  if not idea.text.strip():raise ValueError("idea required")
  return {"idea":asdict(idea),"status":"captured","current_phase":project_state.get("phase"),"implementation_started":False}
 def impact(self,captured,areas):
  return captured|{"status":"impact-reviewed","impact_areas":list(areas),"requires_replan":bool(areas)}
 def schedule(self,reviewed,urgent=False):
  # Do not silently mutate active work: Sudarshan chooses safe boundary unless explicitly urgent.
  return reviewed|{"status":"scheduled","insertion":"controlled-now" if urgent else "next-safe-boundary","update_project_brain":True,"retest_affected_work":True}
