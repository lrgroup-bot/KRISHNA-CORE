import tempfile,unittest
from pathlib import Path
from krishna_core.project_brain import ProjectBrain,LAYERS
class TestProjectBrain(unittest.TestCase):
 def test_contract_and_memory(self):
  with tempfile.TemporaryDirectory() as d:
   b=ProjectBrain(d);s=b.provision("demo")
   self.assertTrue(s["complete"]);self.assertEqual(s["governance_owner"],"Sudarshan")
   for x in LAYERS:self.assertTrue((Path(s["root"])/x).exists())
   b.record("demo","Completed","Feature A verified")
   self.assertIn("Feature A verified",(Path(s["root"])/"MEMORY.md").read_text(encoding="utf-8"))
if __name__=="__main__":unittest.main()
