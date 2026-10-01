from __future__ import annotations

"""BRAHMAGYAN live-subject discovery and source-requirement policy.

This module plans research. Fetching/watching is delegated to approved workers
(SURYADEV/web/repository/paper tools). KRISHNA receives only escalations/digests.
"""

SOURCE_ROLES = {
    "official": "authoritative status, regulation, specifications or first-party facts",
    "paper": "original scientific methods, results and limitations",
    "video": "visual demonstration, lecture, interview, experiment or procedure context",
    "repository": "inspect executable implementation, tests, issues and technical history",
    "patent": "prior art, claims and technical disclosure",
    "standards": "normative technical requirements and interoperability",
    "journalism": "current-event discovery and independently reported context",
    "community": "experience signals and leads; never sufficient as final truth alone",
}

def source_requirement_plan(topic, *, live=True, visual=False, implementation=False,
                            scientific=False, regulated=False):
    roles=["official"]
    if live: roles.append("journalism")
    if scientific: roles.append("paper")
    if visual: roles.append("video")
    if implementation: roles.append("repository")
    if regulated: roles.append("standards")
    roles=list(dict.fromkeys(roles))
    return {
        "topic":str(topic or ""),
        "required_source_roles":roles,
        "requirements":[{"role":r,"purpose":SOURCE_ROLES[r]} for r in roles],
        "youtube_required":bool(visual),
        "website_required":True,
        "truth_policy":"popularity and repetition are discovery signals, not evidence quality",
        "verification":"important claims require primary/authoritative evidence plus independent corroboration when available",
    }

def escalation_policy(*, affects_krishna=False, high_impact_conflict=False,
                      new_permanent_rishi=False, major_resource_request=False,
                      permission_or_safety=False):
    reasons=[k for k,v in {
        "affects_krishna":affects_krishna,
        "high_impact_conflict":high_impact_conflict,
        "new_permanent_rishi":new_permanent_rishi,
        "major_resource_request":major_resource_request,
        "permission_or_safety":permission_or_safety,
    }.items() if v]
    return {
        "escalate_to_krishna":bool(reasons),
        "reasons":reasons,
        "owner":"BRAHMA/BRAHMAGYAN",
        "policy":"routine discovery, source selection, watching, reading, Rishi/Shishya research and QC stay inside BRAHMAGYAN",
    }
