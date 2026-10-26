"""Up to ten approved browser video observations within the ONE SURYADEV supervisor.

The parent worker already owns the canonical data-root OS lock. Its children
run bounded, isolated Playwright observers but never create another scheduler
or bypass the reviewed-video exact-URL, no-repeat and evidence policies.
Real hardware admission determines whether ANY video process can start.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from suryadev_feeder import read_plan
from suryadev_liveops import atomic_json, _safe_read
from suryadev_video_review import VideoReview
from suryadev_trial_limits import trial_cap, select_trial_videos, video_job_id

MAX_VIDEO = 10
RUNTIME = "video-concurrent-runtime.json"
ATTEMPT_JOURNAL = "video-observer-attempts.json"
OUTCOME_JOURNAL = "video-observer-outcomes.json"


class ParallelVideoReader:
    def __init__(self, root, application_dir, *, clock=time.time, execute=None):
        self.root = Path(root).resolve()
        self.app = Path(application_dir).resolve()
        self.review = VideoReview(self.root, self.app)
        self.pool = ThreadPoolExecutor(max_workers=MAX_VIDEO,
                                       thread_name_prefix="suryadev-video")
        self.execute = execute or self._one
        self.clock = clock
        self.futures = {}
        journal=_safe_read(self.root, ATTEMPT_JOURNAL, max_bytes=65536)
        if (self.root / ATTEMPT_JOURNAL).exists() and (journal.get("schema") != "suryadev.video-attempts.v1"
                       or not isinstance(journal.get("job_ids"), list)):
            raise RuntimeError("Invalid video attempt journal; refusing automatic replay")
        self.attempted = set(
            x for x in (journal.get("job_ids", []) if journal else [])
            if isinstance(x,str) and x.startswith("approved-video-") and len(x) <= 100
        )
        self.closed = False
        self.trial_selection_error = ""

    def _tried(self, job_id, prior_states=None):
        """Any previous real attempt/evidence forbids unattended video replay."""
        if job_id in self.attempted:
            return True
        if prior_states is None:
            prior_states = {row["job_id"] for row in self.review.snapshot_unlocked_jobs()}
        return (job_id in prior_states or
                (self.review.root / "runtime" / "jobs" / job_id).exists())

    def _mark_attempt(self, job_id):
        # Persist BEFORE child launch so an interrupted process cannot
        # silently replay a 3x video or reuse already captured evidence.
        ids = set(self.attempted)
        ids.add(job_id)
        atomic_json(self.root, ATTEMPT_JOURNAL,
                    {"schema": "suryadev.video-attempts.v1",
                     "job_ids": sorted(ids), "updated_at": float(self.clock())})
        self.attempted = ids

    def _record_outcome(self, job_id, result):
        """Persist failures/receipt states beyond the next supervisor tick.

        A missing canonical worker-report.json previously left failed video
        subprocesses looking 'pending_or_running' forever. Do not fabricate
        evidence or authorize retries; this is a separate diagnostic journal.
        """
        old = _safe_read(self.root, OUTCOME_JOURNAL, max_bytes=131072)
        if (self.root / OUTCOME_JOURNAL).exists() and (
                old.get("schema") != "suryadev.video-outcomes.v1"
                or not isinstance(old.get("jobs"), dict)):
            raise RuntimeError("Corrupt video outcome journal; refusing overwrite")
        jobs = dict(old.get("jobs", {}))
        state = str(result.get("state", "unknown"))[:80]
        jobs[job_id] = {
            "state": state,
            "worker_status": str(result.get("worker_status") or "")[:80],
            "error": str(result.get("error") or "")[:300],
            "finished_at": float(self.clock()),
            "evidence_verified": False,
            "rishi_exam_verified": False,
        }
        # Bound size without clearing the unrelated immutable evidence files.
        if len(jobs) > 200:
            keep=sorted(jobs.items(), key=lambda p:p[1].get("finished_at",0),
                        reverse=True)[:200]
            jobs=dict(keep)
        atomic_json(self.root, OUTCOME_JOURNAL,
                    {"schema":"suryadev.video-outcomes.v1",
                     "jobs":jobs,"updated_at":float(self.clock())})

    def auto_enabled(self):
        """Only owner-activated reviewed video automation can launch work."""
        return self.review.auto_enabled()

    def has_pending(self):
        """Reserve video capacity only if a reviewed job can actually run."""
        if self.futures:
            return True
        if not self.auto_enabled() or not self.review.plan.is_file():
            return False
        if not (self.review.worker_script.is_file() and
                self.review.adapter_script.is_file()):
            return False
        try:
            plan=read_plan(self.review.plan)
        except (OSError,ValueError,TypeError):
            return False
        prior = {row["job_id"] for row in self.review.snapshot_unlocked_jobs()}
        urls=self.review._approved_videos(plan["approved_urls"])[:80]
        try:
            selected=select_trial_videos(self.root,urls,
                  previously_tried=lambda jid:self._tried(jid,prior))
        except (RuntimeError,OSError,ValueError) as exc:
            self.trial_selection_error=type(exc).__name__+": "+str(exc)[:160]
            return False
        for url in urls:
            jid=video_job_id(url)
            if (selected is None or jid in selected) and not self._tried(jid, prior):
                return True
        return False

    def _one(self, path):
        if not (self.review.worker_script.is_file() and
                self.review.adapter_script.is_file()):
            return {"state":"adapter_not_installed","job":path.stem}
        job = json.loads(path.read_text(encoding="utf-8"))
        # Validate exact approved HTTPS target again before every observation.
        from suryadev_video_review import validate_job
        validate_job(job,self.review.plan)
        env = os.environ.copy()
        env["SURYADEV_JOB_ADAPTER"] = str(self.review.adapter_script)
        env["SURYADEV_ADAPTER_PYTHON"] = sys.executable
        # Each isolated profile may be expensive: parent measures 85% before
        # every launch; no attempt to suppress browser/CAPTCHA restrictions.
        seconds = min(3600,max(1,float(
            (job.get("constraints") or {}).get("duration_seconds") or 600)))
        try:
            completed = subprocess.run([
                sys.executable,str(self.review.worker_script),
                "--root",str(self.review.root/"runtime"),
                "--job",str(path)],
                cwd=str(self.app),env=env,stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                text=True,shell=False,timeout=seconds+1000,check=False)
            if completed.returncode:
                return {"state":"worker_failed","job":path.stem,
                        "error":completed.stderr[-200:]}
            reply = json.loads(completed.stdout)
            state = reply.get("status") or "unknown"
            if state not in ("AWAITING_SERVER_ACK", "ACKNOWLEDGED_CLEANED"):
                return {"state":"evidence_not_complete","job":path.stem,
                        "worker_status":state}
            return {"state":"evidence_ready_not_verified","job":path.stem,
                    "worker_status":state,
                    "core_acceptance_verified":False}
        except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
            return {"state":"worker_failed","job":path.stem,
                    "error":type(exc).__name__+": "+str(exc)[:160]}

    def tick(self, *, capacity, source_active=0, books_active=0):
        if self.closed:
            raise RuntimeError("Video observer pool closed")
        now=float(self.clock())
        done=[]
        for future,job_id in list(self.futures.items()):
            if not future.done():
                continue
            del self.futures[future]
            try:
                result=future.result()
            except Exception as exc:
                result={"state":"worker_failed","job":job_id,
                        "error":type(exc).__name__+": "+str(exc)[:150]}
            # Preserve a durable result even when the child produced no
            # canonical worker report, so the UI can show the real failure.
            try:
                self._record_outcome(job_id,result if isinstance(result,dict)
                                     else {"state":"worker_failed","error":
                                           "Malformed observer result"})
            except (OSError, ValueError, RuntimeError, TypeError) as exc:
                # Corrupt/unwritable diagnostic history must not shut down
                # books, PDF, website or other video lanes. Never overwrite
                # a damaged receipt as a "repair" or claim it was saved.
                result = dict(result) if isinstance(result,dict) else {
                    "state":"worker_failed","job":job_id}
                result["outcome_persistence_error"] = (
                    type(exc).__name__+": "+str(exc)[:140])
            done.append(result)
        safe=capacity.get("safe") is True
        enabled=self.auto_enabled()
        target=trial_cap("video")
        target=MAX_VIDEO if target is None else min(MAX_VIDEO,target)
        slots=min(target,int(capacity.get("reserved_video_slots",0)),
                  max(0,int(capacity.get("max_total",0))-int(source_active)-int(books_active)))
        started=[]
        if enabled and safe and slots > len(self.futures):
            if self.review.plan.is_file():
                approved=read_plan(self.review.plan)
                urls=self.review._approved_videos(approved["approved_urls"])
            else:
                urls=[]
            occupied=set(self.futures.values())
            prior={row["job_id"] for row in self.review.snapshot_unlocked_jobs()}
            try:
                selected=select_trial_videos(self.root,urls[:80],
                  previously_tried=lambda jid:self._tried(jid,prior))
                self.trial_selection_error=""
            except (RuntimeError,OSError,ValueError) as exc:
                selected=frozenset()
                self.trial_selection_error=type(exc).__name__+": "+str(exc)[:160]
            for url in urls[:80]:
                if len(self.futures)>=slots:
                    break
                jid=video_job_id(url)
                if (selected is not None and jid not in selected):
                    continue
                if jid in occupied or self._tried(jid, prior):
                    continue
                path=self.review._path(jid)
                if not (self.review.worker_script.is_file() and
                        self.review.adapter_script.is_file()):
                    break
                if path.exists():
                    # The approved review job may have been staged by an
                    # earlier trial but never attempted. Validate its exact
                    # immutable URL/job identity before using it.
                    try:
                        existing=json.loads(path.read_text(encoding="utf-8"))
                        if (existing.get("job_id") != jid or
                                existing.get("target") != url):
                            continue
                        from suryadev_video_review import validate_job
                        validate_job(existing,self.review.plan)
                    except (OSError,ValueError,TypeError,KeyError):
                        continue
                else:
                    job={"schema":"krishna.suryadev.job.v1","job_id":jid,
                         "kind":"video_research","target":url,
                         "constraints":{"duration_seconds":3600,
                                        "adaptive_playback":True,
                                        "allow_audio_asr_fallback":False}}
                    self.review.import_job(job)
                self._mark_attempt(jid)
                future=self.pool.submit(self.execute,path)
                self.futures[future]=jid
                occupied.add(jid)
                started.append(jid)
        receipt={"schema":"suryadev.parallel-video.v1",
                 "target":target,"trial_selected_count":(
                    len(selected) if enabled and "selected" in locals() and selected is not None
                    else None),"trial_selection_error":self.trial_selection_error,"active":len(self.futures),
                 "active_job_ids":sorted(self.futures.values()),
                 "started_this_tick":started,"finished":done,
                 "enabled":enabled,"hardware_safe":safe,
                 "reserved_slots":int(capacity.get("reserved_video_slots",0)),
                 "video_comprehension_verified":False,
                 "krishna_receipts_verified":False,
                 "updated_at":now}
        atomic_json(self.root,RUNTIME,receipt)
        return receipt

    def close(self):
        if self.closed:
            return
        self.closed=True
        self.pool.shutdown(wait=True)
