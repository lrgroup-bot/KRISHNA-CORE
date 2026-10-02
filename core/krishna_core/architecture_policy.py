from __future__ import annotations
from pathlib import Path
import json,re

class ArchitecturePolicy:
    """Machine-readable dependency rules checked against CodeBrain import edges."""
    def __init__(self,rules=()):
        self.rules=list(rules or [])
    @classmethod
    def from_file(cls,path):
        p=Path(path)
        if not p.is_file():return cls()
        data=json.loads(p.read_text(encoding="utf-8"))
        return cls(data.get("rules") or [])
    def check(self,index):
        violations=[]
        for edge in index.get("edges",[]):
            source=str(edge.get("source",""));target=str(edge.get("target",""))
            for rule in self.rules:
                src=str(rule.get("source","*"));dst=str(rule.get("target","*"));allowed=bool(rule.get("allowed",True))
                sm=src=="*" or re.search(src,source);dm=dst=="*" or re.search(dst,target)
                if sm and dm and not allowed:
                    violations.append({"source":source,"target":target,"rule":rule.get("id"),"reason":rule.get("reason","forbidden dependency")})
        return {"passed":not violations,"violations":violations,"rules_checked":len(self.rules)}
