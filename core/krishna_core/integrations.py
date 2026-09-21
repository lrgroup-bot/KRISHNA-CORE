from __future__ import annotations
import json, os, shutil, subprocess, urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class AdapterStatus:
    name: str
    available: bool
    mode: str
    detail: str = ""
    def as_dict(self): return asdict(self)

class CodebaseMemoryAdapter:
    """Optional CBM bridge. KRISHNA remains the authority; CBM is structural code intelligence."""
    def __init__(self, executable=None, cache_root=None):
        self.executable=executable or os.getenv("KRISHNA_CBM_BIN") or shutil.which("codebase-memory-mcp")
        self.cache_root=Path(cache_root or os.getenv("KRISHNA_CBM_CACHE","E:/CBM-Cache"))
    def status(self):
        return AdapterStatus("codebase-memory-mcp",bool(self.executable),"subprocess/mcp",str(self.executable or "not found")).as_dict()
    def command(self,*args):
        if not self.executable: raise RuntimeError("codebase-memory-mcp is not installed/configured")
        return [str(self.executable),*map(str,args)]

class GraftMemoryAdapter:
    """Optional local Graft bridge behind Gyan-Bhandar; never replaces the canonical MemoryFabric."""
    def __init__(self, executable=None, profile="krishna"):
        self.executable=executable or os.getenv("KRISHNA_GRAFT_BIN") or shutil.which("graft")
        self.profile=profile
    def status(self):
        return AdapterStatus("graft",bool(self.executable),"cli/local",str(self.executable or "not found")).as_dict()
    def _run(self,args,timeout=20):
        if not self.executable: raise RuntimeError("graft is not installed/configured")
        env=dict(os.environ); env["GRAFT_PROFILE"]=self.profile
        p=subprocess.run([self.executable,*args],capture_output=True,text=True,timeout=timeout,env=env)
        if p.returncode: raise RuntimeError((p.stderr or p.stdout).strip())
        return p.stdout.strip()
    def query(self,text): return self._run(["query",text])
    def stats(self): return self._run(["stats"])

class WebhookAdapter:
    """Minimal JSON webhook client used by Narad provider adapters."""
    def post(self,url,payload,headers=None,timeout=15):
        data=json.dumps(payload).encode("utf-8")
        req=urllib.request.Request(url,data=data,headers={"Content-Type":"application/json",**(headers or {})},method="POST")
        with urllib.request.urlopen(req,timeout=timeout) as r:
            return {"status":r.status,"body":r.read().decode("utf-8","replace")[:20000]}
