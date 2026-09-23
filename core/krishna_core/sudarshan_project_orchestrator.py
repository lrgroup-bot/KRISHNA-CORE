from __future__ import annotations

"""End-to-end Sudarshan project lifecycle coordinator."""

from .idea_intake import IdeaIntake
from .project_bootstrap import ProjectBootstrap
from .sudarshan_design_policy import SudarshanDesignPolicy
from .vishvakarma_team import VishvakarmaTeam


class SudarshanProjectOrchestrator:
    def __init__(self, *, vishvakarma=None, design_engine=None):
        self.bootstrap=ProjectBootstrap()
        self.ideas=IdeaIntake()
        self.design_policy=SudarshanDesignPolicy()
        self.design_team=VishvakarmaTeam()
        self.vishvakarma=vishvakarma
        self.design_engine=design_engine

    def start(self,project_id,context):
        loaded=self.bootstrap.load(project_id,context)
        if not loaded["loaded"]:
            return {"state":"BLOCKED_CONTEXT","missing":loaded["missing"],"owner":"Sudarshan"}
        baseline=self.bootstrap.baseline(loaded)
        return {
            "state":"DISCOVERY","project":project_id,"baseline":baseline,
            "next":"project-map-and-plan","owner":"Sudarshan",
        }

    def dispatch(self,task_type,checks,findings=None):
        gate=self.design_policy.require(task_type,checks)
        if not gate["required"]:
            return {"state":"READY","team":"domain-specialists"}

        if not gate["allowed"]:
            return {"state":"BLOCKED_DESIGN_GATES","missing":gate["missing"]}

        resolved=list(findings or [])
        if not resolved and self.vishvakarma is not None:
            try:
                resolved=self.vishvakarma.retrieve(str(task_type),limit=12,verified_only=True)
            except Exception:
                resolved=[]

        if not resolved:
            return {
                "state":"BLOCKED_VISHVAKARMA_KNOWLEDGE",
                "missing":["verified_vishvakarma_findings"],
                "owner":"Sudarshan",
                "knowledge_owner":"Rishi Vishvakarma",
            }

        brief=self.design_team.brief(task_type,resolved)
        plan=None
        if self.design_engine is not None:
            from .sudarshan_design_engine import DesignJob
            plan=self.design_engine.plan(DesignJob(str(task_type),existing_ui=True,topic=str(task_type)))
        return {"state":"READY","team":"design","brief":brief,"design_plan":plan}

    def completion(self,acceptance,deploy_verified,runtime_verified):
        failed=[k for k,v in acceptance.items() if v is not True]
        if failed:
            return {"state":"REPAIR","failed":failed}
        if not deploy_verified or not runtime_verified:
            return {"state":"POST_DEPLOY_VERIFY","complete":False}
        return {
            "state":"VERIFIED_COMPLETE","complete":True,
            "learn":True,"update_memory":True,
        }

    def status(self):
        return {
            "owner":"Sudarshan",
            "design_policy":"mandatory for UI/frontend work",
            "vishvakarma_bound":self.vishvakarma is not None,
            "design_engine_bound":self.design_engine is not None,
        }
