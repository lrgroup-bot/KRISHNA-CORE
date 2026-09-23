import tempfile
import unittest
from pathlib import Path

from krishna_core.project_brain import LAYERS, ProjectBrain


class FakeMemory:
    def __init__(self):
        self.remembered=[]
        self.audits=[]
    def remember(self,*args):
        self.remembered.append(args)
    def audit(self,*args):
        self.audits.append(args)
    def recall(self,project,limit=20):
        return [{"project":project,"limit":limit}]
    def incidents(self,project,limit=10):
        return [{"project":project,"limit":limit}]


class ProjectBrainTests(unittest.TestCase):
    def test_legacy_path_constructor_still_provisions_structured_layers(self):
        with tempfile.TemporaryDirectory() as td:
            brain=ProjectBrain(td)
            status=brain.provision("demo")
            self.assertTrue(status["complete"])
            self.assertFalse(status["source_tree_mutation"])
            for name in LAYERS:
                self.assertTrue((Path(status["root"])/name).is_file())
            brain.record("demo","Completed","Feature A verified")
            self.assertIn("Feature A verified",(Path(status["root"])/"MEMORY.md").read_text(encoding="utf-8"))

    def test_database_memory_and_runtime_governance_coexist(self):
        with tempfile.TemporaryDirectory() as td:
            memory=FakeMemory()
            brain=ProjectBrain(memory,Path(td)/"project-brain")
            brain.provision("KRISHNA")
            brain.learn_verified("KRISHNA","goal",{"passed":True})
            ctx=brain.context("KRISHNA")
            self.assertTrue(memory.remembered)
            self.assertTrue(ctx["governance"]["complete"])
            self.assertEqual(ctx["governance"]["governance_owner"],"Sudarshan")

    def test_project_name_cannot_escape_governance_root(self):
        with tempfile.TemporaryDirectory() as td:
            status=ProjectBrain(td).provision("../../outside")
            root=Path(status["root"]).resolve()
            self.assertTrue(Path(td).resolve() in root.parents)


if __name__=="__main__":
    unittest.main()
