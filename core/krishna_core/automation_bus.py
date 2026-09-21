from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import uuid

@dataclass
class BusEvent:
    id:str; topic:str; payload:dict; source:str; created_at:str
    def as_dict(self): return asdict(self)

class AutomationBus:
    """Compatibility facade for KRISHNA's native event bus. Narad owns workflow orchestration."""
    def __init__(self): self._subs={}; self._recent=[]
    def subscribe(self,topic,handler): self._subs.setdefault(topic,[]).append(handler)
    def unsubscribe(self,topic,handler):
        if topic in self._subs and handler in self._subs[topic]: self._subs[topic].remove(handler)
    def publish(self,topic,payload=None,source="krishna"):
        ev=BusEvent(str(uuid.uuid4()),topic,dict(payload or {}),source,datetime.now(timezone.utc).isoformat()).as_dict()
        self._recent.append(ev); self._recent=self._recent[-500:]
        results=[]
        for h in tuple(self._subs.get(topic,[])):
            try: results.append(h(ev))
            except Exception as exc: results.append({"error":str(exc),"handler":getattr(h,"__name__","handler")})
        return {"event":ev,"results":results}
    def recent(self,topic=None,limit=50):
        rows=self._recent if topic is None else [e for e in self._recent if e["topic"]==topic]
        return rows[-max(0,int(limit)):]
    def status(self): return {"recent_events":len(self._recent),"topics":sorted(self._subs),"owner":"narad-compatible-native-bus"}
