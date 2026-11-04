from __future__ import annotations

"""Read-only, fail-closed projection of real KRISHNA agent events for live UIs.

No synthetic activity is generated. Frontends can animate *observed* transitions,
but must not infer successful work from an enabled agent manifest.
"""
from datetime import datetime, timezone
import math

STATES = frozenset({"idle", "working", "healing", "blocked", "offline", "unknown"})
MAX_AGE_SECONDS = 30.0


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite numeric")
    return float(value)


def project_agent_event(event: dict, *, now: float, max_age: float = MAX_AGE_SECONDS) -> dict:
    """Validate an authenticated server-side event before frontend publication.

    The caller must authenticate the event source and enforce authorization.
    This function validates schema and freshness; it does not authenticate.
    """
    if not isinstance(event, dict):
        raise ValueError("event must be an object")
    now = _number(now, "now")
    max_age = _number(max_age, "max_age")
    if max_age <= 0:
        raise ValueError("max_age must be positive")
    agent_id = event.get("agent_id")
    if not isinstance(agent_id, str) or not agent_id.strip() or len(agent_id) > 128:
        raise ValueError("invalid agent_id")
    state = event.get("state")
    if state not in STATES:
        raise ValueError("invalid state")
    sequence = event.get("sequence")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise ValueError("invalid sequence")
    timestamp = _number(event.get("timestamp"), "timestamp")
    if timestamp > now + 5:
        raise ValueError("event timestamp is in the future")
    age = max(0.0, now - timestamp)
    task_id = event.get("task_id")
    if task_id is not None and (not isinstance(task_id, str) or len(task_id) > 128):
        raise ValueError("invalid task_id")
    progress = event.get("progress")
    if progress is not None:
        progress = _number(progress, "progress")
        if not 0 <= progress <= 1:
            raise ValueError("progress must be between zero and one")
    stale = age > max_age
    return {
        "schema": "krishna.agent-live.v1",
        "agent_id": agent_id.strip(),
        "task_id": task_id,
        "state": "unknown" if stale else state,
        "reported_state": state,
        "sequence": sequence,
        "timestamp": timestamp,
        "age_seconds": age,
        "stale": stale,
        "progress": None if stale else progress,
        "verified_completion": bool(event.get("verified_completion") is True and not stale),
        "display_status": "STALE" if stale else state.upper(),
    }


class AgentLiveProjection:
    """Sequence-safe read-only UI state, keyed by agent ID."""

    def __init__(self, max_age: float = MAX_AGE_SECONDS):
        self.max_age = _number(max_age, "max_age")
        if self.max_age <= 0:
            raise ValueError("max_age must be positive")
        self._latest = {}

    def ingest(self, event: dict, *, now: float) -> dict:
        row = project_agent_event(event, now=now, max_age=self.max_age)
        previous = self._latest.get(row["agent_id"])
        if previous is not None and row["sequence"] <= previous["sequence"]:
            raise ValueError("duplicate or out-of-order event")
        self._latest[row["agent_id"]] = row
        return row

    def snapshot(self, *, now: float) -> list[dict]:
        # Reproject each saved event at read time so silent agents become STALE.
        return [
            project_agent_event(
                {**row, "state": row["reported_state"]},
                now=now,
                max_age=self.max_age,
            )
            for _, row in sorted(self._latest.items())
        ]
