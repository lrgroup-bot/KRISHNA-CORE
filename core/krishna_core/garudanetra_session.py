from __future__ import annotations

import base64
import json
import queue
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlsplit, urlunsplit

from .garudanetra_recovery import BrowserRecoveryAdapter


_SAFE_NAME=re.compile(r"[^A-Za-z0-9._-]+")
_SENSITIVE_URL_KEY=re.compile(r"(?:token|secret|pass(?:word)?|api[_-]?key|auth|signature|credential|session|code)",re.I)
BROWSER_MODES={"private","task_memory","persistent_workspace"}


def _redact_url(value)->str:
    raw=str(value or "")
    try:
        parsed=urlsplit(raw)
        netloc=parsed.netloc.rsplit("@",1)[-1]
        query=urlencode([(key,"REDACTED" if _SENSITIVE_URL_KEY.search(key) else val)
                         for key,val in parse_qsl(parsed.query,keep_blank_values=True)],doseq=True)
        fragment="REDACTED" if parsed.fragment and _SENSITIVE_URL_KEY.search(parsed.fragment) else parsed.fragment
        return urlunsplit((parsed.scheme,netloc,parsed.path,query,fragment))
    except Exception:
        return "[invalid-url]"


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
    frame_mime: str = "image/png"
    frame_seq: int = 0
    stream_mode: str = "starting"
    tab_index: int = 0
    remember_evidence: bool = False
    profile_path: str | None = None
    semantic_revision: int = 0
    semantic_items: list[dict] = field(default_factory=list)
    recording: list[dict] = field(default_factory=list)


class GarudanetraSessionManager:
    """Private/task-memory/persistent Chromium sessions for KRISHNA.

    private: isolated context, destroyed on stop, no durable browser evidence.
    task_memory: isolated context, destroyed on stop, evidence summary persisted.
    persistent_workspace: project-specific browser profile, only with explicit approval.
    """

    ACTIONS={
        "pause","resume","takeover","stop","navigate","back","forward","reload",
        "new_tab","switch_tab","close_tab","click","dblclick","fill","type_text","press",
        "hover","focus","select_option","check","uncheck","scroll_into_view",
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
            "session_id":session.session_id,"project":session.project,"requested_url":_redact_url(session.requested_url),
            "mode":session.mode,"state":session.state,"current_url":_redact_url(session.current_url),"title":session.title,
            "paused":session.paused,"owner_control":session.owner_control,"stopped":session.stopped,
            "created_at":session.created_at,"updated_at":session.updated_at,"last_error":session.last_error,
            "viewport":dict(session.viewport),"visible_text":session.visible_text[:6000],
            "console":list(session.console[-50:]),
            "network":[{**row,"url":_redact_url(row.get("url"))} for row in session.network[-100:]],
            "findings":list(session.findings[-100:]),"downloads":list(session.downloads[-50:]),
            "tabs":[{**row,"url":_redact_url(row.get("url"))} for row in session.tabs[-30:]],
            "frame_available":bool(session.frame),"frame_mime":session.frame_mime,
            "frame_seq":session.frame_seq,"stream_mode":session.stream_mode,"tab_index":session.tab_index,
            "semantic_revision":session.semantic_revision,"semantic_count":len(session.semantic_items),
            "recording_steps":len(session.recording),"recording":[dict(x) for x in session.recording[-200:]],
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

    def frame_info(self,session_id):
        session=self._get(session_id)
        with self._lock:
            return {
                "bytes":bytes(session.frame) if session.frame else None,
                "mime":session.frame_mime,
                "seq":session.frame_seq,
                "stream_mode":session.stream_mode,
            }

    def semantic_snapshot(self,session_id):
        session=self._get(session_id)
        with self._lock:
            return {
                "session_id":session.session_id,
                "url":_redact_url(session.current_url),
                "title":session.title,
                "revision":session.semantic_revision,
                "items":[dict(x) for x in session.semantic_items],
            }

    def element_at(self,session_id,x,y,normalized=True):
        session=self._get(session_id)
        px=float(x);py=float(y)
        if normalized:
            px=min(1.0,max(0.0,px))*float(session.viewport.get("width") or 1)
            py=min(1.0,max(0.0,py))*float(session.viewport.get("height") or 1)
        with self._lock:
            rows=[dict(item) for item in session.semantic_items
                  if float(item.get("x",0))<=px<=float(item.get("x",0))+float(item.get("width",0))
                  and float(item.get("y",0))<=py<=float(item.get("y",0))+float(item.get("height",0))]
        rows.sort(key=lambda item:max(1.0,float(item.get("width",0))*float(item.get("height",0))))
        if not rows:
            return {"session_id":session.session_id,"x":px,"y":py,"element":None}
        return {"session_id":session.session_id,"x":px,"y":py,"element":rows[0]}

    def recording(self,session_id):
        session=self._get(session_id)
        with self._lock:
            return {
                "session_id":session.session_id,
                "project":session.project,
                "mode":session.mode,
                "steps":[dict(x) for x in session.recording],
                "count":len(session.recording),
                "policy":"typed/fill values are redacted unless remember_value=true; consequential replay requires approval",
            }

    def replay(self,session_id,steps=None,approved=False):
        session=self._get(session_id)
        rows=list(steps if steps is not None else session.recording)
        safe={"navigate","back","forward","reload","switch_tab","scroll","pause","resume","hover","focus","scroll_into_view"}
        queued=[];blocked=[]
        for row in rows[:50]:
            if str(row.get("status") or "ok")!="ok":continue
            action=str(row.get("action") or "").strip().lower()
            payload=dict(row.get("payload") or {})
            if not action or action not in self.ACTIONS:continue
            if action not in safe and not approved:
                blocked.append({"action":action,"reason":"explicit approval required"})
                continue
            if any(str(v)=="[REDACTED]" for v in payload.values()):
                blocked.append({"action":action,"reason":"recorded secret/value is redacted"})
                continue
            try:
                self._commands[session.session_id].put_nowait({"action":action,"payload":payload,"replay":True})
                queued.append(action)
            except queue.Full:
                blocked.append({"action":action,"reason":"command queue full"});break
        return {"session_id":session.session_id,"queued":queued,"blocked":blocked,"approved":bool(approved)}

    def command(self,session_id,action,payload=None):
        session=self._get(session_id);action=str(action or "").strip().lower()
        if action not in self.ACTIONS:raise ValueError(f"unsupported Garudanetra action: {action}")
        if session.stopped:raise RuntimeError("Garudanetra session is already stopped")
        try:self._commands[session.session_id].put_nowait({"action":action,"payload":dict(payload or {})})
        except queue.Full as exc:raise RuntimeError("Garudanetra command queue is full") from exc
        return self.status(session.session_id)

    def close_all(self,timeout=5.0):
        with self._lock:ids=list(self._sessions)
        for sid in ids:
            try:
                if not self._get(sid).stopped:self.command(sid,"stop")
            except Exception as exc:
                try:self._warn(self._get(sid),"close_all_error",exc)
                except KeyError:continue
        deadline=time.time()+max(0.0,float(timeout))
        for sid in ids:
            thread=self._threads.get(sid)
            if not thread or not thread.is_alive():continue
            remaining=max(0.0,deadline-time.time())
            if remaining<=0:break
            thread.join(timeout=remaining)
        with self._lock:
            return {"requested":len(ids),"running":sum(1 for sid in ids if self._threads.get(sid) and self._threads[sid].is_alive())}

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
            safe_url=_redact_url(url)[:1500]
            session.network.append({"method":method,"url":safe_url,"status":int(status),"at":time.time()});del session.network[:-400]
            if int(status)>=400:session.findings.append({"kind":"http_error","detail":f"{status} {safe_url}"[:1200],"severity":"error"})

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
            rows.append({"index":i,"url":_redact_url(p.url),"title":title})
        return rows

    def _record_action(self,session,action,payload,status="ok",detail=""):
        safe={}
        for k,v in dict(payload or {}).items():
            key=str(k)
            if key in {"password","secret","token"}:
                safe[key]="[REDACTED]"
            elif key in {"value","text"} and not bool(payload.get("remember_value",False)):
                safe[key]="[REDACTED]"
            elif key=="url":
                safe[key]=_redact_url(v)
            elif key!="remember_value":
                safe[key]=v
        row={"at":time.time(),"action":str(action),"payload":safe,"status":str(status)}
        if detail:row["detail"]=str(detail)[:1000]
        with self._lock:
            session.recording.append(row);del session.recording[:-500]

    def _semantic_capture(self,page,session):
        revision=session.semantic_revision+1
        prefix=f"k{revision}-"
        script=r"""({prefix}) => {
          for (const el of document.querySelectorAll('[data-krishna-ref]')) el.removeAttribute('data-krishna-ref');
          const selector='a[href],button,input:not([type=hidden]),textarea,select,[role=button],[role=link],[role=checkbox],[role=radio],[role=combobox],[tabindex]:not([tabindex="-1"])';
          const nodes=[...document.querySelectorAll(selector)].slice(0,350);
          const roleOf=(el)=>{
            const explicit=el.getAttribute('role'); if(explicit)return explicit;
            const tag=el.tagName.toLowerCase(),type=(el.getAttribute('type')||'').toLowerCase();
            if(tag==='a')return 'link'; if(tag==='button')return 'button';
            if(tag==='textarea')return 'textbox'; if(tag==='select')return 'combobox';
            if(tag==='input'&&type==='checkbox')return 'checkbox';
            if(tag==='input'&&type==='radio')return 'radio';
            if(tag==='input')return 'textbox'; return 'interactive';
          };
          const nameOf=(el)=>{
            const type=(el.getAttribute('type')||'').toLowerCase();
            const raw=el.getAttribute('aria-label')||el.getAttribute('title')||el.getAttribute('placeholder')||
              (type==='password'?'':(el.innerText||el.value||''))||el.getAttribute('name')||'';
            return String(raw).replace(/\s+/g,' ').trim().slice(0,220);
          };
          return nodes.map((el,i)=>{
            const r=el.getBoundingClientRect(),ref='e'+(i+1),marker=prefix+ref;
            el.setAttribute('data-krishna-ref',marker);
            const tag=el.tagName.toLowerCase(),id=el.id||'',classes=Array.from(el.classList||[]).slice(0,6);
            const selectorHint=id?('#'+id):(classes.length?(tag+'.'+classes.join('.')):tag);
            return {ref,selector:'[data-krishna-ref="'+marker+'"]',selector_hint:selectorHint,id,classes,
              role:roleOf(el),name:nameOf(el),tag,visible:!!(r.width&&r.height),x:Math.round(r.x),y:Math.round(r.y),
              width:Math.round(r.width),height:Math.round(r.height),disabled:!!el.disabled};
          }).filter(x=>x.visible);
        }"""
        items=page.evaluate(script,{"prefix":prefix})
        with self._lock:
            session.semantic_revision=revision
            session.semantic_items=list(items or [])[:350]
        return session.semantic_items

    def _locator(self,page,payload,session):
        ref=str(payload.get("ref") or "").strip()
        if ref:
            with self._lock:item=next((x for x in session.semantic_items if x.get("ref")==ref),None)
            if not item:raise ValueError(f"unknown semantic ref: {ref}")
            loc=page.locator(str(item.get("selector") or ""))
            if loc.count()>0:return loc.first
            raise RuntimeError(f"semantic ref is stale: {ref}")
        selector=str(payload.get("selector") or "").strip()
        if selector:
            loc=page.locator(selector)
            if loc.count()>0:return loc.first
        raise ValueError("selector or semantic ref is required")

    def _click_or_fill(self,page,action,payload,session):
        selector=str(payload.get("selector") or payload.get("ref") or "").strip()
        try:
            loc=self._locator(page,payload,session)
            if action=="click":loc.click()
            else:loc.fill(str(payload.get("value") or ""))
            return
        except Exception as first:
            recovery_payload=dict(payload or {})
            ref=str(recovery_payload.get("ref") or "").strip()
            if ref:
                with self._lock:item=next((x for x in session.semantic_items if x.get("ref")==ref),None)
                if item:
                    for key in ("role","name","tag"):
                        if item.get(key) and not recovery_payload.get(key):recovery_payload[key]=item.get(key)
            recovered=self.recovery.recover_locator(page,recovery_payload)
            loc=recovered["locator"]
            if action=="click":loc.click()
            else:loc.fill(str(payload.get("value") or ""))
            with self._lock:
                session.findings.append({"kind":"selector_recovered","detail":recovered["strategy"],"severity":"notice",
                                         "candidate_skill":{"original_selector":selector,"payload":{k:v for k,v in payload.items() if k!="value"},
                                                            "strategy":recovered["strategy"],"source":recovered["source"]}})

    def _start_screencast(self,context,page,session):
        try:
            cdp=context.new_cdp_session(page)
            def on_frame(params):
                try:
                    raw=base64.b64decode(params.get("data") or "")
                    if raw:
                        with self._lock:
                            session.frame=raw;session.frame_mime="image/jpeg";session.frame_seq+=1
                            session.stream_mode="cdp_screencast";session.updated_at=time.time()
                    frame_id=params.get("sessionId")
                    if frame_id is not None:
                        cdp.send("Page.screencastFrameAck",{"sessionId":frame_id})
                except Exception as exc:
                    self._warn(session,"cdp_screencast_frame_error",exc)
            cdp.on("Page.screencastFrame",on_frame)
            cdp.send("Page.startScreencast",{
                "format":"jpeg","quality":72,
                "maxWidth":int(session.viewport["width"]),"maxHeight":int(session.viewport["height"]),
                "everyNthFrame":1,
            })
            with self._lock:session.stream_mode="cdp_screencast"
            return cdp
        except Exception as exc:
            with self._lock:session.stream_mode="screenshot_fallback"
            self._warn(session,"cdp_screencast_unavailable",exc)
            return None

    def _stop_screencast(self,cdp,session):
        if not cdp:return
        try:cdp.send("Page.stopScreencast")
        except Exception as exc:self._warn(session,"cdp_screencast_stop_error",exc)
        try:cdp.detach()
        except Exception:pass

    def _worker(self,sid):
        session=self._get(sid);browser=context=page=None;playwright_cm=None;stream_cdp=None
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
            stream_cdp=self._start_screencast(context,page,session)
            try:self._semantic_capture(page,session)
            except Exception as exc:self._warn(session,"semantic_snapshot_error",exc)
            with self._lock:session.state="LIVE";session.current_url=page.url;session.title=page.title();session.tabs=self._tab_snapshot(context);session.updated_at=time.time()

            last_capture=last_text=last_persist=0.0
            while True:
                now=time.time()
                try:
                    cmd=self._commands[sid].get(timeout=0.12);action,payload=cmd["action"],cmd["payload"]
                    if action=="stop":
                        self._record_action(session,action,payload,"ok")
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
                        self._stop_screencast(stream_cdp,session);stream_cdp=None
                        page=context.new_page();bind(page);target=str(payload.get("url") or "").strip()
                        if target:page.goto(self.validate_url(target),wait_until="domcontentloaded")
                        stream_cdp=self._start_screencast(context,page,session)
                    elif action=="switch_tab":
                        pages=context.pages;idx=int(payload.get("index",0))
                        if idx<0 or idx>=len(pages):raise ValueError("tab index out of range")
                        self._stop_screencast(stream_cdp,session);stream_cdp=None
                        page=pages[idx];page.bring_to_front();stream_cdp=self._start_screencast(context,page,session)
                    elif action=="close_tab":
                        pages=context.pages
                        if len(pages)<=1:raise RuntimeError("cannot close the last Garudanetra tab")
                        self._stop_screencast(stream_cdp,session);stream_cdp=None
                        page.close();page=context.pages[max(0,min(session.tab_index,len(context.pages)-1))];page.bring_to_front()
                        stream_cdp=self._start_screencast(context,page,session)
                    elif action in {"click","fill"}:self._click_or_fill(page,action,payload,session)
                    elif action=="dblclick":self._locator(page,payload,session).dblclick()
                    elif action=="hover":self._locator(page,payload,session).hover()
                    elif action=="focus":self._locator(page,payload,session).focus()
                    elif action=="select_option":self._locator(page,payload,session).select_option(str(payload.get("value") or ""))
                    elif action=="check":self._locator(page,payload,session).check()
                    elif action=="uncheck":self._locator(page,payload,session).uncheck()
                    elif action=="scroll_into_view":self._locator(page,payload,session).scroll_into_view_if_needed()
                    elif action=="type_text":page.keyboard.insert_text(str(payload.get("text") or ""))
                    elif action=="press":
                        key=str(payload.get("key") or "Enter")
                        if payload.get("selector") or payload.get("ref"):self._locator(page,payload,session).press(key)
                        else:page.keyboard.press(key)
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
                        self._locator(page,payload,session).set_input_files(str(self._validate_upload_path(payload.get("path"))))
                    self._record_action(session,action,payload,"ok")
                    try:self._semantic_capture(page,session)
                    except Exception as exc:self._warn(session,"semantic_snapshot_error",exc)
                    with self._lock:
                        pages=context.pages;session.tab_index=pages.index(page) if page in pages else 0
                        session.current_url=page.url;session.title=page.title();session.updated_at=time.time()
                except queue.Empty:pass
                except Exception as exc:
                    self._record_action(session,locals().get("action","unknown"),locals().get("payload",{}),"error",f"{type(exc).__name__}: {exc}")
                    with self._lock:
                        session.last_error=f"{type(exc).__name__}: {exc}"
                        session.findings.append({"kind":"browser_action_error","detail":session.last_error[:1200],"severity":"error"})
                        session.updated_at=time.time()

                if now-last_capture>=0.7 and stream_cdp is None:
                    try:
                        frame=page.screenshot(type="png")
                        with self._lock:
                            session.frame=frame;session.frame_mime="image/png";session.frame_seq+=1
                            session.stream_mode="screenshot_fallback";session.current_url=page.url
                            session.title=page.title();session.tabs=self._tab_snapshot(context);session.updated_at=time.time()
                    except Exception as exc:
                        with self._lock:session.last_error=f"{type(exc).__name__}: {exc}"
                    last_capture=now
                if now-last_text>=2.0:
                    try:
                        text=page.locator("body").inner_text(timeout=min(self.timeout_ms,3000))[:12000]
                        with self._lock:session.visible_text=text
                        self._semantic_capture(page,session)
                    except Exception as exc:self._warn(session,"visible_text_or_semantic_error",exc)
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
            self._stop_screencast(stream_cdp,session)
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
