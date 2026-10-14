from __future__ import annotations
from dataclasses import dataclass,asdict

@dataclass(frozen=True)
class ModelCandidate:
 model_id:str; source:str; license:str; size_gb:float; ram_gb:float; vram_gb:float
 tasks:tuple[str,...]=(); free:bool=True; local:bool=True
 def as_dict(self):return asdict(self)

class LocalModelEvolution:
 """VISHWAKARMA model lifecycle: discover -> gate -> quarantine -> benchmark -> promote."""
 FREE_LICENSE_HINTS=("apache","mit","bsd","llama","gemma","qwen","deepseek","mistral","community")
 def __init__(self,hardware_provider=None):
  self.hardware_provider=hardware_provider or (lambda:{"ram_gb":0,"vram_gb":0,"disk_free_gb":0})
  self.quarantine={};self.approved={}
 def evaluate(self,row):
  c=ModelCandidate(**row) if not isinstance(row,ModelCandidate) else row;hw=self.hardware_provider()
  license_ok=bool(c.license) and any(x in c.license.lower() for x in self.FREE_LICENSE_HINTS)
  fits=bool(c.ram_gb<=float(hw.get("ram_gb",0)) and c.vram_gb<=float(hw.get("vram_gb",0))
            and c.size_gb*1.25<=float(hw.get("disk_free_gb",0)))
  ok=bool(c.free and c.local and license_ok and fits)
  return {"candidate":c.as_dict(),"eligible_for_download":ok,"license_ok":license_ok,"hardware_fit":fits,
   "hardware":hw,"auto_promote":False,"money_cost":"₹0 only"}
 def quarantine_download(self,row,downloader):
  verdict=self.evaluate(row)
  if not verdict["eligible_for_download"]:return {**verdict,"downloaded":False}
  result=downloader(verdict["candidate"]["model_id"])
  if not result.get("ok"):return {**verdict,"downloaded":False,"download":result}
  self.quarantine[verdict["candidate"]["model_id"]]={"candidate":verdict["candidate"],"download":result}
  return {**verdict,"downloaded":True,"quarantined":True,"auto_promote":False}
 def benchmark(self,model_id,results,current_baseline=None):
  if model_id not in self.quarantine:raise KeyError("model is not quarantined")
  quality=float(results.get("quality",0));stability=float(results.get("stability",0));latency=float(results.get("latency_ms",1e12))
  baseline=float((current_baseline or {}).get("quality",0))
  passed=quality>=baseline and stability>=0.95 and latency>0
  self.quarantine[model_id]["benchmark"]=dict(results);self.quarantine[model_id]["benchmark_passed"]=passed
  return {"model_id":model_id,"benchmark_passed":passed,"promotion_ready":passed,"auto_promote":False}
 def promote(self,model_id,approved=False):
  row=self.quarantine.get(model_id)
  if not row or not row.get("benchmark_passed"):raise PermissionError("benchmark gate not passed")
  if not approved:raise PermissionError("promotion requires KRISHNA/SUDARSHAN approval")
  self.approved[model_id]=row;return {"model_id":model_id,"promoted":True}
