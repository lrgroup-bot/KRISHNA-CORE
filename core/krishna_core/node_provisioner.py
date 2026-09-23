"""Copy-first, download-fallback provisioning with hardware-aware profiles."""
from dataclasses import dataclass
@dataclass
class Capacity:
 ram_gb:int=0; vram_gb:int=0; cpu_cores:int=0; disk_free_gb:int=0
class NodeProvisioner:
 PROFILES=(
  ("power",Capacity(32,12,12,80)),
  ("standard",Capacity(16,6,8,40)),
  ("light",Capacity(8,0,4,15)),
 )
 def profile(self,c):
  for name,minimum in self.PROFILES:
   if c.ram_gb>=minimum.ram_gb and c.vram_gb>=minimum.vram_gb and c.cpu_cores>=minimum.cpu_cores and c.disk_free_gb>=minimum.disk_free_gb:return name
  return "minimal"
 def provision_plan(self,c,artifacts,peer_available=True):
  profile=self.profile(c); out=[]
  for a in artifacts:
   if a.get("profiles") and profile not in a["profiles"]: continue
   out.append({"id":a["id"],"primary":"trusted-peer-copy" if peer_available else "approved-download","fallback":"approved-download" if peer_available else None,"sha256":a.get("sha256"),"source":a.get("source")})
  return {"profile":profile,"artifacts":out,"zero_paid_cloud":True}
 def next_method(self,item,copy_ok):
  if copy_ok:return "VERIFY_AND_INSTALL"
  if item.get("fallback")=="approved-download" and item.get("source"):return "DOWNLOAD_VERIFY_INSTALL"
  return "BLOCKED_NO_APPROVED_SOURCE"
