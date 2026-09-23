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

def _first_existing_file(candidates):
    for raw in candidates:
        if not raw:
            continue
        try:
            p=Path(raw).expanduser()
            if p.is_file():
                return str(p.resolve())
        except (OSError, ValueError):
            continue
    return None

class CodebaseMemoryAdapter:
    """Optional CBM bridge. KRISHNA remains authority; CBM supplies structural code intelligence."""
    KNOWN_WINDOWS_BINARIES=(
        "E:/AI-Tools/codebase-memory-mcp/codebase-memory-mcp.exe",
        "E:/CBM-Runtime/codebase-memory-mcp.exe",
        "E:/KRISHNA-CBM/codebase-memory-mcp.exe",
    )
    def __init__(self, executable=None, cache_root=None):
        if executable is not None:
            self.executable=_first_existing_file([executable]) if executable else None
            self.discovery="explicit"
        else:
            env=os.getenv("KRISHNA_CBM_BIN")
            path_hit=shutil.which("codebase-memory-mcp")
            self.executable=_first_existing_file([env,path_hit,*self.KNOWN_WINDOWS_BINARIES])
            self.discovery=("environment" if env and self.executable and Path(self.executable)==Path(env).resolve()
                            else "path" if path_hit and self.executable and Path(self.executable)==Path(path_hit).resolve()
                            else "known_e_drive" if self.executable else "not_found")
        self.cache_root=Path(cache_root or os.getenv("KRISHNA_CBM_CACHE","E:/CBM-Cache"))
    def status(self):
        out=AdapterStatus("codebase-memory-mcp",bool(self.executable),"subprocess/mcp",
                          str(self.executable or "not found")).as_dict()
        out.update({
            "executable":self.executable,"cache_root":str(self.cache_root),"discovery":self.discovery,
            "operations":["query","project_context"],"authority":"read-only structural intelligence",
        })
        return out
    def command(self,*args):
        if not self.executable: raise RuntimeError("codebase-memory-mcp is not installed/configured")
        return [str(self.executable),*map(str,args)]
    def _run(self,args,timeout=30):
        if not self.executable: raise RuntimeError("codebase-memory-mcp is not installed/configured")
        env=dict(os.environ);env["KRISHNA_CBM_CACHE"]=str(self.cache_root)
        p=subprocess.run(self.command(*args),capture_output=True,text=True,timeout=timeout,env=env,shell=False)
        if p.returncode: raise RuntimeError((p.stderr or p.stdout or "").strip())
        text=(p.stdout or "").strip()
        try:return json.loads(text)
        except Exception:return {"text":text[:30000]}
    def query(self,text,*,project_root=None,limit=20):
        q=str(text or "").strip()
        if not q:raise ValueError("CBM query is required")
        args=["query","--limit",str(max(1,min(int(limit),100))),q]
        if project_root:
            root=Path(project_root).resolve()
            args[1:1]=["--root",str(root)]
        return self._run(args)
    def project_context(self,project_root,*,limit=200):
        root=Path(project_root).resolve()
        if not root.is_dir():raise FileNotFoundError(str(root))
        return self._run(["context","--root",str(root),"--limit",str(max(1,min(int(limit),1000)))])

class GraftMemoryAdapter:
    """Optional local Graft bridge behind Gyan-Bhandar; never replaces canonical MemoryFabric."""
    KNOWN_WINDOWS_BINARIES=(
        "E:/AI-Tools/Graft/graft.exe",
        "E:/CBM-Runtime/graft.exe",
        "E:/KRISHNA-CBM/graft.exe",
    )
    def __init__(self, executable=None, profile="krishna"):
        if executable is not None:
            self.executable=_first_existing_file([executable]) if executable else None
            self.discovery="explicit"
        else:
            env=os.getenv("KRISHNA_GRAFT_BIN")
            path_hit=shutil.which("graft")
            self.executable=_first_existing_file([env,path_hit,*self.KNOWN_WINDOWS_BINARIES])
            self.discovery=("environment" if env and self.executable and Path(self.executable)==Path(env).resolve()
                            else "path" if path_hit and self.executable and Path(self.executable)==Path(path_hit).resolve()
                            else "known_e_drive" if self.executable else "not_found")
        self.profile=profile
    def status(self):
        out=AdapterStatus("graft",bool(self.executable),"cli/local",
                          str(self.executable or "not found")).as_dict()
        out.update({
            "executable":self.executable,"profile":self.profile,"discovery":self.discovery,
            "authority":"optional read/query backing only; Gyan-Bhandar remains canonical",
        })
        return out
    def _run(self,args,timeout=20):
        if not self.executable: raise RuntimeError("graft is not installed/configured")
        env=dict(os.environ); env["GRAFT_PROFILE"]=self.profile
        p=subprocess.run([self.executable,*args],capture_output=True,text=True,timeout=timeout,env=env,shell=False)
        if p.returncode: raise RuntimeError((p.stderr or p.stdout).strip())
        return p.stdout.strip()
    def query(self,text):
        q=str(text or "").strip()
        if not q:raise ValueError("graft query is required")
        return self._run(["query",q])
    def stats(self): return self._run(["stats"])

class WebhookAdapter:
    """Minimal JSON webhook client used by Narad provider adapters."""
    def post(self,url,payload,headers=None,timeout=15):
        data=json.dumps(payload).encode("utf-8")
        req=urllib.request.Request(url,data=data,headers={"Content-Type":"application/json",**(headers or {})},method="POST")
        with urllib.request.urlopen(req,timeout=timeout) as r:
            return {"status":r.status,"body":r.read().decode("utf-8","replace")[:20000]}
