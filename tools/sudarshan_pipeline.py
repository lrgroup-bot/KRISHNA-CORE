"""Orchestrate permissioned planning and evidence evaluation without executing external tools."""
from .sudarshan_reconstruction import create_plan
from .sudarshan_evidence import feature_coverage
from .sudarshan_35_gates import evaluate

def assess(request, observations=(), gate_evidence=None):
    plan=create_plan(request)
    coverage=feature_coverage(plan,observations)
    gates=evaluate(gate_evidence or {})
    return {'plan':plan,'coverage':coverage,'gates':gates,'release_ready':bool(coverage['coverage']==1 and gates['release_ready']),'execution_enabled':False,'requires_human_approval':True}
