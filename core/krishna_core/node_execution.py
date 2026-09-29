from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import urlparse
import shlex
import shutil
import subprocess


class TrustedNodeExecutor:
    """Bounded SSH execution for already-trusted Mac/Linux KRISHNA worker nodes.

    This is not a trust authority. It consumes NodeRegistry trust and refuses
    password prompting, unknown host keys, unapproved execution, unsupported
    platforms, or commands outside the engineering allowlist.
    """

    ALLOWED_PROGRAMS={
        "git","python","python3","pytest","npm","pnpm","yarn","cargo","cmake",
        "ninja","dotnet","java","javac","gradle","gradlew","./gradlew","blender",
    }

    def __init__(self,node_registry):
        self.nodes=node_registry

    @staticmethod
    def _endpoint(node):
        parsed=urlparse(str(node.get("endpoint") or ""))
        if parsed.scheme!="ssh" or not parsed.hostname:
            raise ValueError("trusted remote execution requires ssh:// endpoint")
        if parsed.password:
            raise PermissionError("password-bearing SSH endpoints are forbidden")
        if parsed.path not in {"","/"} or parsed.query or parsed.fragment:
            raise ValueError("SSH endpoint must contain only user, host and optional port")
        target=(parsed.username+"@" if parsed.username else "")+parsed.hostname
        return target,parsed.port

    @classmethod
    def _command(cls,argv):
        args=[str(x) for x in argv or []]
        if not args:raise ValueError("remote command is required")
        program=args[0].replace("\\","/").split("/")[-1].lower()
        if program not in {x.replace("./","").lower() for x in cls.ALLOWED_PROGRAMS}:
            raise PermissionError("remote program is outside KRISHNA engineering allowlist")
        for arg in args:
            if "\n" in arg or "\r" in arg or "\x00" in arg:
                raise ValueError("remote command arguments contain forbidden control characters")
            if len(arg)>8000:raise ValueError("remote command argument too long")
        return args

    def plan(self,capability,command,platform=None):
        node=self.nodes.select(str(capability),platform)
        if not node:return {"ready":False,"reason":"no trusted online node with capability"}
        args=self._command(command)
        target,port=self._endpoint(node)
        workspace=str(node.get("workspace_root") or "").strip()
        if not workspace or not PurePosixPath(workspace).is_absolute():
            return {"ready":False,"reason":"trusted node workspace_root is not configured","node":node}
        return {
            "ready":bool(shutil.which("ssh")),
            "node":node,"target":target,"port":port,"workspace_root":workspace,
            "command":args,"transport":"openssh-batch","credential_mode":"ssh-agent/key only",
            "host_key_policy":"StrictHostKeyChecking=yes",
        }

    def run(self,capability,command,*,platform=None,approved=False,timeout=1800):
        if not approved:raise PermissionError("trusted-node execution requires owner/Sudarshan approval")
        plan=self.plan(capability,command,platform)
        if not plan.get("ready"):raise RuntimeError(str(plan.get("reason") or "trusted node unavailable"))
        remote="cd -- "+shlex.quote(plan["workspace_root"])+" && "+shlex.join(plan["command"])
        cmd=[
            "ssh","-o","BatchMode=yes","-o","StrictHostKeyChecking=yes",
            "-o","ConnectTimeout=10",
        ]
        if plan.get("port"):cmd += ["-p",str(plan["port"])]
        cmd += [plan["target"],remote]
        proc=subprocess.run(cmd,capture_output=True,text=True,timeout=max(1,int(timeout)),shell=False)
        return {
            "ok":proc.returncode==0,"exit_code":proc.returncode,
            "node_id":plan["node"]["id"],"transport":"openssh-batch",
            "stdout":(proc.stdout or "")[-50000:],"stderr":(proc.stderr or "")[-50000:],
            "command":plan["command"],"workspace_root":plan["workspace_root"],
        }
