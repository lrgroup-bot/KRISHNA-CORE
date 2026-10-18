import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from tools.sudarshan_adapter_preflight import main

class PreflightTests(unittest.TestCase):
 def test_missing_executable(self):
  with tempfile.TemporaryDirectory() as root:
   manifest=Path(root)/"manifest.json"
   manifest.write_text(json.dumps({"adapters":{"REA":{"probe":["/nonexistent/rea","--version"]}}}))
   with contextlib.redirect_stdout(io.StringIO()) as output:
    result=main(["--manifest",str(manifest)])
   self.assertEqual(result,2)
   self.assertEqual(json.loads(output.getvalue())["REA"]["status"],"executable_missing")
 def test_python_probe(self):
  with tempfile.TemporaryDirectory() as root:
   manifest=Path(root)/"manifest.json"
   manifest.write_text(json.dumps({"adapters":{"REA":{"probe":[sys.executable,"--version"]}}}))
   with contextlib.redirect_stdout(io.StringIO()) as output:
    result=main(["--manifest",str(manifest)])
   self.assertEqual(result,0)
   self.assertEqual(json.loads(output.getvalue())["REA"]["status"],"probe_ok")

if __name__=="__main__":unittest.main()
