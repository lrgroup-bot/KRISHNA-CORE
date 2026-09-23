"""End-to-end Sudarshan project lifecycle coordinator."""

from .project_bootstrap import ProjectBootstrap
from .idea_intake import IdeaIntake
from .sudarshan_design_policy import SudarshanDesignPolicy
from .sudarshan_design_engine import DesignJob, SudarshanDesignEngine
from .vishvakarma_team import VishvakarmaTeam


class SudarshanProjectOrchestrator:
    def __init__(self, design_engine=None):
        self.bootstrap=ProjectBootstrap()
        self.ideas=IdeaIntake()
        self.design_policy=SudarshanDesignPolicy()
        self.design_team=VishvakarmaTeam()
        self.design_engine=design_engine or SudarshanDesignEngine(".")

    def start(self,project_id,context):
        loaded=self.bootstrap.load(project_id,context)
        if not loaded["loaded"]:
            return {"state":"BLOCKED_CONTEXT","missing":loaded["missing"],"owner":"Sudarshan"}
        baseline=self.bootstrap.baseline(loaded)
        return {"state":"DISCOVERY","project":project_id,"baseline":baseline,"next":"project-map-and-plan","owner":"Sudarshan"}

    def design_plan(self,task_type,*,reference_image=False,existing_ui=False,agentic_browser=False):
        return self.design_engine.plan(DesignJob(
            task_type,
            reference_image=bool(reference_image),
            existing_ui=bool(existing_ui),
            agentic_browser=bool(agentic_browser),
        ))

    def dispatch(self,task_type,checks,findings=None):
        gate=self.design_policy.require(task_type,checks)
        if gate["required"]:
            if not gate["allowed"]:
                return {"state":"BLOCKED_DESIGN_GATES","missing":gate["missing"]}
            brief=self.design_team.brief(task_type,findings or [])
            plan=self.design_plan(task_type,existing_ui=True)
            return {"state":"READY","team":"design","brief":brief,"design_plan":plan}
        return {"state":"READY","team":"domain-specialists"}

    def completion(self,acceptance,deploy_verified,runtime_verified):
        failed=[k for k,v in acceptance.items() if v is not True]
        if failed:return {"state":"REPAIR","failed":failed}
        if not deploy_verified or not runtime_verified:return {"state":"POST_DEPLOY_VERIFY","complete":False}
        return {"state":"VERIFIED_COMPLETE","complete":True,"learn":True,"update_memory":True}
