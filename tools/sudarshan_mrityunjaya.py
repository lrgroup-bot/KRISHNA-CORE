"""MRITYUNJAYA integrity check for original Git repositories.

Failed VISHWAKARMA changes are discarded in its disposable worktree. This
module verifies that original HEAD and worktree status remain unchanged.
No destructive git reset or overwriting owner files.
"""
import hashlib
import json
from pathlib import Path
from .sudarshan_execution_contract import AdapterResult
from .sudarshan_worktree import _git


def baseline(repository):
    repository = Path(repository).resolve(strict=True)
    top = Path(_git('-C',repository,'rev-parse','--show-toplevel').strip()).resolve()
    if top != repository:
        raise ValueError('Git repository root required')
    return {'repository': str(repository),
            'head': _git('-C',repository,'rev-parse','HEAD').strip(),
            'status': hashlib.sha256(_git('-C',repository,'status','--porcelain=v1',
                                          '--untracked-files=all').encode()).hexdigest()}


def verify_baseline(snapshot, *, authorized=False):
    if not authorized:
        raise PermissionError('explicit recovery verification authorization required')
    if not isinstance(snapshot, dict) or set(snapshot) != {'repository','head','status'}:
        raise ValueError('complete baseline required')
    now = baseline(snapshot['repository'])
    matches = now['head'] == snapshot['head'] and now['status'] == snapshot['status']
    digest = hashlib.sha256(json.dumps(now,sort_keys=True).encode()).hexdigest()
    return AdapterResult('MRITYUNJAYA', 'passed' if matches else 'failed',
                         'sha256:'+digest if matches else '',
                         'original Git checkout unchanged' if matches else 'original Git checkout changed; human recovery required')
