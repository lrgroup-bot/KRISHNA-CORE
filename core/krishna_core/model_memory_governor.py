from __future__ import annotations

import json
import threading
import time
import urllib.request

from .config import settings


class ModelMemoryGovernor:
    """Local Ollama memory-pressure relief.

    It never deletes models. On critical RAM pressure it may ask Ollama to unload
    currently resident models by setting keep_alive=0.
    """

    def __init__(self,base_url=None):
        self.base_url=(base_url or settings.ollama_url).rstrip("/")
        self._lock=threading.RLock();self.last_action=None;self.actions=[]

    def running(self):
        try:
            with urllib.request.urlopen(self.base_url+"/api/ps",timeout=5) as r:data=json.loads(r.read().decode())
            return [{"name":x.get("name") or x.get("model"),"size":x.get("size"),"size_vram":x.get("size_vram"),
                     "expires_at":x.get("expires_at")} for x in data.get("models",[])]
        except Exception:return []

    def unload(self,model):
        model=str(model or "").strip()
        if not model:raise ValueError("model is required")
        body=json.dumps({"model":model,"prompt":"","stream":False,"keep_alive":0}).encode()
        req=urllib.request.Request(self.base_url+"/api/generate",data=body,headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=30) as r:r.read()
        event={"model":model,"action":"unload","at":time.time()}
        with self._lock:
            self.last_action=event;self.actions=(self.actions+[event])[-100:]
        return event

    def unload_all(self):
        results=[]
        for row in self.running():
            try:results.append({**self.unload(row["name"]),"ok":True})
            except Exception as exc:results.append({"model":row.get("name"),"ok":False,"error":f"{type(exc).__name__}: {exc}"})
        return {"requested":len(results),"results":results}

    def relieve(self,memory_percent,threshold=90):
        value=float(memory_percent)
        if value<float(threshold):
            return {"acted":False,"reason":"below critical unload threshold","memory_percent":value,"threshold":threshold}
        out=self.unload_all()
        return {"acted":bool(out["requested"]),"memory_percent":value,"threshold":threshold,**out}

    def status(self):
        with self._lock:
            return {"running_models":self.running(),"last_action":self.last_action,"recent_actions":list(self.actions[-20:]),
                    "policy":"unload only; never delete local models"}
