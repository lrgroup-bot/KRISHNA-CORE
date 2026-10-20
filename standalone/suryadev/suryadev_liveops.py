"""Truthful local worker telemetry and an explicit, read-only integration state.

The dashboard reads facts only; no future task schedule is invented.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time

from suryadev_sources import source_kind

WORKER_FILE = "worker-runtime.json"
READER_FILE = "krishna-reader-receipt.json"


def atomic_json(root, filename, payload):
    directory = Path(root).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".tmp",
                                         dir=directory, delete=False) as file:
            temp_name = file.name
            json.dump(payload, file, separators=(",", ":"), ensure_ascii=False)
        os.replace(temp_name, directory / filename)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def worker_note(root, state, interval, reason="", *, next_check_at=None, last_result=None):
    """Only the actual worker loop writes scheduling times."""
    if state not in ("starting", "checking", "busy", "idle", "paused", "stopped"):
        raise ValueError("unknown worker state")
    atomic_json(root, WORKER_FILE, {
        "state": state, "heartbeat_at": time.time(), "interval_seconds": int(interval),
        "next_check_at": next_check_at, "reason": str(reason)[:240],
        "pid": os.getpid(), "last_result": last_result,
    })


def _safe_read(root, name):
    path = Path(root).resolve() / name
    try:
        if path.stat().st_size > 4096:
            return {}
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def connection_indicators(root):
    """No integration is assumed. Green Core means recent authorized TLS API read,
    not that Core, BRAHMAGYAN or Rishi accepted a knowledge bundle.
    """
    receipt = _safe_read(root, READER_FILE)
    age = time.time() - float(receipt.get("last_read_at", 0) or 0)
    trusted_read = (receipt.get("type") == "authenticated_tls_read" and 0 <= age < 120)
    return {
        "krishna": {
            "connected": bool(trusted_read),
            "state": "authenticated_live_reader" if trusted_read else "not_connected",
            "detail": ("An approved TLS client read the dashboard export recently. "
                       "This does not prove KRISHNA Core enrollment."
                       if trusted_read else "No recent authenticated KRISHNA reader; secure pairing not confirmed."),
        },
        "brahmagyan": {
            "connected": False, "state": "not_connected",
            "detail": "No authenticated BRAHMAGYAN delivery/ACK is configured.",
        },
        "rishi": {
            "connected": False, "state": "not_connected",
            "detail": "No verified Rishi Council acceptance receipt is configured.",
        },
    }


def operations_snapshot(db, root):
    """Read database and worker heartbeat to report current, queued and last work."""
    now = time.time()
    state = _safe_read(root, WORKER_FILE)
    heartbeat = state.get("heartbeat_at")
    interval = state.get("interval_seconds", 60)
    try:
        interval = max(10, min(3600, int(interval)))
    except (TypeError, ValueError):
        interval = 60
    fresh = (isinstance(heartbeat, (float, int)) and
             0 <= now - heartbeat < max(180, interval * 3))
    active_rows = db.execute(
        "SELECT id,url,updated FROM jobs WHERE status='running' ORDER BY id LIMIT 8"
    ).fetchall()
    queue_rows = db.execute(
        "SELECT id,url,created FROM jobs WHERE status='queued' ORDER BY id LIMIT 8"
    ).fetchall()
    pending = dict(db.execute(
        "SELECT status,count(*) FROM jobs GROUP BY status"
    ).fetchall())
    summary = {}
    for kind in ("youtube", "pdf", "website", "other"):
        summary[kind] = {"queued": 0, "running": 0, "done": 0, "failed": 0}
    for url, status in db.execute("SELECT url,status FROM jobs"):
        if status in summary[source_kind(url)]:
            summary[source_kind(url)][status] += 1
    current = [{"id": job, "url": url, "kind": source_kind(url),
                "started_at": updated, "progress_percent": None}
               for job,url,updated in active_rows]
    upcoming = [{"id": job, "url": url, "kind": source_kind(url),
                 "queued_at": created, "scheduled_at": None}
                for job,url,created in queue_rows]
    last = state.get("last_result") if fresh else None
    return {
        "sample_time": now,
        "worker": {
            "state": state.get("state", "offline") if fresh else "offline",
            "heartbeat_at": heartbeat if fresh else None,
            "reason": state.get("reason", "") if fresh else "No recent worker heartbeat",
            "interval_seconds": interval if fresh else None,
            "next_check_at": state.get("next_check_at") if fresh else None,
            "last_result": last if isinstance(last, dict) else None,
            "note": ("Queue order is known, but per-task start times and processing "
                     "percentages are not scheduled or measured."),
        },
        "current": current, "upcoming": upcoming,
        "queued_total": pending.get("queued", 0),
        "running_total": pending.get("running", 0),
        "by_source": summary,
        "connections": connection_indicators(root),
    }
