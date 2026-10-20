"""Opt-in six-hour SURYADEV research session supervisor.

Manually started only. One locked worker drives owner-approved RSS/URL
discovery, the existing processing queue, and local heartbeat metrics.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from suryadev import Library
from suryadev_feeder import read_plan, feed_once, FEED_STATE
from suryadev_liveops import atomic_json, worker_note
from suryadev_lock import worker_lock
from suryadev_parallel import AdaptiveResearchWorkers

def mission(data, plan_path, *, duration_hours=6, refill_minutes=30,
            check_seconds=60, use_ollama=True, model="qwen3.5:9b"):
    if not (0.05 <= duration_hours <= 48):
        raise ValueError("duration-hours must be between 0.05 and 48")
    if not (5 <= refill_minutes <= 360):
        raise ValueError("refill-minutes must be between 5 and 360")
    if not (10 <= check_seconds <= 3600):
        raise ValueError("check-seconds must be between 10 and 3600")
    plan = read_plan(plan_path)
    root = Path(data).expanduser().resolve()
    deadline = time.time() + duration_hours * 3600
    with worker_lock(root):
        lib = Library(root)
        adaptive = AdaptiveResearchWorkers(
            root, use_ollama=use_ollama, model=model, check_seconds=check_seconds)
        try:
            lib.recover()
            return _run_research_session(lib, adaptive, plan, root, deadline,
                                         duration_hours, refill_minutes, check_seconds)
        finally:
            adaptive.close()
            lib.db.close()
            worker_note(root, "stopped", check_seconds, "Research session stopped")
            state_file = root / FEED_STATE
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
                state["next_run"] = None
                state["loop_enabled"] = False
                atomic_json(root, FEED_STATE, state)
            except (OSError, ValueError, TypeError):
                pass

def _run_research_session(lib, adaptive, plan, root, deadline,
                          duration_hours, refill_minutes, check_seconds):
    refresh_at = 0
    worker_note(root, "starting", check_seconds,
                "Owner-approved adaptive Garudanetra session started")
    while time.time() < deadline:
        now = time.time()
        if now >= refresh_at:
            try:
                outcome = feed_once(lib, plan)
                print(json.dumps({"feeder": outcome}, ensure_ascii=False), flush=True)
                note = ""
            except (ValueError, OSError, RuntimeError) as exc:
                outcome = {"added_total":0,"feed_errors":[{"error":str(exc)[:180]}]}
                note = type(exc).__name__ + ": " + str(exc)[:150]
                print(json.dumps({"feeder_error": note}), flush=True)
            refresh_at = time.time() + refill_minutes * 60
            atomic_json(root, FEED_STATE, {
                "last_run": now, "next_run": refresh_at, "session_ends_at": deadline,
                "period_minutes": refill_minutes, "loop_enabled": True,
                "added_total": outcome.get("added_total", 0),
                "feed_error_count": len(outcome.get("feed_errors", [])),
                "error": note,
            })
        update = adaptive.pump()
        for job_result in update["finished"]:
            print(json.dumps({"work":job_result},ensure_ascii=False),flush=True)
        interval = 2 if update["capacity"]["active_total"] else check_seconds
        time.sleep(max(0, min(interval, deadline-time.time(),
                               refresh_at-time.time())))
    return {"session":"finished","duration_hours":duration_hours,
            "last_completed":adaptive.last_result}

def main(argv=None):
    p = argparse.ArgumentParser(description="Time-boxed 6-hour approved-source SURYADEV study session")
    p.add_argument("--data", required=True)
    p.add_argument("--plan", required=True)
    p.add_argument("--duration-hours", type=float, default=6)
    p.add_argument("--refill-minutes", type=int, default=30)
    p.add_argument("--check-seconds", type=int, default=60)
    p.add_argument("--no-ollama", action="store_true")
    p.add_argument("--model", default="qwen3.5:9b")
    a = p.parse_args(argv)
    try:
        print(json.dumps(mission(a.data, a.plan, duration_hours=a.duration_hours,
                refill_minutes=a.refill_minutes, check_seconds=a.check_seconds,
                use_ollama=not a.no_ollama, model=a.model), ensure_ascii=False))
    except KeyboardInterrupt:
        print("SURYADEV mission stopped by operator.", flush=True)

if __name__ == "__main__":
    main()
