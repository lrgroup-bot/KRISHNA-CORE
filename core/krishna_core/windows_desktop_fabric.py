from __future__ import annotations

"""Capability-gated Windows desktop computer-use provider.

KRISHNA never exposes a raw arbitrary-Python desktop tool. The first provider is the
Apache-2.0 Agent Desktop Harness (ADH), used only through its validated RPA boundary.
Provider source is not bundled and no installation is performed implicitly.
"""

from pathlib import Path
import json
import os
import subprocess
import time


class WindowsDesktopFabric:
    PROVIDER="agent-desktop-harness"
    LICENSE="Apache-2.0"

    def __init__(self,runtime_root):
        self.runtime_root=Path(runtime_root).resolve()
        configured=os.getenv("KRISHNA_ADH_EXE","").strip()
        self.exe=Path(configured).resolve() if configured else (
            self.runtime_root/"tools"/"desktop"/"adh"/"adh.exe"
        ).resolve()
        self.workspace=(self.runtime_root/"workspace"/"desktop-rpa").resolve()
        self.output_root=(self.runtime_root/"reports"/"desktop-rpa").resolve()
        self.workspace.mkdir(parents=True,exist_ok=True)
        self.output_root.mkdir(parents=True,exist_ok=True)
        self.last_run=None

    def _inside(self,path,root):
        p=Path(path).resolve();root=Path(root).resolve()
        try:p.relative_to(root)
        except ValueError as exc:raise PermissionError("desktop RPA path is outside KRISHNA authorized workspace") from exc
        return p

    def _command(self,args,timeout=60):
        if not self.exe.is_file():
            raise RuntimeError("ADH desktop provider is not installed/configured on the KRISHNA E: runtime")
        if self.exe.drive and self.exe.drive.upper()!="E:":
            raise PermissionError("KRISHNA desktop provider executable must be stored on E:")
        started=time.perf_counter()
        p=subprocess.run([str(self.exe),*args],capture_output=True,text=True,timeout=timeout,shell=False)
        detail=((p.stdout or "")+"\n"+(p.stderr or "")).strip()
        result={"ok":p.returncode==0,"exit_code":p.returncode,"output":detail[-30000:],
                "elapsed_ms":int((time.perf_counter()-started)*1000)}
        if not result["ok"]:raise RuntimeError("ADH command failed: "+(detail[-4000:] or f"exit {p.returncode}"))
        return result

    def status(self,probe=False):
        available=self.exe.is_file() and (not self.exe.drive or self.exe.drive.upper()=="E:")
        out={"owner":"KRISHNA Windows Desktop Fabric","provider":self.PROVIDER,"license":self.LICENSE,
             "available":available,"executable":str(self.exe),"workspace":str(self.workspace),
             "mode":"validated-rpa-only","raw_python_exposed":False,"mcp_authority":False,
             "policy":"observe/validate may be delegated; desktop mutation requires Sudarshan approval and an ADH-validated RPA workflow",
             "last_run":self.last_run}
        if probe and available:
            try:
                version=self._command(["--version"],20)
                doctor=self._command(["doctor","--json"],45)
                parsed=None
                try:parsed=json.loads(doctor["output"])
                except (json.JSONDecodeError,TypeError):parsed={"raw":doctor["output"][-8000:]}
                out["probe"]={"version":version["output"],"doctor":parsed,"ok":True}
            except Exception as exc:
                out["probe"]={"ok":False,"error":f"{type(exc).__name__}: {exc}"}
        return out

    def validate(self,workflow,variables=None,task=None):
        wf=self._inside(workflow,self.workspace)
        if not wf.exists():raise FileNotFoundError(str(wf))
        args=["rpa","validate",str(wf)]
        if variables:
            var=self._inside(variables,self.workspace)
            if not var.is_file():raise FileNotFoundError(str(var))
            args+=["--vars",str(var)]
        if task:
            args+=["--task",str(task)[:240]]
        result=self._command(args,120)
        return {"provider":self.PROVIDER,"validated":True,"workflow":str(wf),"result":result}

    def run(self,workflow,variables=None,task=None,approved=False):
        if not approved:raise PermissionError("desktop RPA execution requires explicit owner approval")
        validation=self.validate(workflow,variables,task)
        wf=self._inside(workflow,self.workspace)
        stamp=time.strftime("%Y%m%d-%H%M%S")
        out=(self.output_root/stamp).resolve()
        out.mkdir(parents=True,exist_ok=False)
        args=["rpa","run",str(wf)]
        if variables:
            args+=["--vars",str(self._inside(variables,self.workspace))]
        if task:args+=["--task",str(task)[:240]]
        args+=["--output-root",str(out)]
        result=self._command(args,900)
        self.last_run={"at":time.time(),"workflow":str(wf),"output_root":str(out),"ok":True}
        return {"provider":self.PROVIDER,"validation":validation,"run":result,"output_root":str(out)}
