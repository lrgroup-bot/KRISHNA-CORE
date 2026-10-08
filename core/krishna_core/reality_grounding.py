from __future__ import annotations

import time

"""Reality grounding: prevent digital evidence, inference or simulation from masquerading as observed reality."""

REALITY_LEVELS=("reported","digitally_observed","physically_observed","inferred","simulated","experimentally_verified")
REALITY_STATES=("candidate","corroborated","verified_for_context","contradicted","stale","unknown")

def reality_record(*,claim,level,source_ref="",observer="",observed_at=None,location_context="",
                   conditions=None,measurement=None,uncertainty=None,state="candidate",source_family="",ttl_seconds=None,
                   unit="",precision=None,calibration_ref="",frame_ref=""):
    if level not in REALITY_LEVELS: raise ValueError("invalid reality level")
    if state not in REALITY_STATES: raise ValueError("invalid reality state")
    return {
        "claim":str(claim or ""),"reality_level":level,"reality_state":state,
        "source_ref":str(source_ref or ""),"source_family":str(source_family or source_ref or ""),"observer":str(observer or ""),
        "observed_at":observed_at,"ttl_seconds":ttl_seconds,"location_context":str(location_context or ""),
        "unit":str(unit or ""),"precision":precision,"calibration_ref":str(calibration_ref or ""),"frame_ref":str(frame_ref or ""),
        "conditions":dict(conditions or {}),"measurement":measurement,"uncertainty":uncertainty,
        "rule":"reported/inferred/simulated evidence must never be relabeled as physical observation or experimental verification",
    }

def reality_gate(records,*,intended_context="",high_impact=False):
    rows=list(records or [])
    now=time.time()
    fresh=[]
    for r in rows:
        if not isinstance(r,dict): continue
        observed=r.get("observed_at");ttl=r.get("ttl_seconds")
        stale=bool(r.get("stale"))
        if ttl is not None and observed is not None:
            try: stale=stale or now-float(observed)>max(0.0,float(ttl))
            except Exception: stale=True
        if not stale:fresh.append(r)
    levels={r.get("reality_level") for r in fresh}
    physical=bool(levels & {"physically_observed","experimentally_verified"})
    families={str(r.get("source_family") or r.get("source_ref") or "").strip().lower() for r in fresh}
    families.discard("")
    corroborated=len(families)>=2
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
        "physical_evidence_present":physical,"independent_source_refs":corroborated,"independent_source_families":len(families),
        "fresh_records":len(fresh),"stale_records":len(rows)-len(fresh),
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
