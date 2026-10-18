"""VISHWAKARMA: local coding proposal + verification in disposable Git worktree.

Requires a trusted local agent executable supplied by the owner. The Git worktree
isolates working copies, not processes: OS sandboxing is needed for untrusted
commands. No changes are applied to the original repository.
"""
import hashlib
import io
import json
from pathlib import Path
import zipfile
from .sudarshan_execution_contract import AdapterResult
from .sudarshan_worktree import isolated_worktree, execute, change_report


def propose_code(repository, code_argv, test_argv, output_dir, *, authorized=False):
    if not authorized:
        raise PermissionError('explicit coding agent execution approval required')
    repository = Path(repository).resolve(strict=True)
    output = Path(output_dir).resolve()
    if repository == output or repository in output.parents:
        raise ValueError('proposal artifacts must be outside the source repository')
    if not isinstance(code_argv, (list, tuple)) or not isinstance(test_argv, (list, tuple)):
        raise ValueError('code and test argument vectors required')
    with isolated_worktree(repository) as checkout:
        coding = execute(checkout, code_argv)
        if not coding['passed']:
            return AdapterResult('VISHWAKARMA', 'failed', '', 'trusted coding command failed in disposable worktree')
        changes = change_report(checkout)
        if not changes['dirty']:
            return AdapterResult('VISHWAKARMA', 'not_tested', '', 'coding command produced no changes')
        verification = execute(checkout, test_argv)
        if not verification['passed']:
            return AdapterResult('VISHWAKARMA', 'failed', '', 'verification failed; disposable edits discarded')
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('tracked.patch', changes['tracked_patch'])
            archive.writestr('status.json', json.dumps({
                'status': changes['status'], 'untracked': changes['untracked_files'],
                'test_passed': True, 'requires_owner_review': True}, sort_keys=True))
            total_size = 0
            for name in changes['untracked_files']:
                file = (checkout / name).resolve()
                if checkout not in file.parents or not file.is_file() or (checkout / name).is_symlink():
                    raise ValueError('unsafe generated artifact path')
                data = file.read_bytes()
                total_size += len(data)
                if total_size > 5_000_000:
                    raise ValueError('generated files exceed review artifact limit')
                archive.writestr('untracked/' + name, data)
        blob = buffer.getvalue()
    digest = hashlib.sha256(blob).hexdigest()
    output.mkdir(parents=True, exist_ok=True)
    archive_path = output / ('sudarshan-proposal-' + digest[:16] + '.zip')
    archive_path.write_bytes(blob)
    return AdapterResult('VISHWAKARMA', 'passed', 'sha256:' + digest,
                         'verified disposable changes exported for owner review: ' + str(archive_path))
