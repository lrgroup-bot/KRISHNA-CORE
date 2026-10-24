"""One owner-requested, reproducible SURYADEV YouTube + open-book trial.

Sources are fixed, independently cited public resources, never arbitrary
web/learner output. Original bytes, approvals, and evidence are retained.
The worker lock must be held when calling prepare_trial. No mastery claims.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import ssl
import time
from urllib.request import build_opener, HTTPSHandler, ProxyHandler, Request, HTTPRedirectHandler

from suryadev_liveops import atomic_json
from suryadev_book_continuity import approve_book
from suryadev_book_reader import BookLedger, file_sha256
from suryadev_video_review import VideoReview
from suryadev_feeder import read_plan

VIDEO = "https://www.youtube.com/watch?v=VZ5LU8vHT0s"
BOOK = "https://greenteapress.com/thinkpython2/thinkpython2.pdf"
PDF_MAX = 30 * 1024 * 1024
BOOK_TITLE = "Think Python, 2nd Edition — Allen B. Downey"
VIDEO_TITLE = "Playwright Python 1 | Getting Started — Automation Step by Step"
TRIAL_RECORD = "learning-trial-runtime.json"
AUDIT_RECORD = "learning-trial-audit.json"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def acquire_book(url, dest):
    """Bounded TLS-verified exact-URL PDF transfer, no redirect/SSRF fallback."""
    if url != BOOK:
        raise ValueError("Only the owner-selected exact book URL may be acquired")
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_symlink():
        raise ValueError("Book destination must not be symlink")
    if dest.is_file():
        if dest.stat().st_size > PDF_MAX or dest.stat().st_size < 1024:
            raise ValueError("Existing trial book exceeds size limit")
        with dest.open("rb") as handle:
            if handle.read(5) != b"%PDF-":
                raise ValueError("Existing trial book is not a PDF")
        return file_sha256(dest)
    temp = dest.with_name(dest.name + ".partial-" + str(os.getpid()))
    if temp.exists():
        temp.unlink()  # only this process's own one-time partial
    opener = build_opener(ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context()),
                          NoRedirect())
    try:
        with opener.open(Request(url,headers={"User-Agent":"SuryadevBookTrial/1.0",
                              "Accept":"application/pdf"}), timeout=30) as response:
            if response.status != 200 or response.headers.get_content_type() != "application/pdf":
                raise ValueError("Approved book provider did not return PDF 200")
            if int(response.headers.get("Content-Length") or 0) > PDF_MAX:
                raise ValueError("Approved PDF exceeds 30 MiB")
            digest=hashlib.sha256()
            total=0
            with temp.open("xb") as out:
                first=response.read(8192)
                if not first.startswith(b"%PDF-"):
                    raise ValueError("Book response is not a PDF")
                for piece in (first,):
                    out.write(piece); digest.update(piece); total += len(piece)
                while True:
                    piece=response.read(65536)
                    if not piece: break
                    total += len(piece)
                    if total > PDF_MAX: raise ValueError("Approved PDF exceeds 30 MiB")
                    out.write(piece); digest.update(piece)
            if total < 1024: raise ValueError("Approved PDF unexpectedly short")
        os.replace(temp,dest)
        return digest.hexdigest()
    finally:
        if temp.exists(): temp.unlink()


def prepare_trial(root, app):
    """Seed exactly one already owner-requested video and one book.

    Must run under SURYADEV's exclusive worker lock, not from the dashboard.
    Existing source policy, approvals, databases, and book plan are retained.
    """
    root=Path(root).resolve()
    app=Path(app).resolve()
    state={"schema":"suryadev.automated-trial.v1","youtube_url":VIDEO,
           "book_url":BOOK,"video_title":VIDEO_TITLE,"book_title":BOOK_TITLE,
           "video":"not_prepared","book":"not_prepared",
           "learning_verified":False,"rishi_exam_verified":False,
           "updated_at":time.time()}
    try:
        read_plan(root/"learning-plan.json")
        review=VideoReview(root,app)
        result=review.approve_source(VIDEO)
        review.set_auto(True)
        state["video"]="approved_for_automatic_observation"
        state["video_approval"]=result["status"]
    except (OSError, ValueError, RuntimeError) as exc:
        state["video"]="approval_failed"
        state["video_error"]=type(exc).__name__ + ": " + str(exc)[:180]
    try:
        from suryadev_resources import snapshot
        from suryadev_parallel import plan_capacity
        capacity=plan_capacity(snapshot(root))
        if capacity.get("safe") is not True or capacity.get("max_total",0)<1:
            raise RuntimeError("Local 85% hardware admission refused textbook acquisition")
        path=root/"trial-sources"/"thinkpython2.pdf"
        digest=acquire_book(BOOK,path)
        result=approve_book(root,path,lines_per_step=20)
        state["book"]="indexed_and_approved_for_model_reading"
        state["book_sha256"]=digest
        state["book_id"]=result["book_id"]
        state["book_approval"]=result["status"]
    except (OSError,ValueError,RuntimeError,ImportError,KeyError) as exc:
        state["book"]="acquisition_or_index_failed"
        state["book_error"]=type(exc).__name__ + ": " + str(exc)[:180]
    state["updated_at"]=time.time()
    atomic_json(root,TRIAL_RECORD,state)
    return state


def audit_trial(root, db):
    """Read only original evidence and journals. Never claim model mastery."""
    root=Path(root).resolve()
    prior={}
    try:
        prior=json.loads((root/TRIAL_RECORD).read_text(encoding="utf-8"))
    except (OSError,ValueError):
        pass
    row=db.execute(
        "SELECT id,status,error FROM jobs WHERE url=? ORDER BY id DESC LIMIT 1",
        (VIDEO,)).fetchone()
    from suryadev_youtube_audit import caption_jobs,observer_jobs
    captions=[x for x in caption_jobs(db,50) if x["url"]==VIDEO]
    videos=[x for x in observer_jobs(root,50) if x["url"]==VIDEO]
    has_captions=any(x["status"]=="done" and x.get("caption_cues",0)
                     and x["caption_cues"]>0 for x in captions)
    evidence_chunks=sum(x["learning_candidate_chunks"] for x in videos)
    frames=sum(x["visual_frame_samples"] for x in videos)
    video={"url":VIDEO, "assignment_id":row[0] if row else None,
           "assignment_status":row[1] if row else "not_queued",
           "assignment_error":str(row[2] or "")[:140] if row else "",
           "captions_proven":has_captions,"observation_jobs":len(videos),
           "candidate_chunks":evidence_chunks,"sampled_frames":frames,
           "video_ended_proven":any(x["video_ended"] for x in videos),
           "what_observed":[{"topic":part.get("topic"),"source_start_seconds":part.get("start_seconds"),
                              "candidate_text":part.get("candidate_text")} for v in videos for part in v["what_was_collected"]][:4],
           "coverage_verified":False,"exam_verified":False}
    book={"url":BOOK,"book_id":prior.get("book_id"),"indexed_lines":0,
          "model_lines_processed":0,"journal_integrity":"not_checked",
          "comprehension_verified":False,"exam_verified":False}
    if prior.get("book_id"):
        ledger=BookLedger(root)
        try:
            status=ledger.status(prior["book_id"])
            ver=ledger.verify(prior["book_id"])
            book["indexed_lines"]=status.get("lines_indexed",0)
            book["journal_integrity"]="passed" if ver["sessions_verified"] else "failed"
            sessions=status.get("sessions") or {}
            book["model_lines_processed"]=sum(
                x.get("lines_processed",0) for k,x in sessions.items()
                if k.startswith("ollama:"))
            book["progress_percent"]=max(
                [x.get("progress_percent",0) for k,x in sessions.items()
                 if k.startswith("ollama:")] or [0])
        except (OSError,RuntimeError,ValueError,KeyError) as exc:
            book["journal_integrity"]="error: "+type(exc).__name__
        finally:
            ledger.close()
    report={"schema":"suryadev.automated-learning-trial-audit.v1",
            "video":video,"book":book,
            "status":"candidate_evidence_only",
            "claim":"No mastery: source collection and model notes are not an independent Rishi exam",
            "rishi_exam_verified":False,"brahmagyan_accepted":False,
            "updated_at":time.time()}
    return report
