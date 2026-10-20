from __future__ import annotations

"""BRAHMAGYAN mission-level Shishyas that collect and reconcile Rishi outputs."""

COLLECTOR_ROLES = (
    "research_conductor","rishi_result_collector","evidence_mapper","contradiction_hunter",
    "gap_finder","freshness_checker","cross_rishi_connector","replication_checker","synthesis_auditor",
)

def collector_team_plan(rishi_ids, *, contradictions=0, unresolved=0, resource_pressure=0.0):
    rishis=list(dict.fromkeys(str(x).strip().lower() for x in (rishi_ids or []) if str(x).strip()))
    base=min(9,max(3,2+(len(rishis)+2)//3))
    extra=min(7,max(0,int(contradictions))+min(max(0,int(unresolved)),4))
    if float(resource_pressure)>=.85: size=max(2,base//2)
    else:size=min(16,base+extra)
    roles=[COLLECTOR_ROLES[i % len(COLLECTOR_ROLES)] for i in range(size)]
    return {
        "owner":"BRAHMAGYAN","ephemeral":True,"rishis":rishis,"count":size,"roles":roles,
        "streaming_collection":True,
        "policy":"collect findings as each Rishi finishes; redirect duplicate work toward evidence gaps",
        "retention":"verified findings, evidence, contradictions, failures, provenance and unresolved gaps only",
    }

def collection_decision(*, supported_sources=0, independent_sources=0, contradictions=0,
                        unresolved=0, duplicate_ratio=0.0):
    if contradictions or unresolved:
        return {"action":"redirect","reason":"contradiction_or_gap","stop_duplicate_lanes":duplicate_ratio>=.6}
    if supported_sources>=3 and independent_sources>=2:
        return {"action":"synthesize","reason":"independent_support_sufficient","stop_duplicate_lanes":True}
    return {"action":"continue","reason":"more_independent_evidence_needed","stop_duplicate_lanes":duplicate_ratio>=.6}
