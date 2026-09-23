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
    VERSION = "krishna-cognitive-brain-v1"
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
            return {"query": str(query), "concept_id": exact[0], "score": 1.0, "match": "exact"}
        wanted_terms = set(wanted.split())
        ranked = []
        for cid, row in concepts.items():
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

    def status(self):
        with self.lock:
            concepts = list(self.state["concepts"].values())
            edges = list(self.state["edges"].values())
            activations = list(self.state["activations"])
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
