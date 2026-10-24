"""Durable continuous SURYADEV mission cadence; no independent scheduler.

Six hours of approved work -> drain current work -> mandatory ten-minute rest
-> resume with a new six-hour window. The *only* worker-lock owner calls tick().
Readiness is not permission to invent sources or override safety/429 limits.
"""
from __future__ import annotations

from pathlib import Path
import time

from suryadev_liveops import _safe_read, atomic_json

FILE = "mission-cycle-runtime.json"
SCHEMA = "suryadev.mission-cycle.v1"
WORK_SECONDS = 6 * 3600
REST_SECONDS = 10 * 60
MAX_ACTIVE = 1000


class MissionCycle:
    def __init__(self, root, *, clock=time.time):
        self.root = Path(root).expanduser().resolve()
        self.clock = clock

    def tick(self, *, active_jobs: int = 0, now=None):
        """Advance cadence; do not preempt in-flight writes or source playback.

        'work' authorizes admission subject to the *separate* 85% guard.
        'draining' rejects new jobs until in-flight work safely completes.
        'rest' rejects all new work for at least ten real elapsed minutes.
        """
        if type(active_jobs) is not int or not 0 <= active_jobs <= MAX_ACTIVE:
            raise ValueError("active_jobs must be a bounded nonnegative integer")
        when = float(self.clock() if now is None else now)
        if not 0 < when < 1e12 or when != when:
            raise ValueError("invalid mission clock")
        previous = _safe_read(self.root, FILE, max_bytes=4096)
        if previous and previous.get("schema") != SCHEMA:
            raise RuntimeError("Unknown mission state; refusing to overwrite previous state")
        state = dict(previous) if previous else {
            "schema": SCHEMA, "mission_number": 1, "phase": "work",
            "work_started_at": when, "rest_started_at": None,
            "rest_until": None, "completed_missions": 0,
        }
        phase = state.get("phase")
        start = state.get("work_started_at")
        if phase not in ("work", "draining", "rest"):
            raise RuntimeError("Invalid mission phase; manual inspection required")
        if type(start) not in (float,int) or not 0 < start <= when + 5:
            raise RuntimeError("Invalid mission start timestamp")
        # A clock moved backwards substantially: preserve history, stop new work.
        if start > when:
            phase = "draining"
            state["phase"] = phase
            state["clock_adjustment_detected"] = True
        elif phase == "work" and when - start >= WORK_SECONDS:
            phase = "draining"
            state["phase"] = phase
            state["drain_started_at"] = when

        if phase == "draining" and active_jobs == 0:
            phase = "rest"
            state["phase"] = phase
            state["rest_started_at"] = when
            state["rest_until"] = when + REST_SECONDS
        if phase == "rest":
            until = state.get("rest_until")
            if type(until) not in (float,int) or not until > 0:
                raise RuntimeError("Invalid stored rest deadline")
            # Never shorten the break because a worker was restarted.
            if when >= until and active_jobs == 0:
                state["completed_missions"] = int(state["completed_missions"]) + 1
                state["mission_number"] = int(state["mission_number"]) + 1
                state["work_started_at"] = when
                state["phase"] = "work"
                state["rest_started_at"] = None
                state["rest_until"] = None
                state.pop("clock_adjustment_detected", None)
                phase = "work"

        # A stale lifecycle receipt must never imply in-flight source knowledge.
        state["last_checked_at"] = when
        state["active_jobs_observed"] = active_jobs
        state["admission_allowed"] = phase == "work"
        state["work_until"] = float(state["work_started_at"]) + WORK_SECONDS
        state["remaining_work_seconds"] = max(0, round(state["work_until"] - when)) if phase == "work" else 0
        state["remaining_rest_seconds"] = (
            max(0, round(float(state["rest_until"]) - when))
            if phase == "rest" else 0)
        state["note"] = (
            "Approved queue can run, subject to device limits and source authorization"
            if phase == "work" else
            "Finishing in-flight work; no new tasks admitted"
            if phase == "draining" else
            "Mandatory device rest; no new learning or video tasks"
        )
        if state != previous:
            atomic_json(self.root, FILE, state)
        return state


def status(root):
    """Read-only UI status; never drive a new mission from a dashboard GET."""
    return _safe_read(root, FILE, max_bytes=4096)
