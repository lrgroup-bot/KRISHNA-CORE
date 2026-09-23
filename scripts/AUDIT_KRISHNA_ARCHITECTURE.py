from __future__ import annotations

"""CLI gate for the canonical KRISHNA ArchitectureTruthAudit.

Fails only on objective product-truth defects: missing indexed evidence, invalid
implementation statuses, or an unreadable/missing requirements ledger. Duplicate,
orphan and source-tree drift findings remain review warnings because the canonical
audit deliberately treats them as conservative candidates rather than auto-delete
authority.
"""

import argparse
import json
from pathlib import Path
import sys


REPO=Path(__file__).resolve().parents[1]
CORE=REPO/"core"
if str(CORE) not in sys.path:
    sys.path.insert(0,str(CORE))

from krishna_core.architecture_truth import ArchitectureTruthAudit


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--json",action="store_true",help="print the complete audit report")
    args=parser.parse_args()

    report=ArchitectureTruthAudit(REPO).scan()
    req=report.get("requirements") or {}
    summary=report.get("summary") or {}
    failures=[]
    if not req.get("present"):
        failures.append("canonical requirements ledger is missing")
    for row in req.get("evidence_missing") or []:
        failures.append(f"missing requirement evidence: {row.get('id')} -> {row.get('path')}")
    for value in req.get("invalid_statuses") or []:
        failures.append(f"invalid implementation status: {value}")

    output={
        "version":report.get("version"),
        "requirements_version":req.get("version"),
        "requirements_indexed":summary.get("requirements_indexed"),
        "requirements_missing_evidence":summary.get("requirements_missing_evidence"),
        "invalid_statuses":req.get("invalid_statuses") or [],
        "legacy_roots_present":summary.get("legacy_roots_present"),
        "duplicate_basenames":summary.get("duplicate_basenames"),
        "orphan_candidates":summary.get("orphan_candidates"),
        "source_tree_missing_current_modules":summary.get("source_tree_missing_current_modules"),
        "failures":failures,
        "result":"FAIL" if failures else "PASS",
    }
    print(json.dumps(report if args.json else output,indent=2,ensure_ascii=False))
    return 1 if failures else 0


if __name__=="__main__":
    raise SystemExit(main())
