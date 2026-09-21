from __future__ import annotations

import json
import queue
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from .garudanetra_recovery import BrowserRecoveryAdapter


_SAFE_NAME=re.compile(r"[^A-Za-z0-9._-]+")
BROWSER_MODES={"private","task_memory","persistent_workspace"}


@dataclass
class BrowserSession:
    session_id: str
    project: str
    requested_url: str
    mode: str = "private"
    state: str = "STARTING"
    current_url: str = ""
    title: str = ""
    paused: bool = False
    owner_control: bool = False
    stopped: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_error: str | None = None
    viewport: dict = field(default_factory=lambda: {"width": 1280, "height": 800})
    visible_text: str = ""
    console: list[dict] = field(default_factory=list)
    network: list[dict] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    downloads: list[dict] = field(default_factory=list)
    tabs: list[dict] = field(default_factory=list)
    frame: bytes | None = None
    tab_index: int = 0
    remember_evidence: bool = False
    profile_path: str | None = None


class GarudanetraSessionManager:
    """Private/task-memory/persistent Chromium sessions for KRISHNA.

    private: isolated context, destroyed on stop, no durable browser evidence.
    task_memory: isolated context, destroyed on stop, evidence summary persisted.
    persistent_workspace: project-specific browser profile, only with explicit approval.
    """

    ACTIONS={
        "pause","resume","takeover","stop","navigate","back","forward","reload",
        "new_tab","switch_tab","close_tab","click","fill","type_text","press",
        "click_xy","drag_xy","scroll","upload"
    }

    def __init__(self,runtime_root:str|Path,headless:bool=True,timeout_ms:int=15000,on_closed=None,recovery=None):
        self.root=Path(runtime_root).resolve()
        self.headless=bool(headless)
        self.timeout_ms=int(timeout_ms)
        self.on_closed=on_closed
        self.recovery=recovery or BrowserRecoveryAdapter()
        self._lock=threading.RLock()
        self._sessions:dict[str,BrowserSession]={}
        self._commands:dict[str,queue.Queue]={}
        self._threads:dict[str,threading.Thread]={}
        self.evidence_root=self.root/"state"/"garudanetra"/"sessions"
        self.profile_root=self.root/"garudanetra"/"profiles"
        self.download_root=self.root/"downloads"/"garudanetra"

    @staticmethod
    def validate_url(url:str)->str:
        value=str(url or "").strip()
        parsed=urlparse(value)
        if parsed.scheme not in ("http","https") or not parsed.netloc:
            raise ValueError("Garudanetra requires an http:// or https:// URL")
        return value

    @staticmethod
    def validate_mode(mode):
        mode=str(mode or "private").strip().lower()
        if mode not in BROWSER_MODES:raise ValueError("invalid Garudanetra browser mode")
        return mode

    def create(self,project:str,url:str,mode="private",persistent_approved=False)->dict:
        target=self.validate_url(url);mode=self.validate_mode(mode)
        if mode=="persistent_workspace" and not bool(persistent_approved):
            raise PermissionError("persistent browser workspace requires explicit approval")
        sid=str(uuid.uuid4());project=str(project or "KRISHNA")
        profile=None
        if mode=="persistent_workspace":
            safe=_SAFE_NAME.sub("_",project).strip("._")[:100] or "KRISHNA"
            profile=str((self.profile_root/safe).resolve())
        session=BrowserSession(session_id=sid,project=project,requested_url=target,mode=mode,
                               remember_evidence=(mode=="task_memory"),profile_path=profile)
        with self._lock:
            self._sessions[sid]=session;self._commands[sid]=queue.Queue(maxsize=100)
        thread=threading.Thread(target=self._worker,args=(sid,),name=f"garudanetra-{sid[:8]}",daemon=True)
        self._threads[sid]=thread;thread.start()
        return self.status(sid)

    def _get(self,session_id):
        with self._lock:session=self._sessions.get(str(session_id))
        if not session:raise KeyError("Garudanetra session not found")
        return session

    def status(self,session_id=None):
        if session_id:
            with self._lock:return self._snapshot(self._get(session_id))
        with self._lock:rows=[self._snapshot(s) for s in self._sessions.values()]
        rows.sort(key=lambda x:x["created_at"],reverse=True)
        return {"sessions":rows[:20],"count":len(rows),"modes":sorted(BROWSER_MODES),"recovery":self.recovery.status()}

    @staticmethod
    def _snapshot(session):
        return {
            "session_id":session.session_id,"project":session.project,"requested_url":session.requested_url,
            "mode":session.mode,"state":session.state,"current_url":session.current_url,"title":session.title,
            "paused":session.paused,"owner_control":session.owner_control,"stopped":session.stopped,
            "created_at":session.created_at,"updated_at":session.updated_at,"last_error":session.last_error,
            "viewport":dict(session.viewport),"visible_text":session.visible_text[:6000],
            "console":list(session.console[-50:]),"network":list(session.network[-100:]),
            "findings":list(session.findings[-100:]),"downloads":list(session.downloads[-50:]),"tabs":list(session.tabs[-30:]),
            "frame_available":bool(session.frame),"tab_index":session.tab_index,
            "remember_evidence":session.remember_evidence,"profile_path":session.profile_path,
        }

    def _warn(self,session,kind,exc):
        detail=f"{type(exc).__name__}: {exc}"[:1200]
        with self._lock:
            session.findings.append({"kind":str(kind),"detail":detail,"severity":"warning","at":time.time()})
            del session.findings[:-200]
            session.updated_at=time.time()

    def frame(self,session_id):
        session=self._get(session_id)
        with self._lock:return bytes(session.frame) if session.frame else None

    def command(self,session_id,action,payload=None):
        session=self._get(session_id);action=str(action or "").strip().lower()
        if action not in self.ACTIONS:raise ValueError(f"unsupported Garudanetra action: {action}")
        if session.stopped:raise RuntimeError("Garudanetra session is already stopped")
        try:self._commands[session.session_id].put_nowait({"action":action,"payload":dict(payload or {})})
        except queue.Full as exc:raise RuntimeError("Garudanetra command queue is full") from exc
        return self.status(session.session_id)

    def close_all(self):
        with self._lock:ids=list(self._sessions)
        for sid in ids:
            try:
                if not self._get(sid).stopped:self.command(sid,"stop")
            except Exception as exc:
                try:self._warn(self._get(sid),"close_all_error",exc)
                except KeyError:continue

    def _persist(self,session):
        if session.mode=="private":return
        self.evidence_root.mkdir(parents=True,exist_ok=True)
        out=self.evidence_root/(session.session_id+".json");tmp=out.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._snapshot(session),ensure_ascii=False,indent=2),encoding="utf-8")
        tmp.replace(out)

    def _append_console(self,sid,kind,text):
        session=self._get(sid)
        with self._lock:
            session.console.append({"type":str(kind),"text":str(text)[:1000],"at":time.time()});del session.console[:-200]
            if str(kind).lower() in {"error","pageerror"}:
                session.findings.append({"kind":"console_error","detail":str(text)[:1000],"severity":"error"})

    def _append_network(self,sid,method,url,status):
        session=self._get(sid)
        with self._lock:
            session.network.append({"method":method,"url":str(url)[:1500],"status":int(status),"at":time.time()});del session.network[:-400]
            if int(status)>=400:session.findings.append({"kind":"http_error","detail":f"{status} {url}"[:1200],"severity":"error"})

    def _download(self,sid,download):
        session=self._get(sid)
        try:
            folder=self.download_root/sid;folder.mkdir(parents=True,exist_ok=True)
            name=_SAFE_NAME.sub("_",str(download.suggested_filename or "download"))[:180] or "download"
            path=folder/name;download.save_as(str(path))
            row={"name":name,"path":str(path),"at":time.time()}
            with self._lock:session.downloads.append(row)
        except Exception as exc:
            with self._lock:session.findings.append({"kind":"download_error","detail":f"{type(exc).__name__}: {exc}","severity":"error"})

    def _validate_upload_path(self,value):
        p=Path(str(value or "")).expanduser().resolve()
        try:p.relative_to(self.root)
        except ValueError as exc:raise PermissionError("browser uploads must come from KRISHNA runtime storage") from exc
        if not p.is_file():raise FileNotFoundError(str(p))
        return p

    @staticmethod
    def _tab_snapshot(context):
        rows=[]
        for i,p in enumerate(context.pages):
            try:title=p.title()
            except Exception:title=""
            rows.append({"index":i,"url":p.url,"title":title})
        return rows

    def _click_or_fill(self,page,action,payload,session):
        selector=str(payload.get("selector") or "").strip()
        try:
            if not selector:raise ValueError("selector missing")
            loc=page.locator(selector)
            if action=="click":loc.click()
            else:loc.fill(str(payload.get("value") or ""))
            return
        except Exception as first:
            recovered=self.recovery.recover_locator(page,payload)
            loc=recovered["locator"]
            if action=="click":loc.click()
            else:loc.fill(str(payload.get("value") or ""))
            with self._lock:
                session.findings.append({"kind":"selector_recovered","detail":recovered["strategy"],"severity":"notice",
                                         "candidate_skill":{"original_selector":selector,"payload":{k:v for k,v in payload.items() if k!="value"},
                                                            "strategy":recovered["strategy"],"source":recovered["source"]}})

    def _worker(self,sid):
        session=self._get(sid);browser=context=page=None;playwright_cm=None
        try:
            from playwright.sync_api import sync_playwright
            playwright_cm=sync_playwright();p=playwright_cm.start()
            if session.mode=="persistent_workspace":
                Path(session.profile_path).mkdir(parents=True,exist_ok=True)
                try:context=p.chromium.launch_persistent_context(session.profile_path,channel="chrome",headless=self.headless,
                                                                  viewport=dict(session.viewport),accept_downloads=True)
                except Exception:context=p.chromium.launch_persistent_context(session.profile_path,headless=self.headless,
                                                                               viewport=dict(session.viewport),accept_downloads=True)
                page=context.pages[0] if context.pages else context.new_page()
            else:
                try:browser=p.chromium.launch(channel="chrome",headless=self.headless)
                except Exception:browser=p.chromium.launch(headless=self.headless)
                context=browser.new_context(viewport=dict(session.viewport),accept_downloads=True,java_script_enabled=True)
                page=context.new_page()
            page.set_default_timeout(self.timeout_ms)
            def bind(pg):
                pg.on("console",lambda msg:self._append_console(sid,msg.type,msg.text))
                pg.on("pageerror",lambda exc:self._append_console(sid,"pageerror",str(exc)))
                pg.on("response",lambda resp:self._append_network(sid,resp.request.method,resp.url,resp.status))
                pg.on("download",lambda d:self._download(sid,d))
            bind(page)
            with self._lock:session.state="NAVIGATING";session.updated_at=time.time()
            page.goto(session.requested_url,wait_until="domcontentloaded",timeout=self.timeout_ms)
            with self._lock:session.state="LIVE";session.current_url=page.url;session.title=page.title();session.tabs=self._tab_snapshot(context);session.updated_at=time.time()

            last_capture=last_text=last_persist=0.0
            while True:
                now=time.time()
                try:
                    cmd=self._commands[sid].get(timeout=0.12);action,payload=cmd["action"],cmd["payload"]
                    if action=="stop":
                        with self._lock:session.state="STOPPING"
                        break
                    if action=="pause":
                        with self._lock:session.paused=True;session.owner_control=False;session.state="PAUSED"
                    elif action=="resume":
                        with self._lock:session.paused=False;session.owner_control=False;session.state="LIVE"
                    elif action=="takeover":
                        with self._lock:session.paused=True;session.owner_control=True;session.state="OWNER_CONTROL"
                    elif action=="navigate":page.goto(self.validate_url(payload.get("url")),wait_until="domcontentloaded",timeout=self.timeout_ms)
                    elif action=="back":page.go_back(wait_until="domcontentloaded")
                    elif action=="forward":page.go_forward(wait_until="domcontentloaded")
                    elif action=="reload":page.reload(wait_until="domcontentloaded")
                    elif action=="new_tab":
                        page=context.new_page();bind(page);target=str(payload.get("url") or "").strip()
                        if target:page.goto(self.validate_url(target),wait_until="domcontentloaded")
                    elif action=="switch_tab":
                        pages=context.pages;idx=int(payload.get("index",0))
                        if idx<0 or idx>=len(pages):raise ValueError("tab index out of range")
                        page=pages[idx];page.bring_to_front()
                    elif action=="close_tab":
                        pages=context.pages
                        if len(pages)<=1:raise RuntimeError("cannot close the last Garudanetra tab")
                        page.close();page=context.pages[max(0,min(session.tab_index,len(context.pages)-1))];page.bring_to_front()
                    elif action in {"click","fill"}:self._click_or_fill(page,action,payload,session)
                    elif action=="type_text":page.keyboard.insert_text(str(payload.get("text") or ""))
                    elif action=="press":
                        selector=str(payload.get("selector") or "").strip();key=str(payload.get("key") or "Enter")
                        page.locator(selector).press(key) if selector else page.keyboard.press(key)
                    elif action=="click_xy":
                        nx=min(1.0,max(0.0,float(payload.get("x",0.5))));ny=min(1.0,max(0.0,float(payload.get("y",0.5))))
                        page.mouse.click(nx*session.viewport["width"],ny*session.viewport["height"])
                    elif action=="drag_xy":
                        x1=min(1.0,max(0.0,float(payload.get("x1",0.5))));y1=min(1.0,max(0.0,float(payload.get("y1",0.5))))
                        x2=min(1.0,max(0.0,float(payload.get("x2",0.5))));y2=min(1.0,max(0.0,float(payload.get("y2",0.5))))
                        page.mouse.move(x1*session.viewport["width"],y1*session.viewport["height"]);page.mouse.down()
                        page.mouse.move(x2*session.viewport["width"],y2*session.viewport["height"],steps=8);page.mouse.up()
                    elif action=="scroll":page.mouse.wheel(0,int(payload.get("dy",600)))
                    elif action=="upload":
                        selector=str(payload.get("selector") or "").strip()
                        if not selector:raise ValueError("upload selector is required")
                        page.locator(selector).set_input_files(str(self._validate_upload_path(payload.get("path"))))
                    with self._lock:
                        pages=context.pages;session.tab_index=pages.index(page) if page in pages else 0
                        session.current_url=page.url;session.title=page.title();session.updated_at=time.time()
                except queue.Empty:pass
                except Exception as exc:
                    with self._lock:
                        session.last_error=f"{type(exc).__name__}: {exc}"
                        session.findings.append({"kind":"browser_action_error","detail":session.last_error[:1200],"severity":"error"})
                        session.updated_at=time.time()

                if now-last_capture>=0.7:
                    try:
                        frame=page.screenshot(type="png")
                        with self._lock:
                            session.frame=frame;session.current_url=page.url;session.title=page.title();session.tabs=self._tab_snapshot(context);session.updated_at=time.time()
                    except Exception as exc:
                        with self._lock:session.last_error=f"{type(exc).__name__}: {exc}"
                    last_capture=now
                if now-last_text>=2.0:
                    try:
                        text=page.locator("body").inner_text(timeout=min(self.timeout_ms,3000))[:12000]
                        with self._lock:session.visible_text=text
                    except Exception as exc:self._warn(session,"visible_text_error",exc)
                    last_text=now
                if now-last_persist>=3.0:
                    try:self._persist(session)
                    except Exception as exc:self._warn(session,"evidence_persist_error",exc)
                    last_persist=now
        except Exception as exc:
            with self._lock:
                session.state="ERROR";session.last_error=f"{type(exc).__name__}: {exc}"
                session.findings.append({"kind":"browser_runtime_error","detail":session.last_error[:1200],"severity":"critical"});session.updated_at=time.time()
        finally:
            for obj in (context,browser):
                try:
                    if obj:obj.close()
                except Exception as exc:self._warn(session,"browser_cleanup_error",exc)
            try:
                if playwright_cm:playwright_cm.stop()
            except Exception as exc:self._warn(session,"playwright_stop_error",exc)
            with self._lock:
                if session.state!="ERROR":session.state="STOPPED"
                session.stopped=True;session.paused=False;session.owner_control=False;session.updated_at=time.time()
            try:self._persist(session)
            except Exception as exc:self._warn(session,"final_evidence_persist_error",exc)
            if self.on_closed and session.remember_evidence:
                try:self.on_closed(self._snapshot(session))
                except Exception as exc:self._warn(session,"task_memory_callback_error",exc)
