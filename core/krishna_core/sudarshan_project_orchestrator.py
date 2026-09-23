"""End-to-end Sudarshan project lifecycle coordinator."""
from .project_bootstrap import ProjectBootstrap
from .idea_intake import IdeaIntake
from .sudarshan_design_policy import SudarshanDesignPolicy
from .vishvakarma_team import VishvakarmaTeam
class SudarshanProjectOrchestrator:
 def __init__(self):
  self.bootstrap=ProjectBootstrap();self.ideas=IdeaIntake();self.design_policy=SudarshanDesignPolicy();self.design_team=VishvakarmaTeam()
 def start(self,project_id,context):
  loaded=self.bootstrap.load(project_id,context)
  if not loaded["loaded"]:return {"state":"BLOCKED_CONTEXT","missing":loaded["missing"],"owner":"Sudarshan"}
  baseline=self.bootstrap.baseline(loaded)
  return {"state":"DISCOVERY","project":project_id,"baseline":baseline,"next":"project-map-and-plan","owner":"Sudarshan"}
 def dispatch(self,task_type,checks,findings=None):
  gate=self.design_policy.require(task_type,checks)
  if gate["required"]:
   if not gate["allowed"]:return {"state":"BLOCKED_DESIGN_GATES","missing":gate["missing"]}
   brief=self.design_team.brief(task_type,findings or [])
   return {"state":"READY","team":"design","brief":brief}
  return {"state":"READY","team":"domain-specialists"}
 def completion(self,acceptance,deploy_verified,runtime_verified):
  failed=[k for k,v in acceptance.items() if v is not True]
  if failed:return {"state":"REPAIR","failed":failed}
  if not deploy_verified or not runtime_verified:return {"state":"POST_DEPLOY_VERIFY","complete":False}
  return {"state":"VERIFIED_COMPLETE","complete":True,"learn":True,"update_memory":True}
