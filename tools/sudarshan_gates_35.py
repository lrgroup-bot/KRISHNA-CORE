"""Importable 35-gate evidence evaluator. Claims are not independently verified."""
GATES=('authorization','license','privacy','security','scope','provenance','integrity','freshness','traceability','feature_inventory','route_inventory','interaction_inventory','accessibility','data_contracts','dependencies','architecture','budget','offline','models','reproducibility','simulation_limits','counterevidence','human_review','build_plan','unit_tests','integration_tests','browser_tests','mobile_tests','regression_tests','performance','rollback','audit','owner_approval','deployment','post_deploy_verification')

def evaluate(evidence):
    if not isinstance(evidence,dict):raise TypeError('evidence mapping required')
    if set(evidence)-set(GATES):raise ValueError('unknown gate')
    results={}
    for gate in GATES:
        item=evidence.get(gate)
        if item is None:results[gate]='not_tested'
        elif not isinstance(item,dict) or not item.get('evidence_id') or not item.get('reviewer'):results[gate]='insufficient_evidence'
        else:results[gate]='passed' if item.get('passed') is True else 'failed'
    return {'total':len(GATES),'results':results,'passed':sum(v=='passed' for v in results.values()),'evidence_claims_complete':all(v=='passed' for v in results.values()),'release_ready':False}
