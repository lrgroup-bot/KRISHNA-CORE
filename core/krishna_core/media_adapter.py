from __future__ import annotations
import os, shlex
from pathlib import Path

class OpenMontageAdapter:
    """OpenMontage discovery/worker boundary. Installed source is not execution authority by itself."""
    DEFAULT_HOME=Path("E:/AI-Tools/OpenMontage")
    DEFAULT_PYTHON=DEFAULT_HOME/".venv/Scripts/python.exe"
    def __init__(self,worker_fabric,worker_name="openmontage",home=None,python=None,command=None):
        self.workers=worker_fabric
        self.worker_name=worker_name
        self.home=Path(home or os.getenv("OPENMONTAGE_HOME") or self.DEFAULT_HOME)
        self.python=Path(python or os.getenv("OPENMONTAGE_PYTHON") or self.DEFAULT_PYTHON)
        self.command=command or os.getenv("OPENMONTAGE_CMD")
    def installed(self):
        return self.home.is_dir() and self.python.is_file()
    def worker_registered(self):
        return self.worker_name in self.workers.workers
    def bridge_ready(self):
        return self.worker_registered() or bool(self.command)
    def available(self):
        # "available" means KRISHNA has a controlled execution bridge, not merely cloned source.
        return self.bridge_ready()
    def status(self):
        return {
            "provider":"openmontage",
            "installed":self.installed(),
            "available":self.available(),
            "bridge_ready":self.bridge_ready(),
            "worker_registered":self.worker_registered(),
            "home":str(self.home),
            "python":str(self.python),
            "command_configured":bool(self.command),
            "placement":"media-worker",
            "note":"Installed source is discovery only until a dedicated KRISHNA worker/command bridge is configured.",
        }
    def register_command_bridge(self):
        if self.worker_registered():
            return self.workers.describe(self.worker_name)
        if not self.command:
            raise RuntimeError("OPENMONTAGE_CMD is not configured; refusing to execute repository source directly")
        cmd=shlex.split(self.command, posix=False) if isinstance(self.command,str) else list(self.command)
        if not cmd:
            raise RuntimeError("OPENMONTAGE_CMD is empty")
        self.workers.register(self.worker_name,cmd,cwd=self.home,kind="media",autostart=False)
        return self.workers.describe(self.worker_name)
    def start(self):
        if not self.worker_registered():
            self.register_command_bridge()
        return self.workers.start(self.worker_name)
