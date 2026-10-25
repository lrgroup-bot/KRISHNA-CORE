"""Read-only, source-aware task history and evidence inspection for the local UI.

No claims of complete video, PDF or website coverage are inferred from a 'done' job.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date as CalendarDate
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


def list_tasks(db, *, offset=0, limit=25, q="", status="", kind="", day=""):
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
    if day:
        day = validate_day(day)
    clauses, args = [], []
    if day:
        clauses.append(
            "(date(j.created,'unixepoch','localtime')=? "
            "OR date(f.created,'unixepoch','localtime')=? "
            "OR (j.status IN ('running','done','failed') "
            "AND date(j.updated,'unixepoch','localtime')=?))"
        )
        args.extend((day, day, day))
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


def validate_day(value):
    """Accept only canonical ISO local calendar dates, never arbitrary SQL."""
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("date must be YYYY-MM-DD")
    try:
        parsed = CalendarDate.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("invalid calendar date") from exc
    if parsed.isoformat() != value:
        raise ValueError("date must be YYYY-MM-DD")
    return value


_DAILY_SQL = """
WITH activity AS (
  SELECT date(created,'unixepoch','localtime') day,
         1 assigned,0 completed,0 failed,0 findings FROM jobs
  UNION ALL
  SELECT date(updated,'unixepoch','localtime'),0,1,0,0
    FROM jobs WHERE status='done'
  UNION ALL
  SELECT date(updated,'unixepoch','localtime'),0,0,1,0
    FROM jobs WHERE status='failed'
  UNION ALL
  SELECT date(created,'unixepoch','localtime'),0,0,0,1 FROM findings
)
SELECT day,SUM(assigned) AS assigned,SUM(completed) AS completed,
       SUM(failed) AS failed,SUM(findings) AS findings
FROM activity
WHERE day IS NOT NULL
GROUP BY day
"""


def diary_days(db, limit=180):
    """Daily activity by laptop-local calendar date, newest first.

    Completed/failed are current terminal states dated by last update,
    not an immutable lifecycle event log. Finding dates are recorded independently.
    """
    limit = max(1, min(int(limit), 1000))
    rows = db.execute(_DAILY_SQL + " ORDER BY day DESC LIMIT ?", (limit,))
    return [{"date": day, "assignments": assigned,
             "completed": completed, "failed": failed, "findings": findings}
            for day, assigned, completed, failed, findings in rows]


def diary_day(db, day):
    """Selected-day totals; usable for older dates outside the recent diary list."""
    day = validate_day(day)
    row = db.execute(
        "SELECT day,assigned,completed,failed,findings FROM ("
        + _DAILY_SQL + ") WHERE day=?", (day,)
    ).fetchone()
    if row is None:
        return {"date": day, "assignments": 0, "completed": 0,
                "failed": 0, "findings": 0}
    d, assigned, completed, failed, findings = row
    return {"date": d, "assignments": assigned,
            "completed": completed, "failed": failed, "findings": findings}


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
                    "PDF text-page coverage is recorded separately below when provenance is available; scanned images, diagrams, equations, comprehension and entire-document visual review remain unverified."
                    if task["kind"] == "pdf" else
                    "The web worker extracts a capped text sample; full-page coverage is not verified."
                    if task["kind"] == "website" else
                    "Whole-source coverage was not verified.")},
        {"name": "BRAHMAGYAN / Rishi acceptance", "state": "pending",
         "detail": "No verified acceptance receipt from KRISHNA is recorded."},
    ]
    return stages


def _queue_diagnosis(root):
    """Explain queued work without pretending to inspect the laptop process.

    A stale heartbeat proves only that no *recent heartbeat* was recorded;
    an unrelated or stuck process could still be holding the worker lock.
    """
    from suryadev_liveops import _safe_read
    record = _safe_read(root, "worker-runtime.json")
    heartbeat = record.get("heartbeat_at")
    try:
        poll_interval = max(10, min(3600, int(record.get("interval_seconds", 60))))
        age = time.time() - float(heartbeat)
    except (TypeError, ValueError):
        age = float("inf")
        poll_interval = 60
    fresh = 0 <= age < max(180, poll_interval * 3)
    state = record.get("state", "offline") if fresh else "offline"
    if state == "offline":
        return {"worker_state": "offline",
                "message": ("No recent SURYADEV learning-worker heartbeat. "
                            "The dashboard is read-only and cannot execute queued tasks. "
                            "Check for a stopped or stalled mission before launching another worker.")}
    if state == "stopped":
        return {"worker_state": "stopped",
                "message": ("The learning worker last reported stopped. "
                            "Run either the mission or the worker, not both.")}
    if state == "paused":
        why = str(record.get("reason") or "Resource admission paused")[:160]
        return {"worker_state": "paused",
                "message": "Worker paused new tasks: " + why}
    return {"worker_state": state,
            "message": ("Worker heartbeat present (" + state +
                        "), but this assignment is still queued. "
                        "It will be claimed when scheduling and hardware admission allow it.")}


def task_detail(db, root, job_id):
    if not isinstance(job_id, int) or job_id < 1:
        raise ValueError("invalid task ID")
    row = db.execute(_QUERY + " WHERE j.id=? ORDER BY f.id DESC LIMIT 1", (job_id,)).fetchone()
    if row is None:
        return None
    task = _row_to_task(row)
    state = _evidence_state(root, task["sha256"])
    task["evidence_state"] = state
    provenance = {}
    has_receipts = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='job_provenance'"
    ).fetchone()
    if has_receipts:
        record = db.execute(
            "SELECT report_json FROM job_provenance WHERE job_id=?", (job_id,)
        ).fetchone()
        if record:
            try:
                provenance = json.loads(record[0])
            except (TypeError, ValueError):
                provenance = {}
    task["coverage"] = provenance
    task["publisher_recovery"] = None
    has_publisher = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='publisher_caption_recoveries'"
    ).fetchone()
    if has_publisher:
        entry = db.execute(
            "SELECT transcript_url,recovered_at,previous_error,"
            "previous_failed_at,evidence_sha256 "
            "FROM publisher_caption_recoveries WHERE job_id=?", (job_id,)
        ).fetchone()
        if entry:
            task["publisher_recovery"] = {
                "transcript_url":entry[0], "recovered_at":entry[1],
                "previous_error":entry[2],
                "previous_failed_at":entry[3],
                "evidence_sha256":entry[4],
                "youtube_extraction_success":False,
                "video_visuals_verified":False,
            }
    # These flags describe local acquisition only. A saved hash plus every
    # extractable PDF text page is not a complete multimodal source review.
    pages_total = provenance.get("pages_total")
    task["text_extraction_verified"] = (
        task["kind"] == "pdf" and task["status"] == "done" and
        state == "verified" and type(pages_total) is int and pages_total > 0 and
        provenance.get("pages_extracted") == pages_total and
        not provenance.get("pages_missing_text") and
        provenance.get("extraction_completed") is True
    )
    task["visual_coverage_verified"] = False
    task["comprehension_verified"] = False
    task["rishi_exam_verified"] = False
    task["steps"] = _checklist(task, state)
    task["queue_diagnosis"] = _queue_diagnosis(root) if task["status"] == "queued" else None
    if task["queue_diagnosis"]:
        for step in task["steps"]:
            if step["name"] == "Worker execution":
                step["detail"] = task["queue_diagnosis"]["message"]
                break
    if provenance.get("pages_total"):
        task["steps"].insert(4, {
            "name": "PDF page text extraction",
            "state": "done" if task["text_extraction_verified"] else "unverified",
            "detail": f"{provenance.get('pages_extracted', 0)}/{provenance['pages_total']} pages with text. "
                      "PDF diagrams, images and visual details require separate review."
        })
    if task["publisher_recovery"]:
        task["steps"].insert(4, {
            "name":"Approved publisher subtitle recovery",
            "state":"done" if state == "verified" else "blocked",
            "detail":"Publisher-hosted timestamped text was saved with SHA-256 evidence. "
                     "The original YouTube extraction failed; video visuals, "
                     "uncaptioned speech and exact audiovisual equivalence remain unverified."
        })
    if provenance.get("cue_count"):
        task["steps"].insert(4, {
            "name": "YouTube timed caption processing",
            "state": "done",
            "detail": f"{provenance['cue_count']} timed cues processed; last cue "
                      f"{provenance.get('last_cue_seconds')} seconds. "
                      "Visual content and uncaptained speech are not verified."
        })
    if provenance.get("chunks_total"):
        task["steps"].insert(5, {
            "name": "Text chunks presented to local model",
            "state": "done" if provenance.get("chunks_total") == provenance.get("chunks_summarized")
                     else "unverified",
            "detail": f"{provenance.get('chunks_summarized')}/{provenance.get('chunks_total')} "
                      "extracted text chunks processed. Factual validity is not certified."
        })
    task["complete_verified"] = False  # No coverage or approval receipts currently exist.
    task["stale_running"] = task["status"] == "running" and (
        time.time() - task["updated"] > 7200)
    return task
