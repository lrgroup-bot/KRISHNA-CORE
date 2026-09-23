import unittest
from pathlib import Path


class HistoricalConsolidationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo=Path(__file__).resolve().parents[2]

    def test_restored_capabilities_are_wired_not_dead_files(self):
        orch=(self.repo/"core"/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
        for needle in (
            "self.vishvakarma = VishvakarmaRishi",
            "self.sudarshan_design = SudarshanDesignEngine",
            "self.sudarshan_projects = SudarshanProjectOrchestrator",
            '"design.plan"',
            '"vishvakarma.retrieve"',
            '"vishvakarma.verify"',
            '"model.scout.evaluate"',
            '"model.scout.recommend"',
        ):
            self.assertIn(needle,orch)

    def test_old_weaker_cloud_mesh_is_not_restored_as_authority(self):
        core=self.repo/"core"/"krishna_core"
        self.assertFalse((core/"cloud_providers.py").exists())
        self.assertFalse((core/"unified_model_mesh.py").exists())
        router=(core/"router.py").read_text(encoding="utf-8")
        self.assertIn("no live-verified zero-cost provider succeeded",router)
        self.assertIn("KRISHNA_ALLOW_PAID_CLOUD",router)

    def test_current_architecture_audit_remains_canonical(self):
        truth=(self.repo/"core"/"krishna_core"/"architecture_truth.py").read_text(encoding="utf-8")
        self.assertIn("unmerged/divergent feature branches",truth)
        self.assertIn("requirements + current source + runtime acceptance are authoritative",truth)


if __name__=="__main__":
    unittest.main()
