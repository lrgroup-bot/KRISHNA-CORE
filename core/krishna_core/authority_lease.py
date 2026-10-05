from __future__ import annotations

"""Persistent, one-time owner authority leases for consequential KRISHNA actions.

A boolean supplied by a UI/API caller is intent, not authority.  AuthorityLeaseGate
binds owner approval to one exact action envelope (action/project/source/actor/payload),
expires it, consumes it once, and persists a global kill switch across restarts.
"""

from pathlib import Path
from threading import RLock
import hashlib
import json
import os
import time
import uuid


class AuthorityLeaseGate:
    VERSION = "krishna-authority-lease-v1"
    LIVE = {"PENDING", "APPROVED"}
    TERMINAL = {"DENIED", "CONSUMED", "EXPIRED", "REVOKED"}

    def __init__(self, state_root, *, audit=None, ttl_seconds=300, clock=None, initially_locked=True):
        self.root = Path(state_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "authority-leases.json"
        self.audit = audit
        self.ttl_seconds = max(1, min(int(ttl_seconds), 1800))
        self.clock = clock or time.time
        self.lock = RLock()
        if not self.path.exists():
            self._save({
                "version": self.VERSION,
                "kill_switch_engaged": bool(initially_locked),
                "kill_switch_reason": "initial safety lock" if initially_locked else "",
                "kill_switch_updated_at": self._now(),
                "leases": {},
            })
        else:
            self._load()  # fail closed on unreadable state

    def _now(self):
        return float(self.clock())

    @staticmethod
    def _clean(value, limit=1000):
        return str(value or "").strip()[:limit]

    @staticmethod
    def _digest(value):
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str,
                         separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @classmethod
    def scope(cls, *, action, project, source, actor, payload):
        return {
            "action": cls._clean(action, 300),
            "project": cls._clean(project, 300) or "KRISHNA",
            "source": cls._clean(source, 40).lower() or "pc",
            "actor": cls._clean(actor, 300) or "owner",
            "payload_digest": cls._digest(payload or {}),
        }

    @classmethod
    def scope_fingerprint(cls, **kwargs):
        return cls._digest(cls.scope(**kwargs))

    def _load(self):
        with self.lock:
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise RuntimeError(
                    f"authority lease state unreadable; fail-closed: {type(exc).__name__}: {exc}"
                ) from exc
            if not isinstance(data, dict) or data.get("version") != self.VERSION:
                raise RuntimeError("authority lease state invalid; fail-closed")
            if not isinstance(data.get("leases"), dict):
                raise RuntimeError("authority lease table invalid; fail-closed")
            if "kill_switch_engaged" not in data:
                raise RuntimeError("authority kill-switch state missing; fail-closed")
            return data

    def _save(self, state):
        with self.lock:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
            os.replace(tmp, self.path)

    def _audit(self, status, detail):
        if not self.audit:
            return
        try:
            self.audit("authority_lease", status, str(detail)[:12000])
        except Exception:
            pass

    def _expire(self, state):
        now = self._now()
        changed = False
        for row in state.get("leases", {}).values():
            if row.get("status") not in self.LIVE:
                continue
            if now >= float(row.get("expires_at") or 0):
                row["status"] = "EXPIRED"
                row["resolved_at"] = now
                changed = True
        if changed:
            self._save(state)
        return state

    def request(self, *, action, payload=None, project="KRISHNA", source="pc", actor="owner",
                reason="", ttl_seconds=None):
        action = self._clean(action, 300)
        if not action:
            raise ValueError("action is required")
        ttl = self.ttl_seconds if ttl_seconds is None else max(1, min(int(ttl_seconds), 1800))
        scope = self.scope(action=action, project=project, source=source, actor=actor, payload=payload)
        now = self._now()
        lease_id = "LEASE-" + uuid.uuid4().hex
        row = {
            "schema": self.VERSION,
            "lease_id": lease_id,
            **scope,
            "scope_fingerprint": self._digest(scope),
            "reason": self._clean(reason, 2000),
            "status": "PENDING",
            "created_at": now,
            "expires_at": now + ttl,
            "approved_at": None,
            "approved_by": None,
            "consumed_at": None,
            "resolved_at": None,
            "one_time": True,
        }
        state = self._expire(self._load())
        state["leases"][lease_id] = row
        self._save(state)
        self._audit("requested", f"{lease_id}:{action}:{scope['project']}:{scope['source']}:{scope['actor']}")
        return dict(row)

    def decide(self, lease_id, *, approved, approved_by="owner"):
        state = self._expire(self._load())
        row = state["leases"].get(str(lease_id))
        if not row:
            raise KeyError(lease_id)
        if row.get("status") != "PENDING":
            raise ValueError(f"authority lease is not pending: {row.get('status')}")
        now = self._now()
        if now >= float(row.get("expires_at") or 0):
            row["status"] = "EXPIRED"
            row["resolved_at"] = now
            self._save(state)
            raise PermissionError("authority lease expired")
        row["approved_by"] = self._clean(approved_by, 300) or "owner"
        row["resolved_at"] = now
        if approved:
            row["status"] = "APPROVED"
            row["approved_at"] = now
        else:
            row["status"] = "DENIED"
        self._save(state)
        self._audit(row["status"].lower(), f"{lease_id}:{row.get('action')}")
        return dict(row)

    def consume(self, lease_id, *, action, payload=None, project="KRISHNA", source="pc", actor="owner"):
        if not lease_id:
            raise PermissionError("authority lease required")
        with self.lock:
            state = self._expire(self._load())
            if bool(state.get("kill_switch_engaged")):
                raise PermissionError("KRISHNA authority kill switch is engaged")
            row = state["leases"].get(str(lease_id))
            if not row:
                raise PermissionError("authority lease not found")
            if row.get("status") != "APPROVED":
                raise PermissionError(f"authority lease not executable: {row.get('status')}")
            now = self._now()
            if now >= float(row.get("expires_at") or 0):
                row["status"] = "EXPIRED"
                row["resolved_at"] = now
                self._save(state)
                raise PermissionError("authority lease expired")
            expected = self.scope(action=action, project=project, source=source, actor=actor, payload=payload)
            expected_fp = self._digest(expected)
            if row.get("scope_fingerprint") != expected_fp:
                raise PermissionError("authority lease scope/payload mismatch")
            # Verify stored fields too, so a corrupted row cannot rely on fingerprint alone.
            for key, value in expected.items():
                if str(row.get(key) or "") != str(value):
                    raise PermissionError(f"authority lease scope mismatch: {key}")
            row["status"] = "CONSUMED"
            row["consumed_at"] = now
            row["resolved_at"] = now
            self._save(state)
        self._audit("consumed", f"{lease_id}:{row.get('action')}")
        return {
            "allowed": True,
            "lease_id": row["lease_id"],
            "scope_fingerprint": row["scope_fingerprint"],
            "approved_by": row.get("approved_by"),
            "approved_at": row.get("approved_at"),
            "consumed_at": row.get("consumed_at"),
        }

    def engage_kill_switch(self, reason="owner safety lock"):
        with self.lock:
            state = self._expire(self._load())
            now = self._now()
            state["kill_switch_engaged"] = True
            state["kill_switch_reason"] = self._clean(reason, 2000) or "owner safety lock"
            state["kill_switch_updated_at"] = now
            for row in state["leases"].values():
                if row.get("status") in self.LIVE:
                    row["status"] = "REVOKED"
                    row["resolved_at"] = now
            self._save(state)
        self._audit("kill_switch_engaged", state["kill_switch_reason"])
        return self.status()

    def disarm_kill_switch(self, *, approved_by="owner", reason="controlled readiness test"):
        with self.lock:
            state = self._expire(self._load())
            state["kill_switch_engaged"] = False
            state["kill_switch_reason"] = self._clean(reason, 2000)
            state["kill_switch_updated_at"] = self._now()
            state["kill_switch_disarmed_by"] = self._clean(approved_by, 300) or "owner"
            self._save(state)
        self._audit("kill_switch_disarmed", f"{state['kill_switch_disarmed_by']}:{state['kill_switch_reason']}")
        return self.status()

    def get(self, lease_id):
        state = self._expire(self._load())
        row = state["leases"].get(str(lease_id))
        if not row:
            raise KeyError(lease_id)
        return dict(row)

    def status(self):
        state = self._expire(self._load())
        rows = list(state["leases"].values())
        return {
            "component": "KRISHNA Authority Lease Gate",
            "version": self.VERSION,
            "kill_switch_engaged": bool(state.get("kill_switch_engaged")),
            "kill_switch_reason": state.get("kill_switch_reason") or "",
            "kill_switch_updated_at": state.get("kill_switch_updated_at"),
            "pending": len([x for x in rows if x.get("status") == "PENDING"]),
            "approved_waiting_use": len([x for x in rows if x.get("status") == "APPROVED"]),
            "consumed": len([x for x in rows if x.get("status") == "CONSUMED"]),
            "lease_count": len(rows),
            "default_ttl_seconds": self.ttl_seconds,
            "one_time": True,
            "payload_bound": True,
            "scope": ["action", "project", "source", "actor", "payload_digest"],
            "restart_persistent": True,
            "ready": True,
        }
