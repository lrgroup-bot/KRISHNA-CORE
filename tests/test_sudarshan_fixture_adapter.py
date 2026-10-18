import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from tools.sudarshan_fixture_adapter import main

class FixtureTests(unittest.TestCase):
 def test_valid_fixture(self):
  with tempfile.TemporaryDirectory() as root:
   path=Path(root)/"fixture.json"
   path.write_text(json.dumps({"engine":"REA","checks":[{"name":"contract","passed":True}]}))
   with contextlib.redirect_stdout(io.StringIO()) as output:
    code=main(["REA","--fixture",str(path)])
   self.assertEqual(code,0)
   result=json.loads(output.getvalue())
   self.assertEqual(result["status"],"passed")
   self.assertIn("offline fixture",result["summary"])
 def test_failure(self):
  with tempfile.TemporaryDirectory() as root:
   path=Path(root)/"fixture.json"
   path.write_text(json.dumps({"engine":"REA","checks":[{"name":"contract","passed":False}]}))
   with contextlib.redirect_stdout(io.StringIO()):
    self.assertEqual(main(["REA","--fixture",str(path)]),1)
 def test_engine_mismatch(self):
  with tempfile.TemporaryDirectory() as root:
   path=Path(root)/"fixture.json"
   path.write_text(json.dumps({"engine":"MiroFish","checks":[{"name":"contract","passed":True}]}))
   with self.assertRaises(ValueError):
    main(["REA","--fixture",str(path)])

if __name__=="__main__":unittest.main()
