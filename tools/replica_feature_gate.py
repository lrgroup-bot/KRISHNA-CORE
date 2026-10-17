#!/usr/bin/env python3
"""Local-first, dependency-free feature evidence gate. No network or deployment."""
import argparse,csv,json,pathlib,sys
REQUIRED={"feature_id","priority","status","test_evidence"}
STATUSES={"passed","failed","partial","not_tested","excluded"}
def audit(path):
    with path.open(newline="",encoding="utf-8") as fh:
        reader=csv.DictReader(fh)
        if not REQUIRED.issubset(set(reader.fieldnames or [])):
            raise ValueError("missing columns: "+", ".join(sorted(REQUIRED-set(reader.fieldnames or []))))
        rows=list(reader)
    errors=[];seen=set();counts={s:0 for s in STATUSES}
    for n,row in enumerate(rows,2):
        ident=(row["feature_id"] or "").strip()
        if not ident or ident in seen:errors.append(f"row {n}: missing/duplicate feature_id")
        seen.add(ident)
        status=(row["status"] or "").strip()
        if status not in STATUSES:errors.append(f"row {n}: invalid status {status!r}");continue
        counts[status]+=1
        if status=="passed" and not (row["test_evidence"] or "").strip():
            errors.append(f"row {n}: passed requires test evidence")
        if status=="excluded" and not (row.get("notes") or "").strip():
            errors.append(f"row {n}: exclusion requires reason in notes")
    blockers=[r["feature_id"] for r in rows if (r["priority"] or "").strip()=="must" and r["status"]!="passed"]
    return {"features":len(rows),"counts":counts,"must_have_blockers":blockers,"errors":errors,"release_ready":bool(rows) and not blockers and not errors and counts["failed"]==0}
def main():
    parser=argparse.ArgumentParser();parser.add_argument("matrix",type=pathlib.Path);args=parser.parse_args()
    try:result=audit(args.matrix)
    except (OSError,ValueError) as exc:print(json.dumps({"release_ready":False,"error":str(exc)}));return 2
    print(json.dumps(result,indent=2));return 0 if result["release_ready"] else 1
if __name__=="__main__":sys.exit(main())
