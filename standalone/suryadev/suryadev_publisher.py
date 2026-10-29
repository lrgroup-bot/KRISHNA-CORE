"""Opt-in publisher-hosted timed-caption recovery for previously failed video jobs.

This does NOT access YouTube or overcome its HTTP 429 limit. A publisher SRT
can provide independently hosted caption text from an explicitly approved
video/source pair, but not full audio/visual coverage or human verification.
"""
from __future__ import annotations

import json
from pathlib import Path
import time
from urllib.request import Request, build_opener, ProxyHandler

from suryadev import validate_url, StrictRedirect
from suryadev_evidence import save_evidence
from suryadev_ingest import _youtube_url, caption_cues, caption_report
from suryadev_liveops import atomic_json, _safe_read
from suryadev_summary import summarize_all
from suryadev_parallel import youtube_rate_limited

MAX_PUBLISHER_BYTES = 2_000_000
MAX_PUBLISHER_CHARS = 220_000
PUBLISHER_STATE = "publisher-recovery-runtime.json"
FAILED_ATTEMPT_COOLDOWN = 3600


def download_publisher_captions(url):
    """One small, public HTTPS, no-redirect read of an expressly approved URL."""
    validate_url(url)
    opener = build_opener(ProxyHandler({}), StrictRedirect())
    request = Request(url, headers={
        "User-Agent":"SURYADEVPublisherCaptions/1.0 (approved public captions)",
        "Accept":"text/plain,text/vtt,application/x-subrip,application/octet-stream",
        "Accept-Encoding":"identity",
    })
    with opener.open(request, timeout=20) as response:
        if response.headers.get("Content-Encoding", "identity").lower() != "identity":
            raise ValueError("Publisher transcript response must not be compressed")
        length = response.headers.get("Content-Length")
        if length and int(length) > MAX_PUBLISHER_BYTES:
            raise ValueError("Publisher transcript exceeds the size limit")
        raw = response.read(MAX_PUBLISHER_BYTES + 1)
    if not raw or len(raw) > MAX_PUBLISHER_BYTES:
        raise ValueError("Publisher captions empty or larger than 2 MB")
    return raw


def publisher_transcript_text(raw):
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_PUBLISHER_BYTES:
        raise ValueError("Publisher transcript must be nonempty bytes below 2 MB")
    try:
        source = raw.decode("utf-8-sig", errors="strict")
    except UnicodeError as exc:
        raise ValueError("Publisher timed captions are not valid UTF-8") from exc
    cues = caption_cues(source)
    if len(cues) < 10:
        raise ValueError("Publisher captions do not contain sufficient timed cues")
    report = caption_report(cues, duration=None)
    seen = None
    lines = []
    for start,end,words in cues:
        if words != seen:
            lines.append(f"[{start:.2f}-{end:.2f}s] {words}")
        seen=words
    text = "\n".join(lines)
    if not text or len(text) > MAX_PUBLISHER_CHARS:
        raise ValueError("Publisher transcript exceeds full evidence processing limit")
    return text, report


def recover_failed_video_from_publisher(lib, plan, *, fetcher=download_publisher_captions,
                                        now=None, use_ollama=False, model="qwen3.5:9b"):
    """At most one failed video recovery per feed tick; previous error is audited.

    Explicit mapping is necessary. The video task is completed ONLY on verified
    publisher caption text; provenance explicitly states that YouTube was not
    read successfully and neither visuals nor full speech were verified.
    """
    approved = plan.get("approved_publisher_transcripts", [])
    if not approved:
        return {"status":"not_configured", "recovered":0}
    now = time.time() if now is None else float(now)
    seen = _safe_read(lib.root, PUBLISHER_STATE, max_bytes=8192)
    mapping_by_id = {_youtube_url(x["video_url"]): x["transcript_url"] for x in approved}
    for job_id,url,error,failed_at in lib.db.execute(
        "SELECT id,url,error,updated FROM jobs WHERE status='failed' "
        "ORDER BY id DESC LIMIT 1000"
    ).fetchall():
        try:
            video_id = _youtube_url(url)
        except ValueError:
            continue
        transcript = mapping_by_id.get(video_id)
        if not transcript:
            continue
        # An explicit publisher fallback is only a recovery path for a
        # refused YouTube extraction, never a way to rewrite unrelated errors.
        message = (error or "").casefold()
        if not (youtube_rate_limited(message) or
                "sign in to confirm" in message or
                "bot" in message):
            continue
        if (seen.get("video_id") == video_id and
                seen.get("transcript_url") == transcript and
                seen.get("status") == "failed" and
                isinstance(seen.get("next_attempt"), (int,float)) and
                now < seen["next_attempt"]):
            return {"status":"publisher_backoff", "recovered":0,
                    "next_attempt":seen["next_attempt"],
                    "video_id":video_id}
        try:
            raw = fetcher(transcript)
            text, report = publisher_transcript_text(raw)
            evidence = save_evidence(lib.root, text, source=transcript,
                                     kind="approved_publisher_captions")
            digest = evidence["sha256"]
            if use_ollama:
                from suryadev import summarize
                summary, summary_report = summarize_all(
                    text, model=model, use_ollama=True, summarize_fn=summarize)
            else:
                summary, summary_report = summarize_all(
                    text, model=model, use_ollama=False, summarize_fn=lambda *a: "")
            coverage = {
                **report, **summary_report,
                "kind":"youtube",
                "video_id":video_id,
                "publisher_transcript_url":transcript,
                "publisher_transcript_only":True,
                "youtube_extraction_success":False,
                "youtube_request_made_during_recovery":False,
                "full_video_visuals_verified":False,
                "full_audio_coverage_verified":False,
                "source_characters":len(text),
                "extraction_completed":True,
                "evidence_sha256":digest,
                "coverage_status":"official_publisher_caption_timeline_only_unverified",
                "note":"Publisher-hosted timed text only. YouTube access remained blocked; "
                       "visuals, uncaptioned speech and exact audiovisual equivalence unverified.",
            }
            # A single commit makes historical failure -> publisher-only
            # evidence-backed completion atomic, with the previous error
            # preserved and queryable in a separate audit receipt.
            with lib.db:
                lib.db.execute(
                    "CREATE TABLE IF NOT EXISTS publisher_caption_recoveries ("
                    "job_id INTEGER PRIMARY KEY, transcript_url TEXT NOT NULL,"
                    "recovered_at REAL NOT NULL, previous_error TEXT NOT NULL,"
                    "previous_failed_at REAL NOT NULL,evidence_sha256 TEXT NOT NULL)"
                )
                lib.db.execute(
                    "INSERT INTO findings"
                    "(job_id,url,sha256,title,summary,excerpt,created,summary_method) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (job_id,url,digest,
                     "Publisher transcript for YouTube " + video_id,
                     summary,text[:4000],now,
                     "publisher_caption:" + ("ollama_chunked:" + model if use_ollama
                                          else "extractive_preview"))
                )
                lib.db.execute(
                    "INSERT OR REPLACE INTO job_provenance"
                    "(job_id,kind,report_json,recorded) VALUES (?,?,?,?)",
                    (job_id,"youtube",json.dumps(coverage,ensure_ascii=False),now)
                )
                lib.db.execute(
                    "INSERT INTO publisher_caption_recoveries"
                    "(job_id,transcript_url,recovered_at,previous_error,"
                    "previous_failed_at,evidence_sha256) VALUES (?,?,?,?,?,?)",
                    (job_id,transcript,now,str(error)[:800],failed_at,digest)
                )
                updated = lib.db.execute(
                    "UPDATE jobs SET status='done',updated=?,error='' "
                    "WHERE id=? AND status='failed'",(now,job_id)
                ).rowcount
                if updated != 1:
                    raise RuntimeError("Video assignment changed during publisher receipt commit")
            state = {
                "status":"publisher_transcript_recovered",
                "video_id":video_id, "job_id":job_id,
                "transcript_url":transcript,"recovered_at":now,
                "evidence_sha256":digest, "cue_count":len(caption_cues(
                    raw.decode("utf-8-sig"))),
                "youtube_video_verified":False,
            }
            atomic_json(lib.root,PUBLISHER_STATE,state)
            return {"status":"publisher_transcript_recovered",
                    "job_id":job_id,"recovered":1,
                    "publisher_url":transcript,
                    "cue_count":report["cue_count"],
                    "visual_learning_verified":False}
        except (OSError, ValueError, RuntimeError, UnicodeError) as exc:
            state = {"status":"failed", "video_id":video_id,
                     "transcript_url":transcript,
                     "last_attempt":now,
                     "next_attempt":now+FAILED_ATTEMPT_COOLDOWN,
                     "reason":type(exc).__name__ + ": " + str(exc)[:180],
                     "youtube_video_verified":False}
            atomic_json(lib.root,PUBLISHER_STATE,state)
            return {"status":"publisher_unavailable",
                    "video_id":video_id,"recovered":0,
                    "next_attempt":state["next_attempt"],
                    "error":state["reason"]}
    return {"status":"no_eligible_failed_video", "recovered":0}
