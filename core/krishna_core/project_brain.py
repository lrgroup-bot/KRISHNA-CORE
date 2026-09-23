"""Sudarshan-owned Project Brain contract."""
from pathlib import Path
import json,time
LAYERS=("PROJECT.md","ARCHITECTURE.md","RULES.md","PHASES.md","DESIGN.md","AGENTS.md","MEMORY.md")
SECTIONS={"PROJECT.md":["Project Requirement Document","Purpose","Target Users","Requirements","Features","Acceptance Criteria","Out of Scope"],"ARCHITECTURE.md":["Architecture","System Architecture","App and Data Flow","Folder and File Structure","Tech Stack","APIs and Models","Dependencies"],"RULES.md":["Rules","Required Behaviors","Prohibited Behaviors","Security and Privacy Boundaries","Error Handling","Retry and Rollback","Definition of Done"],"PHASES.md":["Phases","Phase 0 - Requirements and Audit","Phase 1 - Implementation","Final Acceptance"],"DESIGN.md":["Design System","Design Language","Color Tokens","Typography","Spacing","Components","Interaction States","Desktop and Mobile","Accessibility"],"AGENTS.md":["Agent Contract","Sudarshan Ownership","Skill Routing","Worker Boundaries","Verification","Evidence","Escalation","KRISHNA Summary Contract"],"MEMORY.md":["Project Memory","Completed","In Progress","Remaining","Blocked","Decisions","Failed Attempts","Tests and Verification","Commits","Next Action"]}
class ProjectBrain:
 def __init__(self,root):self.root=Path(root)
 def provision(self,project):
  p=self.root/project/".krishna";p.mkdir(parents=True,exist_ok=True)
  for name,parts in SECTIONS.items():
   f=p/name
   if not f.exists():f.write_text("# "+parts[0]+"\n\n"+"\n\n".join("## "+x for x in parts[1:])+"\n",encoding="utf-8")
  self._state(p,project);return self.status(project)
 def status(self,project):
  p=self.root/project/".krishna";missing=[x for x in LAYERS if not (p/x).exists()]
  return {"project":project,"root":str(p),"complete":not missing,"missing":missing,"governance_owner":"Sudarshan"}
 def record(self,project,section,message):
  p=self.root/project/".krishna"
  if not (p/"MEMORY.md").exists():self.provision(project)
  with (p/"MEMORY.md").open("a",encoding="utf-8") as h:h.write("\n### "+section+" - "+time.strftime("%Y-%m-%d %H:%M:%S")+"\n"+message.strip()+"\n")
  self._state(p,project)
 def _state(self,p,project):
  (p/"PROJECT_STATE.json").write_text(json.dumps({"schema":"krishna.project-brain.v2","project":project,"governance_owner":"Sudarshan","layers":list(LAYERS),"krishna_context":"summary-only","updated_at":time.time()},indent=2),encoding="utf-8")
