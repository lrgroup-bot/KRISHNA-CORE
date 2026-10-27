"""Read-only, source-grounded idle diagnosis for the AI Learner control room."""
from __future__ import annotations

import time
from pathlib import Path

from suryadev_feeder import read_plan
from suryadev_liveops import _safe_read
from suryadev_video_review import VideoReview
from suryadev_trial_limits import video_job_id, VIDEO_FILE

FRESH_SECONDS = 90


def snapshot(root, app, *, control=None, now=None):
    """No source approvals, queue writes, video playback, or worker launches."""
    root = Path(root).resolve()
    now = time.time() if now is None else float(now)
    control = control if isinstance(control, dict) else {}
    review = VideoReview(root, app)
    errors = []
    if (root/"learning-plan.json").is_file():
        try:
            plan = read_plan(root/"learning-plan.json")
        except (OSError,ValueError,TypeError) as exc:
            plan = None
            errors.append("Invalid approved source plan: "+type(exc).__name__)
    else:
        plan = None
        errors.append("No approved learning-plan.json")
    approved = review._approved_videos(plan["approved_urls"]) if plan else []
    approved_ids = {video_job_id(url) for url in approved}
    statuses = {row["job_id"]: row.get("status")
                for row in review.snapshot_unlocked_jobs()
                if isinstance(row,dict) and isinstance(row.get("job_id"),str)}
    attempts = _safe_read(root,"video-observer-attempts.json",max_bytes=65536)
    if (root/"video-observer-attempts.json").exists() and (
            attempts.get("schema")!="suryadev.video-attempts.v1"
            or not isinstance(attempts.get("job_ids"),list)):
        errors.append("Video attempt journal invalid; no replay permitted")
        safe_history = False
        attempted = set()
    else:
        safe_history = True
        attempted = {x for x in attempts.get("job_ids",[]) if isinstance(x,str)}
    fresh = set()
    for jid in approved_ids:
        evidence = review.root/"runtime"/"jobs"/jid
        if (safe_history and jid not in attempted and
                (jid not in statuses or statuses[jid]=="QUEUED_FOR_REVIEW")
                and not evidence.exists()):
            fresh.add(jid)
    selection = _safe_read(root, VIDEO_FILE, max_bytes=8192)
    selected_ids = selection.get("job_ids")
    valid_selection = (not (root/VIDEO_FILE).exists() or (
        isinstance(selection,dict) and
        selection.get("schema")=="suryadev.video-trial-selection.v1" and
        isinstance(selected_ids,list) and all(isinstance(x,str) for x in selected_ids)))
    if not valid_selection:
        errors.append("Video trial selection invalid; no replacement authorized")
    if not isinstance(selected_ids,list):
        selected_ids=[]
    book_plan = _safe_read(root, "book-plan.json", max_bytes=200000)
    approved_books = (len(book_plan.get("books",[]))
                       if isinstance(book_plan.get("books"),list) else 0)
    book_runtime = _safe_read(root,"book-concurrent-runtime.json",max_bytes=32768)
    book_updated = book_runtime.get("updated_at")
    fresh_book_runtime = (type(book_updated) in (int,float) and
                          0 <= now-float(book_updated) < FRESH_SECONDS)
    book_active = book_runtime.get("active",0)
    book_active = book_active if type(book_active) is int and book_active>=0 else 0
    book_last = _safe_read(root, "book-continuity-runtime.json", max_bytes=8192)
    last_updated = book_last.get("updated_at")
    book_last_fresh = (type(last_updated) in (int,float) and
                       0 <= now-float(last_updated) <= 600)
    book_last_state = str(book_last.get("state") or "") if book_last_fresh else ""
    book_last_error = (str(book_last.get("error") or "")[:180]
                       if book_last_fresh and book_last_state == "book_paused_error" else "")
    capacity = _safe_read(root, "capacity-runtime.json", max_bytes=32768)
    updated = capacity.get("sample_time")
    current_capacity = (type(updated) in (int,float)
                        and 0 <= now-float(updated) < FRESH_SECONDS)
    admitted_slots = (capacity.get("max_total")
                      if current_capacity and type(capacity.get("max_total")) is int else None)
    book_reserved_slots = (capacity.get("reserved_book_slots")
                           if current_capacity and type(capacity.get("reserved_book_slots")) is int
                           else None)
    queued = capacity.get("queued",{}) if current_capacity else {}
    if not isinstance(queued,dict):
        queued={}
    running = bool(control.get("managed_running") or control.get("external_worker_active"))
    reasons = []
    if not running:
        reasons.append("No verified managed or externally locked learning worker; saved runtime may be stale")
    if not plan:
        reasons.append("Approved source plan unavailable")
    if plan and not plan["approved_feeds"] and not any(
            isinstance(queued.get(k),int) and queued[k]>0
            for k in ("website","youtube","pdf")):
        reasons.append("No queued source tasks or approved feeds reported; prior approved URLs may already be processed")
    if not review.auto_enabled():
        reasons.append("Automatic approved-video observation disabled")
    if not approved:
        reasons.append("No approved YouTube watch URLs")
    if (root/VIDEO_FILE).exists() and valid_selection and not selected_ids:
        if fresh:
            reasons.append("Saved video trial selection is empty although unattempted approved videos exist; guarded empty-selection recovery required")
        else:
            reasons.append("Saved video trial selection empty; no eligible unattempted approved videos")
    if approved_books and not fresh_book_runtime:
        reasons.append("Book runtime snapshot is stale; active count cannot establish current reading")
    if approved_books and fresh_book_runtime and book_active == 0:
        reasons.append("Approved books exist but no book task is active")
        if admitted_slots == 0:
            reasons.append("No learning slots admitted by the measured resource/mission guard")
        elif book_reserved_slots == 0:
            reasons.append("No book capacity reserved this worker cycle; check source/video load")
    if book_last_error:
        reasons.append("Last book checkpoint paused: " + book_last_error)
    return {
        "schema":"suryadev.ai-learner-readiness.v1",
        "worker_managed_running":control.get("managed_running") is True,
        "worker_external_lock":control.get("external_worker_active") is True,
        "worker_heartbeat_recent":control.get("worker_heartbeat_recent") is True,
        "approved_urls":len(plan["approved_urls"]) if plan else 0,
        "approved_feed_count":len(plan["approved_feeds"]) if plan else 0,
        "approved_videos":len(approved_ids),
        "previously_attempted_videos":len(approved_ids & attempted),
        "unattempted_approved_videos":len(fresh) if safe_history else None,
        "selected_videos":len(set(selected_ids)&approved_ids) if valid_selection else None,
        "selection_empty_recovery_possible":bool(valid_selection and
            (root/VIDEO_FILE).exists() and not selected_ids and fresh and safe_history),
        "automatic_video_enabled":review.auto_enabled(),
        "approved_books":approved_books,
        "worker_model":control.get("managed_model"),
        "learning_role":control.get("learning_role"),
        "admitted_slots":admitted_slots,
        "reserved_book_slots":book_reserved_slots,
        "book_last_state":book_last_state or None,
        "book_last_error":book_last_error or None,
        "book_runtime_fresh":fresh_book_runtime,
        "reported_active_books":book_active if fresh_book_runtime else None,
        "capacity_fresh":current_capacity,
        "reasons":reasons,
        "errors":errors,
        "understanding_verified":False,
        "rishi_exam_verified":False,
    }
