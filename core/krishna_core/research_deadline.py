from __future__ import annotations
import time

"""60-second deep-research planner for BRAHMAGYAN.

The deadline bounds interactive latency, never truth. Slow physical/lab/video work
is represented as unresolved evidence instead of blocking or fabricating results.
"""

DEFAULT_BUDGET_SECONDS=60
STAGES=(
    ("frame",0,2),
    ("route",2,5),
    ("parallel_research",5,40),
    ("verify_synthesize",40,50),
    ("brahma_qc",50,58),
    ("deliver",58,60),
)
LANES=(
    "gyan_cache","primary_official","current_web","papers","contradictions",
    "failure_history","repositories","standards_patents","indexed_video","cross_domain",
)

def deadline_plan(question, *, budget_seconds=DEFAULT_BUDGET_SECONDS, available_lanes=None):
    budget=max(10,min(int(budget_seconds),60))
    lanes=list(dict.fromkeys(available_lanes or LANES))
    return {
        "question":str(question or ""),
        "budget_seconds":budget,
        "hard_interactive_deadline":True,
        "parallel_lanes":lanes,
        "stages":[{"name":n,"start_s":a,"target_end_s":min(b,budget)} for n,a,b in STAGES if a < budget],
        "critical_path_policy":"wait for the strongest independent evidence paths, not every worker",
        "slow_evidence_policy":"return unresolved/missing evidence at deadline; never manufacture certainty",
        "background_policy":"long physical experiments, full-length video and unavailable-source work are separate missions",
    }

def evidence_lane_priority(*, authority, relevance, freshness, independence,
                           information_gain, latency_seconds, duplicate_risk=0.0):
    benefit=sum(max(0.0,min(float(x),1.0)) for x in
                (authority,relevance,freshness,independence,information_gain))
    penalty=max(.25,float(latency_seconds))*(1.0+max(0.0,min(float(duplicate_risk),1.0)))
    return round(benefit/penalty,6)

def deadline_state(started_at, completed_lanes, unresolved_lanes):
    elapsed=max(0.0,time.monotonic()-float(started_at))
    return {
        "elapsed_seconds":round(elapsed,3),
        "remaining_seconds":round(max(0.0,DEFAULT_BUDGET_SECONDS-elapsed),3),
        "completed_lanes":list(completed_lanes or []),
        "unresolved_lanes":list(unresolved_lanes or []),
        "deliver_now":elapsed >= DEFAULT_BUDGET_SECONDS,
    }
