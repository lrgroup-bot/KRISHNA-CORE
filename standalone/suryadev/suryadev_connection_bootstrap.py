"""Connection-only bootstrap. No source intake or inference before plan approval."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import time
from urllib.parse import urlsplit

from suryadev_feeder import read_plan
from suryadev_krishna_mission import load_config, post_core
from suryadev_liveops import atomic_json


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def install_plan(root, config, reply):
    """Validate all approval evidence before atomic, non-overwriting publication."""
    if (reply.get("schema") != "krishna.suryadev.learning-plan-delivery.v1" or
            reply.get("status") != "approved_plan" or
            reply.get("device_id") != config["device_id"]):
        raise ValueError("invalid plan delivery identity/schema")
    digest = reply.get("sha256")
    body = {k: v for k, v in reply.items() if k != "sha256"}
    if not isinstance(digest, str) or not hmac.compare_digest(
            digest, hashlib.sha256(canonical(body)).hexdigest()):
        raise ValueError("plan delivery evidence hash mismatch")
    approval = reply.get("approval")
    if not isinstance(approval, dict) or approval.get("schema") != "krishna.suryadev.catalogue-approval.v1":
        raise ValueError("owner catalogue approval missing")
    missions = approval.get("missions")
    if not isinstance(missions, list) or not 1 <= len(missions) <= 200:
        raise ValueError("approval mission bounds exceeded")
    approved = []
    for mission in missions:
        if not isinstance(mission, dict) or mission.get("duration_hours") != 6:
            raise ValueError("invalid approved mission")
        urls = mission.get("approved_urls")
        if not isinstance(urls, list) or not 1 <= len(urls) <= 20:
            raise ValueError("invalid mission source approvals")
        approved.extend(urls)
    plan = reply.get("plan")
    expected = {"approved_urls", "approved_feeds", "allowed_source_hosts",
                "approved_publisher_transcripts", "paired_core_host_delegation",
                "max_new_per_cycle", "max_queued"}
    if not isinstance(plan, dict) or set(plan) != expected:
        raise ValueError("unexpected plan fields")
    urls = plan["approved_urls"]
    if (not isinstance(urls, list) or not 1 <= len(urls) <= 300 or
            any(not isinstance(u, str) or len(u) > 2048 for u in urls + approved) or
            set(urls) != set(approved) or len(set(urls)) != len(urls)):
        raise ValueError("plan differs from exact approved sources")
    for url in urls:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or
                parsed.password or parsed.fragment or parsed.port not in (None, 443)):
            raise ValueError("invalid approved HTTPS source")
        # No DNS/network work here. Existing acquisition validates resolved IPs.
        import ipaddress
        try:
            address = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise ValueError("private source address forbidden")
    if (plan["approved_feeds"] != [] or plan["allowed_source_hosts"] != [] or
            plan["approved_publisher_transcripts"] != [] or
            plan["paired_core_host_delegation"] is not False or
            type(plan["max_new_per_cycle"]) is not int or
            not 1 <= plan["max_new_per_cycle"] <= 5 or
            type(plan["max_queued"]) is not int or not 1 <= plan["max_queued"] <= 75):
        raise ValueError("remote plan exceeds bootstrap safeguards")
    root = Path(root)
    target = root / "learning-plan.json"
    stage = root / (".received-plan-" + secrets.token_hex(12) + ".json")
    try:
        with stage.open("xb") as handle:
            handle.write(canonical(plan))
            handle.flush()
            os.fsync(handle.fileno())
        read_plan(stage)
        evidence = root / "core-plan-evidence"
        evidence.mkdir(exist_ok=True)
        raw = canonical({"delivery": reply, "tls_cert_sha256": config["fingerprint"]})
        record = evidence / (digest + ".json")
        try:
            with record.open("xb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError:
            if record.read_bytes() != raw:
                raise ValueError("immutable approval evidence collision")
        # Same-volume hard link publishes fully flushed bytes atomically and
        # refuses to replace any owner-created plan, including a racing writer.
        if os.name == "nt":
            os.rename(stage, target)  # Windows rename refuses an existing destination
        else:
            os.link(stage, target)
        return target
    finally:
        stage.unlink(missing_ok=True)


class ConnectionBootstrap:
    def __init__(self, root, config_path, *, transport=post_core, clock=time.time):
        self.root = Path(root)
        self.config = load_config(config_path)
        if not self.config["device_id"].startswith("suryadev-"):
            raise ValueError("owner-paired SURYADEV identity required")
        self.transport = transport
        self.clock = clock

    def tick(self, plan_path=None):
        device = self.config["device_id"]
        reply = self.transport(self.config, "/api/suryadev/device/heartbeat", {
            "device_id": device, "worker_running": False,
            "learning_state": "awaiting_approved_plan", "network_online": True,
            "queued_jobs": 0, "running_jobs": 0})
        if reply.get("accepted") is not True or reply.get("device_id") != device:
            raise ValueError("Core did not accept paired device heartbeat")
        atomic_json(self.root, "krishna-fleet-heartbeat-ack.json", {
            "schema": "suryadev.krishna-authenticated-heartbeat.v1",
            "authenticated_core_reply": True, "device_id": device,
            "acknowledged_at": self.clock(), "knowledge_accepted": False,
            "brahmagyan_accepted": False})
        target = Path(plan_path) if plan_path else self.root / "learning-plan.json"
        if target.is_file():
            read_plan(target)
            return target
        reply = self.transport(self.config, "/api/suryadev/learning-plan/request", {"device_id": device})
        if reply.get("status") == "awaiting_owner_approved_plan" and reply.get("device_id") == device:
            return None
        return install_plan(self.root, self.config, reply)


def wait_for_plan(lib, config_path, plan_path=None):
    bootstrap = ConnectionBootstrap(lib.root, config_path)
    while True:
        try:
            result = bootstrap.tick(plan_path)
            if result is not None:
                return result
            state = "connected_awaiting_owner_approved_plan"
        except (OSError, ValueError, RuntimeError):
            # Never log credential-bearing exception details or start learning.
            state = "bootstrap_retry_learning_disabled"
        atomic_json(lib.root, "connection-bootstrap.json", {
            "state": state, "learning_enabled": False, "updated_at": time.time()})
        time.sleep(20)
