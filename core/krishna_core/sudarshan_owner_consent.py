"""KRISHNA local operator consent for specific SUDARSHAN actions.

A proof is HMAC-bound to action, project, exact payload and expiry. Tokens can
only be minted with the host-local secret, are consumed once across restarts,
and must never be accepted as owner identity on an untrusted remote endpoint.

This is a restricted *operator possession* gate, not a replacement for an
authenticated human session / hardware-backed identity.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import base64
import binascii
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time

ENV_KEY = "KRISHNA_SUDARSHAN_CONSENT_KEY"
ACTIONS = frozenset({"sudarshan.research.observe", "sudarshan.research.mission"})
MAX_AGE = 300


def _canonical(payload):
    if not isinstance(payload, dict):
        raise TypeError("consent payload must be an object")
    data = {k: v for k, v in payload.items() if k != "owner_token"}
    raw = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                     allow_nan=False).encode("utf-8")
    if len(raw) > 128_000:
        raise ValueError("consent payload too large")
    return hashlib.sha256(raw).hexdigest()


def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(data):
    if not isinstance(data, str) or len(data) > 8192:
        raise ValueError("invalid token encoding")
    return base64.b64decode(data + "=" * ((-len(data)) % 4),
                            altchars=b"-_", validate=True)


class OwnerConsent:
    def __init__(self, key_hex, db_path):
        if not isinstance(key_hex, str) or len(key_hex) != 64:
            raise ValueError("64-character host-local consent key required")
        try:
            key = bytes.fromhex(key_hex)
        except ValueError as error:
            raise ValueError("invalid host-local key") from error
        if len(key) != 32 or not any(key):
            raise ValueError("strong random 256-bit local key required")
        self._key = key
        self.db_path = str(db_path)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS sudarshan_consent_nonces(
                nonce_sha256 TEXT PRIMARY KEY,
                consumed_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            )""")

    @classmethod
    def from_environment(cls, db_path):
        key = os.environ.get(ENV_KEY)
        return cls(key, db_path) if key else None

    @contextmanager
    def _connect(self):
        # A sqlite3.Connection context manager commits/rolls back but DOES NOT
        # close its file handle; close explicitly for Windows temp/runtime use.
        db = sqlite3.connect(self.db_path, timeout=10)
        try:
            db.execute("PRAGMA busy_timeout = 10000")
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _scope(action, project):
        if action not in ACTIONS or not isinstance(project, str) or not project.strip():
            raise ValueError("unsupported SUDARSHAN action or project")

    def issue(self, action, project, payload, *, ttl_seconds=120):
        self._scope(action, project)
        if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= MAX_AGE:
            raise ValueError("consent lifetime must be 1..300 seconds")
        now = int(time.time())
        body = {"v": 1, "action": action, "project": project,
                "payload_sha256": _canonical(payload),
                "nonce": secrets.token_hex(24), "iat": now, "exp": now + ttl_seconds}
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        sig = hmac.new(self._key, raw, hashlib.sha256).digest()
        return _b64(raw) + "." + _b64(sig)

    def consume(self, token, action, project, payload):
        self._scope(action, project)
        if not isinstance(token, str) or token.count(".") != 1:
            raise PermissionError("fresh SUDARSHAN operator consent required")
        try:
            encoded, signature = token.split(".", 1)
            raw, sig = _unb64(encoded), _unb64(signature)
            expected = hmac.new(self._key, raw, hashlib.sha256).digest()
            if not hmac.compare_digest(expected, sig):
                raise ValueError("signature mismatch")
            body = json.loads(raw)
            now = int(time.time())
            if (not isinstance(body, dict) or body.get("v") != 1 or
                    body.get("action") != action or body.get("project") != project or
                    body.get("payload_sha256") != _canonical(payload) or
                    type(body.get("iat")) is not int or type(body.get("exp")) is not int or
                    body["exp"] <= now or body["iat"] > now + 5 or
                    body["exp"] - body["iat"] > MAX_AGE or
                    not isinstance(body.get("nonce"), str) or
                    len(body["nonce"]) != 48):
                raise ValueError("expired or out-of-scope consent")
        except (ValueError, TypeError, KeyError, binascii.Error) as error:
            raise PermissionError("invalid, expired or out-of-scope SUDARSHAN consent") from error
        nonce_hash = hashlib.sha256(body["nonce"].encode()).hexdigest()
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute("DELETE FROM sudarshan_consent_nonces WHERE expires_at < ?",
                           (now - MAX_AGE,))
                db.execute("INSERT INTO sudarshan_consent_nonces VALUES(?,?,?)",
                           (nonce_hash, now, body["exp"]))
        except sqlite3.IntegrityError as error:
            raise PermissionError("SUDARSHAN consent replay blocked") from error
        return True


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Mint a short-lived local SUDARSHAN action consent proof")
    parser.add_argument("--action", choices=sorted(ACTIONS), required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--payload-json", required=True,
                        help="exact local JSON file for dispatch (without owner_token)")
    parser.add_argument("--db-path", required=True,
                        help="same local SQLite path as KRISHNA runtime")
    args = parser.parse_args(argv)
    owner = OwnerConsent.from_environment(args.db_path)
    if owner is None:
        parser.error("operator consent key is not configured in environment")
    if not Path(args.payload_json).is_file():
        parser.error("local payload JSON file required")
    payload = json.loads(Path(args.payload_json).read_text(encoding="utf-8"))
    print(owner.issue(args.action, args.project, payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
