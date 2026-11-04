from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class GroundingDecision:
    required:bool
    reason:str
    query:str

class DocumentationGroundingGate:
    """Fail-closed decision gate for unfamiliar/version-sensitive APIs."""
    def assess(self,*,library="",api="",version="",confidence=1.0,known=False):
        subject=" ".join(x for x in (library,api,version) if str(x).strip()).strip()
        required=(not known) or float(confidence)<0.85 or bool(version)
        reason="version-sensitive or unfamiliar API requires source documentation" if required else "known API with sufficient confidence"
        return GroundingDecision(required,reason,(subject+" official documentation API reference").strip())
    def authorize_generation(self,decision,evidence):
        rows=[x for x in (evidence or []) if isinstance(x,dict) and (x.get("url") or x.get("path"))]
        if decision.required and not rows:
            raise PermissionError("documentation grounding required before code generation")
        return {"grounded":bool(rows) or not decision.required,"evidence":rows,"reason":decision.reason}
