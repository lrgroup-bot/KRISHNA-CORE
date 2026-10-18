"""Run explicitly configured local, authorized adapter commands.

No shell, no network invocation by this module, no automatic repair or deployment.
External REA/MiroFish installations must be configured by the operator.
"""
import json
import subprocess
from pathlib import Path
from .sudarshan_execution_contract import AdapterResult, ENGINES, validate_result

def run_adapter(engine, argv, *, authorized=False, cwd=None, timeout=60):
    if not authorized:
        raise PermissionError("explicit authorization required")
    if engine not in ENGINES:
        raise ValueError("unknown adapter")
    if not isinstance(argv, (tuple,list)) or not argv or not all(isinstance(x,str) and x for x in argv):
        raise ValueError("argv must be nonempty string sequence")
    if not isinstance(timeout,(int,float)) or not 1 <= timeout <= 300:
        raise ValueError("timeout out of range")
    if cwd is None or not Path(cwd).is_dir():
        raise ValueError("existing isolated working directory required")
    # Executables must be absolute to avoid PATH hijacking.
    executable=Path(argv[0])
    if not executable.is_absolute() or not executable.is_file():
        raise ValueError("absolute existing executable required")
    try:
        result=subprocess.run(list(argv),cwd=str(cwd),capture_output=True,text=True,
                              timeout=timeout,check=False,shell=False)
    except (OSError,subprocess.TimeoutExpired) as exc:
        return AdapterResult(engine,"blocked","",type(exc).__name__)
    if result.returncode:
        return AdapterResult(engine,"failed","","adapter exited nonzero")
    try:
        output=json.loads(result.stdout)
    except (json.JSONDecodeError,TypeError):
        return AdapterResult(engine,"failed","","invalid JSON output")
    if not isinstance(output,dict) or output.get("engine")!=engine:
        return AdapterResult(engine,"failed","","adapter engine mismatch")
    record=AdapterResult(engine,output.get("status","failed"),
                         output.get("evidence_id",""),output.get("summary",""))
    return validate_result(record)
