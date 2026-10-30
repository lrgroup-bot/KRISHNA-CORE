"""Owner-approved SURYADEV fleet task leases.

Only the existing validated six-hour Core curriculum can supply URLs. This
ledger never browses, runs code, creates new source approvals or certifies
knowledge. Every operation is protected by the Core's paired-device API.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from threading import RLock
import time
import uuid
from urllib.parse import urlsplit
from pathlib import PurePosixPath

from .suryadev_fleet_policy import plan_rishi_collection

SCHEMA = "krishna.suryadev.fleet-leases.v1"
LEASE_SECONDS = 600
MAX_ATTEMPTS = 3
MAX_ACTIVE_PER_NODE = 125


class SuryadevFleetService:
    def __init__(self, root, *, curriculum, council, node_reader, clock=time.time):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.file = self.root / "fleet-leases.json"
        self.curriculum = curriculum
        self.council = council
        self.node_reader = node_reader
        self.clock = clock
        self.lock = RLock()

    def _load(self):
        if not self.file.exists():
            return {"schema": SCHEMA, "leases": {}, "receipts": {},
                    "attempts": {}, "rejected_by": {}, "failures": {},
                    "youtube_pause_until": 0}
        state = json.loads(self.file.read_text(encoding="utf-8"))
        if not isinstance(state, dict) or state.get("schema") != SCHEMA:
            raise ValueError("corrupt SURYADEV fleet ledger; refusing overwrite")
        for key in ("leases", "receipts", "attempts", "rejected_by", "failures"):
            if not isinstance(state.get(key), dict):
                raise ValueError("corrupt SURYADEV fleet ledger: " + key)
        return state

    def _save(self, state):
        tmp = self.file.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, self.file)

    def _tasks(self):
        curricula, policy = self.curriculum._catalogue()
        if policy != "approved":
            return {}
        tasks = {}
        for item in curricula:
            rishi = self.council.select(item["topic"], 1)[0]["id"]
            for url in item["approved_urls"]:
                task_id = "fleet-" + hashlib.sha256(
                    json.dumps([item["id"], url], separators=(",", ":")).encode()
                ).hexdigest()[:28]
                parsed = urlsplit(url)
                host = (parsed.hostname or "").lower()
                kind = ("youtube" if host in {
                    "youtube.com", "www.youtube.com", "m.youtube.com",
                    "youtu.be", "www.youtu.be"}
                    else "pdf" if PurePosixPath(parsed.path.lower()).suffix == ".pdf"
                    else "website")
                tasks[task_id] = {"task_id": task_id, "mission_id": item["id"],
                                  "rishi_id": rishi, "url": url, "kind": kind,
                                  "topic": item["topic"]}
        return tasks

    def _eligible(self, device_id, now, node, active):
        if not isinstance(node, dict) or node.get("device_id") != device_id:
            return False
        profile = dict(node)
        # Paired status originates ONLY at the verified Core API boundary.
        # A fabricated local heartbeat may not obtain fleet work.
        if profile.get("authenticated") is not True:
            return False
        capacity = profile.get("available_slots")
        if type(capacity) is not int:
            return False
        profile["available_slots"] = min(MAX_ACTIVE_PER_NODE, max(0, capacity - active))
        # A node enrolled solely for video must not fail a hardcoded
        # website-only eligibility probe. Check its ACTUAL reported lane.
        allowed = {"website", "youtube", "pdf", "book", "experiment"}
        lane = next((kind for kind in (profile.get("capabilities") or [])
                     if kind in allowed), None)
        if lane is None:
            return False
        sample = [{"task_id": "__probe__", "rishi_id": self.council.list()[0]["id"],
                   "kind": lane, "priority": 0, "status": "queued",
                   "approved": True}]
        result = plan_rishi_collection(sample, [profile],
            council_ids=[row["id"] for row in self.council.list()], now=now)
        return result["eligible_nodes"] == 1

    @staticmethod
    def _renewal_healthy(device_id, now, node):
        """An in-flight lease can renew during resource pressure, but only
        for a fresh, owner-paired and running worker."""
        if not isinstance(node, dict):
            return False
        if (node.get("device_id") != device_id or
                node.get("authenticated") is not True or
                node.get("worker_running") is not True or
                node.get("network_online") is not True or node.get("last_error")):
            return False
        for field, ttl in (("last_seen", 150), ("telemetry_sample_at", 45)):
            value = node.get(field)
            if type(value) not in (int, float) or not 0 <= now - value <= ttl:
                return False
        return True

    def status(self):
        with self.lock:
            state = self._load()
            tasks = self._tasks()
            now = self.clock()
            active = sum(x.get("expires_at", 0) > now and tid in tasks
                         for tid, x in state["leases"].items())
            return {"catalogue_tasks": len(tasks), "collected": sum(tid in tasks for tid in state["receipts"]),
                    "active_leases": active, "retry_exhausted": sum(
                        state["attempts"].get(tid, 0) >= MAX_ATTEMPTS and tid not in state["receipts"]
                        for tid in tasks),
                    "queued_estimate": sum(
                        tid not in state["receipts"] and
                        state["attempts"].get(tid, 0) < MAX_ATTEMPTS and
                        (tid not in state["leases"] or state["leases"][tid].get("expires_at", 0) <= now)
                        for tid in tasks),
                    "knowledge_verified": False,
                    "youtube_pause_until": state.get("youtube_pause_until",0),
                    "protocol": SCHEMA,
                    "source_policy": "owner-approved Core curriculum only"}

    def claim(self, *, device_id, known_task_ids=None):
        if known_task_ids is None:
            known_task_ids = []
        if (not isinstance(known_task_ids,list) or len(known_task_ids)>MAX_ACTIVE_PER_NODE
                or any(not isinstance(t,str) or len(t)>100 for t in known_task_ids)):
            raise ValueError("known_task_ids must be a bounded list")
        known = set(known_task_ids)
        now = float(self.clock())
        with self.lock:
            tasks = self._tasks()
            state = self._load()
            active = [(tid, lease) for tid, lease in state["leases"].items()
                      if lease.get("expires_at", 0) > now and tid in tasks]
            owned = [(tid, lease) for tid, lease in active if lease.get("device_id") == device_id]
            try:
                node = self.node_reader(device_id)
            except KeyError:
                return {"status": "no_eligible_capacity", "reason": "device heartbeat missing"}
            # A replay is an opportunity to resume work, not a bypass around
            # pairing/fresh-heartbeat checks. Pressure is allowed for an
            # already-held lease, but missing/offline/unpaired workers are not.
            if owned and not self._renewal_healthy(device_id, now, node):
                return {"status": "no_eligible_capacity",
                        "reason": "lease owner heartbeat is stale, offline or unpaired"}
            for tid, lease in owned:
                # Client crashed before persisting claim? Replay the still-owned
                # lease. Once it reports a durable local job, offer a next slot.
                if tid not in known:
                    return {"status": "leased", "task": tasks[tid], "lease_id": lease["lease_id"],
                            "expires_at": lease["expires_at"], "replay": True}
            if not self._eligible(device_id, now, node, len(owned)):
                return {"status": "no_eligible_capacity", "reason": "paired node hardware admission refused"}
            occupied = {tid for tid, _ in active}
            candidates = [task for tid, task in tasks.items()
                          if tid not in occupied and tid not in state["receipts"]
                          and state["attempts"].get(tid, 0) < MAX_ATTEMPTS
                          and device_id not in state["rejected_by"].get(tid, [])]
            capabilities = node.get("capabilities") or []
            candidates = [task for task in candidates
                          if task["kind"] in capabilities
                          and not (task["kind"]=="youtube" and
                                   now < float(state.get("youtube_pause_until") or 0))]
            if not candidates:
                return {"status": "no_approved_work", "pending_claimable": 0}
            # Balance among Rishis by finished-plus-active assignments.
            totals = {}
            for tid in set(state["receipts"]) | occupied:
                task = tasks.get(tid)
                if task:
                    totals[task["rishi_id"]] = totals.get(task["rishi_id"], 0) + 1
            # Reassign expired, unacknowledged work before opening fresh
            # research. The previous node can no longer complete its old lease.
            expired = {tid for tid, lease in state["leases"].items()
                       if lease.get("expires_at",0) <= now and tid not in state["receipts"]}
            # A specialist-only video node can process the video queue.
            # A generalist prefers non-video tasks while those exist, so a
            # heterogeneous fleet naturally allocates video to video-capable
            # specialists without hardcoding a permanent node number.
            is_generalist = len(set(capabilities) & {"website","pdf","book"}) > 0
            chosen = min(candidates, key=lambda x: (
                0 if x["task_id"] in expired else 1,
                int(is_generalist and x["kind"] == "youtube"),
                totals.get(x["rishi_id"], 0), state["attempts"].get(x["task_id"], 0),
                x["mission_id"], x["task_id"]))
            tid = chosen["task_id"]
            lease = {"lease_id": uuid.uuid4().hex, "device_id": device_id,
                     "issued_at": now, "expires_at": now + LEASE_SECONDS}
            state["leases"][tid] = lease
            state["attempts"][tid] = state["attempts"].get(tid, 0) + 1
            self._save(state)
            return {"status": "leased", "task": chosen, "lease_id": lease["lease_id"],
                    "expires_at": lease["expires_at"], "replay": False}

    def renew(self, *, device_id, task_id, lease_id):
        now = float(self.clock())
        with self.lock:
            state = self._load()
            if task_id not in self._tasks():
                raise ValueError("unknown or revoked approved task")
            lease = state["leases"].get(task_id)
            if (not lease or lease.get("device_id") != device_id or
                    lease.get("lease_id") != lease_id or lease["expires_at"] <= now):
                raise PermissionError("expired or mismatched fleet lease")
            node = self.node_reader(device_id)
            # Hardware headroom controls NEW work, not completion of an owned lease.
            if not self._renewal_healthy(device_id, now, node):
                raise PermissionError("lease owner heartbeat is stale, offline or unpaired")
            lease["expires_at"] = now + LEASE_SECONDS
            self._save(state)
            return {"renewed": True, "task_id": task_id,
                    "lease_id": lease_id, "expires_at": lease["expires_at"]}

    def complete(self, *, device_id, task_id, lease_id, outcome, evidence_sha256="", detail="", source_excerpt="", locator=None):
        now = float(self.clock())
        if outcome not in {"collected", "failed", "rejected", "rate_limited"}:
            raise ValueError("invalid collection outcome")
        if not isinstance(source_excerpt,str) or len(source_excerpt)>700:
            raise ValueError("fleet source excerpt must be <=700 characters")
        if locator is not None and (not isinstance(locator,dict)
                or any(k not in ("page","section","start_seconds","end_seconds","line_start","line_end","url_fragment")
                       for k in locator)):
            raise ValueError("only measured source locator fields permitted")
        if outcome == "collected" and (not isinstance(evidence_sha256, str)
                or len(evidence_sha256) != 64 or any(c not in "0123456789abcdef" for c in evidence_sha256)):
            raise ValueError("collected evidence requires SHA-256")
        with self.lock:
            tasks = self._tasks()
            if task_id not in tasks:
                raise ValueError("unknown or revoked approved task")
            state = self._load()
            existing = state["receipts"].get(task_id)
            if existing:
                if (existing["device_id"] == device_id and
                        existing["lease_id"] == lease_id and existing["evidence_sha256"] == evidence_sha256
                        and outcome == "collected"):
                    return {"acknowledged": True, "idempotent": True, "receipt": existing}
                raise PermissionError("task was already completed under a different lease")
            lease = state["leases"].get(task_id)
            if (not lease or lease.get("device_id") != device_id or
                    lease.get("lease_id") != lease_id or lease["expires_at"] <= now):
                raise PermissionError("fleet completion requires active owned lease")
            if outcome == "collected":
                receipt = {"task_id": task_id, "device_id": device_id,
                           "lease_id": lease_id, "source_url": tasks[task_id]["url"],
                           "rishi_id": tasks[task_id]["rishi_id"],
                           "mission_id":tasks[task_id]["mission_id"],
                           "topic":tasks[task_id]["topic"],
                           "kind":tasks[task_id]["kind"],
                           "evidence_sha256": evidence_sha256, "received_at": now,
                           "source_evidence_unverified": True, "brahmagyan_accepted": False,
                           "source_excerpt": source_excerpt[:700],
                           "untrusted_source_text": True,
                           "locator":dict(locator or {})}
                state["receipts"][task_id] = receipt
            elif outcome == "rejected":
                state["rejected_by"].setdefault(task_id, [])
                if device_id not in state["rejected_by"][task_id]:
                    state["rejected_by"][task_id].append(device_id)
            else:
                state["failures"].setdefault(task_id, []).append(
                    {"device_id": device_id, "at": now, "outcome": outcome,
                     "detail": str(detail)[:300]})
                if outcome == "rate_limited" and tasks[task_id]["kind"] == "youtube":
                    state["youtube_pause_until"] = max(
                        float(state.get("youtube_pause_until") or 0), now+3600)
                if outcome == "failed":
                    state["rejected_by"].setdefault(task_id, [])
                    if device_id not in state["rejected_by"][task_id]:
                        state["rejected_by"][task_id].append(device_id)
            del state["leases"][task_id]
            self._save(state)
            return {"acknowledged": True, "idempotent": False,
                    "outcome": outcome, "receipt": state["receipts"].get(task_id),
                    "brahmagyan_accepted": False}
