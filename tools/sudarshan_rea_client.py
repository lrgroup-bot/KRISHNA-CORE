"""Read authorized local JavaScript analysis from an installed REA CLI.

No npx auto-download. Evidence collection is not proof of feature parity.
"""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from .sudarshan_execution_contract import AdapterResult


def analyze_javascript(target, *, root, rea_executable, authorized=False, timeout=120):
    if not authorized:
        raise PermissionError('authorization required for inspected target')
    target = Path(target).resolve(strict=True)
    root = Path(root).resolve(strict=True)
    if target != root and root not in target.parents:
        raise PermissionError('target outside explicitly authorized root')
    executable = Path(rea_executable)
    if not executable.is_absolute() or not executable.is_file():
        raise ValueError('installed REA executable absolute path required')
    if type(timeout) not in (int, float) or not 1 <= timeout <= 300:
        raise ValueError('timeout out of range')
    try:
        run = subprocess.run([str(executable), 'analyze-javascript-application',
                              str(target), '--json'], cwd=str(root), shell=False,
                             text=True, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return AdapterResult('REA', 'blocked', '', type(error).__name__)
    if run.returncode:
        return AdapterResult('REA', 'failed', '', 'REA exited nonzero')
    if not run.stdout.strip() or len(run.stdout) > 5_000_000:
        return AdapterResult('REA', 'failed', '', 'REA evidence missing or too large')
    try:
        evidence = json.loads(run.stdout)
    except json.JSONDecodeError:
        return AdapterResult('REA', 'failed', '', 'REA returned invalid JSON')
    if not isinstance(evidence, (dict, list)) or not evidence:
        return AdapterResult('REA', 'failed', '', 'REA returned empty evidence')
    if isinstance(evidence, dict) and (evidence.get('success') is False or evidence.get('error')):
        return AdapterResult('REA', 'failed', '', 'REA reported an analysis error')
    digest = sha256(run.stdout.encode()).hexdigest()
    return AdapterResult('REA', 'passed', 'sha256:' + digest,
                         'local REA JSON analysis collected; conclusions require review')
