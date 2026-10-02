from __future__ import annotations
class OTelGenAIExporter:
    """Maps KRISHNA receipts to vendor-neutral span dictionaries; transport remains optional."""
    def span(self,receipt):
        return {"name":"krishna.agent.step","attributes":{"gen_ai.operation.name":str(receipt.get("operation") or "execute"),"gen_ai.agent.name":str(receipt.get("agent") or "unknown"),"krishna.project":str(receipt.get("project") or "KRISHNA"),"krishna.mission":str(receipt.get("mission") or ""),"krishna.verified":bool(receipt.get("verified",False))},"events":list(receipt.get("evidence") or [])}
