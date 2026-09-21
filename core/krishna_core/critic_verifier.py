from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass
class Verdict:
    status:str; passed:bool; checks:list; evidence:list; reason:str
    def as_dict(self): return asdict(self)

class IndependentCriticVerifier:
    """Verifier has no mutation methods. It judges evidence produced by workers."""
    def __init__(self, verification_engine, reviewer): self.engine=verification_engine; self.reviewer=reviewer
    def judge(self, checks, evidence=None):
        rows=list(checks or []); ev=list(evidence or [])
        failures=[x for x in rows if str(x.get('status','')).lower() in {'fail','failed','error'} or x.get('passed') is False]
        warnings=[x for x in rows if str(x.get('status','')).lower() in {'warning','warn'}]
        if failures: return Verdict('FAIL',False,rows,ev,f"{len(failures)} verification check(s) failed").as_dict()
        if warnings: return Verdict('WARNING',True,rows,ev,f"passed with {len(warnings)} warning(s)").as_dict()
        return Verdict('PASS',True,rows,ev,"all supplied checks passed").as_dict()
