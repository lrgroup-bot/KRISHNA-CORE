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
    def test_runtime_governance_layers_are_provisioned(self):
        with tempfile.TemporaryDirectory() as td:
            memory=FakeMemory()
            brain=ProjectBrain(memory,Path(td)/"project-brain")
            status=brain.provision("demo")
            self.assertTrue(status["complete"])
            self.assertFalse(status["source_tree_mutation"])
            for name in LAYERS:
                self.assertTrue((Path(status["root"])/name).is_file())

    def test_verified_learning_and_governance_coexist(self):
        with tempfile.TemporaryDirectory() as td:
            memory=FakeMemory()
            brain=ProjectBrain(memory,Path(td)/"project-brain")
            brain.provision("KRISHNA")
            brain.learn_verified("KRISHNA","goal",{"passed":True})
            ctx=brain.context("KRISHNA")
            self.assertTrue(memory.remembered)
            self.assertTrue(ctx["governance"]["complete"])
            self.assertIn("Verified result",(Path(ctx["governance"]["root"])/"MEMORY.md").read_text(encoding="utf-8"))

    def test_project_name_cannot_escape_governance_root(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve()
            status=ProjectBrain(root).provision("../../outside")
            resolved=Path(status["root"]).resolve()
            self.assertTrue(root in resolved.parents)


if __name__=="__main__":
    unittest.main()
