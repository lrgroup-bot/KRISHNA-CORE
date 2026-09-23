"""Versioned, merge-safe portable knowledge records."""
import json
from pathlib import Path

class KnowledgeSync:
 def read_jsonl(self,path):
  p=Path(path)
  if not p.exists(): return []
  rows=[]
  for lineno,line in enumerate(p.read_text(encoding="utf-8").splitlines(),1):
   if not line.strip():continue
   row=json.loads(line)
   if not isinstance(row,dict):raise ValueError(f"JSONL row {lineno} must be an object")
   rows.append(row)
  return rows
 def _key(self,row,key):
  return str(row.get(key) or row.get("hash") or json.dumps(row,sort_keys=True,separators=(",",":")))
 def merge_jsonl(self,source,target,key="id"):
  src=self.read_jsonl(source); dst=self.read_jsonl(target)
  merged={self._key(x,key):x for x in dst}; added=0; conflicts=[]
  for x in src:
   k=self._key(x,key)
   if k not in merged:
    merged[k]=x; added+=1
   elif merged[k]!=x:
    conflicts.append(k)
  p=Path(target); p.parent.mkdir(parents=True,exist_ok=True)
  tmp=p.with_suffix(p.suffix+".tmp")
  tmp.write_text("".join(json.dumps(x,sort_keys=True)+"\n" for x in merged.values()),encoding="utf-8")
  tmp.replace(p)
  return {"added":added,"total":len(merged),"conflicts":conflicts,"conflict_count":len(conflicts)}
