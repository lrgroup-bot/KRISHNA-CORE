"""Pure SUDARSHAN behavior-graph contracts for authorized UI observations."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Transition:
    feature_id: str
    from_state: str
    action: str
    to_state: str
    expected: str

def inspect_transitions(features, transitions):
    known = set(features)
    edges = set()
    issues = []
    for t in transitions:
        if not isinstance(t, Transition):
            issues.append("invalid_transition")
            continue
        if t.feature_id not in known:
            issues.append("unknown_feature:" + t.feature_id)
        if not all(isinstance(v, str) and v.strip() for v in (t.from_state, t.action, t.to_state, t.expected)):
            issues.append("incomplete_transition:" + t.feature_id)
        key = (t.feature_id, t.from_state, t.action)
        if key in edges:
            issues.append("duplicate_action:" + t.feature_id)
        edges.add(key)
    return {"valid": not issues, "issues": issues, "transition_count": len(transitions)}

def compare_observed(expected, actual):
    """Compare sanitized observed outputs; never claim hidden implementation parity."""
    if not isinstance(expected, dict) or not isinstance(actual, dict):
        raise TypeError("expected and actual observations must be dictionaries")
    missing = sorted(set(expected) - set(actual))
    differing = sorted(k for k in expected.keys() & actual.keys() if expected[k] != actual[k])
    return {"matched": not missing and not differing, "missing": missing, "differing": differing}
