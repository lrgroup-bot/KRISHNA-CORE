from __future__ import annotations

"""KRISHNA Cognitive Brain: evidence-aware associative concept memory.

This is a software cognition layer, not a claim that KRISHNA has a biological
human brain or a measurable "brain percentage". It provides durable concept
nodes, typed relationships, associative activation, gap detection and
progressive-cognition status above BRAHMA/Rishi learning.

Classical/Vedic and modern-science tracks remain distinct. Cross-track links may
compare concepts, but this runtime refuses to store unsupported equivalence
claims between those tracks.
"""

from collections import deque
from pathlib import Path
from threading import RLock
import hashlib
import json
import os
import re
import time
import uuid

from .privacy_guardian.store import PrivacyEvidenceStore


class KrishnaCognitiveBrain:
    VERSION = "krishna-cognitive-brain-v2"
    TRACKS = {
        "general", "modern_science", "vedic_classical", "historical",
        "philosophical", "engineering", "operational",
    }
    EQUIVALENCE_RELATIONS = {
        "same_as", "equivalent_to", "identical_to", "scientifically_equivalent_to",
    }
    LEVELS = (
        ("C0", "Capture", "stores bounded concept observations"),
        ("C1", "Recall", "resolves concepts and aliases"),
        ("C2", "Association", "activates linked concepts"),
        ("C3", "Gap-aware", "identifies missing or weak knowledge"),
        ("C4", "Cross-domain", "connects separately sourced domains and tracks"),
        ("C5", "Metacognitive", "preserves provenance, uncertainty and contradictions"),
        ("C6", "Synthesis", "forms bounded analogies, curiosity questions and semantic consolidation candidates"),
        ("C7", "Hypothesis", "generates cross-domain testable hypotheses without treating them as facts"),
    )

    def __init__(self, state_root, council=None, rishi_learning=None, memory=None):
        self.root = Path(state_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "concept-graph.json"
        self.council = council
        self.rishi_learning = rishi_learning
        self.memory = memory
        self.lock = RLock()
        self.state = {
            "version": self.VERSION,
            "concepts": {},
            "alias_index": {},
            "edges": {},
            "activations": [],
            "analogies": [],
            "curiosity": [],
            "hypotheses": [],
            "consolidation_runs": [],
            "forgetting_runs": [],
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
                self.state.setdefault("concepts", {})
                self.state.setdefault("alias_index", {})
                self.state.setdefault("edges", {})
                self.state.setdefault("activations", [])
                self.state.setdefault("analogies", [])
                self.state.setdefault("curiosity", [])
                self.state.setdefault("hypotheses", [])
                self.state.setdefault("consolidation_runs", [])
                self.state.setdefault("forgetting_runs", [])
        except Exception as exc:
            self.load_error = f"{type(exc).__name__}: {exc}"
            if self.memory:
                self.memory.audit("cognitive_brain", "load_failed", self.load_error)

    def _healthy(self):
        if self.load_error:
            raise RuntimeError(
                "KRISHNA Cognitive Brain state is unreadable; refusing to overwrite it: "
                + self.load_error
            )

    def _save(self):
        self._healthy()
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    @staticmethod
    def _clean(value, limit=1000):
        safe = PrivacyEvidenceStore.sanitize(str(value or "").strip())
        return str(safe or "")[:limit]

    @classmethod
    def _norm(cls, value):
        text = cls._clean(value, 1000).lower()
        text = re.sub(r"[^a-z0-9\u0900-\u097f\u0b00-\u0b7f]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def _concept_id(cls, value):
        norm = cls._norm(value)
        if not norm:
            raise ValueError("concept name is required")
        return "CON-" + hashlib.sha256(norm.encode("utf-8")).hexdigest()[:20]

    @staticmethod
    def _clamp(value, default=0.0):
        try:
            return max(0.0, min(float(value), 1.0))
        except (TypeError, ValueError):
            return default

    @classmethod
    def _track(cls, value):
        track = str(value or "general").strip().lower()
        return track if track in cls.TRACKS else "general"

    def _index_alias(self, alias, concept_id):
        key = self._norm(alias)
        if not key:
            return
        ids = self.state["alias_index"].setdefault(key, [])
        if concept_id not in ids:
            ids.append(concept_id)
            ids[:] = ids[-20:]

    def learn_concept(
        self,
        name,
        *,
        aliases=None,
        track="general",
        confidence=0.0,
        maturity="L0",
        evidence_status="candidate",
        provenance=None,
        rishi_id=None,
    ):
        label = self._clean(name, 500)
        if not label:
            raise ValueError("concept name is required")
        cid = self._concept_id(label)
        aliases = [self._clean(x, 500) for x in (aliases or []) if self._clean(x, 500)]
        track = self._track(track)
        provenance = PrivacyEvidenceStore.sanitize(dict(provenance or {}))
        now = time.time()
        with self.lock:
            row = self.state["concepts"].get(cid)
            if not row:
                row = {
                    "concept_id": cid,
                    "name": label,
                    "aliases": [],
                    "tracks": [],
                    "confidence": 0.0,
                    "maturity": "L0",
                    "evidence_status": "candidate",
                    "rishis": [],
                    "provenance": [],
                    "created_at": now,
                    "updated_at": now,
                    "last_activated_at": None,
                    "activation_count": 0,
                    "dormant": False,
                }
                self.state["concepts"][cid] = row
            for alias in aliases:
                if alias.lower() != row["name"].lower() and alias not in row["aliases"]:
                    row["aliases"].append(alias)
            row["aliases"] = row["aliases"][-100:]
            if track not in row["tracks"]:
                row["tracks"].append(track)
            row["confidence"] = max(float(row.get("confidence") or 0.0), self._clamp(confidence))
            if str(maturity or "").strip():
                row["maturity"] = str(maturity).strip().upper()[:20]
            if str(evidence_status or "").strip():
                row["evidence_status"] = str(evidence_status).strip().lower()[:80]
            if rishi_id and str(rishi_id) not in row["rishis"]:
                row["rishis"].append(str(rishi_id))
            if provenance:
                fp = hashlib.sha256(
                    json.dumps(provenance, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
                ).hexdigest()
                if not any(x.get("fingerprint") == fp for x in row["provenance"]):
                    row["provenance"].append({"fingerprint": fp, "detail": provenance, "recorded_at": now})
                    row["provenance"] = row["provenance"][-100:]
            row["updated_at"] = now
            row["dormant"] = False
            self._index_alias(row["name"], cid)
            for alias in row["aliases"]:
                self._index_alias(alias, cid)
            self._save()
            return json.loads(json.dumps(row))

    def _get(self, concept):
        cid = str(concept or "")
        if cid in self.state["concepts"]:
            return self.state["concepts"][cid]
        resolved = self.resolve(concept)
        rid = resolved.get("concept_id")
        if not rid:
            raise KeyError(concept)
        return self.state["concepts"][rid]

    def link(
        self,
        source,
        target,
        *,
        relation="related_to",
        weight=0.7,
        track="general",
        source_track=None,
        target_track=None,
        evidence_status="candidate",
        provenance=None,
        rishi_id=None,
    ):
        relation = self._norm(relation).replace(" ", "_")[:120] or "related_to"
        source_row = self.learn_concept(
            source, track=source_track or track, provenance=provenance, rishi_id=rishi_id
        )
        target_row = self.learn_concept(
            target, track=target_track or track, provenance=provenance, rishi_id=rishi_id
        )
        source_tracks = set(source_row.get("tracks") or [])
        target_tracks = set(target_row.get("tracks") or [])
        cross_classical_modern = (
            ("modern_science" in source_tracks and "vedic_classical" in target_tracks)
            or ("vedic_classical" in source_tracks and "modern_science" in target_tracks)
        )
        if cross_classical_modern and relation in self.EQUIVALENCE_RELATIONS:
            raise ValueError(
                "modern-science and Vedic/classical concepts may be compared but not stored as equivalent"
            )
        edge_key = {
            "source": source_row["concept_id"],
            "target": target_row["concept_id"],
            "relation": relation,
        }
        edge_id = "EDGE-" + hashlib.sha256(
            json.dumps(edge_key, sort_keys=True).encode("utf-8")
        ).hexdigest()[:20]
        safe_provenance = PrivacyEvidenceStore.sanitize(dict(provenance or {}))
        now = time.time()
        with self.lock:
            row = self.state["edges"].get(edge_id) or {
                "edge_id": edge_id,
                **edge_key,
                "created_at": now,
            }
            row.update({
                "weight": self._clamp(weight, 0.7),
                "track": self._track(track),
                "evidence_status": str(evidence_status or "candidate").strip().lower()[:80],
                "rishi_id": str(rishi_id or "") or None,
                "provenance": safe_provenance,
                "cross_track_comparison": cross_classical_modern,
                "updated_at": now,
            })
            self.state["edges"][edge_id] = row
            self._save()
            return json.loads(json.dumps(row))

    def ingest_research(
        self,
        topic,
        *,
        related_concepts=None,
        relationships=None,
        aliases=None,
        track="general",
        confidence=0.0,
        maturity="L0",
        evidence_status="candidate",
        provenance=None,
        rishi_id=None,
    ):
        root = self.learn_concept(
            topic,
            aliases=aliases,
            track=track,
            confidence=confidence,
            maturity=maturity,
            evidence_status=evidence_status,
            provenance=provenance,
            rishi_id=rishi_id,
        )
        linked = []
        for item in list(related_concepts or [])[:200]:
            if isinstance(item, str):
                item = {"name": item}
            if not isinstance(item, dict):
                continue
            name = self._clean(item.get("name") or item.get("concept"), 500)
            if not name:
                continue
            self.learn_concept(
                name,
                aliases=item.get("aliases") or [],
                track=item.get("track") or track,
                confidence=item.get("confidence", confidence),
                maturity=item.get("maturity") or maturity,
                evidence_status=item.get("evidence_status") or evidence_status,
                provenance=item.get("provenance") or provenance,
                rishi_id=item.get("rishi_id") or rishi_id,
            )
            linked.append(self.link(
                topic,
                name,
                relation=item.get("relation") or "related_to",
                weight=item.get("weight", 0.7),
                track=item.get("track") or track,
                source_track=track,
                target_track=item.get("track") or track,
                evidence_status=item.get("evidence_status") or evidence_status,
                provenance=item.get("provenance") or provenance,
                rishi_id=item.get("rishi_id") or rishi_id,
            ))
        for item in list(relationships or [])[:500]:
            if not isinstance(item, dict):
                continue
            source = self._clean(item.get("source") or topic, 500)
            target = self._clean(item.get("target"), 500)
            if not source or not target:
                continue
            linked.append(self.link(
                source,
                target,
                relation=item.get("relation") or "related_to",
                weight=item.get("weight", 0.7),
                track=item.get("track") or track,
                source_track=item.get("source_track") or item.get("track") or track,
                target_track=item.get("target_track") or item.get("track") or track,
                evidence_status=item.get("evidence_status") or evidence_status,
                provenance=item.get("provenance") or provenance,
                rishi_id=item.get("rishi_id") or rishi_id,
            ))
        if self.memory:
            self.memory.audit(
                "cognitive_brain",
                "ingested",
                f"{root['concept_id']}:{root['name']}:links={len(linked)}",
            )
        return {
            "brain": self.VERSION,
            "root": root,
            "links": linked,
            "concept_count": len(self.state["concepts"]),
            "edge_count": len(self.state["edges"]),
        }

    def resolve(self, query):
        wanted = self._norm(query)
        if not wanted:
            return {"query": "", "concept_id": None, "score": 0.0, "match": "none"}
        with self.lock:
            exact = list(self.state["alias_index"].get(wanted) or [])
            concepts = json.loads(json.dumps(self.state["concepts"]))
        if exact:
            active_exact = [cid for cid in exact if not (concepts.get(cid) or {}).get("dormant")]
            if active_exact:
                return {"query": str(query), "concept_id": active_exact[0], "score": 1.0, "match": "exact"}
        wanted_terms = set(wanted.split())
        ranked = []
        for cid, row in concepts.items():
            if row.get("dormant"):
                continue
            labels = [row.get("name") or ""] + list(row.get("aliases") or [])
            best = 0.0
            for label in labels:
                norm = self._norm(label)
                terms = set(norm.split())
                if not norm:
                    continue
                overlap = len(wanted_terms & terms) / max(1, len(wanted_terms | terms))
                substring = 0.85 if (wanted in norm or norm in wanted) else 0.0
                best = max(best, overlap, substring)
            if best >= 0.34:
                ranked.append((best, cid))
        ranked.sort(key=lambda x: (-x[0], x[1]))
        if not ranked:
            return {"query": str(query), "concept_id": None, "score": 0.0, "match": "none"}
        return {
            "query": str(query),
            "concept_id": ranked[0][1],
            "score": round(ranked[0][0], 4),
            "match": "semantic_lexical",
        }

    def activate(self, query, *, depth=2, limit=40, decay=0.78):
        depth = max(0, min(int(depth), 6))
        limit = max(1, min(int(limit), 200))
        decay = self._clamp(decay, 0.78)
        resolved = self.resolve(query)
        seed = resolved.get("concept_id")
        if not seed:
            return {
                "brain": self.VERSION,
                "query": str(query),
                "resolved": resolved,
                "activated": [],
                "paths": {},
                "knowledge_gap": True,
                "gap_reason": "no stored concept or alias matched the query",
            }
        with self.lock:
            concepts = json.loads(json.dumps(self.state["concepts"]))
            edges = list(json.loads(json.dumps(self.state["edges"])).values())
        adjacency = {}
        for edge in edges:
            adjacency.setdefault(edge["source"], []).append((edge["target"], edge))
            adjacency.setdefault(edge["target"], []).append((edge["source"], edge))
        scores = {seed: 1.0}
        paths = {seed: [seed]}
        queue = deque([(seed, 0, 1.0)])
        while queue:
            current, level, current_score = queue.popleft()
            if level >= depth:
                continue
            for neighbor, edge in adjacency.get(current, []):
                score = current_score * decay * self._clamp(edge.get("weight"), 0.7)
                if score <= scores.get(neighbor, 0.0):
                    continue
                scores[neighbor] = score
                paths[neighbor] = paths[current] + [neighbor]
                queue.append((neighbor, level + 1, score))
        ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))[:limit]
        activated = []
        for cid, score in ranked:
            row = concepts[cid]
            activated.append({
                "concept_id": cid,
                "name": row.get("name"),
                "aliases": row.get("aliases") or [],
                "tracks": row.get("tracks") or [],
                "confidence": row.get("confidence", 0.0),
                "maturity": row.get("maturity"),
                "evidence_status": row.get("evidence_status"),
                "activation": round(score, 4),
                "distance": max(0, len(paths.get(cid, [])) - 1),
            })
        activation = {
            "activation_id": "ACT-" + uuid.uuid4().hex[:20],
            "query": self._clean(query, 1000),
            "seed": seed,
            "resolved": resolved,
            "activated": activated,
            "created_at": time.time(),
        }
        with self.lock:
            now = time.time()
            for cid in scores:
                row = self.state["concepts"].get(cid)
                if not row:
                    continue
                row["last_activated_at"] = now
                row["activation_count"] = int(row.get("activation_count") or 0) + 1
                row["dormant"] = False
            self.state["activations"].append(activation)
            self.state["activations"] = self.state["activations"][-1000:]
            self._save()
        return {
            "brain": self.VERSION,
            **activation,
            "paths": paths,
            "knowledge_gap": False,
            "policy": "association strength prioritizes retrieval; it is not evidence of truth",
        }


    @staticmethod
    def _jaccard(left, right):
        a, b = set(left or []), set(right or [])
        if not a and not b:
            return 0.0
        return len(a & b) / max(1, len(a | b))

    def _structural_signature(self, concept_id, edges, concepts):
        relations = []
        neighbor_tracks = []
        neighbors = set()
        for edge in edges:
            other = None
            if edge.get("source") == concept_id:
                other = edge.get("target")
            elif edge.get("target") == concept_id:
                other = edge.get("source")
            if not other:
                continue
            neighbors.add(other)
            relations.append(str(edge.get("relation") or "related_to"))
            neighbor_tracks.extend((concepts.get(other) or {}).get("tracks") or [])
        return {
            "relations": relations,
            "neighbor_tracks": neighbor_tracks,
            "degree": len(neighbors),
        }

    def form_analogies(self, concept, *, limit=12, min_score=0.30):
        """Find structural analogy candidates; similarity is never promoted as truth."""
        resolved = self.resolve(concept)
        seed = resolved.get("concept_id")
        if not seed:
            return {
                "brain": self.VERSION,
                "query": str(concept or ""),
                "analogies": [],
                "knowledge_gap": True,
                "policy": "no analogy is asserted when the source concept is unknown",
            }
        with self.lock:
            concepts = json.loads(json.dumps(self.state["concepts"]))
            edges = list(json.loads(json.dumps(self.state["edges"])).values())
        source = concepts[seed]
        source_sig = self._structural_signature(seed, edges, concepts)
        ranked = []
        for cid, row in concepts.items():
            if cid == seed or row.get("dormant"):
                continue
            sig = self._structural_signature(cid, edges, concepts)
            relation_overlap = self._jaccard(source_sig["relations"], sig["relations"])
            track_overlap = self._jaccard(source_sig["neighbor_tracks"], sig["neighbor_tracks"])
            max_degree = max(1, source_sig["degree"], sig["degree"])
            degree_similarity = 1.0 - (abs(source_sig["degree"] - sig["degree"]) / max_degree)
            score = 0.65 * relation_overlap + 0.20 * track_overlap + 0.15 * degree_similarity
            if relation_overlap <= 0 or score < float(min_score):
                continue
            cross_domain = not bool(set(source.get("tracks") or []) & set(row.get("tracks") or []))
            ranked.append({
                "analogy_id": "AN-" + uuid.uuid4().hex[:20],
                "source_concept_id": seed,
                "source": source.get("name"),
                "target_concept_id": cid,
                "target": row.get("name"),
                "score": round(score, 4),
                "shared_relations": sorted(set(source_sig["relations"]) & set(sig["relations"])),
                "shared_neighbor_tracks": sorted(set(source_sig["neighbor_tracks"]) & set(sig["neighbor_tracks"])),
                "cross_domain": cross_domain,
                "status": "candidate_analogy",
                "created_at": time.time(),
            })
        ranked.sort(key=lambda x: (-x["score"], x["target"].lower()))
        selected = ranked[: max(1, min(int(limit), 50))]
        with self.lock:
            self.state["analogies"].extend(selected)
            self.state["analogies"] = self.state["analogies"][-1000:]
            self._save()
        return {
            "brain": self.VERSION,
            "query": str(concept or ""),
            "source": source.get("name"),
            "analogies": selected,
            "knowledge_gap": False,
            "policy": "structural analogy suggests where to investigate; it is not evidence that two concepts are equivalent",
        }

    def curiosity_from_contradictions(self, contradictions, *, limit=20):
        """Turn unresolved contradictions into bounded research questions."""
        out = []
        for item in list(contradictions or [])[: max(1, min(int(limit), 100))]:
            if not isinstance(item, dict) or str(item.get("status") or "open") != "open":
                continue
            left = self._clean(item.get("claim_a_text") or item.get("claim_a") or "", 1200)
            right = self._clean(item.get("claim_b_text") or item.get("claim_b") or "", 1200)
            topic = self._clean(item.get("topic") or "contradictory evidence", 500)
            if not left or not right:
                continue
            question = self._clean(
                f"What independent evidence, boundary conditions or measurements distinguish '{left}' from '{right}' for {topic}?",
                2500,
            )
            out.append({
                "curiosity_id": "CQ-" + uuid.uuid4().hex[:20],
                "contradiction_id": str(item.get("contradiction_id") or "") or None,
                "topic": topic,
                "question": question,
                "priority": "high",
                "status": "open_research_question",
                "created_at": time.time(),
            })
        with self.lock:
            existing = {x.get("contradiction_id") for x in self.state["curiosity"] if x.get("contradiction_id")}
            fresh = [x for x in out if not x.get("contradiction_id") or x.get("contradiction_id") not in existing]
            self.state["curiosity"].extend(fresh)
            self.state["curiosity"] = self.state["curiosity"][-2000:]
            self._save()
        return {
            "brain": self.VERSION,
            "questions": out,
            "count": len(out),
            "policy": "contradictions create questions and tests; KRISHNA does not choose a winner without evidence",
        }

    def consolidate_episodes(self, episodes, *, min_occurrences=2, limit=50):
        """Convert repeated episodic observations into semantic *candidates* only."""
        threshold = max(2, min(int(min_occurrences), 20))
        groups = {}
        for item in list(episodes or [])[:2000]:
            if not isinstance(item, dict):
                continue
            topic = self._clean(item.get("topic") or "", 500)
            lesson = self._clean(item.get("lesson") or item.get("content") or "", 4000)
            if not topic or not lesson:
                continue
            key = hashlib.sha256((self._norm(topic) + "|" + self._norm(lesson)).encode("utf-8")).hexdigest()
            row = groups.setdefault(key, {
                "topic": topic,
                "lesson": lesson,
                "count": 0,
                "confidences": [],
                "evidence": [],
                "provenance": [],
                "fingerprints": [],
            })
            row["count"] += 1
            row["confidences"].append(self._clamp(item.get("confidence"), 0.0))
            row["evidence"].extend(list(item.get("evidence") or [])[:20])
            row["provenance"].append(PrivacyEvidenceStore.sanitize(dict(item.get("provenance") or {})))
            if item.get("fingerprint"):
                row["fingerprints"].append(str(item["fingerprint"]))
        candidates = []
        for key, row in groups.items():
            if row["count"] < threshold:
                continue
            avg = sum(row["confidences"]) / max(1, len(row["confidences"]))
            candidates.append({
                "candidate_id": "SC-" + key[:20],
                "topic": row["topic"],
                "lesson": row["lesson"],
                "occurrences": row["count"],
                "confidence": round(avg, 4),
                "memory_kind": "semantic",
                "source_memory_kind": "episodic",
                "evidence": row["evidence"][:50],
                "provenance": {
                    "consolidated_from": row["fingerprints"][-50:],
                    "episode_provenance": row["provenance"][-20:],
                },
                "status": "semantic_candidate",
                "requires_brahma_qc": True,
                "requires_gyan_approval": True,
            })
        candidates.sort(key=lambda x: (-x["occurrences"], -x["confidence"], x["topic"].lower()))
        run = {
            "consolidation_id": "CC-" + uuid.uuid4().hex[:20],
            "created_at": time.time(),
            "episodes_considered": sum(x["count"] for x in groups.values()),
            "semantic_candidates": candidates[: max(1, min(int(limit), 200))],
            "policy": "repetition creates a semantic candidate, never automatic trusted knowledge",
        }
        with self.lock:
            self.state["consolidation_runs"].append(run)
            self.state["consolidation_runs"] = self.state["consolidation_runs"][-500:]
            self._save()
        return run

    def controlled_forget(
        self,
        *,
        now=None,
        activation_ttl_days=30,
        candidate_ttl_days=180,
        confidence_floor=0.20,
        apply=False,
    ):
        """Bound memory growth without deleting evidence-backed knowledge.

        Old activation telemetry may be pruned. Low-value orphan candidates can be
        marked dormant, but verified/provenanced/connected concepts are retained.
        """
        now = float(now or time.time())
        activation_cutoff = now - max(1, int(activation_ttl_days)) * 86400.0
        concept_cutoff = now - max(1, int(candidate_ttl_days)) * 86400.0
        floor = self._clamp(confidence_floor, 0.20)
        with self.lock:
            edges = list(self.state["edges"].values())
            degree = {}
            for edge in edges:
                degree[edge.get("source")] = degree.get(edge.get("source"), 0) + 1
                degree[edge.get("target")] = degree.get(edge.get("target"), 0) + 1
            dormant = []
            for cid, row in self.state["concepts"].items():
                if row.get("dormant"):
                    continue
                eligible = (
                    float(row.get("updated_at") or row.get("created_at") or now) < concept_cutoff
                    and float(row.get("confidence") or 0.0) < floor
                    and str(row.get("evidence_status") or "candidate") not in {"verified", "supported", "provisional_supported"}
                    and not (row.get("provenance") or [])
                    and not (row.get("rishis") or [])
                    and int(degree.get(cid, 0)) == 0
                )
                if eligible:
                    dormant.append({
                        "concept_id": cid,
                        "name": row.get("name"),
                        "reason": "old low-confidence orphan candidate with no provenance or graph links",
                    })
            old_activations = [
                x for x in self.state["activations"]
                if float(x.get("created_at") or now) < activation_cutoff
            ]
            if apply:
                for item in dormant:
                    row = self.state["concepts"].get(item["concept_id"])
                    if row:
                        row["dormant"] = True
                        row["dormant_at"] = now
                self.state["activations"] = [
                    x for x in self.state["activations"]
                    if float(x.get("created_at") or now) >= activation_cutoff
                ]
            run = {
                "forgetting_id": "CF-" + uuid.uuid4().hex[:20],
                "created_at": now,
                "applied": bool(apply),
                "activation_traces_prunable": len(old_activations),
                "concepts_dormant_candidate": dormant[:500],
                "concepts_dormant_count": len(dormant),
                "policy": "never delete verified, provenanced or connected knowledge; forgetting means telemetry pruning and reversible dormancy",
            }
            self.state["forgetting_runs"].append(run)
            self.state["forgetting_runs"] = self.state["forgetting_runs"][-500:]
            self._save()
        return run

    def generate_hypotheses(self, query, *, depth=3, limit=8):
        """Generate cross-domain questions that must be tested before belief."""
        activation = self.activate(query, depth=depth, limit=40)
        nodes = list(activation.get("activated") or [])
        hypotheses = []
        for i, left in enumerate(nodes):
            lt = set(left.get("tracks") or [])
            for right in nodes[i + 1:]:
                rt = set(right.get("tracks") or [])
                if not lt or not rt or lt & rt:
                    continue
                classical_modern = (
                    ("vedic_classical" in lt and "modern_science" in rt)
                    or ("modern_science" in lt and "vedic_classical" in rt)
                )
                score = self._clamp(float(left.get("activation") or 0.0) * float(right.get("activation") or 0.0))
                if score < 0.08:
                    continue
                if classical_modern:
                    question = (
                        f"What similarities and differences between {left.get('name')} and {right.get('name')} "
                        "are supported by their independent source traditions, without assuming scientific equivalence?"
                    )
                    hypothesis_type = "cross_track_comparison"
                else:
                    question = (
                        f"Could a mechanism or structural pattern associated with {left.get('name')} provide a "
                        f"testable analogy for {right.get('name')}? What observation would falsify that idea?"
                    )
                    hypothesis_type = "cross_domain_transfer"
                hypotheses.append({
                    "hypothesis_id": "HY-" + uuid.uuid4().hex[:20],
                    "query": self._clean(query, 1000),
                    "left_concept_id": left.get("concept_id"),
                    "left": left.get("name"),
                    "right_concept_id": right.get("concept_id"),
                    "right": right.get("name"),
                    "score": round(score, 4),
                    "type": hypothesis_type,
                    "question": self._clean(question, 2500),
                    "status": "unverified_hypothesis",
                    "required_next_step": "independent evidence or experiment through Rishi/LAB BOT before promotion",
                    "created_at": time.time(),
                })
        hypotheses.sort(key=lambda x: (-x["score"], x["left"], x["right"]))
        selected = hypotheses[: max(1, min(int(limit), 30))]
        with self.lock:
            self.state["hypotheses"].extend(selected)
            self.state["hypotheses"] = self.state["hypotheses"][-2000:]
            self._save()
        return {
            "brain": self.VERSION,
            "query": str(query or ""),
            "hypotheses": selected,
            "count": len(selected),
            "policy": "hypotheses are questions for falsification, not learned facts or predictions",
        }

    def status(self):
        with self.lock:
            concepts = list(self.state["concepts"].values())
            edges = list(self.state["edges"].values())
            activations = list(self.state["activations"])
            analogies = list(self.state.get("analogies") or [])
            curiosity = list(self.state.get("curiosity") or [])
            hypotheses = list(self.state.get("hypotheses") or [])
            consolidations = list(self.state.get("consolidation_runs") or [])
            forgetting = list(self.state.get("forgetting_runs") or [])
        tracks = {}
        for row in concepts:
            for track in row.get("tracks") or []:
                tracks[track] = tracks.get(track, 0) + 1
        cross = len([x for x in edges if x.get("cross_track_comparison")])
        reached = "C0"
        if concepts:
            reached = "C1"
        if edges:
            reached = "C2"
        if activations:
            reached = "C3"
        if cross or len(tracks) >= 2:
            reached = "C4"
        if any((x.get("provenance") or []) for x in concepts):
            reached = "C5"
        if analogies or curiosity or consolidations or forgetting:
            reached = "C6"
        if hypotheses:
            reached = "C7"
        return {
            "name": "KRISHNA Cognitive Brain",
            "version": self.VERSION,
            "ready": self.load_error is None,
            "load_error": self.load_error,
            "concepts": len(concepts),
            "relationships": len(edges),
            "activations": len(activations),
            "tracks": tracks,
            "cross_track_comparisons": cross,
            "analogies": len(analogies),
            "curiosity_questions": len(curiosity),
            "hypotheses": len(hypotheses),
            "consolidation_runs": len(consolidations),
            "forgetting_runs": len(forgetting),
            "dormant_concepts": len([x for x in concepts if x.get("dormant")]),
            "progressive_cognition_level": reached,
            "levels": [
                {"code": code, "name": name, "meaning": meaning}
                for code, name, meaning in self.LEVELS
            ],
            "scientific_note": (
                "levels describe KRISHNA software capabilities; they are not percentages "
                "of a human brain and do not claim biological consciousness"
            ),
            "knowledge_policy": (
                "modern-science and Vedic/classical concepts remain independently sourced; "
                "cross-track comparison never implies scientific equivalence"
            ),
        }
