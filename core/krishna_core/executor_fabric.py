from __future__ import annotations
import subprocess, sys, time
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class ExecutionResult:
    executor:str; ok:bool; command:str; returncode:int; stdout:str; stderr:str; duration_ms:int
    def as_dict(self): return asdict(self)

class ExecutorFabric:
    """Native executor boundary with optional OpenHands/Open Interpreter adapters.
    External frameworks are adapters, never owners of KRISHNA state or policy.
    """
    def __init__(self, policy): self.policy=policy
    def capabilities(self):
        return {"native":{"shell":True,"python":True},"openhands":{"available":self._has('openhands')},"open_interpreter":{"available":self._has('interpreter')}}
    @staticmethod
    def _has(name):
        try: __import__(name); return True
        except Exception: return False
    def run(self, command, cwd, approved=False, timeout=120):
        decision=self.policy.action("shell", mutating=True, approved=approved)
        if not decision.allowed: raise PermissionError(decision.reason)
        started=time.perf_counter()
        cp=subprocess.run(command,cwd=str(cwd),shell=True,text=True,capture_output=True,timeout=timeout)
        return ExecutionResult("native",cp.returncode==0,command,cp.returncode,cp.stdout[-12000:],cp.stderr[-12000:],int((time.perf_counter()-started)*1000)).as_dict()
