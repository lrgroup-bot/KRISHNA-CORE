from __future__ import annotations

"""KRISHNA Cognitive Brain.

A dependency-light associative concept layer that sits above Gyan-Bhandar retrieval.
It does not claim biological brain equivalence.  Its job is to make knowledge
activation behave more like associative recall: a query can activate related
concepts, preserve evidence/provenance boundaries, expose gaps, and hand those
gaps to the Rishi/BRAHMA research pipeline.
"""

from pathlib import Path
from threading import RLock
import json
import os
import re
import tempfile
import time
from typing import Iterable


_TOKEN = re.compile(r"[a-z0-9][a-z0-9_+.-]{1,}", re.I)
_ALLOWED_TRACKS = {"modern_science", "classical", "cross_domain", "general"}


def _norm(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _terms(value: str) -> set[str]:
    return {x.lower() for x in _TOKEN.findall(str(value or "")) if len(x) > 1}


class KrishnaCognitiveBrain:
    """Persistent concept graph + associative activation engine.

    Design rules:
    * Gyan-Bhandar remains the trusted fact/evidence store.
    * This graph stores concepts/relationships, not unsupported factual truth.
    * Classical and modern-science concepts keep explicit track boundaries.
    * Cross-track links use comparison relations rather than silent equivalence.
    * Research gaps are surfaced instead of invented.
    """

    VERSION = "krishna-cognitive-brain-v1"

    def __init__(self, state_root: str | Path, gyan=None):
        self.root = Path(state_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "concept-graph.json"
        self.gyan = gyan
        self._lock = RLock()
        self._state = self._load()
        self._seed_foundation()

    def _blank(self) -> dict:
        return {
            "version": self.VERSION,
            "concepts": {},
            "relations": [],
            "updated_at": time.time(),
        }

    def _load(self) -> dict:
        if not self.path.exists():
            return self._blank()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return self._blank()
            raw.setdefault("version", self.VERSION)
            raw.setdefault("concepts", {})
            raw.setdefault("relations", [])
            return raw
        except Exception:
            return self._blank()

    def _save(self) -> None:
        self._state["updated_at"] = time.time()
        payload = json.dumps(self._state, ensure_ascii=False, indent=2, sort_keys=True)
        fd, tmp = tempfile.mkstemp(prefix="concept-graph-", suffix=".json", dir=str(self.root))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def _resolve(self, name: str) -> str:
        needle = _norm(name)
        for key, row in self._state["concepts"].items():
            if needle == key or needle in {_norm(x) for x in row.get("aliases", [])}:
                return key
        return needle

    def learn_concept(
        self,
        name: str,
        *,
        aliases: Iterable[str] | None = None,
        track: str = "general",
        description: str = "",
        provenance: dict | None = None,
    ) -> dict:
        canonical = _norm(name)
        if not canonical:
            raise ValueError("concept name is required")
        track = _norm(track)
        if track not in _ALLOWED_TRACKS:
            raise ValueError("invalid concept track")
        cleaned_aliases = sorted({_norm(x) for x in (aliases or []) if _norm(x)} - {canonical})
        with self._lock:
            row = self._state["concepts"].get(canonical) or {
                "name": str(name).strip(),
                "aliases": [],
                "track": track,
                "description": "",
                "provenance": [],
                "created_at": time.time(),
                "updated_at": time.time(),
            }
            row["aliases"] = sorted(set(row.get("aliases", [])) | set(cleaned_aliases))
            if description:
                row["description"] = str(description).strip()
            if row.get("track") in {"", "general"} or track != "general":
                row["track"] = track
            if provenance:
                marker = json.dumps(provenance, sort_keys=True, ensure_ascii=False)
                existing = {json.dumps(x, sort_keys=True, ensure_ascii=False) for x in row.get("provenance", [])}
                if marker not in existing:
                    row.setdefault("provenance", []).append(dict(provenance))
            row["updated_at"] = time.time()
            self._state["concepts"][canonical] = row
            self._save()
            return dict(row)

    def link(
        self,
        source: str,
        target: str,
        relation: str,
        *,
        confidence: float = 0.5,
        provenance: dict | None = None,
        bidirectional: bool = False,
    ) -> dict:
        relation = _norm(relation).replace(" ", "_")
        if not relation:
            raise ValueError("relation is required")
        with self._lock:
            skey, tkey = self._resolve(source), self._resolve(target)
            if skey not in self._state["concepts"] or tkey not in self._state["concepts"]:
                raise KeyError("both concepts must exist before linking")
            s_track = self._state["concepts"][skey].get("track", "general")
            t_track = self._state["concepts"][tkey].get("track", "general")
            if s_track != t_track and {s_track, t_track} <= {"classical", "modern_science"}:
                if relation in {"same_as", "equivalent", "identical_to"}:
                    raise ValueError("classical and modern-science concepts cannot be silently equated")
            row = {
                "source": skey,
                "target": tkey,
                "relation": relation,
                "confidence": max(0.0, min(float(confidence), 1.0)),
                "provenance": dict(provenance or {}),
                "bidirectional": bool(bidirectional),
                "updated_at": time.time(),
            }
            key = (skey, tkey, relation)
            replaced = False
            for idx, old in enumerate(self._state["relations"]):
                if (old.get("source"), old.get("target"), old.get("relation")) == key:
                    self._state["relations"][idx] = row
                    replaced = True
                    break
            if not replaced:
                self._state["relations"].append(row)
            self._save()
            return dict(row)

    def _seed_foundation(self) -> None:
        with self._lock:
            if self._state["concepts"]:
                return
        self.learn_concept(
            "Anu",
            aliases=["aṇu"],
            track="classical",
            description="Classical Indian philosophical concept; preserve source-specific meanings.",
            provenance={"kind": "architecture_seed", "claim": "concept label only"},
        )
        self.learn_concept(
            "Paramanu",
            aliases=["paramāṇu"],
            track="classical",
            description="Classical Indian philosophical concept related to atomistic traditions.",
            provenance={"kind": "architecture_seed", "claim": "concept label only"},
        )
        self.learn_concept(
            "Atom",
            aliases=["atomic structure"],
            track="modern_science",
            description="Modern scientific concept; factual content must come from verified Gyan evidence.",
            provenance={"kind": "architecture_seed", "claim": "concept label only"},
        )
        self.learn_concept(
            "Molecule",
            aliases=["molecular structure"],
            track="modern_science",
            description="Modern scientific concept; factual content must come from verified Gyan evidence.",
            provenance={"kind": "architecture_seed", "claim": "concept label only"},
        )
        seed = {"kind": "architecture_seed", "warning": "comparison is not identity"}
        self.link("Anu", "Paramanu", "related_concept", confidence=0.7, provenance=seed, bidirectional=True)
        self.link("Anu", "Atom", "historical_comparison", confidence=0.45, provenance=seed, bidirectional=True)
        self.link("Paramanu", "Atom", "historical_comparison", confidence=0.45, provenance=seed, bidirectional=True)
        self.link("Atom", "Molecule", "combines_to_form", confidence=0.95,
                  provenance={"kind": "architecture_seed", "verification_required": True})
        self.link("Molecule", "Atom", "composed_of", confidence=0.95,
                  provenance={"kind": "architecture_seed", "verification_required": True})

    def neighbors(self, concept: str, *, depth: int = 1, limit: int = 24) -> list[dict]:
        start = self._resolve(concept)
        if start not in self._state["concepts"]:
            return []
        depth = max(1, min(int(depth), 4))
        limit = max(1, min(int(limit), 100))
        seen = {start}
        frontier = [(start, 0)]
        out = []
        while frontier and len(out) < limit:
            current, level = frontier.pop(0)
            if level >= depth:
                continue
            for rel in self._state["relations"]:
                nxt = None
                direction = "out"
                if rel.get("source") == current:
                    nxt = rel.get("target")
                elif rel.get("bidirectional") and rel.get("target") == current:
                    nxt = rel.get("source")
                    direction = "reverse"
                if not nxt or nxt in seen:
                    continue
                seen.add(nxt)
                row = dict(self._state["concepts"].get(nxt) or {})
                out.append({
                    "concept": nxt,
                    "name": row.get("name", nxt),
                    "track": row.get("track", "general"),
                    "relation": rel.get("relation"),
                    "confidence": rel.get("confidence", 0.0),
                    "distance": level + 1,
                    "direction": direction,
                })
                frontier.append((nxt, level + 1))
                if len(out) >= limit:
                    break
        return out

    def activate(self, query: str, *, depth: int = 2, limit: int = 20) -> dict:
        query_terms = _terms(query)
        hits = []
        with self._lock:
            for key, row in self._state["concepts"].items():
                labels = {key, *[_norm(x) for x in row.get("aliases", [])]}
                score = 0.0
                for label in labels:
                    lt = _terms(label)
                    if not lt:
                        continue
                    if label in _norm(query):
                        score = max(score, 1.0)
                    else:
                        overlap = len(query_terms & lt) / max(1, len(lt))
                        score = max(score, overlap)
                if score > 0:
                    hits.append((score, key))
        hits.sort(reverse=True)
        active = []
        seen = set()
        for score, key in hits[:6]:
            if key not in seen:
                row = self._state["concepts"][key]
                active.append({"concept": key, "name": row.get("name", key), "track": row.get("track"), "score": round(score, 4), "distance": 0})
                seen.add(key)
            for n in self.neighbors(key, depth=depth, limit=limit):
                if n["concept"] in seen:
                    continue
                n["score"] = round(max(0.05, score * (0.72 ** n["distance"]) * float(n.get("confidence") or 0.5)), 4)
                active.append(n)
                seen.add(n["concept"])
                if len(active) >= limit:
                    break
            if len(active) >= limit:
                break
        active.sort(key=lambda x: (float(x.get("score") or 0), -int(x.get("distance") or 0)), reverse=True)
        return {
            "query": query,
            "version": self.VERSION,
            "count": len(active[:limit]),
            "concepts": active[:limit],
            "track_policy": "classical and modern-science tracks may be compared but are not assumed equivalent",
        }

    def related_terms(self, query: str, *, depth: int = 2, limit: int = 16) -> list[str]:
        activated = self.activate(query, depth=depth, limit=limit)
        out = []
        for item in activated["concepts"]:
            key = item["concept"]
            row = self._state["concepts"].get(key) or {}
            for value in [row.get("name", key), *(row.get("aliases") or [])]:
                value = str(value or "").strip()
                if value and value.lower() not in {x.lower() for x in out}:
                    out.append(value)
        return out[:limit]

    def expand_query(self, query: str, *, depth: int = 2, limit: int = 16) -> str:
        related = self.related_terms(query, depth=depth, limit=limit)
        if not related:
            return str(query or "")
        return str(query or "").strip() + "\nASSOCIATED CONCEPTS: " + ", ".join(related)

    @staticmethod
    def _coverage_score(memory_text: str, concept: str, aliases: Iterable[str]) -> float:
        text_terms = _terms(memory_text)
        candidates = [concept, *aliases]
        best = 0.0
        for candidate in candidates:
            cterms = _terms(candidate)
            if not cterms:
                continue
            best = max(best, len(cterms & text_terms) / max(1, len(cterms)))
        return best

    @staticmethod
    def _suggest_rishi(name: str, track: str) -> str:
        terms = _terms(name)
        if terms & {"anu", "paramanu", "atom", "molecule", "atomic", "molecular", "material", "particle", "chemistry", "physics"}:
            return "Kanada"
        if terms & {"logic", "causality", "statistics", "evidence"}:
            return "Gautama"
        if terms & {"system", "cognition", "mind"}:
            return "Kapila"
        return "Veda Vyasa" if track == "classical" else "Vishwamitra"

    def activation_plan(self, project: str, query: str, *, memory_limit: int = 200) -> dict:
        activation = self.activate(query)
        rows = []
        if self.gyan is not None:
            try:
                rows = list(self.gyan.recall(project, None, memory_limit, False, None, False))
            except TypeError:
                rows = list(self.gyan.recall(project, None, memory_limit, False, None))
        memory_text = "\n".join(
            f"{r.get('topic', '')} {r.get('lesson', '')}" for r in rows
        )
        coverage, gaps = [], []
        for item in activation["concepts"]:
            key = item["concept"]
            row = self._state["concepts"].get(key) or {}
            score = self._coverage_score(memory_text, row.get("name", key), row.get("aliases", []))
            status = "covered" if score >= 0.75 else "partial" if score > 0 else "gap"
            record = {
                "concept": key,
                "name": row.get("name", key),
                "track": row.get("track", "general"),
                "memory_coverage": round(score, 4),
                "status": status,
            }
            coverage.append(record)
            if status != "covered":
                gaps.append({
                    **record,
                    "suggested_rishi": self._suggest_rishi(row.get("name", key), row.get("track", "general")),
                    "next_action": "research_and_verify_before_gyan_promotion",
                })
        return {
            **activation,
            "project": project,
            "memory_records_checked": len(rows),
            "coverage": coverage,
            "knowledge_gaps": gaps,
            "research_needed": bool(gaps),
            "research_policy": "reuse verified Gyan first; research only missing/weak branches; BRAHMA QC before trusted promotion",
        }

    def status(self) -> dict:
        with self._lock:
            tracks = {}
            for row in self._state["concepts"].values():
                track = row.get("track", "general")
                tracks[track] = tracks.get(track, 0) + 1
            return {
                "version": self.VERSION,
                "concept_count": len(self._state["concepts"]),
                "relation_count": len(self._state["relations"]),
                "tracks": tracks,
                "state_path": str(self.path),
                "biological_brain_claim": False,
            }
