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
from threading import RLock

from .field_perception import FieldPerceptionPolicy
from .suryadev_capacity import machine_snapshot, capacity_decision, browser_policy, recovery_policy
from .suryadev_scheduler import slot_plan, media_speed_plan, source_adapter_policy, evidence_quality_gate
from .suryadev_ops import SuryadevOpsLog
from .suryadev_handoff import chandradev_handoff, simultaneous_lane_policy


class SuryadevAgent:
    VERSION = "suryadev-eye-ear-v2"
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
        "timestamped_transcript",
        "selected_visual_evidence",
        "server_ack_cleanup",
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
        self.receipts_dir = self.root / "learning-receipts"
        self.nodes_file = self.root / "device-nodes.json"
        self._node_lock = RLock()
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.receipts_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = self.root / "suryadev-ledger.jsonl"
        self.brahma = brahma
        self.council = council
        self.ui_reviewer = ui_reviewer
        self.memory = memory
        self.ops = SuryadevOpsLog(self.root / "ops")

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

    def _load_nodes(self):
        if not self.nodes_file.is_file():
            return {}
        try:
            value = json.loads(self.nodes_file.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RuntimeError(f"SURYDEV node state unreadable: {type(exc).__name__}") from exc
        if not isinstance(value, dict):
            raise RuntimeError("SURYDEV node state must be a JSON object")
        return value

    def _save_nodes(self, rows):
        tmp = self.nodes_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.nodes_file)

    def device_heartbeat(self, payload):
        payload = dict(payload or {})
        device_id = self._text(payload.get("device_id"), 200)
        if not device_id:
            raise ValueError("device_id is required")
        now = time.time()
        row = {
            "device_id": device_id,
            "node_name": self._text(payload.get("node_name") or device_id, 200),
            "platform": self._text(payload.get("platform"), 100),
            "last_seen": now,
            "worker_running": bool(payload.get("worker_running", True)),
            "learning_state": self._text(payload.get("learning_state") or "idle", 80).lower(),
            "current_job_id": self._text(payload.get("current_job_id"), 200),
            "network_online": bool(payload.get("network_online", True)),
            "battery_percent": payload.get("battery_percent"),
            "charging": bool(payload.get("charging", False)),
            "thermal_state": self._text(payload.get("thermal_state") or "unknown", 60).lower(),
            "last_error": self._text(payload.get("last_error"), 1000),
            "cpu_percent": float(payload.get("cpu_percent") or 0),
            "ram_percent": float(payload.get("ram_percent") or 0),
            "gpu_percent": float(payload.get("gpu_percent") or 0),
            "vram_percent": float(payload.get("vram_percent") or 0),
            "network_percent": float(payload.get("network_percent") or 0),
            "active_workers": max(0, int(payload.get("active_workers") or 0)),
            "free_disk_gb": float(payload.get("free_disk_gb") or 0),
        }
        with self._node_lock:
            rows = self._load_nodes()
            previous = dict(rows.get(device_id) or {})
            previous.update(row)
            rows[device_id] = previous
            self._save_nodes(rows)
        learning_active = row["learning_state"] in {
            "watching", "listening", "capturing", "transcribing",
            "researching", "uploading", "awaiting_server_ack",
        }
        return {
            "accepted": True,
            "device_id": device_id,
            "server_link_green": True,
            "suryadev_working_green": bool(row["worker_running"] and row["network_online"] and not row["last_error"]),
            "learning_green": bool(learning_active and not row["last_error"]),
            "heartbeat_at": now,
            "stale_after_seconds": 150,
        }

    def adaptive_worker_plan(self, payload):
        payload=dict(payload or {})
        snap=machine_snapshot(
            cpu_percent=payload.get("cpu_percent",0),ram_percent=payload.get("ram_percent",0),
            gpu_percent=payload.get("gpu_percent",0),vram_percent=payload.get("vram_percent",0),
            network_percent=payload.get("network_percent",0),thermal_state=payload.get("thermal_state","unknown"),
            free_disk_gb=payload.get("free_disk_gb",0),
        )
        decision=capacity_decision(snap,payload.get("active_workers",0),max_workers=payload.get("max_workers",256))
        slots=slot_plan(
            requested=payload.get("requested_slots",50),active=payload.get("active_workers",0),
            resource_decision=decision,media_requested=payload.get("media_requested",0),
            media_cap=payload.get("media_cap"),
        )
        result={**decision,"snapshot":snap,"slots":slots,"browser":browser_policy(),
                "sources":source_adapter_policy(),"recovery":recovery_policy(),
                "parallel_lanes":simultaneous_lane_policy()}
        self.ops.write_status(state="running",capacity=result,active_workers=payload.get("active_workers",0),
                              current_job_id=payload.get("current_job_id",""))
        self.ops.emit("capacity_plan",action=decision.get("action"),slots=slots,snapshot=snap)
        return result

    def media_learning_plan(self, metrics):
        metrics=dict(metrics or {})
        speed=media_speed_plan(
            speech_density=metrics.get("speech_density",.5),
            technical_density=metrics.get("technical_density",.5),
            visual_change=metrics.get("visual_change",.5),
            transcript_confidence=metrics.get("transcript_confidence",.8),
            evidence_criticality=metrics.get("evidence_criticality",.5),
        )
        quality=evidence_quality_gate(
            authority=self._clamp(metrics.get("authority",.5)),
            relevance=self._clamp(metrics.get("relevance",.5)),
            independence=self._clamp(metrics.get("independence",.5)),
            transcript_confidence=self._clamp(metrics.get("transcript_confidence",.8)),
            contradiction_checked=bool(metrics.get("contradiction_checked")),
            timestamped=bool(metrics.get("timestamped")),
        )
        return {"speed":speed,"evidence_gate":quality,"sources":source_adapter_policy()}

    def visual_handoff(self, *, job_id, source_ref, reason, question="", timestamps=None,
                       transcript_confidence=1.0, visual_relevance=0.0):
        packet=chandradev_handoff(
            job_id=job_id,source_ref=source_ref,reason=reason,question=question,
            timestamps=timestamps,transcript_confidence=transcript_confidence,
            visual_relevance=visual_relevance,
        )
        self.ops.emit("chandradev_handoff",**packet)
        return packet

    def brahma_operational_status(self):
        return self.ops.brahma_status()

    def device_status(self, device_id=None):
        now = time.time()
        with self._node_lock:
            rows = self._load_nodes()
        out = []
        for value in rows.values():
            item = dict(value)
            age = max(0.0, now - float(item.get("last_seen") or 0))
            connected = age <= 150
            item["age_seconds"] = round(age, 1)
            item["connected"] = connected
            item["server_link_green"] = connected
            item["suryadev_working_green"] = bool(
                connected and item.get("worker_running") and item.get("network_online") and not item.get("last_error")
            )
            item["learning_green"] = bool(
                connected and item.get("learning_state") in {
                    "watching", "listening", "capturing", "transcribing",
                    "researching", "uploading", "awaiting_server_ack",
                } and not item.get("last_error")
            )
            out.append(item)
        out.sort(key=lambda x: float(x.get("last_seen") or 0), reverse=True)
        if device_id:
            found = next((x for x in out if x.get("device_id") == str(device_id)), None)
            if found is None:
                raise KeyError(device_id)
            return found
        return {
            "nodes": out,
            "count": len(out),
            "stale_after_seconds": 150,
            "truth_rule": "green requires a recent authenticated heartbeat; stale nodes are red",
        }

    def route_learning_bundle(self, bundle, *, device_id=""):
        """Validate and route one external learning bundle through existing BRAHMA/Rishis.

        This deliberately does not create a new learning authority. SURYDEV contributes
        bounded candidate evidence; BRAHMA/Rishi learning remains authoritative.
        A cleanup acknowledgement is issued only after every accepted chunk was routed.
        """
        bundle = dict(bundle or {})
        if bundle.get("schema") != "krishna.suryadev.learning-bundle.v1":
            raise ValueError("unsupported SURYDEV learning bundle schema")
        if bundle.get("raw_media_included") is not False:
            raise ValueError("raw media may not be transferred in a SURYDEV learning bundle")
        job_id = self._text(bundle.get("job_id"), 200)
        if not job_id:
            raise ValueError("learning bundle job_id is required")
        chunks = bundle.get("learning_chunks") or []
        visuals = bundle.get("visual_evidence") or []
        if not isinstance(chunks, list) or not isinstance(visuals, list):
            raise ValueError("learning_chunks and visual_evidence must be lists")
        if not chunks and not visuals:
            raise ValueError("learning bundle contains no evidence")
        if len(chunks) > 120 or len(visuals) > 120:
            raise ValueError("learning bundle exceeds bounded evidence limits")

        bundle_sha = self._digest(bundle)
        receipt_path = self.receipts_dir / f"{job_id}.json"
        if receipt_path.is_file():
            prior = json.loads(receipt_path.read_text(encoding="utf-8"))
            if prior.get("bundle_sha256") != bundle_sha:
                raise RuntimeError("different learning bundle already acknowledged for this job")
            return {**prior, "idempotent_replay": True}

        source = dict(bundle.get("source") or {})
        source_ref = self._text(source.get("url") or "", 2000)
        source_title = self._text(source.get("title") or "", 500)
        safe_visuals = []
        for visual in visuals:
            if not isinstance(visual, dict):
                continue
            sha = self._text(visual.get("sha256"), 80).lower()
            if sha and (len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha)):
                raise ValueError("selected visual evidence has invalid SHA-256")
            if visual.get("bytes") is not None or visual.get("base64") is not None:
                raise ValueError("selected visual evidence may contain metadata/hash only")
            safe_visuals.append({
                "sha256": sha,
                "subject": self._text(visual.get("subject"), 300),
                "timestamp": self._text(visual.get("timestamp"), 80),
                "timestamp_seconds": float(visual.get("timestamp_seconds") or 0),
                "reason": self._text(visual.get("reason"), 600),
                "research_question": self._text(visual.get("research_question"), 1200),
                "lab_relevance": bool(visual.get("lab_relevance", False)),
            })

        routed = []
        for index, chunk in enumerate(chunks[:120], 1):
            if not isinstance(chunk, dict):
                raise ValueError("learning chunk must be an object")
            text = self._text(chunk.get("text"), 8000)
            topic = self._text(chunk.get("topic") or source_title or "SURYDEV video learning", 1000)
            if not text:
                raise ValueError("learning chunk text is required")
            start = chunk.get("start_seconds")
            end = chunk.get("end_seconds")
            timestamps = []
            if start is not None:
                timestamps.append(f"start_seconds={float(start):.2f}")
            if end is not None:
                timestamps.append(f"end_seconds={float(end):.2f}")
            evidence = [{
                "source_ref": source_ref or f"suryadev-job:{job_id}",
                "source_type": "video_source",
                "sha256": "",
                "note": source_title,
            }]
            try:
                start_num = float(start) if start is not None else None
                end_num = float(end) if end is not None else None
            except (TypeError, ValueError):
                start_num = end_num = None
            for visual in safe_visuals:
                if not visual.get("sha256"):
                    continue
                vsec = float(visual.get("timestamp_seconds") or 0)
                if start_num is not None and end_num is not None and not (start_num - 60 <= vsec <= end_num + 60):
                    continue
                evidence.append({
                    "source_ref": f"suryadev-visual:{visual['sha256']}",
                    "source_type": "selected_visual_evidence",
                    "sha256": visual["sha256"],
                    "note": " | ".join(x for x in [
                        visual.get("timestamp"), visual.get("reason"), visual.get("research_question")
                    ] if x)[:1200],
                })
            packet = self.distilled_finding(
                job_id=job_id,
                project=self._text(bundle.get("project") or "KRISHNA", 200),
                topic=topic,
                finding=text,
                modality=self._text(chunk.get("modality") or "video_learning", 120),
                evidence=evidence[:40],
                confidence=self._clamp(chunk.get("confidence", 0.65)),
                timestamps=timestamps,
                source_ref=source_ref,
            )
            route = self.route_finding(packet)
            if not route.get("routed"):
                raise RuntimeError("BRAHMA did not accept SURYDEV learning chunk")
            routed.append({
                "chunk_index": index,
                "finding_id": packet.get("finding_id"),
                "lead_rishi": route.get("lead_rishi"),
                "rishi_team": route.get("rishi_team") or [],
            })

        if not routed and safe_visuals:
            # Visual-only sessions still create one bounded candidate so the relevant
            # Rishi can decide whether the frame warrants deeper research/lab work.
            questions = [x.get("research_question") for x in safe_visuals if x.get("research_question")]
            visual_text = (
                "Selected visual evidence was captured without reliable speech text. "
                "Do not infer unseen/spoken claims. Review the visual hashes/timestamps and research: "
                + "; ".join(questions[:12])
            )
            packet = self.distilled_finding(
                job_id=job_id,
                project=self._text(bundle.get("project") or "KRISHNA", 200),
                topic=self._text(source.get("subject") or source_title or "SURYDEV visual evidence", 1000),
                finding=visual_text,
                modality="visual_observation",
                evidence=[{
                    "source_ref": f"suryadev-visual:{x['sha256']}",
                    "source_type": "selected_visual_evidence",
                    "sha256": x["sha256"],
                    "note": " | ".join(y for y in [x.get("timestamp"), x.get("reason"), x.get("research_question")] if y)[:1200],
                } for x in safe_visuals if x.get("sha256")][:40],
                confidence=0.45,
                source_ref=source_ref,
            )
            route = self.route_finding(packet)
            if not route.get("routed"):
                raise RuntimeError("BRAHMA did not accept SURYDEV visual evidence")
            routed.append({
                "chunk_index": 0,
                "finding_id": packet.get("finding_id"),
                "lead_rishi": route.get("lead_rishi"),
                "rishi_team": route.get("rishi_team") or [],
            })

        receipt = {
            "schema": "krishna.suryadev.learning-receipt.v1",
            "receipt_id": "SURYA-ACK-" + uuid.uuid4().hex[:20],
            "job_id": job_id,
            "device_id": self._text(device_id, 200),
            "bundle_sha256": bundle_sha,
            "accepted_chunks": len(routed),
            "selected_visuals": len(safe_visuals),
            "routed": routed,
            "cleanup_authorized": True,
            "cleanup_rule": "external node may delete transient transcript/audio/video/frames only after verifying this bundle SHA-256",
            "created_at": time.time(),
        }
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
        if self.memory:
            self.memory.audit(
                "suryadev_learning_bundle", "acknowledged",
                f"{job_id}:{bundle_sha[:16]}:{len(routed)}",
            )
        return receipt

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
            "device_nodes": self.device_status(),
            "runs_on_external_node": True,
            "transports": ["trusted_lan", "verified_usb_packet"],
            "raw_media_to_krishna": False,
            "full_transcript_persistent": False,
            "selected_visual_transfer": "metadata/hash only unless separately approved",
            "server_ack_before_external_cleanup": True,
            "routes_findings_to_brahmagyan": self.brahma is not None,
            "release_authority": False,
            "human_verification_handoff": True,
            "authentication_permission": "explicit owner approval required for every checkpoint",
            "auth_approval_scope": "single agent + job + origin + method; one-time; expires",
            "ready": True,
        }
