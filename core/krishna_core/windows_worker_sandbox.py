from __future__ import annotations

from pathlib import Path
import os


class WindowsWorkerSandbox:
    """OS-boundary plan for autonomous coding workers.

    This component refuses to claim isolation unless the host is Windows, a managed
    worktree is supplied, and an elevated bootstrap has created the sandbox account/
    ACL/firewall policy. It does not silently weaken ACLs or install drivers.
    """

    def __init__(self,state_root):
        self.state_root=Path(state_root).resolve();self.state_root.mkdir(parents=True,exist_ok=True)

    def plan(self,worktree,worker_id,network=False):
        wt=Path(worktree).resolve()
        return {
            "worker_id":str(worker_id),
            "worktree":str(wt),
            "os_required":"windows",
            "account_name":"KRISHNA_SBX_"+str(worker_id).replace("-","_")[:24],
            "filesystem":{"write":[str(wt)],"read":["Windows","Program Files","approved toolchains"],"deny":["user profiles","credentials","other projects"]},
            "network":{"default":"allow-approved" if network else "deny","metadata_endpoints":"deny"},
            "token":"restricted",
            "job_object":"kill-on-close/resource-limits",
            "requires_admin_bootstrap":True,
            "ready":False,
        }

    def status(self):
        return {"component":"KRISHNA Windows Worker Sandbox","platform":os.name,"enforcement":"planned/bootstrap-required","logical_policy_is_not_os_enforcement":True}
