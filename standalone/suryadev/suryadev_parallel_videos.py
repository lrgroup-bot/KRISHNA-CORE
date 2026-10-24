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
from suryadev_liveops import atomic_json
from suryadev_video_review import VideoReview

MAX_VIDEO = 10
RUNTIME = "video-concurrent-runtime.json"


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
        self.attempted = set()
        self.closed = False

    def auto_enabled(self):
        """Only owner-activated reviewed video automation can launch work."""
        return self.review.auto_enabled()

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
            done.append(result)
        safe=capacity.get("safe") is True
        enabled=self.auto_enabled()
        slots=min(MAX_VIDEO,int(capacity.get("reserved_video_slots",0)),
                  max(0,int(capacity.get("max_total",0))-int(source_active)-int(books_active)))
        started=[]
        if enabled and safe and slots > len(self.futures):
            if self.review.plan.is_file():
                approved=read_plan(self.review.plan)
                urls=self.review._approved_videos(approved["approved_urls"])
            else:
                urls=[]
            occupied=set(self.futures.values())
            for url in urls[:80]:
                if len(self.futures)>=slots:
                    break
                jid="approved-video-"+hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
                if jid in occupied or jid in self.attempted:
                    continue
                path=self.review._path(jid)
                if path.exists():
                    # Prior evidence/job is never replayed automatically, even
                    # after restarts or transient failure.
                    self.attempted.add(jid)
                    continue
                if not (self.review.worker_script.is_file() and
                        self.review.adapter_script.is_file()):
                    break
                job={"schema":"krishna.suryadev.job.v1","job_id":jid,
                     "kind":"video_research","target":url,
                     "constraints":{"duration_seconds":600,
                                    "adaptive_playback":True,
                                    "allow_audio_asr_fallback":False}}
                self.review.import_job(job)
                self.attempted.add(jid)
                future=self.pool.submit(self.execute,path)
                self.futures[future]=jid
                occupied.add(jid)
                started.append(jid)
        receipt={"schema":"suryadev.parallel-video.v1",
                 "target":MAX_VIDEO,"active":len(self.futures),
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
