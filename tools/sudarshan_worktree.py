"""Disposable Git workspace for VISHWAKARMA and MRITYUNJAYA.

A coding agent may edit and test the disposable checkout; the original repository
is never reset, cleaned, committed, or deployed by this module. Explicit local
owner approval remains the caller's responsibility.
"""
from contextlib import contextmanager
from pathlib import Path
import subprocess
import tempfile


def _git(*args, cwd=None, timeout=30):
    result = subprocess.run(['git', *map(str, args)], cwd=cwd, text=True,
                            capture_output=True, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError('git operation failed: ' + ' '.join(str(a) for a in args[:3])
                           + ': ' + result.stderr[:500])
    return result.stdout


@contextmanager
def isolated_worktree(repository):
    """Yield a temporary checkout at HEAD and remove it even after exceptions."""
    repository = Path(repository).resolve(strict=True)
    top = Path(_git('-C', repository, 'rev-parse', '--show-toplevel').strip()).resolve()
    if top != repository:
        raise ValueError('repository must be the Git worktree root')
    with tempfile.TemporaryDirectory(prefix='sudarshan-sandbox-') as directory:
        checkout = Path(directory) / 'checkout'
        _git('-C', top, 'worktree', 'add', '--detach', str(checkout), 'HEAD')
        try:
            yield checkout
        finally:
            _git('-C', top, 'worktree', 'remove', '--force', str(checkout))


def execute(checkout, argv, timeout=120):
    """Execute a caller-approved argv inside a disposable checkout. No shell."""
    checkout = Path(checkout).resolve(strict=True)
    if not (checkout / '.git').exists():
        raise ValueError('Git worktree checkout required')
    if not isinstance(argv, (list, tuple)) or not argv or not all(
            isinstance(v, str) and v for v in argv):
        raise ValueError('nonempty argument vector required')
    if not Path(argv[0]).is_absolute() or not Path(argv[0]).is_file():
        raise ValueError('absolute existing executable required')
    if type(timeout) not in (int, float) or not 1 <= timeout <= 300:
        raise ValueError('timeout must be 1..300 seconds')
    result = subprocess.run(list(argv), cwd=checkout, text=True, capture_output=True,
                            timeout=timeout, check=False, shell=False)
    return {'returncode': result.returncode, 'stdout': result.stdout[-20000:],
            'stderr': result.stderr[-20000:], 'passed': result.returncode == 0}


def change_report(checkout):
    """Inspect tracked and untracked edits; report only, never apply to source."""
    checkout = Path(checkout).resolve(strict=True)
    tracked = _git('-C', checkout, 'diff', '--binary', 'HEAD', '--')
    untracked = _git('-C', checkout, 'ls-files', '--others', '--exclude-standard')
    status = _git('-C', checkout, 'status', '--porcelain=v1', '--untracked-files=all')
    return {'dirty': bool(status.strip()), 'status': status.splitlines(),
            'tracked_patch': tracked, 'untracked_files': untracked.splitlines(),
            'requires_owner_review': True, 'applied_to_original': False}
