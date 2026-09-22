from __future__ import annotations

"""Capability-gated Android QA provider for KRISHNA Mobile.

Google ARTEMIS is an optional external Apache-2.0 provider. KRISHNA does not bundle,
auto-install, or grant it authority. It is invoked only for owner-approved mobile QA
and returns bounded evidence to the existing KRISHNA/Sudarshan verification flow.
"""

from pathlib import Path
import json
import os
import subprocess
import time


class AndroidTestFabric:
    PROVIDER="google-artemis"
    LICENSE="Apache-2.0"

    def __init__(self,runtime_root):
        self.runtime_root=Path(runtime_root).resolve()
        configured=os.getenv("KRISHNA_ARTEMIS_EXE","").strip()
        self.exe=Path(configured).resolve() if configured else (
            self.runtime_root/"tools"/"android"/"artemis"/".venv"/"Scripts"/"artemis.exe"
        ).resolve()
        self.report_root=(self.runtime_root/"reports"/"android-testing").resolve()
        self.report_root.mkdir(parents=True,exist_ok=True)
        self.last_run=None

    def _ready(self):
        return self.exe.is_file() and (not self.exe.drive or self.exe.drive.upper()=="E:")

    def _run(self,args,timeout=1200):
        if not self._ready():
            raise RuntimeError("ARTEMIS Android provider is not installed/configured on the KRISHNA E: runtime")
        p=subprocess.run([str(self.exe),*args],capture_output=True,text=True,timeout=timeout,shell=False)
        output=((p.stdout or "")+"\n"+(p.stderr or "")).strip()
        if p.returncode:
            raise RuntimeError("ARTEMIS command failed: "+(output[-6000:] or f"exit {p.returncode}"))
        return {"ok":True,"exit_code":p.returncode,"output":output[-40000:]}

    def status(self,probe=False):
        available=self._ready()
        row={
            "owner":"KRISHNA Android Test Fabric","provider":self.PROVIDER,"license":self.LICENSE,
            "available":available,"executable":str(self.exe),"mode":"owner-approved-qa-only",
            "authority":"KRISHNA/Sudarshan","auto_install":False,
            "policy":"test the owner's KRISHNA Android app/device only; no general background phone control",
            "last_run":self.last_run,
        }
        if probe and available:
            try:row["probe"]={**self._run(["--help"],30),"ok":True}
            except Exception as exc:row["probe"]={"ok":False,"error":f"{type(exc).__name__}: {exc}"}
        return row

    @staticmethod
    def _instruction(text):
        value=str(text or "").strip()
        if not value:raise ValueError("Android test instruction is required")
        if len(value)>4000:raise ValueError("Android test instruction exceeds 4000 characters")
        return value

    def run_task(self,instruction,profile="flash",approved=False):
        if not approved:raise PermissionError("Android device automation requires explicit owner approval")
        instruction=self._instruction(instruction)
        profile=str(profile or "flash").strip().lower()
        if profile not in {"flash","pro"}:raise ValueError("ARTEMIS profile must be flash or pro")
        result=self._run(["run",instruction,"--profile",profile],1800)
        stamp=time.strftime("%Y%m%d-%H%M%S")
        report=self.report_root/f"artemis-{stamp}.json"
        payload={"provider":self.PROVIDER,"profile":profile,"instruction":instruction,"result":result,"at":time.time()}
        report.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
        self.last_run={"at":payload["at"],"profile":profile,"report":str(report),"ok":True}
        return {"provider":self.PROVIDER,"profile":profile,"report":str(report),"result":result}
