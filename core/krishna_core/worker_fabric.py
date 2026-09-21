from __future__ import annotations

import os
import shlex
import subprocess
import threading
import time
from pathlib import Path


class WorkerFabric:
    """Supervisor for optional heavy workers with crash-loop quarantine."""

    def __init__(self,runtime_root):
        self.root=Path(runtime_root)
        self.workers={}
        self._lock=threading.RLock()

    def register(self,name,command,cwd=None,kind="specialized",autostart=False):
        with self._lock:
            existing=self.workers.get(name,{})
            self.workers[name]={
                "name":name,"command":command,"cwd":str(cwd or self.root),"kind":kind,
                "autostart":bool(autostart),"desired":bool(autostart),
                "process":existing.get("process"),"started":existing.get("started"),
                "restart_count":int(existing.get("restart_count") or 0),
                "crashes":list(existing.get("crashes") or []),
                "backoff_until":float(existing.get("backoff_until") or 0),
                "quarantined":bool(existing.get("quarantined",False)),
                "last_exit":existing.get("last_exit"),"last_error":existing.get("last_error"),
            }
        return self.describe(name)

    def _spawn(self,w):
        command=w["command"]
        if isinstance(command,str):
            raw=command.strip()
            if not raw:raise ValueError("worker command is empty")
            args=raw if os.name=="nt" else shlex.split(raw,posix=True)
        else:
            args=list(command or [])
            if not args:raise ValueError("worker command is empty")
        p=subprocess.Popen(args,cwd=w["cwd"],shell=False,
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        w["process"]=p;w["started"]=time.time();w["last_error"]=None
        return p

    def start(self,name):
        with self._lock:
            w=self.workers[name]
            if w.get("quarantined"):raise RuntimeError(f"worker quarantined after crash loop: {name}")
            w["desired"]=True
            p=w.get("process")
            if p and p.poll() is None:return self.describe(name)
            self._spawn(w)
            return self.describe(name)

    def stop(self,name):
        with self._lock:
            w=self.workers[name];w["desired"]=False
            p=w.get("process")
            if p and p.poll() is None:
                p.terminate()
                try:p.wait(timeout=5)
                except Exception:
                    try:p.kill()
                    except Exception as exc:w["last_error"]=f"kill_failed: {type(exc).__name__}: {exc}"
            return self.describe(name)

    def quarantine(self,name,reason="manual"):
        with self._lock:
            w=self.workers[name];w["quarantined"]=True;w["desired"]=False;w["last_error"]=str(reason)
            p=w.get("process")
            if p and p.poll() is None:
                try:p.terminate()
                except Exception as exc:w["last_error"]=f"terminate_failed: {type(exc).__name__}: {exc}"
            return self.describe(name)

    def clear_quarantine(self,name):
        with self._lock:
            w=self.workers[name];w["quarantined"]=False;w["crashes"]=[];w["restart_count"]=0;w["backoff_until"]=0;w["last_error"]=None
            return self.describe(name)

    def describe(self,name):
        with self._lock:
            w=self.workers[name];p=w.get("process");running=bool(p and p.poll() is None)
            return {"name":name,"kind":w["kind"],"running":running,"pid":p.pid if running else None,
                    "autostart":w["autostart"],"desired":w["desired"],"started":w["started"],
                    "restart_count":w["restart_count"],"quarantined":w["quarantined"],
                    "backoff_until":w["backoff_until"],"last_exit":w["last_exit"],"last_error":w["last_error"]}

    def status(self):
        with self._lock:names=list(self.workers)
        return {k:self.describe(k) for k in names}

    def tick(self,now=None):
        now=float(now or time.time());events=[]
        with self._lock:
            for name,w in self.workers.items():
                p=w.get("process")
                if p and p.poll() is not None:
                    code=p.returncode
                    if w.get("last_exit") != {"code":code,"at":w.get("_exit_seen_at")}:
                        w["_exit_seen_at"]=now;w["last_exit"]={"code":code,"at":now}
                        w["crashes"]=[x for x in w.get("crashes",[]) if now-x<600]+[now]
                        w["process"]=None
                        if w.get("desired"):
                            if len(w["crashes"])>=5:
                                w["quarantined"]=True;w["desired"]=False
                                w["last_error"]="crash loop: 5 exits within 10 minutes"
                                events.append({"worker":name,"event":"quarantined","reason":w["last_error"]})
                            else:
                                w["restart_count"]+=1
                                delay=min(60,2**min(w["restart_count"]-1,6))
                                w["backoff_until"]=now+delay
                                events.append({"worker":name,"event":"restart_scheduled","delay_seconds":delay,"exit_code":code})
                if w.get("desired") and not w.get("quarantined") and not w.get("process") and now>=float(w.get("backoff_until") or 0):
                    try:
                        self._spawn(w)
                        events.append({"worker":name,"event":"restarted","pid":w["process"].pid})
                    except Exception as exc:
                        w["last_error"]=f"{type(exc).__name__}: {exc}"
                        w["backoff_until"]=now+min(60,2**min(max(0,w["restart_count"]),6))
                        events.append({"worker":name,"event":"restart_failed","error":w["last_error"]})
        return events


class WorkerResilienceSupervisor:
    def __init__(self,fabric:WorkerFabric,interval=5,on_event=None):
        self.fabric=fabric;self.interval=max(1,float(interval));self.on_event=on_event
        self._stop=threading.Event();self._thread=None;self.last_events=[];self.run_count=0

    def start(self):
        if self._thread and self._thread.is_alive():return self.status()
        self._stop.clear();self._thread=threading.Thread(target=self._loop,name="krishna-worker-resilience",daemon=True);self._thread.start()
        return self.status()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():self._thread.join(timeout=3)
        return self.status()

    def _loop(self):
        while not self._stop.wait(self.interval):
            try:
                events=self.fabric.tick()
                self.run_count+=1
                if events:
                    self.last_events=(events+self.last_events)[:100]
                    if self.on_event:
                        for e in events:
                            try:self.on_event(e)
                            except Exception as exc:
                                self.last_events=([{"event":"callback_error","error":f"{type(exc).__name__}: {exc}","source_event":e}]+self.last_events)[:100]
            except Exception as exc:
                self.last_events=([{"event":"supervisor_error","error":f"{type(exc).__name__}: {exc}"}]+self.last_events)[:100]

    def status(self):
        return {"running":bool(self._thread and self._thread.is_alive()),"interval_seconds":self.interval,
                "run_count":self.run_count,"last_events":list(self.last_events[:30]),"workers":self.fabric.status()}
