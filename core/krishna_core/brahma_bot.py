from __future__ import annotations

"""BRAHMA BOT: KRISHNA's learning governor and Gyan-Bhandar QC head.

BRAHMA does not replace the Rishi Council, Gyan-Bhandar, KRISHNA, or Sudarshan.
It decides what is worth learning, routes the learning to the appropriate Rishis,
retrieves relevant Rishi knowledge on demand, and quality-gates candidate knowledge
before it may enter Gyan-Bhandar's normal approval pipeline.
"""

from pathlib import Path
from threading import RLock
import json
import os
import re
import time
import uuid


class BrahmaBot:
    VERSION = "brahma-learning-governor-v2"
    ALLOWED_SOURCES = {"mobile", "pc", "system", "agent", "job", "mcp", "a2a"}
    MATURITY_RANK = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5}
    VERIFIED_EVIDENCE = {"verified", "replicated", "strongly_supported"}
    CANDIDATE_EVIDENCE = VERIFIED_EVIDENCE | {
        "candidate", "supported", "provisional_supported", "qualified", "contested"
    }

    def __init__(self, state_root, council, rishi_learning, gyan_bhandar, memory=None):
        self.root = Path(state_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "brahma-learning.json"
        self.council = council
        self.rishi_learning = rishi_learning
        self.gyan_bhandar = gyan_bhandar
        self.memory = memory
        self.lock = RLock()
        self.state = {
            "version": self.VERSION,
            "decisions": [],
            "qc": [],
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
                self.state.setdefault("decisions", [])
                self.state.setdefault("qc", [])
        except Exception as exc:
            self.load_error = f"{type(exc).__name__}: {exc}"
            if self.memory:
                self.memory.audit("brahma_bot", "load_failed", self.load_error)

    def _healthy(self):
        if self.load_error:
            raise RuntimeError("BRAHMA BOT state is unreadable; refusing to overwrite it: " + self.load_error)

    def _save(self):
        self._healthy()
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    @staticmethod
    def _text(value, limit=4000):
        return str(value or "").strip()[:limit]

    @staticmethod
    def _terms(value):
        return {
            x for x in re.findall(r"[a-z0-9][a-z0-9_+.-]{2,}", str(value or "").lower())
            if len(x) > 2
        }

    @staticmethod
    def _clamp(value):
        try:
            return max(0.0, min(float(value), 1.0))
        except (TypeError, ValueError):
            return 0.0

    def _source_policy(self, source, modality):
        source = str(source or "").strip().lower()
        modality = str(modality or "text").strip().lower()
        if source == "mobile":
            return {
                "source": source,
                "capture_role": "compact observation/evidence acquisition",
                "deep_research_location": "pc",
                "default_memory_kind": "evidence" if modality in {"image", "audio", "video", "sensor"} else "episodic",
                "raw_streaming": False,
                "rule": "mobile captures bounded high-value evidence; Rishis learn/research on the PC side",
            }
        if source == "pc":
            return {
                "source": source,
                "capture_role": "documents/code/research/analysis",
                "deep_research_location": "pc",
                "default_memory_kind": "semantic",
                "raw_streaming": False,
                "rule": "PC may run deep Rishi research, cross-checking, compilation and verification",
            }
        return {
            "source": source,
            "capture_role": "runtime/event evidence",
            "deep_research_location": "pc",
            "default_memory_kind": "episodic",
            "raw_streaming": False,
            "rule": "system/agent events become scoped candidate learning only when informative",
        }

    def _active_learning_score(self, confidence=0.0, novelty=0.0, quality=0.0, importance=0.5,
                               future_reuse=0.5, knowledge_gap=0.5,
                               compute_cost=0.2, network_cost=0.1, storage_cost=0.1):
        """Cost-aware learning value used before starting new Rishi work."""
        return self.memory_intelligence.learning_value(
            confidence=confidence,
            novelty=novelty,
            quality=quality,
            importance=importance,
            future_reuse=future_reuse,
            knowledge_gap=knowledge_gap,
            compute_cost=compute_cost,
            network_cost=network_cost,
            storage_cost=storage_cost,
        )

    def _team(self, topic, content="", limit=6):
        team = self.council.specialist_team(
            (self._text(topic, 1000) + " " + self._text(content, 3000)).strip(),
            limit=max(3, min(int(limit), 8)),
        )
        members = list(team.get("members") or [])
        lead = next((x for x in members if x.get("id") not in {"gautama", "veda-vyasa"}), None)
        if not lead:
            lead = next((x for x in members if x.get("id") == "bharadvaja"), None)
        if not lead and members:
            lead = members[0]
        reviewer_ids = [x.get("id") for x in members if x.get("id") in {"gautama", "veda-vyasa"}]
        for rid in ("gautama", "veda-vyasa"):
            if rid not in reviewer_ids:
                reviewer_ids.append(rid)
        return team, lead, reviewer_ids

    def retrieve(self, topic, *, limit_per_rishi=8, team_limit=6):
        topic = self._text(topic, 2000)
        if not topic:
            raise ValueError("topic is required")
        team, lead, reviewers = self._team(topic, limit=team_limit)
        packets = []
        findings = []
        for member in team.get("members") or []:
            rid = member.get("id")
            if not rid:
                continue
            packet = self.rishi_learning.knowledge_packet(rid, topic, limit_per_rishi)
            packets.append(packet)
            for finding in packet.get("matching_findings") or []:
                findings.append({
                    **finding,
                    "rishi_id": rid,
                    "rishi_name": packet.get("display_name"),
                })
        findings.sort(
            key=lambda x: (
                -float(x.get("confidence") or 0.0),
                -float(x.get("learned_at") or 0.0),
            )
        )
        return {
            "agent": "BRAHMA BOT",
            "topic": topic,
            "lead_rishi": (lead or {}).get("id"),
            "reviewers": reviewers,
            "rishi_packets": packets,
            "findings": findings[:50],
            "policy": "required information is retrieved from the Rishi learning ledgers before new research is requested",
        }

    def plan_learning(self, *, source, topic, content="", modality="text", evidence=None,
                      confidence=0.0, novelty=0.0, quality=0.0, importance=0.5,
                      force=False):
        source = str(source or "").strip().lower()
        if source not in self.ALLOWED_SOURCES:
            raise ValueError("unsupported BRAHMA learning source")
        topic = self._text(topic, 1000)
        content = self._text(content, 4000)
        if not topic and not content:
            raise ValueError("topic or content is required")
        if not topic:
            topic = content[:240]

        evidence = list(evidence or [])
        policy = self._source_policy(source, modality)
        team, lead, reviewers = self._team(topic, content)

        existing = self.retrieve(topic, limit_per_rishi=5, team_limit=6)
        strong_existing = [
            x for x in existing.get("findings") or []
            if float(x.get("confidence") or 0.0) >= 0.80
            and not bool(x.get("unresolved"))
        ]
        knowledge_gap = 1.0 if not strong_existing else max(0.10, 1.0 - min(len(strong_existing), 5) / 5.0)
        future_reuse = max(self._clamp(importance), 0.55 if evidence else 0.25)
        compute_cost = 0.10 if source == "pc" else (0.18 if source == "mobile" else 0.14)
        network_cost = 0.25 if source == "mobile" else 0.05
        storage_cost = 0.12 if str(modality or "text").lower() in {"image", "audio", "video", "sensor"} else 0.04
        active = self._active_learning_score(
            confidence, novelty, quality, importance,
            future_reuse=future_reuse,
            knowledge_gap=knowledge_gap,
            compute_cost=compute_cost,
            network_cost=network_cost,
            storage_cost=storage_cost,
        )
        diagnostic_terms = {
            "fault", "diagnos", "broken", "failure", "error", "circuit", "vehicle",
            "machine", "medical", "safety", "hazard", "research", "unknown"
        }
        important_text = (topic + " " + content).lower()
        mission_relevant = any(x in important_text for x in diagnostic_terms)
        threshold = 0.30 if source == "mobile" else 0.25
        should_learn = bool(force or evidence or mission_relevant or active["score"] >= threshold)
        if strong_existing and active["novelty"] < 0.10 and not evidence and not force:
            should_learn = False

        if not should_learn:
            next_action = "reuse_rishi_knowledge_or_discard_low_value_observation"
        elif source == "mobile":
            next_action = "retain_bounded_evidence_then_route_rishi_learning_to_pc"
        else:
            next_action = "route_to_rishi_research_and_cross_check"

        return {
            "agent": "BRAHMA BOT",
            "version": self.VERSION,
            "source": source,
            "modality": str(modality or "text"),
            "topic": topic,
            "source_policy": policy,
            "active_learning": active,
            "should_learn": should_learn,
            "lead_rishi": (lead or {}).get("id"),
            "team": [x.get("id") for x in team.get("members") or [] if x.get("id")],
            "reviewers": reviewers,
            "existing_high_confidence_findings": len(strong_existing),
            "evidence_count": len(evidence),
            "next_action": next_action,
        }

    def intake(self, *, source, topic, content="", modality="text", evidence=None,
               provenance=None, confidence=0.0, novelty=0.0, quality=0.0,
               importance=0.5, evidence_status="candidate", force=False):
        evidence = list(evidence or [])
        provenance = dict(provenance or {})
        provenance.setdefault(
            "brahma_provenance_fingerprint",
            self.memory_intelligence.provenance_fingerprint(provenance, evidence),
        )
        plan = self.plan_learning(
            source=source, topic=topic, content=content, modality=modality,
            evidence=evidence, confidence=confidence, novelty=novelty,
            quality=quality, importance=importance, force=force,
        )
        decision = {
            "decision_id": str(uuid.uuid4()),
            "created_at": time.time(),
            **plan,
            "provenance": provenance,
            "recorded_finding": None,
            "temporal_claim": None,
        }

        if plan["should_learn"]:
            lead = plan.get("lead_rishi") or "bharadvaja"
            claim = self._text(content or topic, 4000)
            status = str(evidence_status or "candidate").strip().lower()
            if status not in self.CANDIDATE_EVIDENCE:
                status = "candidate"
            finding = self.rishi_learning.record_finding(
                lead,
                plan["topic"],
                claim,
                track=f"brahma:{plan['source']}:{plan['modality']}",
                maturity="L0",
                evidence_status=status,
                confidence=self._clamp(confidence),
                source_count=len(evidence),
                unresolved=(status == "contested"),
                role="brahma_intake",
            )
            decision["recorded_finding"] = finding
            decision["temporal_claim"] = self.memory_intelligence.temporal_record(
                topic=plan["topic"],
                claim=claim,
                provenance={
                    **provenance,
                    "rishi_finding_id": finding.get("finding_id"),
                    "rishi_lead": lead,
                },
                evidence=evidence,
                rishi_id=lead,
                evidence_status=status,
                observed_at=provenance.get("captured_at"),
                valid_from=provenance.get("valid_from"),
                valid_to=provenance.get("valid_to"),
                supersedes=provenance.get("supersedes_temporal_claim"),
                volatility=provenance.get("volatility"),
            )
            if plan["active_learning"]["uncertainty"] >= 0.35:
                self.rishi_learning.add_open_question(
                    lead,
                    plan["topic"],
                    "BRAHMA QC: verify/cross-check this candidate learning before Gyan promotion.",
                )

        with self.lock:
            self.state["decisions"].append(decision)
            self.state["decisions"] = self.state["decisions"][-2000:]
            self._save()

        if self.memory:
            self.memory.audit(
                "brahma_learning",
                "routed" if plan["should_learn"] else "skipped",
                f"{plan['source']}:{plan['topic']}:{plan.get('lead_rishi')}:{plan['active_learning']['score']}",
            )
        return decision

    def qc_for_gyan(self, *, project, topic, lesson, evidence=None, provenance=None,
                    confidence=0.0, maturity="L0", evidence_status="candidate",
                    unresolved_contradictions=0, memory_kind="semantic",
                    source="brahma", supersedes=None):
        project = self._text(project or "KRISHNA", 200)
        topic = self._text(topic, 1000)
        lesson = self._text(lesson, 8000)
        evidence = list(evidence or [])
        provenance = dict(provenance or {})
        confidence = self._clamp(confidence)
        maturity = str(maturity or "L0").upper()
        evidence_status = str(evidence_status or "candidate").strip().lower()
        unresolved = max(0, int(unresolved_contradictions or 0))

        if not topic or not lesson:
            raise ValueError("topic and lesson are required")

        team_context = self.retrieve(topic, limit_per_rishi=6, team_limit=6)
        provenance_ok = bool(
            provenance
            and any(provenance.get(k) for k in (
                "source_ref", "source_url", "file", "mission_id", "claim_id",
                "observation_id", "run_id", "commit"
            ))
        )
        evidence_ok = len(evidence) > 0
        source_summary = self.memory_intelligence.source_summary(evidence)
        provenance_fingerprint = self.memory_intelligence.provenance_fingerprint(provenance, evidence)
        confidence_ok = confidence >= 0.65
        maturity_ok = self.MATURITY_RANK.get(maturity, -1) >= self.MATURITY_RANK["L3"]
        contradiction_ok = unresolved == 0 and evidence_status not in {"rejected", "contradicted", "unknown"}
        status_ok = evidence_status in self.CANDIDATE_EVIDENCE
        rishi_origin_ok = bool(any(provenance.get(k) for k in (
            "rishi_finding_id", "researching_rishi", "rishi_id", "rishi_lead",
            "brahmagyan_claim_id", "mission_id",
        )))
        candidate_pass = all((
            provenance_ok, evidence_ok, confidence_ok, maturity_ok,
            contradiction_ok, status_ok, rishi_origin_ok,
        ))

        knowledge_kind = str(memory_kind or "semantic").strip().lower()
        review_compile_ok = (
            knowledge_kind not in {"semantic", "skill", "graph"}
            or (
                str(provenance.get("verification_agent") or "").strip().lower() == "gautama"
                and str(provenance.get("compiler") or "").strip().lower() == "veda-vyasa"
            )
        )
        verified = bool(
            candidate_pass
            and self.MATURITY_RANK.get(maturity, -1) >= self.MATURITY_RANK["L4"]
            and evidence_status in self.VERIFIED_EVIDENCE
            and confidence >= 0.80
            and review_compile_ok
        )

        reasons = []
        if not provenance_ok:
            reasons.append("traceable provenance is required")
        if not evidence_ok:
            reasons.append("at least one evidence reference is required")
        if not confidence_ok:
            reasons.append("confidence below BRAHMA candidate threshold 0.65")
        if not maturity_ok:
            reasons.append("maturity below L3")
        if unresolved:
            reasons.append("unresolved contradictions remain")
        if not status_ok or evidence_status in {"rejected", "contradicted", "unknown"}:
            reasons.append("evidence status is not admissible")
        if not rishi_origin_ok:
            reasons.append("knowledge must originate from a Rishi learning/research path")
        if candidate_pass and not review_compile_ok and knowledge_kind in {"semantic", "skill", "graph"}:
            reasons.append("Gautama review + Veda Vyasa compilation are required before verified knowledge status")

        qc_id = str(uuid.uuid4())
        qc = {
            "qc_id": qc_id,
            "agent": "BRAHMA BOT",
            "project": project,
            "topic": topic,
            "candidate_passed": candidate_pass,
            "verified_for_gyan": verified,
            "confidence": confidence,
            "maturity": maturity,
            "evidence_status": evidence_status,
            "evidence_count": len(evidence),
            "source_independence": source_summary,
            "provenance_fingerprint": provenance_fingerprint,
            "provenance_ok": provenance_ok,
            "rishi_origin_ok": rishi_origin_ok,
            "review_compile_ok": review_compile_ok,
            "unresolved_contradictions": unresolved,
            "reasons": reasons,
            "rishi_context": {
                "lead_rishi": team_context.get("lead_rishi"),
                "reviewers": team_context.get("reviewers"),
                "supporting_findings": len(team_context.get("findings") or []),
            },
            "created_at": time.time(),
            "proposal": None,
        }

        if candidate_pass:
            enriched_provenance = {
                **provenance,
                "brahma_qc_id": qc_id,
                "brahma_qc_version": self.VERSION,
                "rishi_lead": team_context.get("lead_rishi"),
                "rishi_reviewers": team_context.get("reviewers"),
                "maturity": maturity,
                "evidence_status": evidence_status,
                "provenance_fingerprint": provenance_fingerprint,
                "source_independence": source_summary,
            }
            qc["proposal"] = self.gyan_bhandar.propose(
                project,
                topic,
                lesson,
                evidence,
                confidence,
                source,
                verified,
                memory_kind,
                enriched_provenance,
                supersedes,
            )

        with self.lock:
            self.state["qc"].append(qc)
            self.state["qc"] = self.state["qc"][-2000:]
            self._save()

        if self.memory:
            self.memory.audit(
                "brahma_gyan_qc",
                "proposal_created" if candidate_pass else "blocked",
                f"{project}:{topic}:{qc_id}:{','.join(reasons)[:500]}",
            )
        return qc

    def route_knowledge(self, *, source, project, topic, lesson, evidence=None, provenance=None,
                        confidence=0.0, maturity="L0", evidence_status="candidate",
                        memory_kind="semantic", modality="text", novelty=0.5, quality=0.7,
                        importance=0.7, unresolved_contradictions=0, supersedes=None):
        """Canonical production path for candidate knowledge.

        Every knowledge candidate is first assigned to a Rishi ledger. Only mature
        candidates then proceed to BRAHMA QC and the existing Gyan approval queue.
        """
        source = str(source or "system").strip().lower()
        if source not in self.ALLOWED_SOURCES:
            source = "agent"
        evidence = list(evidence or [])
        provenance = dict(provenance or {})
        intake = self.intake(
            source=source, topic=topic, content=lesson, modality=modality,
            evidence=evidence, provenance=provenance, confidence=confidence,
            novelty=novelty, quality=quality, importance=importance,
            evidence_status=evidence_status, force=True,
        )
        finding = intake.get("recorded_finding") or {}
        routed_provenance = {
            **provenance,
            "rishi_finding_id": finding.get("finding_id"),
            "rishi_lead": intake.get("lead_rishi"),
            "brahma_intake_decision_id": intake.get("decision_id"),
        }
        level = str(maturity or "L0").upper()
        if self.MATURITY_RANK.get(level, -1) < self.MATURITY_RANK["L3"]:
            return {
                "agent": "BRAHMA BOT",
                "routed_to_rishi": True,
                "rishi_intake": intake,
                "qc": None,
                "proposal": None,
                "requires_more_learning": True,
                "next_action": "Rishi research/cross-check must mature this candidate to L3+ before Gyan proposal",
            }
        qc = self.qc_for_gyan(
            project=project, topic=topic, lesson=lesson, evidence=evidence,
            provenance=routed_provenance, confidence=confidence, maturity=level,
            evidence_status=evidence_status, unresolved_contradictions=unresolved_contradictions,
            memory_kind=memory_kind, source="brahma:"+source, supersedes=supersedes,
        )
        return {
            "agent": "BRAHMA BOT",
            "routed_to_rishi": True,
            "rishi_intake": intake,
            "qc": qc,
            "proposal": qc.get("proposal"),
            "requires_more_learning": not bool(qc.get("proposal")),
        }

    def temporal_query(self, topic="", *, as_of=None, include_superseded=False, limit=100):
        return self.memory_intelligence.temporal_query(
            topic, as_of=as_of, include_superseded=include_superseded, limit=limit
        )

    def record_contradiction(self, claim_a, claim_b, reason="", evidence=None):
        return self.memory_intelligence.contradiction_record(
            claim_a, claim_b, reason=reason, evidence=evidence
        )

    def resolve_contradiction(self, contradiction_id, resolution):
        return self.memory_intelligence.contradiction_resolve(contradiction_id, resolution)

    def consolidate(self, max_items=250):
        with self.lock:
            decisions = list(self.state.get("decisions") or [])
        out = self.memory_intelligence.consolidate(decisions, max_items=max_items)
        if self.memory:
            self.memory.audit(
                "brahma_consolidation",
                "completed",
                f"{out['consolidation_id']}:{out['selected_learning_decisions']}:{out['duplicates_collapsed']}",
            )
        return out

    def memory_evaluate(self, expected_ids=None, retrieved_ids=None):
        return self.memory_intelligence.evaluate(
            expected_ids=expected_ids or [], retrieved_ids=retrieved_ids or []
        )

    def rishi_graph(self, topic, limit=8):
        return self.memory_intelligence.rishi_graph(topic, limit=limit)

    def teach_back_create(self, *, topic, claim, evidence=None, lead_rishi=None, reviewer_rishi=None):
        return self.memory_intelligence.teach_back_create(
            topic=topic,
            claim=claim,
            evidence=evidence or [],
            lead_rishi=lead_rishi,
            reviewer_rishi=reviewer_rishi,
        )

    def teach_back_submit(self, challenge_id, *, reviewer_rishi, answer, evidence_refs=None):
        return self.memory_intelligence.teach_back_submit(
            challenge_id,
            reviewer_rishi=reviewer_rishi,
            answer=answer,
            evidence_refs=evidence_refs or [],
        )

    def decay_scan(self, *, now=None, ttl_days=None):
        return self.memory_intelligence.decay_scan(now=now, ttl_days=ttl_days or {})

    def status(self):
        with self.lock:
            decisions = list(self.state.get("decisions") or [])
            qc = list(self.state.get("qc") or [])
        return {
            "agent": "BRAHMA BOT",
            "version": self.VERSION,
            "role": "learning governor + Gyan-Bhandar QC head",
            "learning_authority": "routes learning to Rishis; does not replace Rishi scholarship",
            "gyan_authority": "QC only; accepted items enter Gyan-Bhandar's normal proposal/approval pipeline",
            "sources": sorted(self.ALLOWED_SOURCES),
            "decisions": len(decisions),
            "qc_reviews": len(qc),
            "recent_decisions": decisions[-10:],
            "recent_qc": qc[-10:],
            "memory_intelligence": self.memory_intelligence.status(),
            "load_error": self.load_error,
            "ready": self.load_error is None,
        }
