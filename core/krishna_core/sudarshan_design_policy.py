"""Mandatory Vishvakarma design policy for Sudarshan UI/frontend work."""
UI_TASKS={"frontend","ui","ux","dashboard","mobile-ui","web-design","component","visual-redesign","image-to-code"}
MANDATORY_GATES=("vishvakarma_knowledge","design_spec","functional","visual","responsive","accessibility","security")
class SudarshanDesignPolicy:
 def applies(self,task_type):return task_type.strip().lower() in UI_TASKS
 def require(self,task_type,checks):
  if not self.applies(task_type):return {"required":False,"allowed":True,"missing":[]}
  missing=[g for g in MANDATORY_GATES if checks.get(g) is not True]
  return {"required":True,"allowed":not missing,"missing":missing,"owner":"Sudarshan","knowledge_owner":"Vishvakarma"}
 def dispatch_context(self,task_type,retrieved_findings):
  if not self.applies(task_type):return []
  if not retrieved_findings:raise RuntimeError("Vishvakarma knowledge retrieval is mandatory for design work")
  return retrieved_findings
