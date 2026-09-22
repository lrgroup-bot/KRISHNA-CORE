from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class Specialist:
    name:str; role:str; permissions:tuple; evidence_required:bool=True
    def as_dict(self): return {**asdict(self),"permissions":list(self.permissions)}

DEFAULT_SPECIALISTS=(
    Specialist("researcher","source discovery and cross-checking",("web.read","memory.write")),
    Specialist("code-investigator","structural code analysis and root-cause tracing",("code.read","cbm.query","memory.write")),
    Specialist("implementer","bounded code changes",("code.read","code.write","tests.run")),
    Specialist("verifier","independent verification; cannot implement its own finding",("code.read","tests.run","evidence.write")),
    Specialist("ui-guardian","objective UI/runtime defect detection",("browser.read","browser.test","evidence.write")),
    Specialist("automation-engineer","Narad workflow construction and sandbox validation",("narad.write","narad.test")),
    Specialist("media-worker","delegates media jobs to approved provider adapters",("media.create","files.write")),\n    Specialist("bhumiputra","isolated field geospatial/geological engineering",("geo.read","survey.write","evidence.write","worker.execute")),
)
class SpecialistRegistry:
    def __init__(self,specialists=DEFAULT_SPECIALISTS): self._items={s.name:s for s in specialists}
    def get(self,name): return self._items[name].as_dict()
    def list(self): return [x.as_dict() for x in self._items.values()]
