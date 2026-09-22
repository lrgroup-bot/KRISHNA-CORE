from __future__ import annotations

"""Deterministic end-to-end source/runtime audit for KRISHNA.

These are lightweight audit workers, not autonomous authorities. Each worker owns one
slice of the project and returns evidence. The coordinator never mutates production.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
import argparse
import json
import re
import time

from .avatar_asset_pipeline import AvatarAssetInspector
from .native_voice import KrishnaVoiceStack
from .mission_engine import MISSION_STATES


@dataclass
class AuditFinding:
    worker: str
    name: str
    status: str
    detail: str
    evidence: dict

    def public(self):
        return asdict(self)


class KrishnaProjectAudit:
    WORKERS=(
        "source","repository","ui","core","desktop","avatar","voice","mobile","security","deployment","requirements"
    )

    def __init__(self,source_root: str|Path,runtime_root: str|Path):
        self.source=Path(source_root).resolve()
        self.runtime=Path(runtime_root).resolve()
        self.findings=[]

    def add(self,worker,name,status,detail,**evidence):
        status=str(status).upper()
        if status not in {"PASS","WARN","FAIL"}:
            raise ValueError("invalid audit status")
        self.findings.append(AuditFinding(worker,name,status,detail,evidence))

    def _read(self,rel):
        return (self.source/rel).read_text(encoding="utf-8")

    def audit_source(self):
        required=(
            "core/krishna_core/orchestrator.py","core/krishna_core/server.py",
            "core/web_validation.html","scripts/DEPLOY_KRISHNA_ONCE.ps1",
            "scripts/ACCEPT_KRISHNA_RUNTIME.ps1","scripts/START_KRISHNA.ps1",
        )
        missing=[x for x in required if not (self.source/x).is_file()]
        self.add("source","authoritative source layout","PASS" if not missing else "FAIL",
                 "authoritative source files present" if not missing else "required source files missing",
                 missing=missing,source_root=str(self.source))

        legacy=[
            "core/dashboard.html","core/web_validation.before-clean-sudarshan.html",
            "core/web_validation.before-real-chat-menu.html","core/web_validation.before-sudarshan-fix.html",
            "core/web_validation.pre-consolidated-fix.html",
        ]
        present=[x for x in legacy if (self.source/x).exists()]
        self.add("source","stale UI source removal","PASS" if not present else "WARN",
                 "legacy UI snapshots are absent" if not present else "stale UI snapshots remain in source",
                 present=present)

    def audit_repository(self):
        text_ext={".py",".ps1",".html",".js",".mjs",".java",".json",".md",".txt",".yml",".yaml",".toml"}
        ignored_parts={".git","__pycache__",".venv","node_modules","dist","build"}
        files=[]
        findings={"dangerous":[],"warnings":[],"invalid_json":[],"possible_secrets":[]}
        secret_patterns=(
            re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
            re.compile(r"\bghp_[A-Za-z0-9]{20,}"),
            re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
            re.compile(r"\bAIza[0-9A-Za-z_-]{20,}"),
        )
        for path in sorted(self.source.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in text_ext:continue
            rel=path.relative_to(self.source)
            if any(part in ignored_parts for part in rel.parts):continue
            files.append(str(rel).replace("\\","/"))
            try:text=path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                findings["warnings"].append({"file":str(rel),"issue":"not utf-8 text"})
                continue
            if path.suffix.lower()==".json":
                try:json.loads(text)
                except Exception as exc:findings["invalid_json"].append({"file":str(rel),"error":f"{type(exc).__name__}: {exc}"})
            definite=(
                ("shell=True",r"shell\s*=\s*True"),
                ("os.system",r"\bos\.system\s*\("),
                ("subprocess shell",r"subprocess\.[A-Za-z_]+\([^\n]{0,500}shell\s*=\s*True"),
                ("TLS verify disabled",r"verify\s*=\s*False"),
            )
            for label,pattern in definite:
                if re.search(pattern,text):
                    findings["dangerous"].append({"file":str(rel),"issue":label})
            for label,pattern in (
                ("TODO/FIXME",r"\b(?:TODO|FIXME)\b"),
                ("NotImplementedError",r"\bNotImplementedError\b"),
                ("broad exception swallowed",r"except\s+Exception(?:\s+as\s+\w+)?\s*:\s*(?:#.*\n\s*)?pass\b"),
            ):
                if re.search(pattern,text,re.I if label=="TODO/FIXME" else 0):
                    findings["warnings"].append({"file":str(rel),"issue":label})
            for pattern in secret_patterns:
                if pattern.search(text):
                    findings["possible_secrets"].append({"file":str(rel),"pattern":pattern.pattern})
        tracked_env=[x for x in files if Path(x).name==".env"]
        if tracked_env:findings["dangerous"].extend({"file":x,"issue":"tracked .env"} for x in tracked_env)
        failures=findings["dangerous"]+findings["invalid_json"]+findings["possible_secrets"]
        self.add("repository","whole-source security/syntax scan","PASS" if not failures else "FAIL",
                 f"{len(files)} text/source files scanned" if not failures else "repository-wide static scan found blocking defects",
                 file_count=len(files),failures=failures,warnings=findings["warnings"][:100],
                 warning_count=len(findings["warnings"]))

    def audit_ui(self):
        html=self._read("core/web_validation.html")
        server=self._read("core/krishna_core/server.py")
        marker='data-krishna-ui="2026.09-current"'
        self.add("ui","current UI marker","PASS" if marker in html else "FAIL",
                 "current desktop design marker present" if marker in html else "current desktop design marker missing")

        main=re.search(r'(?s)<div class="section">MAIN MENU</div><div class="nav mainMenuNav">(.*?)</div>\s*<div class="sidebarWorkspace">',html)
        menu=main.group(1) if main else ""
        buttons=menu.count("<button")
        correct=(buttons==3 and all(x in menu for x in ("showView('home')","showView('sudarshan')","showView('plugins')")))
        forbidden=[x for x in ("KABACH","Garuda","Garudanetra","BRAHMAGYAN","Gyan-Bhandar","NARAD","System") if x in menu]
        self.add("ui","minimal MAIN MENU","PASS" if correct and not forbidden else "FAIL",
                 "MAIN MENU is KRISHNA / Sudarshan / Plugins" if correct and not forbidden else "owner-visible menu contract mismatch",
                 button_count=buttons,forbidden=forbidden)

        ids=set(re.findall(r'id="([^"]+)"',html))
        controls=[]
        dead=[]
        for tag,attrs in re.findall(r"<(input|textarea|select)\b([^>]*)>",html,flags=re.I):
            m=re.search(r'\bid="([^"]+)"',attrs)
            if not m:
                dead.append({"tag":tag,"reason":"missing id"})
                continue
            cid=m.group(1)
            refs=len(re.findall(re.escape(cid),html))
            inline=bool(re.search(r"\bon(?:input|change|keydown|keyup|click|submit)=",attrs,re.I))
            controls.append(cid)
            if refs<2 and not inline:
                dead.append({"id":cid,"reason":"not referenced"})
        self.add("ui","textbox/select wiring","PASS" if not dead else "FAIL",
                 f"{len(controls)} input/select/textarea controls inspected; all wired" if not dead else "dead form controls detected",
                 controls=len(controls),dead=dead)

        functions=set(re.findall(r"(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(",html))
        allowed={"preventDefault","stopPropagation","getElementById","click","focus","confirm","alert","prompt","setTimeout","setInterval"}
        missing=[]
        for handler in re.findall(r'\bon(?:click|change|input|submit|keydown|keyup)="([^"]+)"',html,re.I):
            for fn in re.findall(r"(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(",handler):
                if fn in {"if","for","while","switch"} or fn in allowed:continue
                if fn not in functions:missing.append({"function":fn,"handler":handler})
        self.add("ui","inline function handlers","PASS" if not missing else "FAIL",
                 f"{len(functions)} declared UI functions checked" if not missing else "undefined inline handlers found",
                 missing=missing)

        endpoints=set()
        for pattern in (r"\breq\(\s*['\"](/api/[^'\"?]+)",r"\bfetch\(\s*['\"](/api/[^'\"?]+)"):
            endpoints.update(re.findall(pattern,html))
        missing_api=[x for x in sorted(endpoints) if x not in server]
        self.add("ui","UI to Core API wiring","PASS" if not missing_api else "FAIL",
                 f"{len(endpoints)} UI API routes map to Core" if not missing_api else "UI references missing Core routes",
                 endpoint_count=len(endpoints),missing=missing_api)

        refs=set(re.findall(r"\$\('([^']+)'\)",html))
        missing_ids=sorted(refs-ids)
        self.add("ui","DOM id references","PASS" if not missing_ids else "FAIL",
                 "all $() DOM references resolve" if not missing_ids else "missing DOM IDs",
                 missing=missing_ids)

    def audit_core(self):
        required=(
            "durable_event_bus.py","durable_queue.py","mission_engine.py","mission_budget.py",
            "resource_locks.py","permission_runtime.py","provider_contract.py","krishna_protocol.py",
            "sudarshan_control.py","shared_action_bus.py","agent_runtime.py",
        )
        root=self.source/"core"/"krishna_core"
        missing=[x for x in required if not (root/x).is_file()]
        self.add("core","Phase 1 durable foundation","PASS" if not missing and len(MISSION_STATES)==12 else "FAIL",
                 "Mission/Queue/Checkpoint/Lock/Permission/Protocol foundation present" if not missing else "durable foundation modules missing",
                 missing=missing,mission_states=list(MISSION_STATES))
        server=self._read("core/krishna_core/server.py")
        routes=("/api/missions/status","/api/queue/status","/api/resource-locks","/api/events","/api/protocol")
        absent=[x for x in routes if x not in server]
        self.add("core","durable runtime surfaces","PASS" if not absent else "FAIL",
                 "durable runtime status surfaces are exposed" if not absent else "durable status routes missing",
                 missing=absent)

    def audit_desktop(self):
        from .windows_desktop_fabric import WindowsDesktopFabric
        fabric=WindowsDesktopFabric(self.runtime)
        status=fabric.status(probe=False)
        code=self._read("core/krishna_core/server.py")
        wired=all(x in code for x in (
            "/api/desktop/status","desktop.rpa.validate","desktop.rpa.run",
            "windows_desktop_fabric_capability_gated",
        ))
        self.add("desktop","Windows computer-use boundary","PASS" if wired else "FAIL",
                 "capability-gated validated-RPA desktop boundary is wired through Sudarshan" if wired else "desktop fabric is not wired through Core",
                 provider=status.get("provider"),available=bool(status.get("available")),
                 raw_python_exposed=bool(status.get("raw_python_exposed")),mcp_authority=bool(status.get("mcp_authority")))
        if status.get("available"):
            probe=fabric.status(probe=True).get("probe") or {}
            self.add("desktop","Windows desktop provider runtime","PASS" if probe.get("ok") else "WARN",
                     "ADH provider installed and doctor probe passed" if probe.get("ok") else "ADH executable exists but doctor probe did not pass",
                     probe=probe)
        else:
            self.add("desktop","Windows desktop provider runtime","WARN",
                     "ADH is not installed/configured on this runtime; desktop control remains unavailable rather than being falsely reported active",
                     executable=status.get("executable"))

    def audit_avatar(self):
        private=self.runtime/"dashboard"/"assets"/"avatar"/"krishna.glb"
        report=self.runtime/"state"/"avatar"/"full-audit-asset.json"
        result=AvatarAssetInspector(report).inspect(private)
        if not result.get("available"):
            status="WARN";detail="private avatar GLB is not installed in the audited runtime"
        elif result.get("ready"):
            status="PASS";detail="private avatar is production-ready: body rig + ARKit 52 + Oculus 15"
        else:
            status="WARN";detail="private avatar is present but not production-ready"
        self.add("avatar","private GLB compatibility",status,detail,
                 stage=result.get("stage"),issues=result.get("issues") or [],
                 ready=bool(result.get("ready")),path=str(private))
        engine_root=self.runtime/"dashboard"/"assets"/"avatar-engine"
        engines={
            "talkinghead":engine_root/"talkinghead"/"talkinghead.mjs",
            "model_viewer":engine_root/"model-viewer"/"model-viewer.min.js",
            "headaudio":engine_root/"headaudio"/"dist"/"headaudio.min.mjs",
            "motion_engine":engine_root/"motion-engine"/"src"/"MotionEngine.js",
        }
        missing=[k for k,p in engines.items() if not p.is_file()]
        self.add("avatar","local avatar engines","PASS" if not missing else "WARN",
                 "all local avatar engines installed" if not missing else "avatar engine assets still need runtime installation",
                 missing=missing)

    def audit_voice(self):
        status=KrishnaVoiceStack().status()
        stt=status["stt"];tts=status["tts"];wake=status["wake"]
        truthful=("hi" in stt.get("languages",[]) and "or" in stt.get("languages",[]) and "en" not in stt.get("languages",[])
                  and "hi" in tts.get("languages",[]) and "or" in tts.get("languages",[])
                  and "en" in tts.get("known_languages",[]))
        detail=("IndicConformer advertises Hindi/Odia; Indic-TTS advertises only installed/configured checkpoints, "
                "with English supported only when explicitly configured")
        self.add("voice","language contract","PASS" if truthful else "FAIL",
                 detail if truthful else "voice language reporting is inaccurate",
                 stt=stt,tts=tts)
        ready=bool(stt.get("available") and tts.get("available") and wake.get("available"))
        self.add("voice","runtime voice assets","PASS" if ready else "WARN",
                 "local Hindi/Odia voice and Krishna wake assets configured" if ready else "one or more local voice/wake runtime assets are not configured",
                 stt_available=bool(stt.get("available")),tts_available=bool(tts.get("available")),wake_available=bool(wake.get("available")))

    def audit_mobile(self):
        html_path=self.source/"mobile_v3"/"index.html"
        java_path=self.source/"mobile_v3"/"MainActivity.java"
        if not html_path.is_file() or not java_path.is_file():
            self.add("mobile","conversation-only client","FAIL","mobile_v3 source is incomplete",html=html_path.is_file(),java=java_path.is_file())
            return
        html=html_path.read_text(encoding="utf-8")
        lowered=html.lower()
        forbidden=[x for x in ("system health","project list","raw shell","filesystem browser","dashboard") if x in lowered]
        required=[x for x in ("message","microphone","attachment") if x not in lowered]
        self.add("mobile","conversation-only client","PASS" if not forbidden and not required else "FAIL",
                 "mobile UI remains conversation-first" if not forbidden and not required else "mobile UI contract mismatch",
                 forbidden=forbidden,missing_required=required)

    def audit_security(self):
        root=self.source/"core"/"krishna_core"/"privacy_guardian"
        required=("guardian.py","browser.py","mobile.py","network.py","tracking.py","web_security.py","store.py","policy.py","regression.py")
        missing=[x for x in required if not (root/x).is_file()]
        server=self._read("core/krishna_core/server.py")
        remote_ok=("private-network-only" in self._read("core/krishna_core/remote_access.py")
                   and "pairing required" in server)
        self.add("security","KABACH Privacy Guardian modules","PASS" if not missing else "FAIL",
                 "privacy guardian module set present" if not missing else "privacy guardian modules missing",missing=missing)
        self.add("security","private remote/mobile boundary","PASS" if remote_ok else "FAIL",
                 "public remote control is rejected and paired mobile auth is required" if remote_ok else "remote/mobile boundary contract missing")

    def audit_deployment(self):
        deploy=self._read("scripts/DEPLOY_KRISHNA_ONCE.ps1")
        accept=self._read("scripts/ACCEPT_KRISHNA_RUNTIME.ps1")
        start=self._read("scripts/START_KRISHNA.ps1")
        desktop=self._read("core/krishna_desktop.py")
        build=self._read(".github/workflows/build-console.yml")
        checks={
            "verified_acceptance":"ACCEPT_KRISHNA_RUNTIME.ps1" in deploy,
            "current_ui_gate":"Current KRISHNA UI" in accept and "2026.09-current" in accept,
            "source_sync":"DEPLOYED_COMMIT.json" in start,
            "canonical_desktop":"tkinter" not in desktop and "webview.create_window" in desktop,
            "build_current_ui":'core/web_validation.html' in build and 'core/dashboard.html' not in build,
        }
        bad=[k for k,v in checks.items() if not v]
        self.add("deployment","single current desktop surface","PASS" if not bad else "FAIL",
                 "deploy/start/EXE all resolve to the current canonical UI" if not bad else "deployment paths can still expose a stale UI",
                 checks=checks)

    def audit_requirements(self):
        path=self.source/"core"/"requirements"/"krishna_chat_requirements.json"
        try:data=json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            self.add("requirements","chat requirements ledger","FAIL",f"requirements ledger unreadable: {type(exc).__name__}")
            return
        reqs=[]
        for group in data.get("groups") or []:reqs.extend(group.get("requirements") or [])
        stale=[x for x in reqs if "Jobs reuse the durable TaskLedger" in x]
        self.add("requirements","chat requirements ledger","PASS" if len(reqs)>=100 and not stale else "FAIL",
                 f"{len(reqs)} consolidated requirements checked" if not stale else "stale pre-Phase-1 requirements remain",
                 version=data.get("version"),requirement_count=len(reqs),stale=stale)

    def run(self):
        started=time.time()
        for name in self.WORKERS:
            getattr(self,f"audit_{name}")()
        rows=[x.public() for x in self.findings]
        counts={s:sum(1 for x in rows if x["status"]==s) for s in ("PASS","WARN","FAIL")}
        return {
            "schema":1,"generated_at":time.time(),"source_root":str(self.source),"runtime_root":str(self.runtime),
            "workers":list(self.WORKERS),"counts":counts,"release_ready":counts["FAIL"]==0,
            "duration_seconds":round(time.time()-started,3),"findings":rows,
        }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-root",required=True)
    parser.add_argument("--runtime-root",required=True)
    parser.add_argument("--output")
    args=parser.parse_args()
    report=KrishnaProjectAudit(args.source_root,args.runtime_root).run()
    body=json.dumps(report,indent=2,ensure_ascii=False)
    if args.output:
        target=Path(args.output).resolve();target.parent.mkdir(parents=True,exist_ok=True);target.write_text(body,encoding="utf-8")
    print(body)
    raise SystemExit(2 if report["counts"]["FAIL"] else 0)


if __name__=="__main__":
    main()
