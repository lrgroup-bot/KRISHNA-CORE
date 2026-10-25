"""Hardware-auto-admitted parallel SURYADEV research with Garudanetra tabs.

Large approved worklists (including 100 PDFs) can be queued without
implying all tasks can execute at once. Per-cycle admission comes from
measured hardware headroom and is shared with video/browser/book pools.
Expensive local model inference stays serialized to protect the laptop.
No new jobs are launched if psutil metrics are missing or unsafe.
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
# Workload ceilings, not a fixed degree of parallelism.
# Any portion may be pending in the queue while auto-admission runs fewer jobs.
SOURCE_TARGETS = {"website": 10, "youtube": 10, "pdf": 100}
BOOK_TARGET = 5
MAX_PARALLEL = sum(SOURCE_TARGETS.values())
TOTAL_TARGET = MAX_PARALLEL + BOOK_TARGET
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


def plan_capacity(reading, *, logical_cpus=None, collector_only=False):
    """Conservative measured headroom, not an invented fixed laptop capacity."""
    if not isinstance(reading, dict) or reading.get("available") is not True:
        return {"safe": False, "reason": "psutil telemetry unavailable",
                "max_total": 0, "limits": {k:0 for k in KINDS},
                "cpu_percent": None, "ram_percent": None}

    # A failed sensor or malformed cached sample must NEVER look like unused
    # hardware. NaN silently bypasses numeric comparisons and can otherwise
    # turn a damaged hardware report into positive worker admission.
    required = ("cpu_percent", "ram_percent", "disk_percent",
                "ram_total_gb", "ram_used_gb", "disk_free_gb")
    values = {}
    for metric in required:
        value = reading.get(metric)
        if type(value) not in (int, float) or not math.isfinite(value):
            return {"safe": False, "reason": "Invalid or missing hardware telemetry: " + metric,
                    "max_total": 0, "limits": {k: 0 for k in (*KINDS, "book")},
                    "cpu_percent": None, "ram_percent": None}
        values[metric] = float(value)
    cpu, ram, disk, total_ram, used_ram, disk_free = (
        values[name] for name in required)
    if (not 0 <= cpu <= 100 or not 0 <= ram <= 100
            or not 0 <= disk <= 100 or total_ram <= 0
            or not 0 <= used_ram <= total_ram or disk_free < 0):
        return {"safe": False, "reason": "Out-of-range hardware telemetry",
                "max_total": 0, "limits": {k: 0 for k in (*KINDS, "book")},
                "cpu_percent": None, "ram_percent": None}
    gpu = reading.get("gpu") or {}
    if not isinstance(gpu, dict):
        return {"safe": False, "reason": "Invalid GPU telemetry",
                "max_total": 0, "limits": {k: 0 for k in (*KINDS, "book")},
                "cpu_percent": cpu, "ram_percent": ram}
    if gpu.get("available"):
        for metric in ("usage_percent", "vram_percent"):
            value = gpu.get(metric)
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 100:
                return {"safe": False, "reason": "Missing or invalid GPU telemetry: " + metric,
                        "max_total": 0, "limits": {k: 0 for k in (*KINDS, "book")},
                        "cpu_percent": cpu, "ram_percent": ram}
    temp = reading.get("temperature_max_c")
    if temp is not None and (type(temp) not in (int, float) or
                             not math.isfinite(temp) or not -50 <= temp <= 200):
        return {"safe": False, "reason": "Invalid thermal telemetry",
                "max_total": 0, "limits": {k: 0 for k in (*KINDS, "book")},
                "cpu_percent": cpu, "ram_percent": ram}
    if reading.get("battery_plugged") is False:
        battery = reading.get("battery_percent")
        if type(battery) not in (int, float) or not math.isfinite(battery) or not 0 <= battery <= 100:
            return {"safe": False, "reason": "Unverified unplugged battery charge",
                    "max_total": 0, "limits": {k: 0 for k in (*KINDS, "book")},
                    "cpu_percent": cpu, "ram_percent": ram}
    try:
        cpus = max(1, int(logical_cpus or os.cpu_count() or 1))
    except (ValueError, TypeError, OverflowError):
        cpus = 1
    free = total_ram - used_ram
    gpu_hot = (gpu.get("available") is True and
               (gpu["usage_percent"] >= 85 or gpu["vram_percent"] >= 85))
    reason = ""
    if cpu >= 85 or ram >= 85 or disk >= 85 or disk_free < 2 or gpu_hot:
        reason = "Hardware guard: CPU/RAM/disk/GPU exceeded safe limits"
    elif (reading.get("battery_plugged") is False and
          reading.get("battery_percent") is not None and
          float(reading["battery_percent"]) <= 20):
        reason = "Power guard: unplugged battery at or below 20%"
    elif (reading.get("temperature_max_c") is not None and
          float(reading["temperature_max_c"]) >= 85):
        reason = "Thermal guard: observed device sensor at or above 85 C"
    elif free < (0.75 if collector_only else 2.7):
        reason = ("Less than 0.75 GiB free for evidence-only collection" if collector_only
                  else "Less than 2.7 GiB available RAM")
    if reason:
        return {"safe":False, "reason":reason, "max_total":0,
                "limits":{k:0 for k in KINDS},
                "cpu_percent":cpu, "ram_percent":ram,
                "disk_free_gb":disk_free, "free_ram_gb":round(free,2)}
    # A collector does not load a local LLM, so its reserve should adapt to
    # the actual device instead of assuming every node is a 16 GiB laptop.
    # Retain 85% as the hard admission ceiling in BOTH modes. Browser and
    # PDF work still need nonzero free RAM; neither mode guarantees capacity.
    total_ram = float(reading["ram_total_gb"])
    reserve_gb = (max(0.5, min(1.5, total_ram * 0.15))
                  if collector_only else 2.0)
    per_slot_gb = 0.75 if collector_only else 1.35
    mem_budget = max(0.0, min(free - reserve_gb,
                              total_ram * (0.85 - ram / 100)))
    ram_slots = int(math.floor(mem_budget / per_slot_gb))
    cpu_slots = max(1, cpus // 2)
    total = max(0, min(TOTAL_TARGET, cpu_slots, ram_slots))
    if cpu >= 70 or ram >= 75:
        total = min(total, 1)
    limits = {
        "website": min(SOURCE_TARGETS["website"], total),
        # Ten scheduled YouTube assignments must not create ten
        # simultaneous provider requests (or evade HTTP 429).
        "youtube": min(1, SOURCE_TARGETS["youtube"], total),
        "pdf": min(SOURCE_TARGETS["pdf"], total),
        "book": min(BOOK_TARGET, total),
    }
    return {"safe":total > 0,
            "reason":"Measured hardware admission passed" if total else "No remaining safe CPU/RAM slots",
            "max_total":total, "limits":limits,
            "target_slots":{**SOURCE_TARGETS, "book": BOOK_TARGET},
            "target_total":TOTAL_TARGET,
            "capacity_mode":"automatic_hardware",
            "backlog_is_not_running":True,
            "youtube_provider_concurrent_limit":1,
            "cpu_percent":cpu, "ram_percent":ram,
            "disk_free_gb":disk_free, "free_ram_gb":round(free,2),
            "logical_cpus":cpus, "cpu_ceiling_percent":85,
            "memory_reserve_gb":reserve_gb,
            "processing_mode":"collector_only" if collector_only else "local_inference",
            "local_model_concurrency":0 if collector_only else 1}


class AdaptiveResearchWorkers:
    """One supervisor/worker lock owns a pool of per-thread SQLite connections."""
    def __init__(self, root, *, use_ollama=True, model="qwen3.5:9b",
                 check_seconds=60, browser_factory=GarudanetraLite,
                 books_enabled=False):
        self.root = Path(root).expanduser().resolve()
        self.use_ollama = use_ollama
        self.model = model
        self.check_seconds = check_seconds
        self.browser_factory = browser_factory
        self.books_enabled = bool(books_enabled)
        self.video_enabled = False
        self._dual_lane_turn = 0
        self.external_active = 0
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

    def pump(self, *, telemetry=None, admit_new=True):
        if self.closed:
            raise RuntimeError("Adaptive workers already stopped")
        finished = self._reap()
        reading = telemetry if telemetry is not None else snapshot(self.root)
        capacity = plan_capacity(reading, collector_only=not self.use_ollama)
        # Optional operator cap only REDUCES measured capacity, never raises
        # it. Unset means automatic scaling rather than a hardcoded 45.
        # The fresh-session limit belongs to the data root, not merely to
        # the dashboard launcher. It remains enforced for CLI workers too.
        # Historical/nonfresh high-capacity server profiles stay unchanged.
        workspace = _safe_read(self.root,"fresh-workspace.json",max_bytes=4096)
        fresh_mode = workspace.get("schema") == "suryadev.fresh-workspace.v1"
        fleet_adaptive = fresh_mode and workspace.get("node_profile") == "fleet_adaptive"
        requested = os.environ.get("SURYADEV_MAX_PARALLEL", "").strip()
        if fresh_mode:
            try:
                cap = int(requested) if requested else (TOTAL_TARGET if fleet_adaptive else 3)
            except ValueError:
                cap = 1
            # The cap can only REDUCE sampled resource admission; it can never
            # bypass memory, CPU, GPU, temperature, source or provider gates.
            requested = str(max(1,min(TOTAL_TARGET if fleet_adaptive else 3,cap)))
        if requested:
            try:
                ceiling = int(requested)
                if not 1 <= ceiling <= TOTAL_TARGET:
                    raise ValueError
            except ValueError:
                ceiling = 1  # malformed configuration fails closed
            capacity["max_total"] = min(ceiling, capacity["max_total"])
            capacity["limits"] = {kind:min(ceiling, limit)
                                  for kind,limit in capacity["limits"].items()}
            capacity["laptop_profile"] = ("single-job" if ceiling == 1 else
                                          "measured-maximum-" + str(ceiling))
        capacity["node_profile"] = "fleet_adaptive" if fleet_adaptive else "legacy"
        # Reserve capacity for independent books and actual Chromium video
        # observations; all run inside THIS supervisor's one-worker lock.
        # Always retain at least one source lane when possible.
        total = capacity["max_total"]
        reserve_books = (min(BOOK_TARGET, max(1,total // 4))
                         if self.books_enabled and total > 1 else 0)
        reserve_books = min(reserve_books,max(0,total-1))
        # When the approved queue contains ONLY browser videos, use spare
        # measured slots for 2-3 distinct observers rather than forcing one
        # video lane while the other slots stay idle. Any waiting website/PDF/
        # caption source keeps one source slot. Pending books keep their reserve.
        # This is still bounded by the shared fresh-node cap and 85% guard.
        pending_source = False
        if self.video_enabled and total:
            queued_db = Library(self.root)
            try:
                pending_source = bool(queued_db.db.execute(
                    "SELECT 1 FROM jobs WHERE status='queued' LIMIT 1"
                ).fetchone())
            finally:
                queued_db.db.close()
        video_budget = max(0, total - reserve_books - (1 if pending_source else 0))
        reserve_video = (min(SOURCE_TARGETS["youtube"], video_budget)
                         if self.video_enabled else 0)
        if total == 2 and self.books_enabled and self.video_enabled:
            # Only one non-source slot exists. Alternate which lane may
            # claim it instead of permanently starving videos or books.
            self._dual_lane_turn += 1
            reserve_books, reserve_video = (
                (1,0) if (self._dual_lane_turn // 5) % 2 == 0 else (0,1))
        capacity["reserved_book_slots"] = reserve_books
        capacity["reserved_video_slots"] = reserve_video
        capacity["source_execution_slots"] = max(
            0,min(MAX_PARALLEL,total-reserve_books-reserve_video,
                  total-max(0,int(self.external_active))))
        capacity["non_source_active"] = max(0,int(self.external_active))
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
        # Gradual ramp: starting dozens of Chromium/PDF tasks from a single
        # stale measurement can transiently overload even a large server.
        # The next cycle samples actual utilization before admitting more.
        max_new_this_sample = min(4, capacity["source_execution_slots"])
        capacity["new_source_launch_limit_this_sample"] = max_new_this_sample
        if capacity["safe"] and admit_new:
            while (len(self.futures) < capacity["source_execution_slots"]
                   and len(launched) < max_new_this_sample):
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
                        tabs = 1 if os.environ.get("SURYADEV_BROWSER_TABS") == "1" else min(10, max(1,capacity["source_execution_slots"]))
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
        # Hardware admission is separate from the lifecycle rest.
        # Retain the sampled hardware result but advertise zero new slots.
        if not admit_new:
            capacity["hardware_safe_before_mission_pause"] = capacity["safe"]
            capacity["safe"] = False
            capacity["max_total"] = 0
            capacity["source_execution_slots"] = 0
            capacity["reserved_book_slots"] = 0
            capacity["reserved_video_slots"] = 0
            capacity["limits"] = {name: 0 for name in capacity["limits"]}
            capacity["mission_admission_paused"] = True
            capacity["reason"] = "Six-hour mission boundary: draining or mandatory ten-minute rest"
        youtube_blocked = (self.youtube_access["state"] == "rate_limited"
                           and queued["youtube"] > 0)
        capacity["over_admitted_inflight"] = max(
            0, len(self.futures) - capacity["source_execution_slots"])
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
