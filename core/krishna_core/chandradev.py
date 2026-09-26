from __future__ import annotations

"""CHANDRADEV independent PC live-camera vision/QC peer for KRISHNA.

CHANDRADEV runs on the KRISHNA PC and independently watches
live rendered/tested output through a camera or supplied visual observations. It
does not silently override BRAHMA or deterministic tests. Disagreement between
CHANDRADEV and BRAHMA creates an explicit QC debate that must be resolved before
release/promotion can pass.
"""

from pathlib import Path
import hashlib
import json
import time
import uuid

from .field_perception import FieldPerceptionPolicy


class ChandradevQC:
    VERSION = "chandradev-live-qc-v1"
    AGENT_ID = "chandradev"
    CAPABILITIES = (
        "live_camera_qc",
        "screen_visual_qc",
        "frontend_qc",
        "backend_test_observation",
        "suryadev_cross_check",
        "brahma_peer_qc",
        "qc_debate",
    )
    FINAL_STATES = {"PASSED", "BLOCKED", "RETEST_REQUIRED"}

    def __init__(self, state_root, *, memory=None):
        self.root = Path(state_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.ledger = self.root / "chandradev-qc.jsonl"
        self.camera_ledger = self.root / "chandradev-camera.jsonl"
        self.memory = memory

    @staticmethod
    def _text(value, limit=6000):
        return FieldPerceptionPolicy.redact_sensitive_text(str(value or "").strip())[:limit]

    @staticmethod
    def _clamp(value):
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _fingerprint(value):
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _append(self, row):
        with self.ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

    @staticmethod
    def _suryadev_pass(review):
        review = dict(review or {})
        if "passed" in review:
            return bool(review.get("passed"))
        material = review.get("material_issues") or []
        return not bool(material)

    @staticmethod
    def _brahma_pass(review):
        review = dict(review or {})
        if "candidate_passed" in review:
            return bool(review.get("candidate_passed"))
        if "passed" in review:
            return bool(review.get("passed"))
        if review.get("proposal"):
            return True
        return False

    def review(self, *, project="KRISHNA", deterministic_passed, suryadev_review,
               brahma_review, camera_observation=None, test_summary=None):
        surya = dict(suryadev_review or {})
        brahma = dict(brahma_review or {})
        camera = dict(camera_observation or {})
        deterministic_passed = bool(deterministic_passed)

        camera_issues = [
            x for x in (camera.get("issues") or [])
            if isinstance(x, dict)
            and str(x.get("severity") or "").lower() in {"error", "critical"}
            and self._clamp(x.get("confidence")) >= 0.8
        ]
        camera_pass = not camera_issues
        surya_pass = self._suryadev_pass(surya)
        brahma_pass = self._brahma_pass(brahma)

        if not deterministic_passed:
            state = "BLOCKED"
            reason = "deterministic tests/gates failed"
            debate_required = False
        elif not camera_pass:
            state = "BLOCKED"
            reason = "high-confidence live-camera QC issue detected"
            debate_required = False
        elif surya_pass == brahma_pass:
            state = "PASSED" if surya_pass else "BLOCKED"
            reason = "SURYDEV and BRAHMA agree after independent review"
            debate_required = False
        else:
            state = "DEBATE_REQUIRED"
            reason = "SURYDEV and BRAHMA disagree; QC cannot silently pass"
            debate_required = True

        qc_id = "CHANDRA-QC-" + uuid.uuid4().hex[:18]
        row = {
            "schema": "krishna.chandradev.qc.v1",
            "qc_id": qc_id,
            "agent": "CHANDRADEV",
            "version": self.VERSION,
            "project": self._text(project, 200) or "KRISHNA",
            "state": state,
            "reason": reason,
            "deterministic_passed": deterministic_passed,
            "camera_passed": camera_pass,
            "camera_issues": camera_issues[:40],
            "suryadev_passed": surya_pass,
            "brahma_passed": brahma_pass,
            "suryadev_review_ref": surya.get("finding_id") or surya.get("job_id") or surya.get("fingerprint"),
            "brahma_review_ref": brahma.get("qc_id") or brahma.get("decision_id"),
            "test_summary": self._text(test_summary, 4000),
            "debate_required": debate_required,
            "debate": None,
            "created_at": time.time(),
            "final": state in self.FINAL_STATES,
            "policy": {
                "deterministic_tests_cannot_be_overridden": True,
                "camera_is_independent_visual_evidence": True,
                "brahma_and_chandradev_are_peer_qc": True,
                "disagreement_requires_recorded_debate": True,
                "no_raw_camera_media_to_gyan": True,
            },
        }
        if debate_required:
            row["debate"] = {
                "status": "OPEN",
                "participants": ["chandradev", "brahma"],
                "question": "Should this candidate/test be accepted, changed, or retested?",
                "positions": {
                    "suryadev_evidence": {
                        "passed": surya_pass,
                        "issues": (surya.get("material_issues") or surya.get("issues") or [])[:30],
                    },
                    "brahma": {
                        "passed": brahma_pass,
                        "reasons": list(brahma.get("reasons") or [])[:30],
                    },
                    "chandradev": {
                        "camera_passed": camera_pass,
                        "camera_issues": camera_issues[:30],
                    },
                },
                "resolution": None,
            }
        row["fingerprint"] = self._fingerprint({
            "project": row["project"],
            "deterministic": deterministic_passed,
            "camera": camera_issues,
            "surya": surya_pass,
            "brahma": brahma_pass,
        })
        self._append(row)
        if self.memory:
            self.memory.audit(
                "chandradev_qc",
                state.lower(),
                f"{qc_id}:{row['project']}:{row['fingerprint'][:16]}",
            )
        return row

    def resolve_debate(self, qc_id, *, resolution, chandradev_position, brahma_position,
                       notes="", retest_evidence=None):
        resolution = str(resolution or "").strip().upper()
        if resolution not in self.FINAL_STATES:
            raise ValueError("resolution must be PASSED, BLOCKED or RETEST_REQUIRED")
        chandradev_position = self._text(chandradev_position, 3000)
        brahma_position = self._text(brahma_position, 3000)
        if not chandradev_position or not brahma_position:
            raise ValueError("both CHANDRADEV and BRAHMA positions are required")

        latest = None
        if self.ledger.is_file():
            for line in self.ledger.read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if row.get("qc_id") == qc_id:
                    latest = row
        if not latest:
            raise KeyError(qc_id)
        if not latest.get("debate_required"):
            raise ValueError("QC record does not require debate")

        resolved = {
            **latest,
            "state": resolution,
            "final": True,
            "debate_required": False,
            "resolved_at": time.time(),
            "debate": {
                **dict(latest.get("debate") or {}),
                "status": "CLOSED",
                "resolution": resolution,
                "chandradev_position": chandradev_position,
                "brahma_position": brahma_position,
                "notes": self._text(notes, 4000),
                "retest_evidence": list(retest_evidence or [])[:50],
            },
        }
        self._append(resolved)
        if self.memory:
            self.memory.audit("chandradev_qc_debate", resolution.lower(), qc_id)
        return resolved

    def record_camera_observation(self, *, analysis, frame_meta=None, source="camera", prompt=""):
        frame = dict(frame_meta or {})
        row = {
            "schema": "krishna.chandradev.camera-observation.v1",
            "observation_id": "CHANDRA-CAM-" + uuid.uuid4().hex[:18],
            "agent": "CHANDRADEV",
            "source": self._text(source, 300) or "camera",
            "analysis": self._text(analysis, 8000),
            "prompt": self._text(prompt, 3000),
            "frame": {
                "path": self._text(frame.get("path"), 1000),
                "width": int(frame.get("width") or 0),
                "height": int(frame.get("height") or 0),
                "content_type": self._text(frame.get("content_type"), 100),
                "captured_at": frame.get("captured_at"),
            },
            "local_only": True,
            "hawkeye_involved": False,
            "raw_media_uploaded": False,
            "created_at": time.time(),
        }
        row["fingerprint"] = self._fingerprint({
            "source": row["source"],
            "analysis": row["analysis"],
            "frame": row["frame"],
        })
        with self.camera_ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        if self.memory:
            self.memory.audit(
                "chandradev_camera_observation",
                "recorded",
                f"{row['observation_id']}:{row['fingerprint'][:16]}",
            )
        return row

    def camera_observations(self, limit=50):
        rows = []
        if self.camera_ledger.is_file():
            for line in self.camera_ledger.read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
        return list(reversed(rows[-max(1, min(int(limit or 50), 500)):]))

    def status(self):
        count = 0
        open_debates = 0
        if self.ledger.is_file():
            latest = {}
            for line in self.ledger.read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                latest[row.get("qc_id")] = row
            count = len(latest)
            open_debates = len([
                x for x in latest.values()
                if x.get("state") == "DEBATE_REQUIRED"
            ])
        return {
            "agent": "CHANDRADEV",
            "version": self.VERSION,
            "role": "independent PC live-camera vision and final-QC peer",
            "capabilities": list(self.CAPABILITIES),
            "runs_on_pc": True,
            "runs_on_external_node": False,
            "transports": ["local_rtmp", "local_camera", "verified_usb_packet", "trusted_lan"],
            "qc_records": count,
            "camera_observations": len(self.camera_observations(500)),
            "open_debates": open_debates,
            "peer_qc": "BRAHMA",
            "upstream_observer": "SURYDEV",
            "deterministic_gates_authoritative": True,
            "ready": True,
        }
