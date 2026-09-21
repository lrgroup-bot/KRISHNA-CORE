from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from threading import RLock
import base64, json, shutil, time, uuid
from urllib.parse import urlparse


@dataclass
class GarudanetraEvent:
    seq: int
    timestamp: float
    phase: str
    action: str
    status: str
    detail: str = ""
    evidence: dict = field(default_factory=dict)


class GarudanetraService:
    """KRISHNA private-by-default browser runtime and UI-observation ledger.

    Private sessions keep browser state only inside the task folder and delete it on stop.
    Persistent mode is explicit and isolated per project; personal Chrome/Edge profiles are never used.
    """
    MODES = {"private", "task_memory", "persistent"}

    def __init__(self, runtime_root: Path, browser_operator, garuda_agent=None):
        self.root = Path(runtime_root) / "garudanetra"
        self.sessions_root = self.root / "sessions"
        self.profiles_root = self.root / "profiles"
        self.evidence_root = self.root / "evidence"
        for p in (self.sessions_root, self.profiles_root, self.evidence_root): p.mkdir(parents=True, exist_ok=True)
        self.browser = browser_operator
        self.garuda = garuda_agent
        self._lock = RLock(); self._sessions = {}

    @staticmethod
    def _safe_project(value):
        s=''.join(c if c.isalnum() or c in '-_.' else '_' for c in str(value or 'KRISHNA'))
        return s[:80] or 'KRISHNA'

    @staticmethod
    def _check_url(url):
        p=urlparse(str(url or '').strip())
        if p.scheme not in {'http','https'} or not p.netloc: raise ValueError('Garudanetra requires an http:// or https:// URL')
        if p.username or p.password: raise ValueError('credentials in URLs are not allowed')
        return p.geturl()

    def _emit(self, s, phase, action, status, detail='', evidence=None):
        s['seq'] += 1
        e=asdict(GarudanetraEvent(s['seq'],time.time(),phase,action,status,str(detail)[:1200],evidence or {}))
        s['events'].append(e); s['events']=s['events'][-300:]; s['updated_at']=time.time(); s['phase']=phase; s['status']=status
        return e

    def start(self, project='KRISHNA', mode='private'):
        mode=str(mode or 'private').lower()
        if mode not in self.MODES: raise ValueError('mode must be private, task_memory, or persistent')
        sid=uuid.uuid4().hex[:16]; project=self._safe_project(project)
        folder=self.sessions_root/sid; folder.mkdir(parents=True,exist_ok=False)
        s={'session_id':sid,'project':project,'mode':mode,'created_at':time.time(),'updated_at':time.time(),'phase':'READY','status':'ready','seq':0,'events':[],'url':None,'title':None,'findings':[],'screenshot':None,'paused':False,'takeover':False}
        self._emit(s,'READY','session_start','ok',f'{mode} browser session created')
        with self._lock:self._sessions[sid]=s
        return self.status(sid)

    def _get(self,sid):
        with self._lock:s=self._sessions.get(str(sid))
        if not s: raise KeyError('Garudanetra session not found')
        return s

    def status(self,sid):
        s=self._get(sid); out={k:v for k,v in s.items() if k!='events'}; out['events']=s['events'][-80:]; out['private']=s['mode']!='persistent'; return out

    def sessions(self):
        with self._lock: vals=list(self._sessions.values())
        return [{k:v for k,v in s.items() if k!='events'} for s in sorted(vals,key=lambda x:x['updated_at'],reverse=True)]

    def navigate(self,sid,url,actions=None):
        s=self._get(sid)
        if s['paused']: raise RuntimeError('Garudanetra session is paused')
        url=self._check_url(url); folder=self.sessions_root/sid; shot=folder/'latest.png'
        self._emit(s,'NAVIGATE','navigate','working',url)
        try:
            report=self.browser.inspect(url,actions=actions or [],screenshot_path=str(shot))
            s['url']=report.get('final_url') or url; s['title']=report.get('title'); s['findings']=report.get('findings') or []; s['screenshot']=str(shot)
            self._emit(s,'VERIFY','browser_verify','ok' if report.get('ok') else 'warning',f"{len(s['findings'])} finding(s)",{'ok':bool(report.get('ok')),'findings':s['findings'][:20]})
            return {'session':self.status(sid),'report':report}
        except Exception as exc:
            self._emit(s,'FAILED','navigate','error',str(exc)); raise

    def ui_guardian(self,sid,url):
        s=self._get(sid); url=self._check_url(url); folder=self.sessions_root/sid
        self._emit(s,'UI_GUARDIAN','inspect_controls','working',url)
        report=self.browser.exhaustive_clickthrough(url,screenshot_dir=str(folder/'ui-guardian'),max_controls=120)
        findings=list(report.get('findings') or [])
        for ev in report.get('evidence') or []:
            if ev.get('ok') is False and not ev.get('skipped'): findings.append({'kind':'broken_control','severity':'error','detail':ev.get('error','interaction failed'),'control':ev.get('label','')})
        report['findings']=findings; report['professional_gui_review']={'objective_defects':len(findings),'recommendation':'repair objective defects first; preserve project design language; verify before promotion'}
        s['findings']=findings; self._emit(s,'VERIFY','ui_guardian','ok' if not findings else 'warning',f'{len(findings)} UI finding(s)',{'findings':findings[:30]})
        return report

    def control(self,sid,command):
        s=self._get(sid); cmd=str(command or '').lower()
        if cmd=='pause': s['paused']=True; self._emit(s,'PAUSED','pause','warning','operator paused browser work')
        elif cmd in {'resume','continue'}: s['paused']=False; s['takeover']=False; self._emit(s,'READY','resume','ok','KRISHNA browser work resumed')
        elif cmd=='takeover': s['paused']=True; s['takeover']=True; self._emit(s,'TAKEOVER','human_takeover','warning','human control requested')
        else: raise ValueError('command must be pause, takeover, or resume')
        return self.status(sid)

    def frame(self,sid):
        s=self._get(sid); p=Path(s.get('screenshot') or '')
        if not p.is_file(): return None
        return p.read_bytes()

    def stop(self,sid):
        s=self._get(sid); self._emit(s,'STOPPED','session_stop','ok','browser session closed')
        snapshot=self.status(sid)
        if s['mode']=='task_memory':
            dst=self.evidence_root/f"{sid}.json"; dst.write_text(json.dumps({'project':s['project'],'events':s['events'],'findings':s['findings'],'url':s['url']},indent=2),encoding='utf-8')
        folder=self.sessions_root/sid
        if s['mode']!='persistent': shutil.rmtree(folder,ignore_errors=True)
        with self._lock:self._sessions.pop(sid,None)
        snapshot['destroyed_private_state']=s['mode']!='persistent'; return snapshot

    def search(self,project,query,limit=10):
        if not self.garuda: raise RuntimeError('Garuda search agent unavailable')
        return self.garuda.scout(project,str(query or '').strip(),limit)
