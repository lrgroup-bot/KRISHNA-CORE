"""R39-style reviewed video jobs in the existing GitHub SURYADEV dashboard.

Uses canonical KRISHNA worker/adapter; never imports the R39 ZIP UI or HTTP sync.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import ipaddress
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit

from suryadev_lock import worker_lock

MAX_JOB_BYTES = 4096
JOB_ID = re.compile(r"[A-Za-z0-9_-]{1,120}\Z")


def validate_job(job, plan_path):
    if not isinstance(job, dict) or job.get("schema") != "krishna.suryadev.job.v1":
        raise ValueError("Only an explicit KRISHNA SURYADEV job is accepted")
    jid = job.get("job_id")
    if not isinstance(jid, str) or not JOB_ID.fullmatch(jid):
        raise ValueError("Job ID must contain 1-120 letters, digits, - or _")
    if job.get("kind") != "video_research":
        raise ValueError("This lane accepts video_research jobs only")
    url = job.get("target")
    if not isinstance(url, str) or not (1 <= len(url) <= 2048):
        raise ValueError("Video URL is missing or too long")
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid URL") from exc
    if (parsed.scheme != "https" or not host or parsed.username or
            parsed.password or parsed.fragment or port not in (None, 443)):
        raise ValueError("Only credential-free public HTTPS targets are supported")
    if host == "localhost" or host.endswith((".local", ".localhost", ".internal")):
        raise ValueError("Local/private host is not a research target")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if re.fullmatch(r"[0-9.]+", host) or ":" in host:
            raise ValueError("Malformed IP address") from None
    else:
        raise ValueError("IP-literal research targets are forbidden")
    limits = job.get("constraints") or {}
    if not isinstance(limits, dict):
        raise ValueError("Constraints must be an object")
    if "adaptive_playback" in limits and not isinstance(limits["adaptive_playback"], bool):
        raise ValueError("adaptive_playback must be true or false")
    if "capture_terms" in limits and (not isinstance(limits["capture_terms"], list)
            or len(limits["capture_terms"]) > 80
            or any(not isinstance(t, str) or len(t) > 100 for t in limits["capture_terms"])):
        raise ValueError("capture_terms must be a list of up to 80 short important terms")
    duration = limits.get("duration_seconds", 60)
    if isinstance(duration, bool) or not isinstance(duration, (float, int)) or not 1 <= duration <= 3600:
        raise ValueError("Supervised observations are limited to 1-3600 seconds")
    try:
        raw = json.dumps(job, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except (ValueError, TypeError) as exc:
        raise ValueError("Job must be valid JSON") from exc
    if len(raw) > MAX_JOB_BYTES:
        raise ValueError("Job exceeds the local dashboard request limit")
    try:
        plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("Approved learning-plan.json unavailable; start in read-only mode") from exc
    if not isinstance(plan, dict) or url not in plan.get("approved_urls", []):
        raise ValueError("Exact target URL must first be approved in learning-plan.json")
    return jid, raw


class VideoReview:
    """One supervised video lane. No automatic synchronization or cleanup."""
    def __init__(self, data_root, application_dir):
        self.data_root = Path(data_root).expanduser().resolve()
        self.application_dir = Path(application_dir).resolve()
        self.root = self.data_root / "video-review"
        self.inbox = self.root / "approved-inbox"
        self.plan = self.data_root / "learning-plan.json"
        self.worker_script = self.application_dir / "suryadev_r39_worker.py"
        self.adapter_script = self.application_dir / "suryadev_r39_adapter.py"
        self.lock = threading.Lock()
        self.active = None
        self.last_error = ""
        self.auto_file = self.data_root / "video-auto.json"
        self.auto_error = ""
        self.auto_status = "disabled"
        self.auto_stop = threading.Event()
        self.auto_thread = None

    def auto_enabled(self):
        try:
            config = json.loads(self.auto_file.read_text(encoding="utf-8"))
            return (isinstance(config, dict) and config.get("schema") ==
                    "suryadev.video-auto.v1" and config.get("enabled") is True)
        except (OSError, ValueError):
            return False

    def approve_source(self, url):
        """Operator approves one exact video URL through same-origin CSRF.

        Keeps existing owner quotas, feeds and allowed hosts intact. This
        does not run the video or change KRISHNA enrollment.
        """
        if not isinstance(url, str) or not (1 <= len(url) <= 2048):
            raise ValueError("Enter a complete approved HTTPS YouTube URL")
        try:
            parsed = urlsplit(url)
            host = (parsed.hostname or "").lower()
            port = parsed.port
        except ValueError as exc:
            raise ValueError("Invalid video URL") from exc
        if (parsed.scheme != "https" or host not in
            ("www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be")
            or parsed.username or parsed.password or parsed.fragment
            or port not in (None,443)):
            raise ValueError("Only public HTTPS YouTube URLs without fragments are supported")
        if not parsed.path or parsed.path == "/" or (host.endswith("youtube.com") and
            parsed.path == "/watch" and not "v=" in (parsed.query or "")):
            raise ValueError("Enter a specific video URL, not a YouTube homepage")
        from suryadev_feeder import read_plan
        import shutil
        if self.plan.is_file():
            existing = json.loads(self.plan.read_text(encoding="utf-8"))
            read_plan(self.plan)
        else:
            existing={"approved_urls":[],"approved_feeds":[],
                 "allowed_source_hosts":[],"max_new_per_cycle":5,
                 "max_queued":20}
        if url in existing.get("approved_urls",[]):
            return {"ok":True,"status":"already_approved","approved_url":url}
        updated=dict(existing)
        updated["approved_urls"]=list(existing.get("approved_urls",[]))+[url]
        updated["allowed_source_hosts"]=list(dict.fromkeys(
            list(existing.get("allowed_source_hosts",[]))+[host]))
        # Do not modify an invalid/oversized pre-existing source policy.
        temp=self.plan.with_suffix(".json.tmp")
        temp.write_text(json.dumps(updated,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        try:
            read_plan(temp)
            if self.plan.is_file():
                stamp=time.strftime("%Y%m%d-%H%M%S")
                backup=self.plan.with_name("learning-plan.before-video-"+stamp+".json")
                if backup.exists():
                    backup=self.plan.with_name("learning-plan.before-video-"+stamp+"-"+secrets.token_hex(3)+".json")
                shutil.copy2(self.plan,backup)
            os.replace(temp,self.plan)
        finally:
            temp.unlink(missing_ok=True)
        return {"ok":True,"status":"approved","approved_url":url,
                "note":"URL approved once. Enable automatic video observation to learn it."}

    def set_auto(self, enabled):
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be a boolean")
        if enabled:
            from suryadev_feeder import read_plan
            try:
                plan = read_plan(self.plan)
            except (OSError, ValueError, TypeError) as exc:
                raise ValueError("Approved learning-plan.json unavailable or invalid") from exc
            candidates = self._approved_videos(plan.get("approved_urls", []))
            if not candidates:
                raise ValueError("First add at least one exact YouTube URL to approved learning-plan.json")
        record = {"schema":"suryadev.video-auto.v1", "enabled":enabled,
                  "changed_at":time.time(),
                  "policy":"only exact approved video URLs; no Core acceptance assertion"}
        temp = self.auto_file.with_suffix(".json.tmp")
        temp.parent.mkdir(parents=True,exist_ok=True)
        temp.write_text(json.dumps(record), encoding="utf-8")
        os.replace(temp,self.auto_file)
        self.auto_status = "enabled" if enabled else "disabled"
        return {"ok":True,"auto_enabled":enabled,"status":self.auto_status}

    @staticmethod
    def _approved_videos(urls):
        videos = []
        for url in urls:
            if not isinstance(url,str) or len(url)>2048:
                continue
            try:
                p = urlsplit(url)
            except ValueError:
                continue
            if p.scheme=="https" and (p.hostname or "").lower() in (
                    "www.youtube.com","youtube.com","m.youtube.com","youtu.be"):
                videos.append(url)
        return videos

    def start_auto_scheduler(self, worker_control):
        if self.auto_thread is not None:
            return
        self.auto_thread = threading.Thread(target=self._auto_loop,
                   args=(worker_control,),daemon=True,name="suryadev-video-auto")
        self.auto_thread.start()

    def _auto_loop(self, worker_control):
        from suryadev_liveops import _safe_read
        from suryadev_lock import worker_lock
        while not self.auto_stop.is_set():
            try:
                if not self.auto_enabled():
                    self.auto_status="disabled"
                elif self.active:
                    # A previously launched observation may still be finishing.
                    # This UI must report that real in-flight child honestly.
                    self.auto_status="watching"
                elif (_safe_read(self.data_root, "fresh-workspace.json", max_bytes=4096)
                      .get("node_profile") == "fleet_adaptive"):
                    # A fleet-adaptive node uses the ONE research supervisor's
                    # measured ParallelVideoReader pool. Never seize its
                    # exclusive worker lock from the dashboard scheduler,
                    # even when the worker has not started yet.
                    self.auto_status="supervisor_owned_waiting_for_learning_worker"
                else:
                    pulse=worker_control.snapshot()
                    if pulse["managed_running"] or pulse["worker_heartbeat_recent"]:
                        self.auto_status="waiting_for_research_worker"
                    else:
                        # Check the canonical single-worker lock; never compete
                        # with an already running research or video process.
                        try:
                            with worker_lock(self.data_root):
                                pass
                        except RuntimeError:
                            self.auto_status="waiting_for_worker_lock"
                        else:
                            self._auto_tick()
            except (ValueError, OSError, RuntimeError, TypeError, KeyError) as exc:
                self.auto_status="error"
                self.auto_error=f"{type(exc).__name__}: {str(exc)[:140]}"
            self.auto_stop.wait(10)

    def _auto_tick(self):
        from suryadev_feeder import read_plan
        plan=read_plan(self.plan)
        urls=self._approved_videos(plan.get("approved_urls", []))
        # An imported auto job is a durable once-only attempt. A restart must
        # never silently replay a video whose evidence may still be pending.
        for url in urls[:80]:
            jid="approved-video-"+hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
            path=self._path(jid)
            if path.exists():
                continue
            job={"schema":"krishna.suryadev.job.v1","job_id":jid,
                 "kind":"video_research","target":url,
                 "constraints":{"duration_seconds":3600, "adaptive_playback":True,
                                "allow_audio_asr_fallback":False}}
            result=self.import_job(job)
            self.run_job(jid,True,result["sha256"])
            self.auto_status="watching"
            self.auto_error=""
            return
        self.auto_status="no_new_approved_videos"

    def stop_auto_scheduler(self):
        self.auto_stop.set()

    def _path(self, job_id):
        if not isinstance(job_id, str) or not JOB_ID.fullmatch(job_id):
            raise ValueError("Invalid job ID")
        path = self.inbox / (job_id + ".json")
        if self.root.is_symlink() or self.inbox.is_symlink() or path.is_symlink():
            raise ValueError("Linked workspace paths are forbidden")
        return path

    def import_job(self, job):
        jid, raw = validate_job(job, self.plan)
        path = self._path(jid)
        self.inbox.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(raw).hexdigest()
        with self.lock:
            if path.exists():
                if path.read_bytes() != raw:
                    raise ValueError("Job ID already exists with different contents")
                return {"ok": True, "job_id": jid, "sha256": digest, "duplicate": True}
            with path.open("xb") as output:
                output.write(raw)
        return {"ok": True, "job_id": jid, "sha256": digest, "status": "QUEUED_FOR_REVIEW"}

    def snapshot(self):
        states = {row["job_id"]: row["status"] for row in self.snapshot_unlocked_jobs()}
        with self.lock:
            active, error = self.active, self.last_error
        jobs = []
        if self.inbox.is_dir():
            for path in sorted(self.inbox.glob("*.json"))[:200]:
                if path.is_symlink():
                    continue
                try:
                    row = json.loads(path.read_text(encoding="utf-8"))
                    jid = row["job_id"]
                    status = "RUNNING" if jid == active else states.get(jid, "QUEUED_FOR_REVIEW")
                    jobs.append({"job_id": jid, "target": row.get("target", ""),
                                 "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                 "status": status, "can_run": status in (
                                     "QUEUED_FOR_REVIEW", "FAILED", "EVIDENCE_REQUIRED", "ADAPTER_REQUIRED")})
                except (OSError, ValueError, KeyError, TypeError):
                    continue
        playback = None
        if active and JOB_ID.fullmatch(active):
            # Verified readback of actual HTML video playback rate, not guessed speed.
            speed_file = self.root / "runtime" / "jobs" / active / "playback-speed.json"
            if speed_file.is_file() and not speed_file.is_symlink() and speed_file.stat().st_size <= 8192:
                try:
                    reading = json.loads(speed_file.read_text(encoding="utf-8"))
                    if (reading.get("schema") == "krishna.suryadev.playback-speed.v1"
                            and reading.get("job_id") == active):
                        playback = {
                            "observed_rate": reading.get("observed_rate"),
                            "requested_rate": reading.get("requested_rate"),
                            "category": reading.get("category"),
                            "video_seconds": reading.get("video_seconds"),
                            "coverage_verified": False,
                        }
                except (OSError, ValueError, TypeError):
                    playback = None
        return {"active_job": active, "last_error": error, "jobs": jobs,
                "auto_enabled": self.auto_enabled(),
                "auto_status": self.auto_status,
                "auto_error": self.auto_error,
                "playback": playback,
                "policy": "Adaptive 1x/1.5x/2x/3x with conservative caption heuristics; audiovisual coverage unverified",
                "runtime_ready": self.worker_script.is_file() and self.adapter_script.is_file()}

    def snapshot_unlocked_jobs(self):
        path = self.root / "runtime" / "worker-state.json"
        if not path.is_file():
            return []
        try:
            rows = json.loads(path.read_text(encoding="utf-8")).get("jobs", {})
            return [{"job_id": k, "status": v.get("status")} for k, v in rows.items()]
        except (OSError, ValueError, TypeError, AttributeError):
            return []

    def run_job(self, job_id, approved, expected_sha256):
        if approved is not True:
            raise ValueError("Explicit approval is required before observing the video")
        path = self._path(job_id)
        if not path.is_file():
            raise ValueError("Import the job before starting it")
        with self.lock:
            if self.active:
                raise RuntimeError("A video observation is already running")
            data = path.read_bytes()
            if not isinstance(expected_sha256, str) or not secrets.compare_digest(
                    hashlib.sha256(data).hexdigest(), expected_sha256):
                raise ValueError("The approved job changed; refresh and review the full URL")
            validate_job(json.loads(data.decode("utf-8")), self.plan)
            if not (self.worker_script.is_file() and self.adapter_script.is_file()):
                raise RuntimeError("Canonical observer worker/adapter not installed; run guarded installer")
            prior = next((j for j in self.snapshot_unlocked_jobs() if j["job_id"] == job_id), None)
            if prior and prior["status"] in ("AWAITING_SERVER_ACK", "ACKNOWLEDGED_CLEANED"):
                raise RuntimeError("Evidence already exists; do not replay before receipt review")
            self.active = job_id
            self.last_error = ""
        threading.Thread(target=self._execute, args=(path, job_id), daemon=True,
                         name="suryadev-reviewed-video").start()
        return {"ok": True, "job_id": job_id, "status": "RUNNING"}

    def _execute(self, path, job_id):
        try:
            env = os.environ.copy()
            env["SURYADEV_JOB_ADAPTER"] = str(self.adapter_script)
            env["SURYADEV_ADAPTER_PYTHON"] = sys.executable
            self.root.mkdir(parents=True, exist_ok=True)
            with worker_lock(self.data_root):
                result = subprocess.run(
                    [sys.executable, str(self.worker_script), "--root", str(self.root / "runtime"),
                     "--job", str(path)], cwd=str(self.application_dir), env=env,
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, shell=False, timeout=6*3600+1000, check=False)
            if result.returncode:
                raise RuntimeError("observer process returned a failure exit status")
            try:
                report = json.loads(result.stdout)
                if report.get("status") not in ("AWAITING_SERVER_ACK", "ACKNOWLEDGED_CLEANED"):
                    raise RuntimeError("observer did not produce pending or acknowledged evidence")
            except ValueError as exc:
                raise RuntimeError("observer did not return valid JSON status") from exc
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            with self.lock:
                self.last_error = f"{type(exc).__name__}: {str(exc)[:120]}"
        finally:
            with self.lock:
                self.active = None
