from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import uuid

@dataclass
class MemoryEnvelope:
    id:str; project:str; kind:str; text:str; source:str; verified:bool; confidence:float; created_at:str; metadata:dict
    def as_dict(self): return asdict(self)

class MemoryFabric:
    """Gyan-Bhandar is the canonical API; all optional memory engines stay behind this facade."""
    KINDS=("working","episodic","semantic","graph","skill","evidence")
    def __init__(self, memory, gyan): self.memory=memory; self.gyan=gyan
    def adapters(self):
        return {"gyan_bhandar":True,"graphiti":self._has('graphiti_core') or self._has('graphiti'),"letta":self._has('letta'),"mem0":self._has('mem0')}
    @staticmethod
    def _has(name):
        try: __import__(name); return True
        except Exception: return False
    def remember(self,project,kind,text,source="krishna",verified=False,confidence=.5,metadata=None):
        kind=str(kind or "episodic").strip().lower()
        if kind not in self.KINDS: raise ValueError("invalid memory kind")
        env=MemoryEnvelope(str(uuid.uuid4()),project,kind,text,source,bool(verified),float(confidence),datetime.now(timezone.utc).isoformat(),dict(metadata or {}))
        self.memory.remember(project,kind,text,{**env.metadata,"memory_envelope":env.as_dict()})
        return env.as_dict()
    def recall(self,project,topic=None,limit=50,verified_only=False):
        return self.gyan.recall(project,topic,limit,verified_only)

    def inventory(self,project):
        return self.gyan.inventory(project)

    def semantic_store(self,project,topic,text,evidence=None,source="krishna",verified=False,confidence=.5,provenance=None,supersedes=None):
        return self.gyan.store(project,topic,text,evidence or [],confidence,source,verified,"semantic",provenance or {},supersedes)
