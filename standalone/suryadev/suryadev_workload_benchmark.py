"""Read-only SURYADEV 13-source stopwatch and source-evidence audit.

Uses operator-approved local plans only; does not approve URLs, download media,
start a second worker, reset a ledger, bypass 429 or claim model mastery.
The dashboard and its existing worker must already be running.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from urllib.request import urlopen

from suryadev_feeder import read_plan
from suryadev_book_continuity import read_book_plan
from suryadev_book_reader import file_sha256
from suryadev_sources import source_kind
from suryadev_task_details import _evidence_state
from suryadev_youtube_audit import observer_jobs
from suryadev_book_dashboard import book_learning_snapshot

COUNTS = {"pdf": 3, "website": 2, "book": 5, "youtube": 3}
FINISHED = {"done", "failed"}
VIDEO_EVIDENCE = {"AWAITING_SERVER_ACK", "ACKNOWLEDGED_CLEANED"}


def select(root, manifest=None):
    """Select exact sources from approved ledgers; explicit manifest optional."""
    root = Path(root).expanduser().resolve()
    plan = read_plan(root / "learning-plan.json")
    books = read_book_plan(root / "book-plan.json")
    by_kind = {kind: [] for kind in ("pdf", "website", "youtube")}
    for url in dict.fromkeys(plan["approved_urls"]):
        kind = source_kind(url)
        if kind in by_kind:
            by_kind[kind].append(url)
    if manifest is None:
        chosen = {kind: urls[:COUNTS[kind]] for kind, urls in by_kind.items()}
        chosen["book"] = [b["sha256"] for b in books["books"][:COUNTS["book"]]]
    else:
        obj = json.loads(Path(manifest).read_text(encoding="utf-8"))
        if not isinstance(obj, dict) or obj.get("schema") != "suryadev.workload-13.v1":
            raise ValueError("Invalid explicit benchmark selection schema")
        expected = {"schema", "pdf_urls", "website_urls", "youtube_urls", "book_sha256"}
        if set(obj) != expected:
            raise ValueError("Benchmark selection requires exactly the known four source lists")
        chosen = {}
        for kind in by_kind:
            chosen[kind] = obj[kind + "_urls"]
        chosen["book"] = obj["book_sha256"]
    known = {b["sha256"]: b for b in books["books"]}
    for kind, wanted in COUNTS.items():
        targets = chosen.get(kind)
        if not isinstance(targets, list) or len(targets) != wanted or len(set(targets)) != wanted:
            raise ValueError(f"Need exactly {wanted} distinct approved {kind} sources; found "
                             f"{len(targets) if isinstance(targets, list) else 0}. "
                             "Approve missing sources before running; nothing was changed.")
        allowed = set(by_kind[kind]) if kind != "book" else set(known)
        if any(not isinstance(value, str) or value not in allowed for value in targets):
            raise ValueError(f"Unapproved or misclassified {kind} source in benchmark selection")
    for digest in chosen["book"]:
        if file_sha256(known[digest]["path"]) != digest:
            raise ValueError("Previously approved local book changed: " + digest[:16])
    return chosen


def readonly_db(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=6)
    con.execute("PRAGMA query_only=ON")
    return con


def source_snapshot(data, selection):
    data = Path(data)
    with readonly_db(data / "suryadev.sqlite3") as db:
        records = {}
        for kind in ("pdf", "website", "youtube"):
            for url in selection[kind]:
                row = db.execute(
                    "SELECT j.id,j.status,j.error,f.sha256,f.summary_method,"
                    "t.elapsed_seconds,t.acquisition_seconds,t.summary_phase_seconds "
                    "FROM jobs j LEFT JOIN findings f ON f.job_id=j.id "
                    "LEFT JOIN job_timing t ON t.job_id=j.id "
                    "WHERE j.url=? ORDER BY j.id DESC,f.id DESC LIMIT 1",
                    (url,)).fetchone()
                if row:
                    jid,status,error,digest,method,elapsed,acquisition,analysis = row
                    records[url] = {"kind":kind, "job_id":jid, "status":status,
                                    "error":str(error or "")[:180],
                                    "evidence_sha256":digest or "",
                                    "evidence_integrity":_evidence_state(data,digest),
                                    "processing_method":method or "",
                                    "elapsed_seconds":elapsed,
                                    "acquisition_seconds":acquisition,
                                    "analysis_seconds":analysis,
                                    "comprehension_verified":False}
                else:
                    records[url] = {"kind":kind, "status":"not_queued",
                                    "evidence_integrity":"not_recorded",
                                    "comprehension_verified":False}
    book_state = book_learning_snapshot(data)
    by_sha = {x["source_sha256"]: x for x in book_state["books"]}
    for sha in selection["book"]:
        item=by_sha.get(sha)
        records["book:"+sha] = {
            "kind":"book",
            "status":item["status"] if item else "not_indexed",
            "title":item["title"] if item else "",
            "lines_processed":item["lines_processed"] if item else 0,
            "lines_total":item["lines_total"] if item else 0,
            "index_available":item is not None,
            "model":item.get("model") if item else None,
            "source_sha256":sha,
            "comprehension_verified":False,
            "rishi_exam_verified":False}
    observations={x["url"]:x for x in observer_jobs(data,limit=50)}
    for url in selection["youtube"]:
        item=observations.get(url)
        records[url]["video_observation_status"] = item.get("status") if item else "not_observed"
        records[url]["video_observation_seconds"] = item.get("wall_clock_seconds") if item else None
        records[url]["video_visual_coverage_verified"] = False
    return records


def operations(base):
    url = base.rstrip("/")+"/api/operations"
    with urlopen(url, timeout=8) as resp:
        if resp.status != 200:
            raise RuntimeError("Dashboard operation endpoint failed")
        raw=resp.read(1_000_001)
        if len(raw)>1_000_000:
            raise ValueError("Dashboard report is unexpectedly large")
    obj=json.loads(raw)
    if not isinstance(obj,dict):
        raise ValueError("Dashboard returned invalid operations JSON")
    return obj


def collect(root, chosen, base, max_minutes, sample_seconds, output):
    """Observe elapsed wall time, never terminate a worker at timeout."""
    output=Path(output).expanduser().resolve()
    output.mkdir(parents=True,exist_ok=True)
    started=time.time()
    baseline=source_snapshot(root,chosen)
    initial=operations(base)
    if initial.get("worker",{}).get("state") not in ("starting","idle","busy","checking"):
        raise RuntimeError("SURYADEV learning worker is not running; start it in the dashboard")
    report={"schema":"suryadev.workload-audit.v1", "started_at":started,
            "selection":chosen,"baseline":baseline,"observations":[],
            "status":"running", "learning_mastery_verified":False,
            "note":"Successful extraction/indexing is not understanding or Rishi review"}
    deadline=time.monotonic()+max_minutes*60
    try:
        while True:
            now=time.time()
            op=operations(base)
            tasks=source_snapshot(root,chosen)
            cap=op.get("capacity",{})
            checkpoint={
                "at":now,"wall_elapsed_seconds":round(now-started,2),
                "worker":op.get("worker",{}).get("state"),
                "admission_safe":cap.get("safe"),
                "admission_slots":cap.get("max_total"),
                "active":cap.get("active_total"),
                "cpu_percent":cap.get("cpu_percent"),
                "ram_percent":cap.get("ram_percent"),
                "book_workers_active":op.get("concurrent_books",{}).get("active",0),
                "video_workers_active":op.get("concurrent_videos",{}).get("active",0),
                "queued":op.get("queued_total"),
                "source_records":tasks}
            report["observations"].append(checkpoint)
            source_done=all(tasks[u].get("status") in FINISHED
                            for k in ("pdf","website","youtube") for u in chosen[k])
            book_done=all(tasks["book:"+sha].get("status")=="complete"
                          for sha in chosen["book"])
            video_done=all(tasks[u].get("video_observation_status") in VIDEO_EVIDENCE
                           for u in chosen["youtube"])
            if source_done and book_done and video_done:
                report["status"]="all_collection_lanes_terminal"
                break
            if time.monotonic()>=deadline:
                report["status"]="time_limit_reached_jobs_may_still_be_running"
                break
            time.sleep(sample_seconds)
    except (OSError,ValueError,RuntimeError,sqlite3.Error) as exc:
        report["status"]="monitoring_error"
        report["monitoring_error"]=type(exc).__name__+": "+str(exc)[:200]
    report["ended_at"]=time.time()
    report["wall_elapsed_seconds"]=round(report["ended_at"]-started,2)
    report["final"]=report["observations"][-1] if report["observations"] else {}
    report["mastery_verified"]=False
    filename=output/("suryadev-13-benchmark-"+time.strftime("%Y%m%d-%H%M%S",
                                time.localtime(started))+".json")
    filename.write_text(json.dumps(report,indent=2,ensure_ascii=False,default=str),
                        encoding="utf-8")
    return filename,report


def main(argv=None):
    p=argparse.ArgumentParser(description="SURYADEV one-worker 13-source evidence benchmark")
    p.add_argument("--data",required=True,type=Path)
    p.add_argument("--manifest",type=Path)
    p.add_argument("--dashboard",default="http://127.0.0.1:8872")
    p.add_argument("--minutes",type=int,default=45)
    p.add_argument("--sample-seconds",type=int,default=15)
    p.add_argument("--report-dir",type=Path,default=Path.cwd()/"suryadev-benchmark-reports")
    p.add_argument("--preflight",action="store_true")
    a=p.parse_args(argv)
    if not 1<=a.minutes<=720 or not 5<=a.sample_seconds<=300:
        p.error("Minutes must be 1..720 and sampling 5..300 seconds")
    try:
        chosen=select(a.data,a.manifest)
        print(json.dumps({"approved_selection":chosen},ensure_ascii=False,indent=2),flush=True)
        if a.preflight:
            print("PASS: all 13 source approvals and local book SHA-256 values verified")
            return 0
        filename,report=collect(a.data,chosen,a.dashboard,a.minutes,
                                a.sample_seconds,a.report_dir)
        print(json.dumps({"report":str(filename),"outcome":report["status"],
                          "elapsed_seconds":report["wall_elapsed_seconds"],
                          "mastery_verified":False},indent=2),flush=True)
        return 0 if report["status"]=="all_collection_lanes_terminal" else 3
    except (OSError,ValueError,RuntimeError,sqlite3.Error,KeyError) as exc:
        print("BENCHMARK NOT STARTED: "+type(exc).__name__+": "+str(exc),flush=True)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
