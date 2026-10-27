"""Phase 1: evidence-only audit of standalone SURYADEV video learning.

No network calls, browser launch, source approval, model inference, worker
lock, Core pairing or changes to historical video job records. "Playback"
alone can never pass a complete-learning acceptance gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from suryadev_feeder import read_plan
from suryadev_video_review import VideoReview
from suryadev_youtube_audit import observer_jobs
from suryadev_trial_limits import video_job_id

ATTEMPT_FILE = "video-observer-attempts.json"


def _safe_json(path, max_bytes=131072):
    if not path.is_file() or path.is_symlink() or path.stat().st_size > max_bytes:
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError,ValueError,UnicodeError):
        return None
    return value if isinstance(value,dict) else None


def assess_video(record, *, attempted, has_runtime, historical):
    """Classify without confusing a last clock position with coverage."""
    reasons = []
    if attempted or has_runtime or historical not in (None,"QUEUED_FOR_REVIEW"):
        reasons.append("previous_attempt_or_evidence_protected")
    if record:
        stop = record.get("stop_reason")
        if stop:
            reasons.append("observation_stopped:"+str(stop))
        if record.get("legacy_incomplete_evidence"):
            reasons.append("stalled_legacy_receipt_not_acceptance")
        if record.get("video_ended") is not True:
            reasons.append("video_end_not_observed")
        if record.get("bundle_validated") is not True:
            reasons.append("canonical_bundle_not_validated")
        if not record.get("captured_caption_lines"):
            reasons.append("caption_lines_missing")
        if not record.get("visual_frame_samples"):
            reasons.append("visual_frame_samples_missing")
        if not record.get("learning_candidate_chunks"):
            reasons.append("candidate_learning_chunks_missing")
    elif has_runtime:
        reasons.append("runtime_directory_without_indexed_observer_receipt")
    if not (record and record.get("caption_completeness_verified") is True):
        reasons.append("caption_completeness_unverified")
    if not (record and record.get("full_audio_visual_coverage_verified") is True):
        reasons.append("full_audio_visual_coverage_unverified")
    if not (record and record.get("brahmagyan_exam_verified") is True):
        reasons.append("independent_comprehension_unverified")
    blocking=attempted or has_runtime or historical not in (None,"QUEUED_FOR_REVIEW")
    return {
        "status":"HISTORICAL_INCOMPLETE" if blocking else "FRESH_APPROVED_NOT_STARTED",
        "eligible_for_first_observation":not blocking,
        "observation_status":record.get("status") if record else None,
        "stop_reason":record.get("stop_reason") if record else None,
        "source_duration_seconds":record.get("source_duration_seconds") if record else None,
        "last_playback_position_seconds":record.get("last_playback_position_seconds") if record else None,
        "caption_lines":record.get("captured_caption_lines") if record else None,
        "visual_frame_samples":record.get("visual_frame_samples") if record else None,
        "candidate_chunks":record.get("learning_candidate_chunks") if record else None,
        "media_http_errors":(
            (record.get("garudanetra_media") or {}).get("media_http_errors", [])[:20]
            if record and isinstance(record.get("garudanetra_media"),dict) and
               isinstance(record["garudanetra_media"].get("media_http_errors"),list)
            else []),
        "complete_learning_verified":False,
        "reasons":reasons,
    }


def _video_recovery_diagnosis(rows, *, journal_safe):
    """Read-only classification of observed delivery/coverage failures.

    Never assumes a playback provider bypass, silently schedules a retry,
    or converts a partial observer bundle into learned/verified content.
    """
    http_403, media_interruptions, missing_captions = 0, 0, 0
    interrupted = {"media_unloaded_after_playback", "content_playback_stalled",
                   "media_error", "video_element_replaced",
                   "browser_snapshot_unavailable"}
    for entry in rows:
        if entry.get("stop_reason") in interrupted:
            media_interruptions += 1
        if entry.get("caption_lines") == 0:
            missing_captions += 1
        for request in entry.get("media_http_errors", []):
            if isinstance(request, dict) and request.get("status") == 403:
                http_403 += 1
    fresh=sum(bool(x["eligible_for_first_observation"]) for x in rows)
    reasons=[]
    if not journal_safe:
        reasons.append("attempt_history_invalid")
    elif not fresh:
        reasons.append("no_fresh_approved_video")
    if http_403:
        reasons.append("youtube_media_http_403_observed")
    if media_interruptions:
        reasons.append("incomplete_media_playback_observed")
    if missing_captions:
        reasons.append("zero_caption_lines_recorded")
    if not rows:
        reasons.append("no_approved_video_urls")
    return {
        "schema":"suryadev.youtube-recovery.v1",
        "safe_to_autoreplay_attempted":False,
        "automatic_retry_authorized":False,
        "fresh_approved_ready":fresh if journal_safe else None,
        "media_http_403_events":http_403,
        "media_interrupted_videos":media_interruptions,
        "zero_caption_videos":missing_captions,
        "reasons":reasons,
        "next_action":(
            "Inspect damaged attempt history; do not overwrite/replay receipts."
            if not journal_safe else
            "Start only new exact previously approved, unattempted videos in the current worker."
            if fresh else
            "The existing one-time selection is exhausted. Another generation of "
            "explicitly authorized, fresh approved lessons is needed; merely adding URLs "
            "does not reset the frozen selection. A separately audited retry of failed "
            "attempts requires separate operator authorization and retained evidence."
        ),
        "provider_note":(
            "Googlevideo HTTP 403 was observed. Check normal service availability and "
            "media provider restrictions; no bypass or successful playback is implied."
            if http_403 else
            "There is no recorded media HTTP 403 in these indexed observer receipts."
        ),
        "learning_verified":False,
    }


def phase1(root):
    root=Path(root).expanduser().resolve(strict=True)
    plan_path=root/"learning-plan.json"
    plan=read_plan(plan_path)
    urls=list(dict.fromkeys(VideoReview._approved_videos(plan["approved_urls"])))
    journal=_safe_json(root/ATTEMPT_FILE)
    journal_exists=(root/ATTEMPT_FILE).exists()
    journal_safe=(not journal_exists or
        (journal is not None and journal.get("schema")=="suryadev.video-attempts.v1"
         and isinstance(journal.get("job_ids"),list)
         and all(isinstance(x,str) for x in journal["job_ids"])))
    attempted=set(journal.get("job_ids",[])) if journal_safe and journal else set()
    state=_safe_json(root/"video-review"/"runtime"/"worker-state.json")
    raw_jobs=state.get("jobs",{}) if isinstance(state,dict) else {}
    history=raw_jobs if isinstance(raw_jobs,dict) else {}
    observations={row["job_id"]:row for row in observer_jobs(root,limit=200)}
    rows=[]
    for url in urls:
        jid=video_job_id(url)
        past=history.get(jid)
        historical=past.get("status") if isinstance(past,dict) else "UNKNOWN_STATE" if past else None
        has_runtime=(root/"video-review"/"runtime"/"jobs"/jid).exists()
        outcome=assess_video(observations.get(jid),attempted=jid in attempted or
                            not journal_safe,has_runtime=has_runtime,
                            historical=historical)
        rows.append({"job_id":jid,**outcome})
    fresh=sum(r["eligible_for_first_observation"] for r in rows)
    historical_count=len(rows)-fresh
    return {
        "schema":"suryadev.standalone.youtube-phase1.v1",
        "phase":"youtube",
        "core_required":False,
        "core_contacted":False,
        "no_mutations":True,
        "approved_videos":len(rows),
        "fresh_eligible_videos":fresh if journal_safe else None,
        "historical_videos_protected":historical_count,
        "attempt_journal_valid":journal_safe,
        "full_learning_verified":False,
        "result": ("BLOCKED_INVALID_ATTEMPT_HISTORY" if not journal_safe else
                   "READY_FOR_FRESH_APPROVED_OBSERVATION" if fresh else
                   "BLOCKED_NO_NEW_APPROVED_VIDEO"),
        "acceptance_requirements":[
            "verified_content_progression_and_end_without_stall",
            "caption_or_permitted_audio_coverage_proven_complete",
            "visual_source_coverage_and_frame_integrity",
            "source_grounded_learning_chunks_with_provenance",
            "independent_closed_book_comprehension_verification",
        ],
        "videos":rows,
        "recovery":_video_recovery_diagnosis(rows,journal_safe=journal_safe),
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description="Read-only standalone YouTube learning Phase 1 acceptance gate")
    parser.add_argument("--data",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        report=phase1(args.data)
    except (OSError,ValueError,TypeError) as exc:
        print(json.dumps({"result":"BLOCKED_READ_ERROR",
            "error":type(exc).__name__+": "+str(exc)[:240]},indent=2))
        return 2
    print(json.dumps(report,indent=2,ensure_ascii=False))
    return 0 if report["result"]=="READY_FOR_FRESH_APPROVED_OBSERVATION" else 3


if __name__=="__main__":
    raise SystemExit(main())
