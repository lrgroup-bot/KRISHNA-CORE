"""Fail-closed KRISHNA release evidence gate. No GitHub or deployment mutations."""
import argparse
import json
from pathlib import Path

REQUIRED = ('core_api', 'windows_exe', 'android_apk', 'local_models', 'network_enrollment', 'security', 'rollback')
VALID = {'pass', 'fail', 'not_tested', 'blocked'}


def assess(report):
    errors = []
    checks = report.get('checks')
    if not isinstance(checks, dict):
        return {'ready': False, 'errors': ['checks must be an object']}
    for key in REQUIRED:
        entry = checks.get(key)
        if not isinstance(entry, dict):
            errors.append(f'{key}: missing evidence')
            continue
        status = entry.get('status')
        if status not in VALID:
            errors.append(f'{key}: invalid status')
        elif status != 'pass':
            errors.append(f'{key}: {status}')
        if status == 'pass' and not (isinstance(entry.get('evidence'), str) and entry['evidence'].strip()):
            errors.append(f'{key}: PASS requires evidence')
    for name, entry in checks.items():
        if not isinstance(entry, dict) or entry.get('status') not in VALID:
            errors.append(f'{name}: malformed entry')
        elif entry['status'] in ('fail', 'blocked'):
            errors.append(f'{name}: {entry["status"]}')
    return {'ready': not errors, 'errors': sorted(set(errors))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    result = assess(json.loads(args.report.read_text(encoding='utf-8')))
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['ready'] else 1)


if __name__ == '__main__':
    main()
