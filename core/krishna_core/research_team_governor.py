"""BRAHMAGYAN adaptive research-team planning.

Advisory planner: it recommends Shishya expansion/contraction. It never creates
workers or bypasses BRAHMA, AI-HR, resource, permission or safety gates.
"""

SPECIALIST_ROLES = (
    "primary_source", "replication", "negative_evidence", "methodology",
    "statistics", "cross_domain", "patent_prior_art", "standards",
    "open_source_implementation", "failure_history", "safety_ethics",
)

def research_team_decision(*, current, uncovered_specialties=0, unresolved_questions=0,
                           contradictions=0, duplicate_ratio=0.0, information_gain=1.0,
                           resource_pressure=0.0, safety_block=False):
    current=max(0,int(current))
    if safety_block:
        return {"action":"hold","delta":0,"reason":"safety_or_permission_boundary","requires":["BRAHMA","AI-HR"]}
    if resource_pressure >= .85:
        return {"action":"contract","delta":max(1,current//4),"reason":"resource_pressure","requires":["BRAHMA","AI-HR"]}
    if duplicate_ratio >= .65 or information_gain <= .15:
        return {"action":"stop_expansion","delta":0,"reason":"evidence_saturation_or_duplication","requires":["BRAHMA","AI-HR"]}
    demand=max(0,int(uncovered_specialties))+max(0,int(contradictions))+min(max(0,int(unresolved_questions)),8)
    if demand:
        # Expansion recommendation is intentionally bounded per discussion round.
        # Additional capacity comes through later reviewed waves, not one giant spawn.
        return {"action":"expand","delta":min(demand,16),"reason":"coverage_or_independent_evidence_needed","requires":["BRAHMA","AI-HR"]}
    return {"action":"maintain","delta":0,"reason":"current_team_sufficient","requires":["BRAHMA","AI-HR"]}

def specialist_diversity_plan(subject_specialties):
    specs=[str(x).strip() for x in (subject_specialties or []) if str(x).strip()]
    rows=[]
    for i,specialty in enumerate(specs):
        rows.append({"specialty":specialty,"research_role":SPECIALIST_ROLES[i % len(SPECIALIST_ROLES)]})
    return rows
