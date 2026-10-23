"""Explicitly opted-in outbound-only SURYADEV fleet worker connector.

Never launches commands from Core. Never widens local owner-approved source
allowlists. Uses existing pinned TLS transport and paired device credentials.
The durable local journal survives worker restarts; no claim of knowledge mastery.
"""
from __future__ import annotations

import os
import platform
from pathlib import Path
import time

from suryadev_feeder import read_plan, paired_core_source_allowed
from suryadev_krishna_mission import load_config, post_core
from suryadev_liveops import atomic_json, _safe_read
from suryadev_resources import snapshot, hardware_identity
from suryadev_parallel import plan_capacity
from suryadev_sources import source_kind

FILE = "suryadev-fleet-runtime.json"
RETRY_SECONDS = 30
HEARTBEAT_SECONDS = 20
MAX_LOCAL_QUEUED = 20


def hardware_report(root, *, sample=None, now=None):
    """Normalized capacity. Missing measurements never become invented zeros."""
    report = snapshot(root) if sample is None else sample
    if not report.get("available"):
        return None
    moment=time.time() if now is None else float(now)
    stamp=report.get("sample_time")
    if stamp is not None and (not isinstance(stamp,(int,float))
                             or not 0<=moment-float(stamp)<=10):
        return None
    capacity = plan_capacity(report)
    required = ("cpu_percent", "ram_percent", "disk_percent", "ram_total_gb")
    if any(report.get(k) is None for k in required):
        return None
    cpu = report["cpu_percent"]
    ram = report["ram_percent"]
    disk = report["disk_percent"]
    # Source acquisition is permitted independently of CPU-only model work.
    ident=hardware_identity()
    return {
        "sample_age_seconds": max(0.0,moment-float(stamp)) if stamp is not None else 0,
        "cpu_percent": round(float(cpu),2),
        "ram_percent": round(float(ram),2),
        "disk_percent": round(float(disk),2),
        "ram_total_gb": report["ram_total_gb"],
        "disk_free_gb": report.get("disk_free_gb"),
        "max_total": max(0, min(12, int(capacity.get("max_total") or 0))),
        "capabilities": ["website","youtube","pdf","book"],
        "logical_cpus": ident["logical_cpus"],
        "cpu_name": ident["cpu_name"],
        "platform": ident["platform"],
        "gpu_name": ident["gpu_name"],
        "gpu_inventory_verified": ident["gpu_inventory_verified"],
        "gpu_inference": False,
    }


class FleetClient:
    def __init__(self, root, plan_path, config_path, *,
                 transport=post_core, clock=time.time):
        self.root = Path(root).expanduser().resolve()
        self.plan_path = Path(plan_path).expanduser().resolve()
        self.config = load_config(config_path)
        self.transport = transport
        self.clock = clock
        self.next_heartbeat = 0
        self.next_claim = 0
        self.next_retry = 0
        self.state = _safe_read(self.root, FILE, max_bytes=65536)
        if self.state and self.state.get("schema") != "suryadev.fleet-node.v1":
            raise RuntimeError("Unrecognized fleet state; refusing to overwrite")
        if not self.state:
            self.state = {"schema": "suryadev.fleet-node.v1", "assignments": {},
                          "receipts": {}, "last_error": "", "updated_at": 0}

    def _save(self):
        self.state["updated_at"] = self.clock()
        atomic_json(self.root, FILE, self.state)

    def _send(self, endpoint, payload):
        return self.transport(self.config, "/api/suryadev/" + endpoint,
                              {"device_id": self.config["device_id"], **payload})

    def _heartbeat(self, lib, now, report):
        if now < self.next_heartbeat:
            return
        self.next_heartbeat = now + HEARTBEAT_SECONDS
        telemetry = hardware_report(self.root, sample=report)
        pending = lib.db.execute(
            "SELECT COUNT(*) FROM jobs WHERE status IN ('running','queued')").fetchone()[0]
        reply = self._send("device/heartbeat", {
            "node_name": "SURYADEV-" + self.config["device_id"][-8:],
            "platform": platform.system(),
            "worker_running": True,
            "learning_state": "researching" if pending else "idle",
            "network_online": True,
            "thermal_state": "unknown",
            "telemetry": telemetry,
        })
        if not reply.get("accepted") or reply.get("device_id") != self.config["device_id"]:
            raise RuntimeError("Core rejected signed SURYADEV heartbeat")

    def _reconcile(self, lib, now):
        for task_id, row in list(self.state["assignments"].items()):
            if now > row.get("expires_at", 0):
                # Keep source evidence/job checkpoints; never claim an expired
                # lease completed nor overwrite new Core ownership.
                row["state"] = "lease_expired_manual_reconcile"
                self.state.setdefault("orphaned", {})[task_id] = row
                del self.state["assignments"][task_id]
                self._save()
                continue
            lease = row["lease_id"]
            local_id = row["job_id"]
            result = lib.db.execute(
                "SELECT jobs.status, jobs.error, findings.sha256, findings.excerpt FROM jobs "
                "LEFT JOIN findings ON findings.job_id=jobs.id "
                "WHERE jobs.id=? ORDER BY findings.id DESC LIMIT 1",
                (local_id,)).fetchone()
            if result is None:
                row["state"] = "missing_local_job"
                self._save()
                continue
            status, error, digest, excerpt = result
            if status == "done" and digest:
                outcome = "collected"
            elif status == "failed":
                outcome = "rate_limited" if source_kind(row["url"]) == "youtube" and (
                    "429" in str(error) or "rate limit" in str(error).lower()) else "failed"
            else:
                outcome = None
            if outcome:
                reply = self._send("fleet/complete", {
                    "task_id": task_id, "lease_id": lease,
                    "outcome": outcome, "evidence_sha256": digest if outcome == "collected" else "",
                    "source_excerpt":str(excerpt or "")[:500] if outcome=="collected" else "",
                    "detail": str(error or "")[:300]})
                if not reply.get("acknowledged"):
                    raise RuntimeError("Core did not acknowledge result")
                self.state["receipts"][task_id] = {
                    "outcome": outcome, "job_id": local_id,
                    "sha256": digest if outcome == "collected" else None,
                    "core_acknowledged": True, "brahmagyan_accepted": False}
                del self.state["assignments"][task_id]
                self._save()
            elif row.get("expires_at", 0) - now < 120:
                reply = self._send("fleet/renew", {"task_id": task_id, "lease_id": lease})
                if (reply.get("renewed") is not True or reply.get("lease_id") != lease):
                    raise RuntimeError("Core did not renew owned fleet lease")
                row["expires_at"] = float(reply["expires_at"])
                self._save()

    def _claim(self, lib, now):
        if now < self.next_claim:
            return None
        self.next_claim = now + 15
        measure = hardware_report(self.root)
        if measure is None or measure["max_total"] <= len(self.state["assignments"]):
            return None
        pending = lib.db.execute(
            "SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0]
        if pending >= MAX_LOCAL_QUEUED:
            return None
        reply = self._send("fleet/claim", {
            "known_task_ids": list(self.state["assignments"]),
        })
        if reply.get("status") != "leased":
            return {"state": reply.get("status"), "reason": reply.get("reason")}
        task = reply.get("task") or {}
        tid = str(task.get("task_id") or "")
        url = task.get("url")
        lease = reply.get("lease_id")
        if (not tid.startswith("fleet-") or not isinstance(url, str)
                or not isinstance(lease, str) or len(lease)!=32):
            raise ValueError("Untrusted Core fleet task response")
        plan = read_plan(self.plan_path)
        # KRISHNA may select URLs only inside the owner-approved exact list
        # or the separately enabled paired-Core host delegation.
        if not paired_core_source_allowed(url, plan):
            self._send("fleet/complete", {"task_id": tid, "lease_id": lease,
                    "outcome": "rejected", "detail": "not exact owner-approved local URL"})
            return {"state": "locally_rejected_unapproved_url", "task_id": tid}
        if source_kind(url) != task.get("kind"):
            self._send("fleet/complete", {"task_id": tid, "lease_id": lease,
                    "outcome": "rejected", "detail": "source kind mismatch"})
            return {"state": "locally_rejected_kind", "task_id": tid}
        existing = lib.db.execute(
            "SELECT id FROM jobs WHERE url=? ORDER BY id LIMIT 1", (url,)).fetchone()
        job_id = existing[0] if existing else lib.add(url)
        self.state["assignments"][tid] = {
            "url": url, "job_id": job_id, "lease_id": lease,
            "expires_at": float(reply["expires_at"]),
            "state": "local_job_persisted"}
        self._save()
        return {"state": "owner_approved_lease_accepted", "task_id": tid,
                "job_id": job_id, "source_url": url, "reused_job": bool(existing)}

    def tick(self, lib, *, report=None):
        now = self.clock()
        if now < self.next_retry:
            return None
        try:
            self._heartbeat(lib, now, report)
            self._reconcile(lib, now)
            result = self._claim(lib, now)
            if result:
                self.state["last_error"] = ""
                self._save()
            return result
        except (OSError, RuntimeError, ValueError) as exc:
            self.next_retry = now + RETRY_SECONDS
            self.state["last_error"] = type(exc).__name__ + ": " + str(exc)[:220]
            self._save()
            return {"state": "offline_retry", "error": self.state["last_error"],
                    "local_evidence_preserved": True}
