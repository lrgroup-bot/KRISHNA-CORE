"""Deliver only the existing owner-curated catalogue after device connection."""
import hashlib
import json


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def approved_plan(agent, device_id):
    node = agent.device_status(device_id)
    if (not device_id.startswith("suryadev-") or
            node.get("authenticated") is not True or
            not 0 <= agent.clock() - node.get("last_seen", 0) <= 150):
        raise PermissionError("fresh authenticated heartbeat required before plan delivery")
    missions, policy = agent.mission_backlog._catalogue()
    if policy != "approved":
        return {"status": "awaiting_owner_approved_plan", "device_id": device_id}
    urls = list(dict.fromkeys(url for item in missions for url in item["approved_urls"]))
    if not 1 <= len(urls) <= 300:
        raise ValueError("approved plan must contain 1..300 exact sources")
    plan = {"approved_urls": urls, "approved_feeds": [], "allowed_source_hosts": [],
            "approved_publisher_transcripts": [], "paired_core_host_delegation": False,
            "max_new_per_cycle": 5, "max_queued": 75}
    approval = {"schema": "krishna.suryadev.catalogue-approval.v1", "missions": missions}
    result = {"schema": "krishna.suryadev.learning-plan-delivery.v1",
              "status": "approved_plan", "device_id": device_id,
              "approval": approval, "plan": plan}
    result["sha256"] = hashlib.sha256(canonical(result)).hexdigest()
    if len(canonical(result)) > 131072:
        raise ValueError("approved plan delivery exceeds transport bound")
    return result
