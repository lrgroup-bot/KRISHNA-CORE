"""Sudarshan project bootstrap, discovery and context-loader contract."""
REQUIRED_CONTEXT=("source","repository","project_brain","requirements","architecture","design","dependencies","tests","deployment","memory","runtime")
class ProjectBootstrap:
 def load(self,project_id,context):
  missing=[x for x in REQUIRED_CONTEXT if x not in context]
  return {"project_id":project_id,"owner":"Sudarshan","loaded":not missing,"missing":missing,"context":context}
 def baseline(self,loaded):
  if not loaded.get("loaded"):raise RuntimeError("project context must be loaded before baseline")
  return {"map_required":True,"tests_required":True,"runtime_check_required":True,"ready_for_planning":True}
