"""Bridge built-in SUDARSHAN agents to the existing JSON adapter protocol.

Usage: python -m tools.sudarshan_native_cli --engine UI_GUARDIAN --spec ui.json --approve-local-run
All options are explicit; installation, merging and deployment are out of scope.
"""
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from .sudarshan_execution_contract import AdapterResult, ENGINES, validate_result


def dispatch(engine, spec, *, authorized=False):
    if not authorized:
        raise PermissionError('local adapter invocation requires explicit approval')
    if engine not in ENGINES or not isinstance(spec, dict):
        raise ValueError('unsupported engine or non-object specification')
    if engine == 'REA':
        from .sudarshan_rea_client import analyze_javascript
        result = analyze_javascript(spec['target'], root=spec['root'],
                    rea_executable=spec['rea_executable'], authorized=True,
                    project_id=spec.get('project_id'), evidence_root=spec.get('evidence_root'))
    elif engine == 'MiroFish':
        from .sudarshan_mirofish_client import inspect_completed_simulation
        result = inspect_completed_simulation(spec['simulation_id'], spec['project_id'],
                    base_url=spec.get('base_url','http://127.0.0.1:5001'), authorized=True,
                    evidence_root=spec.get('evidence_root'))
    elif engine == 'UI_GUARDIAN':
        if spec.get('mode') == 'android':
            from .sudarshan_android_guardian import inventory_android
            result = inventory_android(
                adb_executable=spec['adb_executable'],
                device_serial=spec['device_serial'],
                app_package=spec['app_package'], authorized=True,
                evidence_root=spec.get('evidence_root'),
                project_id=spec.get('project_id'))
        else:
            from .sudarshan_ui_guardian import run_browser
            result = run_browser(spec['plan'], authorized=True,
                                 evidence_root=spec.get('evidence_root'),
                                 project_id=spec.get('project_id'))
    elif engine == 'VISHWAKARMA':
        from .sudarshan_vishwakarma import propose_code
        result = propose_code(spec['repository'], spec['code_argv'], spec['test_argv'],
                              spec['output_dir'], authorized=True)
    elif engine == 'MRITYUNJAYA':
        from .sudarshan_mrityunjaya import verify_baseline
        result = verify_baseline(spec['baseline'], authorized=True)
    else:
        from .sudarshan_knowledge_store import connect
        from .sudarshan_brahmagyan import propose_lessons, approved_lessons
        db = connect(spec['db_path'])
        try:
            mode=spec.get('mode')
            if mode == 'propose':
                ids=propose_lessons(db,spec['project_id'],spec['feature_id'],
                    spec['rishi'],spec['source_text'],spec['evidence_ids'],
                    model=spec['model'],authorized=True)
                result=AdapterResult('BRAHMAGYAN','not_tested','',
                    '%d local Ollama learning candidates pending owner review' % len(ids))
            elif mode == 'approved':
                entries=approved_lessons(db,spec['project_id'],spec['feature_id'])
                if not entries:
                    result=AdapterResult('BRAHMAGYAN','blocked','','no approved local lessons')
                else:
                    digest=sha256(json.dumps(entries,sort_keys=True).encode()).hexdigest()
                    result=AdapterResult('BRAHMAGYAN','passed','sha256:'+digest,
                                         '%d reviewed local learning records present' % len(entries))
            else:
                raise ValueError('BRAHMAGYAN mode must be propose or approved')
        finally:
            db.close()
    return validate_result(result)


def main(argv=None):
    parser=argparse.ArgumentParser(description='Run explicitly approved native SUDARSHAN adapter')
    parser.add_argument('--engine',required=True,choices=sorted(ENGINES))
    parser.add_argument('--spec',required=True,help='existing local JSON configuration')
    parser.add_argument('--approve-local-run',action='store_true')
    args=parser.parse_args(argv)
    if not args.approve_local_run:
        parser.error('explicit --approve-local-run required')
    path=Path(args.spec).resolve(strict=True)
    if not path.is_file():
        parser.error('spec must be a JSON file')
    spec=json.loads(path.read_text(encoding='utf-8'))
    result=dispatch(args.engine,spec,authorized=True)
    print(json.dumps(asdict(result),sort_keys=True))
    # A valid not_tested/blocked result must reach the parent adapter intact.
    return 0

if __name__=='__main__':
    raise SystemExit(main())
