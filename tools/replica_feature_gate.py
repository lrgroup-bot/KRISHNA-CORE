#!/usr/bin/env python3
"""Fail-closed feature acceptance matrix. An evidence path is not test proof.

This checker validates manifest structure and local evidence file presence.
Release requires a separate, independent review/approval authority.
"""
import argparse
import csv
import json
from pathlib import Path
import sys

REQUIRED = {"feature_id", "priority", "status", "test_evidence"}
STATUSES = {"passed", "failed", "partial", "not_tested", "excluded"}


def audit(path):
    path = Path(path).resolve(strict=True)
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if not REQUIRED.issubset(reader.fieldnames or []):
            raise ValueError("missing columns: " + ", ".join(
                sorted(REQUIRED - set(reader.fieldnames or []))))
        rows = list(reader)
    errors = []
    seen = set()
    counts = {status: 0 for status in STATUSES}
    for n, row in enumerate(rows, 2):
        ident = (row["feature_id"] or "").strip()
        if not ident or ident in seen:
            errors.append(f"row {n}: missing/duplicate feature_id")
        seen.add(ident)
        status = (row["status"] or "").strip()
        if status not in STATUSES:
            errors.append(f"row {n}: invalid status {status!r}")
            continue
        counts[status] += 1
        if status == "passed":
            proof = (row["test_evidence"] or "").strip()
            if not proof:
                errors.append(f"row {n}: passed requires test evidence")
            else:
                # A CSV string is never independently verified evidence. At
                # minimum demand a bounded, real, nonempty local artifact.
                try:
                    target = (path.parent / proof).resolve(strict=True)
                    if (path.parent != target and path.parent not in target.parents) or (
                        target.is_symlink() or not target.is_file() or
                        target.stat().st_size == 0 or target.stat().st_size > 10_000_000):
                        raise ValueError("artifact is not an in-scope nonempty file")
                except (OSError, ValueError, RuntimeError):
                    errors.append(f"row {n}: passed evidence file missing, empty or out of scope")
        if status == "excluded" and not (row.get("notes") or "").strip():
            errors.append(f"row {n}: exclusion requires reason in notes")
    blockers = [row["feature_id"] for row in rows
                if (row["priority"] or "").strip() == "must" and row["status"] != "passed"]
    matrix_complete = bool(rows) and not blockers and not errors and counts["failed"] == 0
    return {
        "features": len(rows), "counts": counts, "must_have_blockers": blockers,
        "errors": errors, "evidence_claims_complete": matrix_complete,
        "release_ready": False,
        "release_blocker": "independent verification and owner approval not performed",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("matrix", type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.matrix)
    except (OSError, ValueError) as exc:
        print(json.dumps({"release_ready": False, "error": str(exc)}))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["release_ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
