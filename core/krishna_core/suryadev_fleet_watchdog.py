"""KRISHNA's five-minute SURYADEV fleet watchdog.

Reads authenticated Core device receipts; never trusts a merely running PID
as proof of learning. Reports remediation requests for operator-governed
MRITYUNJAY/self-heal. It NEVER sends commands to nodes or kills processes.
"""
from __future__ import annotations

import threading
import time

INTERVAL_SECONDS = 300
HEARTBEAT_STALE_AFTER = 150


def fleet_health_report(snapshot: dict, *, now=None) -> dict:
    if not isinstance(snapshot,dict) or not isinstance(snapshot.get("nodes"),list):
        raise ValueError("fleet device snapshot missing")
    checked_at = time.time() if now is None else float(now)
    nodes = []
    errors = 0
    for row in snapshot["nodes"]:
        if not isinstance(row,dict):
            raise ValueError("invalid node record")
        ident = str(row.get("device_id") or "")[:200]
        last_seen = row.get("last_seen")
        age = checked_at - float(last_seen) if type(last_seen) in (float,int) else float("inf")
        if not ident.startswith("suryadev-") or row.get("authenticated") is not True:
            reason = "unpaired_or_unauthenticated"
        elif not 0 <= age <= HEARTBEAT_STALE_AFTER:
            reason = "heartbeat_stale"
        elif row.get("last_error"):
            reason = "reported_error"
        elif row.get("worker_running") is not True:
            reason = "worker_offline"
        elif row.get("network_online") is not True:
            reason = "network_offline"
        elif row.get("thermal_state") in ("hot","critical","overheating"):
            reason = "thermal_pressure"
        elif row.get("ram_percent") is not None and float(row["ram_percent"]) >= 85:
            reason = "resource_guard_ram"
        elif row.get("cpu_percent") is not None and float(row["cpu_percent"]) >= 85:
            reason = "resource_guard_cpu"
        elif row.get("disk_percent") is not None and float(row["disk_percent"]) >= 85:
            reason = "resource_guard_disk"
        elif row.get("telemetry_sample_at") is None or checked_at - float(row["telemetry_sample_at"]) > 45:
            reason = "telemetry_stale"
        else:
            reason = "healthy_telemetry_only"
        if reason != "healthy_telemetry_only":
            errors += 1
        nodes.append({"device_id":ident,"health":reason,
                      "heartbeat_age_seconds":round(age,2) if 0<=age<1e8 else None,
                      "learning_verified":False,
                      "recommended_action":(
                          "inspect_and_request_authorized_repair"
                          if reason != "healthy_telemetry_only" else "none")})
    return {"schema":"krishna.suryadev.health-check.v1",
            "checked_at":checked_at,"interval_seconds":INTERVAL_SECONDS,
            "nodes":nodes,"unhealthy":errors,"total":len(nodes),
            "automatic_process_killing":False,"mastery_verified":False}


class SuryadevFleetWatchdog:
    def __init__(self, read_nodes, *, interval_seconds=INTERVAL_SECONDS):
        self.read_nodes = read_nodes
        self.interval_seconds = max(INTERVAL_SECONDS,int(interval_seconds))
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.Lock()
        self._checks = 0
        self._last_report = None
        self._last_error = None

    def check(self):
        """Idempotent read-only health check. Safe for status view and tests."""
        report = fleet_health_report(self.read_nodes())
        with self._lock:
            self._checks += 1
            self._last_report = report
            self._last_error = None
        return report

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.check()
            except Exception as exc:
                with self._lock:
                    self._last_error = f"{type(exc).__name__}: {str(exc)[:200]}"
            if self._stop.wait(self.interval_seconds):
                return

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return self.status()
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop,
                                        name="krishna-suryadev-health-audit",daemon=True)
        self._thread.start()
        return self.status()

    def stop(self):
        self._stop.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=3)
        return self.status()

    def status(self):
        with self._lock:
            return {"running":bool(self._thread and self._thread.is_alive()),
                    "interval_seconds":self.interval_seconds,
                    "checks":self._checks,
                    "last_report":self._last_report,
                    "last_error":self._last_error,
                    "self_healing_executed":False}
