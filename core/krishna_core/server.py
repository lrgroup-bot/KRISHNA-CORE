from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json, time, threading, base64, sys, uuid, os
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from .config import settings, RUNTIME_ROOT
from .orchestrator import Orchestrator
from .watcher import Watcher
from .pc_observer import PCObserver
from .device_pairing import DevicePairingStore
from .realtime_session import RealtimeSessionStore
from .plugin_runtime import PluginRegistry
from .plugin_executor import PluginExecutor
from .attachments import AttachmentStore
from .vision_adapter import VisionAdapter
from .native_voice import KrishnaVoiceStack
from .remote_access import PrivateRemotePolicy
from .worker_fabric import WorkerResilienceSupervisor
from .model_memory_governor import ModelMemoryGovernor
from .wearable_bridge import WearableBridge
from .specialist_library import SpecialistLibrary
from .runtime_integrity import RuntimeIntegrity
from .requirements_ledger import RequirementsLedger
from .garudanetra_session import GarudanetraSessionManager
from .ui_guardian import UIGuardian, UIGuardianRegistry
from .narad.scheduler import NaradScheduler
from .autonomy_supervisor import AutonomySupervisor
from .specialist_team import SpecialistTeamPlanner
from .lan_discovery import LanDiscoveryService

orch = Orchestrator()
_pairing = DevicePairingStore(Path(settings.db_path).resolve().parent / ".krishna_state")
_sessions = RealtimeSessionStore(Path(settings.db_path).resolve().parent / ".krishna_state")
_plugins = PluginRegistry(Path(settings.db_path).resolve().parent / ".krishna_state")
_plugin_executor = PluginExecutor(_plugins)
_attachments = AttachmentStore(Path(settings.db_path).resolve().parent / ".krishna_state")
_vision = VisionAdapter()
_voice = KrishnaVoiceStack(lambda event: orch.handle_event("wakeword","krishna_detected","Local wake word Krishna detected",severity="notice",project="system",payload=event))
_remote_policy = PrivateRemotePolicy()
_model_memory = ModelMemoryGovernor()
_wearables = WearableBridge(Path(settings.db_path).resolve().parent / ".krishna_state" / "wearables.json")
_worker_resilience = WorkerResilienceSupervisor(
    orch.agi.workers, interval=5,
    on_event=lambda event: orch.handle_event("worker_resilience",event.get("event","worker_event"),json.dumps(event),
                                             severity="critical" if event.get("event")=="quarantined" else "notice",
                                             project="system",payload=event),
)
_worker_resilience.start()
_specialists = SpecialistLibrary(Path(settings.db_path).resolve().parent / ".krishna_state", Path(__file__).resolve().parents[2] / "external" / "agency-agents")
_integrity = RuntimeIntegrity(RUNTIME_ROOT)
_requirements = RequirementsLedger()
_lan_discovery = None
def _remember_garudanetra_session(snapshot):
    project=str(snapshot.get("project") or "KRISHNA")
    sid=str(snapshot.get("session_id") or "")
    lesson=(snapshot.get("visible_text") or "")[:5000] or ("Garudanetra task-memory session "+sid)
    evidence=[{"url":snapshot.get("current_url"),"title":snapshot.get("title"),
               "findings":snapshot.get("findings") or [],"downloads":snapshot.get("downloads") or [],
               "console":snapshot.get("console") or [],"network":snapshot.get("network") or []}]
    try:
        orch.gyan_propose(project,"garudanetra-task-memory:"+sid,lesson,evidence,0.8,
                          "garudanetra_task_memory",False,"evidence",
                          {"session_id":sid,"mode":snapshot.get("mode"),"url":snapshot.get("current_url")})
        for finding in snapshot.get("findings") or []:
            if finding.get("kind")!="selector_recovered" or not finding.get("candidate_skill"):
                continue
            skill=finding["candidate_skill"]
            compiled=orch.agi.skills.compile_candidate(
                "garudanetra-selector-recovery",
                [{"action":"browser_selector_recovery","strategy":skill.get("strategy"),"payload":skill.get("payload") or {}}],
                project=project,
                evidence=[{"session_id":sid,"url":snapshot.get("current_url"),"finding":finding}],
            )
            orch.gyan_propose(project,"garudanetra-browser-skill",
                              "Recovered browser locator candidate: "+json.dumps(skill,ensure_ascii=False),
                              [{"session_id":sid,"url":snapshot.get("current_url"),"finding":finding,
                                "compiled_skill":{"path":compiled.get("path"),"digest":compiled.get("digest"),"status":compiled.get("status")}}],
                              0.75,"garudanetra_recovery",False,"skill",
                              {"session_id":sid,"recovery_source":skill.get("source"),"verification_required":True,
                               "compiled_skill_path":compiled.get("path"),"compiled_skill_digest":compiled.get("digest")})
    except Exception as exc:
        orch.memory.audit("garudanetra_task_memory","proposal_failed",f"{type(exc).__name__}: {exc}")
_garudanetra = GarudanetraSessionManager(RUNTIME_ROOT,on_closed=_remember_garudanetra_session)
_ui_registry = UIGuardianRegistry(Path(settings.db_path).resolve().parent / ".krishna_state" / "ui-guardian-registry.json")
_ui_guardian = UIGuardian(orch.browser, _ui_registry, Path(settings.db_path).resolve().parent / "reports" / "ui-guardian")
_narad_scheduler = NaradScheduler(orch.agi.narad)
_narad_scheduler.start()
_autonomy = AutonomySupervisor(orch)
_autonomy.start()
_team_planner = SpecialistTeamPlanner(_specialists)
try:
    if _specialists.source_root.exists():
        _specialists.index()
except Exception as exc:
    print(f"[KRISHNA] specialist index startup warning: {type(exc).__name__}: {exc}", file=sys.stderr)
started = time.time()
activity = {"current_activity": "Idle", "updated": time.strftime("%Y-%m-%d %H:%M:%S"), "recent": []}
_mobile_lock = threading.RLock()
_mobile_link = {
    "device": None,
    "last_seen": 0.0,
    "last_path": None,
    "requests": 0,
}


def touch_mobile(device, path):
    if not device:
        return
    now = time.time()
    with _mobile_lock:
        _mobile_link["device"] = str(device)[:128]
        _mobile_link["last_seen"] = now
        _mobile_link["last_path"] = str(path)[:256]
        _mobile_link["requests"] += 1


def mobile_link_state():
    now = time.time()
    with _mobile_lock:
        last_seen = float(_mobile_link["last_seen"] or 0.0)
        age = None if not last_seen else max(0.0, now - last_seen)
        return {
            **_mobile_link,
            "connected": bool(last_seen and age <= 20.0),
            "age_seconds": None if age is None else round(age, 1),
        }
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    _BUNDLE_ROOT = Path(sys._MEIPASS)
    DASHBOARD = _BUNDLE_ROOT / "dashboard.html"
    WEB_VALIDATION = _BUNDLE_ROOT / "web_validation.html"
    AVATAR_B64 = _BUNDLE_ROOT / "avatar" / "krishna_child_360.webp.b64"
    AVATAR_GLB = _BUNDLE_ROOT / "avatar" / "krishna.glb"
else:
    _CORE_ROOT = Path(__file__).resolve().parents[1]
    _REPO_ROOT = Path(__file__).resolve().parents[2]
    DASHBOARD = _CORE_ROOT / "dashboard.html"
    WEB_VALIDATION = _CORE_ROOT / "web_validation.html"
    AVATAR_B64 = _REPO_ROOT / "avatar" / "krishna_child_360.webp.b64"
    AVATAR_GLB = RUNTIME_ROOT / "dashboard" / "assets" / "avatar" / "krishna.glb"


def avatar_360_bytes():
    try:
        return base64.b64decode(AVATAR_B64.read_text(encoding="utf-8").strip(), validate=True)
    except Exception:
        return b""


def latest_e_drive_audit():
    reports=RUNTIME_ROOT/"reports"
    try:
        files=sorted(reports.glob("e-drive-audit-*.json"),key=lambda p:p.stat().st_mtime,reverse=True)
        if not files:return {"available":False,"findings":[],"finding_count":0}
        raw=json.loads(files[0].read_text(encoding="utf-8-sig"))
        findings=list(raw.get("findings") or [])
        return {"available":True,"path":str(files[0]),"generated_at":raw.get("generated_at"),
                "finding_count":len(findings),"findings":findings[:50]}
    except Exception as exc:
        return {"available":False,"error":f"{type(exc).__name__}: {exc}","findings":[],"finding_count":0}


def mark(event, detail=""):
    now = time.strftime("%H:%M:%S")
    activity["current_activity"] = detail or event
    activity["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    activity["recent"].insert(0, {"time": now, "event": event + ((": " + detail) if detail else "")})
    del activity["recent"][30:]


def on_transition(transition):
    target = transition["target"]
    status = "UP" if transition["to"] else "DOWN"
    mark("WATCHER TRANSITION", f"{target} -> {status}")
    orch.memory.remember("system", "watcher_transition", f"{target} -> {status}", transition)
    orch.memory.audit("watcher", "transition", json.dumps(transition))
    orch.handle_event(
        "pc_watcher", "service_recovered" if transition["to"] else "service_down",
        f"{target} -> {status}", severity="notice" if transition["to"] else "critical",
        project="system", payload=transition,
    )


watcher = Watcher(on_transition=on_transition)
watcher.start()

def on_pc_event(event):
    orch.handle_event(
        event.get("source", "pc_observer"),
        event.get("kind", "event"),
        event.get("detail", ""),
        severity=event.get("severity", "info"),
        project=event.get("project", "system"),
        payload=event.get("payload") or {},
    )
    if event.get("kind")=="memory_pressure":
        percent=float((event.get("payload") or {}).get("percent") or 0)
        if percent>=90:
            def relieve():
                try:
                    result=_model_memory.relieve(percent,90)
                    orch.handle_event("model_memory_governor","models_unloaded" if result.get("acted") else "no_action",
                                      json.dumps(result),severity="warning",project="system",payload=result)
                except Exception as exc:
                    orch.handle_event("model_memory_governor","unload_failed",f"{type(exc).__name__}: {exc}",
                                      severity="warning",project="system")
            threading.Thread(target=relieve,name="krishna-model-memory-relief",daemon=True).start()

pc_observer = PCObserver(
    orch.projects.list,
    on_event=on_pc_event,
    cpu_budget_percent=orch.governor.cpu_budget,
    memory_budget_percent=orch.governor.memory_budget,
)
pc_observer.start()


class Handler(BaseHTTPRequestHandler):
    def _authorize(self):
        client_ip=self.client_address[0]
        remote_class=_remote_policy.classify(client_ip)
        local = client_ip in ("127.0.0.1", "::1")
        if not remote_class["allowed"]:
            self._json(403,{"error":"KRISHNA accepts only loopback/LAN or explicitly configured private-overlay clients","network":remote_class})
            return False
        host = urlparse("//" + self.headers.get("Host", "")).hostname
        if local and host not in ("localhost", "127.0.0.1", "::1", settings.host):
            self._json(403, {"error": "unrecognized local Host"})
            return False
        origin = self.headers.get("Origin")
        if origin:
            parsed = urlparse(origin)
            if parsed.scheme not in ("http", "https") or parsed.netloc != self.headers.get("Host"):
                self._json(403, {"error": "cross-origin control is not allowed"})
                return False
        device, token = self._device_auth()
        paired = bool(device and _pairing.verify(device, token))
        request_path = urlparse(self.path).path
        public = request_path in ("/health", "/api/mobile/pair/request") or request_path.startswith("/api/narad/webhook/")
        if not local and not paired and not public:
            self._json(401, {"error": "pairing required"})
            return False
        if not local and paired and not public and not _remote_policy.mobile_route_allowed(request_path):
            self._json(403, {"error": "paired remote devices are restricted to KRISHNA conversation/mobile APIs"})
            return False
        if paired:
            touch_mobile(device, self.path)
        return True

    def _dispatch(self, method):
        if not self._authorize():
            return
        try:
            return method()
        except (ValueError, TypeError) as exc:
            return self._json(400, {"error": str(exc)})
        except PermissionError as exc:
            return self._json(403, {"error": str(exc)})
        except KeyError as exc:
            return self._json(404, {"error": str(exc)})
        except RuntimeError as exc:
            return self._json(409, {"error": str(exc)})
        except Exception as exc:
            orch.memory.audit("server","unhandled_exception",f"{type(exc).__name__}: {exc}")
            return self._json(500, {"error": "internal server error", "type": type(exc).__name__})

    def do_GET(self):
        return self._dispatch(self._get)

    def do_POST(self):
        return self._dispatch(self._post)

    def _json(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _binary(self, code, body, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _binary_nostore(self, code, body, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, code, text):
        b = text.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _body(self):
        n = int(self.headers.get("Content-Length", "0"))
        if n < 0 or n > 36 * 1024 * 1024:
            raise ValueError("request body exceeds 36 MB")
        body = json.loads(self.rfile.read(n) or b"{}")
        if not isinstance(body, dict):
            raise ValueError("request body must be a JSON object")
        return body

    def _device_auth(self):
        device = self.headers.get("X-Krishna-Device", "").strip()
        auth = self.headers.get("Authorization", "")
        token = auth[7:].strip() if auth.startswith("Device ") else ""
        return device, token

    def _get(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path in ("/", "/dashboard"):
            ui = WEB_VALIDATION if WEB_VALIDATION.exists() else DASHBOARD
            return self._html(200, ui.read_text(encoding="utf-8"))
        if path in ("/web", "/web-test", "/validation"):
            if not WEB_VALIDATION.exists():
                return self._json(404, {"error": "web validation UI unavailable"})
            return self._html(200, WEB_VALIDATION.read_text(encoding="utf-8"))
        if path == "/api/avatar.glb":
            if not AVATAR_GLB.is_file():return self._json(404,{"error":"private krishna.glb unavailable"})
            return self._binary(200,AVATAR_GLB.read_bytes(),"model/gltf-binary")
        if path == "/api/avatar360":
            body = avatar_360_bytes()
            if not body:
                return self._json(404, {"error": "avatar asset unavailable"})
            return self._binary(200, body, "image/webp")
        if path == "/api/attachments":
            chat_id=(query.get("chat_id") or [""])[0].strip()
            if not chat_id:return self._json(400,{"error":"chat_id is required"})
            return self._json(200,{"attachments":_attachments.list(chat_id)})
        if path == "/api/vision/status":
            return self._json(200,_vision.status())
        if path == "/api/voice/status":
            return self._json(200,_voice.status())
        if path == "/api/garuda/status":
            return self._json(200, orch.garuda_status())
        if path == "/api/garudanetra/sessions":
            return self._json(200, _garudanetra.status())
        if path == "/api/ui-guardian/registry":
            project=(query.get("project") or [None])[0]
            return self._json(200,_ui_registry.list(project))
        if path == "/api/garudanetra/session":
            sid=(query.get("id") or [""])[0].strip()
            if not sid:return self._json(400,{"error":"id is required"})
            return self._json(200,_garudanetra.status(sid))
        if path == "/api/garudanetra/frame":
            sid=(query.get("id") or [""])[0].strip()
            if not sid:return self._json(400,{"error":"id is required"})
            frame=_garudanetra.frame(sid)
            if not frame:return self._json(404,{"error":"frame not available yet"})
            return self._binary_nostore(200,frame,"image/png")
        if path == "/api/commitments/resume":
            project=(query.get("project") or [None])[0]
            return self._json(200,orch.resume_unfinished_work(project))
        if path == "/api/software-factory/workers/status":
            return self._json(200,orch.ephemeral_worker_status())
        if path == "/api/kabach/projects":
            return self._json(200,orch.protect_registered_projects())
        if path == "/api/commitments":
            project=(query.get("project") or [None])[0]
            return self._json(200,orch.commitments_status(project))
        if path == "/api/autonomy/status":
            return self._json(200,_autonomy.status())
        if path == "/api/models":
            project=(query.get("project") or ["KRISHNA"])[0]
            try:return self._json(200,orch.model_pool(project))
            except KeyError:return self._json(404,{"error":"project not registered"})
        if path == "/api/models/gateways":
            return self._json(200,orch.model_gateway.list())
        if path == "/api/secure-vault/status":
            return self._json(200,orch.secure_vault.list())
        if path == "/api/gyan-bhandar/archive/status":
            return self._json(200,orch.gyan_archive_status())
        if path == "/api/gyan-bhandar/pending":
            project=(query.get("project") or [None])[0]
            try:return self._json(200,orch.gyan_pending(project,100))
            except KeyError:return self._json(404,{"error":"project not registered"})
        if path == "/api/gyan-bhandar/inventory":
            project=(query.get("project") or ["KRISHNA"])[0].strip() or "KRISHNA"
            try:return self._json(200,orch.gyan_inventory(project))
            except KeyError:return self._json(404,{"error":"project not registered"})
        if path == "/api/gyan-bhandar/theory":
            project=(query.get("project") or ["KRISHNA"])[0].strip() or "KRISHNA"; topic=(query.get("topic") or [""])[0].strip()
            if not topic:return self._json(400,{"error":"topic is required"})
            try:return self._json(200,orch.gyan_theory(project,topic,25))
            except KeyError:return self._json(404,{"error":"project not registered"})
        if path == "/api/gyan-bhandar":
            project=(query.get("project") or ["KRISHNA"])[0].strip() or "KRISHNA"
            topic=(query.get("topic") or [None])[0]
            verified=str((query.get("verified") or ["0"])[0]).lower() in {"1","true","yes"}
            memory_kind=(query.get("kind") or [None])[0]
            include_superseded=str((query.get("include_superseded") or ["0"])[0]).lower() in {"1","true","yes"}
            try:return self._json(200,{"agent":"Gyan-Bhandar","project":project,
                "learnings":orch.gyan_recall(project,topic,100,verified,memory_kind,include_superseded)})
            except KeyError:return self._json(404,{"error":"project not registered"})
        if path == "/api/agi/status":
            return self._json(200, orch.agi_status())
        if path == "/api/runtime/integrity":
            return self._json(200, _integrity.status())
        if path == "/api/runtime/audit":
            return self._json(200, latest_e_drive_audit())
        if path == "/api/requirements":
            q=(query.get("q") or [""])[0]
            return self._json(200, _requirements.search(q) if q else _requirements.snapshot())
        if path == "/api/narad/status":
            return self._json(200, {**orch.agi.narad.status(),"scheduler":_narad_scheduler.status()})
        if path == "/api/narad/workflows":
            return self._json(200, {"workflows":[w.as_dict() for w in orch.agi.narad.workflows.values()]})
        if path == "/api/narad/history":
            limit=max(1,min(int((query.get("limit") or ["100"])[0]),500))
            return self._json(200, {"history":orch.agi.narad.history[-limit:]})
        if path == "/api/narad/connections":
            return self._json(200,orch.agi.narad_credentials.list())
        if path == "/api/narad/dead-letters":
            return self._json(200,orch.agi.narad.dead_letter_status())
        if path == "/api/narad/scheduler":
            return self._json(200,_narad_scheduler.status())
        if path == "/api/intelligence/status":
            return self._json(200, {
                "codebase_memory":orch.agi.code_intelligence.status(),
                "graft":orch.agi.graft.status(),
                "specialists":orch.agi.specialists.list(),
                "context_governor":{"max_items":orch.agi.context.max_items,"max_chars":orch.agi.context.max_chars},
                "media":orch.agi.media.status(),
            })
        if path in ("/health", "/api/status"):
            return self._json(200, {
                "ok": True,
                "core": "ONLINE",
                "watcher": watcher.snapshot(),
                "resources": orch.governor.snapshot(),
                "pc_observer": pc_observer.snapshot(),
                "mobile_connection": mobile_link_state(),
                "uptime_seconds": int(time.time() - started),
                "agi": orch.agi_status(),
                "deployment_integrity": _integrity.status(),
                "requirements": {"version":_requirements.snapshot()["version"],"count":_requirements.snapshot()["requirement_count"]},
            })
        if path == "/api/dashboard":
            return self._json(200, {
                "active": True,
                "core": "ONLINE",
                "watcher": watcher.snapshot(),
                "resources": orch.governor.snapshot(),
                "pc_observer": pc_observer.snapshot(),
                "neural": orch.neural_state(),
                "current_activity": activity["current_activity"],
                "updated": activity["updated"],
                "recent": activity["recent"],
                "mobile_connection": mobile_link_state(),
                "uptime_seconds": int(time.time() - started),
                "deployment_integrity": _integrity.status(),
            })
        if path == "/api/mobile/connection":
            return self._json(200, {**mobile_link_state(),"remote_policy":_remote_policy.status()})
        if path == "/api/mobile/pair/pending":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"pairing approvals are visible only on KRISHNA PC"})
            return self._json(200,{**_pairing.pending(),"paired":_pairing.paired()})
        if path == "/api/remote/status":
            remote=_remote_policy.status()
            remote["lan_discovery"]=_lan_discovery.status() if _lan_discovery else {"running":False,"policy":"enable KRISHNA_LAN_DISCOVERY=1 with a LAN-reachable Core bind"}
            return self._json(200,remote)
        if path == "/api/resilience/status":
            return self._json(200,{"worker_supervisor":_worker_resilience.status(),"model_memory":_model_memory.status()})
        if path in ("/api/wearables","/api/wearables/status"):
            return self._json(200,_wearables.status())
        if path == "/api/mobile/resume":
            device, token = self._device_auth()
            if not _pairing.verify(device, token):
                return self._json(401, {"error": "pairing required"})
            seq = int((query.get("after") or [0])[0])
            return self._json(200, {"ok": True, "events": _sessions.after(device, seq)})
        if path == "/api/capabilities":
            return self._json(200, {
                "operating_loop": [
                    "observe", "understand", "investigate", "research",
                    "plan", "act", "shadow_test", "verify", "review", "learn"
                ],
                "capabilities": [
                    "project_registry",
                    "repository_index",
                    "project_graph",
                    "evidence_engine",
                    "hypothesis_investigation",
                    "persistent_incident_memory",
                    "knowledge_ingestion",
                    "registered_action_registry",
                    "shadow_workspace",
                    "shadow_repair_pipeline",
                    "verification_gates",
                    "verification_review",
                    "resource_governor",
                    "privacy_aware_model_routing",
                    "chromium_ui_inspection",
                    "garudanetra_private_live_browser",
                    "garudanetra_owner_takeover_stream",
                    "garudanetra_task_memory_mode",
                    "garudanetra_persistent_workspace_mode",
                    "garudanetra_self_healing_selector_recovery",
                    "garudanetra_candidate_skill_compilation",
                    "ui_guardian_viewport_matrix",
                    "gui_registry_stable_candidate_experimental_rejected",
                    "github_repository_research",
                    "goal_completion_evaluation",
                    "recovery_ladder",
                    "defensive_security_scan",
                    "watcher_transitions",
                    "neural_action_graph",
                    "pc_resource_observer",
                    "registered_project_change_observer",
                    "mobile_event_bridge",
                    "mobile_zero_code_client_hash_pairing",
                    "lan_zero_code_core_discovery",
                    "child_krishna_360_avatar",
                    "mobile_pc_remote_control",
                    "private_overlay_remote_access_policy",
                    "wearable_capability_registry",
                    "wearable_bridge_verified_capabilities",
                    "phone_camera_to_local_vision_bridge",
                    "bluetooth_audio_os_bridge",
                    "persistent_project_chats",
                    "local_attachment_vision_reasoning",
                    "local_odia_indicconformer_stt",
                    "local_odia_indic_tts",
                    "openwakeword_krishna_wake_service",
                    "windows_conversation_console",
                    "on_demand_skill_runtime",
                    "untrusted_content_boundary",
                    "specialist_permission_manifests",
                    "agi_policy_kernel",
                    "independent_critic_verifier",
                    "unified_memory_fabric",
                    "gyan_typed_memory_categories",
                    "gyan_learning_supersession",
                    "gyan_provenance_inventory",
                    "skill_compiler",
                    "benchmark_lab",
                    "native_automation_bus",
                    "narad_workflow_runtime",
                    "narad_schedule_trigger",
                    "narad_webhook_gateway",
                    "narad_dead_letter_retry",
                    "narad_secret_reference_vault",
                    "windows_dpapi_secret_vault",
                    "encrypted_free_only_model_gateway",
                    "protected_archive_project_roles",
                    "safe_unattended_commitment_supervisor",
                    "crash_loop_backoff_quarantine",
                    "critical_ram_model_unload",
                    "curated_specialist_team_planner",
                    "independent_critic_verifier_flow",
                    "codebase_memory_adapter",
                    "graft_memory_adapter",
                    "specialist_registry",
                    "context_governor",
                    "openmontage_media_boundary",
                    "isolated_worker_fabric",
                    "creator_provider_fabric",
                    "revenue_engine_adapters",
                ],
                "mutating_actions_enabled": settings.allow_actions,
            })
        if path == "/api/projects":
            return self._json(200, {"projects": orch.projects.list()})
        if path == "/api/plugins":
            return self._json(200, {"plugins": _plugins.list()})
        if path == "/api/specialists":
            return self._json(200, {**_specialists.status(),"curated_team":_team_planner.status()})
        if path == "/api/specialist-teams":
            return self._json(200,_team_planner.status())
        if path == "/api/skills":
            project = (query.get("project") or [None])[0]
            return self._json(200, orch.skill_status(project))
        if path == "/api/actions":
            project = (query.get("project") or [None])[0]
            return self._json(200, {"actions": orch.actions.list(project)})
        if path == "/api/resources":
            return self._json(200, orch.governor.snapshot())
        if path == "/api/tasks":
            project = (query.get("project") or [None])[0]
            limit_raw = (query.get("limit") or ["100"])[0]
            try:
                limit = max(1, min(int(limit_raw), 500))
            except (TypeError, ValueError):
                return self._json(400, {"error": "limit must be an integer"})
            tasks = orch.task_ledger.list_tasks(project=project, limit=limit)
            return self._json(200, {"tasks": tasks, "active": [t for t in tasks if t.get("status") in {"queued","running","verifying","waiting_approval"}]})
        if path in ("/api/core/neural-state", "/api/neural/state"):
            return self._json(200, orch.neural_state())
        if path == "/api/core/state":
            current = activity["current_activity"]
            return self._json(200, {
                "operator": {
                    "avatar_state": "FLUTE" if current == "Idle" else "WORKING",
                    "current": {"task": current},
                    "updated": activity["updated"],
                },
                "neural": orch.neural_state(),
                "pc_observer": pc_observer.snapshot(),
            })
        if path == "/api/chats":
            project = (query.get("project") or [None])[0]
            return self._json(200, {"chats": orch.chats(project)})
        if path == "/api/chat/history":
            chat_id = (query.get("chat_id") or [""])[0]
            if not chat_id:
                return self._json(400, {"error": "chat_id is required"})
            return self._json(200, {
                "chat_id": chat_id,
                "messages": orch.chat_messages(chat_id, 100),
            })
        if path == "/api/project-graph":
            return self._json(200, orch.graph.snapshot())
        if path == "/api/recovery/ladder":
            return self._json(200, {"steps": orch.recovery.ladder()})
        if path == "/api/incidents":
            project = (query.get("project") or [None])[0]
            return self._json(200, {"incidents": orch.memory.incidents(project, 50)})
        return self._json(404, {"error": "not found"})

    def _post(self):
        post_path=urlparse(self.path).path
        try:
            data = self._body()
        except Exception as exc:
            return self._json(400, {"error": f"invalid json: {exc}"})

        if self.path == "/api/ui-guardian/register":
            item=_ui_registry.register(
                str(data.get("name") or "").strip(),
                str(data.get("project") or "KRISHNA").strip() or "KRISHNA",
                str(data.get("url") or "").strip(),
                str(data.get("state") or "candidate"),
                str(data.get("notes") or ""),
            )
            return self._json(201,item)

        if self.path == "/api/ui-guardian/evaluate":
            entry_id=str(data.get("entry_id") or "").strip()
            if not entry_id:return self._json(400,{"error":"entry_id is required"})
            mark("UI GUARDIAN",f"Evaluating {entry_id[:8]}")
            with orch.governor.job(timeout=0):
                result=_ui_guardian.evaluate_entry(entry_id)
            mark("UI GUARDIAN COMPLETE","PASS" if result.get("passed") else "DEFECTS FOUND")
            return self._json(200,result)

        if self.path == "/api/ui-guardian/transition":
            entry_id=str(data.get("entry_id") or "").strip()
            target=str(data.get("target") or "").strip()
            if not entry_id or not target:return self._json(400,{"error":"entry_id and target are required"})
            result=_ui_registry.transition(entry_id,target,verified=bool(data.get("verified",False)),notes=str(data.get("notes") or ""))
            return self._json(200,result)

        if self.path == "/api/garudanetra/session/start":
            project=str(data.get("project") or "KRISHNA").strip() or "KRISHNA"
            url=str(data.get("url") or "").strip()
            mode=str(data.get("mode") or "private").strip().lower()
            approved=bool(data.get("persistent_approved",False))
            out=_garudanetra.create(project,url,mode,persistent_approved=approved)
            mark("GARUDANETRA LIVE",f"{project}: {mode}: {url[:120]}")
            return self._json(201,out)

        if self.path == "/api/garudanetra/session/control":
            sid=str(data.get("session_id") or "").strip()
            action=str(data.get("action") or "").strip()
            if not sid or not action:return self._json(400,{"error":"session_id and action are required"})
            payload=dict(data.get("payload") or {})
            if action=="upload_attachment":
                chat_id=str(payload.get("chat_id") or "").strip();aid=str(payload.get("attachment_id") or "").strip()
                selector=str(payload.get("selector") or "").strip()
                if not chat_id or not aid or not selector:return self._json(400,{"error":"upload_attachment requires chat_id, attachment_id and selector"})
                try:
                    meta,path=_attachments.resolve(chat_id,aid)
                except KeyError:return self._json(404,{"error":"attachment not found"})
                action="upload";payload={"selector":selector,"path":str(path)}
            out=_garudanetra.command(sid,action,payload)
            if action=="stop":mark("GARUDANETRA STOPPED",sid[:8])
            elif action=="takeover":mark("GARUDANETRA OWNER CONTROL",sid[:8])
            elif action=="resume":mark("GARUDANETRA LIVE",sid[:8])
            return self._json(200,out)

        if post_path.startswith("/api/narad/webhook/"):
            token=post_path.rsplit("/",1)[-1].strip()
            if not token:return self._json(404,{"error":"webhook token is required"})
            try:return self._json(200,orch.agi.narad.handle_webhook(token,data))
            except PermissionError as exc:return self._json(403,{"error":str(exc)})

        if self.path == "/api/commitments/create":
            project=str(data.get("project") or "KRISHNA").strip() or "KRISHNA"
            title=str(data.get("title") or "").strip()
            if not title:return self._json(400,{"error":"title is required"})
            detail=data.get("detail") or {}
            if not isinstance(detail,dict):return self._json(400,{"error":"detail must be an object"})
            autonomy=data.get("autonomy")
            if autonomy is not None:
                if not isinstance(autonomy,dict):return self._json(400,{"error":"autonomy must be an object"})
                op=str(autonomy.get("operation") or "").strip().lower()
                if autonomy.get("enabled") and op not in _autonomy.SAFE_OPERATIONS:
                    return self._json(403,{"error":"autonomy operation is outside the non-mutating allowlist"})
                detail={**detail,"autonomy":autonomy}
            return self._json(201,orch.remember_commitment(project,title,detail,str(data.get("source") or "KRISHNA")))

        if self.path == "/api/commitments/update":
            cid=str(data.get("commitment_id") or "").strip();status=str(data.get("status") or "").strip()
            if not cid or not status:return self._json(400,{"error":"commitment_id and status are required"})
            return self._json(200,orch.complete_commitment(cid,status,data.get("detail")))

        if self.path == "/api/autonomy/tick":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"manual autonomy tick must run on KRISHNA PC"})
            return self._json(200,_autonomy.run_once())

        if self.path == "/api/narad/connections/register":
            try:
                return self._json(201,orch.agi.narad_credentials.register(
                    str(data.get("name") or ""),str(data.get("provider") or ""),str(data.get("env_var") or ""),
                    str(data.get("header") or "Authorization"),str(data.get("scheme") if data.get("scheme") is not None else "Bearer"),
                ))
            except ValueError as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/narad/connections/register-secret":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"encrypted secret registration must run on KRISHNA PC"})
            try:
                return self._json(201,orch.agi.narad_credentials.register_secret(
                    str(data.get("name") or ""),str(data.get("provider") or ""),str(data.get("secret") or ""),
                    str(data.get("header") or "Authorization"),str(data.get("scheme") if data.get("scheme") is not None else "Bearer"),
                ))
            except (ValueError,RuntimeError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/narad/connections/delete":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"credential deletion must run on KRISHNA PC"})
            cid=str(data.get("credential_id") or "").strip()
            if not cid:return self._json(400,{"error":"credential_id is required"})
            return self._json(200,{"deleted":orch.agi.narad_credentials.delete(cid)})

        if self.path == "/api/narad/webhooks/provision":
            wid=str(data.get("workflow_id") or "").strip()
            if not wid:return self._json(400,{"error":"workflow_id is required"})
            return self._json(201,orch.agi.narad.provision_webhook(wid))

        if self.path == "/api/narad/dead-letters/retry":
            letter_id=str(data.get("letter_id") or "").strip()
            if not letter_id:return self._json(400,{"error":"letter_id is required"})
            return self._json(200,orch.agi.narad.retry_dead_letter(letter_id,bool(data.get("approved",False))))

        if self.path == "/api/narad/scheduler/tick":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"manual scheduler tick must run on KRISHNA PC"})
            return self._json(200,orch.agi.narad.run_due())

        if self.path == "/api/narad/workflows/create":
            name=str(data.get("name") or "").strip()
            trigger=data.get("trigger") or {"type":"manual"}
            steps=data.get("steps") or []
            if not name or not isinstance(steps,list): return self._json(400,{"error":"name and steps are required"})
            return self._json(201,orch.agi.narad.create_workflow(name,trigger,steps,data.get("permissions") or []))

        if self.path == "/api/narad/workflows/promote":
            wid=str(data.get("workflow_id") or "").strip(); state=str(data.get("state") or "").strip()
            if not wid or not state:return self._json(400,{"error":"workflow_id and state are required"})
            return self._json(200,orch.agi.narad.promote(wid,state,verified=bool(data.get("verified",False))))

        if self.path == "/api/narad/workflows/execute":
            wid=str(data.get("workflow_id") or "").strip()
            if not wid:return self._json(400,{"error":"workflow_id is required"})
            return self._json(200,orch.agi.narad.execute(wid,data.get("context") or {},approved=bool(data.get("approved",False))))

        if self.path == "/api/mobile/pair/request":
            device = str(data.get("device_id", "")).strip()
            if not device:
                return self._json(400, {"error": "device_id required"})
            return self._json(200, _pairing.request(
                device,str(data.get("name","KRISHNA Mobile"))[:128],
                str(data.get("credential_sha256") or ""),
            ))

        if self.path == "/api/mobile/pair/approve":
            if self.client_address[0] not in ("127.0.0.1", "::1"):
                return self._json(403, {"error": "approval must be performed on KRISHNA PC"})
            try:
                result=_pairing.approve(str(data.get("request_id", "")))
                orch.handle_event("device_pairing","device_approved",result.get("device_id",""),severity="notice",project="system",payload={"mode":result.get("mode")})
                return self._json(200,result)
            except PermissionError as exc:
                return self._json(400, {"error": str(exc)})

        if self.path in ("/api/core/event", "/api/neural/event"):
            source = str(data.get("source", "unknown")).strip() or "unknown"
            kind = str(data.get("kind", "event")).strip() or "event"
            detail = str(data.get("detail", ""))
            severity = str(data.get("severity", "info"))
            project = str(data.get("project", "system"))
            return self._json(200, orch.handle_event(
                source, kind, detail, severity=severity, project=project,
                payload=data.get("payload") or {},
            ))

        if self.path in ("/api/mobile-log",):
            event = str(data.get("event", ""))
            return self._json(200, orch.handle_event(
                "mobile", "mobile_log", event, severity="info", project="system",
            ))

        if self.path == "/api/mobile/control":
            action = str(data.get("action", "")).strip().lower()
            project = str(data.get("project", "general")).strip() or "general"
            payload = data.get("payload") or {}
            safe_actions = {
                "status", "projects", "chats", "index", "investigate",
                "inspect_ui", "research_github", "incidents", "engines",
            }
            if action not in safe_actions:
                return self._json(403, {
                    "error": "mobile action is not in the approved control set",
                    "allowed": sorted(safe_actions),
                })
            try:
                if action == "status":
                    return self._json(200, {
                        "ok": True,
                        "core": "ONLINE",
                        "watcher": watcher.snapshot(),
                        "resources": orch.governor.snapshot(),
                        "pc_observer": pc_observer.snapshot(),
                        "mobile_connection": mobile_link_state(),
                    })
                if action == "projects":
                    return self._json(200, {"projects": orch.projects.list()})
                if action == "chats":
                    return self._json(200, {"chats": orch.chats(project)})
                if action == "index":
                    return self._json(200, orch.index_project(project))
                if action == "investigate":
                    symptom = str(payload.get("symptom", "")).strip()
                    if not symptom:
                        return self._json(400, {"error": "symptom is required"})
                    return self._json(200, orch.investigate(symptom, project, payload.get("components") or []))
                if action == "inspect_ui":
                    url = str(payload.get("url", "")).strip()
                    if not url:
                        return self._json(400, {"error": "url is required"})
                    return self._json(200, orch.inspect_ui(
                        project, url,
                        actions=payload.get("actions") or [],
                        screenshot_path=payload.get("screenshot_path"),
                    ))
                if action == "research_github":
                    query = str(payload.get("query", "")).strip()
                    if not query:
                        return self._json(400, {"error": "query is required"})
                    return self._json(200, orch.research_github(project, query, int(payload.get("limit", 10))))
                if action == "incidents":
                    return self._json(200, {"incidents": orch.memory.incidents(project, 50)})
                if action == "engines":
                    return self._json(200, {
                        "capabilities": [
                            "project_registry","repository_index","project_graph",
                            "evidence_engine","hypothesis_investigation",
                            "persistent_incident_memory","knowledge_ingestion",
                            "registered_action_registry","shadow_workspace",
                            "shadow_repair_pipeline","verification_gates",
                            "verification_review","resource_governor",
                            "privacy_aware_model_routing","chromium_ui_inspection",
                            "github_repository_research","goal_completion_evaluation",
                            "recovery_ladder","defensive_security_scan",
                            "watcher_transitions","neural_action_graph",
                            "pc_resource_observer","registered_project_change_observer",
                            "mobile_event_bridge","persistent_project_chats",
                            "windows_conversation_console","child_krishna_360_avatar",
                            "mobile_pc_remote_control",
                            "on_demand_skill_runtime","untrusted_content_boundary",
                            "specialist_permission_manifests",
                    "agi_policy_kernel",
                    "independent_critic_verifier",
                    "unified_memory_fabric",
                    "skill_compiler",
                    "benchmark_lab",
                    "native_automation_bus",
                    "isolated_worker_fabric",
                    "creator_provider_fabric",
                    "revenue_engine_adapters",
                        ]
                    })
            except KeyError:
                return self._json(404, {"error": "project not registered"})
            except (ValueError, RuntimeError) as exc:
                return self._json(400, {"error": str(exc)})
            except Exception as exc:
                return self._json(500, {"error": str(exc)})

        if self.path in ("/v1/chat", "/api/core/chat"):
            msg = data.get("message", "")
            if not isinstance(msg, str) or not msg.strip():
                return self._json(400, {"error": "message must be non-empty text"})
            # KRISHNA is the only public identity/mode. Legacy internal mode values are
            # accepted for compatibility but are not required by clients.
            requested_mode = str(data.get("mode", "chat")).strip().lower()
            if requested_mode not in ("chat", "karma", "vishwakarma"):
                return self._json(400, {"error": "invalid legacy mode"})
            mode = "chat"
            mark("REQUEST RECEIVED", f"{mode}: {msg[:110]}")
            try:
                mark("KRISHNA WORKING", "Processing request")
                project = data.get("project", "general")
                vision_evidence=[]
                attachment_ids=data.get("attachment_ids") or []
                if not isinstance(attachment_ids,list):return self._json(400,{"error":"attachment_ids must be a list"})
                for aid in attachment_ids[:3]:
                    try:
                        meta,raw=_attachments.read(data.get("chat_id"),str(aid))
                        vr=_vision.analyze_bytes(raw,meta.get("content_type"),"Analyze this image for the user's current request: "+msg)
                        vision_evidence.append({"attachment_id":str(aid),"name":meta.get("name"),"sha256":meta.get("sha256"),"analysis":vr["analysis"],"model":vr["model"]})
                    except Exception as exc:
                        vision_evidence.append({"attachment_id":str(aid),"error":f"{type(exc).__name__}: {exc}"})
                vision_text="\n".join("- "+x.get("analysis",x.get("error","")) for x in vision_evidence) if vision_evidence else None
                # KRISHNA selects internal capabilities automatically. Clients never
                # need to choose Sudarshan/Karma/Vishwakarma manually.
                if orch._looks_like_work_request(msg):
                    out = orch.handle_managed_request(msg, project, data.get("source", "pc"), data.get("chat_id"), vision_text)
                else:
                    out = orch.handle(msg, project, data.get("source", "pc"), data.get("chat_id"), vision_text)
                if vision_evidence:out["vision_evidence"]=vision_evidence
                out["mode"] = "chat"
                out["identity"] = "KRISHNA"
                out.setdefault("capability", "conversation")
                mark("REQUEST COMPLETE", "Response generated by Core")
                activity["current_activity"] = "Idle"
                orch.handle_event(
                    data.get("source", "pc"),
                    "response_generated",
                    "KRISHNA response generated and returned",
                    severity="notice",
                    project=data.get("project", "general"),
                    payload={"task_id": out.get("task_id")},
                )
                if str(data.get("source", "")).lower() == "mobile":
                    device, token = self._device_auth()
                    if _pairing.verify(device, token):
                        _sessions.publish(device, "response.generated", {
                            "project": data.get("project", "general"),
                            "chat_id": out.get("chat_id") or data.get("chat_id"),
                            "task_id": out.get("task_id"),
                            "summary": (out.get("reply") or out.get("text") or "KRISHNA completed the task")[:240],
                        })
                return self._json(200, out)
            except Exception as exc:
                mark("ERROR", str(exc)[:160])
                activity["current_activity"] = "Error"
                return self._json(500, {"error": str(exc)})

        if self.path == "/api/specialists/index":
            try:
                return self._json(200, _specialists.index(data.get("source_root") or None))
            except ValueError as exc:
                return self._json(400, {"error": str(exc)})

        if self.path == "/api/specialists/select":
            task = str(data.get("task", "")).strip()
            if not task:
                return self._json(400, {"error": "task is required"})
            project=str(data.get("project") or "KRISHNA").strip() or "KRISHNA"
            plan=_team_planner.plan(task,project,int(data.get("limit",5)))
            return self._json(200, {"selected":plan["agency_advisors"],"team":plan})

        if self.path == "/api/specialist-teams/plan":
            task=str(data.get("task") or "").strip()
            if not task:return self._json(400,{"error":"task is required"})
            return self._json(200,_team_planner.plan(task,str(data.get("project") or "KRISHNA"),int(data.get("external_limit") or 6)))

        if self.path == "/api/specialists/context":
            try:
                return self._json(200, _specialists.context(str(data.get("id", ""))))
            except KeyError:
                return self._json(404, {"error": "specialist not found"})
            except PermissionError as exc:
                return self._json(403, {"error": str(exc)})

        if self.path == "/api/plugins/add":
            try:
                return self._json(200, _plugins.add(data))
            except ValueError as exc:
                return self._json(400, {"error": str(exc)})

        if self.path == "/api/plugins/enable":
            try:
                return self._json(200, _plugins.set_enabled(str(data.get("id", "")).strip(), bool(data.get("enabled", True))))
            except KeyError:
                return self._json(404, {"error": "plugin not found"})

        if self.path == "/api/plugins/remove":
            try:
                return self._json(200, {"removed": _plugins.remove(str(data.get("id", "")).strip())})
            except PermissionError as exc:
                return self._json(403, {"error": str(exc)})

        if self.path == "/api/chats/create":
            project = str(data.get("project", "general")).strip() or "general"
            title = str(data.get("title", "New chat")).strip() or "New chat"
            try:
                return self._json(200, orch.create_chat(project, title))
            except KeyError:
                return self._json(404, {"error": "project not registered"})

        if self.path == "/api/chats/move":
            chat_id = str(data.get("chat_id", "")).strip()
            project = str(data.get("project", "")).strip()
            if not chat_id or not project:
                return self._json(400, {"error": "chat_id and project are required"})
            try:
                return self._json(200, orch.move_chat(chat_id, project))
            except KeyError as exc:
                return self._json(404, {"error": str(exc)})
            except ValueError as exc:
                return self._json(400, {"error": str(exc)})

        if self.path == "/api/chats/delete":
            chat_id = str(data.get("chat_id", "")).strip()
            if not chat_id:
                return self._json(400, {"error": "chat_id is required"})
            try:
                return self._json(200, orch.delete_chat(chat_id))
            except KeyError as exc:
                return self._json(404, {"error": str(exc)})

        if self.path == "/api/chats/rename":
            chat_id = str(data.get("chat_id", "")).strip()
            title = str(data.get("title", "")).strip()
            if not chat_id or not title:
                return self._json(400, {"error": "chat_id and title are required"})
            try:
                return self._json(200, orch.rename_chat(chat_id, title))
            except KeyError as exc:
                return self._json(404, {"error": str(exc)})
            except ValueError as exc:
                return self._json(400, {"error": str(exc)})

        if self.path == "/api/wearables/register":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"wearable registration must run on KRISHNA PC"})
            try:
                return self._json(201,_wearables.register(
                    str(data.get("name") or ""),str(data.get("kind") or ""),data.get("capabilities") or [],
                    str(data.get("provider") or "generic"),False,
                ))
            except ValueError as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/wearables/verify":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"wearable verification must run on KRISHNA PC"})
            did=str(data.get("device_id") or "").strip()
            if not did:return self._json(400,{"error":"device_id is required"})
            try:
                return self._json(200,_wearables.verify(
                    did,data.get("capabilities"),str(data.get("evidence") or ""),
                ))
            except KeyError:return self._json(404,{"error":"wearable device not found"})
            except ValueError as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/resilience/worker/clear-quarantine":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"worker quarantine changes must run on KRISHNA PC"})
            name=str(data.get("worker") or "").strip()
            if not name:return self._json(400,{"error":"worker is required"})
            try:return self._json(200,orch.agi.workers.clear_quarantine(name))
            except KeyError:return self._json(404,{"error":"worker not registered"})

        if self.path == "/api/resilience/models/unload":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"model unload must run on KRISHNA PC"})
            model=str(data.get("model") or "").strip()
            try:return self._json(200,_model_memory.unload(model) if model else _model_memory.unload_all())
            except (ValueError,RuntimeError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/voice/wake/start":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"microphone wake service must be controlled on KRISHNA PC"})
            try:return self._json(200,_voice.wake.start())
            except RuntimeError as exc:return self._json(503,{"error":str(exc),"status":_voice.status()})

        if self.path == "/api/voice/wake/stop":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"microphone wake service must be controlled on KRISHNA PC"})
            return self._json(200,_voice.wake.stop())

        if self.path == "/api/voice/tts":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"local TTS must be requested on KRISHNA PC"})
            text_value=str(data.get("text") or "").strip()
            if not text_value:return self._json(400,{"error":"text is required"})
            out_dir=RUNTIME_ROOT/"state"/"voice";out_dir.mkdir(parents=True,exist_ok=True)
            out_path=out_dir/(str(uuid.uuid4())+".wav")
            try:return self._json(200,{"output_path":_voice.tts.speak(text_value,out_path),"provider":"ai4bharat-indic-tts"})
            except (RuntimeError,ValueError) as exc:return self._json(503,{"error":str(exc)})

        if self.path == "/api/voice/stt":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"local STT must be requested on KRISHNA PC"})
            audio_path=str(data.get("audio_path") or "").strip()
            if not audio_path:return self._json(400,{"error":"audio_path is required"})
            try:return self._json(200,{"text":_voice.stt.transcribe(audio_path),"provider":"ai4bharat-indicconformer"})
            except (RuntimeError,ValueError,FileNotFoundError) as exc:return self._json(503,{"error":str(exc)})

        if self.path == "/api/models/gateways/register":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"model gateway secrets must be configured on KRISHNA PC"})
            try:
                return self._json(201,orch.model_gateway.register(
                    str(data.get("name") or ""),str(data.get("base_url") or ""),
                    str(data.get("model") or ""),str(data.get("api_key") or ""),
                    bool(data.get("free_only",True)),bool(data.get("enabled",True)),
                ))
            except (ValueError,RuntimeError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/models/gateways/delete":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"model gateway deletion must run on KRISHNA PC"})
            pid=str(data.get("profile_id") or "").strip()
            if not pid:return self._json(400,{"error":"profile_id is required"})
            return self._json(200,{"deleted":orch.model_gateway.delete(pid)})

        if self.path == "/api/projects/register":
            try:
                out = orch.register_project(
                    name=str(data.get("name", "")).strip(),
                    root=str(data.get("root", "")).strip(),
                    privacy=str(data.get("privacy", "local_only")),
                    allowed_actions=data.get("allowed_actions") or [],
                    verification_checks=data.get("verification_checks") or [],
                    metadata=data.get("metadata") or {},
                    role=str(data.get("role") or "active"),
                )
                return self._json(200, out)
            except (ValueError, TypeError) as exc:
                return self._json(400, {"error": str(exc)})

        if self.path == "/api/projects/unregister":
            name = str(data.get("name", "")).strip()
            try:
                return self._json(200, orch.unregister_project(name))
            except KeyError:
                return self._json(404, {"error": "project not registered"})
            except PermissionError as exc:
                return self._json(403, {"error": str(exc)})
            except ValueError as exc:
                return self._json(400, {"error": str(exc)})

        if self.path == "/api/e2e/register":
            if self.client_address[0] not in ("127.0.0.1", "::1"):
                return self._json(403, {"error": "E2E harness registration must be performed on KRISHNA PC"})
            project = str(data.get("project", "")).strip()
            if not project:
                return self._json(400, {"error": "project is required"})
            try:
                return self._json(200, orch.register_e2e_test_harness(project))
            except KeyError:
                return self._json(404, {"error": "project not registered"})
            except PermissionError as exc:
                return self._json(403, {"error": str(exc)})
            except (OSError, ValueError) as exc:
                return self._json(400, {"error": str(exc)})

        if self.path == "/api/projects/index":
            project = str(data.get("project", "")).strip()
            if not project:
                return self._json(400, {"error": "project is required"})
            try:
                return self._json(200, orch.index_project(project))
            except KeyError:
                return self._json(404, {"error": "project not registered"})

        if self.path == "/api/investigate":
            symptom = str(data.get("symptom", "")).strip()
            if not symptom:
                return self._json(400, {"error": "symptom is required"})
            project = str(data.get("project", "general"))
            components = data.get("components") or []
            mark("INVESTIGATING", symptom[:120])
            try:
                out = orch.investigate(symptom, project, components)
                mark("EVIDENCE COLLECTED", out["investigation_id"])
                activity["current_activity"] = "Idle"
                return self._json(200, out)
            except Exception as exc:
                mark("INVESTIGATION ERROR", str(exc)[:160])
                return self._json(500, {"error": str(exc)})

        if self.path == "/api/attachments":
            chat_id=str(data.get("chat_id") or "").strip()
            if not chat_id or not orch.memory.chat(chat_id):return self._json(404,{"error":"chat not found"})
            try:
                item=_attachments.save(chat_id,data.get("name"),data.get("data_b64"),data.get("content_type"))
                orch.memory.add_chat_message(chat_id,"tool","Attachment added",{"attachment":item})
                return self._json(201,item)
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/attachments/analyze":
            chat_id=str(data.get("chat_id") or "").strip();aid=str(data.get("attachment_id") or "").strip()
            if not chat_id or not orch.memory.chat(chat_id):return self._json(404,{"error":"chat not found"})
            if not aid:return self._json(400,{"error":"attachment_id is required"})
            try:
                meta,raw=_attachments.read(chat_id,aid)
                result=_vision.analyze_bytes(raw,meta.get("content_type"),str(data.get("prompt") or "Analyze this image as evidence for the current KRISHNA conversation."))
                evidence={"attachment_id":aid,"sha256":meta.get("sha256"),"name":meta.get("name"),**result}
                orch.memory.add_chat_message(chat_id,"tool","Local vision analysis",{"vision":evidence})
                proposal=None
                if bool(data.get("remember",False)):
                    project=str(data.get("project") or (orch.memory.chat(chat_id) or {}).get("project") or "KRISHNA")
                    proposal=orch.gyan_propose(project,"attachment:"+aid,result["analysis"],[evidence],0.9,"local_vision",True,"evidence",
                                              {"attachment_sha256":meta.get("sha256"),"provider":result["provider"],"model":result["model"]})
                return self._json(200,{"vision":evidence,"memory_proposal":proposal})
            except KeyError:return self._json(404,{"error":"attachment not found"})
            except (ValueError,PermissionError,FileNotFoundError) as exc:return self._json(400,{"error":str(exc)})
            except RuntimeError as exc:return self._json(503,{"error":str(exc)})

        if self.path == "/api/plugins/execute":
            try:
                return self._json(200,_plugin_executor.execute(str(data.get("plugin_id") or ""),str(data.get("project") or "KRISHNA"),str(data.get("operation") or "get"),data.get("payload") or {},data.get("auth_env")))
            except KeyError:return self._json(404,{"error":"plugin not found"})
            except (ValueError,PermissionError) as exc:return self._json(403 if isinstance(exc,PermissionError) else 400,{"error":str(exc)})
            except Exception as exc:return self._json(502,{"error":f"plugin request failed: {type(exc).__name__}: {exc}"})

        if self.path == "/api/software-factory/create":
            project=str(data.get("project") or "").strip(); goal=str(data.get("goal") or "").strip()
            if not project or not goal:return self._json(400,{"error":"project and goal are required"})
            try:return self._json(201,orch.create_software_project_team(project,goal,data.get("deadline_hours"),data.get("start_at"),data.get("end_at")))
            except (ValueError,KeyError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/software-factory/workers/request":
            try:return self._json(201,orch.request_ephemeral_workers(str(data.get("project") or ""),str(data.get("manager") or ""),str(data.get("role") or ""),int(data.get("count") or 1),str(data.get("reason") or ""),data.get("hr_snapshot"),False))
            except (ValueError,KeyError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/software-factory/workers/approve":
            try:return self._json(200,orch.request_ephemeral_workers(str(data.get("project") or ""),str(data.get("manager") or ""),str(data.get("role") or ""),int(data.get("count") or 1),str(data.get("reason") or ""),data.get("hr_snapshot"),True))
            except (ValueError,KeyError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/software-factory/workers/run":
            try:return self._json(200,orch.run_ephemeral_workers(str(data.get("project") or ""),data.get("request") or {},str(data.get("task") or "")))
            except (ValueError,KeyError,PermissionError,RuntimeError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/software-factory/gate":
            try:return self._json(200,orch.software_project_gate(str(data.get("project") or ""),str(data.get("stage") or ""),bool(data.get("passed",False)),data.get("evidence") or [],data.get("defects") or []))
            except (ValueError,KeyError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/software-factory/hr":
            try:return self._json(200,orch.software_factory_hr(str(data.get("project") or "KRISHNA"),data.get("workers") or [],data.get("deadline_at"),data.get("total_units"),data.get("completed_units")))
            except (ValueError,KeyError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/software-factory/test-plan":
            return self._json(200,orch.software_factory_test_plan(data.get("project_type","web"),data.get("risk","medium"),bool(data.get("has_ui",True)),bool(data.get("has_api",True))))

        if self.path == "/api/software-factory/testing-lead/verify":
            try:return self._json(200,orch.testing_lead_live_verify(str(data.get("project") or "KRISHNA"),str(data.get("url") or ""),data.get("screenshot_dir"),int(data.get("max_controls") or 100)))
            except (ValueError,KeyError,RuntimeError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/gyan-bhandar/archive":
            project=str(data.get("project") or "KRISHNA").strip(); source_path=str(data.get("source_path") or "").strip()
            if not source_path:return self._json(400,{"error":"source_path is required"})
            try:return self._json(201,orch.gyan_archive_file(project,source_path,str(data.get("topic") or ""),bool(data.get("remove_original",False))))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except (ValueError,FileNotFoundError) as exc:return self._json(400,{"error":str(exc)})
        if self.path == "/api/gyan-bhandar/archive/restore":
            digest=str(data.get("sha256") or "").strip(); destination=str(data.get("destination") or "").strip()
            if not digest or not destination:return self._json(400,{"error":"sha256 and destination are required"})
            try:return self._json(200,orch.gyan_restore_file(digest,destination))
            except (ValueError,FileNotFoundError) as exc:return self._json(400,{"error":str(exc)})
        if self.path == "/api/gyan-bhandar/compact":
            return self._json(200,orch.gyan_compact())

        if self.path == "/api/gyan-bhandar/propose":
            project=str(data.get("project") or "KRISHNA").strip(); topic=str(data.get("topic") or "").strip(); lesson=str(data.get("lesson") or "").strip()
            if not topic or not lesson:return self._json(400,{"error":"topic and lesson are required"})
            try:return self._json(202,orch.gyan_propose(project,topic,lesson,data.get("evidence") or [],float(data.get("confidence") or 0),
                str(data.get("source") or "research"),bool(data.get("verified",False)),str(data.get("memory_kind") or "semantic"),
                data.get("provenance") or {},data.get("supersedes")))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/gyan-bhandar/decide":
            approval_id=str(data.get("approval_id") or "").strip()
            if not approval_id or "approved" not in data:return self._json(400,{"error":"approval_id and approved are required"})
            try:return self._json(200,orch.gyan_decide(approval_id,bool(data.get("approved"))))
            except KeyError:return self._json(404,{"error":"pending finding not found"})
        if self.path == "/api/gyan-bhandar/store":
            project=str(data.get("project") or "KRISHNA").strip(); topic=str(data.get("topic") or "").strip(); lesson=str(data.get("lesson") or "").strip()
            if not topic or not lesson:return self._json(400,{"error":"topic and lesson are required"})
            try:return self._json(201,orch.gyan_store(project,topic,lesson,data.get("evidence") or [],float(data.get("confidence") or 0),
                str(data.get("source") or "sudarshan"),bool(data.get("verified",False)),str(data.get("memory_kind") or "semantic"),
                data.get("provenance") or {},data.get("supersedes")))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/gyan-bhandar/supersede":
            project=str(data.get("project") or "KRISHNA").strip(); fingerprint=str(data.get("fingerprint") or "").strip()
            topic=str(data.get("topic") or "").strip(); lesson=str(data.get("lesson") or "").strip()
            if not fingerprint or not topic or not lesson:return self._json(400,{"error":"fingerprint, topic and lesson are required"})
            try:return self._json(202,orch.gyan_supersede(project,fingerprint,topic,lesson,data.get("evidence") or [],
                float(data.get("confidence") or 0),str(data.get("source") or "krishna"),bool(data.get("verified",False)),
                str(data.get("memory_kind") or "semantic"),data.get("provenance") or {}))
            except KeyError:return self._json(404,{"error":"learning or project not found"})
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/gyan-bhandar/strengthen":
            project=str(data.get("project") or "KRISHNA").strip(); topic=str(data.get("topic") or "").strip()
            if not topic:return self._json(400,{"error":"topic is required"})
            try:return self._json(200,orch.gyan_strengthen(project,topic,bool(data.get("use_garuda",True)),int(data.get("limit") or 10)))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except (ValueError,RuntimeError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/garuda/scout":
            project=str(data.get("project") or "KRISHNA").strip()
            goal=str(data.get("goal") or "").strip()
            if not goal:return self._json(400,{"error":"goal is required"})
            try:return self._json(200,orch.garuda_scout(project,goal,int(data.get("limit") or 10)))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except (ValueError,RuntimeError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/development/git/status":
            project=str(data.get("project","")).strip()
            if not project:return self._json(400,{"error":"project is required"})
            try:return self._json(200,orch.development_git_snapshot(project))
            except KeyError:return self._json(404,{"error":"project not registered"})

        if self.path == "/api/development/git/commit":
            project=str(data.get("project","")).strip()
            try:return self._json(200,orch.development_commit(project,str(data.get("message","KRISHNA verified change")),data.get("files") or [],bool(data.get("approved",False))))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except (ValueError,PermissionError) as exc:return self._json(403 if isinstance(exc,PermissionError) else 400,{"error":str(exc)})

        if self.path == "/api/development/git/push":
            project=str(data.get("project","")).strip()
            try:return self._json(200,orch.development_push(project,bool(data.get("approved",False))))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})

        if self.path == "/api/development/sync":
            project=str(data.get("project","")).strip()
            if not project:return self._json(400,{"error":"project is required"})
            try:return self._json(200,orch.development_sync(project))
            except KeyError:return self._json(404,{"error":"project not registered"})

        if self.path == "/api/development/stage":
            project=str(data.get("project","")).strip(); files=data.get("files") or []
            if not project or not isinstance(files,list):return self._json(400,{"error":"project and files are required"})
            try:return self._json(200,orch.development_stage(project,files))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except (ValueError,OSError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/development/verify":
            project=str(data.get("project","")).strip(); candidate=str(data.get("candidate_root","")).strip()
            if not project or not candidate:return self._json(400,{"error":"project and candidate_root are required"})
            try:return self._json(200,orch.development_verify(project,candidate,data.get("checks") or [],data.get("frontend_url"),data.get("browser_actions") or [],data.get("api_expectations") or [],data.get("screenshot_path") or None))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except (ValueError,OSError,RuntimeError) as exc:return self._json(400,{"error":str(exc)})

        if self.path == "/api/work/run":
            project = str(data.get("project", "")).strip()
            goal = str(data.get("goal", "")).strip()
            action = str(data.get("action", "")).strip() or None
            if not project or not goal:
                return self._json(400, {"error": "project and goal are required"})
            try:
                out = orch.run_managed_goal(
                    project, goal,
                    action_name=action,
                    components=data.get("components") or [],
                    approved=bool(data.get("approved", False)),
                )
                return self._json(200, out)
            except KeyError as exc:
                return self._json(404, {"error": str(exc)})
            except PermissionError as exc:
                return self._json(403, {"error": str(exc)})
            except RuntimeError as exc:
                return self._json(409, {"error": str(exc)})

        if self.path == "/api/work/promotion/prepare":
            project=str(data.get("project","")).strip()
            candidate=str(data.get("candidate_root","")).strip()
            if not project or not candidate: return self._json(400,{"error":"project and candidate_root are required"})
            try: return self._json(200,orch.prepare_promotion(project,candidate,data.get("task_id")))
            except KeyError as exc: return self._json(404,{"error":str(exc)})
            except ValueError as exc: return self._json(400,{"error":str(exc)})

        if self.path == "/api/work/promotion/apply":
            token=str(data.get("promotion_token","")).strip()
            if not token: return self._json(400,{"error":"promotion_token is required"})
            try: return self._json(200,orch.promote_candidate(token,approved=bool(data.get("approved",False))))
            except KeyError as exc: return self._json(404,{"error":str(exc)})
            except PermissionError as exc: return self._json(403,{"error":str(exc)})
            except (ValueError,RuntimeError) as exc: return self._json(409,{"error":str(exc)})

        if self.path == "/api/repair/shadow":
            project = str(data.get("project", "")).strip()
            symptom = str(data.get("symptom", "")).strip()
            action = str(data.get("action", "")).strip()
            if not project or not symptom or not action:
                return self._json(400, {"error": "project, symptom and action are required"})
            mark("SHADOW REPAIR", f"{project}: {symptom[:80]}")
            try:
                out = orch.run_shadow_repair(project, symptom, action, data.get("components") or [])
                mark("SHADOW VERIFIED" if out["promotable"] else "SHADOW REJECTED", out["repair_id"])
                if out.get("promotable"):
                    orch.handle_event(
                        "pc", "repair_verified", f"{project}: {out['repair_id']}",
                        severity="notice", project=project,
                        payload={"repair_id": out["repair_id"]},
                    )
                activity["current_activity"] = "Idle"
                return self._json(200, out)
            except KeyError as exc:
                return self._json(404, {"error": str(exc)})
            except PermissionError as exc:
                return self._json(403, {"error": str(exc)})
            except RuntimeError as exc:
                return self._json(409, {"error": str(exc)})

        if self.path == "/api/browser/inspect":
            project = str(data.get("project", "general"))
            url = str(data.get("url", "")).strip()
            if not url:
                return self._json(400, {"error": "url is required"})
            try:
                out = orch.inspect_ui(
                    project,
                    url,
                    actions=data.get("actions") or [],
                    screenshot_path=data.get("screenshot_path"),
                )
                return self._json(200, out)
            except (ValueError, RuntimeError) as exc:
                return self._json(400, {"error": str(exc)})
            except Exception as exc:
                return self._json(500, {"error": str(exc)})

        if self.path == "/api/research/github":
            project = str(data.get("project", "general"))
            query = str(data.get("query", "")).strip()
            if not query:
                return self._json(400, {"error": "query is required"})
            try:
                out = orch.research_github(project, query, int(data.get("limit", 10)))
                return self._json(200, out)
            except (ValueError, RuntimeError) as exc:
                return self._json(400, {"error": str(exc)})
            except Exception as exc:
                return self._json(500, {"error": str(exc)})

        if self.path == "/api/goal/evaluate":
            project = str(data.get("project", "general"))
            goal = str(data.get("goal", "")).strip()
            checks = data.get("checks") or []
            if not goal:
                return self._json(400, {"error": "goal is required"})
            return self._json(200, orch.evaluate_goal(project, goal, checks))

        if self.path == "/api/knowledge/ingest":
            project = str(data.get("project", "general"))
            source = str(data.get("source", "manual"))
            text = str(data.get("text", ""))
            if not text.strip():
                return self._json(400, {"error": "text is required"})
            result = orch.ingest_knowledge(project, source, text, data.get("metadata"))
            return self._json(200, result)

        if self.path == "/api/project-graph/node":
            name = str(data.get("name", "")).strip()
            if not name:
                return self._json(400, {"error": "name is required"})
            orch.graph.upsert_node(name, str(data.get("kind", "component")), data.get("metadata") or {})
            return self._json(200, {"ok": True})

        if self.path == "/api/project-graph/link":
            source = str(data.get("source", "")).strip()
            target = str(data.get("target", "")).strip()
            if not source or not target:
                return self._json(400, {"error": "source and target are required"})
            orch.graph.link(source, target, str(data.get("relation", "depends_on")))
            return self._json(200, {"ok": True})

        if self.path == "/api/security/scan-text":
            path = str(data.get("path", "submitted-text"))
            text = str(data.get("text", ""))
            return self._json(200, {
                "authorized_defensive_scan": True,
                "findings": orch.security.scan_text(path, text),
            })

        if self.path == "/api/recovery/execute":
            step = str(data.get("step", "")).strip()
            if not step:
                return self._json(400, {"error": "step is required"})
            try:
                return self._json(200, orch.recovery.execute(step, data.get("payload") or {}))
            except KeyError:
                return self._json(404, {"error": "unknown recovery step"})

        return self._json(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer((settings.host, settings.port), Handler)
    if os.getenv("KRISHNA_LAN_DISCOVERY","0") == "1":
        _lan_discovery = LanDiscoveryService(settings.port)
        _lan_discovery.start()
        if _lan_discovery.last_error:
            print(f"[KRISHNA] LAN discovery warning: {_lan_discovery.last_error}", file=sys.stderr)
    shown_host = "127.0.0.1" if settings.host == "0.0.0.0" else settings.host
    print(f"KRISHNA Core: http://{shown_host}:{settings.port}/dashboard")
    try:
        server.serve_forever()
    finally:
        if _lan_discovery:
            _lan_discovery.stop()
        server.server_close()
