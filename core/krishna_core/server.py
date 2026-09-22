from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json, time, threading, base64, sys, uuid, os, mimetypes
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
from .browser_fabric import GarudanetraBrowserFabric
from .ui_guardian import UIGuardian, UIGuardianRegistry
from .narad.scheduler import NaradScheduler
from .autonomy_supervisor import AutonomySupervisor
from .specialist_team import SpecialistTeamPlanner
from .lan_discovery import LanDiscoveryService
from .avatar_asset_pipeline import AvatarAssetInspector
from .video_avatar import VideoAvatarFabric
from .science_atlas import ScienceFrontierScheduler
from .brahma_memory_intelligence import BrahmaConsolidationScheduler
from .windows_desktop_fabric import WindowsDesktopFabric
from .android_test_fabric import AndroidTestFabric

orch = Orchestrator()
_pairing = DevicePairingStore(Path(settings.db_path).resolve().parent / ".krishna_state")
_sessions = RealtimeSessionStore(Path(settings.db_path).resolve().parent / ".krishna_state")
_plugins = PluginRegistry(Path(settings.db_path).resolve().parent / ".krishna_state")
_plugin_executor = PluginExecutor(_plugins, orch.secure_vault)

def _plugin_add_action(payload,context):
    row=dict(payload or {})
    row["enabled"]=False
    return _plugins.add(row)

def _plugin_enable_action(payload,context):
    plugin_id=str(payload.get("id") or "").strip()
    enabled=bool(payload.get("enabled",True))
    if enabled and not bool(context.get("approved")):
        raise PermissionError("enabling a plugin requires explicit owner approval")
    return _plugins.set_enabled(plugin_id,enabled)

def _plugin_remove_action(payload,context):
    if not bool(context.get("approved")):
        raise PermissionError("removing a plugin requires explicit owner approval")
    return {"removed":_plugins.remove(str(payload.get("id") or "").strip())}

def _plugin_execute_action(payload,context):
    operation=str(payload.get("operation") or "get").strip().lower()
    if operation=="post" and not bool(context.get("approved")):
        raise PermissionError("POST plugin execution requires explicit owner approval")
    return _plugin_executor.execute(
        str(payload.get("plugin_id") or ""),
        str(payload.get("project") or context.get("project") or "KRISHNA"),
        operation,payload.get("payload") or {},payload.get("auth_env"),
    )

orch.action_bus.register(
    "plugin.add",_plugin_add_action,description="Add a disabled plugin manifest",
    mutating=True,permissions=("plugin.write",),sources=("pc","system"),
)
orch.action_bus.register(
    "plugin.enable",_plugin_enable_action,description="Enable or disable a plugin",
    mutating=True,permissions=("plugin.write",),sources=("pc","system"),
)
orch.action_bus.register(
    "plugin.remove",_plugin_remove_action,description="Remove a non-builtin plugin manifest",
    mutating=True,permissions=("plugin.write",),sources=("pc","system"),
)
orch.action_bus.register(
    "plugin.execute",_plugin_execute_action,description="Execute a bounded HTTP plugin request",
    mutating=True,permissions=("plugin.execute","network.external"),
    sources=("pc","system","agent","job","mcp","a2a"),
)

def _desktop_validate_action(payload,context):
    return _desktop_fabric.validate(
        str(payload.get("workflow") or ""),payload.get("variables"),payload.get("task"),
    )

def _desktop_run_action(payload,context):
    return _desktop_fabric.run(
        str(payload.get("workflow") or ""),payload.get("variables"),payload.get("task"),
        approved=bool(context.get("approved",False)),
    )

orch.action_bus.register(
    "desktop.rpa.validate",_desktop_validate_action,
    description="Validate a bounded Windows desktop RPA workflow",
    permissions=("desktop.read","tests.run"),sources=("pc","system","agent","job"),
)
orch.action_bus.register(
    "desktop.rpa.run",_desktop_run_action,
    description="Run an approved validated Windows desktop RPA workflow",
    mutating=True,requires_approval=True,permissions=("desktop.control",),
    sources=("pc","system","agent","job"),
)

def _android_test_run_action(payload,context):
    return _android_test_fabric.run_task(
        str(payload.get("instruction") or ""),str(payload.get("profile") or "flash"),
        approved=bool(context.get("approved",False)),
    )

orch.action_bus.register(
    "mobile.test.run",_android_test_run_action,
    description="Run an owner-approved KRISHNA Android QA task through ARTEMIS",
    mutating=True,requires_approval=True,permissions=("mobile.test","device.control"),
    sources=("pc","system","agent","job"),
)

_attachments = AttachmentStore(Path(settings.db_path).resolve().parent / ".krishna_state")

def _cleanup_deleted_chat_attachments(event):
    payload=dict(event.get("payload") or {})
    if str(payload.get("action") or "")!="chat.delete" or str(payload.get("status") or "")!="completed":
        return None
    chat_id=str((payload.get("payload") or {}).get("chat_id") or "").strip()
    if not chat_id:return None
    try:
        result=_attachments.delete_chat(chat_id)
        orch.memory.audit("attachment_cleanup","completed",f"{chat_id}:{result.get('files',0)} files")
        return result
    except Exception as exc:
        orch.memory.audit("attachment_cleanup","failed",f"{chat_id}:{type(exc).__name__}: {exc}")
        return {"error":f"{type(exc).__name__}: {exc}"}

orch.lifecycle_bus.subscribe("action.completed",_cleanup_deleted_chat_attachments)
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
               "console":snapshot.get("console") or [],"network":snapshot.get("network") or [],
               "recording":snapshot.get("recording") or [],"semantic_revision":snapshot.get("semantic_revision")}]
    try:
        orch.gyan_propose(project,"garudanetra-task-memory:"+sid,lesson,evidence,0.8,
                          "garudanetra_task_memory",False,"evidence",
                          {"session_id":sid,"mode":snapshot.get("mode"),"url":snapshot.get("current_url")})
        for idx,finding in enumerate(snapshot.get("findings") or []):
            if finding.get("kind")!="selector_recovered" or not finding.get("candidate_skill"):
                continue
            skill=finding["candidate_skill"]
            compiled=orch.agi.skills.compile_candidate(
                f"garudanetra-selector-recovery-{sid[:8]}-{idx+1}",
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
        successful=[row for row in (snapshot.get("recording") or [])
                    if row.get("status")=="ok" and row.get("action") not in {"pause","resume","takeover","stop"}]
        if len(successful)>=2:
            steps=[]
            for row in successful[:80]:
                payload=dict(row.get("payload") or {})
                steps.append({"action":"browser_"+str(row.get("action") or "step"),
                              "payload":payload,
                              "requires_input":any(str(v)=="[REDACTED]" for v in payload.values())})
            compiled=orch.agi.skills.compile_candidate(
                f"garudanetra-workflow-{sid[:8]}",steps,project=project,
                evidence=[{"session_id":sid,"url":snapshot.get("current_url"),
                           "title":snapshot.get("title"),"step_count":len(steps)}],
            )
            orch.gyan_propose(project,"garudanetra-recorded-workflow",
                              f"Recorded Garudanetra workflow candidate with {len(steps)} verified runtime step(s).",
                              [{"session_id":sid,"url":snapshot.get("current_url"),"steps":steps,
                                "compiled_skill":{"path":compiled.get("path"),"digest":compiled.get("digest"),"status":compiled.get("status")}}],
                              0.7,"garudanetra_recording",False,"skill",
                              {"session_id":sid,"verification_required":True,"replay_requires_approval":True,
                               "compiled_skill_path":compiled.get("path"),"compiled_skill_digest":compiled.get("digest")})
    except Exception as exc:
        orch.memory.audit("garudanetra_task_memory","proposal_failed",f"{type(exc).__name__}: {exc}")
_browser_fabric = GarudanetraBrowserFabric(RUNTIME_ROOT,inspector=orch.browser,on_closed=_remember_garudanetra_session)
# From this point forward the Fabric is KRISHNA's browser authority.  The raw
# BrowserOperator remains internal as _browser_fabric.inspector.
orch.browser = _browser_fabric
orch.development.browser = _browser_fabric
orch.project_perfection.browser = _browser_fabric
_garudanetra = _browser_fabric.sessions

def _shared_garudanetra_start(payload,context):
    project=str(payload.get("project") or context.get("project") or "KRISHNA").strip() or "KRISHNA"
    url=str(payload.get("url") or "").strip()
    mode=str(payload.get("mode") or "private").strip().lower()
    return _browser_fabric.create(
        project,url,mode,persistent_approved=bool(context.get("approved",False)),
    )

def _shared_garudanetra_control(payload,context):
    sid=str(payload.get("session_id") or "").strip()
    action=str(payload.get("action") or "").strip()
    if not sid or not action:raise ValueError("session_id and action are required")
    return _browser_fabric.command(sid,action,dict(payload.get("payload") or {}))

def _shared_garudanetra_replay(payload,context):
    sid=str(payload.get("session_id") or "").strip()
    if not sid:raise ValueError("session_id is required")
    steps=payload.get("steps")
    if steps is not None and not isinstance(steps,list):raise ValueError("steps must be an array")
    return _browser_fabric.replay(sid,steps=steps,approved=bool(context.get("approved",False)))

orch.action_bus.register(
    "garudanetra.start",_shared_garudanetra_start,
    description="Start a canonical Garudanetra browser session",
    mutating=True,permissions=("browser.read","browser.act"),
    sources=("pc","system","agent","job","mcp","a2a"),
)
orch.action_bus.register(
    "garudanetra.control",_shared_garudanetra_control,
    description="Control a canonical Garudanetra browser session",
    mutating=True,permissions=("browser.act",),
    sources=("pc","system","agent","job","mcp","a2a"),
)
orch.action_bus.register(
    "garudanetra.replay",_shared_garudanetra_replay,
    description="Replay recorded Garudanetra steps through the approval gate",
    mutating=True,permissions=("browser.act",),
    sources=("pc","system","agent","job","mcp","a2a"),
)

def _shared_garudanetra_upload_attachment(payload,context):
    sid=str(payload.get("session_id") or "").strip()
    chat_id=str(payload.get("chat_id") or "").strip()
    aid=str(payload.get("attachment_id") or "").strip()
    selector=str(payload.get("selector") or "").strip()
    if not sid or not chat_id or not aid or not selector:
        raise ValueError("session_id, chat_id, attachment_id and selector are required")
    meta,path=_attachments.resolve(chat_id,aid)
    return _browser_fabric.command(sid,"upload",{"selector":selector,"path":str(path)})

orch.action_bus.register(
    "garudanetra.upload_attachment",_shared_garudanetra_upload_attachment,
    description="Upload a KRISHNA chat attachment into the active Garudanetra page",
    mutating=True,permissions=("browser.act","chat.read"),
    sources=("pc","system","agent","job","mcp","a2a"),
)
_ui_registry = UIGuardianRegistry(Path(settings.db_path).resolve().parent / ".krishna_state" / "ui-guardian-registry.json")
_ui_guardian = UIGuardian(_browser_fabric, _ui_registry, Path(settings.db_path).resolve().parent / "reports" / "ui-guardian")

# Server-owned services join the same Shared Action Bus instead of becoming
# parallel mutation authorities. Compatibility HTTP routes below delegate to
# these same actions and the owner UI consumes auditable action receipts.
def _plugin_credential_set_action(payload,context):
    plugin_id=str(payload.get("plugin_id") or "").strip()
    secret=str(payload.get("secret") or "")
    if not plugin_id or not secret:raise ValueError("plugin_id and secret are required")
    item=next((x for x in _plugins.list() if x.get("id")==plugin_id),None)
    if not item:raise KeyError("plugin not found")
    auth=str(item.get("auth_type") or "none")
    if auth not in {"token","api_key"}:
        raise ValueError("this plugin requires local or provider-specific OAuth; raw account passwords are not accepted")
    ref=orch.secure_vault.put("Plugin "+item.get("name",plugin_id),"plugin:"+plugin_id,secret)
    updated=_plugins.set_credential(plugin_id,ref["id"])
    return {"plugin":updated,"credential":{"id":ref["id"],"backend":ref["backend"],"available":ref["available"]}}

def _plugin_credential_delete_action(payload,context):
    plugin_id=str(payload.get("plugin_id") or "").strip()
    item=next((x for x in _plugins.list() if x.get("id")==plugin_id),None)
    if not item:raise KeyError("plugin not found")
    ref=str(item.get("credential_ref") or "").strip()
    if ref:orch.secure_vault.delete(ref)
    return {"plugin":_plugins.clear_credential(plugin_id)}

def _project_index_action(payload,context):
    project=str(payload.get("project") or context.get("project") or "").strip()
    if not project:raise ValueError("project is required")
    return orch.index_project(project)

def _ui_guardian_register_action(payload,context):
    return _ui_registry.register(
        str(payload.get("name") or "").strip(),
        str(payload.get("project") or context.get("project") or "KRISHNA").strip() or "KRISHNA",
        str(payload.get("url") or "").strip(),
        str(payload.get("state") or "candidate"),
        str(payload.get("notes") or ""),
    )

def _ui_guardian_evaluate_action(payload,context):
    entry_id=str(payload.get("entry_id") or "").strip()
    if not entry_id:raise ValueError("entry_id is required")
    with orch.governor.job(timeout=0):
        return _ui_guardian.evaluate_entry(entry_id)

def _ui_guardian_transition_action(payload,context):
    entry_id=str(payload.get("entry_id") or "").strip()
    target=str(payload.get("target") or "").strip()
    if not entry_id or not target:raise ValueError("entry_id and target are required")
    return _ui_registry.transition(entry_id,target,verified=bool(payload.get("verified",False)),notes=str(payload.get("notes") or ""))

def _commitment_update_action(payload,context):
    cid=str(payload.get("commitment_id") or "").strip()
    if not cid:raise ValueError("commitment_id is required")
    return orch.complete_commitment(cid,str(payload.get("status") or "planned"),payload.get("detail"))

def _mobile_pair_approve_action(payload,context):
    result=_pairing.approve(str(payload.get("request_id") or "").strip())
    orch.handle_event("device_pairing","device_approved",result.get("device_id",""),severity="notice",project="system",payload={"mode":result.get("mode")})
    return result

def _model_gateway_register_action(payload,context):
    return orch.model_gateway.register(
        payload.get("name"),payload.get("base_url"),payload.get("model"),payload.get("api_key"),
        bool(payload.get("free_only",True)),bool(payload.get("enabled",True)),
    )

def _model_gateway_delete_action(payload,context):
    return {"deleted":orch.model_gateway.delete(str(payload.get("profile_id") or "").strip())}

def _narad_connection_register_action(payload,context):
    return orch.agi.narad_credentials.register(
        str(payload.get("name") or ""),str(payload.get("provider") or ""),str(payload.get("env_var") or ""),
        str(payload.get("header") or "Authorization"),str(payload.get("scheme") or "Bearer"),
    )

def _narad_connection_secret_action(payload,context):
    return orch.agi.narad_credentials.register_secret(
        str(payload.get("name") or ""),str(payload.get("provider") or ""),str(payload.get("secret") or ""),
        str(payload.get("header") or "Authorization"),str(payload.get("scheme") or "Bearer"),
    )

def _narad_connection_delete_action(payload,context):
    return {"deleted":orch.agi.narad_credentials.delete(str(payload.get("credential_id") or "").strip())}

def _gyan_propose_action(payload,context):
    return orch.gyan_propose(
        str(payload.get("project") or context.get("project") or "KRISHNA"),str(payload.get("topic") or ""),
        str(payload.get("lesson") or ""),payload.get("evidence") or [],float(payload.get("confidence") or 0),
        str(payload.get("source") or "research"),bool(payload.get("verified",False)),
        str(payload.get("memory_kind") or "semantic"),payload.get("provenance") or {},payload.get("supersedes"),
    )

def _gyan_decide_action(payload,context):
    return orch.gyan_decide(str(payload.get("approval_id") or ""),bool(payload.get("approved")))

def _gyan_supersede_action(payload,context):
    return orch.gyan_supersede(
        str(payload.get("project") or context.get("project") or "KRISHNA"),str(payload.get("fingerprint") or ""),
        str(payload.get("topic") or ""),str(payload.get("lesson") or ""),payload.get("evidence") or [],
        float(payload.get("confidence") or 0),str(payload.get("source") or "krishna"),bool(payload.get("verified",False)),
        str(payload.get("memory_kind") or "semantic"),payload.get("provenance") or {},
    )

def _gyan_strengthen_action(payload,context):
    return orch.gyan_strengthen(
        str(payload.get("project") or context.get("project") or "KRISHNA"),str(payload.get("topic") or ""),
        bool(payload.get("use_garuda",True)),int(payload.get("limit") or 10),
    )

def _attachment_add_action(payload,context):
    chat_id=str(payload.get("chat_id") or "").strip()
    if not chat_id or not orch.memory.chat(chat_id):raise KeyError("chat not found")
    item=_attachments.save(
        chat_id,str(payload.get("name") or "attachment"),
        str(payload.get("data_b64") or ""),str(payload.get("content_type") or "application/octet-stream"),
    )
    orch.memory.add_chat_message(chat_id,"tool","Attachment added",{"attachment":item})
    return item

def _autonomy_tick_action(payload,context):
    return _autonomy.run_once()

def _narad_webhook_provision_action(payload,context):
    wid=str(payload.get("workflow_id") or "").strip()
    if not wid:raise ValueError("workflow_id is required")
    return orch.agi.narad.provision_webhook(wid)

for _name,_handler,_desc,_mutating,_approval,_permissions in (
    ("plugin.credential.set",_plugin_credential_set_action,"Store an encrypted plugin credential reference",True,True,("plugin.write","credential.write")),
    ("plugin.credential.delete",_plugin_credential_delete_action,"Delete an encrypted plugin credential reference",True,True,("plugin.write","credential.write")),
    ("project.index",_project_index_action,"Index a registered project into KRISHNA structural memory",True,False,("project.read","memory.write")),
    ("ui.guardian.register",_ui_guardian_register_action,"Register a GUI candidate for viewport verification",True,False,("ui.write",)),
    ("ui.guardian.evaluate",_ui_guardian_evaluate_action,"Evaluate a GUI candidate across verified viewports",False,False,("browser.test","ui.read")),
    ("ui.guardian.transition",_ui_guardian_transition_action,"Transition a GUI registry candidate state",True,False,("ui.write",)),
    ("commitment.update",_commitment_update_action,"Update an explicit KRISHNA commitment/autonomy state",True,False,("work.write",)),
    ("mobile.pair.approve",_mobile_pair_approve_action,"Approve a pending KRISHNA Mobile device pairing",True,True,("mobile.pair",)),
    ("model.gateway.register",_model_gateway_register_action,"Register an encrypted model gateway profile",True,True,("model.admin","credential.write")),
    ("model.gateway.delete",_model_gateway_delete_action,"Delete a model gateway profile and encrypted key",True,True,("model.admin","credential.write")),
    ("narad.connection.register",_narad_connection_register_action,"Register a NARAD environment credential reference",True,False,("narad.write",)),
    ("narad.connection.secret",_narad_connection_secret_action,"Register a DPAPI-encrypted NARAD credential",True,True,("narad.write","credential.write")),
    ("narad.connection.delete",_narad_connection_delete_action,"Delete a NARAD credential reference",True,True,("narad.write","credential.write")),
    ("gyan.propose",_gyan_propose_action,"Route a knowledge candidate through Rishi and BRAHMA QC",True,False,("memory.write","evidence.write")),
    ("gyan.decide",_gyan_decide_action,"Approve or reject a pending Gyan promotion",True,False,("memory.write",)),
    ("gyan.supersede",_gyan_supersede_action,"Propose supersession of an existing Gyan item",True,False,("memory.write","evidence.write")),
    ("gyan.strengthen",_gyan_strengthen_action,"Research and strengthen evidence for a Gyan topic",False,False,("web.read","evidence.write")),
    ("attachment.add",_attachment_add_action,"Attach a bounded file to a persistent KRISHNA chat",True,False,("chat.write","filesystem.write")),
    ("autonomy.tick",_autonomy_tick_action,"Run one bounded safe autonomy-supervisor pass",True,False,("work.execute","runtime.read")),
    ("narad.webhook.provision",_narad_webhook_provision_action,"Provision a one-time-secret NARAD webhook endpoint",True,False,("narad.write",)),
):
    orch.action_bus.register(
        _name,_handler,description=_desc,mutating=_mutating,requires_approval=_approval,
        permissions=_permissions,sources=("pc","system"),
    )
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
_activity_lock = threading.RLock()
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

def _sync_shared_action_to_mobile(event):
    row=dict(event.get("payload") or {})
    action_id=str(row.get("action_id") or "")
    if not action_id:return None
    sync={
        "action_id":action_id,"action":row.get("action"),"project":row.get("project"),
        "status":row.get("status"),"source":row.get("source"),"actor":row.get("actor"),
        "created_at":row.get("created_at"),"completed_at":row.get("completed_at"),
    }
    with _mobile_lock:
        device=_mobile_link.get("device")
    if not device:return None
    return _sessions.publish(
        device,"action.sync",sync,
        idempotency_key=f'action-sync:{event.get("topic")}:{action_id}',
    )

for _topic in ("action.requested","action.completed","action.failed","action.blocked"):
    orch.agi.bus.subscribe(_topic,_sync_shared_action_to_mobile)
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    _BUNDLE_ROOT = Path(sys._MEIPASS)
    WEB_VALIDATION = _BUNDLE_ROOT / "web_validation.html"
    DESIGN_STUDIO = _BUNDLE_ROOT / "design_studio.html"
    VISUAL_EDITOR = _BUNDLE_ROOT / "visual_editor.html"
    AVATAR_B64 = _BUNDLE_ROOT / "avatar" / "krishna_child_360.webp.b64"
    # The private child avatar is owner/runtime data and is deliberately never
    # bundled into KRISHNA.exe. Frozen and source runtimes use the same E: asset.
    AVATAR_GLB = RUNTIME_ROOT / "dashboard" / "assets" / "avatar" / "krishna.glb"
    AVATAR_PRODUCTION_GLB = RUNTIME_ROOT / "dashboard" / "assets" / "avatar" / "krishna.production.glb"
    AVATAR_ENGINE_ROOT = RUNTIME_ROOT / "dashboard" / "assets" / "avatar-engine"
else:
    _CORE_ROOT = Path(__file__).resolve().parents[1]
    _REPO_ROOT = Path(__file__).resolve().parents[2]
    WEB_VALIDATION = _CORE_ROOT / "web_validation.html"
    DESIGN_STUDIO = _CORE_ROOT / "design_studio.html"
    VISUAL_EDITOR = _CORE_ROOT / "visual_editor.html"
    AVATAR_B64 = _REPO_ROOT / "avatar" / "krishna_child_360.webp.b64"
    AVATAR_GLB = RUNTIME_ROOT / "dashboard" / "assets" / "avatar" / "krishna.glb"
    AVATAR_PRODUCTION_GLB = RUNTIME_ROOT / "dashboard" / "assets" / "avatar" / "krishna.production.glb"
    AVATAR_ENGINE_ROOT = RUNTIME_ROOT / "dashboard" / "assets" / "avatar-engine"


def avatar_engine_file(relative_path):
    root=AVATAR_ENGINE_ROOT.resolve()
    raw=str(relative_path or "").replace("\\","/").lstrip("/")
    if not raw or raw.startswith(".") or "/../" in ("/"+raw) or raw.endswith("/.."):
        return None
    candidate=(root/raw).resolve()
    if candidate!=root and root not in candidate.parents:
        return None
    return candidate if candidate.is_file() else None


def avatar_360_bytes():
    try:
        return base64.b64decode(AVATAR_B64.read_text(encoding="utf-8").strip(), validate=True)
    except Exception:
        return b""


_avatar_inspector = AvatarAssetInspector(RUNTIME_ROOT / "state" / "avatar" / "asset-audit.json")
_video_avatar = VideoAvatarFabric(RUNTIME_ROOT)
_desktop_fabric = WindowsDesktopFabric(RUNTIME_ROOT)
_android_test_fabric = AndroidTestFabric(RUNTIME_ROOT)

def avatar_asset_status():
    source=_avatar_inspector.inspect(AVATAR_GLB)
    production=_avatar_inspector.inspect(AVATAR_PRODUCTION_GLB) if AVATAR_PRODUCTION_GLB.is_file() else {"available":False,"ready":False,"stage":"missing"}
    active=AVATAR_PRODUCTION_GLB if production.get("ready") else AVATAR_GLB
    return {
        "source":source,
        "production":production,
        "active":"production" if active==AVATAR_PRODUCTION_GLB else "source",
        "active_path":str(active),
        "active_ready":bool((production if active==AVATAR_PRODUCTION_GLB else source).get("ready")),
        "promotion_policy":"krishna.production.glb is served only after local compatibility inspection reports production-ready",
    }

def active_avatar_glb():
    status=avatar_asset_status()
    return AVATAR_PRODUCTION_GLB if status.get("active")=="production" else AVATAR_GLB


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


def set_current_activity(value):
    with _activity_lock:
        activity["current_activity"]=str(value)
        activity["updated"]=time.strftime("%Y-%m-%d %H:%M:%S")

def activity_snapshot():
    with _activity_lock:
        return {"current_activity":activity["current_activity"],"updated":activity["updated"],"recent":list(activity["recent"])}

def mark(event, detail=""):
    now = time.strftime("%H:%M:%S")
    with _activity_lock:
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

def _science_frontier_tick():
    snap=pc_observer.snapshot()
    return orch.brahmagyan_science_background_tick(
        snap.get("cpu_percent") or 0.0,
        snap.get("memory_percent") or 0.0,
    )

_science_frontier_scheduler = ScienceFrontierScheduler(
    _science_frontier_tick,
    interval_seconds=int(os.getenv("KRISHNA_SCIENCE_RESEARCH_INTERVAL_SECONDS","1800")),
)
if str(os.getenv("KRISHNA_SCIENCE_RESEARCH_ENABLED","1")).strip().lower() not in {"0","false","no","off"}:
    _science_frontier_scheduler.start()


def _brahma_consolidation_tick():
    activity_state=activity_snapshot()
    if str(activity_state.get("current_activity") or "Idle").strip().lower() != "idle":
        return {"status":"skipped_activity_busy","activity":activity_state.get("current_activity")}
    snap=pc_observer.snapshot()
    cpu=float(snap.get("cpu_percent") or 0.0)
    memory=float(snap.get("memory_percent") or 0.0)
    max_cpu=float(os.getenv("KRISHNA_BRAHMA_IDLE_MAX_CPU_PERCENT","45"))
    max_memory=float(os.getenv("KRISHNA_BRAHMA_IDLE_MAX_MEMORY_PERCENT","78"))
    if cpu>max_cpu or memory>max_memory:
        return {
            "status":"skipped_resource_pressure",
            "cpu_percent":cpu,"memory_percent":memory,
            "max_cpu_percent":max_cpu,"max_memory_percent":max_memory,
        }
    try:
        with orch.governor.job(timeout=0):
            consolidation=orch.brahma.consolidate(
                int(os.getenv("KRISHNA_BRAHMA_CONSOLIDATION_MAX_ITEMS","250"))
            )
            decay=orch.brahma.decay_scan()
    except RuntimeError as exc:
        if "resource governor busy" in str(exc).lower():
            return {"status":"skipped_resource_governor_busy"}
        raise
    result={
        "status":"completed",
        "cpu_percent":cpu,
        "memory_percent":memory,
        "consolidation":consolidation,
        "decay":decay,
    }
    orch.memory.audit(
        "brahma_sleep_learning","completed",
        f"{consolidation.get('consolidation_id')}:{consolidation.get('selected_learning_decisions',0)}:"
        f"{consolidation.get('duplicates_collapsed',0)}",
    )
    return result


_brahma_consolidation_scheduler = BrahmaConsolidationScheduler(
    _brahma_consolidation_tick,
    interval_seconds=int(os.getenv("KRISHNA_BRAHMA_CONSOLIDATION_INTERVAL_SECONDS","1800")),
)
if str(os.getenv("KRISHNA_BRAHMA_CONSOLIDATION_ENABLED","1")).strip().lower() not in {"0","false","no","off"}:
    _brahma_consolidation_scheduler.start()


def shutdown_runtime_services():
    failures=[]
    services=(
        ("autonomy", _autonomy.stop),
        ("narad_scheduler", _narad_scheduler.stop),
        ("science_frontier_scheduler", _science_frontier_scheduler.stop),
        ("brahma_consolidation_scheduler", _brahma_consolidation_scheduler.stop),
        ("worker_resilience", _worker_resilience.stop),
        ("pc_observer", pc_observer.stop),
        ("watcher", watcher.stop),
        ("voice_wake", _voice.wake.stop),
        ("garudanetra", _garudanetra.close_all),
    )
    for name, stop in services:
        try:
            stop()
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
    return failures


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
        try:
            paired = bool(device and _pairing.verify(device, token))
        except RuntimeError as exc:
            orch.memory.audit("device_pairing","state_unavailable",f"{type(exc).__name__}: {exc}")
            self._json(503, {"error": "pairing state unavailable"})
            return False
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
        path=urlparse(self.path).path
        if path=="/api/mobile/pair/request":
            limit=16*1024
        elif path.startswith("/api/narad/webhook/"):
            limit=2*1024*1024
        elif path=="/api/attachments":
            limit=36*1024*1024
        else:
            limit=8*1024*1024
        n = int(self.headers.get("Content-Length", "0"))
        if n < 0 or n > limit:
            raise ValueError(f"request body exceeds {limit // 1024} KB limit for this endpoint")
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
            if not WEB_VALIDATION.exists():
                return self._json(503, {
                    "error": "current KRISHNA desktop UI is unavailable",
                    "required_ui_version": "2026.09-current",
                })
            ui_text=WEB_VALIDATION.read_text(encoding="utf-8")
            if 'data-krishna-ui="2026.09-current"' not in ui_text:
                return self._json(503, {
                    "error": "stale KRISHNA desktop UI refused",
                    "required_ui_version": "2026.09-current",
                })
            return self._html(200, ui_text)
        if path == "/favicon.ico":
            return self._binary(204, b"", "image/x-icon")
        if path in ("/web", "/web-test", "/validation"):
            if not WEB_VALIDATION.exists():
                return self._json(503, {"error": "current KRISHNA desktop UI unavailable"})
            ui_text=WEB_VALIDATION.read_text(encoding="utf-8")
            if 'data-krishna-ui="2026.09-current"' not in ui_text:
                return self._json(503, {"error": "stale KRISHNA desktop UI refused"})
            return self._html(200, ui_text)
        if path == "/design-studio":
            if not DESIGN_STUDIO.exists():
                return self._json(404, {"error": "design studio unavailable"})
            return self._html(200, DESIGN_STUDIO.read_text(encoding="utf-8"))
        if path == "/visual-editor":
            if not VISUAL_EDITOR.exists():
                return self._json(404, {"error": "visual editor unavailable"})
            return self._html(200, VISUAL_EDITOR.read_text(encoding="utf-8"))
        if path.startswith("/assets/avatar-engine/"):
            rel=path[len("/assets/avatar-engine/"):]
            asset=avatar_engine_file(rel)
            if not asset:return self._json(404,{"error":"local avatar engine asset unavailable"})
            content_type=mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
            if asset.suffix in (".mjs",".js"):content_type="text/javascript; charset=utf-8"
            elif asset.suffix==".wasm":content_type="application/wasm"
            return self._binary(200,asset.read_bytes(),content_type)
        if path == "/api/avatar/status":
            asset=avatar_asset_status()
            return self._json(200,{
                "preview_available": bool(avatar_360_bytes()),
                "glb_available": active_avatar_glb().is_file(),
                "viewer_policy": "local-only",
                "talkinghead_installed": (AVATAR_ENGINE_ROOT/"talkinghead"/"talkinghead.mjs").is_file(),
                "model_viewer_installed": (AVATAR_ENGINE_ROOT/"model-viewer"/"model-viewer.min.js").is_file(),
                "headaudio_installed": (AVATAR_ENGINE_ROOT/"headaudio"/"dist"/"headaudio.min.mjs").is_file(),
                "motion_engine_installed": (AVATAR_ENGINE_ROOT/"motion-engine"/"src"/"MotionEngine.js").is_file(),
                "lipsync_quality":{"engine":"HeadAudio","bundled_model_training":"English mixed voices",
                                   "english":"trained-model","hindi":"audio-driven approximation","odia":"audio-driven approximation"},
                "asset_pipeline":asset,
                "video_avatar":_video_avatar.status(),
                **orch.agi.avatar.status(),
            })
        if path == "/api/avatar/asset-audit":
            return self._json(200,avatar_asset_status())
        if path == "/api/avatar/performance":
            return self._json(200,orch.agi.avatar.performance_bible())
        if path == "/api/avatar/video/status":
            return self._json(200,_video_avatar.status())
        if path == "/api/avatar/video/recommend":
            goal=(query.get("goal") or [""])[0]
            vram_raw=(query.get("vram_gb") or [""])[0]
            try:vram=float(vram_raw) if str(vram_raw).strip() else None
            except (TypeError,ValueError):return self._json(400,{"error":"vram_gb must be numeric"})
            return self._json(200,_video_avatar.recommend(goal,vram))
        if path == "/api/avatar/video/contract":
            provider=(query.get("provider") or ["musetalk"])[0].strip().lower() or "musetalk"
            try:return self._json(200,_video_avatar.generation_contract(provider))
            except KeyError:return self._json(404,{"error":"unknown video avatar provider"})
        if path == "/api/avatar.glb":
            asset=active_avatar_glb()
            if not asset.is_file():return self._json(404,{"error":"private krishna.glb unavailable"})
            return self._binary(200,asset.read_bytes(),"model/gltf-binary")
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
        if path in ("/api/hawkeye/status", "/api/bhumiputra/status"):
            status=orch.hawkeye.status()
            status["agent"]="hawkeye"
            status["legacy_api_alias"]="/api/bhumiputra/status"
            return self._json(200,status)
        if path == "/api/hawkeye/learning/missions":
            return self._json(200,{"agent":"hawkeye","missions":orch.hawkeye_learning.daily_missions()})
        if path == "/api/hawkeye/diagnostic/status":
            return self._json(200,orch.hawkeye_diagnostic.status())
        if path == "/api/hawkeye/reference/status":
            return self._json(200,orch.hawkeye_reference.status())
        if path == "/api/hawkeye/reference/item":
            reference_id=str((query.get("reference_id") or [""])[0]).strip()
            if not reference_id:return self._json(400,{"error":"reference_id is required"})
            try:return self._json(200,orch.hawkeye_reference.get(reference_id))
            except KeyError:return self._json(404,{"error":"reference not found"})
        if path == "/api/hawkeye/diagnostic/session":
            session_id=str((query.get("session_id") or [""])[0]).strip()
            if not session_id:return self._json(400,{"error":"session_id is required"})
            try:return self._json(200,orch.hawkeye_diagnostic.get_session(session_id))
            except KeyError:return self._json(404,{"error":"diagnostic session not found"})
        if path == "/api/hawkeye/field/maps":
            return self._json(200,{"agent":"hawkeye","providers":orch.hawkeye_field.map_stack(),
                                   "geo_catalog":orch.hawkeye_geo.catalog()})
        if path == "/api/hawkeye/field/devices":
            return self._json(200,{"agent":"hawkeye","devices":orch.hawkeye_field.devices()})
        if path == "/api/hawkeye/field/sync/pending":
            return self._json(200,{"agent":"hawkeye","items":orch.hawkeye_field.pending()})
        if path == "/api/hawkeye/geo/view":
            try:
                lat=float((query.get("lat") or [""])[0]);lon=float((query.get("lon") or [""])[0])
            except (TypeError,ValueError):return self._json(400,{"error":"lat and lon are required numeric values"})
            return self._json(200,orch.hawkeye_geo.unified_view(lat,lon))
        if path == "/api/hawkeye/geo/history":
            site_id=(query.get("site_id") or [None])[0]
            try:limit=max(1,min(int((query.get("limit") or ["100"])[0]),1000))
            except (TypeError,ValueError):return self._json(400,{"error":"limit must be an integer"})
            return self._json(200,{"items":orch.hawkeye_geo.history(site_id,limit)})
        if path in ("/api/hawkeye/live/state", "/api/bhumiputra/live/state"):
            session_id=str((query.get("session_id") or [""])[0]).strip()
            if not session_id:return self._json(400,{"error":"session_id is required"})
            try:return self._json(200,orch.hawkeye.get_live_session(session_id))
            except KeyError:return self._json(404,{"error":"live session not found"})
        if path == "/api/voice/audio":
            audio_id=str((query.get("id") or [""])[0]).strip()
            try:audio_id=str(uuid.UUID(audio_id))
            except (ValueError,AttributeError):return self._json(400,{"error":"valid audio id is required"})
            audio_path=RUNTIME_ROOT/"state"/"voice"/(audio_id+".wav")
            if not audio_path.is_file():return self._json(404,{"error":"voice audio not found"})
            return self._binary_nostore(200,audio_path.read_bytes(),"audio/wav")
        if path == "/api/voice/status":
            return self._json(200,_voice.status())
        if path == "/api/garuda/status":
            return self._json(200, orch.garuda_status())
        if path == "/api/brahmagyan/status":
            return self._json(200,orch.brahmagyan_status())
        if path == "/api/brahmagyan/council":
            return self._json(200,orch.brahmagyan_council())
        if path == "/api/brahmagyan/missions":
            project=(query.get("project") or [None])[0]
            limit_raw=(query.get("limit") or ["100"])[0]
            try:limit=max(1,min(int(limit_raw),500))
            except (TypeError,ValueError):return self._json(400,{"error":"limit must be an integer"})
            return self._json(200,{"missions":orch.brahmagyan_missions(project,limit)})
        if path == "/api/brahmagyan/claim":
            claim_id=str((query.get("id") or [""])[0]).strip()
            if not claim_id:return self._json(400,{"error":"id is required"})
            try:return self._json(200,orch.brahmagyan_claim(claim_id))
            except KeyError:return self._json(404,{"error":"claim not found"})
        if path == "/api/brahmagyan/curiosity":
            project=(query.get("project") or [None])[0]
            limit_raw=(query.get("limit") or ["50"])[0]
            try:limit=max(1,min(int(limit_raw),200))
            except (TypeError,ValueError):return self._json(400,{"error":"limit must be an integer"})
            return self._json(200,{"questions":orch.brahmagyan_curiosity(project,limit)})
        if path == "/api/brahmagyan/projects":
            query_text=str((query.get("query") or [""])[0]).strip()
            limit_raw=(query.get("limit") or ["10"])[0]
            try:limit=max(1,min(int(limit_raw),50))
            except (TypeError,ValueError):return self._json(400,{"error":"limit must be an integer"})
            return self._json(200,orch.brahmagyan_projects(query_text,limit))
        if path == "/api/brahmagyan/rishis/topics":
            return self._json(200,orch.brahmagyan_rishi_topics())
        if path == "/api/brahmagyan/rishis/learning":
            rid=str((query.get("rishi_id") or [""])[0]).strip() or None
            topic=str((query.get("topic") or [""])[0]).strip() or None
            limit_raw=(query.get("limit") or ["50"])[0]
            try:limit=max(1,min(int(limit_raw),200))
            except (TypeError,ValueError):return self._json(400,{"error":"limit must be an integer"})
            try:return self._json(200,orch.brahmagyan_rishi_learning(rid,topic,limit))
            except KeyError:return self._json(404,{"error":"Rishi not found"})
        if path == "/api/brahmagyan/rishis/collaboration":
            cid=str((query.get("collaboration_id") or [""])[0]).strip() or None
            try:return self._json(200,orch.brahmagyan_rishi_collaboration(cid))
            except KeyError:return self._json(404,{"error":"collaboration not found"})
        if path == "/api/brahmagyan/science/status":
            query_text=str((query.get("query") or [""])[0]).strip()
            kind=str((query.get("kind") or [""])[0]).strip() or None
            limit_raw=(query.get("limit") or ["50"])[0]
            try:limit=max(1,min(int(limit_raw),200))
            except (TypeError,ValueError):return self._json(400,{"error":"limit must be an integer"})
            return self._json(200,{
                **orch.brahmagyan_science_status(query_text,kind,limit),
                "scheduler":_science_frontier_scheduler.status(),
            })
        if path == "/api/brahmagyan/live/status":
            run_id=str((query.get("run_id") or [""])[0]).strip() or None
            project=(query.get("project") or [None])[0]
            limit_raw=(query.get("limit") or ["50"])[0]
            try:limit=max(1,min(int(limit_raw),200))
            except (TypeError,ValueError):return self._json(400,{"error":"limit must be an integer"})
            try:return self._json(200,orch.brahmagyan_live_status(run_id,project,limit))
            except KeyError:return self._json(404,{"error":"live research run not found"})
        if path == "/api/garudanetra/fabric":
            return self._json(200, _browser_fabric.status())
        if path == "/api/garudanetra/sessions":
            return self._json(200, _garudanetra.status())
        if path == "/api/garudanetra/semantic":
            sid=(query.get("id") or [""])[0].strip()
            if not sid:return self._json(400,{"error":"id is required"})
            return self._json(200,_browser_fabric.semantic_snapshot(sid))
        if path == "/api/garudanetra/recording":
            sid=(query.get("id") or [""])[0].strip()
            if not sid:return self._json(400,{"error":"id is required"})
            return self._json(200,_browser_fabric.recording(sid))
        if path == "/api/garudanetra/element-at":
            sid=(query.get("id") or [""])[0].strip()
            if not sid:return self._json(400,{"error":"id is required"})
            try:
                x=float((query.get("x") or ["0"])[0]);y=float((query.get("y") or ["0"])[0])
            except ValueError:return self._json(400,{"error":"x and y must be numeric"})
            return self._json(200,_browser_fabric.element_at(sid,x,y,normalized=True))
        if path == "/api/project-perfection/status":
            return self._json(200,orch.project_perfection.status())
        if path == "/api/design-studio/session":
            sid=(query.get("id") or [""])[0].strip()
            if not sid:return self._json(400,{"error":"id is required"})
            try:return self._json(200,orch.project_perfection.design_get(sid))
            except KeyError:return self._json(404,{"error":"design session not found"})
        if path == "/api/design-studio/preview":
            token=(query.get("id") or [""])[0].strip()
            if not token:return self._json(400,{"error":"id is required"})
            try:return self._html(200,orch.project_perfection.design_preview(token))
            except KeyError:return self._json(404,{"error":"design preview not found"})
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
            info=_browser_fabric.frame_info(sid);frame=info.get("bytes")
            if not frame:return self._json(404,{"error":"frame not available yet"})
            return self._binary_nostore(200,frame,info.get("mime") or "image/png")
        if path == "/api/commitments/resume":
            project=(query.get("project") or [None])[0]
            return self._json(200,orch.resume_unfinished_work(project))
        if path == "/api/software-factory/workers/status":
            return self._json(200,orch.ephemeral_worker_status())
        if path == "/api/kabach/projects":
            return self._json(200,orch.protect_registered_projects())
        if path == "/api/kabach/privacy/status":
            return self._json(200,orch.kabach.privacy_status())
        if path == "/api/kabach/privacy/history":
            limit_raw=(query.get("limit") or ["50"])[0]
            try:limit=max(1,min(int(limit_raw),500))
            except (TypeError,ValueError):return self._json(400,{"error":"limit must be an integer"})
            rows=orch.kabach.privacy.history(limit)
            return self._json(200,{"history":rows,"count":len(rows)})
        if path == "/api/kabach/privacy/metrics":
            return self._json(200,orch.kabach.privacy.metrics())
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
        if path == "/api/brahma/status":
            return self._json(200,orch.brahma.status())
        if path == "/api/brahma/retrieve":
            topic=str((query.get("topic") or [""])[0]).strip()
            if not topic:return self._json(400,{"error":"topic is required"})
            try:return self._json(200,orch.brahma.retrieve(topic))
            except KeyError as exc:return self._json(404,{"error":str(exc)})

        if path == "/api/brahma/intelligence/status":
            return self._json(200,{**orch.brahma.memory_intelligence.status(),"scheduler":_brahma_consolidation_scheduler.status()})
        if path == "/api/brahma/temporal":
            topic=str((query.get("topic") or [""])[0]).strip()
            include=str((query.get("include_superseded") or ["0"])[0]).lower() in {"1","true","yes"}
            as_of_raw=(query.get("as_of") or [None])[0]
            limit_raw=(query.get("limit") or ["100"])[0]
            try:
                as_of=float(as_of_raw) if as_of_raw not in (None,"") else None
                limit=max(1,min(int(limit_raw),500))
            except (TypeError,ValueError):return self._json(400,{"error":"invalid as_of or limit"})
            return self._json(200,orch.brahma.temporal_query(topic,as_of=as_of,include_superseded=include,limit=limit))
        if path == "/api/brahma/rishi-graph":
            topic=str((query.get("topic") or [""])[0]).strip()
            if not topic:return self._json(400,{"error":"topic is required"})
            try:return self._json(200,orch.brahma.rishi_graph(topic))
            except (KeyError,ValueError) as exc:return self._json(400,{"error":str(exc)})

        if path == "/api/gyan-bhandar/archive/status":
            return self._json(200,orch.gyan_archive_status())
        if path == "/api/gyan-bhandar/security":
            try:return self._json(200,orch.gyan_security_status())
            except RuntimeError as exc:return self._json(503,{"error":str(exc)})
        if path == "/api/gyan-bhandar/context":
            project=(query.get("project") or ["KRISHNA"])[0].strip() or "KRISHNA"
            topic=(query.get("topic") or [""])[0]
            kind=(query.get("kind") or [None])[0]
            verified=str((query.get("verified") or ["0"])[0]).lower() in {"1","true","yes"}
            principal=(query.get("principal") or ["owner"])[0]
            try:return self._json(200,orch.gyan_compile_context(project,topic,50,verified,kind,principal))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except RuntimeError as exc:return self._json(503,{"error":str(exc)})
        if path == "/api/gyan-bhandar/context-uri":
            uri=(query.get("uri") or [""])[0];principal=(query.get("principal") or ["owner"])[0]
            if not uri:return self._json(400,{"error":"uri is required"})
            try:return self._json(200,orch.gyan_compile_uri(uri,50,principal))
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})
            except KeyError:return self._json(404,{"error":"project not registered"})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
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
        if path == "/api/narad/workflow/plan":
            workflow_id=str((query.get("id") or [""])[0]).strip()
            if not workflow_id:return self._json(400,{"error":"id is required"})
            try:return self._json(200,orch.agi.narad.workflow_plan(workflow_id))
            except KeyError:return self._json(404,{"error":"workflow not found"})
        if path == "/api/narad/connectors":
            return self._json(200,{
                "connectors":orch.agi.narad.connectors.status(),
                "n8n":orch.agi.narad.status().get("n8n"),
                "execution_gate":orch.agi.narad.execution_gate.status(),
            })
        if path == "/api/narad/history":
            limit=max(1,min(int((query.get("limit") or ["100"])[0]),500))
            return self._json(200, {"history":orch.agi.narad.history[-limit:]})
        if path == "/api/narad/connections":
            return self._json(200,orch.agi.narad_credentials.list())
        if path == "/api/narad/dead-letters":
            return self._json(200,orch.agi.narad.dead_letter_status())
        if path == "/api/narad/checkpoints":
            rows=list(orch.agi.narad.checkpoints.values())
            rows.sort(key=lambda x:str(x.get("updated_at") or ""),reverse=True)
            return self._json(200,{"checkpoints":rows,"count":len(rows)})
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
        if path == "/health":
            return self._json(200, {
                "ok": True,
                "core": "ONLINE",
                "uptime_seconds": int(time.time() - started),
            })
        if path == "/api/status":
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
            current_state=activity_snapshot()
            return self._json(200, {
                "active": True,
                "core": "ONLINE",
                "watcher": watcher.snapshot(),
                "resources": orch.governor.snapshot(),
                "pc_observer": pc_observer.snapshot(),
                "neural": orch.neural_state(),
                **current_state,
                "avatar_state": orch.agi.avatar.state_for_activity(current_state["current_activity"]),
                "avatar_character_bible": orch.agi.avatar.VERSION,
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
        if path == "/api/desktop/status":
            probe=str((query.get("probe") or ["0"])[0]).lower() in {"1","true","yes"}
            if probe and self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"desktop provider probing is local-PC only"})
            return self._json(200,_desktop_fabric.status(probe=probe))
        if path == "/api/mobile/testing/status":
            probe=str((query.get("probe") or ["0"])[0]).lower() in {"1","true","yes"}
            if probe and self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"Android test provider probing is local-PC only"})
            return self._json(200,_android_test_fabric.status(probe=probe))
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
                    "durable_mission_engine",
                    "authoritative_durable_queue",
                    "mission_checkpoint_recovery",
                    "durable_resource_locks",
                    "durable_lifecycle_event_bus",
                    "per_mission_resource_budgets",
                    "contextual_permission_policy",
                    "versioned_krishna_protocol",
                    "unified_model_provider_contract",
                    "privacy_aware_model_routing",
                    "chromium_ui_inspection",
                    "project_perfection_finish_pipeline",
                    "deadline_driven_hr_planning",
                    "recursive_route_state_crawl",
                    "xy_dom_geometry_verification",
                    "generated_browser_regression_memory",
                    "persistent_bug_immune_memory",
                    "axe_accessibility_verification",
                    "visual_baseline_regression",
                    "hawkeye_ui_perceptual_review",
                    "api_property_fuzzing",
                    "mutation_testing",
                    "browser_chaos_testing",
                    "clean_artifact_retest",
                    "design_studio_web_research",
                    "design_studio_rendered_previews",
                    "point_drag_speak_visual_editor",
                    "transactional_design_apply_rollback",
                    "garudanetra_private_live_browser",
                    "garudanetra_owner_takeover_stream",
                    "garudanetra_task_memory_mode",
                    "garudanetra_persistent_workspace_mode",
                    "garudanetra_self_healing_selector_recovery",
                    "garudanetra_semantic_accessibility_refs",
                    "garudanetra_cdp_screencast",
                    "garudanetra_action_recording_replay",
                    "garudanetra_optional_browser_adapter_registry",
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
                    "windows_desktop_fabric_capability_gated",
                    "android_artemis_test_fabric_capability_gated",
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
                    "brahma_learning_governor",
                    "brahma_mobile_pc_learning_router",
                    "brahma_rishi_context_retrieval",
                    "brahma_gyan_qc_gate",
                    "gyan_typed_memory_categories",
                    "gyan_learning_supersession",
                    "gyan_provenance_inventory",
                    "gyan_project_scoped_context_compiler",
                    "gyan_acl_fail_closed",
                    "gyan_session_learning_candidates",
                    "gyan_envelope_encryption_capability_gated",
                    "gyan_verified_local_replication",
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
        if path == "/api/action-bus":
            return self._json(200, orch.action_bus_status())
        if path == "/api/action-bus/recent":
            limit_raw=(query.get("limit") or ["50"])[0]
            try:limit=max(1,min(int(limit_raw),500))
            except (TypeError,ValueError):return self._json(400,{"error":"limit must be an integer"})
            return self._json(200,{"actions":orch.action_bus_recent(limit)})
        if path == "/api/agents/runtime":
            return self._json(200,orch.agent_runtime_status())
        if path == "/api/jobs/runtime":
            return self._json(200,orch.job_runtime_status())
        if path == "/api/permissions/runtime":
            return self._json(200,orch.permission_runtime_status())
        if path == "/api/protocols/status":
            return self._json(200,orch.protocol_runtime_status())
        if path == "/api/dispatch/status":
            return self._json(200,orch.dispatch_runtime_status())
        if path == "/api/sudarshan/runtime":
            return self._json(200,orch.sudarshan_status())
        if path == "/api/protocols/mcp/catalog":
            return self._json(200,orch.protocols.mcp_catalog())
        if path == "/api/resources":
            return self._json(200, orch.governor.snapshot())
        if path == "/api/missions/status":
            return self._json(200,orch.mission_status())
        if path == "/api/missions":
            project=(query.get("project") or [None])[0]
            status=(query.get("status") or [None])[0]
            limit_raw=(query.get("limit") or ["100"])[0]
            try:limit=max(1,min(int(limit_raw),500))
            except (TypeError,ValueError):return self._json(400,{"error":"limit must be an integer"})
            try:return self._json(200,{"missions":orch.missions.list(project,status,limit)})
            except ValueError as exc:return self._json(400,{"error":str(exc)})
        if path == "/api/queue/status":
            return self._json(200,orch.queue_status())
        if path == "/api/queue":
            state=(query.get("state") or [None])[0]
            mission=(query.get("mission_id") or [None])[0]
            limit_raw=(query.get("limit") or ["100"])[0]
            try:limit=max(1,min(int(limit_raw),500))
            except (TypeError,ValueError):return self._json(400,{"error":"limit must be an integer"})
            try:return self._json(200,{"items":orch.queue.list(state,mission,limit)})
            except ValueError as exc:return self._json(400,{"error":str(exc)})
        if path == "/api/checkpoints":
            mission=(query.get("mission_id") or [""])[0]
            if not mission:return self._json(400,{"error":"mission_id is required"})
            return self._json(200,{"checkpoints":orch.missions.checkpoints(mission)})
        if path == "/api/resource-locks":
            return self._json(200,orch.resource_lock_status())
        if path == "/api/events":
            topic=(query.get("topic") or [None])[0]
            after=(query.get("after") or [None])[0]
            limit_raw=(query.get("limit") or ["100"])[0]
            try:
                limit=max(1,min(int(limit_raw),500))
                after_seq=int(after) if after not in (None,"") else None
            except (TypeError,ValueError):return self._json(400,{"error":"invalid event cursor/limit"})
            return self._json(200,{"events":orch.lifecycle_bus.recent(topic,limit,after_seq),"status":orch.lifecycle_event_status()})
        if path == "/api/protocol":
            return self._json(200,orch.krishna_protocol_status())
        if path == "/api/models/providers":
            return self._json(200,orch.model_provider_status())
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
            current_state=activity_snapshot();current=current_state["current_activity"]
            return self._json(200, {
                "operator": {
                    "avatar_state": orch.agi.avatar.state_for_activity(current),
                    "character_bible": orch.agi.avatar.VERSION,
                    "current": {"task": current},
                    "updated": current_state["updated"],
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

        if post_path == "/api/mobile/testing/run":
            try:
                receipt=orch.dispatch_action(
                    "mobile.test.run",
                    {"instruction":data.get("instruction"),"profile":data.get("profile") or "flash"},
                    project=str(data.get("project") or "KRISHNA"),source="pc",actor="mobile-test-fabric",
                    approved=bool(data.get("approved",False)),permissions=("mobile.test","device.control"),
                )
                return self._json(200,receipt["result"])
            except ValueError as exc:return self._json(400,{"error":str(exc)})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except RuntimeError as exc:return self._json(503,{"error":str(exc)})

        if post_path == "/api/desktop/rpa/validate":
            try:
                receipt=orch.dispatch_action(
                    "desktop.rpa.validate",
                    {"workflow":data.get("workflow"),"variables":data.get("variables"),"task":data.get("task")},
                    project=str(data.get("project") or "KRISHNA"),source="pc",actor="desktop-fabric",
                    permissions=("desktop.read","tests.run"),
                )
                return self._json(200,receipt["result"])
            except (ValueError,FileNotFoundError,PermissionError) as exc:
                return self._json(403 if isinstance(exc,PermissionError) else 400,{"error":str(exc)})
            except RuntimeError as exc:return self._json(503,{"error":str(exc)})

        if post_path == "/api/desktop/rpa/run":
            try:
                receipt=orch.dispatch_action(
                    "desktop.rpa.run",
                    {"workflow":data.get("workflow"),"variables":data.get("variables"),"task":data.get("task")},
                    project=str(data.get("project") or "KRISHNA"),source="pc",actor="desktop-fabric",
                    approved=bool(data.get("approved",False)),permissions=("desktop.control",),
                )
                return self._json(200,receipt["result"])
            except (ValueError,FileNotFoundError) as exc:return self._json(400,{"error":str(exc)})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except RuntimeError as exc:return self._json(503,{"error":str(exc)})

        if post_path == "/api/design-studio/research":
            project=str(data.get("project") or "").strip();goal=str(data.get("goal") or "").strip()
            if not project or not goal:return self._json(400,{"error":"project and goal are required"})
            try:
                receipt=orch.dispatch_action(
                    "project.design.research",
                    {"project":project,"goal":goal,"limit":int(data.get("limit") or 12)},
                    project=project,source="pc",actor="design-studio-http",
                    permissions=("browser.read","model.use"),
                )
                result=receipt["result"]
                result["studio_url"]="/design-studio?session="+str(result.get("session_id") or "")
                return self._json(201,result)
            except KeyError:return self._json(404,{"error":"project not registered"})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,RuntimeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/design-studio/create":
            project=str(data.get("project") or "KRISHNA").strip() or "KRISHNA"
            candidates=data.get("candidates") or []
            if not isinstance(candidates,list):return self._json(400,{"error":"candidates must be an array"})
            try:
                result=orch.project_perfection.design_create(project,candidates)
                return self._json(201,result)
            except ValueError as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/design-studio/submit":
            sid=str(data.get("session_id") or "").strip();cid=str(data.get("candidate_id") or "").strip()
            if not sid or not cid:return self._json(400,{"error":"session_id and candidate_id are required"})
            try:
                selection=orch.project_perfection.design_submit(sid,cid)
                project=str(selection.get("project") or "").strip()
                if not project:return self._json(400,{"error":"design session has no project"})
                policy=orch.projects.get(project)
                if not policy:return self._json(404,{"error":"project not registered"})
                frontend_url=str(data.get("frontend_url") or (selection.get("metadata") or {}).get("frontend_url") or "").strip() or None
                checks=list(data.get("checks") or policy.verification_checks or [])
                receipt=orch.dispatch_action(
                    "project.design.implement",
                    {"project":project,"session_id":sid,
                     "frontend_url":frontend_url,
                     "checks":checks,
                     "screenshot_path":data.get("screenshot_path"),
                     "axe_required":bool(data.get("axe_required",True)),
                     "performance_required":bool(data.get("performance_required",True)),
                     "performance_limits":data.get("performance_limits") or {},
                     "hawkeye_ui_required":bool(data.get("hawkeye_ui_required",True))},
                    project=project,source="pc",actor="design-studio-submit",
                    permissions=("candidate.write","tests.run","model.use"),
                )
                implementation=receipt["result"]
                apply_result={"requested":bool(data.get("apply",True)),"applied":False,"reason":"candidate_not_verified"}
                post_verify=None
                if bool(data.get("apply",True)) and implementation.get("promotable"):
                    promotion_info=implementation.get("promotion") or {}
                    token=str(promotion_info.get("promotion_token") or "")
                    if not token:raise RuntimeError("verified design candidate has no promotion token")
                    try:
                        live=orch.promote_candidate(token,approved=True)
                        apply_result={**live,"requested":True,"applied":bool(live.get("promoted"))}
                        if live.get("promoted"):
                            post_verify=orch.project_perfection.verify_design_candidate(
                                project,policy.root,checks,frontend_url=frontend_url,
                                approve_selected_baseline=False,
                                axe_required=bool(data.get("axe_required",True)),
                                performance_required=bool(data.get("performance_required",True)),
                                performance_limits=dict(data.get("performance_limits") or {}),
                                hawkeye_required=bool(data.get("hawkeye_ui_required",True)),
                            )
                            if not post_verify.get("passed"):
                                orch.promotions.rollback(policy.root,live["backup"],live["diff"])
                                apply_result.update({
                                    "status":"rolled_back_post_verify","applied":False,
                                    "promoted":False,"rolled_back":True,
                                    "reason":"post-promotion verification failed",
                                })
                                orch.memory.audit("design_submit_post_verify","rolled_back",project)
                            else:
                                orch.memory.audit("design_submit_post_verify","verified",project)
                    except PermissionError as exc:
                        apply_result={"requested":True,"applied":False,"status":"approval_blocked","reason":str(exc)}
                annotation={
                    "live_apply":{
                        "requested":apply_result.get("requested"),"applied":apply_result.get("applied"),
                        "status":apply_result.get("status"),"rolled_back":apply_result.get("rolled_back",False),
                        "transaction_id":apply_result.get("transaction_id"),
                        "post_verified":bool(post_verify and post_verify.get("passed")),
                    }
                }
                orch.project_perfection.design_annotate(sid,annotation)
                return self._json(200,{
                    "selection":selection,"implementation":implementation,
                    "apply":apply_result,"post_verification":post_verify,
                })
            except KeyError as exc:return self._json(404,{"error":str(exc)})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,RuntimeError,OSError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/project-perfection/visual-intent":
            payload=dict(data.get("intent") or data)
            try:return self._json(200,orch.project_perfection.visual_edit_intent(payload))
            except ValueError as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/project-perfection/visual-edit/stage":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"visual source editing must run on KRISHNA PC"})
            project=str(data.get("project") or "").strip();sid=str(data.get("session_id") or "").strip()
            if not project or not sid:return self._json(400,{"error":"project and session_id are required"})
            policy=orch.projects.get(project)
            if not policy:return self._json(404,{"error":"project not registered"})
            try:
                x=float(data.get("x"));y=float(data.get("y"))
            except (TypeError,ValueError):return self._json(400,{"error":"x and y are required normalized coordinates"})
            picked=_browser_fabric.element_at(sid,x,y,normalized=True)
            element=picked.get("element")
            if not element:return self._json(404,{"error":"no interactive element found at point","selection":picked})
            action=str(data.get("action") or "").strip().lower()
            instruction=str(data.get("instruction") or "").strip()
            semantic_needed=(
                bool(instruction) and (
                    not action or action in {"remove","add_component"} or
                    (action in {"move","resize","restyle"} and not data.get("style_patch")) or
                    (action=="replace_text" and not data.get("replacement_text"))
                )
            )
            if semantic_needed:
                try:
                    receipt=orch.dispatch_action(
                        "project.visual_edit.implement",
                        {"project":project,"element":element,"instruction":instruction,
                         "from_box":data.get("from_box"),"to_box":data.get("to_box"),
                         "checks":data.get("checks") or [],"frontend_url":data.get("frontend_url"),
                         "hawkeye_ui_required":bool(data.get("hawkeye_ui_required",True))},
                        project=project,source="pc",actor="visual-editor",
                        permissions=("candidate.write","tests.run","model.use","browser.read"),
                    )
                    result=receipt["result"];result["selection"]=picked;result["mode"]="semantic_agent"
                    return self._json(200,result)
                except PermissionError as exc:return self._json(403,{"error":str(exc),"selection":picked})
                except (ValueError,RuntimeError,OSError) as exc:return self._json(400,{"error":str(exc),"selection":picked})
            payload={
                "action":action,"selector":element.get("selector_hint") or element.get("selector"),
                "instruction":instruction,"from_box":data.get("from_box"),"to_box":data.get("to_box"),
                "replacement_text":data.get("replacement_text"),"style_patch":data.get("style_patch"),
                "source_hint":element.get("selector_hint"),
            }
            try:
                result=orch.project_perfection.stage_visual_edit(
                    policy.root,element,payload,list(data.get("checks") or policy.verification_checks or []),
                )
                if not (result.get("edit") or {}).get("applied") and instruction:
                    receipt=orch.dispatch_action(
                        "project.visual_edit.implement",
                        {"project":project,"element":element,"instruction":instruction,
                         "from_box":data.get("from_box"),"to_box":data.get("to_box"),
                         "checks":data.get("checks") or [],"frontend_url":data.get("frontend_url"),
                         "hawkeye_ui_required":bool(data.get("hawkeye_ui_required",True))},
                        project=project,source="pc",actor="visual-editor-fallback",
                        permissions=("candidate.write","tests.run","model.use","browser.read"),
                    )
                    fallback=receipt["result"];fallback["selection"]=picked;fallback["mode"]="semantic_agent_fallback"
                    return self._json(200,fallback)
                result["selection"]=picked;result["mode"]="deterministic"
                if result.get("promotable") and not result.get("promotion"):
                    result["promotion"]=orch._prepare_promotion_impl(project,result["candidate_root"])
                return self._json(200,result)
            except PermissionError as exc:return self._json(403,{"error":str(exc),"selection":picked})
            except (ValueError,RuntimeError,OSError) as exc:return self._json(400,{"error":str(exc),"selection":picked})

        if post_path == "/api/project-perfection/visual-edit/apply":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"visual source editing must run on KRISHNA PC"})
            project=str(data.get("project") or "").strip()
            token=str(data.get("promotion_token") or "").strip()
            if not project or not token:
                return self._json(400,{"error":"project and promotion_token are required"})
            policy=orch.projects.get(project)
            if not policy:return self._json(404,{"error":"project not registered"})
            sid=str(data.get("session_id") or "").strip()
            frontend_url=str(data.get("frontend_url") or "").strip()
            if not frontend_url and sid:
                try:frontend_url=str((_garudanetra.status(sid) or {}).get("current_url") or "").strip()
                except Exception:frontend_url=""
            if not frontend_url:
                return self._json(400,{"error":"frontend_url or live Garudanetra session is required for post-apply verification"})
            checks=list(data.get("checks") or policy.verification_checks or [])
            try:
                live=orch.promote_candidate(token,approved=True)
                if not live.get("promoted"):
                    return self._json(409,{**live,"applied":False,"reason":live.get("reason") or "promotion failed"})
                post=orch.project_perfection.post_apply_verify(
                    project,policy.root,frontend_url,checks,
                    axe_required=bool(data.get("axe_required",True)),
                    performance_required=bool(data.get("performance_required",True)),
                    performance_limits=dict(data.get("performance_limits") or {}),
                    hawkeye_required=bool(data.get("hawkeye_ui_required",True)),
                )
                if not post.get("passed"):
                    orch.promotions.rollback(policy.root,live["backup"],live["diff"])
                    orch.memory.audit("visual_edit_apply","rolled_back",project)
                    return self._json(200,{
                        **live,"applied":False,"promoted":False,"rolled_back":True,
                        "reason":"post-apply verification failed","post_verification":post,
                    })
                orch.memory.audit("visual_edit_apply","verified",project)
                return self._json(200,{**live,"applied":True,"rolled_back":False,"post_verification":post})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,RuntimeError,OSError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/project-perfection/finish":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"project finishing must run on KRISHNA PC"})
            project=str(data.get("project") or "").strip();url=str(data.get("url") or "").strip()
            if not project or not url:return self._json(400,{"error":"project and url are required"})
            if not orch.projects.get(project):return self._json(404,{"error":"project not registered"})
            try:
                receipt=orch.dispatch_action(
                    "project.perfection.finish",
                    {**data,"project":project,"url":url},
                    project=project,source="pc",actor="project-perfection-http",
                    permissions=("candidate.write","tests.run","browser.test"),
                )
                result=receipt["result"]
                mark("PROJECT PERFECTION",f"{project}: {result.get('verdict')}")
                return self._json(200,result)
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,RuntimeError,OSError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/ui-guardian/register":
            try:
                receipt=orch.dispatch_action("ui.guardian.register",data,project=str(data.get("project") or "KRISHNA"),source="pc",actor="legacy-http")
                return self._json(201,receipt["result"])
            except (ValueError,PermissionError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/ui-guardian/evaluate":
            try:
                receipt=orch.dispatch_action("ui.guardian.evaluate",data,source="pc",actor="legacy-http")
                return self._json(200,receipt["result"])
            except KeyError:return self._json(404,{"error":"GUI registry entry not found"})
            except (ValueError,PermissionError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/ui-guardian/transition":
            try:
                receipt=orch.dispatch_action("ui.guardian.transition",data,source="pc",actor="legacy-http")
                return self._json(200,receipt["result"])
            except KeyError:return self._json(404,{"error":"GUI registry entry not found"})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except ValueError as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/garudanetra/session/start":
            project=str(data.get("project") or "KRISHNA").strip() or "KRISHNA"
            payload={"project":project,"url":str(data.get("url") or "").strip(),"mode":str(data.get("mode") or "private").strip().lower()}
            try:
                receipt=orch.dispatch_action("garudanetra.start",payload,project=project,source="pc",actor="legacy-http",approved=bool(data.get("persistent_approved",False)))
                mark("GARUDANETRA LIVE",f'{project}: {payload["mode"]}: {payload["url"][:120]}')
                return self._json(201,receipt["result"])
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,RuntimeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/garudanetra/session/replay":
            sid=str(data.get("session_id") or "").strip()
            if not sid:return self._json(400,{"error":"session_id is required"})
            steps=data.get("steps")
            if steps is not None and not isinstance(steps,list):return self._json(400,{"error":"steps must be an array"})
            try:
                receipt=orch.dispatch_action("garudanetra.replay",{"session_id":sid,"steps":steps},project="KRISHNA",source="pc",actor="legacy-http",approved=bool(data.get("approved",False)))
                return self._json(200,receipt["result"])
            except KeyError as exc:return self._json(404,{"error":str(exc)})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,RuntimeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/garudanetra/session/control":
            sid=str(data.get("session_id") or "").strip();action=str(data.get("action") or "").strip()
            if not sid or not action:return self._json(400,{"error":"session_id and action are required"})
            payload=dict(data.get("payload") or {})
            if action=="upload_attachment":
                chat_id=str(payload.get("chat_id") or "").strip();aid=str(payload.get("attachment_id") or "").strip();selector=str(payload.get("selector") or "").strip()
                if not chat_id or not aid or not selector:return self._json(400,{"error":"upload_attachment requires chat_id, attachment_id and selector"})
                try:meta,path=_attachments.resolve(chat_id,aid)
                except KeyError:return self._json(404,{"error":"attachment not found"})
                action="upload";payload={"selector":selector,"path":str(path)}
            try:
                receipt=orch.dispatch_action("garudanetra.control",{"session_id":sid,"action":action,"payload":payload},project="KRISHNA",source="pc",actor="legacy-http")
                out=receipt["result"]
                if action=="stop":mark("GARUDANETRA STOPPED",sid[:8])
                elif action=="takeover":mark("GARUDANETRA OWNER CONTROL",sid[:8])
                elif action=="resume":mark("GARUDANETRA LIVE",sid[:8])
                return self._json(200,out)
            except KeyError as exc:return self._json(404,{"error":str(exc)})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,RuntimeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path.startswith("/api/narad/webhook/"):
            token=post_path.rsplit("/",1)[-1].strip()
            if not token:return self._json(404,{"error":"webhook token is required"})
            try:return self._json(200,orch.agi.narad.handle_webhook(token,data))
            except PermissionError as exc:return self._json(403,{"error":str(exc)})

        if post_path == "/api/commitments/create":
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

        if post_path == "/api/commitments/update":
            try:
                receipt=orch.dispatch_action("commitment.update",data,source="pc",actor="legacy-http")
                return self._json(200,receipt["result"])
            except (ValueError,KeyError,PermissionError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/autonomy/tick":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"manual autonomy tick must run on KRISHNA PC"})
            try:
                receipt=orch.dispatch_action("autonomy.tick",data,source="pc",actor="legacy-http")
                return self._json(200,receipt["result"])
            except (ValueError,PermissionError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/narad/connections/register":
            try:
                receipt=orch.dispatch_action("narad.connection.register",data,source="pc",actor="legacy-http")
                return self._json(201,receipt["result"])
            except (ValueError,RuntimeError,PermissionError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/narad/connections/register-secret":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"encrypted secret registration must run on KRISHNA PC"})
            try:
                receipt=orch.dispatch_action("narad.connection.secret",data,source="pc",actor="legacy-http",approved=True)
                return self._json(201,receipt["result"])
            except (ValueError,RuntimeError,PermissionError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/narad/connections/delete":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"credential deletion must run on KRISHNA PC"})
            try:
                receipt=orch.dispatch_action("narad.connection.delete",data,source="pc",actor="legacy-http",approved=True)
                return self._json(200,receipt["result"])
            except (ValueError,RuntimeError,PermissionError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/narad/webhooks/provision":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"webhook provisioning must run on KRISHNA PC"})
            try:
                receipt=orch.dispatch_action("narad.webhook.provision",data,source="pc",actor="legacy-http")
                return self._json(201,receipt["result"])
            except (ValueError,RuntimeError,PermissionError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/narad/dead-letters/retry":
            letter_id=str(data.get("letter_id") or "").strip()
            if not letter_id:return self._json(400,{"error":"letter_id is required"})
            receipt=orch.dispatch_action("narad.dead_letter.retry",{"letter_id":letter_id},source="pc",actor="legacy-http",approved=bool(data.get("approved",False)))
            return self._json(200,receipt["result"])

        if post_path == "/api/narad/checkpoints/resume":
            run_id=str(data.get("run_id") or "").strip()
            if not run_id:return self._json(400,{"error":"run_id is required"})
            receipt=orch.dispatch_action("narad.checkpoint.resume",{"run_id":run_id},source="pc",actor="legacy-http",approved=bool(data.get("approved",False)))
            return self._json(200,receipt["result"])

        if post_path == "/api/narad/scheduler/tick":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"manual scheduler tick must run on KRISHNA PC"})
            return self._json(200,orch.agi.narad.run_due())

        if post_path == "/api/narad/workflows/create":
            name=str(data.get("name") or "").strip()
            trigger=data.get("trigger") or {"type":"manual"}
            steps=data.get("steps") or []
            if not name or not isinstance(steps,list): return self._json(400,{"error":"name and steps are required"})
            receipt=orch.dispatch_action("narad.workflow.create",{"name":name,"trigger":trigger,"steps":steps,"permissions":data.get("permissions") or []},source="pc",actor="legacy-http")
            return self._json(201,receipt["result"])

        if post_path == "/api/narad/workflows/promote":
            wid=str(data.get("workflow_id") or "").strip(); state=str(data.get("state") or "").strip()
            if not wid or not state:return self._json(400,{"error":"workflow_id and state are required"})
            receipt=orch.dispatch_action("narad.workflow.promote",{"workflow_id":wid,"state":state,"verified":bool(data.get("verified",False))},source="pc",actor="legacy-http")
            return self._json(200,receipt["result"])

        if post_path == "/api/narad/workflows/execute":
            wid=str(data.get("workflow_id") or "").strip()
            if not wid:return self._json(400,{"error":"workflow_id is required"})
            receipt=orch.dispatch_action("narad.workflow.execute",{"workflow_id":wid,"context":data.get("context") or {}},source="pc",actor="legacy-http",approved=bool(data.get("approved",False)))
            return self._json(200,receipt["result"])

        if post_path == "/api/mobile/pair/request":
            device = str(data.get("device_id", "")).strip()
            if not device:
                return self._json(400, {"error": "device_id required"})
            return self._json(200, _pairing.request(
                device,str(data.get("name","KRISHNA Mobile"))[:128],
                str(data.get("credential_sha256") or ""),
            ))

        if post_path == "/api/mobile/pair/approve":
            if self.client_address[0] not in ("127.0.0.1", "::1"):
                return self._json(403, {"error": "approval must be performed on KRISHNA PC"})
            try:
                receipt=orch.dispatch_action("mobile.pair.approve",data,source="pc",actor="legacy-http",approved=True)
                return self._json(200,receipt["result"])
            except (PermissionError,ValueError) as exc:return self._json(400,{"error":str(exc)})

        if post_path in ("/api/core/event", "/api/neural/event"):
            source = str(data.get("source", "unknown")).strip() or "unknown"
            kind = str(data.get("kind", "event")).strip() or "event"
            detail = str(data.get("detail", ""))
            severity = str(data.get("severity", "info"))
            project = str(data.get("project", "system"))
            return self._json(200, orch.handle_event(
                source, kind, detail, severity=severity, project=project,
                payload=data.get("payload") or {},
            ))

        if post_path in ("/api/mobile-log",):
            event = str(data.get("event", ""))
            return self._json(200, orch.handle_event(
                "mobile", "mobile_log", event, severity="info", project="system",
            ))

        if post_path == "/api/mobile/control":
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

        if post_path in ("/v1/chat", "/api/core/chat"):
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
                set_current_activity("Idle")
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
                set_current_activity("Error")
                return self._json(500, {"error": str(exc)})

        if post_path == "/api/specialists/index":
            try:
                return self._json(200, _specialists.index(data.get("source_root") or None))
            except ValueError as exc:
                return self._json(400, {"error": str(exc)})

        if post_path == "/api/specialists/select":
            task = str(data.get("task", "")).strip()
            if not task:
                return self._json(400, {"error": "task is required"})
            project=str(data.get("project") or "KRISHNA").strip() or "KRISHNA"
            plan=_team_planner.plan(task,project,int(data.get("limit",5)))
            return self._json(200, {"selected":plan["agency_advisors"],"team":plan})

        if post_path == "/api/specialist-teams/plan":
            task=str(data.get("task") or "").strip()
            if not task:return self._json(400,{"error":"task is required"})
            return self._json(200,_team_planner.plan(task,str(data.get("project") or "KRISHNA"),int(data.get("external_limit") or 6)))

        if post_path == "/api/specialists/context":
            try:
                return self._json(200, _specialists.context(str(data.get("id", ""))))
            except KeyError:
                return self._json(404, {"error": "specialist not found"})
            except PermissionError as exc:
                return self._json(403, {"error": str(exc)})

        if post_path == "/api/plugins/add":
            try:
                receipt=orch.dispatch_action("plugin.add",data,project=str(data.get("project") or "KRISHNA"),source="pc",actor="plugins-ui",permissions=("plugin.write",))
                return self._json(200,receipt["result"])
            except (ValueError,PermissionError) as exc:
                return self._json(403 if isinstance(exc,PermissionError) else 400,{"error":str(exc)})

        if post_path == "/api/plugins/enable":
            try:
                receipt=orch.dispatch_action(
                    "plugin.enable",{"id":str(data.get("id") or "").strip(),"enabled":bool(data.get("enabled",True))},
                    project=str(data.get("project") or "KRISHNA"),source="pc",actor="plugins-ui",
                    approved=bool(data.get("approved",False)),permissions=("plugin.write",),
                )
                return self._json(200,receipt["result"])
            except KeyError:return self._json(404,{"error":"plugin not found"})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})

        if post_path == "/api/plugins/credential":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"plugin credential registration must run on KRISHNA PC"})
            try:
                receipt=orch.dispatch_action("plugin.credential.set",data,source="pc",actor="legacy-http",approved=True)
                return self._json(201,receipt["result"])
            except KeyError:return self._json(404,{"error":"plugin not found"})
            except (ValueError,RuntimeError,PermissionError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/plugins/credential/delete":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"plugin credential deletion must run on KRISHNA PC"})
            try:
                receipt=orch.dispatch_action("plugin.credential.delete",data,source="pc",actor="legacy-http",approved=True)
                return self._json(200,receipt["result"])
            except KeyError:return self._json(404,{"error":"plugin not found"})
            except (ValueError,RuntimeError,PermissionError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/plugins/remove":
            try:
                receipt=orch.dispatch_action(
                    "plugin.remove",{"id":str(data.get("id") or "").strip()},
                    project=str(data.get("project") or "KRISHNA"),source="pc",actor="plugins-ui",
                    approved=bool(data.get("approved",False)),permissions=("plugin.write",),
                )
                return self._json(200,receipt["result"])
            except KeyError:return self._json(404,{"error":"plugin not found"})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})

        if post_path == "/api/chats/create":
            project=str(data.get("project","general")).strip() or "general"
            title=str(data.get("title","New chat")).strip() or "New chat"
            try:
                out=orch.dispatch_action("chat.create",{"project":project,"title":title},project=project,source="pc",actor="legacy-http")
                return self._json(200,out["result"])
            except KeyError:return self._json(404,{"error":"project not registered"})

        if post_path == "/api/chats/move":
            chat_id=str(data.get("chat_id","")).strip();project=str(data.get("project","")).strip()
            if not chat_id or not project:return self._json(400,{"error":"chat_id and project are required"})
            try:
                out=orch.dispatch_action("chat.move",{"chat_id":chat_id,"project":project},project=project,source="pc",actor="legacy-http")
                return self._json(200,out["result"])
            except KeyError as exc:return self._json(404,{"error":str(exc)})
            except ValueError as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/chats/delete":
            chat_id=str(data.get("chat_id","")).strip()
            if not chat_id:return self._json(400,{"error":"chat_id is required"})
            try:
                out=orch.dispatch_action("chat.delete",{"chat_id":chat_id},project="KRISHNA",source="pc",actor="legacy-http")
                return self._json(200,out["result"])
            except KeyError as exc:return self._json(404,{"error":str(exc)})

        if post_path == "/api/chats/rename":
            chat_id=str(data.get("chat_id","")).strip();title=str(data.get("title","")).strip()
            if not chat_id or not title:return self._json(400,{"error":"chat_id and title are required"})
            try:
                out=orch.dispatch_action("chat.rename",{"chat_id":chat_id,"title":title},project="KRISHNA",source="pc",actor="legacy-http")
                return self._json(200,out["result"])
            except KeyError as exc:return self._json(404,{"error":str(exc)})
            except ValueError as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/wearables/register":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"wearable registration must run on KRISHNA PC"})
            try:
                return self._json(201,_wearables.register(
                    str(data.get("name") or ""),str(data.get("kind") or ""),data.get("capabilities") or [],
                    str(data.get("provider") or "generic"),False,
                ))
            except ValueError as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/wearables/verify":
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

        if post_path == "/api/resilience/worker/clear-quarantine":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"worker quarantine changes must run on KRISHNA PC"})
            name=str(data.get("worker") or "").strip()
            if not name:return self._json(400,{"error":"worker is required"})
            try:return self._json(200,orch.agi.workers.clear_quarantine(name))
            except KeyError:return self._json(404,{"error":"worker not registered"})

        if post_path == "/api/resilience/models/unload":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"model unload must run on KRISHNA PC"})
            model=str(data.get("model") or "").strip()
            try:return self._json(200,_model_memory.unload(model) if model else _model_memory.unload_all())
            except (ValueError,RuntimeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/voice/wake/start":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"microphone wake service must be controlled on KRISHNA PC"})
            try:return self._json(200,_voice.wake.start())
            except RuntimeError as exc:return self._json(503,{"error":str(exc),"status":_voice.status()})

        if post_path == "/api/voice/wake/stop":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"microphone wake service must be controlled on KRISHNA PC"})
            return self._json(200,_voice.wake.stop())

        if post_path == "/api/voice/tts":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"local TTS must be requested on KRISHNA PC"})
            text_value=str(data.get("text") or "").strip()
            language=str(data.get("language") or "or").strip().lower()
            if not text_value:return self._json(400,{"error":"text is required"})
            if language not in {"en","hi","or"}:return self._json(400,{"error":"language must be one of: en, hi, or"})
            configured=set(_voice.tts.status().get("languages") or [])
            if language not in configured:
                fallback="browser/OS local speech" if language=="en" else "configured local voice worker"
                return self._json(503,{"error":f"local TTS language is not configured: {language}; fallback={fallback}","configured_languages":sorted(configured)})
            out_dir=RUNTIME_ROOT/"state"/"voice";out_dir.mkdir(parents=True,exist_ok=True)
            audio_id=str(uuid.uuid4());out_path=out_dir/(audio_id+".wav")
            try:
                resolved=_voice.tts.speak(text_value,out_path,language=language)
                return self._json(200,{"output_path":resolved,"audio_id":audio_id,"audio_url":"/api/voice/audio?id="+audio_id,
                                       "language":language,"provider":"ai4bharat-indic-tts"})
            except (RuntimeError,ValueError) as exc:return self._json(503,{"error":str(exc)})

        if post_path == "/api/voice/stt":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"local STT must be requested on KRISHNA PC"})
            audio_path=str(data.get("audio_path") or "").strip()
            language=str(data.get("language") or "or").strip().lower()
            if not audio_path:return self._json(400,{"error":"audio_path is required"})
            if language not in {"hi","or"}:return self._json(400,{"error":"local IndicConformer STT language must be one of: hi, or"})
            try:return self._json(200,{"text":_voice.stt.transcribe(audio_path,language=language),"provider":"ai4bharat-indicconformer","language":language})
            except (RuntimeError,ValueError,FileNotFoundError) as exc:return self._json(503,{"error":str(exc)})

        if post_path == "/api/models/gateways/register":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"model gateway secrets must be configured on KRISHNA PC"})
            try:
                receipt=orch.dispatch_action("model.gateway.register",data,source="pc",actor="legacy-http",approved=True)
                return self._json(201,receipt["result"])
            except (ValueError,RuntimeError,PermissionError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/models/gateways/delete":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"model gateway deletion must run on KRISHNA PC"})
            try:
                receipt=orch.dispatch_action("model.gateway.delete",data,source="pc",actor="legacy-http",approved=True)
                return self._json(200,receipt["result"])
            except (ValueError,RuntimeError,PermissionError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/action-bus/dispatch":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"direct Shared Action Bus dispatch is local-PC only; mobile uses authenticated transport"})
            action=str(data.get("action") or "").strip()
            if not action:return self._json(400,{"error":"action is required"})
            try:
                out=orch.dispatch_action(
                    action,data.get("payload") or {},project=str(data.get("project") or "KRISHNA"),
                    source="pc",actor=str(data.get("actor") or "ui"),
                    approved=bool(data.get("approved",False)),
                    permissions=data.get("permissions") or [],
                    idempotency_key=str(data.get("idempotency_key") or "").strip() or None,
                )
                return self._json(200,out)
            except KeyError as exc:return self._json(404,{"error":str(exc)})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/action-bus/rollback":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"direct Shared Action Bus rollback is local-PC only"})
            action_id=str(data.get("action_id") or "").strip()
            if not action_id:return self._json(400,{"error":"action_id is required"})
            try:return self._json(200,orch.rollback_dispatched_action(action_id,source="pc",actor="ui",approved=bool(data.get("approved",False))))
            except KeyError as exc:return self._json(404,{"error":str(exc)})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except ValueError as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/missions/create":
            payload={
                "goal":str(data.get("goal") or ""),"project_id":str(data.get("project_id") or data.get("project") or "KRISHNA"),
                "parent_mission_id":data.get("parent_mission_id"),"session_id":data.get("session_id"),
                "priority":int(data.get("priority") or 50),"assigned_agents":data.get("assigned_agents") or [],
                "required_tools":data.get("required_tools") or [],"permission_profile":str(data.get("permission_profile") or "default"),
                "resource_budget":data.get("resource_budget") or {},"metadata":data.get("metadata") or {},
            }
            try:
                receipt=orch.dispatch_action("mission.create",payload,project=payload["project_id"],source="pc",actor="mission-http",permissions=("mission.write",))
                return self._json(201,receipt["result"])
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/missions/transition":
            mission_id=str(data.get("mission_id") or "").strip()
            if not mission_id:return self._json(400,{"error":"mission_id is required"})
            try:
                receipt=orch.dispatch_action("mission.transition",data,project=str(data.get("project") or "KRISHNA"),source="pc",actor="mission-http",permissions=("mission.write",))
                return self._json(200,receipt["result"])
            except KeyError as exc:return self._json(404,{"error":str(exc)})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/missions/checkpoint":
            mission_id=str(data.get("mission_id") or "").strip()
            if not mission_id:return self._json(400,{"error":"mission_id is required"})
            try:
                receipt=orch.dispatch_action("mission.checkpoint",data,project=str(data.get("project") or "KRISHNA"),source="pc",actor="mission-http",permissions=("mission.write","evidence.write"))
                return self._json(201,receipt["result"])
            except KeyError as exc:return self._json(404,{"error":str(exc)})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/resource-locks/acquire":
            try:
                receipt=orch.dispatch_action("resource.lock.acquire",data,project=str(data.get("project") or "KRISHNA"),source="pc",actor="lock-http",permissions=("resource.lock",))
                return self._json(201,receipt["result"])
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,RuntimeError,TypeError) as exc:return self._json(409 if isinstance(exc,RuntimeError) else 400,{"error":str(exc)})

        if post_path == "/api/resource-locks/release":
            try:
                receipt=orch.dispatch_action("resource.lock.release",data,project=str(data.get("project") or "KRISHNA"),source="pc",actor="lock-http",permissions=("resource.lock",))
                return self._json(200,receipt["result"])
            except KeyError as exc:return self._json(404,{"error":str(exc)})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/jobs/submit":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"direct job submission is local-PC only; remote clients use authenticated dispatch"})
            action=str(data.get("action") or "").strip()
            if not action:return self._json(400,{"error":"action is required"})
            try:
                return self._json(202,orch.sudarshan.job(
                    action,data.get("payload") or {},project=str(data.get("project") or "KRISHNA"),
                    actor=str(data.get("actor") or "ui-job"),permissions=data.get("permissions") or [],
                    approved=bool(data.get("approved",False)),
                    idempotency_key=str(data.get("idempotency_key") or "").strip() or None,
                ))
            except KeyError as exc:return self._json(404,{"error":str(exc)})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/dispatch":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"direct dispatch is local-PC only"})
            action=str(data.get("action") or "").strip()
            if not action:return self._json(400,{"error":"action is required"})
            try:
                return self._json(200,orch.dispatcher.dispatch(
                    str(data.get("target") or "action"),action,data.get("payload") or {},
                    project=str(data.get("project") or "KRISHNA"),
                    actor=str(data.get("actor") or "ui"),
                    agent_id=str(data.get("agent_id") or "").strip() or None,
                    permissions=data.get("permissions") or [],
                    approved=bool(data.get("approved",False)),
                    idempotency_key=str(data.get("idempotency_key") or "").strip() or None,
                ))
            except KeyError as exc:return self._json(404,{"error":str(exc)})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/protocols/mcp/call":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"MCP adapter test endpoint is local-PC only"})
            tool=str(data.get("tool") or "").strip()
            if not tool:return self._json(400,{"error":"tool is required"})
            try:return self._json(200,orch.protocols.mcp_call(
                tool,data.get("args") or {},principal=str(data.get("principal") or "mcp-client"),
                project=str(data.get("project") or "KRISHNA"),
                permissions=data.get("permissions") or [],approved=bool(data.get("approved",False)),
                request_id=str(data.get("request_id") or "").strip() or None,
            ))
            except KeyError as exc:return self._json(404,{"error":str(exc)})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/protocols/a2a/dispatch":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"A2A adapter test endpoint is local-PC only"})
            try:return self._json(200,orch.protocols.a2a_dispatch(data))
            except KeyError as exc:return self._json(404,{"error":str(exc)})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/projects/register":
            payload={
                "name":str(data.get("name","")).strip(),"root":str(data.get("root","")).strip(),
                "privacy":str(data.get("privacy","local_only")),
                "allowed_actions":data.get("allowed_actions") or [],
                "verification_checks":data.get("verification_checks") or [],
                "metadata":data.get("metadata") or {},"role":str(data.get("role") or "active"),
            }
            try:
                out=orch.dispatch_action("project.register",payload,project=payload["name"] or "KRISHNA",source="pc",actor="legacy-http")
                return self._json(200,out["result"])
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})

        if post_path == "/api/projects/unregister":
            name=str(data.get("name","")).strip()
            try:
                out=orch.dispatch_action("project.unregister",{"name":name},project=name or "KRISHNA",source="pc",actor="legacy-http")
                return self._json(200,out["result"])
            except KeyError:return self._json(404,{"error":"project not registered"})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except ValueError as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/e2e/register":
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

        if post_path == "/api/projects/index":
            try:
                receipt=orch.dispatch_action("project.index",data,project=str(data.get("project") or "KRISHNA"),source="pc",actor="legacy-http")
                return self._json(200,receipt["result"])
            except KeyError:return self._json(404,{"error":"project not registered"})
            except (ValueError,PermissionError) as exc:return self._json(400,{"error":str(exc)})

        if post_path in ("/api/hawkeye/live/start", "/api/bhumiputra/live/start"):
            project=str(data.get("project") or "KRISHNA").strip() or "KRISHNA"
            payload={"project":project,"purpose":str(data.get("purpose") or "live field scan"),
                     "coordinates":data.get("coordinates") or {},
                     "scene_hint":str(data.get("scene_hint") or "auto")}
            session=orch.hawkeye.start_live_session(
                project=project,purpose=payload["purpose"],coordinates=payload["coordinates"],scene_hint=payload["scene_hint"]
            )
            session["diagnostic"]=orch.hawkeye_diagnostic.should_activate(payload["purpose"])
            if session["diagnostic"]:session["diagnostic_specialist"]="HAWKEYE DIAGNOSTIC"
            return self._json(201,session)

        if post_path == "/api/hawkeye/reference/register":
            reference_id=str(data.get("reference_id") or "").strip()
            kind=str(data.get("kind") or "").strip().lower()
            if not reference_id or not kind:return self._json(400,{"error":"reference_id and kind are required"})
            try:
                if isinstance(data.get("data"),dict):
                    out=orch.hawkeye_reference.register(reference_id,kind,data["data"],verified=bool(data.get("verified",False)),source_name=str(data.get("source_name") or ""))
                else:
                    out=orch.hawkeye_reference.register_source(reference_id,kind,str(data.get("source_text") or ""),verified=bool(data.get("verified",False)),source_name=str(data.get("source_name") or ""))
                return self._json(201,out)
            except (ValueError,TypeError,json.JSONDecodeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/hawkeye/reference/align":
            reference_id=str(data.get("reference_id") or "").strip();anchors=data.get("anchors") or []
            if not reference_id:return self._json(400,{"error":"reference_id is required"})
            try:return self._json(200,orch.hawkeye_reference.overlay(reference_id,anchors))
            except KeyError:return self._json(404,{"error":"reference not found"})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except ValueError as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/hawkeye/learn/capture":
            utterance=str(data.get("utterance") or "").strip()
            source_type=str(data.get("source_type") or "mobile").strip()
            source_ref=str(data.get("source_ref") or "").strip()
            modalities=data.get("modalities") or []
            if not isinstance(modalities,list):return self._json(400,{"error":"modalities must be an array"})
            subject=str(data.get("subject") or "").strip()
            analysis=str(data.get("analysis") or "").strip()
            confidence=float(data.get("confidence") or 0.0)
            evidence_state=str(data.get("evidence_state") or "UNKNOWN")
            out=orch.universal_learning.ingest(
                utterance=utterance,source_type=source_type,source_ref=source_ref,
                modalities=modalities,subject=subject,confidence=confidence,
                analysis=analysis,evidence_state=evidence_state,
            )
            if "audio" in [str(x).lower() for x in modalities]:
                out["sound"]=orch.universal_learning.classify_sound_request(utterance,data.get("audio_observations") or {})
            origin="pc" if source_type.lower()=="pc" else "mobile"
            modality=(str(modalities[0]).lower() if len(modalities)==1 else ("multimodal" if modalities else "text"))
            brahma_evidence=[{"source_ref":source_ref,"source_type":source_type}] if source_ref else []
            out["brahma"]=orch.brahma.intake(
                source=origin,
                topic=subject or utterance or "Hawkeye learning observation",
                content=analysis or utterance,
                modality=modality,
                evidence=brahma_evidence,
                provenance={"source_ref":source_ref,"source_type":source_type,"hawkeye_learning_id":out.get("learning_id")},
                confidence=confidence,
                novelty=float(data.get("novelty") if data.get("novelty") is not None else 0.5),
                quality=float(data.get("quality") if data.get("quality") is not None else max(confidence,0.5)),
                importance=float(data.get("importance") if data.get("importance") is not None else (0.8 if subject else 0.5)),
                evidence_status=evidence_state.lower(),
            )
            return self._json(201,out)

        if post_path == "/api/hawkeye/evidence/ingest":
            mobile_session_id=str(data.get("session_id") or "").strip() or "mobile-evidence"
            raw_b64=str(data.get("data_b64") or "").strip()
            if not raw_b64:return self._json(400,{"error":"data_b64 is required"})
            try:raw=base64.b64decode(raw_b64,validate=True)
            except Exception:return self._json(400,{"error":"invalid base64 Hawkeye evidence"})
            content_type=str(data.get("content_type") or "application/octet-stream").split(";",1)[0].strip().lower()
            modality=str(data.get("modality") or (content_type.split("/",1)[0] if "/" in content_type else "unknown")).strip().lower()
            if modality not in {"image","audio","video"}:return self._json(400,{"error":"modality must be image, audio, or video"})
            sensor_context=data.get("sensor_context") or {}
            if not isinstance(sensor_context,dict):return self._json(400,{"error":"sensor_context must be an object"})
            goal=str(data.get("goal") or "mobile curated evidence").strip()
            try:
                try:session=orch.hawkeye.get_live_session(mobile_session_id);session_id=mobile_session_id
                except KeyError:
                    session=orch.hawkeye.start_live_session(project="KRISHNA",purpose=goal,coordinates={},scene_hint="auto")
                    session_id=session["session_id"]
                sensor_context=dict(sensor_context);sensor_context["mobile_session_id"]=mobile_session_id;sensor_context["curator_selected"]=True
                pc_evidence=orch.hawkeye.store_mobile_evidence(session_id,raw,content_type,sensor_context)
                diagnostic=orch.hawkeye_diagnostic.should_activate(goal)
                if modality=="image":
                    if diagnostic:
                        prompt=orch.hawkeye_diagnostic.vision_prompt(goal=goal,sensor_context=sensor_context)
                        with orch.governor.job(timeout=0):vision=_vision.analyze_bytes(raw,content_type,prompt)
                        result=orch.hawkeye_diagnostic.record_model_result(session_id,vision.get("analysis") or "",goal=goal,sensor_context=sensor_context,model=vision.get("model") or "")
                        field=orch.hawkeye.record_live_analysis(session_id,result["analysis"],model=vision.get("model"),sensor_context=sensor_context,frame_meta={"content_type":content_type,"diagnostic":True,"curated":True})
                        result["frame_count"]=field["frame_count"]
                    else:
                        prompt=orch.hawkeye.live_prompt(scene_hint=session.get("scene_hint") or "auto",user_goal=goal,sensor_context=sensor_context)
                        with orch.governor.job(timeout=0):vision=_vision.analyze_bytes(raw,content_type,prompt)
                        field=orch.hawkeye.record_live_analysis(session_id,vision.get("analysis") or "",model=vision.get("model"),sensor_context=sensor_context,frame_meta={"content_type":content_type,"diagnostic":False,"curated":True})
                        result={"diagnostic":False,"analysis":vision.get("analysis") or "","confidence":0.0,"evidence_state":"OBSERVED","model":vision.get("model"),"local":bool(vision.get("local",True)),"frame_count":field["frame_count"]}
                else:
                    previous={}
                    try:previous=(orch.hawkeye_diagnostic.get_session(session_id).get("last_result") or {})
                    except KeyError:pass
                    result={"diagnostic":diagnostic,"analysis":f"Curated {modality} evidence retained for bounded specialist review.","confidence":float(previous.get("confidence") or 0.0),"evidence_state":"OBSERVED","modality":modality}
                    if previous:
                        result["prior_visual_analysis"]=str(previous.get("analysis") or "")[:2000]
                        result["needs_reference"]=bool(previous.get("needs_reference",False))
                        result["warnings"]=list(previous.get("warnings") or [])[:8]
                result["session_id"]=session_id;result["pc_session_id"]=session_id;result["mobile_session_id"]=mobile_session_id
                result["pc_evidence"]=pc_evidence
                if diagnostic:
                    result["specialist_dispatch"]=orch.hawkeye_diagnostic.maybe_dispatch_worker(session_id,result,goal=goal,modality=modality,evidence=pc_evidence)
                evidence_ref={
                    "observation_id":sensor_context.get("mobile_observation_id") or sensor_context.get("observation_id"),
                    "pc_evidence_id":pc_evidence.get("evidence_id") if isinstance(pc_evidence,dict) else None,
                    "sha256":pc_evidence.get("sha256") if isinstance(pc_evidence,dict) else None,
                    "modality":modality,
                }
                result["brahma"]=orch.brahma.intake(
                    source="mobile",topic=goal,content=str(result.get("analysis") or ""),
                    modality=modality,evidence=[evidence_ref],
                    provenance={
                        "observation_id":evidence_ref.get("observation_id"),
                        "session_id":session_id,"mobile_session_id":mobile_session_id,
                        "source_ref":evidence_ref.get("sha256"),
                    },
                    confidence=float(result.get("confidence") or 0.0),
                    novelty=float(sensor_context.get("curator_novelty") or 0.5),
                    quality=float(sensor_context.get("curator_quality") or 0.5),
                    importance=0.9 if diagnostic else 0.6,
                    evidence_status=str(result.get("evidence_state") or "candidate").lower(),
                )
                result=orch.hawkeye.enrich_result(
                    session_id,result,sensor_context=sensor_context,goal=goal,modality=modality
                )
                return self._json(200,result)
            except ValueError as exc:return self._json(400,{"error":str(exc)})
            except RuntimeError as exc:return self._json(503,{"error":str(exc)})

        if post_path in ("/api/hawkeye/live/frame", "/api/bhumiputra/live/frame"):
            session_id=str(data.get("session_id") or "").strip()
            if not session_id:return self._json(400,{"error":"session_id is required"})
            raw_b64=str(data.get("data_b64") or "").strip()
            if not raw_b64:return self._json(400,{"error":"data_b64 is required"})
            try:raw=base64.b64decode(raw_b64,validate=True)
            except Exception:return self._json(400,{"error":"invalid base64 camera frame"})
            if len(raw)>5*1024*1024:return self._json(400,{"error":"camera frame exceeds 5 MB"})
            content_type=str(data.get("content_type") or "image/jpeg").split(";",1)[0].strip().lower()
            sensor_context=data.get("sensor_context") or {}
            if not isinstance(sensor_context,dict):return self._json(400,{"error":"sensor_context must be an object"})
            try:session=orch.hawkeye.get_live_session(session_id)
            except KeyError:return self._json(404,{"error":"live session not found"})
            goal=str(data.get("goal") or session.get("purpose") or "live field scan").strip()
            try:
                pc_evidence=None
                if bool(sensor_context.get("curator_selected",False)):
                    pc_evidence=orch.hawkeye.store_mobile_evidence(session_id,raw,content_type,sensor_context)
                if orch.hawkeye_diagnostic.should_activate(goal):
                    prompt=orch.hawkeye_diagnostic.vision_prompt(goal=goal,sensor_context=sensor_context)
                    with orch.governor.job(timeout=0):
                        vision=_vision.analyze_bytes(raw,content_type,prompt)
                    result=orch.hawkeye_diagnostic.record_model_result(
                        session_id,vision.get("analysis") or "",goal=goal,sensor_context=sensor_context,model=vision.get("model") or ""
                    )
                    field=orch.hawkeye.record_live_analysis(
                        session_id,result["analysis"],model=vision.get("model"),sensor_context=sensor_context,
                        frame_meta={"content_type":content_type,"diagnostic":True,"diagram_mode":result.get("diagram_mode")},
                    )
                    result["session_id"]=session_id
                    result["frame_count"]=field["frame_count"]
                    if pc_evidence is not None:result["pc_evidence"]=pc_evidence
                    result=orch.hawkeye.enrich_result(
                        session_id,result,sensor_context=sensor_context,goal=goal,modality="image"
                    )
                    return self._json(200,result)
                prompt=orch.hawkeye.live_prompt(
                    scene_hint=session.get("scene_hint") or "auto",user_goal=goal,sensor_context=sensor_context
                )
                with orch.governor.job(timeout=0):
                    vision=_vision.analyze_bytes(raw,content_type,prompt)
                field=orch.hawkeye.record_live_analysis(
                    session_id,vision.get("analysis") or "",model=vision.get("model"),sensor_context=sensor_context,
                    frame_meta={"content_type":content_type,"diagnostic":False},
                )
                out={
                    "session_id":session_id,"frame_count":field["frame_count"],"diagnostic":False,
                    "analysis":vision.get("analysis") or "","confidence":0.0,"evidence_state":"OBSERVED",
                    "model":vision.get("model"),"local":bool(vision.get("local",True)),
                }
                if pc_evidence is not None:out["pc_evidence"]=pc_evidence
                out=orch.hawkeye.enrich_result(
                    session_id,out,sensor_context=sensor_context,goal=goal,modality="image"
                )
                return self._json(200,out)
            except ValueError as exc:return self._json(400,{"error":str(exc)})
            except RuntimeError as exc:return self._json(503,{"error":str(exc)})

        if post_path == "/api/hawkeye/geo/survey":
            site_id=str(data.get("site_id") or "field-site").strip() or "field-site"
            boundary=data.get("boundary") or []
            try:return self._json(200,orch.hawkeye_geo.survey_metrics(site_id,boundary))
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/hawkeye/geo/geofence":
            try:return self._json(200,orch.hawkeye_geo.geofence(data.get("boundary") or [],data.get("point")))
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/hawkeye/geo/volume":
            site_id=str(data.get("site_id") or "field-site").strip() or "field-site"
            try:return self._json(200,orch.hawkeye_geo.volume_estimate(site_id,data.get("boundary") or [],data.get("depth_samples") or []))
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/hawkeye/geo/route":
            site_id=str(data.get("site_id") or "field-site").strip() or "field-site"
            try:return self._json(200,orch.hawkeye_geo.route_assessment(site_id,data.get("segments") or [],data.get("vehicle") or {}))
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/hawkeye/geo/export":
            site_id=str(data.get("site_id") or "field-site").strip() or "field-site"
            try:return self._json(200,orch.hawkeye_geo.export_boundary(site_id,data.get("boundary") or [],str(data.get("format") or "geojson")))
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/investigate":
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

        if post_path == "/api/attachments":
            try:
                receipt=orch.dispatch_action("attachment.add",data,source="pc",actor="legacy-http")
                return self._json(201,receipt["result"])
            except KeyError:return self._json(404,{"error":"chat not found"})
            except (ValueError,TypeError,PermissionError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/attachments/analyze":
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

        if post_path == "/api/plugins/execute":
            try:
                payload={
                    "plugin_id":str(data.get("plugin_id") or ""),"project":str(data.get("project") or "KRISHNA"),
                    "operation":str(data.get("operation") or "get"),"payload":data.get("payload") or {},
                    "auth_env":data.get("auth_env"),
                }
                receipt=orch.dispatch_action(
                    "plugin.execute",payload,project=payload["project"],source="pc",actor="plugins-ui",
                    approved=bool(data.get("approved",False)),permissions=("plugin.execute","network.external"),
                )
                return self._json(200,receipt["result"])
            except KeyError:return self._json(404,{"error":"plugin not found"})
            except (ValueError,PermissionError) as exc:return self._json(403 if isinstance(exc,PermissionError) else 400,{"error":str(exc)})
            except RuntimeError as exc:return self._json(502,{"error":str(exc)})
            except Exception as exc:return self._json(502,{"error":f"plugin request failed: {type(exc).__name__}: {exc}"})

        if post_path == "/api/brahmagyan/projects/add":
            project_id=str(data.get("project_id") or "").strip()
            name=str(data.get("name") or "").strip()
            mission=str(data.get("mission") or "").strip()
            if not project_id or not name or not mission:
                return self._json(400,{"error":"project_id, name and mission are required"})
            try:
                return self._json(200,orch.brahmagyan_project_add(
                    project_id,name,mission,
                    data.get("subjects") or [],
                    data.get("leads") or [],
                    data.get("support") or [],
                    str(data.get("safety") or "standard_frontier_research"),
                ))
            except KeyError as exc:return self._json(404,{"error":str(exc)})
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/brahmagyan/science/sync":
            try:
                return self._json(200,orch.brahmagyan_science_sync(
                    bool(data.get("include_topics",True)),
                    data.get("topic_limit"),
                ))
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})
            except RuntimeError as exc:return self._json(503,{"error":str(exc)})

        if post_path == "/api/brahmagyan/science/frontier":
            subject=str(data.get("subject") or "").strip()
            if not subject:return self._json(400,{"error":"subject is required"})
            project=str(data.get("project") or "KRISHNA").strip() or "KRISHNA"
            kwargs={
                "field":data.get("field"),
                "domain":data.get("domain"),
                "question":data.get("question"),
                "rishi_id":data.get("rishi_id"),
                "stakes":str(data.get("stakes") or "normal"),
                "privacy":data.get("privacy"),
                "source_limit":int(data.get("source_limit") or 6),
                "max_perspectives":int(data.get("max_perspectives") or 5),
                "max_claims":int(data.get("max_claims") or 5),
                "question_limit":int(data.get("question_limit") or 8),
                "auto_propose":bool(data.get("auto_propose",True)),
                "node_id":data.get("node_id"),
            }
            try:return self._json(200,orch.brahmagyan_science_frontier(subject,project,**kwargs))
            except KeyError as exc:return self._json(404,{"error":str(exc)})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})
            except RuntimeError as exc:return self._json(503,{"error":str(exc)})

        if post_path == "/api/brahmagyan/science/seed":
            subject=str(data.get("subject") or "").strip()
            if not subject:return self._json(400,{"error":"subject is required"})
            project=str(data.get("project") or "KRISHNA").strip() or "KRISHNA"
            try:
                out=orch.dispatch_action(
                    "brahmagyan.science.frontier.seed",
                    {
                        "project":project,"subject":subject,
                        "field":data.get("field"),"domain":data.get("domain"),
                        "limit":int(data.get("limit") or 8),
                    },
                    project=project,source="pc",actor="science-atlas-http",
                    permissions=("memory.write",),
                )
                return self._json(200,out.get("result") or {})
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/brahmagyan/science/tick":
            if self.client_address[0] not in ("127.0.0.1","::1"):
                return self._json(403,{"error":"science frontier tick must run on KRISHNA PC"})
            snap=pc_observer.snapshot()
            try:return self._json(200,orch.brahmagyan_science_background_tick(
                snap.get("cpu_percent") or 0.0,
                snap.get("memory_percent") or 0.0,
            ))
            except RuntimeError as exc:return self._json(503,{"error":str(exc)})

        if post_path == "/api/brahmagyan/live/run":
            project=str(data.get("project") or "KRISHNA").strip() or "KRISHNA"
            topic=str(data.get("topic") or "").strip()
            if not topic:return self._json(400,{"error":"topic is required"})
            try:
                return self._json(200,orch.brahmagyan_live_run(
                    project,topic,str(data.get("question") or ""),
                    rishi_id=data.get("rishi_id"),
                    knowledge_track=str(data.get("knowledge_track") or "general"),
                    stakes=str(data.get("stakes") or "normal"),
                    privacy=data.get("privacy"),
                    source_limit=int(data.get("source_limit") or 6),
                    max_perspectives=int(data.get("max_perspectives") or 4),
                    max_claims=int(data.get("max_claims") or 5),
                    auto_propose=bool(data.get("auto_propose",True)),
                ))
            except KeyError as exc:return self._json(404,{"error":str(exc)})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})
            except RuntimeError as exc:return self._json(503,{"error":str(exc)})

        if post_path == "/api/software-factory/create":
            project=str(data.get("project") or "").strip(); goal=str(data.get("goal") or "").strip()
            if not project or not goal:return self._json(400,{"error":"project and goal are required"})
            try:return self._json(201,orch.create_software_project_team(project,goal,data.get("deadline_hours"),data.get("start_at"),data.get("end_at")))
            except (ValueError,KeyError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/software-factory/workers/request":
            try:return self._json(201,orch.request_ephemeral_workers(str(data.get("project") or ""),str(data.get("manager") or ""),str(data.get("role") or ""),int(data.get("count") or 1),str(data.get("reason") or ""),data.get("hr_snapshot"),False))
            except (ValueError,KeyError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/software-factory/workers/approve":
            try:return self._json(200,orch.request_ephemeral_workers(str(data.get("project") or ""),str(data.get("manager") or ""),str(data.get("role") or ""),int(data.get("count") or 1),str(data.get("reason") or ""),data.get("hr_snapshot"),True))
            except (ValueError,KeyError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/software-factory/workers/run":
            try:return self._json(200,orch.run_ephemeral_workers(str(data.get("project") or ""),data.get("request") or {},str(data.get("task") or "")))
            except (ValueError,KeyError,PermissionError,RuntimeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/software-factory/gate":
            try:return self._json(200,orch.software_project_gate(str(data.get("project") or ""),str(data.get("stage") or ""),bool(data.get("passed",False)),data.get("evidence") or [],data.get("defects") or []))
            except (ValueError,KeyError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/software-factory/hr":
            try:return self._json(200,orch.software_factory_hr(str(data.get("project") or "KRISHNA"),data.get("workers") or [],data.get("deadline_at"),data.get("total_units"),data.get("completed_units")))
            except (ValueError,KeyError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/software-factory/test-plan":
            return self._json(200,orch.software_factory_test_plan(data.get("project_type","web"),data.get("risk","medium"),bool(data.get("has_ui",True)),bool(data.get("has_api",True))))

        if post_path == "/api/software-factory/testing-lead/verify":
            try:return self._json(200,orch.testing_lead_live_verify(str(data.get("project") or "KRISHNA"),str(data.get("url") or ""),data.get("screenshot_dir"),int(data.get("max_controls") or 100)))
            except (ValueError,KeyError,RuntimeError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/gyan-bhandar/acl/grant":
            try:
                receipt=orch.dispatch_action(
                    "gyan.acl.grant",
                    {"project":data.get("project") or "KRISHNA","principal":data.get("principal"),"permissions":data.get("permissions") or []},
                    project=str(data.get("project") or "KRISHNA"),source="pc",actor="gyan-security",
                    approved=bool(data.get("approved",False)),permissions=("memory.admin",),
                )
                return self._json(200,receipt["result"])
            except ValueError as exc:return self._json(400,{"error":str(exc)})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})

        if post_path == "/api/gyan-bhandar/acl/revoke":
            try:
                receipt=orch.dispatch_action(
                    "gyan.acl.revoke",
                    {"project":data.get("project") or "KRISHNA","principal":data.get("principal")},
                    project=str(data.get("project") or "KRISHNA"),source="pc",actor="gyan-security",
                    approved=bool(data.get("approved",False)),permissions=("memory.admin",),
                )
                return self._json(200,receipt["result"])
            except PermissionError as exc:return self._json(403,{"error":str(exc)})

        if post_path == "/api/gyan-bhandar/session/capture":
            try:
                receipt=orch.dispatch_action(
                    "gyan.session.capture",
                    {"project":data.get("project") or "KRISHNA","chat_id":data.get("chat_id"),"summary":data.get("summary"),
                     "evidence":data.get("evidence") or [],"provenance":data.get("provenance") or {}},
                    project=str(data.get("project") or "KRISHNA"),source="pc",actor="gyan-session",
                    permissions=("memory.write",),
                )
                return self._json(202,receipt["result"])
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/gyan-bhandar/replica/snapshot":
            try:
                receipt=orch.dispatch_action(
                    "gyan.replica.snapshot",{"label":data.get("label") or "gyan"},
                    project="KRISHNA",source="pc",actor="gyan-security",
                    approved=bool(data.get("approved",False)),permissions=("memory.admin","filesystem.write"),
                )
                return self._json(201,receipt["result"])
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,OSError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/gyan-bhandar/encrypted/store":
            try:
                receipt=orch.dispatch_action(
                    "gyan.encrypted.put",
                    {"record_id":data.get("record_id"),"payload":data.get("payload") or {},"project":data.get("project") or "KRISHNA"},
                    project=str(data.get("project") or "KRISHNA"),source="pc",actor="gyan-security",
                    approved=bool(data.get("approved",False)),permissions=("memory.admin","memory.write"),
                )
                return self._json(201,receipt["result"])
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,RuntimeError) as exc:return self._json(503 if isinstance(exc,RuntimeError) else 400,{"error":str(exc)})

        if post_path == "/api/gyan-bhandar/archive":
            project=str(data.get("project") or "KRISHNA").strip(); source_path=str(data.get("source_path") or "").strip()
            if not source_path:return self._json(400,{"error":"source_path is required"})
            try:return self._json(201,orch.gyan_archive_file(project,source_path,str(data.get("topic") or ""),bool(data.get("remove_original",False))))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,FileNotFoundError) as exc:return self._json(400,{"error":str(exc)})
        if post_path == "/api/gyan-bhandar/archive/restore":
            digest=str(data.get("sha256") or "").strip(); destination=str(data.get("destination") or "").strip()
            project=str(data.get("project") or "KRISHNA").strip() or "KRISHNA"
            if not digest or not destination:return self._json(400,{"error":"sha256 and destination are required"})
            try:return self._json(200,orch.gyan_restore_file(digest,destination,project,bool(data.get("approved",False))))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,FileNotFoundError) as exc:return self._json(400,{"error":str(exc)})
        if post_path == "/api/gyan-bhandar/compact":
            return self._json(200,orch.gyan_compact())

        if post_path == "/api/gyan-bhandar/propose":
            try:
                receipt=orch.dispatch_action("gyan.propose",data,project=str(data.get("project") or "KRISHNA"),source="pc",actor="legacy-http")
                return self._json(202,receipt["result"])
            except KeyError:return self._json(404,{"error":"project not registered"})
            except (ValueError,TypeError,PermissionError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/gyan-bhandar/decide":
            try:
                receipt=orch.dispatch_action("gyan.decide",data,source="pc",actor="legacy-http")
                return self._json(200,receipt["result"])
            except KeyError:return self._json(404,{"error":"pending finding not found"})
            except (ValueError,PermissionError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/gyan-bhandar/store":
            project=str(data.get("project") or "KRISHNA").strip(); topic=str(data.get("topic") or "").strip(); lesson=str(data.get("lesson") or "").strip()
            if not topic or not lesson:return self._json(400,{"error":"topic and lesson are required"})
            try:return self._json(201,orch.gyan_store(project,topic,lesson,data.get("evidence") or [],float(data.get("confidence") or 0),
                str(data.get("source") or "sudarshan"),bool(data.get("verified",False)),str(data.get("memory_kind") or "evidence"),
                data.get("provenance") or {},data.get("supersedes")))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,TypeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/gyan-bhandar/supersede":
            try:
                receipt=orch.dispatch_action("gyan.supersede",data,project=str(data.get("project") or "KRISHNA"),source="pc",actor="legacy-http")
                return self._json(202,receipt["result"])
            except KeyError:return self._json(404,{"error":"learning or project not found"})
            except (ValueError,TypeError,PermissionError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/gyan-bhandar/strengthen":
            try:
                receipt=orch.dispatch_action("gyan.strengthen",data,project=str(data.get("project") or "KRISHNA"),source="pc",actor="legacy-http")
                return self._json(200,receipt["result"])
            except KeyError:return self._json(404,{"error":"project not registered"})
            except (ValueError,RuntimeError,PermissionError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/garuda/scout":
            project=str(data.get("project") or "KRISHNA").strip();goal=str(data.get("goal") or "").strip()
            if not goal:return self._json(400,{"error":"goal is required"})
            try:
                out=orch.dispatch_action("garuda.scout",{"project":project,"goal":goal,"limit":int(data.get("limit") or 10)},project=project,source="pc",actor="legacy-http")
                return self._json(200,out["result"])
            except KeyError:return self._json(404,{"error":"project not registered"})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,RuntimeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/development/git/status":
            project=str(data.get("project","")).strip()
            if not project:return self._json(400,{"error":"project is required"})
            try:return self._json(200,orch.development_git_snapshot(project))
            except KeyError:return self._json(404,{"error":"project not registered"})

        if post_path == "/api/development/git/commit":
            project=str(data.get("project","")).strip()
            try:return self._json(200,orch.development_commit(project,str(data.get("message","KRISHNA verified change")),data.get("files") or [],bool(data.get("approved",False))))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except (ValueError,PermissionError) as exc:return self._json(403 if isinstance(exc,PermissionError) else 400,{"error":str(exc)})

        if post_path == "/api/development/git/push":
            project=str(data.get("project","")).strip()
            try:return self._json(200,orch.development_push(project,bool(data.get("approved",False))))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})

        if post_path == "/api/development/sync":
            project=str(data.get("project","")).strip()
            if not project:return self._json(400,{"error":"project is required"})
            try:return self._json(200,orch.development_sync(project,bool(data.get("approved",False))))
            except KeyError:return self._json(404,{"error":"project not registered"})

        if post_path == "/api/development/stage":
            project=str(data.get("project","")).strip(); files=data.get("files") or []
            if not project or not isinstance(files,list):return self._json(400,{"error":"project and files are required"})
            try:return self._json(200,orch.development_stage(project,files))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except (ValueError,OSError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/development/verify":
            project=str(data.get("project","")).strip(); candidate=str(data.get("candidate_root","")).strip()
            if not project or not candidate:return self._json(400,{"error":"project and candidate_root are required"})
            try:return self._json(200,orch.development_verify(project,candidate,data.get("checks") or [],data.get("frontend_url"),data.get("browser_actions") or [],data.get("api_expectations") or [],data.get("screenshot_path") or None))
            except KeyError:return self._json(404,{"error":"project not registered"})
            except (ValueError,OSError,RuntimeError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/work/run":
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

        if post_path == "/api/work/promotion/prepare":
            project=str(data.get("project","")).strip()
            candidate=str(data.get("candidate_root","")).strip()
            if not project or not candidate: return self._json(400,{"error":"project and candidate_root are required"})
            try: return self._json(200,orch.prepare_promotion(project,candidate,data.get("task_id")))
            except KeyError as exc: return self._json(404,{"error":str(exc)})
            except ValueError as exc: return self._json(400,{"error":str(exc)})

        if post_path == "/api/work/promotion/apply":
            token=str(data.get("promotion_token","")).strip()
            if not token: return self._json(400,{"error":"promotion_token is required"})
            try: return self._json(200,orch.promote_candidate(token,approved=bool(data.get("approved",False))))
            except KeyError as exc: return self._json(404,{"error":str(exc)})
            except PermissionError as exc: return self._json(403,{"error":str(exc)})
            except (ValueError,RuntimeError) as exc: return self._json(409,{"error":str(exc)})

        if post_path == "/api/repair/shadow":
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

        if post_path == "/api/browser/inspect":
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

        if post_path == "/api/research/github":
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

        if post_path == "/api/goal/evaluate":
            project = str(data.get("project", "general"))
            goal = str(data.get("goal", "")).strip()
            checks = data.get("checks") or []
            if not goal:
                return self._json(400, {"error": "goal is required"})
            return self._json(200, orch.evaluate_goal(project, goal, checks))

        if post_path == "/api/knowledge/ingest":
            project = str(data.get("project", "general"))
            source = str(data.get("source", "manual"))
            text = str(data.get("text", ""))
            if not text.strip():
                return self._json(400, {"error": "text is required"})
            result = orch.ingest_knowledge(project, source, text, data.get("metadata"))
            return self._json(200, result)

        if post_path == "/api/project-graph/node":
            name = str(data.get("name", "")).strip()
            if not name:
                return self._json(400, {"error": "name is required"})
            orch.graph.upsert_node(name, str(data.get("kind", "component")), data.get("metadata") or {})
            return self._json(200, {"ok": True})

        if post_path == "/api/project-graph/link":
            source = str(data.get("source", "")).strip()
            target = str(data.get("target", "")).strip()
            if not source or not target:
                return self._json(400, {"error": "source and target are required"})
            orch.graph.link(source, target, str(data.get("relation", "depends_on")))
            return self._json(200, {"ok": True})

        if post_path == "/api/kabach/privacy/audit":
            project=str(data.get("project") or "KRISHNA").strip() or "KRISHNA"
            payload={
                "target_type":str(data.get("target_type") or data.get("target") or "").strip().lower(),
                "url":data.get("url"),"web_url":data.get("web_url"),"apk_path":data.get("apk_path"),
                "owned":bool(data.get("owned",True)),"profile":str(data.get("profile") or "BASELINE"),
                "policy":str(data.get("policy") or "STANDARD"),"mission_id":data.get("mission_id"),
            }
            try:
                receipt=orch.dispatch_action("kabach.privacy.audit",payload,project=project,source="pc",actor="privacy-http",permissions=("privacy.read",))
                return self._json(200,receipt["result"])
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except (ValueError,RuntimeError,FileNotFoundError) as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/kabach/privacy/clean-url":
            project=str(data.get("project") or "KRISHNA").strip() or "KRISHNA"
            try:
                receipt=orch.dispatch_action("kabach.privacy.clean_url",{"url":str(data.get("url") or "")},project=project,source="pc",actor="privacy-http",permissions=("privacy.read",))
                return self._json(200,receipt["result"])
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except ValueError as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/kabach/privacy/baseline":
            project=str(data.get("project") or "KRISHNA").strip() or "KRISHNA"
            try:
                receipt=orch.dispatch_action("kabach.privacy.baseline.save",{"name":str(data.get("name") or ""),"report":data.get("report") or {}},project=project,source="pc",actor="privacy-http",permissions=("privacy.write",))
                return self._json(200,receipt["result"])
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except ValueError as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/kabach/privacy/compare":
            project=str(data.get("project") or "KRISHNA").strip() or "KRISHNA"
            try:
                receipt=orch.dispatch_action(
                    "kabach.privacy.baseline.compare",
                    {"name":str(data.get("name") or ""),"report":data.get("report") or {},"mission_id":data.get("mission_id"),"configuration_change":data.get("configuration_change")},
                    project=project,source="pc",actor="privacy-http",permissions=("privacy.read",),
                )
                return self._json(200,receipt["result"])
            except KeyError as exc:return self._json(404,{"error":str(exc)})
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except ValueError as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/kabach/privacy/release-gate":
            project=str(data.get("project") or "KRISHNA").strip() or "KRISHNA"
            try:
                receipt=orch.dispatch_action(
                    "kabach.privacy.release_gate",{"report":data.get("report") or {},"policy":str(data.get("policy") or "STANDARD")},
                    project=project,source="pc",actor="privacy-http",permissions=("privacy.read","release.verify"),
                )
                return self._json(200,receipt["result"])
            except PermissionError as exc:return self._json(403,{"error":str(exc)})
            except ValueError as exc:return self._json(400,{"error":str(exc)})

        if post_path == "/api/security/scan-text":
            path = str(data.get("path", "submitted-text"))
            text = str(data.get("text", ""))
            return self._json(200, {
                "authorized_defensive_scan": True,
                "findings": orch.security.scan_text(path, text),
            })

        if post_path == "/api/recovery/execute":
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
        shutdown_failures=shutdown_runtime_services()
        for failure in shutdown_failures:
            print(f"[KRISHNA] shutdown warning: {failure}", file=sys.stderr)
        server.server_close()
