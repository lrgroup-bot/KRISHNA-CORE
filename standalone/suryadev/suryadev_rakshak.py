"""SURYADEV RAKSHAK: separate, lightweight fleet health observer.

Does not run inside KRISHNA, call Ollama, control nodes, install services,
or kill unrelated processes. Runs on the KRISHNA PC and reads only its
loopback-only fleet-node status API every five minutes.

Deployment to a different PC requires an approved, paired, TLS-pinned
read endpoint in a future increment; this loopback version refuses it.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import signal
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

SCHEMA = "suryadev.rakshak.health.v1"
INTERVAL_SECONDS = 300
HEARTBEAT_TTL = 150
TELEMETRY_TTL = 45
MAX_RESPONSE_BYTES = 1024 * 1024
DEFAULT_CORE_URL = "http://127.0.0.1:8766/api/suryadev/fleet/nodes"
ALERT_LOG = "rakshak-incidents.jsonl"
STATUS_FILE = "rakshak-status.json"


def _valid_core_url(url):
    """Never redirect a health check to the LAN or public Internet."""
    if not isinstance(url, str):
        raise ValueError("Core URL must be text")
    try:
        u = urlsplit(url)
        port = u.port
    except ValueError as exc:
        raise ValueError("Invalid Core port") from exc
    if (u.scheme != "http" or u.hostname != "127.0.0.1" or
            u.username or u.password or u.query or u.fragment or
            u.path != "/api/suryadev/fleet/nodes" or
            port is None or not 1 <= port <= 65535):
        raise ValueError("RAKSHAK accepts only the loopback-only KRISHNA fleet nodes endpoint")
    return url


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def read_core_nodes(url=DEFAULT_CORE_URL):
    """One bounded, read-only GET. No proxy and no cross-origin redirect."""
    url = _valid_core_url(url)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    req = urllib.request.Request(url, method="GET",
                                 headers={"Accept": "application/json"})
    with opener.open(req, timeout=5) as response:
        if response.status != 200:
            raise RuntimeError("KRISHNA did not return an accepted health snapshot")
        data = response.read(MAX_RESPONSE_BYTES + 1)
        if len(data) > MAX_RESPONSE_BYTES:
            raise ValueError("Health snapshot too large")
    parsed = json.loads(data.decode("utf-8"))
    if not isinstance(parsed, dict) or not isinstance(parsed.get("nodes"), list):
        raise ValueError("KRISHNA health snapshot schema invalid")
    if len(parsed["nodes"]) > 1000:
        raise ValueError("Too many registered SURYADEV nodes")
    return parsed


def read_local_core_state(path):
    """Read Core's already-existing atomic device ledger without KRISHNA HTTP.

    RAKSHAK receives no write access and never modifies the original.
    The file must be the local Core-owned suryadev/device-nodes.json.
    """
    source = Path(path).expanduser().resolve(strict=True)
    if source.name != "device-nodes.json" or not source.is_file() or source.is_symlink():
        raise ValueError("Select Core's original device-nodes.json file")
    if source.stat().st_size > MAX_RESPONSE_BYTES:
        raise ValueError("Core device registry too large")
    raw = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or len(raw) > 1000:
        raise ValueError("Invalid Core device registry")
    if any(not isinstance(k,str) or not isinstance(v,dict) or
           k != v.get("device_id") for k,v in raw.items()):
        raise ValueError("Invalid Core device registry rows")
    return {"nodes": list(raw.values())}


def _percent(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        return None
    return float(value) if 0 <= float(value) <= 100 else None


def inspect(snapshot, *, now=None):
    """Evaluate data as evidence of host status, never as proof of mastery."""
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("nodes"), list):
        raise ValueError("Invalid KRISHNA node snapshot")
    when = time.time() if now is None else float(now)
    report = []
    for item in snapshot["nodes"]:
        if not isinstance(item, dict):
            raise ValueError("Invalid node receipt")
        device = item.get("device_id")
        if not isinstance(device, str) or not device.startswith("suryadev-") or len(device) > 200:
            raise ValueError("Invalid SURYADEV node identity")
        last = item.get("last_seen")
        telemetry_at = item.get("telemetry_sample_at")
        age = when - float(last) if type(last) in (float, int) else float("inf")
        telemetry_age = (when - float(telemetry_at)
                         if type(telemetry_at) in (float, int) else float("inf"))
        measured = {k: _percent(item.get(k))
                    for k in ("cpu_percent", "ram_percent", "disk_percent")}
        if item.get("authenticated") is not True:
            state = "unpaired"
        elif not 0 <= age <= HEARTBEAT_TTL:
            state = "heartbeat_stale"
        elif item.get("worker_running") is not True:
            state = "worker_offline"
        elif item.get("network_online") is not True:
            state = "network_offline"
        elif item.get("last_error"):
            state = "reported_error"
        elif item.get("thermal_state") in {"hot", "critical", "overheating"}:
            state = "thermal_guard"
        elif not 0 <= telemetry_age <= TELEMETRY_TTL or any(v is None for v in measured.values()):
            state = "telemetry_stale"
        elif any(v >= 85 for v in measured.values()):
            state = "hardware_guard"
        elif (type(item.get("queued_jobs")) is int
              and item["queued_jobs"] > 0
              and item.get("running_jobs") == 0
              and type(item.get("available_slots")) is int
              and item["available_slots"] > 0
              and item.get("learning_state") == "researching"):
            # Five-minute observation of work waiting despite healthy
            # measured admission. Could be a transient source/provider
            # pause; report for diagnosis, NEVER terminate a process.
            state = "queue_waiting_review"
        else:
            state = "healthy_telemetry_only"
        report.append({
            "device_id": device, "health": state,
            "heartbeat_age_seconds": round(age, 2) if math.isfinite(age) and age >= 0 else None,
            "cpu_percent": measured["cpu_percent"],
            "ram_percent": measured["ram_percent"],
            "disk_percent": measured["disk_percent"],
            "queued_jobs": item.get("queued_jobs"),
            "running_jobs": item.get("running_jobs"),
            "learning_state": item.get("learning_state"),
            "learned_or_mastered": False,
            "automatic_process_killing": False,
        })
    return {"schema": SCHEMA, "checked_at": when,
            "interval_seconds": INTERVAL_SECONDS,
            "total": len(report),
            "unhealthy": sum(r["health"] != "healthy_telemetry_only" for r in report),
            "nodes": report, "repair_executed": False,
            "rishi_mastery_verified": False}


def _atomic_json(path, data):
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    # Atomic replacement; not a lock or permission to write to KRISHNA state.
    import secrets
    stage = parent / ("." + path.name + "." + secrets.token_hex(6) + ".tmp")
    try:
        with stage.open("w", encoding="utf-8") as output:
            json.dump(data, output, indent=2, ensure_ascii=False)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(stage, path)
    finally:
        stage.unlink(missing_ok=True)


def check_once(data_root, *, url=DEFAULT_CORE_URL, fetch=read_core_nodes, now=None):
    """Persist telemetry; emit an incident on each state transition only."""
    url = _valid_core_url(url)
    root = Path(data_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    status_path = root / STATUS_FILE
    try:
        old = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        old = {}
    when = time.time() if now is None else float(now)
    try:
        report = inspect(fetch(url), now=when)
        report["core_state"] = "reachable" if report["total"] else "reachable_no_nodes"
        if not report["total"]:
            report["unhealthy"] = 1
            report["reason"] = "No paired SURYADEV node heartbeats were available"
    except (OSError, ValueError, RuntimeError, urllib.error.URLError, json.JSONDecodeError) as exc:
        report = {"schema": SCHEMA, "checked_at": when,
                  "interval_seconds": INTERVAL_SECONDS,
                  "core_state": "unreachable", "total": 0,
                  "unhealthy": 1, "nodes": [],
                  "reason": type(exc).__name__ + ": " + str(exc)[:180],
                  "repair_executed": False, "rishi_mastery_verified": False}
    prior = {x["device_id"]: x["health"] for x in old.get("nodes", [])
             if isinstance(x, dict) and "device_id" in x and "health" in x}
    current = {x["device_id"]: x["health"] for x in report["nodes"]}
    changes = [{"device_id":k, "previous":prior.get(k), "health":v}
               for k,v in current.items() if prior.get(k) != v]
    if old.get("core_state") != report["core_state"]:
        changes.append({"device_id": "KRISHNA-health-endpoint", 
                        "previous":old.get("core_state"),"health":report["core_state"]})
    report["state_changes"] = changes
    _atomic_json(status_path, report)
    if changes:
        with (root / ALERT_LOG).open("a", encoding="utf-8") as log:
            for change in changes:
                log.write(json.dumps({"at": when, **change}, ensure_ascii=False) + "\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Separate low-resource SURYADEV RAKSHAK health monitor")
    parser.add_argument("--data", type=Path, required=True,
                        help="Own durable state folder, separate from KRISHNA and SURYADEV ledgers")
    parser.add_argument("--core-url", default=DEFAULT_CORE_URL)
    parser.add_argument("--core-state", type=Path, default=None,
                        help="Read KRISHNA's existing device-nodes.json directly; zero HTTP requests")
    parser.add_argument("--interval", type=int, default=INTERVAL_SECONDS)
    parser.add_argument("--once", action="store_true",
                        help="Perform a single safe read-only health check and exit")
    args = parser.parse_args(argv)
    _valid_core_url(args.core_url)
    if args.core_state is not None:
        # Resolve the path early so misconfigured startup fails cleanly
        # instead of reporting a fabricated green state.
        source = args.core_state.expanduser().resolve()
        if source.name != "device-nodes.json":
            parser.error("--core-state must point to Core's device-nodes.json")
        fetch = lambda _url: read_local_core_state(source)
    else:
        fetch = read_core_nodes
    if args.interval < INTERVAL_SECONDS:
        parser.error("Minimum polling interval is five minutes")
    stopping = False

    def request_stop(signum, frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, request_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, request_stop)
    while not stopping:
        report = check_once(args.data, url=args.core_url, fetch=fetch)
        print(json.dumps({"SURYADEV_RAKSHAK": report["core_state"],
              "nodes": report["total"], "issues": report["unhealthy"],
              "state_changes": len(report["state_changes"])}), flush=True)
        if args.once:
            return 0 if report["core_state"] == "reachable" else 2
        # Use short interruptible sleeps so Ctrl+C does not need process kill.
        until = time.monotonic() + args.interval
        while not stopping and time.monotonic() < until:
            time.sleep(min(1.0, until - time.monotonic()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
