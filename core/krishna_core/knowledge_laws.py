from __future__ import annotations
"""Non-bypassable knowledge/reality invariants for BRAHMAGYAN."""

LAWS={
"R1":"SOURCE_IS_NOT_REALITY",
"R2":"OBSERVATION_IS_NOT_INTERPRETATION",
"R3":"INFERENCE_IS_NOT_OBSERVATION",
"R4":"SIMULATION_IS_NOT_VERIFICATION",
"R5":"CONSENSUS_IS_NOT_TRUTH",
"R6":"TIME_AND_CONTEXT_BIND_VALIDITY",
"R7":"INDEPENDENCE_IS_SOURCE_FAMILY_NOT_URL_COUNT",
"R8":"RETRACTION_INVALIDATES_DEPENDENTS",
"R9":"UNRESOLVED_REQUIRED_GATE_BLOCKS_GYAN_PROMOTION",
"R10":"HIGH_IMPACT_CLAIMS_REQUIRE_CONTEXT_APPROPRIATE_REAL_WORLD_VALIDATION",
"R11":"ALL_PARALLEL_WORK_SHARES_RESOURCE_AND_PROVIDER_LIMITS",
"R12":"FAILURE_MUST_BE_VISIBLE_RECOVERABLE_AND_AUDITED",
}

def knowledge_law_gate(*,claim_type,evidence_records,required_gates=None,high_impact=False,
                       current_context="",now=None):
    rows=[dict(x) for x in (evidence_records or []) if isinstance(x,dict)]
    required=set(required_gates or ())
    levels={x.get("reality_level") for x in rows}
    families={x.get("source_family") for x in rows if x.get("source_family")}
    retracted=any(x.get("retracted") or x.get("invalidated") for x in rows)
    stale=any(x.get("stale") for x in rows)
    completed={x.get("gate") for x in rows if x.get("gate_passed") is True}
    unresolved=sorted(required-completed)
    physical=bool(levels & {"physically_observed","experimentally_verified"})
    violations=[]
    if retracted: violations.append("R8")
    if stale: violations.append("R6")
    if unresolved: violations.append("R9")
    if high_impact and not physical: violations.append("R10")
    if len(families)<2 and claim_type in {"verified","strongly_supported"}: violations.append("R7")
    return {"allowed":not violations,"violations":violations,"unresolved_gates":unresolved,
            "independent_source_families":len(families),"physical_validation":physical,
            "context":str(current_context or ""),"laws":LAWS}

def invalidate_dependents(entity_id,derivation_edges,reason):
    affected=set(); frontier=[str(entity_id)]
    edges=list(derivation_edges or [])
    while frontier:
        parent=frontier.pop()
        for e in edges:
            if str(e.get("parent"))==parent:
                child=str(e.get("child"))
                if child and child not in affected:
                    affected.add(child);frontier.append(child)
    return {"invalidated_root":str(entity_id),"affected":sorted(affected),
            "reason":str(reason),"required_action":"mark needs_review; never silently preserve verified status"}
