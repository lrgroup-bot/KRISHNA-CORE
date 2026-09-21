from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import uuid
@dataclass
class BusEvent:
    id:str; topic:str; payload:dict; source:str; created_at:str
    def as_dict(self): return asdict(self)
class AutomationBus:
    """KRISHNA-native bus. n8n/Activepieces connect through webhooks/adapters."""
    def __init__(self): self._subs={}; self._recent=[]
    def subscribe(self,topic,handler): self._subs.setdefault(topic,[]).append(handler)
    def publish(self,topic,payload=None,source='krishna'):
        ev=BusEvent(str(uuid.uuid4()),topic,dict(payload or {}),source,datetime.now(timezone.utc).isoformat()).as_dict(); self._recent.append(ev); self._recent=self._recent[-200:]
        results=[]
        for h in self._subs.get(topic,[]): 
            try: results.append(h(ev))
            except Exception as exc: results.append({"error":str(exc)})
        return {"event":ev,"results":results}
    def status(self): return {"recent_events":len(self._recent),"topics":sorted(self._subs)}
