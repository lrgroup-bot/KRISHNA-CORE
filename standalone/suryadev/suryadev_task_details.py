"""Read-only, source-aware task history and evidence inspection for the local UI.

No claims of complete video, PDF or website coverage are inferred from a 'done' job.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import time

from suryadev_sources import source_kind

MAX_PAGE_SIZE = 50


def _row_to_task(row):
    (job_id, url, status, created, updated, error, finding_id, title,
     summary, sha256, method, excerpt, learned_at) = row
    return {
        "id": job_id, "url": url, "kind": source_kind(url),
        "status": status, "created": created, "updated": updated,
        "error": error or "", "finding_id": finding_id,
        "title": title or "", "summary": summary or "",
        "sha256": sha256 or "", "method": method or "",
        "excerpt": excerpt or "", "learned_at": learned_at,
    }


_QUERY = (
    "SELECT j.id,j.url,j.status,j.created,j.updated,j.error,"
    "f.id,f.title,f.summary,f.sha256,f.summary_method,f.excerpt,f.created "
    "FROM jobs j LEFT JOIN findings f ON f.job_id=j.id "
)


def list_tasks(db, *, offset=0, limit=25, q="", status="", kind=""):
    """Return all historical tasks through bounded, filtered pagination."""
    offset = max(0, min(int(offset), 1_000_000))
    limit = max(1, min(int(limit), MAX_PAGE_SIZE))
    q = str(q).strip().casefold()[:120]
    status = str(status).strip().lower()
    kind = str(kind).strip().lower()
    if status not in ("", "queued", "running", "done", "failed"):
        raise ValueError("invalid task status")
    if kind not in ("", "youtube", "pdf", "website", "other"):
        raise ValueError("invalid source kind")
    clauses, args = [], []
    if status:
        clauses.append("j.status=?")
        args.append(status)
    if q:
        clauses.append("(instr(lower(j.url),?)>0 OR instr(lower(COALESCE(f.title,'')),?)>0 "
                       "OR CAST(j.id AS TEXT)=?)")
        args.extend((q, q, q))
    sql = _QUERY + (" WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY j.id DESC"
    # Categorization is based on source URL rather than a database schema migration.
    result = []
    seen = set()
    for row in db.execute(sql, args):
        task = _row_to_task(row)
        if kind and task["kind"] != kind:
            continue
        # Defend against unexpected duplicate finding rows without repeating tasks.
        if task["id"] not in seen:
            seen.add(task["id"])
            result.append(task)
    total = len(result)
    fields = ("id", "url", "kind", "status", "created", "updated", "error",
              "finding_id", "title", "method")
    return {"total": total, "offset": offset, "limit": limit,
            "has_more": offset + limit < total,
            "tasks": [{k: t[k] for k in fields} for t in result[offset:offset + limit]]}


def _evidence_state(root, sha256):
    if not sha256:
        return "not_recorded"
    if len(sha256) != 64 or any(c not in "0123456789abcdef" for c in sha256):
        return "invalid_digest"
    path = Path(root).resolve() / "evidence" / sha256[:2] / (sha256 + ".txt")
    if not path.is_file():
        return "missing"
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
    return "verified" if digest.hexdigest() == sha256 else "hash_mismatch"


def _checklist(task, evidence_state):
    status = task["status"]
    has_finding = bool(task["finding_id"])
    method = task["method"]
    stages = [
        {"name": "Task registered", "state": "done",
         "detail": "Recorded in the local SQLite assignment ledger."},
        {"name": "Worker execution", "state":
         "done" if status == "done" else ("blocked" if status == "failed" else "pending"),
         "detail": {"done": "Worker marked this task done.",
                    "failed": "Worker failed; review the recorded error.",
                    "running": "Worker has started; completion is pending.",
                    "queued": "Waiting in the worker queue."}.get(status, "Unknown worker status.")},
        {"name": "Source evidence integrity",
         "state": "done" if evidence_state == "verified" else
                  ("blocked" if evidence_state in ("missing", "hash_mismatch", "invalid_digest") else "pending"),
         "detail": {
             "verified": "Saved evidence file exists and its SHA-256 matches the finding.",
             "missing": "Finding exists but the evidence file is missing.",
             "hash_mismatch": "Stored evidence does not match the recorded hash.",
             "invalid_digest": "Recorded digest is invalid.",
             "not_recorded": "No finding/evidence digest has been recorded."
         }[evidence_state]},
        {"name": "Learning result saved",
         "state": "done" if has_finding else ("blocked" if status == "failed" else "pending"),
         "detail": ("Method: " + method) if has_finding else "No learning finding exists for this task."},
        {"name": "Entire source processed and verified", "state": "unverified",
         "detail": ("Full video transcript timeline and visual coverage are not tracked."
                    if task["kind"] == "youtube" else
                    "Full PDF page coverage is not tracked; PDF ingestion is not implemented in the web worker."
                    if task["kind"] == "pdf" else
                    "The web worker extracts a capped text sample; full-page coverage is not verified."
                    if task["kind"] == "website" else
                    "Whole-source coverage was not verified.")},
        {"name": "BRAHMAGYAN / Rishi acceptance", "state": "pending",
         "detail": "No verified acceptance receipt from KRISHNA is recorded."},
    ]
    return stages


def task_detail(db, root, job_id):
    if not isinstance(job_id, int) or job_id < 1:
        raise ValueError("invalid task ID")
    row = db.execute(_QUERY + " WHERE j.id=? ORDER BY f.id DESC LIMIT 1", (job_id,)).fetchone()
    if row is None:
        return None
    task = _row_to_task(row)
    state = _evidence_state(root, task["sha256"])
    task["evidence_state"] = state
    task["steps"] = _checklist(task, state)
    task["complete_verified"] = False  # No coverage or approval receipts currently exist.
    task["stale_running"] = task["status"] == "running" and (
        time.time() - task["updated"] > 7200)
    return task
