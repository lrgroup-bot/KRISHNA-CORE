"""End-to-end Sudarshan project lifecycle coordinator."""

from .project_bootstrap import ProjectBootstrap
from .idea_intake import IdeaIntake
from .sudarshan_design_policy import SudarshanDesignPolicy
from .sudarshan_design_engine import DesignJob, SudarshanDesignEngine
from .vishvakarma_team import VishvakarmaTeam
from .autonomous_project_lifecycle import AutonomousProjectLifecycle
from .chandradev_real_use import ChandradevRealUseExam
from .chandradev_browser_bridge import ChandradevBrowserBridge


class SudarshanProjectOrchestrator:
    def __init__(self, design_engine=None, engineering_intelligence=None, lifecycle_root=None):
        self.bootstrap=ProjectBootstrap()
        self.ideas=IdeaIntake()
        self.design_policy=SudarshanDesignPolicy()
        self.design_team=VishvakarmaTeam()
        self.design_engine=design_engine or SudarshanDesignEngine(".")
        self.engineering_intelligence=engineering_intelligence
        self.autonomous_lifecycle=AutonomousProjectLifecycle(lifecycle_root) if lifecycle_root else None
        self.chandradev_exam=ChandradevRealUseExam()
        self.chandradev_browser=ChandradevBrowserBridge()

    def start(self,project_id,context):
        loaded=self.bootstrap.load(project_id,context)
        if not loaded["loaded"]:
            return {"state":"BLOCKED_CONTEXT","missing":loaded["missing"],"owner":"Sudarshan"}
        baseline=self.bootstrap.baseline(loaded)
        return {"state":"DISCOVERY","project":project_id,"baseline":baseline,"next":"project-map-and-plan","owner":"Sudarshan"}

    def discovery_complete(self,project_id,findings):
        if self.autonomous_lifecycle is None:return {"state":"BLOCKED_LIFECYCLE_STATE"}
        state=self.autonomous_lifecycle.record_discovery(project_id,findings)
        return {"state":state["phase"],"next":"owner-discussion-and-live-prototype","owner":"Sudarshan"}

    def freeze_after_owner_ui(self,project_id,prototype_url,spec_version,spec):
        if self.autonomous_lifecycle is None:return {"state":"BLOCKED_LIFECYCLE_STATE"}
        self.autonomous_lifecycle.approve_prototype(project_id,prototype_url,True)
        state=self.autonomous_lifecycle.freeze(project_id,spec_version,spec)
        return {"state":state["phase"],"silent_build":True,"owner":"Sudarshan"}

    def final_real_use(self,project_id,steps):
        report=self.chandradev_exam.evaluate(steps)
        if self.autonomous_lifecycle is not None:self.autonomous_lifecycle.chandradev_result(project_id,report)
        return report

    def final_from_browser_evidence(self,project_id,regression):
        report=self.chandradev_browser.from_regression(regression)
        if self.autonomous_lifecycle is not None:self.autonomous_lifecycle.chandradev_result(project_id,report)
        return report

    def completion_payload(self,project_id,acceptance,deploy_verified,runtime_verified,live_url=None):
        failed=[k for k,v in acceptance.items() if v is not True]
        if failed:return {"state":"REPAIR","failed":failed,"notify_owner":False}
        if self.autonomous_lifecycle is None:return {"state":"BLOCKED_LIFECYCLE_STATE","notify_owner":False}
        current=self.autonomous_lifecycle.status(project_id)
        ch=current.get("chandradev") or {}
        state=self.autonomous_lifecycle.complete(project_id,True,deploy_verified,runtime_verified,live_url=live_url,replay=ch.get("replay"))
        ok=state["phase"]=="VERIFIED_COMPLETE"
        return {"state":state["phase"],"notify_owner":ok,"live_url":(state.get("completion") or {}).get("live_url"),
                "replay":(state.get("completion") or {}).get("replay"),"message":"Project completed and verified" if ok else "Project remains in repair"}

    def prepare_engineering_task(self,project_id,root,task,*,requirements=(),failures=(),architecture_rules=()):
        if self.engineering_intelligence is None:
            return {"state":"BLOCKED_ENGINEERING_INTELLIGENCE","owner":"Sudarshan"}
        prepared=self.engineering_intelligence.prepare_task(project_id,root,task,requirements=requirements,failures=failures,architecture_rules=architecture_rules)
        if not prepared["architecture"]["passed"]:
            return {"state":"BLOCKED_ARCHITECTURE_POLICY","owner":"Sudarshan","prepared":prepared}
        return {"state":"READY_ENGINEERING_CONTEXT","owner":"Sudarshan","prepared":prepared}

    def design_plan(self,task_type,*,reference_image=False,existing_ui=False,agentic_browser=False,topic=""):
        return self.design_engine.plan(DesignJob(
            task_type,
            reference_image=bool(reference_image),
            existing_ui=bool(existing_ui),
            agentic_browser=bool(agentic_browser),
            topic=str(topic or task_type),
        ))

    def status(self):
        return {
            "owner":"Sudarshan",
            "project_bootstrap":True,
            "idea_intake":True,
            "design_policy":True,
            "design_team":True,
            "design_engine_bound":self.design_engine is not None,
            "engineering_intelligence_bound":self.engineering_intelligence is not None,
            "autonomous_lifecycle_bound":self.autonomous_lifecycle is not None,
            "chandradev_real_use":True,
        }

    def dispatch(self,task_type,checks,findings=None):
        gate=self.design_policy.require(task_type,checks)
        if gate["required"]:
            if not gate["allowed"]:
                return {"state":"BLOCKED_DESIGN_GATES","missing":gate["missing"]}
            plan=self.design_plan(task_type,existing_ui=True)
            verified_findings=list(plan.get("verified_vishvakarma_findings") or [])
            if plan.get("knowledge_bound") and not verified_findings:
                return {
                    "state":"BLOCKED_VISHVAKARMA_KNOWLEDGE",
                    "team":"design",
                    "design_plan":plan,
                    "next":"research-review-verify-vishvakarma-knowledge",
                }
            consulted=list(findings or []) or verified_findings
            brief=self.design_team.brief(task_type,consulted)
            return {"state":"READY","team":"design","brief":brief,"design_plan":plan}
        return {"state":"READY","team":"domain-specialists"}

    def completion(self,acceptance,deploy_verified,runtime_verified):
        failed=[k for k,v in acceptance.items() if v is not True]
        if failed:return {"state":"REPAIR","failed":failed}
        if not deploy_verified or not runtime_verified:return {"state":"POST_DEPLOY_VERIFY","complete":False}
        return {"state":"VERIFIED_COMPLETE","complete":True,"learn":True,"update_memory":True}
