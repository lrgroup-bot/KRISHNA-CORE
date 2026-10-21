import unittest
from krishna_core.garuda_diagnostics import plan_diagnostics, classify_repair_action

class GarudaDiagnosticPlanTests(unittest.TestCase):
    def test_paired_windows_read_only(self):
        p=plan_diagnostics("device-1","windows",paired=True)
        self.assertIn("disk_smart_summary",p.actions)
        self.assertFalse(p.approval_required)
    def test_unpaired_rejected(self):
        with self.assertRaises(PermissionError):
            plan_diagnostics("device-1","android",paired=False)
    def test_mutation_rejected(self):
        with self.assertRaises(PermissionError):
            plan_diagnostics("device-1","windows",paired=True,requested_actions=["factory_reset"])
    def test_repair_never_autoexecutes(self):
        r=classify_repair_action("flash_firmware")
        self.assertTrue(r["high_risk"])
        self.assertFalse(r["executable"])

if __name__=="__main__":
    unittest.main()
