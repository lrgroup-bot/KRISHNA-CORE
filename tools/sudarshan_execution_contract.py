"""Safe integration contracts for REA, MiroFish, Brahmagyan and engineering agents.

Adapters are supplied by the host. No third-party tool is invoked implicitly.
"""
from dataclasses import dataclass
from hashlib import sha256
import json

@dataclass(frozen=True)
class AdapterResult:
    engine: str
    status: str
    evidence_id: str
    summary: str

ENGINES = frozenset(('REA','MiroFish','BRAHMAGYAN','VISHWAKARMA','UI_GUARDIAN','MRITYUNJAYA'))

def validate_result(result):
    if not isinstance(result,AdapterResult):
        raise TypeError('AdapterResult required')
    if result.engine not in ENGINES or result.status not in ('passed','failed','blocked','not_tested'):
        raise ValueError('invalid engine or status')
    if result.status=='passed' and (not result.evidence_id.strip() or not result.summary.strip()):
        raise ValueError('passed results require evidence and summary')
    return result

def prepare_handoff(project_id, feature_id, authorized, results):
    if not authorized:
        raise PermissionError('project authorization required')
    if not project_id.strip() or not feature_id.strip():
        raise ValueError('project and feature required')
    checked=[validate_result(r) for r in results]
    if len({r.engine for r in checked})!=len(checked):
        raise ValueError('duplicate engine results')
    payload={'project_id':project_id,'feature_id':feature_id,
             'results':[{'engine':r.engine,'status':r.status,'evidence_id':r.evidence_id,'summary':r.summary} for r in checked]}
    payload['digest']=sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    payload['implementation_allowed']=False
    payload['deployment_allowed']=False
    return payload

def readiness(handoff):
    by_engine={r['engine']:r['status'] for r in handoff['results']}
    missing=sorted(ENGINES-set(by_engine))
    failed=sorted(k for k,v in by_engine.items() if v!='passed')
    return {'missing':missing,'blocked':failed,'ready_for_human_review':not missing and not failed,
            'automatic_deployment':False}
