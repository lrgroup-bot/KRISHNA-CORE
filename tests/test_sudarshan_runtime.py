import json
import sys
import tempfile
import unittest
from pathlib import Path
from tools.sudarshan_runtime import run_pipeline,ORDER

class PipelineTests(unittest.TestCase):
 def test_requires_authorization(self):
  with self.assertRaises(PermissionError):run_pipeline("p","f",False,{},":memory:")
 def test_no_adapters_rejected(self):
  with tempfile.TemporaryDirectory() as root:
   with self.assertRaises(ValueError):
    run_pipeline("p","f",True,{},str(Path(root)/"e.sqlite"))
 def test_all_local_adapters_handoff(self):
  with tempfile.TemporaryDirectory() as root:
   root=Path(root)
   script=root/"adapter.py"
   script.write_text("import json,sys\nprint(json.dumps({'engine':sys.argv[1],'status':'passed','evidence_id':'test:'+sys.argv[1],'summary':'local smoke test'}))\n")
   config={engine:{"argv":[sys.executable,str(script),engine],"cwd":str(root)} for engine in ORDER}
   out=run_pipeline("p","f",True,config,str(root/"e.sqlite"))
   self.assertEqual(out["completed_engines"],list(ORDER))
   self.assertTrue(out["readiness"]["ready_for_human_review"])
   self.assertFalse(out["handoff"]["deployment_allowed"])
 def test_stops_after_failure(self):
  with tempfile.TemporaryDirectory() as root:
   root=Path(root)
   script=root/"bad.py"
   script.write_text("import sys\nsys.exit(2)\n")
   config={engine:{"argv":[sys.executable,str(script)],"cwd":str(root)} for engine in ORDER}
   out=run_pipeline("p","f",True,config,str(root/"e.sqlite"))
   self.assertEqual(out["completed_engines"],["REA"])
   self.assertTrue(out["execution_stopped"])

if __name__=="__main__":unittest.main()
