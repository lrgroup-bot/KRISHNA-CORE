"""Thin KRISHNA adapter for LR QAQC.

KRISHNA observes, routes and escalates. LR QAQC owns simulation, adversarial
quality work, phase gating, repair prescriptions and outcome calibration.
This adapter intentionally has no spend/publish/deploy authority.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class LRQAQCObservation:
    project_id: str
    stage: str
    objective: str
    evidence_refs: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    observed_failures: tuple[str, ...] = ()
    real_outcome_refs: tuple[str, ...] = ()

def build_lr_qaqc_request(observation: LRQAQCObservation, *, company_id: str | None = None,
                          domain: str = "software-project") -> dict[str, Any]:
    if not observation.project_id or not observation.stage or not observation.objective:
        raise ValueError("project_id, stage and objective are required")
    return {
        "schema": "krishna.lr-qaqc-observer.v1",
        "company_id": company_id,
        "domain": domain,
        "observation": asdict(observation),
        "request": {
            "research_unknowns": True,
            "world_lab": True,
            "independent_judgment_before_debate": True,
            "adversarial_qc": True,
            "qc_of_qc": True,
            "concrete_conclusion_required": True,
            "repair_to_affected_stage": True,
            "completion_required": True,
            "calibrate_against_real_outcome": True,
        },
        "authority": {
            "krishna": "observe_route_escalate",
            "lr_qaqc": "simulate_challenge_gate_repair_calibrate",
            "may_spend": False,
            "may_publish": False,
            "may_purchase": False,
            "may_sign": False,
            "may_deploy": False,
        },
    }
