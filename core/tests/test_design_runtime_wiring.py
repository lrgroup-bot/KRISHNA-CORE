import unittest
from pathlib import Path


class DesignRuntimeWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]

    def test_agi_kernel_wires_design_and_vishvakarma(self):
        text=(self.root/"core"/"krishna_core"/"agi_kernel.py").read_text(encoding="utf-8")
        self.assertIn("SudarshanDesignEngine",text)
        self.assertIn("VishvakarmaRishi",text)
        self.assertIn("VishvakarmaLearning",text)

    def test_main_orchestrator_binds_project_lifecycle_to_design_engine(self):
        text=(self.root/"core"/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
        self.assertIn("SudarshanProjectOrchestrator",text)
        self.assertIn("design_engine=self.sudarshan_design",text)\n        self.assertIn("vishvakarma=self.vishvakarma",text)


if __name__=="__main__":
    unittest.main()
