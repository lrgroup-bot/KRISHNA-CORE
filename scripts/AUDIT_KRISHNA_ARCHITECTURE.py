from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT=Path(__file__).resolve().parents[1]
CORE_ROOT=REPO_ROOT/"core"
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0,str(CORE_ROOT))

from krishna_core.architecture_truth import ArchitectureTruthAudit


def main():
    parser=argparse.ArgumentParser(description="Audit canonical KRISHNA architecture/product truth.")
    parser.add_argument("--json",action="store_true",help="emit full JSON report")
    args=parser.parse_args()

    report=ArchitectureTruthAudit(REPO_ROOT).scan()
    req=report.get("requirements") or {}
    merge_integrity=report.get("merge_integrity") or {}
    summary=report.get("summary") or {}
    failures=[]

    if not req.get("present"):
        failures.append("canonical requirements ledger is missing")
    if req.get("invalid_statuses"):
        failures.append("invalid requirements statuses: "+", ".join(req["invalid_statuses"]))
    if req.get("evidence_missing"):
        failures.append(f"{len(req['evidence_missing'])} requirements evidence paths are missing")

    integrity_failures=(
        ("same_scope_python_redefinitions","same-scope Python redefinitions"),
        ("duplicate_action_bus_registrations","duplicate Shared Action Bus registrations"),
        ("duplicate_agent_runtime_registrations","duplicate agent-runtime registrations"),
        ("duplicate_http_routes_same_handler","duplicate HTTP routes in the same handler"),
        ("duplicate_specialist_ids","duplicate specialist IDs"),
        ("parse_errors","merge-integrity parse errors"),
    )
    for key,label in integrity_failures:
        rows=merge_integrity.get(key) or []
        if rows:
            failures.append(f"{len(rows)} {label}")

    output={
        "ok":not failures,
        "requirements_version":req.get("version"),
        "status_counts":req.get("status_counts"),
        "summary":summary,
        "failures":failures,
        "review_candidates":{
            "orphan_candidates":summary.get("orphan_candidates",0),
            "orphan_candidate_details":report.get("orphan_candidates") or [],
            "duplicate_basenames":summary.get("duplicate_basenames",0),
            "duplicate_basename_details":((report.get("duplicates") or {}).get("same_basename") or [])[:50],
            "merge_integrity":merge_integrity,
            "source_tree_missing_current_modules":summary.get("source_tree_missing_current_modules",0),
            "source_tree_drift":report.get("source_tree_drift") or {},
        },
        "policy":"heuristic duplicate basenames/orphans remain review-only; true same-scope redefinitions, duplicate global registrations/routes/IDs, parse errors, missing canonical evidence and invalid statuses fail closed",
    }
    print(json.dumps(report if args.json else output,indent=2,ensure_ascii=False))
    return 0 if not failures else 2


if __name__=="__main__":
    raise SystemExit(main())
