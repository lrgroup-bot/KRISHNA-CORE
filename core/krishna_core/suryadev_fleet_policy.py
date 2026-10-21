"""Read-only many-to-many Rishi -> SURYADEV fleet placement policy.

BRAHMAGYAN owns research questions, BRAHMA will own authenticated task leases.
This module plans *candidate* placement only. No machine commands, network
requests, task mutations, source approvals or mastery claims are made here.
Actual lease + signed node receipts are a separate unfinished integration.
"""
from __future__ import annotations

import math
import time

LANES = frozenset({"website", "youtube", "pdf", "book", "experiment"})
HEARTBEAT_TTL_SECONDS = 150
TELEMETRY_TTL_SECONDS = 45


def _percentage(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) and 0 <= number <= 100 else None


def plan_rishi_collection(tasks, nodes, *, council_ids, now=None,
                          hard_ceiling=85, slowdown_at=75):
    """Draft assignments from approved Rishi tasks to trusted healthy node slots.

    Tasks are logical Rishi demands, nodes are physical SURYADEV machines.
    No static Rishi/PC ratio exists. Untrusted, stale, hot, unsampled or
    exhausted nodes are *excluded*, not optimistically assigned work.
    """
    now = time.time() if now is None else float(now)
    if not math.isfinite(now) or now <= 0:
        raise ValueError("valid current timestamp required")
    if not 0 < slowdown_at < hard_ceiling <= 100:
        raise ValueError("invalid headroom thresholds")
    if not isinstance(tasks, list) or not isinstance(nodes, list):
        raise TypeError("tasks and nodes must be lists")
    council = set(council_ids or [])
    if not council:
        raise ValueError("Rishi Council registry required")

    healthy = []
    excluded = []
    seen_nodes = set()
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("node record must be a dict")
        ident = str(node.get("device_id") or "").strip()
        if not ident or ident in seen_nodes:
            raise ValueError("node identity missing or duplicate")
        seen_nodes.add(ident)
        reason = None
        if (not ident.startswith("suryadev-")
                or node.get("authenticated") is not True):
            reason = "no verified owner-paired identity"
        elif node.get("worker_running") is not True or node.get("network_online") is not True:
            reason = "worker or network offline"
        elif node.get("last_error"):
            reason = "node reported error"
        elif node.get("thermal_state") in {"hot", "critical", "overheating"}:
            reason = "thermal protection"
        elif (not isinstance(node.get("last_seen"), (int, float))
              or not 0 <= now - node["last_seen"] <= HEARTBEAT_TTL_SECONDS):
            reason = "stale heartbeat"
        elif (not isinstance(node.get("telemetry_sample_at"), (int, float))
              or not 0 <= now - node["telemetry_sample_at"] <= TELEMETRY_TTL_SECONDS):
            reason = "no fresh hardware telemetry"
        measurements = {k: _percentage(node.get(k)) for k in ("cpu_percent", "ram_percent", "disk_percent")}
        if reason is None and any(v is None for v in measurements.values()):
            reason = "unknown CPU/RAM/disk pressure"
        if reason is None and any(v >= hard_ceiling for v in measurements.values()):
            reason = "85% hardware admission ceiling reached"
        slots = node.get("available_slots")
        if reason is None and (type(slots) is not int or not 0 <= slots <= 128):
            reason = "no measured capacity slots"
        if reason is None and slots == 0:
            reason = "no unleased slots"
        lanes = node.get("capabilities")
        if reason is None and (not isinstance(lanes, list)
                               or not lanes or not all(isinstance(x, str) and x in LANES for x in lanes)):
            reason = "capability profile missing"
        if reason:
            excluded.append({"node_id": ident, "reason": reason})
            continue
        capacity = min(slots, 1) if any(v >= slowdown_at for v in measurements.values()) else slots
        healthy.append({"node_id": ident, "remaining": capacity,
                        "total": capacity, "capabilities": set(lanes),
                        "gpu": node.get("gpu_inference") is True,
                        "pressure": max(measurements.values())})
    selected = []
    deferred = []
    seen_tasks = set()
    prepared = []
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError("task record must be a dict")
        ident = str(task.get("task_id") or "").strip()
        if not ident or ident in seen_tasks:
            raise ValueError("task ID missing or duplicate")
        seen_tasks.add(ident)
        rishi = str(task.get("rishi_id") or "").strip()
        lane = task.get("kind")
        if rishi not in council:
            deferred.append({"task_id": ident, "reason": "unknown Rishi specialist"})
            continue
        if lane not in LANES:
            deferred.append({"task_id": ident, "reason": "unsupported research lane"})
            continue
        if task.get("approved") is not True:
            deferred.append({"task_id": ident, "reason": "not owner-approved"})
            continue
        if task.get("status") != "queued":
            deferred.append({"task_id": ident, "reason": "not queued"})
            continue
        prio = task.get("priority", 0)
        if type(prio) is not int or not 0 <= prio <= 100:
            deferred.append({"task_id": ident, "reason": "invalid priority"})
            continue
        prepared.append((prio, ident, rishi, lane, task.get("requires_gpu") is True))

    # Priority first. Equal priority dynamically balances across Rishis instead
    # of assigning permanent specialist ownership to individual machines.
    assigned_per_rishi = {}
    remaining = sorted(prepared, key=lambda t: (-t[0], t[1]))
    while remaining:
        priority = remaining[0][0]
        peers = [t for t in remaining if t[0] == priority]
        task = min(peers, key=lambda t: (assigned_per_rishi.get(t[2], 0), t[1]))
        remaining.remove(task)
        _, task_id, rishi, lane, gpu_required = task
        candidates = [node for node in healthy
                      if node["remaining"] > 0
                      and lane in node["capabilities"]
                      and (not gpu_required or node["gpu"])]
        if not candidates:
            deferred.append({"task_id": task_id,
                             "reason": "no healthy eligible capacity; retain in central queue"})
            continue
        node = min(candidates, key=lambda n: (
            (n["total"] - n["remaining"]) / n["total"],
            n["pressure"], n["node_id"]))
        node["remaining"] -= 1
        assigned_per_rishi[rishi] = assigned_per_rishi.get(rishi, 0) + 1
        selected.append({"task_id": task_id, "rishi_id": rishi,
                         "node_id": node["node_id"], "kind": lane,
                         "dispatch_state": "proposed_not_leased"})

    return {"assignments": selected, "deferred": deferred,
            "eligible_nodes": len(healthy), "excluded_nodes": excluded,
            "rishi_count": len(council),
            "policy": "many-to-many planned placement only; requires BRAHMA lease and device authentication before dispatch",
            "hard_ceiling_percent": hard_ceiling,
            "slowdown_percent": slowdown_at}
