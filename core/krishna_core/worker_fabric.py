from __future__ import annotations
import subprocess, time
from pathlib import Path
class WorkerFabric:
    """Supervisor for optional heavy workers. One app, isolated child processes."""
    def __init__(self,runtime_root): self.root=Path(runtime_root); self.workers={}
    def register(self,name,command,cwd=None,kind='specialized',autostart=False): self.workers[name]={"name":name,"command":command,"cwd":str(cwd or self.root),"kind":kind,"autostart":autostart,"process":None,"started":None}
    def start(self,name):
        w=self.workers[name]; p=w.get('process')
        if p and p.poll() is None: return self.describe(name)
        w['process']=subprocess.Popen(w['command'],cwd=w['cwd'],shell=isinstance(w['command'],str),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); w['started']=time.time(); return self.describe(name)
    def stop(self,name):
        w=self.workers[name]; p=w.get('process')
        if p and p.poll() is None: p.terminate()
        return self.describe(name)
    def describe(self,name):
        w=self.workers[name]; p=w.get('process'); running=bool(p and p.poll() is None)
        return {"name":name,"kind":w['kind'],"running":running,"pid":p.pid if running else None,"autostart":w['autostart']}
    def status(self): return {k:self.describe(k) for k in self.workers}
