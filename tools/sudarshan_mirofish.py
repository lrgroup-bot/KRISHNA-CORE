"""MiroFish simulation adapter boundary for SUDARSHAN feature decisions.

No MiroFish code is vendored; external runs must be explicitly configured.
Simulations are hypotheses, never verified product outcomes or trading signals.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Scenario:
    project_id: str
    feature_id: str
    hypothesis: str
    evidence_ids: tuple[str, ...]
    agent_personas: tuple[str, ...]

def prepare_scenario(scenario: Scenario):
    if not isinstance(scenario, Scenario):
        raise TypeError("Scenario required")
    fields=(scenario.project_id,scenario.feature_id,scenario.hypothesis)
    if any(not isinstance(x,str) or not x.strip() for x in fields):
        raise ValueError("project, feature and hypothesis required")
    if not scenario.evidence_ids or not all(isinstance(x,str) and x.strip() for x in scenario.evidence_ids):
        raise ValueError("traceable source evidence required")
    if not scenario.agent_personas or not all(isinstance(x,str) and x.strip() for x in scenario.agent_personas):
        raise ValueError("simulation personas required")
    return {"engine":"MiroFish","project_id":scenario.project_id,
            "feature_id":scenario.feature_id,"requirement":scenario.hypothesis,
            "evidence_ids":list(scenario.evidence_ids),
            "personas":list(scenario.agent_personas),
            "mode":"offline-sandbox","execution_enabled":False,
            "interpretation":"hypothesis_only","release_approval":False}

def assess_simulation(plan, report):
    if plan.get("engine")!="MiroFish" or plan.get("execution_enabled") is not False:
        raise ValueError("untrusted simulation plan")
    if not isinstance(report,dict) or not isinstance(report.get("summary"),str) or not report["summary"].strip():
        raise ValueError("simulation summary required")
    return {"project_id":plan["project_id"],"feature_id":plan["feature_id"],
            "summary":report["summary"],"confidence":"unvalidated",
            "requires_real_world_tests":True,"eligible_for_auto_implementation":False}
