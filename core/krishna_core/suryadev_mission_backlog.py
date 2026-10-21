"""Fail-closed, durable KRISHNA-owned six-hour SURYADEV curriculum backlog.

Only an operator-supplied Core-side approved-curriculum.json can authorize
source URLs. This planner NEVER browses or launches a worker, never invents a
website, and never claims that six hours of unique content exist. The laptop
must independently validate approval and URLs before enqueueing.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from threading import RLock
import time
from urllib.parse import urlsplit

CATALOG_SCHEMA = "krishna.suryadev.approved-curriculum.v1"
PROTOCOL = "krishna.suryadev.six-hour-mission.v1"
MAX_READY = 2
MAX_ITEMS = 200


class SuryadevMissionBacklog:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.catalogue = self.root / "approved-curriculum.json"
        self.state_file = self.root / "mission-backlog.json"
        self.lock = RLock()

    @staticmethod
    def _atomic(path, payload):
        temp = path.with_name(path.name + ".tmp")
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)

    def _catalogue(self):
        if not self.catalogue.is_file():
            return [], "operator_approved_curriculum_missing"
        data = json.loads(self.catalogue.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("schema") != CATALOG_SCHEMA:
            raise ValueError("invalid Core-approved SURYADEV catalogue schema")
        hosts = data.get("allowed_source_hosts", [])
        items = data.get("missions", [])
        if not isinstance(hosts, list) or not isinstance(items, list):
            raise ValueError("curriculum hosts and missions must be arrays")
        if len(hosts) > 100 or not 1 <= len(items) <= MAX_ITEMS:
            raise ValueError("approved curriculum bounds exceeded")
        allowed = set()
        for host in hosts:
            if (not isinstance(host, str) or not host or host != host.lower()
                    or len(host) > 253 or "/" in host or ":" in host or
                    host.startswith(".") or host.endswith(".")):
                raise ValueError("invalid approved source host")
            allowed.add(host)
        validated = []
        ids = set()
        for entry in items:
            if not isinstance(entry, dict):
                raise ValueError("mission entries must be objects")
            mid = entry.get("id")
            topic = entry.get("topic")
            urls = entry.get("approved_urls")
            if not isinstance(mid, str) or not 1 <= len(mid) <= 80 or not all(
                    ch.isalnum() or ch in "_-" for ch in mid):
                raise ValueError("invalid mission identifier")
            if mid in ids:
                raise ValueError("duplicate curriculum mission identifier")
            ids.add(mid)
            if not isinstance(topic, str) or not 3 <= len(topic.strip()) <= 200:
                raise ValueError("invalid curriculum topic")
            if not isinstance(urls, list) or not 1 <= len(urls) <= 20:
                raise ValueError("curriculum requires 1..20 explicitly approved URLs")
            checked = []
            for url in urls:
                if not isinstance(url, str) or len(url) > 2048:
                    raise ValueError("invalid approved URL")
                parsed = urlsplit(url)
                if (parsed.scheme != "https" or not parsed.hostname or
                        parsed.hostname not in allowed or parsed.username or
                        parsed.password or parsed.port not in (None, 443) or
                        parsed.fragment):
                    raise ValueError("curriculum URL is not on an exact approved HTTPS host")
                checked.append(url)
            validated.append({"id": mid, "topic": topic.strip(),
                              "approved_urls": list(dict.fromkeys(checked)),
                              "duration_hours": 6,
                              "instructions": "Research using only locally approved sources; preserve provenance and evidence. No source or reading-time claim without proof."})
        return validated, "approved"

    def _load(self):
        if not self.state_file.is_file():
            return {"schema": PROTOCOL, "used": [], "prepared": [], "offers": {}}
        state = json.loads(self.state_file.read_text(encoding="utf-8"))
        if not isinstance(state, dict) or state.get("schema") != PROTOCOL:
            raise ValueError("invalid persisted SURYADEV mission state")
        if (not isinstance(state.get("used"), list) or
                not isinstance(state.get("prepared"), list) or
                not isinstance(state.get("offers"), dict)):
            raise ValueError("mission state is corrupt")
        return state

    @staticmethod
    def _refill(state, curriculum):
        known = set(state["used"]) | set(state["prepared"])
        for value in state["offers"].values():
            if isinstance(value, dict) and isinstance(value.get("mission_id"), str):
                known.add(value["mission_id"])
        for entry in curriculum:
            if len(state["prepared"]) >= MAX_READY:
                break
            if entry["id"] not in known:
                state["prepared"].append(entry["id"])
                known.add(entry["id"])

    def status(self):
        with self.lock:
            curriculum, policy = self._catalogue()
            state = self._load()
            self._refill(state, curriculum)
            self._atomic(self.state_file, state)
            return {"source_policy": policy, "prepared": len(state["prepared"]),
                    "issued": len(state["used"]), "total_authorized": len(curriculum),
                    "mission_duration_hours": 6,
                    "guarantees_six_hours_of_unique_content": False}

    def offer(self, request, *, device_id):
        """Idempotently offer one approved packet. Never claim Core->laptop ACK."""
        if not isinstance(request, dict) or request.get("desired_hours") != 6:
            raise ValueError("a six-hour renewal request is required")
        rid = request.get("request_id")
        if not isinstance(rid, str) or len(rid) != 32 or any(
                ch not in "0123456789abcdef" for ch in rid):
            raise ValueError("invalid renewal request ID")
        if not isinstance(device_id, str) or not 1 <= len(device_id) <= 200:
            raise ValueError("paired device identity required")
        with self.lock:
            curriculum, policy = self._catalogue()
            state = self._load()
            self._refill(state, curriculum)
            if rid in state["offers"]:
                offer = state["offers"][rid]
                if offer.get("device_id") != device_id:
                    raise PermissionError("renewal request belongs to another paired device")
                mission = next((row for row in curriculum
                                if row["id"] == offer["mission_id"]), None)
                if mission is None:
                    raise RuntimeError("previously offered curriculum was removed; require manual review")
                digest = hashlib.sha256(json.dumps(mission, sort_keys=True).encode("utf-8")).hexdigest()
                if offer.get("mission_sha256") != digest:
                    raise RuntimeError("offered curriculum changed since first delivery; require manual review")
                return {"status": "offered", "mission": mission,
                        "request_id": rid, "delivery_acknowledged": bool(offer.get("acknowledged")),
                        "replay": True}
            if not state["prepared"]:
                return {"status": "no_approved_work", "request_id": rid,
                        "source_policy": policy, "prepared": 0,
                        "delivery_acknowledged": False}
            mid = state["prepared"].pop(0)
            mission = next(row for row in curriculum if row["id"] == mid)
            state["offers"][rid] = {"mission_id": mid, "device_id": device_id,
                                    "mission_sha256": hashlib.sha256(
                                        json.dumps(mission, sort_keys=True).encode("utf-8")).hexdigest(),
                                    "issued_at": time.time(), "acknowledged": False}
            state["used"].append(mid)
            self._refill(state, curriculum)
            self._atomic(self.state_file, state)
            return {"status": "offered", "mission": mission, "request_id": rid,
                    "delivery_acknowledged": False, "replay": False}

    def acknowledge(self, *, request_id, device_id, accepted, queued_urls=0):
        if not isinstance(accepted, bool) or not isinstance(queued_urls, int) or not 0 <= queued_urls <= 20:
            raise ValueError("invalid mission delivery receipt")
        with self.lock:
            state = self._load()
            offer = state["offers"].get(request_id)
            if not isinstance(offer, dict):
                raise ValueError("unknown mission request")
            if offer.get("device_id") != device_id:
                raise PermissionError("mission receipt paired device mismatch")
            if offer.get("acknowledged"):
                return {"acknowledged": True, "idempotent": True, "request_id": request_id}
            if not accepted or queued_urls == 0:
                return {"acknowledged": False, "reason": "no_new_approved_sources",
                        "request_id": request_id}
            offer["acknowledged"] = True
            offer["queued_urls"] = queued_urls
            offer["acknowledged_at"] = time.time()
            self._atomic(self.state_file, state)
            return {"acknowledged": True, "idempotent": False, "request_id": request_id,
                    "knowledge_accepted": False, "brahmagyan_acknowledged": False}
