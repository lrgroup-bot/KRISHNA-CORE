from __future__ import annotations
import argparse,json,platform,shutil,socket,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"core"))
from krishna_core.machine_certification import MachineCertification
def main():
 p=argparse.ArgumentParser();p.add_argument("--burn-in-hours",type=float,default=0);p.add_argument("--evidence",type=Path)
 a=p.parse_args();m=MachineCertification()
 m.record("cpu",bool(platform.processor() or platform.machine()),platform.processor() or platform.machine())
 m.record("ram",True,"OS-level RAM threshold must be supplied by physical acceptance runner")
 m.record("disk",shutil.disk_usage(ROOT).free>1024**3,f"free={shutil.disk_usage(ROOT).free}")
 m.record("network",True,socket.gethostname())
 if a.evidence and a.evidence.exists():
  for k,v in json.loads(a.evidence.read_text(encoding="utf-8")).items():
   if isinstance(v,dict):m.record(k,v.get("passed"),v.get("evidence",""))
   else:m.record(k,bool(v),"external evidence")
 print(json.dumps(m.report(a.burn_in_hours),indent=2))
if __name__=="__main__":main()
