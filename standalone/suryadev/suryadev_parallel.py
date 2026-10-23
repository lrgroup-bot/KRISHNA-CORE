"""Measured, bounded parallel SURYADEV research with Garudanetra tabs.

Workers run multiple *independent source acquisitions* concurrently.
Expensive local Ollama summary generation is serialized for laptop stability.
No jobs are launched when real psutil telemetry is missing or unsafe.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import math
import os
from pathlib import Path
import threading
import time

from suryadev import Library
from suryadev_sources import source_kind
from suryadev_resources import snapshot
from suryadev_liveops import atomic_json, worker_note, _safe_read
from suryadev_garudanetra import GarudanetraLite

CAPACITY_FILE = "capacity-runtime.json"
KINDS = ("website", "youtube", "pdf")
MAX_PARALLEL = 6
YOUTUBE_ACCESS_FILE = "youtube-access-state.json"
YOUTUBE_RATE_LIMIT_PAUSE_SECONDS = 3600


def youtube_rate_limited(error):
    """Classify provider HTTP 429; never retry this request automatically."""
    msg = str(error or "").casefold()
    return "http 429" in msg or "http error 429" in msg or "too many requests" in msg


def youtube_access(root, now=None):
    """Bound persisted retry window to prevent repeatedly hitting an HTTP 429.

    Reports 429 only for requests actually observed by the current worker or
    an earlier worker. This does not signal the provider has restored access.
    """
    now = time.time() if now is None else now
    data = _safe_read(root, YOUTUBE_ACCESS_FILE)
    try:
        until = float(data.get("cooldown_until", 0))
    except (TypeError, ValueError, OverflowError):
        until = 0.0
    # Malformed data must not impose an indefinite ban or cause launches.
    if not math.isfinite(until) or until > now + YOUTUBE_RATE_LIMIT_PAUSE_SECONDS + 5:
        # A corrupt or manually altered value must not disable all future
        # YouTube jobs indefinitely. Do not trust or silently extend it.
        until = 0.0
    blocked = until > now
    return {"state": "rate_limited" if blocked else "ready",
            "cooldown_until": round(until, 2) if blocked else None,
            "reason": ("YouTube HTTP 429; awaiting rate-limit cooldown. "
                       "Previously failed jobs require an operator-approved retry."
                       if blocked else "No currently recorded YouTube cooldown.")}


def record_youtube_rate_limit(root, now=None):
    now = time.time() if now is None else now
    result = {"state": "rate_limited",
              "recorded_at": now,
              "cooldown_until": now + YOUTUBE_RATE_LIMIT_PAUSE_SECONDS,
              "reason": "YouTube subtitle HTTP 429. Pause new caption requests for one hour."}
    atomic_json(root, YOUTUBE_ACCESS_FILE, result)
    return result


def plan_capacity(reading, *, logical_cpus=None):
    """Conservative measured headroom, not an invented fixed laptop capacity."""
    if not reading.get("available"):
        return {"safe": False, "reason": "psutil telemetry unavailable",
                "max_total": 0, "limits": {k:0 for k in KINDS},
                "cpu_percent": None, "ram_percent": None}
    cpus = max(1, int(logical_cpus or os.cpu_count() or 1))
    cpu = float(reading.get("cpu_percent", 100))
    ram = float(reading.get("ram_percent", 100))
    disk = float(reading.get("disk_percent", 100))
    free = float(reading.get("ram_total_gb", 0)) - float(reading.get("ram_used_gb", 0))
    disk_free = float(reading.get("disk_free_gb", 0))
    gpu = reading.get("gpu") or {}
    gpu_hot = (gpu.get("available") and
               (float(gpu.get("usage_percent") or 0) >= 85 or
                float(gpu.get("vram_percent") or 0) >= 85))
    reason = ""
    if cpu >= 85 or ram >= 85 or disk >= 85 or disk_free < 2 or gpu_hot:
        reason = "Hardware guard: CPU/RAM/disk/GPU exceeded safe limits"
    elif free < 2.7:
        reason = "Less than 2.7 GiB available RAM"
    if reason:
        return {"safe":False, "reason":reason, "max_total":0,
                "limits":{k:0 for k in KINDS},
                "cpu_percent":cpu, "ram_percent":ram,
                "disk_free_gb":disk_free, "free_ram_gb":round(free,2)}
    # Reserve at least 2 GiB for Windows and other user applications.
    ram_slots = int(max(0, math.floor((free - 2.0) / 1.35)))
    cpu_slots = max(1, cpus // 2)
    total = min(MAX_PARALLEL, cpu_slots, ram_slots)
    if cpu >= 70 or ram >= 75:
        total = min(total, 1)
    total = max(0, total)
    # A single shared Garudanetra Chromium process owns at most 4 web tabs.
    limits = {
        "website": min(4, total),
        "youtube": min(2, total),
        "pdf": min(2, total),
    }
    return {"safe":total > 0, "reason":"Measured hardware admission passed" if total else "No remaining processing headroom",
            "max_total":total, "limits":limits,
            "cpu_percent":cpu, "ram_percent":ram,
            "disk_free_gb":disk_free, "free_ram_gb":round(free,2),
            "logical_cpus":cpus, "cpu_ceiling_percent":85,
            "memory_reserve_gb":2.0, "local_model_concurrency":1}


class AdaptiveResearchWorkers:
    """One supervisor/worker lock owns a pool of per-thread SQLite connections."""
    def __init__(self, root, *, use_ollama=True, model="qwen3.5:9b",
                 check_seconds=60, browser_factory=GarudanetraLite):
        self.root = Path(root).expanduser().resolve()
        self.use_ollama = use_ollama
        self.model = model
        self.check_seconds = check_seconds
        self.browser_factory = browser_factory
        self.browser = None
        self.browser_error = ""
        self.summary_lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=MAX_PARALLEL,
                                       thread_name_prefix="suryadev-learning")
        self.futures = {}
        self.last_result = None
        self.rotation = 0
        self.closed = False
        self.youtube_access = youtube_access(self.root)

    def _work(self, kind):
        lib = Library(self.root)
        try:
            return lib.run_next(use_ollama=self.use_ollama, model=self.model,
                                kind=kind, garudanetra=self.browser,
                                summary_lock=self.summary_lock)
        finally:
            lib.db.close()

    def _reap(self):
        complete = [f for f in self.futures if f.done()]
        results = []
        for future in complete:
            kind = self.futures.pop(future)
            try:
                result = future.result()
            except Exception as exc:
                result = {"status":"worker_error", "kind":kind,
                          "error":type(exc).__name__ + ": " + str(exc)[:180]}
            if (kind == "youtube" and isinstance(result, dict)
                    and result.get("status") in ("failed", "worker_error")
                    and youtube_rate_limited(result.get("error"))):
                # Only an observed provider 429 triggers the shared cooldown.
                self.youtube_access = record_youtube_rate_limit(self.root)
            if result is not None:
                self.last_result = result
                results.append(result)
        return results

    def pump(self, *, telemetry=None):
        if self.closed:
            raise RuntimeError("Adaptive workers already stopped")
        finished = self._reap()
        reading = telemetry if telemetry is not None else snapshot(self.root)
        capacity = plan_capacity(reading)
        # A managed low-power worker advertises its actual laptop profile.
        # Existing non-managed research retains the normal adaptive limits.
        if os.environ.get("SURYADEV_MAX_PARALLEL") == "1":
            capacity["max_total"] = min(1, capacity["max_total"])
            capacity["limits"] = {kind:min(1,limit) for kind,limit in capacity["limits"].items()}
            capacity["laptop_profile"] = "single-job"
            capacity["local_model_concurrency"] = 1
        # The cooldown is on disk to remain effective across worker restarts.
        self.youtube_access = youtube_access(self.root)
        if self.youtube_access["state"] == "rate_limited":
            capacity["limits"]["youtube"] = 0
        else:
            # One remote subtitle request at a time regardless of spare CPU.
            capacity["limits"]["youtube"] = min(1, capacity["limits"]["youtube"])
        active = {k:0 for k in KINDS}
        for kind in self.futures.values():
            active[kind] += 1
        queued = {k:0 for k in KINDS}
        lib = Library(self.root)
        try:
            for (url,) in lib.db.execute("SELECT url FROM jobs WHERE status='queued'"):
                kind = source_kind(url)
                if kind in queued:
                    queued[kind] += 1
        finally:
            lib.db.close()
        launched = []
        if capacity["safe"]:
            while len(self.futures) < capacity["max_total"]:
                # Rotate source priority to prevent PDFs or video starving web.
                choices = [KINDS[(self.rotation + offset) % len(KINDS)]
                           for offset in range(len(KINDS))]
                choice = next((kind for kind in choices
                               if queued[kind] > 0 and
                               active[kind] < capacity["limits"][kind] and
                               (kind != "website" or not self.browser_error)), None)
                if not choice:
                    break
                if choice == "website" and self.browser is None:
                    try:
                        tabs = 1 if os.environ.get("SURYADEV_BROWSER_TABS") == "1" else 4
                        self.browser = self.browser_factory(self.root, max_tabs=tabs)
                        self.browser.start()
                    except Exception as exc:
                        self.browser_error = type(exc).__name__ + ": " + str(exc)[:240]
                        self.browser = None
                        # Do not silently switch to urllib/Chrome and claim browser coverage.
                        continue
                task = self.pool.submit(self._work, choice)
                self.futures[task] = choice
                active[choice] += 1
                queued[choice] -= 1
                launched.append(choice)
                self.rotation = (KINDS.index(choice) + 1) % len(KINDS)
        youtube_blocked = (self.youtube_access["state"] == "rate_limited"
                           and queued["youtube"] > 0)
        state = ("busy" if self.futures else "paused" if not capacity["safe"]
                 else "paused" if self.browser_error and queued["website"]
                 else "paused" if youtube_blocked else "idle")
        detail = (self.browser_error if self.browser_error and queued["website"] else
                  capacity["reason"] if not capacity["safe"] else
                  self.youtube_access["reason"] if youtube_blocked else
                  f"{len(self.futures)} learning jobs active · {sum(queued.values())} queued")
        record = {**capacity,
                  "sample_time":time.time(), "state":state,
                  "engine":"Garudanetra Lite / Playwright Chromium",
                  "browser_error":self.browser_error or None,
                  "youtube_access":self.youtube_access,
                  "active":active, "queued":queued,
                  "launched_this_cycle":launched,
                  "active_total":len(self.futures),
                  "browser_tabs_open": None if not self.browser else len(self.browser._tabs),
                  "last_completed":self.last_result}
        atomic_json(self.root, CAPACITY_FILE, record)
        worker_note(self.root, state, self.check_seconds, detail,
                    next_check_at=time.time()+self.check_seconds,
                    last_result=self.last_result if isinstance(self.last_result,dict) else None)
        return {"finished":finished, "capacity":record}

    def close(self):
        if self.closed:
            return
        # Wait for durable job receipts; never abandon SQLite jobs mid-save.
        self.pool.shutdown(wait=True)
        self._reap()
        if self.browser:
            self.browser.stop()
        self.closed = True
        atomic_json(self.root, CAPACITY_FILE, {"state":"stopped",
                    "sample_time":time.time(), "active_total":0,
                    "active":{k:0 for k in KINDS},
                    "max_total":0, "limits":{k:0 for k in KINDS},
                    "engine":"Garudanetra Lite / Playwright Chromium"})

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
