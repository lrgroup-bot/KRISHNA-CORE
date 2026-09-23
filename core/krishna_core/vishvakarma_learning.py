from dataclasses import dataclass,asdict
from pathlib import Path
import json,time
@dataclass
class ResearchLesson:
 source:str;source_version:str;license:str;topic:str;lesson:str;evidence:str
 confidence:float=.5;status:str="candidate";failure_pattern:str=""
class VishvakarmaLearning:
 def __init__(self,root):self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
 def ingest(self,x):
  if not x.source or not x.lesson or not x.evidence:raise ValueError("provenance required")
  row=asdict(x);row.update({"rishi":"Vishvakarma","brahma_review_required":x.status=="candidate","learned_at":time.time()})
  with (self.root/"vishvakarma_knowledge.jsonl").open("a",encoding="utf-8") as h:h.write(json.dumps(row,ensure_ascii=False)+"\n")
  return row
 def verify(self,x):x.status="verified";x.confidence=max(x.confidence,.8);return self.ingest(x)
