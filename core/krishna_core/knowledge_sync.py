"""Versioned, merge-safe portable knowledge records."""
import json
from pathlib import Path
class KnowledgeSync:
 def read_jsonl(self,path):
  p=Path(path)
  if not p.exists(): return []
  return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
 def merge_jsonl(self,source,target,key="id"):
  src=self.read_jsonl(source); dst=self.read_jsonl(target); merged={str(x.get(key) or x.get("hash") or json.dumps(x,sort_keys=True)):x for x in dst}
  added=0
  for x in src:
   k=str(x.get(key) or x.get("hash") or json.dumps(x,sort_keys=True))
   if k not in merged: merged[k]=x; added+=1
  p=Path(target); p.parent.mkdir(parents=True,exist_ok=True); p.write_text("".join(json.dumps(x,sort_keys=True)+"\\n" for x in merged.values()),encoding="utf-8")
  return {"added":added,"total":len(merged)}
