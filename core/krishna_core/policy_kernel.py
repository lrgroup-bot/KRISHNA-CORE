from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import urlparse

@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    risk: str = "low"
    requires_approval: bool = False
    def as_dict(self): return asdict(self)

class PolicyKernel:
    """Single execution boundary for KRISHNA AGI.

    Page/model text is data, never authority. Mutations require explicit project policy
    and, for destructive/high-impact operations, an approval token from the caller.
    """
    SAFE_SCHEMES={"http","https"}
    DESTRUCTIVE={"delete","format","wipe","publish","purchase","transfer","deploy_production","send_external"}
    def __init__(self, runtime_root: Path): self.runtime_root=Path(runtime_root).resolve()
    def browser_url(self,url:str)->PolicyDecision:
        p=urlparse(str(url or ''))
        if p.scheme not in self.SAFE_SCHEMES: return PolicyDecision(False,"unsupported browser scheme","high")
        return PolicyDecision(True,"web navigation allowed")
    def filesystem(self,path,roots=())->PolicyDecision:
        try: target=Path(path).resolve()
        except Exception: return PolicyDecision(False,"invalid filesystem path","high")
        allowed=[Path(x).resolve() for x in roots if x]
        if not allowed: return PolicyDecision(False,"no filesystem scope granted","high")
        if any(target==r or r in target.parents for r in allowed): return PolicyDecision(True,"path inside granted project scope")
        return PolicyDecision(False,"path outside granted project scope","high")
    def action(self,name,mutating=False,approved=False)->PolicyDecision:
        n=str(name or '').strip().lower()
        if n in self.DESTRUCTIVE and not approved: return PolicyDecision(False,"high-impact action requires approval","high",True)
        if mutating and not approved: return PolicyDecision(False,"mutation requires transaction approval","medium",True)
        return PolicyDecision(True,"action permitted by AGI boundary", "medium" if mutating else "low")
