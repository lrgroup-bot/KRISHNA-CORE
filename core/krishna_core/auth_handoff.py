from __future__ import annotations

"""Owner-controlled authentication handoff tickets for external observer agents.

A ticket authorizes only a human handoff for one authentication checkpoint. It never
authorizes the agent to learn/store credentials, solve CAPTCHA, spoof liveness, or
reuse approval across jobs/origins.
"""

from pathlib import Path
import hashlib
import json
import os
import time
import uuid


class AuthenticationHandoffGate:
    VERSION = "external-auth-handoff-v1"
    AGENTS = {"suryadev", "chandradev"}
    METHODS = {"password", "mfa", "captcha", "liveness", "passkey", "device_auth", "other_auth"}
    TERMINAL = {"APPROVED", "DENIED", "CONSUMED", "EXPIRED"}

    def __init__(self, state_root, *, memory=None, ttl_seconds=600):
        self.root = Path(state_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "auth-handoffs.json"
        self.memory = memory
        self.ttl_seconds = max(60, min(int(ttl_seconds), 3600))

    def _load(self):
        if not self.path.is_file():
            return {"version": self.VERSION, "tickets": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("invalid auth handoff state")
            data.setdefault("tickets", {})
            return data
        except Exception as exc:
            raise RuntimeError(f"authentication handoff state unreadable: {type(exc).__name__}: {exc}") from exc

    def _save(self, state):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)

    @staticmethod
    def _clean(value, limit=1000):
        return str(value or "").strip()[:limit]

    @staticmethod
    def _fingerprint(value):
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _expire(self, state):
        now = time.time()
        changed = False
        for ticket in state.get("tickets", {}).values():
            if ticket.get("status") in self.TERMINAL:
                continue
            if now >= float(ticket.get("expires_at") or 0):
                ticket["status"] = "EXPIRED"
                ticket["resolved_at"] = now
                changed = True
        if changed:
            self._save(state)
        return state

    def request(self, *, agent, job_id, origin, method, reason="", checkpoint_ref=""):
        agent = self._clean(agent, 40).lower()
        method = self._clean(method, 40).lower()
        if agent not in self.AGENTS:
            raise ValueError("unsupported authentication handoff agent")
        if method not in self.METHODS:
            raise ValueError("unsupported authentication method")
        job_id = self._clean(job_id, 200)
        origin = self._clean(origin, 1000)
        if not job_id or not origin:
            raise ValueError("job_id and origin are required")

        now = time.time()
        request_id = "AUTH-" + uuid.uuid4().hex[:20]
        row = {
            "schema": "krishna.external-auth-handoff.v1",
            "request_id": request_id,
            "agent": agent,
            "job_id": job_id,
            "origin": origin,
            "method": method,
            "reason": self._clean(reason, 2000),
            "checkpoint_ref": self._clean(checkpoint_ref, 500),
            "status": "OWNER_APPROVAL_REQUIRED",
            "created_at": now,
            "expires_at": now + self.ttl_seconds,
            "resolved_at": None,
            "approved_by": None,
            "grant_id": None,
            "grant_consumed_at": None,
            "policy": {
                "one_time": True,
                "origin_scoped": True,
                "job_scoped": True,
                "credential_capture": False,
                "secret_storage": False,
                "captcha_solving": False,
                "liveness_spoofing": False,
                "meaning_of_approval": "allow authorized human to take over this specific checkpoint",
            },
        }
        row["fingerprint"] = self._fingerprint({
            "agent": agent,
            "job_id": job_id,
            "origin": origin,
            "method": method,
            "checkpoint_ref": row["checkpoint_ref"],
        })
        state = self._expire(self._load())
        state["tickets"][request_id] = row
        self._save(state)
        if self.memory:
            self.memory.audit(
                "external_auth_handoff",
                "owner_approval_required",
                f"{agent}:{job_id}:{method}:{request_id}",
            )
        return dict(row)

    def decide(self, request_id, *, approved, approved_by="owner"):
        state = self._expire(self._load())
        row = state["tickets"].get(str(request_id))
        if not row:
            raise KeyError(request_id)
        if row.get("status") != "OWNER_APPROVAL_REQUIRED":
            raise ValueError(f"authentication request is not pending: {row.get('status')}")
        now = time.time()
        if now >= float(row.get("expires_at") or 0):
            row["status"] = "EXPIRED"
            row["resolved_at"] = now
            self._save(state)
            raise PermissionError("authentication handoff request expired")

        row["resolved_at"] = now
        row["approved_by"] = self._clean(approved_by, 200) or "owner"
        if approved:
            row["status"] = "APPROVED"
            row["grant_id"] = "AUTH-GRANT-" + uuid.uuid4().hex[:18]
        else:
            row["status"] = "DENIED"
            row["grant_id"] = None
        self._save(state)
        if self.memory:
            self.memory.audit(
                "external_auth_handoff",
                row["status"].lower(),
                f"{row['agent']}:{row['job_id']}:{row['method']}:{request_id}",
            )
        return dict(row)

    def consume(self, request_id, *, agent, job_id, origin, method):
        state = self._expire(self._load())
        row = state["tickets"].get(str(request_id))
        if not row:
            raise KeyError(request_id)
        if row.get("status") != "APPROVED":
            raise PermissionError(f"authentication handoff not approved: {row.get('status')}")
        expected = {
            "agent": self._clean(agent, 40).lower(),
            "job_id": self._clean(job_id, 200),
            "origin": self._clean(origin, 1000),
            "method": self._clean(method, 40).lower(),
        }
        for key, value in expected.items():
            if str(row.get(key) or "") != value:
                raise PermissionError(f"authentication approval scope mismatch: {key}")
        if time.time() >= float(row.get("expires_at") or 0):
            row["status"] = "EXPIRED"
            row["resolved_at"] = time.time()
            self._save(state)
            raise PermissionError("authentication handoff approval expired")

        row["status"] = "CONSUMED"
        row["grant_consumed_at"] = time.time()
        self._save(state)
        if self.memory:
            self.memory.audit(
                "external_auth_handoff",
                "consumed",
                f"{row['agent']}:{row['job_id']}:{row['method']}:{request_id}",
            )
        return {
            "allowed": True,
            "request_id": row["request_id"],
            "grant_id": row["grant_id"],
            "agent": row["agent"],
            "job_id": row["job_id"],
            "origin": row["origin"],
            "method": row["method"],
            "action": "HUMAN_HANDOFF_ALLOWED",
            "credential_capture": False,
            "captcha_solving": False,
            "liveness_spoofing": False,
        }

    def pending(self):
        state = self._expire(self._load())
        return [
            dict(x)
            for x in state["tickets"].values()
            if x.get("status") == "OWNER_APPROVAL_REQUIRED"
        ]

    def get(self, request_id):
        state = self._expire(self._load())
        row = state["tickets"].get(str(request_id))
        if not row:
            raise KeyError(request_id)
        return dict(row)

    def status(self):
        state = self._expire(self._load())
        rows = list(state["tickets"].values())
        return {
            "component": "KRISHNA External Authentication Handoff Gate",
            "version": self.VERSION,
            "pending": len([x for x in rows if x.get("status") == "OWNER_APPROVAL_REQUIRED"]),
            "approved_waiting_use": len([x for x in rows if x.get("status") == "APPROVED"]),
            "ticket_count": len(rows),
            "ttl_seconds": self.ttl_seconds,
            "approval_scope": "single agent + job + origin + authentication method",
            "approval_effect": "human takeover only",
            "credential_capture": False,
            "captcha_solving": False,
            "liveness_spoofing": False,
            "ready": True,
        }
