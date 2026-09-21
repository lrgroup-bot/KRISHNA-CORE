from __future__ import annotations
import json, re, hashlib
from pathlib import Path
from datetime import datetime, timezone

class SkillCompiler:
    def __init__(self, root): self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
    @staticmethod
    def _slug(s): return re.sub(r'[^a-z0-9]+','-',str(s).lower()).strip('-')[:64] or 'skill'
    def compile_candidate(self,name,steps,project='KRISHNA',evidence=None):
        payload={"schema":1,"name":name,"project":project,"authority":"guidance_only","steps":list(steps or []),"evidence":list(evidence or []),"created_at":datetime.now(timezone.utc).isoformat(),"status":"candidate"}
        payload['digest']=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
        path=self.root/f"{self._slug(project)}__{self._slug(name)}.json"; path.write_text(json.dumps(payload,indent=2),encoding='utf-8')
        return {"path":str(path),**payload}
    def promote(self,path,benchmark):
        p=Path(path); data=json.loads(p.read_text(encoding='utf-8'))
        if not benchmark.get('passed'): raise ValueError('benchmark has not passed')
        data['status']='verified'; data['benchmark']=benchmark; p.write_text(json.dumps(data,indent=2),encoding='utf-8'); return data
