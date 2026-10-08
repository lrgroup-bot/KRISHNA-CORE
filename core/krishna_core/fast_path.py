from __future__ import annotations
import hashlib,json,time
from pathlib import Path

class VerifiedResponseCache:
    def __init__(self,path,max_entries=500):
        self.path=Path(path);self.max_entries=max(10,int(max_entries));self.items={};self._load()
    def _load(self):
        try:self.items=json.loads(self.path.read_text(encoding="utf-8")) if self.path.is_file() else {}
        except Exception:self.items={}
    def _save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        rows=sorted(self.items.items(),key=lambda x:x[1].get("at",0),reverse=True)[:self.max_entries]
        self.path.write_text(json.dumps(dict(rows),indent=2),encoding="utf-8")
    @staticmethod
    def key(request,context=""):return hashlib.sha256((str(request)+"\n"+str(context)).encode()).hexdigest()
    def get(self,request,context=""):
        row=self.items.get(self.key(request,context))
        return row.get("value") if row and row.get("verified") else None
    def put(self,request,value,context="",verified=False,evidence=None):
        if not verified: raise PermissionError("only verified results may enter fast-path cache")
        self.items[self.key(request,context)]={"value":value,"verified":True,"evidence":list(evidence or []),"at":time.time()};self._save()

class FastPathRouter:
    """Deterministic -> verified skill -> verified cache -> model/agent handoff."""
    def __init__(self,cache=None):self.cache=cache
    def route(self,request,*,deterministic=None,skill=None,context=""):
        if deterministic:
            out=deterministic(request)
            if out is not None:return {"tier":"deterministic","result":out}
        if skill:
            out=skill(request)
            if out is not None:return {"tier":"verified_skill","result":out}
        if self.cache:
            out=self.cache.get(request,context)
            if out is not None:return {"tier":"verified_cache","result":out}
        return {"tier":"model_or_agent","result":None}
