from __future__ import annotations
class KabachAgentEvaluation:
    CASES=("indirect_prompt_injection","secret_exfiltration","tool_permission_escalation","malicious_tool_description","rag_poisoning","unsafe_tool_chaining","system_prompt_extraction")
    def plan(self,target,enabled_cases=None):
        cases=[x for x in (enabled_cases or self.CASES) if x in self.CASES]
        return {"target":target,"cases":cases,"mode":"isolated-evaluation","production":False,"requires_authorization":True}
    def evaluate_receipts(self,receipts):
        failures=[r for r in receipts if not r.get("passed")]
        return {"passed":not failures and bool(receipts),"total":len(receipts),"failures":failures}
