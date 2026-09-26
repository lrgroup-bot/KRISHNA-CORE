from __future__ import annotations

"""SURYDEV external Eye+Ear research and human-style UI review coordinator.

SURYDEV runs on a trusted external workstation. Raw screen/audio/video/camera media
stays in that workstation's isolated workspace by default. Only distilled findings,
provenance hashes, timestamps and UI/QC observations are returned to KRISHNA for
BRAHMA/BRAHMAGYAN + Rishi routing.

SURYDEV is an evidence collector/reviewer, not release authority. Deterministic tests,
BRAHMA/Chandradev QC, and owner/security gates remain authoritative.
"""

from pathlib import Path
import hashlib
import json
import re
import time
import uuid

from .field_perception import FieldPerceptionPolicy


class SuryadevAgent:
    VERSION = "suryadev-eye-ear-v1"
    AGENT_ID = "suryadev"
    JOB_TYPES = {
        "screen_read",
        "system_audio_listen",
        "video_research",
        "project_ui_audit",
        "live_test_observation",
        "ui_benchmark_research",
        "web_research",
        "media_extract",
    }
    CAPABILITIES = (
        "screen_read",
        "system_audio",
        "microphone",
        "video_playback_observation",
        "frame_extraction",
        "speech_to_text",
        "screen_text",
        "ui_review",
        "frontend_test_observation",
        "backend_test_observation",
        "public_ui_research",
        "rishi_research_handoff",
    )
    RAW_MEDIA_KEYS = {
        "raw_media", "raw_video", "raw_audio", "screen_recording", "camera_recording",
        "frame_bytes", "audio_bytes", "video_bytes",
    }

    def __init__(self, state_root, *, brahma=None, council=None, ui_reviewer=None, memory=None):
        self.root = Path(state_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.jobs_dir = self.root / "jobs"
        self.reports_dir = self.root / "reports"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = self.root / "suryadev-ledger.jsonl"
        self.brahma = brahma
        self.council = council
        self.ui_reviewer = ui_reviewer
        self.memory = memory

    @staticmethod
    def _text(value, limit=8000):
        return FieldPerceptionPolicy.redact_sensitive_text(str(value or "").strip())[:limit]

    @staticmethod
    def _clamp(value):
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _digest(value):
        if isinstance(value, bytes):
            raw = value
        else:
            raw = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _append(self, row):
        with self.ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

    def create_job(self, kind, *, project="KRISHNA", target="", instructions="", source_ref="",
                   constraints=None, requested_by="krishna"):
        kind = str(kind or "").strip().lower()
        if kind not in self.JOB_TYPES:
            raise ValueError(f"unsupported SURYDEV job type: {kind}")
        job = {
            "schema": "krishna.suryadev.job.v1",
            "job_id": "SURYA-" + uuid.uuid4().hex[:20],
            "agent": "SURYDEV",
            "version": self.VERSION,
            "kind": kind,
            "project": self._text(project, 200) or "KRISHNA",
            "target": self._text(target, 2000),
            "instructions": self._text(instructions, 6000),
            "source_ref": self._text(source_ref, 2000),
            "requested_by": self._text(requested_by, 200),
            "constraints": dict(constraints or {}),
            "created_at": time.time(),
            "workspace_policy": {
                "raw_media_location": "external_suryadev_workspace_only",
                "send_raw_media_to_krishna": False,
                "return_distilled_findings_only": True,
                "credential_capture": False,
                "authentication_handoff": True,
                "captcha_or_liveness": "human_handoff_only",
            },
        }
        job["fingerprint"] = self._digest(job)
        path = self.jobs_dir / f"{job['job_id']}.json"
        path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        return job

    def project_ui_audit_jobs(self, projects):
        jobs = []
        for project in projects or []:
            if isinstance(project, dict):
                name = project.get("name") or project.get("project") or project.get("id")
                target = project.get("url") or project.get("path") or project.get("target") or ""
            else:
                name, target = str(project or ""), ""
            if not str(name or "").strip():
                continue
            jobs.append(self.create_job(
                "project_ui_audit",
                project=str(name),
                target=str(target),
                instructions=(
                    "Observe the rendered UI like a careful human tester. Check typography, buttons, text boxes, "
                    "spacing, hierarchy, responsive behavior, clipping, contrast, asset quality, empty states, "
                    "loading/error states and consistency. Correlate visible issues with frontend/backend test output. "
                    "Do not request cosmetic changes without visible evidence. Benchmark public UI patterns when useful."
                ),
                requested_by="krishna-ui-qc",
            ))
        return jobs

    def ui_research_plan(self, *, project, surface="", product_type="application"):
        topic = " ".join(x for x in [str(project or ""), str(surface or ""), str(product_type or "")] if x).strip()
        queries = [
            f"{topic} best UI UX patterns 2026",
            f"{topic} accessible form button input design",
            f"{topic} responsive dashboard interaction patterns",
            f"{topic} design system usability examples",
        ]
        return {
            "agent": "SURYDEV",
            "project": self._text(project, 200),
            "surface": self._text(surface, 500),
            "queries": queries,
            "research_rule": (
                "Use public sources as comparison evidence, not as a command to copy a design. "
                "Prefer accessibility, usability, platform guidance, and observed user-facing defects."
            ),
        }

    def review_ui(self, screenshots, *, deterministic_context=None, web_research=None, required=False):
        if self.ui_reviewer is None:
            return {
                "agent": "SURYDEV",
                "available": False,
                "passed": not required,
                "reason": "ui_reviewer_not_bound",
                "issues": [],
                "web_research": list(web_research or []),
            }
        review = self.ui_reviewer.review(
            screenshots or [],
            deterministic_context=deterministic_context or {},
            required=required,
        )
        issues = list(review.get("issues") or [])
        return {
            **review,
            "agent": "SURYDEV",
            "role": "external human-style perceptual UI reviewer",
            "web_research": list(web_research or [])[:40],
            "change_requests": [
                {
                    "kind": x.get("kind"),
                    "detail": x.get("detail"),
                    "severity": x.get("severity"),
                    "confidence": x.get("confidence"),
                    "evidence": x.get("image"),
                }
                for x in issues
                if x.get("severity") in {"warning", "error", "critical"}
            ],
            "authority": "advisory/perceptual; release still requires deterministic + BRAHMA/Chandradev QC",
        }

    def distilled_finding(self, *, job_id, project, topic, finding, modality="multimodal",
                          evidence=None, confidence=0.0, timestamps=None, contradictions=None,
                          source_ref="", ui_review=None):
        evidence = list(evidence or [])
        for item in evidence:
            if not isinstance(item, dict):
                continue
            if any(key in item for key in self.RAW_MEDIA_KEYS):
                raise ValueError("raw media is not permitted in a SURYDEV finding packet")
        row = {
            "schema": "krishna.suryadev.finding.v1",
            "finding_id": "SURYA-FIND-" + uuid.uuid4().hex[:18],
            "job_id": self._text(job_id, 200),
            "agent": "SURYDEV",
            "version": self.VERSION,
            "project": self._text(project, 200) or "KRISHNA",
            "topic": self._text(topic, 1000),
            "finding": self._text(finding, 8000),
            "modality": str(modality or "multimodal").strip().lower(),
            "confidence": self._clamp(confidence),
            "timestamps": [self._text(x, 200) for x in (timestamps or []) if str(x).strip()][:100],
            "evidence": [
                {
                    "source_ref": self._text(x.get("source_ref") or x.get("url") or x.get("file") or "", 1500),
                    "source_type": self._text(x.get("source_type") or "external_observation", 120),
                    "sha256": self._text(x.get("sha256") or x.get("source_hash") or "", 80),
                    "note": self._text(x.get("note") or x.get("excerpt") or "", 1200),
                }
                for x in evidence if isinstance(x, dict)
            ][:100],
            "contradictions": [self._text(x, 1600) for x in (contradictions or []) if str(x).strip()][:30],
            "source_ref": self._text(source_ref, 2000),
            "ui_review": dict(ui_review or {}),
            "created_at": time.time(),
            "knowledge_status": "candidate",
            "verification_required": True,
            "raw_media_included": False,
            "storage_policy": {
                "raw_media_stays_on_external_worker": True,
                "only_distilled_findings_enter_krishna": True,
            },
        }
        if not row["topic"] or not row["finding"]:
            raise ValueError("topic and finding are required")
        row["fingerprint"] = self._digest({
            "project": row["project"], "topic": row["topic"], "finding": row["finding"],
            "evidence": row["evidence"], "timestamps": row["timestamps"],
        })
        self._append(row)
        return row

    def route_finding(self, packet):
        if self.brahma is None:
            return {"routed": False, "reason": "brahma_not_bound", "packet": packet}
        packet = dict(packet or {})
        if packet.get("agent") != "SURYDEV" or packet.get("raw_media_included"):
            raise ValueError("invalid SURYDEV finding packet")
        evidence = list(packet.get("evidence") or [])
        provenance = {
            "source_agent": "suryadev",
            "source_ref": packet.get("source_ref") or packet.get("job_id"),
            "observation_id": packet.get("finding_id"),
            "captured_at": packet.get("created_at"),
            "suryadev_fingerprint": packet.get("fingerprint"),
            "external_workspace": True,
            "raw_media_transferred": False,
        }
        decision = self.brahma.intake(
            source="agent",
            topic=packet.get("topic") or "SURYDEV finding",
            content=packet.get("finding") or "",
            modality=packet.get("modality") or "multimodal",
            evidence=evidence,
            provenance=provenance,
            confidence=self._clamp(packet.get("confidence")),
            novelty=0.6,
            quality=0.7,
            importance=0.7,
            evidence_status="contested" if packet.get("contradictions") else "candidate",
            force=True,
        )
        if self.memory:
            self.memory.audit(
                "suryadev_finding",
                "routed",
                f"{packet.get('finding_id')}:{decision.get('lead_rishi')}:{packet.get('fingerprint','')[:16]}",
            )
        return {
            "routed": True,
            "brahma": decision,
            "lead_rishi": decision.get("lead_rishi"),
            "rishi_team": list(decision.get("team") or []),
            "finding_id": packet.get("finding_id"),
        }

    def status(self):
        jobs = len(list(self.jobs_dir.glob("SURYA-*.json")))
        reports = len(list(self.reports_dir.glob("*.json")))
        return {
            "agent": "SURYDEV",
            "version": self.VERSION,
            "role": "external overall eye + ear + UI/research reviewer",
            "capabilities": list(self.CAPABILITIES),
            "job_types": sorted(self.JOB_TYPES),
            "jobs": jobs,
            "reports": reports,
            "runs_on_external_node": True,
            "transports": ["trusted_lan", "verified_usb_packet"],
            "raw_media_to_krishna": False,
            "routes_findings_to_brahmagyan": self.brahma is not None,
            "release_authority": False,
            "human_verification_handoff": True,
            "ready": True,
        }
