from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone
import json
class ArchitectureLedger:
 """Append-only verified handover records for VISHWAKARMA -> MRITYUNJAY."""
 def __init__(self,path):self.path=Path(path).resolve()
 def append_verified(self,record):
  if str(record.get("status","")).upper()!="VERIFIED":raise ValueError("only VERIFIED changes become architecture truth")
  safe={k:v for k,v in dict(record).items() if k.lower() not in {"secret","token","password","api_key"}}
  block="\n\nVERIFIED CHANGE RECORD\n----------------------\n"+json.dumps(safe,indent=2,ensure_ascii=False)+"\n"
  with self.path.open("a",encoding="utf-8") as f:f.write(block)
  return {"appended":True,"path":str(self.path),"deployed_commit":safe.get("deployed_commit")}
 def verified_records(self):
  text=self.path.read_text(encoding="utf-8") if self.path.exists() else ""
  return {"path":str(self.path),"verified_change_records":text.count("VERIFIED CHANGE RECORD")}
