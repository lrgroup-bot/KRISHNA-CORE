"""MiroFish-inspired selection gates; deterministic evaluation of simulation evidence."""
SIMULATION_GATES = (
    "stakeholder_simulation", "scenario_comparison", "relationship_impact",
    "second_order_effects", "agent_interviews", "temporal_behavior",
    "stress_scenarios", "contradictory_evidence",
    "simulation_reproducibility", "prediction_validation",
)

def evaluate_simulation_gates(evidence):
    if not isinstance(evidence, dict):
        raise TypeError("evidence mapping required")
    unknown = set(evidence) - set(SIMULATION_GATES)
    if unknown:
        raise ValueError("unknown simulation gates: " + ",".join(sorted(unknown)))
    results = {}
    for gate in SIMULATION_GATES:
        item = evidence.get(gate)
        if item is None:
            results[gate] = "not_tested"
        elif not isinstance(item, dict) or not isinstance(item.get("source"), str) or not item["source"].strip():
            results[gate] = "insufficient_evidence"
        elif item.get("verified") is True and item.get("real_world_test") is True:
            results[gate] = "validated"
        else:
            results[gate] = "simulation_only"
    return {"gates": results, "validated": sum(v == "validated" for v in results.values()),
            "simulation_only": sum(v == "simulation_only" for v in results.values()),
            "all_validated": all(v == "validated" for v in results.values())}
