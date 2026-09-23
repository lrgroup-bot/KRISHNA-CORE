from __future__ import annotations

"""HAWKEYE Learning Observer.

A bounded observer/curator that turns user-selected camera/video/book/object/audio
observations into provenance-preserving learning packets, then routes candidate
knowledge through Universal Learning -> BRAHMA -> the appropriate Rishi team.

The observer never treats raw media as knowledge. It stores distilled findings,
source hashes and provenance only. Unknown faces are not used as web/social-media
identity search keys; public research may use an explicit user-supplied identity,
an enrolled+consented local match, or ordinary public clues such as a visible
name, username, organization or asset marking.
"""

from pathlib import Path
import hashlib
import json
import os
import re
import time
import uuid

from .field_perception import FieldPerceptionPolicy


class HawkeyeLearningObserver:
    VERSION = "hawkeye-learning-observer-v1"
    SOURCE_TYPES = {
        "camera", "image", "video", "book", "page", "document", "screen", "object",
        "audio", "mobile", "mobile_curated_evidence", "pc", "web", "user_note",
    }
    EVIDENCE_STATES = {"MEASURED", "OBSERVED", "INFERRED", "PREDICTED", "UNKNOWN"}
    ALLOWED_MODALITIES = {"image", "video", "audio", "text", "sensor", "document", "multimodal"}

    def __init__(self, state_dir, *, universal_learning, brahma, council, memory=None):
        self.root = Path(state_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.ledger = self.root / "observer-ledger.jsonl"
        self.universal_learning = universal_learning
        self.brahma = brahma
        self.council = council
        self.memory = memory

    @staticmethod
    def _text(value, limit=8000):
        return str(value or "").strip()[:limit]

    @staticmethod
    def _clamp(value):
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _source_hash(source_type, source_ref, subject):
        raw = f"{source_type}|{source_ref}|{subject}".encode("utf-8", errors="ignore")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _public_clues(values):
        out = []
        for value in values or []:
            text = re.sub(r"\s+", " ", str(value or "").strip())
            if text and text not in out:
                out.append(text[:240])
        return out[:20]

    def public_research_plan(
        self,
        *,
        known_identity="",
        identity_basis="",
        public_clues=None,
        subject="",
    ):
        """Create text/public-clue research queries without face-to-web identification."""
        identity = self._text(known_identity, 240)
        basis = str(identity_basis or "").strip().lower()
        clues = self._public_clues(public_clues)
        identity_allowed = bool(identity and basis in {"user_supplied", "enrolled_consented_match"})
        terms = []
        if identity_allowed:
            terms.append(identity)
        terms.extend(clues)
        if subject and not terms:
            terms.append(self._text(subject, 240))

        queries = []
        for term in terms[:6]:
            suffixes = ["", " official"]
            if identity_allowed or clues:
                suffixes += [
                    " site:linkedin.com/in",
                    " site:instagram.com",
                    " site:facebook.com",
                    " site:x.com",
                ]
            for suffix in suffixes:
                q = (term + suffix).strip()
                if q and q not in queries:
                    queries.append(q)

        return {
            "allowed": bool(queries),
            "identity_allowed": identity_allowed,
            "identity_basis": basis or "none",
            "queries": queries[:24],
            "face_to_social_search": False,
            "policy": (
                "Public research may use an explicit identity, an enrolled+consented local match, "
                "or ordinary public clues. An unknown face/embedding is never used to discover identity."
            ),
        }

    def capture(
        self,
        *,
        utterance,
        source_type,
        source_ref="",
        modalities=None,
        subject="",
        analysis="",
        confidence=0.0,
        evidence_state="UNKNOWN",
        audio_observations=None,
        novelty=0.5,
        quality=0.5,
        importance=0.6,
        known_identity="",
        identity_basis="",
        public_clues=None,
    ):
        source_type = str(source_type or "camera").strip().lower()
        if source_type not in self.SOURCE_TYPES:
            source_type = "camera"

        modalities = [
            str(x).strip().lower() for x in (modalities or [])
            if str(x).strip().lower() in self.ALLOWED_MODALITIES
        ]
        modalities = list(dict.fromkeys(modalities))[:8]
        state = str(evidence_state or "UNKNOWN").strip().upper()
        if state not in self.EVIDENCE_STATES:
            state = "UNKNOWN"

        utterance = FieldPerceptionPolicy.redact_sensitive_text(self._text(utterance, 4000))
        subject = FieldPerceptionPolicy.redact_sensitive_text(self._text(subject, 1000))
        analysis = FieldPerceptionPolicy.redact_sensitive_text(self._text(analysis, 8000))
        source_ref = self._text(source_ref, 2000)
        confidence = self._clamp(confidence)
        observation_id = str(uuid.uuid4())
        source_hash = self._source_hash(source_type, source_ref, subject)

        universal = self.universal_learning.ingest(
            utterance=utterance,
            source_type=source_type,
            source_ref=source_ref,
            modalities=modalities,
            subject=subject,
            confidence=confidence,
            analysis=analysis,
            evidence_state=state,
        )
        if "audio" in modalities:
            universal["sound"] = self.universal_learning.classify_sound_request(
                utterance, audio_observations or {}
            )

        modality = (
            modalities[0] if len(modalities) == 1
            else ("multimodal" if modalities else "text")
        )
        evidence = [{
            "source_ref": source_ref or f"observer:{observation_id}",
            "source_type": source_type,
            "source_hash": source_hash,
        }]
        brahma = self.brahma.intake(
            source="pc" if source_type == "pc" else "mobile",
            topic=subject or utterance or "HAWKEYE observation",
            content=analysis or utterance,
            modality=modality,
            evidence=evidence,
            provenance={
                "source_ref": source_ref,
                "source_type": source_type,
                "source_hash": source_hash,
                "hawkeye_observation_id": observation_id,
                "captured_at": time.time(),
            },
            confidence=confidence,
            novelty=self._clamp(novelty),
            quality=self._clamp(quality),
            importance=self._clamp(importance),
            evidence_status=state.lower(),
        )

        topic = (subject + " " + analysis[:1500]).strip()
        team = self.council.specialist_team(topic or "general knowledge", limit=6)
        research = self.public_research_plan(
            known_identity=known_identity,
            identity_basis=identity_basis,
            public_clues=public_clues,
            subject=subject,
        )

        row = {
            "observation_id": observation_id,
            "version": self.VERSION,
            "created_at": time.time(),
            "source_type": source_type,
            "source_ref": source_ref,
            "source_hash": source_hash,
            "modalities": modalities,
            "subject": subject,
            "finding": analysis,
            "confidence": confidence,
            "evidence_state": state,
            "universal_learning_id": universal.get("learning_id"),
            "lead_rishi": brahma.get("lead_rishi") or universal.get("rishi"),
            "rishi_team": [
                x.get("id") for x in (team.get("members") or []) if x.get("id")
            ],
            "brahma_decision_id": brahma.get("decision_id"),
            "research_plan": research,
            "storage_policy": {
                "raw_media_stored_here": False,
                "distilled_finding_only": True,
                "private_raw_media_cloud_upload": False,
                "credentials_redacted": True,
            },
        }
        with self.ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

        if self.memory:
            self.memory.audit(
                "hawkeye_learning_observer",
                "routed",
                f"{observation_id}:{row['lead_rishi']}:{source_hash[:16]}",
            )

        return {
            **row,
            "universal": universal,
            "unknown_resolution": universal.get("unknown_resolution"),
            "sound": universal.get("sound"),
            "brahma": brahma,
            "next_action": (
                "Rishi/BRAHMA research and cross-check on PC"
                if brahma.get("should_learn")
                else "reuse existing knowledge or discard low-value observation"
            ),
        }

    def status(self):
        count = 0
        if self.ledger.is_file():
            with self.ledger.open("r", encoding="utf-8") as handle:
                for _ in handle:
                    count += 1
        return {
            "agent": "HAWKEYE LEARNING OBSERVER",
            "version": self.VERSION,
            "observations": count,
            "sources": sorted(self.SOURCE_TYPES),
            "modalities": sorted(self.ALLOWED_MODALITIES),
            "routes_to_rishis": True,
            "raw_media_learning": False,
            "distilled_findings_only": True,
            "face_to_social_search": False,
            "known_identity_public_research": True,
            "ready": True,
        }
