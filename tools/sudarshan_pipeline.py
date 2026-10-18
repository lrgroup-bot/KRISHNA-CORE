"""Orchestrate permissioned planning and evidence evaluation without executing external tools."""
from .sudarshan_reconstruction import create_plan
from .sudarshan_evidence import feature_coverage
from .sudarshan_gates_35 import evaluate

def assess(request, observations=(), gate_evidence=None):
    plan=create_plan(request)
    coverage=feature_coverage(plan,observations)
    gates=evaluate(gate_evidence or {})
    return {'plan':plan,'coverage':coverage,'gates':gates,'release_ready':bool(coverage['coverage']==1 and gates['release_ready']),'execution_enabled':False,'requires_human_approval':True}

from .sudarshan_execution_contract import prepare_handoff, readiness

def assess_integrations(project_id, feature_id, authorized, adapter_results):
    """Evaluate explicit host-provided adapter results; no implicit execution."""
    handoff=prepare_handoff(project_id,feature_id,authorized,adapter_results)
    return {'handoff':handoff,'readiness':readiness(handoff)}
