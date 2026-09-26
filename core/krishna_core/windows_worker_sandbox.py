from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess


class WindowsWorkerSandbox:
    """KRISHNA adapter for the open-source Codex Windows sandbox.

    KRISHNA owns policy; Codex may provide OS enforcement. If Codex is absent or
    setup is incomplete, this component refuses to claim the worker is sandboxed.
    """

    def __init__(self,state_root):
        self.state_root=Path(state_root).resolve();self.state_root.mkdir(parents=True,exist_ok=True)

    @staticmethod
    def _codex():
        configured=os.getenv("KRISHNA_CODEX_EXE","").strip()
        if configured:
            p=Path(configured).resolve()
            return str(p) if p.is_file() else None
        return shutil.which("codex")

    def plan(self,worktree,worker_id,network=False):
        wt=Path(worktree).resolve()
        codex=self._codex()
        return {
            "worker_id":str(worker_id),
            "worktree":str(wt),
            "provider":"openai-codex-windows-sandbox",
            "provider_available":bool(codex),
            "provider_executable":codex,
            "mode":"workspace-write",
            "filesystem":{"write":[str(wt)],"protected":[".git","credentials","other projects"]},
            "network":{"default":"managed/disabled by configured permission profile","requested":bool(network)},
            "setup_command":"codex sandbox setup --elevated --current-user",
            "run_shape":"codex sandbox windows -c sandbox_mode=\"workspace-write\" -- <command> <args...>",
            "ready":bool(codex) and os.name=="nt",
            "truth":"ready means provider binary is present on Windows; enforcement must still pass a smoke probe before production use",
        }

    def probe(self,worktree):
        codex=self._codex();wt=Path(worktree).resolve()
        if os.name!="nt":
            return {"ready":False,"reason":"windows_only"}
        if not codex:
            return {"ready":False,"reason":"codex_cli_missing"}
        if not wt.is_dir():
            return {"ready":False,"reason":"worktree_missing"}
        marker=".krishna_sandbox_probe.txt"
        target=wt/marker
        target.unlink(missing_ok=True)
        cmd=[codex,"sandbox","windows","-c",'sandbox_mode="workspace-write"',"--",
             "python","-c",f"from pathlib import Path; Path(r'{marker}').write_text('ok',encoding='utf-8')"]
        p=subprocess.run(cmd,cwd=str(wt),capture_output=True,text=True,timeout=45,shell=False)
        exists=target.is_file()
        target.unlink(missing_ok=True)
        return {
            "ready":p.returncode==0 and exists,
            "exit_code":p.returncode,
            "write_in_worktree":exists,
            "stderr":(p.stderr or "")[-4000:],
            "provider":"openai-codex-windows-sandbox",
        }

    def run(self,worktree,worker_id,command,args=None,*,approved=False,timeout=900):
        if not approved:
            raise PermissionError("sandboxed worker execution requires KRISHNA/Sudarshan approval")
        wt=Path(worktree).resolve()
        probe=self.probe(wt)
        if not probe.get("ready"):
            raise RuntimeError("Codex Windows sandbox is not verified ready: "+str(probe.get("reason") or probe.get("stderr") or "probe failed"))
        codex=self._codex()
        argv=[codex,"sandbox","windows","-c",'sandbox_mode="workspace-write"',"--",str(command),*[str(x) for x in (args or [])]]
        p=subprocess.run(argv,cwd=str(wt),capture_output=True,text=True,timeout=max(1,int(timeout)),shell=False)
        return {
            "worker_id":str(worker_id),"worktree":str(wt),"provider":"openai-codex-windows-sandbox",
            "command":[str(command),*[str(x) for x in (args or [])]],
            "exit_code":p.returncode,"ok":p.returncode==0,
            "stdout":(p.stdout or "")[-30000:],"stderr":(p.stderr or "")[-30000:],
            "sandbox_verified":True,
        }

    def status(self):
        return {
            "component":"KRISHNA Windows Worker Sandbox",
            "platform":os.name,
            "provider":"openai-codex-windows-sandbox",
            "provider_available":bool(self._codex()),
            "enforcement":"external OS sandbox when verified by probe; otherwise unavailable",
            "logical_policy_is_not_os_enforcement":True,
        }
