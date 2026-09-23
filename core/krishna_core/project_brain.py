from __future__ import annotations

"""Sudarshan-owned Project Brain.

Preserves the newer database-backed verified learning/context API while restoring
the structured project-governance layers from the historical master integration.
Governance files live in KRISHNA runtime state by default, not inside source trees.
"""

from pathlib import Path
import json
import re
import time


LAYERS=("PROJECT.md","ARCHITECTURE.md","RULES.md","PHASES.md","DESIGN.md","AGENTS.md","MEMORY.md")
SECTIONS={
    "PROJECT.md":("Project Requirement Document","Purpose","Target Users","Requirements","Features","Acceptance Criteria","Out of Scope"),
    "ARCHITECTURE.md":("Architecture","System Architecture","App and Data Flow","Folder and File Structure","Tech Stack","APIs and Models","Dependencies"),
    "RULES.md":("Rules","Required Behaviors","Prohibited Behaviors","Security and Privacy Boundaries","Error Handling","Retry and Rollback","Definition of Done"),
    "PHASES.md":("Phases","Phase 0 - Requirements and Audit","Phase 1 - Implementation","Final Acceptance"),
    "DESIGN.md":("Design System","Design Language","Color Tokens","Typography","Spacing","Components","Interaction States","Desktop and Mobile","Accessibility"),
    "AGENTS.md":("Agent Contract","Sudarshan Ownership","Skill Routing","Worker Boundaries","Verification","Evidence","Escalation","KRISHNA Summary Contract"),
    "MEMORY.md":("Project Memory","Completed","In Progress","Remaining","Blocked","Decisions","Failed Attempts","Tests and Verification","Commits","Next Action"),
}


class ProjectBrain:
    VERSION="krishna.project-brain.v3"

    def __init__(self,memory_or_root,governance_root=None):
        if hasattr(memory_or_root,"remember") and hasattr(memory_or_root,"recall"):
            self.memory=memory_or_root
            self.root=Path(governance_root).resolve() if governance_root else None
        else:
            self.memory=None
            self.root=Path(memory_or_root).resolve()

    @staticmethod
    def _slug(project):
        value=str(project or "").strip()
        if not value:
            raise ValueError("project is required")
        slug=re.sub(r"[^A-Za-z0-9._-]+","-",value).strip(".-")
        if not slug:
            raise ValueError("project name cannot be normalized safely")
        return slug[:120]

    def _project_dir(self,project):
        if self.root is None:
            raise RuntimeError("Project Brain governance root is not configured")
        return self.root/self._slug(project)/".krishna"

    def provision(self,project):
        p=self._project_dir(project)
        p.mkdir(parents=True,exist_ok=True)
        for name,parts in SECTIONS.items():
            target=p/name
            if target.exists():
                continue
            target.write_text(
                "# "+parts[0]+"\n\n"+"\n\n".join("## "+x for x in parts[1:])+"\n",
                encoding="utf-8",
            )
        self._state(p,project)
        return self.status(project)

    def status(self,project):
        p=self._project_dir(project)
        missing=[x for x in LAYERS if not (p/x).is_file()]
        state=p/"PROJECT_STATE.json"
        return {
            "project":str(project),
            "root":str(p),
            "complete":not missing and state.is_file(),
            "missing":missing,
            "state_present":state.is_file(),
            "governance_owner":"Sudarshan",
            "source_tree_mutation":False,
            "version":self.VERSION,
        }

    def record(self,project,section,message):
        section=str(section or "").strip()[:120]
        message=str(message or "").strip()
        if not section or not message:
            raise ValueError("section and message are required")
        p=self._project_dir(project)
        if not (p/"MEMORY.md").is_file():
            self.provision(project)
        with (p/"MEMORY.md").open("a",encoding="utf-8") as h:
            h.write("\n### "+section+" - "+time.strftime("%Y-%m-%d %H:%M:%S")+"\n"+message[:12000]+"\n")
        self._state(p,project)
        return {"recorded":True,"project":str(project),"section":section,"root":str(p)}

    def _state(self,p,project):
        state={
            "schema":self.VERSION,
            "project":str(project),
            "governance_owner":"Sudarshan",
            "layers":list(LAYERS),
            "krishna_context":"summary-only",
            "source_tree_mutation":False,
            "updated_at":time.time(),
        }
        target=p/"PROJECT_STATE.json"
        tmp=target.with_suffix(".tmp")
        tmp.write_text(json.dumps(state,indent=2),encoding="utf-8")
        tmp.replace(target)

    def learn_verified(self,project,goal,result):
        if self.memory is None:
            raise RuntimeError("database-backed Project Brain memory is not configured")
        self.memory.remember(project,"verified_learning",goal,{"result":result})
        self.memory.audit("project_brain","learned",project)
        if self.root is not None:
            try:self.record(project,"Completed",f"{goal}\n\nVerified result: {result}")
            except Exception:self.memory.audit("project_brain","governance_record_failed",str(project))

    def context(self,project,limit=20):
        if self.memory is None:
            return {"project":project,"memory":[],"incidents":[],"governance":self.status(project)}
        out={
            "project":project,
            "memory":self.memory.recall(project,limit=limit),
            "incidents":self.memory.incidents(project,limit=10),
        }
        if self.root is not None:
            out["governance"]=self.status(project)
        return out
