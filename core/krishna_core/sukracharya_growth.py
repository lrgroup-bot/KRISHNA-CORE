from __future__ import annotations

"""Rishi Sukracharya: evidence-first business growth research for KRISHNA -> LR Group advisory."""

from dataclasses import dataclass
from pathlib import Path
from threading import Event, Lock, Thread
from urllib import request
import json
import os
import time
import uuid


SUKRACHARYA_SCHEMA = "krishna.lr-group.sukracharya-finding.v1"
DEFAULT_LR_GROUP_URL = "http://127.0.0.1:8788/api/advisory/sukracharya"

GROWTH_FOCUS_ROTATION = (
    "customer discovery, product-market fit and unmet demand",
    "pricing, willingness-to-pay, unit economics and contribution margin",
    "retention, repeat purchase, referral loops and customer lifetime value",
    "distribution, sales channels, partnerships and route-to-market",
    "competitor intelligence, substitutes, market gaps and strategic differentiation",
    "geographic expansion and adjacent markets with a defensible right-to-win",
    "cross-company synergies across the LR Group portfolio",
    "business model design, monetization and recurring revenue",
    "cash conversion, working capital, capacity utilization and cost-to-serve",
    "portfolio choices: start, improve, scale, pause or investigate",
)

YOUTUBE_SEEDS = (
    {
        "title": "How to Get and Evaluate Startup Ideas | Startup School",
        "url": "https://www.youtube.com/watch?v=Th8JoIan4dg",
        "publisher": "Y Combinator",
        "topics": ["opportunity discovery", "idea evaluation", "market need"],
    },
    {
        "title": "How To Talk To Users | Startup School",
        "url": "https://www.youtube.com/watch?v=z1iF1c8w5Lg",
        "publisher": "Y Combinator",
        "topics": ["customer discovery", "user interviews", "product-market fit"],
    },
    {
        "title": "Business Model Canvas overview",
        "url": "https://www.youtube.com/watch?v=QoAOzMTLP5s",
        "publisher": "Strategyzer",
        "topics": ["business model", "value creation", "value capture"],
    },
    {
        "title": "Lecture 1 - How to Start a Startup",
        "url": "https://www.youtube.com/watch?v=CBYhVcO4WgI",
        "publisher": "YC Root Access",
        "topics": ["ideas", "products", "teams", "execution"],
    },
)

YOUTUBE_DISCOVERY_QUERIES = (
    'site:youtube.com business growth strategy pricing unit economics customer discovery',
    'site:youtube.com Y Combinator growth pricing customer acquisition retention startup',
    'site:youtube.com Strategyzer business model testing value proposition growth',
    'site:youtube.com Stanford GSB growth strategy pricing distribution business',
)

DEBATE_TEAM = (
    "sukracharya",
    "gautama",
    "chanakya",
    "jamadagni",
    "narada",
    "veda-vyasa",
)


@dataclass(frozen=True)
class DeliveryResult:
    delivered: bool
    queued: bool
    status_code: int | None = None
    error: str | None = None
    response: dict | None = None

    def as_dict(self):
        return {
            "delivered": self.delivered,
            "queued": self.queued,
            "status_code": self.status_code,
            "error": self.error,
            "response": self.response,
        }


class SukracharyaGrowthRishi:
    VERSION = "sukracharya-growth-v1"

    def __init__(self, root, *, rishi_live, suryadev=None, memory=None, lr_group_url=None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "state.json"
        self.outbox_path = self.root / "lr-group-outbox.jsonl"
        self.rishi_live = rishi_live
        self.suryadev = suryadev
        self.memory = memory
        self.lr_group_url = str(
            lr_group_url
            or os.getenv("KRISHNA_LR_GROUP_ADVISORY_URL")
            or DEFAULT_LR_GROUP_URL
        ).strip()
        self.state = self._load_state()

    def _load_state(self):
        if not self.state_path.is_file():
            return {"focus_index": 0, "seen_videos": [], "cycles": 0, "last_cycle_at": None}
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            return {
                "focus_index": int(raw.get("focus_index") or 0),
                "seen_videos": list(raw.get("seen_videos") or [])[-500:],
                "cycles": int(raw.get("cycles") or 0),
                "last_cycle_at": raw.get("last_cycle_at"),
            }
        except Exception:
            return {"focus_index": 0, "seen_videos": [], "cycles": 0, "last_cycle_at": None}

    def _save_state(self):
        self.state_path.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _is_youtube(url):
        value = str(url or "").lower()
        return "youtube.com/watch" in value or "youtu.be/" in value

    def research_plan(self, *, company_id="lr-group", focus=""):
        focus = str(focus or "").strip()
        if not focus:
            idx = self.state["focus_index"] % len(GROWTH_FOCUS_ROTATION)
            focus = GROWTH_FOCUS_ROTATION[idx]
        return {
            "rishi": "sukracharya",
            "display_name": "Rishi Śukrācārya",
            "authority": "advisory-only",
            "company_id": company_id,
            "focus": focus,
            "project": "LR-GROUP-ADVISORY",
            "research_questions": [
                f"What current evidence supports or weakens growth opportunities in {focus}?",
                f"What assumptions in {focus} would need to be true for LR Group to create durable profit or cash?",
                f"What customer, competitor, pricing, channel, operating and regulatory evidence is missing for {focus}?",
                f"What low-cost test can falsify the riskiest hypothesis in {focus} before scale?",
                f"What cross-company synergies or conflicts inside LR Group affect {focus}?",
            ],
            "youtube_discovery_queries": list(YOUTUBE_DISCOVERY_QUERIES),
            "youtube_seed_videos": [dict(x) for x in YOUTUBE_SEEDS],
            "debate_team": list(DEBATE_TEAM),
            "evidence_rules": [
                "separate facts, hypotheses, forecasts and recommendations",
                "require source URL/title and observation date for material external claims",
                "YouTube commentary is a research lead, not proof by itself",
                "search for counter-evidence and base rates before recommending scale",
                "express pricing and growth claims as measurable hypotheses with thresholds",
                "preserve unresolved disagreement for LR Group debate",
            ],
        }

    def _garuda(self):
        return getattr(self.rishi_live, "garuda", None)

    def discover_youtube(self, *, focus="", limit=6):
        limit = max(1, min(int(limit), 12))
        garuda = self._garuda()
        found = []
        seen = set(self.state.get("seen_videos") or [])
        queries = list(YOUTUBE_DISCOVERY_QUERIES)
        if focus:
            queries.insert(0, f"site:youtube.com {focus} business growth strategy")
        if garuda is not None and hasattr(garuda, "scout"):
            for q in queries[:3]:
                try:
                    report = garuda.scout("LR-GROUP-ADVISORY", q, max(4, limit))
                except Exception:
                    continue
                for row in (report or {}).get("web") or []:
                    item = row if isinstance(row, dict) else getattr(row, "__dict__", {})
                    url = str(item.get("url") or "").strip()
                    if not self._is_youtube(url) or url in seen or any(x["url"] == url for x in found):
                        continue
                    found.append({
                        "title": str(item.get("title") or "YouTube growth research"),
                        "url": url,
                        "publisher": str(item.get("source") or "youtube"),
                        "topics": [focus] if focus else [],
                        "discovered": True,
                    })
                    if len(found) >= limit:
                        break
                if len(found) >= limit:
                    break
        if len(found) < limit:
            for seed in YOUTUBE_SEEDS:
                if seed["url"] in seen or any(x["url"] == seed["url"] for x in found):
                    continue
                found.append(dict(seed))
                if len(found) >= limit:
                    break
        return found

    def queue_youtube_learning(self, *, focus="", limit=2):
        if self.suryadev is None:
            return {"queued": 0, "jobs": [], "reason": "suryadev_not_bound"}
        videos = self.discover_youtube(focus=focus, limit=limit)
        jobs = []
        for video in videos:
            job = self.suryadev.create_job(
                "video_research",
                project="LR-GROUP-ADVISORY",
                target=video["url"],
                instructions=(
                    "Study this business-growth material as candidate evidence for Rishi Sukracharya. "
                    "Create timestamped transcript chunks and selected visual evidence. Extract concrete claims about "
                    "customers, pricing, unit economics, retention, channels, partnerships, expansion, business models "
                    "or growth execution. Mark opinions and forecasts separately. Generate questions for independent "
                    "web verification and counter-evidence. Do not treat speaker authority or view count as proof."
                ),
                source_ref=video["url"],
                constraints={
                    "subject": focus or "business growth",
                    "finish_grace_seconds": 300,
                    "raw_media_transfer": False,
                    "rishi": "sukracharya",
                },
                requested_by="sukracharya",
            )
            jobs.append({"video": video, "job": job})
            self.state.setdefault("seen_videos", []).append(video["url"])
        self.state["seen_videos"] = self.state["seen_videos"][-500:]
        self._save_state()
        return {"queued": len(jobs), "jobs": jobs}

    def run_research(self, *, company_id="lr-group", focus="", privacy="approved_cloud"):
        plan = self.research_plan(company_id=company_id, focus=focus)
        question = " ".join(plan["research_questions"])
        return self.rishi_live.run(
            "LR-GROUP-ADVISORY",
            plan["focus"],
            question,
            rishi_id="sukracharya",
            knowledge_track="general",
            stakes="high",
            privacy=privacy,
            source_limit=8,
            max_perspectives=6,
            max_claims=6,
            auto_propose=False,
            preferred_rishis=list(DEBATE_TEAM),
        )

    @staticmethod
    def _unique_sources(claims):
        rows = []
        seen = set()
        for claim in claims:
            for bucket in ("sources", "supporting_evidence", "qualifying_evidence", "contradicting_evidence"):
                for source in claim.get(bucket) or []:
                    url = str(source.get("url") or source.get("source_ref") or "").strip()
                    title = str(source.get("title") or source.get("name") or "").strip()
                    key = url or title
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    rows.append({
                        "title": title,
                        "url": url,
                        "source_family": source.get("source_family"),
                        "source_type": source.get("source_type"),
                        "primary": bool(source.get("primary", False)),
                        "citation_notes": source.get("citation_notes"),
                    })
        return rows

    def packet_from_run(self, run_result, *, company_id="lr-group"):
        run_result = dict(run_result or {})
        run = dict(run_result.get("run") or {})
        mission = dict(run_result.get("mission") or {})
        synthesis = dict(run_result.get("synthesis") or {})
        claim_ids = list(mission.get("claim_ids") or [])
        claims = []
        for claim_id in claim_ids:
            try:
                claims.append(self.rishi_live.brahmagyan.claim(claim_id))
            except Exception:
                continue
        sources = self._unique_sources(claims)
        finding = str(synthesis.get("summary") or "").strip()
        if not finding and claims:
            finding = "; ".join(str(x.get("claim") or "") for x in claims[:3])
        if not finding:
            finding = "Research completed without a sufficiently supported synthesized growth finding."
        confidences = [
            float(x.get("confidence"))
            for x in claims
            if x.get("confidence") is not None
        ]
        confidence = (sum(confidences) / len(confidences)) if confidences else None
        packet = {
            "schema": SUKRACHARYA_SCHEMA,
            "packetId": str(uuid.uuid4()),
            "requestId": mission.get("mission_id") or run.get("mission_id") or run.get("run_id"),
            "researchRunId": run.get("run_id"),
            "missionId": mission.get("mission_id"),
            "companyId": company_id,
            "topic": mission.get("topic"),
            "question": mission.get("question"),
            "source": {
                "system": "KRISHNA",
                "rishi": "sukracharya",
                "displayName": "Rishi Śukrācārya",
                "authority": "advisory-only",
            },
            "target": {
                "system": "LR Group",
                "recipients": [
                    "lr-intelligence",
                    "lr-strategy-growth",
                    "lr-sales",
                    "lr-ca",
                    "lr-legal",
                    "lr-compliance",
                    "lr-audit-risk",
                ],
            },
            "finding": finding,
            "claims": [{
                "claimId": x.get("claim_id"),
                "claim": x.get("claim"),
                "maturity": x.get("maturity"),
                "evidenceStatus": x.get("evidence_status"),
                "confidence": x.get("confidence"),
            } for x in claims],
            "sources": sources,
            "observedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "confidence": confidence,
            "supported": list(synthesis.get("supported") or []),
            "contested": list(synthesis.get("contested") or []),
            "limitations": list(synthesis.get("unknowns") or []),
            "nextEvidence": list(synthesis.get("next_evidence") or []),
            "tests": list((run_result.get("test_plan") or {}).get("tests") or []),
            "debateRequired": True,
            "requiredChallenges": [
                "evidence and source independence",
                "customer and demand reality",
                "pricing and unit economics",
                "cash and time-to-value",
                "competitor response and strategic differentiation",
                "failure modes and downside",
                "legal and compliance constraints",
                "implementation feasibility",
            ],
            "requiresIndependentBusinessValidation": True,
            "decisionAuthority": "LR Group and owner approval gates; KRISHNA/Sukracharya has no execution authority",
        }
        return packet

    def _queue_outbox(self, packet, error):
        row = {
            "queuedAt": time.time(),
            "error": str(error),
            "packet": packet,
        }
        with self.outbox_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        return DeliveryResult(False, True, error=str(error)).as_dict()

    def deliver(self, packet, *, timeout=5):
        data = json.dumps(packet, ensure_ascii=False).encode("utf-8")
        headers = {"content-type": "application/json"}
        token = str(os.getenv("KRISHNA_LR_GROUP_ADVISORY_TOKEN") or "").strip()
        if token:
            headers["x-lr-group-advisory-token"] = token
        req = request.Request(self.lr_group_url, data=data, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=max(1, int(timeout))) as response:
                raw = response.read().decode("utf-8", errors="replace")
                body = json.loads(raw) if raw.strip() else {}
                result = DeliveryResult(True, False, response.status, response=body).as_dict()
        except Exception as exc:
            result = self._queue_outbox(packet, exc)
        if self.memory is not None:
            try:
                self.memory.audit(
                    "sukracharya_lr_group_delivery",
                    "delivered" if result["delivered"] else "queued",
                    str(packet.get("packetId") or ""),
                )
            except Exception:
                pass
        return result

    def retry_outbox(self, *, timeout=5, limit=20):
        """Retry queued LR Group packets without creating another queued copy on failure."""
        if not self.outbox_path.is_file():
            return {"attempted": 0, "delivered": 0, "remaining": 0}
        try:
            rows = [
                json.loads(line)
                for line in self.outbox_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except Exception as exc:
            return {"attempted": 0, "delivered": 0, "remaining": None, "error": str(exc)}
        attempted = delivered = 0
        remaining = []
        for row in rows:
            if attempted >= max(1, int(limit)):
                remaining.append(row)
                continue
            packet = dict(row.get("packet") or {})
            if not packet:
                continue
            attempted += 1
            data = json.dumps(packet, ensure_ascii=False).encode("utf-8")
            headers = {"content-type": "application/json"}
            token = str(os.getenv("KRISHNA_LR_GROUP_ADVISORY_TOKEN") or "").strip()
            if token:
                headers["x-lr-group-advisory-token"] = token
            req = request.Request(self.lr_group_url, data=data, headers=headers, method="POST")
            try:
                with request.urlopen(req, timeout=max(1, int(timeout))) as response:
                    response.read()
                    if 200 <= int(response.status) < 300:
                        delivered += 1
                    else:
                        remaining.append(row)
            except Exception as exc:
                row["lastRetryAt"] = time.time()
                row["error"] = str(exc)
                remaining.append(row)
        tmp = self.outbox_path.with_suffix(".tmp")
        if remaining:
            tmp.write_text(
                "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in remaining),
                encoding="utf-8",
            )
            tmp.replace(self.outbox_path)
        else:
            self.outbox_path.unlink(missing_ok=True)
            tmp.unlink(missing_ok=True)
        return {"attempted": attempted, "delivered": delivered, "remaining": len(remaining)}

    def cycle(self, *, company_id="lr-group", focus="", privacy="approved_cloud", queue_video=True, share=True):
        retry = self.retry_outbox() if share else {"attempted": 0, "delivered": 0, "remaining": 0, "skipped": True}
        plan = self.research_plan(company_id=company_id, focus=focus)
        video = self.queue_youtube_learning(focus=plan["focus"], limit=2) if queue_video else {"queued": 0, "jobs": []}
        result = self.run_research(company_id=company_id, focus=plan["focus"], privacy=privacy)
        packet = self.packet_from_run(result, company_id=company_id)
        delivery = self.deliver(packet) if share else {"delivered": False, "queued": False, "skipped": True}
        self.state["cycles"] = int(self.state.get("cycles") or 0) + 1
        self.state["last_cycle_at"] = time.time()
        self.state["focus_index"] = (int(self.state.get("focus_index") or 0) + 1) % len(GROWTH_FOCUS_ROTATION)
        self._save_state()
        return {"outbox_retry": retry, "plan": plan, "video_learning": video, "research": result, "packet": packet, "delivery": delivery}

    def status(self):
        return {
            "name": "Rishi Śukrācārya",
            "version": self.VERSION,
            "role": "KRISHNA business-growth research Rishi; external advisor to LR Group",
            "authority": "advisory-only",
            "lr_group_url": self.lr_group_url,
            "focus_rotation": list(GROWTH_FOCUS_ROTATION),
            "youtube_seed_count": len(YOUTUBE_SEEDS),
            "youtube_dynamic_discovery": True,
            "debate_team": list(DEBATE_TEAM),
            "state": dict(self.state),
            "outbox_path": str(self.outbox_path),
            "rules": [
                "YouTube is candidate evidence, not truth authority",
                "findings must preserve provenance, counter-evidence and uncertainty",
                "LR Group must independently debate findings before action",
                "no autonomous spend, contracting, outreach, trading or company operations",
            ],
        }


class SukracharyaScheduler:
    """Low-frequency background trigger. It waits one full interval before the first cycle."""

    def __init__(self, worker, interval_seconds=21600):
        self.worker = worker
        self.interval_seconds = max(3600, int(interval_seconds))
        self.stop_event = Event()
        self.thread = None
        self.lock = Lock()
        self.last_run_at = None
        self.last_result = None
        self.last_error = None

    def _loop(self):
        while not self.stop_event.wait(self.interval_seconds):
            try:
                result = self.worker()
                with self.lock:
                    self.last_run_at = time.time()
                    self.last_result = result
                    self.last_error = None
            except Exception as exc:
                with self.lock:
                    self.last_run_at = time.time()
                    self.last_error = f"{type(exc).__name__}: {exc}"

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = Thread(target=self._loop, name="krishna-sukracharya-growth", daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)

    def status(self):
        with self.lock:
            return {
                "running": bool(self.thread and self.thread.is_alive()),
                "interval_seconds": self.interval_seconds,
                "last_run_at": self.last_run_at,
                "last_error": self.last_error,
            }
