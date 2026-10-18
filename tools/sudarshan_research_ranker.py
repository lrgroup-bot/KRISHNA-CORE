"""SUDARSHAN research decision matrix, combining REA observations and MiroFish hypotheses.

This module does not run external tools, copy protected code, or approve releases.
"""
from .sudarshan_simulation_gates import evaluate_simulation_gates

CRITERIA = {
    "user_value": 30, "technical_gain": 25, "reuse": 20,
    "testability": 15, "cost_maintainability": 10,
}
MANDATORY = ("authorization", "license", "security", "privacy")

def rank_feature(feature_id, ratings, compliance, observations=(), simulations=None):
    if not isinstance(feature_id, str) or not feature_id.strip():
        raise ValueError("feature id required")
    if not isinstance(ratings, dict) or set(ratings) != set(CRITERIA):
        raise ValueError("all scoring criteria required")
    if not isinstance(compliance, dict):
        raise TypeError("compliance mapping required")
    for name, value in ratings.items():
        if type(value) not in (int, float) or not 0 <= value <= 5:
            raise ValueError("ratings must be numeric 0..5: " + name)
    # Unknown or unreviewed mandatory gates fail closed.
    blockers = [key for key in MANDATORY if compliance.get(key) is not True]
    observed = sorted({o for o in observations if isinstance(o, str) and o.strip()})
    if not observed:
        blockers.append("missing_research_evidence")
    sim = evaluate_simulation_gates(simulations or {})
    score = round(sum(ratings[k] * weight / 5 for k, weight in CRITERIA.items()), 2)
    return {
        "feature_id": feature_id.strip(), "score": score,
        "eligible_for_implementation_review": not blockers,
        "blockers": blockers, "observation_ids": observed,
        "simulation_gate_results": sim,
        "release_ready": False, "automatic_execution": False,
    }

def rank_backlog(items):
    ranked = [rank_feature(**item) for item in items]
    return sorted(ranked, key=lambda x: (
        not x["eligible_for_implementation_review"], -x["score"], x["feature_id"]))
