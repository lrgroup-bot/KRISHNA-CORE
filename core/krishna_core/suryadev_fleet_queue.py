"""Durable, fail-closed BRAHMA research task leases for the SURYADEV fleet.

Only explicit owner-approved source tasks are eligible. This is a dispatch
ledger, not a model, knowledge store or free-form remote command facility.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
from threading import RLock
import time
from urllib.parse import urlsplit

from .suryadev_fleet_policy import plan_rishi_collection

SCHEMA = "krishna.suryadev.fleet-queue.v1"
LEASE_SECONDS = 300
MAX_TASKS = 2000
MAX_ATTEMPTS = 4


class SuryadevFleetQueue:
    def __init__(self, root, *, clock=time.time):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.file = self.root / "fleet-tasks.json"
        self.lock = RLock()
        self.clock = clock

    def _load(self):
        if not self.file.is_file():
            return {"schema": SCHEMA, "tasks": {}}
        state = json.loads(self.file.read_text(encoding="utf-8"))
        if (not isinstance(state, dict) or state.get("schema") != SCHEMA
                or not isinstance(state.get("tasks"), dict)):
            raise RuntimeError("SURYDEV fleet task state corrupt; refusing overwrite")
        return state

    def _save(self, state):
        target = self.file.with_suffix(".tmp")
        with target.open("w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(target, self.file)

    @staticmethod
    def _valid_source(url):
        if not isinstance(url, str) or len(url) > 2048:
            raise ValueError("approved HTTPS source URL required")
        p = urlsplit(url)
        if (p.scheme != "https" or not p.hostname or p.username or p.password
                or p.port not in (None, 443) or p.fragment):
            raise ValueError("source must be an approved HTTPS URL without credentials or fragment")
        return url

    def enqueue(self, *, mission_id, task_id, rishi_id, kind, url, priority,
                approved_urls, council_ids):
        """Only local KRISHNA operator/authorized caller may invoke enqueue."""
        if (not isinstance(mission_id, str) or not 1 <= len(mission_id) <= 100
                or not isinstance(task_id, str) or not 1 <= len(task_id) <= 100
                or any(not (c.isalnum() or c in "-_") for c in task_id)):
            raise ValueError("valid mission and task identifiers required")
        if rishi_id not in set(council_ids) or kind not in {"website", "youtube", "pdf"}:
            raise ValueError("registered Rishi and supported collection kind required")
        if type(priority) is not int or not 0 <= priority <= 100:
            raise ValueError("priority must be 0..100")
        url = self._valid_source(url)
        if url not in set(approved_urls):
            raise PermissionError("source URL is not explicitly approved in Core curriculum")
        from urllib.parse import urlsplit as split
        from pathlib import PurePosixPath
        host = split(url).hostname
        if kind == "youtube":
            if host not in {"youtube.com","www.youtube.com","m.youtube.com","youtu.be","www.youtu.be"}:
                raise ValueError("YouTube task must refer to the YouTube host")
        elif host in {"youtube.com","www.youtube.com","m.youtube.com","youtu.be","www.youtu.be"}:
            raise ValueError("YouTube source type mismatch")
        elif (PurePosixPath(split(url).path.lower()).suffix == ".pdf") != (kind == "pdf"):
            raise ValueError("PDF/website source type mismatch")
        now = float(self.clock())
        row = {"task_id": task_id, "mission_id": mission_id, "rishi_id": rishi_id,
               "kind": kind, "url": url, "priority": priority,
               "approved": True, "status": "queued", "attempts": 0,
               "created_at": now, "updated_at": now}
        with self.lock:
            state = self._load()
            if task_id in state["tasks"]:
                existing = state["tasks"][task_id]
                identity = ("task_id", "mission_id", "rishi_id", "kind", "url", "priority")
                if any(existing.get(k) != row[k] for k in identity):
                    raise RuntimeError("same task ID has different source or authority")
                return {"task": dict(existing), "idempotent": True}
            if len(state["tasks"]) >= MAX_TASKS:
                raise RuntimeError("fleet task capacity reached; archive under owner control")
            state["tasks"][task_id] = row
            self._save(state)
        return {"task": dict(row), "idempotent": False}

    def _expire(self, state, now):
        changed = False
        for task in state["tasks"].values():
            if task["status"] == "leased" and float(task.get("expires_at") or 0) <= now:
                task.pop("lease_token", None)
                task.pop("device_id", None)
                task.pop("expires_at", None)
                task["status"] = "failed" if task["attempts"] >= MAX_ATTEMPTS else "queued"
                task["last_error"] = "lease expired; local completion not acknowledged"
                task["updated_at"] = now
                changed = True
        return changed

    def offer(self, *, device_id, nodes, council_ids):
        now = float(self.clock())
        with self.lock:
            state = self._load()
            modified = self._expire(state, now)
            # Replay active lease before proposing new work. Polling never
            # changes lease owner or creates duplicate task attempts.
            active = sorted((t for t in state["tasks"].values()
                             if t["status"] == "leased" and t.get("device_id") == device_id),
                            key=lambda t: t["created_at"])
            if active:
                if modified: self._save(state)
                return {"status": "leased", "lease": dict(active[0]),
                        "replayed": True}
            tasks = [dict(t) for t in state["tasks"].values() if t["status"] == "queued"]
            planned = plan_rishi_collection(tasks, nodes, council_ids=council_ids, now=now)
            candidate = next((x for x in planned["assignments"]
                              if x["node_id"] == device_id), None)
            if candidate is None:
                if modified: self._save(state)
                return {"status": "no_eligible_work", "replayed": False,
                        "deferred_count": len(planned["deferred"])}
            row = state["tasks"][candidate["task_id"]]
            row["status"] = "leased"
            row["device_id"] = device_id
            row["lease_token"] = secrets.token_hex(24)
            row["expires_at"] = now + LEASE_SECONDS
            row["attempts"] += 1
            row["updated_at"] = now
            self._save(state)
            return {"status": "leased", "lease": dict(row), "replayed": False}

    @staticmethod
    def _require_lease(row, *, device_id, lease_token, now):
        if (row.get("status") != "leased" or row.get("device_id") != device_id
                or not isinstance(lease_token,str) or
                not hmac.compare_digest(row.get("lease_token") or "", lease_token)):
            raise PermissionError("task does not have a matching device lease")
        if float(row.get("expires_at") or 0) <= now:
            raise RuntimeError("task lease expired; fetch a new lease")

    def renew(self, task_id, *, device_id, lease_token):
        now = float(self.clock())
        with self.lock:
            state = self._load()
            row = state["tasks"].get(task_id)
            if not row: raise KeyError(task_id)
            self._require_lease(row, device_id=device_id, lease_token=lease_token, now=now)
            row["expires_at"] = now + LEASE_SECONDS
            row["updated_at"] = now
            self._save(state)
            return {"renewed": True, "task_id": task_id, "expires_at": row["expires_at"]}

    def complete(self, task_id, *, device_id, lease_token, outcome,
                 evidence_sha256="", error=""):
        now = float(self.clock())
        with self.lock:
            state = self._load()
            row = state["tasks"].get(task_id)
            if not row: raise KeyError(task_id)
            if row["status"] in ("done", "failed") and row.get("completion_device") == device_id:
                same = (row.get("completed_lease_token") == hashlib.sha256(lease_token.encode()).hexdigest()
                        and row.get("outcome") == outcome
                        and row.get("evidence_sha256","") == evidence_sha256)
                if not same: raise RuntimeError("conflicting completed task receipt")
                return {"acknowledged": True, "idempotent": True, "task_id": task_id,
                        "status": row["status"], "knowledge_verified": False}
            self._require_lease(row,device_id=device_id,lease_token=lease_token,now=now)
            if outcome not in {"done", "failed"}:
                raise ValueError("completion outcome must be done or failed")
            if outcome == "done":
                if (not isinstance(evidence_sha256,str) or len(evidence_sha256)!=64
                        or any(c not in "0123456789abcdef" for c in evidence_sha256)):
                    raise ValueError("completed evidence must have exact SHA-256")
            elif not isinstance(error,str) or not error.strip():
                raise ValueError("failed task must include an error")
            row["status"] = outcome
            row["outcome"] = outcome
            row["evidence_sha256"] = evidence_sha256 if outcome == "done" else ""
            row["last_error"] = str(error)[:300] if outcome == "failed" else ""
            row["completion_device"] = device_id
            row["completed_lease_token"] = hashlib.sha256(lease_token.encode()).hexdigest()
            row["completed_at"] = now
            row["updated_at"] = now
            row.pop("lease_token", None)
            row.pop("expires_at", None)
            self._save(state)
            return {"acknowledged": True, "idempotent": False, "task_id": task_id,
                    "status": outcome, "knowledge_verified": False,
                    "brahmagyan_accepted": False}

    def status(self):
        with self.lock:
            state = self._load()
            counts = {s: 0 for s in ("queued", "leased", "done", "failed")}
            for t in state["tasks"].values():
                counts[t["status"]] += 1
            return {"schema": SCHEMA, "total": len(state["tasks"]),
                    "counts": counts,
                    "warning": "Completion acknowledges collected evidence only, not comprehension or BRAHMAGYAN acceptance"}
