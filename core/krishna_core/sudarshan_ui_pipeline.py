from __future__ import annotations

"""Evidence-oriented UI build/repair loop owned by Sudarshan."""

from dataclasses import dataclass,field


@dataclass
class UIEvidence:
    attempts:int=0
    findings:list=field(default_factory=list)


class UIPipeline:
    def __init__(self,design_engine,max_repairs=3):
        self.engine=design_engine
        self.max_repairs=max(1,min(int(max_repairs),10))

    def next_action(self,checks,evidence:UIEvidence):
        verdict=self.engine.acceptance.evaluate(checks)
        if verdict["verified"]:
            return {"action":"accept","verdict":verdict,"attempts":evidence.attempts}
        evidence.findings.append(list(verdict["failed"]))
        if evidence.attempts>=self.max_repairs:
            return {
                "action":"escalate",
                "verdict":verdict,
                "attempts":evidence.attempts,
                "history":list(evidence.findings),
            }
        evidence.attempts+=1
        return {
            "action":"repair-and-retest",
            "failed":verdict["failed"],
            "attempt":evidence.attempts,
            "max_repairs":self.max_repairs,
        }
