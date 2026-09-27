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
import urllib.parse

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
    PODCAST_NODE_NAME = "SURYADEV SHRAVANA — Podcast Gurukul"
    PODCAST_RISHI = "shravana"
    PODCAST_QUEUE_LIMIT = 30
    PODCAST_QUEUE_SEED = (
        "The Daily","Crime Junkie","Dateline NBC","Up First from NPR","REAL AF with Andy Frisella",
        "The Joe Rogan Experience","Pardon My Take","Mick Unplugged","Live Free with Josh Howerton",
        "The Dylan Gemelli Podcast","Good Hang with Amy Poehler","Morbid","Pod Save America",
        "The Learning Leader Show With Ryan Hawk","In The Dark","Tomorrow, Today","The Bill Simmons Podcast",
        "Coffeez with Joe Shalaby","The Shawn Ryan Show","The Team House","The Megyn Kelly Show",
        "The Mel Robbins Podcast","20/20","We're Out of Time","Unblinded with Sean Callagy",
        "The Ezra Klein Show","The Level Up Podcast w/ Paul Alex","Founder's Story","Notes from the Edge",
        "Bred To Lead | With Dr. Jake Tayler Jacobs",
    )

    def __init__(self, state_root, *, brahma=None, council=None, ui_reviewer=None, memory=None):
        self.root = Path(state_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.jobs_dir = self.root / "jobs"
        self.reports_dir = self.root / "reports"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = self.root / "suryadev-ledger.jsonl"
        self.device_file = self.root / "ipad-learning-nodes.json"
        self.alert_ledger = self.root / "ipad-node-alerts.jsonl"
        self.podcast_ledger = self.root / "podcast-learning.jsonl"
        self.podcast_queue_file = self.root / "podcast-top30.json"
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

    @staticmethod
    def _load_object(path):
        if not path.exists():
            return {}
        data=json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data,dict):
            raise RuntimeError(f"invalid SURYDEV state file: {path.name}")
        return data

    @staticmethod
    def _save_object(path,data):
        tmp=path.with_suffix(path.suffix+".tmp")
        tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
        tmp.replace(path)

    @staticmethod
    def _youtube_url(value):
        value=str(value or "").strip()
        return bool(re.match(r"^https://(?:www\.)?(?:youtube\.com|youtu\.be)/",value,re.I))

    def podcast_queue(self):
        if self.podcast_queue_file.exists():
            try:
                data=self._load_object(self.podcast_queue_file)
                items=list(data.get("items") or [])[:self.PODCAST_QUEUE_LIMIT]
                if items:
                    return {**data,"items":items,"count":len(items)}
            except Exception:
                pass
        now=time.time()
        items=[
            {
                "rank":i+1,
                "show":name,
                "youtube_search":"https://www.youtube.com/results?search_query="+
                    urllib.parse.quote_plus(name+" full podcast episode"),
                "approved":True,
            }
            for i,name in enumerate(self.PODCAST_QUEUE_SEED)
        ]
        return {
            "schema":"krishna.suryadev.podcast-queue.v1",
            "node_name":self.PODCAST_NODE_NAME,
            "rishi":self.PODCAST_RISHI,
            "mode":"bootstrap-chart-snapshot",
            "scope_note":"Seed is a current chart snapshot for bootstrap only; Garudanetra refresh should reconcile Apple/Spotify regional charts before treating rank as global.",
            "source_refs":[
                "https://podcasts.apple.com/browse/top-charts/shows",
                "https://podcastcharts.byspotify.com/",
            ],
            "refreshed_at":now,
            "items":items,
            "count":len(items),
            "refresh_required":True,
        }

    def update_podcast_queue(self,items,*,source_refs=None,scope_note="",refreshed_by="garudanetra"):
        clean=[]
        for row in list(items or [])[:self.PODCAST_QUEUE_LIMIT]:
            if isinstance(row,str):
                row={"show":row}
            if not isinstance(row,dict):
                continue
            show=self._text(row.get("show") or row.get("name"),240)
            if not show:
                continue
            clean.append({
                "rank":len(clean)+1,
                "show":show,
                "youtube_url":self._text(row.get("youtube_url"),1600),
                "youtube_search":self._text(row.get("youtube_search"),1600),
                "approved":bool(row.get("approved",True)),
                "source":self._text(row.get("source"),300),
            })
        if not clean:
            raise ValueError("podcast queue requires at least one show")
        data={
            "schema":"krishna.suryadev.podcast-queue.v1",
            "node_name":self.PODCAST_NODE_NAME,
            "rishi":self.PODCAST_RISHI,
            "mode":"garudanetra-refreshed",
            "scope_note":self._text(scope_note,1200) or "Top podcast discovery is chart-derived and time/region sensitive.",
            "source_refs":[self._text(x,1600) for x in (source_refs or []) if str(x).strip()][:20],
            "refreshed_by":self._text(refreshed_by,120),
            "refreshed_at":time.time(),
            "items":clean,
            "count":len(clean),
            "refresh_required":len(clean)<self.PODCAST_QUEUE_LIMIT,
        }
        self._save_object(self.podcast_queue_file,data)
        return data

    def podcast_refresh_plan(self):
        return {
            "agent":"GARUDANETRA",
            "consumer":"SURYDEV SHRAVANA",
            "target_count":self.PODCAST_QUEUE_LIMIT,
            "queries":[
                "Apple Podcasts top shows current chart",
                "Spotify top podcasts current charts",
                "top long-form interview podcasts current",
                "top science technology business history podcasts current",
            ],
            "policy":[
                "rankings are time- and region-sensitive; preserve chart, region and retrieval date",
                "popularity is not evidence quality",
                "Shravana Rishi verifies learned factual claims independently",
                "YouTube playback is limited to approved podcast queue items",
            ],
        }

    def device_heartbeat(self,packet):
        packet=dict(packet or {})
        device_id=self._text(packet.get("device_id"),160)
        if not device_id:
            raise ValueError("device_id is required")
        now=time.time()
        battery=int(packet.get("battery_percent",-1))
        thermal=self._text(packet.get("thermal_state"),40).lower() or "unknown"
        network=bool(packet.get("network_online",False))
        foreground=str(packet.get("app_state") or "").lower()=="foreground"
        screen_awake=bool(packet.get("screen_awake",False))
        youtube=self._text(packet.get("youtube_url"),1600)
        devices=self._load_object(self.device_file)
        prior=dict(devices.get(device_id) or {})
        last_learning=float(prior.get("last_learning_at") or 0.0)
        row={
            "device_id":device_id,
            "node_name":self._text(packet.get("node_name"),160) or self.PODCAST_NODE_NAME,
            "device_role":"suryadev-ipad",
            "platform":self._text(packet.get("platform"),80) or "iPadOS",
            "hardware":self._text(packet.get("hardware"),120),
            "battery_percent":battery,
            "battery_state":self._text(packet.get("battery_state"),40),
            "thermal_state":thermal,
            "low_power_mode":bool(packet.get("low_power_mode",False)),
            "network_online":network,
            "screen_awake":screen_awake,
            "app_state":"foreground" if foreground else "background",
            "youtube_url":youtube,
            "youtube_title":self._text(packet.get("youtube_title"),500),
            "youtube_seconds":max(0.0,float(packet.get("youtube_seconds") or 0.0)),
            "free_storage_bytes":max(0,int(packet.get("free_storage_bytes") or 0)),
            "last_seen":now,
            "last_learning_at":last_learning,
            "krishna_link_green":True,
            "suryadev_working_green":bool(network and foreground and screen_awake and self._youtube_url(youtube)),
            "rishi_learning_green":bool(last_learning and now-last_learning<=180.0),
        }
        devices[device_id]=row
        self._save_object(self.device_file,devices)
        return {"ok":True,**row,"online":True}

    def device_status(self,device_id=None):
        devices=self._load_object(self.device_file)
        now=time.time()
        rows=[]
        for did,row in devices.items():
            x=dict(row)
            age=max(0.0,now-float(x.get("last_seen") or 0.0))
            x["age_seconds"]=round(age,1)
            x["online"]=age<=75.0
            x["krishna_link_green"]=x["online"]
            x["suryadev_working_green"]=bool(
                x["online"] and x.get("network_online") and x.get("screen_awake") and
                x.get("app_state")=="foreground" and self._youtube_url(x.get("youtube_url"))
            )
            learning_age=max(0.0,now-float(x.get("last_learning_at") or 0.0)) if x.get("last_learning_at") else None
            x["rishi_learning_green"]=bool(learning_age is not None and learning_age<=180.0 and x["online"])
            x["learning_age_seconds"]=None if learning_age is None else round(learning_age,1)
            rows.append(x)
        rows.sort(key=lambda x:x.get("last_seen") or 0,reverse=True)
        if device_id:
            for row in rows:
                if row.get("device_id")==device_id:
                    return row
            raise KeyError(device_id)
        return {
            "node_name":self.PODCAST_NODE_NAME,
            "rishi":self.PODCAST_RISHI,
            "devices":rows,
            "count":len(rows),
            "online":sum(1 for x in rows if x.get("online")),
        }

    def device_alert(self,packet):
        packet=dict(packet or {})
        device_id=self._text(packet.get("device_id"),160)
        if not device_id:
            raise ValueError("device_id is required")
        severity=self._text(packet.get("severity"),20).lower() or "warning"
        if severity not in {"info","notice","warning","error","critical"}:
            severity="warning"
        row={
            "schema":"krishna.suryadev.device-alert.v1",
            "alert_id":"SURYA-ALERT-"+uuid.uuid4().hex[:16],
            "device_id":device_id,
            "node_name":self._text(packet.get("node_name"),160) or self.PODCAST_NODE_NAME,
            "kind":self._text(packet.get("kind"),120) or "device.alert",
            "detail":self._text(packet.get("detail"),1200),
            "severity":severity,
            "battery_percent":int(packet.get("battery_percent",-1)),
            "thermal_state":self._text(packet.get("thermal_state"),40),
            "network_online":bool(packet.get("network_online",False)),
            "created_at":time.time(),
        }
        with self.alert_ledger.open("a",encoding="utf-8") as handle:
            handle.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")
        if self.memory:
            self.memory.audit(row["alert_id"],"suryadev_device_alert",f"{device_id}:{row['kind']}:{severity}")
        return row

    def podcast_learning(self,packet):
        packet=dict(packet or {})
        device_id=self._text(packet.get("device_id"),160)
        source_url=self._text(packet.get("source_url"),1600)
        title=self._text(packet.get("title"),500)
        caption=self._text(packet.get("visible_caption_text"),6000)
        if not device_id:
            raise ValueError("device_id is required")
        if not self._youtube_url(source_url):
            raise ValueError("SURYDEV iPad learning accepts YouTube podcast observations only")
        queue_show=self._text(packet.get("queue_show"),240)
        approved={str(x.get("show") or "").strip().lower() for x in self.podcast_queue().get("items") or [] if x.get("approved",True)}
        if not queue_show or queue_show.lower() not in approved:
            return {
                "accepted":False,
                "routed_to_rishi":False,
                "reason":"not_approved_top30_podcast_queue",
                "rishi":self.PODCAST_RISHI,
                "learning_green":False,
            }
        start=max(0.0,float(packet.get("start_seconds") or 0.0))
        end=max(start,float(packet.get("end_seconds") or start))
        event={
            "schema":"krishna.suryadev.podcast-observation.v1",
            "device_id":device_id,
            "node_name":self.PODCAST_NODE_NAME,
            "rishi":self.PODCAST_RISHI,
            "source_url":source_url,
            "title":title,
            "queue_show":queue_show,
            "start_seconds":start,
            "end_seconds":end,
            "caption_available":bool(caption),
            "caption_text":caption,
            "raw_media_included":False,
            "created_at":time.time(),
        }
        with self.podcast_ledger.open("a",encoding="utf-8") as handle:
            handle.write(json.dumps(event,ensure_ascii=False,separators=(",",":"))+"\n")
        if len(re.sub(r"\W+","",caption))<40:
            return {
                "accepted":True,
                "routed_to_rishi":False,
                "reason":"not_enough_caption_evidence",
                "rishi":self.PODCAST_RISHI,
                "learning_green":False,
            }
        packet_out=self.distilled_finding(
            job_id="IPAD-"+device_id,
            project="BRAHMAGYAN",
            topic=f"Podcast learning for Rishi Shravana — approved show {queue_show}: {title}",
            finding=caption,
            modality="transcript",
            evidence=[{
                "source_ref":source_url,
                "source_type":"youtube_visible_caption",
                "sha256":self._digest(caption),
                "note":f"Foreground podcast observation {start:.1f}s-{end:.1f}s on {self.PODCAST_NODE_NAME}.",
            }],
            confidence=0.55,
            timestamps=[f"{start:.1f}-{end:.1f}s"],
            source_ref=source_url,
        )
        routed=self.route_finding(packet_out)
        devices=self._load_object(self.device_file)
        state=dict(devices.get(device_id) or {})
        state["last_learning_at"]=time.time()
        state["last_learning_title"]=title
        state["last_learning_finding_id"]=packet_out["finding_id"]
        state["rishi_learning_green"]=bool(routed.get("routed"))
        devices[device_id]=state
        self._save_object(self.device_file,devices)
        return {
            "accepted":True,
            "routed_to_rishi":bool(routed.get("routed")),
            "lead_rishi":routed.get("lead_rishi"),
            "rishi_team":routed.get("rishi_team") or [],
            "rishi":self.PODCAST_RISHI,
            "finding_id":packet_out["finding_id"],
            "learning_green":bool(routed.get("routed")),
            "verification_required":True,
            "garudanetra_followup_recommended":True,
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
                "ipad_podcast_learning_node","always_on_foreground_watchdog","device_health_heartbeat",
                "podcast_top30_queue","shravana_rishi_learning","garudanetra_followup_research",
            ],
            "podcast_gurukul":{
                "name":self.PODCAST_NODE_NAME,
                "rishi":self.PODCAST_RISHI,
                "device_status":self.device_status(),
                "queue":self.podcast_queue(),
            },
            "job_types": sorted(self.JOB_TYPES),
            "jobs": jobs,
            "reports": reports,
            "runs_on_external_node": True,
            "transports": ["trusted_lan", "verified_usb_packet"],
            "raw_media_to_krishna": False,
            "routes_findings_to_brahmagyan": self.brahma is not None,
            "release_authority": False,
            "human_verification_handoff": True,
            "authentication_permission": "explicit owner approval required for every checkpoint",
            "auth_approval_scope": "single agent + job + origin + method; one-time; expires",
            "ready": True,
        }
