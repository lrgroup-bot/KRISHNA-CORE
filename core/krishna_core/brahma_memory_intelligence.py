from __future__ import annotations

"""Deterministic memory-intelligence primitives owned by BRAHMA BOT.

This module deliberately does not make model calls. It gives BRAHMA durable,
testable contracts for temporal knowledge, provenance, source independence,
consolidation, memory evaluation, Rishi collaboration graphs, teach-back
verification and freshness/decay. Higher-level Rishi/BRAHMAGYAN workers may
use these contracts, but they cannot bypass BRAHMA/Gyan quality gates.
"""

from pathlib import Path
from threading import RLock
from urllib.parse import urlparse, urlunparse
import hashlib
import json
import math
import os
import re
import time
import uuid


class BrahmaMemoryIntelligence:
    VERSION = "brahma-memory-intelligence-v2"
    DEFAULT_TTLS_DAYS = {
        "volatile": 7,
        "operational": 14,
        "software": 30,
        "research": 180,
        "stable": 365,
    }

    def __init__(self, state_root, council, rishi_learning, memory=None):
        self.root = Path(state_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "memory-intelligence.json"
        self.council = council
        self.rishi_learning = rishi_learning
        self.memory = memory
        self.lock = RLock()
        self.state = {
            "version": self.VERSION,
            "temporal_claims": {},
            "contradictions": [],
            "teach_back": {},
            "consolidations": [],
            "evaluations": [],
            "decay_reviews": [],
            "created_at": time.time(),
        }
        self.load_error = None
        self._load()

    def _load(self):
        if not self.path.is_file():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self.state.update(raw)
                for key, default in (
                    ("temporal_claims", {}),
                    ("contradictions", []),
                    ("teach_back", {}),
                    ("consolidations", []),
                    ("evaluations", []),
                    ("decay_reviews", []),
                ):
                    self.state.setdefault(key, default)
        except Exception as exc:
            self.load_error = f"{type(exc).__name__}: {exc}"
            if self.memory:
                self.memory.audit("brahma_memory_intelligence", "load_failed", self.load_error)

    def _healthy(self):
        if self.load_error:
            raise RuntimeError(
                "BRAHMA memory-intelligence state is unreadable; refusing to overwrite it: "
                + self.load_error
            )

    def _save(self):
        self._healthy()
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    @staticmethod
    def _clamp(value):
        try:
            return max(0.0, min(float(value), 1.0))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _terms(value):
        return {
            x
            for x in re.findall(r"[a-z0-9][a-z0-9_+.-]{2,}", str(value or "").lower())
            if len(x) > 2
        }

    @staticmethod
    def _canonical_json(value):
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)

    @classmethod
    def fingerprint(cls, value):
        return hashlib.sha256(cls._canonical_json(value).encode("utf-8")).hexdigest()

    @staticmethod
    def _canonical_url(value):
        raw = str(value or "").strip()
        if not raw.startswith(("http://", "https://")):
            return ""
        try:
            u = urlparse(raw)
            host = (u.hostname or "").lower()
            if not host:
                return ""
            port = u.port
            netloc = host
            if port and not ((u.scheme == "https" and port == 443) or (u.scheme == "http" and port == 80)):
                netloc = f"{host}:{port}"
            path = re.sub(r"/+", "/", u.path or "/")
            return urlunparse((u.scheme.lower(), netloc, path.rstrip("/") or "/", "", "", ""))
        except Exception:
            return ""

    def provenance_fingerprint(self, provenance=None, evidence=None):
        provenance = dict(provenance or {})
        compact = {
            k: provenance.get(k)
            for k in sorted(provenance)
            if k
            in {
                "source_ref",
                "source_url",
                "file",
                "mission_id",
                "claim_id",
                "observation_id",
                "run_id",
                "commit",
                "rishi_id",
                "rishi_lead",
                "researching_rishi",
                "verification_agent",
                "compiler",
                "captured_at",
                "valid_from",
                "valid_to",
            }
            and provenance.get(k) not in (None, "")
        }
        ev = []
        for item in list(evidence or []):
            if isinstance(item, dict):
                ev.append(
                    {
                        k: item.get(k)
                        for k in (
                            "source_ref",
                            "source_url",
                            "url",
                            "sha256",
                            "fingerprint",
                            "observation_id",
                            "copied_from",
                            "source_family",
                        )
                        if item.get(k) not in (None, "")
                    }
                )
            else:
                ev.append(str(item)[:500])
        return self.fingerprint({"provenance": compact, "evidence": ev})

    def _source_family(self, item):
        if not isinstance(item, dict):
            return "raw:" + self.fingerprint(str(item))[:20]
        explicit = str(item.get("source_family") or item.get("copied_from") or "").strip()
        if explicit:
            return "family:" + self.fingerprint(explicit.lower())[:20]
        source_hash = str(item.get("source_hash") or item.get("sha256") or item.get("fingerprint") or "").strip().lower()
        if source_hash:
            return "hash:" + source_hash[:32]
        url = self._canonical_url(item.get("source_url") or item.get("url"))
        if url:
            parsed = urlparse(url)
            path = (parsed.path or "/").lower()
            return "url:" + self.fingerprint({"host": parsed.hostname, "path": path})[:20]
        for key in ("source_ref", "observation_id", "file", "commit", "claim_id"):
            value = str(item.get(key) or "").strip()
            if value:
                return f"{key}:" + self.fingerprint(value)[:20]
        return "dict:" + self.fingerprint(item)[:20]

    def source_summary(self, evidence=None):
        rows = list(evidence or [])
        families = {}
        for item in rows:
            family = self._source_family(item)
            families.setdefault(family, []).append(item)
        total = len(rows)
        independent = len(families)
        duplicates = max(0, total - independent)
        return {
            "evidence_count": total,
            "independent_source_families": independent,
            "duplicate_or_related_sources": duplicates,
            "independence_ratio": round(independent / total, 4) if total else 0.0,
            "families": sorted(families),
            "policy": "related/copied sources count as one independent family",
        }

    def learning_value(
        self,
        *,
        confidence=0.0,
        novelty=0.0,
        quality=0.0,
        importance=0.5,
        future_reuse=0.5,
        knowledge_gap=0.5,
        compute_cost=0.2,
        network_cost=0.1,
        storage_cost=0.1,
    ):
        confidence = self._clamp(confidence)
        novelty = self._clamp(novelty)
        quality = self._clamp(quality)
        importance = self._clamp(importance)
        future_reuse = self._clamp(future_reuse)
        knowledge_gap = self._clamp(knowledge_gap)
        uncertainty = 1.0 - confidence
        compute_cost = self._clamp(compute_cost)
        network_cost = self._clamp(network_cost)
        storage_cost = self._clamp(storage_cost)
        benefit = (
            0.18 * uncertainty
            + 0.20 * novelty
            + 0.16 * quality
            + 0.16 * importance
            + 0.15 * future_reuse
            + 0.15 * knowledge_gap
        )
        cost = 0.50 * compute_cost + 0.30 * network_cost + 0.20 * storage_cost
        score = self._clamp(benefit * (1.0 - 0.45 * cost))
        return {
            "score": round(score, 4),
            "benefit": round(benefit, 4),
            "cost": round(cost, 4),
            "uncertainty": round(uncertainty, 4),
            "novelty": round(novelty, 4),
            "quality": round(quality, 4),
            "importance": round(importance, 4),
            "future_reuse": round(future_reuse, 4),
            "knowledge_gap": round(knowledge_gap, 4),
            "compute_cost": round(compute_cost, 4),
            "network_cost": round(network_cost, 4),
            "storage_cost": round(storage_cost, 4),
        }

    def temporal_record(
        self,
        *,
        topic,
        claim,
        provenance=None,
        evidence=None,
        rishi_id=None,
        evidence_status="candidate",
        valid_from=None,
        valid_to=None,
        observed_at=None,
        supersedes=None,
        volatility=None,
    ):
        topic = str(topic or "").strip()[:1000]
        claim = str(claim or "").strip()[:8000]
        if not topic or not claim:
            raise ValueError("topic and claim are required")
        now = time.time()
        provenance = dict(provenance or {})
        evidence = list(evidence or [])
        observed = float(observed_at or provenance.get("captured_at") or now)
        starts = float(valid_from or provenance.get("valid_from") or observed)
        ends = None if valid_to in (None, "") and provenance.get("valid_to") in (None, "") else float(valid_to or provenance.get("valid_to"))
        pfp = self.provenance_fingerprint(provenance, evidence)
        cid = "TK-" + self.fingerprint({"topic": topic.lower(), "claim": claim, "provenance": pfp})[:24]
        row = {
            "claim_id": cid,
            "topic": topic,
            "claim": claim,
            "rishi_id": str(rishi_id or provenance.get("rishi_id") or provenance.get("rishi_lead") or "") or None,
            "evidence_status": str(evidence_status or "candidate").lower(),
            "valid_from": starts,
            "valid_to": ends,
            "observed_at": observed,
            "learned_at": now,
            "provenance_fingerprint": pfp,
            "source_summary": self.source_summary(evidence),
            "supersedes": str(supersedes or "") or None,
            "superseded_by": None,
            "status": "current" if ends is None else "historical",
            "volatility": str(volatility or provenance.get("volatility") or self._infer_volatility(topic, claim)),
            "freshness": "current",
        }
        with self.lock:
            claims = self.state["temporal_claims"]
            if row["supersedes"] and row["supersedes"] in claims:
                older = claims[row["supersedes"]]
                older["valid_to"] = older.get("valid_to") or starts
                older["superseded_by"] = cid
                older["status"] = "superseded"
            existing = claims.get(cid)
            if existing:
                row["learned_at"] = existing.get("learned_at", now)
            claims[cid] = row
            self._save()
        return dict(row)

    def temporal_query(self, topic="", *, as_of=None, include_superseded=False, limit=100):
        when = float(as_of or time.time())
        wanted = self._terms(topic)
        with self.lock:
            rows = [dict(x) for x in self.state.get("temporal_claims", {}).values()]
        out = []
        for row in rows:
            if wanted and not (wanted & self._terms(row.get("topic", "") + " " + row.get("claim", ""))):
                continue
            start = float(row.get("valid_from") or 0)
            end = row.get("valid_to")
            if start > when:
                continue
            if end is not None and float(end) <= when and not include_superseded:
                continue
            if row.get("status") == "superseded" and not include_superseded and end is None:
                continue
            out.append(row)
        out.sort(key=lambda x: (float(x.get("valid_from") or 0), float(x.get("learned_at") or 0)), reverse=True)
        return {
            "agent": "BRAHMA BOT",
            "topic": str(topic or ""),
            "as_of": when,
            "claims": out[: max(1, min(int(limit), 500))],
            "count": len(out),
            "model": "bi-temporal: valid-time + learned-time",
        }

    def contradiction_record(self, claim_a, claim_b, reason="", evidence=None):
        a, b = str(claim_a or "").strip(), str(claim_b or "").strip()
        if not a or not b or a == b:
            raise ValueError("two distinct claim ids are required")
        with self.lock:
            claims = self.state.get("temporal_claims", {})
            if a not in claims or b not in claims:
                raise KeyError("temporal claim not found")
            row = {
                "contradiction_id": "CON-" + uuid.uuid4().hex[:20],
                "claim_a": a,
                "claim_b": b,
                "reason": str(reason or "")[:2000],
                "evidence": list(evidence or [])[:50],
                "status": "open",
                "created_at": time.time(),
                "resolved_at": None,
            }
            self.state["contradictions"].append(row)
            self.state["contradictions"] = self.state["contradictions"][-4000:]
            self._save()
        return dict(row)

    def contradiction_resolve(self, contradiction_id, resolution):
        cid = str(contradiction_id or "").strip()
        with self.lock:
            row = next((x for x in self.state.get("contradictions", []) if x.get("contradiction_id") == cid), None)
            if not row:
                raise KeyError(cid)
            row["status"] = "resolved"
            row["resolution"] = str(resolution or "")[:4000]
            row["resolved_at"] = time.time()
            self._save()
            return dict(row)

    def consolidate(self, decisions, *, max_items=250):
        rows = list(decisions or [])[-max(1, min(int(max_items), 1000)) :]
        selected = [x for x in rows if x.get("should_learn") and x.get("recorded_finding")]
        clusters = {}
        for row in selected:
            finding = row.get("recorded_finding") or {}
            topic = str(finding.get("topic") or row.get("topic") or "").strip()
            claim = str(finding.get("claim") or "").strip()
            if not topic or not claim:
                continue
            key = self.fingerprint({"topic": topic.lower(), "claim": re.sub(r"\s+", " ", claim.lower())})
            cluster = clusters.setdefault(
                key,
                {
                    "topic": topic,
                    "claim": claim,
                    "count": 0,
                    "rishis": set(),
                    "decision_ids": [],
                    "provenance": [],
                },
            )
            cluster["count"] += 1
            if row.get("lead_rishi"):
                cluster["rishis"].add(row["lead_rishi"])
            if row.get("decision_id"):
                cluster["decision_ids"].append(row["decision_id"])
            cluster["provenance"].append(dict(row.get("provenance") or {}))
        compact = []
        for key, row in clusters.items():
            compact.append(
                {
                    "cluster_id": "CL-" + key[:20],
                    "topic": row["topic"],
                    "claim": row["claim"],
                    "observations": row["count"],
                    "duplicate_count": max(0, row["count"] - 1),
                    "rishis": sorted(row["rishis"]),
                    "decision_ids": row["decision_ids"][-50:],
                    "provenance_fingerprints": sorted(
                        {self.provenance_fingerprint(x, []) for x in row["provenance"]}
                    ),
                }
            )
        compact.sort(key=lambda x: (-x["observations"], x["topic"].lower()))
        run = {
            "consolidation_id": "BC-" + uuid.uuid4().hex[:20],
            "created_at": time.time(),
            "input_decisions": len(rows),
            "selected_learning_decisions": len(selected),
            "clusters": compact[:250],
            "duplicates_collapsed": sum(x["duplicate_count"] for x in compact),
            "policy": "deterministic idle-time consolidation; no direct Gyan promotion",
        }
        with self.lock:
            self.state["consolidations"].append(run)
            self.state["consolidations"] = self.state["consolidations"][-500:]
            self._save()
        return run

    def evaluate(self, *, expected_ids=None, retrieved_ids=None):
        expected = {str(x) for x in (expected_ids or []) if str(x)}
        retrieved = [str(x) for x in (retrieved_ids or []) if str(x)]
        retrieved_set = set(retrieved)
        true_pos = len(expected & retrieved_set)
        precision = true_pos / len(retrieved_set) if retrieved_set else (1.0 if not expected else 0.0)
        recall = true_pos / len(expected) if expected else 1.0
        with self.lock:
            claims = list(self.state.get("temporal_claims", {}).values())
            contradictions = list(self.state.get("contradictions", []))
        claim_keys = [
            self.fingerprint(
                {
                    "topic": str(x.get("topic") or "").lower(),
                    "claim": re.sub(r"\s+", " ", str(x.get("claim") or "").lower()),
                }
            )
            for x in claims
        ]
        duplicate_count = len(claim_keys) - len(set(claim_keys))
        current = [x for x in claims if x.get("status") == "current"]
        stale = [x for x in current if x.get("freshness") in {"review_due", "stale"}]
        provenance_complete = [x for x in claims if x.get("provenance_fingerprint")]
        report = {
            "evaluation_id": "BE-" + uuid.uuid4().hex[:20],
            "created_at": time.time(),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round((2 * precision * recall / (precision + recall)) if precision + recall else 0.0, 4),
            "temporal_claims": len(claims),
            "duplicate_claims": duplicate_count,
            "duplicate_rate": round(duplicate_count / len(claims), 4) if claims else 0.0,
            "stale_current_claims": len(stale),
            "stale_rate": round(len(stale) / len(current), 4) if current else 0.0,
            "open_contradictions": len([x for x in contradictions if x.get("status") == "open"]),
            "provenance_completeness": round(len(provenance_complete) / len(claims), 4) if claims else 1.0,
            "metrics": [
                "retrieval_precision",
                "retrieval_recall",
                "temporal_freshness",
                "duplicate_rate",
                "contradiction_rate",
                "provenance_completeness",
            ],
        }
        with self.lock:
            self.state["evaluations"].append(report)
            self.state["evaluations"] = self.state["evaluations"][-1000:]
            self._save()
        return report

    def rishi_graph(self, topic, *, limit=8):
        topic = str(topic or "").strip()
        if not topic:
            raise ValueError("topic is required")
        team = self.council.specialist_team(topic, limit=max(3, min(int(limit), 8)))
        members = list(team.get("members") or [])
        nodes = []
        for item in members:
            nodes.append(
                {
                    "id": item.get("id"),
                    "name": item.get("display_name") or item.get("name") or item.get("id"),
                    "role": item.get("role"),
                    "domains": list(item.get("domains") or []),
                }
            )
        ids = [x["id"] for x in nodes if x.get("id")]
        lead = next((x for x in ids if x not in {"gautama", "veda-vyasa"}), ids[0] if ids else None)
        edges = []
        if lead:
            for rid in ids:
                if rid == lead:
                    continue
                relation = "epistemic_review" if rid == "gautama" else ("compile" if rid == "veda-vyasa" else "collaborate")
                edges.append({"from": lead, "to": rid, "relation": relation})
        for i, left in enumerate(nodes):
            dl = {str(x).lower() for x in left.get("domains") or []}
            for right in nodes[i + 1 :]:
                shared = sorted(dl & {str(x).lower() for x in right.get("domains") or []})
                if shared:
                    edges.append({"from": left["id"], "to": right["id"], "relation": "shared_domain", "shared": shared[:8]})
        return {
            "agent": "BRAHMA BOT",
            "topic": topic,
            "lead_rishi": lead,
            "nodes": nodes,
            "edges": edges,
            "policy": "BRAHMA forms the council; knowledge remains owned by the Rishis",
        }

    def teach_back_create(self, *, topic, claim, evidence=None, lead_rishi=None, reviewer_rishi=None):
        topic = str(topic or "").strip()
        claim = str(claim or "").strip()
        if not topic or not claim:
            raise ValueError("topic and claim are required")
        graph = self.rishi_graph(topic)
        lead = str(lead_rishi or graph.get("lead_rishi") or "").strip()
        candidates = [x.get("id") for x in graph.get("nodes") or [] if x.get("id") and x.get("id") != lead]
        reviewer = str(reviewer_rishi or next((x for x in candidates if x not in {"veda-vyasa"}), candidates[0] if candidates else "")).strip()
        if not reviewer or reviewer == lead:
            raise ValueError("teach-back requires an independent reviewer Rishi")
        cid = "TB-" + uuid.uuid4().hex[:20]
        expected_refs = sorted(
            {
                str((x or {}).get("source_ref") or (x or {}).get("observation_id") or (x or {}).get("claim_id") or "")
                for x in list(evidence or [])
                if isinstance(x, dict)
                and ((x or {}).get("source_ref") or (x or {}).get("observation_id") or (x or {}).get("claim_id"))
            }
        )
        stored = {
            "challenge_id": cid,
            "topic": topic,
            "claim": claim,
            "claim_terms": sorted(self._terms(claim)),
            "lead_rishi": lead,
            "reviewer_rishi": reviewer,
            "expected_evidence_refs": expected_refs,
            "status": "open",
            "created_at": time.time(),
        }
        with self.lock:
            self.state["teach_back"][cid] = stored
            self._save()
        return {
            "challenge_id": cid,
            "topic": topic,
            "lead_rishi": lead,
            "reviewer_rishi": reviewer,
            "prompt": "Independently reconstruct the best-supported conclusion for this topic from available evidence. Do not ask for or quote the original Rishi conclusion.",
            "original_claim_hidden": True,
        }

    def teach_back_submit(self, challenge_id, *, reviewer_rishi, answer, evidence_refs=None):
        cid = str(challenge_id or "").strip()
        with self.lock:
            challenge = self.state.get("teach_back", {}).get(cid)
            if not challenge:
                raise KeyError(cid)
            if challenge.get("status") != "open":
                raise ValueError("teach-back challenge is already closed")
            reviewer = str(reviewer_rishi or "").strip()
            if reviewer != challenge.get("reviewer_rishi") or reviewer == challenge.get("lead_rishi"):
                raise PermissionError("teach-back must be completed by the assigned independent Rishi")
            expected_terms = set(challenge.get("claim_terms") or [])
            answer_terms = self._terms(answer)
            term_recall = len(expected_terms & answer_terms) / len(expected_terms) if expected_terms else 1.0
            expected_refs = set(challenge.get("expected_evidence_refs") or [])
            supplied_refs = {str(x) for x in (evidence_refs or []) if str(x)}
            evidence_score = (
                len(expected_refs & supplied_refs) / len(expected_refs)
                if expected_refs
                else 1.0
            )
            score = 0.65 * term_recall + 0.35 * evidence_score
            passed = score >= 0.58 and (not expected_refs or evidence_score > 0)
            challenge["status"] = "passed" if passed else "failed"
            challenge["score"] = round(score, 4)
            challenge["term_recall"] = round(term_recall, 4)
            challenge["evidence_score"] = round(evidence_score, 4)
            challenge["answer_fingerprint"] = self.fingerprint(str(answer or ""))
            challenge["completed_at"] = time.time()
            self._save()
            return {
                "challenge_id": cid,
                "passed": passed,
                "score": challenge["score"],
                "term_recall": challenge["term_recall"],
                "evidence_score": challenge["evidence_score"],
                "reviewer_rishi": reviewer,
            }

    @classmethod
    def _infer_volatility(cls, topic, claim):
        text = (str(topic or "") + " " + str(claim or "")).lower()
        if any(x in text for x in ("price", "weather", "current status", "live", "today", "schedule", "availability")):
            return "volatile"
        if any(x in text for x in ("software", "api", "version", "dependency", "model", "library", "config")):
            return "software"
        if any(x in text for x in ("vehicle condition", "machine state", "fault", "incident", "runtime", "server")):
            return "operational"
        if any(x in text for x in ("study", "paper", "research", "clinical", "benchmark", "consensus")):
            return "research"
        return "stable"

    def decay_scan(self, *, now=None, ttl_days=None):
        now = float(now or time.time())
        ttls = dict(self.DEFAULT_TTLS_DAYS)
        ttls.update({str(k): max(1, int(v)) for k, v in dict(ttl_days or {}).items()})
        reviewed = []
        with self.lock:
            for row in self.state.get("temporal_claims", {}).values():
                if row.get("status") not in {"current", "historical"}:
                    continue
                klass = str(row.get("volatility") or "stable")
                ttl = int(ttls.get(klass, ttls["stable"]))
                age_days = max(0.0, (now - float(row.get("observed_at") or row.get("learned_at") or now)) / 86400.0)
                freshness = "current"
                if age_days >= ttl * 2:
                    freshness = "stale"
                elif age_days >= ttl:
                    freshness = "review_due"
                row["freshness"] = freshness
                row["freshness_checked_at"] = now
                row["ttl_days"] = ttl
                if freshness != "current":
                    reviewed.append(
                        {
                            "claim_id": row.get("claim_id"),
                            "topic": row.get("topic"),
                            "freshness": freshness,
                            "age_days": round(age_days, 2),
                            "ttl_days": ttl,
                        }
                    )
            run = {
                "decay_id": "BD-" + uuid.uuid4().hex[:20],
                "created_at": now,
                "review_due": len([x for x in reviewed if x["freshness"] == "review_due"]),
                "stale": len([x for x in reviewed if x["freshness"] == "stale"]),
                "items": reviewed[:500],
                "policy": "knowledge is never silently deleted; stale items require re-verification",
            }
            self.state["decay_reviews"].append(run)
            self.state["decay_reviews"] = self.state["decay_reviews"][-1000:]
            self._save()
        return run

    def status(self):
        with self.lock:
            claims = list(self.state.get("temporal_claims", {}).values())
            contradictions = list(self.state.get("contradictions", []))
            teach = list(self.state.get("teach_back", {}).values())
            consolidations = list(self.state.get("consolidations", []))
            evaluations = list(self.state.get("evaluations", []))
        return {
            "component": "BRAHMA Memory Intelligence",
            "version": self.VERSION,
            "temporal_claims": len(claims),
            "open_contradictions": len([x for x in contradictions if x.get("status") == "open"]),
            "teach_back_open": len([x for x in teach if x.get("status") == "open"]),
            "teach_back_passed": len([x for x in teach if x.get("status") == "passed"]),
            "consolidations": len(consolidations),
            "evaluations": len(evaluations),
            "features": [
                "bi_temporal_claims",
                "source_family_independence",
                "provenance_fingerprints",
                "learning_value_budget",
                "idle_consolidation",
                "memory_evaluation",
                "contradiction_graph",
                "rishi_knowledge_graph",
                "teach_back_verification",
                "freshness_decay",
            ],
            "load_error": self.load_error,
            "ready": self.load_error is None,
        }


class BrahmaConsolidationScheduler:
    """Low-frequency scheduler for deterministic BRAHMA housekeeping only.

    The supplied tick owns resource/idle policy. This class only supplies a
    bounded daemon lifecycle, observability, and a manual run_once contract.
    It intentionally performs no model call or deep Rishi research itself.
    """

    def __init__(self, tick, interval_seconds=1800):
        self.tick = tick
        self.interval_seconds = max(300, int(interval_seconds))
        self._stop = threading.Event()
        self._thread = None
        self.run_count = 0
        self.skip_count = 0
        self.last_result = None
        self.last_error = None
        self.last_run_at = None

    def run_once(self):
        try:
            result = self.tick()
            self.last_result = result
            self.last_run_at = time.time()
            self.last_error = None
            if isinstance(result, dict) and str(result.get("status") or "").startswith("skipped"):
                self.skip_count += 1
            else:
                self.run_count += 1
            return result
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.last_run_at = time.time()
            return {"status": "error", "error": self.last_error}

    def start(self):
        if self._thread and self._thread.is_alive():
            return self.status()
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="brahma-memory-consolidation", daemon=True
        )
        self._thread.start()
        return self.status()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        return self.status()

    def _loop(self):
        while not self._stop.wait(self.interval_seconds):
            self.run_once()

    def status(self):
        return {
            "running": bool(self._thread and self._thread.is_alive()),
            "interval_seconds": self.interval_seconds,
            "run_count": self.run_count,
            "skip_count": self.skip_count,
            "last_run_at": self.last_run_at,
            "last_result": self.last_result,
            "last_error": self.last_error,
            "policy": "deterministic consolidation/decay only; deep Rishi research is not run by this scheduler",
        }
