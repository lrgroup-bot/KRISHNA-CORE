import sys
import tempfile
import unittest
from pathlib import Path
from tools.sudarshan_local_adapters import run_adapter

class LocalAdapterTests(unittest.TestCase):
 def test_permission_required(self):
  with self.assertRaises(PermissionError):
   run_adapter('REA',[sys.executable],cwd='.')
 def test_missing_workdir(self):
  with self.assertRaises(ValueError):
   run_adapter('REA',[sys.executable],authorized=True,cwd='/nonexistent/path/for/test')
 def test_invalid_engine(self):
  with self.assertRaises(ValueError):
   run_adapter('NOT_REAL',[sys.executable],authorized=True,cwd='.')
 def test_local_adapter_result(self):
  with tempfile.TemporaryDirectory() as root:
   script=Path(root)/'adapter.py'
   script.write_text('import json\nprint(json.dumps(dict(engine="REA",status="passed",evidence_id="sample-evidence",summary="local test")))\n')
   result=run_adapter('REA',[sys.executable,str(script)],authorized=True,cwd=root)
   self.assertEqual(result.status,'passed')
 def test_engine_mismatch_rejected(self):
  with tempfile.TemporaryDirectory() as root:
   script=Path(root)/'adapter.py'
   script.write_text('import json\nprint(json.dumps(dict(engine="MiroFish",status="passed",evidence_id="e",summary="x")))\n')
   result=run_adapter('REA',[sys.executable,str(script)],authorized=True,cwd=root)
   self.assertEqual(result.status,'failed')

if __name__=='__main__':unittest.main()
