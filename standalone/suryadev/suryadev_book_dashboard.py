"""Read-only book telemetry for existing SURYADEV Garudanetra/source/hardware cards.

Never creates a missing database, considers indexing equal to learning, or
reports an old completed step as a currently running Ollama operation.
"""
from __future__ import annotations
import json
from pathlib import Path
import sqlite3
import time
from urllib.parse import quote

from suryadev_liveops import _safe_read


def book_learning_snapshot(root, *, now=None):
    root = Path(root).expanduser().resolve()
    now = time.time() if now is None else float(now)
    result = {
        "available":True, "indexed":0, "approved":0,
        "pending":0, "reading":0, "completed":0, "failed":0,
        "lines_processed":0, "lines_total":0, "model_seconds":0.0,
        "visual_items_examined":0, "visual_books_finished":0,
        "brahmagyan_candidate_receipts":0, "rishi_verified":False,
        "books":[], "activity":{"state":"not_started", "active":False},
        "plan_present":False,
    }
    plan_path = root / "book-plan.json"
    if plan_path.is_file():
        result["plan_present"] = True
        try:
            if plan_path.stat().st_size > 65536:
                raise ValueError("approved book plan is oversized")
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            if not isinstance(plan,dict) or plan.get("schema") != "suryadev.book-plan.v1" or not isinstance(plan.get("books"),list):
                raise ValueError("approved book plan schema is invalid")
            if len(plan["books"]) > 100:
                raise ValueError("too many approved books")
            hashes = {entry.get("sha256") for entry in plan["books"]
                      if isinstance(entry,dict) and isinstance(entry.get("sha256"),str)
                      and len(entry["sha256"]) == 64}
            result["approved"] = len(hashes)
        except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
            result["plan_error"] = type(exc).__name__ + ": " + str(exc)[:130]
    dbfile = root / "book-learning.sqlite3"
    if dbfile.is_file():
        try:
            uri = "file:" + quote(dbfile.as_posix(),safe="/:") + "?mode=ro"
            con = sqlite3.connect(uri,uri=True,timeout=2)
            try:
                # Query only existing book ledger structures, not production
                # jobs; preserve exact source/model identities per book.
                books = con.execute(
                    "SELECT id,title,lines_total,source_sha256 FROM books "
                    "ORDER BY imported_at DESC LIMIT 100").fetchall()
                session_rows = con.execute(
                    "SELECT book_id,mode,next_ordinal,COALESCE(last_error,''),"
                    "updated_at FROM book_sessions ORDER BY updated_at DESC").fetchall()
                history = {}
                for bid,mode,next_line,error,updated_at in session_rows:
                    if mode.startswith("ollama:"):
                        history.setdefault(bid,(mode,next_line,error,updated_at))
                present = {x[0] for x in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
                visuals = dict(con.execute(
                    "SELECT book_id,COUNT(*) FROM book_visuals GROUP BY book_id")
                    ) if "book_visuals" in present else {}
                visual_done = {r[0] for r in con.execute(
                    "SELECT book_id FROM book_visual_runs"
                    )} if "book_visual_runs" in present else set()
                receipts = dict(con.execute(
                    "SELECT book_id,COUNT(*) FROM book_delivery GROUP BY book_id")
                    ) if "book_delivery" in present else {}
                selected_models = []
                for bid,title,total,digest in books:
                    read = history.get(bid)
                    if read:
                        selected_models.append((bid,read[0]))
                    processed = min(total,max(0,int(read[1])-1)) if read else 0
                    complete = bool(read and processed>=total)
                    failure = bool(read and read[2])
                    if failure: status="error"
                    elif complete: status="complete"
                    elif processed: status="reading"
                    else: status="indexed"
                    item = {
                        "book_id":bid, "title":title, "lines_total":total,
                        "lines_processed":processed, "remaining_lines":total-processed,
                        "progress_percent":round(100*processed/total,1) if total else 0.0,
                        "status":status,"model":read[0][7:] if read else None,
                        "last_error":read[2] if failure else "",
                        "visual_items_examined":visuals.get(bid,0),
                        "visual_inventory_finished":bid in visual_done,
                        "brahmagyan_candidate_receipts":receipts.get(bid,0),
                        "source_sha256":digest,
                    }
                    result["books"].append(item)
                    result["indexed"]+=1
                    result["lines_processed"]+=processed
                    result["lines_total"]+=total
                    result["visual_items_examined"]+=item["visual_items_examined"]
                    result["visual_books_finished"]+=int(item["visual_inventory_finished"])
                    result["brahmagyan_candidate_receipts"]+=item["brahmagyan_candidate_receipts"]
                    if complete:result["completed"]+=1
                    elif failure:result["failed"]+=1
                    elif processed:result["reading"]+=1
                    else:result["pending"]+=1
                # Keep elapsed time aligned to the SAME most-recent local
                # model session used for processed-line counters, rather than
                # double-counting a second model's reread of the same book.
                model_time = sum(float(con.execute(
                    "SELECT COALESCE(SUM(elapsed_seconds),0) FROM book_journal "
                    "WHERE book_id=? AND mode=?", pair).fetchone()[0])
                    for pair in selected_models)
                result["model_seconds"]=round(model_time,2)
            finally:
                con.close()
        except (OSError,sqlite3.Error,ValueError,TypeError) as exc:
            result["available"]=False
            result["error"]="Book ledger temporarily unavailable: "+type(exc).__name__
    activity = _safe_read(root,"book-continuity-runtime.json",max_bytes=8192)
    state = str(activity.get("state") or "not_started")
    updated = activity.get("updated_at")
    try:
        age=now-float(updated)
    except (ValueError,TypeError,OverflowError):
        age=float("inf")
    # An in-flight observation can legitimately take >1 minute on a laptop.
    active=state in ("book_reading_in_progress","book_visual_in_progress") and 0<=age<=240
    result["activity"]={
        "state":state,
        "active":active,
        "book_id":str(activity.get("book_id") or ""),
        "title":str(activity.get("title") or "")[:240],
        "model":str(activity.get("model") or "")[:100],
        "processed_lines":activity.get("processed_lines"),
        "total_lines":activity.get("total_lines"),
        "error":str(activity.get("error") or "")[:180],
        "updated_at":updated,
        "stale":bool(updated and age>240),
    }
    return result
