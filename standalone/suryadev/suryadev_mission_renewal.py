"""Durable, fail-closed six-hour task renewal request for KRISHNA readers.

This is the SURYADEV-side REQUEST contract, not a remote command channel.
The existing authorized read-only bridge can surface this outbox through
/api/operations; until a separately verified KRISHNA dispatcher acknowledges
and delivers an owner-approved batch, the request remains unfulfilled.
No internet requests, source auto-approval, worker launches or DB mutations.
"""
from __future__ import annotations

from pathlib import Path
import time
from uuid import uuid4

from suryadev_liveops import atomic_json, _safe_read
from suryadev_sources import source_kind

RENEWAL_FILE = "krishna-mission-renewal.json"
LOW_WATER_JOBS = 3
NEXT_MISSION_HOURS = 6


def renewal_tick(lib, *, youtube_blocked=False, low_water=LOW_WATER_JOBS,
                 session_ends_at=None, now=None):
    """Publish an idempotent request when eligible approved work runs low.

    Called ONLY by an existing worker that owns the single-worker lock and
    has an explicitly enabled learning plan. Does not assume Core connectivity.
    A rate-limited YouTube assignment is not counted as executable work.
    """
    if not 1 <= low_water <= 100:
        raise ValueError("low_water must be 1..100")
    when = time.time() if now is None else float(now)
    if not 0 < when < 1e12:
        raise ValueError("invalid current timestamp")
    root = Path(lib.root).resolve()
    counts = {"queued": 0, "running": 0, "eligible": 0,
              "blocked_youtube": 0, "done": 0, "failed": 0}
    for url, status in lib.db.execute("SELECT url,status FROM jobs"):
        if status in counts:
            counts[status] += 1
        if status in ("queued", "running"):
            if youtube_blocked and source_kind(url) == "youtube":
                counts["blocked_youtube"] += 1
            else:
                counts["eligible"] += 1
    previous = _safe_read(root, RENEWAL_FILE, max_bytes=8192)
    existing = previous.get("request")
    if not isinstance(existing, dict) or not isinstance(existing.get("request_id"), str):
        existing = None
    need = counts["eligible"] < low_water
    # A locally available RSS/URL queue may satisfy the immediate learning
    # need; this does NOT prove KRISHNA delivered or acknowledged anything.
    if need:
        if (existing is None or previous.get("status") != "awaiting_assignment"):
            existing = {
                "request_id": uuid4().hex,
                "requested_at": when,
                "desired_hours": NEXT_MISSION_HOURS,
                "kind": "approved_source_research",
                "requested_by": "suryadev",
                "requires_owner_approved_sources": True,
                "coordinator_requested": "BRAHMAGYAN",
                "rishi_assignment": "BRAHMAGYAN_CHOOSES",
                "delivery_authority": "KRISHNA_AUTHENTICATED_DEVICE_ONLY",
                "queue_policy": "prepare_next_before_current_finishes",
                "expert_source_policy": "prefer_institutional_official_profiles_and_correlated_ORCID_DOI",
                "expert_identity_verified": False,
                "source_provenance_required": True,
                "rest_after_mission_minutes": 10,
            }
        status = "awaiting_assignment"
    else:
        status = "local_work_available"
    deadline = None
    if session_ends_at is not None:
        deadline = float(session_ends_at)
        if deadline <= 0 or deadline > 1e12:
            raise ValueError("invalid session end")
    relay_state = _safe_read(root, "krishna-mission-sync.json", max_bytes=8192)
    confirmed = bool(existing and relay_state.get("request_id") == existing["request_id"]
                     and relay_state.get("acknowledged") is True
                     and relay_state.get("state") == "core_delivery_acknowledged")
    value = {
        "protocol": "suryadev-krishna-renewal-v1",
        "status": status,
        "request": existing,
        "eligible_queued_or_running": counts["eligible"],
        "blocked_youtube": counts["blocked_youtube"],
        "completed_total": counts["done"],
        "failed_total": counts["failed"],
        "low_water_jobs": low_water,
        "mission_cadence": {"work_seconds": 21600, "rest_seconds": 600,
                           "new_work_requires_safe_hardware": True},
        "coordinator_assignment_verified": False,
        "session_ends_at": deadline,
        "transport": "read_only_bridge_outbox",
        "delivered_to_krishna": confirmed,
        "krishna_assignment_acknowledged": confirmed,
        "brahmagyan_acknowledged": False,
        "note": ("KRISHNA accepted and acknowledged local mission delivery; "
                 "completed learning and BRAHMAGYAN intake remain unverified."
                 if confirmed else
                 "Renewal request is durable locally; no authenticated KRISHNA "
                 "mission delivery has been acknowledged."),
    }
    # Avoid rewriting the outbox on every 2-second active-worker poll.
    if value != previous:
        atomic_json(root, RENEWAL_FILE, value)
    return value
