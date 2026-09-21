from __future__ import annotations

from dataclasses import asdict, dataclass
import re
import uuid


@dataclass(frozen=True)
class RoleManifest:
    role: str
    purpose: str
    permissions: tuple[str,...]
    risk: str
    can_mutate_live: bool = False
    evidence_required: bool = True
    independent_from: tuple[str,...] = ()
    def as_dict(self):
        out=asdict(self)
        out["permissions"]=list(self.permissions)
        out["independent_from"]=list(self.independent_from)
        return out


ROLE_MANIFESTS=(
    RoleManifest("architect","system architecture and boundaries",("code.read","docs.read","design.write"),"advisory"),
    RoleManifest("backend","backend/API implementation in bounded candidate workspace",("code.read","candidate.write","tests.run"),"medium"),
    RoleManifest("frontend","frontend/UI implementation in bounded candidate workspace",("code.read","candidate.write","browser.test","tests.run"),"medium"),
    RoleManifest("debugger","root-cause analysis and reproducible diagnostics",("code.read","logs.read","tests.run","evidence.write"),"advisory"),
    RoleManifest("devops","runtime/build/deployment analysis and candidate automation",("code.read","runtime.read","candidate.write","tests.run"),"medium"),
    RoleManifest("security","defensive review, permissions and trust-boundary analysis",("code.read","security.inspect","evidence.write"),"advisory"),
    RoleManifest("testing","test strategy, regression and independent evidence",("code.read","tests.run","browser.test","evidence.write"),"advisory"),
    RoleManifest("research","source discovery and cross-checking",("web.read","docs.read","evidence.write"),"advisory"),
    RoleManifest("data","data/schema analysis and validation",("data.read","code.read","tests.run"),"advisory"),
    RoleManifest("ui","UI/UX inspection and GUI Guardian candidate review",("browser.read","browser.test","design.write","evidence.write"),"advisory"),
    RoleManifest("docs","documentation and handover from verified evidence",("docs.read","docs.write","evidence.read"),"low"),
    RoleManifest("critic","challenge assumptions and identify unsupported claims",("evidence.read","code.read"),"advisory",False,True,("implementer",)),
    RoleManifest("verifier","independent acceptance; cannot verify its own implementation",("evidence.read","tests.run","browser.test","evidence.write"),"advisory",False,True,("backend","frontend","devops")),
)


class SpecialistTeamPlanner:
    """Builds bounded advisory/implementation teams; KRISHNA retains authority."""

    KEYWORDS={
        "architect":("architecture","design system","system design","boundary","orchestrat"),
        "backend":("backend","api","server","database","sqlite","python","endpoint"),
        "frontend":("frontend","html","css","javascript","react","dashboard","web ui"),
        "debugger":("bug","error","fail","debug","broken","issue","diagnos","traceback"),
        "devops":("deploy","ci","github actions","runtime","docker","build","server restart","windows"),
        "security":("security","auth","permission","secret","credential","vulnerab","threat","policy"),
        "testing":("test","verify","regression","acceptance","qa","coverage"),
        "research":("research","search","compare","github","internet","source"),
        "data":("data","schema","dataset","sql","analytics","memory"),
        "ui":("ui","ux","layout","avatar","visual","responsive","accessibility","garudanetra"),
        "docs":("docs","documentation","readme","handover","manual"),
    }

    def __init__(self, agency_library=None):
        self.agency=agency_library
        self.manifests={x.role:x for x in ROLE_MANIFESTS}

    def roles_for(self, task: str):
        text=str(task or "").strip().lower()
        if not text:raise ValueError("task is required")
        roles=[]
        for role,terms in self.KEYWORDS.items():
            if any(term in text for term in terms):roles.append(role)
        software=any(x in text for x in ("code","project","software","app","core","runtime","implementation","implement","fix"))
        if software and "architect" not in roles:roles.insert(0,"architect")
        if not roles:roles=["research","debugger"]
        if "testing" not in roles:roles.append("testing")
        # Critic and verifier are mandatory and intentionally separate from implementers.
        for role in ("critic","verifier"):
            if role not in roles:roles.append(role)
        seen=set()
        return [x for x in roles if not (x in seen or seen.add(x))]

    def plan(self, task: str, project="KRISHNA", external_limit=6):
        roles=self.roles_for(task)
        external=[];advisor_error=None
        if self.agency:
            try:external=self.agency.select(task,max(1,min(int(external_limit),8)))
            except Exception as exc:
                external=[]
                advisor_error=f"{type(exc).__name__}: {exc}"
        manifests=[self.manifests[x].as_dict() for x in roles]
        return {
            "team_id":str(uuid.uuid4()),
            "project":str(project or "KRISHNA"),
            "task":str(task).strip(),
            "roles":manifests,
            "agency_advisors":external,
            "advisor_error":advisor_error,
            "flow":["KRISHNA","Planner","Specialists","Critic","Independent Verifier","KRISHNA Decision","Action"],
            "authority":"KRISHNA",
            "live_mutation_allowed":False,
            "implementation_scope":"candidate/shadow workspace only until separate verified promotion",
            "verification_rule":"Verifier must be independent from the role that produced the implementation.",
        }

    def status(self):
        return {"roles":[x.as_dict() for x in ROLE_MANIFESTS],"count":len(ROLE_MANIFESTS),
                "authority":"KRISHNA","live_mutation_allowed":False}
