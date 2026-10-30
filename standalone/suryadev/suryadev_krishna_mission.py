"""Opt-in, TLS-pinned KRISHNA mission assignment client for SURYADEV.

Outbound only. No credential leaves the laptop before verifying the pinned
Core server TLS leaf certificate. KRISHNA may offer research URLs; the laptop
still admits ONLY exact owner-approved URLs with the existing SQLite dedup.
Core mission delivery != evidence acquired != BRAHMAGYAN learning acceptance.
"""
from __future__ import annotations

import hashlib
import hmac
import http.client
import ipaddress
import json
from pathlib import Path
import ssl
import time
from urllib.parse import urlsplit

from suryadev_feeder import read_plan, paired_core_source_allowed
from suryadev_liveops import atomic_json, _safe_read

STATE_FILE = "krishna-mission-sync.json"
MAX_REPLY = 131072
RETRY_SECONDS = 300


def load_config(path):
    config_path = Path(path).expanduser().resolve(strict=True)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != "suryadev.krishna-mission-connection.v1":
        raise ValueError("invalid opt-in KRISHNA mission configuration")
    address = urlsplit(data.get("endpoint", ""))
    if (address.scheme != "https" or not address.hostname or
            address.username or address.password or address.path not in ("", "/")
            or address.query or address.fragment):
        raise ValueError("KRISHNA mission endpoint must be a plain HTTPS origin")
    try:
        ip = ipaddress.ip_address(address.hostname)
    except ValueError as exc:
        raise ValueError("KRISHNA mission endpoint requires explicit private IPv4") from exc
    if ip.version != 4 or not (ip.is_private or ip.is_loopback) or ip.is_unspecified:
        raise ValueError("KRISHNA mission endpoint must use a private IPv4")
    digest = str(data.get("cert_sha256") or "").lower().replace(":", "")
    if len(digest) != 64 or any(x not in "0123456789abcdef" for x in digest):
        raise ValueError("invalid pinned Core TLS certificate fingerprint")
    device = data.get("device_id")
    if not isinstance(device, str) or not 1 <= len(device) <= 200:
        raise ValueError("paired device ID is required")
    token_path = Path(data.get("token_file", "")).expanduser()
    if not token_path.is_absolute():
        token_path = config_path.parent / token_path
    token = token_path.resolve(strict=True).read_text(encoding="ascii").strip()
    if not 48 <= len(token) <= 256 or not token.isascii() or not token.isprintable():
        raise ValueError("paired credential file requires a 48..256 ASCII token")
    return {"host": address.hostname, "port": address.port or 443,
            "fingerprint": digest, "device_id": device, "credential": token}


def post_core(config, path, payload):
    if path not in ("/api/suryadev/learning-plan/request", "/api/suryadev/mission/request", "/api/suryadev/mission/ack",
                    "/api/suryadev/learning-bundle",
                    "/api/suryadev/device/heartbeat",
                    "/api/suryadev/fleet/claim", "/api/suryadev/fleet/renew",
                    "/api/suryadev/fleet/complete"):
        raise ValueError("unsupported Core mission API")
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    # Explicit leaf certificate pinning is the trust anchor for local Core.
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    conn = http.client.HTTPSConnection(config["host"], config["port"],
                                       timeout=12, context=ctx)
    try:
        conn.connect()
        actual = hashlib.sha256(conn.sock.getpeercert(binary_form=True)).hexdigest()
        if not hmac.compare_digest(actual, config["fingerprint"]):
            raise ssl.SSLError("KRISHNA Core TLS certificate mismatch; no credential sent")
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        conn.request("POST", path, body=raw, headers={
            "Content-Type": "application/json", "Accept": "application/json",
            "X-Krishna-Device": config["device_id"],
            "Authorization": "Device " + config["credential"],
        })
        response = conn.getresponse()
        data = response.read(MAX_REPLY + 1)
        if len(data) > MAX_REPLY:
            raise ValueError("Core mission reply is oversized")
        if response.status != 200:
            raise RuntimeError("Core mission API rejected request: HTTP " + str(response.status))
        obj = json.loads(data)
        if not isinstance(obj, dict):
            raise ValueError("Core mission reply must be an object")
        return obj
    finally:
        conn.close()


class MissionRelay:
    def __init__(self, root, plan_path, config_path, *, transport=post_core,
                 clock=time.time):
        self.root = Path(root).resolve()
        self.plan_path = Path(plan_path).resolve()
        self.config = load_config(config_path)
        self.transport = transport
        self.clock = clock

    def tick(self, lib, renewal):
        """Poll only with an unfulfilled low-water renewal, respecting cooldown."""
        if renewal.get("status") != "awaiting_assignment":
            return None
        request = renewal.get("request")
        if not isinstance(request, dict) or request.get("desired_hours") != 6:
            raise ValueError("invalid six-hour low-water request")
        rid = request.get("request_id")
        state = _safe_read(self.root, STATE_FILE, max_bytes=8192)
        now = float(self.clock())
        if (state.get("request_id") == rid and state.get("acknowledged")):
            return None  # Already acknowledged; avoid repeatedly logging the same receipt.
        if (state.get("request_id") == rid and
                float(state.get("next_attempt_at", 0)) > now):
            return None
        try:
            return self._attempt(lib, request, state, now)
        except (OSError, RuntimeError, ValueError, ssl.SSLError) as exc:
            # Remote Core failure cannot stop local Garudanetra/SQLite work.
            committed = _safe_read(self.root, STATE_FILE, max_bytes=8192)
            event = {"request_id": rid, "acknowledged": False,
                     "next_attempt_at": now + RETRY_SECONDS,
                     "state": "retry_later",
                     "receipt": committed.get("receipt") if committed.get("request_id") == rid else None,
                     "last_error": type(exc).__name__ +
                     ": " + str(exc)[:160], "updated_at": now}
            atomic_json(self.root, STATE_FILE, event)
            return event

    def _attempt(self, lib, request, previous, now):
        rid = request["request_id"]
        receipt = previous.get("receipt") if previous.get("request_id") == rid else None
        mission = None
        if not isinstance(receipt, dict):
            offer = self.transport(self.config, "/api/suryadev/mission/request", {
                "device_id": self.config["device_id"], "request": request,
            })
            if offer.get("request_id") != rid:
                raise ValueError("Core mission request ID mismatch")
            if offer.get("status") == "no_approved_work":
                result = {"request_id": rid, "state": "core_curriculum_exhausted",
                          "acknowledged": False, "next_attempt_at": now + RETRY_SECONDS,
                          "updated_at": now, "queued_urls": 0}
                atomic_json(self.root, STATE_FILE, result)
                return result
            mission = offer.get("mission")
            if offer.get("status") != "offered" or not isinstance(mission, dict):
                raise ValueError("Core did not return a valid approved mission")
            if mission.get("duration_hours") != 6:
                raise ValueError("Core mission duration is not six hours")
            urls = mission.get("approved_urls")
            if not isinstance(urls, list) or not 1 <= len(urls) <= 20:
                raise ValueError("Core mission URLs missing or oversized")
            plan = read_plan(self.plan_path)
            # Host delegation is authorized separately, and is available
            # only to requests from the TLS-pinned authenticated KRISHNA Core.
            if any(not paired_core_source_allowed(url, plan) for url in urls):
                raise ValueError("Core mission contains a URL not explicitly approved on laptop")
            known = {x[0] for x in lib.db.execute("SELECT url FROM jobs")}
            space = max(0, plan["max_queued"] -
                        lib.stats().get("queued", 0) - lib.stats().get("running", 0))
            budget = min(plan["max_new_per_cycle"], space)
            queued = []
            receipt = {"mission_id": mission.get("id"), "queued": queued,
                       "queued_urls": 0, "request_id": rid}
            for url in urls:
                if url not in known and len(queued) < budget:
                    queued.append({"url": url, "job_id": lib.add(url)})
                    known.add(url)
                    receipt["queued_urls"] = len(queued)
                    # SQLite commits each job independently. Persist its
                    # receipt immediately so a crash mid-batch never results
                    # in silent duplicate intake or a lost Core ACK.
                    atomic_json(self.root, STATE_FILE, {"request_id": rid,
                        "receipt": receipt, "state": "local_jobs_persisted",
                        "acknowledged": False, "updated_at": now})
            if not queued:
                atomic_json(self.root, STATE_FILE, {"request_id": rid,
                    "receipt": receipt, "state": "no_new_approved_sources",
                    "acknowledged": False, "updated_at": now})
        if not receipt["queued_urls"]:
            result = {"request_id": rid, "state": "no_new_approved_sources",
                      "receipt": receipt, "acknowledged": False,
                      "next_attempt_at": now + RETRY_SECONDS, "updated_at": now}
            atomic_json(self.root, STATE_FILE, result)
            return result
        reply = self.transport(self.config, "/api/suryadev/mission/ack", {
            "device_id": self.config["device_id"], "request_id": rid,
            "accepted": True, "queued_urls": receipt["queued_urls"],
        })
        if reply.get("request_id") != rid or reply.get("acknowledged") is not True:
            raise ValueError("Core did not confirm mission delivery receipt")
        result = {"request_id": rid, "receipt": receipt, "acknowledged": True,
                  "state": "core_delivery_acknowledged", "updated_at": now,
                  "queued_urls": receipt["queued_urls"],
                  "brahmagyan_acknowledged": False}
        atomic_json(self.root, STATE_FILE, result)
        return result
