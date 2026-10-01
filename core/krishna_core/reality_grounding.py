from __future__ import annotations

"""Reality grounding: prevent digital evidence, inference or simulation from masquerading as observed reality."""

REALITY_LEVELS=("reported","digitally_observed","physically_observed","inferred","simulated","experimentally_verified")
REALITY_STATES=("candidate","corroborated","verified_for_context","contradicted","stale","unknown")

def reality_record(*,claim,level,source_ref="",observer="",observed_at=None,location_context="",
                   conditions=None,measurement=None,uncertainty=None,state="candidate"):
    if level not in REALITY_LEVELS: raise ValueError("invalid reality level")
    if state not in REALITY_STATES: raise ValueError("invalid reality state")
    return {
        "claim":str(claim or ""),"reality_level":level,"reality_state":state,
        "source_ref":str(source_ref or ""),"observer":str(observer or ""),
        "observed_at":observed_at,"location_context":str(location_context or ""),
        "conditions":dict(conditions or {}),"measurement":measurement,"uncertainty":uncertainty,
        "rule":"reported/inferred/simulated evidence must never be relabeled as physical observation or experimental verification",
    }

def reality_gate(records,*,intended_context="",high_impact=False):
    rows=list(records or [])
    levels={r.get("reality_level") for r in rows if isinstance(r,dict)}
    physical=bool(levels & {"physically_observed","experimentally_verified"})
    corroborated=len({str(r.get("source_ref")) for r in rows if isinstance(r,dict) and r.get("source_ref")})>=2
    if high_impact and not physical:
        status="needs_real_world_validation"
    elif physical and corroborated:
        status="grounded_for_context"
    elif corroborated:
        status="digitally_corroborated_not_physically_verified"
    else:
        status="unverified"
    return {
        "status":status,"intended_context":str(intended_context or ""),
        "physical_evidence_present":physical,"independent_source_refs":corroborated,
        "promotion_allowed":status=="grounded_for_context" or (not high_impact and status=="digitally_corroborated_not_physically_verified"),
        "limitations_required":status!="grounded_for_context",
    }

def observation_escalation(*,digital_only=True,visual_ambiguity=False,physical_state_matters=False,
                           measurement_required=False,consequence_severity="low",environment="pc"):
    need=bool(visual_ambiguity or physical_state_matters or measurement_required or
              str(consequence_severity).lower() in {"high","critical"})
    return {
        "needs_real_world_observation":need,
        "preferred_worker":(("HAWKEYE" if str(environment).lower() in {"mobile","field","outdoor"} else "CHANDRADEV") if need else "SURYDEV"),
        "human_or_instrument_confirmation":bool(measurement_required or str(consequence_severity).lower()=="critical"),
        "digital_only":bool(digital_only),"krishna_continuous_perception":False,
        "rule":"escalate when the answer depends on present physical state, visual ambiguity, measurement, or consequential context",
    }
