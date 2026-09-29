from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess


class WindowsWorkerSandbox:
    """KRISHNA adapter for an OS-enforced Windows coding-worker sandbox.

    When the open-source Codex CLI is installed, KRISHNA can run a worker command
    through its native Windows restricted-token sandbox. KRISHNA never installs,
    elevates, or provisions it silently; setup remains an explicit admin action.
    """

    def __init__(self,state_root):
        self.state_root=Path(state_root).resolve();self.state_root.mkdir(parents=True,exist_ok=True)
        self.codex_home=(self.state_root/"codex-home").resolve()
        self.codex_home.mkdir(parents=True,exist_ok=True)

    @staticmethod
    def _codex():
        return shutil.which("codex")

    def setup_plan(self):
        exe=self._codex()
        return {
            "provider":"openai-codex-windows-sandbox",
            "available":bool(exe),
            "codex_executable":exe,
            "codex_home":str(self.codex_home),
            "requires_admin_bootstrap":True,
            "setup_command":[
                exe or "codex","sandbox","setup","--elevated","--current-user",
                "--codex-home",str(self.codex_home),
            ],
            "automatic_install":False,
            "automatic_elevation":False,
        }

    def plan(self,worktree,worker_id,network=False):
        wt=Path(worktree).resolve()
        if not wt.exists():
            # planning is allowed before the worktree exists, but execution is not.
            exists=False
        else:
            exists=True
        flags=["-c",'sandbox_mode="workspace-write"']
        if not network:
            # Native Windows sandbox defaults to blocked direct egress for the
            # workspace-write profile; managed proxy/network allowlists can be
            # layered later without granting general network access.
            network_mode="restricted/default-deny"
        else:
            network_mode="managed-policy-required"
        return {
            "worker_id":str(worker_id),
            "worktree":str(wt),
            "worktree_exists":exists,
            "provider":"openai-codex-windows-sandbox",
            "provider_available":bool(self._codex()),
            "command_prefix":[self._codex() or "codex","sandbox","windows",*flags,"--"],
            "filesystem":{"write":[str(wt)],"protected":[".git","credentials","other projects"]},
            "network":{"mode":network_mode,"metadata_endpoints":"deny"},
            "token":"restricted/native Windows sandbox",
            "job_object":"provider-managed",
            "requires_admin_bootstrap":True,
            "ready":bool(os.name=="nt" and self._codex() and exists),
            "authority":"Sudarshan + owner policy",
        }

    def run(self,worktree,worker_id,command,*,approved=False,timeout=900):
        if not approved:raise PermissionError("sandboxed coding execution requires owner/Sudarshan approval")
        if os.name!="nt":raise RuntimeError("Windows sandbox execution is available only on Windows")
        exe=self._codex()
        if not exe:raise RuntimeError("Codex CLI Windows sandbox provider is not installed")
        wt=Path(worktree).resolve()
        if not wt.is_dir():raise FileNotFoundError(str(wt))
        argv=[str(x) for x in (command or []) if str(x)]
        if not argv:raise ValueError("sandbox command is required")
        cmd=[exe,"sandbox","windows","-c",'sandbox_mode="workspace-write"',"--",*argv]
        env=os.environ.copy();env["CODEX_HOME"]=str(self.codex_home)
        proc=subprocess.run(cmd,cwd=str(wt),env=env,capture_output=True,text=True,timeout=max(1,int(timeout)),shell=False)
        return {
            "provider":"openai-codex-windows-sandbox","worker_id":str(worker_id),
            "exit_code":proc.returncode,"ok":proc.returncode==0,
            "stdout":(proc.stdout or "")[-30000:],"stderr":(proc.stderr or "")[-30000:],
            "worktree":str(wt),
        }

    def status(self):
        return {
            "component":"KRISHNA Windows Worker Sandbox",
            "platform":os.name,
            "provider":"openai-codex-windows-sandbox",
            "provider_available":bool(self._codex()),
            "setup":self.setup_plan(),
            "enforcement":"os-enforced when provider is installed/provisioned; fail-closed otherwise",
            "logical_policy_is_not_os_enforcement":False if (os.name=="nt" and self._codex()) else True,
        }
