from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import uuid

@dataclass
class MemoryEnvelope:
    id:str; project:str; kind:str; text:str; source:str; verified:bool; confidence:float; created_at:str; metadata:dict
    def as_dict(self): return asdict(self)

class MemoryFabric:
    """Gyan-Bhandar is canonical; optional memory/code engines stay behind this facade."""
    KINDS=("working","episodic","semantic","graph","skill","evidence")
    def __init__(self, memory, gyan, *, graft=None, codebase_memory=None):
        self.memory=memory
        self.gyan=gyan
        self.graft=graft
        self.codebase_memory=codebase_memory
    def adapters(self):
        out={"gyan_bhandar":True,"graphiti":self._has('graphiti_core') or self._has('graphiti'),"letta":self._has('letta'),"mem0":self._has('mem0')}
        out["graft"]=bool(self.graft and self.graft.status().get("available"))
        out["codebase_memory"]=bool(self.codebase_memory and self.codebase_memory.status().get("available"))
        return out
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

    def structural_context(self,project_root,query,limit=20):
        """Read-only structural code context from configured Codebase-Memory."""
        if not self.codebase_memory:
            return {"available":False,"reason":"codebase-memory adapter not configured","results":[]}
        status=self.codebase_memory.status()
        if not status.get("available"):
            return {"available":False,"reason":"codebase-memory executable not available","results":[],"status":status}
        result=self.codebase_memory.query(query,project_root=project_root,limit=limit)
        return {"available":True,"authority":"read-only structural context","results":result}

    def optional_memory_query(self,text):
        """Query Graft as optional backing context without bypassing Gyan-Bhandar."""
        if not self.graft:
            return {"available":False,"reason":"graft adapter not configured"}
        status=self.graft.status()
        if not status.get("available"):
            return {"available":False,"reason":"graft executable not available","status":status}
        return {
            "available":True,
            "result":self.graft.query(text),
            "authority":"optional context only; trusted memory remains Gyan-Bhandar",
        }
