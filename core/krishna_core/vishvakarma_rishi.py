"""Rishi Vishvakarma: durable design/UI/software-craft knowledge curator."""
from dataclasses import dataclass,asdict
from pathlib import Path
import json,time
@dataclass
class DesignFinding:
 source:str; topic:str; finding:str; license:str="unknown"; confidence:float=0.5
 evidence:str=""; version:str=""; learned_at:float=0.0
 def normalized(self):
  d=asdict(self);d["learned_at"]=self.learned_at or time.time();return d
class VishvakarmaRishi:
 DOMAINS=("design-systems","ui-ux","typography","spacing","responsive-ui","component-architecture","image-to-code","visual-diff","browser-testing","accessibility","design-drift","frontend-quality","ui-repair")
 def __init__(self,root):self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
 def learn(self,finding:DesignFinding):
  if not finding.source or not finding.finding:raise ValueError("provenance and finding required")
  p=self.root/"vishvakarma_findings.jsonl"
  with p.open("a",encoding="utf-8") as h:h.write(json.dumps(finding.normalized(),ensure_ascii=False)+"\n")
  return {"stored":True,"rishi":"Vishvakarma","path":str(p)}
 def retrieve(self,topic,limit=20):
  p=self.root/"vishvakarma_findings.jsonl"
  if not p.exists():return []
  rows=[json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
  q=topic.lower();rows=[r for r in rows if q in (r["topic"]+" "+r["finding"]).lower()]
  return rows[-limit:]
