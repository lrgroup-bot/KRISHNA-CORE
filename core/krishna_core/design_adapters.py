from __future__ import annotations

"""Zero-vendor-lock local adapters for Sudarshan design tooling."""

from dataclasses import asdict, dataclass
import shutil
import subprocess


@dataclass(frozen=True)
class ToolResult:
    tool:str
    available:bool
    ok:bool
    output:str=""
    def as_dict(self): return asdict(self)


class LocalToolAdapter:
    def __init__(self,command):
        self.command=str(command or "").strip()
        if not self.command:
            raise ValueError("command is required")

    def executable(self):
        return shutil.which(self.command)

    def available(self):
        return self.executable() is not None

    def run(self,args=(),timeout=120):
        exe=self.executable()
        if not exe:
            return ToolResult(self.command,False,False,"not installed")
        argv=[exe,*[str(x) for x in (args or ())]]
        p=subprocess.run(
            argv,capture_output=True,text=True,
            timeout=max(1,min(int(timeout),600)),shell=False,
        )
        return ToolResult(
            self.command,True,p.returncode==0,
            ((p.stdout or "")+(p.stderr or ""))[-12000:],
        )


class PlaywrightCLI(LocalToolAdapter):
    def __init__(self):super().__init__("playwright-cli")


class StagehandAdapter:
    """Optional agentic-browser recovery. Disabled until explicitly configured."""
    def __init__(self,enabled=False):self.enabled=bool(enabled)
    def available(self):return self.enabled
    def status(self):
        return {
            "available":self.enabled,
            "mode":"optional recovery only",
            "canonical_browser":"Garudanetra/Playwright",
        }


class StorybookAdapter:
    """Component-state verification contract; project supplies its own runner."""
    def required_states(self):
        return ("default","hover","focus","disabled","loading","error","empty","long-text","mobile")
