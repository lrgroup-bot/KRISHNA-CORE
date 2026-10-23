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
                "playback": playback,
                "policy": "Adaptive 1x/1.5x/2x/4x with conservative caption heuristics; audiovisual coverage unverified",
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
