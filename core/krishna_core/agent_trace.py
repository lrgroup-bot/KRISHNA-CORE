from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import json,time,uuid
class AgentTrace:
 """Dependency-free JSONL trace compatible with later OpenTelemetry export adapters."""
 def __init__(self,path): self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
 def emit(self,name,**attrs):
  row={"trace_event_id":uuid.uuid4().hex,"ts":time.time(),"name":str(name),"attrs":attrs}
  with self.path.open("a",encoding="utf-8") as f:f.write(json.dumps(row,ensure_ascii=False)+"\n")
  return row
 @contextmanager
 def span(self,name,**attrs):
  start=time.perf_counter(); self.emit(name+".start",**attrs)
  try: yield
  except Exception as e:
   self.emit(name+".error",elapsed_ms=(time.perf_counter()-start)*1000,error=type(e).__name__); raise
  else:self.emit(name+".end",elapsed_ms=(time.perf_counter()-start)*1000)
