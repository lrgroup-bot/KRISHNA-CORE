"""Local user-initiated SURYADEV research worker process control.

Starts only through the loopback dashboard CSRF-protected endpoint. Does not
enable Windows services, modify startup, pair with KRISHNA, or spawn a second
worker when a live heartbeat/lock exists.
"""
from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

from suryadev_liveops import _safe_read
from suryadev_lock import worker_lock


class DashboardWorkerControl:
    def __init__(self, data_root, application_dir, *, python_executable=None):
        self.root = Path(data_root).resolve()
        self.application_dir = Path(application_dir).resolve()
        self.python = python_executable or sys.executable
        self.lock = threading.Lock()
        self.process = None
        self.logfile = None
        self.running_model = None

    def _external_lock_held(self):
        """Probe the canonical OS worker lock without trusting a stale PID receipt.

        The read-only probe releases a successfully acquired lock immediately.
        An active background video or CLI learner still excludes duplicate work.
        """
        try:
            with worker_lock(self.root):
                return False
        except RuntimeError as exc:
            if str(exc) == "another SURYADEV worker holds the lock":
                return True
            raise

    def core_pairing(self):
        """Read only an existing, owner-provisioned pinned-TLS credential.

        Merely entering a Core IP in Settings is NOT enrollment.
        The caller gets no credential bytes, only a readiness reason.
        """
        config_file = self.root / "core-mission-connection.json"
        if not config_file.is_file():
            return {"configured":False,"ready":False,
                    "reason":"KRISHNA paired TLS device configuration is not installed"}
        try:
            from suryadev_krishna_mission import load_config
            cfg = load_config(config_file)
            if not cfg["device_id"].startswith("suryadev-"):
                raise ValueError("paired device ID must start with suryadev-")
        except (OSError, ValueError, TypeError) as exc:
            return {"configured":True,"ready":False,
                    "reason":"Paired KRISHNA configuration invalid: "+type(exc).__name__}
        return {"configured":True,"ready":True,
                "reason":"Pinned TLS configuration validated locally; server connection unverified"}

    def set_core_delegation(self, enabled):
        """One-time operator approval of paired-Core source selection by host.

        Preserves existing exact URLs, quotas, feeds, evidence and backups.
        All remote work still requires a TLS-pinned paired Core and the
        Core's own approved mission catalogue.
        """
        if type(enabled) is not bool:
            raise ValueError("Delegation state must be true or false")
        if enabled and not self.core_pairing()["ready"]:
            raise ValueError("Pair KRISHNA with verified HTTPS certificate and device token first")
        from suryadev_feeder import read_plan
        import shutil
        import secrets
        plan = self.root/"learning-plan.json"
        parsed = read_plan(plan)
        if enabled and not parsed["allowed_source_hosts"]:
            raise ValueError("Approve one or more permitted research hosts first")
        original = json.loads(plan.read_text(encoding="utf-8"))
        if original.get("paired_core_host_delegation",False) is enabled:
            return {"ok":True,"enabled":enabled,"state":"unchanged"}
        updated = dict(original, paired_core_host_delegation=enabled)
        temp = plan.with_name(".core-delegation-"+secrets.token_hex(6)+".json")
        temp.write_text(json.dumps(updated,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        try:
            read_plan(temp)
            backup = plan.with_name("learning-plan.before-core-delegation-"+secrets.token_hex(8)+".json")
            shutil.copy2(plan, backup)
            os.replace(temp,plan)
        finally:
            temp.unlink(missing_ok=True)
        return {"ok":True,"enabled":enabled,"state":"updated",
                "source_policy":"paired KRISHNA only, existing approved HTTPS hostnames"}

    def _save_fresh_model(self, model):
        """Remember an explicitly selected local model without editing the study ledger.

        Only an already initialized fresh workspace marker can be updated.
        Replacing the marker atomically keeps the preceding approved sources,
        job receipts and model-independent learning checkpoints unchanged.
        """
        marker = self.root / "fresh-workspace.json"
        if not marker.is_file():
            return
        data = _safe_read(self.root, "fresh-workspace.json", max_bytes=4096)
        if data.get("schema") != "suryadev.fresh-workspace.v1":
            return
        if data.get("trial_model") == model:
            return
        updated = dict(data, trial_model=model)
        stage = marker.with_name(".fresh-workspace-model-" + secrets.token_hex(8) + ".tmp")
        try:
            stage.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
            os.replace(stage, marker)
        finally:
            stage.unlink(missing_ok=True)

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
        # Heartbeat receipts are historical telemetry; only the OS lock
        # proves that an external process still owns the worker lane.
        external_lock = False if active else self._external_lock_held()
        core = self.core_pairing()
        standalone_test = os.environ.get("SURYADEV_STANDALONE_TEST") == "1"
        try:
            from suryadev_feeder import read_plan
            policy=read_plan(self.root/"learning-plan.json")
            delegated = bool(policy.get("paired_core_host_delegation"))
            host_count = len(policy.get("allowed_source_hosts", []))
        except (OSError, ValueError, TypeError):
            delegated = False
            host_count = 0
        workspace=_safe_read(self.root, "fresh-workspace.json", max_bytes=4096)
        is_fresh=workspace.get("schema")=="suryadev.fresh-workspace.v1"
        fleet_adaptive = is_fresh and workspace.get("node_profile") == "fleet_adaptive"
        return {
            "workspace_mode":"fresh" if is_fresh else "existing",
            "node_profile":"fleet_adaptive" if fleet_adaptive else "legacy",
            "workspace_active_task_limit":125 if fleet_adaptive else 3,
            "workspace_data_dir":str(self.root),
            "workspace_previous_retained":bool(is_fresh),
            "preferred_model":workspace.get("trial_model", "qwen3.5:2b") if is_fresh else None,
            "managed_model":self.running_model if active else None,
            # A CLI-launched worker owns the SAME canonical OS lock but is
            # not a child of this dashboard. Its actual model is unknown
            # here: don't falsely mark it "inactive" or borrow a stale model.
            "learning_role":("collector_only" if self.running_model == "collector" else
                             "local_inference") if active else
                            "external_worker" if external_lock and fresh and
                                pulse.get("state") not in ("offline","stopped") else
                            "external_lock_only" if external_lock else "inactive",
            "worker_owner":"dashboard" if active else
                           "external_process" if external_lock else "none",
            "managed_model_source":"dashboard_process" if active else
                                   "not_reported",
            "paired_core_host_delegation":delegated,
            "paired_core_approved_host_count":host_count,
            "core_dispatch": core,
            "dispatch_mode": "standalone_test" if standalone_test else
                             "krishna_fleet_configured" if core["ready"] else "local_only",
            "managed_running": active,
            "external_worker_active": external_lock,
            "can_start": not (active or external_lock),
            "blocked_reason": ("Dashboard worker is already running" if active else
                               "Another learning/video process holds the worker lock" if external_lock else
                               ""),
            "managed_pid": owned.pid if active else None,
            "managed_exit_code": code if owned is not None else None,
            "worker_heartbeat_recent": fresh and pulse.get("state") not in ("offline","stopped"),
            "heartbeat_state": pulse.get("state") if fresh else "offline",
            "plan_exists": (self.root/"learning-plan.json").is_file(),
            "log_path": str(self.root/"dashboard-worker.log"),
            "auto_research_requires_approved_plan": True,
        }

    def start(self, *, model="qwen3.5:2b"):
        if not isinstance(model, str) or model not in ("auto", "collector", "qwen3.5:2b", "qwen3.5:4b", "qwen3.5:9b", "gemma3:4b"):
            raise ValueError("Select one supported local Ollama model")
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                raise RuntimeError("Dashboard-managed worker already running")
            if self._external_lock_held():
                raise RuntimeError("Another SURYADEV research or video process owns the worker lock")
            # Select the actual model using only THIS node's telemetry.
            # Auto never downloads model weights or selects heavy inference.
            from suryadev_model_router import resolve_model
            selection = resolve_model(model, self.root)
            actual_model = selection["model"]
            # A recently written heartbeat alone is not an active process.
            # The child independently acquires the lock before doing any work.
            standalone_test = os.environ.get("SURYADEV_STANDALONE_TEST") == "1"
            core = self.core_pairing() if not standalone_test else {"configured":False, "ready":False}
            plan = self.root/"learning-plan.json"
            args = [self.python, "-u", str(self.application_dir/"suryadev_extras.py"),
                    "--data", str(self.root), "worker", "--interval", "30",
                    "--model", actual_model]
            if plan.is_file():
                from suryadev_feeder import read_plan
                if not core["ready"]:
                    read_plan(plan)   # paired policy is checked AFTER heartbeat
                args += ["--plan", str(plan)]
            if actual_model == "collector":
                # Evidence capture only: no local inference, Ollama process or model download.
                args += ["--no-ollama"]
            approved_books = self.root / "book-plan.json"
            if approved_books.is_file():
                if not core["ready"]:
                    from suryadev_book_continuity import read_book_plan
                    from suryadev_book_reader import file_sha256
                    entries = read_book_plan(approved_books)["books"]
                    if any(file_sha256(item["path"]) != item["sha256"] for item in entries):
                        raise ValueError("Approved book bytes changed; refuse worker startup")
                # Collector indexes evidence only; a local model performs
                # serialized checkpointed book interpretation when enabled.
                args += (["--book-collect-plan", str(approved_books)]
                         if actual_model == "collector" else
                         ["--book-plan", str(approved_books)])
            # Once installed and authenticated by its existing pinned TLS
            # device credential, KRISHNA owns the mission queue. Never
            # derive permission from an unauthenticated LAN /health probe.
            standalone_test = os.environ.get("SURYADEV_STANDALONE_TEST") == "1"
            core = self.core_pairing() if not standalone_test else {
                "configured":False, "ready":False}
            if core["configured"] and not core["ready"]:
                raise RuntimeError("Core pairing file is invalid; fix verified TLS device enrollment")
            if core["ready"]:
                args += ["--core-mission-config", str(self.root/"core-mission-connection.json"),
                         "--fleet-mode"]
            # Persist the operator-selected 2B model for the next dashboard boot.
            # No mutation of sources, SQLite history or model evidence occurs.
            self._save_fresh_model(model)
            logfile = self.root/"dashboard-worker.log"
            logfile.parent.mkdir(parents=True,exist_ok=True)
            # Append only; retaining diagnostics is preferable to hiding worker failures.
            handle = logfile.open("ab", buffering=0)
            flags = getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0) if os.name=="nt" else 0
            # Only the dashboard-managed child receives this laptop profile.
            # Other KRISHNA workers and system-wide Ollama configuration stay untouched.
            env = os.environ.copy()
            env["SURYADEV_OLLAMA_THREADS"] = str(min(2, max(1, (os.cpu_count() or 2)//2)))
            workspace = _safe_read(self.root,"fresh-workspace.json",max_bytes=4096)
            # Honor the persisted operator preference even when the dashboard
            # is reopened directly instead of through start-node.py.
            if "SURYADEV_BOOK_FAST" not in env:
                env["SURYADEV_BOOK_FAST"] = "1" if workspace.get("fast_books") is True else "0"
            fleet_adaptive = (workspace.get("schema") == "suryadev.fresh-workspace.v1"
                              and workspace.get("node_profile") == "fleet_adaptive")
            ceiling = 125 if fleet_adaptive else 3
            try:
                requested = int(env.get("SURYADEV_MAX_PARALLEL", str(ceiling)))
            except (TypeError, ValueError):
                requested = 1
            env["SURYADEV_MAX_PARALLEL"] = str(max(1, min(ceiling, requested)))
            env["SURYADEV_BROWSER_TABS"] = "auto"
            env["SURYADEV_COLLECTOR_ONLY"] = "1" if actual_model == "collector" else "0"
            try:
                proc = subprocess.Popen(args, cwd=str(self.application_dir),
                    stdin=subprocess.DEVNULL, stdout=handle, stderr=subprocess.STDOUT,
                    shell=False, creationflags=flags, env=env)
            except Exception:
                handle.close()
                raise
            self.process = proc
            self.running_model = actual_model
            self.logfile = handle
            return {"ok": True, "status":"STARTING", "pid":proc.pid,
                    "model":actual_model, "requested_model":model,
                    "model_policy_reason":selection["reason"],
                    "learning_role":"collector_only" if actual_model=="collector" else "local_inference",
                    "ollama_required":actual_model!="collector", "approved_plan_loaded":plan.is_file(),
                    "approved_books_loaded":approved_books.is_file(),
                    "book_mode": ("indexed_evidence_only" if actual_model=="collector" else
                                  "local_model_interpretation_unverified")
                                 if approved_books.is_file() else "no_approved_books",
                    "core_dispatch_mode":"standalone_test" if standalone_test else
                                         "krishna_fleet" if core["ready"] else "local",
                    "cpu_thread_budget":int(env["SURYADEV_OLLAMA_THREADS"]),
                    "automatic_hardware_capacity":True,
                    "pdf_workload_limit":100,
                    "max_parallel_research":int(env["SURYADEV_MAX_PARALLEL"]),
                    "browser_tabs_limit":"dynamic_up_to_10",
                    "note":("KRISHNA paired fleet mission polling enabled; Core acceptance not claimed."
                            if core["ready"] else
                            "Local approved-source research enabled; KRISHNA not paired."
                            if plan.is_file() else
                            "Existing queued tasks only. KRISHNA not paired.")}

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
