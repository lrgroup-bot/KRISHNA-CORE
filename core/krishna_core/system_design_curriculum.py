from __future__ import annotations

import json
import os
import time
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from threading import RLock
from zoneinfo import ZoneInfo


OFFICIAL_SOURCES = (
    {
        "title": "Alex Xu / ByteByteGo official system-design references — Volume 1",
        "url": "https://github.com/alex-xu-system/bytebytego/blob/main/system_design_links.md",
        "kind": "official_reference_index",
    },
    {
        "title": "Alex Xu / ByteByteGo official system-design references — Volume 2",
        "url": "https://github.com/alex-xu-system/bytebytego/blob/main/system_design_links_vol2.md",
        "kind": "official_reference_index",
    },
    {
        "title": "ByteByteGo System Design 101",
        "url": "https://github.com/ByteByteGoHq/system-design-101",
        "kind": "official_public_learning_repo",
    },
)

PREFERRED_WINDOWS_IST = ("02:30", "14:30")
DEFAULT_START_DATE = "2026-10-01"


def _module(mid, volume, chapter, title, lead, team, question, apply_to):
    return {
        "id": mid,
        "volume": volume,
        "chapter": chapter,
        "title": title,
        "lead_rishi": lead,
        "team": list(dict.fromkeys((lead, *team, "gautama", "veda-vyasa"))),
        "question": question,
        "apply_to": list(apply_to),
    }


CURRICULUM = (
    _module("v1-01-scale", 1, 1, "Scale from zero to millions of users", "bharadvaja",
            ("chanakya", "jamadagni", "aryabhata"),
            "How should KRISHNA-style systems scale from one machine to distributed services while keeping failure domains, caches, databases and load balancing explicit?",
            ("KRISHNA control plane", "LR shared services advisory")),
    _module("v1-02-estimation", 1, 2, "Back-of-the-envelope estimation", "aryabhata",
            ("bharadvaja", "chanakya"),
            "Build reusable capacity-estimation methods for QPS, storage, bandwidth, RAM, latency budgets and growth assumptions.",
            ("resource governor", "capacity planning", "hardware planning")),
    _module("v1-03-framework", 1, 3, "System design framework", "bharadvaja",
            ("gautama", "veda-vyasa"),
            "Create a repeatable architecture-review sequence: requirements, constraints, estimates, APIs, data model, high-level design, bottlenecks, failure modes and trade-offs.",
            ("Project Genesis", "architecture reviews", "BRAHMA QC")),
    _module("v1-04-rate-limiter", 1, 4, "Rate limiter", "jamadagni",
            ("pingala", "bharadvaja"),
            "Which rate-limiting algorithms and distributed enforcement patterns best protect KRISHNA APIs, action buses and connectors without harming legitimate work?",
            ("Shared Action Bus", "API boundaries", "connector protection")),
    _module("v1-05-consistent-hashing", 1, 5, "Consistent hashing", "pingala",
            ("aryabhata", "jamadagni"),
            "When should KRISHNA use consistent hashing or rendezvous hashing for sharding, worker routing, cache placement and device assignment?",
            ("worker routing", "cache shards", "device routing")),
    _module("v1-06-kv-store", 1, 6, "Distributed key-value store", "pingala",
            ("jamadagni", "bharadvaja"),
            "Study partitioning, replication, quorum, conflict handling, Merkle trees, Bloom filters and LSM/SSTable trade-offs for durable state.",
            ("state stores", "cache/index layer", "knowledge metadata")),
    _module("v1-07-unique-id", 1, 7, "Distributed unique ID generator", "pingala",
            ("aryabhata", "jamadagni"),
            "Compare UUID, sequence, ticket and Snowflake-like IDs for sortable, collision-resistant event and mission identifiers.",
            ("event IDs", "mission IDs", "audit IDs")),
    _module("v1-08-url-shortener", 1, 8, "URL shortener", "vishvakarma",
            ("pingala", "bharadvaja"),
            "Use the URL-shortener design to study API contracts, key generation, redirects, caching and hot-key behavior.",
            ("short links", "API design patterns", "redirect services")),
    _module("v1-09-web-crawler", 1, 9, "Web crawler", "vishwamitra",
            ("jamadagni", "bharadvaja", "vashistha"),
            "Design a respectful research crawler with URL frontier, deduplication, robots/politeness, retries, content fingerprints and provenance.",
            ("GARUDA discovery", "BRAHMAGYAN acquisition", "ArchiveBox handoff")),
    _module("v1-10-notification", 1, 10, "Notification system", "jamadagni",
            ("bharadvaja", "chanakya"),
            "Design reliable multi-channel notifications with queues, retries, deduplication, user preferences, backoff and delivery observability.",
            ("KRISHNA alerts", "LR Watchtower advisory", "mobile notifications")),
    _module("v1-11-news-feed", 1, 11, "News feed", "chanakya",
            ("pingala", "bharadvaja"),
            "Study fan-out-on-write versus fan-out-on-read, ranking, cache strategy and hot-user behavior for attention queues and activity feeds.",
            ("activity feed", "work attention queue", "research updates")),
    _module("v1-12-chat", 1, 12, "Chat system", "jamadagni",
            ("pingala", "bharadvaja"),
            "Study WebSocket/session routing, message ordering, presence, offline delivery, durable history and idempotent message processing.",
            ("KRISHNA chat", "mobile companion", "agent messaging")),
    _module("v1-13-autocomplete", 1, 13, "Search autocomplete", "panini",
            ("pingala", "madhava"),
            "Study tries/prefix indexes, ranking, streaming updates, Unicode and cache patterns for fast multilingual autocomplete.",
            ("Gyan search", "command palette", "multilingual search")),
    _module("v1-14-video", 1, 14, "Video platform", "vishwamitra",
            ("chanakya", "jamadagni", "bharadvaja"),
            "Study upload, transcoding, object storage, CDN, metadata, chunking and failure recovery for large video-learning pipelines.",
            ("SURYDEV learning", "LR Production advisory", "media evidence")),
    _module("v1-15-drive", 1, 15, "Cloud drive / file sync", "jamadagni",
            ("pingala", "veda-vyasa", "bharadvaja"),
            "Study chunking, differential sync, conflict handling, metadata, object storage and offline reconciliation for KRISHNA device/file synchronization.",
            ("LocalSend workflows", "mobile sync", "knowledge artifacts")),

    _module("v2-01-proximity", 2, 1, "Proximity service", "baudhayana",
            ("aryabhata", "jamadagni"),
            "Study geohash/spatial indexes, radius search, caching and partitioning for nearby-object and field-service queries.",
            ("HAWKEYE geospatial", "field survey", "nearby services")),
    _module("v2-02-nearby-friends", 2, 2, "Nearby friends", "baudhayana",
            ("jamadagni", "gautama", "vashistha"),
            "Study real-time location updates, privacy boundaries, fan-out, geospatial indexing and stale-location handling.",
            ("HAWKEYE location", "trusted-device presence")),
    _module("v2-03-maps", 2, 3, "Google Maps-style system", "baudhayana",
            ("aryabhata", "chanakya"),
            "Study map tiling, routing graphs, ETA, geospatial storage, caching and offline map delivery.",
            ("HAWKEYE maps", "route planning", "offline geospatial")),
    _module("v2-04-message-queue", 2, 4, "Distributed message queue", "pingala",
            ("jamadagni", "chanakya", "bharadvaja"),
            "Study partitions, consumer groups, ordering, acknowledgements, replay, dead-letter queues and delivery semantics.",
            ("Durable Queue", "event bus", "agent jobs")),
    _module("v2-05-metrics", 2, 5, "Metrics monitoring", "madhava",
            ("jamadagni", "bharadvaja"),
            "Study metric ingestion, labels/cardinality, time-series storage, pull versus push, aggregation, alerting and tracing.",
            ("KRISHNA observability", "health dashboard", "SLOs")),
    _module("v2-06-ad-events", 2, 6, "Event aggregation / stream processing", "madhava",
            ("pingala", "aryabhata", "bharadvaja"),
            "Study exactly-once claims critically, event-time windows, deduplication, stream aggregation and batch/stream trade-offs.",
            ("analytics", "telemetry aggregation", "revenue/event reporting")),
    _module("v2-07-reservation", 2, 7, "Reservation system", "chanakya",
            ("jamadagni", "bharadvaja"),
            "Study concurrency control, inventory holds, idempotency, transactional boundaries, sagas and overbooking prevention.",
            ("inventory reservations", "booking workflows", "resource allocation")),
    _module("v2-08-email", 2, 8, "Distributed email service", "jamadagni",
            ("panini", "pingala"),
            "Study mail ingestion, queues, retries, search indexing, threading, spam/security controls and attachment storage.",
            ("Gmail connector architecture", "message indexing", "notification workflows")),
    _module("v2-09-object-storage", 2, 9, "S3-like object storage", "jamadagni",
            ("pingala", "bharadvaja"),
            "Study object metadata, data placement, checksums, replication/erasure coding, repair and consistency for durable artifacts.",
            ("Gyan archive", "media artifacts", "backups")),
    _module("v2-10-leaderboard", 2, 10, "Real-time leaderboard", "pingala",
            ("aryabhata", "madhava"),
            "Study sorted sets, ranking, partitioning, hot keys and approximate versus exact rank queries.",
            ("priority queues", "performance ranking", "non-financial scoring")),
    _module("v2-11-payment", 2, 11, "Payment system", "chanakya",
            ("jamadagni", "narada", "gautama"),
            "Study ledger integrity, idempotency, reconciliation, webhook reliability, fraud boundaries and double-entry accounting without enabling autonomous spending.",
            ("LR payment architecture advisory", "receive-only ledgers", "audit design")),
    _module("v2-12-wallet", 2, 12, "Digital wallet", "chanakya",
            ("jamadagni", "narada", "gautama"),
            "Study transactional invariants, ledgers, sagas, compensating transactions and auditability while preserving KRISHNA's zero-spend policy.",
            ("KUBER/LR FinTech advisory only", "ledger patterns")),
    _module("v2-13-exchange", 2, 13, "Stock exchange", "chanakya",
            ("madhava", "jamadagni", "narada"),
            "Study deterministic ordering, event sourcing, matching-engine latency, market-data fan-out, replay and operational resilience; do not convert this into trading autonomy.",
            ("KUBER architecture research", "high-throughput event systems")),

    _module("synthesis-01", 0, 29, "Cross-cutting distributed-systems synthesis", "veda-vyasa",
            ("bharadvaja", "gautama", "jamadagni", "pingala", "chanakya", "aryabhata"),
            "Synthesize reusable KRISHNA architecture patterns, anti-patterns, trade-offs and evidence-backed decision rules across both volumes.",
            ("BRAHMAGYAN system-design knowledge map",)),
    _module("synthesis-02", 0, 30, "Implementation gap audit", "bharadvaja",
            ("jamadagni", "vishwamitra", "veda-vyasa", "gautama"),
            "Compare learned system-design patterns against current KRISHNA architecture and produce a prioritized implement/test/do-not-implement backlog with evidence and measurable acceptance tests.",
            ("KRISHNA architecture backlog", "separate-project advisory outputs")),
)


class SystemDesignCurriculum:
    VERSION = "alex-xu-system-design-curriculum-v1"

    def __init__(self, state_root, memory=None):
        self.root = Path(state_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "system-design-curriculum.json"
        self.memory = memory
        self.lock = RLock()
        self.tz = ZoneInfo("Asia/Kolkata")
        self.start_date = date.fromisoformat(os.environ.get("KRISHNA_SYSTEM_DESIGN_START_DATE", DEFAULT_START_DATE))
        self.state = {
            "version": self.VERSION,
            "start_date": self.start_date.isoformat(),
            "timezone": "Asia/Kolkata",
            "preferred_windows": list(PREFERRED_WINDOWS_IST),
            "modules": {},
            "created_at": time.time(),
        }
        self._load()
        self.start_date = date.fromisoformat(str(self.state.get("start_date") or self.start_date.isoformat()))
        self._ensure_modules()

    def _load(self):
        if not self.path.is_file():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            self.state.update(raw)
            self.state.setdefault("modules", {})

    def _save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def _ensure_modules(self):
        changed = False
        with self.lock:
            for idx, module in enumerate(CURRICULUM):
                row = self.state["modules"].setdefault(module["id"], {
                    "status": "queued",
                    "attempts": 0,
                    "mission_ids": [],
                    "run_ids": [],
                    "last_scorecard": {},
                    "last_error": None,
                    "updated_at": None,
                })
                row["day"] = idx + 1
                row["scheduled_date"] = (self.start_date + timedelta(days=idx)).isoformat()
                changed = True
            if changed:
                self._save()

    @staticmethod
    def source_policy():
        return {
            "official_index": [dict(x) for x in OFFICIAL_SOURCES],
            "rules": [
                "Use Alex Xu/ByteByteGo official public reference lists as the syllabus index.",
                "Verify technical claims against current primary papers, standards, official product/docs, or engineering publications.",
                "Do not ingest unauthorized full-book PDF copies into BRAHMAGYAN.",
                "Do not treat multiple summaries copied from the same source as independent evidence.",
                "Store atomic claims with provenance and BRAHMAGYAN maturity; unresolved contradictions remain visible.",
            ],
        }

    def schedule(self):
        rows = []
        for idx, module in enumerate(CURRICULUM):
            state = self.state["modules"][module["id"]]
            rows.append({
                **module,
                "day": idx + 1,
                "scheduled_date": state["scheduled_date"],
                "preferred_windows_ist": list(PREFERRED_WINDOWS_IST),
                "status": state["status"],
                "attempts": state["attempts"],
            })
        return {
            "version": self.VERSION,
            "start_date": self.start_date.isoformat(),
            "timezone": "Asia/Kolkata",
            "new_modules_per_day": 1,
            "preferred_windows_ist": list(PREFERRED_WINDOWS_IST),
            "catch_up_rule": "missed or insufficiently verified modules carry forward; never skip ahead just to match the calendar",
            "resource_rule": "run only when BRAHMAGYAN background gate permits: production idle, CPU < 50%, RAM < 70%",
            "modules": rows,
            "source_policy": self.source_policy(),
        }

    def _module_for_id(self, module_id):
        for module in CURRICULUM:
            if module["id"] == module_id:
                return module
        raise KeyError(module_id)

    def next_assignment(self, now=None):
        now = now or datetime.now(self.tz)
        if now.tzinfo is None:
            now = now.replace(tzinfo=self.tz)
        today = now.astimezone(self.tz).date()

        # Retry the earliest unfinished module before advancing.
        for module in CURRICULUM:
            state = self.state["modules"][module["id"]]
            scheduled = date.fromisoformat(state["scheduled_date"])
            if scheduled <= today and state["status"] not in {"verified", "skipped"}:
                return self._assignment(module, state, today)

        # If deployed before the start date, expose the first upcoming assignment.
        first = CURRICULUM[0]
        first_state = self.state["modules"][first["id"]]
        if today < date.fromisoformat(first_state["scheduled_date"]):
            row = self._assignment(first, first_state, today)
            row["not_before"] = first_state["scheduled_date"]
            return row
        return None

    def _assignment(self, module, state, today):
        return {
            **module,
            "day": state["day"],
            "scheduled_date": state["scheduled_date"],
            "today": today.isoformat(),
            "preferred_windows_ist": list(PREFERRED_WINDOWS_IST),
            "attempt": int(state.get("attempts") or 0) + 1,
            "research_instruction": (
                f"Study '{module['title']}' using the official Alex Xu/ByteByteGo reference index as a syllabus. "
                "Then verify each reusable design claim against primary/current engineering sources. "
                "Extract atomic claims, trade-offs, failure modes, implementation conditions and tests. "
                "Do not copy or ingest unauthorized book PDFs. "
                f"Application question: {module['question']}"
            ),
            "source_policy": self.source_policy(),
        }

    def record_result(self, module_id, *, mission_id=None, run_id=None, scorecard=None, error=None):
        module = self._module_for_id(module_id)
        scorecard = dict(scorecard or {})
        with self.lock:
            row = self.state["modules"][module_id]
            row["attempts"] = int(row.get("attempts") or 0) + 1
            if mission_id and str(mission_id) not in row["mission_ids"]:
                row["mission_ids"].append(str(mission_id))
            if run_id and str(run_id) not in row["run_ids"]:
                row["run_ids"].append(str(run_id))
            row["last_scorecard"] = scorecard
            row["last_error"] = str(error)[:1000] if error else None
            cross_checked = int(scorecard.get("cross_checked_claims") or 0)
            source_count = int(scorecard.get("source_count") or 0)
            if error:
                row["status"] = "retry" if row["attempts"] < 3 else "needs_human_review"
            elif cross_checked > 0 and source_count >= 2:
                row["status"] = "verified"
            else:
                row["status"] = "retry" if row["attempts"] < 3 else "needs_human_review"
            row["updated_at"] = time.time()
            self._save()
        if self.memory:
            self.memory.audit(
                "brahmagyan_system_design",
                row["status"],
                f"{module_id}:{module['lead_rishi']}:{row['attempts']}:{mission_id or ''}",
            )
        return {**module, **json.loads(json.dumps(row))}

    def status(self):
        rows = list(self.state["modules"].values())
        counts = {}
        for row in rows:
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        return {
            "version": self.VERSION,
            "start_date": self.start_date.isoformat(),
            "timezone": "Asia/Kolkata",
            "preferred_windows_ist": list(PREFERRED_WINDOWS_IST),
            "total_modules": len(CURRICULUM),
            "status_counts": counts,
            "next_assignment": self.next_assignment(),
            "source_policy": self.source_policy(),
        }


class SystemDesignLearningScheduler:
    """Lightweight clock only; actual research remains resource-gated by BRAHMAGYAN."""

    def __init__(self, state_root, run_tick, *, poll_seconds=900):
        self.root = Path(state_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "system-design-scheduler.json"
        self.run_tick = run_tick
        self.poll_seconds = max(300, int(poll_seconds))
        self.tz = ZoneInfo("Asia/Kolkata")
        self._stop = threading.Event()
        self._thread = None
        self._lock = RLock()
        self.state = {
            "version": 1,
            "preferred_windows_ist": list(PREFERRED_WINDOWS_IST),
            "last_window_key": None,
            "last_verified_date": None,
            "last_run_at": None,
            "last_result": None,
            "last_error": None,
            "run_count": 0,
        }
        self._load()

    def _load(self):
        if not self.path.is_file():
            self._save()
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self.state.update(raw)
        except Exception as exc:
            self.state["last_error"] = f"state_load:{type(exc).__name__}: {exc}"

    def _save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def due_window(self, now=None):
        now = now or datetime.now(self.tz)
        if now.tzinfo is None:
            now = now.replace(tzinfo=self.tz)
        local = now.astimezone(self.tz)
        today = local.date().isoformat()
        if self.state.get("last_verified_date") == today:
            return None
        eligible = []
        for value in PREFERRED_WINDOWS_IST:
            hour, minute = (int(x) for x in value.split(":"))
            candidate = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if local >= candidate:
                eligible.append((candidate, value))
        if not eligible:
            return None
        _, window = eligible[-1]
        key = f"{today}@{window}"
        if self.state.get("last_window_key") == key:
            return None
        return {"key": key, "date": today, "window": window}

    def run_once(self, *, now=None, force=False):
        with self._lock:
            due = self.due_window(now)
            if not force and not due:
                return {"status": "not_due", **self.status()}
            local = (now or datetime.now(self.tz)).astimezone(self.tz)
            due = due or {"key": f"{local.date().isoformat()}@forced", "date": local.date().isoformat(), "window": "forced"}
            self.state["last_window_key"] = due["key"]
            self.state["last_run_at"] = time.time()
            self.state["run_count"] = int(self.state.get("run_count") or 0) + 1
            try:
                result = self.run_tick()
                self.state["last_result"] = result
                self.state["last_error"] = None
                module = (result or {}).get("curriculum_module") or {}
                if module.get("status") == "verified":
                    self.state["last_verified_date"] = due["date"]
                status = "completed"
            except Exception as exc:
                result = None
                self.state["last_error"] = f"{type(exc).__name__}: {exc}"
                status = "error"
            self._save()
            return {"status": status, "window": due, "result": result, "error": self.state.get("last_error")}

    def start(self):
        if self._thread and self._thread.is_alive():
            return self.status()
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="krishna-system-design-learning", daemon=True)
        self._thread.start()
        return self.status()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        return self.status()

    def _loop(self):
        while not self._stop.is_set():
            if self.due_window():
                self.run_once()
            if self._stop.wait(self.poll_seconds):
                break

    def status(self):
        return {
            "running": bool(self._thread and self._thread.is_alive()),
            "poll_seconds": self.poll_seconds,
            "policy": (
                "lightweight scheduler only; at most one verified module per local day; "
                "actual web/model research is still blocked unless BRAHMAGYAN resource gates permit it"
            ),
            **self.state,
        }
