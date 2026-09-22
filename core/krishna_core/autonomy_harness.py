"""Persistent maker/checker execution harness.

KRISHNA plans; maker changes an isolated workspace; checker independently
verifies evidence. Completion requires explicit checks rather than self-report.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
import hashlib,json,time

@dataclass
class HarnessState:
    goal:str
    phase:str="planned"
    attempts:int=0
    evidence:list|None=None
    failures:list|None=None
    def __post_init__(self):
        self.evidence=[] if self.evidence is None else self.evidence
        self.failures=[] if self.failures is None else self.failures
    def as_dict(self): return asdict(self)

class AutonomyHarness:
    PHASES=("planned","making","checking","repairing","verified","blocked")
    def __init__(self,store=None,max_attempts=5):
        self.store=store; self.max_attempts=max(1,int(max_attempts))

    def checkpoint(self,state):
        payload=state.as_dict()
        payload["receipt"]=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
        payload["timestamp"]=time.time()
        if self.store: self.store(payload)
        return payload

    def begin(self,goal):
        if not str(goal).strip(): raise ValueError("goal required")
        return self.checkpoint(HarnessState(str(goal).strip()))

    def evaluate(self,state,checks):
        state.phase="checking"; state.attempts+=1
        failed=[c for c in checks if not bool(c.get("ok"))]
        state.evidence.extend(checks)
        if not failed: state.phase="verified"
        elif state.attempts>=self.max_attempts: state.phase="blocked"
        else:
            state.phase="repairing"
            state.failures.extend(failed)
        return self.checkpoint(state)
