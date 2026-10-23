"""Local user-initiated SURYADEV research worker process control.

Starts only through the loopback dashboard CSRF-protected endpoint. Does not
enable Windows services, modify startup, pair with KRISHNA, or spawn a second
worker when a live heartbeat/lock exists.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

from suryadev_liveops import _safe_read


class DashboardWorkerControl:
    def __init__(self, data_root, application_dir, *, python_executable=None):
        self.root = Path(data_root).resolve()
        self.application_dir = Path(application_dir).resolve()
        self.python = python_executable or sys.executable
        self.lock = threading.Lock()
        self.process = None
        self.logfile = None

    def snapshot(self):
        with self.lock:
            owned = self.process
            code = owned.poll() if owned is not None else None
            active = owned is not None and code is None
        pulse = _safe_read(self.root, "worker-runtime.json", max_bytes=8192)
        try:
            fresh = 0 <= time.time() - float(pulse.get("heartbeat_at")) < 180
        except (TypeError, ValueError, OverflowError):
            fresh = False
        return {
            "managed_running": active,
            "managed_pid": owned.pid if active else None,
            "managed_exit_code": code if owned is not None else None,
            "worker_heartbeat_recent": fresh and pulse.get("state") not in ("offline","stopped"),
            "heartbeat_state": pulse.get("state") if fresh else "offline",
            "plan_exists": (self.root/"learning-plan.json").is_file(),
            "log_path": str(self.root/"dashboard-worker.log"),
            "auto_research_requires_approved_plan": True,
        }

    def start(self, *, model="qwen3.5:2b"):
        if not isinstance(model, str) or model not in ("qwen3.5:2b", "qwen3.5:4b", "gemma3:4b"):
            raise ValueError("Select one supported local Ollama model")
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                raise RuntimeError("Dashboard-managed worker already running")
            pulse = _safe_read(self.root, "worker-runtime.json", max_bytes=8192)
            try:
                active = (0 <= time.time()-float(pulse.get("heartbeat_at")) < 180 and
                          pulse.get("state") not in ("offline","stopped"))
            except (ValueError, TypeError):
                active = False
            if active:
                raise RuntimeError("Another worker has a recent heartbeat; do not start a duplicate")
            # A lock holder may exist despite a stale heartbeat. The subprocess
            # still performs the canonical worker_lock fail-closed check.
            plan = self.root/"learning-plan.json"
            args = [self.python, "-u", str(self.application_dir/"suryadev_extras.py"),
                    "--data", str(self.root), "worker", "--interval", "30",
                    "--model", model]
            if plan.is_file():
                from suryadev_feeder import read_plan
                read_plan(plan)   # malformed plan prevents any launch
                args += ["--plan", str(plan)]
            logfile = self.root/"dashboard-worker.log"
            logfile.parent.mkdir(parents=True,exist_ok=True)
            # Append only; retaining diagnostics is preferable to hiding worker failures.
            handle = logfile.open("ab", buffering=0)
            flags = getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0) if os.name=="nt" else 0
            # Only the dashboard-managed child receives this laptop profile.
            # Other KRISHNA workers and system-wide Ollama configuration stay untouched.
            env = os.environ.copy()
            env["SURYADEV_OLLAMA_THREADS"] = str(min(2, max(1, (os.cpu_count() or 2)//2)))
            env["SURYADEV_MAX_PARALLEL"] = "1"
            env["SURYADEV_BROWSER_TABS"] = "1"
            try:
                proc = subprocess.Popen(args, cwd=str(self.application_dir),
                    stdin=subprocess.DEVNULL, stdout=handle, stderr=subprocess.STDOUT,
                    shell=False, creationflags=flags, env=env)
            except Exception:
                handle.close()
                raise
            self.process = proc
            self.logfile = handle
            return {"ok": True, "status":"STARTING", "pid":proc.pid,
                    "model":model, "approved_plan_loaded":plan.is_file(),
                    "cpu_thread_budget":int(env["SURYADEV_OLLAMA_THREADS"]),
                    "max_parallel_research":1, "browser_tabs_limit":1,
                    "note":("Continuous approved-source research enabled."
                            if plan.is_file() else
                            "Existing queued tasks only. No new URLs are approved.")}

    def stop(self):
        with self.lock:
            proc = self.process
            if proc is None or proc.poll() is not None:
                raise RuntimeError("No dashboard-managed worker is running")
            # Graceful interruption preserves worker finally / lock-release
            # behavior. Windows process group must be started above.
            try:
                if os.name=="nt":
                    proc.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    proc.send_signal(signal.SIGINT)
            except (OSError, ValueError) as exc:
                raise RuntimeError("Could not request graceful worker stop") from exc
            return {"ok":True, "status":"STOPPING", "pid":proc.pid}

    def close(self):
        with self.lock:
            if self.logfile is not None:
                self.logfile.close()
                self.logfile = None
