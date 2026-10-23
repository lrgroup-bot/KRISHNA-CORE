"""Read-only, evidence-first audit of the TWO distinct SURYADEV YouTube lanes.

A caption extraction is never described as watching. A browser playback
timestamp is never described as time watched, complete visual coverage, or
Rishi mastery. This module does not start, retry or modify any worker.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit

from suryadev_sources import source_kind

_ID = re.compile(r"[A-Za-z0-9_-]{1,120}\Z")
MAX_REPORT_BYTES = 128_000
MAX_BUNDLE_BYTES = 3_000_000


def _read(path, max_bytes):
    path = Path(path)
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > max_bytes:
            return {}
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _seconds(value):
    try:
        number = float(value)
        return round(number, 2) if math.isfinite(number) and 0 <= number <= 1_000_000 else None
    except (ValueError, TypeError, OverflowError):
        return None


def _epoch(value):
    try:
        number = float(value)
        return number if math.isfinite(number) and 1_000_000_000 <= number <= 4_000_000_000 else None
    except (ValueError, TypeError, OverflowError):
        return None


def _short(value, chars=500):
    return str(value or "").strip()[:chars]


def _provenance(raw):
    if not raw or len(raw) > 65_536:
        return {}
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except (ValueError, TypeError):
        return {}


def caption_jobs(db, limit=30):
    """Read SQLite timings/summary method, without treating 'done' as mastery."""
    limit = max(1, min(int(limit), 50))
    rows = db.execute(
        "SELECT j.id,j.url,j.status,j.error,f.title,f.summary,f.summary_method,"
        "p.report_json,t.acquisition_seconds,t.summary_phase_seconds,"
        "t.elapsed_seconds,t.outcome "
        "FROM jobs j LEFT JOIN findings f ON f.job_id=j.id "
        "LEFT JOIN job_provenance p ON p.job_id=j.id "
        "LEFT JOIN job_timing t ON t.job_id=j.id "
        "WHERE lower(j.url) LIKE '%youtu%' "
        "ORDER BY j.id DESC LIMIT ?", (max(100,limit * 8),)
    )
    seen, out = set(), []
    for (jid,url,status,error,title,summary,method,raw,acquisition,
         summary_seconds,elapsed,outcome) in rows:
        if jid in seen or source_kind(url) != "youtube":
            continue
        seen.add(jid)
        coverage = _provenance(raw)
        out.append({
            "job_id":jid, "url":url, "status":status, "title":_short(title,240),
            "error":_short(error,260),
            "video_duration_seconds":_seconds(coverage.get("duration_seconds")),
            "caption_cues":coverage.get("cue_count") if type(coverage.get("cue_count")) is int else None,
            "first_caption_seconds":_seconds(coverage.get("first_cue_seconds")),
            "last_caption_seconds":_seconds(coverage.get("last_cue_seconds")),
            "long_caption_gaps":len(coverage.get("long_uncaptioned_gaps") or []),
            "caption_language":_short(coverage.get("caption_language"),12),
            "acquisition_wall_seconds":_seconds(acquisition),
            "analysis_wall_seconds":_seconds(summary_seconds),
            "total_wall_seconds":_seconds(elapsed),
            "analysis_method":_short(method,100),
            "analysis_coverage":_short(coverage.get("summary_coverage"),100),
            "source_characters":coverage.get("source_characters"),
            "chunks_total":coverage.get("chunks_total"),
            "chunks_summarized":coverage.get("chunks_summarized"),
            "what_extracted_or_summarized":_short(summary,1600),
            "youtube_video_watched":False,
            "full_audio_visual_coverage_verified":False,
            "brahmagyan_exam_verified":False,
            "outcome":outcome or status,
        })
        if len(out) >= limit:
            break
    return out


def observer_jobs(root, limit=30):
    """Read canonical adapter's post-run bundle and live playback receipt."""
    root = Path(root).resolve() / "video-review"
    inbox = root / "approved-inbox"
    runtime = root / "runtime" / "jobs"
    if inbox.is_symlink() or runtime.is_symlink() or not inbox.is_dir():
        return []
    paths = sorted(inbox.glob("*.json"), key=lambda p:p.name, reverse=True)
    out = []
    for file in paths[:200]:
        jid = file.stem
        if not _ID.fullmatch(jid):
            continue
        job = _read(file, 4096)
        if job.get("job_id") != jid or job.get("kind") != "video_research":
            continue
        directory = runtime / jid
        if directory.is_symlink():
            continue
        report = _read(directory / "worker-report.json",MAX_REPORT_BYTES)
        bundle = _read(directory / "learning-bundle.json",MAX_BUNDLE_BYTES)
        playback = _read(directory / "playback-speed.json",8192)
        session = bundle.get("session") if isinstance(bundle.get("session"),dict) else {}
        transcript = bundle.get("transcript") if isinstance(bundle.get("transcript"),dict) else {}
        chunks = bundle.get("learning_chunks") if isinstance(bundle.get("learning_chunks"),list) else []
        visuals = bundle.get("visual_evidence") if isinstance(bundle.get("visual_evidence"),list) else []
        actual_chunks = [c for c in chunks if isinstance(c,dict)]
        started, ended = _epoch(session.get("started_at")),_epoch(session.get("ended_at"))
        elapsed = round(ended-started,2) if started is not None and ended is not None and ended >= started else None
        previews = [{
            "topic":_short(c.get("topic"),160),
            "start_seconds":_seconds(c.get("start_seconds")),
            "end_seconds":_seconds(c.get("end_seconds")),
            "candidate_text":_short(c.get("text"),550),
            "evidence_status":_short(c.get("evidence_status"),60),
        } for c in actual_chunks[:5]]
        out.append({
            "job_id":jid, "url":_short(job.get("target"),2048),
            "status":_short(report.get("status") or "pending_or_running",70),
            "title":_short((bundle.get("source") or {}).get("title")
                           if isinstance(bundle.get("source"),dict) else "",240),
            "wall_clock_seconds":elapsed,
            # This is currentTime, NOT watched time or fraction validated.
            "last_playback_position_seconds":_seconds(session.get("watched_seconds"))
                if session else _seconds(playback.get("video_seconds")),
            "source_duration_seconds":_seconds(session.get("source_duration_seconds")),
            "video_ended":session.get("video_ended") is True,
            "adaptive_playback":session.get("adaptive_playback"),
            "four_x_observed":session.get("four_x_observed") is True,
            "live_observed_playback_rate":_seconds(playback.get("observed_rate")),
            "caption_or_asr_source":_short(transcript.get("source") or "not_reported",70),
            "captured_caption_lines":transcript.get("line_count")
                if type(transcript.get("line_count")) is int else None,
            "learning_candidate_chunks":len(actual_chunks),
            "visual_frame_samples":len([x for x in visuals if isinstance(x,dict)]),
            "what_was_collected":previews,
            "bundle_validated":report.get("bundle_valid") is True,
            "awaiting_server_ack":report.get("status") == "AWAITING_SERVER_ACK",
            "receipt_recorded":report.get("status") == "ACKNOWLEDGED_CLEANED",
            "caption_completeness_verified":False,
            "full_audio_visual_coverage_verified":False,
            "brahmagyan_exam_verified":False,
            "note":"Playback position does not prove continuous watching; text/frame evidence is unverified candidate material.",
        })
        if len(out) >= limit:
            break
    return out


def youtube_audit(root, db, limit=30):
    captions = caption_jobs(db,limit)
    observed = observer_jobs(root,limit)
    return {
        "schema":"suryadev.youtube-learning-audit.v1",
        "caption_extraction":captions,
        "browser_observations":observed,
        "counts":{"caption_jobs":len(captions),"browser_observations":len(observed),
                  "caption_jobs_completed":sum(x["status"]=="done" for x in captions),
                  "browser_candidate_chunks":sum(x["learning_candidate_chunks"] for x in observed),
                  "rishi_exams_verified":0},
        "explanation":"YouTube caption extraction is not video watching. Browser playback position is not wall-clock watched time or verified coverage. Summaries/chunks are candidate knowledge; BRAHMAGYAN exams are not recorded here.",
        "read_only":True,
    }


def main(argv=None):
    """Run a read-only laptop audit without modifying the live worker/SQLite."""
    import argparse
    import sqlite3
    parser = argparse.ArgumentParser(description="Inspect real YouTube time and candidate learning without starting a worker")
    parser.add_argument("--data", required=True)
    parser.add_argument("--limit", type=int, default=20)
    options = parser.parse_args(argv)
    folder = Path(options.data).expanduser().resolve()
    database = folder / "suryadev.sqlite3"
    if database.is_file():
        conn = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=10)
        try:
            conn.execute("PRAGMA query_only=ON")
            data = youtube_audit(folder,conn,limit=options.limit)
        finally:
            conn.close()
    else:
        data = {"schema":"suryadev.youtube-learning-audit.v1",
                "caption_extraction":[],
                "browser_observations":observer_jobs(folder,options.limit),
                "read_only":True, "database_missing":True,
                "note":"No SQLite source database present; it was not created."}
    print(json.dumps(data,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
