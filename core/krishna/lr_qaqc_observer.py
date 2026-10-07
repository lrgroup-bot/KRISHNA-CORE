"""KRISHNA authority gateway for LR QAQC.

All LR company systems, LR QAQC, Brahma, Rishis and Sukracharya report upward
to KRISHNA. KRISHNA is the sole system authority that communicates with the
human owner. Specialists never bypass KRISHNA.

KRISHNA may route ordinary internal work after verified GO. Protected external
actions are escalated by KRISHNA to the human owner when human authority is
required. This module grants no implicit spend/publish/purchase/sign/deploy.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

PROTECTED_ACTIONS=frozenset({"spend","purchase","payment","paid-subscription","paid-ad","bank-write","statutory-file","legal-sign","production-deploy","platform-connect","distribution-publish","distribution-schedule"})

@dataclass(frozen=True)
class LRQAQCObservation:
    project_id: str
    stage: str
    objective: str
    evidence_refs: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    observed_failures: tuple[str, ...] = ()
    real_outcome_refs: tuple[str, ...] = ()

def build_lr_qaqc_request(observation: LRQAQCObservation, *, company_id: str | None = None, domain: str = "software-project") -> dict[str, Any]:
    if not observation.project_id or not observation.stage or not observation.objective:
        raise ValueError("project_id, stage and objective are required")
    return {"schema":"krishna.lr-qaqc-authority.v2","company_id":company_id,"domain":domain,"observation":asdict(observation),
      "request":{"research_unknowns":True,"world_lab":True,"independent_judgment_before_debate":True,"adversarial_qc":True,"qc_of_qc":True,"concrete_conclusion_required":True,"repair_to_affected_stage":True,"completion_required":True,"calibrate_against_real_outcome":True,"success_mining":True},
      "authority":{"krishna":"PRIMARY_SYSTEM_AUTHORITY","lr_qaqc":"reports_to_krishna","brahma":"reports_to_krishna","rishis":"report_to_krishna","sukracharya":"reports_to_krishna","human_contact":"KRISHNA_ONLY"}}

def decide_qaqc_gate(*, gate: str, protected_action: str | None = None, evidence_complete: bool = False, conclusion: str | None = None) -> dict[str, Any]:
    if gate != "GO":
        return {"advance":False,"decision":"RETURN_TO_QAQC_PIPELINE","gate":gate,"krishna_message":"QAQC has not cleared this phase."}
    if not evidence_complete or not conclusion:
        return {"advance":False,"decision":"RETURN_TO_QAQC_PIPELINE","gate":"REPAIR","krishna_message":"Evidence or conclusion is incomplete."}
    if protected_action in PROTECTED_ACTIONS:
        return {"advance":False,"decision":"ASK_HUMAN_THROUGH_KRISHNA","gate":"KRISHNA_DECISION","protected_action":protected_action,"krishna_message":"KRISHNA must present the verified conclusion and request human authority before this protected action."}
    return {"advance":True,"decision":"KRISHNA_AUTHORIZED_NEXT_INTERNAL_PHASE","gate":"GO","krishna_message":"KRISHNA authorizes the next non-protected internal phase."}

def human_brief(*, project_id: str, conclusion: str, recommendation: str, evidence: list[str] | None = None, disagreements: list[str] | None = None, requested_decision: str | None = None) -> dict[str, Any]:
    if not project_id or not conclusion or not recommendation:
        raise ValueError("project_id, conclusion and recommendation required")
    return {"schema":"krishna.human-brief.v1","speaker":"KRISHNA","project_id":project_id,"conclusion":conclusion,"recommendation":recommendation,"evidence":evidence or [],"material_disagreements":disagreements or [],"requested_decision":requested_decision,"specialist_direct_contact":False}
