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
from .suryadev_horses import SuryadevHorseFleet
from .suryadev_curriculum import SuryadevCurriculumPlanner


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

    def __init__(self, state_root, *, brahma=None, brahmagyan=None, council=None, garuda_scout=None, ui_reviewer=None, memory=None):
        self.root = Path(state_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.jobs_dir = self.root / "jobs"
        self.reports_dir = self.root / "reports"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = self.root / "suryadev-ledger.jsonl"
        self.horses = SuryadevHorseFleet(self.root / "seven-horses")
        self.brahma = brahma
        self.brahmagyan = brahmagyan
        self.council = council
        self.curriculum = (
            SuryadevCurriculumPlanner(
                self.root / "curriculum",
                brahma=brahma,
                brahmagyan=brahmagyan,
                council=council,
                garuda_scout=garuda_scout,
                memory=memory,
            )
            if brahma is not None and brahmagyan is not None and council is not None and garuda_scout is not None
            else None
        )
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

    def horse_status(self):
        return self.horses.status()

    def horse_auto_bind(self, *, node_id, profile, label="", approved=False):
        row=self.horses.auto_bind(
            node_id=node_id,profile=profile or {},label=label,approved=approved,
        )
        if self.memory:
            binding=row.get("binding") or {}
            self.memory.audit(
                "suryadev_horse_auto_bind",
                "bound" if binding else "fleet_full",
                f"{binding.get('horse_id','none')}:{node_id}:{row.get('classification',{}).get('workload')}",
            )
        return row

    def curriculum_plan(self, subject, *, horse_id, reason="", preferred_rishis=None,
                        max_videos=10, candidate_limit=40, enrich_metadata=True):
        if self.curriculum is None:
            raise RuntimeError("SURYDEV curriculum planner is not bound to BRAHMA/BRAHMAGYAN/Garuda")
        # The horse must already exist as a permanent profile; a physical binding may
        # be added later but unrecognized worker IDs cannot receive curricula.
        self.horses._horse(horse_id)
        return self.curriculum.build_six_hour_plan(
            subject,horse_id=horse_id,reason=reason,
            preferred_rishis=preferred_rishis or [],
            max_videos=max_videos,candidate_limit=candidate_limit,
            enrich_metadata=enrich_metadata,
        )

    def curriculum_next(self, *, horse_id, max_videos=10, candidate_limit=40, enrich_metadata=True):
        if self.curriculum is None:
            raise RuntimeError("SURYDEV curriculum planner is not bound to BRAHMA/BRAHMAGYAN/Garuda")
        self.horses._horse(horse_id)
        return self.curriculum.build_next_plan(
            horse_id=horse_id,max_videos=max_videos,
            candidate_limit=candidate_limit,enrich_metadata=enrich_metadata,
        )

    def curriculum_latest(self, horse_id):
        if self.curriculum is None:
            raise RuntimeError("SURYDEV curriculum planner is not available")
        return self.curriculum.latest_for_horse(horse_id)

    def horse_bind(self, horse_id, *, node_id, device_class, label="", approved=False):
        row=self.horses.bind(
            horse_id,node_id=node_id,device_class=device_class,label=label,approved=approved,
        )
        if self.memory:
            self.memory.audit(
                "suryadev_horse_bind","bound",
                f"{row['horse_id']}:{row['node_id']}:{row['device_class']}",
            )
        return row

    def horse_unbind(self, horse_id, *, approved=False):
        row=self.horses.unbind(horse_id,approved=approved)
        if self.memory:
            self.memory.audit("suryadev_horse_bind","unbound",str(row.get("horse_id") or horse_id))
        return row

    def horse_heartbeat(self, horse_id, *, node_id, status=None):
        return self.horses.heartbeat(horse_id,node_id=node_id,status=status or {})

    def horse_shift_boundary(self, elapsed_seconds, video_remaining_seconds=None):
        return self.horses.shift_boundary(elapsed_seconds,video_remaining_seconds)

    @staticmethod
    def _horse_learning_text(source):
        parts=[]
        title=str(source.get("title") or "").strip()
        if title:parts.append("TITLE: "+title)
        publisher=str(source.get("publisher") or "").strip()
        if publisher:parts.append("SOURCE/PUBLISHER: "+publisher)
        tags=[str(x).strip() for x in (source.get("tags") or []) if str(x).strip()]
        if tags:parts.append("TAGS: "+", ".join(tags))
        description=str(source.get("description") or "").strip()
        if description:parts.append("DESCRIPTION: "+description)
        transcript=str(source.get("transcript_excerpt") or "").strip()
        if transcript:parts.append("TRANSCRIPT/CAPTIONS: "+transcript)
        screen_notes=str(source.get("screen_notes") or "").strip()
        if screen_notes:parts.append("SCREEN UNDERSTANDING: "+screen_notes)
        return "\n".join(parts)

    def horse_learning_batch(self, horse_id, *, node_id, payload):
        """Route a bound horse's distilled media batch into the existing BRAHMA/Rishi path."""
        batch=self.horses.ingest_batch(horse_id,node_id=node_id,payload=payload or {})
        routes=[];errors=[]
        for index,source in enumerate(batch.get("sources") or []):
            learning=self._horse_learning_text(source)
            if not learning.strip():continue
            title=str(source.get("title") or "").strip() or "Untitled media source"
            tags=[str(x).strip() for x in (source.get("tags") or []) if str(x).strip()]
            topic=(" ".join([title,*tags[:12]])).strip()[:1000]
            evidence=[{
                "source_ref":source.get("url") or source.get("source_sha256"),
                "source_type":"suryadev_horse_media_source",
                "sha256":source.get("source_sha256"),
                "note":(
                    f"{batch['horse_name']} device-learning source; "
                    f"publisher={source.get('publisher') or 'unknown'}; "
                    f"watched={source.get('start_seconds',0):.1f}-{source.get('end_seconds',0):.1f}s; "
                    "raw media stayed on the edge device"
                ),
            }]
            if source.get("transcript_sha256"):
                evidence.append({
                    "source_ref":source.get("url") or source.get("source_sha256"),
                    "source_type":"transcript_or_caption_digest",
                    "sha256":source.get("transcript_sha256"),
                    "note":"Transcript/caption excerpt supplied by the bound SURYDEV horse; important claims still require independent verification.",
                })
            packet=self.distilled_finding(
                job_id=batch["batch_id"],
                project="BRAHMAGYAN",
                topic=topic,
                finding=learning,
                modality="transcript" if source.get("transcript_excerpt") else "video_metadata",
                evidence=evidence,
                confidence=0.60 if source.get("transcript_excerpt") else 0.42,
                timestamps=[f"{source.get('start_seconds',0):.1f}-{source.get('end_seconds',0):.1f}s"],
                source_ref=source.get("url") or source.get("source_sha256"),
            )
            packet.update({
                "horse_id":batch["horse_id"],
                "horse_name":batch["horse_name"],
                "node_id":batch["node_id"],
                "learning_batch_id":batch["batch_id"],
            })
            try:
                routed=self.route_finding(packet)
                routes.append({
                    "source_index":index,
                    "title":title,
                    "finding_id":packet.get("finding_id"),
                    "lead_rishi":routed.get("lead_rishi"),
                    "rishi_team":routed.get("rishi_team") or [],
                    "routed":bool(routed.get("routed")),
                    "next_action":"existing Rishi/BRAHMAGYAN research and cross-check",
                })
            except Exception as exc:
                errors.append({"source_index":index,"title":title,"error":f"{type(exc).__name__}: {exc}"})
        accepted=bool(routes) and not errors and all(x.get("routed") for x in routes)
        receipt=self.horses.receipt(
            batch["batch_id"],
            routed_count=sum(1 for x in routes if x.get("routed")),
            accepted=accepted,
            details={
                "source_count":batch.get("source_count"),
                "route_count":len(routes),
                "errors":errors,
                "rule":"clear only transient device batch/cache after this positive receipt",
            },
        )
        completed_curriculum=None
        if accepted and self.curriculum is not None and batch.get("curriculum_plan_id"):
            try:
                completed_curriculum=self.curriculum.complete(
                    batch["curriculum_plan_id"],batch["batch_id"],
                )
            except Exception as exc:
                errors.append({
                    "source_index":None,
                    "title":"curriculum completion",
                    "error":f"{type(exc).__name__}: {exc}",
                })
        if self.memory:
            self.memory.audit(
                "suryadev_horse_learning",
                "accepted" if accepted else "partial_or_failed",
                f"{batch['horse_id']}:{batch['batch_id']}:{len(routes)} routes:{len(errors)} errors",
            )
        return {
            "batch_id":batch["batch_id"],
            "batch_sha256":batch["batch_sha256"],
            "horse_id":batch["horse_id"],
            "node_id":batch["node_id"],
            "source_count":batch["source_count"],
            "routes":routes,
            "errors":errors,
            "receipt":receipt,
            "cleanup_allowed":bool(receipt.get("cleanup_allowed")),
            "curriculum_completed":None if completed_curriculum is None else {
                "plan_id":completed_curriculum.get("plan_id"),
                "status":completed_curriculum.get("status"),
            },
            "architecture":"SURYDEV horse -> existing BRAHMA intake -> existing subject Rishis",
        }

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
                "authentication_handoff": "owner_permission_required_per_checkpoint",
                "auth_permission_scope": "one_time_job_origin_method",
                "captcha_or_liveness": "owner-approved_human_handoff_only",
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
            "suryadev_horse_id": packet.get("horse_id"),
            "suryadev_horse_name": packet.get("horse_name"),
            "suryadev_node_id": packet.get("node_id"),
            "suryadev_learning_batch_id": packet.get("learning_batch_id"),
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
            "capabilities": list(self.CAPABILITIES)+[
                "seven_horse_device_fleet","multi_device_learning","edge_cache_ack_cleanup",
            ],
            "job_types": sorted(self.JOB_TYPES),
            "jobs": jobs,
            "reports": reports,
            "runs_on_external_node": True,
            "transports": ["trusted_lan", "verified_usb_packet"],
            "raw_media_to_krishna": False,
            "routes_findings_to_brahmagyan": self.brahma is not None,
            "seven_horses": self.horses.status(),
            "curriculum": self.curriculum.status() if self.curriculum is not None else {
                "available":False,
                "reason":"BRAHMA/BRAHMAGYAN/Garuda curriculum dependencies not bound",
            },
            "release_authority": False,
            "human_verification_handoff": True,
            "authentication_permission": "explicit owner approval required for every checkpoint",
            "auth_approval_scope": "single agent + job + origin + method; one-time; expires",
            "ready": True,
        }
